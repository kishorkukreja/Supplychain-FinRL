# Supplier Selection Agent Architecture Spec

## Governance

Parent roadmap: `2026-05-01-supplier-selection-program-governance.md`

Related specs:

- Use case contract: `2026-05-01-supplier-selection-use-case.md`
- Dataset + evaluator: `2026-05-01-supplier-selection-dataset-evaluator.md`
- Reward model + GRPO: `2026-05-01-supplier-selection-reward-model-grpo.md`

This spec owns the later supplier-selection agent architecture. It does not authorize agent implementation before the reward-model verifier is stable.

## Purpose

Define the eventual supplier-selection agent that uses the trained reward model as a verifier.

The agent follows an orchestrator-executor-verifier architecture:

```text
input case
  -> orchestrator
      -> executor generates candidate recommendations
      -> reward-model verifier scores candidates
      -> orchestrator selects, retries, or escalates
  -> final recommendation
```

## Orchestrator Role

The orchestrator controls the workflow.

Responsibilities:

- validate user or workflow input,
- normalize the case into the use-case contract,
- request one or more candidate recommendations from the executor,
- request verifier scores for each candidate,
- select the best passing candidate,
- request revision if candidate quality is below threshold,
- escalate to the external verifier when configured and uncertainty is high,
- return the final recommendation and rationale.

The orchestrator must not invent supplier facts. It can only use provided case data, generated synthetic case data, or executor/verifier outputs.

## Executor Role

The executor proposes supplier allocations and business-facing summaries.

Responsibilities:

- generate one or more supplier allocation candidates,
- keep allocations in range,
- respect supplier IDs from the case,
- respect supplier capacity constraints,
- provide concise explanation text,
- avoid unsupported claims.

Initial executor options:

- rule-based executor using candidate policies from the dataset spec,
- LoRA-tuned open model after SFT data exists,
- GRPO-trained executor after reward-model verifier stabilization.

The first agent version should prefer a simple executor and focus on verifier quality.

## Reward-Model Verifier Role

The verifier is the trained reward model from the reward-model spec.

Responsibilities:

- score each executor candidate across the five rubric dimensions,
- return overall score,
- return failure reasons,
- return risk flags,
- reject invalid or infeasible recommendations,
- provide structured critique that the orchestrator can use for retry.

The reward-model verifier is the normal production verifier. The external frontier verifier is not the default production path.

## External Verifier Escalation Role

The external verifier is optional and expensive.

Use it only when:

- reward-model verifier scores are near decision threshold,
- executor candidates disagree strongly,
- generated output fails grounding checks repeatedly,
- user or workflow explicitly requests high-assurance review,
- periodic evaluation or drift checks are running.

Escalation must be configurable and disabled by default for local tests.

## Agent Decision Flow

Default flow:

```text
1. Orchestrator receives supplier-selection request.
2. Orchestrator validates required fields.
3. Executor generates K candidate recommendations.
4. Reward-model verifier scores each candidate.
5. Orchestrator selects the highest-scoring feasible candidate.
6. If no candidate passes, orchestrator asks executor for revision.
7. If retry limit is reached, orchestrator returns failure or escalates if enabled.
8. Final response includes recommendation, rationale, scores, and risk flags.
```

Default candidate count: `K = 4`

Default retry limit: `2`

Default pass threshold: `overall >= 0.75` and no blocking failure reason.

## Retry And Revision Behavior

The orchestrator should retry when:

- allocation does not sum to `1.0`,
- supplier ID is unknown,
- capacity is exceeded,
- overall score is below threshold,
- any rubric dimension is below `0.50`,
- verifier reports unsupported factual claims.

The retry prompt should include verifier failure reasons and request a revised allocation. It should not reveal hidden evaluation data that would not be available in production.

## Agent GRPO After Reward Model Stabilization

Agent GRPO is a later phase.

Preconditions:

- reward-model verifier has passed held-out evaluation,
- verifier outputs are stable under repeated sampling,
- dataset/evaluator pipeline is reproducible,
- external verifier audits show reward-model alignment.

Agent GRPO loop:

1. Executor samples `K` recommendations for a case.
2. Frozen reward-model verifier scores each recommendation.
3. Group-relative rewards are computed.
4. Executor is updated toward higher-scoring recommendations.
5. Held-out external verifier checks whether gains transfer.

The reward model should remain frozen during the first agent GRPO pass to reduce reward drift.

## Boundaries Between Agent And Reward Model

The reward model:

- judges recommendations,
- produces critique and scores,
- rejects infeasible candidates,
- does not own orchestration,
- does not own user interaction state.

The agent:

- manages workflow,
- generates or revises recommendations,
- calls the verifier,
- decides retry or escalation,
- returns final response.

The external verifier:

- judges reward-model outputs during training and audits,
- handles optional hard-case escalation,
- does not replace the reward model in normal operation.

## Non-Goals For V1

- No negotiation email drafting.
- No live supplier systems integration.
- No procurement workflow UI.
- No real procurement data ingestion.
- No automatic paid external verifier calls.
- No agent GRPO before reward-model validation.

## Acceptance Criteria

This architecture is ready for implementation when:

- orchestrator, executor, and verifier responsibilities are distinct,
- the reward model is clearly the normal verifier,
- external verifier escalation is optional and controlled,
- retry behavior is deterministic,
- agent implementation is blocked until reward-model verifier readiness is achieved.
