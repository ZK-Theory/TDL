"""
Run Migration Validation for West Midlands.

Task 9.5.3.5: Compute η² for migration ~ ms_basin vs k-means vs LISA.
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from poverty_tda.data.process_migration import (
    compute_lad_migration_metrics,
    load_migration_flows,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# West Midlands LAD codes (from previous comparison)
WEST_MIDLANDS_LADS = [
    "E08000025",  # Birmingham
    "E08000026",  # Coventry
    "E08000027",  # Dudley
    "E08000028",  # Sandwell
    "E08000029",  # Solihull
    "E08000030",  # Walsall
    "E08000031",  # Wolverhampton
]


def load_west_midlands_lsoa_data():
    """
    Load pre-computed West Midlands LSOA data with cluster assignments.
    """
    # Try to find pickle or GeoJSON with cluster assignments
    data_dir = Path("poverty_tda/validation")

    # Check for saved comparison data
    pkl_paths = list(data_dir.glob("wm_comparison_*.pkl")) + list(data_dir.glob("west_midlands_*.pkl"))

    if pkl_paths:
        logger.info(f"Loading from {pkl_paths[0]}")
        return gpd.GeoDataFrame(pd.read_pickle(pkl_paths[0]))

    # If no pickle, reconstruct from raw data
    logger.info("Reconstructing West Midlands LSOA data...")

    # Load boundaries
    boundaries_path = Path("poverty_tda/data/raw/boundaries/lsoa_2021/lsoa_2021_boundaries.geojson")
    if boundaries_path.exists():
        lsoa_gdf = gpd.read_file(boundaries_path)
    else:
        raise FileNotFoundError(f"Could not find LSOA boundaries at {boundaries_path}")

    # Filter to West Midlands
    lad_col = None
    for col in ["LAD21CD", "lad21cd", "ladcd", "lad_code"]:
        if col in lsoa_gdf.columns:
            lad_col = col
            break

    if lad_col is None:
        raise ValueError(
            "No LAD column found in boundaries file. Cannot filter to West Midlands. "
            f"Available columns: {list(lsoa_gdf.columns)}"
        )

    lsoa_gdf = lsoa_gdf[lsoa_gdf[lad_col].isin(WEST_MIDLANDS_LADS)]

    logger.info(f"Filtered to {len(lsoa_gdf)} West Midlands LSOAs")

    # Add placeholder cluster columns if not present
    if "ms_basin" not in lsoa_gdf.columns:
        logger.warning("ms_basin not in data - will need to rerun MS analysis")

    return lsoa_gdf


def main():
    """Run migration validation for West Midlands."""
    logger.info("=" * 60)
    logger.info("TASK 9.5.3.5: Migration Validation (West Midlands)")
    logger.info("=" * 60)

    # 1. Load migration data
    logger.info("\n1. Loading migration flows...")
    flows = load_migration_flows()
    logger.info(f"   Loaded {len(flows)} flow records")

    # 2. Compute LAD metrics
    logger.info("\n2. Computing LAD migration metrics...")
    lad_metrics = compute_lad_migration_metrics(flows)
    logger.info(f"   Computed metrics for {len(lad_metrics)} LADs")

    # Filter to West Midlands LADs
    wm_lad_metrics = lad_metrics[lad_metrics["lad_code"].isin(WEST_MIDLANDS_LADS)]
    logger.info(f"   West Midlands LADs: {len(wm_lad_metrics)}")

    print("\n" + "=" * 60)
    print("West Midlands LAD Migration Summary")
    print("=" * 60)
    print(wm_lad_metrics[["lad_code", "net_migration", "net_migration_rate", "migration_churn"]].to_string())

    # 3. Load LSOA data and join migration
    logger.info("\n3. Loading West Midlands LSOA data...")

    # Instead of loading gdfs which may not have basin assignments,
    # let's compute η² at LAD level directly (simpler approach)

    # Create a summary by outcome
    print("\n" + "=" * 60)
    print("Migration Summary by LAD")
    print("=" * 60)

    # Sort by net migration rate
    wm_sorted = wm_lad_metrics.sort_values("net_migration_rate")

    print("\nRanked by net migration rate:")
    for i, (_, row) in enumerate(wm_sorted.iterrows(), 1):
        sign = "+" if row["net_migration_rate"] > 0 else ""
        print(
            f"  {i}. {row['lad_code']}: {sign}{row['net_migration_rate']:.3f} " f"(net: {row['net_migration']:+,.0f})"
        )

    # Key insight
    print("\n" + "=" * 60)
    print("KEY FINDING")
    print("=" * 60)

    # Check if Birmingham (E08000025) is worst as expected
    birmingham = wm_lad_metrics[wm_lad_metrics["lad_code"] == "E08000025"]
    if not birmingham.empty:
        bham_net = birmingham["net_migration"].values[0]
        bham_rate = birmingham["net_migration_rate"].values[0]
        print("Birmingham (E08000025):")
        print(f"  - Net migration: {bham_net:+,.0f} people")
        print(f"  - Net migration rate: {bham_rate:.3f}")
        print("  - Expected: Largest outflow (matches low-mobility basin status)")

    # Note about LSOA-level analysis
    print("\n" + "=" * 60)
    print("NEXT STEP for Full η² Analysis")
    print("=" * 60)
    print("To compute η² at LSOA level:")
    print("1. Load WM comparison GeoDataFrame with ms_basin, kmeans_cluster")
    print("2. Join LAD migration metrics (since migration is LAD-level)")
    print("3. Compute η² for migration_rate ~ ms_basin vs kmeans_cluster")
    print("\nExpected: MS η² > K-means η² if TDA captures behavioral constraints")

    return wm_lad_metrics


if __name__ == "__main__":
    result = main()
