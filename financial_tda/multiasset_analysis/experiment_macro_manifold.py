"""
Multi-Asset TDA: Experiment A - Macro Manifold Analysis
Tests cross-asset topology for systemic stress detection.

This experiment answers:
1. Does cross-asset TDA detect known stress events (2008, 2011, 2020)?
2. Can we distinguish "Risk-Off" from "Liquidity Crisis" topologically?
"""

import os
import pandas as pd

# Local imports
from fetch_multiasset_data import MultiAssetDataFetcher
from tda_analysis import rolling_tda_analysis, compute_variance_tau, CONFIG_PRESETS

# =============================================================================
# CONFIGURATION
# =============================================================================

OUTPUT_DIR = "../outputs/multiasset/exp_a_manifold"


# =============================================================================
# EXPERIMENT A: CROSS-ASSET TOPOLOGY
# =============================================================================


def run_experiment_a(
    config_name: str = "extended", tda_preset: str = "standard", save_results: bool = True
) -> pd.DataFrame:
    """
    Run Experiment A: Cross-Asset Macro Manifold analysis.

    Args:
        config_name: Asset configuration ('minimal', 'extended', 'full_crypto')
        tda_preset: TDA parameter preset ('standard', 'fast', 'sensitive')
        save_results: Whether to save outputs

    Returns:
        DataFrame with tau values for each stress event
    """
    print("=" * 70)
    print(f"EXPERIMENT A: MACRO MANIFOLD ({config_name.upper()})")
    print("=" * 70)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Step 1: Fetch Data
    print("\n[1/3] Fetching and aligning data...")
    fetcher = MultiAssetDataFetcher(config=config_name)
    data = fetcher.fetch_and_align(standardize=True)

    # Step 2: Run TDA
    print("\n[2/3] Running TDA analysis...")
    tda_config = CONFIG_PRESETS[tda_preset]
    norms = rolling_tda_analysis(data, config=tda_config, verbose=True)

    # Save intermediate results
    if save_results:
        norms.to_csv(os.path.join(OUTPUT_DIR, f"{config_name}_norms.csv"))

    # Step 3: Analyze Stress Events
    print("\n[3/3] Analyzing stress events...")
    events_in_range = fetcher.get_stress_events_in_range()

    results = []
    for event in events_in_range:
        try:
            tau_l2, p_l2 = compute_variance_tau(norms, event["date"], tda_config, metric="L2")
            tau_l1, p_l1 = compute_variance_tau(norms, event["date"], tda_config, metric="L1")

            result = {
                "Event": event["name"],
                "Date": event["date"],
                "Type": event["type"],
                "Severity": event["severity"],
                "Tau_L2": tau_l2,
                "P_L2": p_l2,
                "Tau_L1": tau_l1,
                "P_L1": p_l1,
                "Detected": tau_l2 >= tda_config.tau_warning,
            }
            results.append(result)

            status = "✓ DETECTED" if result["Detected"] else "✗ MISSED"
            print(f"  {event['name']:25s} τ_L2={tau_l2:+.4f} (p={p_l2:.2e}) {status}")

        except ValueError as e:
            print(f"  {event['name']:25s} SKIPPED: {e}")

    results_df = pd.DataFrame(results)

    if save_results:
        results_df.to_csv(os.path.join(OUTPUT_DIR, f"{config_name}_event_results.csv"), index=False)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    detected = results_df["Detected"].sum()
    total = len(results_df)
    print(f"Detection Rate: {detected}/{total} ({100*detected/total:.1f}%)")

    return results_df


def compare_asset_configs():
    """
    Compare TDA performance across different asset configurations.

    Tests whether adding more assets improves or degrades signal quality.
    """
    print("\n" + "=" * 70)
    print("ASSET CONFIGURATION COMPARISON")
    print("=" * 70)

    all_results = {}

    for config_name in ["minimal", "extended"]:  # Skip crypto for initial comparison
        print(f"\n--- Running {config_name} ---")
        results = run_experiment_a(config_name=config_name, save_results=True)
        all_results[config_name] = results

    # Comparison table
    print("\n" + "=" * 70)
    print("CROSS-CONFIG COMPARISON (L2 Tau)")
    print("=" * 70)

    # Merge on event
    minimal = all_results["minimal"].set_index("Event")["Tau_L2"].rename("Minimal_4")
    extended = all_results["extended"].set_index("Event")["Tau_L2"].rename("Extended_8")

    comparison = pd.concat([minimal, extended], axis=1)
    print(comparison.to_string())

    # Save comparison
    comparison.to_csv(os.path.join(OUTPUT_DIR, "config_comparison.csv"))

    return comparison


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Experiment A: Macro Manifold")
    parser.add_argument(
        "--config", default="extended", choices=["minimal", "extended", "full_crypto"], help="Asset configuration"
    )
    parser.add_argument(
        "--preset", default="standard", choices=["standard", "fast", "sensitive"], help="TDA parameter preset"
    )
    parser.add_argument("--compare", action="store_true", help="Run comparison across configs")

    args = parser.parse_args()

    if args.compare:
        compare_asset_configs()
    else:
        run_experiment_a(config_name=args.config, tda_preset=args.preset)
