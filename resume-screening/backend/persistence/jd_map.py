"""jd_map.yml 维度表（岗位 → JD，SPEC §2.3）。"""
from __future__ import annotations

from pathlib import Path
from typing import Union

import yaml


def load_jd_map(path: Union[Path, str]) -> dict:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    roles = data.get("roles", {})
    return roles if isinstance(roles, dict) else {}


def jd_text(jd: dict) -> str:
    """把一条 JD 渲染成给 LLM 的文本（岗位 + 技能要求 + 红线）。"""
    parts = []
    if jd.get("position"):
        parts.append(f"岗位：{jd['position']}")
    skills = jd.get("skills", [])
    if skills:
        parts.append("技能要求：" + ", ".join(skills))
    reds = jd.get("red_lines", [])
    if reds:
        parts.append("红线：" + ", ".join(reds))
    return "\n".join(parts)
