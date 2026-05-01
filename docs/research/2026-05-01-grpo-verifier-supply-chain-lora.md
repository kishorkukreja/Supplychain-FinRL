# GRPO and LLM-Verifier Pipeline for Supply Chain LoRA

## Purpose

This document captures the agreed research direction for building a supply-chain-specific LoRA adapter using this FinRL supply-chain fork as a synthetic scenario engine, with a PARROT-inspired rationale pipeline extended by GRPO and LLM-as-verifier training.

The goal is not only to create synthetic instruction data. The goal is to create a grounded training loop where supply-chain decisions, negotiation outcomes, and procurement critiques are tied to observable outcomes, filtered for consistency, and then optimized with verifier-guided reinforcement learning.

## Core Idea

The baseline PARROT-style approach uses outcome-anchored rationale generation:

1. Start with cases that have known outcomes.
2. Ask a strong teacher model to generate structured rationales conditioned on the outcome.
3. Filter rationales by checking whether they predict the hidden outcome.
4. Distill the filtered rationales into a smaller student model.

The proposed extension adds GRPO and LLM-as-verifier:

1. The reward model is first bootstrapped with SFT.
2. The reward model is then improved with GRPO using a strong verifier model as the judge.
3. A negotiation or decision agent is then trained with GRPO against the calibrated reward model.
4. The verifier is used sparingly for reward-model training, periodic evaluation, and hard-case escalation.

This turns the system from one-shot imitation into a two-loop training architecture.

## Models

### Verifier

The verifier is a strong closed or frontier model such as Claude Opus or GPT-5. It is treated as the expensive judge, not the production model.

Responsibilities:

- Judge candidate rationales during reward-model GRPO.
- Check factual grounding against the scenario, transcript, and known outcome.
- Score rubric adherence and internal consistency.
- Evaluate held-out cases for drift and calibration.
- Optionally handle high-uncertainty production cases.

The verifier should not sit in the normal production path except for escalations.

### Reward Model

The reward model is a 7B-13B open-weights model trained to produce structured critiques, dimension scores, and an aggregate judgment.

Responsibilities:

- Evaluate supply-chain or procurement decisions.
- Produce multi-dimensional rationale and scores.
- Serve as the training reward for the downstream negotiation or decision agent.
- Run cheaply enough for production-scale scoring.

### Negotiation or Decision Agent

The agent is the model users interact with. It drafts procurement emails, recommends supplier actions, proposes counteroffers, or explains supply-chain decisions.

Responsibilities:

- Generate candidate actions or negotiation drafts.
- Optimize against the calibrated reward model.
- Respect factual, commercial, and policy constraints.

## Training Loops

### Loop 1: Reward Model GRPO

For each case, the reward model samples multiple candidate critiques:

```text
input case x -> reward model -> z1, z2, ..., zK
```

The verifier scores each candidate critique. Rewards should include:

- Outcome predictiveness.
- Factual grounding.
- Internal consistency.
- Rubric coverage.
- Specificity and actionability.
- Calibration of scores.
- Absence of generic procurement language.

GRPO then updates the reward model using group-relative rewards. The model is rewarded for producing critiques that beat its own alternatives for the same case.

This improves on PARROT's binary keep/drop filter by providing graded, comparative training signal.

### Loop 2: Agent GRPO

Once the reward model is calibrated, freeze it for the first agent-training pass.

For each case, the negotiation or decision agent samples multiple candidate outputs:

```text
input case x -> agent -> draft1, draft2, ..., draftK
```

The reward model scores each candidate across the rubric dimensions. GRPO updates the agent toward outputs that score better than other outputs for the same case.

The agent should not optimize a single scalar too early. The reward should preserve dimensions long enough to penalize tradeoffs such as improving price while damaging relationship quality or contractual completeness.

## Recommended First Use Cases

### Use Case 1: Supplier Selection Critique and Recommendation

This is the best first use case because the existing repo already has supplier selection mechanics and synthetic supplier data.

Input:

- Supplier quotes.
- Reliability.
- Lead time.
- Capacity.
- Disruption risk.
- Demand context.
- Buyer objective.

Output:

- Recommended supplier allocation.
- Structured rationale.
- Dimension scores.
- Risk flags.
- Expected cost and service-level tradeoff.

Why first:

- Close fit to existing `SupplierSelectionEnv`.
- Clear observable outcomes.
- Easy to simulate many cases.
- Strong basis for verifier consistency checks.

### Use Case 2: Inventory Replenishment Decision Support

Input:

- SKU demand history.
- Current inventory.
- Lead time.
- holding cost.
- stockout cost.
- disruption flag.
- service-level target.

Output:

- Reorder recommendation.
- Explanation of fill-rate and cost tradeoff.
- Risk assessment.
- Confidence/calibration score.

Why second:

- Existing single-SKU and multi-SKU environments are already available.
- Outcomes are measurable through cost, stockouts, fill rate, and inventory levels.
- Useful for generating large synthetic datasets.

