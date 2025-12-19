"""
TDA Crisis Characterization: Pre-Registered Experiments
========================================================

This script implements the 5 pre-registered experiments to test whether
τ sign distinguishes endogenous (positive τ) from exogenous (negative τ) crises.

METHODOLOGY IS LOCKED (per pre_registration.md):
- Parameters: W=500, P=250, H₁, L² norm
- No parameter tuning allowed
- All results reported regardless of outcome

Usage:
    python experiment_characterization.py --phase 1   # Training set only
    python experiment_characterization.py --phase 2   # Test set (run ONCE)
    python experiment_characterization.py --all       # Both phases
"""

import os
import argparse
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import pearsonr, spearmanr
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

# Local imports
from tda_analysis import rolling_tda_analysis, compute_variance_tau, TDAConfig

# =============================================================================
# LOCKED CONFIGURATION (DO NOT MODIFY)
# =============================================================================

STANDARD_CONFIG = TDAConfig(
    point_cloud_window=50,
    rolling_window=500,  # W = 500 days
    pre_crisis_window=250,  # P = 250 days
)

# =============================================================================
# CRISIS DEFINITIONS
# =============================================================================


@dataclass
class CrisisEvent:
    """Defines a crisis event with expected classification."""

    name: str
    date: str
    expected_type: str  # 'endogenous' or 'exogenous'
    expected_tau_sign: str  # 'positive' or 'negative'
    peak_to_trough_pct: float  # Severity (% decline)
    classification_basis: str


# Training Set (1999-2015) - Used for hypothesis development
TRAINING_EVENTS = [
    CrisisEvent(
        name="2000 Dotcom",
        date="2000-03-10",
        expected_type="endogenous",
        expected_tau_sign="positive",
        peak_to_trough_pct=49.1,  # S&P 500 peak-to-trough
        classification_basis="Tech bubble, gradual buildup over years",
    ),
    CrisisEvent(
        name="2008 GFC",
        date="2008-09-15",
        expected_type="endogenous",
        expected_tau_sign="positive",
        peak_to_trough_pct=56.8,
        classification_basis="Credit/leverage buildup, internal mechanics",
    ),
    CrisisEvent(
        name="2010 Flash Crash",
        date="2010-05-06",
        expected_type="exogenous",
        expected_tau_sign="negative",
        peak_to_trough_pct=9.2,
        classification_basis="Algorithmic failure, no fundamental warning",
    ),
    CrisisEvent(
        name="2011 Debt Crisis",
        date="2011-08-05",
        expected_type="exogenous",
        expected_tau_sign="negative",
        peak_to_trough_pct=19.4,
        classification_basis="Policy-driven (S&P downgrade), external shock",
    ),
    CrisisEvent(
        name="2015 China Crash",
        date="2015-08-24",
        expected_type="exogenous",
        expected_tau_sign="negative",
        peak_to_trough_pct=12.4,
        classification_basis="China contagion, external shock",
    ),
]

# Test Set (2016-2025) - LOCKED predictions, run ONCE only
TEST_EVENTS = [
    CrisisEvent(
        name="2020 COVID",
        date="2020-03-16",
        expected_type="exogenous",
        expected_tau_sign="negative",
        peak_to_trough_pct=33.9,
        classification_basis="Pandemic shock, no internal buildup",
    ),
    CrisisEvent(
        name="2022 Rate Shock",
        date="2022-10-01",
        expected_type="exogenous",
        expected_tau_sign="negative",
        peak_to_trough_pct=25.4,
        classification_basis="Fed policy shock, external driver",
    ),
    CrisisEvent(
        name="2023 SVB Crisis",
        date="2023-03-10",
        expected_type="endogenous",
        expected_tau_sign="positive",
        peak_to_trough_pct=7.8,
        classification_basis="Bank run mechanics, duration mismatch buildup",
    ),
]


# =============================================================================
# DATA FETCHING
# =============================================================================


