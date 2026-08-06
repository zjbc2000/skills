# book-distiller/tests/test_fold_in.py
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from fold_in import split_fold, normalize_title, existing_titles_from_outputs, build_plan


def test_normalize_title_strips_chapter_prefix():
    assert normalize_title("第1章 心态与理念") == "1心态与理念"


def test_split_fold_categorizes():
    old = ["第1章 心态", "第2章 前端", "第3章 后端"]
    new = ["第1章 心态", "第2章 前端", "第4章 基础设施"]
    r = split_fold(new, old)
    assert r["new"] == ["第4章 基础设施"]
    assert [d["existing"] for d in r["duplicate"]] == ["第1章 心态", "第2章 前端"]


def test_split_fold_detects_revision_on_renamed():
    old = ["第1章 心态与理念"]
    new = ["第1章 心态新理念"]
    r = split_fold(new, old)
    assert len(r["revision"]) == 1
    assert r["revision"][0]["new"] == "第1章 心态新理念"


def test_split_fold_ignores_whitespace_diff():
    old = ["第2章 前端设计与AI实现"]
    new = ["第2章 前端设计与 AI 实现"]
    r = split_fold(new, old)
    assert r["duplicate"] and not r["new"] and not r["revision"]


def test_existing_titles_from_outputs(tmp_path):
    refs = tmp_path / "references"
    refs.mkdir()
    (refs / "ch1.md").write_text("# 第1章 心态\n正文\n", encoding="utf-8")
    (refs / "ch2.md").write_text("# 第2章 前端\n正文\n", encoding="utf-8")
    titles = existing_titles_from_outputs(tmp_path)
    assert "第1章 心态" in titles and "第2章 前端" in titles


def test_build_plan_summary_counts(tmp_path):
    out = tmp_path / "skill"
    (out / "references").mkdir(parents=True)
    (out / "references" / "ch1.md").write_text("# 第1章 心态\n", encoding="utf-8")
    new = tmp_path / "new.md"
    new.write_text("# 第1章 心态\n# 第2章 前端\n", encoding="utf-8")
    plan = build_plan(out, new)
    assert "新增 1" in plan["summary"]
    assert plan["new"] == ["第2章 前端"]
