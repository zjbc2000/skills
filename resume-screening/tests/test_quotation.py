"""quotation 校验（T06）：后置确定性 grep，exact/fuzzy/missing。"""
from __future__ import annotations

from backend.verify.quotation import (
    EXACT,
    FUZZY,
    MISSING,
    verify_quotation,
    verify_snapshot,
)

TEXT = (
    "Zhang San - Senior Engineer\n"
    "3 years of experience with react and python.\n"
    "Led an OCR pipeline team at company X."
)


def test_exact_substring():
    assert verify_quotation("Led an OCR pipeline team", TEXT) == EXACT


def test_exact_ignores_whitespace():
    assert verify_quotation("react   and\npython", TEXT) == EXACT


def test_fuzzy_similar():
    assert verify_quotation("3 years react & python", TEXT) == FUZZY


def test_missing_no_overlap():
    assert verify_quotation("完全不存在的引用xyzzy", TEXT) == MISSING


def test_snapshot_annotates_all_quoted_items():
    snap = {
        "general": {
            "projects": [{"bonus": 2, "quotation": "Led an OCR pipeline team"}],
            "tech_stack": [{"bonus": 3, "quotation": "react and python"}],
            "highlights": [{"bonus": 1, "quotation": "不存在的引用xyzzy"}],
            "red_lines": [],
        },
        "specific": {
            "position_match": {"bonus": 2, "quotation": "Senior Engineer"},
            "skills": [{"skill": "react", "hit": True, "bonus": 3, "quotation": "react"}],
        },
        "totals": {"G": 8, "S": 5, "T": 13},
        "thresholds": {"general": 8, "specific": 8, "total": 16},
        "verdict": "fail",
    }
    out = verify_snapshot(snap, TEXT)
    assert out["general"]["projects"][0]["verify"] == EXACT
    assert out["general"]["tech_stack"][0]["verify"] == EXACT
    assert out["general"]["highlights"][0]["verify"] == MISSING
    assert out["general"]["highlights"][0]["suspect"] is True  # missing → suspect
    assert out["specific"]["position_match"]["verify"] == EXACT
    assert out["specific"]["skills"][0]["verify"] == EXACT
    assert out["verdict"] == snap["verdict"]  # 顶层字段保留


def test_snapshot_does_not_mutate_original():
    snap = {
        "general": {"projects": [{"bonus": 2, "quotation": "Led an OCR pipeline team"}],
                    "tech_stack": [], "highlights": [], "red_lines": []},
        "specific": {"position_match": {"bonus": 1, "quotation": "react"},
                     "skills": [{"skill": "react", "hit": True, "bonus": 1, "quotation": "react"}]},
        "totals": {"G": 2, "S": 2, "T": 4},
        "thresholds": {"general": 8, "specific": 8, "total": 16},
        "verdict": "fail",
    }
    verify_snapshot(snap, TEXT)
    assert "verify" not in snap["general"]["projects"][0]
    assert "verify" not in snap["specific"]["position_match"]


def test_red_lines_also_verified():
    snap = {
        "general": {"projects": [], "tech_stack": [], "highlights": [],
                    "red_lines": [{"rule": "r", "hit": True, "quotation": "Led an OCR pipeline team"}]},
        "specific": {"position_match": {"bonus": 0, "quotation": "react"},
                     "skills": [{"skill": "react", "hit": True, "bonus": 1, "quotation": "react"}]},
        "totals": {"G": 0, "S": 1, "T": 1},
        "thresholds": {"general": 8, "specific": 8, "total": 16},
        "verdict": "fail",
    }
    out = verify_snapshot(snap, TEXT)
    assert out["general"]["red_lines"][0]["verify"] == EXACT
