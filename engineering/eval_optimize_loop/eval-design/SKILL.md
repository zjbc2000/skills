---
name: eval-design
description: Define a reviewable evaluation specification and reusable eval set for a skill, agent, or bounded system target. Use when success criteria, metrics, rubrics, datasets, or gates are missing; do not execute evaluations or choose a release decision.
---

# Eval Design

Produce a versioned `eval_spec` and `eval_set`. Work from the target's observable
input/output seam, its objective, constraints, risk, and known failures. Do not
run the target, modify it, or declare it improved.

## Required output

`eval_spec` must identify the target and variant, input/output contract, primary
outcome metric, hard and soft constraint metrics, rubric/scorer version, slices,
thresholds, repetition policy, side-effect policy, budget, and data provenance.

`eval_set` must be reusable and versioned. Include normal, expected-failure,
conflict, authorization, and required-refusal cases where relevant to target
risk. Each case states input, fixture, expected outcome, judge, split, risk tag,
provenance, `evaluation_scope` (`e2e` or `process`), and `gate_tier`
(`must_pass` or `challenge`). Use process scope only when the target exposes
meaningful intermediate behavior; use must-pass for non-negotiable outcomes.

## Metric rules

- Define one primary outcome and only constraints needed to protect the target.
- Every metric declares operational definition, direction, unit, evidence source,
  judge/scorer version, threshold, slices, and known confounders.
- Prefer deterministic assertions; use human rubrics for ambiguous domain truth;
  use AI judges only with a rubric and a human-calibrated subset.
- Validate an ambiguous rubric against representative human-labelled cases before
  using it as a release gate; record the rubric version and calibration result.
- Treat generated cases as drafts. Freeze approved benchmark and holdout cases;
  newly discovered failures begin as regression candidates.

## Hand-off

Return the draft for the Orchestrator's criteria-confirmation gate. On approval,
Eval Execution receives the frozen spec/set. If target I/O or truth cannot be
defined credibly, return the missing decision or evidence rather than inventing a
proxy metric.
