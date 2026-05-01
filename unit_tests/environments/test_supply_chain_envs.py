from __future__ import annotations

import numpy as np

from finrl.meta.env_supply_chain import MultiSKUInventoryEnv
from finrl.meta.env_supply_chain import ProductionSchedulingEnv
from finrl.meta.env_supply_chain import SingleSKUInventoryEnv
from finrl.meta.env_supply_chain import SupplierSelectionEnv


def _assert_gymnasium_contract(env, expected_shape):
    obs, info = env.reset(seed=123)
    assert obs.shape == expected_shape
    assert obs.dtype == np.float32
    assert np.isfinite(obs).all()
    assert isinstance(info, dict)

    action = np.full(env.action_space.shape, 0.5, dtype=np.float32)
    next_obs, reward, terminated, truncated, step_info = env.step(action)
    assert next_obs.shape == expected_shape
    assert next_obs.dtype == np.float32
    assert np.isfinite(next_obs).all()
    assert np.isfinite(reward)
    assert isinstance(terminated, bool)
    assert truncated is False
    assert isinstance(step_info, dict)
    assert len(env.actions_memory) == 1
    assert len(env.kpi_memory) == 1
    assert len(env.cost_memory) == 1


def test_single_sku_inventory_env_contract_and_termination():
    env = SingleSKUInventoryEnv(horizon_days=3, demand_mean=20.0, demand_std=2.0)
    _assert_gymnasium_contract(env, (6,))

    terminated = False
    while not terminated:
        _, _, terminated, truncated, _ = env.step(np.array([0.0], dtype=np.float32))
        assert truncated is False
    assert env.day == env.horizon_days


def test_multi_sku_inventory_env_contract_and_vectorization():
    env = MultiSKUInventoryEnv(n_skus=3, horizon_days=5)
    _assert_gymnasium_contract(env, (13,))

    vec_env, obs = env.get_sb_env()
    assert obs.shape == (1, 13)
    action = np.full((1, 3), 0.25, dtype=np.float32)
    next_obs, rewards, dones, infos = vec_env.step(action)
    assert next_obs.shape == (1, 13)
    assert rewards.shape == (1,)
    assert dones.shape == (1,)
    assert isinstance(infos[0], dict)


def test_supplier_selection_env_contract_and_allocation_info():
    env = SupplierSelectionEnv(n_suppliers=3, horizon_days=4)
    _assert_gymnasium_contract(env, (15,))

    _, _, _, _, info = env.step(np.array([1.0, 1.0, 1.0], dtype=np.float32))
    assert np.isclose(np.sum(info["allocation_fractions"]), 1.0)
    assert len(info["allocation_fractions"]) == 3


def test_production_scheduling_env_contract_and_backlog_tracking():
    env = ProductionSchedulingEnv(n_products=2, horizon_days=4)
    _assert_gymnasium_contract(env, (8,))

    _, _, _, _, info = env.step(np.zeros(2, dtype=np.float32))
    assert "total_backlog" in info
    assert info["total_backlog"] >= 0
