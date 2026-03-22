"""
Phase 1/1.5 Diagnostic Tests: Methodological Vulnerability Assessment.

Runs 5 diagnostic tests to determine whether MS basins explain outcome
variance genuinely or via methodological artefacts.

Tests:
    1. Random partition test - expected η² from random k-way partition
    2. Matched-k K-means - K-means forced to same k as MS basins
    3. Interpolation sensitivity - linear vs cubic topology
    4. LAD collapse test - effective sample size check
    5. CV R² extraction - out-of-sample performance

Usage:
    # Phase 1.5: LSOA-level outcomes (recommended)
    python -m poverty_tda.validation.diagnostic_overfitting --region west_midlands --outcome health_deprivation_score
    python -m poverty_tda.validation.diagnostic_overfitting --region west_midlands --outcome education_score
    python -m poverty_tda.validation.diagnostic_overfitting --all --outcome income_score

    # Phase 1 (original, invalidated):
    python -m poverty_tda.validation.diagnostic_overfitting --region west_midlands --outcome life_expectancy_male

See: docs/EXPERIMENTAL_METHODOLOGY_CHECKLIST.md
"""

from __future__ import annotations

import argparse
import json
import logging
import time
import warnings
from dataclasses import asdict, dataclass, field
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VALIDATION_DIR = PROJECT_ROOT / "poverty_tda" / "validation"
DATA_DIR = PROJECT_ROOT / "poverty_tda" / "data" / "raw"
OUTCOMES_DIR = PROJECT_ROOT / "data" / "raw" / "outcomes"
OUTPUT_DIR = VALIDATION_DIR / "diagnostic_results"


# =============================================================================
# METHODOLOGY CHECKLIST (from docs/EXPERIMENTAL_METHODOLOGY_CHECKLIST.md)
# =============================================================================


def check_resolution(outcome_values: np.ndarray, n_observations: int, label: str = "outcome") -> dict:
    """
    Pre-flight check #1: Resolution alignment.

    Raises ValueError if outcome has < 10% unique values relative to observations.
    Returns diagnostic dict.
    """
    n_unique = len(np.unique(outcome_values[~np.isnan(outcome_values)]))
    ratio = n_unique / n_observations
    result = {
        "check": "resolution_alignment",
        "n_observations": n_observations,
        "n_unique_outcomes": n_unique,
        "ratio": ratio,
        "passed": ratio >= 0.1,
        "severity": "CRITICAL" if ratio < 0.01 else "HIGH" if ratio < 0.1 else "OK",
    }

    if ratio < 0.01:
        logger.error(
            f"RESOLUTION MISMATCH [{label}]: {n_unique} unique values for "
            f"{n_observations} observations (ratio={ratio:.4f}). "
            f"Results are NOT meaningful — effective sample size is {n_unique}."
        )
    elif ratio < 0.1:
        logger.warning(
            f"LOW RESOLUTION [{label}]: {n_unique} unique values for "
            f"{n_observations} observations (ratio={ratio:.3f}). "
            f"Consider finding finer-grained outcome data."
        )
    else:
        logger.info(f"Resolution check passed [{label}]: {n_unique}/{n_observations} unique outcomes ({ratio:.1%})")
    return result


def random_partition_baseline(
    outcome_values: np.ndarray,
    k: int,
    n_trials: int = 200,
    seed: int = 42,
) -> dict:
    """
    Pre-flight check #2: Fair comparison baseline.

    Compute expected η² from random k-way partition.
    Any method must EXCEED this to claim genuine structure.
    """
    rng = np.random.default_rng(seed)
    valid = outcome_values[~np.isnan(outcome_values)]
    grand_mean = valid.mean()
    ss_total = np.sum((valid - grand_mean) ** 2)

    etas = []
    for _ in range(n_trials):
        labels = rng.integers(0, k, size=len(valid))
        ss_between = sum(
            np.sum(labels == c) * (valid[labels == c].mean() - grand_mean) ** 2
            for c in range(k)
            if np.sum(labels == c) > 0
        )
        etas.append(ss_between / ss_total if ss_total > 0 else 0)

    return {
        "check": "random_partition_baseline",
        "k": k,
        "n_observations": len(valid),
        "n_trials": n_trials,
        "mean_eta2": float(np.mean(etas)),
        "std_eta2": float(np.std(etas)),
        "p95_eta2": float(np.percentile(etas, 95)),
        "p99_eta2": float(np.percentile(etas, 99)),
        "theoretical_expectation": (k - 1) / (len(valid) - 1),
    }


# =============================================================================
# η² COMPUTATION
# =============================================================================


