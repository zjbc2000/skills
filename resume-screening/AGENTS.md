# AGENTS.md — 给 agent 维护者的指引

> **Agent 维护规则**：本文件由 agent 维护。
> 版本 V0.x，每次用户可见变更末位 +1；major 仅当用户明确要求。
> HISTORY.md 只增不减；文档/代码变更须同步 HISTORY 并 bump 版本。

## 模块总览

本项目分两个模块：

### 模块 A：开发者工具（筛简历产品）

- **筛简历 skill**（`SKILL.md`）：Claude Code 入口，编排后端，两模式（筛简历 / 跑评估）
- **backend/**：python 评分管线（doc_loader → llm → scoring → manifest），注册表驱动（config yml + 统一接口）
- **web/**：react AE 工作台（v0 本地）
- **规格**：[docs/spec/SPEC.md](docs/spec/SPEC.md) —— 一切实现的单一真源
- **能力列表**：[docs/capabilities.md](docs/capabilities.md) —— 由注册表自动生成，勿手改

### 模块 B：项目维护工程 skill

- 版本与文档纪律：见下方「版本规则」与每个文档头的维护规则块
- 变更流程：改代码/文档 → 更新 HISTORY → bump 版本 → Conventional Commits

## 快速开始

```bash
pip install -r requirements.txt
python -m backend.cli.screen <简历.pdf> --jd <岗位key> --llm fake
pytest
```

## 版本规则

- 版本号 **V0.x**，每次用户可见变更**末位 +1**（V0.1 → V0.2 → …）
- major 仅当**用户明确要求**时才 bump
- **不使用** `update` skill 的 SemVer 语义
- HISTORY.md **只增不减**，禁止改写历史条目

## 开发纪律

- 测试先行（TDD），核心逻辑用 fake LLM，无网络依赖
- 外部凭据只走 `.env`（见 `.env.example`），绝不硬编码
- 改完跑 `pytest`，提交信息用 Conventional Commits
