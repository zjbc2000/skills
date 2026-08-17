# HISTORY — 版本迭代记录

> **Agent 维护规则**：本文件由 agent 维护，**只增不减**，禁止改写历史条目。
> 版本 V0.x，每次用户可见变更末位 +1；major 仅当用户明确要求。
> 每次变更在本文件新增一条，并 bump 版本号。

## V0.3 — 2026-08-17

### Added
- layout-parsing 远程文档解析接入（实测契约：POST JSON `{"file": base64}` + Bearer；响应 `result.layoutParsingResults[].markdown.text` 多页拼接），作为 doc_loader 主力
- paddleocr 本地兜底模块（未安装时抛 LoaderError 自动降级；需 `pip install paddleocr paddlepaddle` 激活）
- CLI 加载项目根 `.env`（python-dotenv），凭据本地化不硬编码

## V0.2 — 2026-08-17

### Added
- 注册表与统一接口：config（models/tools/thresholds）加载、LLM 客户端（瞬时重试 3 次 / 连续失败降级 / JSON 校验纠正重试 / failed 队列）、capabilities 能力列表自动生成
- 评分引擎：三模式计分、T=G+S 双闸门 AND、红线一票否决、0–3 量纲 schema 校验、系统提示词
- 追踪弹端到端链路：`python -m backend.cli.screen <简历.pdf> --jd <岗位key>`，doc_loader（pymupdf 数字 PDF 直读 + 未实现解析器自动降级）、manifest 落库、jd_map 维度表
- 假 LLM（`--llm fake`）：本地无外部凭据即可跑通全链路

## V0.1 — 2026-08-17

### Added
- 项目骨架与规格固化：docs/spec/SPEC.md（完整设计规格）、AGENTS.md、README.md、.env.example、.gitignore
- 建立版本规则：V0.x 末位 +1，推翻 SemVer；HISTORY 只增不减
