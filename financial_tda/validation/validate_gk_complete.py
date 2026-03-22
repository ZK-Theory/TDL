"""
Phase 10C Complete: G&K Methodology - Full Replication
========================================================

Purpose:
    Complete, reproducible replication of Gidea & Katz (2018).
    Compute ALL 6 statistics for ALL 10 events.

Statistics (6):
    1. L1_norm_variance
    2. L2_norm_variance
    3. L1_norm_spectral_density_low
    4. L2_norm_spectral_density_low
    5. L1_norm_acf_lag1
    6. L2_norm_acf_lag1

Events (10):
    2008 GFC, 2000 Dotcom, 2020 COVID, 1997 Asian, 2011 EU Debt,
    9/11, 2015 China, Brexit, 2010 Flash Crash, 2022 Rate Shock

Parameters (FIXED - NO TUNING):
    W = 500, P = 250, Point Cloud = 50, H1

Author: Phase 10C Complete Implementation
Date: 2025-12-17
"""

import pandas as pd
import numpy as np
from scipy.stats import kendalltau
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

# Import existing pipeline
from financial_tda.validation.gidea_katz_replication import (
    fetch_historical_data,
    compute_persistence_landscape_norms,
    compute_rolling_statistics,
)

# ============================================================================
# CONFIGURATION (FIXED - NO TUNING)
# ============================================================================
W = 500  # Rolling window
P = 250  # Pre-crisis trend window
POINT_CLOUD_WINDOW = 50

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = BASE_DIR / "outputs" / "phase_10c_complete"
NORMS_CACHE = OUTPUT_DIR / "norms_cache_complete.csv"

# All 6 statistics from G&K
STATISTICS = [
    "L1_norm_variance",
    "L2_norm_variance",
    "L1_norm_spectral_density_low",
    "L2_norm_spectral_density_low",
    "L1_norm_acf_lag1",
    "L2_norm_acf_lag1",
]

# All 10 events
EVENTS = [
    {"name": "2008 GFC", "date": "2008-09-15", "expected": "positive", "note": "Subprime crisis peak"},
    {"name": "2000 Dotcom", "date": "2000-03-10", "expected": "positive", "note": "NASDAQ peak"},
    {"name": "2020 COVID", "date": "2020-03-23", "expected": "mixed", "note": "COVID crash bottom"},
    {"name": "1997 Asian", "date": "1997-10-27", "expected": "positive", "note": "Mini-crash day"},
    {"name": "2011 EU Debt", "date": "2011-08-08", "expected": "mixed", "note": "S&P downgrade aftermath"},
    {"name": "9/11", "date": "2001-09-11", "expected": "neutral", "note": "Terrorist attack"},
    {"name": "2015 China", "date": "2015-08-24", "expected": "neutral", "note": "China devaluation shock"},
    {"name": "Brexit", "date": "2016-06-24", "expected": "neutral", "note": "Referendum result"},
    {"name": "2010 Flash Crash", "date": "2010-05-06", "expected": "neutral", "note": "Intraday crash"},
    {"name": "2022 Rate Shock", "date": "2022-06-16", "expected": "mixed", "note": "Fed rate hike"},
]


