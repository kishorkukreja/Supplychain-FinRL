from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from finrl.config_supply_chain import DEFAULT_DEMAND_MEAN
from finrl.config_supply_chain import DEFAULT_DEMAND_STD
from finrl.config_supply_chain import DEFAULT_DISRUPTION_PROB
from finrl.meta.data_processors.processor_supply_chain import SupplyChainDataProcessor


GENERATOR_VERSION = "v1"
OBJECTIVE_PROFILES = [
    {
        "profile_id": "balanced_risk_adjusted_cost",
        "buyer_objective": "Minimize risk-adjusted total cost while maintaining fill rate above 0.95.",
        "demand_mean_multiplier": 1.0,
        "demand_std_multiplier": 1.0,
        "inventory_multiplier": 1.1,
        "service_level_target": 0.95,
        "stockout_cost_rate": 0.1,
        "late_delivery_penalty_rate": 0.05,
        "quality_rejection_cost_rate": 0.1,
    },
    {
        "profile_id": "lowest_landed_cost",
        "buyer_objective": "Minimize total landed cost while keeping service levels acceptable.",
        "demand_mean_multiplier": 0.9,
        "demand_std_multiplier": 0.8,
        "inventory_multiplier": 1.25,
        "service_level_target": 0.9,
        "stockout_cost_rate": 0.07,
        "late_delivery_penalty_rate": 0.04,
        "quality_rejection_cost_rate": 0.08,
    },
    {
        "profile_id": "high_fill_rate_service_protection",
        "buyer_objective": "Protect fill rate above 0.98 even if procurement costs increase.",
        "demand_mean_multiplier": 1.05,
        "demand_std_multiplier": 1.2,
        "inventory_multiplier": 1.15,
        "service_level_target": 0.98,
        "stockout_cost_rate": 0.18,
        "late_delivery_penalty_rate": 0.08,
        "quality_rejection_cost_rate": 0.12,
    },
    {
        "profile_id": "lead_time_pressure",
        "buyer_objective": "Prioritize short lead times because starting inventory is tight.",
        "demand_mean_multiplier": 1.0,
        "demand_std_multiplier": 1.1,
        "inventory_multiplier": 0.65,
        "service_level_target": 0.96,
        "stockout_cost_rate": 0.15,
        "late_delivery_penalty_rate": 0.09,
        "quality_rejection_cost_rate": 0.1,
    },
    {
        "profile_id": "disruption_resilience",
        "buyer_objective": "Reduce disruption exposure with resilient suppliers and backup coverage.",
        "demand_mean_multiplier": 0.95,
        "demand_std_multiplier": 1.3,
        "inventory_multiplier": 1.0,
        "service_level_target": 0.96,
        "stockout_cost_rate": 0.14,
        "late_delivery_penalty_rate": 0.07,
        "quality_rejection_cost_rate": 0.1,
    },
    {
        "profile_id": "capacity_fit_high_demand",
        "buyer_objective": "Meet elevated demand with allocations that fit supplier capacity limits.",
        "demand_mean_multiplier": 1.3,
        "demand_std_multiplier": 1.0,
        "inventory_multiplier": 0.95,
        "service_level_target": 0.94,
        "stockout_cost_rate": 0.12,
        "late_delivery_penalty_rate": 0.05,
        "quality_rejection_cost_rate": 0.1,
    },
]
DEFAULT_CASE_OUTPUT_PATH = (
    Path(__file__).resolve().parents[3]
    / "examples"
    / "supply_chain"
    / "supplier_selection_llm"
    / "outputs"
    / "cases"
    / "supplier_selection_cases.jsonl"
)
REQUIRED_CASE_FIELDS = {
    "case_id",
    "case_type",
    "seed",
    "buyer_objective",
    "demand_context",
    "supplier_options",
    "rubric",
    "metadata",
}
REQUIRED_SUPPLIER_FIELDS = {
    "supplier_id",
    "base_price",
    "reliability",
    "lead_time_days",
    "capacity",
    "disruption_probability",
}


def assign_case_split(
    case_id: str,
    train_ratio: float = 0.8,
    validation_ratio: float = 0.1,
) -> str:
    split_bucket = int(hashlib.sha256(case_id.encode("utf-8")).hexdigest(), 16) % 100
    train_cutoff = int(train_ratio * 100)
    validation_cutoff = train_cutoff + int(validation_ratio * 100)
    if split_bucket < train_cutoff:
        return "train"
    if split_bucket < validation_cutoff:
        return "validation"
    return "test"


