"""
Phase 6 publication figures: regime switching, escape paths, phase PH.

Generates four panels:
    1. Transition matrix heatmap
    2. Escape probability horizon plot
    3. Phase PH persistence diagram + null violin
    4. Escape archetype barplots
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from trajectory_tda.viz.constants import (
    DPI,
    FIGSIZE_HALF,
    FIGSIZE_WIDE,
    PUBLICATION_RC,
    REGIME_LABELS,
)

logger = logging.getLogger(__name__)

plt.rcParams.update(PUBLICATION_RC)


def plot_transition_heatmap(
    transition_matrix: np.ndarray,
    out_path: Path,
    regime_labels: dict[int, str] | None = None,
) -> None:
    """Annotated heatmap of regime transition probabilities."""
    if regime_labels is None:
        regime_labels = REGIME_LABELS

    n = transition_matrix.shape[0]
    labels = [regime_labels.get(i, f"R{i}") for i in range(n)]

    fig, ax = plt.subplots(figsize=FIGSIZE_HALF)
    im = ax.imshow(transition_matrix, cmap="YlOrRd", vmin=0, vmax=1, aspect="auto")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("To regime")
    ax.set_ylabel("From regime")
    ax.set_title("Regime Transition Probabilities")

    # Annotate cells
    for i in range(n):
        for j in range(n):
            val = transition_matrix[i, j]
            color = "white" if val > 0.5 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=6, color=color)

    fig.colorbar(im, ax=ax, shrink=0.8, label="P(transition)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=DPI)
    plt.close(fig)
    logger.info(f"Saved: {out_path}")


def plot_escape_probabilities(
    escape_data: dict,
    out_path: Path,
) -> None:
    """Plot cumulative escape probability by horizon."""
    horizons = escape_data.get("escape_by_horizon", {})
    if not horizons:
        logger.warning("No escape horizon data to plot")
        return

    x = sorted(int(k) for k in horizons.keys())
    y = [horizons[str(h)] if isinstance(horizons.get(str(h)), float) else horizons.get(h, 0) for h in x]

    fig, ax = plt.subplots(figsize=FIGSIZE_HALF)
    ax.bar(x, y, color="#42a5f5", edgecolor="black", linewidth=0.5)
    ax.set_xlabel("Horizon (windows)")
    ax.set_ylabel("Cumulative escape fraction")
    ax.set_title("Escape Probability from Disadvantaged Regimes")
    ax.set_ylim(0, min(1.0, max(y) * 1.3) if y else 1.0)

    # Annotate
    for xi, yi in zip(x, y):
        ax.text(xi, yi + 0.01, f"{yi:.1%}", ha="center", va="bottom", fontsize=8)

    n_start = escape_data.get("n_starting_disadvantaged", "?")
    ever_rate = escape_data.get("ever_escape_rate", 0)
    ax.text(
        0.95,
        0.95,
        f"N={n_start}, ever={ever_rate:.1%}",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "wheat", "alpha": 0.8},
    )

    fig.tight_layout()
    fig.savefig(out_path, dpi=DPI)
    plt.close(fig)
    logger.info(f"Saved: {out_path}")


def plot_phase_ph_with_nulls(
    diagrams: dict,
    null_distributions: dict,
    observed: dict,
    p_values: dict,
    out_path: Path,
) -> None:
    """Persistence diagram + null distribution violin for phase PH."""
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)

    # Left: persistence diagram
    ax = axes[0]
    colors = {0: "#1a237e", 1: "#b71c1c"}
    for dim_str, dgm in diagrams.items():
        dim = int(dim_str)
        arr = np.array(dgm)
        if len(arr) == 0:
            continue
        births = arr[:, 0]
        deaths = arr[:, 1]
        ax.scatter(
            births,
            deaths,
            s=8,
            alpha=0.5,
            color=colors.get(dim, "gray"),
            label=f"H{dim} ({len(arr)} features)",
        )

    # Diagonal
    lims = ax.get_xlim()
    ax.plot(lims, lims, "k--", linewidth=0.5, alpha=0.3)
    ax.set_xlabel("Birth")
    ax.set_ylabel("Death")
    ax.set_title("Phase PH Diagram")
    ax.legend(fontsize=7)

    # Right: null violin
    ax = axes[1]
    dim_keys = sorted(null_distributions.keys())
    positions = list(range(len(dim_keys)))
    ax.violinplot(
        [null_distributions[k] for k in dim_keys],
        positions=positions,
        showmeans=True,
        showmedians=True,
    )

    # Overlay observed values
    for i, k in enumerate(dim_keys):
        obs_val = observed.get(k, 0)
        ax.scatter(
            [i],
            [obs_val],
            color="red",
            zorder=5,
            s=60,
            marker="D",
            label="Observed" if i == 0 else None,
        )
        pval = p_values.get(k, 1.0)
        ax.annotate(
            f"p={pval:.3f}",
            (i, obs_val),
            textcoords="offset points",
            xytext=(10, 5),
            fontsize=7,
        )

    ax.set_xticks(positions)
    ax.set_xticklabels(dim_keys)
    ax.set_ylabel("Total persistence")
    ax.set_title("Phase-Order Shuffle Null Test")
    ax.legend(fontsize=7)

    fig.tight_layout()
    fig.savefig(out_path, dpi=DPI)
    plt.close(fig)
    logger.info(f"Saved: {out_path}")


def plot_escape_archetypes(
    cluster_data: dict,
    out_path: Path,
) -> None:
    """Bar chart of escape archetype cluster profiles."""
    profiles = cluster_data.get("cluster_profiles", {})
    if not profiles:
        logger.warning("No cluster profiles to plot")
        return

    clusters = sorted(profiles.keys(), key=lambda x: int(x))
    n_clusters = len(clusters)

    metrics = ["mean_path_length", "mean_regime_changes", "mean_unique_regimes"]
    metric_labels = ["Path Length", "Regime Changes", "Unique Regimes"]

    fig, axes = plt.subplots(1, len(metrics), figsize=FIGSIZE_WIDE)
    if len(metrics) == 1:
        axes = [axes]

    colors = plt.cm.Set2(np.linspace(0, 1, max(n_clusters, 3)))

    for ax, metric, label in zip(axes, metrics, metric_labels):
        values = [profiles[c].get(metric, 0) for c in clusters]
        n_members = [profiles[c].get("n_members", 0) for c in clusters]
        ax.bar(
            range(n_clusters),
            values,
            color=colors[:n_clusters],
            edgecolor="black",
            linewidth=0.5,
        )
        ax.set_xticks(range(n_clusters))
        ax.set_xticklabels([f"C{c}\n(n={n_members[i]})" for i, c in enumerate(clusters)], fontsize=7)
        ax.set_ylabel(label)
        ax.set_title(label)

    sil = cluster_data.get("silhouette", 0)
    fig.suptitle(
        f"Escape Path Archetypes (k={n_clusters}, sil={sil:.3f})",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=DPI)
    plt.close(fig)
    logger.info(f"Saved: {out_path}")


def generate_all_phase6_figures(phase6_dir: str | Path) -> None:
    """Generate all Phase 6 figures from saved checkpoint data."""
    d = Path(phase6_dir)
    fig_dir = d / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # 1. Transition heatmap
    trans_path = d / "03_regime_transitions.json"
    if trans_path.exists():
        with open(trans_path) as f:
            trans_data = json.load(f)
        tm = np.array(trans_data["transition_matrix"])
        plot_transition_heatmap(tm, fig_dir / "transition_heatmap.pdf")

        # 2. Escape probabilities
        esc = trans_data.get("escape_probabilities", {})
        if esc:
            plot_escape_probabilities(esc, fig_dir / "escape_probabilities.pdf")
    else:
        logger.warning(f"Missing {trans_path}")

    # 3. Phase PH + nulls
    dgm_path = d / "05_phase_ph_diagrams.json"
    null_path = d / "06_phase_nulls.json"
    if dgm_path.exists() and null_path.exists():
        with open(dgm_path) as f:
            diagrams = json.load(f)
        with open(null_path) as f:
            null_data = json.load(f)
        plot_phase_ph_with_nulls(
            diagrams,
            null_data["null_distributions"],
            null_data["observed"],
            null_data["p_values"],
            fig_dir / "phase_ph_nulls.pdf",
        )
    else:
        logger.warning("Missing diagrams or null data for phase PH figure")

    # 4. Escape archetypes
    cluster_path = d / "08_escape_clusters.json"
    if cluster_path.exists():
        with open(cluster_path) as f:
            cluster_data = json.load(f)
        plot_escape_archetypes(cluster_data, fig_dir / "escape_archetypes.pdf")
    else:
        logger.warning(f"Missing {cluster_path}")

    logger.info(f"All Phase 6 figures saved to {fig_dir}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Phase 6 figures")
    parser.add_argument(
        "--phase6-dir",
        type=str,
        default="results/trajectory_tda_phase6",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    generate_all_phase6_figures(args.phase6_dir)
