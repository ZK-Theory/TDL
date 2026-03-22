"""
Phase 10C: Extended Crisis Validation
======================================

Purpose:
    Validate the τ sign hypothesis on 7 additional historical crises:
    - Positive τ → Endogenous (systemic buildup)
    - Negative τ → Exogenous (external shock)

Crises:
    Expected Positive: 1997 Asian, 2000 Dotcom, 2011 EU Debt
    Expected Negative: 9/11, 2015 China, Brexit
    Ambiguous: 2010 Flash Crash

Parameters (LOCKED - NO TUNING):
    W = 500 (Rolling Variance Window)
    P = 250 (Pre-Crisis Trend Window)
    Homology: H1
    Norm: L² variance

Author: Phase 10C Implementation
Date: 2025-12-17
"""

import pandas as pd
import numpy as np
import yfinance as yf
from scipy.stats import kendalltau
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

# Import TDA pipeline
from financial_tda.validation.gidea_katz_replication import fetch_historical_data, compute_persistence_landscape_norms
from financial_tda.validation.trend_analysis_validator import compute_gk_rolling_statistics

# ============================================================================
# CONFIGURATION (LOCKED - NO P-HACKING)
# ============================================================================
W = 500  # Rolling Variance Window
P = 250  # Pre-Crisis Trend Window
POINT_CLOUD_WINDOW = 50

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = BASE_DIR / "outputs" / "phase_10c"
NORMS_CACHE = OUTPUT_DIR / "norms_cache_1996_2017.csv"

