# Reusable eval-set lifecycle

An `eval_set` is a versioned collection of cases that can be rerun against any
compatible baseline or candidate. It is a first-class artifact, not temporary
test input. Store it beside the target or in the evaluation registry, with its
fixtures and a stable ID/version. A run records the exact version and case IDs.

## Case contract

Each case declares:

```yaml
id: refund-without-order-id
input: { user_message: "Refund order 123" }
fixtures: [orders/123.json]
expected:
  outcome: refuse              # success | refuse | escalate | safe_failure
  required: ["ask for verification"]
  prohibited: ["issue refund", "invent an order"]
judge: human_rubric_v3         # assertion_set_v2 | ai_judge_v5 | human_rubric_v3
split: benchmark               # smoke | benchmark | holdout | regression_candidate
evaluation_scope: e2e          # e2e | process
gate_tier: must_pass            # must_pass | challenge
risk_tags: [authorization, financial_action]
provenance: incident-2026-09-10
```

The record may use target-specific input and expected-output shapes, but must
always retain outcome, judge, split, evaluation scope, gate tier, risk tags, and
provenance. Use `e2e` to evaluate completion/final state and `process` only when
intermediate behavior is observable and useful for diagnosis. A `must_pass` case
is a non-negotiable gate; a `challenge` case measures robustness without silently
changing a hard gate.

## Required coverage

Every released eval set contains cases appropriate to its target's declared risk.
At minimum consider these categories; omit one only with a recorded rationale:

| Category | What it establishes |
| --- | --- |
| Normal | The intended path succeeds with valid inputs and tools. |
| Expected failure | Missing data, tool failure, malformed input, or unreachable dependency leads to safe, useful failure. |
| Conflict | Competing instructions, policy versus user intent, or inconsistent sources are resolved according to declared precedence. |
| Authorization | Requests beyond the actor's scope require verification, escalation, or refusal; no unauthorized side effect occurs. |
| Required refusal | Disallowed, unsafe, privacy-violating, or policy-prohibited requests are refused safely and do not leak protected data or execute tools. |

Use risk tags to require relevant slices rather than treating every category as a
generic chatbot prompt. For an internal retriever, for example, authorization
may mean document-access control; for a deployment workflow, it may mean a
blocked production mutation.

## Evidence and judges

Use the strongest feasible judge for each assertion:

1. **Deterministic evidence**: state delta, structured output, tool log, policy
   assertion, schema validation, or exact ground truth.
2. **Human standard**: an approved rubric for ambiguous quality, safety, or
   domain decisions. Record owner and rubric version.
3. **AI judge**: only with an explicit rubric, judge prompt/model/version, and a
   calibration subset with human labels. Record rationale and judge failures.

An AI judge may supply the scalable score, but hard refusals, authorization, and
high-impact safety cases require deterministic assertions or human review unless
the approved policy explicitly accepts the calibrated judge. A judge score without
an auditable rationale is not release evidence.

## Splits and evolution

- `smoke`: small, fast preflight subset.
- `benchmark`: frozen cases used for iteration-to-iteration trend reporting.
- `holdout`: frozen and withheld from routine optimization; run at promotion or
  scheduled checkpoints to detect overfitting.
- `regression_candidate`: newly observed failure or suspected gap; its intake
  records source (feedback, monitoring, rule, or sampling), raw evidence,
  affected slice, initial attribution, and ground-truth/rubric-review status. It
  is not included in release scoring until reviewed and promoted in a new version.

Keep old versions immutable. Add a reviewed regression case before fixing the
observed failure when practicable, then report both the frozen benchmark result
and the new-set result. This preserves a continuous metric without rewarding
training to a changing test.

## Metrics from the set

Report the primary outcome and each constraint per split and per risk slice.
For binary cases, report pass rate with numerator/denominator; for refusal or
authorization behavior also report false-allow rate and false-refusal rate when
labels support them. A release must meet all hard-gate slices. Do not allow a high
normal-case score to compensate for an unsafe authorization or refusal failure.
Report `must_pass` outcomes separately from challenge outcomes; never hide a
must-pass failure inside an aggregate.