def compute_eta_squared(labels: np.ndarray, values: np.ndarray) -> float:
    """Raw η² = SS_between / SS_total."""
    valid = ~np.isnan(values)
    labels, values = labels[valid], values[valid]
    unique = np.unique(labels)
    groups = [values[labels == c] for c in unique if np.sum(labels == c) > 0]
    if len(groups) < 2:
        return 0.0
    gm = np.mean(values)
    ss_t = np.sum((values - gm) ** 2)
    ss_b = sum(len(g) * (np.mean(g) - gm) ** 2 for g in groups)
    return ss_b / ss_t if ss_t > 0 else 0.0


def compute_omega_squared(labels: np.ndarray, values: np.ndarray) -> float:
    """
    ω² = (SS_b - (k-1) * MS_w) / (SS_t + MS_w)

    Less biased than η², accounts for degrees of freedom.
    """
    valid = ~np.isnan(values)
    labels, values = labels[valid], values[valid]
    unique = np.unique(labels)
    groups = [values[labels == c] for c in unique if np.sum(labels == c) > 0]
    if len(groups) < 2:
        return 0.0
    k = len(groups)
    n = len(values)
    gm = np.mean(values)
    ss_t = np.sum((values - gm) ** 2)
    ss_b = sum(len(g) * (np.mean(g) - gm) ** 2 for g in groups)
    ss_w = ss_t - ss_b
    ms_w = ss_w / (n - k) if n > k else 0
    omega2 = (ss_b - (k - 1) * ms_w) / (ss_t + ms_w) if (ss_t + ms_w) > 0 else 0
    return max(0, omega2)  # ω² can be negative for poor models


def compute_adjusted_eta_squared(labels: np.ndarray, values: np.ndarray) -> float:
    """adj_η² = 1 - (1 - η²) * (N - 1) / (N - k)."""
    valid = ~np.isnan(values)
    labels, values = labels[valid], values[valid]
    n = len(values)
    k = len(np.unique(labels))
    eta2 = compute_eta_squared(labels, values)
    if n <= k:
        return 0.0
    return 1 - (1 - eta2) * (n - 1) / (n - k)


# =============================================================================
# DATA LOADING (mirrors run_gm_comparison.py pattern)
# =============================================================================


REGION_CONFIGS = {
    "west_midlands": {
        "lad_names": [
            "Birmingham",
            "Coventry",
            "Dudley",
            "Sandwell",
            "Solihull",
            "Walsall",
            "Wolverhampton",
        ],
        "surface_path": "mobility_surface_west_midlands.vti",
    },
    "greater_manchester": {
        "lad_names": [
            "Bolton",
            "Bury",
            "Manchester",
            "Oldham",
            "Rochdale",
            "Salford",
            "Stockport",
            "Tameside",
            "Trafford",
            "Wigan",
        ],
        "surface_path": "mobility_surface_greater_manchester.vti",
    },
}


# IMD sub-domain column mapping: short name -> CSV column name
IMD_OUTCOME_COLS = {
    "imd_score": "Index of Multiple Deprivation (IMD) Score",
    "income_score": "Income Score (rate)",
    "employment_score": "Employment Score (rate)",
    "education_score": "Education, Skills and Training Score",
    "health_deprivation_score": "Health Deprivation and Disability Score",
    "crime_score": "Crime Score",
    "housing_barriers_score": "Barriers to Housing and Services Score",
    "living_environment_score": "Living Environment Score",
    "idaci_score": "Income Deprivation Affecting Children Index (IDACI) Score (rate)",
    "idaopi_score": "Income Deprivation Affecting Older People (IDAOPI) Score (rate)",
    "children_young_people_score": "Children and Young People Sub-domain Score",
    "adult_skills_score": "Adult Skills Sub-domain Score",
}

# Default LSOA-level outcomes to test with
DEFAULT_LSOA_OUTCOMES = [
    "health_deprivation_score",
    "education_score",
    "income_score",
    "employment_score",
]


