from __future__ import annotations

SC_INDICATORS = [
    "demand_volatility_7d",
    "fill_rate_7d",
    "lead_time_variance",
    "days_of_supply",
    "supplier_disruption_index",
    "demand_trend_14d",
    "stockout_rate_7d",
    "reorder_frequency_30d",
]

SINGLE_SKU = ["SKU_001"]
MULTI_SKU_10 = [f"SKU_{i:03d}" for i in range(1, 11)]
MULTI_SKU_50 = [f"SKU_{i:03d}" for i in range(1, 51)]

SUPPLIER_SET_SMALL = ["SUP_A", "SUP_B", "SUP_C"]
SUPPLIER_SET_LARGE = [f"SUP_{i:02d}" for i in range(1, 11)]

SIMULATION_HORIZON_DAYS = 365
TRAIN_EPISODES = 500
TEST_EPISODES = 100

DEFAULT_HOLDING_COST_RATE = 0.02
DEFAULT_STOCKOUT_COST_RATE = 0.10
DEFAULT_ORDERING_FIXED_COST = 50.0
DEFAULT_BACKLOG_PENALTY_RATE = 0.15

DEFAULT_DEMAND_MEAN = 100.0
DEFAULT_DEMAND_STD = 20.0
DEFAULT_SEASONALITY_AMPLITUDE = 0.3
DEFAULT_DISRUPTION_PROB = 0.02

SC_PPO_PARAMS = {
    "n_steps": 64,
    "ent_coef": 0.005,
    "learning_rate": 0.0003,
    "batch_size": 32,
}
SC_SAC_PARAMS = {
    "batch_size": 64,
    "buffer_size": 10000,
    "learning_rate": 0.0003,
    "learning_starts": 100,
    "ent_coef": "auto",
}
SC_TD3_PARAMS = {
    "batch_size": 64,
    "buffer_size": 10000,
    "learning_rate": 0.001,
}
SC_A2C_PARAMS = {"n_steps": 5, "ent_coef": 0.01, "learning_rate": 0.0007}
SC_DDPG_PARAMS = {
    "batch_size": 64,
    "buffer_size": 10000,
    "learning_rate": 0.001,
}
