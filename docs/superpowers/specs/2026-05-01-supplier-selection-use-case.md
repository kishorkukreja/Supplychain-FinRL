# Supplier Selection Use Case Contract

## Governance

Parent roadmap: `2026-05-01-supplier-selection-program-governance.md`

This spec owns the user-facing behavior for the first supplier-selection use case. It does not own dataset generation, reward-model training, or agent orchestration internals.

## First Use Case

The first use case is supplier selection recommend + critique.

Given supplier options and demand context, the system recommends a supplier allocation and explains the recommendation with a structured rubric.

The output must be useful both to:

- a human supply-chain user reviewing the decision, and
- a reward-model training pipeline that needs structured target outputs.

## User-Facing Behavior

The system receives a supplier-selection case and returns:

- recommended supplier allocation,
- short recommendation summary,
- five-dimension rationale,
- five dimension scores,
- overall score,
- risk flags.

The recommendation may allocate to one supplier or split allocation across suppliers. The allocation must sum to `1.0` within tolerance and must be feasible against supplier capacity when capacity is provided.

## Input Fields

Required input fields:

- `buyer_objective`: text description of the procurement objective.
- `demand_context.demand_mean`: expected demand.
- `demand_context.demand_std`: demand uncertainty.
- `demand_context.initial_inventory`: inventory at decision start.
- `demand_context.initial_budget`: available budget.
- `demand_context.horizon_days`: simulated planning horizon.
- `supplier_options`: one or more supplier records.

Required supplier fields:

- `supplier_id`
- `base_price`
- `reliability`
- `lead_time_days`
- `capacity`
- `disruption_probability`

Optional input fields:

- `service_level_target`
- `stockout_cost_rate`
- `late_delivery_penalty_rate`
- `quality_rejection_cost_rate`
- `category`
- `notes`

## Output Fields

Required output fields:

- `recommendation.allocation`
- `recommendation.summary`
- `rationale.total_landed_cost`
- `rationale.reliability_and_service_risk`
- `rationale.lead_time_suitability`
- `rationale.capacity_fit`
- `rationale.disruption_resilience`
- `scores.total_landed_cost`
- `scores.reliability_and_service_risk`
- `scores.lead_time_suitability`
- `scores.capacity_fit`
- `scores.disruption_resilience`
- `scores.overall`
- `risk_flags`

Scores must use the range `0.0` to `1.0`, where `1.0` is best.

## Example Request

```json
{
  "buyer_objective": "Minimize risk-adjusted total cost while maintaining fill rate above 0.95.",
  "demand_context": {
    "demand_mean": 100.0,
    "demand_std": 20.0,
    "initial_inventory": 100.0,
    "initial_budget": 100000.0,
    "horizon_days": 60,
    "service_level_target": 0.95
  },
  "supplier_options": [
    {
      "supplier_id": "SUP_01",
      "base_price": 10.5,
      "reliability": 0.92,
      "lead_time_days": 2,
      "capacity": 150.0,
      "disruption_probability": 0.02
    },
    {
      "supplier_id": "SUP_02",
      "base_price": 9.8,
      "reliability": 0.82,
      "lead_time_days": 4,
      "capacity": 120.0,
      "disruption_probability": 0.04
    },
    {
      "supplier_id": "SUP_03",
      "base_price": 11.2,
      "reliability": 0.96,
      "lead_time_days": 3,
      "capacity": 80.0,
      "disruption_probability": 0.01
    }
  ]
}
```

## Example Response

```json
{
  "recommendation": {
    "allocation": {
      "SUP_01": 0.65,
      "SUP_02": 0.10,
      "SUP_03": 0.25
    },
    "summary": "Use SUP_01 as the primary supplier, preserve a smaller allocation to SUP_03 for reliability, and limit SUP_02 because its lower price is offset by weaker service risk."
  },
  "rationale": {
    "total_landed_cost": "SUP_02 has the lowest unit price, but the allocation should remain limited because lower reliability and longer lead time increase expected penalty and stockout exposure.",
    "reliability_and_service_risk": "SUP_01 and SUP_03 provide stronger service protection than SUP_02. A split between them supports the fill-rate objective.",
    "lead_time_suitability": "SUP_01 has the shortest lead time and should carry most near-term volume. SUP_03 is acceptable as backup, while SUP_02 is slower.",
    "capacity_fit": "The allocation respects the available capacities and avoids depending on SUP_03 beyond its lower capacity.",
    "disruption_resilience": "The recommendation avoids a single-supplier concentration and keeps backup coverage with the most reliable supplier."
  },
  "scores": {
    "total_landed_cost": 0.78,
    "reliability_and_service_risk": 0.86,
    "lead_time_suitability": 0.88,
    "capacity_fit": 0.84,
    "disruption_resilience": 0.82,
    "overall": 0.84
  },
  "risk_flags": ["limited_low_cost_supplier_due_to_service_risk"]
}
```

## Rubric Dimensions

### Total Landed Cost

Measures procurement cost, late-delivery penalty, quality rejection cost, and stockout cost.

High-scoring behavior:

- Considers expected total cost, not only unit price.
- Explains when cheap suppliers create hidden service cost.
- Mentions cost tradeoffs using case-specific facts.

### Reliability And Service Risk

Measures whether the allocation protects service levels and fill rate.

High-scoring behavior:

- Favors reliable suppliers when demand uncertainty or stockout cost is high.
- Connects reliability to fill-rate and stockout exposure.
- Avoids unsupported confidence when reliability is weak.

### Lead-Time Suitability

Measures whether supplier lead times fit inventory pressure and demand timing.

High-scoring behavior:

- Penalizes slow suppliers when inventory pressure is high.
- Accepts longer lead time only when justified by other dimensions.
- Connects lead time to stockout risk.

### Capacity Fit

Measures whether the recommendation can be fulfilled by supplier capacity.

High-scoring behavior:

- Respects capacity limits.
- Splits allocation when one supplier cannot satisfy demand.
- Avoids impossible or over-concentrated allocations.

### Disruption Resilience

Measures exposure to disruption probability and concentration risk.

High-scoring behavior:

- Avoids excessive dependence on fragile suppliers.
- Uses backup allocation where appropriate.
- Mentions disruption exposure explicitly.

## Overall Score

Version one uses equal weighting:

```text
overall = mean(
  total_landed_cost,
  reliability_and_service_risk,
  lead_time_suitability,
  capacity_fit,
  disruption_resilience
)
```

Buyer-objective-specific weighting is out of scope for version one.

## Non-Goals

- No negotiation email drafting.
- No real procurement data ingestion.
- No production deployment.
- No UI.
- No human category-manager review workflow.
- No buyer-objective-specific score weights in v1.

## Success Criteria

This use case contract is satisfied when:

- Inputs and outputs are represented in the dataset and reward-model specs.
- The five rubric dimensions are used consistently across all child specs.
- Example request and response are sufficient to guide implementation.
- The first implementation milestone can generate synthetic cases that match this contract.