def load_regional_data(region: str) -> tuple[gpd.GeoDataFrame, np.ndarray | None]:
    """
    Load LSOA data for a region, with IMD domain/sub-domain scores.

    Returns:
        gdf: GeoDataFrame with LSOAs, IMD scores, mobility, LAD info
        ms_basins: basin labels if VTI surface exists, else None
    """
    config = REGION_CONFIGS[region]

    # Load boundaries
    boundaries_path = DATA_DIR / "boundaries" / "lsoa_2021" / "lsoa_2021_boundaries.geojson"
    if not boundaries_path.exists():
        boundaries_path = VALIDATION_DIR / "data" / "lsoa_2021_boundaries.geojson"
    gdf = gpd.read_file(boundaries_path)

    # Load and merge IMD (including all sub-domain scores)
    imd_path = VALIDATION_DIR / "data" / "england_imd_2019.csv"
    if not imd_path.exists():
        imd_path = DATA_DIR / "imd" / "england_imd_2019.csv"
    imd = pd.read_csv(imd_path)

    # Core columns always needed
    core_imd_cols = {
        "LSOA code (2011)": "lsoa_code",
        "Index of Multiple Deprivation (IMD) Score": "imd_score",
        "Local Authority District code (2019)": "lad_code",
        "Local Authority District name (2019)": "lad_name",
    }
    # Add all sub-domain outcome columns
    outcome_rename = {csv_col: short_name for short_name, csv_col in IMD_OUTCOME_COLS.items()}

    all_cols = {**core_imd_cols, **outcome_rename}
    available_cols = {c: n for c, n in all_cols.items() if c in imd.columns}
    imd_subset = imd[list(available_cols.keys())].copy()
    imd_subset.columns = list(available_cols.values())

    gdf = gdf.merge(imd_subset, left_on="LSOA21CD", right_on="lsoa_code", how="inner")

    # Filter to region
    gdf = gdf[gdf["lad_name"].isin(config["lad_names"])].reset_index(drop=True)

    # Mobility proxy
    gdf["mobility"] = -gdf["imd_score"]
    mob_range = gdf["mobility"].max() - gdf["mobility"].min()
    if mob_range > 0:
        gdf["mobility"] = (gdf["mobility"] - gdf["mobility"].min()) / mob_range
    else:
        gdf["mobility"] = 0.5

    # Load life expectancy (LAD level — kept for comparison, now secondary)
    le_path = OUTCOMES_DIR / "life_expectancy_processed.csv"
    if le_path.exists():
        le = pd.read_csv(le_path)
        gdf = gdf.merge(
            le[["area_code", "life_expectancy_male"]],
            left_on="lad_code",
            right_on="area_code",
            how="left",
        )
    else:
        gdf["life_expectancy_male"] = np.nan

    gdf = gdf.to_crs("EPSG:27700")

    # Load MS basins from VTI if available (using pyvista for VTK I/O)
    ms_basins = None
    vtk_path = VALIDATION_DIR / config["surface_path"]
    if vtk_path.exists():
        try:
            import pyvista as pv

            from poverty_tda.topology.morse_smale import compute_morse_smale

            # compute_morse_smale uses TTK subprocess internally
            ms_result = compute_morse_smale(vtk_path, persistence_threshold=0.05)

            # Read VTI metadata with pyvista (project env VTK)
            mesh = pv.read(str(vtk_path))
            dims = mesh.dimensions
            origin = mesh.origin
            spacing = mesh.spacing

            centroids = gdf.geometry.centroid
            x_idx = np.clip(
                ((centroids.x.values - origin[0]) / spacing[0]).astype(int),
                0,
                dims[0] - 1,
            )
            y_idx = np.clip(
                ((centroids.y.values - origin[1]) / spacing[1]).astype(int),
                0,
                dims[1] - 1,
            )
            ms_basins = ms_result.ascending_manifold.reshape(dims[1], dims[0])[y_idx, x_idx]
            gdf["ms_basin"] = ms_basins
            logger.info(f"Loaded {len(np.unique(ms_basins))} MS basins from {vtk_path.name}")
        except Exception as e:
            logger.warning(f"Could not load MS basins: {e}")

    # Log available outcome columns
    avail_outcomes = [c for c in IMD_OUTCOME_COLS if c in gdf.columns]
    logger.info(f"Loaded {region}: {len(gdf)} LSOAs, {gdf['lad_name'].nunique()} LADs")
    logger.info(f"Available LSOA-level outcomes: {avail_outcomes}")
    return gdf, ms_basins


# =============================================================================
# DIAGNOSTIC TESTS
# =============================================================================


