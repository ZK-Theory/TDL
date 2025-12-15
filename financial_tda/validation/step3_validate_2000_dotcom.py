"""
Step 3: 2000 Dotcom Crash Validation using G&K Methodology.

Applies the complete Gidea & Katz (2018) trend detection methodology to validate
the 2000 Dotcom Crash (NASDAQ peak: March 10, 2000).

Expected Result: τ ≈ 0.89 (per G&K paper Table 1)
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from financial_tda.validation.gidea_katz_replication import (
    compute_persistence_landscape_norms,
    fetch_historical_data,
)
from financial_tda.validation.trend_analysis_validator import (
    compute_gk_rolling_statistics,
    validate_gk_event,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Output directories
OUTPUTS_DIR = Path(__file__).parent / "outputs"
FIGURES_DIR = Path(__file__).parent / "figures"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def create_gk_visualization(
    norms_df: pd.DataFrame,
    stats_df: pd.DataFrame,
    result: dict,
    output_path: Path,
) -> None:
    """Create comprehensive G&K validation visualization."""
    crisis_date = pd.to_datetime(result["crisis_date"])

    # Handle timezone
    if norms_df.index.tz is not None and crisis_date.tz is None:
        crisis_date = crisis_date.tz_localize(norms_df.index.tz)

    # Extract pre-crisis window
    window_start = pd.to_datetime(result["window_start"])
    window_end = pd.to_datetime(result["window_end"])

    if norms_df.index.tz is not None:
        window_start = window_start.tz_localize(norms_df.index.tz)
        window_end = window_end.tz_localize(norms_df.index.tz)

    window_mask = (norms_df.index >= window_start) & (norms_df.index <= window_end)
    norms_window = norms_df[window_mask]
    stats_window = stats_df.reindex(norms_window.index)

    # Create 4-panel figure
    fig, axes = plt.subplots(4, 1, figsize=(16, 14))

    # Panel 1: L^p norms
    ax = axes[0]
    ax.plot(
        norms_window.index,
        norms_window["L1_norm"],
        label="L¹ Norm",
        color="steelblue",
        linewidth=1.5,
        alpha=0.8,
    )
    ax.plot(
        norms_window.index,
        norms_window["L2_norm"],
        label="L² Norm",
        color="darkorange",
        linewidth=1.5,
        alpha=0.8,
    )
    ax.axvline(
        crisis_date,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Peak: {crisis_date.date()}",
    )
    ax.set_ylabel("L^p Norm", fontsize=11, fontweight="bold")
    ax.set_title(
        "2000 Dotcom Crash: Persistence Landscape L^p Norms (250-day Pre-Crisis Window)",
        fontsize=13,
        fontweight="bold",
    )
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(alpha=0.3)

    # Panel 2: Variance
    ax = axes[1]
    var_col = "L2_norm_variance"
    if var_col in stats_window.columns:
        variance_data = stats_window[var_col].dropna()
        ax.plot(
            variance_data.index,
            variance_data,
            color="darkgreen",
            linewidth=2,
            label="L² Variance (500-day rolling)",
        )

        if len(variance_data) > 10:
            from scipy.stats import theilslopes

            time_idx = np.arange(len(variance_data))
            slope, intercept, _, _ = theilslopes(variance_data.values, time_idx)
            trend = slope * time_idx + intercept

            tau = result["statistics"].get(var_col, {}).get("tau", 0)
            ax.plot(
                variance_data.index,
                trend,
                color="darkred",
                linestyle="--",
                linewidth=2.5,
                label=f"Trend (τ={tau:.3f})",
            )

    ax.axvline(crisis_date, color="red", linestyle="--", linewidth=2)
    ax.set_ylabel("Variance", fontsize=11, fontweight="bold")
    ax.set_title("Rolling Variance (G&K Statistic)", fontsize=12, fontweight="bold")
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(alpha=0.3)

    # Panel 3: Spectral density
    ax = axes[2]
    spec_col = "L2_norm_spectral_density_low"
    if spec_col in stats_window.columns:
        spec_data = stats_window[spec_col].dropna()
        ax.plot(
            spec_data.index,
            spec_data,
            color="darkblue",
            linewidth=2,
            label="L² Spectral Density (500-day rolling)",
        )

        if len(spec_data) > 10:
            from scipy.stats import theilslopes

            time_idx = np.arange(len(spec_data))
            slope, intercept, _, _ = theilslopes(spec_data.values, time_idx)
            trend = slope * time_idx + intercept

            tau = result["statistics"].get(spec_col, {}).get("tau", 0)
            ax.plot(
                spec_data.index,
                trend,
                color="purple",
                linestyle="--",
                linewidth=2.5,
                label=f"Trend (τ={tau:.3f})",
            )

    ax.axvline(crisis_date, color="red", linestyle="--", linewidth=2)
    ax.set_ylabel("Spectral Density", fontsize=11, fontweight="bold")
    ax.set_title(
        "Rolling Spectral Density (Low Freq) - G&K Primary Metric",
        fontsize=12,
        fontweight="bold",
    )
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(alpha=0.3)

    # Panel 4: Summary
    ax = axes[3]
    ax.axis("off")

    summary_text = f"""
