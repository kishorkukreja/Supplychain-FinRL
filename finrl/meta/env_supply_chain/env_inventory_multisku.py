from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from finrl.config_supply_chain import DEFAULT_DEMAND_MEAN
from finrl.config_supply_chain import DEFAULT_DEMAND_STD
from finrl.config_supply_chain import DEFAULT_HOLDING_COST_RATE
from finrl.config_supply_chain import DEFAULT_ORDERING_FIXED_COST
from finrl.config_supply_chain import DEFAULT_STOCKOUT_COST_RATE
from finrl.config_supply_chain import SIMULATION_HORIZON_DAYS
from finrl.meta.env_supply_chain._common import PendingArrival
from finrl.meta.env_supply_chain._common import SupplyChainMemoryMixin
from finrl.meta.env_supply_chain._common import finite_float32
from finrl.meta.env_supply_chain._common import make_index_frame


class MultiSKUInventoryEnv(SupplyChainMemoryMixin, gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        n_skus: int = 10,
        holding_costs=None,
        stockout_costs=None,
        ordering_costs=None,
        lead_times=None,
        warehouse_capacity: float = 2500.0,
        demand_means=None,
        demand_stds=None,
        demand_correlation_matrix=None,
        max_order_qty: float = 200.0,
        horizon_days: int = SIMULATION_HORIZON_DAYS,
        initial_inventory=None,
        capacity_penalty_rate: float = 1.0,
    ) -> None:
        self.n_skus = int(n_skus)
        self.holding_costs = self._array(holding_costs, DEFAULT_HOLDING_COST_RATE)
        self.stockout_costs = self._array(stockout_costs, DEFAULT_STOCKOUT_COST_RATE)
        self.ordering_costs = self._array(ordering_costs, DEFAULT_ORDERING_FIXED_COST)
        self.lead_times = np.maximum(1, self._array(lead_times, 2.0)).astype(int)
        self.warehouse_capacity = float(warehouse_capacity)
        self.demand_means = self._array(demand_means, DEFAULT_DEMAND_MEAN)
        self.demand_stds = self._array(demand_stds, DEFAULT_DEMAND_STD)
        self.max_order_qty = float(max_order_qty)
        self.horizon_days = int(horizon_days)
        self.initial_inventory = self._array(initial_inventory, 100.0)
        self.capacity_penalty_rate = float(capacity_penalty_rate)
        self.demand_correlation_matrix = (
            np.eye(self.n_skus)
            if demand_correlation_matrix is None
            else np.asarray(demand_correlation_matrix, dtype=np.float32)
        )
        self.df = make_index_frame(self.horizon_days + 1)

        self.action_space = spaces.Box(
            low=0.0, high=1.0, shape=(self.n_skus,), dtype=np.float32
        )
        self.observation_space = spaces.Box(
            low=0.0, high=np.inf, shape=(4 * self.n_skus + 1,), dtype=np.float32
        )
        self.rng = np.random.default_rng()
        self.reset()

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.rng = np.random.default_rng(seed)
        self.day = 0
        self.inventory_levels = self.initial_inventory.astype(np.float32).copy()
        self.pending_arrivals: list[PendingArrival] = []
        self._reset_memory()
        return self._get_obs(), {}

    def step(self, action):
        action = np.clip(np.asarray(action, dtype=np.float32), 0.0, 1.0)
        self._receive_arrivals()

        demand = self._sample_demand()
        demand_met = np.minimum(self.inventory_levels, demand)
        stockout = np.maximum(demand - demand_met, 0.0)
        self.inventory_levels -= demand_met

        order_qty = action * self.max_order_qty
        for sku, qty in enumerate(order_qty):
            if qty > 1e-6:
                arrival_qty = np.zeros(self.n_skus, dtype=np.float32)
                arrival_qty[sku] = qty
                self.pending_arrivals.append(
                    PendingArrival(self.day + int(self.lead_times[sku]), arrival_qty)
                )

        holding_cost = float(np.sum(self.holding_costs * self.inventory_levels))
        stockout_cost = float(np.sum(self.stockout_costs * stockout))
        ordering_cost = float(np.sum(self.ordering_costs * (order_qty > 1e-6)))
        excess_capacity = max(0.0, float(np.sum(self.inventory_levels) - self.warehouse_capacity))
        capacity_violation_penalty = self.capacity_penalty_rate * excess_capacity
        total_cost = holding_cost + stockout_cost + ordering_cost + capacity_violation_penalty

        self.day += 1
        terminated = self.day >= self.horizon_days
        fill_rate = float(np.sum(demand_met) / np.sum(demand)) if np.sum(demand) > 0 else 1.0
        kpis = {
            "total_demand": float(np.sum(demand)),
            "fill_rate": fill_rate,
            "stockout_units": float(np.sum(stockout)),
            "warehouse_utilization": self._warehouse_utilization(),
        }
        costs = {
            "holding_cost": holding_cost,
            "stockout_cost": stockout_cost,
            "ordering_cost": ordering_cost,
            "capacity_violation_penalty": capacity_violation_penalty,
            "total_cost": total_cost,
        }
        self._record_step(action, costs, kpis)
        return self._get_obs(), -float(total_cost), bool(terminated), False, {**kpis, **costs}

    def _array(self, values, default: float) -> np.ndarray:
        if values is None:
            return np.full(self.n_skus, default, dtype=np.float32)
        arr = np.asarray(values, dtype=np.float32)
        if arr.size != self.n_skus:
            raise ValueError(f"Expected {self.n_skus} values, got {arr.size}.")
        return arr

    def _sample_demand(self) -> np.ndarray:
        cov = np.outer(self.demand_stds, self.demand_stds) * self.demand_correlation_matrix
        demand = self.rng.multivariate_normal(self.demand_means, cov)
        return np.maximum(demand, 0.0).astype(np.float32)

    def _receive_arrivals(self) -> None:
        remaining = []
        for arrival in self.pending_arrivals:
            if arrival.arrival_day <= self.day:
                self.inventory_levels += arrival.quantity
            else:
                remaining.append(arrival)
        self.pending_arrivals = remaining

    def _in_transit(self) -> np.ndarray:
        if not self.pending_arrivals:
            return np.zeros(self.n_skus, dtype=np.float32)
        return np.sum([arrival.quantity for arrival in self.pending_arrivals], axis=0)

    def _warehouse_utilization(self) -> float:
        if self.warehouse_capacity <= 0:
            return 0.0
        return float(np.sum(self.inventory_levels) / self.warehouse_capacity)

    def _get_obs(self) -> np.ndarray:
        obs = np.concatenate(
            [
                self.inventory_levels,
                self._in_transit(),
                self.demand_means,
                self.demand_stds,
                np.array([self._warehouse_utilization()], dtype=np.float32),
            ]
        )
        return finite_float32(obs)

    def render(self):
        return self._get_obs()