@dataclass
class DiagnosticResults:
    """Container for all diagnostic test results."""

    region: str
    timestamp: str = ""
    resolution_check: dict = field(default_factory=dict)
    random_partition: dict = field(default_factory=dict)
    matched_k: dict = field(default_factory=dict)
    interpolation: dict = field(default_factory=dict)
    lad_collapse: dict = field(default_factory=dict)
    cv_r2: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def test_1_random_partition(
    gdf: gpd.GeoDataFrame,
    ms_basins: np.ndarray | None,
    outcome_col: str = "health_deprivation_score",
) -> dict:
    """
    Test 1: Random Partition Baseline.

    Generate random partitions at same k as MS basins.
    If random η² is close to MS η², the cluster count drives the result.
    """
    logger.info("=" * 60)
    logger.info("TEST 1: RANDOM PARTITION BASELINE")
    logger.info("=" * 60)

    outcome = gdf[outcome_col].values
    valid = ~np.isnan(outcome)

    if ms_basins is None:
        logger.warning("No MS basins available — using placeholder k=200")
        k_ms = 200
        ms_eta2 = None
        ms_omega2 = None
    else:
        k_ms = len(np.unique(ms_basins))
        ms_eta2 = compute_eta_squared(ms_basins[valid], outcome[valid])
        ms_omega2 = compute_omega_squared(ms_basins[valid], outcome[valid])
        logger.info(f"MS basins: k={k_ms}, η²={ms_eta2:.4f}, ω²={ms_omega2:.4f}")

    # Random partition test
    baseline = random_partition_baseline(outcome, k_ms, n_trials=200)
    logger.info(f"Random partition at k={k_ms}:")
    logger.info(f"  Mean η² = {baseline['mean_eta2']:.4f} (± {baseline['std_eta2']:.4f})")
    logger.info(f"  95th percentile = {baseline['p95_eta2']:.4f}")
    logger.info(f"  Theoretical E[η²] = {baseline['theoretical_expectation']:.4f}")

    if ms_eta2 is not None:
        excess = ms_eta2 - baseline["mean_eta2"]
        logger.info(f"  MS excess over random = {excess:.4f}")
        if excess < 0.05:
            logger.error("  ⚠ MS η² is BARELY above random — cluster count is driving results")
        elif excess < 0.20:
            logger.warning("  ⚠ MS η² is modestly above random — cluster count contributes significantly")
        else:
            logger.info("  ✓ MS η² substantially exceeds random baseline")

    result = {
        **baseline,
        "ms_k": k_ms,
        "ms_eta2": ms_eta2,
        "ms_omega2": ms_omega2,
        "ms_excess_over_random_mean": ms_eta2 - baseline["mean_eta2"] if ms_eta2 else None,
        "ms_exceeds_p95": ms_eta2 > baseline["p95_eta2"] if ms_eta2 else None,
    }
    return result


def test_2_matched_k_kmeans(
    gdf: gpd.GeoDataFrame,
    ms_basins: np.ndarray | None,
    outcome_col: str = "health_deprivation_score",
) -> dict:
    """
    Test 2: Matched-k K-means.

    Force K-means to same k as MS basins. If K-means at k=206 matches
    MS η², the MS advantage is entirely from cluster count.
    """
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    logger.info("=" * 60)
    logger.info("TEST 2: MATCHED-k K-MEANS")
    logger.info("=" * 60)

    outcome = gdf[outcome_col].values
    valid = ~np.isnan(outcome)
    centroids = gdf.geometry.centroid
    X = np.column_stack([centroids.x.values, centroids.y.values, gdf["mobility"].values])
    X_scaled = StandardScaler().fit_transform(X)

    if ms_basins is None:
        k_ms = 200
        ms_eta2 = None
    else:
        k_ms = len(np.unique(ms_basins))
        ms_eta2 = compute_eta_squared(ms_basins[valid], outcome[valid])

    # K-means at matched k
    logger.info(f"Running K-means at k={k_ms} (matching MS basin count)...")
    km_matched = KMeans(n_clusters=k_ms, random_state=42, n_init=10, max_iter=300)
    labels_matched = km_matched.fit_predict(X_scaled)
    eta2_matched = compute_eta_squared(labels_matched[valid], outcome[valid])
    omega2_matched = compute_omega_squared(labels_matched[valid], outcome[valid])

    # Also run K-means at the auto-selected k for comparison
    auto_k_values = [5, 10, 15, 20, 50, 100]
    auto_results = {}
    for k in auto_k_values:
        if k >= len(gdf):
            continue
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        lbl = km.fit_predict(X_scaled)
        eta2 = compute_eta_squared(lbl[valid], outcome[valid])
        omega2 = compute_omega_squared(lbl[valid], outcome[valid])
        auto_results[k] = {"eta2": eta2, "omega2": omega2}
        logger.info(f"  K-means k={k:>4}: η²={eta2:.4f}, ω²={omega2:.4f}")

    logger.info(f"\n  K-means k={k_ms} (matched): η²={eta2_matched:.4f}, ω²={omega2_matched:.4f}")
    if ms_eta2 is not None:
        logger.info(f"  Morse-Smale k={k_ms}:         η²={ms_eta2:.4f}")
        diff = ms_eta2 - eta2_matched
        logger.info(f"  MS advantage at matched k = {diff:+.4f}")
        if abs(diff) < 0.05:
            logger.error("  ⚠ MS advantage DISAPPEARS at matched k — topology adds nothing")
        elif diff > 0.05:
            logger.info("  ✓ MS outperforms K-means even at matched k — topology adds genuine value")
        else:
            logger.warning("  ⚠ K-means outperforms MS at matched k")

    return {
        "check": "matched_k_kmeans",
        "ms_k": k_ms,
        "ms_eta2": ms_eta2,
        "kmeans_matched_k_eta2": eta2_matched,
        "kmeans_matched_k_omega2": omega2_matched,
        "ms_advantage_at_matched_k": ms_eta2 - eta2_matched if ms_eta2 else None,
        "auto_k_results": auto_results,
    }


