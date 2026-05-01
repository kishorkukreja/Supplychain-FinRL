# Supplier Selection Issue Backlog

## Summary

This document preserves the implementation and tracking alignment for the supplier-selection program.

Specs are contracts. GitHub issues are executable implementation work orders. One GitHub issue should represent one unit of work that can be implemented, tested, reviewed, and closed independently.

The governing roadmap remains the oversight source of truth:

`docs/superpowers/specs/2026-05-01-supplier-selection-program-governance.md`

This backlog document records the issue sequence and issue body structure so the team does not lose alignment before GitHub issues are enabled and created.

## Issue Unit Rule

One issue equals one executable, testable unit of work.

A good issue is:

- independently implementable,
- independently testable,
- independently reviewable,
- linked to the relevant approved spec section,
- small enough that done is unambiguous,
- large enough to deliver a meaningful capability.

Avoid issue sizes that are too broad or too narrow:

- Too broad: `Implement dataset system`
- Too narrow: `Create schemas.py`
- Good: `Dataset: supplier-selection case factory`
- Good: `Export: SFT JSONL`

## Issue Template

Each implementation issue should use this structure:

```markdown
## Goal

Describe the capability this issue delivers.

## Spec Reference

Link the relevant spec file and section.

## Implementation Notes

State boundaries, important behavior, and what is intentionally out of scope.

## Acceptance Criteria

- [ ] Concrete done condition.
- [ ] Concrete done condition.
- [ ] Concrete done condition.

## Verification

List commands or checks that prove the issue is complete.
```

## M0 Issue

Create this issue first and create no M1 implementation issues until it is accepted.

Title:

`Docs: finalize supplier-selection spec set`

Labels:

`spec`

Milestone:

`M0 Specs`

Body:

```markdown
## Goal

Review and finalize the supplier-selection five-document spec set before implementation begins.

This issue tracks the M0 Specs gate. No M1 dataset/evaluator implementation issues should start until this issue is accepted.

## Source Of Truth

Governing roadmap:
- `docs/superpowers/specs/2026-05-01-supplier-selection-program-governance.md`

Child specs:
- `docs/superpowers/specs/2026-05-01-supplier-selection-use-case.md`
- `docs/superpowers/specs/2026-05-01-supplier-selection-dataset-evaluator.md`
- `docs/superpowers/specs/2026-05-01-supplier-selection-reward-model-grpo.md`
- `docs/superpowers/specs/2026-05-01-supplier-selection-agent-architecture.md`

Background only:
- `docs/research/2026-05-01-grpo-verifier-supply-chain-lora.md`

## Review Checklist

- [ ] Governing roadmap links all child specs.
- [ ] Child specs link back to the governing roadmap.
- [ ] Use case contract clearly defines supplier selection recommend + critique.
- [ ] Dataset + evaluator spec is implementable without product decisions.
- [ ] Reward model + GRPO spec separates teacher, verifier, reward model, and GRPO roles.
- [ ] Agent architecture spec defines orchestrator, executor, and verifier without pulling agent implementation into M1.
- [ ] The research note is referenced as background only.
- [ ] No child spec duplicates another child spec's ownership.
- [ ] M1 Dataset + Evaluator issues can be derived from the approved specs.

## Acceptance Criteria

- [ ] All five specs are reviewed and accepted.
- [ ] Any requested doc revisions are completed.
- [ ] The governing roadmap status can move from `Drafted` to `Accepted`.
- [ ] M1 implementation issues may be created after this issue is closed.
```

## M1 Dataset + Evaluator Issues

Create these only after the M0 issue is accepted.

### 1. Dataset: supplier-selection case factory

Spec reference:

`docs/superpowers/specs/2026-05-01-supplier-selection-dataset-evaluator.md`

Delivers:

- deterministic synthetic supplier-selection cases,
- valid case schema,
- supplier options and demand context,
- 100+ locally generated cases.

Acceptance:

- fixed seed gives stable output,
- cases match the dataset spec,
- generated records contain required supplier and demand fields.

### 2. Dataset: candidate action and outcome evaluator

Spec reference:

`docs/superpowers/specs/2026-05-01-supplier-selection-dataset-evaluator.md`

Delivers:

- candidate supplier action policies,
- action execution through `SupplierSelectionEnv`,
- comparable KPI and cost outcomes.

Acceptance:

- each case has at least four candidate actions,
- candidate actions produce comparable outcomes,
- implementation has no external LLM or API dependency.

### 3. Dataset: risk-adjusted best-action selection

Spec reference:

`docs/superpowers/specs/2026-05-01-supplier-selection-dataset-evaluator.md`

Delivers:

- selected `observed_or_optimal_action`,
- fixed risk-adjusted scoring formula,
- metadata recording scoring weights.

Acceptance:

- best action is reproducible,
- selected action exists in candidate actions,
- scoring weights are present in output metadata.

### 4. Evaluator: dataset quality reports

Spec reference:

`docs/superpowers/specs/2026-05-01-supplier-selection-dataset-evaluator.md`

Delivers:

- local dataset quality summaries,
- invalid record counts,
- split counts,
- selected action distribution,
- duplicate and allocation validation checks.

Acceptance:

- report JSON files are generated locally,
- reports include required metrics,
- tests verify expected report fields.

## Later Issue Placeholders

These issues are part of the planned sequence but should not be created until earlier milestone gates are accepted.

### M2 Rationale + SFT Export

- `LLM interfaces: teacher and verifier mocks`
- `Reward data: rationale schema and consistency filter`
- `Export: SFT JSONL`

### M3 Reward Model GRPO

- `Reward model: GRPO pilot scaffold`

### M4 Supplier Selection Agent

- `Agent: orchestrator-executor-verifier interfaces`

## Tracking Rules

The governing roadmap should record issue IDs once GitHub issues are created.

Required roadmap tracking fields:

- phase,
- spec link,
- GitHub issue link,
- owner or status,
- blockers,
- acceptance gate.

Recommended labels:

- `spec`
- `dataset`
- `evaluator`
- `reward-model`
- `grpo`
- `agent`
- `tests`

Recommended milestones:

- `M0 Specs`
- `M1 Dataset + Evaluator`
- `M2 Rationale + SFT Export`
- `M3 Reward Model GRPO`
- `M4 Supplier Selection Agent`

## GitHub Issue Creation Status

Current status:

- GitHub Issues were disabled on `kishorkukreja/Supplychain-FinRL` during the last creation attempt.
- No GitHub issue was created.
- Enable Issues in the repository settings before retrying issue creation.

Next action after Issues are enabled:

1. Create the M0 issue only.
2. Review and accept the five-document spec set.
3. Create M1 issues after M0 is accepted.
4. Do not create M2-M4 issues until their dependency gates are satisfied.
