#!/usr/bin/env python3
"""生成前预估 Token 成本：读合并 Markdown，估算输入/输出 token 与费用。

适配 book-to-skill 的 Step 2.5：在生成子 skill 前先给用户报价，避免大书跑完
才发现成本。价格默认按示例（Claude Sonnet $3/$15 per MTok）标注"估算"，可用
--rate-in/--rate-out 覆盖，模型价格变化快，脚本不硬编码真实价格。

用法:
  python3 estimate_cost.py <book.md> [--book-type technical|text] [--depth study|reference]
"""
from __future__ import annotations
import re
import sys
import unicodedata
from pathlib import Path

HEADING = re.compile(r"^#{1,3}\s+(.+)$")

# 章节预算矩阵（与 references/book-types.md 一致）：[浅读下限, 浅读上限, 深读下限, 深读上限]
BUDGET = {
    "text":      (600, 900, 800, 1200),
    "technical": (900, 1400, 1400, 2200),
}
FIXED_OUTPUT = {  # SKILL.md + references + 汇总报告
    "SKILL.md": 4000,
    "references": 4500,
    "overhead": 1000,
}


def count_tokens(text: str) -> int:
    """CJK 加权 token 估算：中文/日文/韩文字符 ≈ 1 token，其他 ≈ 0.25 token。"""
    total = 0
    for ch in text:
        total += 1.0 if unicodedata.category(ch).startswith("Lo") else 0.25
    return int(total)


def count_chapters(text: str) -> int:
    """统计一级标题数量作为章节数；无标题时按每 3KB 一段估。"""
    level1 = [l for l in text.splitlines() if re.match(r"^#\s+\S", l)]
    if level1:
        return max(len(level1), 1)
    return max(len(text) // 3000, 1)


def estimate_book_cost(
    text: str,
    book_type: str = "text",
    depth: str = "study",
    rate_in: float = 3.0,
    rate_out: float = 15.0,
    chapters: int | None = None,
) -> dict:
    """估算输入/输出 token 与费用，返回可展示的 dict。

    - 输入 token = 全书 token × 1.3（逐章摘要的 prompt 开销）
    - 输出 token = 章节数 × 每章预算中值 + 固定产出（SKILL.md + references + 报告）
    """
    bt = book_type if book_type in BUDGET else "text"
    depth_idx = 1 if depth == "reference" else 3  # 取每档上限作为预算
    per_chapter = BUDGET[bt][depth_idx - 1] if depth_idx == 1 else BUDGET[bt][depth_idx]
    n = chapters or count_chapters(text)

    input_tokens = int(count_tokens(text) * 1.3)
    output_tokens = n * per_chapter + sum(FIXED_OUTPUT.values())
    cost_in = input_tokens / 1e6 * rate_in
    cost_out = output_tokens / 1e6 * rate_out
    cost_total = cost_in + cost_out
    minutes = max(int((input_tokens + output_tokens) / 2500), 1)  # 粗糙吞吐估

    return {
        "book_type": bt,
        "depth": depth,
        "chapters": n,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_in_usd": round(cost_in, 2),
        "cost_out_usd": round(cost_out, 2),
        "cost_total_usd": round(cost_total, 2),
        "estimate_minutes": minutes,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="生成前 Token 成本预估")
    ap.add_argument("md", help="合并 Markdown 路径")
    ap.add_argument("--book-type", choices=["technical", "text", "mixed"], default="text")
    ap.add_argument("--depth", choices=["study", "reference"], default="study")
    ap.add_argument("--rate-in", type=float, default=3.0, help="每百万输入 token 价格（USD，估算示例）")
    ap.add_argument("--rate-out", type=float, default=15.0, help="每百万输出 token 价格（USD，估算示例）")
    ap.add_argument("--chapters", type=int, default=None, help="覆盖章节数（默认从一级标题统计）")
    args = ap.parse_args(argv)

    text = Path(args.md).read_text(encoding="utf-8")
    bt = "text" if args.book_type == "mixed" else args.book_type
    r = estimate_book_cost(
        text, book_type=bt, depth=args.depth,
        rate_in=args.rate_in, rate_out=args.rate_out, chapters=args.chapters,
    )
    print(f"📖 来源: {args.md}")
    print(f"   书型: {r['book_type']} | 深度: {r['depth']} | 章节: ~{r['chapters']}")
    print(f"📄 输入(读+提示): ~{r['input_tokens']:,} token")
    print(f"   输出(生成skill): ~{r['output_tokens']:,} token")
    print(f"💰 预估费用(按 ${args.rate_in:g}/${args.rate_out:g} per MTok, 估算):")
    print(f"   输入 ${r['cost_in_usd']:.2f} + 输出 ${r['cost_out_usd']:.2f} = ${r['cost_total_usd']:.2f}")
    print(f"⏱ 预估时间: ~{r['estimate_minutes']} 分钟")
    return 0


if __name__ == "__main__":
    sys.exit(main())