def test_3_interpolation_sensitivity(
    gdf: gpd.GeoDataFrame,
    outcome_col: str = "health_deprivation_score",
    grid_size: int = 100,
) -> dict:
    """
    Test 3: Interpolation Sensitivity.

    Compare Morse-Smale results with cubic vs linear interpolation.
    If basin count or η² differs substantially, topology is an interpolation artefact.
    """
    from scipy.interpolate import griddata

    logger.info("=" * 60)
    logger.info("TEST 3: INTERPOLATION SENSITIVITY")
    logger.info("=" * 60)

    centroids = gdf.geometry.centroid
    x, y = centroids.x.values, centroids.y.values
    z = gdf["mobility"].values
    outcome = gdf[outcome_col].values
    valid = ~np.isnan(outcome)

    buffer = 1000
    xi = np.linspace(x.min() - buffer, x.max() + buffer, grid_size)
    yi = np.linspace(y.min() - buffer, y.max() + buffer, grid_size)
    xi_grid, yi_grid = np.meshgrid(xi, yi)

    results = {}
    for method in ["linear", "cubic"]:
        logger.info(f"\n  Interpolation: {method}")

        # Interpolate
        zi = griddata((x, y), z, (xi_grid, yi_grid), method=method)
        zi_nn = griddata((x, y), z, (xi_grid, yi_grid), method="nearest")
        zi = np.where(np.isnan(zi), zi_nn, zi)

        # Create VTK surface with pyvista (project env), compute MS via TTK subprocess
        try:
            import pyvista as pv

            from poverty_tda.topology.morse_smale import compute_morse_smale

            x_min, x_max = x.min() - buffer, x.max() + buffer
            y_min, y_max = y.min() - buffer, y.max() + buffer
            spacing_x = (x_max - x_min) / (grid_size - 1)
            spacing_y = (y_max - y_min) / (grid_size - 1)

            # Create ImageData with pyvista
            image = pv.ImageData(
                dimensions=(grid_size, grid_size, 1),
                spacing=(spacing_x, spacing_y, 1.0),
                origin=(x_min, y_min, 0.0),
            )
            # pyvista uses Fortran ordering for structured grids
            image.point_data["mobility"] = zi.ravel(order="F").astype(np.float32)

            # Write to temp file
            tmp_path = VALIDATION_DIR / f"_diagnostic_surface_{method}.vti"
            image.save(str(tmp_path))

            # Compute MS via TTK subprocess
            ms_result = compute_morse_smale(tmp_path, persistence_threshold=0.05)

            origin_vals = image.origin
            spacing_vals = image.spacing
            dims_vals = image.dimensions

            x_idx = np.clip(((x - origin_vals[0]) / spacing_vals[0]).astype(int), 0, dims_vals[0] - 1)
            y_idx = np.clip(((y - origin_vals[1]) / spacing_vals[1]).astype(int), 0, dims_vals[1] - 1)
            basins = ms_result.ascending_manifold.reshape(dims_vals[1], dims_vals[0])[y_idx, x_idx]

            k = len(np.unique(basins))
            eta2 = compute_eta_squared(basins[valid], outcome[valid])
            omega2 = compute_omega_squared(basins[valid], outcome[valid])

            logger.info(f"    Basins: {k}, η²={eta2:.4f}, ω²={omega2:.4f}")
            results[method] = {"basins": k, "eta2": eta2, "omega2": omega2}

            # Clean up
            tmp_path.unlink(missing_ok=True)

        except Exception as e:
            logger.warning(f"    Failed for {method}: {e}")
            results[method] = {"basins": None, "eta2": None, "omega2": None, "error": str(e)}

    # Compare
    if "cubic" in results and "linear" in results:
        if results["cubic"]["basins"] and results["linear"]["basins"]:
            basin_ratio = results["cubic"]["basins"] / results["linear"]["basins"]
            eta_diff = (results["cubic"]["eta2"] or 0) - (results["linear"]["eta2"] or 0)
            logger.info(f"\n  Basin ratio (cubic/linear): {basin_ratio:.2f}")
            logger.info(f"  η² difference (cubic - linear): {eta_diff:+.4f}")
            if basin_ratio > 2.0:
                logger.warning("  ⚠ Cubic creates 2×+ more basins — many may be interpolation artefacts")
            results["basin_ratio"] = basin_ratio
            results["eta2_difference"] = eta_diff

    return {"check": "interpolation_sensitivity", **results}


