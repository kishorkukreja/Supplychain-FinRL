from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from finrl.config_supply_chain import DEFAULT_DEMAND_MEAN
from finrl.config_supply_chain import DEFAULT_DEMAND_STD
from finrl.config_supply_chain import DEFAULT_DISRUPTION_PROB
from finrl.config_supply_chain import DEFAULT_HOLDING_COST_RATE
from finrl.config_supply_chain import DEFAULT_ORDERING_FIXED_COST
from finrl.config_supply_chain import DEFAULT_STOCKOUT_COST_RATE
from finrl.config_supply_chain import SIMULATION_HORIZON_DAYS
from finrl.meta.env_supply_chain._common import PendingArrival
from finrl.meta.env_supply_chain._common import SupplyChainMemoryMixin
from finrl.meta.env_supply_chain._common import finite_float32
from finrl.meta.env_supply_chain._common import make_index_frame


class SingleSKUInventoryEnv(SupplyChainMemoryMixin, gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        holding_cost_rate: float = DEFAULT_HOLDING_COST_RATE,
        stockout_cost_rate: float = DEFAULT_STOCKOUT_COST_RATE,
        ordering_fixed_cost: float = DEFAULT_ORDERING_FIXED_COST,
        lead_time_mean: float = 2.0,
        lead_time_std: float = 0.5,
        demand_mean: float = DEFAULT_DEMAND_MEAN,
        demand_std: float = DEFAULT_DEMAND_STD,
        max_order_qty: float = 250.0,
        review_period: int = 1,
        horizon_days: int = SIMULATION_HORIZON_DAYS,
        initial_inventory: float = 100.0,
        disruption_prob: float = DEFAULT_DISRUPTION_PROB,
    ) -> None:
        self.holding_cost_rate = float(holding_cost_rate)
        self.stockout_cost_rate = float(stockout_cost_rate)
        self.ordering_fixed_cost = float(ordering_fixed_cost)
        self.lead_time_mean = float(lead_time_mean)
        self.lead_time_std = float(lead_time_std)
        self.demand_mean = float(demand_mean)
        self.demand_std = float(demand_std)
        self.max_order_qty = float(max_order_qty)
        self.review_period = max(1, int(review_period))
        self.horizon_days = int(horizon_days)
        self.initial_inventory = float(initial_inventory)
        self.disruption_prob = float(disruption_prob)
        self.df = make_index_frame(self.horizon_days + 1)

        self.action_space = spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32)
        self.observation_space = spaces.Box(
            low=0.0, high=np.inf, shape=(6,), dtype=np.float32
        )
        self.rng = np.random.default_rng()
        self.reset()

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.rng = np.random.default_rng(seed)
        self.day = 0
        self.inventory_on_hand = self.initial_inventory
        self.pending_arrivals: list[PendingArrival] = []
        self.disruption_flag = 0.0
        self._reset_memory()
        return self._get_obs(), {}

    def step(self, action):
        action = np.clip(np.asarray(action, dtype=np.float32), 0.0, 1.0)
        self._receive_arrivals()

        disruption = self.rng.random() < self.disruption_prob
        self.disruption_flag = float(disruption)
        demand_multiplier = 1.8 if disruption else 1.0
        demand = max(
            0.0,
            float(self.rng.normal(self.demand_mean * demand_multiplier, self.demand_std)),
        )
        demand_met = min(self.inventory_on_hand, demand)
        stockout = max(0.0, demand - demand_met)
        self.inventory_on_hand -= demand_met

        order_qty = float(action[0]) * self.max_order_qty
        days_until_review = self._days_until_review()
        if days_until_review == 0 and order_qty > 1e-6:
            lead_time = max(1, int(round(self.rng.normal(self.lead_time_mean, self.lead_time_std))))
            self.pending_arrivals.append(
                PendingArrival(self.day + lead_time, np.array([order_qty], dtype=np.float32))
            )
            ordering_cost = self.ordering_fixed_cost
        else:
            order_qty = 0.0
            ordering_cost = 0.0

        holding_cost = self.holding_cost_rate * self.inventory_on_hand
        stockout_cost = self.stockout_cost_rate * stockout
        total_cost = holding_cost + stockout_cost + ordering_cost

        self.day += 1
        terminated = self.day >= self.horizon_days
        kpis = {
            "demand": demand,
            "demand_met": demand_met,
            "fill_rate": demand_met / demand if demand > 0 else 1.0,
            "stockout_units": stockout,
            "inventory_on_hand": self.inventory_on_hand,
            "order_qty": order_qty,
        }
        costs = {
            "holding_cost": holding_cost,
            "stockout_cost": stockout_cost,
            "ordering_cost": ordering_cost,
            "total_cost": total_cost,
        }
        self._record_step(action, costs, kpis)
        return self._get_obs(), -float(total_cost), bool(terminated), False, {**kpis, **costs}

    def _receive_arrivals(self) -> None:
        remaining = []
        for arrival in self.pending_arrivals:
            if arrival.arrival_day <= self.day:
                self.inventory_on_hand += float(arrival.quantity[0])
            else:
                remaining.append(arrival)
        self.pending_arrivals = remaining

    def _days_until_review(self) -> int:
        return (self.review_period - (self.day % self.review_period)) % self.review_period

    def _get_obs(self) -> np.ndarray:
        in_transit = sum(float(arrival.quantity[0]) for arrival in self.pending_arrivals)
        obs = [
            self.inventory_on_hand,
            in_transit,
            self.demand_mean,
            self.demand_std,
            self._days_until_review(),
            self.disruption_flag,
        ]
        return finite_float32(obs)

    def render(self):
        return self._get_obs()
