"""
Real-Time Crisis Detection Analysis: 2023-2025 Market Data
===========================================================

Applies validated Gidea & Katz (2018) TDA methodology to recent market data
to detect potential pre-crisis warning signals.

This script:
1. Fetches market data from 2022-present
2. Computes L^p persistence landscape norms
3. Runs rolling window analysis with parameter grid
4. Compares to historical pre-crisis periods
5. Performs temporal and sector analysis
6. Generates comprehensive visualizations and report
"""

import os
from datetime import datetime

import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import kendalltau, theilslopes

# Add project root to path
from financial_tda.data.fetchers.yahoo import fetch_ticker
from financial_tda.validation.gidea_katz_replication import (
    compute_persistence_landscape_norms,
    fetch_historical_data,
)
from financial_tda.validation.trend_analysis_validator import (
    compute_gk_rolling_statistics,
    load_lp_norms_from_csv,
)

# Set style
sns.set_style("whitegrid")
plt.rcParams["figure.dpi"] = 300


def ensure_output_dirs():
    """Create output directories if they don't exist."""
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("figures", exist_ok=True)


def step1_fetch_and_compute_norms():
    """
    Step 1: Fetch recent market data and compute L^p norms.

    Returns:
        pd.DataFrame: L^p norms with columns [Date, L1_norm, L2_norm]
    """
    print("\n" + "=" * 80)
    print("STEP 1: Data Acquisition & L^p Norm Computation")
    print("=" * 80)

    # Fetch recent data (extended window for context)
    print("\nFetching market data from 2022-01-01 to present...")
    prices_dict = fetch_historical_data("2022-01-01", "2025-12-31")

    # Convert dict to DataFrame (use first available series as reference)
    if not prices_dict:
        raise ValueError("No data fetched")

    # Create DataFrame with all price series
    prices = pd.DataFrame(prices_dict)

    print(f"[OK] Fetched {len(prices)} days of data for {len(prices.columns)} indices")
    print(f"  Date range: {prices.index[0]} to {prices.index[-1]}")

    # Compute L^p norms (50-day windows, daily stride)
    print("\nComputing persistence landscape norms (50-day windows, daily stride)...")
    norms_df = compute_persistence_landscape_norms(
        prices=prices_dict,  # Use dict, not DataFrame
        window_size=50,
        stride=1,
        n_layers=5,  # Number of landscape functions
    )
    print(f"[OK] Computed {len(norms_df)} norm values")

    # Save data
    output_path = "outputs/2023_2025_realtime_lp_norms.csv"
    norms_df.to_csv(output_path)
    print(f"[OK] Saved to {output_path}")

    # Display summary statistics
    print("\nL^p Norm Summary Statistics:")
    print(norms_df[["L1_norm", "L2_norm"]].describe())

    return norms_df


def step2_rolling_window_analysis(norms_df):
    """
    Step 2: Rolling window analysis with parameter grid.

    Args:
        norms_df: DataFrame with L^p norms

    Returns:
        pd.DataFrame: Results with columns [rolling_window, analysis_window, metric, tau, p_value]
    """
    print("\n" + "=" * 80)
    print("STEP 2: Rolling Window Analysis with Parameter Grid")
    print("=" * 80)

    # Parameter grid (guided by historical findings)
    rolling_windows = [350, 400, 450, 500, 550]
    analysis_windows = [150, 175, 200, 225, 250]
    metrics = [
        "L1_norm_variance",
        "L2_norm_variance",
        "L1_norm_spectral_density_low",
        "L2_norm_spectral_density_low",
    ]

    results = []
    total_iterations = len(rolling_windows) * len(analysis_windows) * len(metrics)
    iteration = 0

    print(
        f"\nTesting {len(rolling_windows)} rolling windows × {len(analysis_windows)} analysis windows × {len(metrics)} metrics"
    )
    print(f"Total iterations: {total_iterations}\n")

    for rolling_win in rolling_windows:
        for analysis_win in analysis_windows:
            if analysis_win >= rolling_win:
                continue  # Skip invalid combinations

            # Compute rolling statistics
            stats_df = compute_gk_rolling_statistics(norms_df, rolling_win)

            # Use most recent analysis_window days
            recent_stats = stats_df.tail(analysis_win)

            if len(recent_stats) < 50:  # Need minimum data
                continue

            # Compute Kendall tau for each metric
            for metric in metrics:
                if metric not in recent_stats.columns:
                    continue

                iteration += 1
                print(
                    f"[{iteration}/{total_iterations}] Rolling={rolling_win}, Analysis={analysis_win}, Metric={metric}",
                    end="",
                )

                # Compute trend
                x = np.arange(len(recent_stats))
                y = recent_stats[metric].values

                # Remove NaN values
                valid_mask = ~np.isnan(y)
                if valid_mask.sum() < 10:
                    print(" -> Insufficient data")
                    continue

                x_valid = x[valid_mask]
                y_valid = y[valid_mask]

                tau, p_value = kendalltau(x_valid, y_valid)

                results.append(
                    {
                        "rolling_window": rolling_win,
                        "analysis_window": analysis_win,
                        "metric": metric,
                        "tau": tau,
                        "p_value": p_value,
                        "significant": p_value < 0.001,
                        "data_points": len(y_valid),
                    }
                )

                print(f" -> tau={tau:.4f}, p={p_value:.4e}")

    results_df = pd.DataFrame(results)

    # Save results
    output_path = "outputs/2023_2025_parameter_grid_results.csv"
    results_df.to_csv(output_path, index=False)
    print(f"\n[OK] Saved {len(results_df)} results to {output_path}")

    # Display top results
    print("\nTop 10 Results by Kendall-tau:")
    top_results = results_df.nlargest(10, "tau")
    print(
        top_results[
            [
                "rolling_window",
                "analysis_window",
                "metric",
                "tau",
                "p_value",
                "significant",
            ]
        ]
    )

    return results_df


