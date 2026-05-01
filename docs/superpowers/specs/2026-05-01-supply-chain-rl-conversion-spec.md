# Supply Chain RL Conversion Spec

## Goal

Convert this FinRL fork into an additive Supply Chain RL framework while preserving the Stable Baselines 3 agent layer and the train, test, evaluate workflow.

## Architecture

The conversion adds supply-chain-specific environment, data, configuration, examples, and tests. Existing finance modules and agent wrappers remain unchanged. New environments use Gymnasium and expose FinRL-compatible helper methods so `finrl.agents.stablebaselines3.models.DRLAgent` can train and evaluate them without agent-layer changes.

## Functional Requirements

- Add four environments under `finrl/meta/env_supply_chain/`:
  - `SingleSKUInventoryEnv`
  - `MultiSKUInventoryEnv`
  - `SupplierSelectionEnv`
  - `ProductionSchedulingEnv`
- Each environment must:
  - Use `gymnasium.Env`.
  - Return `(observation, info)` from `reset()`.
  - Return `(observation, reward, terminated, truncated, info)` from `step()`.
  - Use continuous `spaces.Box(low=0, high=1, ...)` actions.
  - Return finite `float32` observations.
  - Return reward as negative supply-chain cost.
  - Maintain `actions_memory`, `kpi_memory`, and `cost_memory`.
  - Implement `get_sb_env()`, `save_asset_memory()`, and `save_action_memory()`.
- Add `SupplyChainDataProcessor` under `finrl/meta/data_processors/processor_supply_chain.py`.
- Add supply-chain constants and model hyperparameters in `finrl/config_supply_chain.py`.
- Add two example bundles under `examples/supply_chain/`.
- Add pytest coverage under `unit_tests/`.

## Acceptance Criteria

- The new unit tests for environments and data processors pass.
- Bundle 1 data generation, smoke training, and evaluation scripts run locally.
- Existing finance agent code is not modified.
- Existing finance config is not modified.
