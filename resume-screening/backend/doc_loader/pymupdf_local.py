"""本地数字 PDF 直读（降级链第一档，SPEC §5.3）。"""
from __future__ import annotations

import fitz

from .base import LoaderError

# 低于该字符数的页判定为扫描页（每页过少 → 走 OCR，SPEC §5.3）
MIN_PAGE_CHARS = 50


def extract_text(path) -> str:
    try:
        doc = fitz.open(str(path))
    except Exception as e:
        raise LoaderError(f"无法打开 PDF: {e}") from e
    try:
        pages = [page.get_text() for page in doc]
    finally:
        doc.close()
    if pages and all(len(page.strip()) < MIN_PAGE_CHARS for page in pages):
        raise LoaderError("各页抽取文本过少，疑似扫描件（需 OCR 兜底）")
    return "\n".join(pages).strip()
