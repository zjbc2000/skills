---
name: evals-builder
description: 搭建 LLM 评估体系（eval）的方法论 skill。触发词："搭建评估体系"、"设计 eval / 写评测"、"怎么评估这个功能/agent/skill"、"评估管线怎么建"、"评测环节还能优化什么"、"加 CI 门禁 / 回归测试"、"评估指标怎么选"。把 LLM-as-judge 打分系统做成可回测、可校准、可 CI 门禁的评估管线，按 7 步推进：调研同类项目 → 固化评分契约 → 量化标注噪声 → 指标选型 → 测试器 → 定期执行 → 小样本纪律。其他 skill 需要给自己的输出建回归评估时也可引用本 skill。
---

# 搭建 LLM 评估体系（evals-builder）

> 把"LLM 打分"从 stochastic 变成可预测。核心是**锚**：评估体系的每个环节都锚在一个可验证的东西上——锚定契约（LLM 输出有校验）、锚定真值（人工标注可量化噪声）、锚定 judge（LLM 裁判周期性对人类校准）、锚定阈值（用真实标注数据扫，不拍脑袋）、锚定门禁（每次提交的便宜绊线）。
> 遵循单一真源：方法论的深材料在 `references/`，本文件只放步骤主线与完成判据，按需加载。

## 何时用

- 给一个 LLM 功能 / agent / skill 建评估（eval），或回答"怎么评估 / 评测还能优化什么"
- 已有打分逻辑但没法回测、指标只到 pass/fail、阈值拍脑袋定、judge 没校准过
- 需要把评估接进 CI 门禁或定期执行脚本

## 主线：7 步，每步一个可核查的完成判据

> 顺序不可跳。先建度量再动打分器，先量化噪声再信任何数字。
> 判据全部"可核查"：能明确判断"做完 vs 没做完"。做完一项再进下一项（防 premature completion）。

### 1. 调研同类项目

先看别人怎么做，不重复造轮子。用联网搜索 + GitHub 代码搜索：

- 找 ≥3 个可比实现/论文/框架：同类打分系统、成熟 eval 框架（promptfoo / DeepEval / Ragas / Langfuse / OpenAI Evals）、行业基准与数据集。
- 每个候选记录：它做什么、评分量纲、ground truth 怎么来、已知缺陷。
- 产出调研注记，写进 `references/` 或项目自己的 docs/。

**完成判据**：写下 ≥3 个可比系统的调研注记，且每个注记含"评分量纲 / 真值来源 / 已知缺陷"三要素；据此圈定本项目的指标集初稿（可改）。

### 2. 锚定评分契约

LLM 与确定性引擎之间必须有一条**校验过的 JSON 契约**——这是整个评估体系的承重墙：

- 契约形态（模板见 `templates/eval-contract.json`）：每条目 `{分数, 证据 evidence, 原文引用 quotation}`，分数有明确量纲（如 bonus 0-3，每档有行为描述）。
- 给契约写校验器：非法输出（越界分数 / 缺证据 / 缺引用）必须被拒绝并触发纠正性重试，而不是静默接受。
- 做一个 fixture 证明"契约 + 校验器"能跑通。

**完成判据**：LLM 输出契约有配套校验器；造一个合法 fixture + 一个非法 fixture，非法者被拒。

### 3. 锚定真值：量化标注噪声

评估的 ground truth 是自己的标注——先量化它有多噪声，否则后面所有数字不可信：

- 每条标注带 `confidence`（0-1）。
- 有第二人（或隔期重标）→ 报 Cohen's kappa（二元）+ QWK（序数分）一致性。
- 单人标注 → 明确写出"未校验"caveat，并至少做一次抽样重标自检。
- 度量脚本见 `scripts/judge_validate.py`。

**完成判据**：标注带置信度；双标注给出 kappa/QWK 数字，单人标注则文档明写未校验。

### 4. 指标选型

指标族全景见 `references/metrics-taxonomy.md`。对"打分系统"的 table-stakes：