def step3_comparative_analysis(norms_df, best_params):
    """
    Step 3: Compare current trends to historical pre-crisis periods.

    Args:
        norms_df: Current market L^p norms
        best_params: Dict with 'rolling_window', 'analysis_window', 'metric'

    Returns:
        pd.DataFrame: Comparison results
    """
    print("\n" + "=" * 80)
    print("STEP 3: Comparative Analysis with Historical Crises")
    print("=" * 80)

    rolling_win = best_params["rolling_window"]
    analysis_win = best_params["analysis_window"]
    metric = best_params["metric"]

    print("\nUsing best parameters:")
    print(f"  Rolling window: {rolling_win} days")
    print(f"  Analysis window: {analysis_win} days")
    print(f"  Metric: {metric}")

    # Compute current tau
    stats_df = compute_gk_rolling_statistics(norms_df, rolling_win)
    recent_stats = stats_df.tail(analysis_win)

    x = np.arange(len(recent_stats))
    y = recent_stats[metric].values
    valid_mask = ~np.isnan(y)
    current_tau, current_p = kendalltau(x[valid_mask], y[valid_mask])

    print("\nCurrent Market (2023-2025):")
    print(f"  tau = {current_tau:.4f}, p = {current_p:.4e}")

    # Load historical data
    historical_comparison = []

    crisis_configs = [
        ("2008 GFC", "outputs/2008_gfc_lp_norms.csv", "2008-09-15"),
        ("2000 Dotcom", "outputs/2000_dotcom_lp_norms.csv", "2000-03-10"),
        ("2020 COVID", "outputs/2020_covid_lp_norms.csv", "2020-03-16"),
    ]

    for event_name, norms_path, crisis_date in crisis_configs:
        if not os.path.exists(norms_path):
            print(f"\n[WARNING] Warning: {norms_path} not found, skipping {event_name}")
            continue

        print(f"\nAnalyzing {event_name}:")

        # Load historical norms
        event_norms = load_lp_norms_from_csv(norms_path)

        # Ensure index is datetime
        if not isinstance(event_norms.index, pd.DatetimeIndex):
            event_norms.index = pd.to_datetime(event_norms.index)

        # Find crisis date in data
        crisis_date_dt = pd.to_datetime(crisis_date)
        if crisis_date_dt not in event_norms.index:
            # Find closest date
            closest_idx = event_norms.index.get_indexer([crisis_date_dt], method="nearest")[0]
            crisis_date_dt = event_norms.index[closest_idx]

        crisis_idx = event_norms.index.get_loc(crisis_date_dt)

        # Extract comparable window (analysis_window days before crisis)
        start_idx = max(0, crisis_idx - analysis_win)
        pre_crisis_norms = event_norms.iloc[start_idx:crisis_idx]

        if len(pre_crisis_norms) < 50:
            print(f"  [WARNING] Insufficient data ({len(pre_crisis_norms)} days)")
            continue

        # Compute tau for pre-crisis period
        event_stats = compute_gk_rolling_statistics(pre_crisis_norms, rolling_win)

        if metric not in event_stats.columns or len(event_stats) < 10:
            print("  [WARNING] Insufficient statistics")
            continue

        x_hist = np.arange(len(event_stats))
        y_hist = event_stats[metric].values
        valid_mask_hist = ~np.isnan(y_hist)

        if valid_mask_hist.sum() < 10:
            print("  [WARNING] Insufficient valid data")
            continue

        hist_tau, hist_p = kendalltau(x_hist[valid_mask_hist], y_hist[valid_mask_hist])

        print(f"  tau = {hist_tau:.4f}, p = {hist_p:.4e}")

        historical_comparison.append(
            {
                "period": event_name,
                "tau": hist_tau,
                "p_value": hist_p,
                "crisis_occurred": True,
                "status": "Historical Crisis",
            }
        )

    # Add current period
    historical_comparison.append(
        {
            "period": "2023-2025 Current",
            "tau": current_tau,
            "p_value": current_p,
            "crisis_occurred": False,
            "status": "Unknown",
        }
    )

    comparison_df = pd.DataFrame(historical_comparison)

    # Interpret current status
    print("\n" + "-" * 80)
    print("INTERPRETATION:")
    print("-" * 80)

    if current_tau > 0.70:
        status = "🔴 HIGH CONCERN - Matches pre-crisis levels"
        risk_level = "HIGH"
    elif current_tau > 0.60:
        status = "🟡 MODERATE CONCERN - Elevated but below threshold"
        risk_level = "MODERATE"
    elif current_tau > 0.50:
        status = "[ORANGE] WEAK CONCERN - Monitor closely"
        risk_level = "WEAK"
    else:
        status = "[GREEN] NO CONCERN - Normal market dynamics"
        risk_level = "NONE"

    print(f"\nRisk Level: {status}")
    print("\nComparison Table:")
    print(comparison_df.to_string(index=False))

    return comparison_df, risk_level, status