VALIDATION RESULTS: 2000 DOTCOM CRASH

Event: {result["event_name"]}
Crisis Date: {result["crisis_date"]}
Analysis Window: {result["window_start"]} to {result["window_end"]} ({result["n_observations"]} days)

KENDALL-TAU RESULTS (Sorted by |τ|):
"""

    stats_sorted = sorted(result["statistics"].items(), key=lambda x: abs(x[1]["tau"]), reverse=True)

    for stat_name, values in stats_sorted[:6]:
        tau = values["tau"]
        p_val = values["p_value"]
        marker = "✓" if abs(tau) >= 0.70 else " "
        summary_text += f"\n{marker} {stat_name:40s} τ={tau:7.4f}  p={p_val:.2e}"

    summary_text += f"""

BEST METRIC: {result["best_metric"]}
BEST TAU: {result["best_tau"]:.4f}
THRESHOLD: τ ≥ {result["tau_threshold"]}
STATUS: {result["status"]}

COMPARISON TO G&K (2018):
Expected: τ ≈ 0.89 for 2000 dotcom crash
Our Result: τ = {result["best_tau"]:.4f}
"""

    if result["status"] == "PASS":
        summary_text += "\n✓ VALIDATION SUCCESS: Strong pre-crisis trend detected"
    else:
        summary_text += "\n⚠ VALIDATION PARTIAL: Weaker than expected trend"

    ax.text(
        0.05,
        0.95,
        summary_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        family="monospace",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.3),
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    logger.info(f"✓ Saved visualization to {output_path}")


def generate_validation_report(result: dict, output_path: Path) -> None:
    """Generate markdown validation report for 2000 dotcom crash."""

    stats_sorted = sorted(result["statistics"].items(), key=lambda x: abs(x[1]["tau"]), reverse=True)

    stats_table = "| Metric | Kendall-tau (τ) | P-value | N | Status |\n"
    stats_table += "|--------|-----------------|---------|---|--------|\n"

    for stat_name, values in stats_sorted:
        tau = values["tau"]
        p_val = values["p_value"]
        n = values["n_samples"]
        status = "✓ PASS" if abs(tau) >= 0.70 else ""
        stats_table += f"| {stat_name} | {tau:.4f} | {p_val:.2e} | {n} | {status} |\n"

    report = f"""# 2000 Dotcom Crash Validation Report: G&K Methodology

## Executive Summary

**Event**: {result["event_name"]}  
**Crisis Date**: {result["crisis_date"]} (NASDAQ peak)  
**Validation Status**: **{result["status"]}**  
**Best Kendall-tau**: **{result["best_tau"]:.4f}** ({result["best_metric"]})

This report validates the 2000 Dotcom Crash using the complete Gidea & Katz (2018) trend detection methodology.

---

## Methodology: Complete G&K (2018) Approach

### Three-Stage Pipeline

1. **L^p Norm Computation**
   - 50-day sliding windows over 4 US indices
   - Vietoris-Rips persistence (H₁ homology)
   - Persistence landscapes → L¹ and L² norms

2. **Rolling Statistics** (500-day windows)
   - Variance
   - Spectral density at low frequencies (PRIMARY METRIC)
   - ACF lag-1

3. **Kendall-Tau Trend Analysis** (250-day pre-crisis window)
   - Measures monotonic trend strength
   - τ ≈ +1: Strong upward trend (pre-crisis signal)

---

## Results: 2000 Dotcom Crash

### Analysis Parameters

- **Crisis Date**: {result["crisis_date"]}
- **Analysis Window**: {result["window_start"]} to {result["window_end"]}
- **Observations**: {result["n_observations"]} trading days
- **Rolling Window**: {result["rolling_window_size"]} days
- **Pre-crisis Window**: {result["precrash_window_size"]} days

### Kendall-Tau Results (All 6 G&K Statistics)

{stats_table}

### Best Performing Metric

- **Metric**: {result["best_metric"]}
- **Kendall-tau**: {result["best_tau"]:.4f}
- **Interpretation**: {
        "Strong upward trend detected"
        if result["best_tau"] >= 0.70
        else "Moderate trend detected"
    }

---

## Comparison to Gidea & Katz (2018)

| Aspect | G&K Paper (2018) | Our Validation |
|--------|------------------|----------------|
| **2000 Dotcom Crash** | τ ≈ 0.89 (spectral density) | τ = {result["best_tau"]:.4f} ({
        result["best_metric"]
    }) |
| **Methodology** | Complete (rolling stats) | Complete (rolling stats) |
| **Success Threshold** | τ ≥ 0.70 | τ ≥ 0.70 |
| **Status** | PASS | {result["status"]} |

