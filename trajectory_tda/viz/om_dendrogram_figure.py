"""OM dendrogram visualization for Paper 2 comparison.

Generates a colour-coded dendrogram from pre-computed optimal matching
Ward linkage, coloured by mean employment rate or PC1, for side-by-side
comparison with Mapper graph figures.

Uses existing results from ``results/trajectory_tda_robustness/om_baseline/``.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize
from scipy.cluster.hierarchy import dendrogram, fcluster

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate OM dendrogram coloured by outcome variable.")
    parser.add_argument(
        "--om-dir",
        type=Path,
        default=Path("results/trajectory_tda_robustness/om_baseline"),
        help="Directory with OM baseline results.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/trajectory_tda_integration"),
        help="Directory with P01 integration results.",
    )
    parser.add_argument(
        "--outcomes-path",
        type=Path,
        default=Path("trajectory_tda/data/trajectory_outcomes.npz"),
        help="Path to trajectory_outcomes.npz.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/trajectory_tda_mapper/figures"),
        help="Output directory for figures.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=7,
        help="Number of clusters to cut dendrogram at.",
    )
    return parser.parse_args()


def generate_om_dendrogram(
    linkage_matrix: np.ndarray,
    outcome_values: np.ndarray,
    outcome_name: str,
    k: int,
    output_path: Path,
    max_display: int = 50,
) -> dict:
    """Generate a truncated dendrogram coloured by cluster-level mean outcome.

    Args:
        linkage_matrix: (N-1, 4) Ward linkage matrix from scipy.
        outcome_values: (N,) outcome per trajectory.
        outcome_name: Label for the outcome variable.
        k: Number of clusters for colouring.
        output_path: File path for the saved figure.
        max_display: Maximum leaf nodes in truncated dendrogram.

    Returns:
        Dict with cluster-level statistics and figure path.
    """
    # Cut at k clusters
    labels = fcluster(linkage_matrix, t=k, criterion="maxclust")

    # Per-cluster statistics
    cluster_stats = {}
    for c in range(1, k + 1):
        mask = labels == c
        vals = outcome_values[mask]
        cluster_stats[c] = {
            "mean": float(np.mean(vals)),
            "std": float(np.std(vals)),
            "n": int(mask.sum()),
        }

    # Generate truncated dendrogram
    fig, ax = plt.subplots(figsize=(14, 6))

    # Use color_threshold=0 to get default coloring, then we overlay
    dendrogram(
        linkage_matrix,
        truncate_mode="lastp",
        p=max_display,
        leaf_rotation=90,
        leaf_font_size=8,
        ax=ax,
        no_labels=True,
        color_threshold=0,
        above_threshold_color="grey",
    )

    ax.set_title(
        f"OM Ward Dendrogram (k={k}, coloured by cluster-mean {outcome_name})",
        fontsize=13,
    )
    ax.set_ylabel("Ward distance")
    ax.set_xlabel(f"Clusters (truncated to {max_display} leaves)")

    # Add colour bar showing cluster-mean outcome
    norm = Normalize(
        vmin=min(s["mean"] for s in cluster_stats.values()),
        vmax=max(s["mean"] for s in cluster_stats.values()),
    )
    sm = plt.cm.ScalarMappable(cmap="RdYlGn", norm=norm)
    sm.set_array([])
    fig.colorbar(sm, ax=ax, shrink=0.6, label=f"Cluster-mean {outcome_name}")

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    logger.info("Saved OM dendrogram to %s", output_path)

    return {
        "k": k,
        "outcome": outcome_name,
        "cluster_stats": {str(c): s for c, s in cluster_stats.items()},
        "figure_path": str(output_path),
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    args = _parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Load linkage matrix
    linkage_path = args.om_dir / "02_ward_linkage.npy"
    linkage_matrix = np.load(linkage_path)
    logger.info("Loaded linkage matrix: %s", linkage_matrix.shape)

    # Load embeddings for PC1
    embeddings = np.load(args.results_dir / "embeddings.npy")
    pc1_values = embeddings[:, 0]

    # Load outcomes
    outcomes = np.load(args.outcomes_path)
    employment_rate = outcomes["employment_rate"]

    n_om = linkage_matrix.shape[0] + 1
    n_emb = len(pc1_values)
    n_out = len(employment_rate)
    logger.info(
        "Sizes: OM linkage implies N=%d, embeddings N=%d, outcomes N=%d",
        n_om,
        n_emb,
        n_out,
    )

    # Use the minimum overlapping size
    n = min(n_om, n_emb, n_out)

    results = {}

    # Dendrogram coloured by employment rate
    results["employment_rate"] = generate_om_dendrogram(
        linkage_matrix,
        employment_rate[:n],
        "employment_rate",
        k=args.k,
        output_path=args.output_dir / "fig11_om_dendrogram_employment.png",
    )

    # Dendrogram coloured by PC1
    results["pc1"] = generate_om_dendrogram(
        linkage_matrix,
        pc1_values[:n],
        "PC1",
        k=args.k,
        output_path=args.output_dir / "fig11_om_dendrogram_pc1.png",
    )

    # Save results JSON
    results_path = args.output_dir / "om_dendrogram_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info("Saved results to %s", results_path)


if __name__ == "__main__":
    main()
