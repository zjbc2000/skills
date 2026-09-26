#!/usr/bin/env bash
# 周期执行包装：跑评估 + judge 校准，产物带时间戳。cron 调用示例：
#   0 3 * * *  /path/to/evals-builder/scripts/periodic_eval.sh
# GitHub Actions: 见 templates/ci-*.yml 的 schedule 触发。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
DATA="${1:-$ROOT/examples/sample_dataset.jsonl}"
OUT="${2:-$ROOT/out}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"

echo "== 评估 $(date) =="
python3 "$HERE/run_evals.py" \
    --data "$DATA" \
    --json "$OUT/eval-$STAMP.json" \
    --html "$OUT/report-$STAMP.html" \
    --threshold 0.8 || true   # 门禁失败不中断排程（保留产物供复盘），如需硬阻断去掉 || true

echo "== judge 校准 =="
if [[ -f "$DATA.judge.jsonl" && -f "$DATA.human.jsonl" ]]; then
    python3 "$HERE/judge_validate.py" \
        --predictions "$DATA.judge.jsonl" --labels "$DATA.human.jsonl" \
        --kappa-threshold 0.55 || true
else
    echo "（跳过：未提供 $DATA.judge.jsonl / $DATA.human.jsonl）"
fi

echo "产物: $OUT/eval-$STAMP.json $OUT/report-$STAMP.html"