### Key Findings

{
        f"✓ **VALIDATION SUCCESS**: Our result (τ = {result['best_tau']:.4f}) matches G&K expectations (τ ≈ 0.89)"
        if result["status"] == "PASS"
        else f"⚠ **PARTIAL VALIDATION**: Our result (τ = {result['best_tau']:.4f}) is below G&K expectations"
    }

The complete G&K methodology {
        "successfully detects"
        if result["status"] == "PASS"
        else "shows moderate signals for"
    } pre-crisis trends for the 2000 dotcom crash.

---

## Visualizations

See [2000_dotcom_validation_complete.png](figures/2000_dotcom_validation_complete.png) for:
1. Raw L^p norms time series
2. Rolling variance with Kendall-tau trend line
3. Rolling spectral density (primary G&K metric)
4. Summary statistics panel

---

## Validation Status: {result["status"]}

{
        f'''✓ **SUCCESS**

The G&K methodology successfully identifies pre-crisis signals for the 2000 dotcom crash:
- Best metric: {result['best_metric']} (τ = {result['best_tau']:.4f})
- Exceeds threshold: τ = {result['best_tau']:.4f} ≥ 0.70
- Matches G&K paper expectations

**Conclusion**: The TDA implementation validates correctly for the 2000 dotcom crash.
'''
        if result["status"] == "PASS"
        else f'''⚠ **PARTIAL VALIDATION**

The G&K methodology shows weaker signals for 2000 dotcom:
- Best metric: {result['best_metric']} (τ = {result['best_tau']:.4f})
- Below threshold: τ = {result['best_tau']:.4f} < 0.70

**Note**: This may reflect differences in:
- Data sources (Yahoo Finance vs. original G&K data)
- Crisis nature (tech bubble vs. systemic financial crisis)
- Parameter sensitivity
'''
    }

---

## References

- Gidea, M., & Katz, Y. (2018). Topological data analysis of financial time series: Landscapes of crashes. *Physica A: Statistical Mechanics and its Applications*, 491, 820-834.
"""

    output_path.write_text(report, encoding="utf-8")
    logger.info(f"✓ Saved validation report to {output_path}")


def run_2000_dotcom_validation():
    """Execute complete 2000 dotcom crash validation."""

    logger.info("\n" + "=" * 80)
    logger.info("STEP 3: 2000 DOTCOM CRASH VALIDATION (G&K METHODOLOGY)")
    logger.info("=" * 80)

    # Step 1: Fetch data
    logger.info("\n[1/5] Fetching historical data...")
    # Need ~750 days before crisis (500 rolling + 250 analysis)
    # Crisis: 2000-03-10, so need data from ~1997
    prices = fetch_historical_data("1997-01-01", "2001-12-31")
    logger.info(f"      ✓ Fetched {len(prices)} indices")

    # Step 2: Compute L^p norms
    logger.info("\n[2/5] Computing persistence landscape L^p norms...")
    norms_df = compute_persistence_landscape_norms(prices, window_size=50, stride=1, n_layers=5)
    logger.info(f"      ✓ Computed {len(norms_df)} norm observations")

    # Save norms
    norms_file = OUTPUTS_DIR / "2000_dotcom_lp_norms.csv"
    norms_df.to_csv(norms_file)
    logger.info(f"      ✓ Saved to {norms_file}")

    # Step 3: Apply G&K methodology
    logger.info("\n[3/5] Applying G&K methodology (rolling stats + Kendall-tau)...")
    result = validate_gk_event(
        norms_df,
        event_name="2000 Dotcom Crash",
        crisis_date="2000-03-10",  # NASDAQ peak
        rolling_window=500,
        precrash_window=250,
    )
    logger.info(f"      ✓ Status: {result['status']}")
    logger.info(f"      ✓ Best tau: {result['best_tau']:.4f} ({result['best_metric']})")

    # Step 4: Generate visualization
    logger.info("\n[4/5] Creating visualization...")
    stats_df = compute_gk_rolling_statistics(norms_df, window_size=500)
    create_gk_visualization(norms_df, stats_df, result, FIGURES_DIR / "2000_dotcom_validation_complete.png")

    # Step 5: Generate report
    logger.info("\n[5/5] Generating validation report...")
    generate_validation_report(result, Path(__file__).parent / "2000_dotcom_validation.md")

    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("STEP 3 COMPLETE: 2000 DOTCOM CRASH VALIDATION")
    logger.info("=" * 80)
    logger.info(f"Status: {result['status']}")
    logger.info(f"Best Metric: {result['best_metric']}")
    logger.info(f"Kendall-tau: {result['best_tau']:.4f}")
    logger.info(f"Threshold: ≥ {result['tau_threshold']}")
    logger.info("=" * 80)

    return result


if __name__ == "__main__":
    result = run_2000_dotcom_validation()
