---
name: optimization-orchestrator
description: Coordinate Eval Design, Eval Execution, and Experiment & Compare in an evidence-backed optimization loop for a skill, agent, or bounded system target. Use when a target needs criteria, a baseline, candidate evaluation, or an accept/reject decision; do not implement the target itself.
---

# Optimization Orchestrator

Coordinate specialist skills; do not absorb their domain logic. This skill owns
canonical state, artifact contracts, transition guards, and the two human gates.
It does **not** route among evaluation frameworks at runtime. The referenced
projects inform the specialist structures, but the specialists choose their own
tools and methods.

A target can be a skill, an agent, or one bounded system stage (for example,
retrieval, routing, prompting, tool policy, or a workflow node). Do not evaluate
an unbounded "whole system" as one target; split it at an observable input/output
seam first.

## Route the request

- `NO_CRITERIA` → **Eval Design**. It defines target I/O, good, metrics, rubric,
  reusable eval set, and gate policy; it returns `eval_spec` + `eval_set`.
- `CRITERIA_CONFIRMED` + `NO_BASELINE` → **Eval Execution**. It runs the
  baseline and returns an immutable `run_manifest` with raw evidence.
- `BASELINE_READY` → **Experiment & Compare**. It clusters failures, diagnoses
  likely causes, and returns ranked, falsifiable candidate proposals.
- `CANDIDATE_READY` → **Eval Execution**. It re-runs the approved spec against
  that candidate and returns another `run_manifest`.
- `BASELINE_AND_CANDIDATE_READY` → **Experiment & Compare**. It compares the
  compatible runs and returns a `comparison_report` with accept/reject evidence.
- `ACCEPTANCE_REQUIRED` → **human review**. The operator accepts or rejects the
  improvement. A policy, authority, budget, or safety exception also stops for
  review rather than being routed to a specialist.

Read [the state and artifact contract](references/state-contract.md) before
creating or moving state. Read [the specialist contracts](references/specialist-contracts.md)
before delegating work. Read [the eval-set lifecycle](references/eval-set-lifecycle.md)
when designing, growing, judging, or freezing reusable cases.

## Run the loop

1. Create or load a run record. Infer its state only from valid artifacts and
   append-only events, never from conversational claims.
2. Route to exactly one specialist from the state rules above. Give it canonical
   inputs and required outputs; specialists never mutate global state.
3. Validate output artifacts, append an event, and then transition state.
4. Before every execution, bind the approved immutable `eval_set` and run
   preflight. Setup, fixture, or scorer failure is not target regression.
5. Before comparison, require compatible manifests. If controlled factors differ,
   return to Design rather than declaring a winner.
6. After a ranked candidate is selected, invoke the existing target change
   workflow to implement it. Record its identity and resume at Eval Execution;
   implementation is coordinated but not a fourth specialist.
7. On acceptance, hand `promotion_evidence` to the existing change or release
   workflow. If the target already has safe monitoring, shadow, or A/B capability,
   it may emit a non-blocking post-acceptance observation event; credible failures
   return as `regression_candidate` intake, not an automatic benchmark edit.

## Guardrails

- Keep `eval_spec`, `run_manifest`, and `comparison_report` execution-tool-neutral.
  Specialist-specific files are linked evidence, not global state.
- Keep events append-only with before/after state, route, reason, artifact hash,
  operator, and timestamp.
- Treat generated cases as drafts until review approves their ground truth and
  gates.
- Preserve frozen benchmark and holdout cases across iterations. Newly discovered
  failures belong in a candidate regression set first; never rewrite historical
  cases to improve a reported score.
- A metric is admissible only when its operational definition, direction, unit,
  evidence source, scorer version, threshold, slices, and known confounders are
  explicit. Combine a primary outcome metric with non-negotiable constraint
  metrics; do not use a single weighted score to hide a safety or cost regression.
- Preserve raw evidence and per-case outcomes; an aggregate score alone cannot
  support triage or causal claims.
- Stop at `accepted`, `blocked`, or `cancelled`. Do not loop indefinitely on a
  score that did not improve; obey the iteration and budget limits in policy.
- Online observation is optional evidence discovery, never a prerequisite for an
  offline acceptance decision and never a fourth specialist.
