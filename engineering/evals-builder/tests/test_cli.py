"""CLI 冒烟：在 examples/sample_dataset.jsonl 上跑通 run_evals / threshold_scan / judge_validate。

只验证外部行为：退出码、输出文件存在、关键数字合理。
"""
import json

import pytest

import judge_validate
import run_evals
import threshold_scan

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
DATASET = EXAMPLES / "sample_dataset.jsonl"
JUDGE = EXAMPLES / "sample_dataset.jsonl.judge.jsonl"
HUMAN = EXAMPLES / "sample_dataset.jsonl.human.jsonl"


def test_run_evals_smoke(tmp_path):
    out_json = tmp_path / "eval.json"
    out_html = tmp_path / "report.html"
    rc = run_evals.main([
        "--data", str(DATASET), "--json", str(out_json), "--html", str(out_html),
    ])
    assert rc == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["n"] == 10 and data["labeled"] == 10
    # 示例数据 8/10 正确
    assert data["metrics"]["accuracy"] == pytest.approx(0.8)
    assert data["metrics"]["accuracy_ci"][0] < 0.8 < data["metrics"]["accuracy_ci"][1]
    assert data["qwk"] is not None and 0.0 < data["qwk"]["value"] <= 1.0
    assert data["discrimination"], "group 区分度应有输出"
    html = out_html.read_text(encoding="utf-8")
    assert "__DATA__" not in html, "占位符应已被替换"
    assert "混淆矩阵" in html


def test_run_evals_gate(tmp_path):
    # accuracy=0.8，threshold=0.85 → 门禁失败 exit 1
    rc = run_evals.main(["--data", str(DATASET), "--threshold", "0.85"])
    assert rc == 1
    rc_ok = run_evals.main(["--data", str(DATASET), "--threshold", "0.8"])
    assert rc_ok == 0


def test_run_evals_missing_data():
    with pytest.raises(SystemExit):
        run_evals.main(["--data", str(ROOT / "nope.jsonl")])


def test_threshold_scan_smoke(tmp_path):
    out_json = tmp_path / "scan.json"
    rc = threshold_scan.main(["--data", str(DATASET), "--lo", "0", "--hi", "100", "--json", str(out_json)])
    assert rc == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["best"]["n"] == 10
    assert data["best"]["threshold_range"][0] <= data["best"]["threshold_range"][1]
    assert isinstance(data["misclassified_at_best"], list)


def test_judge_validate_passing(tmp_path):
    # 示例 judge/human 有 1 处不一致 → kappa≈0.762 > 0.55，退出 0
    rc = judge_validate.main(["--predictions", str(JUDGE), "--labels", str(HUMAN),
                              "--kappa-threshold", "0.55"])
    assert rc == 0


def test_judge_validate_alerts_on_low_kappa():
    # 阈值提到 0.9 → 告警 exit 1
    rc = judge_validate.main(["--predictions", str(JUDGE), "--labels", str(HUMAN),
                              "--kappa-threshold", "0.9"])
    assert rc == 1
