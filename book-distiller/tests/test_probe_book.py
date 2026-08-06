# book-distiller/tests/test_probe_book.py
from __future__ import annotations
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from probe_book import list_chapters, slice_lines, slice_chapter, grep_lines, count_tokens


SAMPLE = "\n".join(
    [
        "# 第1章 心态",
        "正文一。",
        "## 1.1 概述",
        "正文二。",
        "# 第2章 前端",
        "正文三。",
        "# 第3章 后端",
        "正文四。",
    ]
)


def test_list_chapters_detects_levels():
    chs = list_chapters(SAMPLE)
    assert [c["title"] for c in chs] == ["第1章 心态", "1.1 概述", "第2章 前端", "第3章 后端"]
    assert chs[0]["level"] == 1 and chs[0]["line"] == 1


def test_slice_lines_range():
    out = slice_lines(SAMPLE, 2, 4)
    assert "正文一。" in out and "正文二。" in out
    assert "# 第1章" not in out


def test_slice_chapter_bounds():
    chs = list_chapters(SAMPLE)
    out = slice_chapter(SAMPLE, chs, 2)  # 第2章到第3章之前
    assert "第2章 前端" in out and "正文三。" in out
    assert "第3章 后端" not in out


def test_slice_chapter_last():
    chs = list_chapters(SAMPLE)
    out = slice_chapter(SAMPLE, chs, 3)
    assert "第3章 后端" in out and "正文四。" in out


def test_slice_chapter_out_of_range():
    chs = list_chapters(SAMPLE)
    with pytest.raises(IndexError):
        slice_chapter(SAMPLE, chs, 99)


def test_grep_finds_hits():
    hits = grep_lines(SAMPLE, "正文")
    assert len(hits) == 4
    assert hits[0]["line"] == 2


def test_grep_respects_max_hits():
    text = "x\n" * 100
    assert len(grep_lines(text, "x", max_hits=10)) == 10


def test_count_tokens_consistent():
    assert count_tokens("中文" * 10) == 20
    assert count_tokens("abcd") == 1  # 4 × 0.25
