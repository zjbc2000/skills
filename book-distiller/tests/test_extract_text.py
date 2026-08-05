# book-distiller/tests/test_extract_text.py
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import fitz
from extract_text import extract_toc, extract_text, pdf_is_scanned, extract_to_markdown


def _gen_text_pdf(path: Path, with_toc: bool = True) -> None:
    doc = fitz.open()
    for i in range(5):
        page = doc.new_page()
        page.insert_text((72, 100), f"Chapter {i} content line one.")
        page.insert_text((72, 120), f"Some body text for page {i}.")
    if with_toc:
        doc.set_toc([[1, "Chapter 0", 1], [1, "Chapter 1", 2], [1, "Chapter 2", 3]])
    doc.save(str(path))
    doc.close()


def test_extract_toc(tmp_path):
    p = tmp_path / "book.pdf"
    _gen_text_pdf(p)
    toc = extract_toc(p)
    assert len(toc) == 3
    assert toc[0] == {"level": 1, "title": "Chapter 0", "page": 1}


def test_extract_text(tmp_path):
    p = tmp_path / "book.pdf"
    _gen_text_pdf(p)
    assert "Chapter 0 content" in extract_text(p)


def test_text_pdf_not_scanned(tmp_path):
    p = tmp_path / "book.pdf"
    _gen_text_pdf(p)
    assert pdf_is_scanned(p) is False


def test_blank_pdf_is_scanned(tmp_path):
    p = tmp_path / "scanned.pdf"
    doc = fitz.open()
    doc.new_page()  # 无文字
    doc.save(str(p))
    doc.close()
    assert pdf_is_scanned(p) is True


def test_extract_to_markdown_with_toc(tmp_path):
    p = tmp_path / "book.pdf"
    _gen_text_pdf(p)
    out = tmp_path / "book.md"
    extract_to_markdown(p, out)
    md = out.read_text(encoding="utf-8")
    assert "## Chapter 0" in md
    assert "## Chapter 2" in md


def test_extract_to_markdown_no_toc(tmp_path):
    p = tmp_path / "book.pdf"
    _gen_text_pdf(p, with_toc=False)
    out = tmp_path / "book.md"
    extract_to_markdown(p, out)
    assert "Chapter 0 content" in out.read_text(encoding="utf-8")
