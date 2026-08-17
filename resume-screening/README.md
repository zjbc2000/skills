# 筛简历 Skill（resume-screening）

> **Agent 维护规则**：本文件由 agent 维护。
> 版本 V0.x，每次用户可见变更末位 +1；major 仅当用户明确要求。
> HISTORY.md 只增不减；文档/代码变更须同步 HISTORY 并 bump 版本。

## 背景

个人简历筛选工具：用加分制（通用分 / 特定分 / 红线）对简历打分，输出判定。配套评估 pipeline，用个人成功/失败数据集回测 skill 自身，持续校准阈值与指标。

## 当前版本

**V0.3** — layout-parsing 接入 + .env 凭据加载，真实链路可跑。

## 功能

- **筛简历（v0.3 可用）**：`python -m backend.cli.screen <简历.pdf> --jd <岗位key>` —— 三模式评分（通用 / 特定 / 通用+特定）、双闸门判定、红线一票否决、quotation 原文引用、manifest 落库；凭据从 `.env` 加载；`--llm fake` 本地无凭据跑通
- **文档解析**：layout-parsing 远程主力（POST PDF→Markdown）→ pymupdf 直读 → paddleocr 兜底
- **评估 pipeline**：batch 回测 + 自包含 HTML 报告 + 阈值扫描（规划中）
- **飞书集成**：群聊 @bot 发简历（含压缩包）→ 自动筛 → 纯文本回复（规划中）
- **AE 工作台**：react 极客风界面（规划中）

详见 [HISTORY.md](HISTORY.md) 版本迭代，[docs/spec/SPEC.md](docs/spec/SPEC.md) 完整规格，[AGENTS.md](AGENTS.md) 维护指引。
