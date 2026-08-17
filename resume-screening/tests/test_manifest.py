"""manifest 事件流读写（T04）。"""
from __future__ import annotations

from backend.persistence.manifest import append_record, load_records


def test_append_and_load_roundtrip(tmp_path):
    p = tmp_path / "manifest.jsonl"
    append_record({"resume": "a.pdf", "decision": "pass"}, p)
    append_record({"resume": "b.pdf", "decision": "fail"}, p)
    recs = load_records(p)
    assert len(recs) == 2
    assert recs[0]["resume"] == "a.pdf"
    assert recs[1]["decision"] == "fail"


def test_missing_file_returns_empty(tmp_path):
    assert load_records(tmp_path / "nope.jsonl") == []


def test_build_record_contains_snapshot_and_decision(tmp_path):
    from backend.persistence.manifest import build_record

    class FakeVerdict:
        passed = True
        snapshot = {"totals": {"G": 9}}

    rec = build_record(
        resume="r.pdf", jd_ref="西安AE", verdict=FakeVerdict(), doc_loader="local_pymupdf",
    )
    assert rec["decision"] == "pass"
    assert rec["jd_ref"] == "西安AE"
    assert rec["score_snapshot"]["totals"] == {"G": 9}
    assert rec["doc_loader"] == "local_pymupdf"
    assert rec["time"]
