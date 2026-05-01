# Supplier Selection Dataset + Evaluator Spec

## Governance

Parent roadmap: `2026-05-01-supplier-selection-program-governance.md`

Related specs:

- Use case contract: `2026-05-01-supplier-selection-use-case.md`
- Reward model + GRPO: `2026-05-01-supplier-selection-reward-model-grpo.md`

This spec owns synthetic supplier-selection case generation, outcome evaluation, dataset splitting, and dataset quality reports.

## Purpose

Create grounded supplier-selection cases with known outcomes. These cases become the input data for teacher rationale generation, consistency filtering, and SFT export.

Version one uses synthetic-only data generated from existing repo supply-chain components.

## Data Source

Synthetic-only v1.

Use existing repo components:

- `finrl.meta.data_processors.processor_supply_chain.SupplyChainDataProcessor.generate_supplier_data`
- `finrl.meta.env_supply_chain.env_supplier_selection.SupplierSelectionEnv`

Do not ingest real procurement data in v1.

## Case Schema

Each generated case must be serialized as JSON.

Required fields:

```json
{
  "case_id": "supplier_case_000001",
  "case_type": "supplier_selection",
  "seed": 123,
  "buyer_objective": "Minimize risk-adjusted total cost while maintaining fill rate above 0.95.",
  "demand_context": {
    "demand_mean": 100.0,
    "demand_std": 20.0,
    "initial_inventory": 100.0,
    "initial_budget": 100000.0,
    "horizon_days": 60,
    "stockout_cost_rate": 0.1,
    "late_delivery_penalty_rate": 0.05,
    "quality_rejection_cost_rate": 0.1
  },
  "supplier_options": [
    {
      "supplier_id": "SUP_01",
      "base_price": 10.5,
      "reliability": 0.92,
      "lead_time_days": 2,
      "capacity": 150.0,
      "disruption_probability": 0.02
    }
  ],
  "candidate_actions": [
    {
      "action_id": "lowest_cost",
      "allocation": {
        "SUP_01": 1.0
      }
    }
  ],
  "observed_or_optimal_action": {
    "action_id": "balanced",
    "allocation": {
      "SUP_01": 0.65,
      "SUP_02": 0.10,
      "SUP_03": 0.25
    }
  },
  "outcome": {
    "total_cost": 0.0,
    "fill_rate": 0.0,
    "stockout_units": 0.0,
    "on_time_rate": 0.0,
    "current_inventory": 0.0,
    "risk_adjusted_cost": 0.0
  },
  "rubric": {
    "dimensions": [
      "total_landed_cost",
      "reliability_and_service_risk",
      "lead_time_suitability",
      "capacity_fit",
      "disruption_resilience"
    ],
    "score_range": [0.0, 1.0],
    "aggregation": "equal_weight_mean"
  },
  "metadata": {
    "generator_version": "v1",
    "selection_method": "risk_adjusted_best",
    "split": "train"
  }
}
```

## Candidate Supplier Action Policies

Each generated case must contain at least four candidate actions. Version one should generate these policies:

- `lowest_cost`: prefer the lowest base price supplier subject to capacity.
- `highest_reliability`: prefer the supplier with the highest reliability subject to capacity.
- `fastest_lead_time`: prefer the shortest lead-time supplier subject to capacity.
- `balanced`: allocate by a normalized blend of reliability, inverse price, inverse lead time, and capacity.
- `diversified`: spread allocation across suppliers while penalizing low reliability.

Allocations must:

- include all suppliers in the case,
- use values between `0.0` and `1.0`,
- sum to `1.0` within a fixed tolerance,
- be normalized before evaluation.

## Use Of SupplierSelectionEnv

For each case:

1. Instantiate `SupplierSelectionEnv` with the generated supplier and demand parameters.
2. Evaluate each candidate action using the same seed and horizon.
3. Capture cost and KPI memories.
4. Compute aggregate outcome metrics for each candidate action.
5. Select the observed or optimal action using risk-adjusted cost.

The environment should not be modified for the first dataset milestone unless a discovered bug prevents deterministic evaluation.

## Outcome Capture

For each candidate action, capture:

- `total_cost`
- `procurement_cost`
- `late_delivery_penalty`
- `stockout_cost`
- `quality_rejection_cost`
- `fill_rate`
- `stockout_units`
- `on_time_rate`
- `current_inventory`
- `risk_adjusted_cost`

The selected `observed_or_optimal_action` is the candidate with the lowest `risk_adjusted_cost`.

## Risk-Adjusted Best-Action Selection

Version one uses fixed weights:

```text
risk_adjusted_cost =
  total_cost
  + stockout_units * 10.0
  - fill_rate * 100.0
  - on_time_rate * 50.0
```

These weights must be included in generated metadata. Later versions may make the weights configurable, but v1 uses constants to keep calibration stable.

## Dataset Split Rules

Splits must be deterministic by `case_id` hash.

Default split:

- train: 80%
- validation: 10%
- test: 10%

Runtime randomness must not change which split a case belongs to.

## Dataset Quality Reports

The evaluator must produce these local JSON reports:

- `case_generation_summary.json`
- `candidate_action_summary.json`
- `outcome_selection_summary.json`
- `sft_input_summary.json`

Reports must include:

- generated case count,
- invalid case count,
- split counts,
- candidate action count distribution,
- selected action distribution,
- score and outcome distributions,
- duplicate or near-duplicate case count,
- allocation validation failures,
- missing field failures.

## Local Artifact Locations

Generated artifacts should go under:

```text
examples/supply_chain/supplier_selection_llm/outputs/
```

Recommended layout:

```text
cases/
candidate_outcomes/
reports/
sft/
```

Generated artifacts should not be committed by default.

## Unit Test Requirements

Tests must not call external APIs.

Required tests:

- deterministic case generation for a fixed seed,
- generated case schema validation,
- allocation values are in range,
- allocation sums equal `1.0` within tolerance,
- candidate actions include the required policies,
- outcome evaluation returns required metrics,
- best-action selection is deterministic,
- split assignment is deterministic by case ID,
- reports include required fields.

## Acceptance Criteria

The dataset + evaluator milestone is complete when:

- At least 100 valid synthetic cases can be generated locally.
- Each case has at least four candidate actions.
- Each selected action is reproducible under fixed seed.
- Dataset reports are generated locally.
- Unit tests pass without external network calls.
- The output case records can be consumed by the reward-model spec without additional product decisions.
