from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from finrl.meta.data_processors.processor_supply_chain import SupplyChainDataProcessor


OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

processor = SupplyChainDataProcessor(seed=84)
supplier_data = processor.generate_supplier_data(n_suppliers=3, n_periods=730)
production_data = processor.generate_production_data(n_products=3, n_periods=730)

supplier_midpoint = supplier_data["date"].min() + (
    supplier_data["date"].max() - supplier_data["date"].min()
) / 2
production_midpoint = production_data["date"].min() + (
    production_data["date"].max() - production_data["date"].min()
) / 2

supplier_data[supplier_data["date"] <= supplier_midpoint].to_csv(
    OUTPUT_DIR / "train_supplier_data.csv", index=False
)
supplier_data[supplier_data["date"] > supplier_midpoint].to_csv(
    OUTPUT_DIR / "test_supplier_data.csv", index=False
)
production_data[production_data["date"] <= production_midpoint].to_csv(
    OUTPUT_DIR / "train_production_data.csv", index=False
)
production_data[production_data["date"] > production_midpoint].to_csv(
    OUTPUT_DIR / "test_production_data.csv", index=False
)

print(f"Saved supplier and production datasets to {OUTPUT_DIR}")
