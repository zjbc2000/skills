#!/usr/bin/env python3
"""检测书稿书型：technical（代码/表格/公式多）vs text（纯文字）。

书型决定抽取引擎与章节摘要预算（见 references/book-types.md）：
- technical → 用 Docling 保留表格/代码块，章节预算取高值
- text → 用最快提取器（pdftotext/PyMuPDF），章节预算取低值

用法: python3 detect_book_type.py <book.md>
输出: technical | text | mixed（对应 --book-type 选项）
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

FENCE = re.compile(r"^```", re.MULTILINE)
TABLE_ROW = re.compile(r"^\|.+\|$")
MATH = re.compile(r"\$\$|\\\(|\\\)|\\\[|\\\]")


def detect_book_type(text: str) -> dict:
    """统计代码/表格/公式占比，返回判定与依据。

    规则：代码行占比 ≥5% 或表格行 ≥20 或公式块 ≥10 → technical；
    三者都接近 0 → text；其余 → mixed。
    """
    lines = text.splitlines()
    in_code = False
    code_lines = 0
    for ln in lines:
        if FENCE.match(ln):
            in_code = not in_code
        elif in_code:
            code_lines += 1
    table_rows = sum(1 for ln in lines if TABLE_ROW.match(ln) and "---" not in ln[:8])
    math_blocks = len(MATH.findall(text))
    total = max(len(lines), 1)
    code_ratio = code_lines / total

    if code_ratio >= 0.05 or table_rows >= 20 or math_blocks >= 10:
        book_type = "technical"
    elif code_ratio <= 0.01 and table_rows == 0 and math_blocks == 0:
        book_type = "text"
    else:
        book_type = "mixed"

    return {
        "book_type": book_type,
        "code_lines": code_lines,
        "table_rows": table_rows,
        "math_blocks": math_blocks,
        "code_ratio": round(code_ratio, 3),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="检测书稿书型（technical/text/mixed）")
    ap.add_argument("md", help="输入 Markdown 路径")
    args = ap.parse_args(argv)
    text = Path(args.md).read_text(encoding="utf-8")
    print(detect_book_type(text)["book_type"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
