# book-distiller/tests/test_weread_fetch.py
from __future__ import annotations
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from weread_fetch import (
    parse_book_id, detect_export_failure, export_book, WereadExportError,
)


def test_parse_book_id_from_url():
    assert parse_book_id("https://weread.qq.com/web/reader/abc123def") == "abc123def"


def test_parse_book_id_raw():
    assert parse_book_id("abc123def") == "abc123def"


def test_parse_book_id_trailing_slash():
    assert parse_book_id("https://weread.qq.com/web/reader/abc123def/") == "abc123def"


def test_detect_publisher_restriction():
    assert detect_export_failure("该书显示去 App 阅读") is not None


def test_detect_exported_ok():
    assert detect_export_failure("导出完成") is None


def test_export_book_publisher_restriction(tmp_path):
    fake = tmp_path / "fake_exporter.py"
    fake.write_text("print('显示去 App 阅读')\n", encoding="utf-8")
    with pytest.raises(WereadExportError):
        export_book("abc123", tmp_path, fake)


def test_export_book_missing_output(tmp_path):
    fake = tmp_path / "fake_exporter.py"
    fake.write_text("print('导出完成')\n", encoding="utf-8")  # 但 output/ 无产物
    with pytest.raises(WereadExportError):
        export_book("abc123", tmp_path, fake)


def test_export_book_success(tmp_path):
    fake = tmp_path / "fake_exporter.py"
    fake.write_text("print('导出完成')\n", encoding="utf-8")
    out = tmp_path / "output"
    out.mkdir()
    (out / "书名.md").write_text("# 书名", encoding="utf-8")
    result = export_book("abc123", tmp_path, fake)
    assert result.name == "书名.md"