def generate_supplier_selection_cases(
    case_count: int,
    seed: int,
    n_suppliers: int = 3,
) -> list[dict[str, Any]]:
    if case_count < 0:
        raise ValueError("case_count must be non-negative.")
    if n_suppliers < 1:
        raise ValueError("n_suppliers must be positive.")

    return [
        _build_case(
            case_number=case_number,
            case_seed=seed + case_number - 1,
            n_suppliers=n_suppliers,
        )
        for case_number in range(1, case_count + 1)
    ]


def write_supplier_selection_cases_jsonl(
    cases: list[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for case in cases:
            handle.write(json.dumps(case, sort_keys=True) + "\n")
    return path


def generate_and_write_supplier_selection_cases(
    case_count: int = 100,
    seed: int = 1,
    output_path: str | Path = DEFAULT_CASE_OUTPUT_PATH,
    n_suppliers: int = 3,
) -> Path:
    cases = generate_supplier_selection_cases(
        case_count=case_count,
        seed=seed,
        n_suppliers=n_suppliers,
    )
    return write_supplier_selection_cases_jsonl(cases, output_path)


def _build_case(case_number: int, case_seed: int, n_suppliers: int) -> dict[str, Any]:
    case_id = f"supplier_case_{case_number:06d}"
    objective_profile = _objective_profile_for_case(case_number)
    rng = np.random.default_rng(case_seed)
    demand_mean = float(
        DEFAULT_DEMAND_MEAN
        * float(objective_profile["demand_mean_multiplier"])
        * rng.uniform(0.8, 1.2)
    )
    demand_std = float(
        DEFAULT_DEMAND_STD
        * float(objective_profile["demand_std_multiplier"])
        * rng.uniform(0.7, 1.4)
    )

    return {
        "case_id": case_id,
        "case_type": "supplier_selection",
        "seed": int(case_seed),
        "buyer_objective": str(objective_profile["buyer_objective"]),
        "demand_context": {
            "demand_mean": _round_float(demand_mean),
            "demand_std": _round_float(demand_std),
            "initial_inventory": _round_float(
                demand_mean
                * float(objective_profile["inventory_multiplier"])
                * rng.uniform(0.8, 1.4)
            ),
            "initial_budget": 100000.0,
            "horizon_days": 60,
            "service_level_target": float(objective_profile["service_level_target"]),
            "stockout_cost_rate": float(objective_profile["stockout_cost_rate"]),
            "late_delivery_penalty_rate": float(
                objective_profile["late_delivery_penalty_rate"]
            ),
            "quality_rejection_cost_rate": float(
                objective_profile["quality_rejection_cost_rate"]
            ),
        },
        "supplier_options": _build_supplier_options(case_seed, n_suppliers),
        "rubric": {
            "dimensions": [
                "total_landed_cost",
                "reliability_and_service_risk",
                "lead_time_suitability",
                "capacity_fit",
                "disruption_resilience",
            ],
            "score_range": [0.0, 1.0],
            "aggregation": "equal_weight_mean",
        },
        "metadata": {
            "generator_version": GENERATOR_VERSION,
            "objective_profile": str(objective_profile["profile_id"]),
            "split": assign_case_split(case_id),
        },
    }


def _objective_profile_for_case(case_number: int) -> dict[str, str | float]:
    return OBJECTIVE_PROFILES[(case_number - 1) % len(OBJECTIVE_PROFILES)]


def _build_supplier_options(case_seed: int, n_suppliers: int) -> list[dict[str, Any]]:
    supplier_rows = SupplyChainDataProcessor(seed=case_seed).generate_supplier_data(
        n_suppliers=n_suppliers,
        n_periods=1,
    )
    supplier_rows = supplier_rows.sort_values("supplier_id")
    suppliers = []
    for row in supplier_rows.to_dict(orient="records"):
        suppliers.append(
            {
                "supplier_id": str(row["supplier_id"]),
                "base_price": _round_float(row["price"]),
                "reliability": _round_float(row["reliability"]),
                "lead_time_days": max(1, int(round(float(row["lead_time"])))),
                "capacity": _round_float(row["capacity"]),
                "disruption_probability": float(DEFAULT_DISRUPTION_PROB),
            }
        )
    return suppliers


def _round_float(value: float) -> float:
    return float(round(float(value), 6))
