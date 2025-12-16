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

    # Reproject to BNG if needed (grid is in BNG coordinates)
    if gdf.crs and gdf.crs.to_epsg() != 27700:
        logger.info(f"Reprojecting from {gdf.crs} to EPSG:27700 (BNG)")
        gdf = gdf.to_crs(epsg=27700)

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

    # Build minimum point_id → index mapping
    min_id_to_idx = {m.point_id: i for i, m in enumerate(minima)}

    # Average minimum value for reference
    avg_min = np.mean([m.value for m in minima])

    # Find adjacent basin pairs from separatrices
    # Each separatrix connects two critical points
    # For min-saddle-min paths, we look for saddles that connect two minima

    barrier_heights = []
    le_gradients = []

    # First, get adjacency from the descending manifold grid
    # Two basins are adjacent if there are neighboring cells with different basin IDs
    if ms_result.descending_manifold is not None:
        desc = ms_result.descending_manifold.reshape(150, 150)  # Reshape to grid

        # Load mobility values from VTI
        grid = pv.read(str(Path("poverty_tda/validation/mobility_surface_wm_150.vti")))
        mobility = grid.point_data["mobility"].reshape(150, 150)

        adjacent_pairs = {}  # pair -> list of boundary mobility values

        # Look at horizontal neighbors
        for i in range(150):
            for j in range(149):
                b1, b2 = desc[i, j], desc[i, j + 1]
                if b1 != b2:
                    pair = tuple(sorted([b1, b2]))
                    if pair not in adjacent_pairs:
                        adjacent_pairs[pair] = []
                    # Barrier = max mobility along boundary
                    adjacent_pairs[pair].append(max(mobility[i, j], mobility[i, j + 1]))

        # Look at vertical neighbors
        for i in range(149):
            for j in range(150):
                b1, b2 = desc[i, j], desc[i + 1, j]
                if b1 != b2:
                    pair = tuple(sorted([b1, b2]))
                    if pair not in adjacent_pairs:
                        adjacent_pairs[pair] = []
                    adjacent_pairs[pair].append(max(mobility[i, j], mobility[i + 1, j]))

        logger.info(f"Found {len(adjacent_pairs)} adjacent basin pairs from grid")

        # For each adjacent pair, compute LE gradient and barrier height
        for pair, boundary_mobs in adjacent_pairs.items():
            b1, b2 = pair
            le1 = basin_le.get(b1)
            le2 = basin_le.get(b2)

            if le1 is None or le2 is None:
                continue

            gradient = abs(le1 - le2)

            # Barrier = max mobility along boundary between these basins
            barrier = max(boundary_mobs) - avg_min

            le_gradients.append(gradient)
            barrier_heights.append(barrier)

    if len(barrier_heights) < 3:
        logger.warning(f"Only {len(barrier_heights)} pairs with LE data")
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
    logger.info(f"Loaded {len(gdf)} LSOAs")

    # Load IMD with LAD codes (bridge LSOA to LAD)
    imd = pd.read_csv("poverty_tda/validation/data/england_imd_2019.csv")
    imd = imd.rename(
        columns={
            "LSOA code (2011)": "lsoa_code_2011",
            "Local Authority District code (2019)": "lad_code",
            "Index of Multiple Deprivation (IMD) Score": "imd_score",
        }
    )

    # LSOA21CD to LSOA11CD mapping (first 9 chars often match)
    # Try direct merge first, then substring
    gdf["lsoa_code_2011"] = gdf["LSOA21CD"].str[:9]  # E01XXXXXX pattern

    # Merge IMD to get LAD codes
    gdf = gdf.merge(imd[["lsoa_code_2011", "lad_code", "imd_score"]], on="lsoa_code_2011", how="left")
    logger.info(f"After IMD merge: {gdf['lad_code'].notna().sum()} with LAD code")

    # Filter to WM
    wm_lads = ["E08000025", "E08000026", "E08000027", "E08000028", "E08000029", "E08000030", "E08000031"]
    gdf = gdf[gdf["lad_code"].isin(wm_lads)]
    logger.info(f"Filtered to {len(gdf)} WM LSOAs")

    # Load LE data
    le_path = Path("data/raw/outcomes/life_expectancy_processed.csv")
    if le_path.exists():
        le = pd.read_csv(le_path)
        # Rename for merge
        le = le.rename(columns={"area_code": "lad_code", "life_expectancy_male": "le_male"})
        logger.info(f"LE LADs: {le['lad_code'].nunique()}")

        # Join by LAD
        gdf = gdf.merge(le[["lad_code", "le_male"]], on="lad_code", how="left")
        logger.info(f"LE range: {gdf['le_male'].min():.1f} - {gdf['le_male'].max():.1f}")
    else:
        logger.warning(f"LE file not found: {le_path}")

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