- 混淆矩阵 + 精确率/召回率/F1（per-verdict）
- 序数一致性 QWK（per-score，与标注分比）——只到 pass/fail 会漏掉"方向对但分差大"
- 逐指标区分度（发现哪个指标没干活）
- 证据/引用准确率（faithfulness 的确定性版）
- 每个**比例类指标必须带置信区间**（Wilson / bootstrap，见 `scripts/metrics.py`）
- 行业相关指标包：`references/metric-packs.md`（简历 / 客服 / 内容审核）

**完成判据**：指标清单带理由；每个比例类指标确认配了置信区间。

### 5. 测试器：完整执行评估

把评估做成可重复执行的 CLI（`scripts/run_evals.py` 模板）：

- 输入标注数据集（JSONL）→ 输出结构化 JSON（数据侧）+ 自包含 HTML 报告（用户侧，`templates/report.html`）
- 支持 `--threshold` pass-rate 门禁，低于阈值 exit 非 0（CI 可用）

**完成判据**：`run_evals` 在数据集上出 JSON + HTML，门禁 exit code 生效。

### 6. 定期执行 + 周期校准

**CI gate ≠ eval**。两条腿都要：

- **门禁（gate）**：每次提交跑便宜小集（20-50 条代表子集），用 `templates/ci-*.yml` 三套模板（promptfoo / DeepEval / Langfuse）。
- **eval（深度测量）**：周期跑全量 + **judge 校准**——抽线上 traces → 人工标注 → 与 judge 算 kappa → 低于阈值告警。judge 本身要周期性对人类校准，绿门禁不等于评估有效。
- 排程脚本：`scripts/periodic_eval.sh`（cron / workflow_dispatch）。

**完成判据**：cron/CI 模板接上；`judge_validate` 能跑出 kappa 并在低于阈值时告警。

### 7. 小样本纪律（10-50 条起步）

- 10-50 条标注就够起步（来自真实失败的样本，质量 > 数量）。
- 但指标必须带置信区间：n=50、acc≈0.8 时 CI ≈ ±0.12；n<30 时**逐条 case review 比任何汇总数字可信**。
- 阈值扫描只给"建议区间 + 样本级列举"，不输出单点精确值（防过拟合到小样本噪声）。

**完成判据**：数据集 ≥10 条已标注；报告带置信区间；n<30 时附逐条 case review 记录。

## 产出物清单

| 文件 | 作用 |
|---|---|
| `references/eval-loop.md` | canonical eval-loop 词汇 + grader 三族 + pass@k/pass^k |
| `references/metrics-taxonomy.md` | 指标族全景 + 置信区间公式 + QWK 局限 |
| `references/metric-packs.md` | 行业指标包：简历 / 客服 / 内容审核 |
| `references/worked-example.md` | resume-screening 完整案例（抽象成 8 个通用模块） |
| `scripts/metrics.py` | Wilson / Clopper-Pearson / QWK / kappa / bootstrap / 混淆矩阵 |
| `scripts/run_evals.py` | 测试器 CLI（JSON + HTML + 门禁） |
| `scripts/threshold_scan.py` | 阈值扫描（建议区间 + 样本级列举） |
| `scripts/judge_validate.py` | judge 校准（kappa/QWK + 告警） |
| `scripts/periodic_eval.sh` | 周期执行包装 |
| `templates/eval-contract.json` | LLM 输出契约模板 |
| `templates/ci-promptfoo.yml` / `ci-deepeval.yml` / `ci-langfuse.yml` | 三套 CI 门禁模板 |
| `templates/report.html` | 自包含 HTML 报告模板 |
| `.mcp.json` | 可选：promptfoo MCP（调研确认一等公民） |
| `examples/` | 示例标注数据集（10 条，可跑通全链路） |

## 维护

- 本 skill 的方法论与脚本遵循"单一真源"：脚本只此一套，CI 模板与文档按需引用不复制。
- 来源：方法论的每一条都有一手出处，见各 references 文件内的引用；完整调研报告见 `../resume-screening/docs/research/`。
