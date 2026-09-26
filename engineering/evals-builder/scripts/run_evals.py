"""评估测试器 CLI：标注数据集 → 指标（带置信区间）→ JSON + HTML，可选 pass-rate 门禁。

用法：
    python scripts/run_evals.py --data examples/sample_dataset.jsonl \
        [--json out.json] [--html out.html] [--threshold 0.85] [--no-gate]

数据契约（JSONL，每行一条记录）：
    {
      "id": "rec-001",
      "input_ref": "case/1.txt",                    # 可选
      "group": "accuracy",                           # 可选：逐组区分度用
      "predicted": {"verdict": "pass", "score": 82, "band": 3},
      "actual":    {"verdict": "pass", "score": 85, "band": 3},
      "confidence": 0.9                              # 可选 0-1
    }

- verdict: "pass"|"fail"（二元层，必填）
- band: 0..N-1 序数档（QWK 层，两侧都有才算）
- score: 数值（阈值扫描层用）
指标只基于已标注记录（actual.verdict 存在）；QWK 只基于两侧都有 band 的记录。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from metrics import (
    accuracy,
    bootstrap_ci,
    confusion_matrix,
    discrimination,
    f1,
    precision,
    qwk,
    recall,
    wilson_ci,
)

HERE = Path(__file__).resolve().parent
REPORT_TEMPLATE = HERE.parent / "templates" / "report.html"


def load_records(path: Path) -> List[dict]:
    if not path.exists():
        raise SystemExit(f"数据集不存在: {path}")
    records = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise SystemExit(f"{path}:{lineno} 非法 JSON: {e}")
    if not records:
        raise SystemExit(f"{path}: 无记录")
    return records


def _verdict_bool(v: dict) -> Optional[bool]:
    vd = (v or {}).get("verdict")
    if vd is None:
        return None
    return vd == "pass"


def _band(v: dict) -> Optional[int]:
    b = (v or {}).get("band")
    return b if isinstance(b, int) else None


def compute(records: List[dict]) -> Dict:
    actual = [_verdict_bool(r.get("actual")) for r in records]
    predicted = [_verdict_bool(r.get("predicted")) for r in records]
    labeled = [i for i in range(len(records)) if actual[i] is not None]
    if not labeled:
        return {"n": len(records), "labeled": 0, "error": "无已标注记录"}

    acts = [actual[i] for i in labeled]
    preds = [predicted[i] for i in labeled]
    c = confusion_matrix(acts, preds)
    acc = accuracy(c)
    acc_lo, acc_hi = wilson_ci(len(acts), c["tp"] + c["tn"])
    p = precision(c)
    r = recall(c)
    f = f1(c)

    out: Dict = {
        "n": len(records),
        "labeled": len(labeled),
        "unlabeled": len(records) - len(labeled),
        "confusion": c,
        "metrics": {
            "accuracy": acc,
            "accuracy_ci": [round(acc_lo, 4), round(acc_hi, 4)],
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f, 4),
        },
        "qwk": None,
        "discrimination": [],
    }

    # QWK：两侧都有 band 的已标注记录
    pairs = [(i, j) for i, j in
             ((_band(r.get("predicted")), _band(r.get("actual"))) for r in records)
             if i is not None and j is not None]
    if pairs:
        r1 = [a for a, _ in pairs]
        r2 = [b for _, b in pairs]
        k = max(max(r1), max(r2)) + 1
        kappa = qwk(r1, r2, n_classes=k)
        out["qwk"] = {
            "value": round(kappa, 4),
            "n": len(pairs),
            "n_classes": k,
            "ci": _qwk_ci(r1, r2, k),
        }

    # 逐组区分度：group 字段存在时，对每个 group 比较 pass/fail 桶的得分
    groups: Dict[str, List[float]] = {}
    for r in records:
        g = r.get("group")
        sc = (r.get("predicted") or {}).get("score")
        a = _verdict_bool(r.get("actual"))
        if g and isinstance(sc, (int, float)) and a is not None:
            groups.setdefault(g, []).append((sc, a))
    out["discrimination"] = [
        dict(g=g, **discrimination([sc for sc, a in v if a], [sc for sc, a in v if not a]))
        for g, v in sorted(groups.items())
    ]
    return out


def _qwk_ci(r1: List[int], r2: List[int], n_classes: int) -> Optional[list]:
    """QWK 的 bootstrap 区间（配对重采样）。"""
    if len(r1) < 5:
        return None
    idx = list(range(len(r1)))
    stat = lambda sample: qwk([r1[i] for i in sample], [r2[i] for i in sample], n_classes=n_classes)  # noqa: E731
    lo, hi = bootstrap_ci(idx, stat)
    return [round(lo, 4), round(hi, 4)]


def render_html(data: Dict, template: Path) -> str:
    html = template.read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return html.replace("__DATA__", payload)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="评估测试器：标注数据 → 指标(带 CI) → JSON+HTML")
    parser.add_argument("--data", required=True, help="标注数据集 JSONL")
    parser.add_argument("--json", default=None, help="数据侧 JSON 输出路径（缺省不写）")
    parser.add_argument("--html", default=None, help="用户侧 HTML 报告路径（缺省不写）")
    parser.add_argument("--threshold", type=float, default=None, help="pass-rate 门禁（低于则 exit 1）")
    parser.add_argument("--no-gate", action="store_true", help="忽略门禁（只报告）")
    args = parser.parse_args(argv)

    records = load_records(Path(args.data))
    data = compute(records)
    if data.get("error"):
        print(data["error"], file=sys.stderr)
        return 1

    n, labeled = data["n"], data["labeled"]
    acc = data["metrics"]["accuracy"]
    lo, hi = data["metrics"]["accuracy_ci"]
    print(f"n={n} labeled={labeled} accuracy={acc:.3f} (95% CI {lo:.3f}-{hi:.3f})")
    print(f"  confusion={data['confusion']} P={data['metrics']['precision']:.3f} "
          f"R={data['metrics']['recall']:.3f} F1={data['metrics']['f1']:.3f}")
    if data["qwk"]:
        q = data["qwk"]
        ci = f" CI {q['ci']}" if q["ci"] else ""
        print(f"  QWK={q['value']:.3f} (n={q['n']}, {q['n_classes']} 档){ci}")
    for d in data["discrimination"]:
        print(f"  group={d['g']}: mean_pass={d['mean_pass']} mean_fail={d['mean_fail']} "
              f"(n_pass={d['n_pass']} n_fail={d['n_fail']})")

    if args.json:
        Path(args.json).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.html:
        if not REPORT_TEMPLATE.exists():
            raise SystemExit(f"HTML 模板缺失: {REPORT_TEMPLATE}")
        Path(args.html).write_text(render_html(data, REPORT_TEMPLATE), encoding="utf-8")

    if args.threshold is not None and not args.no_gate:
        if acc < args.threshold:
            print(f"门禁失败: accuracy {acc:.3f} < {args.threshold}", file=sys.stderr)
            return 1
        print(f"门禁通过: accuracy {acc:.3f} >= {args.threshold}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
