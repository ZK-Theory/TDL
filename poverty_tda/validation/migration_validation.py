"""
Migration Validation for TDA Comparison Protocol.

Validates Morse-Smale basins against internal migration patterns
to demonstrate that topological structure captures behavioral
constraints, not just socioeconomic outcomes.

Key insight: If MS basins explain migration variance, they capture
real barriers to geographic mobility, not just statistical artifacts.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


def compute_migration_eta_squared(
    gdf,
    cluster_column: str,
    migration_column: str,
    n_bootstrap: int = 1000,
    random_state: int = 42,
) -> dict:
    """
    Compute η² (eta-squared) for migration ~ cluster_id.

    Args:
        gdf: GeoDataFrame with LSOA data, cluster assignments, and migration metrics
        cluster_column: Column containing cluster/basin assignments
        migration_column: Column containing migration metric (e.g., 'net_migration_rate')
        n_bootstrap: Number of bootstrap iterations for CI
        random_state: Random seed for reproducibility

    Returns:
        dict with:
        - eta_squared: Point estimate
        - eta_squared_ci_lower: 95% CI lower bound
        - eta_squared_ci_upper: 95% CI upper bound
        - n_clusters: Number of unique clusters
        - n_observations: Number of valid observations
    """
    # Filter to valid observations
    valid = gdf[[cluster_column, migration_column]].dropna()

    if len(valid) == 0:
        logger.warning(f"No valid observations for {cluster_column} vs {migration_column}")
        return {
            "eta_squared": np.nan,
            "eta_squared_ci_lower": np.nan,
            "eta_squared_ci_upper": np.nan,
            "n_clusters": 0,
            "n_observations": 0,
        }

    clusters = valid[cluster_column].values
    values = valid[migration_column].values

    # Compute point estimate
    eta_sq = _compute_eta_squared(clusters, values)

    # Bootstrap confidence intervals
    rng = np.random.default_rng(random_state)
    bootstrap_etas = []

    for _ in range(n_bootstrap):
        indices = rng.choice(len(values), size=len(values), replace=True)
        boot_eta = _compute_eta_squared(clusters[indices], values[indices])
        if not np.isnan(boot_eta):
            bootstrap_etas.append(boot_eta)

    if len(bootstrap_etas) > 0:
        ci_lower = np.percentile(bootstrap_etas, 2.5)
        ci_upper = np.percentile(bootstrap_etas, 97.5)
    else:
        ci_lower = ci_upper = np.nan

    return {
        "eta_squared": eta_sq,
        "eta_squared_ci_lower": ci_lower,
        "eta_squared_ci_upper": ci_upper,
        "n_clusters": len(np.unique(clusters)),
        "n_observations": len(valid),
    }


def _compute_eta_squared(groups: np.ndarray, values: np.ndarray) -> float:
    """Compute eta-squared (ANOVA effect size)."""
    unique_groups = np.unique(groups)

    if len(unique_groups) < 2:
        return np.nan

    # Overall mean
    grand_mean = np.mean(values)

    # Sum of squares between groups
    ss_between = 0
    for g in unique_groups:
        group_values = values[groups == g]
        group_mean = np.mean(group_values)
        ss_between += len(group_values) * (group_mean - grand_mean) ** 2

    # Total sum of squares
    ss_total = np.sum((values - grand_mean) ** 2)

    if ss_total == 0:
        return np.nan

    return ss_between / ss_total


def compare_methods_migration(
    gdf,
    method_columns: list[str],
    migration_column: str = "net_migration_rate",
    n_bootstrap: int = 500,
) -> pd.DataFrame:
    """
    Compare multiple clustering methods for predicting migration.

    Args:
        gdf: GeoDataFrame with cluster assignments and migration data
        method_columns: List of columns containing cluster assignments
        migration_column: Column with migration metric
        n_bootstrap: Number of bootstrap iterations

    Returns:
        DataFrame with η² comparison for each method
    """
    results = []

    for method_col in method_columns:
        eta_result = compute_migration_eta_squared(gdf, method_col, migration_column, n_bootstrap)

        results.append(
            {
                "method": method_col,
                "eta_squared": eta_result["eta_squared"],
                "eta_squared_ci_lower": eta_result["eta_squared_ci_lower"],
                "eta_squared_ci_upper": eta_result["eta_squared_ci_upper"],
                "n_clusters": eta_result["n_clusters"],
                "n_observations": eta_result["n_observations"],
            }
        )

    df = pd.DataFrame(results)
    df = df.sort_values("eta_squared", ascending=False)

    return df


def compute_basin_migration_summary(
    gdf,
    basin_column: str = "ms_basin",
    migration_columns: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Summarize migration metrics by basin.

    Args:
        gdf: GeoDataFrame with basin assignments and migration columns
        basin_column: Column containing basin IDs
        migration_columns: List of migration columns to summarize

    Returns:
        DataFrame with per-basin migration statistics
    """
    if migration_columns is None:
        migration_columns = [
            "net_migration",
            "net_migration_rate",
            "migration_churn",
            "upward_flow",
            "downward_flow",
            "escape_ratio",
        ]

    # Filter to columns that exist
    valid_cols = [c for c in migration_columns if c in gdf.columns]

    if not valid_cols:
        logger.warning("No valid migration columns found")
        return pd.DataFrame()

    # Group by basin
    agg_dict = {col: ["mean", "std", "count"] for col in valid_cols}

    summary = gdf.groupby(basin_column).agg(agg_dict)
    summary.columns = ["_".join(col).strip() for col in summary.columns.values]

    return summary.reset_index()


