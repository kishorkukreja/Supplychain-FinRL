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

from finrl.meta.env_supply_chain import ProductionSchedulingEnv
from finrl.meta.env_supply_chain import SupplierSelectionEnv


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
MODEL_DIR = OUTPUT_DIR / "trained_models" / "supplier_production"
RESULTS_DIR = OUTPUT_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def run_policy(env, model=None, fixed_action=None):
    obs, _ = env.reset(seed=200)
    terminated = False
    while not terminated:
        if model is None:
            action = fixed_action
        else:
            action, _ = model.predict(obs, deterministic=True)
        obs, _, terminated, _, _ = env.step(action)
    costs = env.save_cost_memory()
    kpis = env.save_kpi_memory()
    return {
        "total_cost": float(costs["total_cost"].sum()),
        "service_or_throughput": float(
            kpis["fill_rate"].mean() if "fill_rate" in kpis else kpis["throughput"].mean()
        ),
        "stockout_or_backlog": float(
            kpis["stockout_units"].sum() if "stockout_units" in kpis else kpis["total_backlog"].mean()
        ),
    }, costs


env_specs = {
    "supplier_selection": lambda: SupplierSelectionEnv(n_suppliers=3, horizon_days=60),
    "production_scheduling": lambda: ProductionSchedulingEnv(n_products=3, horizon_days=60),
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
        metrics, costs = run_policy(env_factory(), model=model_cls.load(str(model_path)))
        rows.append({"env": env_name, "policy": model_name, **metrics})
        cost_curves[f"{env_name}_{model_name}"] = costs["total_cost"].cumsum().to_numpy()

    env = env_factory()
    fixed_action = np.full(env.action_space.shape, 1.0 / env.action_space.shape[0], dtype=np.float32)
    baseline_name = "round_robin_supplier" if env_name == "supplier_selection" else "fixed_schedule"
    metrics, costs = run_policy(env, fixed_action=fixed_action)
    rows.append({"env": env_name, "policy": baseline_name, **metrics})
    cost_curves[f"{env_name}_{baseline_name}"] = costs["total_cost"].cumsum().to_numpy()

metrics_df = pd.DataFrame(rows)
metrics_df.to_csv(RESULTS_DIR / "supplier_production_metrics.csv", index=False)
print(metrics_df)

plt.figure(figsize=(10, 5))
for name, curve in cost_curves.items():
    plt.plot(curve, label=name)
plt.title("Supplier and Production Cost Over Time")
plt.xlabel("Day")
plt.ylabel("Cumulative Cost")
plt.legend()
plt.tight_layout()
plt.savefig(RESULTS_DIR / "supplier_production_cost_curves.png", dpi=150)
print(f"Saved results to {RESULTS_DIR}")
