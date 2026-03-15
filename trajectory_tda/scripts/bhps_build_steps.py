"""Build BHPS trajectories step by step, saving intermediate results."""

import logging
import sys

logging.disable(logging.CRITICAL)

from pathlib import Path

import pandas as pd

step = sys.argv[1] if len(sys.argv) > 1 else "emp"
out_dir = Path("trajectory_tda/scripts")

if step == "emp":
    from trajectory_tda.data.employment_status import extract_employment_status

    emp_df = extract_employment_status("trajectory_tda/data", usoc_waves=[])
    emp_df.to_pickle(out_dir / "bhps_emp.pkl")
    print(f"BHPS emp: {len(emp_df)} obs, {emp_df['pidp'].nunique()} persons")

elif step == "inc":
    from trajectory_tda.data.income_band import extract_income_bands

    inc_df = extract_income_bands("trajectory_tda/data", usoc_waves=[])
    inc_df.to_pickle(out_dir / "bhps_inc.pkl")
    print(f"BHPS inc: {len(inc_df)} obs, {inc_df['pidp'].nunique()} persons")

elif step == "build":
    import json

    from trajectory_tda.data.trajectory_builder import build_trajectories

    emp_df = pd.read_pickle(out_dir / "bhps_emp.pkl")
    inc_df = pd.read_pickle(out_dir / "bhps_inc.pkl")
    trajectories, metadata = build_trajectories(emp_df=emp_df, inc_df=inc_df)

    print(f"Total: {len(trajectories)}")
    era_counts = metadata["survey_era"].value_counts()
    for era, count in era_counts.items():
        sub = metadata[metadata["survey_era"] == era]
        print(f"  {era}: n={count}, mean_len={sub['n_years'].mean():.1f}")

    # Save for pipeline use
    import numpy as np

    np.save(
        out_dir / "bhps_trajectories.npy",
        np.array(trajectories, dtype=object),
        allow_pickle=True,
    )
    metadata.to_pickle(out_dir / "bhps_metadata.pkl")

    result = {
        "total": len(trajectories),
        "era": {k: int(v) for k, v in era_counts.items()},
        "mean_len": float(metadata["n_years"].mean()),
        "min_year": int(metadata["start_year"].min()),
        "max_year": int(metadata["end_year"].max()),
    }
    with open(out_dir / "bhps_result.json", "w") as f:
        json.dump(result, f, indent=2)
    print("Saved results.")
