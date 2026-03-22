"""
Embedding sensitivity analysis (Phase 5B, Concern #8).

Tests 6 embedding configurations to assess robustness of topological findings:

1. Bigram + TF   + PCA-20 (baseline)
2. Bigram + TFIDF + PCA-20
3. Trigram + TF   + PCA-20
4. Trigram + TFIDF + PCA-20
5. Bigram + TF   + PCA-10
6. Bigram + TF   + PCA-30

For each: VR PH at L=5000, order-shuffle null (n=100).

Usage:
    python -m trajectory_tda.scripts.run_embedding_sensitivity \
        --checkpoint-dir results/trajectory_tda_integration \
        --output-dir results/trajectory_tda_integration/embedding_sensitivity
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# Sensitivity grid: (name, include_trigrams, tfidf, pca_dim)
CONFIGS = [
    ("bigram_tf_pca20", False, False, 20),
    ("bigram_tfidf_pca20", False, True, 20),
    ("trigram_tf_pca20", True, False, 20),
    ("trigram_tfidf_pca20", True, True, 20),
    ("bigram_tf_pca10", False, False, 10),
    ("bigram_tf_pca30", False, False, 30),
]


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
        return obj

    with open(fpath, "w") as f:
        json.dump(convert(data), f, indent=2)
    logger.info(f"Saved: {fpath}")


def run_sensitivity(args: argparse.Namespace) -> dict:
    """Run embedding sensitivity grid."""
    from trajectory_tda.embedding.ngram_embed import ngram_embed
    from trajectory_tda.topology.permutation_nulls import permutation_test_trajectories
    from trajectory_tda.topology.trajectory_ph import compute_trajectory_ph

    t0 = time.time()
    cp_dir = Path(args.checkpoint_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ─── Load trajectories ───
    seq_path = cp_dir / "01_trajectories_sequences.json"
    with open(seq_path) as f:
        trajectories = json.load(f)
    logger.info(f"Loaded {len(trajectories)} trajectories")

    n_landmarks = args.landmarks
    n_perms = args.n_perms
    results_table = []

    for config_name, include_trigrams, tfidf, pca_dim in CONFIGS:
        logger.info("=" * 60)
        logger.info(f"Config: {config_name}")
        logger.info(f"  trigrams={include_trigrams}, tfidf={tfidf}, pca_dim={pca_dim}")
        logger.info("=" * 60)
        t1 = time.time()

        # Embed
        embed_kwargs = {
            "include_bigrams": True,
            "include_trigrams": include_trigrams,
            "tfidf": tfidf,
            "pca_dim": pca_dim,
        }
        embeddings, info = ngram_embed(trajectories, **embed_kwargs)

        # Compute n_components for 90% variance from saved PCA
        n_components_90pct = None
        fitted_reducer = info.get("fitted_models", {}).get("reducer")
        if fitted_reducer is not None and hasattr(
            fitted_reducer, "explained_variance_ratio_"
        ):
            cumvar = np.cumsum(fitted_reducer.explained_variance_ratio_)
            above_90 = np.where(cumvar >= 0.90)[0]
            n_components_90pct = (
                int(above_90[0] + 1) if len(above_90) > 0 else len(cumvar)
            )

        logger.info(
            f"  Embedding: {embeddings.shape}, raw_dims={info['raw_dims']}, "
            f"explained_var={info.get('explained_variance')}, "
            f"n_components_90pct={n_components_90pct}"
        )

        # PH
        ph_result = compute_trajectory_ph(
            embeddings,
            max_dim=1,
            n_landmarks=min(n_landmarks, embeddings.shape[0]),
            method="maxmin_vr",
            validate=False,
        )
        summaries = ph_result.get("summaries", {})
        method_summary = summaries.get("maxmin_vr", {})
        h0_total = method_summary.get("H0", {}).get("total_persistence", 0.0)
        h1_total = method_summary.get("H1", {}).get("total_persistence", 0.0)

        logger.info(f"  PH: H0_total={h0_total:.4f}, H1_total={h1_total:.4f}")

        # Order-shuffle null
        null_result = permutation_test_trajectories(
            embeddings,
            trajectories=trajectories,
            null_type="order_shuffle",
            n_permutations=n_perms,
            max_dim=1,
            n_landmarks=min(n_landmarks, embeddings.shape[0]),
            embed_kwargs=embed_kwargs,
        )

        h0_p = null_result.get("H0", {}).get("p_value", float("nan"))
        h1_p = null_result.get("H1", {}).get("p_value", float("nan"))

        logger.info(f"  Null p-values: H0={h0_p:.4f}, H1={h1_p:.4f}")

        config_result = {
            "config_name": config_name,
            "include_trigrams": include_trigrams,
            "tfidf": tfidf,
            "pca_dim": pca_dim,
            "raw_dims": info["raw_dims"],
            "explained_variance": info.get("explained_variance"),
            "n_components_90pct_variance": n_components_90pct,
            "H0_total_persistence": h0_total,
            "H1_total_persistence": h1_total,
            "H0_order_shuffle_p": h0_p,
            "H1_order_shuffle_p": h1_p,
            "H0_null_mean": null_result.get("H0", {}).get("null_mean", 0.0),
            "H1_null_mean": null_result.get("H1", {}).get("null_mean", 0.0),
            "elapsed_seconds": time.time() - t1,
        }
        results_table.append(config_result)

        # Save per-config (including null distributions)
        config_full = {**config_result, "null_details": null_result}
        _save(config_full, out_dir, config_name)

    # ─── Summary ───
    total_elapsed = time.time() - t0

    # Check qualitative stability
    baseline = results_table[0]
    all_significant_h0 = all(r["H0_order_shuffle_p"] < 0.05 for r in results_table)
    all_significant_h1 = all(r["H1_order_shuffle_p"] < 0.05 for r in results_table)

    # Trigram vs bigram comparison
    bigram_baseline = results_table[0]  # bigram_tf_pca20
    trigram_tf = results_table[2]  # trigram_tf_pca20
    trigram_h1_diff = abs(
        trigram_tf["H1_total_persistence"] - bigram_baseline["H1_total_persistence"]
    )
    trigram_h1_ratio = (
        trigram_tf["H1_total_persistence"] / bigram_baseline["H1_total_persistence"]
        if bigram_baseline["H1_total_persistence"] > 0
        else float("inf")
    )

    summary = {
        "configs": results_table,
        "qualitative_stability": {
            "all_H0_significant": all_significant_h0,
            "all_H1_significant": all_significant_h1,
            "stable": all_significant_h0 and all_significant_h1,
        },
        "trigram_vs_bigram": {
            "H1_total_persistence_bigram": bigram_baseline["H1_total_persistence"],
            "H1_total_persistence_trigram": trigram_tf["H1_total_persistence"],
            "H1_abs_difference": trigram_h1_diff,
            "H1_ratio": trigram_h1_ratio,
            "meaningfully_different": trigram_h1_ratio > 1.5 or trigram_h1_ratio < 0.67,
        },
        "trigram_markov2_note": (
            "The trigram embedding directly encodes three-state transition memory. "
            "If trigram-based topology differs significantly from bigram-based topology "
            "(e.g., different total persistence or different null-model p-values), "
            "this indicates that third-order sequential structure is geometrically "
            "detectable in the point cloud. This has implications for the Markov-2 null: "
            "a trigram embedding that produces substantially different PH would suggest "
            "the Markov-2 null is testing against a richer structural hypothesis embedded "
            "in the representation itself."
        ),
        "n_permutations": n_perms,
        "n_landmarks": n_landmarks,
        "total_elapsed_seconds": total_elapsed,
    }

    _save(summary, out_dir, "embedding_sensitivity_summary")

    # Print summary table
    logger.info("=" * 80)
    logger.info("EMBEDDING SENSITIVITY RESULTS")
    logger.info("=" * 80)
    logger.info(
        f"{'Config':<25} {'H0 Total':>10} {'H1 Total':>10} {'OS H0 p':>10} {'OS H1 p':>10}"
    )
    logger.info("-" * 65)
    for r in results_table:
        logger.info(
            f"{r['config_name']:<25} {r['H0_total_persistence']:>10.4f} "
            f"{r['H1_total_persistence']:>10.4f} {r['H0_order_shuffle_p']:>10.4f} "
            f"{r['H1_order_shuffle_p']:>10.4f}"
        )
    logger.info("-" * 65)
    logger.info(f"Qualitatively stable: {summary['qualitative_stability']['stable']}")
    logger.info(
        f"Trigram meaningfully different: {summary['trigram_vs_bigram']['meaningfully_different']}"
    )
    logger.info(f"Total elapsed: {total_elapsed:.1f}s")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Embedding sensitivity analysis (Phase 5B)"
    )
    parser.add_argument(
        "--checkpoint-dir",
        default="results/trajectory_tda_integration",
        help="Phase 1–5 checkpoint directory",
    )
    parser.add_argument(
        "--output-dir",
        default="results/trajectory_tda_integration/embedding_sensitivity",
        help="Output directory",
    )
    parser.add_argument(
        "--landmarks",
        type=int,
        default=5000,
        help="VR PH landmark count",
    )
    parser.add_argument(
        "--n-perms",
        type=int,
        default=100,
        help="Order-shuffle permutations per config",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Debug logging",
    )

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    run_sensitivity(args)


if __name__ == "__main__":
    main()
