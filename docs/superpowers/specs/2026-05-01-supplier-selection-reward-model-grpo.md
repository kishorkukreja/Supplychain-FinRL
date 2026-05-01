# Supplier Selection Reward Model + GRPO Spec

## Governance

Parent roadmap: `2026-05-01-supplier-selection-program-governance.md`

Related specs:

- Use case contract: `2026-05-01-supplier-selection-use-case.md`
- Dataset + evaluator: `2026-05-01-supplier-selection-dataset-evaluator.md`
- Agent architecture: `2026-05-01-supplier-selection-agent-architecture.md`

This spec owns teacher rationale generation, consistency filtering, SFT export target, reward-model role, and the reward-model GRPO pilot.

## Reward Model Role

The reward model is the first trainable LoRA artifact.

It receives a supplier-selection case and returns:

- recommendation,
- structured rationale,
- five rubric scores,
- overall score,
- risk flags.

The reward model later becomes the verifier inside the supplier-selection agent. It is not the same as the external frontier verifier.

## External Teacher And Verifier Role

Version one uses an external frontier model as teacher and verifier.

Teacher use:

- sees the case and the selected outcome,
- writes an outcome-anchored rationale,
- produces structured scores and recommendation.

Verifier use:

- checks rationale consistency with the hidden outcome,
- scores candidate rationales during GRPO,
- evaluates held-out examples,
- may later handle hard-case escalation.

The external verifier must not be required for unit tests.

## Outcome-Anchored Rationale Generation

The teacher prompt must include:

- full supplier-selection case,
- candidate actions,
- selected observed or optimal action,
- selected action outcome metrics,
- rubric definitions,
- required JSON schema.

The teacher must return valid JSON only.

The teacher is allowed to use the outcome when writing the rationale. This is intentional hindsight rationalization. The later consistency filter decides whether the rationale is predictive and grounded.

## Rationale JSON Schema

Required teacher output:

```json
{
  "case_id": "supplier_case_000001",
  "recommendation": {
    "allocation": {
      "SUP_01": 0.65,
      "SUP_02": 0.10,
      "SUP_03": 0.25
    },
    "summary": "..."
  },
  "rationale": {
    "total_landed_cost": "...",
    "reliability_and_service_risk": "...",
    "lead_time_suitability": "...",
    "capacity_fit": "...",
    "disruption_resilience": "..."
  },
  "scores": {
    "total_landed_cost": 0.0,
    "reliability_and_service_risk": 0.0,
    "lead_time_suitability": 0.0,
    "capacity_fit": 0.0,
    "disruption_resilience": 0.0,
    "overall": 0.0
  },
  "risk_flags": [],
  "outcome_prediction": {
    "predicted_best_action_id": "balanced",
    "reason": "..."
  }
}
```

Validation rules:

- all required keys must exist,
- all scores must be in `[0.0, 1.0]`,
- allocation must sum to `1.0` within tolerance,
- supplier IDs must match the case,
- rationale strings must cite case-specific facts,
- output must be parseable JSON.

## Consistency Filtering

The consistency filter hides the selected action and selected outcome. It gives the verifier:

- case input,
- candidate actions,
- teacher rationale,
- teacher scores.

Verifier output:

```json
{
  "case_id": "supplier_case_000001",
  "predicted_best_action_id": "balanced",
  "is_consistent": true,
  "factual_grounding_score": 0.0,
  "rubric_alignment_score": 0.0,
  "score_consistency_score": 0.0,
  "specificity_score": 0.0,
  "failure_reasons": []
}
```

Keep an example only if:

- predicted best action matches the selected action,
- `is_consistent` is true,
- all verifier scores are at least `0.75`,
- rationale JSON passes validation,
- no failure reason is severity-blocking.

Discard examples that are generic, contradictory, impossible, or unable to predict the selected action.

## SFT JSONL Format

Filtered examples must export as chat JSONL.

Record shape:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a supply-chain reward model. Evaluate supplier-selection decisions using the provided structured rubric. Return valid JSON only."
    },
    {
      "role": "user",
      "content": "Serialized supplier-selection case JSON with supplier options, candidate actions, and rubric, excluding the selected outcome."
    },
    {
      "role": "assistant",
      "content": "Valid JSON containing recommendation, rationale, scores, and risk flags."
    }
  ],
  "metadata": {
    "case_id": "supplier_case_000001",
    "split": "train",
    "source": "synthetic_supplier_selection_v1"
  }
}
```

The user message must not reveal the selected outcome. The assistant message is the filtered teacher output.

## LoRA SFT Target

Default reward-model candidate:

- Qwen2.5-7B-Instruct or a Qwen3-8B class open-weights model.

The SFT objective is:

```text
supplier-selection case -> recommendation + rationale + scores + risk flags
```

SFT training itself is not part of the first implementation milestone. The first milestone prepares valid data and evaluator outputs.

## GRPO Pilot Design

GRPO starts only after SFT data export is validated.

For each case:

1. The reward model samples `K` candidate critiques.
2. The external verifier scores each candidate.
3. Scores are converted into scalar rewards.
4. Group-relative advantages are computed within the case.
5. The reward model is updated toward verifier-preferred critiques.

Initial `K`: `4`

Later `K` after reward signal validation: `8`

The GRPO pilot must be scaffolded so verifier calls can be mocked.

## Verifier Reward Dimensions

Verifier reward should combine:

- outcome predictiveness,
- factual grounding,
- rubric coverage,
- score calibration,
- specificity and actionability,
- JSON validity,
- allocation feasibility.

Suggested scalar reward:

```text
reward =
  0.25 * outcome_predictiveness
  + 0.20 * factual_grounding
  + 0.20 * rubric_coverage
  + 0.15 * score_calibration
  + 0.10 * specificity
  + 0.10 * feasibility
```

Invalid JSON receives a hard penalty and should not be selected for SFT.

## Mocking Strategy For Tests

All teacher and verifier clients must be interface-driven.

Tests must use:

- deterministic fake teacher outputs,
- deterministic fake verifier judgments,
- malformed output fixtures,
- keep/drop examples.

No unit test may require paid LLM API calls or network access.

## Evaluation Metrics

Reward-data metrics:

- teacher rationale count,
- valid JSON rate,
- consistency filter pass rate,
- predicted-best-action accuracy,
- average verifier scores,
- pass/fail reason distribution,
- rubric score distribution,
- invalid allocation rate.

Reward-model metrics after SFT or GRPO:

- held-out outcome prediction accuracy,
- rank correlation with verifier judgments,
- calibration error by dimension,
- repeated-sampling score variance,
- factual grounding error rate,
- hallucination or unsupported-claim rate.

## Cost Controls

Verifier calls must be budgeted and controlled.

Required controls:

- dry-run mode with mocks,
- maximum case count per run,
- maximum verifier calls per run,
- cached verifier responses by prompt hash,
- pilot defaults in the hundreds of cases, not tens of thousands,
- no automatic large-scale verifier run without explicit approval.

## Acceptance Criteria

This spec is ready for implementation when:

- teacher and verifier responsibilities are distinct,
- rationale schema is stable,
- consistency filter keep/drop criteria are explicit,
- SFT JSONL format is defined,
- GRPO pilot can run with mocked verifier scores,
- evaluation metrics are defined before model training starts.