### Use Case 3: Procurement Negotiation Draft Scoring

Input:

- Negotiation context.
- Supplier position.
- Buyer target.
- Previous offer/counteroffer.
- Candidate draft.

Output:

- Multi-dimensional critique.
- Scores for BATNA strength, anchoring, concession pacing, relationship management, and contractual completeness.
- Suggested revision.

Why third:

- High commercial value.
- Strong fit for LLM-as-judge and GRPO.
- Requires additional transcript and negotiation simulation machinery not currently present in the repo.

### Use Case 4: Production Scheduling Explanation

Input:

- Demand forecast.
- capacity.
- backlog.
- raw material cost.
- candidate production plan.

Output:

- Plan critique.
- Backlog/capacity/cost tradeoff.
- Recommended adjustment.

Why later:

- Existing environment support is present.
- Less directly tied to procurement negotiation than supplier selection.

## Initial Rubrics

### Supplier Selection Rubric

- Total landed cost.
- Reliability and service risk.
- Lead-time suitability.
- Capacity fit.
- Disruption resilience.
- Allocation diversity.
- Contractual or operational feasibility.

### Inventory Rubric

- Stockout risk.
- Holding-cost control.
- Demand uncertainty handling.
- Lead-time risk handling.
- Service-level alignment.
- Action feasibility.

### Negotiation Rubric

- BATNA awareness.
- Anchoring quality.
- Concession pacing.
- Relationship management.
- Contractual completeness.
- Factual grounding.
- Policy compliance.

## Data Pipeline

### Case Generation

Use this repo's supply-chain components to generate structured cases:

- `SupplyChainDataProcessor.generate_demand_data`
- `SupplyChainDataProcessor.generate_supplier_data`
- `SupplyChainDataProcessor.generate_production_data`
- `SingleSKUInventoryEnv`
- `MultiSKUInventoryEnv`
- `SupplierSelectionEnv`
- `ProductionSchedulingEnv`

Each generated case should include enough state to reconstruct the decision and enough outcome data to verify it.

### Outcome Capture

For each case, store:

- Scenario input.
- Candidate action or observed action.
- Environment outcome.
- KPI memory.
- Cost memory.
- Final label or ranking.

The outcome is the anchor. The verifier judges whether rationales are faithful to this outcome, but the verifier should not replace the outcome.

### Rationale Generation

Use a teacher model to generate structured critiques conditioned on the known outcome:

```text
scenario + observed outcome + rubric -> structured rationale + scores
```

This creates the initial PARROT-style dataset.

### Consistency Filtering

Hide the outcome and ask the verifier or predictor to recover it from the scenario and rationale:

```text
scenario + rationale -> predicted outcome
```

Keep rationales that predict the true outcome and discard rationales that are vague, contradictory, or inconsistent with the outcome.

### SFT Bootstrap

Fine-tune the reward model on the filtered dataset:

```text
scenario -> rationale + dimension scores + aggregate score
```

This gives the reward model a stable starting point before GRPO.

### Reward Model GRPO

For each scenario, sample multiple critiques from the reward model and ask the verifier to score them. Use group-relative advantages to train the reward model toward better critiques.

### Agent GRPO

Freeze the calibrated reward model initially. Train the agent to produce better decisions, drafts, or revisions using reward-model scores as the GRPO reward signal.

## Why GRPO Fits

GRPO is appropriate here because:

- It does not require a separate value model.
- It works naturally with multiple completions per case.
- It supports multi-objective reward functions.
- It is lighter than PPO for a client-deliverable system.
- It is more direct than DPO when the reward can be computed from rubric scores.

The core training signal is comparative: for the same case, which candidate critique or draft is best?

## Verifier Usage Policy

Use the expensive verifier only in controlled places:

1. Reward-model GRPO training.
2. Held-out reward-model evaluation.
3. Periodic drift checks.
4. Optional hard-case production escalation.

Avoid using the verifier for normal production scoring. The deployable artifact should be the distilled reward model and, later, the trained agent.

## Evaluation

### Reward Model Metrics

- Outcome prediction accuracy from generated rationale.
- Rank correlation with verifier judgments.
- Calibration error by category.
- Score variance under repeated sampling.
- Rubric coverage.
- Factual grounding error rate.
- Hallucination rate.

### Agent Metrics

- Reward-model score improvement over base model.
- Verifier win rate over base model on held-out cases.
- Human category-manager preference rate.
- Constraint violation rate.
- Factual grounding error rate.
- Robustness under disruptions and edge cases.

## Risks

### Reward Drift

If the reward model is updated while the agent is also being updated, the target can move. The first version should freeze the reward model during agent training.

### Verifier Bias

The verifier can inherit biases from its prompt, provider, or training data. Mitigate with structured rubrics, held-out cases, and human review.

### Reward Hacking

