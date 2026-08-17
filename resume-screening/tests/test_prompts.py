"""系统提示词（T03）。"""
from __future__ import annotations

from backend.scoring.prompts import SYSTEM_PROMPT, build_prompt


def test_build_prompt_contains_resume_and_jd():
    p = build_prompt("简历内容", "岗位要求内容")
    assert "简历内容" in p
    assert "岗位要求内容" in p


def test_system_prompt_mentions_quotation_and_scale():
    assert "quotation" in SYSTEM_PROMPT
    assert "0..3" in SYSTEM_PROMPT
    assert "red_lines" in SYSTEM_PROMPT
