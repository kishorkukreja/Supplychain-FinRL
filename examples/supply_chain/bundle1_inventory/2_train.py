from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from finrl.agents.stablebaselines3.models import DRLAgent
from finrl.config_supply_chain import SC_A2C_PARAMS
from finrl.config_supply_chain import SC_PPO_PARAMS
from finrl.meta.env_supply_chain import MultiSKUInventoryEnv
from finrl.meta.env_supply_chain import SingleSKUInventoryEnv


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
MODEL_DIR = OUTPUT_DIR / "trained_models" / "inventory"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

TIMESTEPS = 256
MODEL_SPECS = {
    "a2c": SC_A2C_PARAMS,
    "ppo": SC_PPO_PARAMS,
}

train_path = OUTPUT_DIR / "train_inventory_data.csv"
if not train_path.exists():
    raise FileNotFoundError("Run 1_data.py before training.")

train = pd.read_csv(train_path)
single_sku = train[train["sku_id"] == "SKU_001"]
demand_mean = float(single_sku["demand"].mean())
demand_std = float(single_sku["demand"].std())

envs = {
    "single_sku": SingleSKUInventoryEnv(
        horizon_days=60,
        demand_mean=demand_mean,
        demand_std=max(1.0, demand_std),
    ),
    "multi_sku": MultiSKUInventoryEnv(n_skus=10, horizon_days=60),
}

for env_name, gym_env in envs.items():
    vec_env, _ = gym_env.get_sb_env()
    agent = DRLAgent(env=vec_env)
    for model_name, params in MODEL_SPECS.items():
        model = agent.get_model(model_name, model_kwargs=params, verbose=0)
        trained_model = agent.train_model(
            model=model,
            tb_log_name=f"{env_name}_{model_name}",
            total_timesteps=TIMESTEPS,
        )
        model_path = MODEL_DIR / f"{env_name}_{model_name}"
        trained_model.save(str(model_path))
        print(f"Saved {model_name} model for {env_name} to {model_path}")
