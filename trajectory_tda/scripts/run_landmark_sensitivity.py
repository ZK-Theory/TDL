"""
P1.2: Landmark sensitivity analysis.

Recomputes PH at L = 2500, 5000, 8000 landmarks and re-runs
order-shuffle and Markov-1 null models (n=100 each) at each L.

Saves:
    results/trajectory_tda_robustness/landmark_sensitivity/
        ph_L{L}.json                  – PH summaries at each L
        nulls_order_shuffle_L{L}.json – order-shuffle null at each L
        nulls_markov1_L{L}.json       – Markov-1 null at each L
        landmark_sensitivity_summary.json – combined table

Usage:
    python -m trajectory_tda.scripts.run_landmark_sensitivity \
        --checkpoint-dir results/trajectory_tda_integration \
        --output-dir results/trajectory_tda_robustness/landmark_sensitivity
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

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
        if isinstance(obj, dict):
            return {str(k): convert(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [convert(v) for v in obj]
        return obj

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(convert(data), f, indent=2)
    logger.info(f"Saved: {path}")


def run_landmark_sensitivity(args: argparse.Namespace) -> dict:
    """Run PH + null tests at multiple landmark counts."""
    from trajectory_tda.topology.permutation_nulls import (
        permutation_test_trajectories,
    )
    from trajectory_tda.topology.trajectory_ph import compute_trajectory_ph

    t0 = time.time()
    cp_dir = Path(args.checkpoint_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    landmark_values = [int(x) for x in args.landmarks.split(",")]
    n_null_perms = args.n_null_perms
    n_jobs_base = args.n_jobs

    # ─── Load data ───
    logger.info("Loading embeddings and trajectories...")
    embeddings = np.load(cp_dir / "embeddings.npy")
    with open(cp_dir / "01_trajectories_sequences.json") as f:
        trajectories = json.load(f)
    logger.info(f"Loaded {embeddings.shape[0]} embeddings, {len(trajectories)} trajectories")

    summary_rows = []

    for L in landmark_values:
        logger.info("=" * 60)
        logger.info(f"Landmark sensitivity: L = {L}")
        logger.info("=" * 60)

        actual_L = min(L, embeddings.shape[0])

        # Cap parallelism for large L to avoid OOM
        # 8000 landmarks → ~512MB distance matrix per worker
        if actual_L >= 8000:
            n_jobs = min(n_jobs_base, 2) if n_jobs_base != -1 else 2
            logger.info(f"  Capping n_jobs={n_jobs} for L={L} to limit memory")
        else:
            n_jobs = n_jobs_base

        # ─── PH computation ───
        ph_path = out_dir / f"ph_L{L}.json"
        if ph_path.exists() and not args.force:
            logger.info(f"  Loading cached PH from {ph_path}")
            with open(ph_path) as f:
                ph_summary = json.load(f)
        else:
            logger.info(f"  Computing PH with {actual_L} landmarks...")
            ph_result = compute_trajectory_ph(
                embeddings,
                max_dim=1,
                n_landmarks=actual_L,
                method="maxmin_vr",
                validate=False,
                seed=42,
            )
            ph_summary = {
                "n_landmarks": actual_L,
                "elapsed_seconds": ph_result["elapsed_seconds"],
                "summaries": ph_result.get("summaries", {}),
            }
            _save_json(ph_summary, ph_path)

        # Extract H0/H1 stats
        vr_summary = ph_summary["summaries"].get("maxmin_vr", {})
        h0 = vr_summary.get("H0", {})
        h1 = vr_summary.get("H1", {})

        row = {
            "L": L,
            "H0_total_persistence": h0.get("total_persistence", 0),
            "H0_max_persistence": h0.get("max_persistence", 0),
            "H0_n_finite": h0.get("n_finite", 0),
            "H0_persistence_entropy": h0.get("persistence_entropy", 0),
            "H1_total_persistence": h1.get("total_persistence", 0),
            "H1_max_persistence": h1.get("max_persistence", 0),
            "H1_n_finite": h1.get("n_finite", 0),
            "H1_persistence_entropy": h1.get("persistence_entropy", 0),
        }

        # ─── Order-shuffle null ───
        os_path = out_dir / f"nulls_order_shuffle_L{L}.json"
        if os_path.exists() and not args.force:
            logger.info(f"  Loading cached order-shuffle null from {os_path}")
            with open(os_path) as f:
                os_result = json.load(f)
        else:
            logger.info(f"  Running order-shuffle null (n={n_null_perms})...")
            os_result = permutation_test_trajectories(
                embeddings,
                trajectories=trajectories,
                null_type="order_shuffle",
                n_permutations=n_null_perms,
                max_dim=1,
                n_landmarks=actual_L,
                statistic="total_persistence",
                n_jobs=n_jobs,
                seed=42,
            )
            _save_json(os_result, os_path)

        row["order_shuffle_H0_p"] = os_result["H0"]["p_value"]
        row["order_shuffle_H1_p"] = os_result["H1"]["p_value"]

        # ─── Markov-1 null ───
        m1_path = out_dir / f"nulls_markov1_L{L}.json"
        if m1_path.exists() and not args.force:
            logger.info(f"  Loading cached Markov-1 null from {m1_path}")
            with open(m1_path) as f:
                m1_result = json.load(f)
        else:
            logger.info(f"  Running Markov-1 null (n={n_null_perms})...")
            m1_result = permutation_test_trajectories(
                embeddings,
                trajectories=trajectories,
                null_type="markov",
                n_permutations=n_null_perms,
                max_dim=1,
                n_landmarks=actual_L,
                statistic="total_persistence",
                markov_order=1,
                n_jobs=n_jobs,
                seed=42,
            )
            _save_json(m1_result, m1_path)

        row["markov1_H0_p"] = m1_result["H0"]["p_value"]
        row["markov1_H1_p"] = m1_result["H1"]["p_value"]

        summary_rows.append(row)
        logger.info(
            f"  L={L}: H0_total={row['H0_total_persistence']:.1f}, "
            f"H1_total={row['H1_total_persistence']:.1f}, "
            f"os_p=({row['order_shuffle_H0_p']}, {row['order_shuffle_H1_p']}), "
            f"m1_p=({row['markov1_H0_p']}, {row['markov1_H1_p']})"
        )

    # ─── Save combined summary ───
    summary = {
        "landmark_values": landmark_values,
        "n_null_perms": n_null_perms,
        "rows": summary_rows,
        "elapsed_total_seconds": time.time() - t0,
    }
    _save_json(summary, out_dir / "landmark_sensitivity_summary.json")

    logger.info("=" * 60)
    logger.info("Landmark Sensitivity Complete")
    for row in summary_rows:
        logger.info(
            f"  L={row['L']:5d}: H0_total={row['H0_total_persistence']:10.1f}, "
            f"H1_total={row['H1_total_persistence']:8.1f}, "
            f"order_shuffle p=({row['order_shuffle_H0_p']:.3f}, {row['order_shuffle_H1_p']:.3f}), "
            f"markov-1 p=({row['markov1_H0_p']:.3f}, {row['markov1_H1_p']:.3f})"
        )
    logger.info(f"  Elapsed: {time.time() - t0:.1f}s")
    logger.info("=" * 60)

    return summary


def main():
    parser = argparse.ArgumentParser(description="P1.2: Landmark sensitivity analysis")
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="results/trajectory_tda_integration",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/trajectory_tda_robustness/landmark_sensitivity",
    )
    parser.add_argument(
        "--landmarks",
        type=str,
        default="2500,5000,8000",
        help="Comma-separated landmark counts (default: 2500,5000,8000)",
    )
    parser.add_argument(
        "--n-null-perms",
        type=int,
        default=100,
        help="Permutations per null test (default: 100)",
    )
    parser.add_argument(
        "--n-jobs",
        type=int,
        default=-1,
        help="Parallelism for null permutations (-1=all cores, default: -1). "
        "Auto-capped to 2 for L>=8000 to avoid OOM.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute even if cached results exist",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()
    setup_logging(args.verbose)
    run_landmark_sensitivity(args)


if __name__ == "__main__":
    main()
