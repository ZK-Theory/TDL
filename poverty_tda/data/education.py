"""
UK Education data acquisition and processing.

This module provides utilities for downloading and processing education-related
data for mobility analysis, including POLAR4 (Participation of Local Areas)
higher education participation data.

Data Sources:
    POLAR4: Office for Students - Young Participation by Area
    https://www.officeforstudents.org.uk/data-and-analysis/young-participation-by-area/

    POLAR4 classifies areas by young HE participation rates into quintiles:
    - Quintile 1: Lowest participation (most disadvantaged)
    - Quintile 5: Highest participation (most advantaged)

    IMD Education Domain: From English Indices of Deprivation 2019
    - Measures lack of attainment and skills in local areas

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Office for Students POLAR4 postcode lookup data
# Contains POLAR4 and TUNDRA quintiles for all UK postcodes
_POLAR4_POSTCODE_ZIP_URL = (
    "https://blobofsproduks.blob.core.windows.net/files/POLAR2024/"
    "Postcode-lookup-dataset-September-2026.zip"
)

# Alternative: Direct CSV if available
_POLAR4_CSV_URL = (
    "https://blobofsproduks.blob.core.windows.net/files/POLAR2024/"
    "Postcode-lookup-dataset-September-2024.csv"
)

# Default data directory
DEFAULT_DATA_DIR = Path(__file__).parent / "raw" / "education"

# POLAR4 quintile descriptions
POLAR4_QUINTILE_DESCRIPTIONS = {
    1: "Lowest participation (most disadvantaged)",
    2: "Low participation",
    3: "Medium participation",
    4: "High participation",
    5: "Highest participation (most advantaged)",
}


def download_polar4_data(
    output_dir: Path | None = None,
    timeout: int = 300,
) -> Path:
    """
    Download POLAR4 postcode classification data from Office for Students.

    Downloads the postcode lookup dataset containing POLAR4 quintiles
    for all UK postcodes. This is a large file (~174MB zipped).

    Args:
        output_dir: Directory to save downloaded file. Defaults to
            poverty_tda/data/raw/education/
        timeout: Request timeout in seconds.

    Returns:
        Path to the downloaded file.

    Raises:
        requests.RequestException: If download fails.

    Note:
        The POLAR4 data is at postcode level, not LSOA level directly.
        Use aggregate_polar4_to_lsoa() to convert to LSOA-level.
    """
    if output_dir is None:
        output_dir = DEFAULT_DATA_DIR

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "polar4_postcode_lookup.zip"

    if output_path.exists():
        logger.info(f"POLAR4 data already exists at {output_path}")
        return output_path

    logger.info("Downloading POLAR4 postcode lookup data...")
    logger.info("Source: Office for Students")
    logger.info("Note: This is a large file (~174MB), download may take a while")

    try:
        response = requests.get(_POLAR4_POSTCODE_ZIP_URL, timeout=timeout, stream=True)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        logger.info(f"Downloaded POLAR4 data to {output_path}")
        return output_path

    except requests.RequestException as e:
        if output_path.exists():
            output_path.unlink()
        logger.error(f"Failed to download POLAR4 data: {e}")
        raise


def load_polar4_data(
    filepath: Path | None = None,
    download_if_missing: bool = False,
) -> pd.DataFrame:
    """
    Load POLAR4 postcode quintile data.

    Loads POLAR4 quintile classifications from the Office for Students
    postcode lookup dataset. Quintile 1 = lowest HE participation,
    Quintile 5 = highest participation.

    Args:
        filepath: Path to POLAR4 CSV file. If None, uses default location.
        download_if_missing: If True and file not found, download automatically.
            Note: Download is ~174MB and requires extraction.

    Returns:
        DataFrame with columns:
        - postcode: UK postcode
        - polar4_quintile: POLAR4 quintile (1-5)
        - tundra_quintile: TUNDRA quintile (1-5, newer measure)

    Raises:
        FileNotFoundError: If file not found and download_if_missing is False.

    Note:
        Due to the large file size, consider using get_education_from_imd()
        as a lightweight alternative that uses IMD education domain scores.
    """
    if filepath is None:
        default_csv = DEFAULT_DATA_DIR / "polar4_postcode_lookup.csv"
        default_zip = DEFAULT_DATA_DIR / "polar4_postcode_lookup.zip"

        if default_csv.exists():
            filepath = default_csv
        elif default_zip.exists():
            # Extract CSV from ZIP
            import zipfile

            with zipfile.ZipFile(default_zip, "r") as z:
                csv_files = [f for f in z.namelist() if f.endswith(".csv")]
                if csv_files:
                    z.extract(csv_files[0], DEFAULT_DATA_DIR)
                    filepath = DEFAULT_DATA_DIR / csv_files[0]
        elif download_if_missing:
            download_polar4_data()  # Download the file
            return load_polar4_data(filepath=None, download_if_missing=False)
        else:
            raise FileNotFoundError(
                f"POLAR4 data not found. Expected at {default_csv} or {default_zip}. "
                "Due to large file size (~174MB), manual download is recommended: "
                "https://www.officeforstudents.org.uk/data-and-analysis/"
                "young-participation-by-area/get-the-postcode-data/"
            )
    else:
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"POLAR4 file not found: {filepath}")

    logger.info(f"Loading POLAR4 data from {filepath}")

    # Load with appropriate encoding
    df = pd.read_csv(filepath, encoding="utf-8", low_memory=False)

    # Standardize column names (original columns vary by release)
    df.columns = df.columns.str.lower().str.strip()

    # Extract key columns
    polar4_col = None
    for col in df.columns:
        if "polar4" in col and "quintile" in col:
            polar4_col = col
            break

    if polar4_col:
        df = df.rename(columns={polar4_col: "polar4_quintile"})

    logger.info(f"Loaded {len(df)} postcode records")
    return df


def get_education_from_imd(
    imd_df: pd.DataFrame,
    score_column: str = "education_score",
    rank_column: str = "education_rank",
    decile_column: str = "education_decile",
) -> pd.DataFrame:
    """
    Extract education metrics from IMD data as lightweight alternative to POLAR4.

    The IMD Education, Skills and Training domain measures:
    - Children and young people sub-domain: attainment, absence, staying on
    - Adult skills sub-domain: qualifications, English language proficiency

    Args:
        imd_df: DataFrame with IMD data (from load_imd_data).
        score_column: Column name for education score.
        rank_column: Column name for education rank.
        decile_column: Column name for education decile.

    Returns:
        DataFrame with LSOA codes and education metrics:
        - lsoa_code: LSOA identifier
        - education_score: IMD education domain score
        - education_rank: Rank (1 = most deprived)
        - education_decile: Decile (1 = most deprived 10%)
        - education_normalized: Normalized score [0, 1] where 1 = best outcomes

    Example:
        >>> from poverty_tda.data.opportunity_atlas import load_imd_data
        >>> imd_df = load_imd_data()
        >>> education = get_education_from_imd(imd_df)
    """
    required_cols = ["lsoa_code"]
    optional_cols = [score_column, rank_column, decile_column]

    if "lsoa_code" not in imd_df.columns:
        raise ValueError("IMD DataFrame must contain 'lsoa_code' column")

    available_cols = [c for c in optional_cols if c in imd_df.columns]
    if not available_cols:
        raise ValueError(f"IMD DataFrame must contain at least one of: {optional_cols}")

    result = imd_df[required_cols + available_cols].copy()

    # Add normalized education score (0 = worst, 1 = best)
    if rank_column in result.columns:
        max_rank = result[rank_column].max()
        # Higher rank = better outcomes, normalize to [0, 1]
        result["education_normalized"] = result[rank_column] / max_rank
    elif score_column in result.columns:
        # Lower score = better outcomes for IMD, so invert
        max_score = result[score_column].max()
        min_score = result[score_column].min()
        result["education_normalized"] = 1 - (
            (result[score_column] - min_score) / (max_score - min_score)
        )

    return result


def compute_educational_upward(
    imd_df: pd.DataFrame,
    polar_df: pd.DataFrame | None = None,
    imd_weight: float = 0.7,
    polar_weight: float = 0.3,
) -> pd.Series:
    """
    Compute educational upward mobility metric.

    Combines IMD education domain scores with POLAR4 quintiles (if available)
    to create a composite educational mobility indicator.

    Higher values indicate better educational outcomes relative to local
    deprivation levels, suggesting upward mobility potential.

    Args:
        imd_df: DataFrame with IMD data including education domain.
        polar_df: Optional DataFrame with POLAR4 quintiles by postcode/LSOA.
            If None, uses only IMD education domain.
        imd_weight: Weight for IMD education component (default 0.7).
        polar_weight: Weight for POLAR4 component (default 0.3).
            Note: If polar_df is None, all weight goes to IMD.

    Returns:
        Series with educational upward mobility scores per LSOA.
        Values are normalized to [0, 1] where 1 = highest upward mobility.

    Formula:
        If POLAR4 available:
            edu_upward = imd_weight * edu_normalized + polar_weight * polar_normalized
        If POLAR4 not available:
            edu_upward = edu_normalized (from IMD education domain)

    Example:
        >>> imd_df = load_imd_data()
        >>> edu_upward = compute_educational_upward(imd_df)
        >>> print(edu_upward.describe())
    """
    # Get education metrics from IMD
    education = get_education_from_imd(imd_df)

    if polar_df is None:
        # Use only IMD education domain
        logger.info("Computing educational upward mobility from IMD education domain")
        return education["education_normalized"].rename("educational_upward")

    # Combine IMD with POLAR4
    logger.info("Computing educational upward mobility from IMD + POLAR4")

    # POLAR4 quintile: 5 = highest participation = best outcomes
    if "polar4_quintile" not in polar_df.columns:
        logger.warning("POLAR4 quintile column not found, using IMD only")
        return education["education_normalized"].rename("educational_upward")

    # Merge datasets (requires common key - postcode or LSOA)
    # This is simplified; real implementation would need postcode-LSOA mapping
    # For now, if we can't merge, fall back to IMD only
    if "lsoa_code" in polar_df.columns:
        merged = education.merge(
            polar_df[["lsoa_code", "polar4_quintile"]],
            on="lsoa_code",
            how="left",
        )
        merged["polar_normalized"] = (merged["polar4_quintile"] - 1) / 4

        # Compute weighted average where POLAR4 is available
        has_polar = merged["polar_normalized"].notna()
        edu_upward = merged["education_normalized"].copy()
        edu_upward[has_polar] = (
            imd_weight * merged.loc[has_polar, "education_normalized"]
            + polar_weight * merged.loc[has_polar, "polar_normalized"]
        )
        return edu_upward.rename("educational_upward")

    # Fallback to IMD only
    return education["education_normalized"].rename("educational_upward")


def load_ks4_outcomes(
    filepath: Path | None = None,
    download_if_missing: bool = False,
) -> pd.DataFrame:
    """
    Load Key Stage 4 (GCSE) outcomes data.

    Note: LSOA-level KS4 data is not publicly available. This function
    provides a placeholder that falls back to IMD education domain scores.

    For school-level KS4 data, see:
    https://www.gov.uk/government/collections/statistics-gcses-key-stage-4

    Args:
        filepath: Path to KS4 data file (if available).
        download_if_missing: If True, would download data (not implemented).

    Returns:
        DataFrame with KS4 outcomes. Currently returns empty DataFrame
        with expected schema as KS4 LSOA-level data is not available.

    Note:
        Use get_education_from_imd() instead, which uses the IMD
        Education domain that incorporates KS4-level attainment data.
    """
    logger.warning(
        "LSOA-level KS4 data not publicly available. "
        "Use get_education_from_imd() for education metrics from IMD."
    )

    if filepath is not None and Path(filepath).exists():
        return pd.read_csv(filepath)

    # Return empty DataFrame with expected schema
    return pd.DataFrame(
        columns=[
            "lsoa_code",
            "ks4_attainment_8",
            "ks4_progress_8",
            "ks4_english_maths",
        ]
    )