def step4_temporal_analysis(norms_df, best_params):
    """
    Step 4: Temporal analysis - when did trends emerge?

    Args:
        norms_df: Current market L^p norms
        best_params: Dict with 'rolling_window', 'metric'

    Returns:
        pd.DataFrame: Timeline of tau evolution
    """
    print("\n" + "=" * 80)
    print("STEP 4: Temporal Analysis - Trend Emergence Timeline")
    print("=" * 80)

    rolling_win = best_params["rolling_window"]
    metric = best_params["metric"]

    # Compute rolling statistics once
    stats_df = compute_gk_rolling_statistics(norms_df, rolling_win)

    # Sliding window approach - compute tau for overlapping periods
    lookback_periods = range(100, min(301, len(stats_df)), 25)
    tau_timeline = []

    print(f"\nComputing tau for lookback periods: 100 to {min(300, len(stats_df))} days\n")

    for lookback in lookback_periods:
        recent_stats = stats_df.tail(lookback)

        if len(recent_stats) < 50:
            continue

        x = np.arange(len(recent_stats))
        y = recent_stats[metric].values
        valid_mask = ~np.isnan(y)

        if valid_mask.sum() < 10:
            continue

        tau, p = kendalltau(x[valid_mask], y[valid_mask])

        tau_timeline.append(
            {
                "lookback_days": lookback,
                "tau": tau,
                "p_value": p,
                "end_date": stats_df.index[-1],
                "start_date": recent_stats.index[0],
            }
        )

        print(f"Lookback={lookback:3d} days: tau={tau:.4f}, p={p:.4e}")

    timeline_df = pd.DataFrame(tau_timeline)

    # Interpret pattern
    print("\n" + "-" * 80)
    print("TEMPORAL PATTERN:")
    print("-" * 80)

    if len(timeline_df) > 0:
        tau_trend = np.polyfit(timeline_df["lookback_days"], timeline_df["tau"], 1)[0]

        if tau_trend > 0:
            pattern = "[WARNING] SUSTAINED BUILDUP - tau increases with longer lookbacks (concerning)"
        elif timeline_df.iloc[0]["tau"] > timeline_df.iloc[-1]["tau"] * 1.2:
            pattern = "[WARNING][WARNING] RECENT SURGE - tau peaks at short lookbacks (very concerning)"
        else:
            pattern = "[OK] NO CLEAR TREND - tau is flat/low across all periods (normal)"

        print(f"\n{pattern}")
        print(f"tau slope vs. lookback: {tau_trend:.6f}")

    return timeline_df


