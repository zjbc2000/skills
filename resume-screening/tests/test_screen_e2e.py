"""端到端追踪弹（T04）：PDF → 解析 → 评分 → manifest（fake LLM）。"""
from __future__ import annotations

import json

import pytest

from backend.cli.screen import main

RESUME_TEXT = (
    "Zhang San - Senior Engineer\n"
    "3 years of experience with react and python.\n"
    "Led an OCR pipeline team at company X.\n"
)

JD_YML = """roles:
  西安AE:
    position: 高级AE工程师
    skills: [react]
    red_lines: []
"""


def _make_pdf(path):
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), RESUME_TEXT)
    doc.save(str(path))
    doc.close()


def test_screen_writes_manifest_with_fake_llm(tmp_path):
    pdf = tmp_path / "resume.pdf"
    _make_pdf(pdf)
    (tmp_path / "jd_map.yml").write_text(JD_YML, encoding="utf-8")

    rc = main([
        str(pdf), "--jd", "西安AE", "--mode", "general_specific",
        "--datasets", str(tmp_path), "--llm", "fake",
    ])
    assert rc == 0

    manifest = tmp_path / "manifest.jsonl"
    assert manifest.exists()
    lines = [json.loads(l) for l in manifest.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1
    rec = lines[0]
    assert rec["jd_ref"] == "西安AE"
    snap = rec["score_snapshot"]
    assert snap["totals"] == {"G": 3, "S": 3, "T": 6}  # fake LLM 固定输出
    assert rec["doc_loader"] == "local_pymupdf"


def test_list_failed_lists_records(tmp_path, capsys):
    (tmp_path / "failed.jsonl").write_text(
        '{"prompt": "x", "providers": ["p1"], "error": "all providers failed", "ts": 1}\n',
        encoding="utf-8",
    )
    rc = main(["--list-failed", "--datasets", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"providers": ["p1"]' in out


def test_screen_requires_jd_when_not_listing(tmp_path):
    with pytest.raises(SystemExit) as e:
        main(["some.pdf", "--datasets", str(tmp_path)])
    assert e.value.code == 2  # argparse 错误


def test_screen_rejects_unknown_jd(tmp_path, capsys):
    pdf = tmp_path / "resume.pdf"
    _make_pdf(pdf)
    (tmp_path / "jd_map.yml").write_text(JD_YML, encoding="utf-8")

    rc = main([str(pdf), "--jd", "不存在岗位", "--datasets", str(tmp_path), "--llm", "fake"])
    assert rc == 1
    assert "不存在岗位" in capsys.readouterr().err
    assert not (tmp_path / "manifest.jsonl").exists()
