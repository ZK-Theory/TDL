"""
Recompute bootstrap confidence intervals for validation result files that have null CIs.

This script identifies result JSON files with null eta_squared_ci_lower/upper values
and recomputes them using the original data.
"""

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"
PROJECT_ROOT = Path(__file__).parent.parent.parent


def has_null_cis(result_file: Path) -> bool:
    """Check if a result file has null confidence intervals."""
    try:
        with open(result_file) as f:
            data = json.load(f)

        for method in data.get("methods", []):
            if method.get("eta_squared_ci_lower") is None:
                return True
        return False
    except Exception as e:
        logger.error(f"Error reading {result_file}: {e}")
        return False


def identify_files_needing_cis():
    """Identify all result files that need CI recomputation."""
    files_needing_cis = []

    for json_file in RESULTS_DIR.glob("2025-12-16_*.json"):
        if has_null_cis(json_file):
            files_needing_cis.append(json_file)
            logger.info(f"Found file with null CIs: {json_file.name}")

    return files_needing_cis


def recompute_cis_for_file(result_file: Path, n_bootstrap: int = 1000) -> bool:
    """
    Recompute CIs for a result file.

    This requires loading the original data and re-running the computation.
    Since we don't have a perfect way to reconstruct the exact analysis,
    we'll provide a template that needs to be filled in.

    Returns True if successful, False otherwise.
    """
    logger.info(f"Processing {result_file.name}...")

    try:
        with open(result_file) as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {result_file}: {e}")
        return False

    # Extract metadata
    region = data["region"]
    outcome_var = data["outcome_variable"]

    logger.info(f"  Region: {region}")
    logger.info(f"  Outcome: {outcome_var}")
    logger.info(f"  Methods: {len(data['methods'])}")

    # Check input files
    input_files = data.get("input_files", [])
    if not input_files:
        logger.warning("  No input files recorded - cannot automatically recompute")
        return False

    logger.info(f"  Input files: {len(input_files)}")
    for f in input_files:
        logger.info(f"    - {f}")

    # This is where we would need to:
    # 1. Load the data files
    # 2. Reconstruct the GeoDataFrame
    # 3. Re-run record_comparison_result with n_bootstrap > 0

    logger.warning("  ⚠️  Automatic recomputation not implemented - needs manual intervention")
    return False


def generate_recomputation_guide():
    """Generate a guide for manually recomputing CIs."""
    files = identify_files_needing_cis()

    if not files:
        logger.info("✅ All result files have bootstrap CIs computed!")
        return

    logger.info(f"\n{'=' * 80}")
    logger.info(f"Found {len(files)} files with missing bootstrap CIs:")
    logger.info(f"{'=' * 80}\n")

    for f in files:
        with open(f) as fh:
            data = json.load(fh)

        print(f"📄 {f.name}")
        print(f"   Region: {data['region']}")
        print(f"   Outcome: {data['outcome_variable']}")
        print(f"   Methods: {[m['name'] for m in data['methods']]}")
        print(f"   Timestamp: {data['timestamp']}")

        # Group similar files
        if "male_female" in f.name:
            print("   Type: Male/Female comparison")
        elif "ks4" in f.name:
            print("   Type: KS4 (GCSE) comparison")
        elif "150x150" in f.name or "tda_comparison" in f.name:
            print("   Type: Resolution/TDA comparison")
        print()

    print(f"{'=' * 80}")
    print("RECOMPUTATION PLAN:")
    print(f"{'=' * 80}\n")

    # Group files by type for batch recomputation
    male_female_files = [f for f in files if "male_female" in f.name]
    ks4_files = [f for f in files if "ks4" in f.name]
    resolution_files = [f for f in files if "150x150" in f.name]
    other_files = [f for f in files if f not in male_female_files + ks4_files + resolution_files]

    if male_female_files:
        print("1️⃣  MALE/FEMALE COMPARISONS:")
        print(f"   Files: {len(male_female_files)}")
        for f in male_female_files:
            print(f"   - {f.name}")
        print()

    if ks4_files:
        print("2️⃣  KS4 (GCSE) COMPARISONS:")
        print(f"   Files: {len(ks4_files)}")
        for f in ks4_files:
            print(f"   - {f.name}")
        print()

    if resolution_files:
        print("3️⃣  RESOLUTION COMPARISONS:")
        print(f"   Files: {len(resolution_files)}")
        for f in resolution_files:
            print(f"   - {f.name}")
        print()

    if other_files:
        print("4️⃣  OTHER COMPARISONS:")
        print(f"   Files: {len(other_files)}")
        for f in other_files:
            print(f"   - {f.name}")
        print()

    print(f"{'=' * 80}")
    print("RECOMMENDED APPROACH:")
    print(f"{'=' * 80}\n")
    print("Since these files were likely generated from interactive Python sessions,")
    print("you have two options:\n")
    print("Option A: Create a new script that loads the original data and reruns")
    print("          record_comparison_result() with n_bootstrap=1000\n")
    print("Option B: Use the existing data files and patch the JSON files directly")
    print("          by computing bootstrap CIs from the stored data\n")
    print("Recommendation: Option A is cleaner and ensures reproducibility\n")


if __name__ == "__main__":
    print("Bootstrap CI Recomputation Tool")
    print("=" * 80)
    print()

    generate_recomputation_guide()
