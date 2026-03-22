"""Build BHPS-only trajectories and verify counts."""

import logging

logging.disable(logging.CRITICAL)

import json

from trajectory_tda.data.employment_status import extract_employment_status
from trajectory_tda.data.income_band import extract_income_bands
from trajectory_tda.data.trajectory_builder import build_trajectories

print("Extracting BHPS employment...", flush=True)
emp_df = extract_employment_status(
    "trajectory_tda/data",
    usoc_waves=[],
)
print(f"  BHPS emp: {len(emp_df)} obs, {emp_df['pidp'].nunique()} persons", flush=True)

print("Extracting BHPS income...", flush=True)
inc_df = extract_income_bands(
    "trajectory_tda/data",
    usoc_waves=[],
)
print(f"  BHPS inc: {len(inc_df)} obs, {inc_df['pidp'].nunique()} persons", flush=True)

print("Building BHPS trajectories...", flush=True)
trajectories, metadata = build_trajectories(emp_df=emp_df, inc_df=inc_df)
print(f"  Total BHPS trajectories: {len(trajectories)}", flush=True)

era_counts = metadata["survey_era"].value_counts()
print("\nSurvey era distribution:", flush=True)
for era, count in era_counts.items():
    sub = metadata[metadata["survey_era"] == era]
    print(
        f"  {era}: n={count}, mean_len={sub['n_years'].mean():.1f}, "
        f"range={sub['start_year'].min()}-{sub['end_year'].max()}",
        flush=True,
    )

result = {
    "total": len(trajectories),
    "era": era_counts.to_dict(),
    "bhps_stats": {
        "n": len(metadata),
        "mean_len": float(metadata["n_years"].mean()),
        "min_year": int(metadata["start_year"].min()),
        "max_year": int(metadata["end_year"].max()),
    },
}
with open("trajectory_tda/scripts/bhps_verify_result.json", "w") as f:
    json.dump(result, f, indent=2)
print("\nResults saved to bhps_verify_result.json", flush=True)
