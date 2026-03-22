"""
Patch bootstrap CIs into existing result files by loading the original data.

This script loads the data files referenced in (or inferred for) result JSONs
and recomputes bootstrap confidence intervals for eta-squared values.
"""

import json
import logging
from pathlib import Path
from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"
PROJECT_ROOT = Path(__file__).parent.parent.parent
VALIDATION_DIR = Path(__file__).parent


def load_region_data(region: str) -> Optional[gpd.GeoDataFrame]:
    """Load the GeoDataFrame with MS basins and outcomes for a region."""

    # Try to find the corresponding VTI file and processed data
    if "West Midlands" in region:
        basin_csv = VALIDATION_DIR / "results" / "west_midlands_with_outcomes.csv"
    elif "Greater Manchester" in region:
        basin_csv = VALIDATION_DIR / "results" / "greater_manchester_with_outcomes.csv"
    elif "Merseyside" in region or "Liverpool" in region:
        basin_csv = VALIDATION_DIR / "results" / "merseyside_with_outcomes.csv"
    else:
        logger.warning(f"Unknown region: {region}")
        return None

    if not basin_csv.exists():
        logger.warning(f"Basin CSV not found: {basin_csv}")
        return None

    # Load data
    try:
        gdf = pd.read_csv(basin_csv)
        logger.info(f"Loaded {len(gdf)} rows from {basin_csv.name}")
        return gdf
    except Exception as e:
        logger.error(f"Failed to load {basin_csv}: {e}")
        return None


def compute_eta_squared_with_bootstrap(
    labels: np.ndarray,
    values: np.ndarray,
    n_bootstrap: int = 1000,
    random_state: int = 42,
) -> tuple[float, float, float]:
    """
    Compute eta-squared with bootstrap confidence intervals.

    Returns:
        (eta_squared, ci_lower, ci_upper)
    """

    def compute_eta_squared(lab, val):
        # Remove NaN
        mask = ~(np.isnan(lab) | np.isnan(val))
        lab = lab[mask]
        val = val[mask]

        if len(lab) < 2:
            return np.nan

        unique_labels = np.unique(lab)
        if len(unique_labels) < 2:
            return np.nan

        grand_mean = np.mean(val)
        ss_total = np.sum((val - grand_mean) ** 2)

        if ss_total == 0:
            return np.nan

        ss_between = 0
        for label in unique_labels:
            group_values = val[lab == label]
            if len(group_values) > 0:
                group_mean = np.mean(group_values)
                ss_between += len(group_values) * (group_mean - grand_mean) ** 2

        return ss_between / ss_total if ss_total > 0 else 0.0

    # Point estimate
    eta2 = compute_eta_squared(labels, values)

    # Bootstrap
    rng = np.random.default_rng(random_state)
    boot_stats = []

    n_samples = len(labels)
    for _ in range(n_bootstrap):
        indices = rng.integers(0, n_samples, n_samples)
        boot_eta = compute_eta_squared(labels[indices], values[indices])
        if not np.isnan(boot_eta):
            boot_stats.append(boot_eta)

    if len(boot_stats) > 0:
        ci_lower = np.percentile(boot_stats, 2.5)
        ci_upper = np.percentile(boot_stats, 97.5)
    else:
        ci_lower = None
        ci_upper = None

    return eta2, ci_lower, ci_upper


