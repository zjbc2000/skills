# Optimization Orchestrator：一手资料调研（2026-09-10）

## 结论摘要

这五个项目共同支持一个清晰的拆分：**Eval Design** 产出“测什么、为何测、何为通过”的可审查规格；**Eval Execution** 将规格绑定到某个运行时并产出可追溯的原始运行证据；**Experiment & Compare** 消费多个结果，判断变化、归因并提出下一轮实验。Orchestrator 不应复刻任一评测器的扫描、执行或判分逻辑；它应保存规范化状态、检查前置条件、选择 specialist，并在 gate、人工复核和停止条件之间推进。

这是从各项目的官方仓库和官方文档得出的架构推论，而非它们所声明的共同 API。

## Capability matrix

| 项目 | 主要能力与工作流 | 具体输入 | 具体输出 / 证据 | 对三类 specialist 的启示 |
| --- | --- | --- | --- | --- |
| [MLflow agent-evaluation skill](https://github.com/mlflow/skills/blob/main/agent-evaluation/SKILL.md) 与 [MLflow GenAI Evaluation](https://mlflow.org/docs/latest/genai/eval-monitor/running-evaluation/eval-examples/) | 用原生 `mlflow.genai.evaluate(data, predict_fn, scorers)` 运行评测；数据集、trace 与 scorer 保存在同一实验体系中。内置、规则、LLM、自定义代码与 trace/trajectory 评测器可组合。 | 已 trace 的 agent / callable `predict_fn`；含 `inputs` 和可选 `expectations` 的版本化 dataset、字典列表或 DataFrame；scorers。`predict_fn` 参数须与 `inputs` 对齐，或由 wrapper 适配。 | evaluation run、聚合指标、每行 trace/assessment；scorer 以 `Feedback(name, value, rationale, metadata, error)` 表达评定。[Scorer contract](https://mlflow.org/docs/latest/genai/concepts/scorers/) | **Execution** 的首选后端：负责 trace readiness、dataset/predict adapter/scorer binding、dry run、运行和持久化。**Compare** 只读其 run/trace；**Design** 不直接编写 MLflow 调用。 |
| [Microsoft eval-guide](https://github.com/microsoft/eval-guide) | 10-step 方法论被实施为 Discover → Plan → Generate & Baseline → Run → Interpret & Improve；按 prompt/RAG/agentic 架构决定需测深度，并把 capability 与 trust & safety 分开。 | Agent 描述或真实 Copilot Studio 配置；规划 workbook；单轮/多轮需求；随后是 live-agent results CSV 或摘要。前 0–2 阶段不要求运行中的 agent。 | Agent Vision、风险层级与 owner；带 gates 的 workbook/HTML review；单轮 CSV 或多轮 conversation blueprint；SHIP/ITERATE/BLOCK、失败根因与改进方案。[README stages](https://github.com/microsoft/eval-guide/blob/main/README.md) | 最贴近 specialist 划分的模板：Discover/Plan/Generate → **Design**；Run → **Execution**；Interpret/Triage → **Experiment & Compare**。每个 dashboard 确认点应成为 orchestrator 的 `awaiting_review`。 |
| [AWS sample-agent-skill-eval](https://github.com/aws-samples/sample-agent-skill-eval) | Skill 层面的静态 audit、functional with/without-skill、trigger precision、cost Pareto、snapshot/regression/lifecycle 与统一 report。核心 audit 路径无需 agent，functional/trigger/compare/report 需 agent runner。 | skill directory；`evals/evals.json`（`id`、`prompt`、`assertions`、可选 fixtures）；`eval_queries.json`（`query`、`should_trigger`）；可选 `.skilleval.yaml` 规则/阈值。 | Finding/score/grade；`benchmark.json`；trigger 结果；baseline snapshot/regression；加权统一分数（audit 40%、functional 40%、trigger 20%）。[SKILL contract](https://github.com/aws-samples/sample-agent-skill-eval/blob/main/SKILL.md) | 适合 **Execution**（结构/安全/触发/功能测试）和 **Compare**（baseline/regression/Pareto）。它的固定统一权重不应被 Orchestrator 设为通用跨域 policy。 |
| [tardigrde/agent-skill-eval](https://github.com/tardigrde/agent-skill-eval) | 在真实 Codex、Claude Code、OpenCode CLI harness 中，以 fresh workspace 运行；baseline、重复运行/pass@k、state-delta + LLM rubric grading、预算 guard、hooks、re-grade、iteration compare。 | skill path；schema 校验过的 `evals.json`；目标 agent/model；fixtures；可选 source repo、side-effect level、budget、hooks、`--runs`。case 可声明 `should_trigger` 和 `force_skill_invocation`。 | 每次运行的 pre/post state、logs、`grading.json`、`timing.json`、`run_meta.json`、`summary.json`、`benchmark.json`、progress JSONL；iteration compare 给出 pass/time/token delta。[README workflow and schema](https://github.com/tardigrde/agent-skill-eval/blob/main/README.md) | **Execution** 的真实 harness 选择；**Compare** 消费 iteration 结果。Orchestrator 应将 side-effect level、budget、固定 model/reasoning config 视为 run preconditions，而非把它们隐藏在 prompt 中。 |
| [NVIDIA SkillEvaluator](https://github.com/NVIDIA/SkillEvaluator) | 三个可独立运行的 tier：Tier 1 validation（schema/quality/security/PII/lint/rubric），Tier 2 semantic dedup/context optimization，Tier 3 synthetic dataset + sandboxed live agent eval + compare；`--full` 可串联并以 gate 控制。 | skill directory；Tier 1 checks；Tier 2 embedding/chat provider；Tier 3 provider、agent credential、Docker/local/cloud sandbox 与 accepted eval source。 | validation evidence，overlap/context findings，生成的 `evals/evals.json`，Tier 3 agent-eval report 与 comparison。Tier 1 强制 gate；Tier 2 默认 gate 可改为 advisory；Tier 3 默认 advisory，可提升为 exit gate。[README tier/gate behavior](https://github.com/NVIDIA/SkillEvaluator/blob/main/README.md) | **Design** 可请求 dataset synthesis，**Execution** 可请求 validation/live eval，**Compare** 可解释 dedup 与 comparison。它说明 gate policy 必须属于 Orchestrator 的显式状态，而不是每个 specialist 自行决定。 |

## 输入、输出与责任边界

### 1. Eval Design

**输入：** agent/skill 的目标、用户和边界；架构与风险；已知失败；可用证据/ground truth；预算与发布门槛。Microsoft 的 planner 将这些组织为 capability 与 trust-and-safety eval sets、pass-rate target、hard/soft gate、human input、source-to-ground-truth mapping 和 grader-validation note。[Planner contract](https://raw.githubusercontent.com/microsoft/eval-guide/main/skills/eval-suite-planner/SKILL.md)

**输出（建议的 canonical artifact）：** `eval_spec`：版本、目标系统与候选变量、case/fixture、expected behavior、scorer/rubric、风险标签、gate、repetition、side-effect level、预算和数据来源。它应可投影为 MLflow dataset、AWS 的两个 JSON 文件、agent-skill-eval `evals.json` 或 NVIDIA `evals/evals.json`，而不是被某个后端格式反向定义。

**不负责：** 不运行 agent，不把未审核的 LLM 生成用例当作真值，不比较实验结果。MLflow 对 versioned dataset 和可选 expectations 的区分、Microsoft 对 human inputs 的显式要求，均支持该边界。[MLflow datasets](https://mlflow.org/docs/latest/genai/datasets/)

### 2. Eval Execution

**输入：** 已确认的 `eval_spec`、具体 target variant、runner/backend、已解析凭证/环境、预算与并发限制。

**输出（建议的 canonical artifact）：** immutable `run_manifest`（spec/target/runner/model/seed/commit/config）、raw evidence locations、逐 case outcome、metric/assessment、usage/cost/duration、异常、完成状态。MLflow 将结果组织为 run + traces；agent-skill-eval 还记录有效 model/reasoning/harness 配置及逐 run 文件；两者都说明“只有 aggregate score”不足以支持后续归因。[MLflow results](https://mlflow.org/docs/latest/genai/eval-monitor/faq/)；[ASE artifacts](https://github.com/tardigrde/agent-skill-eval/blob/main/README.md)

**不负责：** 不自行改变 acceptance gate、也不根据一次分数直接修改 skill。可执行的 failure（缺 agent CLI、无凭证、schema 无效、预算超限、tool/scorer error）应返回结构化 preflight/execution failure，由 Orchestrator 转入修复或停止状态。

### 3. Experiment & Compare

**输入：** 两个或多个兼容的 `run_manifest`/原始证据、比较假设与 gate policy；必要时 previous baseline。MLflow 明确支持对同一数据比较 prompt/model/app logic，agent-skill-eval 的 `compare` 以 iteration 的 pass/time/token delta 为反馈循环，AWS 支持 snapshot/regression。[MLflow datasets use cases](https://mlflow.org/docs/latest/genai/datasets/)；[AWS commands](https://github.com/aws-samples/sample-agent-skill-eval/blob/main/SKILL.md)

**输出（建议）：** `comparison_report`：兼容性检查、指标与置信/重复运行摘要、分组回归、成本质量 trade-off、trace/evidence 链接、根因假设、SHIP/ITERATE/BLOCK 或“证据不足”，以及下一轮最小实验建议。

**不负责：** 不隐式改动 candidate；不把不同 spec、model、dataset、scorer 或 environment 的 run 伪装成因果比较。Microsoft 将“eval setup vs agent quality”作为不同根因，说明先验兼容性和归因都必须显式。[Interpreter contract](https://raw.githubusercontent.com/microsoft/eval-guide/main/skills/eval-result-interpreter/SKILL.md)

## 重叠区：由 Orchestrator 裁决，而非合并 specialist

| 重叠 | 证据 | 归属规则 |
| --- | --- | --- |
| 测试数据生成 | Microsoft Generate、NVIDIA `create-eval-dataset` 与 AWS `init` 都会生成用例/模板。 | **Design** 拥有规范；生成器只能创建 `draft`，必须经 review 才能成为 executable spec。 |
| 安全/静态质量 | AWS audit 与 NVIDIA Tier 1 都会检查安全、结构或质量。 | **Execution preflight** 统一收集 findings；gate 由 Orchestrator policy 决定（例如 critical 阻断、warning 需豁免）。 |
| Functional/trigger/live evaluation | AWS、ASE、NVIDIA Tier 3 与 MLflow 都能执行某类行为评测。 | Execution 根据 target：需要 production trace/LLM observability → MLflow；要 skill static+trigger unified grade → AWS；要真实 coding-agent harness/side effects/repeated trials → ASE；要 NVIDIA verified-skill tier/dedup/sandbox → NVIDIA。 |
| 比较与回归 | MLflow experiment/run，AWS snapshot/regression，ASE iteration compare，NVIDIA compare。 | **Compare** 输出后端无关的结论；后端保留为 evidence provider。只有 spec compatibility 通过才允许比较。 |
| 根因与改进建议 | Microsoft Interpret/Triage 与 MLflow trace review 都可支持诊断。 | **Compare** 产出诊断假设与下一实验；实际改动属于外部 build/change workflow，改动后返回 Design/Execution。 |

## 可直接采用的 routing conditions

| 观察到的请求或 state | Route | 必要 gate |
| --- | --- | --- |
| “我有 agent/skill 想知道怎么测”、目标或风险不清 | Eval Design / discover-plan | 必须形成 success criteria、owner 和 risk before execution。Microsoft Discover 正是从描述启动。[Source](https://raw.githubusercontent.com/microsoft/eval-guide/main/skills/eval-guide/SKILL.md) |
| 已有 agent 描述或已知架构，但没有 eval plan/cases | Eval Design / plan-generate | architecture/risk 决定单轮、多轮、capability 与 T&S 覆盖；人工确认 draft。 |
| 有计划但没有可运行数据集/后端格式 | Eval Design / compile spec | 明确 target runner、ground truth、grader、fixture 和 side-effect level。 |
| 有 spec，要求 score/baseline/验证改动 | Eval Execution | 先做 schema、credential、target、budget、sandbox/side-effect 与 scorer preflight；建议小样本 dry run。MLflow skill 明确使用 dry run 阻止损坏的 tools/scorers 进入完整运行。[Source](https://github.com/mlflow/skills/blob/main/agent-evaluation/SKILL.md) |
| 有两个以上 compatible runs，要求“有没有提升/是否能发布” | Experiment & Compare | run manifest 必须匹配或明确控制 spec、dataset、scorer、target/runtime；不匹配则回到 Design。 |
| result 失败，缺少 trace/证据，或 classifier 判断为 eval-setup failure | Eval Execution / repair evidence | 不先优化被测系统；修复 runner/data/scorer 后重跑。 |
| result 失败且 evidence 完整，存在明确 regression/failure cluster | Experiment & Compare → next experiment proposal | 产生最小可检验 hypothesis；改动后以新 candidate 回到 Execution。 |
| critical security finding、hard T&S gate 失败、预算/side-effect policy 不允许 | Orchestrator terminal/block state | 不把任务交给优化 loop；需要 waiver、scope change 或人工决策。NVIDIA 的 tier gate 策略可作为该策略的参考。[Source](https://github.com/NVIDIA/SkillEvaluator/blob/main/README.md) |

## 给状态机/SKILL.md 的实现约束

1. **状态应由 artifact 完整性驱动。** 最小状态可为 `intake → designing → awaiting_spec_review → ready_to_execute → preflight → running → evidence_ready → comparing → awaiting_decision → iterating | shipped | blocked | cancelled`。Microsoft 的 dashboard-confirm 流程支持明确的 review 状态，而非把确认埋在聊天文本里。[Dashboard behavior](https://github.com/microsoft/eval-guide/blob/main/README.md)
2. **每一次 transition 写 append-only event。** 至少记录 `state_before/after`、route、reason、artifact URI/hash、operator、timestamp；不要让 specialist 直接改全局 state。
3. **将后端专有文件编译/适配到 canonical artifacts。** `eval_spec`、`run_manifest` 与 `comparison_report` 是跨 specialist 的契约；MLflow dataset、AWS JSON、ASE workspace、NVIDIA reports 是 evidence adapters。
4. **比较前检查兼容性。** 至少比较 spec hash、case set、scorer/rubric version、target commit/prompt/model/reasoning、runner、environment、repetition 与预算 policy；不匹配时报告“不可归因”，而非报 winner。
5. **把循环的终止条件写成 policy。** 达到 hard gates 且无阻断 finding → `shipped`；达到最大迭代/预算、证据不足、或需人类权限 → `blocked`/`awaiting_decision`；仅“分数未提升”不足以自动继续无限循环。

## Sources and scope

仅使用项目拥有者的官方 GitHub 仓库、项目 `SKILL.md`/README，及 MLflow/NVIDIA 官方文档；未将博客、第三方评测或搜索摘要作为事实来源。上表中的“建议/归属/状态机”均是基于这些来源对 Optimization Orchestrator 的设计推论。