The agent may learn to produce text that sounds good to the reward model without improving the actual commercial decision. Mitigate with factual grounding checks, outcome-linked rewards, and verifier audits.

### Cost

Verifier calls during GRPO can be expensive. Start with a small calibrated corpus, use group sizes of 4-8 for early experiments, and scale only after the reward signal is validated.

### Infrastructure

GRPO requires open-weights models and training infrastructure. Closed models can serve as verifier or teacher, but not as trainable GRPO agents.

## Finalized Starting Scope

The first implementation track should focus on a reward model for supplier selection critique and recommendation.

This scope is narrow enough to build with the current repo and still representative of the larger methodology. It has clear structured inputs, measurable outcomes, and a natural multi-dimensional rubric.

### First Use Case

Supplier selection critique and recommendation is the first use case.

Inputs:

- Supplier options with price, reliability, lead time, capacity, and disruption risk.
- Demand context and buyer objective.
- Optional inventory pressure or service-level target.

Outputs:

- Recommended supplier or supplier allocation.
- Structured rationale.
- Dimension scores.
- Aggregate risk-adjusted score.
- Expected cost/service tradeoff.

Initial rubric:

- Total landed cost.
- Reliability and service risk.
- Lead-time suitability.
- Capacity fit.
- Disruption resilience.

These five dimensions should be used for the first version. Negotiation-specific dimensions such as BATNA and concession pacing should wait until transcript-style negotiation cases exist.

### First Deliverable

The first deliverable should be a reward-model dataset and evaluator, not a negotiation agent.

The deliverable should include:

- Synthetic supplier-selection cases.
- Outcome records from simulation.
- Teacher-generated rationales for a small pilot subset.
- Consistency-filtered SFT JSONL.
- Verifier scoring reports.
- Baseline metrics showing whether rationales predict outcomes.

Only after this dataset/evaluator milestone works should the project proceed to LoRA SFT, reward-model GRPO, and agent GRPO.

### Model Defaults for First Experiment

Use these defaults unless later constraints require changes:

- Reward model candidate: Qwen2.5-7B-Instruct or Qwen3-8B class open-weights model.
- Verifier: the strongest available frontier model through the user's API account.
- Teacher: same as verifier for the pilot, split later if cost or bias requires it.
- Initial group size for GRPO experiments: 4 candidates per case.
- Later group size after reward signal validation: 8 candidates per case.

The first pilot should avoid 50,000 verifier calls. Start with hundreds of cases, prove the scoring and filtering logic, then scale.

## Methodology To Start

### Milestone 1: Synthetic Case Factory

Generate supplier-selection cases from the existing supply-chain processor and environment.

Each case should serialize as JSON with:

- `case_id`
- `scenario`
- `supplier_options`
- `buyer_objective`
- `observed_or_optimal_action`
- `outcome`
- `kpis`
- `costs`
- `rubric`

The scenario should be self-contained so an LLM can judge it without reading code.

### Milestone 2: Outcome-Anchored Rationale Dataset

For a pilot subset, ask the teacher model to generate a structured rationale while showing the true outcome.

The target JSON shape should be:

```json
{
  "case_id": "supplier_case_000001",
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
  "recommendation": "...",
  "risk_flags": []
}
```

Scores should use a fixed range, such as 0-1 or 1-5, and the range should not change between datasets.

### Milestone 3: Consistency Filter

Hide the true outcome and ask the verifier to infer the selected supplier or allocation from the scenario plus rationale.

Keep a rationale only if:

- The inferred supplier/action matches the true or optimal action.
- The verifier finds no factual contradiction.
- The rationale cites scenario-specific facts.
- The scores align with the written critique.

Discard rationales that are generic, contradictory, or unable to predict the outcome.

### Milestone 4: SFT Dataset Export

Export filtered examples to JSONL for LoRA SFT.

Training format:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a supply-chain reward model that evaluates supplier-selection decisions using a structured rubric."
    },
    {
      "role": "user",
      "content": "<serialized supplier-selection case>"
    },
    {
      "role": "assistant",
      "content": "<structured rationale and scores>"
    }
  ]
}
```

### Milestone 5: Reward-Model GRPO Pilot

After SFT, run a small GRPO pilot.

For each case:

1. Sample 4 critiques from the reward model.
2. Ask the verifier to score each critique against the rubric and true outcome.
3. Convert verifier scores into group-relative rewards.
4. Update the reward model.
5. Evaluate on held-out cases after each run.

Do not train the negotiation agent in this milestone.

### Milestone 6: Agent GRPO

Train the agent only after the reward model is stable.

For each case:

1. The agent samples multiple supplier recommendations or negotiation drafts.
2. The frozen reward model scores each candidate.
3. GRPO updates the agent toward better candidates.
4. Held-out verifier evaluation checks whether reward-model gains transfer to verifier and human preference.

The reward model should stay frozen during the first agent-training pass to reduce reward drift.
