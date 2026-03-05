"""
P1.3: Wasserstein FDR correction.

Applies Benjamini-Hochberg correction to all pairwise Wasserstein
tests from the stratified comparison (gender, NS-SEC, cohort).
Reports both raw and corrected counts.

Saves:
    results/trajectory_tda_robustness/
        fdr_correction_results.json   – all raw/corrected p-values and summary

Usage:
    python -m trajectory_tda.scripts.run_fdr_correction \
        --checkpoint-dir results/trajectory_tda_integration \
        --output-dir results/trajectory_tda_robustness
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
from statsmodels.stats.multitest import multipletests

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _save_json(data: dict, path: Path) -> None:
    """Save dict as JSON with numpy-safe conversion."""

    def convert(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, dict):
            return {str(k): convert(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [convert(v) for v in obj]
        return obj

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(convert(data), f, indent=2)
    logger.info(f"Saved: {path}")


def run_fdr_correction(args: argparse.Namespace) -> dict:
    """Apply BH FDR correction to all stratified Wasserstein p-values."""
    cp_dir = Path(args.checkpoint_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ─── Load stratified results ───
    strat_path = cp_dir / "06_stratified.json"
    with open(strat_path) as f:
        strat_data = json.load(f)

    axes = ["gender", "parental_nssec", "cohort", "gor"]
    logger.info(f"Loaded stratified results with axes: {axes}")

    # ─── Extract all p-values ───
    all_tests = []
    for axis in axes:
        if axis not in strat_data:
            logger.warning(f"  Axis '{axis}' not found in stratified results, skipping")
            continue

        pairwise_pvals = strat_data[axis].get("pairwise_p_values", {})
        for test_key, test_data in pairwise_pvals.items():
            if isinstance(test_data, dict):
                raw_p = test_data.get("p_value", None)
            else:
                raw_p = test_data

            if raw_p is not None:
                all_tests.append(
                    {
                        "axis": axis,
                        "test_key": test_key,
                        "raw_p": float(raw_p),
                        "observed": test_data.get("observed") if isinstance(test_data, dict) else None,
                        "null_mean": test_data.get("null_mean") if isinstance(test_data, dict) else None,
                    }
                )

    n_tests = len(all_tests)
    logger.info(f"Extracted {n_tests} p-values across all axes")

    if n_tests == 0:
        logger.error("No p-values found!")
        return {"error": "no_pvalues_found"}

    # ─── Apply BH correction (all tests together) ───
    raw_pvals = np.array([t["raw_p"] for t in all_tests])

    reject_bh, corrected_bh, _, _ = multipletests(raw_pvals, alpha=args.alpha, method="fdr_bh")

    for i, test in enumerate(all_tests):
        test["corrected_p_bh"] = float(corrected_bh[i])
        test["significant_raw"] = bool(raw_pvals[i] < args.alpha)
        test["significant_bh"] = bool(reject_bh[i])

    # ─── Also apply within each axis separately ───
    for axis in axes:
        axis_tests = [t for t in all_tests if t["axis"] == axis]
        if len(axis_tests) < 2:
            for t in axis_tests:
                t["corrected_p_bh_within_axis"] = t["raw_p"]
                t["significant_bh_within_axis"] = t["significant_raw"]
            continue

        axis_pvals = np.array([t["raw_p"] for t in axis_tests])
        reject_ax, corrected_ax, _, _ = multipletests(axis_pvals, alpha=args.alpha, method="fdr_bh")
        for i, t in enumerate(axis_tests):
            t["corrected_p_bh_within_axis"] = float(corrected_ax[i])
            t["significant_bh_within_axis"] = bool(reject_ax[i])

    # ─── Summaries ───
    n_sig_raw = sum(1 for t in all_tests if t["significant_raw"])
    n_sig_bh = sum(1 for t in all_tests if t["significant_bh"])

    per_axis_summary = {}
    for axis in axes:
        axis_tests = [t for t in all_tests if t["axis"] == axis]
        n_ax = len(axis_tests)
        n_sig_raw_ax = sum(1 for t in axis_tests if t["significant_raw"])
        n_sig_bh_ax = sum(1 for t in axis_tests if t["significant_bh"])
        n_sig_bh_within_ax = sum(1 for t in axis_tests if t.get("significant_bh_within_axis", False))

        per_axis_summary[axis] = {
            "n_tests": n_ax,
            "n_significant_raw": n_sig_raw_ax,
            "n_significant_bh_global": n_sig_bh_ax,
            "n_significant_bh_within_axis": n_sig_bh_within_ax,
        }
        logger.info(
            f"  {axis}: {n_ax} tests, "
            f"{n_sig_raw_ax} sig (raw), "
            f"{n_sig_bh_ax} sig (BH global), "
            f"{n_sig_bh_within_ax} sig (BH within-axis)"
        )

    # Per-dimension summary
    h0_tests = [t for t in all_tests if "H0" in t["test_key"]]
    h1_tests = [t for t in all_tests if "H1" in t["test_key"]]

    dim_summary = {
        "H0": {
            "n_tests": len(h0_tests),
            "n_significant_raw": sum(1 for t in h0_tests if t["significant_raw"]),
            "n_significant_bh": sum(1 for t in h0_tests if t["significant_bh"]),
        },
        "H1": {
            "n_tests": len(h1_tests),
            "n_significant_raw": sum(1 for t in h1_tests if t["significant_raw"]),
            "n_significant_bh": sum(1 for t in h1_tests if t["significant_bh"]),
        },
    }

    results = {
        "n_total_tests": n_tests,
        "alpha": args.alpha,
        "correction_method": "benjamini_hochberg",
        "n_significant_raw": n_sig_raw,
        "n_significant_bh_global": n_sig_bh,
        "per_axis_summary": per_axis_summary,
        "per_dimension_summary": dim_summary,
        "tests": all_tests,
    }

    _save_json(results, out_dir / "fdr_correction_results.json")

    logger.info("=" * 60)
    logger.info("FDR Correction Complete")
    logger.info(f"  Total tests: {n_tests}")
    logger.info(f"  Significant (raw p < {args.alpha}): {n_sig_raw}")
    logger.info(f"  Significant (BH-corrected): {n_sig_bh}")
    logger.info(f"  H0: {dim_summary['H0']['n_significant_raw']} raw → {dim_summary['H0']['n_significant_bh']} BH")
    logger.info(f"  H1: {dim_summary['H1']['n_significant_raw']} raw → {dim_summary['H1']['n_significant_bh']} BH")
    logger.info("=" * 60)

    return results


def main():
    parser = argparse.ArgumentParser(description="P1.3: Wasserstein FDR correction")
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="results/trajectory_tda_integration",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/trajectory_tda_robustness",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="Significance level (default: 0.05)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()
    setup_logging(args.verbose)
    run_fdr_correction(args)


if __name__ == "__main__":
    main()
