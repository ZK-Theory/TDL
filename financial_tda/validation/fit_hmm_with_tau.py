"""
Phase 10B - Task B.3: HMM Augmented (with τ)
=============================================

Purpose:
    Fit a 3-state Gaussian HMM using returns, VIX, AND τ.
    Compare to baseline to assess if τ improves regime detection.

Input:
    outputs/phase_10b/hmm_features.csv

Output:
    outputs/phase_10b/hmm_tau_states.csv
    outputs/phase_10b/hmm_tau_report.md

Author: Phase 10B Implementation
Date: 2025-12-17
"""

import pandas as pd
import numpy as np
from hmmlearn import hmm
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
FEATURES_FILE = BASE_DIR / "outputs" / "phase_10b" / "hmm_features.csv"
OUTPUT_DIR = BASE_DIR / "outputs" / "phase_10b"
STATES_FILE = OUTPUT_DIR / "hmm_tau_states.csv"
REPORT_FILE = OUTPUT_DIR / "hmm_tau_report.md"

# Known crisis periods for validation
CRISIS_PERIODS = {
    "2008 GFC": ("2008-09-15", "2009-03-09"),
    "2020 COVID": ("2020-02-20", "2020-04-01"),
    "2022 Bear Market": ("2022-06-01", "2022-10-15"),
}

# Model config
N_STATES = 3
N_ITER = 100
RANDOM_STATE = 42


def load_features():
    """Load feature matrix."""
    print(f"Loading features from: {FEATURES_FILE}")
    df = pd.read_csv(FEATURES_FILE, index_col=0, parse_dates=True)
    print(f"  Loaded {len(df)} rows with columns: {list(df.columns)}")
    return df


def prepare_augmented_features(df):
    """Prepare features for augmented model (with τ)."""
    # Augmented: returns + VIX + τ
    augmented_cols = ["ret_1d", "ret_5d", "ret_21d", "vix", "vix_5d_chg", "tau"]
    X = df[augmented_cols].values

    # Standardize features
    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0)
    X_scaled = (X - X_mean) / X_std

    print(f"  Augmented features: {augmented_cols}")
    print(f"  Shape: {X_scaled.shape}")

    return X_scaled, X_mean, X_std


def fit_hmm(X, n_states=N_STATES):
    """Fit Gaussian HMM."""
    print(f"\nFitting {n_states}-state Gaussian HMM (with τ)...")

    model = hmm.GaussianHMM(
        n_components=n_states,
        covariance_type="full",
        n_iter=N_ITER,
        random_state=RANDOM_STATE,
    )

    model.fit(X)

    # Decode states
    states = model.predict(X)
    log_prob = model.score(X)

    # Model metrics (adjusted for 6 features now)
    n_features = X.shape[1]
    n_params = n_states * (n_states - 1) + n_states * n_features + n_states * n_features * (n_features + 1) // 2
    aic = -2 * log_prob + 2 * n_params
    bic = -2 * log_prob + n_params * np.log(len(X))

    print(f"  Converged: {model.monitor_.converged}")
    print(f"  Log-likelihood: {log_prob:.2f}")
    print(f"  AIC: {aic:.2f}")
    print(f"  BIC: {bic:.2f}")

    return model, states, {"log_prob": log_prob, "aic": aic, "bic": bic, "n_params": n_params}


def label_states(model, states, df):
    """Label states as Calm, Transition, Crisis based on characteristics."""
    # Compute mean VIX for each state
    state_vix = []
    for s in range(N_STATES):
        mask = states == s
        mean_vix = df.loc[mask, "vix"].mean()
        mean_ret = df.loc[mask, "ret_1d"].mean()
        mean_tau = df.loc[mask, "tau"].mean()
        state_vix.append((s, mean_vix, mean_ret, mean_tau))

    # Sort by VIX (lowest = Calm, highest = Crisis)
    state_vix.sort(key=lambda x: x[1])

    state_labels = {
        state_vix[0][0]: "Calm",
        state_vix[1][0]: "Transition",
        state_vix[2][0]: "Crisis",
    }

    print("\nState labeling (by mean VIX):")
    for s, vix, ret, tau in state_vix:
        print(f"  State {s} ({state_labels[s]}): VIX={vix:.1f}, Mean Ret={ret*100:.3f}%, Mean τ={tau:.2f}")

    return state_labels


