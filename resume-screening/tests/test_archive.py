"""压缩包支持（T09）：安全解压（zip-slip 防护）+ 逐份筛汇总。"""
from __future__ import annotations

import zipfile

import pytest

from backend.archive import ArchiveError, safe_extract_zip, screen_archive


def _zip_with(entries, zip_path):
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, content in entries:
            zf.writestr(name, content)
    return zip_path


def _fake_screen(name):
    return {
        "verdict": type("V", (), {"g": 1, "s": 1, "t": 2, "red_lines_hit": []}),
        "snapshot": {"verdict": "pass", "thresholds": {"general": 1, "total": 2}},
        "doc": type("D", (), {"loader": "fake"}),
    }


def test_extract_pdfs_recursively(tmp_path):
    z = _zip_with([("a.pdf", b"a"), ("notes.txt", b"n"), ("sub/b.pdf", b"b")], tmp_path / "x.zip")
    pdfs = safe_extract_zip(z, tmp_path / "out")
    assert {p.name for p in pdfs} == {"a.pdf", "b.pdf"}


def test_zip_slip_relative_rejected(tmp_path):
    z = _zip_with([("../evil.txt", b"boom")], tmp_path / "evil.zip")
    with pytest.raises(ArchiveError):
        safe_extract_zip(z, tmp_path / "out")
    assert not (tmp_path / "evil.txt").exists()


def test_zip_slip_absolute_rejected(tmp_path):
    z = tmp_path / "abs.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("/etc/evil.txt", b"x")
    with pytest.raises(ArchiveError):
        safe_extract_zip(z, tmp_path / "out")


def test_screen_archive_no_pdf_returns_hint(tmp_path):
    z = _zip_with([("notes.txt", b"n")], tmp_path / "x.zip")
    assert "没有 PDF" in screen_archive(z, _fake_screen)


def test_screen_archive_aggregates_each_pdf(tmp_path):
    z = _zip_with([("a.pdf", b"a"), ("b.pdf", b"b")], tmp_path / "x.zip")
    out = screen_archive(z, _fake_screen)
    assert "a.pdf" in out
    assert "b.pdf" in out
    assert out.count("判定") == 2
