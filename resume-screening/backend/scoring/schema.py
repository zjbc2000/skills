"""LLM 输出 schema 校验（SPEC §4）。

作为统一 LLM 客户端的 validator 注入：解析 JSON 并校验结构，
非法即抛 SchemaError（触发纠正性重试）。
"""
from __future__ import annotations

import json
from typing import Any

from ..registry.llm_client import SchemaError

MIN_BONUS, MAX_BONUS = 0, 3


def validate_jd_output(raw: str) -> dict:
    """解析并校验 JD 抽取响应：{position, skills[], red_lines[]}。"""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SchemaError(f"响应不是合法 JSON: {e}") from e
    if not isinstance(data, dict):
        raise SchemaError("响应应为 JSON 对象")
    if not isinstance(data.get("position"), str) or not data["position"].strip():
        raise SchemaError("position 必填且非空")
    for key in ("skills", "red_lines"):
        items = data.get(key)
        if not isinstance(items, list):
            raise SchemaError(f"{key}: 应为列表")
        for i, item in enumerate(items):
            if not isinstance(item, str) or not item.strip():
                raise SchemaError(f"{key}[{i}]: 应为非空字符串")
    return data


def validate_llm_output(raw: str) -> dict:
    """解析并校验 LLM 原始响应，返回规范化 dict。"""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SchemaError(f"响应不是合法 JSON: {e}") from e
    if not isinstance(data, dict):
        raise SchemaError("响应应为 JSON 对象")
    _check_general(data.get("general"))
    _check_specific(data.get("specific"))
    return data


def _check_scored_item(item: Any, where: str) -> None:
    if not isinstance(item, dict):
        raise SchemaError(f"{where}: 条目应为对象")
    bonus = item.get("bonus")
    if not isinstance(bonus, int) or not (MIN_BONUS <= bonus <= MAX_BONUS):
        raise SchemaError(f"{where}: bonus 应为 {MIN_BONUS}..{MAX_BONUS} 的整数，实得 {bonus!r}")
    quotation = item.get("quotation")
    if not isinstance(quotation, str) or not quotation.strip():
        raise SchemaError(f"{where}: quotation 必填且非空")


def _check_items(items: Any, where: str) -> None:
    if not isinstance(items, list):
        raise SchemaError(f"{where}: 应为列表")
    for i, item in enumerate(items):
        _check_scored_item(item, f"{where}[{i}]")


def _check_red_lines(items: Any) -> None:
    if not isinstance(items, list):
        raise SchemaError("general.red_lines: 应为列表")
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise SchemaError(f"general.red_lines[{i}]: 条目应为对象")
        if not isinstance(item.get("hit"), bool):
            raise SchemaError(f"general.red_lines[{i}]: hit 应为布尔")
        quotation = item.get("quotation")
        if not isinstance(quotation, str) or not quotation.strip():
            raise SchemaError(f"general.red_lines[{i}]: quotation 必填且非空")


def _check_general(g: Any) -> None:
    if not isinstance(g, dict):
        raise SchemaError("general: 应为对象")
    _check_items(g.get("projects"), "general.projects")
    _check_items(g.get("tech_stack"), "general.tech_stack")
    _check_items(g.get("highlights"), "general.highlights")
    _check_red_lines(g.get("red_lines"))


def _check_specific(sp: Any) -> None:
    if not isinstance(sp, dict):
        raise SchemaError("specific: 应为对象")
    _check_scored_item(sp.get("position_match"), "specific.position_match")
    skills = sp.get("skills")
    if not isinstance(skills, list):
        raise SchemaError("specific.skills: 应为列表")
    for i, item in enumerate(skills):
        _check_scored_item(item, f"specific.skills[{i}]")
        skill = item.get("skill")
        if not isinstance(skill, str) or not skill.strip():
            raise SchemaError(f"specific.skills[{i}]: skill 必填")
        if not isinstance(item.get("hit"), bool):
            raise SchemaError(f"specific.skills[{i}]: hit 应为布尔")
