# Specialist contracts

The Orchestrator routes only by state. These contracts preserve specialist depth
without turning the Orchestrator into another evaluation framework.

| Specialist | Enters when | Receives | Returns | Does not own |
| --- | --- | --- | --- | --- |
| Eval Design | `NO_CRITERIA` or an invalid/non-comparable spec | target I/O, objective, risks, known failures, constraints | versioned `eval_spec` and `eval_set` | execution, candidate implementation, accept/reject |
| Eval Execution | approved criteria need baseline or candidate evidence | approved spec/set, target variant, execution policy | immutable `run_manifest` and raw per-case evidence | changing criteria, diagnosis, release decision |
| Experiment & Compare | baseline evidence exists, or baseline/candidate evidence is ready | compatible manifests, gate policy, prior hypothesis | failure analysis, ranked falsifiable candidates, or `comparison_report` | implementing a candidate, changing gates, final acceptance |

## Reference patterns, not runtime dependencies

- **MLflow** contributes the trace/dataset/scorer pattern for execution evidence.
- **Microsoft eval-guide** contributes discover/plan/generate, interpretation,
  and explicit review checkpoints.
- **AWS sample-agent-skill-eval** contributes Skill-focused audit, trigger, and
  regression dimensions.
- **agent-skill-eval** contributes baseline/treatment, repeated trials,
  pass@k, workspace evidence, and iteration comparison.
- **NVIDIA SkillEvaluator** contributes tiered quality gates, safety checks,
  generated-eval drafts, and paired evaluation discipline.

The Orchestrator does not expose, select, or depend on these projects' CLIs,
schemas, weights, or runtime behavior. Their detailed source study remains in
the project research notes, not in the execution state machine.
