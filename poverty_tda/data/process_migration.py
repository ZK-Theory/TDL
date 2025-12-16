"""
Migration Data Processing for TDA Validation.

Processes ONS internal migration by LAD data for use in validating
Morse-Smale basins against behavioral outcomes.

Data source: ONS Internal Migration detailed estimates
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Default data path (relative to project root)
DEFAULT_MIGRATION_PATH = Path("data/raw/outcomes/internal_migration_by_lad.xlsx")


def load_migration_flows(
    file_path: Optional[Path] = None,
    year: int = 2024,
    aggregate_sex: bool = True,
) -> pd.DataFrame:
    """
    Load and parse ONS internal migration flows.

    Args:
        file_path: Path to migration xlsx file. If None, uses default location.
        year: Year to filter (default 2024, most recent).
        aggregate_sex: If True, sum male + female flows.

    Returns:
        DataFrame with columns:
        - origin_lad: Origin LAD code
        - dest_lad: Destination LAD code
        - total_flow: Total migrants (all ages)
        - working_age_flow: Migrants aged 18-64
    """
    if file_path is None:
        file_path = DEFAULT_MIGRATION_PATH

    logger.info(f"Loading migration data from {file_path}")

    # Load the detailed data sheet
    df = pd.read_excel(file_path, sheet_name="IM2024 on 2023 LAs")

    # Filter to specified year
    df = df[df["year"] == year].copy()
    logger.info(f"Filtered to year {year}: {len(df)} rows")

    # Identify age columns
    age_cols = [c for c in df.columns if c.startswith("Age_")]

    # Compute total flow (sum all ages)
    df["total_flow"] = df[age_cols].sum(axis=1)

    # Compute working age flow (18-64)
    working_age_cols = [f"Age_{i}" for i in range(18, 65) if f"Age_{i}" in age_cols]
    df["working_age_flow"] = df[working_age_cols].sum(axis=1)

    # Rename columns
    df = df.rename(columns={"outla": "origin_lad", "inla": "dest_lad"})

    # Select relevant columns
    result_cols = ["origin_lad", "dest_lad", "sex", "total_flow", "working_age_flow"]
    df = df[result_cols].copy()

    if aggregate_sex:
        # Sum male + female flows
        df = df.groupby(["origin_lad", "dest_lad"], as_index=False).agg(
            {"total_flow": "sum", "working_age_flow": "sum"}
        )
        logger.info(f"Aggregated by sex: {len(df)} unique LAD pairs")

    return df


def compute_lad_migration_metrics(
    flows_df: pd.DataFrame,
    mobility_by_lad: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Compute LAD-level migration metrics.

    Args:
        flows_df: DataFrame from load_migration_flows()
        mobility_by_lad: Optional DataFrame with 'lad_code' and 'mean_mobility'
                        for computing directional metrics

    Returns:
        DataFrame with columns:
        - lad_code: LAD identifier
        - total_outflow: Total migrants leaving
        - total_inflow: Total migrants arriving
        - net_migration: inflow - outflow
        - migration_churn: inflow + outflow
        - net_migration_rate: net / (inflow + outflow) if available
        - upward_flow: Migrants to higher-mobility LADs (if mobility provided)
        - downward_flow: Migrants to lower-mobility LADs (if mobility provided)
        - escape_ratio: upward / (upward + downward)
    """
    logger.info("Computing LAD-level migration metrics")

    # Compute outflows per LAD
    outflows = (
        flows_df.groupby("origin_lad")
        .agg({"total_flow": "sum", "working_age_flow": "sum"})
        .rename(columns={"total_flow": "total_outflow", "working_age_flow": "working_age_outflow"})
    )

    # Compute inflows per LAD
    inflows = (
        flows_df.groupby("dest_lad")
        .agg({"total_flow": "sum", "working_age_flow": "sum"})
        .rename(columns={"total_flow": "total_inflow", "working_age_flow": "working_age_inflow"})
    )

    # Combine
    lad_metrics = outflows.join(inflows, how="outer").fillna(0)
    lad_metrics.index.name = "lad_code"
    lad_metrics = lad_metrics.reset_index()

    # Basic metrics
    lad_metrics["net_migration"] = lad_metrics["total_inflow"] - lad_metrics["total_outflow"]
    lad_metrics["migration_churn"] = lad_metrics["total_inflow"] + lad_metrics["total_outflow"]
    lad_metrics["net_working_age"] = lad_metrics["working_age_inflow"] - lad_metrics["working_age_outflow"]

    # Normalize by churn (avoids need for population data)
    lad_metrics["net_migration_rate"] = np.where(
        lad_metrics["migration_churn"] > 0, lad_metrics["net_migration"] / lad_metrics["migration_churn"], 0
    )

    # Directional metrics (if mobility data provided)
    if mobility_by_lad is not None:
        lad_metrics = _add_directional_metrics(flows_df, lad_metrics, mobility_by_lad)

    logger.info(f"Computed metrics for {len(lad_metrics)} LADs")
    return lad_metrics