def patch_file_cis(result_file: Path, gdf: pd.DataFrame, n_bootstrap: int = 1000) -> bool:
    """
    Patch bootstrap CIs into a result file.

    Args:
        result_file: Path to the JSON result file
        gdf: GeoDataFrame with the data
        n_bootstrap: Number of bootstrap iterations

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"\n{'=' * 80}")
    logger.info(f"Patching: {result_file.name}")
    logger.info(f"{'=' * 80}")

    # Load existing result
    try:
        with open(result_file, encoding="utf-8") as f:
            data = json.load(f)
    except UnicodeDecodeError:
        try:
            with open(result_file, encoding="latin-1") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {result_file}: {e}")
            return False
    except Exception as e:
        logger.error(f"Failed to load {result_file}: {e}")
        return False

    outcome_var = data["outcome_variable"]
    methods = data["methods"]

    logger.info(f"Outcome variable: {outcome_var}")
    logger.info(f"Methods: {len(methods)}")

    # Check if we need to process multiple outcomes (e.g., male and female)
    is_multi_outcome = "male and female" in outcome_var.lower() or " and " in outcome_var.lower()

    updated = False

    for method in methods:
        method_name = method["name"]
        column = method["column"]
        current_eta2 = method["eta_squared"]

        # Skip if CIs already exist
        if method.get("eta_squared_ci_lower") is not None:
            logger.info(f"  ✓ {method_name}: CIs already exist, skipping")
            continue

        # Determine outcome column
        if is_multi_outcome:
            if "Male" in method_name:
                outcome_col = "life_expectancy_male"
            elif "Female" in method_name:
                outcome_col = "life_expectancy_female"
            elif "LE" in method_name:
                outcome_col = "life_expectancy_male"
            elif "KS4" in method_name:
                outcome_col = "attainment8_average"
            else:
                logger.warning(f"  ⚠️  Could not determine outcome for {method_name}")
                continue
        else:
            # Single outcome - try to infer from outcome_variable
            if "life_expectancy" in outcome_var.lower():
                if "male" in outcome_var.lower() and "female" not in outcome_var.lower():
                    outcome_col = "life_expectancy_male"
                elif "female" in outcome_var.lower() and "male" not in outcome_var.lower():
                    outcome_col = "life_expectancy_female"
                else:
                    outcome_col = "life_expectancy_male"  # default
            elif "attainment" in outcome_var.lower() or "ks4" in outcome_var.lower():
                outcome_col = "attainment8_average"
            else:
                logger.warning(f"  ⚠️  Unknown outcome type: {outcome_var}")
                continue

        # Check if columns exist
        if column not in gdf.columns:
            logger.warning(f"  ⚠️  Column {column} not found in data")
            continue

        if outcome_col not in gdf.columns:
            logger.warning(f"  ⚠️  Outcome column {outcome_col} not found in data")
            continue

        # Extract data
        labels = gdf[column].values
        values = gdf[outcome_col].values

        # Compute bootstrap CIs
        logger.info(f"  Computing CIs for {method_name} ({column} vs {outcome_col})...")
        eta2, ci_lower, ci_upper = compute_eta_squared_with_bootstrap(labels, values, n_bootstrap=n_bootstrap)

        # Verify eta2 matches
        if not np.isnan(eta2) and abs(eta2 - current_eta2) > 0.001:
            logger.warning(f"  ⚠️  Computed η² ({eta2:.4f}) differs from stored value ({current_eta2:.4f})")

        # Update method
        if ci_lower is not None and ci_upper is not None:
            method["eta_squared_ci_lower"] = round(ci_lower, 4)
            method["eta_squared_ci_upper"] = round(ci_upper, 4)
            logger.info(f"  ✅ {method_name}: η² = {current_eta2:.4f} [{ci_lower:.4f}, {ci_upper:.4f}]")
            updated = True
        else:
            logger.warning(f"  ❌ {method_name}: Failed to compute CIs")

    if updated:
        # Add note about CI computation
        if "notes" not in data:
            data["notes"] = []

        ci_note = f"Bootstrap CIs added post-hoc: n={n_bootstrap} iterations (2025-12-16)"
        if ci_note not in data["notes"]:
            data["notes"].append(ci_note)

        # Save updated file
        backup_file = result_file.with_suffix(".json.bak")
        result_file.rename(backup_file)
        logger.info(f"  📦 Backup saved: {backup_file.name}")

        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info("  ✅ Updated file saved")

        # Also update the markdown file if it exists
        md_file = result_file.with_suffix(".md")
        if md_file.exists():
            update_markdown_file(md_file, data)
            logger.info("  ✅ Updated markdown file")

        return True
    else:
        logger.info("  ℹ️  No updates needed")
        return False


def update_markdown_file(md_file: Path, data: dict):
    """Update the markdown file to reflect new CIs."""
    # For now, just add a note - full regeneration would require the results_framework
    with open(md_file, "a", encoding="utf-8") as f:
        f.write(
            "\n\n---\n\n**Note**: Bootstrap confidence intervals were recomputed on 2025-12-16 with n=1000 iterations.\n"
        )


def main():
    """Main execution."""
    logger.info("Bootstrap CI Patcher")
    logger.info("=" * 80)

    # Files to patch (identified from earlier analysis)
    files_to_patch = [
        # Male/Female comparisons
        "2025-12-16_west_midlands_male_female_comparison_b7b09831.json",
        "2025-12-16_greater_manchester_male_female_comparison_88e35f74.json",
        # KS4 comparisons
        "2025-12-16_west_midlands_ks4_comparison_763dc07a.json",
        "2025-12-16_greater_manchester_ks4_comparison_69efca4e.json",
        "2025-12-16_merseyside_ks4_comparison_f6bacd68.json",
        # Resolution/TDA comparisons
        "2025-12-16_liverpool_150x150_comparison_abe234a7.json",
        "2025-12-16_merseyside_150x150_comparison_d77a466d.json",
        "2025-12-16_west_midlands_tda_comparison_5957f1b3.json",
        "2025-12-16_west_midlands_tda_comparison_88425aa7.json",
    ]

    # Group by region
    regions = {
        "West Midlands": [],
        "Greater Manchester": [],
        "Merseyside": [],
        "Liverpool": [],
    }

    for filename in files_to_patch:
        if "west_midlands" in filename:
            regions["West Midlands"].append(filename)
        elif "greater_manchester" in filename:
            regions["Greater Manchester"].append(filename)
        elif "merseyside" in filename:
            regions["Merseyside"].append(filename)
        elif "liverpool" in filename:
            regions["Liverpool"].append(filename)

    success_count = 0
    total_count = 0

    for region, filenames in regions.items():
        if not filenames:
            continue

        logger.info(f"\n{'#' * 80}")
        logger.info(f"# PROCESSING {region.upper()}")
        logger.info(f"{'#' * 80}")

        # Load region data
        gdf = load_region_data(region)

        if gdf is None:
            logger.warning(f"Could not load data for {region}, skipping {len(filenames)} files")
            continue

        # Process each file
        for filename in filenames:
            result_file = RESULTS_DIR / filename
            if not result_file.exists():
                logger.warning(f"File not found: {filename}")
                continue

            total_count += 1
            if patch_file_cis(result_file, gdf, n_bootstrap=1000):
                success_count += 1

    logger.info(f"\n{'=' * 80}")
    logger.info("SUMMARY")
    logger.info(f"{'=' * 80}")
    logger.info(f"Successfully patched: {success_count}/{total_count} files")

    if success_count > 0:
        logger.info("\n✅ Files have been updated with bootstrap CIs")
        logger.info("⚠️  Original files backed up with .bak extension")
        logger.info("\nNext steps:")
        logger.info("1. Review the updated files")
        logger.info("2. If satisfied, delete the .bak files")
        logger.info("3. Commit the updated files to git")


if __name__ == "__main__":
    main()
