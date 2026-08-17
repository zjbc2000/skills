"""评估 CLI（SPEC §8）：从 manifest 构建记录，输出 JSON（数据侧）+ HTML 报告（用户侧）。

用法：python -m backend.eval.run_eval --datasets <dir> [--html out.html] [--json out.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import List, Optional

from ..config import load_config
from ..persistence.labels import load_labels
from ..persistence.manifest import load_records
from .metrics import (
    accuracy,
    confusion,
    f1,
    metric_discrimination,
    precision,
    quotation_accuracy,
    recall,
    threshold_scan,
)
from .report import render_html

DEFAULT_DATASETS = Path(__file__).resolve().parent.parent.parent / "datasets"


def record_key(r: dict) -> str:
    """manifest 记录指纹：resume + jd_ref + time 的 sha1。"""
    raw = f"{r.get('resume')}|{r.get('jd_ref')}|{r.get('time')}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def build_records(
    raw: List[dict],
    labels: Optional[dict] = None,
    thresholds: Optional[dict] = None,
) -> List[dict]:
    """由 manifest 记录构建评测记录。

    actual 来自人工标注（labels，缺省 None=未标注）；predicted 按当前阈值
    从 totals 重算（G>=general 且 T>=total），调阈值后无需重新筛简历。
    """
    labels = labels or {}
    out = []
    for r in raw:
        snap = r.get("score_snapshot") or {}
        totals = snap.get("totals") or {}
        if thresholds is not None:
            predicted = (
                totals.get("G", 0) >= thresholds["general"]
                and totals.get("T", 0) >= thresholds["total"]
            )
        else:
            predicted = snap.get("verdict") == "pass"
        label = labels.get(record_key(r))
        out.append({
            "record_key": record_key(r),
            "resume": r.get("resume"),
            "jd_ref": r.get("jd_ref"),
            "label": label,
            "actual": (label == "pass") if label else None,
            "predicted": predicted,
            "snapshot": snap,
        })
    return out


def _max_total(records: List[dict]) -> int:
    return max(
        ((r.get("snapshot") or {}).get("totals") or {}).get("T", 0) for r in records
    ) if records else 0


def build_eval_data(records: List[dict], cfg, fixed_general=None, total_range=None) -> dict:
    """由记录与配置计算完整评估数据（CLI 与 API 共用，DRY）。

    指标只基于已人工标注的子集；quoted 准确率基于全部记录。
    """
    labeled = [dict(r, actual=bool(r["actual"])) for r in records if r.get("actual") is not None]
    unlabeled = len(records) - len(labeled)
    row = lambda r: {  # noqa: E731
        "record_key": r["record_key"],
        "resume": r["resume"], "jd_ref": r["jd_ref"],
        "label": r.get("label"),
        "predicted": "pass" if r["predicted"] else "fail",
    }
    if not labeled:
        return {
            "n": len(records), "labeled": 0, "unlabeled": unlabeled,
            "thresholds": {k: cfg.thresholds[k] for k in ("general", "specific", "total")},
            "records": [row(r) for r in records],
            "metrics": {}, "confusion": {}, "threshold_scan": [], "best": None,
            "discrimination": [], "quotation_accuracy": {"ratio": 0.0},
        }
    fixed_general = fixed_general if fixed_general is not None else int(cfg.thresholds["general"])
    # 扫描下界围绕当前配置的总阈值（-30，最低 0），避免从 0 起扫导致推荐无意义的低阈值
    lo, hi = (0, _max_total(labeled)) if total_range is None else total_range
    if total_range is None:
        lo = max(0, int(cfg.thresholds["total"]) - 30)

    c = confusion(labeled)
    q_exact, q_total, q_ratio = quotation_accuracy(records)
    rows, best = threshold_scan(labeled, fixed_general=fixed_general, total_range=(lo, hi))
    return {
        "n": len(records),
        "labeled": len(labeled),
        "unlabeled": unlabeled,
        "thresholds": {k: cfg.thresholds[k] for k in ("general", "specific", "total")},
        "metrics": {
            "accuracy": accuracy(c), "precision": precision(c),
            "recall": recall(c), "f1": f1(c), "n": len(labeled),
        },
        "confusion": {"tp": c.tp, "fp": c.fp, "tn": c.tn, "fn": c.fn},
        "quotation_accuracy": {"exact": q_exact, "total": q_total, "ratio": q_ratio},
        "threshold_scan": rows,
        "best": best,
        "discrimination": metric_discrimination(labeled),
        "records": [row(r) for r in records],
    }


def _parse_range(s):
    if not s:
        return None
    return tuple(int(x) for x in s.split(","))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="评估：对标注数据计算指标并出报告")
    parser.add_argument("--datasets", default=str(DEFAULT_DATASETS))
    parser.add_argument("--json", default=None, help="数据侧 JSON 输出路径（缺省 datasets/eval.json）")
    parser.add_argument("--html", default=None, help="HTML 报告路径（缺省 datasets/eval.html）")
    parser.add_argument("--general", type=int, default=None, help="阈值扫描固定的通用阈值（缺省取 config）")
    parser.add_argument("--total-range", default=None, help="阈值扫描区间 'lo,hi'（缺省 0..最大 T）")
    args = parser.parse_args(argv)

    datasets = Path(args.datasets)
    import os

    cfg = load_config(os.environ.get("RESUME_CONFIG") or None)
    records = build_records(
        load_records(datasets / "manifest.jsonl"),
        labels=load_labels(datasets / "labels.json"),
        thresholds=cfg.thresholds,
    )
    if not records:
        print(f"manifest 无记录: {datasets / 'manifest.jsonl'}", file=sys.stderr)
        return 1

    data = build_eval_data(records, cfg, fixed_general=args.general,
                           total_range=_parse_range(args.total_range))


    out_json = Path(args.json) if args.json else datasets / "eval.json"
    out_html = Path(args.html) if args.html else datasets / "eval.html"
    out_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    out_html.write_text(render_html(data), encoding="utf-8")
    print(f"评估完成: {out_json}\n报告: {out_html}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
