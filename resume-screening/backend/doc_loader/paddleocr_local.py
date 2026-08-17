"""本地 paddleocr（扫描件/图片兜底，SPEC §5.3 第三档）。

依赖较重：需 `pip install paddleocr paddlepaddle`，未安装时抛 LoaderError，
由降级链继续（不会因缺少该工具而中断判定流程）。
"""
from __future__ import annotations

from .base import LoaderError


def extract_text(path) -> str:
    try:
        from paddleocr import PaddleOCR
    except ImportError as e:
        raise LoaderError("paddleocr 未安装（pip install paddleocr paddlepaddle）") from e
    ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    result = ocr.ocr(str(path), cls=True)
    lines = []
    for page in result or []:
        for item in page or []:
            text = item[1][0] if len(item) > 1 else ""
            if text:
                lines.append(text)
    text = "\n".join(lines).strip()
    if not text:
        raise LoaderError("paddleocr 未识别到文本")
    return text
