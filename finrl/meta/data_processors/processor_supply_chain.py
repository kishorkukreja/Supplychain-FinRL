from __future__ import annotations

import numpy as np
import pandas as pd

from finrl.config_supply_chain import DEFAULT_DEMAND_MEAN
from finrl.config_supply_chain import DEFAULT_DEMAND_STD
from finrl.config_supply_chain import DEFAULT_DISRUPTION_PROB
from finrl.config_supply_chain import DEFAULT_SEASONALITY_AMPLITUDE
from finrl.config_supply_chain import SC_INDICATORS


class SupplyChainDataProcessor:
    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def generate_demand_data(
        self,
        n_skus: int,
        n_periods: int,
        seasonal: bool = True,
        disruptions: bool = True,
        start_date: str = "2026-01-01",
    ) -> pd.DataFrame:
        dates = pd.date_range(start=start_date, periods=n_periods, freq="D")
        rows = []
        for sku_idx in range(n_skus):
            sku_id = f"SKU_{sku_idx + 1:03d}"
            base_mean = DEFAULT_DEMAND_MEAN * self.rng.uniform(0.7, 1.3)
            demand_std = DEFAULT_DEMAND_STD * self.rng.uniform(0.7, 1.4)
            trend = self.rng.uniform(-0.04, 0.04)
            price = self.rng.uniform(8.0, 25.0)
            for period, date in enumerate(dates):
                seasonal_factor = (
                    1.0
                    + DEFAULT_SEASONALITY_AMPLITUDE * np.sin(2 * np.pi * period / 30.0)
                    if seasonal
                    else 1.0
                )
                mean = max(1.0, base_mean * seasonal_factor * (1.0 + trend * period / n_periods))
                disruption_flag = int(disruptions and self.rng.random() < DEFAULT_DISRUPTION_PROB)
                demand_multiplier = self.rng.uniform(1.5, 2.5) if disruption_flag else 1.0
                demand = max(0.0, self.rng.normal(mean * demand_multiplier, demand_std))
                inventory = max(0.0, self.rng.normal(mean * 1.2, demand_std))
                demand_met = min(inventory, demand)
                rows.append(
                    {
                        "date": date,
                        "sku_id": sku_id,
                        "demand": float(demand),
                        "demand_mean": float(mean),
                        "demand_std": float(demand_std),
                        "price": float(price * self.rng.uniform(0.95, 1.05)),
                        "lead_time": int(max(1, round(self.rng.gamma(shape=2.0, scale=1.0)))),
                        "disruption_flag": disruption_flag,
                        "inventory": float(inventory),
                        "demand_met": float(demand_met),
                    }
                )
        return pd.DataFrame(rows)

    def generate_supplier_data(
        self,
        n_suppliers: int,
        n_periods: int,
        start_date: str = "2026-01-01",
    ) -> pd.DataFrame:
        dates = pd.date_range(start=start_date, periods=n_periods, freq="D")
        rows = []
        for supplier_idx in range(n_suppliers):
            supplier_id = f"SUP_{supplier_idx + 1:02d}"
            price = self.rng.uniform(8.0, 20.0)
            reliability_center = self.rng.uniform(0.75, 0.98)
            capacity_center = self.rng.uniform(80.0, 200.0)
            for date in dates:
                price = max(1.0, price + self.rng.normal(0.0, 0.35) - 0.05 * (price - 12.0))
                reliability = np.clip(
                    self.rng.beta(reliability_center * 30, (1 - reliability_center) * 30),
                    0.01,
                    0.999,
                )
                lead_time = max(1.0, self.rng.gamma(shape=2.0, scale=1.0))
                if self.rng.random() < DEFAULT_DISRUPTION_PROB:
                    lead_time *= self.rng.uniform(1.5, 3.0)
                rows.append(
                    {
                        "date": date,
                        "supplier_id": supplier_id,
                        "price": float(price),
                        "reliability": float(reliability),
                        "lead_time": float(lead_time),
                        "capacity": float(max(1.0, self.rng.normal(capacity_center, 15.0))),
                    }
                )
        return pd.DataFrame(rows)

    def generate_production_data(
        self,
        n_products: int,
        n_periods: int,
        start_date: str = "2026-01-01",
    ) -> pd.DataFrame:
        dates = pd.date_range(start=start_date, periods=n_periods, freq="D")
        rows = []
        shared_cost = 5.0
        for period, date in enumerate(dates):
            shared_cost = max(1.0, shared_cost + self.rng.normal(0.0, 0.08))
            utilization_factor = np.clip(self.rng.normal(1.0, 0.08), 0.6, 1.2)
            for product_idx in range(n_products):
                product_id = f"PROD_{product_idx + 1:03d}"
                mean = DEFAULT_DEMAND_MEAN * (0.8 + 0.1 * product_idx)
                seasonal = 1.0 + 0.2 * np.sin(2 * np.pi * period / 45.0)
                demand = max(0.0, self.rng.normal(mean * seasonal, DEFAULT_DEMAND_STD))
                rows.append(
                    {
                        "date": date,
                        "product_id": product_id,
                        "demand": float(demand),
                        "raw_material_cost": float(shared_cost * self.rng.uniform(0.9, 1.1)),
                        "capacity": float(120.0 * utilization_factor),
                    }
                )
        return pd.DataFrame(rows)

    def add_supply_chain_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        group_col = "sku_id" if "sku_id" in result.columns else result.columns[1]
        result = result.sort_values(["date", group_col]).reset_index(drop=True)
        grouped = result.groupby(group_col, group_keys=False)

        demand = result["demand"].astype(float)
        result["demand_volatility_7d"] = grouped["demand"].transform(
            lambda s: s.rolling(7, min_periods=1).std().fillna(0.0)
            / s.rolling(7, min_periods=1).mean().replace(0, np.nan)
        )
        if "demand_met" in result.columns:
            rolling_met = grouped["demand_met"].transform(
                lambda s: s.rolling(7, min_periods=1).sum()
            )
            rolling_demand = grouped["demand"].transform(
                lambda s: s.rolling(7, min_periods=1).sum()
            )
            result["fill_rate_7d"] = rolling_met / rolling_demand.replace(0, np.nan)
        else:
            result["fill_rate_7d"] = 1.0
        if "lead_time" in result.columns:
            result["lead_time_variance"] = grouped["lead_time"].transform(
                lambda s: s.rolling(7, min_periods=1).std().fillna(0.0)
            )
        else:
            result["lead_time_variance"] = 0.0
        if "inventory" in result.columns:
            avg_demand = grouped["demand"].transform(
                lambda s: s.rolling(7, min_periods=1).mean()
            )
            result["days_of_supply"] = result["inventory"] / avg_demand.replace(0, np.nan)
        else:
            result["days_of_supply"] = 0.0
        disruption = result.get("disruption_flag", pd.Series(0, index=result.index)).astype(float)
        result["supplier_disruption_index"] = grouped[disruption.name].transform(
            lambda s: s.rolling(7, min_periods=1).mean()
        )
        result["demand_trend_14d"] = grouped["demand"].transform(
            lambda s: s.diff(14).fillna(0.0)
        )
        stockout = np.where(result.get("demand_met", demand) < demand, 1.0, 0.0)
        result["stockout_rate_7d"] = pd.Series(stockout).groupby(result[group_col]).transform(
            lambda s: s.rolling(7, min_periods=1).mean()
        )
        reorder_signal = np.where(result.get("inventory", demand) < demand, 1.0, 0.0)
        result["reorder_frequency_30d"] = pd.Series(reorder_signal).groupby(result[group_col]).transform(
            lambda s: s.rolling(30, min_periods=1).mean()
        )
        result[SC_INDICATORS] = result[SC_INDICATORS].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        return result

    def df_to_env_arrays(self, df: pd.DataFrame):
        missing = [indicator for indicator in SC_INDICATORS if indicator not in df.columns]
        if missing:
            df = self.add_supply_chain_indicators(df)

        id_col = "sku_id" if "sku_id" in df.columns else df.columns[1]
        ordered = df.sort_values(["date", id_col])
        demand_array = ordered.pivot(index="date", columns=id_col, values="demand").fillna(0.0)
        disruption_array = ordered.pivot(
            index="date", columns=id_col, values="disruption_flag"
        ).fillna(0.0)
        feature_frames = []
        for indicator in SC_INDICATORS:
            feature_frames.append(
                ordered.pivot(index="date", columns=id_col, values=indicator).fillna(0.0)
            )
        feature_array = np.stack([frame.to_numpy(dtype=np.float32) for frame in feature_frames], axis=2)
        return (
            demand_array.to_numpy(dtype=np.float32),
            feature_array.astype(np.float32),
            disruption_array.to_numpy(dtype=np.float32),
        )
