"""评估指标（T07）：混淆矩阵、准确率/精确率/召回率/F1、引用准确率、阈值扫描、单指标区分度。

records 为 dict 列表：{actual: bool, predicted: bool, snapshot: dict}。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Confusion:
    tp: int
    fp: int
    tn: int
    fn: int


def confusion(records: List[dict]) -> Confusion:
    tp = fp = tn = fn = 0
    for r in records:
        pred, act = bool(r["predicted"]), bool(r["actual"])
        if act and pred:
            tp += 1
        elif (not act) and pred:
            fp += 1
        elif (not act) and (not pred):
            tn += 1
        else:
            fn += 1
    return Confusion(tp=tp, fp=fp, tn=tn, fn=fn)


def accuracy(c: Confusion) -> float:
    total = c.tp + c.fp + c.tn + c.fn
    return (c.tp + c.tn) / total if total else 0.0


def precision(c: Confusion) -> float:
    return c.tp / (c.tp + c.fp) if (c.tp + c.fp) else 0.0


def recall(c: Confusion) -> float:
    return c.tp / (c.tp + c.fn) if (c.tp + c.fn) else 0.0


def f1(c: Confusion) -> float:
    p, r = precision(c), recall(c)
    return 2 * p * r / (p + r) if (p + r) else 0.0


def _iter_snapshot_items(snapshot: dict):
    general = snapshot.get("general") or {}
    for key in ("projects", "tech_stack", "highlights", "red_lines"):
        for it in general.get(key) or []:
            yield it
    specific = snapshot.get("specific") or {}
    pm = specific.get("position_match")
    if isinstance(pm, dict):
        yield pm
    for it in specific.get("skills") or []:
        yield it


def quotation_accuracy(records: List[dict]) -> Tuple[int, int, float]:
    """(exact 数, 总数, 比例)——校验基准是 exact/total（SPEC §4.3）。"""
    exact = total = 0
    for r in records:
        for it in _iter_snapshot_items(r.get("snapshot") or {}):
            v = it.get("verify")
            if v:
                total += 1
                exact += 1 if v == "exact" else 0
    return exact, total, (exact / total if total else 0.0)


def _predicted_with(totals: dict, fixed_general: int, total_gate: int) -> bool:
    return totals.get("G", 0) >= fixed_general and totals.get("T", 0) >= total_gate


def threshold_scan(
    records: List[dict], fixed_general: int, total_range: Tuple[int, int]
) -> Tuple[List[dict], dict]:
    """扫描总分阈值，返回每行 {threshold, n_pass, n_fail, accuracy} 与最优操作点。"""
    lo, hi = total_range
    rows: List[dict] = []
    best: Dict[str, object] = {}
    for t in range(lo, hi + 1):
        n_pass = n_fail = correct = 0
        for r in records:
            totals = (r.get("snapshot") or {}).get("totals") or {}
            predicted = _predicted_with(totals, fixed_general, t)
            if predicted:
                n_pass += 1
            else:
                n_fail += 1
            if predicted == bool(r.get("actual")):
                correct += 1
        acc = correct / len(records) if records else 0.0
        row = {"threshold": t, "n_pass": n_pass, "n_fail": n_fail, "accuracy": acc}
        rows.append(row)
        if not best or acc > best["accuracy"]:
            best = row
    return rows, best


def _avg(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _group_items(snapshot: dict, grp: str):
    if grp == "position_match":
        pm = (snapshot.get("specific") or {}).get("position_match")
        return [pm] if isinstance(pm, dict) else []
    if grp == "skills":
        return (snapshot.get("specific") or {}).get("skills") or []
    return (snapshot.get("general") or {}).get(grp) or []


def metric_discrimination(records: List[dict]) -> List[dict]:
    """每个指标组的 pass/fail 平均加分——区分度信号。"""
    out = []
    for grp in ("projects", "tech_stack", "highlights", "position_match", "skills"):
        pass_bonuses, fail_bonuses = [], []
        for r in records:
            items = _group_items(r.get("snapshot") or {}, grp)
            bucket = pass_bonuses if r.get("actual") else fail_bonuses
            for it in items:
                b = it.get("bonus")
                if isinstance(b, (int, float)):
                    bucket.append(float(b))
        out.append({
            "metric": grp,
            "avg_pass": _avg(pass_bonuses),
            "avg_fail": _avg(fail_bonuses),
            "n_pass": len(pass_bonuses),
            "n_fail": len(fail_bonuses),
        })
    return out
