# Supply Chain RL Conversion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this task-by-task.

**Goal:** Convert the FinRL fork into an additive Supply Chain RL framework while keeping the SB3 agent layer unchanged.

**Architecture:** Add Gymnasium supply-chain environments, synthetic data generation, config constants, example pipelines, and tests. Reuse `DRLAgent`, `DummyVecEnv`, and the existing train/test/evaluate pattern.

**Tech Stack:** Python, Gymnasium, NumPy, Pandas, Matplotlib, Stable Baselines 3, pytest.

---

## Tasks

- [ ] Add supply-chain config constants in `finrl/config_supply_chain.py`.
- [ ] Add four Gymnasium supply-chain environments in `finrl/meta/env_supply_chain/`.
- [ ] Add synthetic data generation in `finrl/meta/data_processors/processor_supply_chain.py`.
- [ ] Add focused pytest coverage for environments and processor.
- [ ] Add Bundle 1 inventory example scripts.
- [ ] Add Bundle 2 supplier and production example scripts.
- [ ] Run focused verification commands.

## Verification Commands

```bash
pytest unit_tests/environments/test_supply_chain_envs.py -v
pytest unit_tests/data_processors/test_supply_chain_processor.py -v
python examples/supply_chain/bundle1_inventory/1_data.py
python examples/supply_chain/bundle1_inventory/2_train.py
python examples/supply_chain/bundle1_inventory/3_evaluate.py
```

## Acceptance Criteria

- Environments satisfy Gymnasium and Stable Baselines 3 vectorization contracts.
- Rewards and observations remain finite.
- Synthetic data outputs contain required schemas and indicators.
- Bundle 1 scripts generate data, train smoke models, and produce metrics/plots.
- Existing finance model wrappers and config files remain unchanged.
