# eval-loop: 评估回路词汇表与 grader 三族

> 来源：Anthropic《Demystifying evals for AI agents》(anthropic.com/engineering/demystifying-evals-for-ai-agents) 与 OpenAI Evals 文档，二者术语同源。完整调研见 ../resume-screening/docs/research/eval-methodology-skill-research.md §1。

## canonical eval-loop

一次评估的标准结构（所有主流框架对齐）：

```
task → trial（多次采样）→ grader（可多个，各含多个 assertion/check）→ transcript（轨迹）→ 聚合指标 → 报告/门禁
```

| 环节 | 含义 | 好坏的判据 |
|---|---|---|
| **task** | 一个带输入 + 成功标准的测试用例 | 好 task：两个领域专家能独立给出同样的 pass/fail；task 含糊 = 指标里的噪声 |
| **reference solution** | 一个已知能通过全部 grader 的参考输出 | 证明 task 可解、grader 配置正确 |
| **trial** | 对同一 task 的一次尝试 | 模型有方差 → 多次 trial 取一致 |
| **grader** | 对某一面打分的逻辑，含多个 assertion | 见下表三族 |
| **transcript** | 一次 trial 的完整记录（输出/工具调用/中间结果） | 可审计；是"逐条 case review"的原料 |
| **聚合** | 组合 grader 分数 | weighted（加权过阈值）/ binary（全过）/ hybrid |
| **报告/门禁** | 输出指标 + 是否拦截 | 指标带置信区间；门禁只作便宜绊线 |

> 映射示例（resume-screening）：manifest = transcript；schema + quotation 校验 = code-based grader 的 assertions；rubric JSON 契约 = model-based grader；metrics 聚合 = reporting。

## grader 三族

| 族 | 方法 | 优点 | 缺点 |
|---|---|---|---|
| **Code-based（确定性）** | 字符串/regex/fuzzy 匹配、fail-to-pass 测试、静态分析、结果校验、工具调用校验 | 便宜、客观、可复现、易调试 | 抓不到开放任务的质量 |
| **Model-based（LLM-as-judge）** | rubric 打分、自然语言断言、两两对比、reference-based、多 judge 共识 | 灵活、能处理开放输出 | 非确定、贵、**必须与人类校准** |
| **Human** | SME 评审、抽样 spot-check、inter-annotator agreement | 黄金标准、校准 LLM grader | 贵、慢、需专家 |

官方准则：**能确定性就确定性**（OpenAI Evals 原话："Wherever Basic Templates can work, avoid Model Graded Templates"）。LLM grader 要与人类校准到小分歧后才可减少人工评审。

## 抗非确定性：pass@k vs pass^k

- **pass@k**：k 次 trial 至少一次成功——适合"一次成功就够"的工具场景。
- **pass^k**：k 次全部成功——适合"每次都要稳定"的客服/打分场景。75%/trial 时跑 3 次全过的概率只有 42%。
- 打分系统属"一致性敏感"，应报告 pass^k 或多次采样均值 ± 方差。

## 判据细节

- **加权聚合**：组合 grader 分数必须过 threshold（如 promptfoo 的 `namedScores` 加权 → `threshold`）。
- **judge 校准**：judge 输出 vs 人工标注报 kappa/ICC，周期性重验（judge 会 drift）。见 scripts/judge_validate.py。
- **不要单侧 eval**：只测 should 不测 shouldn't → 单侧优化。正反都要测。
