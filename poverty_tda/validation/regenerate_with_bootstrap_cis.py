"""
Regenerate validation results with bootstrap confidence intervals.

This script loads the same data used in the original analyses and regenerates
the result files with proper bootstrap CIs (n=1000).
"""

import json
import logging
import subprocess
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
VALIDATION_DIR = Path(__file__).parent
RESULTS_DIR = VALIDATION_DIR / "results"


def load_lsoa_with_outcomes(region_lads: list[str], region_name: str) -> gpd.GeoDataFrame:
    """Load LSOA data with outcomes for a specific region."""
    logger.info(f"Loading data for {region_name}...")

    # Load boundaries
    gdf = gpd.read_file(PROJECT_ROOT / "poverty_tda/data/raw/boundaries/lsoa_2021/lsoa_2021_boundaries.geojson")

    # Load IMD
    imd = pd.read_csv(VALIDATION_DIR / "data/england_imd_2019.csv")
    imd_cols = [
        "LSOA code (2011)",
        "Index of Multiple Deprivation (IMD) Score",
        "Local Authority District code (2019)",
        "Local Authority District name (2019)",
    ]
    imd_subset = imd[imd_cols].copy()
    imd_subset.columns = ["lsoa_code", "imd_score", "lad_code", "lad_name"]

    # Merge
    gdf = gdf.merge(imd_subset, left_on="LSOA21CD", right_on="lsoa_code", how="inner")

    # Filter to region
    gdf = gdf[gdf["lad_name"].isin(region_lads)].reset_index(drop=True)

    # Create mobility (inverse deprivation)
    gdf["mobility"] = -gdf["imd_score"]
    gdf["mobility"] = (gdf["mobility"] - gdf["mobility"].min()) / (gdf["mobility"].max() - gdf["mobility"].min())

    # Load life expectancy (both male and female)
    le = pd.read_csv(PROJECT_ROOT / "data/raw/outcomes/life_expectancy_both.csv")
    gdf = gdf.merge(
        le[["area_code", "le_male", "le_female"]],
        left_on="lad_code",
        right_on="area_code",
        how="left",
    )
    gdf = gdf.rename(
        columns={
            "le_male": "life_expectancy_male",
            "le_female": "life_expectancy_female",
        }
    )

    # Load KS4 (if exists)
    ks4_path = PROJECT_ROOT / "data/raw/outcomes/attainment8_processed.csv"
    if ks4_path.exists():
        ks4 = pd.read_csv(ks4_path)
        gdf = gdf.merge(
            ks4[["area_code", "attainment8_average"]],
            left_on="lad_code",
            right_on="area_code",
            how="left",
            suffixes=("", "_ks4"),
        )

    # Drop NaN life expectancy
    gdf = gdf.dropna(subset=["life_expectancy_male"])

    # Convert to British National Grid
    gdf = gdf.to_crs("EPSG:27700")

    logger.info(f"  Loaded {len(gdf)} LSOAs")

    return gdf


