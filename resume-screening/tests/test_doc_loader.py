"""文档解析（T04）：数字 PDF 直读 + 未实现解析器自动跳过。"""
from __future__ import annotations

import pytest

from backend.doc_loader.base import LoaderError, doc_to_text, resolve_loader_names
from backend.doc_loader.pymupdf_local import extract_text

RESUME_TEXT = (
    "Zhang San - Senior Engineer\n"
    "3 years of experience with react and python.\n"
    "Led a team building an OCR pipeline at company X.\n"
)


def _make_pdf(path, text=RESUME_TEXT):
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()
    return path


def test_extract_text_from_digital_pdf(tmp_path):
    pdf = _make_pdf(tmp_path / "r.pdf")
    text = extract_text(pdf)
    assert "react" in text
    assert "python" in text


def test_sparse_text_flagged_as_scanned(tmp_path):
    pdf = _make_pdf(tmp_path / "scan.pdf", text="hi")
    with pytest.raises(LoaderError):
        extract_text(pdf)


def test_mixed_pages_not_flagged_scanned(tmp_path):
    """多页：首页丰富、次页稀疏 → 不算扫描件（每页过少才算，SPEC §5.3）。"""
    import fitz

    pdf = tmp_path / "mixed.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), RESUME_TEXT)
    doc.new_page().insert_text((72, 72), "hi")
    doc.save(str(pdf))
    doc.close()
    assert "react" in extract_text(pdf)


def test_doc_to_text_falls_back_when_primary_fails(tmp_path):
    pdf = _make_pdf(tmp_path / "r.pdf")
    # layout_parsing 缺凭据（测试环境无 .env）→ 应落到 local_pymupdf
    res = doc_to_text(pdf, ["layout_parsing", "local_pymupdf"])
    assert "react" in res.text
    assert res.loader == "local_pymupdf"


def test_doc_to_text_uses_layout_parsing_when_available(tmp_path, monkeypatch, fake_response):
    import backend.doc_loader.layout_parsing as lp

    pdf = _make_pdf(tmp_path / "r.pdf")
    monkeypatch.setenv("LAYOUT_PARSING_URL", "https://x")
    monkeypatch.setenv("LAYOUT_PARSING_TOKEN", "tok")
    body = {"errorCode": 0, "result": {"layoutParsingResults": [{"markdown": {"text": "# Parsed markdown"}}]}}
    monkeypatch.setattr(lp.requests, "post", lambda *a, **k: fake_response(200, json_body=body))
    res = doc_to_text(pdf, ["layout_parsing", "local_pymupdf"])
    assert res.loader == "layout_parsing"
    assert "# Parsed markdown" in res.text


def test_doc_to_text_raises_when_all_fail(tmp_path):
    pdf = _make_pdf(tmp_path / "scan.pdf", text="hi")
    with pytest.raises(LoaderError):
        doc_to_text(pdf, ["layout_parsing", "local_pymupdf"])


def test_resolve_loader_names_dedups():
    cfg = type("C", (), {"doc_loader": {"primary": "layout_parsing", "fallback": ["local_pymupdf", "layout_parsing"]}})()
    assert resolve_loader_names(cfg) == ["layout_parsing", "local_pymupdf"]
