"""评估 CLI（SPEC §8）：从 manifest 构建记录，输出 JSON（数据侧）+ HTML 报告（用户侧）。

用法：python -m backend.eval.run_eval --datasets <dir> [--html out.html] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from ..config import load_config
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


def build_records(raw: List[dict]) -> List[dict]:
    out = []
    for r in raw:
        snap = r.get("score_snapshot") or {}
        out.append({
            "resume": r.get("resume"),
            "jd_ref": r.get("jd_ref"),
            "actual": r.get("decision") == "pass",
            "predicted": snap.get("verdict") == "pass",
            "snapshot": snap,
        })
    return out


def _max_total(records: List[dict]) -> int:
    return max(
        ((r.get("snapshot") or {}).get("totals") or {}).get("T", 0) for r in records
    ) if records else 0


def build_eval_data(records: List[dict], cfg, fixed_general=None, total_range=None) -> dict:
    """由记录与配置计算完整评估数据（CLI 与 API 共用，DRY）。"""
    if not records:
        return {"n": 0, "records": [], "metrics": {}, "confusion": {},
                "quotation_accuracy": {"ratio": 0.0}}
    fixed_general = fixed_general if fixed_general is not None else int(cfg.thresholds["general"])
    lo, hi = (0, _max_total(records)) if total_range is None else total_range

    c = confusion(records)
    q_exact, q_total, q_ratio = quotation_accuracy(records)
    rows, best = threshold_scan(records, fixed_general=fixed_general, total_range=(lo, hi))
    return {
        "n": len(records),
        "metrics": {
            "accuracy": accuracy(c), "precision": precision(c),
            "recall": recall(c), "f1": f1(c), "n": len(records),
        },
        "confusion": {"tp": c.tp, "fp": c.fp, "tn": c.tn, "fn": c.fn},
        "quotation_accuracy": {"exact": q_exact, "total": q_total, "ratio": q_ratio},
        "threshold_scan": rows,
        "best": best,
        "discrimination": metric_discrimination(records),
        "records": [
            {"resume": r["resume"], "jd_ref": r["jd_ref"],
             "actual": "pass" if r["actual"] else "fail",
             "predicted": "pass" if r["predicted"] else "fail"}
            for r in records
        ],
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
    records = build_records(load_records(datasets / "manifest.jsonl"))
    if not records:
        print(f"manifest 无记录: {datasets / 'manifest.jsonl'}", file=sys.stderr)
        return 1

    data = build_eval_data(records, load_config(), fixed_general=args.general,
                           total_range=_parse_range(args.total_range))


    out_json = Path(args.json) if args.json else datasets / "eval.json"
    out_html = Path(args.html) if args.html else datasets / "eval.html"
    out_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    out_html.write_text(render_html(data), encoding="utf-8")
    print(f"评估完成: {out_json}\n报告: {out_html}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
