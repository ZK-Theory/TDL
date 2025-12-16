"""
Unified TDA Comparison Protocol Runner.

This module orchestrates the complete comparison protocol between TDA methods
and traditional spatial statistics, following the empirical comparison framework.

The runner executes all phases:
1. Baseline Characterization: Apply all methods
2. Agreement Analysis: Compute ARI matrix with CIs
3. Outcome Validation: η² for outcome prediction
4. Boundary Analysis: Barrier-outcome correlation (TDA-specific)
5. Stability Analysis: Parameter sensitivity testing
6. Regression Comparison: ΔR² and AIC
7. Report Generation: Structured results output

Usage:
    python -m poverty_tda.validation.comparison_runner --help

License: Open Government Licence v3.0
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from poverty_tda.validation.spatial_comparison import (
    # Bootstrap CIs
    bootstrap_eta_squared_ci,
    # Regression
    compare_regression_models,
    # TDA-specific
    compute_barrier_outcome_correlation,
    compute_dbscan_clusters,
    compute_full_comparison_matrix,
    compute_getis_ord_hotspots,
    compute_kmeans_clusters,
    # Traditional methods
    compute_lisa_clusters,
    compute_stability_analysis,
)

logger = logging.getLogger(__name__)


# =============================================================================
# RESULT DATA STRUCTURES
# =============================================================================


@dataclass
class Phase1Result:
    """Results from Phase 1: Method Application."""

    n_lsoas: int
    methods_applied: list[str]
    cluster_counts: dict[str, int]
    timestamp: str


@dataclass
class Phase2Result:
    """Results from Phase 2: Agreement Analysis."""

    ari_matrix: pd.DataFrame
    mean_tda_ari: float
    agreement_interpretation: str


@dataclass
class Phase3Result:
    """Results from Phase 3: Outcome Validation."""

    method_eta_squared: dict[str, dict]  # method -> {outcome -> eta_sq with CI}
    best_method_per_outcome: dict[str, str]
    interpretation: str


@dataclass
class Phase4Result:
    """Results from Phase 4: Boundary Analysis (TDA-specific)."""

    barrier_correlation: float
    barrier_p_value: float
    n_basin_pairs: int
    interpretation: str


@dataclass
class Phase5Result:
    """Results from Phase 5: Stability Analysis."""

    tda_stability: float | None
    dbscan_stability: float | None
    more_stable_method: str
    interpretation: str


@dataclass
class Phase6Result:
    """Results from Phase 6: Regression Comparison."""

    models: dict
    best_model: str
    delta_r2: dict[str, float]
    interpretation: str


@dataclass
class ComparisonReport:
    """Complete comparison protocol results."""

    phase1: Phase1Result
    phase2: Phase2Result
    phase3: Phase3Result | None
    phase4: Phase4Result | None
    phase5: Phase5Result
    phase6: Phase6Result | None
    overall_scenario: str
    recommendations: list[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "phase1": asdict(self.phase1),
            "phase2": {
                "ari_matrix": self.phase2.ari_matrix.to_dict(),
                "mean_tda_ari": self.phase2.mean_tda_ari,
                "interpretation": self.phase2.agreement_interpretation,
            },
            "phase3": asdict(self.phase3) if self.phase3 else None,
            "phase4": asdict(self.phase4) if self.phase4 else None,
            "phase5": asdict(self.phase5),
            "phase6": asdict(self.phase6) if self.phase6 else None,
            "overall_scenario": self.overall_scenario,
            "recommendations": self.recommendations,
        }


# =============================================================================
# MAIN RUNNER
# =============================================================================


class TDAComparisonRunner:
    """
    Orchestrates the complete TDA vs traditional methods comparison.

    Args:
        gdf: GeoDataFrame with LSOA data and TDA basin assignments
        value_column: Column with mobility/deprivation values
        tda_basin_column: Column with TDA basin labels
        output_dir: Directory for results output
    """

    def __init__(
        self,
        gdf,
        value_column: str = "mobility",
        tda_basin_column: str = "tda_basin",
        output_dir: Path | str | None = None,
    ):
        self.gdf = gdf.copy()
        self.value_column = value_column
        self.tda_basin_column = tda_basin_column
        self.output_dir = Path(output_dir) if output_dir else Path(".")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Results storage
        self.phase1_result: Phase1Result | None = None
        self.phase2_result: Phase2Result | None = None
        self.phase3_result: Phase3Result | None = None
        self.phase4_result: Phase4Result | None = None
        self.phase5_result: Phase5Result | None = None
        self.phase6_result: Phase6Result | None = None

        # Method column mapping
        self.method_columns: dict[str, str] = {}

    def run_phase1_baseline(self) -> Phase1Result:
        """
        Phase 1: Apply all clustering/classification methods.

        Returns:
            Phase1Result with method application summary
        """
        logger.info("Phase 1: Baseline Characterization")
        logger.info("-" * 50)

        methods_applied = []
        cluster_counts = {}

        # Check for TDA basins
        if self.tda_basin_column in self.gdf.columns:
            methods_applied.append("TDA (Morse-Smale)")
            n_basins = self.gdf[self.tda_basin_column].nunique()
            cluster_counts["TDA"] = n_basins
            self.method_columns["TDA"] = self.tda_basin_column
            logger.info(f"TDA basins: {n_basins}")

        # Apply LISA
        try:
            self.gdf = compute_lisa_clusters(self.gdf, self.value_column)
            methods_applied.append("LISA")
            cluster_counts["LISA"] = self.gdf["lisa_cluster"].nunique()
            self.method_columns["LISA"] = "lisa_cluster"
            logger.info(f"LISA clusters: {cluster_counts['LISA']}")
        except Exception as e:
            logger.warning(f"LISA failed: {e}")

        # Apply Getis-Ord
        try:
            self.gdf = compute_getis_ord_hotspots(self.gdf, self.value_column)
            methods_applied.append("Getis-Ord")
            cluster_counts["Getis-Ord"] = self.gdf["gi_classification"].nunique()
            self.method_columns["Getis-Ord"] = "gi_classification"
            logger.info(f"Getis-Ord classifications: {cluster_counts['Getis-Ord']}")
        except Exception as e:
            logger.warning(f"Getis-Ord failed: {e}")

        # Apply DBSCAN
        try:
            self.gdf = compute_dbscan_clusters(self.gdf, self.value_column)
            methods_applied.append("DBSCAN")
            n_clusters = self.gdf["dbscan_cluster"].nunique()
            cluster_counts["DBSCAN"] = n_clusters
            self.method_columns["DBSCAN"] = "dbscan_cluster"
            logger.info(f"DBSCAN clusters: {n_clusters}")
        except Exception as e:
            logger.warning(f"DBSCAN failed: {e}")

        # Apply K-means
        try:
            self.gdf = compute_kmeans_clusters(self.gdf, self.value_column)
            methods_applied.append("K-means")
            cluster_counts["K-means"] = self.gdf["kmeans_cluster"].nunique()
            self.method_columns["K-means"] = "kmeans_cluster"
            logger.info(f"K-means clusters: {cluster_counts['K-means']}")
        except Exception as e:
            logger.warning(f"K-means failed: {e}")

        self.phase1_result = Phase1Result(
            n_lsoas=len(self.gdf),
            methods_applied=methods_applied,
            cluster_counts=cluster_counts,
            timestamp=datetime.now().isoformat(),
        )

        return self.phase1_result

    def run_phase2_agreement(
        self,
        n_bootstrap: int = 1000,
    ) -> Phase2Result:
        """
        Phase 2: Compute agreement matrix between methods.

        Args:
            n_bootstrap: Number of bootstrap iterations for CIs

        Returns:
            Phase2Result with ARI matrix and interpretation
        """
        logger.info("\nPhase 2: Agreement Analysis")
        logger.info("-" * 50)

        if not self.method_columns:
            raise ValueError("Run Phase 1 first")

        # Compute full pairwise matrix with CIs
        ari_matrix = compute_full_comparison_matrix(self.gdf, self.method_columns, n_bootstrap=n_bootstrap)

        # Compute mean ARI for TDA vs all others
        if "TDA" in self.method_columns:
            tda_rows = ari_matrix[(ari_matrix["method1"] == "TDA") | (ari_matrix["method2"] == "TDA")]
            mean_tda_ari = tda_rows["ari"].mean()
        else:
            mean_tda_ari = np.nan

        # Interpretation
        if mean_tda_ari > 0.7:
            interpretation = (
                f"STRONG agreement (mean ARI = {mean_tda_ari:.3f}): "
                "TDA finds similar structures to traditional methods. "
                "Value is in rigorous mathematical framework."
            )
        elif mean_tda_ari > 0.4:
            interpretation = (
                f"MODERATE agreement (mean ARI = {mean_tda_ari:.3f}): "
                "TDA and traditional methods share some structure but differ in details."
            )
        else:
            interpretation = (
                f"WEAK agreement (mean ARI = {mean_tda_ari:.3f}): "
                "TDA finds substantially different structures. "
                "Outcome validation (Phase 3) will determine which is more meaningful."
            )

        logger.info(f"Mean TDA ARI: {mean_tda_ari:.3f}")
        logger.info(interpretation)

        self.phase2_result = Phase2Result(
            ari_matrix=ari_matrix,
            mean_tda_ari=mean_tda_ari,
            agreement_interpretation=interpretation,
        )

        return self.phase2_result

    def run_phase3_outcomes(
        self,
        outcome_columns: list[str],
        n_bootstrap: int = 500,
    ) -> Phase3Result:
        """
        Phase 3: Validate clusters against outcome variables.

        Args:
            outcome_columns: List of outcome columns to test
            n_bootstrap: Number of bootstrap iterations for CIs

        Returns:
            Phase3Result with η² for each method/outcome
        """
        logger.info("\nPhase 3: Outcome Validation")
        logger.info("-" * 50)

        if not self.method_columns:
            raise ValueError("Run Phase 1 first")

        method_eta_squared = {}
        best_per_outcome = {}

        for outcome in outcome_columns:
            if outcome not in self.gdf.columns:
                logger.warning(f"Outcome column {outcome} not found, skipping")
                continue

            logger.info(f"\nOutcome: {outcome}")
            method_eta_squared[outcome] = {}
            best_eta = -1
            best_method = None

            for method_name, cluster_col in self.method_columns.items():
                labels = pd.Categorical(self.gdf[cluster_col]).codes
                values = self.gdf[outcome].values

                # Remove NaN
                valid_mask = ~np.isnan(values)
                labels_valid = labels[valid_mask]
                values_valid = values[valid_mask]

                # Bootstrap η²
                result = bootstrap_eta_squared_ci(labels_valid, values_valid, n_bootstrap=n_bootstrap)

                method_eta_squared[outcome][method_name] = {
                    "eta_squared": result.point_estimate,
                    "ci_lower": result.ci_lower,
                    "ci_upper": result.ci_upper,
                    "std_error": result.std_error,
                }

                logger.info(
                    f"  {method_name}: η² = {result.point_estimate:.3f} "
                    f"(95% CI: [{result.ci_lower:.3f}, {result.ci_upper:.3f}])"
                )

                if result.point_estimate > best_eta:
                    best_eta = result.point_estimate
                    best_method = method_name

            best_per_outcome[outcome] = best_method
            logger.info(f"  Best: {best_method}")

        # Interpretation
        tda_wins = sum(1 for v in best_per_outcome.values() if v == "TDA")
        total_outcomes = len(best_per_outcome)

        if tda_wins == total_outcomes:
            interpretation = "TDA outperforms all alternatives for every outcome."
        elif tda_wins > total_outcomes / 2:
            interpretation = f"TDA wins for {tda_wins}/{total_outcomes} outcomes."
        elif tda_wins > 0:
            interpretation = f"TDA wins for {tda_wins}/{total_outcomes} outcomes; others win for rest."
        else:
            interpretation = "Traditional methods outperform TDA for all outcomes."

        self.phase3_result = Phase3Result(
            method_eta_squared=method_eta_squared,
            best_method_per_outcome=best_per_outcome,
            interpretation=interpretation,
        )

        return self.phase3_result

    def run_phase4_boundaries(
        self,
        ms_result,
        outcome_column: str,
    ) -> Phase4Result:
        """
        Phase 4: Test barrier-outcome correlation (TDA-specific).

        Args:
            ms_result: MorseSmaleResult object
            outcome_column: Column with outcome variable

        Returns:
            Phase4Result with correlation and interpretation
        """
        logger.info("\nPhase 4: Boundary Analysis (TDA-Specific)")
        logger.info("-" * 50)

        result = compute_barrier_outcome_correlation(
            ms_result, self.gdf, outcome_column, basin_column=self.tda_basin_column
        )

        logger.info(f"Barrier-outcome correlation: r = {result.pearson_r:.3f}")
        logger.info(f"p-value: {result.p_value:.4f}")
        logger.info(f"Basin pairs analyzed: {result.n_pairs}")
        logger.info(result.interpretation)

        self.phase4_result = Phase4Result(
            barrier_correlation=result.pearson_r,
            barrier_p_value=result.p_value,
            n_basin_pairs=result.n_pairs,
            interpretation=result.interpretation,
        )

        return self.phase4_result

    def run_phase5_stability(self) -> Phase5Result:
        """
        Phase 5: Test parameter stability for methods.

        Returns:
            Phase5Result with stability comparison
        """
        logger.info("\nPhase 5: Stability Analysis")
        logger.info("-" * 50)

        # DBSCAN stability
        dbscan_result = compute_stability_analysis(self.gdf, self.value_column, method="dbscan")
        logger.info(f"DBSCAN stability: {dbscan_result.mean_stability:.3f}")
        logger.info(dbscan_result.interpretation)

        # TDA stability would require re-running Morse-Smale at different thresholds
        # Placeholder for now
        tda_stability = None
        logger.info("TDA stability: requires VTK surface (not implemented)")

        # Compare
        if tda_stability is not None:
            if tda_stability > dbscan_result.mean_stability:
                more_stable = "TDA"
            else:
                more_stable = "DBSCAN"
        else:
            more_stable = "Unknown (TDA stability not computed)"

        interpretation = f"DBSCAN mean stability: {dbscan_result.mean_stability:.3f}. {more_stable} is more stable."

        self.phase5_result = Phase5Result(
            tda_stability=tda_stability,
            dbscan_stability=dbscan_result.mean_stability,
            more_stable_method=more_stable,
            interpretation=interpretation,
        )

        return self.phase5_result

    def run_phase6_regression(
        self,
        outcome_column: str,
        baseline_predictors: list[str],
    ) -> Phase6Result:
        """
        Phase 6: Compare regression models with cluster indicators.

        Args:
            outcome_column: Dependent variable
            baseline_predictors: Baseline predictor columns

        Returns:
            Phase6Result with model comparison
        """
        logger.info("\nPhase 6: Regression Comparison")
        logger.info("-" * 50)

        result = compare_regression_models(self.gdf, outcome_column, baseline_predictors, self.method_columns)

        logger.info(f"Best model (R²): {result.best_model_r2}")
        logger.info(f"Best model (AIC): {result.best_model_aic}")
        logger.info("Model details:")
        for name, metrics in result.models.items():
            logger.info(f"  {name}: R²={metrics['r2']:.3f}, AIC={metrics['aic']:.1f}")
        logger.info(result.interpretation)

        self.phase6_result = Phase6Result(
            models=result.models,
            best_model=result.best_model_r2,
            delta_r2=result.delta_r2_vs_baseline,
            interpretation=result.interpretation,
        )

        return self.phase6_result

    def determine_scenario(self) -> str:
        """
        Determine which of the 4 scenarios best matches results.

        Returns:
            One of: "TDA_REPLICATES", "TDA_ADDS_VALUE", "TDA_ARTIFACTS", "COMPLEMENTARY"
        """
        if self.phase2_result is None:
            return "UNKNOWN"

        high_agreement = self.phase2_result.mean_tda_ari > 0.6

        # Check if TDA adds predictive value
        tda_adds_value = False
        if self.phase3_result:
            tda_wins = sum(1 for v in self.phase3_result.best_method_per_outcome.values() if v == "TDA")
            tda_adds_value = tda_wins > 0

        if high_agreement and not tda_adds_value:
            return "TDA_REPLICATES"
        elif not high_agreement and tda_adds_value:
            return "TDA_ADDS_VALUE"
        elif not high_agreement and not tda_adds_value:
            return "TDA_ARTIFACTS"
        else:
            return "COMPLEMENTARY"

    def generate_recommendations(self, scenario: str) -> list[str]:
        """Generate recommendations based on scenario."""
        recommendations = {
            "TDA_REPLICATES": [
                "TDA provides rigorous mathematical framework but no substantive advantage.",
                "Value is in vocabulary (basins, saddles, separatrices) and formal properties.",
                "Consider using TDA for its unique capabilities (barrier quantification) in follow-up analyses.",
            ],
            "TDA_ADDS_VALUE": [
                "TDA captures structure missed by traditional methods.",
                "This validates the methodological innovation.",
                "Proceed with TDA-based policy analysis with confidence.",
                "Investigate what makes TDA structure outcome-relevant.",
            ],
            "TDA_ARTIFACTS": [
                "TDA structures may be mathematical artifacts rather than real features.",
                "Caution warranted in interpreting TDA results.",
                "Consider whether the surface or filtration is appropriate.",
                "Traditional methods may be more reliable for this application.",
            ],
            "COMPLEMENTARY": [
                "TDA and traditional methods capture different aspects of structure.",
                "Optimal analysis uses both: traditional for significance, TDA for structure.",
                "Basin-stratified analysis recommended for policy applications.",
                "Report both perspectives in publications.",
            ],
            "UNKNOWN": [
                "Insufficient results to determine scenario.",
                "Run all phases before generating recommendations.",
            ],
        }
        return recommendations.get(scenario, ["Unknown scenario"])

    def run_all(
        self,
        outcome_columns: list[str] | None = None,
        baseline_predictors: list[str] | None = None,
        ms_result=None,
        n_bootstrap: int = 1000,
    ) -> ComparisonReport:
        """
        Run complete comparison protocol.

        Args:
            outcome_columns: Columns with outcome variables for Phase 3
            baseline_predictors: Predictors for Phase 6 regression
            ms_result: MorseSmaleResult for Phase 4
            n_bootstrap: Number of bootstrap iterations

        Returns:
            ComparisonReport with all results
        """
        logger.info("=" * 60)
        logger.info("TDA COMPARISON PROTOCOL - FULL RUN")
        logger.info("=" * 60)

        # Phase 1: Baseline
        self.run_phase1_baseline()

        # Phase 2: Agreement
        self.run_phase2_agreement(n_bootstrap=n_bootstrap)

        # Phase 3: Outcomes (if columns provided)
        if outcome_columns:
            self.run_phase3_outcomes(outcome_columns, n_bootstrap=n_bootstrap // 2)

        # Phase 4: Boundaries (if MS result provided)
        if ms_result and outcome_columns:
            self.run_phase4_boundaries(ms_result, outcome_columns[0])

        # Phase 5: Stability
        self.run_phase5_stability()

        # Phase 6: Regression (if predictors provided)
        if outcome_columns and baseline_predictors:
            self.run_phase6_regression(outcome_columns[0], baseline_predictors)

        # Determine scenario and recommendations
        scenario = self.determine_scenario()
        recommendations = self.generate_recommendations(scenario)

        logger.info("\n" + "=" * 60)
        logger.info(f"OVERALL SCENARIO: {scenario}")
        logger.info("=" * 60)
        for rec in recommendations:
            logger.info(f"• {rec}")

        report = ComparisonReport(
            phase1=self.phase1_result,
            phase2=self.phase2_result,
            phase3=self.phase3_result,
            phase4=self.phase4_result,
            phase5=self.phase5_result,
            phase6=self.phase6_result,
            overall_scenario=scenario,
            recommendations=recommendations,
        )

        return report

    def save_report(self, report: ComparisonReport, filename: str = "comparison_report.json") -> Path:
        """Save report to JSON file."""
        output_path = self.output_dir / filename
        with open(output_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2, default=str)
        logger.info(f"Report saved to {output_path}")
        return output_path

    def generate_markdown_report(self, report: ComparisonReport) -> str:
        """Generate markdown-formatted report."""
        lines = [
            "# TDA Comparison Protocol Results",
            "",
            f"**Generated:** {report.phase1.timestamp}",
            f"**LSOAs analyzed:** {report.phase1.n_lsoas}",
            "",
            "## Phase 1: Method Application",
            "",
            "| Method | Clusters |",
            "|--------|----------|",
        ]

        for method, count in report.phase1.cluster_counts.items():
            lines.append(f"| {method} | {count} |")

        lines.extend(
            [
                "",
                "## Phase 2: Agreement Analysis",
                "",
                f"**Mean TDA ARI:** {report.phase2.mean_tda_ari:.3f}",
                "",
                f"**Interpretation:** {report.phase2.agreement_interpretation}",
                "",
                "### ARI Matrix",
                "",
                report.phase2.ari_matrix.to_markdown()
                if hasattr(report.phase2.ari_matrix, "to_markdown")
                else str(report.phase2.ari_matrix),
            ]
        )

        if report.phase3:
            lines.extend(
                [
                    "",
                    "## Phase 3: Outcome Validation",
                    "",
                    f"**Interpretation:** {report.phase3.interpretation}",
                ]
            )

        if report.phase4:
            lines.extend(
                [
                    "",
                    "## Phase 4: Boundary Analysis",
                    "",
                    f"**Barrier-outcome correlation:** r = {report.phase4.barrier_correlation:.3f} (p = {report.phase4.barrier_p_value:.4f})",
                    "",
                    f"**Interpretation:** {report.phase4.interpretation}",
                ]
            )

        lines.extend(
            [
                "",
                "## Phase 5: Stability Analysis",
                "",
                f"**Interpretation:** {report.phase5.interpretation}",
            ]
        )

        if report.phase6:
            lines.extend(
                [
                    "",
                    "## Phase 6: Regression Comparison",
                    "",
                    f"**Best model:** {report.phase6.best_model}",
                    "",
                    f"**Interpretation:** {report.phase6.interpretation}",
                ]
            )

        lines.extend(
            [
                "",
                "## Overall Assessment",
                "",
                f"**Scenario:** {report.overall_scenario}",
                "",
                "### Recommendations",
                "",
            ]
        )

        for rec in report.recommendations:
            lines.append(f"- {rec}")

        return "\n".join(lines)


# =============================================================================
# CLI INTERFACE
# =============================================================================


def main():
    """Command-line interface for comparison runner."""
    parser = argparse.ArgumentParser(description="Run TDA comparison protocol")
    parser.add_argument("--gdf-path", required=True, help="Path to GeoDataFrame pickle or GeoJSON")
    parser.add_argument(
        "--value-column",
        default="mobility",
        help="Column with mobility/deprivation values",
    )
    parser.add_argument("--basin-column", default="tda_basin", help="Column with TDA basin labels")
    parser.add_argument("--outcome-columns", nargs="+", help="Columns with outcome variables")
    parser.add_argument("--output-dir", default="./comparison_results", help="Output directory")
    parser.add_argument("--n-bootstrap", type=int, default=1000, help="Number of bootstrap iterations")
    parser.add_argument(
        "--allow-pickle",
        action="store_true",
        default=False,
        help="Allow loading pickle files (security risk; use GeoJSON or Parquet instead)",
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Load data
    import geopandas as gpd

    gdf_path = Path(args.gdf_path)
    if gdf_path.suffix == ".pkl":
        if args.allow_pickle:
            logger.warning("Loading pickle files is a security risk. Consider using GeoJSON or Parquet.")
            gdf = pd.read_pickle(gdf_path)
        else:
            error_msg = (
                f"Pickle files are not allowed by default due to security risks. "
                f"To load '{gdf_path}', pass the --allow-pickle flag. "
                f"Recommended: convert to GeoJSON or Parquet format."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
    elif gdf_path.suffix == ".parquet":
        gdf = gpd.read_parquet(gdf_path)
    else:
        gdf = gpd.read_file(gdf_path)
    # Run comparison
    runner = TDAComparisonRunner(
        gdf,
        value_column=args.value_column,
        tda_basin_column=args.basin_column,
        output_dir=args.output_dir,
    )

    report = runner.run_all(outcome_columns=args.outcome_columns, n_bootstrap=args.n_bootstrap)

    # Save results
    runner.save_report(report)

    md_report = runner.generate_markdown_report(report)
    md_path = Path(args.output_dir) / "comparison_report.md"
    md_path.write_text(md_report)
    logger.info(f"Markdown report saved to {md_path}")


if __name__ == "__main__":
    main()
