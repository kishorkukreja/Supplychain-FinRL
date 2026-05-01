from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from finrl.config_supply_chain import DEFAULT_DEMAND_MEAN
from finrl.config_supply_chain import DEFAULT_DEMAND_STD
from finrl.config_supply_chain import DEFAULT_DISRUPTION_PROB
from finrl.config_supply_chain import DEFAULT_STOCKOUT_COST_RATE
from finrl.config_supply_chain import SIMULATION_HORIZON_DAYS
from finrl.meta.env_supply_chain._common import PendingArrival
from finrl.meta.env_supply_chain._common import SupplyChainMemoryMixin
from finrl.meta.env_supply_chain._common import finite_float32
from finrl.meta.env_supply_chain._common import make_index_frame
from finrl.meta.env_supply_chain._common import normalize_action


class SupplierSelectionEnv(SupplyChainMemoryMixin, gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        n_suppliers: int = 3,
        base_prices=None,
        reliability_params=None,
        lead_time_params=None,
        max_capacity=None,
        disruption_prob: float = DEFAULT_DISRUPTION_PROB,
        demand_mean: float = DEFAULT_DEMAND_MEAN,
        demand_std: float = DEFAULT_DEMAND_STD,
        horizon_days: int = SIMULATION_HORIZON_DAYS,
        initial_inventory: float = 100.0,
        initial_budget: float = 100000.0,
        stockout_cost_rate: float = DEFAULT_STOCKOUT_COST_RATE,
        late_delivery_penalty_rate: float = 0.05,
        quality_rejection_cost_rate: float = 0.10,
    ) -> None:
        self.n_suppliers = int(n_suppliers)
        self.base_prices = self._array(base_prices, 10.0)
        self.supplier_reliability = self._array(reliability_params, 0.9)
        self.supplier_lead_times = np.maximum(1, self._array(lead_time_params, 2.0)).astype(int)
        self.supplier_capacity = self._array(max_capacity, 150.0)
        self.disruption_prob = float(disruption_prob)
        self.demand_mean = float(demand_mean)
        self.demand_std = float(demand_std)
        self.horizon_days = int(horizon_days)
        self.initial_inventory = float(initial_inventory)
        self.initial_budget = float(initial_budget)
        self.stockout_cost_rate = float(stockout_cost_rate)
        self.late_delivery_penalty_rate = float(late_delivery_penalty_rate)
        self.quality_rejection_cost_rate = float(quality_rejection_cost_rate)
        self.df = make_index_frame(self.horizon_days + 1)

        self.action_space = spaces.Box(
            low=0.0, high=1.0, shape=(self.n_suppliers,), dtype=np.float32
        )
        self.observation_space = spaces.Box(
            low=0.0, high=np.inf, shape=(3 + 4 * self.n_suppliers,), dtype=np.float32
        )
        self.rng = np.random.default_rng()
        self.reset()

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.rng = np.random.default_rng(seed)
        self.day = 0
        self.current_inventory = self.initial_inventory
        self.budget_remaining = self.initial_budget
        self.demand_forecast = self.demand_mean
        self.pending_arrivals: list[PendingArrival] = []
        self._reset_memory()
        return self._get_obs(), {}

    def step(self, action):
        action = np.asarray(action, dtype=np.float32)
        allocation_fractions = normalize_action(action)
        self._receive_arrivals()

        disruption = self.rng.random(self.n_suppliers) < self.disruption_prob
        effective_reliability = np.where(disruption, self.supplier_reliability * 0.5, self.supplier_reliability)
        target_order = max(0.0, self.demand_forecast * 1.25 - self.current_inventory)
        requested = allocation_fractions * target_order
        ordered_qty = np.minimum(requested, self.supplier_capacity)
        on_time_flags = self.rng.random(self.n_suppliers) <= effective_reliability
        accepted_qty = ordered_qty * on_time_flags.astype(np.float32)
        rejected_qty = ordered_qty - accepted_qty

        for supplier, qty in enumerate(accepted_qty):
            if qty > 1e-6:
                self.pending_arrivals.append(
                    PendingArrival(
                        self.day + int(self.supplier_lead_times[supplier]),
                        np.array([qty], dtype=np.float32),
                    )
                )

        demand = max(0.0, float(self.rng.normal(self.demand_mean, self.demand_std)))
        demand_met = min(self.current_inventory, demand)
        stockout = max(0.0, demand - demand_met)
        self.current_inventory -= demand_met

        procurement_cost = float(np.sum(ordered_qty * self.base_prices))
        late_delivery_penalty = float(np.sum(rejected_qty * self.base_prices * self.late_delivery_penalty_rate))
        stockout_cost = self.stockout_cost_rate * stockout
        quality_rejection_cost = float(np.sum(rejected_qty * self.base_prices * self.quality_rejection_cost_rate))
        total_cost = procurement_cost + late_delivery_penalty + stockout_cost + quality_rejection_cost
        self.budget_remaining = max(0.0, self.budget_remaining - procurement_cost)
        self.demand_forecast = 0.8 * self.demand_forecast + 0.2 * demand

        self.day += 1
        terminated = self.day >= self.horizon_days
        kpis = {
            "demand": demand,
            "demand_met": demand_met,
            "fill_rate": demand_met / demand if demand > 0 else 1.0,
            "stockout_units": stockout,
            "on_time_rate": float(np.mean(on_time_flags)),
            "current_inventory": self.current_inventory,
        }
        costs = {
            "procurement_cost": procurement_cost,
            "late_delivery_penalty": late_delivery_penalty,
            "stockout_cost": stockout_cost,
            "quality_rejection_cost": quality_rejection_cost,
            "total_cost": total_cost,
        }
        self._record_step(allocation_fractions, costs, kpis)
        info = {**kpis, **costs, "allocation_fractions": allocation_fractions.copy()}
        return self._get_obs(), -float(total_cost), bool(terminated), False, info

    def _array(self, values, default: float) -> np.ndarray:
        if values is None:
            return np.full(self.n_suppliers, default, dtype=np.float32)
        arr = np.asarray(values, dtype=np.float32)
        if arr.size != self.n_suppliers:
            raise ValueError(f"Expected {self.n_suppliers} values, got {arr.size}.")
        return arr

    def _receive_arrivals(self) -> None:
        remaining = []
        for arrival in self.pending_arrivals:
            if arrival.arrival_day <= self.day:
                self.current_inventory += float(arrival.quantity[0])
            else:
                remaining.append(arrival)
        self.pending_arrivals = remaining

    def _get_obs(self) -> np.ndarray:
        obs = np.concatenate(
            [
                np.array(
                    [self.current_inventory, self.demand_forecast, self.budget_remaining],
                    dtype=np.float32,
                ),
                self.base_prices,
                self.supplier_reliability,
                self.supplier_lead_times.astype(np.float32),
                self.supplier_capacity,
            ]
        )
        return finite_float32(obs)

    def render(self):
        return self._get_obs()
