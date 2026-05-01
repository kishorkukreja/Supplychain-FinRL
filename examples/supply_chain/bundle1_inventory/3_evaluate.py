from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from stable_baselines3 import A2C
from stable_baselines3 import PPO

from finrl.meta.env_supply_chain import MultiSKUInventoryEnv
from finrl.meta.env_supply_chain import SingleSKUInventoryEnv


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
MODEL_DIR = OUTPUT_DIR / "trained_models" / "inventory"
RESULTS_DIR = OUTPUT_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def run_model(model, env):
    obs, _ = env.reset(seed=100)
    terminated = False
    while not terminated:
        action, _ = model.predict(obs, deterministic=True)
        obs, _, terminated, _, _ = env.step(action)
    costs = env.save_cost_memory()
    kpis = env.save_kpi_memory()
    inventory_cols = kpis.filter(like="inventory")
    avg_inventory = (
        float(inventory_cols.mean().mean())
        if not inventory_cols.empty
        else float(kpis["warehouse_utilization"].mean())
    )
    return {
        "total_cost": float(costs["total_cost"].sum()),
        "fill_rate": float(kpis["fill_rate"].mean()),
        "avg_inventory": avg_inventory,
        "stockout_events": int((kpis["stockout_units"] > 0).sum()),
    }, costs


def run_fixed_policy(env, action):
    obs, _ = env.reset(seed=100)
    terminated = False
    while not terminated:
        obs, _, terminated, _, _ = env.step(action)
    costs = env.save_cost_memory()
    kpis = env.save_kpi_memory()
    inventory_cols = kpis.filter(like="inventory")
    avg_inventory = (
        float(inventory_cols.mean().mean())
        if not inventory_cols.empty
        else float(kpis["warehouse_utilization"].mean())
    )
    return {
        "total_cost": float(costs["total_cost"].sum()),
        "fill_rate": float(kpis["fill_rate"].mean()),
        "avg_inventory": avg_inventory,
        "stockout_events": int((kpis["stockout_units"] > 0).sum()),
    }, costs


test_path = OUTPUT_DIR / "test_inventory_data.csv"
if not test_path.exists():
    raise FileNotFoundError("Run 1_data.py before evaluation.")

test = pd.read_csv(test_path)
single_sku = test[test["sku_id"] == "SKU_001"]
demand_mean = float(single_sku["demand"].mean())
demand_std = float(single_sku["demand"].std())

env_specs = {
    "single_sku": lambda: SingleSKUInventoryEnv(
        horizon_days=60,
        demand_mean=demand_mean,
        demand_std=max(1.0, demand_std),
    ),
    "multi_sku": lambda: MultiSKUInventoryEnv(n_skus=10, horizon_days=60),
}
model_classes = {"a2c": A2C, "ppo": PPO}
rows = []
cost_curves = {}

for env_name, env_factory in env_specs.items():
    for model_name, model_cls in model_classes.items():
        model_path = MODEL_DIR / f"{env_name}_{model_name}.zip"
        if not model_path.exists():
            print(f"Skipping missing model {model_path}")
            continue
        metrics, costs = run_model(model_cls.load(str(model_path)), env_factory())
        rows.append({"env": env_name, "policy": model_name, **metrics})
        cost_curves[f"{env_name}_{model_name}"] = costs["total_cost"].cumsum().to_numpy()

    env = env_factory()
    action = np.full(env.action_space.shape, 0.4, dtype=np.float32)
    metrics, costs = run_fixed_policy(env, action)
    rows.append({"env": env_name, "policy": "eoq_fixed_qty", **metrics})
    cost_curves[f"{env_name}_eoq"] = costs["total_cost"].cumsum().to_numpy()

    env = env_factory()
    action = np.full(env.action_space.shape, 0.75, dtype=np.float32)
    metrics, costs = run_fixed_policy(env, action)
    rows.append({"env": env_name, "policy": "sS_policy", **metrics})
    cost_curves[f"{env_name}_sS"] = costs["total_cost"].cumsum().to_numpy()

metrics_df = pd.DataFrame(rows)
metrics_df.to_csv(RESULTS_DIR / "inventory_metrics.csv", index=False)
print(metrics_df)

plt.figure(figsize=(10, 5))
for name, curve in cost_curves.items():
    plt.plot(curve, label=name)
plt.title("Inventory Cost Over Time")
plt.xlabel("Day")
plt.ylabel("Cumulative Cost")
plt.legend()
plt.tight_layout()
plt.savefig(RESULTS_DIR / "inventory_cost_curves.png", dpi=150)
print(f"Saved results to {RESULTS_DIR}")
