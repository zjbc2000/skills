"""quotation 校验（SPEC §4.3）：后置确定性 grep，标注 exact/fuzzy/missing。

校验基准是解析后的简历文本（LLM 实际读到的内容）。missing 项标记 suspect
但保留分数——错误率在评估阶段沉淀，先不定惩罚规则。
"""
from __future__ import annotations

from copy import deepcopy
from typing import List, Union

EXACT = "exact"
FUZZY = "fuzzy"
MISSING = "missing"
FUZZY_THRESHOLD = 0.6


def normalize(s: str) -> str:
    """折叠空白（OCR/解析噪声）。"""
    return " ".join(s.split())


def _bigrams(s: str) -> set:
    s = normalize(s).lower()
    if not s:
        return set()
    if len(s) <= 1:
        return {s}
    return {s[i:i + 2] for i in range(len(s) - 1)}


def _containment(qb: set, tb: set) -> float:
    """quotation 侧大gram 在文本中可找到的比例（改写检测）。"""
    if not qb:
        return 0.0
    return len(qb & tb) / len(qb)


def verify_quotation(quotation: str, text: str) -> str:
    """判定一条引用的校验状态：exact | fuzzy | missing。

    exact = 规范化后为子串；fuzzy = 引用内容大部分能在文本中找到（改写/噪声）；
    missing = 内容与文本几乎无重叠。
    """
    nq, nt = normalize(quotation), normalize(text)
    if nq and nq in nt:
        return EXACT
    qb, tb = _bigrams(nq), _bigrams(nt)
    if _containment(qb, tb) >= FUZZY_THRESHOLD:
        return FUZZY
    return MISSING


def _annotate_item(item: dict, text: str) -> dict:
    out = dict(item)
    q = item.get("quotation")
    if isinstance(q, str) and q.strip():
        v = verify_quotation(q, text)
        out["verify"] = v
        if v == MISSING:
            out["suspect"] = True
    return out


def _annotate_list(items, text: str) -> list:
    return [_annotate_item(i, text) for i in items] if isinstance(items, list) else items


def verify_snapshot(snapshot: dict, text: str) -> dict:
    """深拷贝 snapshot，为每个含 quotation 的条目打 verify 标；不改变原对象。"""
    out = deepcopy(snapshot)
    general = out.get("general")
    if isinstance(general, dict):
        for key in ("projects", "tech_stack", "highlights", "red_lines"):
            general[key] = _annotate_list(general.get(key), text)
    specific = out.get("specific")
    if isinstance(specific, dict):
        if isinstance(specific.get("position_match"), dict):
            specific["position_match"] = _annotate_item(specific["position_match"], text)
        specific["skills"] = _annotate_list(specific.get("skills"), text)
    return out
