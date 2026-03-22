"""Verify USoc trajectories unchanged and check BHPS/spanning counts."""
import logging

logging.basicConfig(level=logging.INFO)
from trajectory_tda.data.trajectory_builder import build_trajectories_from_raw

trajectories, metadata = build_trajectories_from_raw('trajectory_tda/data')

print("\n=== TRAJECTORY SUMMARY ===")
print(f"Total trajectories: {len(trajectories)}")
print("Survey era distribution:")
era_counts = metadata['survey_era'].value_counts()
for era, count in era_counts.items():
    subset = metadata[metadata['survey_era'] == era]
    print(f"  {era}: {count} (mean length={subset['n_years'].mean():.1f}, "
          f"range={subset['start_year'].min()}-{subset['end_year'].max()})")

# Check USoc-only count matches expected 27,280
usoc_only = era_counts.get('usoc_only', 0)
print(f"\nUSoc-only count: {usoc_only} (expected: ~27,280)")
print(f"BHPS-only count: {era_counts.get('bhps_only', 0)}")
print(f"Spanning count: {era_counts.get('spanning', 0)}")
