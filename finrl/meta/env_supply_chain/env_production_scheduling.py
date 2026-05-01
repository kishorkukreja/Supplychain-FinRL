from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from finrl.config_supply_chain import DEFAULT_BACKLOG_PENALTY_RATE
from finrl.config_supply_chain import DEFAULT_DEMAND_MEAN
from finrl.config_supply_chain import DEFAULT_DEMAND_STD
from finrl.config_supply_chain import DEFAULT_HOLDING_COST_RATE
from finrl.config_supply_chain import SIMULATION_HORIZON_DAYS
from finrl.meta.env_supply_chain._common import SupplyChainMemoryMixin
from finrl.meta.env_supply_chain._common import finite_float32
from finrl.meta.env_supply_chain._common import make_index_frame


class ProductionSchedulingEnv(SupplyChainMemoryMixin, gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        n_products: int = 3,
        production_rates=None,
        material_consumption=None,
        changeover_matrix=None,
        holding_costs=None,
        backlog_penalty_rate: float = DEFAULT_BACKLOG_PENALTY_RATE,
        demand_means=None,
        demand_stds=None,
        machine_capacity: float = 300.0,
        horizon_days: int = SIMULATION_HORIZON_DAYS,
        initial_raw_material: float = 1000.0,
        initial_finished_goods: float = 50.0,
        production_cost_rate: float = 1.0,
        waste_cost_rate: float = 0.02,
    ) -> None:
        self.n_products = int(n_products)
        self.production_rates = self._array(production_rates, 100.0)
        self.material_consumption = self._array(material_consumption, 1.0)
        self.changeover_matrix = (
            np.ones((self.n_products, self.n_products), dtype=np.float32) * 25.0
            if changeover_matrix is None
            else np.asarray(changeover_matrix, dtype=np.float32)
        )
        np.fill_diagonal(self.changeover_matrix, 0.0)
        self.holding_costs = self._array(holding_costs, DEFAULT_HOLDING_COST_RATE)
        self.backlog_penalty_rate = float(backlog_penalty_rate)
        self.demand_means = self._array(demand_means, DEFAULT_DEMAND_MEAN)
        self.demand_stds = self._array(demand_stds, DEFAULT_DEMAND_STD)
        self.machine_capacity = float(machine_capacity)
        self.horizon_days = int(horizon_days)
        self.initial_raw_material = float(initial_raw_material)
        self.initial_finished_goods = float(initial_finished_goods)
        self.production_cost_rate = float(production_cost_rate)
        self.waste_cost_rate = float(waste_cost_rate)
        self.df = make_index_frame(self.horizon_days + 1)

        self.action_space = spaces.Box(
            low=0.0, high=1.0, shape=(self.n_products,), dtype=np.float32
        )
        self.observation_space = spaces.Box(
            low=0.0, high=np.inf, shape=(4 * self.n_products,), dtype=np.float32
        )
        self.rng = np.random.default_rng()
        self.reset()

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.rng = np.random.default_rng(seed)
        self.day = 0
        self.raw_material_inventory = np.full(
            self.n_products, self.initial_raw_material, dtype=np.float32
        )
        self.wip = np.zeros(self.n_products, dtype=np.float32)
        self.finished_goods = np.full(
            self.n_products, self.initial_finished_goods, dtype=np.float32
        )
        self.demand_backlog = np.zeros(self.n_products, dtype=np.float32)
        self.previous_product = None
        self._reset_memory()
        return self._get_obs(), {}

    def step(self, action):
        action = np.clip(np.asarray(action, dtype=np.float32), 0.0, 1.0)
        available_capacity = self.machine_capacity * action
        production_qty = np.minimum(available_capacity, self.production_rates)
        material_limited_qty = np.minimum(
            production_qty,
            self.raw_material_inventory / np.maximum(self.material_consumption, 1e-6),
        )
        self.raw_material_inventory -= material_limited_qty * self.material_consumption
        self.wip = material_limited_qty.astype(np.float32)
        self.finished_goods += self.wip

        demand = np.maximum(
            self.rng.normal(self.demand_means, self.demand_stds), 0.0
        ).astype(np.float32)
        total_required = demand + self.demand_backlog
        shipped = np.minimum(self.finished_goods, total_required)
        self.finished_goods -= shipped
        self.demand_backlog = total_required - shipped

        active_products = np.where(material_limited_qty > 1e-6)[0]
        changeover_cost = self._changeover_cost(active_products)
        if active_products.size > 0:
            self.previous_product = int(active_products[-1])

        production_cost = float(np.sum(material_limited_qty) * self.production_cost_rate)
        holding_cost = float(np.sum(self.holding_costs * self.finished_goods))
        backlog_penalty = float(np.sum(self.demand_backlog) * self.backlog_penalty_rate)
        waste_cost = float(np.sum(np.maximum(self.wip - demand, 0.0)) * self.waste_cost_rate)
        total_cost = production_cost + changeover_cost + holding_cost + backlog_penalty + waste_cost

        self.day += 1
        terminated = self.day >= self.horizon_days
        kpis = {
            "throughput": float(np.sum(shipped)),
            "total_backlog": float(np.sum(self.demand_backlog)),
            "finished_goods": float(np.sum(self.finished_goods)),
            "production_qty": float(np.sum(material_limited_qty)),
        }
        costs = {
            "production_cost": production_cost,
            "changeover_cost": changeover_cost,
            "holding_cost": holding_cost,
            "backlog_penalty": backlog_penalty,
            "waste_cost": waste_cost,
            "total_cost": total_cost,
        }
        self._record_step(action, costs, kpis)
        return self._get_obs(), -float(total_cost), bool(terminated), False, {**kpis, **costs}

    def _array(self, values, default: float) -> np.ndarray:
        if values is None:
            return np.full(self.n_products, default, dtype=np.float32)
        arr = np.asarray(values, dtype=np.float32)
        if arr.size != self.n_products:
            raise ValueError(f"Expected {self.n_products} values, got {arr.size}.")
        return arr

    def _changeover_cost(self, active_products: np.ndarray) -> float:
        if active_products.size == 0:
            return 0.0
        cost = 0.0
        previous = self.previous_product
        for product in active_products:
            if previous is not None:
                cost += float(self.changeover_matrix[previous, product])
            previous = int(product)
        return cost

    def _get_obs(self) -> np.ndarray:
        obs = np.concatenate(
            [
                self.raw_material_inventory,
                self.wip,
                self.finished_goods,
                self.demand_backlog,
            ]
        )
        return finite_float32(obs)

    def render(self):
        return self._get_obs()
