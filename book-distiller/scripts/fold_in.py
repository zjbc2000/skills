#!/usr/bin/env python3
"""Update/Fold-in：把新书（修订版/同作者续作）增量合并进既有 skill 输出。

适配 book-to-skill 的 Mode 4（Update/Fold-in），落到本项目"一书多主题"形态：
本项目没有逐章文件，合并发生在 references/ 精要 + 各主题子 skill 的核心规则上。
本脚本做机械部分——对比新旧章节标题，产出"合并计划"；语义合并（改写 references、
往子 skill 追加规则并标注新来源、更新总入口决策树）由 LLM 按 SKILL.md Mode 4 完成。

用法:
  python3 fold_in.py <既有outputs/book-slug目录> <新书合并md> [--existing-titles <既有章节标题文本>]
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

from probe_book import list_chapters  # noqa: F401  (同 scripts/ 目录复用)


def normalize_title(title: str) -> str:
    """归一化标题用于比对：去空白/章节号差异（第1章 vs 1 章）。"""
    s = title.strip()
    s = s.replace("第", "").replace("章", "").replace("节", "")
    s = s.replace(" ", "").replace("：", ":").replace("—", "-").replace("——", "-")
    return s.lower()


def chapter_number(title: str) -> int | None:
    """提取"第N章"编号；无编号标题返回 None。编号是比对的稳定主键。"""
    m = re.search(r"第\s*(\d+)\s*[章节]", title)
    return int(m.group(1)) if m else None


def split_fold(new_titles: list[str], existing_titles: list[str]) -> dict:
    """比较新旧一级章节标题，返回 {'new': [str], 'revision': [dict], 'duplicate': [dict]}。

    匹配主键 = 章节编号（第N章）；无编号标题用归一化全名。元素统一为 dict（new/existing）：
    - duplicate: 编号/名称都匹配 → 章节保留，内容可能更新
    - revision: 编号匹配但标题改了 → 需复审既有精要是否被改写
    - new: 仅新书有 → 需新增 references 精要 + 可能新主题
    """
    num_existing: dict[int, str] = {
        chapter_number(t): t for t in existing_titles if chapter_number(t) is not None
    }
    norm_existing = {normalize_title(t): t for t in existing_titles}
    duplicate: list[dict] = []
    revision: list[dict] = []
    new: list[str] = []
    for t in new_titles:
        num = chapter_number(t)
        n = normalize_title(t)
        if num is not None and num in num_existing:
            existing = num_existing[num]
            pair = {"new": t, "existing": existing}
            (revision if normalize_title(existing) != n else duplicate).append(pair)
        elif n in norm_existing:
            duplicate.append({"new": t, "existing": norm_existing[n]})
        else:
            new.append(t)
    return {"new": new, "revision": revision, "duplicate": duplicate}


def existing_titles_from_outputs(output_dir: Path) -> list[str]:
    """从既有输出的 references/*.md 的第一个一级 # 标题抽取既有章节名，用于比对。"""
    titles = []
    for f in sorted((output_dir / "references").glob("*.md")):
        for ln in f.read_text(encoding="utf-8").splitlines():
            if ln.startswith("# "):
                titles.append(ln[2:].strip())
                break
    return titles


def build_plan(
    output_dir: Path, new_book_md: Path, existing_titles: list[str] | None = None,
) -> dict:
    """产出合并计划。返回 {'book': str, 'new_chapters': [...], 'revision': [...],
    'duplicate': [...], 'summary': str}。"""
    new_text = new_book_md.read_text(encoding="utf-8")
    new_level1 = [c["title"] for c in list_chapters(new_text) if c["level"] == 1]
    if existing_titles is None:
        existing_titles = existing_titles_from_outputs(output_dir)
    plan = split_fold(new_level1, existing_titles)
    n_new = len(plan["new"])
    n_rev = len(plan["revision"])
    n_dup = len(plan["duplicate"])
    summary = (
        f"新书 {len(new_level1)} 个一级章节：新增 {n_new}，需复审 {n_rev}，与既有重合 {n_dup}。"
    )
    plan.update({"book": new_book_md.name, "summary": summary})
    return plan


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Update/Fold-in 合并计划")
    ap.add_argument("output_dir", help="既有 outputs/<book-slug>/ 目录")
    ap.add_argument("new_book_md", help="新书合并 Markdown")
    ap.add_argument("--existing-titles", default=None,
                    help="既有章节标题文本（每行一个）；默认从 references/*.md 抽取")
    args = ap.parse_args(argv)

    out = Path(args.output_dir)
    if not (out / "references").exists():
        print(f"✗ {out}/references/ 不存在，确认是既有 skill 输出目录", file=sys.stderr)
        return 1
    existing = None
    if args.existing_titles:
        existing = Path(args.existing_titles).read_text(encoding="utf-8").splitlines()
    plan = build_plan(out, Path(args.new_book_md), existing)
    print(f"📚 合并计划: {plan['book']}")
    print(f"   {plan['summary']}")
    if plan["new"]:
        print("   新增章节（→ 新增 references 精要，可能开新主题）：")
        for t in plan["new"]:
            print(f"     + {t}")
    if plan["revision"]:
        print("   需复审章节（标题有差异，检查既有精要是否被新内容改写）：")
        for r in plan["revision"]:
            print(f"     ~ {r['existing']}  ↔  {r['new']}")
    if plan["duplicate"]:
        print(f"   重合章节（{len(plan['duplicate'])} 个，内容可能更新）：")
        for d in plan["duplicate"]:
            print(f"     = {d['existing']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