def test_4_lad_collapse(
    gdf: gpd.GeoDataFrame,
    ms_basins: np.ndarray | None,
    outcome_col: str = "health_deprivation_score",
) -> dict:
    """
    Test 4: LAD-Level Collapse.

    Determine if the outcome has so few unique values that high η²
    is trivially achieved by any partition that aligns with LAD boundaries.
    """
    logger.info("=" * 60)
    logger.info("TEST 4: LAD-LEVEL COLLAPSE")
    logger.info("=" * 60)

    outcome = gdf[outcome_col].values
    n_lsoas = len(gdf)
    n_unique_outcomes = len(np.unique(outcome[~np.isnan(outcome)]))
    n_lads = gdf["lad_name"].nunique()

    logger.info(f"  LSOAs: {n_lsoas}")
    logger.info(f"  Unique outcome values: {n_unique_outcomes}")
    logger.info(f"  LADs: {n_lads}")
    logger.info(f"  Ratio (unique outcomes / LSOAs): {n_unique_outcomes / n_lsoas:.3f}")

    # Resolution check
    res_check = check_resolution(outcome, n_lsoas, outcome_col)

    # Compute η² using LAD labels directly
    lad_labels = pd.Categorical(gdf["lad_name"]).codes
    valid = ~np.isnan(outcome)
    lad_eta2 = compute_eta_squared(lad_labels[valid], outcome[valid])
    lad_omega2 = compute_omega_squared(lad_labels[valid], outcome[valid])
    logger.info(f"  LAD-as-partition η² = {lad_eta2:.4f} (at k={n_lads})")
    logger.info(f"  LAD-as-partition ω² = {lad_omega2:.4f}")

    # If outcome is at LAD level, LAD η² should be ~1.0 (perfect prediction)
    if n_unique_outcomes <= n_lads + 2:  # allow minor variation
        logger.error(
            f"  ⚠ CRITICAL: Only {n_unique_outcomes} unique outcome values "
            f"for {n_lads} LADs. Outcome appears to be at LAD level."
        )
        logger.error(
            "  ⚠ Any partition aligning with LADs will achieve high η². This is a lookup table, not prediction."
        )

    # Compare MS η² with LAD η²
    ms_comparison = None
    if ms_basins is not None:
        ms_eta2 = compute_eta_squared(ms_basins[valid], outcome[valid])
        ms_comparison = {
            "ms_eta2": ms_eta2,
            "lad_eta2": lad_eta2,
            "difference": ms_eta2 - lad_eta2,
            "ms_captures_within_lad_variance": ms_eta2 > lad_eta2 + 0.02,
        }
        logger.info(f"  MS η² = {ms_eta2:.4f} vs LAD η² = {lad_eta2:.4f}")
        if ms_eta2 <= lad_eta2 + 0.02:
            logger.error(
                "  ⚠ MS does not explain more variance than LAD labels alone. "
                "The 'prediction' is just LAD boundary detection."
            )
        else:
            logger.info(
                f"  ✓ MS explains {ms_eta2 - lad_eta2:.4f} more variance than LAD labels "
                "(captures within-LAD structure)"
            )

    return {
        "check": "lad_collapse",
        "n_lsoas": n_lsoas,
        "n_unique_outcomes": n_unique_outcomes,
        "n_lads": n_lads,
        "outcome_is_lad_level": n_unique_outcomes <= n_lads + 2,
        "lad_eta2": lad_eta2,
        "lad_omega2": lad_omega2,
        "resolution_check": res_check,
        "ms_comparison": ms_comparison,
    }


