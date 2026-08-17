"""评分引擎与判定（T03）：两模式 / 通用双条件 / 红线否决 / schema 校验。"""
from __future__ import annotations

import json
from copy import deepcopy

import pytest

from backend.scoring.engine import (
    MODE_GENERAL,
    MODE_SPECIFIC,
    assess,
)
from backend.scoring.schema import SchemaError, validate_llm_output

THRESH = {"general": 3, "specific": 3, "total": 6}

VALID = {
    "general": {
        "projects": [{"name": "P", "bonus": 2, "quotation": "做过项目", "evidence": ""}],
        "tech_stack": [{"tech": "react", "bonus": 1, "quotation": "熟悉react", "evidence": ""}],
        "highlights": [],
        "red_lines": [],
    },
    "specific": {
        "position_match": {"bonus": 1, "quotation": "匹配岗位", "evidence": ""},
        "skills": [{"skill": "react", "hit": True, "bonus": 2, "quotation": "用过react", "evidence": ""}],
    },
}


# --- schema 校验 ---


def test_validate_accepts_valid():
    assert validate_llm_output(json.dumps(VALID)) == VALID


def test_validate_rejects_bad_bonus():
    bad = deepcopy(VALID)
    bad["general"]["projects"][0]["bonus"] = 4
    with pytest.raises(SchemaError):
        validate_llm_output(json.dumps(bad))


def test_validate_rejects_negative_bonus():
    bad = deepcopy(VALID)
    bad["general"]["projects"][0]["bonus"] = -1
    with pytest.raises(SchemaError):
        validate_llm_output(json.dumps(bad))


def test_validate_rejects_missing_quotation():
    bad = deepcopy(VALID)
    bad["general"]["projects"][0].pop("quotation")
    with pytest.raises(SchemaError):
        validate_llm_output(json.dumps(bad))


def test_validate_rejects_empty_quotation():
    bad = deepcopy(VALID)
    bad["specific"]["skills"][0]["quotation"] = ""
    with pytest.raises(SchemaError):
        validate_llm_output(json.dumps(bad))


def test_validate_rejects_invalid_json():
    with pytest.raises(SchemaError):
        validate_llm_output("not json at all")


def test_validate_rejects_missing_specific_skills():
    bad = deepcopy(VALID)
    bad["specific"].pop("skills")
    with pytest.raises(SchemaError):
        validate_llm_output(json.dumps(bad))


def test_validate_rejects_non_object_general():
    with pytest.raises(SchemaError):
        validate_llm_output(json.dumps({"general": [], "specific": VALID["specific"]}))


def test_validate_rejects_red_line_missing_hit():
    bad = deepcopy(VALID)
    bad["general"]["red_lines"] = [{"rule": "r", "quotation": "q"}]
    with pytest.raises(SchemaError):
        validate_llm_output(json.dumps(bad))


def test_validate_rejects_skill_missing_hit():
    bad = deepcopy(VALID)
    bad["specific"]["skills"][0].pop("hit")
    with pytest.raises(SchemaError):
        validate_llm_output(json.dumps(bad))


# --- 计分与判定 ---


def test_general_score_sums():
    v = assess(VALID, MODE_GENERAL, THRESH)
    assert v.g == 3  # projects 2 + tech_stack 1
    assert v.s == 3  # 引擎始终计算 G 与 S；general 模式用 G 与 T 判定
    assert v.passed


def test_specific_score_sums():
    v = assess(VALID, MODE_SPECIFIC, THRESH)
    assert v.s == 3  # position_match 1 + skills 2
    assert v.passed


def test_specific_ignores_non_hit_skills():
    bad = deepcopy(VALID)
    bad["specific"]["skills"][0]["hit"] = False
    v = assess(bad, MODE_SPECIFIC, THRESH)
    assert v.s == 1  # 仅 position_match；未命中技能不计入（SPEC §1 命中之和）


def test_general_fails_when_total_short():
    v = assess(VALID, MODE_GENERAL, {"general": 3, "specific": 3, "total": 99})
    assert v.g >= 3
    assert v.t < 99
    assert not v.passed


def test_general_fails_when_g_short():
    v = assess(VALID, MODE_GENERAL, {"general": 99, "specific": 3, "total": 6})
    assert v.t >= 6
    assert v.g < 99
    assert not v.passed


def test_general_passes_when_both_clear():
    v = assess(VALID, MODE_GENERAL, THRESH)
    assert v.g >= 3 and v.t >= 6
    assert v.passed


def test_red_line_vetoes_all_modes():
    bad = deepcopy(VALID)
    bad["general"]["red_lines"] = [{"rule": "失信记录", "hit": True, "quotation": "有失信", "evidence": ""}]
    for mode in (MODE_GENERAL, MODE_SPECIFIC):
        v = assess(bad, mode, THRESH)
        assert not v.passed
        assert v.red_lines_hit == ["失信记录"]


def test_snapshot_contains_totals_thresholds_verdict():
    v = assess(VALID, MODE_GENERAL, THRESH)
    snap = v.snapshot
    assert snap["totals"] == {"G": 3, "S": 3, "T": 6}
    assert snap["thresholds"] == THRESH
    assert snap["verdict"] == "pass"
    assert snap["mode"] == MODE_GENERAL
