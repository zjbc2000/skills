#!/usr/bin/env python3
"""REPL 式按需读整本书：避免把 >50k token 的全文一次性读进上下文。

适配 book-to-skill 的 Step 2.6（RLM 范式）：把大书当可查询语料，用 grep/sed
切片只读需要的部分，生成成本与输出成正比而非与源书成正比。

用法:
  python3 probe_book.py size <book.md>                # 字符/token/行数
  python3 probe_book.py chapters <book.md>            # 列出章节标题+起始行号
  python3 probe_book.py slice <book.md> --start L --end L   # 按行切片
  python3 probe_book.py slice <book.md> --chapter N   # 按章节号切片
  python3 probe_book.py grep <book.md> <pattern>      # 找关键词所在行
"""
from __future__ import annotations
import re
import sys
import unicodedata
from pathlib import Path

HEADING = re.compile(r"^(#{1,3})\s+(\S.+)$")


def count_tokens(text: str) -> int:
    """与 estimate_cost.py 一致的 CJK 加权 token 估算。"""
    total = 0
    for ch in text:
        total += 1.0 if unicodedata.category(ch).startswith("Lo") else 0.25
    return int(total)


def list_chapters(text: str) -> list[dict]:
    """返回 [{'level': 1, 'title': '第1章', 'line': 12}, ...]（按出现顺序）。"""
    out = []
    for idx, ln in enumerate(text.splitlines(), start=1):
        m = HEADING.match(ln)
        if m:
            out.append({"level": len(m.group(1)), "title": m.group(2).strip(), "line": idx})
    return out


def slice_lines(text: str, start: int, end: int) -> str:
    lines = text.splitlines()
    return "\n".join(lines[start - 1:end])


def slice_chapter(text: str, chapters: list[dict], chapter_no: int) -> str:
    """按一级章节序号切片（1 起）。只认 level==1 的标题为"章"，子标题不单独成章。"""
    top = [c for c in chapters if c["level"] == 1]
    if chapter_no < 1 or chapter_no > len(top):
        raise IndexError(f"章节号 {chapter_no} 超出范围（共 {len(top)} 章）")
    start = top[chapter_no - 1]["line"]
    end = top[chapter_no]["line"] - 1 if chapter_no < len(top) else None
    lines = text.splitlines()
    return "\n".join(lines[start - 1:end])


def grep_lines(text: str, pattern: str, max_hits: int = 40) -> list[dict]:
    """返回 [{'line': 12, 'text': '...'}, ...]，命中超过 max_hits 截断。"""
    hits = []
    rx = re.compile(pattern)
    for idx, ln in enumerate(text.splitlines(), start=1):
        if rx.search(ln):
            hits.append({"line": idx, "text": ln[:160]})
            if len(hits) >= max_hits:
                break
    return hits


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="REPL 式按需读整本书")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_size = sub.add_parser("size", help="字符/token/行数")
    p_size.add_argument("md")

    p_ch = sub.add_parser("chapters", help="列出章节")
    p_ch.add_argument("md")

    p_sl = sub.add_parser("slice", help="按行/章节切片")
    p_sl.add_argument("md")
    p_sl.add_argument("--start", type=int)
    p_sl.add_argument("--end", type=int)
    p_sl.add_argument("--chapter", type=int)

    p_gr = sub.add_parser("grep", help="找关键词")
    p_gr.add_argument("md")
    p_gr.add_argument("pattern")

    args = ap.parse_args(argv)
    text = Path(args.md).read_text(encoding="utf-8")

    if args.cmd == "size":
        lines = len(text.splitlines())
        print(f"字符: {len(text):,} | token(估): {count_tokens(text):,} | 行: {lines:,}")
    elif args.cmd == "chapters":
        for c in list_chapters(text):
            print(f"L{c['line']:>6}  {'#'*c['level']} {c['title']}")
    elif args.cmd == "slice":
        if args.chapter:
            chs = list_chapters(text)
            try:
                print(slice_chapter(text, chs, args.chapter))
            except IndexError as e:
                print(str(e), file=sys.stderr)
                return 1
        elif args.start:
            print(slice_lines(text, args.start, args.end or args.start))
        else:
            print("slice 需要 --chapter N 或 --start L [--end L]", file=sys.stderr)
            return 1
    elif args.cmd == "grep":
        for h in grep_lines(text, args.pattern):
            print(f"L{h['line']:>6}  {h['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
