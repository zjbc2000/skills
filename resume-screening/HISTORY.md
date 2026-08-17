# HISTORY — 版本迭代记录

> **Agent 维护规则**：本文件由 agent 维护，**只增不减**，禁止改写历史条目。
> 版本 V0.x，每次用户可见变更末位 +1；major 仅当用户明确要求。
> 每次变更在本文件新增一条，并 bump 版本号。

## V0.14 — 2026-08-17

### Added
- JD 管理页：粘贴 JD 原文 -> LLM 抽取 position/skills/red_lines（可编辑预览）-> 保存注册到 `datasets/jd_map.yml`，保存后岗位下拉框即时可选；`POST /jd/extract` `POST /jd/save`
- 批量筛选：支持多选 PDF/docx 或上传 zip 包（后端解包逐份筛选，单份失败不中断），`POST /screen/batch`
- docx 解析器 `local_docx`（python-docx，段落+表格），加入降级链
- 评测工作台独立菜单页：manifest 记录人工打标（`POST /label`，存 `datasets/labels.json`，manifest 保持 append-only）；指标只算已标注子集；判定按当前阈值从 totals 重算（调阈值无需重筛）；阈值扫描 + 一键回写 `config/thresholds.yml`（`POST /eval/apply-threshold`，支持 `RESUME_CONFIG` 覆盖配置目录）

### Changed
- 前端拆分为三页（筛简历 / JD 管理 / 评测），视图组件移入 `web/src/views/`
- 评测 HTML 报告适配人工标注语义（岗位列 + 标注列）

## V0.13 — 2026-08-17

### Changed
- 移除「通用+特定（双闸门）」模式，仅保留 通用 / 特定 两模式
- 通用模式判定改为 G≥30 且 T≥45；特定模式改为 S≥20（`config/thresholds.yml`）
- 前端 / API / CLI / 飞书 bot 默认模式统一为 `general`

## V0.12 — 2026-08-17

### Changed
- 前后端端口解耦到 `.env`：`API_HOST` / `API_PORT` / `WEB_PORT`；新增 `python3 -m backend.cli.api` 启动器
- 前端 vite 自动从根 `.env` 读 `API_PORT` 派生 `VITE_API_BASE`、读 `WEB_PORT` 设 dev 端口

## V0.11 — 2026-08-17

### Changed
- AE 工作台视觉升级：OLED 暗色 + JetBrains Mono + 运行绿 accent（设计系统）
- 左侧菜单栏（当前仅「筛简历」）+ 底部账号 mock（头像 zed）
- 网络错误提示更清晰（后端未启动时明确提示启动命令）

## V0.10 — 2026-08-17

### Fixed
- `jd_text` 崩溃修复：skills/red_lines 过滤非字符串（防 `{"岗位职责": null}` 脏条目引发 TypeError），技能要求改逐行渲染以保留 JD 章节结构

## V0.9 — 2026-08-17

### Added
- 飞书 bot 消息内按格式指定岗位：@bot 发文本匹配 jd_map key 设岗位（确定性匹配，非模型提取），chat 内 pending 岗位用完即清；未指定则用 `RESUME_DEFAULT_JD`

## V0.8 — 2026-08-17

### Changed
- 前端自动从根 `.env` 注入 `VITE_API_KEY`（无需再建 web/.env）

## V0.7 — 2026-08-17

### Added
- FastAPI 后端（`backend/api/main.py`）：`/health` `/roles` `/screen` `/eval` + X-API-Key 鉴权 + CORS
- AE 工作台（`web/`，react + Vite，极客风暗色）：上传简历 → 选岗位/模式 → G/S/T 明细、评估指标、jd_map 浏览
- SKILL.md 入口：筛简历 / 跑评估两模式，本地 CLI + 服务器 API 编排

## V0.6 — 2026-08-17

### Added
- 飞书 bot 支持压缩包：安全解压（zip-slip 路径穿越防护，`../` 与绝对路径均拦截）→ 逐份筛 → 汇总纯文本回复
- `build_summary` 移入共用管线（pipeline），archive 与 feishu 复用

## V0.5 — 2026-08-17

### Added
- 飞书长连接双向 bot：`python -m backend.cli.bot`（企业自建应用 + WebSocket，订阅 im.message.receive_v1，@机器人 + 发 PDF → 下载 → 筛 → 纯文本回复；chat 白名单；3 秒回执异步化）
- 抽取共用筛简历管线 `screening.pipeline.screen_file`（CLI 与 bot 复用，DRY）
- 统一频道接口 `Channel.notify`（SPEC §5.4）

## V0.4 — 2026-08-17

### Added
- quotation 校验（后置 grep）：exact/fuzzy/missing 三态打标，missing 标记 suspect 保留分数；挂到 CLI 评分后
- 评估 pipeline：`python -m backend.eval.run_eval` —— 混淆矩阵 / 准确率·精确率·召回率·F1 / 引用准确率 / 阈值扫描找最优操作点 / 单指标区分度；JSON（数据侧）+ 自包含 HTML 报告（用户侧）

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