def test_barrier_migration_correlation(
    barrier_data: pd.DataFrame,
    adjacent_basin_migration: pd.DataFrame,
) -> dict:
    """
    Test whether barrier heights correlate with migration gradients.

    This is the key TDA validation: do topological barriers predict
    real discontinuities in migration patterns?

    Args:
        barrier_data: DataFrame with barrier heights between adjacent basins
            Columns: basin_a, basin_b, barrier_height
        adjacent_basin_migration: DataFrame with mean migration per basin
            Columns: basin_id, mean_net_migration

    Returns:
        dict with correlation coefficient, p-value, and interpretation
    """
    if len(barrier_data) == 0 or len(adjacent_basin_migration) == 0:
        return {"correlation": np.nan, "p_value": np.nan, "n_pairs": 0, "interpretation": "Insufficient data"}

    # Create lookup for basin migration
    migration_lookup = adjacent_basin_migration.set_index("basin_id")["mean_net_migration"].to_dict()

    # Compute migration gradient for each barrier
    gradients = []
    barriers = []

    for _, row in barrier_data.iterrows():
        mig_a = migration_lookup.get(row["basin_a"], np.nan)
        mig_b = migration_lookup.get(row["basin_b"], np.nan)

        if np.isnan(mig_a) or np.isnan(mig_b):
            continue

        gradient = abs(mig_a - mig_b)
        gradients.append(gradient)
        barriers.append(row["barrier_height"])

    if len(gradients) < 3:
        return {
            "correlation": np.nan,
            "p_value": np.nan,
            "n_pairs": len(gradients),
            "interpretation": "Too few adjacent basin pairs",
        }

    # Compute correlation
    r, p = stats.pearsonr(barriers, gradients)

    # Interpretation
    if p < 0.05 and r > 0.3:
        interp = f"SIGNIFICANT POSITIVE (r={r:.3f}, p={p:.4f}): Barriers predict migration discontinuities"
    elif p < 0.05 and r < -0.3:
        interp = f"SIGNIFICANT NEGATIVE (r={r:.3f}, p={p:.4f}): Unexpected - higher barriers, smaller gradients"
    elif p >= 0.05:
        interp = f"NOT SIGNIFICANT (r={r:.3f}, p={p:.4f}): Barriers do not predict migration patterns"
    else:
        interp = f"WEAK (r={r:.3f}, p={p:.4f}): Small correlation"

    return {"correlation": r, "p_value": p, "n_pairs": len(gradients), "interpretation": interp}


def compute_escape_rate_by_severity(
    gdf,
    basin_column: str = "ms_basin",
    severity_column: str = "mean_imd",
    escape_column: str = "escape_ratio",
    n_quantiles: int = 4,
) -> pd.DataFrame:
    """
    Compute escape rates stratified by basin severity.

    Tests whether low-mobility basins (high deprivation) have lower
    escape rates (fewer migrants moving to better areas).

    Args:
        gdf: GeoDataFrame with basin assignments and migration data
        basin_column: Column with basin IDs
        severity_column: Column with deprivation/severity metric
        escape_column: Column with escape ratio
        n_quantiles: Number of severity bins

    Returns:
        DataFrame showing escape rate by severity quantile
    """
    # Aggregate to basin level
    # Compute means for severity and escape columns
    basin_means = (
        gdf.groupby(basin_column)
        .agg(
            {
                severity_column: "mean",
                escape_column: "mean",
            }
        )
        .reset_index()
    )

    # Compute counts (number of LSOAs per basin) separately
    basin_counts = gdf.groupby(basin_column).size().reset_index(name="n_lsoa")

    # Merge means and counts
    basin_df = basin_means.merge(basin_counts, on=basin_column)

    # Filter valid
    basin_df = basin_df.dropna(subset=[severity_column, escape_column])

    if len(basin_df) < n_quantiles:
        logger.warning(f"Only {len(basin_df)} basins with migration data")
        return pd.DataFrame()

    # Create severity quantiles
    basin_df["severity_quantile"] = pd.qcut(
        basin_df[severity_column], q=n_quantiles, labels=[f"Q{i+1}" for i in range(n_quantiles)]
    )

    # Summarize by quantile
    summary = basin_df.groupby("severity_quantile").agg(
        {escape_column: ["mean", "std", "count"], severity_column: "mean"}
    )
    summary.columns = ["escape_rate_mean", "escape_rate_std", "n_basins", "mean_severity"]

    # Test for trend
    q1_escape = summary.loc["Q1", "escape_rate_mean"] if "Q1" in summary.index else np.nan
    q4_escape = summary.loc[f"Q{n_quantiles}", "escape_rate_mean"] if f"Q{n_quantiles}" in summary.index else np.nan

    if not np.isnan(q1_escape) and not np.isnan(q4_escape):
        summary_df = summary.reset_index()
        summary_df["interpretation"] = ""
        summary_df.loc[0, "interpretation"] = f"Least severe: {q1_escape:.3f} escape rate"
        summary_df.loc[len(summary_df) - 1, "interpretation"] = f"Most severe: {q4_escape:.3f} escape rate"

        if q4_escape < q1_escape:
            logger.info(f"EXPECTED: Higher severity → lower escape rate ({q1_escape:.3f} → {q4_escape:.3f})")
        else:
            logger.info(f"UNEXPECTED: Higher severity → higher escape rate ({q1_escape:.3f} → {q4_escape:.3f})")

        return summary_df

    return summary.reset_index()


