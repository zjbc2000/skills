# 美团《Agent 评测白皮书》系列 01 对当前 Skill 的影响

## 来源与读取说明

- 原文：[《Agent 评测白皮书》系列01：Agent 评测全览](https://mp.weixin.qq.com/s/hBSIPQnsBeWwX9UZLjWYFA)，美团技术团队，页面时间戳 `1789007040`（2026-09-10 10:24 CST）。
- 本次使用移动端 WeChat UA 读取原始公开 HTML；普通桌面访问会显示“环境异常，完成验证后即可继续访问”。以下结论仅来自原文正文，不依赖搜索摘要。

## 文章要点

文章用“**四个模块、三种能力、两条 Loop、一套资产**”概括 Agent 评测：离线评测守住已知问题；在线评测与监控发现未知问题；Case 挖掘与归因连接问题发现、修复和评测集；观测基建提供证据。两条 loop 分别是 Agent 迭代（归因 → 修复 → 回测 → A/B）和评测体系迭代（新增 case、校准 metric/rubric、更新评测集）。

与本项目最相关的具体主张：

- 长程 Agent 应同时评最终环境状态和关键行为/路径；端到端集回答“是否办成”，过程集回答“哪一步出错”。
- 固定样本、评标器和尽量生产等价的执行环境，结合多 trial / pass@k，才可比较候选与基线。
- 安全和准确性可一票否决；门禁必须接到实际变更/发布流程。
- 线上反馈、监控、规则和随机采样应成为新 case 的来源；Bad case 需归因后再沉淀，且 rubric 本身也要接受校验，避免优化成迎合评测。
- 文章明确提醒“全景图是终局，不是起点”。

## 建议采纳的最小改动

| 建议改动 | 积极影响 | 精确落点 | 为什么不是 scope creep |
| --- | --- | --- | --- |
| 给每个 case 增加 `evaluation_scope: e2e | process` 与 `gate_tier: must_pass | challenge`；仅在目标含有可观察过程或风险不均时要求使用。 | 把“任务完成”与“故障定位”分开，且避免用总体均分掩盖安全/准确性故障。 | [eval-set-lifecycle.md](optimization-orchestrator/references/eval-set-lifecycle.md) 的 `Case contract` 与 `Splits and evolution`；[SKILL.md](eval-design/SKILL.md) 的 `Required output`。 | 是现有 case schema 与 hard-gate 原则的两个枚举字段，不增加新的 specialist、runner 或平台。 |
| 将执行环境保真度和最小可归因证据加入 preflight/manifest：声明 `fidelity`（生产等价、受控仿真或未知）、与生产差异；对多步目标至少保留完整 I/O、工具/Skill 调用和最终状态。 | 让比较结果更能迁移到真实使用，并让 Bad case 可复现、可归因；也能区分工程故障与 target 回归。 | [SKILL.md](eval-execution/SKILL.md) 的 `Preflight`、`Run and record`；[state-contract.md](optimization-orchestrator/references/state-contract.md) 的 `run_manifest`。 | 只补充已要求的环境指纹和 raw trajectory evidence，不规定 MLflow、trace backend 或线上监控系统。 |
| 在 `regression_candidate` 的进入条件增加结构化“case intake”：来源（用户反馈/监控/规则/抽样）、原始证据、影响 slice、初步归因，以及“rubric/ground truth 是否已复核”。 | 将“线上未知问题 → 可审核回归 case”做成可审计闭环，减少把噪声或错误 rubric 固化进 benchmark 的风险。 | [eval-set-lifecycle.md](optimization-orchestrator/references/eval-set-lifecycle.md) 的 `Splits and evolution`；[SKILL.md](experiment-compare/SKILL.md) 的 `Failure analysis`。 | 扩展的是已有的 `provenance` 和“审核后晋级”流程；不创建独立的在线 Case-mining specialist。 |
| 在接受 Gate 的交接产物中要求可执行的 `promotion_evidence`：比较报告、硬门禁结果、绑定版本，以及供既有 CI/CD 或变更流程消费的结论。 | 落实“没有接入流程的门禁只是建议”，使 Gate 2 的证据可真正阻止不合格候选进入后续变更/发布流程。 | [SKILL.md](optimization-orchestrator/SKILL.md) 的 `Run the loop` 第 6 步与 `Guardrails`；[state-contract.md](optimization-orchestrator/references/state-contract.md) 的 `comparison_report`。 | Orchestrator 仍不实现 CI/CD 或发布；只定义把已有判断交给既有 workflow 的最小契约。 |
| 将线上验证定义为**可选的接受后观测**：当 target 已有安全合规的监控/影子/A/B 能力时，记录线上结论，并将可信 Bad case 回流到 `regression_candidate`；它不应成为当前离线 loop 的必经状态。 | 补上文章“离线守已知、在线发现未知”的盲区，同时不阻塞无线上系统的 Skill/Agent 优化。 | [SKILL.md](optimization-orchestrator/SKILL.md) 的 terminal policy 后增加非阻塞 `post-acceptance observation`；[eval-set-lifecycle.md](optimization-orchestrator/references/eval-set-lifecycle.md) 的来源说明。 | 不新建 online-eval specialist，不改变 `accepted` 的终态，也不把监控平台纳入本项目依赖。 |

## 已有设计已覆盖、无需重复添加

- 不可变 `eval_set`、benchmark/holdout、回归样本先审核后晋级：已在 `eval-set-lifecycle.md`。
- baseline/candidate 的受控比较、重复执行、pass@k 可作为 Skill 指标：已在 `metric-design.md`、`eval-execution` 和 `experiment-compare`。
- 安全、越权、拒答等硬门禁不可被平均分抵消：已在 `state-contract.md`、`metric-design.md`。
- 保留 raw per-case 与 trajectory/tool evidence：已在 `eval-execution/SKILL.md`。
- “归因 → 最小可证伪候选 → 回测 → 比较”的 Agent 迭代 loop：已在 Orchestrator 状态机。

## 明确不采纳的文章观点

| 不采纳项 | 原因 |
| --- | --- |
| 将四模块完整实现为一个统一评测平台（在线监控、Case 挖掘、观测基建、离线评测）。 | 这会吞掉 specialist 的能力并把 Skill 扩张为平台；当前目标是编排可复用的已有能力。 |
| 强制每个 target 都接入线上 A/B、影子流量和持续监控。 | Skill、离线 Agent 或有副作用的系统节点未必具备安全可用的线上路径；会把不可得基础设施误判为评测失败。 |
| 强制每个 case 同时拥有端到端和过程标签。 | 对纯函数、检索器或无可观测过程的目标无收益；采用条件化字段即可。 |
| 自动把所有线上 Bad case 直接写进 benchmark。 | 文章也强调归因与 rubric 校验；当前不可变/审核机制应继续防止噪声污染持续指标。 |
| 新增第四个“观测/Case 挖掘 specialist”。 | 目前只需在 Design、Execution、Compare 的 artifact contract 中增加入口；单独 specialist 没有足够独立职责。 |
