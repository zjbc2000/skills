"""测试共享 fixture：JSON validator 与可控 call_fn。"""
from __future__ import annotations

import json

import pytest

from backend.registry.llm_client import SchemaError


@pytest.fixture
def json_validator():
    """把原始响应 JSON 解析为 dict；非法 JSON 抛 SchemaError。"""

    def validate(raw: str) -> dict:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise SchemaError(f"invalid json: {e}") from e

    return validate
