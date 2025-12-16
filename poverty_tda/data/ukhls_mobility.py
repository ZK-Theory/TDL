"""
UKHLS Actual Mobility Surface Construction.

This module constructs genuine social mobility surfaces from Understanding Society
(UK Household Longitudinal Study) panel data, replacing the IMD-based deprivation
proxy with actual income trajectory measurement.

Key Features:
- Uses real longitudinal income data (not cross-sectional deprivation)
- Computes income mobility as quintile transitions over time
- Aggregates to MSOA level for stable geographic estimates
- Provides comparison with deprivation-based proxy

Data Requirements:
- UKHLS main survey data (Special Licence for geographic identifiers)
- Variables: fihhmnnet1_dv (household income), pidp (person ID), hidp (household ID)
- Geographic: lsoa11, msoa11 (requires Special Licence Access)

UK Data Service Access:
- Standard End User Licence: Basic demographic/income data
- Special Licence: Geographic identifiers (LSOA/MSOA)
- Apply at: https://ukdataservice.ac.uk/

References:
- Understanding Society documentation: https://www.understandingsociety.ac.uk/
- UKHLS geographic guide: https://www.understandingsociety.ac.uk/documentation/mainstage/user-guides/geography
- Intergenerational mobility: Blanden et al. (2005), Golothorpe & Jackson (2007)

License: Open Government Licence v3.0 (for code; UKHLS data has separate terms)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score

logger = logging.getLogger(__name__)


# =============================================================================
# DATA LOADING (requires UKHLS Special Licence access)
# =============================================================================


def load_ukhls_income_panel(
    data_dir: Path | str,
    waves: list[int] | None = None,
    geographic_level: Literal["lsoa", "msoa", "lad"] = "msoa",
) -> pd.DataFrame:
    """
    Load UKHLS panel data with income and geographic identifiers.

    This function requires Special Licence access to UKHLS geographic identifiers.
    Apply via UK Data Service: https://ukdataservice.ac.uk/

    Args:
        data_dir: Path to UKHLS data files (.dta format)
        waves: List of wave numbers to load (default: waves 1-11)
        geographic_level: Geographic aggregation level ('lsoa', 'msoa', 'lad')

    Returns:
        DataFrame with columns:
        - pidp: Person identifier
        - hidp: Household identifier
        - wave: Survey wave number
        - income: Monthly household net income (fihhmnnet1_dv)
        - geo_id: Geographic identifier at requested level
        - year: Survey year

    Example:
        >>> panel = load_ukhls_income_panel('/path/to/ukhls', waves=[1, 5, 11])
        >>> print(f"Loaded {len(panel)} person-wave observations")

    Raises:
        FileNotFoundError: If UKHLS data files not found
        PermissionError: If geographic identifiers not accessible (need Special Licence)
    """
    data_dir = Path(data_dir)

    if waves is None:
        waves = list(range(1, 12))  # Waves 1-11 (2009-2020)

    # Wave letters for file naming
    wave_letters = {
        1: "a",
        2: "b",
        3: "c",
        4: "d",
        5: "e",
        6: "f",
        7: "g",
        8: "h",
        9: "i",
        10: "j",
        11: "k",
        12: "l",
    }

    # Survey years (approximate)
    wave_years = {
        1: 2009,
        2: 2010,
        3: 2011,
        4: 2012,
        5: 2013,
        6: 2014,
        7: 2015,
        8: 2016,
        9: 2017,
        10: 2018,
        11: 2019,
        12: 2020,
    }

    # Geographic column names
    geo_columns = {"lsoa": "lsoa11", "msoa": "msoa11", "lad": "lad11cd"}
    geo_col = geo_columns[geographic_level]

    panel_data = []

    for wave in waves:
        letter = wave_letters.get(wave)
        if letter is None:
            logger.warning(f"Wave {wave} not supported, skipping")
            continue

        # Main individual response file
        indresp_file = data_dir / f"{letter}_indresp.dta"

        # Geographic identifiers file (Special Licence)
        geo_file = data_dir / f"{letter}_lsoa11.dta"  # or similar naming

        if not indresp_file.exists():
            logger.warning(f"Wave {wave} indresp file not found: {indresp_file}")
            continue

        try:
            # Load individual response data
            indresp = pd.read_stata(indresp_file, columns=["pidp", "hidp", f"{letter}_fihhmnnet1_dv"])
            indresp = indresp.rename(columns={f"{letter}_fihhmnnet1_dv": "income"})

            # Load geographic identifiers if available
            if geo_file.exists():
                geo = pd.read_stata(geo_file, columns=["pidp", geo_col])
                indresp = indresp.merge(geo, on="pidp", how="left")
                indresp = indresp.rename(columns={geo_col: "geo_id"})
            else:
                logger.warning(f"Geographic file not found: {geo_file}")
                indresp["geo_id"] = np.nan

            indresp["wave"] = wave
            indresp["year"] = wave_years.get(wave, 2009 + wave - 1)

            panel_data.append(indresp)
            logger.info(f"Loaded wave {wave}: {len(indresp)} observations")

        except Exception as e:
            logger.error(f"Error loading wave {wave}: {e}")
            continue

    if not panel_data:
        raise FileNotFoundError(
            f"No UKHLS data found in {data_dir}. " "Download from UK Data Service: https://ukdataservice.ac.uk/"
        )

    panel = pd.concat(panel_data, ignore_index=True)

    # Filter to valid income observations
    panel = panel[panel["income"] > 0]
    panel = panel.dropna(subset=["income"])

    logger.info(f"Total panel: {len(panel)} observations, {panel['pidp'].nunique()} individuals")

    return panel


# =============================================================================
# MOBILITY COMPUTATION
# =============================================================================


def compute_income_quintiles(panel: pd.DataFrame, wave_col: str = "wave") -> pd.DataFrame:
    """
    Compute income quintiles within each wave.

    Args:
        panel: Panel data with 'income' column
        wave_col: Column identifying survey wave

    Returns:
        Panel with added 'income_quintile' column (1=lowest, 5=highest)
    """
    result = panel.copy()

    def assign_quintile(group):
        group["income_quintile"] = pd.qcut(group["income"], q=5, labels=False, duplicates="drop") + 1
        return group

    result = result.groupby(wave_col, group_keys=False).apply(assign_quintile)

    return result


def compute_individual_mobility(
    panel: pd.DataFrame,
    wave_start: int = 1,
    wave_end: int = 11,
    method: Literal["quintile_change", "rank_change", "absolute_change"] = "quintile_change",
) -> pd.DataFrame:
    """
    Compute individual-level income mobility between two waves.

    Args:
        panel: Panel data with income and wave information
        wave_start: Starting wave for mobility calculation
        wave_end: Ending wave for mobility calculation
        method: Mobility calculation method:
            - 'quintile_change': Change in income quintile (Chetty-style)
            - 'rank_change': Change in national income percentile rank
            - 'absolute_change': Standardized absolute income change

    Returns:
        DataFrame with individual mobility scores and geographic identifiers

    Example:
        >>> mobility = compute_individual_mobility(panel, wave_start=1, wave_end=11)
        >>> print(f"Mean mobility: {mobility['mobility'].mean():.3f}")
    """
    # Filter to individuals present in both waves
    start_data = panel[panel["wave"] == wave_start][["pidp", "income", "geo_id", "income_quintile"]]
    end_data = panel[panel["wave"] == wave_end][["pidp", "income", "income_quintile"]]

    start_data = start_data.rename(columns={"income": "income_start", "income_quintile": "quintile_start"})
    end_data = end_data.rename(columns={"income": "income_end", "income_quintile": "quintile_end"})

    merged = start_data.merge(end_data, on="pidp", how="inner")

    if len(merged) == 0:
        raise ValueError(f"No individuals found in both waves {wave_start} and {wave_end}")

    logger.info(f"Computing mobility for {len(merged)} individuals tracked across waves")

    if method == "quintile_change":
        # Quintile transition (positive = upward mobility)
        merged["mobility"] = merged["quintile_end"] - merged["quintile_start"]

    elif method == "rank_change":
        # Percentile rank change
        merged["rank_start"] = merged["income_start"].rank(pct=True)
        merged["rank_end"] = merged["income_end"].rank(pct=True)
        merged["mobility"] = merged["rank_end"] - merged["rank_start"]

    elif method == "absolute_change":
        # Standardized absolute change (z-score)
        merged["income_change"] = merged["income_end"] - merged["income_start"]
        merged["mobility"] = (merged["income_change"] - merged["income_change"].mean()) / merged["income_change"].std()

    else:
        raise ValueError(f"Unknown method: {method}")

    # Add indicator for upward mobility from bottom quintile (key metric)
    merged["upward_from_bottom"] = ((merged["quintile_start"] == 1) & (merged["quintile_end"] > 1)).astype(int)

    # Add indicator for downward mobility from top quintile
    merged["downward_from_top"] = ((merged["quintile_start"] == 5) & (merged["quintile_end"] < 5)).astype(int)

    return merged


def aggregate_mobility_to_geography(
    individual_mobility: pd.DataFrame,
    geographic_level: Literal["lsoa", "msoa", "lad"] = "msoa",
    min_observations: int = 5,
) -> pd.DataFrame:
    """
    Aggregate individual mobility scores to geographic areas.

    Args:
        individual_mobility: DataFrame with individual mobility and geo_id
        geographic_level: Level of aggregation (for labeling)
        min_observations: Minimum observations for reliable estimate

    Returns:
        DataFrame with geographic-level mobility statistics:
        - geo_id: Geographic identifier
        - mean_mobility: Mean mobility score
        - median_mobility: Median mobility score
        - upward_rate: Proportion achieving upward mobility from bottom quintile
        - n_observations: Sample size
        - reliable: Boolean indicating if n >= min_observations

    Example:
        >>> geo_mobility = aggregate_mobility_to_geography(individual_mobility)
        >>> reliable = geo_mobility[geo_mobility['reliable']]
        >>> print(f"{len(reliable)} reliable MSOA estimates")
    """
    # Remove observations without geographic identifier
    with_geo = individual_mobility.dropna(subset=["geo_id"])

    if len(with_geo) == 0:
        raise ValueError("No observations with geographic identifiers. Check Special Licence access.")

    logger.info(f"Aggregating {len(with_geo)} observations to {geographic_level} level")

    # Aggregate to geographic level
    geo_agg = (
        with_geo.groupby("geo_id")
        .agg(
            {
                "mobility": ["mean", "median", "std", "count"],
                "upward_from_bottom": ["sum", "mean"],
                "downward_from_top": ["sum", "mean"],
                "quintile_start": "mean",  # Initial position (for context)
            }
        )
        .reset_index()
    )

    # Flatten column names
    geo_agg.columns = [
        "geo_id",
        "mean_mobility",
        "median_mobility",
        "std_mobility",
        "n_observations",
        "n_upward_from_bottom",
        "upward_rate",
        "n_downward_from_top",
        "downward_rate",
        "mean_starting_quintile",
    ]

    # Mark reliable estimates
    geo_agg["reliable"] = geo_agg["n_observations"] >= min_observations

    reliable_count = geo_agg["reliable"].sum()
    total_count = len(geo_agg)

    logger.info(
        f"Geographic aggregation complete: {reliable_count}/{total_count} "
        f"({100 * reliable_count / total_count:.1f}%) areas have reliable estimates"
    )

    return geo_agg


# =============================================================================
# MOBILITY SURFACE CONSTRUCTION
# =============================================================================


def construct_mobility_surface(
    geo_mobility: pd.DataFrame,
    centroids_df: pd.DataFrame,
    grid_size: int = 75,
    interpolation_method: str = "linear",
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Construct interpolated mobility surface for Morse-Smale analysis.

    This creates a regular grid suitable for TTK topological analysis,
    using actual mobility measurements rather than deprivation proxy.

    Args:
        geo_mobility: Geographic-level mobility data with 'geo_id', 'mean_mobility'
        centroids_df: DataFrame with 'geo_id', 'x', 'y' centroid coordinates
        grid_size: Resolution of output grid (default 75x75)
        interpolation_method: scipy.interpolate.griddata method ('linear', 'cubic', 'nearest')

    Returns:
        Tuple of (xi, yi, zi) numpy arrays:
        - xi: X coordinates grid (eastings)
        - yi: Y coordinates grid (northings)
        - zi: Interpolated mobility values

    Example:
        >>> xi, yi, zi = construct_mobility_surface(geo_mobility, centroids)
        >>> # Save to VTI for TTK analysis
        >>> save_to_vti(xi, yi, zi, 'mobility_surface_actual.vti')
    """
    from scipy.interpolate import griddata

    # Use only reliable estimates for interpolation
    reliable = geo_mobility[geo_mobility["reliable"]].copy()

    if len(reliable) == 0:
        raise ValueError("No reliable geographic estimates for interpolation")

    # Merge with centroids
    reliable = reliable.merge(centroids_df, on="geo_id", how="inner")

    if len(reliable) == 0:
        raise ValueError("No matching centroids found for geographic units")

    logger.info(f"Interpolating mobility surface from {len(reliable)} reliable observations")

    # Extract coordinates and values
    x = reliable["x"].values
    y = reliable["y"].values
    z = reliable["mean_mobility"].values

    # Create regular grid
    xi = np.linspace(x.min(), x.max(), grid_size)
    yi = np.linspace(y.min(), y.max(), grid_size)
    xi, yi = np.meshgrid(xi, yi)

    # Interpolate
    zi = griddata(points=(x, y), values=z, xi=(xi, yi), method=interpolation_method)

    # Log statistics
    valid_mask = ~np.isnan(zi)
    if valid_mask.any():
        logger.info(
            f"Surface statistics: min={zi[valid_mask].min():.3f}, "
            f"max={zi[valid_mask].max():.3f}, mean={zi[valid_mask].mean():.3f}"
        )

    return xi, yi, zi


