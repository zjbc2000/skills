"""doc_to_text 统一入口：按降级链调用已注册的解析器。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Union

from ..config import AppConfig


class LoaderError(Exception):
    pass


@dataclass(frozen=True)
class DocResult:
    text: str
    loader: str


def get_loader(name: str) -> Optional[Callable[[str], str]]:
    """按名称返回解析器函数；未注册返回 None（跳过，自动降级）。"""
    if name == "layout_parsing":
        from . import layout_parsing

        return layout_parsing.extract_text
    if name == "local_pymupdf":
        from . import pymupdf_local

        return pymupdf_local.extract_text
    if name == "local_paddleocr":
        from . import paddleocr_local

        return paddleocr_local.extract_text
    return None


def resolve_loader_names(cfg: AppConfig) -> List[str]:
    """tools.yml 的 [primary] + fallback，去重保序。"""
    d = cfg.doc_loader or {}
    names: List[str] = []
    if d.get("primary"):
        names.append(d["primary"])
    names.extend(d.get("fallback", []))
    seen, out = set(), []
    for n in names:
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def doc_to_text(path: Union[Path, str], loader_names: List[str]) -> DocResult:
    """按降级链尝试解析，返回首份成功结果（含所用解析器名）。"""
    errors = []
    for name in loader_names:
        loader = get_loader(name)
        if loader is None:
            continue
        try:
            return DocResult(text=loader(path), loader=name)
        except LoaderError as e:
            errors.append(f"{name}: {e}")
            continue
    detail = "; ".join(errors) if errors else "无可用的解析器"
    raise LoaderError(f"所有解析器均失败: {detail}")