def test_5_cv_r2(
    gdf: gpd.GeoDataFrame,
    ms_basins: np.ndarray | None,
    outcome_col: str = "health_deprivation_score",
) -> dict:
    """
    Test 5: Cross-Validated R².

    Compare in-sample R² (what was reported) with:
    - Random 5-fold CV R²
    - Leave-one-LAD-out CV R²
    - Spatial block CV R²

    Uses one-hot encoded basin dummies as features (matching original pipeline).
    """
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import OneHotEncoder

    logger.info("=" * 60)
    logger.info("TEST 5: CROSS-VALIDATED R²")
    logger.info("=" * 60)

    outcome = gdf[outcome_col].values
    valid = ~np.isnan(outcome)
    y = outcome[valid]
    n = len(y)

    results = {}

    # Prepare method features
    methods_to_test = {}
    if ms_basins is not None:
        methods_to_test["MS_basins"] = ms_basins[valid]

    # Also add K-means at matched k
    if ms_basins is not None:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler

        centroids = gdf.geometry.centroid
        X_spatial = np.column_stack(
            [
                centroids.x.values[valid],
                centroids.y.values[valid],
                gdf["mobility"].values[valid],
            ]
        )
        X_scaled = StandardScaler().fit_transform(X_spatial)
        k_ms = len(np.unique(ms_basins))
        km = KMeans(n_clusters=min(k_ms, n - 1), random_state=42, n_init=10)
        methods_to_test["KMeans_matched_k"] = km.fit_predict(X_scaled)

    # IMD baseline
    methods_to_test["IMD_only"] = None  # special case — use imd_score directly

    encoder = OneHotEncoder(sparse_output=False, drop="first", handle_unknown="ignore")

    for method_name, labels in methods_to_test.items():
        logger.info(f"\n  Method: {method_name}")

        if labels is None:
            # IMD baseline - use raw imd_score
            X = gdf["imd_score"].values[valid].reshape(-1, 1)
            p = 1
        else:
            # One-hot encode labels
            X = encoder.fit_transform(labels.reshape(-1, 1).astype(str))
            p = X.shape[1]

        lr = LinearRegression()

        # In-sample R²
        lr.fit(X, y)
        r2_insample = lr.score(X, y)

        # Random 5-fold CV
        cv_scores_random = cross_val_score(lr, X, y, cv=min(5, n // 2), scoring="r2")
        r2_cv_random = cv_scores_random.mean()

        # Leave-one-LAD-out CV
        lad_labels = pd.Categorical(gdf["lad_name"].values[valid]).codes
        unique_lads = np.unique(lad_labels)
        loo_lad_scores = []
        for test_lad in unique_lads:
            train_mask = lad_labels != test_lad
            test_mask = lad_labels == test_lad

            if sum(test_mask) < 2 or sum(train_mask) < p + 1:
                continue

            try:
                lr_cv = LinearRegression()
                lr_cv.fit(X[train_mask], y[train_mask])
                score = lr_cv.score(X[test_mask], y[test_mask])
                loo_lad_scores.append(score)
            except Exception:
                continue

        r2_loo_lad = np.mean(loo_lad_scores) if loo_lad_scores else None

        logger.info(f"    Features: {p}")
        logger.info(f"    In-sample R² = {r2_insample:.4f}")
        logger.info(f"    Random 5-fold CV R² = {r2_cv_random:.4f}")
        if r2_loo_lad is not None:
            logger.info(f"    Leave-one-LAD-out R² = {r2_loo_lad:.4f}")

        # Overfitting gap
        gap = r2_insample - r2_cv_random
        logger.info(f"    Overfitting gap (in-sample - CV) = {gap:+.4f}")
        if gap > 0.10:
            logger.warning(f"    ⚠ Large overfitting gap ({gap:.3f}) — in-sample R² is misleading")

        results[method_name] = {
            "n_features": p,
            "r2_insample": r2_insample,
            "r2_cv_random_5fold": r2_cv_random,
            "r2_cv_random_fold_scores": cv_scores_random.tolist(),
            "r2_loo_lad": r2_loo_lad,
            "r2_loo_lad_fold_scores": loo_lad_scores if loo_lad_scores else None,
            "overfitting_gap": gap,
        }

    return {"check": "cv_r2", "methods": results}


# =============================================================================
# MAIN ORCHESTRATION
# =============================================================================


def run_all_diagnostics(region: str, outcome_col: str = "health_deprivation_score") -> DiagnosticResults:
    """Run all 5 diagnostic tests for a region with specified outcome."""
    from datetime import datetime

    logger.info("=" * 70)
    logger.info(f"METHODOLOGICAL DIAGNOSTIC SUITE — {region.upper()}")
    logger.info(f"OUTCOME: {outcome_col}")
    logger.info("=" * 70)
    t0 = time.time()

    # Load data
    gdf, ms_basins = load_regional_data(region)

    # Validate the requested outcome column exists
    if outcome_col not in gdf.columns:
        available = [c for c in IMD_OUTCOME_COLS if c in gdf.columns]
        raise ValueError(
            f"Outcome column '{outcome_col}' not found in data. Available LSOA-level outcomes: {available}"
        )

    results = DiagnosticResults(
        region=region,
        timestamp=datetime.now().isoformat(),
    )

    # Pre-flight: Resolution check
    outcome = gdf[outcome_col].values
    results.resolution_check = check_resolution(outcome, len(gdf), outcome_col)

    # Test 1: Random partition
    results.random_partition = test_1_random_partition(gdf, ms_basins, outcome_col=outcome_col)

    # Test 2: Matched-k K-means
    results.matched_k = test_2_matched_k_kmeans(gdf, ms_basins, outcome_col=outcome_col)

    # Test 3: Interpolation sensitivity
    results.interpolation = test_3_interpolation_sensitivity(gdf, outcome_col=outcome_col)

    # Test 4: LAD collapse
    results.lad_collapse = test_4_lad_collapse(gdf, ms_basins, outcome_col=outcome_col)

    # Test 5: CV R²
    results.cv_r2 = test_5_cv_r2(gdf, ms_basins, outcome_col=outcome_col)

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("DIAGNOSTIC SUMMARY")
    logger.info(f"Outcome: {outcome_col}")
    logger.info("=" * 70)

    issues = []
    if results.resolution_check.get("severity") in ("CRITICAL", "HIGH"):
        issues.append(f"RESOLUTION MISMATCH: {outcome_col} has insufficient unique values")

    rp = results.random_partition
    if rp.get("ms_excess_over_random_mean") is not None and rp["ms_excess_over_random_mean"] < 0.20:
        issues.append(f"CLUSTER COUNT INFLATION: MS excess over random is only {rp['ms_excess_over_random_mean']:.3f}")

    mk = results.matched_k
    if mk.get("ms_advantage_at_matched_k") is not None and mk["ms_advantage_at_matched_k"] < 0.05:
        issues.append(f"NO MS ADVANTAGE AT MATCHED K: diff = {mk['ms_advantage_at_matched_k']:+.3f}")

    lc = results.lad_collapse
    if lc.get("outcome_is_lad_level"):
        issues.append(f"LAD-LEVEL OUTCOME: Only {lc['n_unique_outcomes']} unique values for {lc['n_lsoas']} LSOAs")

    cv = results.cv_r2
    for method, method_results in cv.get("methods", {}).items():
        if method_results.get("overfitting_gap", 0) > 0.10:
            issues.append(f"OVERFITTING ({method}): gap = {method_results['overfitting_gap']:.3f}")

    results.summary = {
        "outcome_col": outcome_col,
        "total_issues": len(issues),
        "issues": issues,
        "elapsed_seconds": time.time() - t0,
    }

    if issues:
        logger.warning(f"\n  FOUND {len(issues)} ISSUE(S):")
        for i, issue in enumerate(issues, 1):
            logger.warning(f"    {i}. {issue}")
    else:
        logger.info("  ✓ No critical issues found. Results appear methodologically sound.")

    return results


def save_results(results: DiagnosticResults):
    """Save diagnostic results to JSON."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outcome = results.summary.get("outcome_col", "unknown")
    path = OUTPUT_DIR / f"diagnostic_{results.region}_{outcome}_{results.timestamp[:10]}.json"
    with open(path, "w") as f:
        json.dump(results.to_dict(), f, indent=2, default=str)
    logger.info(f"\nResults saved to {path}")
    return path


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Diagnostic Tests for TDA Methodology Validation (Phase 1/1.5)",
        epilog="See docs/EXPERIMENTAL_METHODOLOGY_CHECKLIST.md for context.",
    )
    parser.add_argument(
        "--region",
        choices=list(REGION_CONFIGS.keys()),
        default="west_midlands",
        help="Region to analyze (default: west_midlands)",
    )
    parser.add_argument(
        "--outcome",
        choices=list(IMD_OUTCOME_COLS.keys()) + ["life_expectancy_male"],
        default="health_deprivation_score",
        help="Outcome variable to test against (default: health_deprivation_score)",
    )
    parser.add_argument(
        "--test",
        choices=["random_partition", "matched_k", "interpolation", "lad_collapse", "cv_r2"],
        help="Run a single test (default: run all)",
    )
    parser.add_argument("--all", action="store_true", help="Run all tests for all regions")
    parser.add_argument(
        "--all-outcomes",
        action="store_true",
        help="Run diagnostics for all default LSOA-level outcomes",
    )
    args = parser.parse_args()

    if args.all_outcomes:
        for region in REGION_CONFIGS:
            for outcome in DEFAULT_LSOA_OUTCOMES:
                logger.info(f"\n{'#' * 80}")
                logger.info(f"# {region.upper()} — {outcome}")
                logger.info(f"{'#' * 80}")
                results = run_all_diagnostics(region, outcome_col=outcome)
                save_results(results)
    elif args.all:
        for region in REGION_CONFIGS:
            results = run_all_diagnostics(region, outcome_col=args.outcome)
            save_results(results)
    elif args.test:
        gdf, ms_basins = load_regional_data(args.region)
        oc = args.outcome
        test_fn = {
            "random_partition": lambda: test_1_random_partition(gdf, ms_basins, outcome_col=oc),
            "matched_k": lambda: test_2_matched_k_kmeans(gdf, ms_basins, outcome_col=oc),
            "interpolation": lambda: test_3_interpolation_sensitivity(gdf, outcome_col=oc),
            "lad_collapse": lambda: test_4_lad_collapse(gdf, ms_basins, outcome_col=oc),
            "cv_r2": lambda: test_5_cv_r2(gdf, ms_basins, outcome_col=oc),
        }
        result = test_fn[args.test]()
        print(json.dumps(result, indent=2, default=str))
    else:
        results = run_all_diagnostics(args.region, outcome_col=args.outcome)
        save_results(results)


if __name__ == "__main__":
    main()