def _add_directional_metrics(
    flows_df: pd.DataFrame,
    lad_metrics: pd.DataFrame,
    mobility_by_lad: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add directional migration metrics based on mobility levels.

    Computes flows to higher-mobility vs lower-mobility destinations.
    """
    logger.info("Computing directional migration metrics")

    # Ensure mobility data has required columns
    if "lad_code" not in mobility_by_lad.columns or "mean_mobility" not in mobility_by_lad.columns:
        logger.warning("mobility_by_lad must have 'lad_code' and 'mean_mobility' columns")
        return lad_metrics

    mobility_lookup = mobility_by_lad.set_index("lad_code")["mean_mobility"].to_dict()

    # For each origin LAD, compute flows to higher/lower mobility destinations
    upward_flows = []
    downward_flows = []

    for origin_lad, group in flows_df.groupby("origin_lad"):
        origin_mobility = mobility_lookup.get(origin_lad, np.nan)

        if np.isnan(origin_mobility):
            upward_flows.append({"lad_code": origin_lad, "upward_flow": np.nan, "downward_flow": np.nan})
            continue

        # Split flows by destination mobility
        upward = 0
        downward = 0

        for _, row in group.iterrows():
            dest_mobility = mobility_lookup.get(row["dest_lad"], np.nan)
            if np.isnan(dest_mobility):
                continue

            if dest_mobility > origin_mobility:
                upward += row["total_flow"]
            else:
                downward += row["total_flow"]

        upward_flows.append({"lad_code": origin_lad, "upward_flow": upward, "downward_flow": downward})

    directional_df = pd.DataFrame(upward_flows)

    # Compute escape ratio
    directional_df["escape_ratio"] = np.where(
        (directional_df["upward_flow"] + directional_df["downward_flow"]) > 0,
        directional_df["upward_flow"] / (directional_df["upward_flow"] + directional_df["downward_flow"]),
        np.nan,
    )

    # Merge with main metrics
    lad_metrics = lad_metrics.merge(directional_df, on="lad_code", how="left")

    return lad_metrics


def join_migration_to_lsoa(
    lad_migration: pd.DataFrame,
    lsoa_gdf,  # GeoDataFrame with LSOA boundaries
    lad_column: str = "lad_code",
) -> pd.DataFrame:
    """
    Join LAD-level migration metrics to LSOA data.

    Since migration is at LAD level, all LSOAs in a LAD get the same values.

    Args:
        lad_migration: DataFrame from compute_lad_migration_metrics()
        lsoa_gdf: GeoDataFrame with LSOA data (must have LAD code column)
        lad_column: Column name containing LAD codes in lsoa_gdf

    Returns:
        LSOA GeoDataFrame with migration columns added
    """
    logger.info(f"Joining migration metrics to {len(lsoa_gdf)} LSOAs")

    # Find LAD column in LSOA data
    possible_cols = [lad_column, "LAD21CD", "lad21cd", "LAD11CD", "ladcd"]
    lad_col = None
    for col in possible_cols:
        if col in lsoa_gdf.columns:
            lad_col = col
            break

    if lad_col is None:
        logger.warning(f"Could not find LAD column in LSOA data. Tried: {possible_cols}")
        return lsoa_gdf

    # Merge
    result = lsoa_gdf.merge(lad_migration, left_on=lad_col, right_on="lad_code", how="left")

    # Count matches
    matched = result["net_migration"].notna().sum()
    logger.info(f"Matched {matched}/{len(result)} LSOAs to migration data")

    return result


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)

    flows = load_migration_flows()
    print(f"Loaded {len(flows)} flow records")

    metrics = compute_lad_migration_metrics(flows)
    print("\nTop 5 LADs by net migration:")
    print(metrics.nlargest(5, "net_migration")[["lad_code", "net_migration", "migration_churn"]])

    print("\nBottom 5 LADs by net migration:")
    print(metrics.nsmallest(5, "net_migration")[["lad_code", "net_migration", "migration_churn"]])