# =============================================================================
# COMPARISON WITH DEPRIVATION PROXY
# =============================================================================


def compare_mobility_vs_deprivation_basins(
    mobility_basins: pd.DataFrame,
    deprivation_basins: pd.DataFrame,
) -> dict:
    """
    Compare basins identified from actual mobility vs deprivation proxy.

    This is a key validation: if basins differ substantially, mobility
    measurement adds value. If they're similar, the proxy was adequate.

    Args:
        mobility_basins: Basins from actual mobility surface
        deprivation_basins: Basins from deprivation proxy surface

    Returns:
        Dictionary with comparison metrics:
        - ari: Adjusted Rand Index for basin assignment agreement
        - correlation: Pearson r between severity rankings
        - discordant_areas: List of areas that differ substantially
        - interpretation: Text summary of findings
    """
    # Merge on geographic identifier
    comparison = mobility_basins.merge(
        deprivation_basins,
        on="geo_id",
        suffixes=("_mobility", "_deprivation"),
        how="inner",
    )

    if len(comparison) == 0:
        return {
            "error": "No overlapping geographic units found",
            "ari": np.nan,
            "correlation": np.nan,
        }

    # Adjusted Rand Index (ARI) for basin assignments
    # ARI is the proper metric for comparing clusterings with arbitrary labels
    if "basin_id_mobility" in comparison.columns and "basin_id_deprivation" in comparison.columns:
        # Drop rows with NaN in either basin_id column
        valid_comparison = comparison.dropna(subset=["basin_id_mobility", "basin_id_deprivation"])
        if len(valid_comparison) > 0:
            ari = adjusted_rand_score(
                valid_comparison["basin_id_mobility"],
                valid_comparison["basin_id_deprivation"],
            )
        else:
            ari = np.nan
    else:
        ari = np.nan

    # Correlation between severity rankings
    if "severity_mobility" in comparison.columns and "severity_deprivation" in comparison.columns:
        correlation = comparison["severity_mobility"].corr(comparison["severity_deprivation"])
    else:
        correlation = np.nan

    # Identify discordant areas (large rank differences)
    if "rank_mobility" in comparison.columns and "rank_deprivation" in comparison.columns:
        comparison["rank_diff"] = abs(comparison["rank_mobility"] - comparison["rank_deprivation"])
        discordant = comparison[comparison["rank_diff"] > comparison["rank_diff"].quantile(0.9)]
        discordant_areas = discordant["geo_id"].tolist()
    else:
        discordant_areas = []

    # Interpretation
    if ari > 0.8:
        interpretation = (
            "Strong agreement (ARI > 0.8): Deprivation proxy was a reasonable "
            "approximation of mobility. Actual mobility measurement confirms prior findings."
        )
    elif ari > 0.5:
        interpretation = (
            "Moderate agreement (0.5 < ARI < 0.8): Some divergence between mobility "
            "and deprivation basins. Actual mobility measurement adds nuance but core "
            "patterns align."
        )
    else:
        interpretation = (
            "Weak agreement (ARI < 0.5): Substantial divergence between mobility "
            "and deprivation basins. This validates the importance of actual mobility "
            "measurement over deprivation proxy."
        )

    return {
        "ari": ari,
        "correlation": correlation,
        "discordant_areas": discordant_areas,
        "n_comparisons": len(comparison),
        "interpretation": interpretation,
    }


