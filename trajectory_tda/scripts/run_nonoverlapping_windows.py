"""
Non-overlapping window analysis — sensitivity check (Phase 5A, Concern #6).

Compares regime transition dynamics between:
  - Overlapping windows (10yr, 5yr step — existing design)
  - Non-overlapping windows (5yr, 5yr step — no shared years)

Outputs overlap baseline analysis, transition matrices, and escape rates.

Usage:
    python -m trajectory_tda.scripts.run_nonoverlapping_windows \
        --checkpoint-dir results/trajectory_tda_integration \
        --output-dir results/trajectory_tda_integration/nonoverlapping
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

DISADVANTAGED_REGIMES = {2, 6}
GOOD_REGIMES = {1, 4}


def _save(data: dict, path: Path, name: str) -> None:
    """Save checkpoint JSON with numpy-safe serialisation."""
    path.mkdir(parents=True, exist_ok=True)
    fpath = path / f"{name}.json"

    def convert(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        if isinstance(obj, dict):
            return {str(k): convert(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [convert(v) for v in obj]
        if isinstance(obj, set):
            return sorted(convert(v) for v in obj)
        return obj

    with open(fpath, "w") as f:
        json.dump(convert(data), f, indent=2)
    logger.info(f"Saved: {fpath}")


def _compute_overlap_baseline(
    overlapping_windows: list[dict],
    nonoverlapping_windows: list[dict],
    overlapping_regimes: np.ndarray,
    nonoverlapping_regimes: np.ndarray,
    window_years_overlap: int = 10,
    window_step_overlap: int = 5,
) -> dict:
    """Analyse the overlap artefact on self-transition rates.

    For overlapping design: consecutive windows share
    (window_years - window_step) / window_years of their years.
    """
    shared_years = window_years_overlap - window_step_overlap
    shared_fraction = shared_years / window_years_overlap

    # Build per-individual regime sequences for overlapping windows
    ol_by_pidp: dict = defaultdict(list)
    for i, w in enumerate(overlapping_windows):
        ol_by_pidp[w["pidp"]].append((w["start_year"], int(overlapping_regimes[i])))
    for pidp in ol_by_pidp:
        ol_by_pidp[pidp].sort()

    # Compute same-regime rate for consecutive overlapping windows
    ol_same = 0
    ol_total = 0
    for pidp, seq in ol_by_pidp.items():
        for i in range(len(seq) - 1):
            ol_total += 1
            if seq[i][1] == seq[i + 1][1]:
                ol_same += 1
    ol_self_rate = ol_same / ol_total if ol_total > 0 else 0.0

    # Same for non-overlapping windows
    nol_by_pidp: dict = defaultdict(list)
    for i, w in enumerate(nonoverlapping_windows):
        nol_by_pidp[w["pidp"]].append((w["start_year"], int(nonoverlapping_regimes[i])))
    for pidp in nol_by_pidp:
        nol_by_pidp[pidp].sort()

    nol_same = 0
    nol_total = 0
    for pidp, seq in nol_by_pidp.items():
        for i in range(len(seq) - 1):
            nol_total += 1
            if seq[i][1] == seq[i + 1][1]:
                nol_same += 1
    nol_self_rate = nol_same / nol_total if nol_total > 0 else 0.0

    return {
        "shared_years": shared_years,
        "shared_fraction": shared_fraction,
        "overlapping_self_transition_rate": ol_self_rate,
        "overlapping_n_transitions": ol_total,
        "nonoverlapping_self_transition_rate": nol_self_rate,
        "nonoverlapping_n_transitions": nol_total,
        "self_rate_difference": ol_self_rate - nol_self_rate,
        "interpretation": (
            f"Overlapping windows share {shared_fraction:.0%} of years. "
            f"Self-transition rate: overlapping={ol_self_rate:.3f}, "
            f"non-overlapping={nol_self_rate:.3f}. "
            f"Difference={ol_self_rate - nol_self_rate:+.3f}."
        ),
    }


def run_nonoverlapping(args: argparse.Namespace) -> dict:
    """Execute non-overlapping window analysis."""
    from trajectory_tda.analysis.regime_switching import (
        build_regime_sequences,
        compute_escape_probabilities,
        compute_transition_matrix,
    )
    from trajectory_tda.data.trajectory_builder import build_windows
    from trajectory_tda.embedding.ngram_embed import (
        _compute_bigrams,
        _compute_unigrams,
    )
    from trajectory_tda.utils.model_io import load_model

    t0 = time.time()
    cp_dir = Path(args.checkpoint_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict = {}

    # ─── Load Phase 1–5 artefacts ───
    logger.info("Loading Phase 1–5 artefacts...")

    seq_path = cp_dir / "01_trajectories_sequences.json"
    with open(seq_path) as f:
        trajectories = json.load(f)
    logger.info(f"Loaded {len(trajectories)} trajectories")

    meta_path = cp_dir / "01_trajectories.json"
    with open(meta_path) as f:
        meta_raw = json.load(f)
    metadata = pd.DataFrame(meta_raw["metadata"])

    scaler = load_model(cp_dir / "02_scaler.joblib")
    pca = load_model(cp_dir / "02_pca.joblib")
    gmm = load_model(cp_dir / "05_gmm.joblib")
    n_regimes = gmm.n_components
    logger.info(f"Models loaded: Scaler, PCA ({pca.n_components_} dims), GMM (k={n_regimes})")

    # ─── Build non-overlapping windows (5yr, step=5) ───
    logger.info("=" * 60)
    logger.info("Building non-overlapping windows (5yr, step=5)")
    logger.info("=" * 60)

    nol_windows = build_windows(
        trajectories, metadata,
        window_years=5, window_step=5, min_valid=3,
    )
    results["n_nonoverlapping_windows"] = len(nol_windows)
    logger.info(f"Non-overlapping windows: {len(nol_windows)}")

    # ─── Build overlapping windows (10yr, step=5) for comparison ───
    logger.info("Building overlapping windows (10yr, step=5)")

    ol_windows = build_windows(
        trajectories, metadata,
        window_years=10, window_step=5, min_valid=5,
    )
    results["n_overlapping_windows"] = len(ol_windows)
    logger.info(f"Overlapping windows: {len(ol_windows)}")

    # ─── Embed both sets using saved transforms ───
    def _embed_windows(windows: list[dict]) -> np.ndarray:
        n = len(windows)
        raw = np.zeros((n, 90), dtype=np.float64)
        for i, w in enumerate(windows):
            uni = _compute_unigrams(w["states"])
            bi = _compute_bigrams(w["states"])
            raw[i] = np.concatenate([uni, bi])
        scaled = scaler.transform(raw)
        return pca.transform(scaled)

    nol_embeddings = _embed_windows(nol_windows)
    ol_embeddings = _embed_windows(ol_windows)
    logger.info(f"Embedded: non-overlapping {nol_embeddings.shape}, overlapping {ol_embeddings.shape}")

    # ─── Assign regimes via GMM ───
    nol_regimes = gmm.predict(nol_embeddings)
    ol_regimes = gmm.predict(ol_embeddings)

    # ─── Transition matrices ───
    logger.info("Computing transition matrices...")

    nol_regime_seqs = build_regime_sequences(nol_windows, nol_regimes)
    ol_regime_seqs = build_regime_sequences(ol_windows, ol_regimes)

    nol_tm = compute_transition_matrix(nol_regime_seqs, n_regimes=n_regimes)
    ol_tm = compute_transition_matrix(ol_regime_seqs, n_regimes=n_regimes)

    results["nonoverlapping_transition_matrix"] = nol_tm.tolist()
    results["overlapping_transition_matrix"] = ol_tm.tolist()

    # Per-regime self-transition rates
    nol_self_rates = {int(r): float(nol_tm[r, r]) for r in range(n_regimes)}
    ol_self_rates = {int(r): float(ol_tm[r, r]) for r in range(n_regimes)}
    results["nonoverlapping_self_transition_rates"] = nol_self_rates
    results["overlapping_self_transition_rates"] = ol_self_rates

    logger.info(f"Self-transition rates (non-overlapping): {nol_self_rates}")
    logger.info(f"Self-transition rates (overlapping):     {ol_self_rates}")

    # ─── Escape rates ───
    logger.info("Computing escape rates...")

    nol_escape = compute_escape_probabilities(
        nol_regime_seqs,
        disadvantaged_regimes=DISADVANTAGED_REGIMES,
        good_regimes=GOOD_REGIMES,
        max_horizon=5,
    )
    ol_escape = compute_escape_probabilities(
        ol_regime_seqs,
        disadvantaged_regimes=DISADVANTAGED_REGIMES,
        good_regimes=GOOD_REGIMES,
        max_horizon=5,
    )

    results["nonoverlapping_escape"] = {
        k: v for k, v in nol_escape.items() if k != "path_lengths"
    }
    results["overlapping_escape"] = {
        k: v for k, v in ol_escape.items() if k != "path_lengths"
    }

    # ─── Overlap baseline analysis ───
    logger.info("Computing overlap baseline analysis...")

    baseline = _compute_overlap_baseline(
        ol_windows, nol_windows,
        ol_regimes, nol_regimes,
        window_years_overlap=10,
        window_step_overlap=5,
    )
    results["overlap_baseline"] = baseline
    logger.info(baseline["interpretation"])

    # ─── Summary ───
    elapsed = time.time() - t0
    results["elapsed_seconds"] = elapsed
    _save(results, out_dir, "nonoverlapping_analysis")

    logger.info("=" * 60)
    logger.info(f"Non-overlapping window analysis complete ({elapsed:.1f}s)")
    logger.info(f"  Non-overlapping escape rate: {nol_escape['ever_escape_rate']:.3f}")
    logger.info(f"  Overlapping escape rate:     {ol_escape['ever_escape_rate']:.3f}")
    logger.info("=" * 60)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Non-overlapping window sensitivity analysis (Phase 5A)"
    )
    parser.add_argument(
        "--checkpoint-dir",
        default="results/trajectory_tda_integration",
        help="Phase 1–5 checkpoint directory",
    )
    parser.add_argument(
        "--output-dir",
        default="results/trajectory_tda_integration/nonoverlapping",
        help="Output directory for results",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Debug logging"
    )

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    run_nonoverlapping(args)


if __name__ == "__main__":
    main()