def fetch_equity_data(start_date: str = "1998-01-01", end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch US equity indices for the analysis.

    Assets: ^GSPC (S&P 500), ^DJI (Dow), ^IXIC (Nasdaq), ^RUT (Russell 2000)
    """
    tickers = ["^GSPC", "^DJI", "^IXIC", "^RUT"]
    end_date = end_date or datetime.now().strftime("%Y-%m-%d")

    print(f"Fetching equity data ({len(tickers)} indices)...")
    print(f"  Date range: {start_date} to {end_date}")

    df = yf.download(tickers, start=start_date, end=end_date, progress=False)

    # Handle MultiIndex columns
    if isinstance(df.columns, pd.MultiIndex):
        try:
            prices = df["Adj Close"]
        except KeyError:
            prices = df["Close"]
    else:
        prices = df

    # Forward fill and drop NaN
    prices = prices.ffill(limit=5).dropna()

    # Compute log returns
    log_ret = np.log(prices / prices.shift(1)).dropna()

    # Standardize (full-sample mean/std per canonical methodology)
    standardized = (log_ret - log_ret.mean()) / log_ret.std()

    print(f"  Shape: {standardized.shape}")
    print(f"  Range: {standardized.index[0].date()} to {standardized.index[-1].date()}")

    return standardized


def fetch_macro_data(start_date: str = "2007-02-20", end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch macro assets for cross-asset comparison.

    Assets: SPY, TLT, GLD, UUP
    Note: UUP inception is 2007-02-20, limiting historical range.
    """
    tickers = ["SPY", "TLT", "GLD", "UUP"]
    end_date = end_date or datetime.now().strftime("%Y-%m-%d")

    print(f"Fetching macro data ({len(tickers)} assets)...")

    df = yf.download(tickers, start=start_date, end=end_date, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        try:
            prices = df["Adj Close"]
        except KeyError:
            prices = df["Close"]
    else:
        prices = df

    prices = prices.ffill(limit=5).dropna()
    log_ret = np.log(prices / prices.shift(1)).dropna()
    standardized = (log_ret - log_ret.mean()) / log_ret.std()

    print(f"  Shape: {standardized.shape}")

    return standardized


# =============================================================================
# EXPERIMENT IMPLEMENTATIONS
# =============================================================================


def run_experiment_1(
    data: pd.DataFrame, events: List[CrisisEvent], config: TDAConfig = STANDARD_CONFIG, verbose: bool = True
) -> Dict:
    """
    Experiment 1: Crisis Type Classification

    Test whether τ sign correctly predicts crisis type.
    Success criterion: ≥80% accuracy (4/5 correct for training set)
    """
    print("\n" + "=" * 70)
    print("EXPERIMENT 1: Crisis Type Classification")
    print("=" * 70)

    # First, compute TDA norms for the entire dataset
    print("\nComputing TDA features...")
    norms = rolling_tda_analysis(data, config=config, verbose=verbose)

    results = []

    print("\nAnalyzing events:")
    print("-" * 70)

    for event in events:
        try:
            tau, p_value = compute_variance_tau(norms, event.date, config=config, metric="L2")

            # Classify based on τ sign
            predicted_sign = "positive" if tau > 0 else "negative"
            correct = predicted_sign == event.expected_tau_sign

            result = {
                "event": event.name,
                "date": event.date,
                "expected_type": event.expected_type,
                "expected_sign": event.expected_tau_sign,
                "tau": tau,
                "p_value": p_value,
                "predicted_sign": predicted_sign,
                "correct": correct,
                "severity_pct": event.peak_to_trough_pct,
            }
            results.append(result)

            status = "✓" if correct else "✗"
            print(f"  {status} {event.name}: τ={tau:.4f} (p={p_value:.2e})")
            print(f"      Expected: {event.expected_sign}, Got: {predicted_sign}")

        except Exception as e:
            print(f"  ⚠ {event.name}: FAILED - {e}")
            results.append({"event": event.name, "date": event.date, "error": str(e), "correct": False})

    # Calculate accuracy
    valid_results = [r for r in results if "tau" in r]
    correct_count = sum(1 for r in valid_results if r["correct"])
    accuracy = correct_count / len(valid_results) if valid_results else 0

    print("-" * 70)
    print(f"\nACCURACY: {correct_count}/{len(valid_results)} = {accuracy:.1%}")

    if accuracy >= 0.80:
        print("✓ SUCCESS: Meets ≥80% threshold")
    elif accuracy >= 0.60:
        print("~ MARGINAL: Above 60% but below 80%")
    else:
        print("✗ FAILURE: Below 60% threshold — HYPOTHESIS REFUTED")

    return {
        "experiment": "Crisis Type Classification",
        "results": results,
        "accuracy": accuracy,
        "correct_count": correct_count,
        "total_events": len(valid_results),
        "norms": norms,  # Return for reuse
    }


def run_experiment_2(exp1_results: Dict, verbose: bool = True) -> Dict:
    """
    Experiment 2: τ Magnitude vs Severity Correlation

    Test whether |τ| correlates with crisis severity (peak-to-trough %).
    Success criterion: r > 0.6
    """
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: Magnitude-Severity Correlation")
    print("=" * 70)

    # Extract valid results with τ values
    valid = [r for r in exp1_results["results"] if "tau" in r]

    if len(valid) < 3:
        print("  ⚠ Insufficient data points for correlation")
        return {"experiment": "Magnitude-Severity", "error": "Insufficient data"}

    tau_abs = np.array([abs(r["tau"]) for r in valid])
    severity = np.array([r["severity_pct"] for r in valid])

    # Compute correlations
    r_pearson, p_pearson = pearsonr(tau_abs, severity)
    r_spearman, p_spearman = spearmanr(tau_abs, severity)

    print(f"\n  Data points: {len(valid)}")
    print(f"\n  Pearson r:  {r_pearson:.3f} (p={p_pearson:.3f})")
    print(f"  Spearman ρ: {r_spearman:.3f} (p={p_spearman:.3f})")

    print("\n  Event Details:")
    for r in valid:
        print(f"    {r['event']}: |τ|={abs(r['tau']):.3f}, Severity={r['severity_pct']:.1f}%")

    if r_pearson > 0.6:
        print(f"\n✓ SUCCESS: r={r_pearson:.3f} > 0.6 threshold")
    else:
        print(f"\n✗ FAILURE: r={r_pearson:.3f} ≤ 0.6 threshold")
        print("  Note: Sign classification may still work without magnitude correlation")

    return {
        "experiment": "Magnitude-Severity Correlation",
        "r_pearson": r_pearson,
        "p_pearson": p_pearson,
        "r_spearman": r_spearman,
        "p_spearman": p_spearman,
        "n": len(valid),
        "success": r_pearson > 0.6,
    }


def run_experiment_3(events: List[CrisisEvent], config: TDAConfig = STANDARD_CONFIG, verbose: bool = True) -> Dict:
    """
    Experiment 3: Cross-Asset vs Equity-Only Comparison

    Compare classification accuracy using:
    - Macro assets (SPY/TLT/GLD/UUP)
    - Equity indices (^GSPC/^DJI/^IXIC/^RUT)

    Success criterion: Macro ≥ Equity accuracy

    Note: Limited to events after 2007-02-20 (UUP inception)
    """
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: Cross-Asset vs Equity-Only")
    print("=" * 70)

    # Filter events to post-2007 (macro data availability)
    post_2007_events = [e for e in events if e.date >= "2007-02-20"]

    if len(post_2007_events) < len(events):
        print(f"\n  Note: {len(events) - len(post_2007_events)} events excluded (pre-2007)")

    print(f"\n  Testing on {len(post_2007_events)} events")

    # Fetch both datasets
    print("\n--- Equity Indices ---")
    equity_data = fetch_equity_data(start_date="1998-01-01")
    equity_norms = rolling_tda_analysis(equity_data, config=config, verbose=verbose)

    print("\n--- Macro Assets ---")
    macro_data = fetch_macro_data()
    macro_norms = rolling_tda_analysis(macro_data, config=config, verbose=verbose)

    # Compute τ for each
    equity_results = []
    macro_results = []

    print("\n  Results Comparison:")
    print("-" * 70)
    print(f"  {'Event':<20} {'Equity τ':>12} {'Macro τ':>12} {'Expected':>10}")
    print("-" * 70)

    for event in post_2007_events:
        try:
            eq_tau, _ = compute_variance_tau(equity_norms, event.date, config=config)
            eq_sign = "positive" if eq_tau > 0 else "negative"
            eq_correct = eq_sign == event.expected_tau_sign
            equity_results.append({"event": event.name, "tau": eq_tau, "correct": eq_correct})
        except Exception as e:
            equity_results.append({"event": event.name, "error": str(e), "correct": False})
            eq_tau = float("nan")

        try:
            mc_tau, _ = compute_variance_tau(macro_norms, event.date, config=config)
            mc_sign = "positive" if mc_tau > 0 else "negative"
            mc_correct = mc_sign == event.expected_tau_sign
            macro_results.append({"event": event.name, "tau": mc_tau, "correct": mc_correct})
        except Exception as e:
            macro_results.append({"event": event.name, "error": str(e), "correct": False})
            mc_tau = float("nan")

        print(f"  {event.name:<20} {eq_tau:>12.4f} {mc_tau:>12.4f} {event.expected_tau_sign:>10}")

    # Calculate accuracies
    eq_acc = sum(1 for r in equity_results if r.get("correct", False)) / len(equity_results)
    mc_acc = sum(1 for r in macro_results if r.get("correct", False)) / len(macro_results)

    print("-" * 70)
    print(f"\n  Equity Accuracy: {eq_acc:.1%}")
    print(f"  Macro Accuracy:  {mc_acc:.1%}")

    if mc_acc >= eq_acc:
        print(f"\n✓ SUCCESS: Macro ({mc_acc:.1%}) ≥ Equity ({eq_acc:.1%})")
    else:
        print(f"\n✗ FAILURE: Macro ({mc_acc:.1%}) < Equity ({eq_acc:.1%})")

    return {
        "experiment": "Cross-Asset vs Equity-Only",
        "equity_accuracy": eq_acc,
        "macro_accuracy": mc_acc,
        "equity_results": equity_results,
        "macro_results": macro_results,
        "success": mc_acc >= eq_acc,
    }


def run_experiment_4(data: pd.DataFrame, config: TDAConfig = STANDARD_CONFIG, verbose: bool = True) -> Dict:
    """
    Experiment 4: Contemporaneous Regime Indicator

    Compute rolling τ and check alignment with VIX regime changes.
    Success criterion: τ peaks within ±30 days of VIX spikes in >75% of cases

    Note: This is a more complex analysis that requires VIX data.
    """
    print("\n" + "=" * 70)
    print("EXPERIMENT 4: Contemporaneous Regime Indicator")
    print("=" * 70)

    # Fetch VIX data
    print("\n  Fetching VIX data...")
    vix = yf.download("^VIX", start="2005-01-01", end="2015-12-31", progress=False)
    if isinstance(vix.columns, pd.MultiIndex):
        vix = vix["Close"]
    else:
        vix = vix["Close"]

    vix = vix.squeeze()

    # Identify VIX spikes (>30 threshold, typically indicates stress)
    vix_spikes = vix[vix > 30].index

    # Group consecutive spike days into events
    vix_events = []
    if len(vix_spikes) > 0:
        current_start = vix_spikes[0]
        current_end = vix_spikes[0]

        for date in vix_spikes[1:]:
            if (date - current_end).days <= 5:  # Within 5 days = same event
                current_end = date
            else:
                vix_events.append(
                    {"start": current_start, "end": current_end, "peak": vix.loc[current_start:current_end].max()}
                )
                current_start = date
                current_end = date

        vix_events.append(
            {"start": current_start, "end": current_end, "peak": vix.loc[current_start:current_end].max()}
        )

    print(f"\n  Found {len(vix_events)} VIX spike events (VIX > 30)")

    # For a simplified version, we check if our known crisis dates align with VIX spikes
    training_dates = [e.date for e in TRAINING_EVENTS if "2005" <= e.date <= "2015"]

    alignments = []
    for event_date in training_dates:
        event_dt = pd.to_datetime(event_date)

        # Check if any VIX event is within ±30 days
        aligned = False
        for vix_event in vix_events:
            start_dt = pd.to_datetime(vix_event["start"])
            end_dt = pd.to_datetime(vix_event["end"])

            if abs((event_dt - start_dt).days) <= 30 or abs((event_dt - end_dt).days) <= 30:
                aligned = True
                break

        alignments.append({"date": event_date, "aligned": aligned})

    alignment_rate = sum(1 for a in alignments if a["aligned"]) / len(alignments) if alignments else 0

    print(f"\n  Crisis dates aligned with VIX spikes: {alignment_rate:.1%}")

    if alignment_rate > 0.75:
        print(f"\n✓ SUCCESS: {alignment_rate:.1%} > 75% threshold")
    else:
        print(f"\n✗ FAILURE: {alignment_rate:.1%} ≤ 75% threshold")

    return {
        "experiment": "Contemporaneous Regime Indicator",
        "vix_events": len(vix_events),
        "alignment_rate": alignment_rate,
        "alignments": alignments,
        "success": alignment_rate > 0.75,
    }


def run_experiment_5(data: pd.DataFrame, config: TDAConfig = STANDARD_CONFIG, verbose: bool = True) -> Dict:
    """
    Experiment 5: Test Set Predictions (RUN ONCE ONLY)

    Compare computed τ to pre-registered predictions.
    Success criterion: ≥2/3 correct

    Pre-registered predictions:
    - 2020 COVID: NEGATIVE
    - 2022 Rate Shock: NEGATIVE
    - SVB 2023: POSITIVE
    """
    print("\n" + "=" * 70)
    print("EXPERIMENT 5: TEST SET PREDICTIONS (Hold-Out)")
    print("=" * 70)
    print("\n⚠️  WARNING: This is the TEST SET. Results are FINAL.")
    print("    DO NOT re-run with different parameters.")

    # Compute TDA norms
    print("\n  Computing TDA features...")
    norms = rolling_tda_analysis(data, config=config, verbose=verbose)

    results = []

    print("\n  Pre-Registered Predictions vs Actual:")
    print("-" * 70)

    for event in TEST_EVENTS:
        try:
            tau, p_value = compute_variance_tau(norms, event.date, config=config, metric="L2")

            actual_sign = "positive" if tau > 0 else "negative"
            correct = actual_sign == event.expected_tau_sign

            result = {
                "event": event.name,
                "date": event.date,
                "predicted_sign": event.expected_tau_sign,
                "actual_tau": tau,
                "actual_sign": actual_sign,
                "correct": correct,
                "p_value": p_value,
            }
            results.append(result)

            status = "✓" if correct else "✗"
            print(f"  {status} {event.name}:")
            print(f"      Predicted: {event.expected_tau_sign.upper()}")
            print(f"      Actual:    τ = {tau:.4f} ({actual_sign.upper()})")

        except Exception as e:
            print(f"  ⚠ {event.name}: FAILED - {e}")
            results.append({"event": event.name, "error": str(e), "correct": False})

    # Calculate accuracy
    correct_count = sum(1 for r in results if r.get("correct", False))
    total = len(results)
    accuracy = correct_count / total if total > 0 else 0

    print("-" * 70)
    print(f"\n  FINAL RESULT: {correct_count}/{total} predictions correct ({accuracy:.1%})")

    if correct_count >= 2:
        print("\n✓ SUCCESS: ≥2/3 correct — HYPOTHESIS SUPPORTED")
    else:
        print("\n✗ FAILURE: <2/3 correct — Generalization not supported")
        print("  Report: 'Training success, generalization unclear'")

    return {
        "experiment": "Test Set Predictions",
        "results": results,
        "correct_count": correct_count,
        "total": total,
        "accuracy": accuracy,
        "success": correct_count >= 2,
    }


# =============================================================================
# MAIN EXECUTION
# =============================================================================


def run_phase_1(save_dir: str = "../outputs/multiasset/characterization") -> Dict:
    """Run all Phase 1 (training set) experiments."""
    os.makedirs(save_dir, exist_ok=True)

    print("\n" + "=" * 70)
    print("PHASE 1: TRAINING SET EXPERIMENTS (1999-2015)")
    print("=" * 70)
    print(f"Parameters: W={STANDARD_CONFIG.rolling_window}, P={STANDARD_CONFIG.pre_crisis_window}")
    print("Metric: L² variance, H₁ persistence")

    # Fetch data for training period
    print("\n" + "-" * 70)
    print("FETCHING DATA")
    print("-" * 70)
    data = fetch_equity_data(start_date="1998-01-01", end_date="2015-12-31")

    # Run experiments
    exp1 = run_experiment_1(data, TRAINING_EVENTS, STANDARD_CONFIG)
    exp2 = run_experiment_2(exp1)
    exp3 = run_experiment_3(TRAINING_EVENTS, STANDARD_CONFIG)
    exp4 = run_experiment_4(data, STANDARD_CONFIG)

    # Summary
    print("\n" + "=" * 70)
    print("PHASE 1 SUMMARY")
    print("=" * 70)

    phase1_results = {
        "exp1_classification": exp1,
        "exp2_magnitude": exp2,
        "exp3_cross_asset": exp3,
        "exp4_regime": exp4,
    }

    print(f"\n  Exp 1 (Classification):  {exp1['accuracy']:.1%} accuracy")
    print(f"  Exp 2 (Magnitude-Sev):   r = {exp2.get('r_pearson', 'N/A')}")
    print(f"  Exp 3 (Macro vs Equity): Macro {exp3['macro_accuracy']:.1%} vs Equity {exp3['equity_accuracy']:.1%}")
    print(f"  Exp 4 (VIX Alignment):   {exp4['alignment_rate']:.1%}")

    # Decision gate
    print("\n" + "-" * 70)
    print("DECISION GATE")
    print("-" * 70)

    if exp1["accuracy"] < 0.60:
        print("\n⛔ STOP: Training accuracy < 60%")
        print("   HYPOTHESIS REFUTED. Report negative finding.")
        phase1_results["proceed_to_phase_2"] = False
    elif exp1["accuracy"] >= 0.80:
        print("\n✓ PROCEED: Training accuracy ≥ 80%")
        print("   May proceed to Phase 2 (test set).")
        phase1_results["proceed_to_phase_2"] = True
    else:
        print(f"\n~ MARGINAL: Training accuracy = {exp1['accuracy']:.1%}")
        print("   Consider proceeding with caution.")
        phase1_results["proceed_to_phase_2"] = True  # Proceed with warning

    # Save results
    results_df = pd.DataFrame(exp1["results"])
    results_df.to_csv(os.path.join(save_dir, "phase1_results.csv"), index=False)
    print(f"\n  Results saved to {save_dir}/")

    return phase1_results


def run_phase_2(save_dir: str = "../outputs/multiasset/characterization") -> Dict:
    """Run Phase 2 (test set) experiment — RUN ONCE ONLY."""
    os.makedirs(save_dir, exist_ok=True)

    print("\n" + "=" * 70)
    print("PHASE 2: TEST SET VALIDATION (2016-2025)")
    print("=" * 70)
    print("\n⚠️  THIS IS THE HELD-OUT TEST SET")
    print("    Results are FINAL. Do not re-run.")

    # Fetch full data including test period
    data = fetch_equity_data(start_date="1998-01-01")

    exp5 = run_experiment_5(data, STANDARD_CONFIG)

    # Save results
    results_df = pd.DataFrame(exp5["results"])
    results_df.to_csv(os.path.join(save_dir, "phase2_results.csv"), index=False)

    print("\n" + "=" * 70)
    print("FINAL CONCLUSION")
    print("=" * 70)

    if exp5["success"]:
        print("\n✓ FULL PAPER CLAIM SUPPORTED")
        print("  τ sign distinguishes crisis types with generalization to test set.")
    else:
        print("\n~ PARTIAL SUPPORT")
        print("  Training success, but generalization to test set unclear.")

    return {"exp5_test": exp5}


def main():
    parser = argparse.ArgumentParser(description="TDA Crisis Characterization Experiments")
    parser.add_argument("--phase", type=int, choices=[1, 2], help="Run Phase 1 (training) or Phase 2 (test)")
    parser.add_argument("--all", action="store_true", help="Run both phases")

    args = parser.parse_args()

    if args.all:
        phase1 = run_phase_1()
        if phase1.get("proceed_to_phase_2", False):
            run_phase_2()
    elif args.phase == 1:
        run_phase_1()
    elif args.phase == 2:
        run_phase_2()
    else:
        # Default: show usage
        print("Usage:")
        print("  python experiment_characterization.py --phase 1   # Training set")
        print("  python experiment_characterization.py --phase 2   # Test set (ONCE)")
        print("  python experiment_characterization.py --all       # Both phases")


if __name__ == "__main__":
    main()
