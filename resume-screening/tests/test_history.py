"""筛选历史（v0.21）：sqlite 会话存储 + API。"""
from __future__ import annotations

import json

import pytest

from backend.persistence.history import add_session, get_session, list_sessions


@pytest.fixture
def db(tmp_path):
    return tmp_path / "history.db"


def _snap():
    return {
        "mode": "general",
        "general": {"projects": [{"name": "P", "bonus": 3, "evidence": "e", "quotation": "q"}],
                    "tech_stack": [], "highlights": [], "red_lines": []},
        "specific": {"position_match": {"bonus": 2, "evidence": "e", "quotation": "q"},
                     "skills": [{"skill": "react", "hit": True, "bonus": 2, "evidence": "e", "quotation": "q"}]},
        "totals": {"G": 3, "S": 4, "T": 7},
    }


def test_add_and_list_sessions(db):
    sid = add_session(db, "西安AE", "general", [
        {"name": "a.pdf", "verdict": "pass", "totals": {"G": 3, "S": 4, "T": 7}, "snapshot": _snap()},
        {"name": "b.pdf", "error": "解析失败"},
    ])
    assert sid == 1
    sessions = list_sessions(db)
    assert len(sessions) == 1
    assert sessions[0]["jd"] == "西安AE"
    assert sessions[0]["n_ok"] == 1 and sessions[0]["n_fail"] == 1


def test_get_session_returns_records_and_snapshot(db):
    sid = add_session(db, "西安AE", "general", [
        {"name": "a.pdf", "verdict": "pass", "totals": {"G": 3, "S": 4, "T": 7}, "snapshot": _snap()},
        {"name": "b.pdf", "error": "解析失败"},
    ])
    detail = get_session(db, sid)
    assert detail["mode"] == "general"
    assert len(detail["records"]) == 2
    r0 = detail["records"][0]
    assert r0["name"] == "a.pdf" and r0["verdict"] == "pass"
    assert r0["snapshot"]["totals"]["T"] == 7
    assert detail["records"][1]["error"] == "解析失败"


def test_get_missing_session_returns_none(db):
    assert get_session(db, 999) is None
    assert list_sessions(db / "nope.db") == []