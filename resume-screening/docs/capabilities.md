# Capabilities — 模型/工具能力列表

> **Agent 维护规则**：本文件由 agent 维护。
> 版本 V0.x，每次用户可见变更末位 +1；major 仅当用户明确要求。
> HISTORY.md 只增不减；文档/代码变更须同步 HISTORY 并 bump 版本。

> 本文件由 `scripts/gen_capabilities_doc.py` 从注册表自动生成，勿手改。

## 模型

| Provider | 模型 | Base URL |
|---|---|---|
| ark_coding | deepseek-v4-flash | https://ark.cn-beijing.volces.com/api/coding/v3 |
| ark_coding | doubao-seed-2.0-lite | https://ark.cn-beijing.volces.com/api/coding/v3 |
| deepseek_official | deepseek-v4-flash | https://api.deepseek.com |
| deepseek_official | deepseek-v4-pro | https://api.deepseek.com |

默认模型：`ark_coding/deepseek-v4-flash`

## 工具

- doc_loader 主力：`layout_parsing`
- doc_loader 降级链：`local_pymupdf`, `local_paddleocr`
