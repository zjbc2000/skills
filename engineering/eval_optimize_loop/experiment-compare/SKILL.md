---
name: experiment-compare
description: Diagnose evaluation evidence, propose falsifiable candidates, and compare compatible baseline and candidate runs. Use after a baseline exists or when a candidate needs an accept/reject recommendation; do not change the target, criteria, or final decision.
---

# Experiment Compare

Consume immutable run evidence and the approved gate policy. Return either ranked,
falsifiable candidate proposals or an immutable `comparison_report`. Do not edit
the target, change criteria, or accept an improvement.

## Failure analysis

For a baseline, group failures by case slice, metric, evidence pattern, and
suspected cause. Separate evaluation setup failures from target failures. Propose
the smallest candidate changes that could explain or fix a cluster; each proposal
states the expected metric effect, cost/risk, and what result would falsify it.
Rank proposals by expected value under the declared constraints, not by an
invented universal score.

When a new failure could become a regression case, return a `case_intake` record:
source (feedback, monitoring, rule, or sampling), raw evidence, affected slice,
initial attribution, and whether ground truth/rubric has been reviewed. It remains
a `regression_candidate` until that review completes.

## Comparison

Before comparing, verify spec hash, eval-set version, scorer/rubric version,
target/model/runtime configuration, repetition, budget policy, side-effect level,
and the declared experimental variable. If incompatible, return
`non_comparable`; do not name a winner.

For compatible runs, report primary-outcome delta, every constraint result,
required slices, uncertainty or trial detail, regressions, cost/latency trade-off,
raw evidence links, and a recommendation. A hard-constraint failure cannot be
offset by a higher average score.

For a recommendation that can pass the acceptance gate, include
`promotion_evidence`: compared manifest IDs, bound spec/eval-set/rubric versions,
hard-gate results, recommendation, and a machine- or human-readable conclusion
for the existing change or release workflow.

## Hand-off

Return candidate proposals to the existing target change workflow. Return the
comparison report to the Orchestrator's acceptance gate. If evidence is
insufficient, state what execution or design artifact is missing.
