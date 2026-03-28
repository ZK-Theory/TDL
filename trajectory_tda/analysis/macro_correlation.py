"""Macroeconomic correlation analysis for topological time series.

Paper 3 analysis: Correlates the annual topological time series (β₀,
total persistence H₀/H₁) with UK macroeconomic indicators (GDP growth,
unemployment rate, Gini coefficient) using Spearman rank correlation
with bootstrap confidence intervals.

Uses ONS published data for 1991–2022. Data is embedded directly as
constants to avoid external file dependencies.

Run::

    python -m trajectory_tda.analysis.macro_correlation \
        --time-series-path results/trajectory_tda_zigzag/03_time_series.json \
        --output-dir results/trajectory_tda_zigzag
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy import stats

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# UK macroeconomic data — ONS published series
# Sources:
#   GDP growth: ONS series IHYP (Real GDP % change YoY)
#   Unemployment: ONS series MGSX (ILO unemployment rate, annual avg)
#   Gini: ONS/DWP HBAI series (before housing costs)
# ─────────────────────────────────────────────────────────────────────

# Annual real GDP growth rate (%, ONS IHYP)
UK_GDP_GROWTH: dict[int, float] = {
    1991: -1.1,
    1992: 0.4,
    1993: 2.5,
    1994: 3.9,
    1995: 2.5,
    1996: 2.5,
    1997: 4.3,
    1998: 3.1,
    1999: 3.2,
    2000: 3.5,
    2001: 2.7,
    2002: 2.5,
    2003: 3.3,
    2004: 2.4,
    2005: 3.0,
    2006: 2.5,
    2007: 2.4,
    2008: -0.3,
    2009: -4.2,
    2010: 2.1,
    2011: 1.5,
    2012: 1.4,
    2013: 2.2,
    2014: 2.9,
    2015: 2.4,
    2016: 1.9,
    2017: 1.7,
    2018: 1.3,
    2019: 1.4,
    2020: -11.0,
    2021: 7.6,
    2022: 4.3,
}

# ILO unemployment rate (%, annual average, ONS MGSX)
UK_UNEMPLOYMENT: dict[int, float] = {
    1991: 8.6,
    1992: 9.8,
    1993: 10.3,
    1994: 9.3,
    1995: 8.5,
    1996: 7.9,
    1997: 6.8,
    1998: 6.1,
    1999: 5.9,
    2000: 5.4,
    2001: 5.0,
    2002: 5.1,
    2003: 5.0,
    2004: 4.7,
    2005: 4.8,
    2006: 5.4,
    2007: 5.3,
    2008: 5.6,
    2009: 7.6,
    2010: 7.8,
    2011: 8.1,
    2012: 7.9,
    2013: 7.6,
    2014: 6.1,
    2015: 5.3,
    2016: 4.9,
    2017: 4.4,
    2018: 4.1,
    2019: 3.8,
    2020: 4.5,
    2021: 4.5,
    2022: 3.7,
}

# Gini coefficient (before housing costs, ONS/HBAI)
UK_GINI: dict[int, float] = {
    1991: 0.34,
    1992: 0.34,
    1993: 0.34,
    1994: 0.33,
    1995: 0.33,
    1996: 0.33,
    1997: 0.33,
    1998: 0.34,
    1999: 0.34,
    2000: 0.35,
    2001: 0.35,
    2002: 0.35,
    2003: 0.34,
    2004: 0.35,
    2005: 0.35,
    2006: 0.35,
    2007: 0.36,
    2008: 0.36,
    2009: 0.35,
    2010: 0.34,
    2011: 0.34,
    2012: 0.33,
    2013: 0.34,
    2014: 0.34,
    2015: 0.34,
    2016: 0.33,
    2017: 0.33,
    2018: 0.34,
    2019: 0.35,
    2020: 0.34,
    2021: 0.33,
    2022: 0.33,
}


def _align_series(
    years: list[int],
    topo_series: list[float],
    macro_dict: dict[int, float],
) -> tuple[NDArray[np.float64], NDArray[np.float64], list[int]]:
    """Align topological and macroeconomic series to common years.

    Args:
        years: Calendar years from topological time series.
        topo_series: Topological metric values aligned with years.
        macro_dict: Macroeconomic indicator keyed by year.

    Returns:
        (topo_array, macro_array, common_years) aligned arrays.
    """
    common = [y for y in years if y in macro_dict]
    topo_idx = [years.index(y) for y in common]
    topo_arr = np.array([topo_series[i] for i in topo_idx], dtype=np.float64)
    macro_arr = np.array([macro_dict[y] for y in common], dtype=np.float64)
    return topo_arr, macro_arr, common


def bootstrap_spearman(
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    n_bootstrap: int = 1000,
    seed: int = 42,
) -> dict:
    """Compute Spearman correlation with bootstrap 95% CI.

    Args:
        x: First variable.
        y: Second variable.
        n_bootstrap: Number of bootstrap resamples.
        seed: Random seed.

    Returns:
        Dict with rho, p_value, ci_lower, ci_upper.
    """
    rho_obs, p_obs = stats.spearmanr(x, y)
    rng = np.random.default_rng(seed)
    n = len(x)
    rho_boot = np.empty(n_bootstrap, dtype=np.float64)
    for i in range(n_bootstrap):
        idx = rng.choice(n, size=n, replace=True)
        rho_boot[i], _ = stats.spearmanr(x[idx], y[idx])

    ci_lower = float(np.nanpercentile(rho_boot, 2.5))
    ci_upper = float(np.nanpercentile(rho_boot, 97.5))

    return {
        "rho": float(rho_obs),
        "p_value": float(p_obs),
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "n": n,
    }


def cross_correlation(
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    max_lag: int = 2,
) -> dict[int, float]:
    """Compute Spearman cross-correlation at integer lags.

    Positive lag means y is shifted forward (topology leads economics).

    Args:
        x: Topological series.
        y: Macroeconomic series.
        max_lag: Maximum lag in years.

    Returns:
        Dict mapping lag → Spearman rho.
    """
    results: dict[int, float] = {}
    n = len(x)
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            x_slice = x[: n - lag] if lag > 0 else x
            y_slice = y[lag:]
        else:
            x_slice = x[-lag:]
            y_slice = y[: n + lag]
        if len(x_slice) < 5:
            continue
        rho, _ = stats.spearmanr(x_slice, y_slice)
        results[lag] = float(rho)
    return results


def main() -> None:
    """Run macroeconomic correlation analysis."""
    parser = argparse.ArgumentParser(
        description="Macroeconomic correlation for topological time series.",
    )
    parser.add_argument(
        "--time-series-path",
        default="results/trajectory_tda_zigzag/03_time_series.json",
    )
    parser.add_argument(
        "--output-dir",
        default="results/trajectory_tda_zigzag",
    )
    parser.add_argument("--n-bootstrap", type=int, default=1000)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    ts_path = Path(args.time_series_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(ts_path) as f:
        ts = json.load(f)

    years = ts["years"]
    topo_series = {
        "betti_0": ts["betti_0_series"],
        "total_persistence_h0": ts["total_persistence_h0"],
        "total_persistence_h1": ts["total_persistence_h1"],
    }

    macro_indicators = {
        "gdp_growth": UK_GDP_GROWTH,
        "unemployment": UK_UNEMPLOYMENT,
        "gini": UK_GINI,
    }

    results: dict = {"correlations": {}, "cross_correlations": {}}

    for topo_name, topo_vals in topo_series.items():
        results["correlations"][topo_name] = {}
        results["cross_correlations"][topo_name] = {}

        for macro_name, macro_dict in macro_indicators.items():
            topo_arr, macro_arr, common_years = _align_series(
                years,
                topo_vals,
                macro_dict,
            )

            corr = bootstrap_spearman(
                topo_arr,
                macro_arr,
                n_bootstrap=args.n_bootstrap,
            )
            results["correlations"][topo_name][macro_name] = corr

            xcorr = cross_correlation(topo_arr, macro_arr, max_lag=2)
            results["cross_correlations"][topo_name][macro_name] = xcorr

            logger.info(
                "%s × %s: ρ=%.3f (p=%.4f) [%.3f, %.3f]",
                topo_name,
                macro_name,
                corr["rho"],
                corr["p_value"],
                corr["ci_lower"],
                corr["ci_upper"],
            )

    # Add metadata
    results["metadata"] = {
        "n_years": len(years),
        "year_range": [years[0], years[-1]],
        "n_bootstrap": args.n_bootstrap,
        "macro_sources": {
            "gdp_growth": "ONS IHYP (Real GDP % change YoY)",
            "unemployment": "ONS MGSX (ILO rate, annual avg)",
            "gini": "ONS/DWP HBAI (before housing costs)",
        },
    }

    out_path = output_dir / "macro_correlations.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info("Saved: %s", out_path)

    # Print summary table
    logger.info("=" * 70)
    logger.info("%-25s %-15s %8s %8s %16s", "Topo metric", "Macro", "ρ", "p", "95% CI")
    logger.info("-" * 70)
    for topo_name in topo_series:
        for macro_name in macro_indicators:
            c = results["correlations"][topo_name][macro_name]
            logger.info(
                "%-25s %-15s %8.3f %8.4f [%6.3f, %6.3f]",
                topo_name,
                macro_name,
                c["rho"],
                c["p_value"],
                c["ci_lower"],
                c["ci_upper"],
            )


if __name__ == "__main__":
    main()
