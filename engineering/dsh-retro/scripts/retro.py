#!/usr/bin/env python3
"""Aggregate DSH session logs into a compact retro digest.

Reads ~/.dsh/sessions/**/session.v4.jsonl.zstd, emits a small markdown digest
(and optionally full JSON) so the model reads kilobytes instead of gigabytes.

Usage:
  python3 retro.py                      # last 7 days, compare to previous 7
  python3 retro.py --days 30
  python3 retro.py --since 2026-10-01 --until 2026-10-15
  python3 retro.py --json /tmp/retro.json
  python3 retro.py --topic my-topic     # trace one topic across sessions
"""
import argparse
import collections
import datetime as dt
import json
import os
import re
import subprocess
import sys

SESSIONS = os.path.expanduser("~/.dsh/sessions")
HERE = os.path.dirname(os.path.abspath(__file__))

CJK = r"\u4e00-\u9fff"
CJK_RUN = re.compile(f"[{CJK}]+")
WORD = re.compile(r"[a-zA-Z][a-zA-Z0-9_.+-]{2,}")
UNESC = re.compile(r"~([0-9A-Fa-f]{4,6})~")

EN_STOP = set("""the and for with that this from your you are was were will would can could
should have has had not but all any our out its it's they them there here what when where
which who how why use used using into onto over under about after before more most some
such than then them these those very just only also does did doing make made get got
python src lib app let print return def class import true false none null json string
number object array value key data file files run running test tests code working
wants current instructions assistant respond returned output format following example example

""".split())

CJK_STOP = set("""我们 你们 他们 这个 那个 这些 那些 什么 怎么 可以 不是 就是 但是 如果 因为 所以 然后
现在 已经 还是 一个 一些 这样 那样 自己 时候 问题 没有 需要 应该 可能 直接 一下 东西 地方
的话 时候 就是 这个 是不 我们 他们 大家 这种 那段 里面 上面 下面 之前 之后 一下 这个
请问 帮我 麻烦 谢谢 好的 可以了 是不是 有没有 能不能 要不要 会不会 对不 你看 我觉得
继续 不要 实际 参考 用的 确认 两个 的是 完成 重新 内容 提交 信息 目前 显示 说明
的问题 最后 是一 工作 可以 需要 应该 这个 那个 我们 你们 他们 现在 已经 还是
但是 因为 所以 然后 如果 就是 没有 一个 一些 这样 那样 自己 时候 问题 东西
地方 里面 上面 下面 之前 之后 一下 一下 这种 那段 大家 或者是 以及 另外 同时
并且 而且 不过 其实 确实 直接 主要 具体 相关 对应 各自 有些 有的 一切 全部
""".split())

DEFAULT_KEYWORDS = {
    "域": {
        "DSH 本体": ["dsh", "deepseek harness", "插件", "plugin", "skill", "技能", "mcp", "连接器",
                    "提示词", "prompt", "上下文", "context", "会话", "session", "看板", "task board",
                    "子代理", "subagent", "模型", "model"],
        "成本/性能": ["token", "成本", "cost", "计费", "缓存", "cache", "性能", "延迟", "内存"],
        "记忆/复盘": ["记忆", "memory", "复盘", "retro", "总结", "归档", "审计", "audit"],
        "前端": ["react", "vue", "tailwind", "css", "页面", "组件", "样式", "设计", "ui", "动画"],
        "后端/数据": ["python", "typescript", "node", "sql", "api", "接口", "数据库", "脚本"],
        "工程操作": ["git", "合并", "分支", "冲突", "部署", "构建", "build", "测试", "lint", "ci", "回滚"],
        "调研/写作": ["调研", "对比", "选型", "方案", "评估", "分析", "报告", "文档", "周报", "写作"],
        "抓取/检索": ["抓取", "爬虫", "网页", "搜索", "检索", "索引", "codegraph"],
    },
    "活动": {
        "排查修复": ["报错", "失败", "bug", "修复", "异常", "崩溃", "不生效", "error", "fail"],
        "重构优化": ["重构", "优化", "性能", "精简", "压缩", "瘦身", "提速"],
        "调研决策": ["调研", "对比", "选型", "方案", "评估", "权衡", "要不要"],
        "实现开发": ["实现", "开发", "新增", "支持", "功能", "接入", "集成"],
        "审查评审": ["审查", "评审", "review", "检查", "复查", "核对"],
        "同步运维": ["同步", "合并", "升级", "更新", "迁移", "重载", "部署"],
        "设计视觉": ["设计", "原型", "配色", "排版", "视觉", "动效"],
    },
    "摩擦点": ["报错", "失败", "冲突", "超时", "回滚", "重试", "限流", "429", "abort", "revert",
             "错误", "报错信息", "挂了", "崩了", "不行", "不生效", "没反应"],
}


