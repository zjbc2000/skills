#!/usr/bin/env python3
"""PDF → Markdown：读内嵌书签做章节切分；检测扫描版提示换 MinerU。

用法: python3 extract_text.py <book.pdf> -o <out.md>
"""
from __future__ import annotations
import sys
from pathlib import Path

import fitz  # PyMuPDF


def extract_toc(pdf_path: Path) -> list[dict]:
    doc = fitz.open(str(pdf_path))
    toc = [{"level": level, "title": title, "page": page}
           for level, title, page in doc.get_toc()]
    doc.close()
    return toc


def extract_text(pdf_path: Path) -> str:
    doc = fitz.open(str(pdf_path))
    parts = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(parts)


def pdf_is_scanned(pdf_path: Path, min_chars_per_page: int = 20) -> bool:
    doc = fitz.open(str(pdf_path))
    total = sum(len(page.get_text()) for page in doc)
    n = len(doc)
    doc.close()
    return n > 0 and total / n < min_chars_per_page


def extract_to_markdown(pdf_path: Path, out_md: Path, engine: str = "pymupdf") -> None:
    if engine == "docling":
        _extract_to_markdown_docling(pdf_path, out_md)
        return
    doc = fitz.open(str(pdf_path))
    text_pages = [page.get_text() for page in doc]
    toc = doc.get_toc()
    doc.close()
    if not toc:
        body = "\n\n".join(text_pages)
    else:
        body = ""
        toc_pages = [t[2] for t in toc]
        for idx, (_level, title, page) in enumerate(toc):
            end = toc_pages[idx + 1] if idx + 1 < len(toc_pages) else len(text_pages) + 1
            seg = text_pages[page - 1:end - 1]
            body += f"\n\n## {title}\n\n" + "\n\n".join(seg)
    out_md.write_text(body, encoding="utf-8")


def _extract_to_markdown_docling(pdf_path: Path, out_md: Path) -> None:
    from docling.document_converter import DocumentConverter
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    out_md.write_text(result.document.export_to_markdown(), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="PDF → Markdown")
    ap.add_argument("pdf", help="输入 PDF 路径")
    ap.add_argument("-o", "--out", required=True, help="输出 Markdown 路径")
    ap.add_argument("--engine", choices=["pymupdf", "docling"], default="pymupdf",
                    help="提取引擎：pymupdf（默认）或 docling（需 pip install docling）")
    args = ap.parse_args(argv)
    src = Path(args.pdf)
    if args.engine == "docling":
        try:
            import docling  # noqa: F401
        except ImportError:
            print("未安装 docling 库，需要 pip install docling。", file=sys.stderr)
            return 1
    if pdf_is_scanned(src):
        print("检测到扫描版 PDF（无可提取文字）。请改用 MinerU 做 OCR，或人工提供 Markdown。", file=sys.stderr)
        return 1
    extract_to_markdown(src, Path(args.out), engine=args.engine)
    print(f"已输出: {args.out} (章节数: {len(extract_toc(src))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