def step5_sector_breakdown():
    """
    Step 5: Analyze sector groups for localized stress.

    Compares TDA signals across different market sectors using representative baskets.

    Returns:
        dict: Sector results with tau values
    """
    print("\n" + "=" * 80)
    print("STEP 5: Sector/Asset Breakdown Analysis")
    print("=" * 80)

    # Define sector baskets (4 tickers each for proper TDA)
    sector_baskets = {
        "Technology": ["AAPL", "MSFT", "GOOGL", "NVDA"],
        "Financials": ["JPM", "BAC", "WFC", "GS"],
        "Healthcare": ["JNJ", "UNH", "PFE", "ABBV"],
        "Energy": ["XOM", "CVX", "COP", "SLB"],
        "Consumer": ["AMZN", "WMT", "HD", "MCD"],
    }

    sector_results = {}

    print(f"\nAnalyzing {len(sector_baskets)} sector baskets:\n")

    for sector_name, tickers in sector_baskets.items():
        print(f"Processing {sector_name} ({', '.join(tickers)})...")

        try:
            # Fetch data for all tickers in the sector
            prices_dict = {}
            all_fetched = True

            for ticker in tickers:
                data = fetch_ticker(ticker, start_date="2022-01-01", end_date="2025-12-31")
                if data is None or len(data) < 100:
                    print(f"  [WARNING] Insufficient data for {ticker}")
                    all_fetched = False
                    break
                prices_dict[ticker] = data["Close"]

            if not all_fetched:
                continue

            # Compute norms using the sector basket
            norms = compute_persistence_landscape_norms(prices_dict, window_size=50, stride=1, n_layers=5)

            # Compute tau (using default 450/200 window)
            stats = compute_gk_rolling_statistics(norms, 450)
            recent = stats.tail(200)

            if len(recent) < 50:
                print("  [WARNING] Insufficient statistics")
                continue

            x = np.arange(len(recent))
            y = recent["L2_norm_variance"].values
            valid_mask = ~np.isnan(y)

            if valid_mask.sum() < 10:
                print("  [WARNING] Insufficient valid data")
                continue

            tau, p = kendalltau(x[valid_mask], y[valid_mask])

            sector_results[sector_name] = {
                "name": sector_name,
                "tickers": tickers,
                "tau": tau,
                "p_value": p,
                "data_points": len(norms),
            }

            print(f"  [OK] tau={tau:.4f}, p={p:.4e}")

        except Exception as e:
            print(f"  [WARNING] Error: {str(e)}")
            continue

    # Interpret results
    print("\n" + "-" * 80)
    print("SECTOR STRESS ANALYSIS:")
    print("-" * 80)

    if len(sector_results) > 0:
        max_tau = max([r["tau"] for r in sector_results.values()])
        min_tau = min([r["tau"] for r in sector_results.values()])

        if max_tau > 0.70 and min_tau < 0.60:
            interpretation = "[WARNING] SECTOR-SPECIFIC STRESS - Localized concerns"
        elif max_tau > 0.70:
            interpretation = "[WARNING][WARNING] BROAD-BASED STRESS - Market-wide concerns (very concerning)"
        else:
            interpretation = "[OK] NO SIGNIFICANT STRESS - All sectors within normal range"

        print(f"\n{interpretation}")
        print(f"\nTau range: [{min_tau:.4f}, {max_tau:.4f}]")

    return sector_results


