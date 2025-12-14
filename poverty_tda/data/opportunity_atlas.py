"""
UK Index of Multiple Deprivation (IMD) data acquisition and processing.

This module provides utilities for downloading and processing IMD 2019 data
from the UK Government's official statistics portal.

Data Sources:
    English IMD 2019: https://www.gov.uk/government/statistics/english-indices-of-deprivation-2019
    Welsh IMD 2019: https://statswales.gov.wales/Catalogue/Community-Safety-and-Social-Inclusion/Welsh-Index-of-Multiple-Deprivation

IMD Domains (England):
    1. Income Deprivation - Proportion on low income
    2. Employment Deprivation - Involuntary exclusion from labour market
    3. Education, Skills and Training - Lack of attainment and skills
    4. Health Deprivation and Disability - Risk of premature death/quality of life
    5. Crime - Risk of personal and material victimisation
    6. Barriers to Housing and Services - Physical/financial accessibility
    7. Living Environment - Quality of indoor and outdoor environment

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

import geopandas as gpd
import pandas as pd
import requests

logger = logging.getLogger(__name__)

# GOV.UK direct download URLs for English IMD 2019
# File 7 contains all ranks, deciles, scores, and population denominators
_ENGLAND_IMD_2019_CSV_URL = (
    "https://assets.publishing.service.gov.uk/media/5dc407b440f0b6379a7acc8d/"
    "File_7_-_All_IoD2019_Scores__Ranks__Deciles_and_Population_Denominators_3.csv"
)

# File 5 contains just scores (alternative, smaller file)
_ENGLAND_IMD_2019_SCORES_URL = (
    "https://assets.publishing.service.gov.uk/media/5d8b3b51ed915d036a455aa6/"
    "File_5_-_IoD2019_Scores.xlsx"
)

# Welsh IMD 2019 (StatsWales Open Data)
# Note: Welsh IMD uses different methodology and is not directly comparable
_WALES_IMD_2019_URL = "https://statswales.gov.wales/Download/File?fileId=719"

# Expected counts for validation
EXPECTED_ENGLAND_LSOA_COUNT = 32844  # England only
EXPECTED_WALES_LSOA_COUNT = 1909  # Wales LSOAs in WIMD

# Default data directory
DEFAULT_DATA_DIR = Path(__file__).parent / "raw" / "imd"

# Column name mappings for standardization
# English IMD 2019 column names (from File 7)
# Note: Long lines unavoidable as they match exact column names from gov.uk data
_ENGLAND_COLUMN_MAP = {
    "LSOA code (2011)": "lsoa_code",
    "LSOA name (2011)": "lsoa_name",
    "Local Authority District code (2019)": "lad_code",
    "Local Authority District name (2019)": "lad_name",
    # Overall IMD
    "Index of Multiple Deprivation (IMD) Score": "imd_score",
    "Index of Multiple Deprivation (IMD) Rank (where 1 is most deprived)": "imd_rank",  # noqa: E501
    "Index of Multiple Deprivation (IMD) Decile (where 1 is most deprived 10% of LSOAs)": "imd_decile",  # noqa: E501
    # Income domain
    "Income Score (rate)": "income_score",
    "Income Rank (where 1 is most deprived)": "income_rank",
    "Income Decile (where 1 is most deprived 10% of LSOAs)": "income_decile",
    # Employment domain
    "Employment Score (rate)": "employment_score",
    "Employment Rank (where 1 is most deprived)": "employment_rank",
    "Employment Decile (where 1 is most deprived 10% of LSOAs)": "employment_decile",  # noqa: E501
    # Education domain
    "Education, Skills and Training Score": "education_score",
    "Education, Skills and Training Rank (where 1 is most deprived)": "education_rank",  # noqa: E501
    "Education, Skills and Training Decile (where 1 is most deprived 10% of LSOAs)": "education_decile",  # noqa: E501
    # Health domain
    "Health Deprivation and Disability Score": "health_score",
    "Health Deprivation and Disability Rank (where 1 is most deprived)": "health_rank",  # noqa: E501
    "Health Deprivation and Disability Decile (where 1 is most deprived 10% of LSOAs)": "health_decile",  # noqa: E501
    # Crime domain
    "Crime Score": "crime_score",
    "Crime Rank (where 1 is most deprived)": "crime_rank",
    "Crime Decile (where 1 is most deprived 10% of LSOAs)": "crime_decile",
    # Barriers to Housing and Services domain
    "Barriers to Housing and Services Score": "housing_score",
    "Barriers to Housing and Services Rank (where 1 is most deprived)": "housing_rank",  # noqa: E501
    "Barriers to Housing and Services Decile (where 1 is most deprived 10% of LSOAs)": "housing_decile",  # noqa: E501
    # Living Environment domain
    "Living Environment Score": "environment_score",
    "Living Environment Rank (where 1 is most deprived)": "environment_rank",
    "Living Environment Decile (where 1 is most deprived 10% of LSOAs)": "environment_decile",  # noqa: E501
    # Supplementary indices
    "Income Deprivation Affecting Children Index (IDACI) Score (rate)": "idaci_score",  # noqa: E501
    "Income Deprivation Affecting Children Index (IDACI) Rank (where 1 is most deprived)": "idaci_rank",  # noqa: E501
    "Income Deprivation Affecting Children Index (IDACI) Decile (where 1 is most deprived 10% of LSOAs)": "idaci_decile",  # noqa: E501
    "Income Deprivation Affecting Older People (IDAOPI) Score (rate)": "idaopi_score",  # noqa: E501
    "Income Deprivation Affecting Older People (IDAOPI) Rank (where 1 is most deprived)": "idaopi_rank",  # noqa: E501
    "Income Deprivation Affecting Older People (IDAOPI) Decile (where 1 is most deprived 10% of LSOAs)": "idaopi_decile",  # noqa: E501
    # Population
    "Total population: mid 2015 (excluding prisoners)": "population",
}

# Known deprivation patterns for validation
# Based on IMD 2019 official statistics
KNOWN_MOST_DEPRIVED_LADS = [
    "Blackpool",
    "Knowsley",
    "Kingston upon Hull, City of",
    "Liverpool",
    "Middlesbrough",
]

KNOWN_LEAST_DEPRIVED_LADS = [
    "Hart",
    "Wokingham",
    "Surrey Heath",
    "Elmbridge",
    "Waverley",
]

# Jaywick (Tendring) is famously the most deprived LSOA
# E01021988 "Tendring 018A" is the #1 ranked most deprived LSOA in England (IMD 2019)
JAYWICK_LSOA_CODE = "E01021988"


def download_imd_data(
    output_dir: Path | None = None,
    country: Literal["england", "wales"] = "england",
    timeout: int = 120,
) -> Path:
    """
    Download IMD 2019 data from official government sources.

    Downloads the Index of Multiple Deprivation data for the specified country.
    For England, downloads File 7 which contains all scores, ranks, and deciles.

    Args:
        output_dir: Directory to save downloaded file. Defaults to
            poverty_tda/data/raw/imd/
        country: Country to download data for. Options:
            - "england": English IMD 2019 (recommended, ~32,844 LSOAs)
            - "wales": Welsh IMD 2019 (~1,909 LSOAs)
        timeout: Request timeout in seconds.

    Returns:
        Path to the downloaded CSV file.

    Raises:
        ValueError: If unsupported country is specified.
        requests.RequestException: If download fails.

    Example:
        >>> filepath = download_imd_data()
        >>> print(filepath)
        PosixPath('.../imd/england_imd_2019.csv')
    """
    if output_dir is None:
        output_dir = DEFAULT_DATA_DIR

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if country == "england":
        url = _ENGLAND_IMD_2019_CSV_URL
        filename = "england_imd_2019.csv"
    elif country == "wales":
        url = _WALES_IMD_2019_URL
        filename = "wales_imd_2019.csv"
    else:
        raise ValueError(
            f"Country '{country}' not supported. Use 'england' or 'wales'."
        )

    output_path = output_dir / filename

    # Skip if already downloaded
    if output_path.exists():
        logger.info(f"IMD data already exists at {output_path}")
        return output_path

    logger.info(f"Downloading {country.title()} IMD 2019 data...")
    logger.info("Source: GOV.UK Official Statistics")

    try:
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        logger.info(f"Downloaded IMD data to {output_path}")
        return output_path

    except requests.RequestException as e:
        if output_path.exists():
            output_path.unlink()
        logger.error(f"Failed to download IMD data: {e}")
        raise


def load_imd_data(
    filepath: Path | None = None,
    country: Literal["england", "wales"] = "england",
    download_if_missing: bool = True,
    standardize_columns: bool = True,
) -> pd.DataFrame:
    """
    Load IMD data into a pandas DataFrame.

    Loads IMD 2019 data from CSV file. If no filepath is provided and
    download_if_missing is True, downloads the data first.

    Args:
        filepath: Path to IMD CSV file. If None, uses default location.
        country: Country for data (used if downloading). Options: "england", "wales"
        download_if_missing: If True and file not found, download automatically.
        standardize_columns: If True, rename columns to standardized names.

    Returns:
        DataFrame with IMD data containing columns for LSOA codes, names,
        overall IMD score/rank/decile, and domain-specific scores/ranks.

    Raises:
        FileNotFoundError: If file not found and download_if_missing is False.

    Example:
        >>> df = load_imd_data()
        >>> print(df.columns.tolist()[:5])
        ['lsoa_code', 'lsoa_name', 'lad_code', 'lad_name', 'imd_score']
    """
    if filepath is None:
        default_filename = f"{country}_imd_2019.csv"
        default_path = DEFAULT_DATA_DIR / default_filename

        if not default_path.exists():
            if download_if_missing:
                filepath = download_imd_data(country=country)
            else:
                raise FileNotFoundError(
                    f"IMD data file not found at {default_path}. "
                    "Set download_if_missing=True to download automatically."
                )
        else:
            filepath = default_path
    else:
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"IMD data file not found: {filepath}")

    logger.info(f"Loading IMD data from {filepath}")

    # Load CSV with appropriate encoding
    df = pd.read_csv(filepath, encoding="utf-8")

    if standardize_columns and country == "england":
        df = _standardize_england_columns(df)

    logger.info(f"Loaded {len(df)} LSOA records")
    return df


def _standardize_england_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize English IMD column names.

    Args:
        df: DataFrame with original column names.

    Returns:
        DataFrame with standardized column names.
    """
    # Rename columns that exist in the mapping
    rename_map = {k: v for k, v in _ENGLAND_COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    # Handle any remaining columns with very long names
    # by keeping them but logging a warning
    unmapped = [c for c in df.columns if c not in rename_map.values()]
    if unmapped:
        logger.debug(f"Unmapped columns retained: {len(unmapped)}")

    return df


def parse_imd_domains(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract and structure individual domain scores from IMD data.

    Parses the DataFrame to ensure all 7 IMD domain scores and ranks
    are available with standardized column names.

    Args:
        df: DataFrame with IMD data (should have standardized columns).

    Returns:
        DataFrame with columns for each domain:
        - income_score, income_rank, income_decile
        - employment_score, employment_rank, employment_decile
        - education_score, education_rank, education_decile
        - health_score, health_rank, health_decile
        - crime_score, crime_rank, crime_decile
        - housing_score, housing_rank, housing_decile
        - environment_score, environment_rank, environment_decile

    Raises:
        ValueError: If required domain columns are missing.

    Example:
        >>> df = load_imd_data()
        >>> domains = parse_imd_domains(df)
        >>> print(domains['income_score'].describe())
    """
    required_domains = [
        "income",
        "employment",
        "education",
        "health",
        "crime",
        "housing",
        "environment",
    ]

    missing_domains = []
    for domain in required_domains:
        score_col = f"{domain}_score"
        if score_col not in df.columns:
            missing_domains.append(domain)

    if missing_domains:
        raise ValueError(
            f"Missing domain columns for: {missing_domains}. "
            "Ensure columns are standardized first."
        )

    # Select core identification and domain columns
    core_cols = ["lsoa_code", "lsoa_name"]
    domain_cols = []

    for domain in required_domains:
        for suffix in ["_score", "_rank", "_decile"]:
            col = f"{domain}{suffix}"
            if col in df.columns:
                domain_cols.append(col)

    select_cols = [c for c in core_cols if c in df.columns] + domain_cols
    return df[select_cols].copy()


def get_deprivation_decile(
    df: pd.DataFrame,
    rank_column: str = "imd_rank",
    total_lsoas: int | None = None,
) -> pd.Series:
    """
    Calculate IMD decile from rank.

    Deciles range from 1 (most deprived 10%) to 10 (least deprived 10%).
    If decile column already exists, returns it. Otherwise calculates from rank.

    Args:
        df: DataFrame with IMD data.
        rank_column: Column containing IMD rank (1 = most deprived).
        total_lsoas: Total number of LSOAs for decile calculation.
            If None, uses the maximum rank value.

    Returns:
        Series with decile values (1-10).

    Example:
        >>> df = load_imd_data()
        >>> deciles = get_deprivation_decile(df)
        >>> print(deciles.value_counts().sort_index())
    """
    # If decile column already exists, return it
    if "imd_decile" in df.columns:
        return df["imd_decile"]

    if rank_column not in df.columns:
        raise ValueError(f"Rank column '{rank_column}' not found in DataFrame")

    ranks = df[rank_column]

    if total_lsoas is None:
        total_lsoas = ranks.max()

    # Calculate decile: rank 1 -> decile 1, rank N -> decile 10
    # Formula: ceil(rank / (total / 10))
    deciles = pd.Series(
        ((ranks - 1) // (total_lsoas // 10) + 1).clip(1, 10),
        index=df.index,
        name="imd_decile",
    )

    return deciles.astype(int)


def merge_with_boundaries(
    imd_df: pd.DataFrame,
    boundaries_gdf: gpd.GeoDataFrame,
    imd_code_column: str = "lsoa_code",
    boundary_code_column: str = "LSOA21CD",
) -> gpd.GeoDataFrame:
    """
    Join IMD data with LSOA boundary geometries.

    Merges IMD socioeconomic data with LSOA boundary polygons from
    census_shapes module for spatial analysis and visualization.

    Note: IMD 2019 uses 2011 LSOA codes, while boundaries may use 2021 codes.
    There is high overlap but some LSOAs were merged/split between censuses.

    Args:
        imd_df: DataFrame with IMD data (from load_imd_data).
        boundaries_gdf: GeoDataFrame with LSOA boundaries (from load_lsoa_boundaries).
        imd_code_column: Column in imd_df containing LSOA codes.
        boundary_code_column: Column in boundaries_gdf containing LSOA codes.

    Returns:
        GeoDataFrame with IMD data joined to boundary geometries.
        Rows without matching boundaries are excluded.

    Example:
        >>> from poverty_tda.data.census_shapes import load_lsoa_boundaries
        >>> imd_df = load_imd_data()
        >>> boundaries = load_lsoa_boundaries()
        >>> merged = merge_with_boundaries(imd_df, boundaries)
        >>> merged.plot(column='imd_score', legend=True)
    """
    if imd_code_column not in imd_df.columns:
        raise ValueError(f"IMD code column '{imd_code_column}' not found")

    if boundary_code_column not in boundaries_gdf.columns:
        raise ValueError(f"Boundary code column '{boundary_code_column}' not found")

    logger.info(
        f"Merging {len(imd_df)} IMD records with {len(boundaries_gdf)} boundaries"
    )

    # Try exact match first
    merged = boundaries_gdf.merge(
        imd_df,
        left_on=boundary_code_column,
        right_on=imd_code_column,
        how="inner",
    )

    match_rate = len(merged) / len(imd_df) * 100
    logger.info(f"Merged {len(merged)} records ({match_rate:.1f}% match rate)")

    if match_rate < 90:
        logger.warning(
            "Low match rate. This may be due to LSOA code version mismatch "
            "(IMD uses 2011 codes, boundaries may use 2021 codes)."
        )

    return merged


def get_domain_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract just the domain scores (not ranks or deciles) from IMD data.

    Args:
        df: DataFrame with IMD data.

    Returns:
        DataFrame with LSOA identifiers and 7 domain score columns.

    Example:
        >>> df = load_imd_data()
        >>> scores = get_domain_scores(df)
        >>> print(scores.describe())
    """
    score_cols = [
        "income_score",
        "employment_score",
        "education_score",
        "health_score",
        "crime_score",
        "housing_score",
        "environment_score",
    ]

    id_cols = ["lsoa_code", "lsoa_name"]
    existing_id_cols = [c for c in id_cols if c in df.columns]
    existing_score_cols = [c for c in score_cols if c in df.columns]

    if not existing_score_cols:
        raise ValueError("No domain score columns found. Ensure data is standardized.")

    return df[existing_id_cols + existing_score_cols].copy()


def validate_deprivation_patterns(df: pd.DataFrame) -> dict:
    """
    Validate IMD data against known deprivation patterns.

    Checks that known most-deprived and least-deprived areas appear
    in the expected deciles as a sanity check.

    Args:
        df: DataFrame with IMD data (standardized columns).

    Returns:
        Dictionary with validation results:
        - jaywick_decile: Decile for Jaywick (should be 1)
        - most_deprived_lads: Dict of LAD names and their avg deciles
        - least_deprived_lads: Dict of LAD names and their avg deciles
        - validation_passed: Boolean indicating if patterns are as expected

    Example:
        >>> df = load_imd_data()
        >>> results = validate_deprivation_patterns(df)
        >>> print(f"Jaywick decile: {results['jaywick_decile']}")
    """
    results = {
        "jaywick_decile": None,
        "most_deprived_lads": {},
        "least_deprived_lads": {},
        "validation_passed": True,
    }

    # Check Jaywick
    if "lsoa_code" in df.columns and "imd_decile" in df.columns:
        jaywick = df[df["lsoa_code"] == JAYWICK_LSOA_CODE]
        if len(jaywick) > 0:
            results["jaywick_decile"] = int(jaywick["imd_decile"].iloc[0])
            if results["jaywick_decile"] != 1:
                results["validation_passed"] = False

    # Check LAD-level patterns
    if "lad_name" in df.columns and "imd_decile" in df.columns:
        lad_avg = df.groupby("lad_name")["imd_decile"].mean()

        for lad in KNOWN_MOST_DEPRIVED_LADS:
            if lad in lad_avg.index:
                avg_decile = lad_avg[lad]
                results["most_deprived_lads"][lad] = round(avg_decile, 2)
                if avg_decile > 5:  # Should be below average
                    results["validation_passed"] = False

        for lad in KNOWN_LEAST_DEPRIVED_LADS:
            if lad in lad_avg.index:
                avg_decile = lad_avg[lad]
                results["least_deprived_lads"][lad] = round(avg_decile, 2)
                if avg_decile < 5:  # Should be above average
                    results["validation_passed"] = False

    return results
