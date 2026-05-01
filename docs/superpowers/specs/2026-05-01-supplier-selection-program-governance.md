# Supplier Selection Program Governance

## Purpose

This document is the governing roadmap for the supplier-selection LoRA and agent program. It owns oversight, sequencing, status, and links to the child specs. It is the implementation source of truth for program structure.

The research note at `docs/research/2026-05-01-grpo-verifier-supply-chain-lora.md` is background rationale only. Implementation decisions must come from this governing roadmap and the child specs linked below.

## Program Goal

Build a supply-chain-specific supplier-selection system in stages:

1. Generate synthetic supplier-selection cases with known outcomes.
2. Create and evaluate outcome-anchored rationale data.
3. Export LoRA-ready SFT data for a reward model.
4. Pilot GRPO to improve the reward model with an external verifier.
5. Later build a supplier-selection agent with orchestrator, executor, and reward-model verifier roles.

The first implementation deliverable is a reward-model dataset and evaluator, not a production agent.

## Current Phase

Current phase: `M0 Specs Accepted`

The five-document spec set has been reviewed against the M0 gate and is accepted for M1 Dataset + Evaluator issue creation. Implementation should still start from milestone-scoped GitHub issues that link back to the approved specs.

## Source-Of-Truth Document Map

| Document | File | Owns |
| --- | --- | --- |
| Governance roadmap | `2026-05-01-supplier-selection-program-governance.md` | Program oversight, milestones, dependency order, tracking model |
| Use case contract | `2026-05-01-supplier-selection-use-case.md` | User-facing supplier-selection behavior and rubric |
| Dataset + evaluator spec | `2026-05-01-supplier-selection-dataset-evaluator.md` | Synthetic cases, outcomes, dataset reports, SFT input records |
| Reward model + GRPO spec | `2026-05-01-supplier-selection-reward-model-grpo.md` | Teacher rationales, consistency filtering, SFT target, GRPO pilot |
| Agent architecture spec | `2026-05-01-supplier-selection-agent-architecture.md` | Later orchestrator-executor-verifier agent architecture |
| Research note | `../../research/2026-05-01-grpo-verifier-supply-chain-lora.md` | Background methodology only |

Child specs may reference each other, but each child spec has one ownership area. If requirements conflict, this precedence applies:

1. Governance roadmap for sequencing and scope.
2. Child spec for its owned subsystem.
3. Research note for context only.

## Dependency Graph

```text
research note
  -> governing roadmap
      -> use case contract
          -> dataset + evaluator spec
              -> reward model + GRPO spec
                  -> agent architecture spec
```

Implementation dependency order:

```text
M0 Specs
  -> M1 Dataset + Evaluator
      -> M2 Rationale + SFT Export
          -> M3 Reward Model GRPO
              -> M4 Supplier Selection Agent
```

The agent must not be implemented before the reward-model verifier interface and evaluation path exist.

## Milestones

| Milestone | Goal | Exit Gate |
| --- | --- | --- |
| M0 Specs | Write and review this spec set | All five docs exist, link to each other, and have no unresolved product decisions |
| M1 Dataset + Evaluator | Generate deterministic synthetic supplier-selection cases and outcome reports | Local run creates 100+ valid cases and dataset quality summaries |
| M2 Rationale + SFT Export | Generate or mock teacher rationales, filter them, and export chat JSONL | Filter and export work with mocked LLM clients and deterministic splits |
| M3 Reward Model GRPO | Pilot reward-model GRPO scoring loop | K-candidate reward scoring works with mocks before paid verifier calls |
| M4 Supplier Selection Agent | Build orchestrator-executor-verifier agent | Agent uses frozen reward-model verifier and can retry or escalate |

## GitHub Issue Tracking Model

Specs define contracts. GitHub issues define implementation tasks.

Issue rules:

- Each issue must link to the relevant spec section.
- Each issue must include acceptance criteria and verification commands.
- Issues should be milestone-sized, not file-sized.
- The governing roadmap records issue IDs after issues are created.

Recommended labels:

- `spec`
- `dataset`
- `evaluator`
- `reward-model`
- `grpo`
- `agent`
- `tests`

Initial issue tracking:

