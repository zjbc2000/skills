# Optimization Orchestrator：源码级拆解

**调研日期：** 2026-09-10。本文固定到列出的 commit；链接均指向该 commit，而不是会漂移的 `main`。只陈述已检查到的实现。`adapter contract` 是基于源码的集成建议，不是上游声明的接口。

## 先纠正原有抽象

这五个项目没有共享的 runtime 协议，也不是五个等价的 "eval execution backend"：

| 项目 | 已验证的实现性质 | 可由 Orchestrator 使用的层 |
| --- | --- | --- |
| MLflow agent-evaluation | 对 MLflow API 的 agent skill 与**代码生成器**；真正执行在安装的 MLflow 包和 tracking server | 运行适配器，外加 dataset/scorer 资产注册 |
| Microsoft eval-guide | 多个 prompt/`SKILL.md` 的方法论工作流；唯一 checked-in runner 仅面向 Copilot Studio DirectLine | 设计/人工 review；可选 Copilot 专用执行器 |
| AWS sample-agent-skill-eval | Python CLI，静态审计、agent-run functional/trigger、snapshot 比较和报告 | skill 专用执行 + 报告适配器 |
| tardigrde/agent-skill-eval | Python CLI + harness；在隔离 workspace 中做 with/without-skill 的重复 agent runs | skill/coding-agent 执行 + compare 适配器 |
| NVIDIA SkillEvaluator | 见下文；不可据 README 假定其与前三者兼容 | 独立适配器，须先核对实际 CLI/schema |

所以 canonical state 不应保存“某后端的总分”，而要保存：冻结的 case/scorer 版本、target variant、runner/config、每 case evidence URI、side effect observation 和该后端原生 artifact URI。

## 1. MLflow `agent-evaluation`

