---
name: eval-execution
description: Run an approved evaluation specification against a baseline or candidate and preserve raw evidence. Use after criteria and a reusable eval set are approved; do not redefine metrics, alter gates, or decide whether an improvement is accepted.
---

# Eval Execution

Consume an approved `eval_spec`, immutable `eval_set` version, target variant, and
execution policy. Produce an immutable `run_manifest` with raw per-case evidence.
Do not change the target, criteria, thresholds, or release decision.

## Preflight

Verify target identity, fixtures, access, scorer/judge availability, side-effect
policy, budget, repetition policy, and evidence destination before running. State
execution `fidelity` (`production_equivalent`, `controlled_simulation`, or
`unknown`) and material differences from production. Bind the exact eval-set and
spec versions. Report setup, fixture, scorer, or target access failures as
structured execution failures; do not misclassify them as a target regression.

## Run and record

- Execute the approved cases and repetitions against one named variant.
- Preserve raw response, trajectory/tool/state evidence where available, not only
  aggregate scores.
- For a multi-step target, preserve at least complete input/output, key
  tool/Skill calls, and final state so an observed failure can be attributed.
- Record per-case outcomes, metric assessments, usage/cost, duration, errors,
  runtime/model configuration, and execution environment fingerprint.
- Mark a run complete only when its evidence locations and completion status are
  recorded in the immutable `run_manifest`.

## Hand-off

Return baseline evidence to Experiment & Compare for failure analysis. Return a
candidate manifest with the same approved criteria for comparison. If a rerun
would change an uncontrolled factor, report non-comparability risk to the
Orchestrator before execution.
