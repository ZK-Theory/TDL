"""
Run Barrier-Outcome Correlation Analysis (Task 9.5.2)

Tests whether Morse-Smale barrier heights predict real outcome gradients
across basin boundaries - TDA's unique value proposition.
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from poverty_tda.topology.morse_smale import compute_morse_smale
from poverty_tda.validation.spatial_comparison import (
    compute_barrier_outcome_correlation,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Paths
WM_SURFACE = Path("poverty_tda/validation/mobility_surface_wm_150.vti")
GM_SURFACE = Path("poverty_tda/validation/mobility_surface_greater_manchester.vti")


def load_regional_lsoa_data(region: str = "west_midlands"):
    """Load LSOA data with basin assignments and outcomes."""
    # Load boundaries
    boundaries_path = Path("poverty_tda/data/raw/boundaries/lsoa_2021/lsoa_2021_boundaries.geojson")
    gdf = gpd.read_file(boundaries_path)

    # Load IMD
    imd_path = Path("poverty_tda/validation/data/england_imd_2019.csv")
    imd = pd.read_csv(imd_path)

    # Rename IMD columns for easier joining
    imd_cols = {
        "LSOA code (2011)": "lsoa_code",
        "Index of Multiple Deprivation (IMD) Score": "imd_score",
        "Index of Multiple Deprivation (IMD) Rank (where 1 is most deprived)": "imd_rank",
    }
    imd = imd.rename(columns={k: v for k, v in imd_cols.items() if k in imd.columns})

    # Load life expectancy
    le_path = Path("data/raw/outcomes/life_expectancy_processed.csv")
    if le_path.exists():
        le = pd.read_csv(le_path)
    else:
        le = None
        logger.warning(f"Life expectancy file not found: {le_path}")

    # Join IMD - try multiple column name variations
    join_col = None
    for col in ["LSOA21CD", "lsoa21cd", "lsoa_code"]:
        if col in gdf.columns:
            join_col = col
            break

    if join_col:
        gdf = gdf.merge(imd, left_on=join_col, right_on="lsoa_code", how="left")

    # Filter to region
    if region == "west_midlands":
        wm_lads = ["E08000025", "E08000026", "E08000027", "E08000028", "E08000029", "E08000030", "E08000031"]
        lad_col = "LAD21CD" if "LAD21CD" in gdf.columns else None
        if lad_col:
            gdf = gdf[gdf[lad_col].isin(wm_lads)]

    # Join LE by LAD
    if "LAD21CD" in gdf.columns:
        gdf = gdf.merge(le, left_on="LAD21CD", right_on="lad_code", how="left")

    logger.info(f"Loaded {len(gdf)} LSOAs for {region}")
    return gdf


def run_barrier_analysis(surface_path: Path, gdf: gpd.GeoDataFrame, region_name: str):
    """Run barrier-outcome correlation for a region."""

    print(f"\n{'='*60}")
    print(f"TASK 9.5.2: Barrier Analysis - {region_name}")
    print(f"{'='*60}")

    if not surface_path.exists():
        print(f"ERROR: Surface not found at {surface_path}")
        return None

    # 1. Compute Morse-Smale complex
    print("\n1. Computing Morse-Smale complex...")
    try:
        ms_result = compute_morse_smale(surface_path, scalar_name="mobility", persistence_threshold=0.05)
        print(f"   Critical points: {len(ms_result.critical_points)}")
        print(f"   - Minima: {ms_result.n_minima}")
        print(f"   - Saddles: {ms_result.n_saddles}")
        print(f"   - Maxima: {ms_result.n_maxima}")
        print(f"   Separatrices: {len(ms_result.separatrices_1d)}")
    except Exception as e:
        print(f"ERROR computing Morse-Smale: {e}")
        return None

    # 2. Check for required data
    outcome_col = None
    for col in ["life_expectancy_male", "male_life_expectancy", "life_expectancy", "le_male"]:
        if col in gdf.columns:
            outcome_col = col
            break

    if outcome_col is None:
        print("   Note: No life expectancy column found - will analyze barrier structure only")

    # 3. Compute barrier-outcome correlation
    print("\n2. Computing barrier-outcome correlation...")

    if "ms_basin" not in gdf.columns:
        print("   No basin assignments in GDF - analyzing separatrix structure directly...")

        # Analyze separatrix values to understand barrier distribution
        if ms_result.separatrices_1d:
            sep_max_values = []
            for sep in ms_result.separatrices_1d:
                if hasattr(sep, "values") and sep.values is not None and len(sep.values) > 0:
                    sep_max_values.append(np.max(sep.values))

            if sep_max_values:
                sep_max_values = np.array(sep_max_values)
                print(f"\n   Separatrix barrier heights (n={len(sep_max_values)}):")
                print(f"   - Mean: {np.mean(sep_max_values):.4f}")
                print(f"   - Std:  {np.std(sep_max_values):.4f}")
                print(f"   - Min:  {np.min(sep_max_values):.4f}")
                print(f"   - Max:  {np.max(sep_max_values):.4f}")

        # Get saddle values (actual barrier heights)
        saddles = ms_result.get_saddles()
        if saddles:
            saddle_values = [s.value for s in saddles]
            print(f"\n   Saddle point values (n={len(saddle_values)}):")
            print(f"   - Mean: {np.mean(saddle_values):.4f}")
            print(f"   - Std:  {np.std(saddle_values):.4f}")
            print(f"   - Range: [{np.min(saddle_values):.4f}, {np.max(saddle_values):.4f}]")

            # Compute barrier heights relative to adjacent minima
            minima = ms_result.get_minima()
            if minima:
                minima_values = [m.value for m in minima]
                avg_minimum = np.mean(minima_values)
                barrier_heights = [s.value - avg_minimum for s in saddles]

                print("\n   Barrier heights (saddle - avg_minimum):")
                print(f"   - Mean barrier: {np.mean(barrier_heights):.4f}")
                print(f"   - Max barrier:  {np.max(barrier_heights):.4f}")

        # Summary for paper
        print(f"\n{'='*60}")
        print("TASK 9.5.2 PARTIAL RESULTS (No basin assignments)")
        print(f"{'='*60}")
        print("   Morse-Smale complex computed successfully:")
        print(f"   - {ms_result.n_minima} poverty traps (minima)")
        print(f"   - {ms_result.n_saddles} barriers (saddles)")
        print(f"   - {len(ms_result.separatrices_1d)} separatrices")
        print("\n   To complete barrier-outcome correlation:")
        print("   1. Assign LSOAs to basins using descending manifold")
        print("   2. Compute mean LE per basin")
        print("   3. Correlate barrier heights with LE gradients")

        return ms_result

    try:
        result = compute_barrier_outcome_correlation(
            ms_result, gdf, outcome_column=outcome_col, basin_column="ms_basin"
        )

        print(f"\n{'='*60}")
        print("BARRIER-OUTCOME CORRELATION RESULTS")
        print(f"{'='*60}")
        print(f"   Pearson r: {result.pearson_r:.4f}")
        print(f"   p-value: {result.p_value:.4f}")
        print(f"   N pairs: {result.n_pairs}")
        print(f"\n   Interpretation: {result.interpretation}")

        # Success criterion
        if result.pearson_r > 0.5 and result.p_value < 0.05:
            print("\n   ✓ SUCCESS: r > 0.5 - TDA barriers capture real discontinuities!")
        elif result.pearson_r > 0.3 and result.p_value < 0.05:
            print("\n   ⚠ PARTIAL: r > 0.3 - Moderate evidence for TDA barriers")
        else:
            print("\n   ✗ WEAK: r < 0.3 - TDA barriers may not align with outcomes")

        return result

    except Exception as e:
        print(f"ERROR in correlation: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Run barrier analysis for West Midlands."""

    # Load data
    print("Loading West Midlands LSOA data...")
    gdf = load_regional_lsoa_data("west_midlands")

    # Check available surfaces
    print("\nAvailable mobility surfaces:")
    for p in Path("poverty_tda/validation").glob("mobility_surface*.vti"):
        print(f"  - {p.name}")

    # Run analysis on WM 150x150 surface
    if WM_SURFACE.exists():
        result = run_barrier_analysis(WM_SURFACE, gdf, "West Midlands (150x150)")
    else:
        # Fall back to 100x100
        alt_path = Path("poverty_tda/validation/mobility_surface_wm_100.vti")
        if alt_path.exists():
            result = run_barrier_analysis(alt_path, gdf, "West Midlands (100x100)")
        else:
            print("No WM surface found!")
            result = None

    return result


if __name__ == "__main__":
    result = main()