def load_ms_basins_from_vti(gdf: gpd.GeoDataFrame, vti_file: Path) -> gpd.GeoDataFrame:
    """Load Morse-Smale basins from VTI file using existing topology module."""
    logger.info(f"Computing MS basins from {vti_file.name}...")

    # Use the existing compute_morse_smale function that handles TTK properly
    from poverty_tda.topology.morse_smale import compute_morse_smale

    ms_result = compute_morse_smale(vti_file, persistence_threshold=0.05)

    # Get VTI grid parameters using TTK conda environment
    script = f"""
import vtk
reader = vtk.vtkXMLImageDataReader()
reader.SetFileName("{str(vti_file).replace(chr(92), "/")}")
reader.Update()
img = reader.GetOutput()
print(f"{{img.GetDimensions()[0]}},{{img.GetDimensions()[1]}},{{img.GetDimensions()[2]}}")
print(f"{{img.GetOrigin()[0]}},{{img.GetOrigin()[1]}},{{img.GetOrigin()[2]}}")
print(f"{{img.GetSpacing()[0]}},{{img.GetSpacing()[1]}},{{img.GetSpacing()[2]}}")
"""

    ttk_python = Path(
        "~/miniconda3/envs/ttk_env/python.exe" if sys.platform == "win32" else "~/miniconda3/envs/ttk_env/bin/python"
    ).expanduser()

    result = subprocess.run([str(ttk_python), "-c", script], capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        raise RuntimeError(f"Failed to read VTI: {result.stderr}")

    lines = result.stdout.strip().split("\n")
    dims = tuple(map(int, lines[0].split(",")))
    origin = tuple(map(float, lines[1].split(",")))
    spacing = tuple(map(float, lines[2].split(",")))

    # Map LSOA centroids to grid
    centroids = gdf.geometry.centroid
    x, y = centroids.x.values, centroids.y.values

    x_idx = np.clip(((x - origin[0]) / spacing[0]).astype(int), 0, dims[0] - 1)
    y_idx = np.clip(((y - origin[1]) / spacing[1]).astype(int), 0, dims[1] - 1)

    gdf["ms_basin"] = ms_result.ascending_manifold.reshape(dims[1], dims[0])[y_idx, x_idx]

    logger.info(f"  Computed {gdf['ms_basin'].nunique()} basins")

    return gdf


def load_kmeans_clusters(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add K-means clusters."""
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    centroids = gdf.geometry.centroid
    x, y = centroids.x.values, centroids.y.values
    X = np.column_stack([x, y, gdf["mobility"].values])
    X_scaled = StandardScaler().fit_transform(X)

    gdf["kmeans"] = KMeans(n_clusters=10, random_state=42, n_init=10).fit_predict(X_scaled)

    logger.info("  K-means: 10 clusters")

    return gdf


def compute_eta_squared_with_bootstrap(
    labels: np.ndarray,
    values: np.ndarray,
    n_bootstrap: int = 1000,
    random_state: int = 42,
) -> tuple[float, float, float]:
    """Compute eta-squared with bootstrap CIs."""

    def eta_sq(lab, val):
        # Remove NaN
        mask = ~(np.isnan(lab) | np.isnan(val))
        lab = lab[mask]
        val = val[mask]

        if len(lab) < 2:
            return np.nan

        unique = np.unique(lab)
        if len(unique) < 2:
            return np.nan

        groups = [val[lab == c] for c in unique if np.sum(lab == c) > 0]
        if len(groups) < 2:
            return 0.0

        gm = np.mean(val)
        ss_t = np.sum((val - gm) ** 2)
        ss_b = sum(len(g) * (np.mean(g) - gm) ** 2 for g in groups)

        return ss_b / ss_t if ss_t > 0 else 0.0

    point = eta_sq(labels, values)

    rng = np.random.default_rng(random_state)
    etas = []
    n = len(labels)

    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, n)
        boot_eta = eta_sq(labels[idx], values[idx])
        if not np.isnan(boot_eta):
            etas.append(boot_eta)

    if len(etas) > 0:
        ci_lower = np.percentile(etas, 2.5)
        ci_upper = np.percentile(etas, 97.5)
    else:
        ci_lower = None
        ci_upper = None

    return point, ci_lower, ci_upper


def update_result_file_with_cis(result_file: Path, gdf: gpd.GeoDataFrame, n_bootstrap: int = 1000) -> bool:
    """Update a result file with bootstrap CIs."""
    logger.info(f"\nProcessing: {result_file.name}")

    # Load existing result
    try:
        with open(result_file, encoding="utf-8") as f:
            data = json.load(f)
    except UnicodeDecodeError:
        with open(result_file, encoding="latin-1") as f:
            data = json.load(f)

    outcome_var = data["outcome_variable"]
    methods = data["methods"]

    logger.info(f"  Outcome: {outcome_var}")
    logger.info(f"  Methods: {len(methods)}")

    updated = False

    for method in methods:
        method_name = method["name"]
        column = method["column"]
        current_eta2 = method["eta_squared"]

        # Skip if already has CIs
        if method.get("eta_squared_ci_lower") is not None:
            logger.info(f"  ✓ {method_name}: Already has CIs, skipping")
            continue

        # Determine outcome column
        if "Male" in method_name or "(LE)" in method_name:
            outcome_col = "life_expectancy_male"
        elif "Female" in method_name:
            outcome_col = "life_expectancy_female"
        elif "KS4" in method_name:
            outcome_col = "attainment8_average"
        elif "male and female" in outcome_var.lower():
            outcome_col = "life_expectancy_male"  # Default for multi-outcome
        elif "attainment" in outcome_var.lower():
            outcome_col = "attainment8_average"
        else:
            outcome_col = "life_expectancy_male"  # Default

        # Check columns exist
        if column not in gdf.columns:
            # Try common variations
            column_variations = [
                column,
                f"{column}_cluster",
                column.replace("_cluster", ""),
            ]
            found_column = None
            for variant in column_variations:
                if variant in gdf.columns:
                    found_column = variant
                    break

            if found_column is None:
                logger.warning(f"  ⚠️  Column {column} not found")
                continue
            column = found_column

        if outcome_col not in gdf.columns:
            logger.warning(f"  ⚠️  Outcome {outcome_col} not found - skipping")
            continue

        # Compute CIs
        labels = gdf[column].values
        values = gdf[outcome_col].values

        eta2, ci_lower, ci_upper = compute_eta_squared_with_bootstrap(labels, values, n_bootstrap=n_bootstrap)

        # Verify eta2 matches (within tolerance)
        if not np.isnan(eta2) and abs(eta2 - current_eta2) > 0.005:
            logger.warning(f"  ⚠️  Computed η²={eta2:.4f} differs from stored={current_eta2:.4f}")

        # Update
        if ci_lower is not None and ci_upper is not None:
            method["eta_squared_ci_lower"] = round(ci_lower, 4)
            method["eta_squared_ci_upper"] = round(ci_upper, 4)
            logger.info(f"  ✅ {method_name}: η²={current_eta2:.4f} [{ci_lower:.4f}, {ci_upper:.4f}]")
            updated = True
        else:
            logger.warning(f"  ❌ {method_name}: Failed to compute CIs")

    if updated:
        # Update notes
        if "notes" not in data:
            data["notes"] = []

        # Replace warning note if present
        new_notes = []
        added_ci_note = False
        for note in data["notes"]:
            if "⚠️" in note and ("Bootstrap CIs required" in note or "Statistical claims deferred" in note):
                # Replace with confirmation
                if not added_ci_note:
                    new_notes.append(f"Bootstrap CIs computed: n={n_bootstrap} iterations")
                    added_ci_note = True
            else:
                new_notes.append(note)

        if not added_ci_note:
            new_notes.append(f"Bootstrap CIs computed: n={n_bootstrap} iterations")

        data["notes"] = new_notes

        # Backup and save
        backup_file = result_file.with_suffix(".json.backup")
        if backup_file.exists():
            backup_file.unlink()
        result_file.rename(backup_file)
        logger.info(f"  📦 Backup: {backup_file.name}")

        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("  💾 Saved updated file")

        return True

    return False


def main():
    """Main execution."""
    logger.info("=" * 80)
    logger.info("REGENERATE RESULTS WITH BOOTSTRAP CIs")
    logger.info("=" * 80)

    # Define regions
    regions = {
        "West Midlands": {
            "lads": [
                "Birmingham",
                "Coventry",
                "Dudley",
                "Sandwell",
                "Solihull",
                "Walsall",
                "Wolverhampton",
            ],
            "vti": VALIDATION_DIR / "mobility_surface_west_midlands.vti",
            "files": [
                "2025-12-16_west_midlands_male_female_comparison_b7b09831.json",
                "2025-12-16_west_midlands_ks4_comparison_763dc07a.json",
                "2025-12-16_west_midlands_tda_comparison_5957f1b3.json",
                "2025-12-16_west_midlands_tda_comparison_88425aa7.json",
            ],
        },
        "Greater Manchester": {
            "lads": [
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
            "vti": VALIDATION_DIR / "mobility_surface_greater_manchester.vti",
            "files": [
                "2025-12-16_greater_manchester_male_female_comparison_88e35f74.json",
                "2025-12-16_greater_manchester_ks4_comparison_69efca4e.json",
            ],
        },
        "Merseyside": {
            "lads": ["Liverpool", "Knowsley", "Sefton", "St. Helens", "Wirral"],
            "vti": VALIDATION_DIR / "mobility_surface_merseyside_150.vti",
            "files": [
                "2025-12-16_merseyside_150x150_comparison_d77a466d.json",
                "2025-12-16_merseyside_ks4_comparison_f6bacd68.json",
            ],
        },
        "Liverpool": {
            "lads": ["Liverpool"],
            "vti": VALIDATION_DIR / "mobility_surface_liverpool_150.vti",
            "files": [
                "2025-12-16_liverpool_150x150_comparison_abe234a7.json",
            ],
        },
    }

    success_count = 0
    total_count = 0

    for region_name, config in regions.items():
        logger.info(f"\n{'#' * 80}")
        logger.info(f"# {region_name.upper()}")
        logger.info(f"{'#' * 80}")

        # Load data
        try:
            gdf = load_lsoa_with_outcomes(config["lads"], region_name)
            gdf = load_ms_basins_from_vti(gdf, config["vti"])
            gdf = load_kmeans_clusters(gdf)
        except Exception as e:
            logger.error(f"Failed to load data for {region_name}: {e}")
            continue

        # Process files
        for filename in config["files"]:
            result_file = RESULTS_DIR / filename
            if not result_file.exists():
                logger.warning(f"File not found: {filename}")
                continue

            total_count += 1
            if update_result_file_with_cis(result_file, gdf, n_bootstrap=1000):
                success_count += 1

    logger.info(f"\n{'=' * 80}")
    logger.info("SUMMARY")
    logger.info(f"{'=' * 80}")
    logger.info(f"Updated: {success_count}/{total_count} files")

    if success_count > 0:
        logger.info("\n✅ Files updated with bootstrap CIs")
        logger.info("📦 Original files backed up with .backup extension")
        logger.info("\nNext steps:")
        logger.info("1. Review the updated files")
        logger.info("2. Run tests to verify")
        logger.info("3. Commit the changes")
        logger.info("4. Delete .backup files if satisfied")


if __name__ == "__main__":
    main()
