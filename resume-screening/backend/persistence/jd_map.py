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


def save_jd(path: Union[Path, str], key: str, jd: dict) -> None:
    """新增一个岗位到 jd_map.yml（key 已存在抛 ValueError）。"""
    roles = load_jd_map(path)
    if key in roles:
        raise ValueError(f"岗位已存在: {key}")
    roles[key] = jd
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"roles": roles}, f, allow_unicode=True, sort_keys=False)


def jd_text(jd: dict) -> str:
    """把一条 JD 渲染成给 LLM 的文本（岗位 + 技能要求 + 红线）。

    技能要求逐行渲染以保留章节结构；非字符串条目跳过（防脏数据崩溃）。
    """
    parts = []
    if jd.get("position"):
        parts.append(f"岗位：{jd['position']}")
    skills = [s for s in jd.get("skills", []) if isinstance(s, str)]
    if skills:
        parts.append("技能要求：\n" + "\n".join(skills))
    reds = [r for r in jd.get("red_lines", []) if isinstance(r, str)]
    if reds:
        parts.append("红线：" + ", ".join(reds))
    return "\n".join(parts)
