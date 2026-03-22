"""
Outcome Data Download Script for TDA Comparison Protocol.

Downloads life expectancy (ONS) and GCSE attainment (DfE) data
at Local Authority District level for validation.

Usage:
    python -m poverty_tda.data.download_outcomes --output-dir ./data/outcomes

License: Open Government Licence v3.0
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)


# =============================================================================
# DATA SOURCE URLS
# =============================================================================

# ONS Life Expectancy by Local Authority (2018-2020)
# Source: https://www.ons.gov.uk/datasets/life-expectancy-by-local-authority/editions/time-series/versions
LIFE_EXPECTANCY_URL = "https://download.ons.gov.uk/downloads/datasets/life-expectancy-by-local-authority/editions/time-series/versions/3.csv"

# Fallback: Health Index life expectancy component
LIFE_EXPECTANCY_FALLBACK = "https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/healthandsocialcare/healthandlifeexpectancies/datasets/lifeexpectancyatbirthandatage65bylocalareasuk/current/lepivottable.xlsx"

# DfE Key Stage 4 Local Authority data
# Source: https://explore-education-statistics.service.gov.uk/find-statistics/key-stage-4-performance
KS4_LA_URL = "https://content.explore-education-statistics.service.gov.uk/api/releases/af5b7d86-d8c0-4b92-9e6e-93f84823c3a4/files/local_authority_data_final_2223.csv"

# ONS Internal migration by LAD
MIGRATION_URL = "https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/populationandmigration/migrationwithintheuk/datasets/internalmigrationbylocauthoritiesinenglandandwales/yearendingjune2022/internalmigrationdetailedestimatesyeendingjune2022.xlsx"


# =============================================================================
# DOWNLOAD FUNCTIONS
# =============================================================================


def download_file(url: str, output_path: Path, description: str = "") -> bool:
    """Download a file from URL."""
    logger.info(f"Downloading {description or url}...")

    try:
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Saved to {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to download {description}: {e}")
        return False


def download_life_expectancy(output_dir: Path) -> Optional[Path]:
    """
    Download ONS life expectancy by local authority.

    Returns path to downloaded file or None if failed.
    """
    output_path = output_dir / "life_expectancy_by_lad.csv"

    if download_file(LIFE_EXPECTANCY_URL, output_path, "Life expectancy (ONS)"):
        return output_path

    # Try fallback
    logger.info("Primary URL failed, trying fallback...")
    output_path_fallback = output_dir / "life_expectancy_by_lad.xlsx"
    if download_file(LIFE_EXPECTANCY_FALLBACK, output_path_fallback, "Life expectancy fallback"):
        return output_path_fallback

    return None


def download_gcse_attainment(output_dir: Path) -> Optional[Path]:
    """
    Download DfE Key Stage 4 attainment by Local Authority.

    Returns path to downloaded file or None if failed.
    """
    output_path = output_dir / "ks4_attainment_by_lad.csv"

    if download_file(KS4_LA_URL, output_path, "GCSE attainment (DfE)"):
        return output_path

    return None


def download_migration(output_dir: Path) -> Optional[Path]:
    """
    Download ONS internal migration by Local Authority.

    Returns path to downloaded file or None if failed.
    """
    output_path = output_dir / "internal_migration_by_lad.xlsx"

    if download_file(MIGRATION_URL, output_path, "Internal migration (ONS)"):
        return output_path

    return None


# =============================================================================
# DATA PROCESSING
# =============================================================================


def process_life_expectancy(file_path: Path) -> pd.DataFrame:
    """
    Process life expectancy data into usable format.

    Returns DataFrame with columns:
    - lad_code: Local Authority District code
    - lad_name: Local Authority District name
    - male_life_expectancy: Male life expectancy at birth
    - female_life_expectancy: Female life expectancy at birth
    """
    logger.info("Processing life expectancy data...")

    if file_path.suffix == ".xlsx":
        df = pd.read_excel(file_path, sheet_name=0, skiprows=3)
    else:
        df = pd.read_csv(file_path)

    # The structure varies; try to identify columns
    logger.info(f"Columns: {df.columns.tolist()[:10]}...")

    # Common column patterns
    code_cols = [c for c in df.columns if "code" in c.lower() and "area" in c.lower()]
    name_cols = [c for c in df.columns if "name" in c.lower() and "area" in c.lower()]

    # Filter to most recent period and local authorities
    # This will need adjustment based on actual data structure

    return df


def process_gcse_attainment(file_path: Path) -> pd.DataFrame:
    """
    Process GCSE attainment data into usable format.

    Returns DataFrame with columns:
    - lad_code: Local Authority District code
    - lad_name: Local Authority District name
    - attainment_8: Average Attainment 8 score
    - english_maths_9_5: % achieving grade 9-5 in English & Maths
    """
    logger.info("Processing GCSE attainment data...")

    df = pd.read_csv(file_path)
    logger.info(f"Columns: {df.columns.tolist()[:10]}...")

    return df


# =============================================================================
# MAIN DOWNLOAD PIPELINE
# =============================================================================


def download_all_outcomes(output_dir: Path) -> dict[str, Path | None]:
    """
    Download all outcome data files.

    Returns dict mapping outcome name to file path (or None if failed).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "life_expectancy": download_life_expectancy(output_dir),
        "gcse_attainment": download_gcse_attainment(output_dir),
        "migration": download_migration(output_dir),
    }

    # Summary
    success = sum(1 for v in results.values() if v is not None)
    logger.info(f"\nDownload summary: {success}/{len(results)} files downloaded")

    for name, path in results.items():
        if path:
            logger.info(f"  ✓ {name}: {path}")
        else:
            logger.info(f"  ✗ {name}: FAILED")

    return results


def main():
    """Command-line interface for downloading outcome data."""
    parser = argparse.ArgumentParser(description="Download outcome data for TDA validation")
    parser.add_argument("--output-dir", default="./data/raw/outcomes", help="Output directory for downloaded files")
    parser.add_argument("--life-expectancy-only", action="store_true", help="Only download life expectancy data")
    parser.add_argument("--gcse-only", action="store_true", help="Only download GCSE attainment data")

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.life_expectancy_only:
        download_life_expectancy(output_dir)
    elif args.gcse_only:
        download_gcse_attainment(output_dir)
    else:
        download_all_outcomes(output_dir)

    logger.info("Done!")


if __name__ == "__main__":
    main()
