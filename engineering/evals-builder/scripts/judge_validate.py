"""judge 校准 CLI：LLM judge 输出 vs 人工标注 → Cohen's kappa / QWK，低于阈值告警。

背景（references/metrics-taxonomy.md §2.4）：CI gate ≠ eval——judge 必须周期性对人类校准。
本工具即"每周抽 traces → 人工标注 → 算 kappa → 低于阈值告警"的落点。

用法：
    python scripts/judge_validate.py --predictions judge_out.jsonl --labels human.jsonl \
        [--kappa-threshold 0.55] [--qwk-threshold 0.6]

两份文件都是 JSONL，按 "id" 关联；verdict 字段 "pass"|"fail"，band 为序数档（可选）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from metrics import cohen_kappa, qwk


def load_map(path: Path) -> Dict[str, dict]:
    if not path.exists():
        raise SystemExit(f"文件不存在: {path}")
    out = {}
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError as e:
            raise SystemExit(f"{path}:{lineno} 非法 JSON: {e}")
        rid = r.get("id")
        if rid is None:
            raise SystemExit(f"{path}:{lineno} 缺 id")
        out[str(rid)] = r
    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="judge 校准：judge vs 人工 → kappa/QWK，低于阈值告警")
    parser.add_argument("--predictions", required=True, help="judge 输出 JSONL")
    parser.add_argument("--labels", required=True, help="人工标注 JSONL")
    parser.add_argument("--kappa-threshold", type=float, default=0.55)
    parser.add_argument("--qwk-threshold", type=float, default=0.6)
    args = parser.parse_args(argv)

    preds = load_map(Path(args.predictions))
    labels = load_map(Path(args.labels))
    common = sorted(set(preds) & set(labels))
    if not common:
        raise SystemExit("两份文件无重叠 id")

    def verdict(r: dict) -> Optional[bool]:
        v = (r.get("verdict"))
        return (v == "pass") if v is not None else None

    def band(r: dict) -> Optional[int]:
        b = r.get("band")
        return b if isinstance(b, int) else None

    v_pred = [verdict(preds[i]) for i in common]
    v_lab = [verdict(labels[i]) for i in common]
    pairs = [(i, j) for i, j in zip(v_pred, v_lab) if i is not None and j is not None]
    if not pairs:
        raise SystemExit("无 verdict 配对")
    k = cohen_kappa([a for a, _ in pairs], [b for _, b in pairs])

    b_pred = [band(preds[i]) for i in common]
    b_lab = [band(labels[i]) for i in common]
    b_pairs = [(i, j) for i, j in zip(b_pred, b_lab) if i is not None and j is not None]
    q = qwk([a for a, _ in b_pairs], [b for _, b in b_pairs],
            n_classes=max(max(a, b) for a, b in b_pairs) + 1) if b_pairs else None

    print(f"重叠样本 n={len(common)}（verdict 配对 {len(pairs)}）")
    print(f"Cohen's kappa = {k:.3f}" + ("  ⚠️ 低于阈值 " + str(args.kappa_threshold) if k < args.kappa_threshold else ""))
    if q is not None:
        print(f"QWK = {q:.3f}" + ("  ⚠️ 低于阈值 " + str(args.qwk_threshold) if q < args.qwk_threshold else ""))
    else:
        print("QWK: 无两侧 band，不适用")

    disagree = [i for i in common if verdict(preds[i]) is not None and verdict(preds[i]) != verdict(labels[i])]
    if disagree:
        print("不一致记录: " + ", ".join(disagree[:20]) + ("…" if len(disagree) > 20 else ""))

    if k < args.kappa_threshold:
        print(f"告警: judge 与人工一致性 kappa={k:.3f} < {args.kappa_threshold}，需校准 judge", file=sys.stderr)
        return 1
    if q is not None and q < args.qwk_threshold:
        print(f"告警: 序数一致性 QWK={q:.3f} < {args.qwk_threshold}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
