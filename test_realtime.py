"""Quick test of realtime analysis"""

import sys
from pathlib import Path

# Set matplotlib backend
import matplotlib

matplotlib.use("Agg")

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from financial_tda.validation.gidea_katz_replication import (
    compute_persistence_landscape_norms,
    fetch_historical_data,
)

print("Fetching data...")
prices_dict = fetch_historical_data("2024-01-01", "2024-12-31")
print(f"Got {len(next(iter(prices_dict.values())))} days")

print("Computing norms...")
norms = compute_persistence_landscape_norms(prices_dict, window_size=50, stride=5, n_layers=5)
print(f"Computed {len(norms)} norms")
print(norms.head())

print("Test complete!")
