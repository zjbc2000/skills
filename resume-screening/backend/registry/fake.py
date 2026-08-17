"""开发/测试用假 LLM：返回带真实引用的固定评分 JSON。

供 CLI `--llm fake` 与测试使用；无网络依赖，便于本地跑通整条链路。
"""
from __future__ import annotations

import json
from typing import Callable, Optional


def fake_call_fn() -> Callable:
    def call(
        provider: str, model: str, prompt: str, feedback: Optional[str] = None
    ) -> str:
        resume = _section(prompt, "[简历]", "[岗位要求]")
        lines = [line.strip() for line in resume.splitlines() if line.strip()]
        quotation = lines[0] if lines else "（原文为空）"
        payload = {
            "general": {
                "projects": [{"name": "P", "bonus": 2, "evidence": "fake", "quotation": quotation}],
                "tech_stack": [{"tech": "react", "bonus": 1, "evidence": "fake", "quotation": quotation}],
                "highlights": [],
                "red_lines": [],
            },
            "specific": {
                "position_match": {"bonus": 1, "evidence": "fake", "quotation": quotation},
                "skills": [{"skill": "react", "hit": True, "bonus": 2, "evidence": "fake", "quotation": quotation}],
            },
        }
        return json.dumps(payload, ensure_ascii=False)

    return call


def _section(text: str, start: str, end: str) -> str:
    i = text.find(start)
    if i == -1:
        return ""
    j = text.find(end, i + 1)
    segment = text[i + len(start):] if j == -1 else text[i + len(start):j]
    return segment
