"""
Demonstration of proper G&K methodology using trend_analysis_validator.py

This shows that the extracted/refactored G&K functions produce the same
strong results (τ ≈ 0.8) as the original gidea_katz_replication.py
"""

import logging

from financial_tda.validation.gidea_katz_replication import (
    compute_persistence_landscape_norms,
    fetch_historical_data,
)
from financial_tda.validation.trend_analysis_validator import validate_gk_event

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 80)
    logger.info("DEMONSTRATING PROPER G&K METHODOLOGY")
    logger.info("=" * 80)

    # Fetch 2008 GFC data
    logger.info("\nStep 1: Fetching 2008 GFC historical data...")
    prices = fetch_historical_data("2006-01-01", "2008-12-31")
    logger.info(f"✓ Fetched {len(prices)} indices")

    # Compute L^p norms (same as G&K replication)
    logger.info("\nStep 2: Computing persistence landscape L^p norms...")
    norms_df = compute_persistence_landscape_norms(
        prices,
        window_size=50,
        stride=1,
        n_layers=5,
    )
    logger.info(f"✓ Computed {len(norms_df)} norm observations")

    # Apply COMPLETE G&K methodology (rolling stats + Kendall-tau)
    logger.info("\nStep 3: Applying COMPLETE G&K methodology...")
    logger.info("  - Computing rolling statistics (variance, spectral density, ACF)")
    logger.info("  - Analyzing Kendall-tau on 250-day pre-crisis window")

    result = validate_gk_event(
        norms_df,
        event_name="2008 GFC",
        crisis_date="2008-09-15",
        rolling_window=500,  # G&K uses 500-day rolling window
        precrash_window=250,  # G&K analyzes 250 days before crisis
    )

    # Display results
    logger.info("\n" + "=" * 80)
    logger.info("RESULTS: G&K METHODOLOGY ON 2008 GFC")
    logger.info("=" * 80)
    logger.info(f"Event: {result['event_name']}")
    logger.info(f"Crisis Date: {result['crisis_date']}")
    logger.info(f"Analysis Window: {result['window_start']} to {result['window_end']}")
    logger.info(f"Observations: {result['n_observations']} days")

    logger.info("\n" + "-" * 80)
    logger.info("KENDALL-TAU RESULTS FOR ALL 6 G&K STATISTICS:")
    logger.info("-" * 80)

    stats = result["statistics"]

    # Sort by absolute tau value to show best performers first
    sorted_stats = sorted(stats.items(), key=lambda x: abs(x[1]["tau"]), reverse=True)

    for stat_name, values in sorted_stats:
        tau = values["tau"]
        p_val = values["p_value"]
        n = values["n_samples"]

        # Highlight if passes threshold
        marker = "✓ PASS" if abs(tau) >= 0.70 else "  "

        logger.info(f"{marker} {stat_name:40s} τ={tau:7.4f}  p={p_val:.4e}  n={n}")

    logger.info("\n" + "-" * 80)
    logger.info(f"BEST METRIC: {result['best_metric']}")
    logger.info(f"BEST TAU: {result['best_tau']:.4f}")
    logger.info(f"THRESHOLD: {result['tau_threshold']:.2f}")
    logger.info(f"STATUS: {result['status']}")
    logger.info("-" * 80)

    # Compare to G&K expectations
    logger.info("\n" + "=" * 80)
    logger.info("COMPARISON TO GIDEA & KATZ (2018) PAPER")
    logger.info("=" * 80)
    logger.info("Expected for 2008 Lehman crisis: τ ≈ 1.00 (spectral density)")
    logger.info(f"Our result:                      τ = {result['best_tau']:.4f} ({result['best_metric']})")

    if result["status"] == "PASS":
        logger.info("\n✓ SUCCESS: G&K methodology properly replicated!")
        logger.info("  The complete methodology (rolling stats + Kendall-tau) works as expected.")
    else:
        logger.info("\n⚠ PARTIAL: Did not reach τ ≥ 0.70")
        logger.info("  May indicate data source differences or parameter sensitivity.")

    logger.info("\n" + "=" * 80)

    return result


if __name__ == "__main__":
    result = main()
