# Metric design

Metrics must be consequences of the target's declared output contract, not a
backend's default dashboard. Design them before selecting a runner.

## Minimum metric set

1. Choose one **primary outcome** that expresses the target's intended effect:
   task success, answer quality, retrieval utility, correct route selection, or
   artifact validity.
2. Add **constraint metrics** for effects that may not regress: safety/policy,
   reliability, latency, cost, and destructive side effects as applicable.
3. Define risk and operating slices before running: common traffic, known failure
   modes, adversarial/safety inputs, and inputs where the candidate is expected
   to help. A global mean may be reported, but cannot replace a hard-gate slice.

## Acceptance rules

- A hard constraint must meet its threshold on every required slice.
- A primary outcome must meet its absolute target or improve against a compatible
  baseline by the declared practical minimum.
- When sampling or LLM judges are noisy, declare repetition and a decision rule
  before execution. Report uncertainty or individual trial outcomes instead of
  claiming a winner from one run.
- Cost and latency are either constraints or explicit trade-off dimensions. State
  the permitted exchange; do not infer it after seeing results.

## Examples of operational definitions

| Target | Outcome metric | Constraint metric |
| --- | --- | --- |
| Retrieval stage | `recall_at_5`: share of cases where a required source appears in top five results | `p95_latency_ms`; no restricted document returned |
| Tool-using agent | `task_success_rate`: grader-confirmed completion of final workspace state | policy-compliant tool calls; `p95_cost_usd` |
| Skill | `pass_at_k`: at least one valid result across `k` independent trials | trigger precision; no prohibited file/network side effect |
| Router node | route accuracy against labelled intents | unsafe-route rate equals zero on safety slice |

These are patterns, not defaults. Select only measurements that the target's I/O
contract can support with trustworthy evidence.
