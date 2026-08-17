"""能力列表文档自动生成（T02）。"""
from __future__ import annotations

from backend.config import load_config
from backend.registry.capabilities import render_capabilities


def test_render_contains_registry_content():
    cfg = load_config()
    md = render_capabilities(cfg)
    assert "ark_coding" in md
    assert "deepseek-v4-flash" in md
    assert "layout_parsing" in md
    assert "Agent 维护规则" in md
    assert "阈值" not in md  # §7 定义能力列表仅含模型/工具
