from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class PendingArrival:
    arrival_day: int
    quantity: np.ndarray


class SupplyChainMemoryMixin:
    def _reset_memory(self) -> None:
        self.actions_memory = []
        self.kpi_memory = []
        self.cost_memory = []
        self.date_memory = [0]

    def _record_step(self, action, costs: dict[str, float], kpis: dict[str, float]) -> None:
        self.actions_memory.append(np.asarray(action, dtype=np.float32).copy())
        self.cost_memory.append({"day": self.day, **costs})
        self.kpi_memory.append({"day": self.day, **kpis})
        self.date_memory.append(self.day)

    def save_asset_memory(self) -> pd.DataFrame:
        total_cost = np.cumsum([row["total_cost"] for row in self.cost_memory])
        dates = list(range(1, len(total_cost) + 1))
        return pd.DataFrame({"date": dates, "account_value": -total_cost})

    def save_action_memory(self) -> pd.DataFrame:
        if not self.actions_memory:
            return pd.DataFrame()
        actions = np.vstack([np.ravel(action) for action in self.actions_memory])
        columns = [f"action_{i}" for i in range(actions.shape[1])]
        df_actions = pd.DataFrame(actions, columns=columns)
        df_actions.insert(0, "date", range(1, len(df_actions) + 1))
        return df_actions

    def save_kpi_memory(self) -> pd.DataFrame:
        return pd.DataFrame(self.kpi_memory)

    def save_cost_memory(self) -> pd.DataFrame:
        return pd.DataFrame(self.cost_memory)

    def get_sb_env(self):
        from stable_baselines3.common.vec_env import DummyVecEnv

        env = DummyVecEnv([lambda: self])
        obs = env.reset()
        return env, obs


def make_index_frame(horizon_days: int) -> pd.DataFrame:
    return pd.DataFrame({"date": range(horizon_days)}).set_index("date")


def finite_float32(values) -> np.ndarray:
    return np.nan_to_num(np.asarray(values, dtype=np.float32), nan=0.0, posinf=1e6, neginf=-1e6)


def positive_normal(rng: np.random.Generator, mean, std, size=None) -> np.ndarray:
    values = rng.normal(mean, std, size=size)
    return np.maximum(values, 0.0)


def normalize_action(action: np.ndarray) -> np.ndarray:
    action = np.clip(np.asarray(action, dtype=np.float32), 0.0, 1.0)
    total = float(action.sum())
    if total <= 1e-8:
        return np.full_like(action, 1.0 / action.size, dtype=np.float32)
    return action / total