**Repository / revision：** [`mlflow/skills@79d28d61`](https://github.com/mlflow/skills/tree/79d28d61f1edac723c2f2c80ab1795d24bca66c5)。此目录是 skill，不是 MLflow evaluation API 的源码；其实现明确要求调用 `mlflow.genai.*` 原生 API。[SKILL.md](https://github.com/mlflow/skills/blob/79d28d61f1edac723c2f2c80ab1795d24bca66c5/agent-evaluation/SKILL.md)

### 实际调用链

1. `validate_environment.py` / `utils.env_validation.validate_env_vars()` 检查 `MLFLOW_TRACKING_URI`、`MLFLOW_EXPERIMENT_ID`，并在另一校验路径要求 MLflow >= 3.8。[环境实现](https://github.com/mlflow/skills/blob/79d28d61f1edac723c2f2c80ab1795d24bca66c5/agent-evaluation/scripts/utils/env_validation.py)
2. `create_dataset_template.py` 读输入文件，生成一个**新的 Python 脚本**；生成脚本调用 `create_dataset(...)`，把 records 编译为 `[{"inputs": test_case}, ...]`，然后 `dataset.merge_records(records)`。[生成器](https://github.com/mlflow/skills/blob/79d28d61f1edac723c2f2c80ab1795d24bca66c5/agent-evaluation/scripts/create_dataset_template.py)
3. `run_evaluation_template.py` 再生成一个 Python 脚本。该脚本 `get_dataset(DATASET_NAME).to_df()`、`list_scorers(experiment_id=...)`、导入用户指定的模块/函数，并调用 `mlflow.genai.evaluate(data=df, predict_fn=entry_point, scorers=registered_scorers)`。[生成器及生成调用](https://github.com/mlflow/skills/blob/79d28d61f1edac723c2f2c80ab1795d24bca66c5/agent-evaluation/scripts/run_evaluation_template.py)
4. 生成脚本把 `results.eval_results_table` 写到当前工作目录的 `evaluation_results.csv`；聚合 `results.metrics` 只打印到 stdout。MLflow run、trace、assessment 的持久化逻辑在外部 MLflow 包/配置的 tracking backend 中，不在本仓库。

### 真正输入、输出、隔离语义

| 项 | 代码事实 |
| --- | --- |
| 输入 schema | dataset creator 接受 JSON `list[dict]`（每个 dict 是 agent entrypoint 的 keyword inputs）或逐行纯文本（转换为 `{"query": line}`）。生成 dataset record 时仅包装为 `{"inputs": tc}`；模板没有 `expected_output`、risk tag 或 side-effect 字段。 |
| execution precondition | 环境变量、已有 experiment、可导入 `--module` / `--entry-point`、entrypoint 参数名等于 dataset `inputs` keys、已注册 scorer。缺一则 `sys.exit(1)`。 |
| 输出 | MLflow server 中的 dataset/run/traces/assessments（由 MLflow API 管理）+ 本地可覆盖的 `evaluation_results.csv`。没有 manifest、case-level filesystem snapshot 或 retry record。 |
| side effect / retry / isolation | `predict_fn` 在当前 Python process 执行；模板没有 sandbox、timeout、重试或 cleanup。`merge_records` 会写 remote/local tracking store，且已有 dataset 走 load-then-merge，非 immutable snapshot。 |

### Generic adapter contract

`MlflowAdapter.execute(request)` 应要求 `(tracking_uri, experiment_id, dataset_ref_or_records, predict_import_ref, scorer_refs)`；在启动前读取 dataset 的 `inputs` key set、验证 callable signature 和 scorer 可加载性。返回值至少应规范化为 `RunEvidence { backend="mlflow", run_ref, dataset_ref, scorer_refs, local_result_csv?, aggregate_metrics, raw_trace_refs }`。**不得**宣称该 skill 本身能隔离副作用或产生可比较 run manifest；这些必须由 Orchestrator 包装并记录。

## 2. Microsoft `eval-guide`

**Repository / revision：** [`microsoft/eval-guide@7a22a895`](https://github.com/microsoft/eval-guide/tree/7a22a8957ced79a35fd7b4634fd5b5eac56c308e)。这是多个 specialist skill 和 dashboard 的集合，不是一套通用 agent execution library。[tree](https://github.com/microsoft/eval-guide/tree/7a22a8957ced79a35fd7b4634fd5b5eac56c308e/skills)

### 实际调用链

* 设计链由 `skills/eval-guide/SKILL.md` 编排 planner/generator/interpreter；dashboard `serve.py` 读 stage JSON，把数据嵌入 HTML，`POST /api/feedback` 写 `{stage,status,...}` JSON。它不会执行被测 agent。[dashboard server](https://github.com/microsoft/eval-guide/blob/7a22a8957ced79a35fd7b4634fd5b5eac56c308e/skills/eval-guide/dashboard/serve.py)
* 唯一 checked-in live runner 是 `scripts/eval-runner.js`：解析 CSV → 每题新建 DirectLine conversation → `sendAndCollect()` 轮询 → `scoreTestCase()` → 聚合并写文件。[entry/call chain](https://github.com/microsoft/eval-guide/blob/7a22a8957ced79a35fd7b4634fd5b5eac56c308e/skills/eval-guide/scripts/eval-runner.js)

### 真正输入、输出、隔离语义

| 项 | 代码事实 |
| --- | --- |
| runner CLI | 必须有 `--token-endpoint` 或 `--directline-secret`，并有一个或多个 `--csv` / `--csv-dir`；可设 `--output-dir`、`--concurrency`、`--timeout`。但目前执行 loop 是串行的，`concurrency` 被 parse 后没有用于调度。 |
| CSV schema | header 被 lower-case/space→underscore；每 row 读取 `question`、`expected_response`（或 `expected`）、`testing_method`（缺省 `General quality`）。空 question 被跳过。不是 JSON eval schema。 |
| grading | `keyword_match`、`exact_match` 在本地；`compare_meaning`、`general_quality`、`similarity` 调 Anthropic Claude Sonnet，硬编码阈值分别 0.6/0.5/0.6；无 `ANTHROPIC_API_KEY` 时 LLM grade 是 N/A，不是失败。 |
| outputs | `<output-dir>/eval-results-YYYY-MM-DD.csv` 与同名 JSON；JSON 为 `{timestamp, summary:[{name,total,pass,fail}], results:[{category,question,expected,actual,testingMethod,score,pass,explanation}]}`，并把无 timestamp 的 `{summary,results}` 输出 stdout。重复同日运行会覆盖。 |
| isolation/retry | 每 case fresh DirectLine conversation，避免**会话**串扰；网络/API 异常被填入 `actual="[ERROR: ...]"` 后仍评分。没有 request retry、没有 transactional rollback、没有 target filesystem sandbox。poll 的 timeout 缺省 45s。 |

### Generic adapter contract

这是 `CopilotDirectLineAdapter`，不是 generic `AgentAdapter`：输入必须是 CSV cases + DirectLine auth + 可选 Anthropic judge credential；输出需捕获原生 results JSON/CSV 与每 case endpoint error。Orchestrator 应拒绝把 runner 的固定 date filename 当 immutable artifact，并在 manifest 记录 judge model/阈值；若要求并发，不能依赖已 parse 但未实现的 `--concurrency`。

## 3. `tardigrde/agent-skill-eval`

**Repository / revision：** [`tardigrde/agent-skill-eval@59de161f`](https://github.com/tardigrde/agent-skill-eval/tree/59de161f657b82bfaf8f6abe83dfff38552deb21)。确认 repo 名并非 typo；其 package 入口是 `src/agent_skill_eval/__main__.py` → Typer `cli.app`。[CLI](https://github.com/tardigrde/agent-skill-eval/blob/59de161f657b82bfaf8f6abe83dfff38552deb21/src/agent_skill_eval/cli.py)

### 实际调用链

`agent-skill-eval run` 构造 `EvalRunner` → `load_and_validate_suite()` → 每 `(case, agent, with_skill/without_skill, run_index)` 调 `_run_single()` → fresh `WorkspaceManager.create_workspace()` → optional `SkillInstaller.install()` → harness (`codex` / `claude-code` / `opencode` / `fake`) → pre/post git snapshots → deterministic/LLM assertion grader → benchmark/summary writers。[runner](https://github.com/tardigrde/agent-skill-eval/blob/59de161f657b82bfaf8f6abe83dfff38552deb21/src/agent_skill_eval/runner.py)

### 真正输入 schema 与 preflight

根对象是 `{skill_name: string, evals: EvalCase[]}`。每 case 必填 `id`、`prompt`、`expected_output`；可选 `files`、字符串或结构化 `assertions`、`should_trigger`（默认 true）、`force_skill_invocation`（默认 false）、`stage_files`、side-effect level (`static|local-only|live-safe|live-external`) 和 branch/commit/PR/worktree allowance。`force_skill_invocation=true && should_trigger=false` 直接 schema failure。结构化断言支持 `file_exists`、`file_not_exists`、`file_contains`、`file_not_contains`、`file_unchanged`、`command_ran`、`command_not_ran`、`tests_pass`、`git_clean`、`json_path`、`json_path_not_exists`。[models](https://github.com/tardigrde/agent-skill-eval/blob/59de161f657b82bfaf8f6abe83dfff38552deb21/src/agent_skill_eval/models.py)；[published schema](https://github.com/tardigrde/agent-skill-eval/blob/59de161f657b82bfaf8f6abe83dfff38552deb21/schemas/evals.schema.json)

`validate` 与 `run` 共用 validator：拒绝重复 IDs、fixture 缺失/逃逸路径/目标碰撞、缺结构化字段和无效路径；但“缺 natural trigger、negative control、cheap case、全部 LLM judge”等只是 strict warnings，不会阻止执行。[validation](https://github.com/tardigrde/agent-skill-eval/blob/59de161f657b82bfaf8f6abe83dfff38552deb21/src/agent_skill_eval/validation.py)

### 产物、隔离与 retry

每 iteration 写 `evals_meta.json`、`progress.jsonl`、`benchmark.json`、`cleanup.json`、summary；每 run 写 `outputs/pre_state.json`、`post_state.json`、`output.txt`、`timing.json`、`run_meta.json`、`grading.json`，并写 trajectory/hook records。`compare` 只读两个 `benchmark.json` 和 summary，输出 pass/full-pass/pass@k、time/token/cost、skill hash/size 和 failed-assertion deltas；它**不**验证相同 eval/scorer/runtime，只提示 skill hash 改变。[artifact writer](https://github.com/tardigrde/agent-skill-eval/blob/59de161f657b82bfaf8f6abe83dfff38552deb21/src/agent_skill_eval/runner.py)；[compare](https://github.com/tardigrde/agent-skill-eval/blob/59de161f657b82bfaf8f6abe83dfff38552deb21/src/agent_skill_eval/cli.py#L2674-L2843)

workspace manager 会删除同名既有临时 workspace，然后 clone `source_repo` 或新建 git repo 并复制 fixture；它不是容器/网络 sandbox。cleanup 只是可调用的 `shutil.rmtree`，自动执行与否取决于 CLI/flags；live-external case 的 remote branch/PR 仅被 snapshot/cleanup manifest 记录，不能当作可靠 rollback。harness 有 `max_retries` 参数并把 retry 次数写入 timing，但具体 retry 由每种 harness 实现，不能从 `EvalRunner` 推导幂等性。[workspace](https://github.com/tardigrde/agent-skill-eval/blob/59de161f657b82bfaf8f6abe83dfff38552deb21/src/agent_skill_eval/workspace.py)

### Generic adapter contract

`AgentSkillEvalAdapter.execute` 的 request 至少包含 `{skill_path, evals_path, agent[], model_by_agent, with_baseline, runs, source_repo?, workspace_base, side_effect_level_allowlist, budget, grader_config, timeout, retry_policy}`。adapter 要返回 iteration URI、suite schema hash、skill hash、每 case/run 的 raw artifact URI、observed git/remote effects 和 benchmark；Orchestrator 必须在调用前单独检查 external authority，并在 compare 前自己匹配 suite hash、grader/model/harness versions 与 fixture source commit。

## 4. AWS `sample-agent-skill-eval`

**Repository / revision：** [`aws-samples/sample-agent-skill-eval@13b2277b`](https://github.com/aws-samples/sample-agent-skill-eval/tree/13b2277b300d2beafa09bbbe425ca0cc41f34c8d)。`pyproject.toml` 的 console entry point 是 `skill_eval.cli:main`。[entry point](https://github.com/aws-samples/sample-agent-skill-eval/blob/13b2277b300d2beafa09bbbe425ca0cc41f34c8d/pyproject.toml)

### 实际调用链

CLI dispatch 到 audit、`functional`、`trigger`、`snapshot`/`regression`、`compare`、`report`。[CLI](https://github.com/aws-samples/sample-agent-skill-eval/blob/13b2277b300d2beafa09bbbe425ca0cc41f34c8d/skill_eval/cli.py) functional path 对每个 case × `--runs` 执行 `_execute_eval_pair`：建立两个 `TemporaryDirectory`、向两臂复制 fixtures、只向 treatment workspace 复制 `SKILL.md` 与 skill resources、调用 agent runner、parse 后 grade，并计算 with/without skill 的均值/标准差、token/tool-call 与 Pareto 分类。[functional](https://github.com/aws-samples/sample-agent-skill-eval/blob/13b2277b300d2beafa09bbbe425ca0cc41f34c8d/skill_eval/functional.py)

### 输入、输出、隔离语义

| 项 | 代码事实 |
| --- | --- |
| functional case schema | `evals/evals.json` 必须为 JSON array；每项至少 `id`、`prompt`，可带 `assertions`、`files`。这与 ASE 的 `{skill_name, evals}` 根对象不兼容。 |
| runner protocol | `AgentRunner` 有 `check_available()`、`run_prompt(prompt, skill_path?, workspace_dir?, timeout, output_format)` 和 `parse_output()`；后者正规化为 `{events, tool_calls, text, token_counts}`。当前 registry 只注册 Claude runner。[agent runner](https://github.com/aws-samples/sample-agent-skill-eval/blob/13b2277b300d2beafa09bbbe425ca0cc41f34c8d/skill_eval/agent_runner.py) |
| execution / isolation | Claude runner 使用 local subprocess 的 `claude -p`，以 `--append-system-prompt` 注入**只有 SKILL.md 的内容**，并使用 `--permission-mode bypassPermissions` 和 Read/Glob/Grep/Bash/Write/Edit。两个 temporary workspaces 隔离 fixture 与 skill files，但没有 Docker/network/credential isolation。`files` 在复制时 flatten 为 basename；`.claude/` 只在 treatment arm，故可能混入 treatment effect。 |
| retry | `--runs` 是重复采样而非 transient retry；non-zero subprocess result 会被采集，但 functional flow 不因它显式 retry/fail。 |
| outputs / pass policy | `benchmark.json`（默认 `<skill>/evals/benchmark.json` 或 `--output`）保存 pair/aggregate；functional “pass”仅为 `mean_with >= mean_without && mean_with >= .5`。`eval_queries.json` 项为 `{query, should_trigger}`，trigger 利用 output/trajectory heuristic 计算 precision/recall/F1；由于 skill 是 append prompt，这不证明 native skill routing。[trigger](https://github.com/aws-samples/sample-agent-skill-eval/blob/13b2277b300d2beafa09bbbe425ca0cc41f34c8d/skill_eval/trigger.py) |
| snapshot/regression | 只针对 static audit：写 `evals/baselines/<version>/results.json`、`latest`、`history.json`；regression 是新 CRITICAL 或 audit score 下降 >5，不比较 functional benchmark。统一 `report.json` 将 audit/functional/trigger 按 40/40/20 合并，这只是该应用的固定 policy。[regression](https://github.com/aws-samples/sample-agent-skill-eval/blob/13b2277b300d2beafa09bbbe425ca0cc41f34c8d/skill_eval/regression.py)；[unified report](https://github.com/aws-samples/sample-agent-skill-eval/blob/13b2277b300d2beafa09bbbe425ca0cc41f34c8d/skill_eval/unified_report.py) |

### Generic adapter contract

输入为 `{skill_dir, eval_cases[], trigger_cases?, runner="claude", runs, timeout, audit_policy}`，输出要拆成 `static_audit_evidence`、`functional_pair_evidence`、`trigger_evidence`，不要只接受统一 report。Orchestrator 应禁止把该仓库的 40/40/20 权重或 0.5 pass threshold 设为全局策略，并在结果中标注 `skill_prompt_injected=true`、`sandbox_strength="temporary-dir-only"`。

## 5. NVIDIA `SkillEvaluator`

**Repository / revision：** [`NVIDIA/SkillEvaluator@ff349e0d`](https://github.com/NVIDIA/SkillEvaluator/tree/ff349e0d9f03868fc27d1e2bbd62eb849cba66c9)。Tier 3 不是纯文档：CLI → tier3 command preflight/validation → `run_harbor_eval` → private evaluator snapshot + task staging → Harbor jobs for treatment and (除非 `--skip-baseline`) baseline → collection/validation/render/publish latest。[tier3 command](https://github.com/NVIDIA/SkillEvaluator/blob/ff349e0d9f03868fc27d1e2bbd62eb849cba66c9/src/skillevaluator/tier3/commands.py)；[Harbor runner](https://github.com/NVIDIA/SkillEvaluator/blob/ff349e0d9f03868fc27d1e2bbd62eb849cba66c9/src/skillevaluator/tier3/harbor/runner.py)

### 实际输入 schema、grader 与 execution policy

| 项 | 代码事实 |
| --- | --- |
| dataset | `evals/evals.json` 的 canonical root 是 `{skill_name, evals:[...]}`；case 有 `id,prompt,expected_output` 与可选 `assertions,expected_skill,expected_script,acceptable_skills`。loader 还接受 json/jsonl/yaml/yml 和 legacy flat questions。fixtures `files` 缺省=shared fixtures，显式空/null=无 fixture。[spec](https://github.com/NVIDIA/SkillEvaluator/blob/ff349e0d9f03868fc27d1e2bbd62eb849cba66c9/src/skillevaluator/tier3/evals_spec.py)；[dataset docs](https://github.com/NVIDIA/SkillEvaluator/blob/ff349e0d9f03868fc27d1e2bbd62eb849cba66c9/docs/eval-datasets.mdx) |
| config | `config.yml` 未知 key 失败；`schema_version=1`，Harbor task source、`n_attempts>=1`、pass threshold [0,1]、stop-on-pass、并发/timeout、runtime preflight/setup、per-agent model、isolated/group workspace、grading mode 都是显式字段。[config validation](https://github.com/NVIDIA/SkillEvaluator/blob/ff349e0d9f03868fc27d1e2bbd62eb849cba66c9/src/skillevaluator/tier3/evals_config.py) |
| attempts / isolation | `n_attempts` 是 pass@k 试验次数，不能当 network/transient retry。treatment/baseline 独立 staging，避免 skill leak。run roots collision-safe，先写 `dataset_snapshot.json`，atomic writes；`HarborArtifactLifecycle` 默认删除 staged task/job dirs，`--harbor-keep-jobs` 保留。local sandbox 默认 require、不可用时 fail closed；Docker/cloud 才是 untrusted code 运行选项。[local sandbox](https://github.com/NVIDIA/SkillEvaluator/blob/ff349e0d9f03868fc27d1e2bbd62eb849cba66c9/src/skillevaluator/tier3/harbor/local_sandbox.py) |
| grading | 默认维度 Security、Correctness、Discoverability、Effectiveness、Efficiency。custom grader 消费 ATIF `/logs/agent/trajectory.json`、`/tests/entry.json`，写 `/logs/verifier/reward.json`（[0,1]）及 `reward.txt`；`default_plus_custom` 不能覆盖保留 metric，`custom_only` 必须提供 numeric overall。[custom graders](https://github.com/NVIDIA/SkillEvaluator/blob/ff349e0d9f03868fc27d1e2bbd62eb849cba66c9/docs/custom-graders.mdx) |

### 产物与 adapter contract

stable run dir 写 `dataset_snapshot.json`、`result.json`、`run_config.json`、`attempt_policy.json`、`report.html`、可选 `comparison.json`，并按 agent/arm 存 summary、trials、`lift.json`、`pass_at_k_lift.json`；`latest` 选择最新 completed run。只有有效 paired 数据才计算 paired McNemar diagnostic；Wilson interval、+0.05/-0.10 lift bands 是诊断，非 promotion 决策。[reports](https://github.com/NVIDIA/SkillEvaluator/blob/ff349e0d9f03868fc27d1e2bbd62eb849cba66c9/docs/reports.mdx)

`NvidiaSkillEvaluatorAdapter.execute` 应要求 `{skill_dir, frozen_dataset_ref, config_ref, agent/provider, sandbox_policy, baseline_required, run_id}`，并返回完整 run-dir、treatment/baseline trial refs、attempt policy、grader dimensions 与 cleanup state。禁止 `--skip-baseline` 的结果进入 lift comparison；`create-eval-dataset` 生成或 `--refine` 覆盖的 `evals.json` 只能是 draft，不能静默改写冻结 benchmark。它仍是 skill-centric（虽有 Codex/Claude/OpenCode runtime adapters），不是任意 agent/system-stage I/O adapter；LLM judge 也不会自动按人工校准。

## 不支持的旧说法 / 必须显式处理的歧义

1. “这五个共同形成 Design/Execution/Compare”只能是架构建议，不是任一项目实现的共同 API。
2. Microsoft 的 `--concurrency` 不代表实际并行；源码目前是嵌套 `for` 串行运行。
3. MLflow skill 并不写通用 immutable manifest，也没有自己实现 retry/sandbox；其远程 artifact schema 取决于安装的 MLflow 版本和 tracking backend。
4. agent-skill-eval 的 compare 并不保证两 iteration 的 eval/scorer/agent config 可归因；Orchestrator 需增加 compatibility gate。
5. case 的 `side_effect_level` 是 agent-skill-eval 的声明/筛选和 post-hoc contract 检查，不是 runtime 权限边界。需要 OS/container/network/credential policy 的执行层。