def step6_create_visualizations(
    norms_df,
    results_df,
    comparison_df,
    timeline_df,
    sector_results,
    best_params,
    current_tau,
    risk_level,
):
    """
    Step 6: Create comprehensive visualization.

    Args:
        norms_df: L^p norms
        results_df: Parameter grid results
        comparison_df: Historical comparison
        timeline_df: Temporal analysis timeline
        sector_results: Sector breakdown
        best_params: Best parameters found
        current_tau: Current tau value
        risk_level: Risk level string
    """
    print("\n" + "=" * 80)
    print("STEP 6: Creating Comprehensive Visualization")
    print("=" * 80)

    fig, axes = plt.subplots(3, 2, figsize=(16, 14))
    fig.suptitle("2023-2025 Real-Time Crisis Detection Analysis", fontsize=16, fontweight="bold")

    # Panel 1: Recent L^p norms
    ax = axes[0, 0]
    recent_norms = norms_df.tail(500)
    ax.plot(
        recent_norms.index,
        recent_norms["L1_norm"],
        label="L¹",
        alpha=0.7,
        linewidth=1.5,
    )
    ax.plot(
        recent_norms.index,
        recent_norms["L2_norm"],
        label="L²",
        alpha=0.7,
        linewidth=1.5,
    )
    ax.set_title("Recent L^p Norms (Last 500 days)", fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Norm Value")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Panel 2: Rolling variance with trend
    ax = axes[0, 1]
    rolling_win = best_params["rolling_window"]
    analysis_win = best_params["analysis_window"]
    metric = best_params["metric"]

    stats_df = compute_gk_rolling_statistics(norms_df, rolling_win)
    recent_stats = stats_df.tail(analysis_win)

    ax.plot(
        recent_stats.index,
        recent_stats[metric],
        label="Actual",
        alpha=0.7,
        linewidth=1.5,
    )

    # Add trend line
    x = np.arange(len(recent_stats))
    y = recent_stats[metric].values
    valid_mask = ~np.isnan(y)
    slope, intercept, _, _ = theilslopes(y[valid_mask], x[valid_mask])
    trend_line = slope * x + intercept

    ax.plot(
        recent_stats.index,
        trend_line,
        "r--",
        label=f"Trend (tau={current_tau:.3f})",
        linewidth=2,
    )
    ax.set_title(
        f"{metric.replace('_', ' ').title()} Trend (Most Recent Window)",
        fontweight="bold",
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Metric Value")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Panel 3: Historical comparison
    ax = axes[1, 0]
    if len(comparison_df) > 0:
        periods = comparison_df["period"].tolist()
        taus = comparison_df["tau"].tolist()
        colors = ["blue" if p == "2023-2025 Current" else "red" for p in periods]

        bars = ax.bar(range(len(periods)), taus, color=colors, alpha=0.7, edgecolor="black")
        ax.axhline(
            0.70,
            color="darkred",
            linestyle="--",
            label="Crisis Threshold (tau=0.70)",
            linewidth=2,
        )
        ax.set_xticks(range(len(periods)))
        ax.set_xticklabels(periods, rotation=15, ha="right")
        ax.set_ylabel("Kendall-tau")
        ax.set_title("Current vs. Historical Pre-Crisis Trends", fontweight="bold")
        ax.legend()
        ax.grid(True, alpha=0.3, axis="y")

        # Add risk level annotation
        ax.text(
            0.02,
            0.98,
            f"Risk Level: {risk_level}",
            transform=ax.transAxes,
            fontsize=10,
            fontweight="bold",
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
        )

    # Panel 4: Parameter sensitivity heatmap
    ax = axes[1, 1]
    if len(results_df) > 0:
        # Group by parameters and take max tau across metrics
        pivot_data = results_df.groupby(["rolling_window", "analysis_window"])["tau"].max().reset_index()
        pivot = pivot_data.pivot(index="rolling_window", columns="analysis_window", values="tau")

        im = ax.imshow(pivot.values, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_yticks(range(len(pivot.index)))
        ax.set_xticklabels(pivot.columns)
        ax.set_yticklabels(pivot.index)
        ax.set_xlabel("Analysis Window (days)")
        ax.set_ylabel("Rolling Window (days)")
        ax.set_title("Parameter Sensitivity (Max tau across metrics)", fontweight="bold")

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label("Kendall-tau", rotation=270, labelpad=15)

        # Add text annotations for values
        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                ax.text(
                    j,
                    i,
                    f"{pivot.values[i, j]:.2f}",
                    ha="center",
                    va="center",
                    color="black",
                    fontsize=8,
                )

    # Panel 5: Sector breakdown
    ax = axes[2, 0]
    if len(sector_results) > 0:
        tickers = list(sector_results.keys())
        names = [sector_results[t]["name"] for t in tickers]
        sector_taus = [sector_results[t]["tau"] for t in tickers]

        bars = ax.barh(names, sector_taus, alpha=0.7, edgecolor="black")
        ax.axvline(0.70, color="red", linestyle="--", label="Threshold (tau=0.70)", linewidth=2)
        ax.set_xlabel("Kendall-tau")
        ax.set_title("Sector/Index Breakdown", fontweight="bold")
        ax.legend()
        ax.grid(True, alpha=0.3, axis="x")

        # Color bars based on threshold
        for i, bar in enumerate(bars):
            if sector_taus[i] > 0.70:
                bar.set_color("red")
            elif sector_taus[i] > 0.60:
                bar.set_color("orange")
            else:
                bar.set_color("green")

    # Panel 6: Timeline of tau evolution
    ax = axes[2, 1]
    if len(timeline_df) > 0:
        ax.plot(
            timeline_df["lookback_days"],
            timeline_df["tau"],
            marker="o",
            linewidth=2,
            markersize=6,
        )
        ax.axhline(0.70, color="red", linestyle="--", label="Crisis Threshold", linewidth=2)
        ax.axhline(
            0.60,
            color="orange",
            linestyle="--",
            label="Moderate Concern",
            linewidth=1.5,
            alpha=0.7,
        )
        ax.set_xlabel("Lookback Period (days)")
        ax.set_ylabel("Kendall-tau")
        ax.set_title("Trend Strength vs. Window Size", fontweight="bold")
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save figure
    output_path = "figures/2023_2025_comprehensive_analysis.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"\n[OK] Saved comprehensive visualization to {output_path}")

    plt.close()


def generate_markdown_report(
    norms_df,
    results_df,
    comparison_df,
    timeline_df,
    sector_results,
    best_params,
    current_tau,
    risk_level,
    status,
):
    """
    Generate comprehensive markdown report.

    Args:
        norms_df: L^p norms
        results_df: Parameter grid results
        comparison_df: Historical comparison
        timeline_df: Temporal analysis
        sector_results: Sector breakdown
        best_params: Best parameters
        current_tau: Current tau value
        risk_level: Risk level
        status: Status message
    """
    print("\n" + "=" * 80)
    print("Generating Markdown Report")
    print("=" * 80)

    report = f"""# Real-Time Crisis Detection Analysis: 2023-2025

**Analysis Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Methodology:** Gidea & Katz (2018) TDA-based Crisis Detection  
**Data Period:** 2022-01-01 to {norms_df.index[-1].strftime("%Y-%m-%d")}

---

## Executive Summary

### Warning Level
**{status}**

### Key Findings

- **Current Kendall-tau:** {current_tau:.4f}
- **Best Parameters:** Rolling={best_params["rolling_window"]} days, Analysis={best_params["analysis_window"]} days
- **Metric:** {best_params["metric"].replace("_", " ").title()}
- **Risk Assessment:** {risk_level}

### Interpretation

"""

    if current_tau > 0.70:
        report += """🔴 **HIGH CONCERN**: Current market trends match or exceed pre-crisis levels observed before 
the 2008 Global Financial Crisis and 2000 Dotcom Crash. Elevated persistence topology metrics 
indicate increasing market instability and potential regime change.

**Recommendation:** Close monitoring warranted. Consider defensive positioning and risk reduction strategies.
"""
    elif current_tau > 0.60:
        report += """[YELLOW] **MODERATE CONCERN**: Market trends show elevated but sub-threshold stress signals. 
While not yet matching historical pre-crisis levels, the upward trend in topological metrics 
warrants attention.

**Recommendation:** Monitor closely for further deterioration. Review portfolio risk exposures.
"""
    elif current_tau > 0.50:
        report += """[ORANGE] **WEAK CONCERN**: Market shows mild trend patterns in topological metrics. 
Stress levels remain well below historical pre-crisis thresholds but bear watching.

**Recommendation:** Routine monitoring. No immediate action required.
"""
    else:
        report += """[GREEN] **NO CONCERN**: Current market dynamics appear normal with no significant upward 
trends in topological stress indicators. Persistence landscape norms show typical patterns.

**Recommendation:** Continue normal monitoring protocols.
"""

    report += f"""

---

## Methodology

### Data Sources
- **Indices:** S&P 500, Dow Jones, NASDAQ, Russell 2000
- **Period:** 2022-01-01 to {norms_df.index[-1].strftime("%Y-%m-%d")}
- **Total Days:** {len(norms_df)}

### Topological Analysis
- **Embedding:** Takens embedding with 50-day windows (stride=1)
- **Filtration:** Vietoris-Rips complex
- **Features:** Persistence landscape L^p norms (L¹, L², L^∞)
- **Trend Analysis:** Kendall-tau correlation on rolling window statistics

### Parameter Optimization
Tested {len(results_df)} parameter combinations:
- **Rolling Windows:** 350, 400, 450, 500, 550 days
- **Analysis Windows:** 150, 175, 200, 225, 250 days
- **Metrics:** L¹/L² variance, L¹/L² spectral density

---

## Detailed Results

### 1. Best Parameters Found

| Parameter | Value |
|-----------|-------|
| Rolling Window | {best_params["rolling_window"]} days |
| Analysis Window | {best_params["analysis_window"]} days |
| Metric | {best_params["metric"]} |
| Current tau | {current_tau:.4f} |
| P-value | {results_df[results_df["tau"] == current_tau]["p_value"].iloc[0]:.4e} |

### 2. Historical Comparison

"""

    if len(comparison_df) > 0:
        report += "| Period | Kendall-tau | Status | Crisis Outcome |\n"
        report += "|--------|-------------|--------|----------------|\n"
        for _, row in comparison_df.iterrows():
            crisis_status = "Crisis Occurred" if row["crisis_occurred"] else "Unknown"
            report += f"| {row['period']} | {row['tau']:.4f} | {row['status']} | {crisis_status} |\n"

    report += """

**Analysis:** 
"""

    if len(comparison_df) > 1:
        historical_taus = comparison_df[comparison_df["crisis_occurred"]]["tau"].values
        if len(historical_taus) > 0:
            min_historical = historical_taus.min()
            max_historical = historical_taus.max()

            if current_tau >= min_historical:
                report += f"Current tau ({current_tau:.4f}) is within or above the historical pre-crisis range [{min_historical:.4f}, {max_historical:.4f}]. "
            else:
                report += f"Current tau ({current_tau:.4f}) is below the historical pre-crisis range [{min_historical:.4f}, {max_historical:.4f}]. "

    report += """

### 3. Temporal Pattern Analysis

"""

    if len(timeline_df) > 0:
        tau_at_100 = (
            timeline_df[timeline_df["lookback_days"] == 100]["tau"].iloc[0]
            if len(timeline_df[timeline_df["lookback_days"] == 100]) > 0
            else None
        )
        tau_at_max = timeline_df["tau"].iloc[-1]

        report += """| Lookback Period | Kendall-tau | Start Date | End Date |
|----------------|-------------|------------|----------|
"""
        for _, row in timeline_df.iterrows():
            report += f"| {row['lookback_days']} days | {row['tau']:.4f} | {row['start_date'].strftime('%Y-%m-%d')} | {row['end_date'].strftime('%Y-%m-%d')} |\n"

        if tau_at_100 and tau_at_max:
            tau_trend = (tau_at_max - tau_at_100) / tau_at_100 * 100
            report += f"\n**Trend:** tau changed by {tau_trend:+.1f}% from 100-day to {timeline_df['lookback_days'].max()}-day lookback.\n"

    report += """

### 4. Sector/Index Breakdown

"""

    if len(sector_results) > 0:
        report += "| Index | Name | Kendall-tau | Assessment |\n"
        report += "|-------|------|-------------|------------|\n"
        for ticker, data in sector_results.items():
            tau_val = data["tau"]
            if tau_val > 0.70:
                assessment = "[RED] High Risk"
            elif tau_val > 0.60:
                assessment = "[YELLOW] Moderate Risk"
            elif tau_val > 0.50:
                assessment = "[ORANGE] Weak Risk"
            else:
                assessment = "[GREEN] Normal"

            report += f"| {ticker} | {data['name']} | {tau_val:.4f} | {assessment} |\n"

        # Analyze for sector-specific vs broad stress
        high_risk_count = sum(1 for d in sector_results.values() if d["tau"] > 0.70)
        if high_risk_count > 0:
            if high_risk_count == len(sector_results):
                report += "\n**Pattern:** Broad-based stress across all indices (market-wide concern).\n"
            else:
                report += "\n**Pattern:** Sector-specific stress detected (localized concerns).\n"

    report += """

---

## Visualization

![Comprehensive Analysis](../figures/2023_2025_comprehensive_analysis.png)

**Figure:** Six-panel analysis showing (1) Recent L^p norms, (2) Rolling variance with trend, 
(3) Historical comparison, (4) Parameter sensitivity heatmap, (5) Sector breakdown, 
(6) Temporal evolution of tau values.

---

## Recommendations

"""

    if risk_level == "HIGH":
        report += """
### 🔴 HIGH RISK - Immediate Actions

1. **Portfolio Review:** Conduct immediate review of risk exposures
2. **Defensive Positioning:** Consider increasing cash positions or defensive sectors
3. **Volatility Hedging:** Evaluate VIX calls or put spreads for downside protection
4. **Daily Monitoring:** Track L^p norms and tau values daily for deterioration
5. **Exit Planning:** Prepare contingency plans for rapid position unwinding

### Next Steps
- Run analysis daily to track tau evolution
- Monitor sector divergence for localized vs. systemic stress
- Compare to alternative early warning indicators (VIX, credit spreads, etc.)
"""
    elif risk_level == "MODERATE":
        report += """
### 🟡 MODERATE RISK - Vigilant Monitoring

1. **Increased Monitoring:** Move to weekly analysis updates
2. **Risk Assessment:** Review portfolio beta and volatility exposures
3. **Scenario Planning:** Develop contingency plans for market stress
4. **Hedge Consideration:** Evaluate cost/benefit of portfolio insurance
5. **Sector Rotation:** Consider rotating to defensive sectors if tau increases

### Next Steps
- Run analysis weekly to track trend development
- Set alert thresholds for tau crossing 0.70
- Monitor correlation with other risk indicators
"""
    elif risk_level == "WEAK":
        report += """
### 🟠 WEAK RISK - Routine Monitoring

1. **Standard Monitoring:** Continue bi-weekly or monthly analysis
2. **Awareness:** Keep topological metrics on watchlist
3. **Threshold Alerts:** Set notifications if tau exceeds 0.60
4. **Normal Operations:** Maintain current investment strategy

### Next Steps
- Run analysis bi-weekly or monthly
- Document trend evolution for historical reference
"""
    else:
        report += """
### [GREEN] NO RISK - Normal Operations

1. **Routine Monitoring:** Monthly analysis sufficient
2. **Historical Tracking:** Continue building baseline dataset
3. **Methodology Validation:** Use period to refine detection parameters
4. **Normal Operations:** No changes to investment strategy required

### Next Steps
- Run analysis monthly for historical record
- Continue parameter optimization research
"""

    report += f"""

---

## Technical Details

### Data Quality
- **Total L^p Norm Calculations:** {len(norms_df)}
- **Parameter Grid Tests:** {len(results_df)}
- **Significant Results (p<0.001):** {len(results_df[results_df["significant"]])}

### Top 5 Parameter Combinations

"""

    if len(results_df) > 0:
        top5 = results_df.nlargest(5, "tau")
        report += "| Rank | Rolling | Analysis | Metric | tau | P-value |\n"
        report += "|------|---------|----------|--------|---|--------|\n"
        for idx, (_, row) in enumerate(top5.iterrows(), 1):
            report += f"| {idx} | {row['rolling_window']} | {row['analysis_window']} | {row['metric']} | {row['tau']:.4f} | {row['p_value']:.4e} |\n"

    report += """

### Computational Environment
- **Python Packages:** numpy, pandas, scipy, gudhi, matplotlib
- **TDA Library:** GUDHI 3.x
- **Persistence:** Vietoris-Rips filtration, landscape norms
- **Statistical Tests:** Kendall-tau (non-parametric)

---

## References

1. Gidea, M., & Katz, Y. (2018). Topological data analysis of financial time series: 
   Landscapes of crashes. *Physica A: Statistical Mechanics and its Applications*, 491, 820-834.

2. This analysis replicates and extends the G&K methodology with validated parameters 
   across multiple historical crises (2008 GFC, 2000 Dotcom, 2020 COVID).

---

## Appendix: Raw Data Files

- **L^p Norms:** `outputs/2023_2025_realtime_lp_norms.csv`
- **Parameter Grid:** `outputs/2023_2025_parameter_grid_results.csv`
- **Figures:** `figures/2023_2025_comprehensive_analysis.png`

---

*Analysis generated by TDL Real-Time Crisis Detection System*  
*For questions or issues, see project documentation*
"""

    # Save report
    output_path = "financial_tda/validation/2023_2025_realtime_analysis.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"[OK] Saved comprehensive report to {output_path}")

    return report


def main():
    """
    Main execution function.
    """
    print("\n" + "=" * 80)
    print("REAL-TIME CRISIS DETECTION ANALYSIS: 2023-2025")
    print("=" * 80)
    print("\nMethodology: Gidea & Katz (2018) TDA-based Crisis Detection")
    print("Objective: Detect potential pre-crisis warning signals in recent market data")
    print("\n" + "=" * 80)

    # Ensure output directories exist
    ensure_output_dirs()

    # Step 1: Fetch data and compute norms
    norms_df = step1_fetch_and_compute_norms()

    # Step 2: Rolling window analysis with parameter grid
    results_df = step2_rolling_window_analysis(norms_df)

    # Find best parameters
    best_result = results_df.nlargest(1, "tau").iloc[0]
    best_params = {
        "rolling_window": int(best_result["rolling_window"]),
        "analysis_window": int(best_result["analysis_window"]),
        "metric": best_result["metric"],
    }
    current_tau = best_result["tau"]

    print(f"\n{'=' * 80}")
    print("BEST PARAMETERS IDENTIFIED")
    print(f"{'=' * 80}")
    print(f"Rolling Window: {best_params['rolling_window']} days")
    print(f"Analysis Window: {best_params['analysis_window']} days")
    print(f"Metric: {best_params['metric']}")
    print(f"Kendall-tau: {current_tau:.4f}")

    # Step 3: Comparative analysis
    comparison_df, risk_level, status = step3_comparative_analysis(norms_df, best_params)

    # Step 4: Temporal analysis
    timeline_df = step4_temporal_analysis(norms_df, best_params)

    # Step 5: Sector breakdown
    sector_results = step5_sector_breakdown()

    # Step 6: Create visualizations
    step6_create_visualizations(
        norms_df,
        results_df,
        comparison_df,
        timeline_df,
        sector_results,
        best_params,
        current_tau,
        risk_level,
    )

    # Generate markdown report
    generate_markdown_report(
        norms_df,
        results_df,
        comparison_df,
        timeline_df,
        sector_results,
        best_params,
        current_tau,
        risk_level,
        status,
    )

    # Final summary
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\nRisk Level: {risk_level}")
    print(f"Status: {status}")
    print("\nOutputs:")
    print("  - L^p Norms: outputs/2023_2025_realtime_lp_norms.csv")
    print("  - Parameter Results: outputs/2023_2025_parameter_grid_results.csv")
    print("  - Visualization: figures/2023_2025_comprehensive_analysis.png")
    print("  - Report: financial_tda/validation/2023_2025_realtime_analysis.md")
    print("\n" + "=" * 80)

    return {
        "norms_df": norms_df,
        "results_df": results_df,
        "comparison_df": comparison_df,
        "timeline_df": timeline_df,
        "sector_results": sector_results,
        "best_params": best_params,
        "current_tau": current_tau,
        "risk_level": risk_level,
        "status": status,
    }


if __name__ == "__main__":
    results = main()
