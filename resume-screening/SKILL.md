---
name: resume-screening
description: 筛简历 skill。加分制（通用分 G / 特定分 S / 总分 T）评分 + 红线一票否决；配套评估 pipeline 用个人标注数据回测、阈值扫描校准。触发词："筛简历"、"评估简历筛选"、"跑评估"。本地 CLI 或经服务器 API 编排。
---

# 筛简历 Skill

> **Agent 维护规则**：本文件由 agent 维护。
> 版本 V0.x，每次用户可见变更末位 +1；major 仅当用户明确要求。
> HISTORY.md 只增不减；文档/代码变更须同步 HISTORY 并 bump 版本。

## 概述

对一份简历（PDF）按岗位要求打分判定。加分制三类指标：通用（项目 / 技术栈 / 亮眼经历）、特定（岗位 + 技能要求，由 jd_map 派生）、通用+特定（双闸门：`G ≥ 通用阈值 且 T ≥ 总分阈值`）。红线命中一票否决。每项加分带 `quotation`（原文引用）并经后置校验（exact/fuzzy/missing）。评估 pipeline 用个人成功/失败标注数据回测 skill 本身。

规格：[docs/spec/SPEC.md](docs/spec/SPEC.md)（单一真源）。

## 模式一：筛简历

**输入**：简历 PDF + 岗位 key（jd_map）+ 指标类型（模式）。

**过程**（本地）：

```bash
python -m backend.cli.screen <简历.pdf> --jd <岗位key> [--mode general|specific] [--llm fake|real]
```

- `--llm fake`：本地无凭据跑通（开发/测试）
- `--llm real`：真实模型（.env 配置，layout-parsing + deepseek-v4-flash）
- 经服务器 API：`POST /screen`（multipart file + `jd` + `mode`，头 `X-API-Key`）

**输出**：
- 用户侧：控制台一行 `verdict= G= S= T= mode= loader=`（或 API JSON）
- 数据侧：`datasets/manifest.jsonl` 追加一条记录（含 score_snapshot + quotation 校验标签）

## 模式二：跑评估

**输入**：标注数据（datasets/ 的 manifest.jsonl）。

**过程**：

```bash
python -m backend.eval.run_eval --datasets <dir> [--html out.html] [--json out.json]
```

或经 API：`GET /eval`（头 `X-API-Key`）。

**输出**：
- 用户侧：自包含 HTML 报告（混淆矩阵 / 指标 / 阈值扫描 / 单指标区分度）
- 数据侧：JSON（逐条 verdict vs ground truth，供迭代）

## 配置（.env）

复制 `.env.example` 为 `.env`：`ARK_API_KEY` / `DEEPSEEK_API_KEY` / `LAYOUT_PARSING_URL` / `LAYOUT_PARSING_TOKEN` / 飞书三项 / `X_API_KEY` / `RESUME_DEFAULT_JD`。

## 维护

- 版本与文档纪律见 [AGENTS.md](AGENTS.md) 与 [HISTORY.md](HISTORY.md)
- 模型/工具能力列表见 [docs/capabilities.md](docs/capabilities.md)（自动生成，勿手改）