# Crisis definitions
CRISES = [
    # Expected Positive (Endogenous)
    {
        "name": "1997 Asian Crisis",
        "date": "1997-10-27",
        "expected_sign": "positive",
        "rationale": "Currency/debt contagion, systemic buildup",
    },
    {
        "name": "2000 Dotcom",
        "date": "2000-03-10",
        "expected_sign": "positive",
        "rationale": "Valuation bubble, gradual buildup",
    },
    {
        "name": "2011 EU Debt",
        "date": "2011-08-08",
        "expected_sign": "positive",
        "rationale": "Sovereign debt contagion, systemic",
    },
    # Expected Negative (Exogenous)
    {
        "name": "9/11 Attacks",
        "date": "2001-09-11",
        "expected_sign": "negative",
        "rationale": "External shock, sudden",
    },
    {
        "name": "2015 China Devaluation",
        "date": "2015-08-24",
        "expected_sign": "negative",
        "rationale": "External policy shock",
    },
    {
        "name": "Brexit Vote",
        "date": "2016-06-24",
        "expected_sign": "negative",
        "rationale": "External political shock",
    },
    # Ambiguous
    {
        "name": "2010 Flash Crash",
        "date": "2010-05-06",
        "expected_sign": "neutral",
        "rationale": "Too fast (intraday), likely τ ≈ 0",
    },
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

    print("Fetching historical data (1996-2017)...")

    # Fetch data
    # Need extra buffer before earliest crisis (1997) for W=500 + P=250
    start_date = "1994-01-01"
    end_date = "2017-06-30"

    prices_dict = fetch_historical_data(start_date, end_date)

    print("Computing persistence landscape norms...")
    norms_df = compute_persistence_landscape_norms(
        prices=prices_dict, window_size=POINT_CLOUD_WINDOW, stride=1, n_layers=5
    )

    # Cache
    norms_df.to_csv(NORMS_CACHE)
    print(f"  Cached norms to: {NORMS_CACHE}")

    return norms_df


def compute_tau_for_date(stats_df, event_date):
    """Compute Kendall-tau for P days before event date."""
    event_date = pd.to_datetime(event_date)

    # Ensure index is DatetimeIndex
    if not isinstance(stats_df.index, pd.DatetimeIndex):
        stats_df.index = pd.to_datetime(stats_df.index)

    # Find the nearest date in the index
    date_diffs = abs(stats_df.index - event_date)
    event_loc = date_diffs.argmin()
    event_date = stats_df.index[event_loc]

    # Check if we have enough data
    if event_loc < P:
        return None, None, "Insufficient pre-event data"

    # Extract P-day window before event
    segment = stats_df["L2_norm_variance"].iloc[event_loc - P : event_loc]

    # Check for NaNs
    if segment.isna().any():
        valid_count = (~segment.isna()).sum()
        if valid_count < P * 0.9:
            return None, None, f"Too many NaNs ({P - valid_count}/{P})"

    # Compute Kendall-tau
    x = np.arange(len(segment))
    tau, p_value = kendalltau(x, segment.values, nan_policy="omit")

    return tau, p_value, None


def compute_forward_metrics(spx_close, event_date):
    """Compute forward returns and drawdowns after event."""
    event_date = pd.to_datetime(event_date)

    # Ensure index is DatetimeIndex
    if not isinstance(spx_close.index, pd.DatetimeIndex):
        spx_close.index = pd.to_datetime(spx_close.index)

    # Find the nearest date in the index
    date_diffs = abs(spx_close.index - event_date)
    event_loc = date_diffs.argmin()
    current_price = spx_close.iloc[event_loc]

    metrics = {}
    for window in [30, 60, 90]:
        future_loc = min(event_loc + window, len(spx_close) - 1)
        if future_loc > event_loc:
            future_price = spx_close.iloc[future_loc]
            # Forward return
            metrics[f"fwd_ret_{window}d"] = (future_price - current_price) / current_price
            # Max drawdown
            window_prices = spx_close.iloc[event_loc : future_loc + 1]
            min_price = window_prices.min()
            metrics[f"max_dd_{window}d"] = (current_price - min_price) / current_price
        else:
            metrics[f"fwd_ret_{window}d"] = np.nan
            metrics[f"max_dd_{window}d"] = np.nan

    return metrics


def validate_crises(norms_df):
    """Validate all crises and compute results."""
    print("\nComputing rolling statistics...")
    stats_df = compute_gk_rolling_statistics(norms_df, window_size=W)

    # Fetch S&P 500 for forward metrics
    print("Fetching S&P 500 for forward metrics...")
    spx = yf.download("^GSPC", start="1996-01-01", end="2017-12-31", progress=False)
    if isinstance(spx.columns, pd.MultiIndex):
        spx.columns = spx.columns.get_level_values(0)
    spx_close = spx["Close"]

    results = []

    print("\nValidating crises:")
    print("-" * 60)

    for crisis in CRISES:
        print(f"\n{crisis['name']} ({crisis['date']})...")

        # Compute tau
        tau, p_value, error = compute_tau_for_date(stats_df, crisis["date"])

        if error:
            print(f"  ERROR: {error}")
            result = {
                "name": crisis["name"],
                "date": crisis["date"],
                "expected_sign": crisis["expected_sign"],
                "rationale": crisis["rationale"],
                "tau": np.nan,
                "p_value": np.nan,
                "actual_sign": "error",
                "correct": False,
                "error": error,
            }
        else:
            # Determine actual sign
            if abs(tau) < 0.3:
                actual_sign = "neutral"
            elif tau > 0:
                actual_sign = "positive"
            else:
                actual_sign = "negative"

            # Check if prediction is correct
            if crisis["expected_sign"] == "neutral":
                correct = abs(tau) < 0.3
            else:
                correct = actual_sign == crisis["expected_sign"]

            print(f"  τ = {tau:.3f} (p={p_value:.4f})")
            print(f"  Expected: {crisis['expected_sign']}, Actual: {actual_sign}")
            print(f"  Correct: {'✅' if correct else '❌'}")

            result = {
                "name": crisis["name"],
                "date": crisis["date"],
                "expected_sign": crisis["expected_sign"],
                "rationale": crisis["rationale"],
                "tau": tau,
                "p_value": p_value,
                "actual_sign": actual_sign,
                "correct": correct,
                "error": None,
            }

            # Add forward metrics
            fwd_metrics = compute_forward_metrics(spx_close, crisis["date"])
            result.update(fwd_metrics)

        results.append(result)

    return pd.DataFrame(results)


def generate_report(results_df):
    """Generate markdown validation report."""
    report = []
    report.append("# Phase 10C: Extended Crisis Validation Report")
    report.append("")
    report.append(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")

    report.append("## Objective")
    report.append("")
    report.append("Validate the τ sign hypothesis on additional historical crises:")
    report.append("- **Positive τ** → Endogenous crisis (systemic buildup)")
    report.append("- **Negative τ** → Exogenous crisis (external shock)")
    report.append("")

    report.append("## Results Summary")
    report.append("")

    # Count correct predictions
    valid_results = results_df[results_df["error"].isna()]
    n_total = len(valid_results)
    n_correct = valid_results["correct"].sum()

    report.append(f"**Predictions correct: {n_correct}/{n_total}**")
    report.append("")

    if n_correct >= 5:
        report.append("> [!IMPORTANT]")
        report.append("> **Strong support** for the τ sign hypothesis (≥5/7 correct)")
    elif n_correct >= 4:
        report.append("> [!NOTE]")
        report.append("> **Moderate support** for the τ sign hypothesis (4/7 correct)")
    else:
        report.append("> [!WARNING]")
        report.append("> **Weak support** - hypothesis may be too simplistic (≤3/7 correct)")
    report.append("")

    report.append("## Detailed Results")
    report.append("")
    report.append("| Crisis | Date | Expected | τ Value | Actual | Correct? |")
    report.append("|--------|------|----------|---------|--------|----------|")

    for _, row in results_df.iterrows():
        if pd.isna(row["tau"]):
            tau_str = "ERROR"
            actual_str = row.get("error", "Unknown")[:20]
        else:
            tau_str = f"{row['tau']:.3f}"
            actual_str = row["actual_sign"]

        correct_str = "✅" if row["correct"] else "❌"
        report.append(
            f"| {row['name']} | {row['date']} | {row['expected_sign']} | {tau_str} | {actual_str} | {correct_str} |"
        )

    report.append("")

    # Expected Positive analysis
    report.append("## Analysis by Expected Sign")
    report.append("")
    report.append("### Expected Positive (Endogenous)")
    report.append("")
    pos_expected = results_df[results_df["expected_sign"] == "positive"]
    pos_correct = pos_expected["correct"].sum()
    report.append(f"Correct: {pos_correct}/{len(pos_expected)}")
    report.append("")
    for _, row in pos_expected.iterrows():
        if pd.notna(row["tau"]):
            status = "✅" if row["correct"] else "❌"
            report.append(f"- **{row['name']}:** τ = {row['tau']:.3f} {status}")
            report.append(f"  - Rationale: {row['rationale']}")
    report.append("")

    report.append("### Expected Negative (Exogenous)")
    report.append("")
    neg_expected = results_df[results_df["expected_sign"] == "negative"]
    neg_correct = neg_expected["correct"].sum()
    report.append(f"Correct: {neg_correct}/{len(neg_expected)}")
    report.append("")
    for _, row in neg_expected.iterrows():
        if pd.notna(row["tau"]):
            status = "✅" if row["correct"] else "❌"
            report.append(f"- **{row['name']}:** τ = {row['tau']:.3f} {status}")
            report.append(f"  - Rationale: {row['rationale']}")
    report.append("")

    report.append("### Ambiguous")
    report.append("")
    neutral_expected = results_df[results_df["expected_sign"] == "neutral"]
    for _, row in neutral_expected.iterrows():
        if pd.notna(row["tau"]):
            status = "✅" if row["correct"] else "❌"
            report.append(f"- **{row['name']}:** τ = {row['tau']:.3f} {status}")
            report.append(f"  - Expected near-zero, got: {row['actual_sign']}")
    report.append("")

    # Forward metrics
    report.append("## Forward Performance After Events")
    report.append("")
    report.append("| Crisis | 30d Return | 60d Return | 90d Return | Max DD 30d |")
    report.append("|--------|------------|------------|------------|------------|")
    for _, row in results_df.iterrows():
        if pd.notna(row.get("fwd_ret_30d")):
            ret_30 = f"{row['fwd_ret_30d']*100:.1f}%"
            ret_60 = f"{row['fwd_ret_60d']*100:.1f}%"
            ret_90 = f"{row['fwd_ret_90d']*100:.1f}%"
            dd_30 = f"{row['max_dd_30d']*100:.1f}%"
        else:
            ret_30 = ret_60 = ret_90 = dd_30 = "N/A"
        report.append(f"| {row['name']} | {ret_30} | {ret_60} | {ret_90} | {dd_30} |")
    report.append("")

    report.append("## Conclusions")
    report.append("")

    if n_correct >= 5:
        report.append("The τ sign hypothesis is **strongly supported** by extended validation:")
        report.append("")
        report.append("- Endogenous crises (systemic buildup) tend to show positive τ")
        report.append("- Exogenous shocks tend to show negative or near-zero τ")
        report.append("- This provides a potential mechanism for crisis type classification")
    elif n_correct >= 4:
        report.append("The τ sign hypothesis receives **moderate support**:")
        report.append("")
        report.append("- Pattern generally holds but with exceptions")
        report.append("- The characterization framework may need refinement")
    else:
        report.append("The τ sign hypothesis receives **weak support**:")
        report.append("")
        report.append("- The simple positive/negative dichotomy may be too simplistic")
        report.append("- Other factors may influence τ sign")

    report.append("")
    report.append("---")
    report.append("*Generated by Phase 10C Extended Crisis Validation*")

    return "\n".join(report)


def main():
    """Main execution."""
    print("=" * 60)
    print("PHASE 10C: EXTENDED CRISIS VALIDATION")
    print("=" * 60)
    print(f"Parameters: W={W}, P={P} (STRICT - NO TUNING)")
    print("")

    ensure_dirs()

    # Fetch/load norms
    norms_df = fetch_or_load_norms()

    # Validate all crises
    results_df = validate_crises(norms_df)

    # Save raw results
    csv_file = OUTPUT_DIR / "crisis_tau_values.csv"
    results_df.to_csv(csv_file, index=False)
    print(f"\nSaved raw results to: {csv_file}")

    # Generate report
    report = generate_report(results_df)
    report_file = OUTPUT_DIR / "extended_validation_report.md"
    report_file.write_text(report, encoding="utf-8")
    print(f"Saved report to: {report_file}")

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    valid_results = results_df[results_df["error"].isna()]
    n_correct = valid_results["correct"].sum()
    n_total = len(valid_results)

    print(f"\nPredictions correct: {n_correct}/{n_total}")
    print("")

    for _, row in results_df.iterrows():
        if pd.notna(row["tau"]):
            status = "✅" if row["correct"] else "❌"
            print(f"  {row['name']}: τ={row['tau']:.3f} (expected {row['expected_sign']}) {status}")
        else:
            print(f"  {row['name']}: ERROR - {row.get('error', 'Unknown')}")

    print("\n" + "=" * 60)
    print("PHASE 10C COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
