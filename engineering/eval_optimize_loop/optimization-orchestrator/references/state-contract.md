# State and artifact contract

## Canonical artifacts

| Artifact | Created by | Required contents | Mutability |
| --- | --- | --- | --- |
| `eval_spec` | Eval Design | `id`, `version`, target identity/type, input/output contract, objective, non-negotiable constraints, risks, cases/fixtures, metric definitions, expected behavior, scorer or rubric version, gate policy, repetition, side-effect level, budget, data/ground-truth provenance | Versioned; approval freezes a version |
| `eval_set` | Eval Design, reviewed by a domain owner | `id`, `version`, compatible input/output contract, case records, split, expected outcome, judge method, provenance, fixtures, risk tags, `evaluation_scope`, `gate_tier`, and approval | Immutable once bound to a run; evolve by a new version |
| `run_manifest` | Eval Execution | `id`, `eval_spec_hash`, target variant/commit, execution configuration, model/reasoning/seed, runtime/environment fingerprint, fidelity and production differences, resolved budget, raw-evidence URIs, per-case outcomes, aggregates, usage, duration, failures, completion status | Immutable |
| `comparison_report` | Experiment & Compare | compared manifest IDs, compatibility result, deltas, uncertainty or repeat summary, failure clusters, trade-offs, evidence URIs, ranked recommendation, next falsifiable hypothesis, `promotion_evidence` when recommended for acceptance | Immutable; supersede instead of edit |
| `event` | Orchestrator | event ID, timestamp, operator, route, reason, state before/after, artifact URI/hash, policy version | Append-only |

`eval_spec` and its referenced immutable `eval_set` version are the canonical
inputs to Eval Execution. Any execution-tool-specific files and reports remain
linked evidence, not replacements for these artifacts.

## Target and metric definitions

The target must be narrow enough to expose a stable input/output seam.

| Target type | Input contract | Output contract | Typical candidate variable |
| --- | --- | --- | --- |
| `skill` | Invocation request, workspace/context, available tools | Agent behavior, artifacts, tool calls, final response | Skill instructions, scripts, references |
| `agent` | Task, conversation/context, tools, initial state | Response, trajectory, tool calls, produced artifacts | Model, prompt, planning/tool policy, memory |
| `system_stage` | Named upstream artifact/event and environment | Named downstream artifact/event and side effects | Retriever, router, prompt template, model, workflow node |

An `eval_spec.metric` must include: `name`; `purpose` (`outcome` or
`constraint`); operational definition; direction; unit; evidence source; scorer
or computation version; threshold or comparison rule; required slices; and known
confounders. An outcome metric measures the optimization objective. A constraint
metric is a hard or soft gate such as safety, policy compliance, latency, cost,
or reliability. Do not collapse a failed hard constraint into a weighted average.

Metric selection is valid only when each metric maps to a declared output or
allowed side effect, and the eval set covers realistic use plus relevant failure
and risk slices. If no trustworthy evidence or scorer exists, the state remains
`designing` or moves to `blocked`; a convenient proxy is not silently promoted to
a release gate.

## State machine

```text
intake -> diagnosing -> designing -> awaiting_criteria_confirmation
  -> baseline_execution -> baseline_ready -> failure_analysis
  -> candidate_proposed -> implementing -> candidate_execution
  -> comparing -> awaiting_acceptance -> accepted | rejected

rejected -> failure_analysis
any non-terminal state -> blocked | cancelled
```

| From | To | Entry guard / trigger | Required new evidence |
| --- | --- | --- | --- |
| `intake` | `diagnosing` | Target, observable I/O, objective, and operator are known. | Intake event |
| `diagnosing` | `designing` | Known failures, assumptions, and constraints are recorded; lack of evidence is explicit. | Diagnosis note |
| `designing` | `awaiting_criteria_confirmation` | Draft `eval_spec` and versioned `eval_set` exist. | Draft hashes |
| `awaiting_criteria_confirmation` | `baseline_execution` | **Gate 1:** reviewer confirms metrics, rubric, dataset, and thresholds. | Approval event |
| `baseline_execution` | `baseline_ready` | Preflight passes and baseline manifest with raw evidence is complete. | Baseline `run_manifest` |
| `baseline_ready` | `failure_analysis` | Baseline evidence is available. | Analysis request |
| `failure_analysis` | `candidate_proposed` | A smallest falsifiable candidate is ranked with its expected metric effect. | Candidate proposal |
| `candidate_proposed` | `implementing` | Existing target change workflow accepts the proposal. | Change request |
| `implementing` | `candidate_execution` | Change workflow records a candidate identity; approved criteria still apply. | Candidate reference |
| `candidate_execution` | `comparing` | Candidate manifest with raw evidence is complete. | Candidate `run_manifest` |
| `comparing` | `awaiting_acceptance` | Manifests are compatible and comparison report is complete. | `comparison_report` |
| `comparing` | `designing` | Runs are non-comparable or expose invalid criteria. | Non-comparability report |
| `awaiting_acceptance` | `accepted` | **Gate 2:** reviewer accepts evidence-backed improvement. | Acceptance event |
| `awaiting_acceptance` | `rejected` | **Gate 2:** reviewer rejects or defers improvement. | Rejection event |
| `rejected` | `failure_analysis` | Another iteration is allowed by budget and policy. | Iteration decision |
| Any active | `blocked` | Human authority, budget, iteration limit, policy, or evidence is insufficient to continue safely. | Block reason |
| Any active | `cancelled` | Operator cancels. | Cancellation event |

## Comparison compatibility

The comparator must verify these fields before interpreting a delta as a target
change effect: spec hash; immutable eval-set version or explicitly equivalent case
set; scorer/rubric version;
target/model/reasoning configuration; backend/runtime/environment; repetition;
budget policy; and side-effect level. A mismatch is allowed only when declared as
the controlled experimental variable. Otherwise the report outcome is
`non_comparable`.

## Terminal policy

- `accepted`: hard gates pass and an authorized decision is recorded.
- `blocked`: continuation needs a waiver, authority, scope change, more budget,
  or evidence unavailable to the orchestrator.
- `cancelled`: the operator intentionally ends the loop.

The policy must cap iterations and budget before the first execution. A failed
candidate alone does not authorize another iteration.

After `accepted`, an existing safe monitoring, shadow, or A/B workflow may append
an observation event without reopening the terminal state. A credible observed
failure enters Eval Design/Experiment & Compare as a reviewed
`regression_candidate`; it never mutates the accepted eval-set version.
