"""
UMAP sensitivity check: re-embed trajectories with UMAP-16D and compare
regime assignments to PCA-20D baseline using Adjusted Rand Index.

Generates Figure S1 (supplementary) and saves UMAP embeddings.

Usage:
    python -m trajectory_tda.scripts.run_umap_sensitivity \\
        --results-dir results/trajectory_tda_integration \\
        --data-dir trajectory_tda/data
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def run_umap_sensitivity(args: argparse.Namespace) -> dict:
    """Run UMAP embedding and compare to PCA regimes."""
    from trajectory_tda.analysis.regime_discovery import discover_regimes
    from trajectory_tda.data.trajectory_builder import build_trajectories_from_raw
    from trajectory_tda.embedding.ngram_embed import ngram_embed

    t0 = time.time()
    results_dir = Path(args.results_dir)

    # ─── Load PCA baseline ───
    logger.info("Loading PCA-20D baseline...")
    pca_embeddings = np.load(results_dir / "embeddings.npy")

    with open(results_dir / "05_analysis.json") as f:
        analysis = json.load(f)
    pca_labels = np.array(analysis["gmm_labels"])
    logger.info(
        f"PCA-20D: {pca_embeddings.shape}, {len(np.unique(pca_labels))} regimes"
    )

    # ─── Rebuild trajectories ───
    logger.info("Rebuilding trajectories for UMAP re-embedding...")
    trajectories, _ = build_trajectories_from_raw(
        data_dir=args.data_dir,
        min_years=10,
        max_gap=2,
    )
    logger.info(f"Rebuilt {len(trajectories)} trajectories")

    # ─── UMAP-16D embedding ───
    logger.info("Computing UMAP-16D embedding...")
    umap_embeddings, umap_info = ngram_embed(
        trajectories,
        include_bigrams=True,
        tfidf=False,
        pca_dim=None,
        umap_dim=16,
    )
    logger.info(f"UMAP-16D: {umap_embeddings.shape}")

    # Save UMAP embeddings
    umap_path = results_dir / "embeddings_umap16.npy"
    np.save(umap_path, umap_embeddings)
    logger.info(f"Saved UMAP embeddings: {umap_path}")

    # ─── Regime discovery on UMAP ───
    logger.info("Running regime discovery on UMAP-16D...")
    umap_regimes = discover_regimes(umap_embeddings, trajectories)
    umap_labels = umap_regimes["gmm_labels"]
    logger.info(f"UMAP regimes: k={umap_regimes['k_optimal']}")

    # ─── Compare via Adjusted Rand Index ───
    from sklearn.metrics import adjusted_rand_score

    ari = adjusted_rand_score(pca_labels, umap_labels)
    logger.info(f"ARI (PCA-20D vs UMAP-16D): {ari:.4f}")

    # Save results
    sensitivity_results = {
        "pca_shape": list(pca_embeddings.shape),
        "umap_shape": list(umap_embeddings.shape),
        "pca_k": int(len(np.unique(pca_labels))),
        "umap_k": int(umap_regimes["k_optimal"]),
        "ari": float(ari),
        "umap_info": umap_info,
        "umap_labels": umap_labels.tolist(),
        "elapsed_seconds": time.time() - t0,
    }

    out_path = results_dir / "07_umap_sensitivity.json"
    with open(out_path, "w") as f:
        json.dump(sensitivity_results, f, indent=2)
    logger.info(f"Saved: {out_path}")

    # ─── Generate Figure S1 ───
    logger.info("Generating Figure S1...")
    _generate_fig_s1(umap_embeddings, umap_labels, pca_labels, ari, args.output_dir)

    logger.info(f"UMAP sensitivity check complete: ARI={ari:.4f}")
    return sensitivity_results


def _generate_fig_s1(
    umap_embeddings: np.ndarray,
    umap_labels: np.ndarray,
    pca_labels: np.ndarray,
    ari: float,
    output_dir: str,
) -> None:
    """Generate Figure S1: UMAP embedding colored by UMAP regimes + PCA regimes."""
    import matplotlib.pyplot as plt

    from trajectory_tda.viz.constants import DPI, FIGSIZE_WIDE, PUBLICATION_RC

    plt.rcParams.update(PUBLICATION_RC)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use UMAP for 2D vis (first 2 components for quick check)
    try:
        import umap

        vis = umap.UMAP(n_components=2, random_state=42).fit_transform(umap_embeddings)
    except ImportError:
        from sklearn.decomposition import PCA

        vis = PCA(n_components=2).fit_transform(umap_embeddings)

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)

    for ax, labels, title in [
        (axes[0], umap_labels, "UMAP-16D Regimes"),
        (axes[1], pca_labels, "PCA-20D Regimes (projected)"),
    ]:
        ax.scatter(
            vis[:, 0],
            vis[:, 1],
            c=labels,
            cmap="Set2",
            s=0.3,
            alpha=0.3,
            rasterized=True,
        )
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("UMAP-1")
        ax.set_ylabel("UMAP-2")
        ax.tick_params(labelsize=7)

    fig.suptitle(
        f"Embedding Sensitivity: UMAP-16D vs PCA-20D (ARI = {ari:.3f})",
        fontsize=11,
    )
    fig.tight_layout()

    fig.savefig(output_dir / "figS1_umap_sensitivity.pdf", format="pdf")
    fig.savefig(output_dir / "figS1_umap_sensitivity.png", format="png", dpi=DPI)
    plt.close(fig)
    logger.info("Saved figS1_umap_sensitivity.pdf + .png")


def main():
    parser = argparse.ArgumentParser(description="UMAP sensitivity check")
    parser.add_argument(
        "--results-dir",
        type=str,
        default="results/trajectory_tda_integration",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="trajectory_tda/data",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="figures/trajectory_tda",
    )
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    run_umap_sensitivity(args)


if __name__ == "__main__":
    main()