# =============================================================================
# SAMPLE SIZE DIAGNOSTICS
# =============================================================================


def analyze_sample_coverage(
    panel: pd.DataFrame,
    geographic_level: Literal["lsoa", "msoa", "lad"] = "msoa",
) -> dict:
    """
    Analyze sample size and geographic coverage for mobility estimation.

    Helps determine optimal geographic level (MSOA recommended over LSOA).

    Args:
        panel: Panel data with geographic identifiers
        geographic_level: Level to analyze

    Returns:
        Dictionary with coverage statistics:
        - n_geographic_units: Total units in data
        - mean_observations: Mean observations per unit
        - median_observations: Median observations per unit
        - pct_reliable: Percentage with n >= 5
        - recommendation: Text recommendation
    """
    with_geo = panel.dropna(subset=["geo_id"])

    if len(with_geo) == 0:
        return {"error": "No geographic identifiers available"}

    geo_counts = with_geo.groupby("geo_id").size()

    n_units = len(geo_counts)
    mean_obs = geo_counts.mean()
    median_obs = geo_counts.median()
    pct_reliable = (geo_counts >= 5).mean() * 100

    # Expected counts for different geographic levels
    expected_units = {"lsoa": 32844, "msoa": 7201, "lad": 317}
    coverage_pct = (n_units / expected_units.get(geographic_level, n_units)) * 100

    # Recommendation
    if geographic_level == "lsoa" and pct_reliable < 50:
        recommendation = (
            f"LSOA-level analysis has only {pct_reliable:.1f}% reliable estimates. "
            "Recommend aggregating to MSOA level for more stable estimates."
        )
    elif geographic_level == "msoa" and pct_reliable < 70:
        recommendation = (
            f"MSOA-level has {pct_reliable:.1f}% reliable estimates. "
            "Consider combining UKHLS with BHPS for larger sample."
        )
    elif geographic_level == "lad":
        recommendation = (
            f"LAD-level has {pct_reliable:.1f}% reliable estimates. "
            "Good coverage but geographic resolution is coarse."
        )
    else:
        recommendation = f"Good sample coverage at {geographic_level} level."

    return {
        "geographic_level": geographic_level,
        "n_geographic_units": n_units,
        "coverage_percent": coverage_pct,
        "mean_observations": mean_obs,
        "median_observations": median_obs,
        "pct_reliable": pct_reliable,
        "recommendation": recommendation,
    }