def evaluate_crisis_detection(states, df, state_labels):
    """Evaluate how well states align with known crisis periods."""
    print("\nCrisis Detection Evaluation:")

    # Reverse lookup
    label_to_state = {v: k for k, v in state_labels.items()}
    crisis_state = label_to_state["Crisis"]

    results = {}
    for crisis_name, (start, end) in CRISIS_PERIODS.items():
        # Get states during crisis
        mask = (df.index >= start) & (df.index <= end)
        crisis_days = mask.sum()

        if crisis_days == 0:
            print(f"  {crisis_name}: No data in range")
            continue

        crisis_states = states[mask]
        crisis_pct = (crisis_states == crisis_state).mean()

        results[crisis_name] = {
            "days": crisis_days,
            "crisis_pct": crisis_pct,
        }

        print(f"  {crisis_name}: {crisis_pct*100:.1f}% in Crisis state ({crisis_days} days)")

    return results


def generate_report(df, states, metrics, state_labels, crisis_results):
    """Generate markdown report."""
    report = []
    report.append("# HMM τ-Augmented Model Report")
    report.append("")
    report.append(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")
    report.append("## Model Configuration")
    report.append("")
    report.append("| Parameter | Value |")
    report.append("|-----------|-------|")
    report.append(f"| States | {N_STATES} |")
    report.append("| Features | ret_1d, ret_5d, ret_21d, vix, vix_5d_chg, **τ** |")
    report.append("| τ included | **Yes** (augmented) |")
    report.append(f"| Observations | {len(df)} |")
    report.append("")

    report.append("## Model Fit Metrics")
    report.append("")
    report.append("| Metric | Value |")
    report.append("|--------|-------|")
    report.append(f"| Log-likelihood | {metrics['log_prob']:.2f} |")
    report.append(f"| AIC | {metrics['aic']:.2f} |")
    report.append(f"| BIC | {metrics['bic']:.2f} |")
    report.append(f"| Parameters | {metrics['n_params']} |")
    report.append("")

    report.append("## State Distribution")
    report.append("")
    report.append("| State | Days | Percentage |")
    report.append("|-------|------|------------|")
    for s in range(N_STATES):
        count = (states == s).sum()
        pct = count / len(states) * 100
        report.append(f"| {state_labels[s]} | {count} | {pct:.1f}% |")
    report.append("")

    report.append("## State Characteristics (with τ)")
    report.append("")
    report.append("| State | Mean VIX | Mean τ | Mean Daily Return |")
    report.append("|-------|----------|--------|-------------------|")
    for s in range(N_STATES):
        mask = states == s
        mean_vix = df.loc[mask, "vix"].mean()
        mean_tau = df.loc[mask, "tau"].mean()
        mean_ret = df.loc[mask, "ret_1d"].mean() * 100
        report.append(f"| {state_labels[s]} | {mean_vix:.1f} | {mean_tau:.2f} | {mean_ret:.3f}% |")
    report.append("")

    report.append("## Crisis Detection Accuracy")
    report.append("")
    report.append("| Crisis | Days in Crisis State | Accuracy |")
    report.append("|--------|---------------------|----------|")
    for crisis_name, res in crisis_results.items():
        report.append(f"| {crisis_name} | {res['days']} | {res['crisis_pct']*100:.1f}% |")
    report.append("")

    report.append("---")
    report.append("*τ-augmented model for comparison with baseline*")

    return "\n".join(report)


def main():
    """Main execution."""
    print("=" * 60)
    print("PHASE 10B - TASK B.3: HMM AUGMENTED (WITH τ)")
    print("=" * 60)

    # Load features
    df = load_features()

    # Prepare augmented features
    X, X_mean, X_std = prepare_augmented_features(df)

    # Fit HMM
    model, states, metrics = fit_hmm(X)

    # Label states
    df["state"] = states
    state_labels = label_states(model, states, df)
    df["state_label"] = df["state"].map(state_labels)

    # Evaluate crisis detection
    crisis_results = evaluate_crisis_detection(states, df, state_labels)

    # Save states
    output_df = df[["state", "state_label", "tau"]].copy()
    output_df.to_csv(STATES_FILE)
    print(f"\nSaved states to: {STATES_FILE}")

    # Generate report
    report = generate_report(df, states, metrics, state_labels, crisis_results)
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"Saved report to: {REPORT_FILE}")

    print("\n" + "=" * 60)
    print("TASK B.3 COMPLETE")
    print("=" * 60)

    # Return metrics for comparison
    return metrics


if __name__ == "__main__":
    main()
