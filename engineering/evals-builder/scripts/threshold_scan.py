"""阈值扫描 CLI：输出「建议区间 + 样本级列举」，不输出单点精确值。

小样本纪律（references/metrics-taxonomy.md §5）：阈值调到 max-F1 再直接上线是常见错误
（过拟合到 10-50 条噪声）。本工具只给最优准确率所在的阈值区间，并在该区间列出误判样本。

用法：
    python scripts/threshold_scan.py --data examples/sample_dataset.jsonl \
        --score-key predicted.score --lo 0 --hi 100 [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from metrics import accuracy, confusion_matrix


def _num(v) -> Optional[float]:
    return v if isinstance(v, (int, float)) else None


def load_rows(path: Path, score_key: str):
    if not path.exists():
        raise SystemExit(f"数据集不存在: {path}")
    rows = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError as e:
            raise SystemExit(f"{path}:{lineno} 非法 JSON: {e}")
        score = r
        for key in score_key.split("."):
            if isinstance(score, dict):
                score = score.get(key)
        actual_v = ((r.get("actual") or {}).get("verdict"))
        if score is None or actual_v is None:
            continue
        rows.append({"id": r.get("id", lineno), "score": float(score), "actual": actual_v == "pass"})
    if not rows:
        raise SystemExit(f"{path}: 无含 score + actual.verdict 的记录")
    return rows


def scan(rows: List[dict], lo: int, hi: int) -> Dict:
    out = []
    best_acc = -1.0
    best_thresholds = []
    for t in range(lo, hi + 1):
        preds = [r["score"] >= t for r in rows]
        acts = [r["actual"] for r in rows]
        c = confusion_matrix(acts, preds)
        acc = accuracy(c)
        out.append({"threshold": t, "n_pass": c["tp"] + c["fp"], "n_fail": c["tn"] + c["fn"], "accuracy": round(acc, 4)})
        if acc > best_acc:
            best_acc = acc
            best_thresholds = [t]
        elif acc == best_acc:
            best_thresholds.append(t)

    # 最优区间：连续取最大准确率的阈值段
    best_lo = min(best_thresholds) if best_thresholds else None
    best_hi = max(best_thresholds) if best_thresholds else None
    t_mid = best_thresholds[len(best_thresholds) // 2]
    mis = []
    for r in rows:
        pred = r["score"] >= t_mid
        if pred != r["actual"]:
            mis.append({"id": r["id"], "score": r["score"],
                        "actual": "pass" if r["actual"] else "fail",
                        "predicted": "pass" if pred else "fail"})
    return {
        "rows": out,
        "best": {"accuracy": round(best_acc, 4), "threshold_range": [best_lo, best_hi],
                 "n": len(rows)},
        "misclassified_at_best": mis,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="阈值扫描：建议区间 + 误判样本列举")
    parser.add_argument("--data", required=True)
    parser.add_argument("--score-key", default="predicted.score")
    parser.add_argument("--lo", type=int, default=0)
    parser.add_argument("--hi", type=int, default=100)
    parser.add_argument("--json", default=None)
    args = parser.parse_args(argv)

    rows = load_rows(Path(args.data), args.score_key)
    data = scan(rows, args.lo, args.hi)

    b = data["best"]
    print(f"n={b['n']} 最优准确率={b['accuracy']:.3f} @ 阈值区间 [{b['threshold_range'][0]}, {b['threshold_range'][1]}]")
    print("（小样本下只作量级参考，勿单点精确调参；以下为该区间中位阈值的误判样本）")
    for m in data["misclassified_at_best"]:
        print(f"  ✗ {m['id']}: score={m['score']} actual={m['actual']} predicted={m['predicted']}")

    if args.json:
        Path(args.json).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
