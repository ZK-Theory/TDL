"""
Multi-Outcome Barrier-Gradient Correlation Analysis (Task 9.5.2 Extended)

Tests barrier-outcome correlation with multiple independent outcomes:
1. IMD (LSOA-level) - finer granularity
2. KS4 GCSE attainment (LAD-level)
3. Net migration (LAD-level)
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyvista as pv
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from poverty_tda.topology.morse_smale import compute_morse_smale

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def assign_lsoas_to_basins(gdf: gpd.GeoDataFrame, ms_result, vti_path: Path) -> gpd.GeoDataFrame:
    """Assign LSOAs to Morse-Smale basins."""
    grid = pv.read(str(vti_path))
    origin = np.array(grid.origin[:2])
    spacing = np.array(grid.spacing[:2])
    dims = np.array(grid.dimensions[:2])

    # Reproject to BNG
    if gdf.crs and gdf.crs.to_epsg() != 27700:
        gdf = gdf.to_crs(epsg=27700)

    centroids = gdf.geometry.centroid
    x_coords = centroids.x.values
    y_coords = centroids.y.values

    i_indices = np.clip(((x_coords - origin[0]) / spacing[0]).astype(int), 0, dims[0] - 1)
    j_indices = np.clip(((y_coords - origin[1]) / spacing[1]).astype(int), 0, dims[1] - 1)
    flat_indices = np.clip(i_indices + j_indices * dims[0], 0, dims[0] * dims[1] - 1)

    gdf = gdf.copy()
    gdf["ms_basin"] = ms_result.descending_manifold[flat_indices]

    return gdf


def compute_barrier_gradient_correlation(ms_result, gdf, outcome_column: str, vti_path: Path):
    """Compute correlation between barrier heights and outcome gradients."""
    # Get mean outcome per basin
    basin_outcome = gdf.groupby("ms_basin")[outcome_column].mean().to_dict()

    minima = ms_result.get_minima()
    if not minima:
        return None

    avg_min = np.mean([m.value for m in minima])

    # Get adjacency from grid
    desc = ms_result.descending_manifold.reshape(150, 150)
    grid = pv.read(str(vti_path))
    mobility = grid.point_data["mobility"].reshape(150, 150)

    adjacent_pairs = {}
    for i in range(150):
        for j in range(149):
            b1, b2 = desc[i, j], desc[i, j + 1]
            if b1 != b2:
                pair = tuple(sorted([b1, b2]))
                if pair not in adjacent_pairs:
                    adjacent_pairs[pair] = []
                adjacent_pairs[pair].append(max(mobility[i, j], mobility[i, j + 1]))

    for i in range(149):
        for j in range(150):
            b1, b2 = desc[i, j], desc[i + 1, j]
            if b1 != b2:
                pair = tuple(sorted([b1, b2]))
                if pair not in adjacent_pairs:
                    adjacent_pairs[pair] = []
                adjacent_pairs[pair].append(max(mobility[i, j], mobility[i + 1, j]))

    barrier_heights = []
    outcome_gradients = []

    for pair, boundary_mobs in adjacent_pairs.items():
        b1, b2 = pair
        o1 = basin_outcome.get(b1)
        o2 = basin_outcome.get(b2)

        if o1 is None or o2 is None or np.isnan(o1) or np.isnan(o2):
            continue

        gradient = abs(o1 - o2)
        barrier = max(boundary_mobs) - avg_min

        outcome_gradients.append(gradient)
        barrier_heights.append(barrier)

    if len(barrier_heights) < 3:
        return {"n_pairs": len(barrier_heights), "pearson_r": np.nan, "p_value": np.nan}

    r, p = stats.pearsonr(barrier_heights, outcome_gradients)

    return {"pearson_r": r, "p_value": p, "n_pairs": len(barrier_heights), "significant": p < 0.05}


def load_wm_data_with_outcomes():
    """Load WM LSOA data with multiple outcomes."""
    gdf = gpd.read_file("poverty_tda/data/raw/boundaries/lsoa_2021/lsoa_2021_boundaries.geojson")

    # Load IMD (LSOA-level)
    imd = pd.read_csv("poverty_tda/validation/data/england_imd_2019.csv")
    imd = imd.rename(
        columns={
            "LSOA code (2011)": "lsoa_code_2011",
            "Local Authority District code (2019)": "lad_code",
            "Index of Multiple Deprivation (IMD) Score": "imd_score",
            "Index of Multiple Deprivation (IMD) Rank (where 1 is most deprived)": "imd_rank",
        }
    )

    gdf["lsoa_code_2011"] = gdf["LSOA21CD"].str[:9]
    gdf = gdf.merge(imd[["lsoa_code_2011", "lad_code", "imd_score", "imd_rank"]], on="lsoa_code_2011", how="left")

    # Filter to WM
    wm_lads = ["E08000025", "E08000026", "E08000027", "E08000028", "E08000029", "E08000030", "E08000031"]
    gdf = gdf[gdf["lad_code"].isin(wm_lads)]

    # Load KS4 data
    ks4_path = Path("data/raw/outcomes/ks4_2024.csv")
    if ks4_path.exists():
        ks4 = pd.read_csv(ks4_path)
        ks4_cols = ["la_code", "new_la_code", "la_name"]
        ks4_val = None
        for col in ["avgatt8", "pt_l2basics_94", "att8", "ptebacc_94"]:
            if col in ks4.columns:
                ks4_val = col
                break
        if ks4_val:
            ks4 = ks4.rename(columns={ks4_val: "ks4_score"})
            # Find LA code column
            la_col = "new_la_code" if "new_la_code" in ks4.columns else "la_code"
            gdf = gdf.merge(ks4[[la_col, "ks4_score"]], left_on="lad_code", right_on=la_col, how="left")
            logger.info("Loaded KS4 data")

    # Load migration data
    migration_path = Path("data/raw/outcomes/internal_migration_by_lad.xlsx")
    if migration_path.exists():
        try:
            from poverty_tda.data.process_migration import load_migration_flows, compute_lad_migration_metrics

            flows = load_migration_flows(migration_path)
            migration = compute_lad_migration_metrics(flows)
            gdf = gdf.merge(migration[["lad_code", "net_migration_rate"]], on="lad_code", how="left")
            logger.info("Loaded migration data")
        except Exception as e:
            logger.warning(f"Could not load migration: {e}")

    logger.info(f"Loaded {len(gdf)} WM LSOAs with outcomes")
    return gdf


def main():
    """Run multi-outcome barrier correlation analysis."""

    print("=" * 70)
    print("TASK 9.5.2 EXTENDED: Multi-Outcome Barrier-Gradient Correlation")
    print("=" * 70)

    vti_path = Path("poverty_tda/validation/mobility_surface_wm_150.vti")

    # Load data
    print("\n1. Loading data with multiple outcomes...")
    gdf = load_wm_data_with_outcomes()

    # Compute Morse-Smale
    print("\n2. Computing Morse-Smale complex...")
    ms_result = compute_morse_smale(vti_path, scalar_name="mobility", persistence_threshold=0.05)
    print(f"   {ms_result.n_minima} minima, {ms_result.n_saddles} saddles")

    # Assign basins
    print("\n3. Assigning LSOAs to basins...")
    gdf = assign_lsoas_to_basins(gdf, ms_result, vti_path)
    print(f"   {len(gdf)} LSOAs -> {gdf['ms_basin'].nunique()} basins")

    # Test multiple outcomes
    outcomes = []

    # 1. IMD Score (LSOA-level)
    if "imd_score" in gdf.columns and gdf["imd_score"].notna().sum() > 100:
        outcomes.append(("IMD Score (LSOA)", "imd_score"))

    # 2. IMD Rank
    if "imd_rank" in gdf.columns and gdf["imd_rank"].notna().sum() > 100:
        outcomes.append(("IMD Rank (LSOA)", "imd_rank"))

    # 3. KS4
    if "ks4_score" in gdf.columns and gdf["ks4_score"].notna().sum() > 100:
        outcomes.append(("KS4 Attainment (LAD)", "ks4_score"))

    # 4. Migration
    if "net_migration_rate" in gdf.columns and gdf["net_migration_rate"].notna().sum() > 100:
        outcomes.append(("Net Migration Rate (LAD)", "net_migration_rate"))

    print(f"\n4. Testing {len(outcomes)} outcomes...")

    results = []
    for name, col in outcomes:
        result = compute_barrier_gradient_correlation(ms_result, gdf, col, vti_path)
        result["outcome"] = name
        results.append(result)

        sig = "*" if result["significant"] else ""
        print(f"   {name}: r={result['pearson_r']:.3f}, p={result['p_value']:.4f}, n={result['n_pairs']} {sig}")

    # Summary
    print("\n" + "=" * 70)
    print("BARRIER-OUTCOME CORRELATION SUMMARY")
    print("=" * 70)
    print(f"{'Outcome':<30} {'r':>8} {'p':>10} {'N':>8} {'Sig':>5}")
    print("-" * 70)
    for r in results:
        sig = "*" if r["significant"] else ""
        print(f"{r['outcome']:<30} {r['pearson_r']:>8.3f} {r['p_value']:>10.4f} {r['n_pairs']:>8} {sig:>5}")

    return results


if __name__ == "__main__":
    results = main()
