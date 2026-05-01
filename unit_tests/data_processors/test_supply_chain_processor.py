from __future__ import annotations

import numpy as np
import pandas as pd

from finrl.config_supply_chain import SC_INDICATORS
from finrl.meta.data_processors.processor_supply_chain import SupplyChainDataProcessor


def test_generate_demand_data_schema_and_determinism():
    first = SupplyChainDataProcessor(seed=7).generate_demand_data(
        n_skus=2, n_periods=10
    )
    second = SupplyChainDataProcessor(seed=7).generate_demand_data(
        n_skus=2, n_periods=10
    )

    required = {
        "date",
        "sku_id",
        "demand",
        "demand_mean",
        "demand_std",
        "price",
        "lead_time",
        "disruption_flag",
        "inventory",
        "demand_met",
    }
    assert required.issubset(first.columns)
    assert first.shape[0] == 20
    pd.testing.assert_frame_equal(first, second)


def test_supplier_and_production_data_schemas():
    processor = SupplyChainDataProcessor(seed=11)
    suppliers = processor.generate_supplier_data(n_suppliers=3, n_periods=8)
    production = processor.generate_production_data(n_products=2, n_periods=8)

    assert {"date", "supplier_id", "price", "reliability", "lead_time", "capacity"}.issubset(
        suppliers.columns
    )
    assert {"date", "product_id", "demand", "raw_material_cost", "capacity"}.issubset(
        production.columns
    )
    assert suppliers.shape[0] == 24
    assert production.shape[0] == 16


def test_add_supply_chain_indicators_and_array_conversion():
    processor = SupplyChainDataProcessor(seed=13)
    demand = processor.generate_demand_data(n_skus=3, n_periods=12)
    enriched = processor.add_supply_chain_indicators(demand)
    demand_array, feature_array, disruption_array = processor.df_to_env_arrays(enriched)

    assert set(SC_INDICATORS).issubset(enriched.columns)
    assert demand_array.shape == (12, 3)
    assert feature_array.shape[0] == 12
    assert feature_array.shape[1] == 3
    assert feature_array.shape[2] == len(SC_INDICATORS)
    assert disruption_array.shape == (12, 3)
    assert np.isfinite(demand_array).all()
    assert np.isfinite(feature_array).all()
    assert np.isfinite(disruption_array).all()