def ensure_dirs():
    """Create output directories."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")


def fetch_or_load_norms():
    """Fetch historical data and compute norms, or load from cache."""
    if NORMS_CACHE.exists():
        print(f"Loading cached norms from: {NORMS_CACHE}")
        norms_df = pd.read_csv(NORMS_CACHE, index_col=0, parse_dates=True)
        print(f"  Loaded {len(norms_df)} days")
        return norms_df

    print("Fetching historical data (1994-2025)...")

    # Need extra buffer for earliest event (1997) with W=500 + P=250
    start_date = "1994-01-01"
    end_date = "2025-12-31"

    prices_dict = fetch_historical_data(start_date, end_date)

    print("Computing persistence landscape norms...")
    norms_df = compute_persistence_landscape_norms(
        prices=prices_dict, window_size=POINT_CLOUD_WINDOW, stride=1, n_layers=5
    )

    # Ensure tz-naive before caching
    if hasattr(norms_df.index, "tz") and norms_df.index.tz is not None:
        norms_df.index = norms_df.index.tz_localize(None)

    # Cache
    norms_df.to_csv(NORMS_CACHE)
    print(f"  Cached norms to: {NORMS_CACHE}")

    return norms_df


def compute_tau_for_event(stats_df, event_date, stat_col):
    """Compute Kendall-tau for a specific statistic and event date."""
    # Parse event date as naive datetime
    event_date = pd.Timestamp(event_date).tz_localize(None)

    # Ensure index is DatetimeIndex and tz-naive
    if not isinstance(stats_df.index, pd.DatetimeIndex):
        stats_df.index = pd.to_datetime(stats_df.index)

    # Remove timezone info if present
    if stats_df.index.tz is not None:
        stats_df.index = stats_df.index.tz_localize(None)

    # Find nearest date by converting to day-resolution integers
    event_day = (event_date - pd.Timestamp("1970-01-01")).days
    index_days = (stats_df.index - pd.Timestamp("1970-01-01")).days
    date_diffs = np.abs(index_days - event_day)
    event_loc = date_diffs.argmin()

    # Check if we have enough data
    if event_loc < P:
        return np.nan, np.nan, "Insufficient data"

    # Extract P-day window before event
    segment = stats_df[stat_col].iloc[event_loc - P : event_loc]

    # Check for NaNs
    valid_count = (~segment.isna()).sum()
    if valid_count < P * 0.5:
        return np.nan, np.nan, f"Too many NaNs ({P - valid_count}/{P})"

    # Compute Kendall-tau
    x = np.arange(len(segment))
    tau, p_value = kendalltau(x, segment.values, nan_policy="omit")

    return tau, p_value, None


def compute_all_tau_values(stats_df):
    """Compute all τ values for all events and statistics."""
    results = []

    print("\nComputing τ values for all events and statistics...")
    print("-" * 70)

    for event in EVENTS:
        print(f"\n{event['name']} ({event['date']}):")

        event_result = {
            "event": event["name"],
            "date": event["date"],
            "expected": event["expected"],
            "note": event["note"],
        }

        for stat in STATISTICS:
            tau, p_val, error = compute_tau_for_event(stats_df, event["date"], stat)

            # Shortened column names
            stat_short = stat.replace("_norm_", "_").replace("spectral_density_low", "spec").replace("variance", "var")

            event_result[f"{stat_short}_tau"] = tau
            event_result[f"{stat_short}_p"] = p_val

            if error:
                print(f"  {stat}: ERROR - {error}")
            else:
                sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else ""
                print(f"  {stat}: τ={tau:+.3f} (p={p_val:.4f}) {sig}")

        results.append(event_result)

    return pd.DataFrame(results)


def generate_report(results_df):
    """Generate comprehensive markdown report."""
    report = []
    report.append("# Phase 10C Complete: G&K Full Replication Report")
    report.append("")
    report.append(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")

    report.append("## Methodology")
    report.append("")
    report.append("Complete replication of Gidea & Katz (2018) methodology:")
    report.append(f"- Rolling window (W): {W} days")
    report.append(f"- Pre-crisis window (P): {P} days")
    report.append(f"- Point cloud: {POINT_CLOUD_WINDOW} days")
    report.append("- Homology: H₁")
    report.append("")

    report.append("## Statistics Computed")
    report.append("")
    report.append("| Statistic | Description |")
    report.append("|-----------|-------------|")
    report.append("| L1_var | Rolling variance of L¹ norm |")
    report.append("| L2_var | Rolling variance of L² norm |")
    report.append("| L1_spec | Low-frequency spectral density of L¹ norm |")
    report.append("| L2_spec | Low-frequency spectral density of L² norm |")
    report.append("| L1_acf | Lag-1 autocorrelation of L¹ norm |")
    report.append("| L2_acf | Lag-1 autocorrelation of L² norm |")
    report.append("")

    # Summary table - L2 variance (primary metric)
    report.append("## Primary Results: L² Variance τ")
    report.append("")
    report.append("| Event | Date | L2 Variance τ | p-value | Significant? |")
    report.append("|-------|------|---------------|---------|--------------|")

    for _, row in results_df.iterrows():
        tau = row.get("L2_var_tau", np.nan)
        p = row.get("L2_var_p", np.nan)
        if pd.notna(tau):
            sig = "✅ Yes" if p < 0.05 else "❌ No"
            tau_str = f"{tau:+.3f}"
            p_str = f"{p:.4f}"
        else:
            sig = "—"
            tau_str = "N/A"
            p_str = "N/A"
        report.append(f"| {row['event']} | {row['date']} | {tau_str} | {p_str} | {sig} |")

    report.append("")

    # Full results matrix
    report.append("## Complete τ Matrix (All Events × All Statistics)")
    report.append("")

    # Header
    stat_cols = ["L1_var_tau", "L2_var_tau", "L1_spec_tau", "L2_spec_tau", "L1_acf_lag1_tau", "L2_acf_lag1_tau"]
    header = "| Event | " + " | ".join([c.replace("_tau", "") for c in stat_cols]) + " |"
    separator = "|" + "|".join(["-------"] * (len(stat_cols) + 1)) + "|"
    report.append(header)
    report.append(separator)

    for _, row in results_df.iterrows():
        vals = [row["event"]]
        for col in stat_cols:
            tau = row.get(col, np.nan)
            if pd.notna(tau):
                vals.append(f"{tau:+.2f}")
            else:
                vals.append("N/A")
        report.append("| " + " | ".join(vals) + " |")

    report.append("")

    # Analysis by event type
    report.append("## Analysis by Expected Classification")
    report.append("")

    # Count significant positive τ values
    for expected_type in ["positive", "neutral", "mixed"]:
        events = results_df[results_df["expected"] == expected_type]
        if len(events) > 0:
            report.append(f"### Expected: {expected_type.title()}")
            report.append("")
            for _, row in events.iterrows():
                tau = row.get("L2_var_tau", np.nan)
                if pd.notna(tau):
                    if tau > 0.5:
                        status = "✅ Strong positive"
                    elif tau > 0.3:
                        status = "Moderate positive"
                    elif tau < -0.5:
                        status = "❌ Strong negative"
                    elif tau < -0.3:
                        status = "Moderate negative"
                    else:
                        status = "Neutral"
                    report.append(f"- **{row['event']}**: τ = {tau:+.3f} ({status})")
                else:
                    report.append(f"- **{row['event']}**: N/A")
            report.append("")

    # Count statistics
    report.append("## Summary Statistics")
    report.append("")

    tau_col = "L2_var_tau"
    valid_tau = results_df[tau_col].dropna()

    n_positive = (valid_tau > 0.5).sum()
    n_moderate_pos = ((valid_tau > 0.3) & (valid_tau <= 0.5)).sum()
    n_neutral = ((valid_tau >= -0.3) & (valid_tau <= 0.3)).sum()
    n_moderate_neg = ((valid_tau < -0.3) & (valid_tau >= -0.5)).sum()
    n_negative = (valid_tau < -0.5).sum()

    report.append("For L² Variance τ (primary G&K metric):")
    report.append(f"- Strong positive (τ > 0.5): {n_positive}/10")
    report.append(f"- Moderate positive: {n_moderate_pos}/10")
    report.append(f"- Neutral: {n_neutral}/10")
    report.append(f"- Moderate negative: {n_moderate_neg}/10")
    report.append(f"- Strong negative (τ < -0.5): {n_negative}/10")
    report.append("")

    report.append("---")
    report.append("*Generated by Phase 10C Complete G&K Replication*")

    return "\n".join(report)


def main():
    """Main execution."""
    print("=" * 70)
    print("PHASE 10C COMPLETE: G&K FULL METHODOLOGY REPLICATION")
    print("=" * 70)
    print(f"Parameters: W={W}, P={P}, Point Cloud={POINT_CLOUD_WINDOW} (FIXED)")
    print(f"Statistics: {len(STATISTICS)}")
    print(f"Events: {len(EVENTS)}")
    print(f"Total τ values to compute: {len(STATISTICS) * len(EVENTS)}")
    print("")

    ensure_dirs()

    # Fetch/load norms
    norms_df = fetch_or_load_norms()

    # Compute rolling statistics
    print("\nComputing rolling statistics...")
    stats_df = compute_rolling_statistics(norms_df, window_size=W)

    # Compute all τ values
    results_df = compute_all_tau_values(stats_df)

    # Save results
    csv_file = OUTPUT_DIR / "gk_complete_replication.csv"
    results_df.to_csv(csv_file, index=False)
    print(f"\nSaved complete results to: {csv_file}")

    # Generate report
    report = generate_report(results_df)
    report_file = OUTPUT_DIR / "complete_replication_report.md"
    report_file.write_text(report, encoding="utf-8")
    print(f"Saved report to: {report_file}")

    # Summary
    print("\n" + "=" * 70)
    print("COMPLETE REPLICATION SUMMARY")
    print("=" * 70)

    print("\nL² Variance τ (Primary G&K Metric):")
    for _, row in results_df.iterrows():
        tau = row.get("L2_var_tau", np.nan)
        if pd.notna(tau):
            if tau > 0.5:
                status = "✅"
            elif tau > 0.3:
                status = "~"
            elif tau < -0.5:
                status = "❌"
            else:
                status = "○"
            print(f"  {row['event']:20s}: τ = {tau:+.3f} {status}")
        else:
            print(f"  {row['event']:20s}: N/A")

    print("\n" + "=" * 70)
    print("PHASE 10C COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
