"""
Deep Dive Analysis: Understanding Tau Discrepancies and COVID Differences.

This script investigates:
1. Why our τ values differ from G&K paper (0.92 vs 1.00 for 2008)
2. Parameter sensitivity analysis
3. What specifically differs in COVID crash structure
4. Whether differences are methodological or reflect real signal differences

Scientific rigor: Don't accept results, understand causes.
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import kendalltau

from financial_tda.validation.trend_analysis_validator import (
    compute_gk_rolling_statistics,
    load_lp_norms_from_csv,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

OUTPUTS_DIR = Path(__file__).parent / "outputs"
FIGURES_DIR = Path(__file__).parent / "figures"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

def analyze_parameter_sensitivity(
    norms_df: pd.DataFrame,
    crisis_date: str,
    event_name: str,
) -> pd.DataFrame:
    """
    Test sensitivity to rolling window and precrash window sizes.

    G&K uses: rolling=500, precrash=250
    Test variations to understand parameter impact.
    """
    logger.info(f"\n{'=' * 80}")
    logger.info(f"PARAMETER SENSITIVITY ANALYSIS: {event_name}")
    logger.info(f"{'=' * 80}")

    crisis_dt = pd.to_datetime(crisis_date)
    if isinstance(norms_df.index, pd.DatetimeIndex) and norms_df.index.tz is not None and crisis_dt.tz is None:
        crisis_dt = crisis_dt.tz_localize(norms_df.index.tz)

    # Test different parameter combinations
    rolling_windows = [400, 450, 500, 550, 600]
    precrash_windows = [200, 225, 250, 275, 300]

    results = []

    for rolling_win in rolling_windows:
        for precrash_win in precrash_windows:
            # Compute rolling stats
            stats_df = compute_gk_rolling_statistics(norms_df, window_size=rolling_win)

            # Extract pre-crisis window
            pre_crisis_mask = stats_df.index < crisis_dt
            pre_crisis_data = stats_df[pre_crisis_mask].tail(precrash_win)

            if len(pre_crisis_data) < 100:  # Need sufficient data
                continue

            time_index = np.arange(len(pre_crisis_data))

            # Compute tau for each metric
            for col in [
                "L1_norm_variance",
                "L1_norm_spectral_density_low",
                "L2_norm_variance",
                "L2_norm_spectral_density_low",
            ]:
                series = pre_crisis_data[col].dropna()
                if len(series) < 50:
                    continue

                tau, p_value = kendalltau(time_index[: len(series)], series.values)

                results.append(
                    {
                        "rolling_window": rolling_win,
                        "precrash_window": precrash_win,
                        "metric": col,
                        "tau": tau,
                        "p_value": p_value,
                        "n_samples": len(series),
                    }
                )

    results_df = pd.DataFrame(results)

    # Show results for G&K standard parameters
    gk_params = results_df[(results_df["rolling_window"] == 500) & (results_df["precrash_window"] == 250)]

    logger.info("\nG&K Standard Parameters (rolling=500, precrash=250):")
    for _, row in gk_params.iterrows():
        logger.info(f"  {row['metric']:40s} τ={row['tau']:.4f}")

    # Show best parameters for each metric
    logger.info("\nBest Parameters by Metric:")
    for metric in results_df["metric"].unique():
        metric_data = results_df[results_df["metric"] == metric]
        best = metric_data.loc[metric_data["tau"].abs().idxmax()]
        logger.info(
            f"  {metric:40s} τ={best['tau']:.4f} (rolling={int(best['rolling_window'])}, precrash={int(best['precrash_window'])})"
        )

    return results_df


def compare_metric_behaviors(
    event_dfs: dict[str, pd.DataFrame],
    crisis_dates: dict[str, str],
) -> None:
    """
    Compare how different metrics behave across events.

    Understanding: Do L1 vs L2, variance vs spectral density show
    different patterns for 2008/2000 vs COVID?
    """
    logger.info(f"\n{'=' * 80}")
    logger.info("CROSS-EVENT METRIC COMPARISON")
    logger.info(f"{'=' * 80}")

    fig, axes = plt.subplots(3, 2, figsize=(16, 12))
    fig.suptitle(
        "Rolling Statistics Comparison: 2008 GFC vs 2000 Dotcom vs 2020 COVID",
        fontsize=14,
        fontweight="bold",
    )

    metrics = [
        ("L1_norm_variance", "L¹ Variance"),
        ("L2_norm_variance", "L² Variance"),
        ("L1_norm_spectral_density_low", "L¹ Spectral Density"),
        ("L2_norm_spectral_density_low", "L² Spectral Density"),
        ("L1_norm_acf_lag1", "L¹ ACF lag-1"),
        ("L2_norm_acf_lag1", "L² ACF lag-1"),
    ]

    for idx, (metric, label) in enumerate(metrics):
        ax = axes[idx // 2, idx % 2]

        for event_name, norms_df in event_dfs.items():
            crisis_date = pd.to_datetime(crisis_dates[event_name])
            if (
                isinstance(norms_df.index, pd.DatetimeIndex)
                and norms_df.index.tz is not None
                and crisis_date.tz is None
            ):
                crisis_date = crisis_date.tz_localize(norms_df.index.tz)

            # Compute rolling stats
            stats_df = compute_gk_rolling_statistics(norms_df, window_size=500)

            # Extract 250-day pre-crisis window
            pre_crisis_mask = stats_df.index < crisis_date
            pre_crisis_data = stats_df[pre_crisis_mask].tail(250)

            if metric in pre_crisis_data.columns:
                series = pre_crisis_data[metric].dropna()
                if len(series) > 10:
                    # Normalize to [0, 1] for comparison
                    normalized = (series - series.min()) / (series.max() - series.min() + 1e-10)

                    # Compute tau
                    time_idx = np.arange(len(normalized))
                    tau, _ = kendalltau(time_idx, normalized.values)

                    ax.plot(
                        normalized.values,
                        label=f"{event_name} (τ={tau:.2f})",
                        alpha=0.7,
                        linewidth=2,
                    )

        ax.set_title(label, fontsize=11, fontweight="bold")
        ax.set_xlabel("Days Before Crisis", fontsize=9)
        ax.set_ylabel("Normalized Value", fontsize=9)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "cross_event_metric_comparison.png", dpi=300, bbox_inches="tight")
    plt.close()

    logger.info(f"\n✓ Saved cross-event comparison to {FIGURES_DIR / 'cross_event_metric_comparison.png'}")


def analyze_covid_specifics(
    covid_norms: pd.DataFrame,
    gfc_norms: pd.DataFrame,
) -> None:
    """
    Deep dive into what's different about COVID structure.

    Compare:
    - Signal volatility
    - Trend linearity
    - Noise characteristics
    - Time scale differences
    """
    logger.info(f"\n{'=' * 80}")
    logger.info("COVID-SPECIFIC ANALYSIS")
    logger.info(f"{'=' * 80}")

    covid_stats = compute_gk_rolling_statistics(covid_norms, window_size=500)
    gfc_stats = compute_gk_rolling_statistics(gfc_norms, window_size=500)

    # Extract pre-crisis windows
    covid_date = pd.to_datetime("2020-03-16")
    gfc_date = pd.to_datetime("2008-09-15")

    if isinstance(covid_norms.index, pd.DatetimeIndex) and covid_norms.index.tz is not None:
        covid_date = covid_date.tz_localize(covid_norms.index.tz)
    if isinstance(gfc_norms.index, pd.DatetimeIndex) and gfc_norms.index.tz is not None:
        gfc_date = gfc_date.tz_localize(gfc_norms.index.tz)

    covid_window = covid_stats[covid_stats.index < covid_date].tail(250)
    gfc_window = gfc_stats[gfc_stats.index < gfc_date].tail(250)

    # Analyze L2 variance (best performer for both)
    metric = "L2_norm_variance"

    covid_series = covid_window[metric].dropna()
    gfc_series = gfc_window[metric].dropna()

    logger.info("\nComparing L² Variance:")
    logger.info("  2020 COVID:")
    logger.info(f"    Mean: {covid_series.mean():.6f}")
    logger.info(f"    Std:  {covid_series.std():.6f}")
    logger.info(f"    CV:   {covid_series.std() / covid_series.mean():.4f}")
    logger.info(f"    Range: [{covid_series.min():.6f}, {covid_series.max():.6f}]")

    logger.info("  2008 GFC:")
    logger.info(f"    Mean: {gfc_series.mean():.6f}")
    logger.info(f"    Std:  {gfc_series.std():.6f}")
    logger.info(f"    CV:   {gfc_series.std() / gfc_series.mean():.4f}")
    logger.info(f"    Range: [{gfc_series.min():.6f}, {gfc_series.max():.6f}]")

    # Compute tau
    covid_tau, _ = kendalltau(np.arange(len(covid_series)), covid_series.values)
    gfc_tau, _ = kendalltau(np.arange(len(gfc_series)), gfc_series.values)

    logger.info("\n  Kendall-tau:")
    logger.info(f"    COVID: {covid_tau:.4f}")
    logger.info(f"    GFC:   {gfc_tau:.4f}")
    logger.info(f"    Difference: {abs(gfc_tau - covid_tau):.4f}")

    # Analyze trend linearity using R² from linear fit
    from sklearn.linear_model import LinearRegression

    def compute_linearity(series):
        X = np.arange(len(series)).reshape(-1, 1)
        y = series.values
        model = LinearRegression().fit(X, y)
        r2 = model.score(X, y)
        return r2, model.coef_[0]

    covid_r2, covid_slope = compute_linearity(covid_series)
    gfc_r2, gfc_slope = compute_linearity(gfc_series)

    logger.info("\n  Trend Linearity (R²):")
    logger.info(f"    COVID: {covid_r2:.4f} (slope={covid_slope:.8f})")
    logger.info(f"    GFC:   {gfc_r2:.4f} (slope={gfc_slope:.8f})")

    # Analyze noise/residuals
    covid_residuals = covid_series.values - LinearRegression().fit(
        np.arange(len(covid_series)).reshape(-1, 1), covid_series.values
    ).predict(np.arange(len(covid_series)).reshape(-1, 1))

    gfc_residuals = gfc_series.values - LinearRegression().fit(
        np.arange(len(gfc_series)).reshape(-1, 1), gfc_series.values
    ).predict(np.arange(len(gfc_series)).reshape(-1, 1))

    logger.info("\n  Residual Noise:")
    logger.info(f"    COVID std: {covid_residuals.std():.8f}")
    logger.info(f"    GFC std:   {gfc_residuals.std():.8f}")
    logger.info(f"    Ratio:     {covid_residuals.std() / gfc_residuals.std():.2f}x")

    # Visualize
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("COVID vs GFC: Signal Structure Analysis", fontsize=14, fontweight="bold")

    # Panel 1: Raw signals
    ax = axes[0, 0]
    ax.plot(covid_series.values, label="COVID", color="red", alpha=0.7, linewidth=2)
    ax.plot(gfc_series.values, label="GFC", color="blue", alpha=0.7, linewidth=2)
    ax.set_title("L² Variance (Raw)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Days Before Crisis")
    ax.legend()
    ax.grid(alpha=0.3)

    # Panel 2: Normalized signals
    ax = axes[0, 1]
    covid_norm = (covid_series - covid_series.min()) / (covid_series.max() - covid_series.min())
    gfc_norm = (gfc_series - gfc_series.min()) / (gfc_series.max() - gfc_series.min())
    ax.plot(
        covid_norm.values,
        label=f"COVID (τ={covid_tau:.3f})",
        color="red",
        alpha=0.7,
        linewidth=2,
    )
    ax.plot(
        gfc_norm.values,
        label=f"GFC (τ={gfc_tau:.3f})",
        color="blue",
        alpha=0.7,
        linewidth=2,
    )
    ax.set_title("Normalized [0,1]", fontsize=11, fontweight="bold")
    ax.set_xlabel("Days Before Crisis")
    ax.legend()
    ax.grid(alpha=0.3)

    # Panel 3: Detrended (residuals)
    ax = axes[1, 0]
    ax.plot(covid_residuals, label="COVID residuals", color="red", alpha=0.5)
    ax.plot(gfc_residuals, label="GFC residuals", color="blue", alpha=0.5)
    ax.axhline(0, color="black", linestyle="--", linewidth=1)
    ax.set_title("Detrended (Residuals)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Days Before Crisis")
    ax.legend()
    ax.grid(alpha=0.3)

    # Panel 4: Autocorrelation
    ax = axes[1, 1]
    ax.acorr(covid_series.values, maxlags=50, label="COVID", color="red", alpha=0.7)
    ax.acorr(gfc_series.values, maxlags=50, label="GFC", color="blue", alpha=0.7)
    ax.set_title("Autocorrelation", fontsize=11, fontweight="bold")
    ax.set_xlabel("Lag (days)")
    ax.set_ylabel("ACF")
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "covid_vs_gfc_signal_analysis.png", dpi=300, bbox_inches="tight")
    plt.close()

    logger.info(f"\n✓ Saved signal analysis to {FIGURES_DIR / 'covid_vs_gfc_signal_analysis.png'}")

    # Summary
    logger.info(f"\n{'=' * 80}")
    logger.info("KEY FINDINGS:")
    logger.info(f"{'=' * 80}")
    if covid_tau != 0:
        logger.info(f"1. Trend Strength: GFC has {gfc_tau / covid_tau:.2f}x stronger tau")
    else:
        logger.info(f"1. Trend Strength: GFC tau={gfc_tau:.4f}, COVID tau=0")
    logger.info(f"2. Linearity: GFC more linear (R²={gfc_r2:.3f} vs {covid_r2:.3f})")
    logger.info(f"3. Noise: COVID has {covid_residuals.std() / gfc_residuals.std():.2f}x more noise")
    logger.info("4. Signal Quality: GFC shows clearer monotonic buildup")


def main():
    """Execute comprehensive analysis."""

    logger.info("\n" + "=" * 80)
    logger.info("DEEP DIVE: TAU DISCREPANCIES & COVID DIFFERENCES")
    logger.info("=" * 80)

    # Load all events
    logger.info("\nLoading event data...")
    gfc_norms_raw = load_lp_norms_from_csv(OUTPUTS_DIR / "2008_gfc_lp_norms.csv")
    dotcom_norms_raw = load_lp_norms_from_csv(OUTPUTS_DIR / "2000_dotcom_lp_norms.csv")
    covid_norms_raw = load_lp_norms_from_csv(OUTPUTS_DIR / "2020_covid_lp_norms.csv")

    # Create copies and remove timezone to avoid conversion issues (data is already properly ordered)
    # Operating on copies to avoid mutating original DataFrames
    gfc_norms = gfc_norms_raw.copy()
    dotcom_norms = dotcom_norms_raw.copy()
    covid_norms = covid_norms_raw.copy()

    for df in [gfc_norms, dotcom_norms, covid_norms]:
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_localize(None)

    event_dfs = {
        "2008 GFC": gfc_norms,
        "2000 Dotcom": dotcom_norms,
        "2020 COVID": covid_norms,
    }

    crisis_dates = {
        "2008 GFC": "2008-09-15",
        "2000 Dotcom": "2000-03-10",
        "2020 COVID": "2020-03-16",
    }

    # Analysis 1: Parameter sensitivity
    logger.info("\n" + "=" * 80)
    logger.info("ANALYSIS 1: PARAMETER SENSITIVITY")
    logger.info("=" * 80)

    for event_name, norms_df in event_dfs.items():
        results_df = analyze_parameter_sensitivity(norms_df, crisis_dates[event_name], event_name)
        results_df.to_csv(OUTPUTS_DIR / f"{event_name.lower().replace(' ', '_')}_parameter_sensitivity.csv")

    # Analysis 2: Cross-event metric comparison
    logger.info("\n" + "=" * 80)
    logger.info("ANALYSIS 2: CROSS-EVENT METRIC COMPARISON")
    logger.info("=" * 80)
    compare_metric_behaviors(event_dfs, crisis_dates)

    # Analysis 3: COVID-specific deep dive
    logger.info("\n" + "=" * 80)
    logger.info("ANALYSIS 3: COVID SIGNAL STRUCTURE")
    logger.info("=" * 80)
    analyze_covid_specifics(covid_norms, gfc_norms)

    logger.info("\n" + "=" * 80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 80)
    logger.info("\nNext Steps:")
    logger.info("1. Review parameter sensitivity results")
    logger.info("2. Examine cross-event visualizations")
    logger.info("3. Understand COVID signal differences")
    logger.info("4. Determine if G&K tau difference is methodological or real")


if __name__ == "__main__":
    main()
