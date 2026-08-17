"""压缩包支持（SPEC §6）：安全解压（zip-slip 防护）+ 逐份筛汇总。"""
from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from typing import Callable, List

from .screening.pipeline import build_summary


class ArchiveError(Exception):
    pass


def safe_extract_zip(zip_path, dest_dir) -> List[Path]:
    """安全解压 zip，返回其中 PDF 文件路径列表；越界成员直接拒绝。"""
    dest = Path(dest_dir).resolve()  # resolve 以对齐 macOS /var→/private/var 符号链接
    dest.mkdir(parents=True, exist_ok=True)
    pdfs: List[Path] = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            target = (dest / info.filename).resolve()
            if not target.is_relative_to(dest):
                raise ArchiveError(f"zip-slip 拦截: {info.filename}")
            if info.is_dir():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                out.write(src.read())
            if target.suffix.lower() == ".pdf":
                pdfs.append(target)
    return pdfs


def screen_archive(zip_path, screen_fn: Callable[[Path], dict]) -> str:
    """安全解压并逐份筛，返回汇总文本（每份带文件名）。"""
    with tempfile.TemporaryDirectory() as d:
        pdfs = safe_extract_zip(zip_path, Path(d))
        if not pdfs:
            return "压缩包内没有 PDF 文件"
        parts = [f"[{i + 1}] {p.name}\n{build_summary(screen_fn(p))}" for i, p in enumerate(pdfs)]
        return "\n\n".join(parts)
