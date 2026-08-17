"""远程 layout-parsing 文档解析（SPEC §5.3 主力）。

契约（已实测）：POST JSON `{"file": "<base64 编码的 PDF>"}` +
`Authorization: Bearer <token>`；响应 `result.layoutParsingResults[].markdown.text`
为结构化 Markdown 文本（多页拼接）。凭据走 .env。
"""
from __future__ import annotations

import base64
import os

import requests

from .base import LoaderError

TIMEOUT_SECONDS = 60


def extract_text(path) -> str:
    url = os.environ.get("LAYOUT_PARSING_URL")
    token = os.environ.get("LAYOUT_PARSING_TOKEN")
    if not url or not token:
        raise LoaderError("缺少 LAYOUT_PARSING_URL / LAYOUT_PARSING_TOKEN（.env）")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
    except OSError as e:
        raise LoaderError(f"无法读取文件: {path}: {e}") from e
    try:
        resp = requests.post(
            url, headers=headers, json={"file": encoded}, timeout=TIMEOUT_SECONDS
        )
    except requests.RequestException as e:
        raise LoaderError(f"layout-parsing 请求失败: {e}") from e
    try:
        body = resp.json()
    except ValueError:
        body = {}
    if resp.status_code != 200 or body.get("errorCode") != 0:
        detail = body.get("errorMsg") if isinstance(body, dict) else resp.text[:200]
        raise LoaderError(f"layout-parsing 返回 {resp.status_code}: {detail}")
    texts = []
    for item in body.get("result", {}).get("layoutParsingResults", []):
        md = item.get("markdown") if isinstance(item, dict) else None
        t = md.get("text") if isinstance(md, dict) else None
        if isinstance(t, str) and t.strip():
            texts.append(t.strip())
    text = "\n".join(texts).strip()
    if not text:
        raise LoaderError("layout-parsing 未提取到文本")
    return text
