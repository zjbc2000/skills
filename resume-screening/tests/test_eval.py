"""评估 pipeline（T07）：指标、混淆矩阵、阈值扫描、报告生成。"""
from __future__ import annotations

import json

import pytest

from backend.eval.metrics import (
    accuracy,
    confusion,
    f1,
    metric_discrimination,
    precision,
    quotation_accuracy,
    recall,
    threshold_scan,
)


def test_confusion_and_metrics_basic():
    records = [
        {"actual": True, "predicted": True},    # tp
        {"actual": False, "predicted": True},   # fp
        {"actual": False, "predicted": False},  # tn
        {"actual": True, "predicted": False},   # fn
    ]
    c = confusion(records)
    assert (c.tp, c.fp, c.tn, c.fn) == (1, 1, 1, 1)
    assert accuracy(c) == 0.5
    assert precision(c) == 0.5
    assert recall(c) == 0.5
    assert f1(c) == 0.5


def test_accuracy_perfect():
    c = confusion([{"actual": True, "predicted": True}, {"actual": False, "predicted": False}])
    assert accuracy(c) == 1.0
    assert precision(c) == 1.0
    assert recall(c) == 1.0
    assert f1(c) == 1.0


def test_zero_division_guards():
    c = confusion([{"actual": False, "predicted": False}])  # 只有 tn
    assert precision(c) == 0.0
    assert recall(c) == 0.0
    assert f1(c) == 0.0


def test_quotation_accuracy():
    records = [{
        "snapshot": {
            "general": {"projects": [{"verify": "exact"}], "tech_stack": [],
                        "highlights": [{"verify": "missing"}], "red_lines": []},
            "specific": {"position_match": {"verify": "exact"},
                         "skills": [{"verify": "fuzzy"}]},
        }
    }]
    exact, total, ratio = quotation_accuracy(records)
    assert (exact, total) == (2, 4)
    assert ratio == 0.5


def test_threshold_scan_finds_best_operating_point():
    records = [
        {"actual": True, "snapshot": {"totals": {"G": 10, "S": 1, "T": 10}}},
        {"actual": False, "snapshot": {"totals": {"G": 10, "S": 1, "T": 4}}},
    ]
    rows, best = threshold_scan(records, fixed_general=8, total_range=(0, 12))
    assert best["accuracy"] == 1.0  # 阈值 5..10 区间两记录都判对
    assert all("n_pass" in r and "n_fail" in r for r in rows)
    assert len(rows) == 13  # 0..12 每个阈值一行


def test_metric_discrimination():
    records = [
        {"actual": True, "snapshot": {
            "general": {"projects": [{"bonus": 3}], "tech_stack": [], "highlights": [], "red_lines": []},
            "specific": {"position_match": {"bonus": 2}, "skills": []}}},
        {"actual": False, "snapshot": {
            "general": {"projects": [{"bonus": 1}], "tech_stack": [], "highlights": [], "red_lines": []},
            "specific": {"position_match": {"bonus": 0}, "skills": []}}},
    ]
    disc = {d["metric"]: d for d in metric_discrimination(records)}
    assert disc["projects"]["avg_pass"] == 3.0
    assert disc["projects"]["avg_fail"] == 1.0
    assert disc["position_match"]["avg_pass"] == 2.0
    assert disc["position_match"]["avg_fail"] == 0.0


def test_run_eval_writes_json_and_html(tmp_path, monkeypatch):
    from backend.eval.run_eval import main as eval_main, record_key
    from backend.config import load_config

    manifest = tmp_path / "manifest.jsonl"
    recs = [
        {"resume": "a.pdf", "decision": "pass", "jd_ref": "R",
         "score_snapshot": {"verdict": "pass", "totals": {"G": 10, "S": 1, "T": 10},
                            "general": {"projects": [{"verify": "exact"}], "tech_stack": [],
                                        "highlights": [], "red_lines": []},
                            "specific": {"position_match": {"verify": "exact"}, "skills": []}}},
        {"resume": "b.pdf", "decision": "fail", "jd_ref": "R",
         "score_snapshot": {"verdict": "fail", "totals": {"G": 10, "S": 1, "T": 4},
                            "general": {"projects": [{"verify": "missing"}], "tech_stack": [],
                                        "highlights": [], "red_lines": []},
                            "specific": {"position_match": {"verify": "exact"}, "skills": []}}},
    ]
    for r in recs:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest, "a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 人工真值：a=pass, b=fail；阈值用 tmp 配置（G>=8 且 T>=5 -> a 判对）
    labels = {record_key(recs[0]): "pass", record_key(recs[1]): "fail"}
    (tmp_path / "labels.json").write_text(json.dumps(labels), encoding="utf-8")
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "models.yml").write_text(
        "providers:\n  p:\n    base_url: http://x\n    api_key_env: K\n    models: [m]\n"
        "default:\n  provider: p\n  model: m\n", encoding="utf-8")
    (cfg_dir / "tools.yml").write_text("doc_loader:\n  primary: local_pymupdf\n", encoding="utf-8")
    (cfg_dir / "thresholds.yml").write_text(
        "general: 8\nspecific: 20\ntotal: 5\n", encoding="utf-8")
    monkeypatch.setenv("RESUME_CONFIG", str(cfg_dir))
    assert load_config(cfg_dir).thresholds["total"] == 5

    out_html = tmp_path / "report.html"
    out_json = tmp_path / "report.json"
    rc = eval_main(["--datasets", str(tmp_path), "--html", str(out_html), "--json", str(out_json)])
    assert rc == 0
    assert out_html.exists()
    assert "混淆矩阵" in out_html.read_text(encoding="utf-8")
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["metrics"]["accuracy"] == 1.0
    assert data["labeled"] == 2 and data["unlabeled"] == 0
    assert data["quotation_accuracy"] == {"exact": 3, "total": 4, "ratio": 0.75}
    assert len(data["records"]) == 2
    assert all("record_key" in r and "label" in r for r in data["records"])
