"""
Complete Barrier-Outcome Correlation Analysis (Task 9.5.2)

Assigns LSOAs to Morse-Smale basins using descending manifold,
then computes correlation between barrier heights and LE gradients.
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyvista as pv
from scipy import stats

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from poverty_tda.topology.morse_smale import compute_morse_smale

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def assign_lsoas_to_basins(gdf: gpd.GeoDataFrame, ms_result, vti_path: Path) -> gpd.GeoDataFrame:
    """
    Assign LSOAs to Morse-Smale basins using descending manifold.

    Args:
        gdf: GeoDataFrame with LSOA polygons
        ms_result: MorseSmaleResult with descending_manifold
        vti_path: Path to VTI grid for coordinates

    Returns:
        GeoDataFrame with 'ms_basin' column added
    """
    # Load VTI to get grid parameters
    grid = pv.read(str(vti_path))
    origin = np.array(grid.origin[:2])
    spacing = np.array(grid.spacing[:2])
    dims = np.array(grid.dimensions[:2])

    logger.info(f"Grid: {dims[0]}x{dims[1]}, origin={origin}, spacing={spacing}")

    # Get LSOA centroids
    centroids = gdf.geometry.centroid
    x_coords = centroids.x.values
    y_coords = centroids.y.values

    # Convert to grid indices
    i_indices = ((x_coords - origin[0]) / spacing[0]).astype(int)
    j_indices = ((y_coords - origin[1]) / spacing[1]).astype(int)

    # Clip to valid range
    i_indices = np.clip(i_indices, 0, dims[0] - 1)
    j_indices = np.clip(j_indices, 0, dims[1] - 1)

    # Get descending manifold (basin IDs)
    # Flatten index: k = i + j * dims[0]
    flat_indices = i_indices + j_indices * dims[0]

    # Check bounds
    n_cells = dims[0] * dims[1]
    flat_indices = np.clip(flat_indices, 0, n_cells - 1)

    # Look up basin IDs
    descending = ms_result.descending_manifold
    if descending is None:
        logger.error("No descending manifold in MS result")
        return gdf

    logger.info(f"Descending manifold: {descending.shape}, range [{descending.min()}, {descending.max()}]")

    basin_ids = descending[flat_indices]
    gdf = gdf.copy()
    gdf["ms_basin"] = basin_ids

    # Count LSOAs outside grid
    in_grid = (
        (x_coords >= origin[0])
        & (x_coords < origin[0] + dims[0] * spacing[0])
        & (y_coords >= origin[1])
        & (y_coords < origin[1] + dims[1] * spacing[1])
    )
    logger.info(f"LSOAs in grid: {in_grid.sum()}/{len(gdf)}")

    n_basins = len(np.unique(basin_ids))
    logger.info(f"Assigned to {n_basins} unique basins")

    return gdf


def compute_basin_le_stats(gdf: gpd.GeoDataFrame, le_column: str, basin_column: str = "ms_basin"):
    """Compute mean LE per basin."""
    return gdf.groupby(basin_column)[le_column].agg(["mean", "std", "count"]).reset_index()


def compute_barrier_gradient_correlation(ms_result, gdf, le_column: str):
    """
    Compute correlation between barrier heights and LE gradients
    for adjacent basin pairs.
    """
    # Get mean LE per basin
    basin_le = gdf.groupby("ms_basin")[le_column].mean().to_dict()

    # Get saddle points and their values
    saddles = ms_result.get_saddles()
    minima = ms_result.get_minima()

    if not saddles or not minima:
        return None

    # Compute average minimum value for reference
    avg_min = np.mean([m.value for m in minima])

    # For each separatrix, get the connected basins and barrier height
    barrier_heights = []
    le_gradients = []

    for sep in ms_result.separatrices_1d:
        if not hasattr(sep, "source_id") or not hasattr(sep, "destination_id"):
            continue

        basin_a = sep.source_id
        basin_b = sep.destination_id

        # Get LE values for both basins
        le_a = basin_le.get(basin_a)
        le_b = basin_le.get(basin_b)

        if le_a is None or le_b is None:
            continue

        # Barrier height from separatrix
        if hasattr(sep, "values") and sep.values is not None and len(sep.values) > 0:
            barrier = np.max(sep.values) - avg_min
        else:
            continue

        gradient = abs(le_a - le_b)

        barrier_heights.append(barrier)
        le_gradients.append(gradient)

    if len(barrier_heights) < 3:
        logger.warning(f"Only {len(barrier_heights)} adjacent pairs found")
        return None

    # Compute correlation
    r, p = stats.pearsonr(barrier_heights, le_gradients)

    return {
        "pearson_r": r,
        "p_value": p,
        "n_pairs": len(barrier_heights),
        "barrier_heights": barrier_heights,
        "le_gradients": le_gradients,
    }


def load_wm_data_with_le():
    """Load West Midlands LSOA data with life expectancy."""
    # Load boundaries
    gdf = gpd.read_file("poverty_tda/data/raw/boundaries/lsoa_2021/lsoa_2021_boundaries.geojson")

    # Filter to WM
    wm_lads = ["E08000025", "E08000026", "E08000027", "E08000028", "E08000029", "E08000030", "E08000031"]
    if "LAD21CD" in gdf.columns:
        gdf = gdf[gdf["LAD21CD"].isin(wm_lads)]

    # Load LE data
    le_path = Path("data/raw/outcomes/life_expectancy_processed.csv")
    if le_path.exists():
        le = pd.read_csv(le_path)
        logger.info(f"LE columns: {le.columns.tolist()}")

        # Join by LAD
        if "LAD21CD" in gdf.columns:
            le_col = "lad_code" if "lad_code" in le.columns else le.columns[0]
            gdf = gdf.merge(le, left_on="LAD21CD", right_on=le_col, how="left")
    else:
        logger.warning(f"LE file not found: {le_path}")

    logger.info(f"Loaded {len(gdf)} WM LSOAs")
    logger.info(f"Columns: {gdf.columns.tolist()}")

    return gdf


def main():
    """Run complete barrier-outcome correlation analysis."""

    print("=" * 60)
    print("TASK 9.5.2: Complete Barrier-Outcome Correlation")
    print("=" * 60)

    vti_path = Path("poverty_tda/validation/mobility_surface_wm_150.vti")

    # 1. Load data
    print("\n1. Loading data...")
    gdf = load_wm_data_with_le()

    # Find LE column
    le_col = None
    for col in ["le_male", "life_expectancy_male", "male_life_expectancy", "life_expectancy"]:
        if col in gdf.columns:
            le_col = col
            break

    if le_col is None:
        print("   Available columns:", gdf.columns.tolist())
        print("   ERROR: No life expectancy column found!")
        return

    print(f"   Using LE column: {le_col}")
    print(f"   LE range: {gdf[le_col].min():.1f} - {gdf[le_col].max():.1f}")

    # 2. Compute Morse-Smale
    print("\n2. Computing Morse-Smale complex...")
    ms_result = compute_morse_smale(vti_path, scalar_name="mobility", persistence_threshold=0.05)
    print(f"   {ms_result.n_minima} minima, {ms_result.n_saddles} saddles")

    # 3. Assign LSOAs to basins
    print("\n3. Assigning LSOAs to basins...")
    gdf = assign_lsoas_to_basins(gdf, ms_result, vti_path)

    n_basins = gdf["ms_basin"].nunique()
    print(f"   {len(gdf)} LSOAs assigned to {n_basins} basins")

    # 4. Compute basin LE stats
    print("\n4. Computing basin LE statistics...")
    basin_stats = compute_basin_le_stats(gdf, le_col)
    print(f"   Basins with LE data: {len(basin_stats)}")

    # 5. Compute barrier-gradient correlation
    print("\n5. Computing barrier-gradient correlation...")
    result = compute_barrier_gradient_correlation(ms_result, gdf, le_col)

    if result:
        print("\n" + "=" * 60)
        print("BARRIER-OUTCOME CORRELATION RESULTS")
        print("=" * 60)
        print(f"   Pearson r: {result['pearson_r']:.4f}")
        print(f"   p-value:   {result['p_value']:.4f}")
        print(f"   N pairs:   {result['n_pairs']}")

        # Interpretation
        r = result["pearson_r"]
        p = result["p_value"]

        if r > 0.5 and p < 0.05:
            print("\n   ✓ STRONG: Barriers predict LE discontinuities")
            print("   TDA topology captures real health outcome gradients!")
        elif r > 0.3 and p < 0.05:
            print("\n   ⚠ MODERATE: Partial barrier-outcome relationship")
        elif p >= 0.05:
            print("\n   ✗ NOT SIGNIFICANT: No clear relationship")
        else:
            print(f"\n   Weak correlation: r={r:.3f}")
    else:
        print("   Could not compute correlation (insufficient data)")

    return result


if __name__ == "__main__":
    result = main()
