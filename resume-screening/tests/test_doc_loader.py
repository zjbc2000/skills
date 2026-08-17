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


def test_doc_to_text_skips_unimplemented_and_uses_fallback(tmp_path):
    pdf = _make_pdf(tmp_path / "r.pdf")
    # layout_parsing 未实现（T05 才有），应跳过并落到 local_pymupdf
    res = doc_to_text(pdf, ["layout_parsing", "local_pymupdf"])
    assert "react" in res.text
    assert res.loader == "local_pymupdf"


def test_doc_to_text_raises_when_all_fail(tmp_path):
    pdf = _make_pdf(tmp_path / "scan.pdf", text="hi")
    with pytest.raises(LoaderError):
        doc_to_text(pdf, ["layout_parsing", "local_pymupdf"])


def test_resolve_loader_names_dedups():
    cfg = type("C", (), {"doc_loader": {"primary": "layout_parsing", "fallback": ["local_pymupdf", "layout_parsing"]}})()
    assert resolve_loader_names(cfg) == ["layout_parsing", "local_pymupdf"]
