"""
Multi-Asset TDA: Experiment C - Crypto's Role in Portfolio Topology
Investigates how adding Bitcoin/Ethereum changes the portfolio's stress signatures.

Questions:
1. Does crypto increase portfolio "complexity" (H1 count)?
2. Does crypto correlate with equities during stress (March 2020, May 2022)?
3. Could crypto serve as an early warning indicator?
"""

import os
import pandas as pd
from scipy.stats import pearsonr

# Local imports
from fetch_multiasset_data import MultiAssetDataFetcher
from tda_analysis import rolling_tda_analysis, compute_variance_tau, CONFIG_PRESETS

# =============================================================================
# CONFIGURATION
# =============================================================================

OUTPUT_DIR = "../outputs/multiasset/exp_c_crypto"

CRYPTO_EVENTS = [
    {"name": "2018 Crypto Winter", "date": "2018-01-16"},
    {"name": "2021 May Crash", "date": "2021-05-19"},
    {"name": "2022 Terra/Luna", "date": "2022-05-09"},
    {"name": "2022 FTX Collapse", "date": "2022-11-08"},
]


# =============================================================================
# EXPERIMENT C
# =============================================================================


def run_experiment_c(save_results: bool = True) -> pd.DataFrame:
    """
    Compare TDA behavior with and without crypto in the portfolio.

    Analysis:
    1. Run TDA on 8-asset (no crypto) for 2017-2024
    2. Run TDA on 10-asset (with crypto) for 2017-2024
    3. Compare H1 count, L2 variance, and tau values at crypto events
    """
    print("=" * 70)
    print("EXPERIMENT C: CRYPTO'S ROLE IN PORTFOLIO TOPOLOGY")
    print("=" * 70)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tda_config = CONFIG_PRESETS["fast"]  # Crypto needs faster params

    # Step 1: Fetch both configurations
    print("\n[1/3] Fetching data...")

    # Extended (8 assets, no crypto)
    fetcher_8 = MultiAssetDataFetcher(config="extended")
    data_8 = fetcher_8.fetch_and_align(standardize=True)

    # Full + Crypto (10 assets)
    fetcher_10 = MultiAssetDataFetcher(config="full_crypto")
    data_10 = fetcher_10.fetch_and_align(standardize=True)

    # Align to common date range
    common_start = max(data_8.index[0], data_10.index[0])
    common_end = min(data_8.index[-1], data_10.index[-1])

    data_8 = data_8.loc[common_start:common_end]
    data_10 = data_10.loc[common_start:common_end]

    print(f"  Common range: {common_start.date()} to {common_end.date()}")

    # Step 2: Run TDA on both
    print("\n[2/3] Running TDA...")
    print("  8-asset (no crypto):")
    norms_8 = rolling_tda_analysis(data_8, config=tda_config, verbose=True)

    print("  10-asset (with crypto):")
    norms_10 = rolling_tda_analysis(data_10, config=tda_config, verbose=True)

    # Step 3: Compare at crypto events
    print("\n[3/3] Comparing at crypto events...")

    results = []
    for event in CRYPTO_EVENTS:
        event_date = pd.to_datetime(event["date"])

        if event_date < common_start or event_date > common_end:
            print(f"  {event['name']}: Out of range")
            continue

        try:
            tau_8, p_8 = compute_variance_tau(norms_8, event["date"], tda_config, metric="L2")
            tau_10, p_10 = compute_variance_tau(norms_10, event["date"], tda_config, metric="L2")

            # H1 count comparison in pre-event window
            event_loc_8 = norms_8.index.get_indexer([event_date], method="nearest")[0]
            event_loc_10 = norms_10.index.get_indexer([event_date], method="nearest")[0]

            h1_8 = norms_8["H1_Count"].iloc[event_loc_8 - 60 : event_loc_8].mean()
            h1_10 = norms_10["H1_Count"].iloc[event_loc_10 - 60 : event_loc_10].mean()

            result = {
                "Event": event["name"],
                "Date": event["date"],
                "Tau_8Asset": tau_8,
                "Tau_10Asset": tau_10,
                "Tau_Diff": tau_10 - tau_8,
                "H1_8Asset": h1_8,
                "H1_10Asset": h1_10,
                "H1_Increase": h1_10 - h1_8,
            }
            results.append(result)

            print(
                f"  {event['name']:20s} τ_8={tau_8:+.3f} τ_10={tau_10:+.3f} "
                f"(Δ={tau_10-tau_8:+.3f}) H1: {h1_8:.1f}→{h1_10:.1f}"
            )

        except Exception as e:
            print(f"  {event['name']}: Error - {e}")

    results_df = pd.DataFrame(results)

    # Summary statistics
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    # Overall H1 comparison
    h1_corr, _ = pearsonr(norms_8["H1_Count"].dropna(), norms_10["H1_Count"].dropna())
    print(f"H1 correlation (8 vs 10 asset): {h1_corr:.3f}")

    avg_h1_8 = norms_8["H1_Count"].mean()
    avg_h1_10 = norms_10["H1_Count"].mean()
    print(f"Average H1 Count: 8-asset={avg_h1_8:.2f}, 10-asset={avg_h1_10:.2f}")
    print(
        f"  -> Crypto {'increases' if avg_h1_10 > avg_h1_8 else 'decreases'} complexity by {abs(avg_h1_10 - avg_h1_8):.2f}"
    )

    if save_results:
        results_df.to_csv(os.path.join(OUTPUT_DIR, "crypto_comparison.csv"), index=False)
        norms_8.to_csv(os.path.join(OUTPUT_DIR, "norms_8asset.csv"))
        norms_10.to_csv(os.path.join(OUTPUT_DIR, "norms_10asset.csv"))

    return results_df


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    run_experiment_c()
