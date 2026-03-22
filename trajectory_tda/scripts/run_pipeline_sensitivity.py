"""
P3.10: Pipeline sensitivity checks.

Varies three pipeline parameters and reports which core results are stable:
  1. Minimum trajectory length (8, 10, 12 years)
  2. N-gram weighting (TF vs TF-IDF)
  3. VR filtration threshold percentile (50th, 75th, 90th)

For each configuration, re-runs build → embed → PH → GMM and records:
  - Number of trajectories
  - Embedding shape + explained variance
  - H0/H1 feature counts + total persistence
  - GMM k_optimal and regime profile stability (ARI vs baseline)

Usage:
    python -m trajectory_tda.scripts.run_pipeline_sensitivity \
        --data-dir trajectory_tda/data \
        --output-dir results/trajectory_tda_robustness \
        --landmarks 2000
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
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _save_json(data: dict, path: Path) -> None:
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


def _run_single_config(
    data_dir: str,
    min_years: int,
    tfidf: bool,
    thresh_pct: int,
    n_landmarks: int,
    baseline_labels: np.ndarray | None = None,
) -> dict:
    """Run one pipeline configuration and return summary metrics."""
    from scipy.spatial.distance import pdist
    from sklearn.metrics import adjusted_rand_score

    from poverty_tda.topology.multidim_ph import compute_rips_ph, persistence_summary
    from trajectory_tda.analysis.regime_discovery import discover_regimes
    from trajectory_tda.data.trajectory_builder import build_trajectories_from_raw
    from trajectory_tda.embedding.ngram_embed import ngram_embed
    from trajectory_tda.topology.trajectory_ph import maxmin_landmarks

    config_name = f"min{min_years}_{'tfidf' if tfidf else 'tf'}_thresh{thresh_pct}"
    logger.info(f"  Config: {config_name}")
    t0 = time.time()

    # Step 1: Build trajectories
    trajectories, _metadata = build_trajectories_from_raw(
        data_dir=data_dir,
        min_years=min_years,
        max_gap=2,
    )
    n_traj = len(trajectories)
    logger.info(f"    Trajectories: {n_traj}")

    # Step 2: Embed
    embeddings, embed_info = ngram_embed(
        trajectories,
        include_bigrams=True,
        tfidf=tfidf,
        pca_dim=20,
    )
    logger.info(f"    Embedding: {embeddings.shape}, " f"var={embed_info.get('explained_variance_ratio', 0):.4f}")

    # Step 3: PH with specified threshold percentile
    n_lm = min(n_landmarks, len(embeddings))
    _, landmarks = maxmin_landmarks(embeddings, n_lm, seed=42)

    # Compute threshold at specified percentile
    n_sample = min(500, len(landmarks))
    rng = np.random.RandomState(42)
    idx = rng.choice(len(landmarks), n_sample, replace=False)
    dists = pdist(landmarks[idx])
    thresh = float(np.percentile(dists, thresh_pct))
    logger.info(f"    Threshold: {thresh:.3f} ({thresh_pct}th pct)")

    ph = compute_rips_ph(landmarks, max_dim=1, thresh=thresh)
    ph_summary = persistence_summary(ph)

    h0_info = ph_summary.get("H0", {})
    h1_info = ph_summary.get("H1", {})

    # Step 4: GMM regime discovery
    regimes = discover_regimes(embeddings, trajectories)
    k_opt = regimes["k_optimal"]
    labels = np.array(regimes["gmm_labels"])
    logger.info(f"    GMM k_optimal: {k_opt}")

    # Compare to baseline if available
    ari = None
    if baseline_labels is not None and len(labels) == len(baseline_labels):
        ari = float(adjusted_rand_score(baseline_labels, labels))
        logger.info(f"    ARI vs baseline: {ari:.4f}")

    elapsed = time.time() - t0
    return {
        "config": config_name,
        "min_years": min_years,
        "tfidf": tfidf,
        "thresh_percentile": thresh_pct,
        "n_trajectories": n_traj,
        "embedding_shape": list(embeddings.shape),
        "explained_variance": embed_info.get("explained_variance_ratio"),
        "threshold_value": thresh,
        "h0_n_finite": h0_info.get("n_finite", 0),
        "h0_total_persistence": h0_info.get("total_persistence", 0),
        "h0_max_persistence": h0_info.get("max_persistence", 0),
        "h0_entropy": h0_info.get("persistence_entropy", 0),
        "h1_n_finite": h1_info.get("n_finite", 0),
        "h1_total_persistence": h1_info.get("total_persistence", 0),
        "h1_max_persistence": h1_info.get("max_persistence", 0),
        "h1_entropy": h1_info.get("persistence_entropy", 0),
        "k_optimal": k_opt,
        "ari_vs_baseline": ari,
        "elapsed_seconds": elapsed,
    }


def run_sensitivity(args: argparse.Namespace) -> dict:
    """Run all sensitivity configurations."""
    output_dir = Path(args.output_dir)

    # Load baseline labels for ARI comparison
    baseline_labels = None
    baseline_path = Path(args.baseline_dir) / "05_analysis.json"
    if baseline_path.exists():
        with open(baseline_path) as f:
            baseline = json.load(f)
        baseline_labels = np.array(baseline["gmm_labels"])
        logger.info(f"Loaded baseline labels (n={len(baseline_labels)})")

    # Define configurations to test
    # Axis 1: min_years (8, 10, 12) — hold others at baseline
    # Axis 2: tfidf (True/False) — hold others at baseline
    # Axis 3: thresh_pct (50, 75, 90) — hold others at baseline
    configs = [
        # Baseline
        {"min_years": 10, "tfidf": False, "thresh_pct": 75},
        # Vary min_years
        {"min_years": 8, "tfidf": False, "thresh_pct": 75},
        {"min_years": 12, "tfidf": False, "thresh_pct": 75},
        # Vary tfidf
        {"min_years": 10, "tfidf": True, "thresh_pct": 75},
        # Vary threshold
        {"min_years": 10, "tfidf": False, "thresh_pct": 50},
        {"min_years": 10, "tfidf": False, "thresh_pct": 90},
    ]

    results = []
    for cfg in configs:
        result = _run_single_config(
            data_dir=args.data_dir,
            n_landmarks=args.landmarks,
            baseline_labels=baseline_labels,
            **cfg,
        )
        results.append(result)
        # Save incrementally
        _save_json({"configs": results}, output_dir / "pipeline_sensitivity.json")

    # Summarise stability
    baseline_result = results[0]
    summary = {
        "baseline": baseline_result["config"],
        "n_configs": len(results),
        "k_optimal_range": [r["k_optimal"] for r in results],
        "k_stable": len(set(r["k_optimal"] for r in results)) == 1,
        "h0_persistence_range": [r["h0_total_persistence"] for r in results],
        "h1_persistence_range": [r["h1_total_persistence"] for r in results],
        "ari_values": {r["config"]: r["ari_vs_baseline"] for r in results if r["ari_vs_baseline"] is not None},
    }

    final = {"configs": results, "summary": summary}
    _save_json(final, output_dir / "pipeline_sensitivity.json")

    # Log summary
    logger.info("=" * 60)
    logger.info("Pipeline Sensitivity Summary")
    logger.info("=" * 60)
    for r in results:
        tag = " (BASELINE)" if r["config"] == baseline_result["config"] else ""
        ari_str = f", ARI={r['ari_vs_baseline']:.3f}" if r["ari_vs_baseline"] else ""
        logger.info(
            f"  {r['config']}{tag}: n={r['n_trajectories']}, "
            f"k={r['k_optimal']}, "
            f"H0_pers={r['h0_total_persistence']:.1f}, "
            f"H1_pers={r['h1_total_persistence']:.1f}"
            f"{ari_str}"
        )
    logger.info(f"  k_optimal stable: {summary['k_stable']}")
    logger.info("=" * 60)

    return final


def main():
    parser = argparse.ArgumentParser(description="P3.10: Pipeline sensitivity checks")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="trajectory_tda/data",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/trajectory_tda_robustness",
    )
    parser.add_argument(
        "--baseline-dir",
        type=str,
        default="results/trajectory_tda_integration",
    )
    parser.add_argument(
        "--landmarks",
        type=int,
        default=2000,
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    setup_logging(args.verbose)
    run_sensitivity(args)


if __name__ == "__main__":
    main()
