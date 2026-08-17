"""从注册表元数据生成能力列表 Markdown（docs/capabilities.md）。"""
from __future__ import annotations

from typing import List

from ..config import AppConfig

MAINTENANCE_BLOCK = (
    "> **Agent 维护规则**：本文件由 agent 维护。\n"
    "> 版本 V0.x，每次用户可见变更末位 +1；major 仅当用户明确要求。\n"
    "> HISTORY.md 只增不减；文档/代码变更须同步 HISTORY 并 bump 版本。"
)


def render_capabilities(cfg: AppConfig) -> str:
    lines: List[str] = [
        "# Capabilities — 模型/工具能力列表",
        "",
        MAINTENANCE_BLOCK,
        "",
        "> 本文件由 `scripts/gen_capabilities_doc.py` 从注册表自动生成，勿手改。",
        "",
        "## 模型",
        "",
        "| Provider | 模型 | Base URL |",
        "|---|---|---|",
    ]
    for pname, pcfg in cfg.providers.items():
        url = pcfg.get("base_url", "")
        for m in pcfg.get("models", []):
            lines.append(f"| {pname} | {m} | {url} |")
    default = cfg.default
    lines += ["", f"默认模型：`{default['provider']}/{default['model']}`"]

    doc_loader = cfg.doc_loader or {}
    lines += ["", "## 工具", "", "- doc_loader 主力：`{0}`".format(doc_loader.get("primary", "—"))]
    fallback = doc_loader.get("fallback", [])
    if fallback:
        lines.append("- doc_loader 降级链：" + ", ".join(f"`{f}`" for f in fallback))
    return "\n".join(lines) + "\n"
