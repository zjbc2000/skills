"""判定引擎（SPEC §3）：两模式计分、红线一票否决。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

MODE_GENERAL = "general"
MODE_SPECIFIC = "specific"
MODES = (MODE_GENERAL, MODE_SPECIFIC)


@dataclass(frozen=True)
class Verdict:
    passed: bool
    g: int
    s: int
    t: int
    red_lines_hit: List[str]
    snapshot: dict


def _sum_items(items) -> int:
    return sum(int(i.get("bonus", 0)) for i in items)


def compute_scores(data: dict) -> tuple:
    """返回 (G, S)。S 只累计 hit=true 的技能（SPEC §1「命中之和」）。"""
    general = data.get("general", {})
    g = (
        _sum_items(general.get("projects", []))
        + _sum_items(general.get("tech_stack", []))
        + _sum_items(general.get("highlights", []))
    )
    specific = data.get("specific", {})
    pm = specific.get("position_match", {}) if isinstance(specific.get("position_match"), dict) else {}
    hit_skills = [sk for sk in specific.get("skills", []) if sk.get("hit")]
    s = int(pm.get("bonus", 0)) + _sum_items(hit_skills)
    return g, s


def red_lines_hit(data: dict) -> List[str]:
    return [
        r.get("rule", "(未命名红线)")
        for r in data.get("general", {}).get("red_lines", [])
        if r.get("hit")
    ]


def _build_snapshot(
    data: dict, mode: str, g: int, s: int, t: int, thresholds: dict, passed: bool
) -> dict:
    return {
        "mode": mode,
        "general": data.get("general", {}),
        "specific": data.get("specific", {}),
        "totals": {"G": g, "S": s, "T": t},
        "thresholds": dict(thresholds),
        "verdict": "pass" if passed else "fail",
    }


def assess(data: dict, mode: str, thresholds: dict) -> Verdict:
    """对已校验的 LLM 输出做判定，返回 Verdict（含 snapshot）。"""
    if mode not in MODES:
        raise ValueError(f"未知模式: {mode}")
    g, s = compute_scores(data)
    t = g + s
    hits = red_lines_hit(data)

    passed = False
    if not hits:
        if mode == MODE_GENERAL:
            passed = g >= thresholds["general"] and t >= thresholds["total"]
        else:
            passed = s >= thresholds["specific"]

    return Verdict(
        passed=passed,
        g=g,
        s=s,
        t=t,
        red_lines_hit=hits,
        snapshot=_build_snapshot(data, mode, g, s, t, thresholds, passed),
    )
