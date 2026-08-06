# book-distiller/tests/test_estimate_cost.py
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from estimate_cost import count_tokens, count_chapters, estimate_book_cost, BUDGET


def test_count_tokens_cjk_heavy():
    # 纯中文：每字 ≈ 1 token
    assert count_tokens("中文" * 100) >= 180
    # 英文：每字符 ≈ 0.25 token
    assert count_tokens("abc") <= 2


def test_count_chapters_from_headings():
    text = "\n".join([f"# 第{i}章" for i in range(1, 8)])
    assert count_chapters(text) == 7


def test_count_chapters_fallback():
    # 无一级标题 → 按 3KB 估
    text = "普通文本。\n" * 500  # ~2500 字符 < 3KB，估 1 章
    assert count_chapters(text) >= 1


def test_estimate_output_scales_with_budget():
    # technical 深读章节预算 > text 深读
    base = "# 章\n" * 5
    t = estimate_book_cost(base, book_type="technical", depth="study", chapters=5)
    x = estimate_book_cost(base, book_type="text", depth="study", chapters=5)
    assert t["output_tokens"] > x["output_tokens"]


def test_estimate_reference_cheaper_than_study():
    base = "# 章\n" * 5
    ref = estimate_book_cost(base, book_type="technical", depth="reference", chapters=5)
    study = estimate_book_cost(base, book_type="technical", depth="study", chapters=5)
    assert ref["output_tokens"] < study["output_tokens"]


def test_estimate_fixed_overhead_always_included():
    base = "# 章\n"
    r = estimate_book_cost(base, chapters=1)
    assert r["output_tokens"] > sum(BUDGET["text"])  # 固定产出恒大于单章预算


def test_estimate_chapters_override():
    base = "# 章\n"
    r = estimate_book_cost(base, chapters=39)
    assert r["chapters"] == 39
    assert r["output_tokens"] > estimate_book_cost(base, chapters=5)["output_tokens"]