# =============================================================================
# CONVENIENCE PIPELINE
# =============================================================================


def run_mobility_analysis_pipeline(
    data_dir: Path | str,
    output_dir: Path | str,
    wave_start: int = 1,
    wave_end: int = 11,
    geographic_level: Literal["lsoa", "msoa", "lad"] = "msoa",
    min_observations: int = 5,
) -> dict:
    """
    Run complete mobility analysis pipeline from UKHLS data to mobility surface.

    This is the main entry point for constructing actual mobility surfaces.

    Args:
        data_dir: Path to UKHLS data files
        output_dir: Path for output files
        wave_start: Starting wave for mobility calculation
        wave_end: Ending wave for mobility calculation
        geographic_level: Aggregation level ('msoa' recommended)
        min_observations: Minimum observations for reliable estimate

    Returns:
        Dictionary with pipeline results and file paths

    Example:
        >>> results = run_mobility_analysis_pipeline(
        ...     data_dir='/path/to/ukhls',
        ...     output_dir='./output',
        ...     geographic_level='msoa'
        ... )
        >>> print(f"Created mobility surface: {results['surface_path']}")
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting mobility analysis pipeline...")

    # Step 1: Load data
    logger.info("Step 1: Loading UKHLS panel data...")
    panel = load_ukhls_income_panel(
        data_dir,
        waves=list(range(wave_start, wave_end + 1)),
        geographic_level=geographic_level,
    )

    # Step 2: Analyze coverage
    logger.info("Step 2: Analyzing sample coverage...")
    coverage = analyze_sample_coverage(panel, geographic_level)
    logger.info(f"Coverage: {coverage['pct_reliable']:.1f}% reliable estimates")

    # Step 3: Compute quintiles
    logger.info("Step 3: Computing income quintiles...")
    panel_with_quintiles = compute_income_quintiles(panel)

    # Step 4: Compute individual mobility
    logger.info("Step 4: Computing individual mobility...")
    individual_mobility = compute_individual_mobility(
        panel_with_quintiles,
        wave_start=wave_start,
        wave_end=wave_end,
        method="quintile_change",
    )

    # Step 5: Aggregate to geography
    logger.info("Step 5: Aggregating to geographic level...")
    geo_mobility = aggregate_mobility_to_geography(
        individual_mobility,
        geographic_level=geographic_level,
        min_observations=min_observations,
    )

    # Save intermediate results
    geo_mobility.to_csv(output_dir / f"{geographic_level}_mobility.csv", index=False)

    # Step 6: Create mobility surface (requires centroid data)
    # Note: Centroids need to be loaded separately from ONS boundary files
    logger.info("Step 6: Geographic mobility data saved. Load centroids to create surface.")

    results = {
        "panel_size": len(panel),
        "individuals_tracked": len(individual_mobility),
        "geographic_units": len(geo_mobility),
        "reliable_units": geo_mobility["reliable"].sum(),
        "coverage_stats": coverage,
        "mobility_data_path": str(output_dir / f"{geographic_level}_mobility.csv"),
        "mean_mobility": geo_mobility["mean_mobility"].mean(),
        "upward_rate": geo_mobility["upward_rate"].mean(),
    }

    logger.info("Pipeline complete!")
    logger.info(f"Tracked {results['individuals_tracked']} individuals across {wave_end - wave_start} years")
    logger.info(f"Mean upward mobility rate: {results['upward_rate']:.1%}")

    return results