class MigrationValidator:
    """
    Comprehensive migration validation for TDA basins.

    Usage:
        validator = MigrationValidator(gdf_with_basins, lad_migration_metrics)
        results = validator.run_full_validation()
    """

    def __init__(
        self,
        gdf,
        migration_metrics: pd.DataFrame,
        basin_column: str = "ms_basin",
    ):
        """
        Initialize validator.

        Args:
            gdf: GeoDataFrame with LSOA data and basin assignments
            migration_metrics: DataFrame from compute_lad_migration_metrics()
            basin_column: Column containing basin IDs
        """
        self.gdf = gdf
        self.migration_metrics = migration_metrics
        self.basin_column = basin_column
        self.results = {}

    def run_full_validation(
        self,
        method_columns: Optional[list[str]] = None,
    ) -> dict:
        """
        Run complete migration validation suite.

        Args:
            method_columns: Columns to compare (default: ms_basin, kmeans_cluster, lisa_cluster)

        Returns:
            dict with all validation results
        """
        from poverty_tda.data.process_migration import join_migration_to_lsoa

        # Join migration data to LSOAs
        gdf_with_mig = join_migration_to_lsoa(self.migration_metrics, self.gdf)

        if method_columns is None:
            # Auto-detect method columns
            method_columns = [
                c
                for c in gdf_with_mig.columns
                if c in ["ms_basin", "kmeans_cluster", "lisa_cluster", "gi_cluster", "dbscan_cluster"]
            ]

        # 1. η² comparison
        if "net_migration_rate" in gdf_with_mig.columns:
            eta_comparison = compare_methods_migration(gdf_with_mig, method_columns, "net_migration_rate")
            self.results["eta_squared_comparison"] = eta_comparison
            logger.info(f"Migration η² comparison:\n{eta_comparison}")

        # 2. Escape rate by severity
        if "escape_ratio" in gdf_with_mig.columns and "mean_imd" in gdf_with_mig.columns:
            escape_analysis = compute_escape_rate_by_severity(gdf_with_mig)
            self.results["escape_rate_by_severity"] = escape_analysis

        # 3. Basin migration summary
        basin_summary = compute_basin_migration_summary(gdf_with_mig, self.basin_column)
        self.results["basin_migration_summary"] = basin_summary

        return self.results

    def generate_report(self, output_path: Optional[Path] = None) -> str:
        """Generate markdown report of validation results."""
        lines = [
            "# Migration Validation Results",
            "",
            f"**Basin column:** {self.basin_column}",
            "",
            "## Method Comparison (η²)",
            "",
        ]

        if "eta_squared_comparison" in self.results:
            df = self.results["eta_squared_comparison"]
            lines.append("| Method | η² | 95% CI | Clusters |")
            lines.append("|--------|-----|--------|----------|")
            for _, row in df.iterrows():
                lines.append(
                    f"| {row['method']} | {row['eta_squared']:.3f} | "
                    f"[{row['eta_squared_ci_lower']:.3f}, {row['eta_squared_ci_upper']:.3f}] | "
                    f"{row['n_clusters']} |"
                )
            lines.append("")

        if "escape_rate_by_severity" in self.results:
            lines.append("## Escape Rate by Basin Severity")
            lines.append("")
            df = self.results["escape_rate_by_severity"]
            lines.append("| Severity | Escape Rate | Std | N Basins |")
            lines.append("|----------|-------------|-----|----------|")
            for _, row in df.iterrows():
                lines.append(
                    f"| {row['severity_quantile']} | {row['escape_rate_mean']:.3f} | "
                    f"{row['escape_rate_std']:.3f} | {row['n_basins']} |"
                )
            lines.append("")

        report = "\n".join(lines)

        if output_path:
            output_path.write_text(report)
            logger.info(f"Wrote report to {output_path}")

        return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Quick demo
    print("Migration validation module loaded successfully")
    print("Use MigrationValidator class for full validation pipeline")
