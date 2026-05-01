from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from finrl.meta.data_processors.processor_supply_chain import SupplyChainDataProcessor


OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

processor = SupplyChainDataProcessor(seed=42)
data = processor.generate_demand_data(n_skus=10, n_periods=730)
data = processor.add_supply_chain_indicators(data)

split_date = data["date"].min() + (data["date"].max() - data["date"].min()) / 2
train = data[data["date"] <= split_date]
test = data[data["date"] > split_date]

train.to_csv(OUTPUT_DIR / "train_inventory_data.csv", index=False)
test.to_csv(OUTPUT_DIR / "test_inventory_data.csv", index=False)

print(f"Saved {len(train)} train rows to {OUTPUT_DIR / 'train_inventory_data.csv'}")
print(f"Saved {len(test)} test rows to {OUTPUT_DIR / 'test_inventory_data.csv'}")
