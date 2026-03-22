"""Complete BHPS pipeline - runs emp, income, trajectory building, saves all results."""

import os
import sys

# Add project root to path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import logging

logging.disable(logging.CRITICAL)

import json
from pathlib import Path

import numpy as np

out_dir = Path(__file__).parent

print("=== BHPS Pipeline ===", flush=True)

# Step 1: Employment
print("1/3 Employment extraction...", flush=True)
from trajectory_tda.data.employment_status import extract_employment_status

emp_df = extract_employment_status("trajectory_tda/data", usoc_waves=[])
print(f"    {len(emp_df)} obs, {emp_df['pidp'].nunique()} persons", flush=True)

# Step 2: Income
print("2/3 Income extraction...", flush=True)
from trajectory_tda.data.income_band import extract_income_bands

inc_df = extract_income_bands("trajectory_tda/data", usoc_waves=[])
print(f"    {len(inc_df)} obs, {inc_df['pidp'].nunique()} persons", flush=True)

# Step 3: Build trajectories
print("3/3 Building trajectories...", flush=True)
from trajectory_tda.data.trajectory_builder import build_trajectories

trajectories, metadata = build_trajectories(emp_df=emp_df, inc_df=inc_df)
print(f"    {len(trajectories)} trajectories built", flush=True)

# Report
era_counts = metadata["survey_era"].value_counts()
print("\n=== Results ===", flush=True)
for era, count in era_counts.items():
    sub = metadata[metadata["survey_era"] == era]
    print(
        f"  {era}: n={count}, mean_len={sub['n_years'].mean():.1f}, "
        f"range={sub['start_year'].min()}-{sub['end_year'].max()}",
        flush=True,
    )

# Save
np.save(
    out_dir / "bhps_trajectories.npy",
    np.array(trajectories, dtype=object),
    allow_pickle=True,
)
metadata.to_pickle(out_dir / "bhps_metadata.pkl")
result = {
    "total": len(trajectories),
    "era": {k: int(v) for k, v in era_counts.items()},
    "mean_len": float(metadata["n_years"].mean()) if len(metadata) > 0 else 0,
    "min_year": int(metadata["start_year"].min()) if len(metadata) > 0 else 0,
    "max_year": int(metadata["end_year"].max()) if len(metadata) > 0 else 0,
}
with open(out_dir / "bhps_result.json", "w") as f:
    json.dump(result, f, indent=2)
print("Saved to bhps_result.json", flush=True)