def load_keywords(path):
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    local = os.path.join(HERE, "keywords.json")
    if os.path.exists(local):
        with open(local, encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_KEYWORDS


def cwd_of(session_dir_name):
    s = session_dir_name
    if s.startswith("--"):
        s = s[2:]
    if s.endswith("--"):
        s = s[:-2]
    s = UNESC.sub(lambda m: chr(int(m.group(1), 16)), s)
    return "/" + s.replace("-", "/")


def project_of(cwd):
    parts = [p for p in cwd.split("/") if p]
    if not parts:
        return "?"
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"
    return parts[-1]


INJECTED = ("Current runtime context", "Current working directory",
            "The DSH file sandbox does not restrict", "Approval policy:",
            "Current DeepSeek Harness implementation checkout", "Current DeepSeek Harness Web GUI URL",
            "The approval policy changed", "Background job", "A background job",
            "Background subagent",
            "<system-reminder>", "Instructions from:", "<available_skills>",
            "<skill_content", "The available skill catalog changed",
            "[Compressed conversation section]", "[ACP]", "## 语气", "AGENTS.md")


def looks_injected(t):
    head = t[:300]
    return any(m in t[:1200] or m in head for m in INJECTED) or \
        t.lstrip().startswith("Instructions from") or \
        t.lstrip().startswith("<system")


def texts_of(msg):
    out = []
    for c in msg.get("content") or []:
        if isinstance(c, dict) and c.get("type") == "text":
            out.append(c.get("text") or "")
    return out


def scan_session(path, day):
    """Return a per-session record. Streams with the zstd CLI."""
    rec = {
        "dir": os.path.basename(os.path.dirname(os.path.dirname(path))),
        "day": day,
        "title": None,
        "cwd": None,
        "model": None,
        "user_text": [],
        "tools": collections.Counter(),
        "files": collections.Counter(),
        "skills": collections.Counter(),
        "usage": {"in": 0, "out": 0, "cached": 0},
        "turns": 0,
        "errors": 0,
    }
    try:
        proc = subprocess.Popen(["zstd", "-dc", path], stdout=subprocess.PIPE,
                                text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        sys.stderr.write("zstd CLI not found; install zstd\n")
        sys.exit(2)
    for line in proc.stdout:
        if '"type":"session"' in line and rec["cwd"] is None:
            try:
                rec["cwd"] = json.loads(line).get("cwd")
            except Exception:
                pass
        elif '"user/message"' in line:
            try:
                e = json.loads(line)
            except Exception:
                continue
            rec["user_text"].extend(t for t in texts_of(e.get("data") or {})
                                    if not looks_injected(t))
        elif '"session/title"' in line:
            try:
                rec["title"] = (json.loads(line).get("data") or {}).get("title")
            except Exception:
                pass
        elif '"request/header"' in line:
            if rec["model"] is None:
                try:
                    cfg = ((json.loads(line).get("data") or {}).get("header") or {}).get("config") or {}
                    rec["model"] = f"{cfg.get('provider')}/{cfg.get('model')}"
                except Exception:
                    pass
        elif '"tool/call"' in line:
            try:
                d = json.loads(line).get("data") or {}
            except Exception:
                continue
            name = d.get("name") or "?"
            rec["tools"][name] += 1
            if name == "skill":
                arg = d.get("arguments")
                try:
                    a = json.loads(arg) if isinstance(arg, str) else (arg or {})
                    sk = a.get("name") or a.get("skill")
                    if sk:
                        rec["skills"][sk] += 1
                except Exception:
                    pass
            if name in ("write", "edit", "multi_edit"):
                arg = d.get("arguments")
                try:
                    a = json.loads(arg) if isinstance(arg, str) else (arg or {})
                    p = a.get("file_path") or a.get("path")
                    if p:
                        ext = os.path.splitext(p)[1] or "(none)"
                        rec["files"][ext] += 1
                except Exception:
                    pass
        elif '"inputTokens"' in line:
            try:
                d = json.loads(line).get("data") or {}
            except Exception:
                continue
            for st in d.get("stream") or []:
                ch = (st or {}).get("chunk") or {}
                if ch.get("type") == "usage":
                    u = ch.get("usage") or {}
                    rec["usage"]["in"] += u.get("inputTokens") or 0
                    rec["usage"]["out"] += u.get("outputTokens") or 0
                    rec["usage"]["cached"] += u.get("cacheReadTokens") or 0
                elif ch.get("type") == "finish":
                    if ((ch.get("reason") or {}).get("kind")) == "error":
                        rec["errors"] += 1
        elif '"turn/start"' in line:
            rec["turns"] += 1
    proc.wait()
    return rec


def collect(days=None, since=None, until=None):
    files = []
    for dirpath, _, names in os.walk(SESSIONS):
        if "session.v4.jsonl.zstd" in names:
            p = os.path.join(dirpath, "session.v4.jsonl.zstd")
            try:
                mtime = os.path.getmtime(p)
            except OSError:
                continue
            day = dt.date.fromtimestamp(mtime)
            if since and day < since:
                continue
            if until and day > until:
                continue
            if days is not None:
                cutoff = dt.datetime.now() - dt.timedelta(days=days)
                if dt.datetime.fromtimestamp(mtime) < cutoff:
                    continue
            files.append((mtime, day, p))
    files.sort()
    out = []
    for mtime, day, p in files:
        rec = scan_session(p, day.isoformat())
        rec["cwd"] = rec["cwd"] or cwd_of(rec["dir"])
        rec["project"] = project_of(rec["cwd"])
        rec["minutes"] = len(rec["user_text"])
        rec["mtime"] = mtime
        out.append(rec)
    return out


def mine_terms(session_texts, top=30):
    """Surface repeatedly-mentioned terms across sessions (document frequency).

    Uses per-session presence, not raw occurrence, so one huge pasted prompt
    cannot dominate the ranking.
    """
    cjk_df = collections.Counter()
    cjk_tf = collections.Counter()
    en_df = collections.Counter()
    en_tf = collections.Counter()
    for texts in session_texts:
        blob = "\n".join(texts)
        seen_cjk, seen_en = set(), set()
        for run in CJK_RUN.findall(blob):
            if len(run) < 2:
                continue
            run = run[:120]
            for n in range(2, 7):
                for i in range(len(run) - n + 1):
                    g = run[i:i + n]
                    if g in CJK_STOP:
                        continue
                    cjk_tf[g] += 1
                    seen_cjk.add(g)
        for w in WORD.findall(blob):
            lw = w.lower()
            if lw in EN_STOP or lw.isdigit():
                continue
            en_tf[lw] += 1
            seen_en.add(lw)
        cjk_df.update(seen_cjk)
        en_df.update(seen_en)

    keep = {g: d for g, d in cjk_df.items() if d >= 2 and cjk_tf[g] >= 3}
    dropped = set()
    for g in sorted(keep, key=len, reverse=True):
        if g in dropped:
            continue
        for longer in keep:
            if (len(longer) > len(g) and g in longer and longer not in dropped
                    and keep[longer] >= keep[g] * 0.7):
                dropped.add(g)
                break
    grams = sorted(((g, d, cjk_tf[g]) for g, d in keep.items() if g not in dropped),
                   key=lambda t: (-t[1], -t[2]))[:top]
    ens = [(w, d, en_tf[w]) for w, d in en_df.most_common(400) if d >= 3][:top]
    return grams, ens[:top]


def dim_hits(keywords, texts):
    text = "\n".join(texts).lower()
    hits = {}
    for dim, groups in keywords.items():
        if dim == "摩擦点":
            continue
        hits[dim] = []
        for group, terms in groups.items():
            n = sum(text.count(t.lower()) for t in terms)
            if n:
                hits[dim].append((group, n, [t for t in terms if t.lower() in text][:6]))
        hits[dim].sort(key=lambda x: -x[1])
    return hits


def money(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}k"
    return str(n)


def render(recs, prev, keywords, topic=None):
    L = []
    days = sorted({r["day"] for r in recs})
    L.append(f"# 复盘摘要 {days[0]} ~ {days[-1]}" if days else "# 复盘摘要（空）")
    L.append("")
    tot_calls = sum(sum(r["tools"].values()) for r in recs)
    tot_in = sum(r["usage"]["in"] for r in recs)
    tot_out = sum(r["usage"]["out"] for r in recs)
    tot_cached = sum(r["usage"]["cached"] for r in recs)
    tot_turns = sum(r["turns"] for r in recs)
    L.append("## 概览")
    empty = sum(1 for r in recs if not sum(r["tools"].values()) and not r["user_text"])
    L.append(f"- 会话 {len(recs)}（其中空会话 {empty}）· 轮次 {tot_turns} · 工具调用 {tot_calls}")
    L.append(f"- tokens 未缓存输入 {money(tot_in)} · 缓存读 {money(tot_cached)} · 输出 {money(tot_out)}")
    if tot_in or tot_cached:
        L.append(f"- 缓存命中率 {tot_cached / max(tot_in + tot_cached, 1) * 100:.0f}%")
    if prev:
        pin = sum(r["usage"]["in"] for r in prev)
        pcalls = sum(sum(r["tools"].values()) for r in prev)
        d = lambda a, b: f"{(a-b)/max(b,1)*100:+.0f}%" if b else "n/a"
        L.append(f"- 对比上周期：会话 {len(prev)}→{len(recs)} ({d(len(recs),len(prev))})、"
                 f"调用 {pcalls}→{tot_calls} ({d(tot_calls,pcalls)})、"
                 f"未缓存输入 {money(pin)}→{money(tot_in)} ({d(tot_in,pin)})")
    L.append("")

    L.append("## 项目分布")
    proj = collections.Counter({p: sum(1 for r in recs if r["project"] == p)
                                for p in {r["project"] for r in recs}})
    proj_calls = collections.Counter()
    for r in recs:
        proj_calls[r["project"]] += sum(r["tools"].values())
    for p, c in proj.most_common(12):
        mins = sum(r["minutes"] for r in recs if r["project"] == p)
        L.append(f"- {p}: {c} 会话 / {proj_calls[p]} 调用")
    L.append("")

    L.append("## 工具画像（top 20）")
    tools = collections.Counter()
    for r in recs:
        tools.update(r["tools"])
    for n, c in tools.most_common(20):
        L.append(f"- {n}: {c}")
    L.append("")

    L.append("## 模型分布")
    models = collections.Counter(r["model"] or "?" for r in recs)
    for m, c in models.most_common(8):
        L.append(f"- {m}: {c} 会话")
    L.append("")

    L.append("## Skill 使用")
    sk = collections.Counter()
    for r in recs:
        sk.update(r["skills"])
    if sk:
        L.append("- " + " · ".join(f"{n}({c})" for n, c in sk.most_common(15)))
    else:
        L.append("- （无）")
    L.append("")

    L.append("## 模型错误最多的会话")
    bad = [r for r in recs if r["errors"]]
    bad.sort(key=lambda r: -r["errors"])
    if bad:
        for r in bad[:6]:
            L.append(f"- {r['errors']} 次 · {r['day']} [{r['project']}] {r['title'] or '(无标题)'}")
    else:
        L.append("- 无")
    L.append("")

    L.append("## 产出物（按扩展名）")
    exts = collections.Counter()
    for r in recs:
        exts.update(r["files"])
    if exts:
        L.append("- " + " · ".join(f"{e} {c}" for e, c in exts.most_common(10)))
    else:
        L.append("- （无 write/edit 记录）")
    L.append("")

    all_user = [t for r in recs for t in r["user_text"]]
    titles = [r["title"] for r in recs if r["title"]]
    L.append("## 域分布（预置词典命中，按次数）")
    hits = dim_hits(keywords, all_user)
    for dim, groups in hits.items():
        if not groups:
            continue
        L.append(f"**{dim}**")
        for g, n, terms in groups[:6]:
            L.append(f"- {g}: {n} 次（{', '.join(terms)}）")
    L.append("")

    stuck = keywords.get("摩擦点") or []
    st = collections.Counter()
    low = "\n".join(all_user).lower()
    for t in stuck:
        n = low.count(t.lower())
        if n:
            st[t] = n
    L.append("## 摩擦信号")
    if st:
        L.append("- " + " · ".join(f"{t}×{c}" for t, c in st.most_common(12)))
    else:
        L.append("- 无")
    L.append("")

    grams, ens = mine_terms([r["user_text"] for r in recs if r["user_text"]])
    L.append("## 反复提及的词（出现过该词的会话数 / 出现次数）")
    L.append("- 中文片段：" + " · ".join(f"{g}({d}/{c})" for g, d, c in grams[:24]))
    L.append("- 英文词：" + " · ".join(f"{w}({d}/{c})" for w, d, c in ens[:18]))
    L.append("")

    L.append("## 会话清单")
    for r in sorted(recs, key=lambda x: x["day"]):
        if not sum(r["tools"].values()) and not r["user_text"]:
            continue
        L.append(f"- {r['day']} [{r['project']}] {r['title'] or '(无标题)'} "
                 f"— {sum(r['tools'].values())} 调用"
                 + (f"，{r['errors']} 次模型错误" if r["errors"] else ""))
    L.append("")

    if topic:
        L.append(f"## 话题追踪：{topic}")
        tl = topic.lower()
        for r in recs:
            blob = ((r["title"] or "") + "\n" + "\n".join(r["user_text"])).lower()
            if tl in blob:
                L.append(f"- {r['day']} [{r['project']}] {r['title'] or '(无标题)'} "
                         f"— {r['minutes']} 条用户消息")
        L.append("")

    L.append("## 时间分布（按日）")
    per_day = collections.Counter(r["day"] for r in recs)
    calls_day = collections.Counter()
    for r in recs:
        calls_day[r["day"]] += sum(r["tools"].values())
    for d in days:
        L.append(f"- {d}: {per_day[d]} 会话 / {calls_day[d]} 调用")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--json")
    ap.add_argument("--topic")
    ap.add_argument("--keywords")
    ap.add_argument("--no-compare", action="store_true")
    a = ap.parse_args()

    since = dt.date.fromisoformat(a.since) if a.since else None
    until = dt.date.fromisoformat(a.until) if a.until else None
    keywords = load_keywords(a.keywords)

    if since or until:
        recs = collect(since=since, until=until)
        prev = []
    else:
        recs = collect(days=a.days)
        prev = []
        if not a.no_compare:
            hi = dt.datetime.now() - dt.timedelta(days=a.days)
            lo = hi - dt.timedelta(days=a.days)
            prev = [r for r in collect(days=a.days * 2) if lo <= dt.datetime.fromtimestamp(r["mtime"]) <= hi]

    print(render(recs, prev, keywords, a.topic))

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(recs, f, ensure_ascii=False, indent=1)
        sys.stderr.write(f"json → {a.json}\n")


if __name__ == "__main__":
    main()