| Issue | Milestone | Spec | Tracking |
| --- | --- | --- | --- |
| Docs: finalize supplier-selection spec set | M0 | Governance + all child specs | [#1](https://github.com/kishorkukreja/Supplychain-FinRL/issues/1) |
| Dataset: supplier-selection case factory | M1 | Dataset + evaluator | Create after #1 is closed |
| Dataset: candidate action and outcome evaluator | M1 | Dataset + evaluator | Create after #1 is closed |
| Dataset: risk-adjusted best-action selection | M1 | Dataset + evaluator | Create after #1 is closed |
| Evaluator: dataset quality reports | M1 | Dataset + evaluator | Create after #1 is closed |
| LLM interfaces: teacher and verifier mocks | M2 | Reward model + GRPO | Later milestone |
| Reward data: rationale schema and consistency filter | M2 | Reward model + GRPO | Later milestone |
| Export: SFT JSONL | M2 | Reward model + GRPO | Later milestone |
| Reward model: GRPO pilot scaffold | M3 | Reward model + GRPO | Later milestone |
| Agent: orchestrator-executor-verifier interfaces | M4 | Agent architecture | Later milestone |

## Acceptance Gates

### M0 Specs Gate

- All five spec docs exist.
- Governance links to all child specs.
- Child specs link back to governance.
- Each child spec has one clear ownership area.
- The first implementation milestone can be converted into GitHub issues.
- The agent is defined but does not pull agent implementation into M1.

M0 review result on 2026-05-01: accepted.

Review notes:

- The governance roadmap links all four child specs and the research note.
- Each child spec links back to this roadmap and declares its ownership boundary.
- The use case contract defines supplier selection recommend + critique.
- The dataset + evaluator spec is implementable without unresolved product decisions.
- The reward model + GRPO spec keeps teacher, external verifier, reward model, and GRPO responsibilities separate.
- The agent architecture spec defines orchestrator, executor, verifier, and optional external escalation without authorizing agent implementation in M1.
- The research note is referenced as background only.
- M1 Dataset + Evaluator issues can be created from the accepted dataset + evaluator spec.

### M1 Dataset + Evaluator Gate

- At least 100 synthetic supplier-selection cases can be generated locally.
- Case generation is deterministic with a fixed seed.
- Each case has at least four candidate actions and one selected best action.
- Dataset reports are generated locally.
- Unit tests do not call paid LLM APIs.

### M2 Rationale + SFT Export Gate

- Rationale and verifier interfaces are mockable.
- Consistency filtering keeps and drops examples deterministically.
- SFT JSONL exports valid chat messages.
- Train, validation, and test splits are deterministic by case ID.

### M3 Reward Model GRPO Gate

- GRPO reward computation works with mocked verifier scores.
- K-candidate grouping is implemented.
- Held-out evaluation is defined before any paid verifier run.

### M4 Agent Gate

- Orchestrator, executor, and verifier boundaries are implemented.
- The reward model is frozen for the first agent pass.
- External verifier escalation is optional and controlled.

## Decision Log

| Date | Decision |
| --- | --- |
| 2026-05-01 | First use case is supplier selection recommend + critique. |
| 2026-05-01 | First data source is synthetic only. |
| 2026-05-01 | First deliverable is reward-model dataset + evaluator, not the agent. |
| 2026-05-01 | Specs are source-of-truth contracts; GitHub issues are implementation tasks. |
| 2026-05-01 | Use five documents: governance plus four child specs. |
| 2026-05-01 | The reward model later acts as verifier inside the supplier-selection agent. |
| 2026-05-01 | M0 Specs gate accepted; M1 Dataset + Evaluator issue creation is unblocked after issue #1 is closed. |

## Status Table

| Area | Status | Notes |
| --- | --- | --- |
| Governance roadmap | Accepted | Reviewed for M0 gate |
| Use case contract | Accepted | Defines recommend + critique behavior |
| Dataset + evaluator | Accepted | Defines synthetic-only v1 |
| Reward model + GRPO | Accepted | Defines SFT and GRPO pilot boundaries |
| Agent architecture | Accepted | Later-stage architecture only |
| GitHub issues | M0 created | [#1](https://github.com/kishorkukreja/Supplychain-FinRL/issues/1) tracks this review; create M1 issues after #1 is closed |

## Implementation Rule

Do not implement directly from the research note. Do not implement from memory. Implementation must start from a GitHub issue that links to the relevant approved spec section.
