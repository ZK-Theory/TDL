"""
UK Social Mobility Proxy Calculator.

This module implements a mobility proxy formula that combines:
- Deprivation change (from IMD data)
- Educational upward mobility (from IMD education domain + POLAR4)
- Income growth indicators (from IMD income domain)

Validation against Social Mobility Commission LAD-level estimates is included.

Formula:
    mobility_proxy = α × DeprivationChange + β × EducationalUpward + γ × IncomeGrowth

Default weights: α = 0.4, β = 0.3, γ = 0.3

Data Sources:
    - IMD 2019: https://www.gov.uk/government/statistics/english-indices-of-deprivation-2019
    - Social Mobility Commission: https://www.gov.uk/government/organisations/social-mobility-commission

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
from typing import Literal

import numpy as np
import pandas as pd

from poverty_tda.data.education import compute_educational_upward

logger = logging.getLogger(__name__)

# Social Mobility Commission State of the Nation LAD rankings
# Top and bottom LADs for validation (2020 data)
# Lower rank = better mobility
SMC_TOP_MOBILITY_LADS = [
    "Westminster",
    "Kensington and Chelsea",
    "Camden",
    "City of London",
    "Wandsworth",
]

SMC_BOTTOM_MOBILITY_LADS = [
    "West Somerset",  # Now Somerset West and Taunton
    "Mansfield",
    "Bolsover",
    "Barnsley",
    "Hastings",
]

# Known industrial areas with lower mobility (for geographic validation)
INDUSTRIAL_NORTH_LADS = [
    "Blackpool",
    "Middlesbrough",
    "Kingston upon Hull, City of",
    "Hartlepool",
    "Burnley",
    "Stoke-on-Trent",
]


def compute_deprivation_change(
    imd_current: pd.DataFrame,
    imd_baseline: pd.DataFrame | None = None,
    rank_column: str = "imd_rank",
    normalize: bool = True,
) -> pd.Series:
    """
    Compute deprivation change from IMD data.

    If baseline data is available, calculates the change in deprivation rank.
    Positive values indicate improvement (becoming less deprived).

    If no baseline available, normalizes current rank to [-1, 1] scale where
    positive values indicate less deprivation than average.

    Args:
        imd_current: DataFrame with current IMD data.
        imd_baseline: Optional DataFrame with baseline IMD data (e.g., IMD 2015).
            Must contain 'lsoa_code' and rank column.
        rank_column: Column name for IMD rank.
        normalize: If True, normalize output to [-1, 1] scale.

    Returns:
        Series with deprivation change scores per LSOA.
        Positive = improvement (less deprived), Negative = worsening.

    Example:
        >>> imd_df = load_imd_data()
        >>> dep_change = compute_deprivation_change(imd_df)
        >>> print(dep_change.describe())
    """
    if rank_column not in imd_current.columns:
        raise ValueError(f"Column '{rank_column}' not found in current IMD data")

    if imd_baseline is not None:
        # Calculate change between time periods
        if rank_column not in imd_baseline.columns:
            raise ValueError(f"Column '{rank_column}' not found in baseline IMD data")

        merged = imd_current[["lsoa_code", rank_column]].merge(
            imd_baseline[["lsoa_code", rank_column]],
            on="lsoa_code",
            suffixes=("_current", "_baseline"),
        )

        # Positive change = rank increased = less deprived = improvement
        change = merged[f"{rank_column}_current"] - merged[f"{rank_column}_baseline"]

        if normalize:
            max_change = max(abs(change.max()), abs(change.min()))
            if max_change > 0:
                change = change / max_change

        return pd.Series(change.values, index=merged.index, name="deprivation_change")

    # No baseline: normalize current rank
    # Higher rank = less deprived = positive indicator
    logger.info(
        "No baseline IMD data provided. "
        "Using current rank normalized to mean-centered scale."
    )

    ranks = imd_current[rank_column]
    total_lsoas = ranks.max()

    if normalize:
        # Center around 0: rank 1 -> -1, rank N -> +1
        normalized = (2 * ranks / total_lsoas) - 1
    else:
        normalized = ranks

    return pd.Series(
        normalized.values, index=imd_current.index, name="deprivation_change"
    )


def compute_income_growth(
    imd_df: pd.DataFrame,
    score_column: str = "income_score",
    rank_column: str = "income_rank",
    normalize: bool = True,
) -> pd.Series:
    """
    Compute income growth indicator from IMD income domain.

    The IMD income domain measures the proportion of the population
    experiencing deprivation relating to low income. Lower scores/ranks
    indicate less income deprivation.

    Args:
        imd_df: DataFrame with IMD data.
        score_column: Column name for income score.
        rank_column: Column name for income rank.
        normalize: If True, normalize output to [0, 1] scale.

    Returns:
        Series with income indicator per LSOA.
        Higher values = less income deprivation = positive indicator.

    Note:
        This is a static measure. For true income growth, multi-year
        data would be needed (e.g., comparing IMD 2015 to IMD 2019).
    """
    if rank_column in imd_df.columns:
        ranks = imd_df[rank_column]
        total = ranks.max()

        # Higher rank = less deprived = positive
        if normalize:
            income_indicator = ranks / total
        else:
            income_indicator = ranks

    elif score_column in imd_df.columns:
        scores = imd_df[score_column]
        # Lower score = less income deprivation
        if normalize:
            income_indicator = 1 - scores  # Invert: lower score -> higher value
        else:
            income_indicator = -scores  # Negative because lower is better

    else:
        raise ValueError(
            f"IMD DataFrame must contain '{rank_column}' or '{score_column}'"
        )

    return pd.Series(income_indicator.values, index=imd_df.index, name="income_growth")


def compute_mobility_proxy(
    imd_df: pd.DataFrame,
    education_df: pd.DataFrame | None = None,
    imd_baseline: pd.DataFrame | None = None,
    alpha: float = 0.4,
    beta: float = 0.3,
    gamma: float = 0.3,
) -> pd.DataFrame:
    """
    Compute social mobility proxy combining deprivation, education, and income.

    Implements the mobility proxy formula:
        mobility_proxy = α×DeprivationChange + β×EducationalUpward + γ×IncomeGrowth

    Args:
        imd_df: DataFrame with current IMD data.
        education_df: Optional DataFrame with POLAR4 or additional education data.
            If None, uses IMD education domain only.
        imd_baseline: Optional DataFrame with baseline IMD data for change calculation.
        alpha: Weight for deprivation change component (default 0.4).
        beta: Weight for educational upward mobility (default 0.3).
        gamma: Weight for income growth component (default 0.3).

    Returns:
        DataFrame with columns:
        - lsoa_code: LSOA identifier
        - deprivation_change: Normalized deprivation change [-1, 1]
        - educational_upward: Educational mobility [0, 1]
        - income_growth: Income indicator [0, 1]
        - mobility_proxy: Combined proxy score

    Raises:
        ValueError: If weights don't sum to 1.0 or required columns missing.

    Example:
        >>> imd_df = load_imd_data()
        >>> result = compute_mobility_proxy(imd_df)
        >>> print(result['mobility_proxy'].describe())
    """
    # Validate weights
    weight_sum = alpha + beta + gamma
    if not np.isclose(weight_sum, 1.0, atol=0.01):
        raise ValueError(
            f"Weights must sum to 1.0, got {weight_sum} "
            f"(α={alpha}, β={beta}, γ={gamma})"
        )

    if "lsoa_code" not in imd_df.columns:
        raise ValueError("IMD DataFrame must contain 'lsoa_code' column")

    logger.info(
        f"Computing mobility proxy with weights: "
        f"α={alpha} (deprivation), β={beta} (education), γ={gamma} (income)"
    )

    # Component 1: Deprivation change
    dep_change = compute_deprivation_change(imd_df, imd_baseline, normalize=True)

    # Component 2: Educational upward mobility
    edu_upward = compute_educational_upward(imd_df, education_df)

    # Component 3: Income growth
    income = compute_income_growth(imd_df, normalize=True)

    # Normalize deprivation change to [0, 1] for consistent combination
    # Original is [-1, 1], shift to [0, 1]
    dep_change_normalized = (dep_change + 1) / 2

    # Compute weighted combination
    mobility_proxy = alpha * dep_change_normalized + beta * edu_upward + gamma * income

    # Build result DataFrame
    result = pd.DataFrame(
        {
            "lsoa_code": imd_df["lsoa_code"].values,
            "deprivation_change": dep_change.values,
            "educational_upward": edu_upward.values,
            "income_growth": income.values,
            "mobility_proxy": mobility_proxy.values,
        }
    )

    # Add LAD info if available for aggregation
    if "lad_name" in imd_df.columns:
        result["lad_name"] = imd_df["lad_name"].values
    if "lad_code" in imd_df.columns:
        result["lad_code"] = imd_df["lad_code"].values

    logger.info(
        f"Computed mobility proxy for {len(result)} LSOAs. "
        f"Mean: {mobility_proxy.mean():.3f}, Std: {mobility_proxy.std():.3f}"
    )

    return result


def aggregate_to_lad(
    mobility_df: pd.DataFrame,
    lad_column: str = "lad_name",
    method: Literal["mean", "median", "weighted"] = "mean",
    population_column: str | None = None,
) -> pd.DataFrame:
    """
    Aggregate LSOA-level mobility proxy to Local Authority District level.

    Args:
        mobility_df: DataFrame with LSOA-level mobility proxy data.
        lad_column: Column containing LAD identifier.
        method: Aggregation method:
            - "mean": Simple average of LSOA values
            - "median": Median of LSOA values
            - "weighted": Population-weighted average
        population_column: Column for population weights.
            Required if method="weighted".

    Returns:
        DataFrame with LAD-level mobility proxy statistics.

    Example:
        >>> imd_df = load_imd_data()
        >>> mobility = compute_mobility_proxy(imd_df)
        >>> lad_mobility = aggregate_to_lad(mobility)
    """
    if lad_column not in mobility_df.columns:
        raise ValueError(f"LAD column '{lad_column}' not found in DataFrame")

    numeric_cols = [
        "deprivation_change",
        "educational_upward",
        "income_growth",
        "mobility_proxy",
    ]
    cols_to_agg = [c for c in numeric_cols if c in mobility_df.columns]

    if method == "weighted":
        if population_column is None or population_column not in mobility_df.columns:
            logger.warning(
                "Population column not available, falling back to mean aggregation"
            )
            method = "mean"

    if method == "mean":
        agg = mobility_df.groupby(lad_column)[cols_to_agg].mean()
    elif method == "median":
        agg = mobility_df.groupby(lad_column)[cols_to_agg].median()
    elif method == "weighted":
        # Weighted average
        def weighted_mean(group):
            weights = group[population_column]
            result = {}
            for col in cols_to_agg:
                if col in group.columns:
                    result[col] = np.average(group[col], weights=weights)
            return pd.Series(result)

        agg = mobility_df.groupby(lad_column).apply(weighted_mean, include_groups=False)

    # Add count of LSOAs per LAD
    lsoa_counts = mobility_df.groupby(lad_column).size()
    agg["lsoa_count"] = lsoa_counts

    # Rank LADs by mobility proxy
    agg["mobility_rank"] = agg["mobility_proxy"].rank(ascending=False)

    return agg.reset_index()


def validate_against_smc(
    mobility_df: pd.DataFrame,
    smc_data: pd.DataFrame | None = None,
) -> dict:
    """
    Validate mobility proxy against Social Mobility Commission estimates.

    Compares LAD-level mobility proxy values against known SMC rankings
    and geographic patterns (e.g., industrial North showing lower mobility).

    Args:
        mobility_df: DataFrame with mobility proxy data (LSOA or LAD level).
            If LSOA level, will be aggregated to LAD.
        smc_data: Optional DataFrame with SMC LAD-level estimates.
            If None, uses built-in validation against known patterns.

    Returns:
        Dictionary with validation results:
        - correlation: Correlation with SMC data (if provided)
        - top_lads_check: Dict of expected top LADs and their ranks
        - bottom_lads_check: Dict of expected bottom LADs and their ranks
        - industrial_north_check: Average rank of industrial areas
        - validation_passed: Boolean indicating if validation passed

    Example:
        >>> imd_df = load_imd_data()
        >>> mobility = compute_mobility_proxy(imd_df)
        >>> results = validate_against_smc(mobility)
        >>> print(f"Validation passed: {results['validation_passed']}")
    """
    results = {
        "correlation": None,
        "top_lads_check": {},
        "bottom_lads_check": {},
        "industrial_north_check": None,
        "validation_passed": True,
        "details": {},
    }

    # Aggregate to LAD if needed
    if "mobility_proxy" in mobility_df.columns and "lad_name" in mobility_df.columns:
        if "lsoa_code" in mobility_df.columns:
            lad_mobility = aggregate_to_lad(mobility_df)
        else:
            lad_mobility = mobility_df
    else:
        logger.warning(
            "Cannot validate: mobility_df must contain 'mobility_proxy' and 'lad_name'"
        )
        results["validation_passed"] = False
        return results

    # Get mobility values by LAD name
    lad_values = lad_mobility.set_index("lad_name")["mobility_proxy"]
    total_lads = len(lad_values)

    # Check expected top mobility LADs (should have high proxy values)
    for lad in SMC_TOP_MOBILITY_LADS:
        if lad in lad_values.index:
            value = lad_values[lad]
            percentile = (lad_values <= value).sum() / total_lads * 100
            results["top_lads_check"][lad] = {
                "value": round(value, 3),
                "percentile": round(percentile, 1),
            }
            # Should be in top 30%
            if percentile < 70:
                results["validation_passed"] = False

    # Check expected bottom mobility LADs (should have low proxy values)
    for lad in SMC_BOTTOM_MOBILITY_LADS:
        if lad in lad_values.index:
            value = lad_values[lad]
            percentile = (lad_values <= value).sum() / total_lads * 100
            results["bottom_lads_check"][lad] = {
                "value": round(value, 3),
                "percentile": round(percentile, 1),
            }
            # Should be in bottom 30%
            if percentile > 30:
                results["validation_passed"] = False

    # Check industrial North pattern
    north_values = []
    for lad in INDUSTRIAL_NORTH_LADS:
        if lad in lad_values.index:
            north_values.append(lad_values[lad])

    if north_values:
        avg_north = np.mean(north_values)
        avg_all = lad_values.mean()
        results["industrial_north_check"] = {
            "avg_industrial_north": round(avg_north, 3),
            "avg_all_lads": round(avg_all, 3),
            "below_average": avg_north < avg_all,
        }
        # Industrial North should be below national average
        if avg_north >= avg_all:
            results["validation_passed"] = False

    # Correlation with SMC data if provided
    if smc_data is not None and "mobility_rank" in smc_data.columns:
        merged = lad_mobility.merge(
            smc_data, on="lad_name", suffixes=("_proxy", "_smc")
        )
        if len(merged) > 10:
            correlation = merged["mobility_proxy"].corr(merged["mobility_rank"])
            results["correlation"] = round(correlation, 3)
            # Expect positive correlation > 0.5
            if correlation < 0.5:
                results["validation_passed"] = False

    results["details"] = {
        "total_lads_analyzed": total_lads,
        "top_lads_found": len(results["top_lads_check"]),
        "bottom_lads_found": len(results["bottom_lads_check"]),
    }

    return results


def get_mobility_quintiles(mobility_df: pd.DataFrame) -> pd.Series:
    """
    Classify LSOAs into mobility quintiles.

    Args:
        mobility_df: DataFrame with mobility_proxy column.

    Returns:
        Series with quintile values (1-5) where:
        - 1 = lowest mobility (bottom 20%)
        - 5 = highest mobility (top 20%)
    """
    if "mobility_proxy" not in mobility_df.columns:
        raise ValueError("DataFrame must contain 'mobility_proxy' column")

    return pd.qcut(
        mobility_df["mobility_proxy"],
        q=5,
        labels=[1, 2, 3, 4, 5],
    ).rename("mobility_quintile")
