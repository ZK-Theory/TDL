"""
Publication figures for the trajectory TDA paper.

Generates Figures 1–11 + S1 from pipeline checkpoint data.
All figures follow Journal of Economic Geography submission standards:
PDF vector + PNG 300 DPI, full-width 190mm, perceptually uniform colormaps.

Usage:
    python -m trajectory_tda.viz.paper_figures \\
        --results-dir results/trajectory_tda_integration \\
        --output-dir figures/trajectory_tda
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.figure import Figure

from trajectory_tda.viz.constants import (
    DPI,
    FIGSIZE_FULL,
    FIGSIZE_WIDE,
    PUBLICATION_RC,
    REGIME_LABELS,
    STATE_COLORS,
    STATES,
)

logger = logging.getLogger(__name__)

plt.rcParams.update(PUBLICATION_RC)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _save_figure(fig: Figure, output_dir: Path, name: str) -> None:
    """Save figure in both PDF and PNG formats."""
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / f"{name}.pdf", format="pdf")
    fig.savefig(output_dir / f"{name}.png", format="png", dpi=DPI)
    logger.info(f"Saved {name}.pdf + .png")


def _load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _state_colormap() -> ListedColormap:
    """Create a ListedColormap for the 9 states in STATES order."""
    return ListedColormap([STATE_COLORS[s] for s in STATES])


# ─────────────────────────────────────────────────────────────────────
# Figure 1: Data Overview & Trajectory Heatmap
# ─────────────────────────────────────────────────────────────────────


def plot_trajectory_heatmap(
    analysis: dict,
    figsize: tuple[float, float] = FIGSIZE_WIDE,
    title: str = "Trajectory Exemplars by Mobility Regime",
    save_path: Path | None = None,
) -> Figure:
    """State-sequence heatmap with 5 exemplar trajectories per regime.

    Args:
        analysis: Loaded 05_analysis.json with regime_exemplars
        figsize: Figure dimensions
        title: Plot title
        save_path: Output directory (saves fig1_trajectory_heatmap)

    Returns:
        matplotlib Figure
    """
    exemplars = analysis.get("regime_exemplars", {})
    if not exemplars:
        logger.warning("No regime exemplars in analysis data")
        return plt.figure()

    state_to_idx = {s: i for i, s in enumerate(STATES)}
    cmap = _state_colormap()

    # Collect all exemplar trajectories with regime labels
    rows = []
    row_labels = []
    for regime_id in sorted(exemplars.keys(), key=int):
        trajs = exemplars[regime_id]["trajectories"]
        label = REGIME_LABELS.get(int(regime_id), f"Regime {regime_id}")
        for i, traj in enumerate(trajs[:5]):
            row = [state_to_idx.get(s, 0) for s in traj]
            rows.append(row)
            row_labels.append(f"{label}" if i == 0 else "")

    # Pad to equal length
    max_len = max(len(r) for r in rows)
    padded = np.full((len(rows), max_len), np.nan)
    for i, row in enumerate(rows):
        padded[i, : len(row)] = row

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(
        padded,
        aspect="auto",
        cmap=cmap,
        vmin=0,
        vmax=len(STATES) - 1,
        interpolation="nearest",
    )

    ax.set_xlabel("Year in Trajectory")
    ax.set_ylabel("")
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels, fontsize=8)
    ax.set_title(title)

    # Add horizontal lines between regimes
    for i in range(5, len(rows), 5):
        ax.axhline(i - 0.5, color="black", linewidth=0.8)

    # Colorbar with state labels
    cbar = fig.colorbar(im, ax=ax, ticks=range(len(STATES)))
    cbar.ax.set_yticklabels(STATES, fontsize=8)

    fig.tight_layout()
    if save_path:
        _save_figure(fig, save_path, "fig1_trajectory_heatmap")
    return fig


# ─────────────────────────────────────────────────────────────────────
# Figure 2: Embedding Point Cloud (UMAP 2D projection)
# ─────────────────────────────────────────────────────────────────────


def plot_embedding_cloud(
    embeddings: np.ndarray,
    labels: np.ndarray,
    figsize: tuple[float, float] = FIGSIZE_FULL,
    title: str = "Trajectory Embedding Space (PCA-20D → UMAP-2D)",
    save_path: Path | None = None,
) -> Figure:
    """UMAP 2D projection of embeddings, colored by regime.

    Args:
        embeddings: (N, D) embeddings (will be reduced to 2D via UMAP)
        labels: (N,) regime assignments
        figsize: Figure dimensions
        title: Plot title
        save_path: Output directory

    Returns:
        matplotlib Figure
    """
    from sklearn.preprocessing import StandardScaler

    try:
        from umap import UMAP
    except ImportError:
        logger.warning("umap-learn not available; using PCA 2D fallback")
        from sklearn.decomposition import PCA

        reducer = PCA(n_components=2, random_state=42)
        title = title.replace("UMAP-2D", "PCA-2D")
    else:
        reducer = UMAP(n_components=2, random_state=42, n_neighbors=30, min_dist=0.3)

    scaled = StandardScaler().fit_transform(embeddings)
    coords = reducer.fit_transform(scaled)

    unique_labels = np.unique(labels)
    # Use a qualitative colormap
    cmap_set2 = plt.colormaps.get_cmap("Set2")
    colors = cmap_set2(np.linspace(0, 1, len(unique_labels)))

    fig, ax = plt.subplots(figsize=figsize)

    for i, lab in enumerate(unique_labels):
        mask = labels == lab
        regime_name = REGIME_LABELS.get(int(lab), f"Regime {lab}")
        ax.scatter(
            coords[mask, 0],
            coords[mask, 1],
            c=[colors[i]],
            s=3,
            alpha=0.4,
            label=f"{regime_name} (n={mask.sum():,})",
            rasterized=True,
        )
        # Centroid
        cx, cy = coords[mask].mean(axis=0)
        ax.scatter(
            cx, cy, c=[colors[i]], s=80, edgecolors="black", linewidths=0.8, zorder=5
        )

    ax.set_xlabel("Component 1")
    ax.set_ylabel("Component 2")
    ax.set_title(title)
    ax.legend(fontsize=7, markerscale=3, loc="best", framealpha=0.9)

    fig.tight_layout()
    if save_path:
        _save_figure(fig, save_path, "fig2_embedding_cloud")
    return fig


# ─────────────────────────────────────────────────────────────────────
# Figure 3: Persistence Diagrams (H₀ + H₁)
# ─────────────────────────────────────────────────────────────────────


def plot_persistence_diagrams(
    diagrams: dict,
    method: str = "maxmin_vr",
    n_highlight_h1: int = 50,
    n_barcode: int = 30,
    figsize: tuple[float, float] = FIGSIZE_WIDE,
    title: str = "Persistence Diagrams",
    save_path: Path | None = None,
) -> Figure:
    """Plot H₀ and H₁ persistence diagrams side by side.

    H₀ includes an inset barcode of the top features, since all VR H₀
    births are at 0 and the standard scatter degenerates to a vertical
    stripe.

    Args:
        diagrams: Loaded 03_ph_diagrams.json with {method: {dim: [[b,d],...]}}
        method: PH method key
        n_highlight_h1: Number of top H₁ features to highlight
        n_barcode: Number of top H₀ features to show in barcode inset
        figsize: Figure dimensions
        title: Plot title
        save_path: Output directory

    Returns:
        matplotlib Figure
    """
    method_data = diagrams.get(method, {})

    fig, axes = plt.subplots(1, 2, figsize=figsize)

    for ax_idx, dim_key in enumerate(["0", "1"]):
        ax = axes[ax_idx]
        pairs = np.array(method_data.get(dim_key, []))
        dim_label = f"H{dim_key}"

        if len(pairs) == 0:
            ax.set_title(f"{dim_label}: No features")
            continue

        births = pairs[:, 0]
        deaths = pairs[:, 1]

        # Filter finite
        finite = np.isfinite(deaths)
        b_fin = births[finite]
        d_fin = deaths[finite]
        persistence = d_fin - b_fin

        # Diagonal
        lim_min = min(b_fin.min(), 0) if len(b_fin) > 0 else 0
        lim_max = d_fin.max() * 1.05 if len(d_fin) > 0 else 1
        ax.plot(
            [lim_min, lim_max],
            [lim_min, lim_max],
            "k--",
            linewidth=0.5,
            alpha=0.5,
        )

        if dim_key == "0":
            # H₀: color by persistence
            sc = ax.scatter(
                b_fin,
                d_fin,
                c=persistence,
                cmap="viridis",
                s=4,
                alpha=0.6,
                rasterized=True,
            )
            fig.colorbar(sc, ax=ax, label="Persistence", shrink=0.7)
            # Mark infinite features
            inf_mask = ~finite
            if inf_mask.any():
                ax.scatter(
                    births[inf_mask],
                    np.full(inf_mask.sum(), lim_max),
                    marker="^",
                    c="red",
                    s=20,
                    label=f"∞ ({inf_mask.sum()})",
                )
                ax.legend(fontsize=8)

            # ── Barcode inset for H₀ ──────────────────────────────
            # All VR H₀ births are 0, so the scatter degenerates to a
            # vertical stripe. An inset barcode of the top features
            # makes the gap structure readable.
            if len(persistence) > 0:
                n_show = min(n_barcode, len(persistence))
                top_idx = np.argsort(persistence)[::-1][:n_show]
                top_deaths = d_fin[top_idx]
                # Sort by death (descending) for visual clarity
                bar_order = np.argsort(top_deaths)[::-1]
                top_deaths = top_deaths[bar_order]

                inset = ax.inset_axes([0.30, 0.22, 0.62, 0.58])
                colors = plt.cm.viridis(top_deaths / top_deaths.max())
                y_pos = np.arange(n_show)
                inset.barh(
                    y_pos,
                    top_deaths,
                    height=0.8,
                    color=colors,
                    edgecolor="none",
                )
                inset.set_xlim(0, lim_max)
                inset.set_yticks([])
                inset.set_xlabel(
                    "Death (= persistence)",
                    fontsize=6,
                    labelpad=2,
                )
                inset.set_title(
                    f"Top {n_show} $H_0$ bars",
                    fontsize=7,
                    pad=3,
                )
                inset.tick_params(labelsize=5, pad=1)
                # White background with subtle border
                inset.patch.set_facecolor("white")
                inset.patch.set_alpha(0.95)
                for spine in inset.spines.values():
                    spine.set_edgecolor("0.5")
                    spine.set_linewidth(0.6)
        else:
            # H₁: highlight top features
            order = np.argsort(persistence)[::-1]
            n_top = min(n_highlight_h1, len(order))

            # Background
            ax.scatter(
                b_fin[order[n_top:]],
                d_fin[order[n_top:]],
                c="lightgray",
                s=3,
                alpha=0.4,
                rasterized=True,
            )
            # Top features
            sc = ax.scatter(
                b_fin[order[:n_top]],
                d_fin[order[:n_top]],
                c=persistence[order[:n_top]],
                cmap="magma",
                s=15,
                alpha=0.8,
                edgecolors="black",
                linewidths=0.3,
            )
            fig.colorbar(sc, ax=ax, label="Persistence", shrink=0.7)

            # Significance threshold line
            if len(persistence) > 0:
                max_pers = persistence.max()
                thresh = max_pers * 0.1
                ax.axhline(
                    y=thresh,
                    color="red",
                    linestyle=":",
                    linewidth=0.8,
                    label=f"10% threshold ({thresh:.2f})",
                )
                ax.legend(fontsize=8)

        ax.set_xlabel("Birth")
        ax.set_ylabel("Death")
        ax.set_title(f"{dim_label} ({len(b_fin):,} features)")
        ax.set_xlim(lim_min, lim_max)
        ax.set_ylim(lim_min, lim_max)
        ax.set_aspect("equal")

    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    if save_path:
        _save_figure(fig, save_path, "fig3_persistence_diagrams")
    return fig


# ─────────────────────────────────────────────────────────────────────
# Figure 4: Betti Curves — Observed vs Null Envelopes
# ─────────────────────────────────────────────────────────────────────


def plot_betti_null_comparison(
    nulls: dict,
    null_type_h0: str = "order_shuffle",
    null_type_h1: str = "markov",
    figsize: tuple[float, float] = FIGSIZE_WIDE,
    title: str = "Null Model Comparison: Observed vs Null Distributions",
    save_path: Path | None = None,
) -> Figure:
    """Plot observed vs null total persistence distributions.

    Args:
        nulls: Loaded 04_nulls.json with null_distribution arrays
        null_type_h0: Null model to show for H₀ panel
        null_type_h1: Null model to show for H₁ panel
        figsize: Figure dimensions
        title: Plot title
        save_path: Output directory

    Returns:
        matplotlib Figure
    """
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    panels = [
        (axes[0], null_type_h0, "H0", "H₀ Total Persistence"),
        (axes[1], null_type_h1, "H1", "H₁ Total Persistence"),
    ]

    for ax, null_type, dim_key, panel_title in panels:
        null_data = nulls.get(null_type, {})
        dim_data = null_data.get(dim_key, {})

        observed = dim_data.get("observed")
        null_dist = dim_data.get("null_distribution", [])
        p_value = dim_data.get("p_value")

        if not null_dist or observed is None:
            ax.text(
                0.5,
                0.5,
                f"No data for {null_type}",
                transform=ax.transAxes,
                ha="center",
                va="center",
            )
            ax.set_title(panel_title)
            continue

        null_arr = np.array(null_dist)

        ax.hist(
            null_arr,
            bins=30,
            alpha=0.6,
            color="steelblue",
            density=True,
            label=f"Null ({null_type})",
        )
        ax.axvline(
            observed, color="red", linewidth=2, label=f"Observed ({observed:,.1f})"
        )

        # Null envelope
        null_mean = null_arr.mean()
        null_std = null_arr.std()
        ax.axvline(null_mean, color="steelblue", linewidth=1, linestyle="--", alpha=0.7)
        ax.axvspan(
            null_mean - 2 * null_std,
            null_mean + 2 * null_std,
            alpha=0.15,
            color="steelblue",
            label="±2σ",
        )

        p_str = f"p = {p_value:.4f}" if p_value is not None else ""
        sig = (
            "★ Significant"
            if p_value is not None and p_value < 0.05
            else "Not significant"
        )
        ax.set_title(f"{panel_title}\n{null_type} ({sig}, {p_str})")
        ax.set_xlabel("Total Persistence")
        ax.set_ylabel("Density")
        ax.legend(fontsize=8)

    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    if save_path:
        _save_figure(fig, save_path, "fig4_betti_null_comparison")
    return fig


# ─────────────────────────────────────────────────────────────────────
# Figure 5: Regime Profiles Heatmap
# ─────────────────────────────────────────────────────────────────────


def plot_regime_profiles(
    analysis: dict,
    figsize: tuple[float, float] = FIGSIZE_WIDE,
    title: str = "Mobility Regime Profiles",
    save_path: Path | None = None,
) -> Figure:
    """Heatmap of regime characteristics (7 regimes × key metrics).

    Args:
        analysis: Loaded 05_analysis.json
        figsize: Figure dimensions
        title: Plot title
        save_path: Output directory

    Returns:
        matplotlib Figure
    """
    profiles = analysis.get("regimes", {}).get("profiles", {})
    if not profiles:
        return plt.figure()

    metrics = [
        "employment_rate",
        "unemployment_rate",
        "inactivity_rate",
        "low_income_rate",
        "mid_income_rate",
        "high_income_rate",
        "stability",
        "mean_transition_rate",
    ]
    metric_labels = [
        "Employment",
        "Unemployment",
        "Inactivity",
        "Low Income",
        "Mid Income",
        "High Income",
        "Stability",
        "Transition Rate",
    ]

    sorted_keys = sorted(profiles.keys(), key=int)
    n_regimes = len(sorted_keys)

    data = np.zeros((n_regimes, len(metrics)))
    row_labels = []
    for i, key in enumerate(sorted_keys):
        p = profiles[key]
        for j, m in enumerate(metrics):
            data[i, j] = p.get(m, 0)
        label = REGIME_LABELS.get(int(key), f"Regime {key}")
        n = p.get("n_members", 0)
        row_labels.append(f"{label}\n(n={n:,})")

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(data, aspect="auto", cmap="RdYlBu_r")

    ax.set_xticks(range(len(metric_labels)))
    ax.set_xticklabels(metric_labels, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(n_regimes))
    ax.set_yticklabels(row_labels, fontsize=8)
    ax.set_title(title)

    # Annotate cells with values
    for i in range(n_regimes):
        for j in range(len(metrics)):
            val = data[i, j]
            color = "white" if val > 0.6 or val < 0.15 else "black"
            ax.text(
                j, i, f"{val:.0%}", ha="center", va="center", fontsize=7, color=color
            )

    fig.colorbar(im, ax=ax, shrink=0.7, label="Rate")
    fig.tight_layout()
    if save_path:
        _save_figure(fig, save_path, "fig5_regime_profiles")
    return fig


# ─────────────────────────────────────────────────────────────────────
# Figure 6: Stability–Income Correlation
# ─────────────────────────────────────────────────────────────────────


def plot_stability_income(
    analysis: dict,
    figsize: tuple[float, float] = FIGSIZE_FULL,
    title: str = "Regime Stability vs High-Income Rate",
    save_path: Path | None = None,
) -> Figure:
    """Scatter of stability vs high_income_rate, sized by n_members.

    Args:
        analysis: Loaded 05_analysis.json
        figsize: Figure dimensions
        title: Plot title
        save_path: Output directory

    Returns:
        matplotlib Figure
    """
    from scipy import stats

    profiles = analysis.get("regimes", {}).get("profiles", {})
    if not profiles:
        return plt.figure()

    sorted_keys = sorted(profiles.keys(), key=int)
    stability = [profiles[k]["stability"] for k in sorted_keys]
    high_income = [profiles[k]["high_income_rate"] for k in sorted_keys]
    n_members = [profiles[k]["n_members"] for k in sorted_keys]

    cmap_set2 = plt.colormaps.get_cmap("Set2")
    colors = cmap_set2(np.linspace(0, 1, len(sorted_keys)))

    fig, ax = plt.subplots(figsize=figsize)

    for i, key in enumerate(sorted_keys):
        label = REGIME_LABELS.get(int(key), f"Regime {key}")
        ax.scatter(
            stability[i],
            high_income[i],
            s=n_members[i] / 15,  # Scale size
            c=[colors[i]],
            edgecolors="black",
            linewidths=0.5,
            label=f"{label} (n={n_members[i]:,})",
            zorder=5,
        )

    # Annotate key regimes
    for i, key in enumerate(sorted_keys):
        regime_id = int(key)
        if regime_id in (1, 6):
            label = REGIME_LABELS.get(regime_id, "")
            ax.annotate(
                label,
                (stability[i], high_income[i]),
                textcoords="offset points",
                xytext=(10, 10),
                fontsize=8,
                arrowprops={"arrowstyle": "->", "color": "gray", "lw": 0.8},
            )

    # Correlation
    r, p = stats.pearsonr(stability, high_income)
    ax.text(
        0.05,
        0.95,
        f"r = {r:.3f}, p = {p:.3f}",
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.8},
    )

    ax.set_xlabel("Stability (fraction in dominant state)")
    ax.set_ylabel("High-Income Rate")
    ax.set_title(title)
    ax.legend(fontsize=7, loc="lower right")

    fig.tight_layout()
    if save_path:
        _save_figure(fig, save_path, "fig6_stability_income")
    return fig


# ─────────────────────────────────────────────────────────────────────
# Figure 7: Cycle/Trap Analysis
# ─────────────────────────────────────────────────────────────────────


def plot_cycle_analysis(
    analysis: dict,
    diagrams: dict | None = None,
    method: str = "maxmin_vr",
    figsize: tuple[float, float] = FIGSIZE_WIDE,
    title: str = "H₁ Cycle / Trap Analysis",
    save_path: Path | None = None,
) -> Figure:
    """Panel: (A) top H₁ features birth/death, (B) cycle length distribution.

    Args:
        analysis: Loaded 05_analysis.json with cycles
        diagrams: Loaded 03_ph_diagrams.json (optional, for PD subplot)
        method: PH method key
        figsize: Figure dimensions
        title: Plot title
        save_path: Output directory

    Returns:
        matplotlib Figure
    """
    cycles = analysis.get("cycles", {})
    n_loops = cycles.get("n_persistent_loops", 0)

    fig, axes = plt.subplots(1, 2, figsize=figsize)

    # Panel A: H₁ persistence diagram
    ax = axes[0]
    if diagrams and method in diagrams:
        h1_pairs = np.array(diagrams[method].get("1", []))
        if len(h1_pairs) > 0:
            births = h1_pairs[:, 0]
            deaths = h1_pairs[:, 1]
            finite = np.isfinite(deaths)
            b_fin, d_fin = births[finite], deaths[finite]
            persistence = d_fin - b_fin

            # Sort by persistence, show top 20 in color
            order = np.argsort(persistence)[::-1]
            n_top = min(20, len(order))

            ax.scatter(
                b_fin[order[n_top:]],
                d_fin[order[n_top:]],
                c="lightgray",
                s=3,
                alpha=0.3,
                rasterized=True,
            )
            sc = ax.scatter(
                b_fin[order[:n_top]],
                d_fin[order[:n_top]],
                c=persistence[order[:n_top]],
                cmap="magma",
                s=25,
                edgecolors="black",
                linewidths=0.3,
            )
            fig.colorbar(sc, ax=ax, label="Persistence", shrink=0.7)

            lim = max(d_fin.max(), b_fin.max()) * 1.05
            ax.plot([0, lim], [0, lim], "k--", lw=0.5, alpha=0.5)
            ax.set_xlim(0, lim)
            ax.set_ylim(0, lim)
            ax.set_aspect("equal")
    ax.set_xlabel("Birth")
    ax.set_ylabel("Death")
    ax.set_title(f"H₁ Persistence ({n_loops:,} persistent loops)")

    # Panel B: Cycle length distribution from loop profiles
    ax = axes[1]
    loop_profiles = cycles.get("loop_profiles", [])  # May not exist in old results
    h1_summary = cycles.get("h1_summary", {})

    if loop_profiles:
        cycle_lengths = [
            lp.get("mean_cycle_length", 0)
            for lp in loop_profiles
            if lp.get("mean_cycle_length", 0) > 0
        ]
        if cycle_lengths:
            ax.hist(
                cycle_lengths,
                bins=30,
                color="steelblue",
                alpha=0.7,
                edgecolor="black",
                linewidth=0.3,
            )
            ax.axvline(
                np.median(cycle_lengths),
                color="red",
                linewidth=1.5,
                linestyle="--",
                label=f"Median: {np.median(cycle_lengths):.1f}",
            )
            ax.legend(fontsize=8)

    ax.set_xlabel("Mean Cycle Length (years)")
    ax.set_ylabel("Count")
    ax.set_title("Cycle Length Distribution")

    # Add text box with summary stats
    max_pers = h1_summary.get("max_persistence", 0)
    total_pers = h1_summary.get("total_persistence", 0)
    summary_text = (
        f"Max persistence: {max_pers:.2f}\n"
        f"Total persistence: {total_pers:.1f}\n"
        f"Persistent loops: {n_loops:,}"
    )
    ax.text(
        0.95,
        0.95,
        summary_text,
        transform=ax.transAxes,
        fontsize=8,
        verticalalignment="top",
        horizontalalignment="right",
        bbox={"boxstyle": "round", "facecolor": "lightyellow", "alpha": 0.9},
    )

    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    if save_path:
        _save_figure(fig, save_path, "fig7_cycle_analysis")
    return fig


# ─────────────────────────────────────────────────────────────────────
# Figure 8: Null Model Summary Table (Markov Ladder)
# ─────────────────────────────────────────────────────────────────────


def plot_null_table(
    nulls: dict,
    nulls_markov2: dict | None = None,
    figsize: tuple[float, float] = FIGSIZE_WIDE,
    title: str = "Null Model Validation Summary",
    save_path: Path | None = None,
) -> Figure:
    """Table-as-figure: null models × H₀/H₁ results with Markov ladder.

    Args:
        nulls: Loaded 04_nulls.json
        nulls_markov2: Loaded 04_nulls_markov2.json (optional)
        figsize: Figure dimensions
        title: Plot title
        save_path: Output directory

    Returns:
        matplotlib Figure
    """
    null_order = ["label_shuffle", "cohort_shuffle", "order_shuffle", "markov"]
    null_display = {
        "label_shuffle": "Label Shuffle",
        "cohort_shuffle": "Cohort Shuffle",
        "order_shuffle": "Order Shuffle",
        "markov": "Markov (order 1)",
    }

    if nulls_markov2:
        null_order.append("markov_2")
        null_display["markov_2"] = "Markov (order 2)"

    rows = []
    for null_type in null_order:
        if null_type == "markov_2":
            data = nulls_markov2.get("markov", {})
        else:
            data = nulls.get(null_type, {})

        if "error" in data or not data:
            continue

        row = [null_display.get(null_type, null_type)]
        for dim_key in ["H0", "H1"]:
            d = data.get(dim_key, {})
            obs = d.get("observed", 0)
            null_mean = d.get("null_mean", 0)
            null_std = d.get("null_std", 1)
            p = d.get("p_value")
            sig = d.get("significant_at_005", False)

            z = (obs - null_mean) / null_std if null_std > 0 else 0
            p_str = f"{p:.4f}" if p is not None else "—"
            sig_marker = "★" if sig else ""

            row.extend(
                [
                    f"{obs:,.1f}",
                    f"{null_mean:,.1f} ± {null_std:.1f}",
                    f"{z:.2f}",
                    p_str,
                    sig_marker,
                ]
            )
        rows.append(row)

    col_labels = [
        "Null Model",
        "H₀ Obs",
        "H₀ Null (μ ± σ)",
        "H₀ z",
        "H₀ p",
        "H₀ Sig",
        "H₁ Obs",
        "H₁ Null (μ ± σ)",
        "H₁ z",
        "H₁ p",
        "H₁ Sig",
    ]

    fig, ax = plt.subplots(figsize=figsize)
    ax.axis("off")

    table = ax.table(
        cellText=rows,
        colLabels=col_labels,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.auto_set_column_width(range(len(col_labels)))
    table.scale(1, 1.5)

    # Bold significant cells and color header
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#4472C4")
            cell.set_text_props(color="white", fontweight="bold")
        elif col in (4, 9) and row > 0:  # p-value columns
            text = cell.get_text().get_text()
            try:
                p_val = float(text)
                if p_val < 0.05:
                    cell.set_facecolor("#C6E0B4")
                    cell.set_text_props(fontweight="bold")
            except ValueError:
                pass

    ax.set_title(title, fontsize=12, pad=20)
    fig.tight_layout()
    if save_path:
        _save_figure(fig, save_path, "fig8_null_table")
    return fig


# ─────────────────────────────────────────────────────────────────────
# Figure 9: Markov Memory Depth Comparison
# ─────────────────────────────────────────────────────────────────────


def plot_markov_memory_depth(
    nulls: dict,
    nulls_markov2: dict | None = None,
    figsize: tuple[float, float] = FIGSIZE_WIDE,
    title: str = "Markov Memory Depth: Total Persistence by Null Model",
    save_path: Path | None = None,
) -> Figure:
    """Violin/histogram comparison of observed vs Markov-1 vs Markov-2 nulls.

    Args:
        nulls: Loaded 04_nulls.json (contains order_shuffle + markov)
        nulls_markov2: Loaded 04_nulls_markov2.json (optional)
        figsize: Figure dimensions
        title: Plot title
        save_path: Output directory

    Returns:
        matplotlib Figure
    """
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    for ax_idx, dim_key in enumerate(["H0", "H1"]):
        ax = axes[ax_idx]
        dim_label = "H₀" if dim_key == "H0" else "H₁"

        distributions = []
        labels = []
        observed = None

        # Order shuffle
        order_data = nulls.get("order_shuffle", {}).get(dim_key, {})
        if order_data.get("null_distribution"):
            distributions.append(np.array(order_data["null_distribution"]))
            labels.append("Order\nShuffle")
            observed = order_data.get("observed")

        # Markov order 1
        m1_data = nulls.get("markov", {}).get(dim_key, {})
        if m1_data.get("null_distribution"):
            distributions.append(np.array(m1_data["null_distribution"]))
            labels.append("Markov\nOrder 1")
            if observed is None:
                observed = m1_data.get("observed")

        # Markov order 2
        if nulls_markov2:
            m2_data = nulls_markov2.get("markov", {}).get(dim_key, {})
            if m2_data.get("null_distribution"):
                distributions.append(np.array(m2_data["null_distribution"]))
                labels.append("Markov\nOrder 2")

        if distributions:
            parts = ax.violinplot(
                distributions,
                positions=range(len(distributions)),
                showmeans=True,
                showmedians=True,
            )
            for pc in parts["bodies"]:
                pc.set_facecolor("steelblue")
                pc.set_alpha(0.6)

            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, fontsize=9)

            # Observed line
            if observed is not None:
                ax.axhline(
                    observed,
                    color="red",
                    linewidth=2,
                    linestyle="-",
                    label=f"Observed ({observed:,.1f})",
                )
                ax.legend(fontsize=8)

        ax.set_ylabel("Total Persistence")
        ax.set_title(f"{dim_label} Total Persistence by Null Model")

    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    if save_path:
        _save_figure(fig, save_path, "fig9_markov_memory_depth")
    return fig


# ─────────────────────────────────────────────────────────────────────
# Figure 10: Wasserstein Distance by Social Origin
# ─────────────────────────────────────────────────────────────────────


def plot_wasserstein_heatmap(
    group_results: dict,
    figsize: tuple[float, float] = FIGSIZE_FULL,
    title: str = "Wasserstein Distance by Social Origin",
    save_path: Path | None = None,
) -> Figure:
    """Heatmap of pairwise Wasserstein distances with p-values.

    Args:
        group_results: Output of group_comparison.compare_groups()
        figsize: Figure dimensions
        title: Plot title
        save_path: Output directory

    Returns:
        matplotlib Figure
    """
    w_matrix = group_results.get("pairwise_wasserstein", {})
    p_matrix = group_results.get("pairwise_p_values", {})
    groups = sorted(group_results.get("group_sizes", {}).keys())

    if not groups or not w_matrix:
        fig = plt.figure()
        plt.text(
            0.5,
            0.5,
            "No group comparison data available",
            ha="center",
            va="center",
            transform=plt.gca().transAxes,
        )
        return fig

    n = len(groups)
    w_arr = np.zeros((n, n))
    p_arr = np.full((n, n), np.nan)

    for i, g1 in enumerate(groups):
        for j, g2 in enumerate(groups):
            if i == j:
                continue
            # Try both key formats: tuple-style "(g1, g2, H1)" and "g1_vs_g2"
            w_val = 0.0
            p_val = None
            for hk in ["H1", "H0"]:
                tk = f"('{g1}', '{g2}', '{hk}')"
                if tk in w_matrix:
                    w_val = w_matrix[tk]
                    break
                tk2 = f"{g1}_vs_{g2}_{hk}"
                if tk2 in w_matrix:
                    w_val = w_matrix[tk2]
                    break
                # Also try as simple key
                sk = f"{g1}_vs_{g2}"
                if sk in w_matrix:
                    w_val = w_matrix[sk]
                    break
            w_arr[i, j] = w_val

            for hk in ["H1", "H0"]:
                tk = f"('{g1}', '{g2}', '{hk}')"
                if tk in p_matrix:
                    pv = p_matrix[tk]
                    p_val = pv.get("p_value") if isinstance(pv, dict) else pv
                    break
                tk2 = f"{g1}_vs_{g2}_{hk}"
                if tk2 in p_matrix:
                    pv = p_matrix[tk2]
                    p_val = pv.get("p_value") if isinstance(pv, dict) else pv
                    break
            if p_val is not None:
                p_arr[i, j] = p_val

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(w_arr, cmap="YlOrRd")

    ax.set_xticks(range(n))
    ax.set_xticklabels(groups, rotation=45, ha="right")
    ax.set_yticks(range(n))
    ax.set_yticklabels(groups)

    # Annotate with values and p-values
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            w = w_arr[i, j]
            p = p_arr[i, j]
            text = f"{w:.2f}"
            if not np.isnan(p) and p < 0.05:
                text += "\n★"
            ax.text(j, i, text, ha="center", va="center", fontsize=7)

    fig.colorbar(im, ax=ax, label="Wasserstein Distance", shrink=0.7)
    ax.set_title(title)

    fig.tight_layout()
    if save_path:
        _save_figure(fig, save_path, "fig10_wasserstein_heatmap")
    return fig


# ─────────────────────────────────────────────────────────────────────
# Figure 11: Gender Persistence Landscape Overlay
# ─────────────────────────────────────────────────────────────────────


def plot_landscape_comparison(
    landscape_data: dict,
    group_a: str = "Male",
    group_b: str = "Female",
    figsize: tuple[float, float] = FIGSIZE_FULL,
    title: str = "Persistence Landscape: Gender Comparison",
    save_path: Path | None = None,
) -> Figure:
    """L₁ landscapes for two groups on same axes with difference shading.

    Args:
        landscape_data: Dict with {group: {"t_values": [...], "landscapes": [[...], ...]}}
        group_a: First group label
        group_b: Second group label
        figsize: Figure dimensions
        title: Plot title
        save_path: Output directory

    Returns:
        matplotlib Figure
    """
    fig, ax = plt.subplots(figsize=figsize)

    a_data = landscape_data.get(group_a)
    b_data = landscape_data.get(group_b)

    if a_data is None or b_data is None:
        ax.text(
            0.5,
            0.5,
            f"Missing data for {group_a} or {group_b}",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        return fig

    t_a = np.array(a_data["t_values"])
    l_a = np.array(a_data["landscapes"])[0]  # L₁

    t_b = np.array(b_data["t_values"])
    l_b = np.array(b_data["landscapes"])[0]  # L₁

    ax.plot(t_a, l_a, color="steelblue", linewidth=1.5, label=group_a)
    ax.plot(t_b, l_b, color="coral", linewidth=1.5, label=group_b)

    # Shade difference (interpolate to common grid)
    t_common = np.linspace(
        max(t_a.min(), t_b.min()),
        min(t_a.max(), t_b.max()),
        200,
    )
    l_a_interp = np.interp(t_common, t_a, l_a)
    l_b_interp = np.interp(t_common, t_b, l_b)

    ax.fill_between(
        t_common,
        l_a_interp,
        l_b_interp,
        alpha=0.2,
        color="gray",
        label="Difference",
    )

    ax.set_xlabel("Filtration Parameter")
    ax.set_ylabel("Landscape Value (L₁)")
    ax.set_title(title)
    ax.legend()

    fig.tight_layout()
    if save_path:
        _save_figure(fig, save_path, "fig11_landscape_comparison")
    return fig


# ─────────────────────────────────────────────────────────────────────
# Master: Generate all figures from checkpoint data
# ─────────────────────────────────────────────────────────────────────


def generate_all_figures(
    results_dir: str | Path,
    output_dir: str | Path,
) -> None:
    """Generate all publication figures from pipeline checkpoint data.

    Args:
        results_dir: Path to results/trajectory_tda_integration/
        output_dir: Path to figures/trajectory_tda/
    """
    results_dir = Path(results_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Generating figures from {results_dir} → {output_dir}")

    # Load data
    analysis = _load_json(results_dir / "05_analysis.json")

    diagrams = None
    diagrams_path = results_dir / "03_ph_diagrams.json"
    if diagrams_path.exists():
        diagrams = _load_json(diagrams_path)

    nulls = _load_json(results_dir / "04_nulls.json")

    nulls_markov2 = None
    m2_path = results_dir / "04_nulls_markov2.json"
    if m2_path.exists():
        nulls_markov2 = _load_json(m2_path)

    embeddings = None
    emb_path = results_dir / "embeddings.npy"
    if emb_path.exists():
        embeddings = np.load(emb_path)

    # Figure 1: Trajectory heatmap
    logger.info("Figure 1: Trajectory heatmap")
    plot_trajectory_heatmap(analysis, save_path=output_dir)

    # Figure 2: Embedding cloud
    if embeddings is not None and "gmm_labels" in analysis:
        logger.info("Figure 2: Embedding cloud")
        labels = np.array(analysis["gmm_labels"])
        plot_embedding_cloud(embeddings, labels, save_path=output_dir)

    # Figure 3: Persistence diagrams
    if diagrams:
        logger.info("Figure 3: Persistence diagrams")
        plot_persistence_diagrams(diagrams, save_path=output_dir)

    # Figure 4: Betti vs null
    logger.info("Figure 4: Betti null comparison")
    plot_betti_null_comparison(nulls, save_path=output_dir)

    # Figure 5: Regime profiles
    logger.info("Figure 5: Regime profiles")
    plot_regime_profiles(analysis, save_path=output_dir)

    # Figure 6: Stability-income
    logger.info("Figure 6: Stability–income correlation")
    plot_stability_income(analysis, save_path=output_dir)

    # Figure 7: Cycle analysis
    logger.info("Figure 7: Cycle analysis")
    plot_cycle_analysis(analysis, diagrams=diagrams, save_path=output_dir)

    # Figure 8: Null table
    logger.info("Figure 8: Null model table")
    plot_null_table(nulls, nulls_markov2, save_path=output_dir)

    # Figure 9: Markov memory depth
    logger.info("Figure 9: Markov memory depth")
    plot_markov_memory_depth(nulls, nulls_markov2, save_path=output_dir)

    logger.info("Figures 10–11 require stratified group comparison data (Phase 3)")

    # Load stratified data if available
    stratified_path = results_dir / "06_stratified.json"
    if stratified_path.exists():
        stratified = _load_json(stratified_path)

        # Figure 10: Wasserstein heatmap (use parental NS-SEC if available, else gender)
        strat_key = None
        for candidate in ["parental_nssec", "gender", "cohort"]:
            if candidate in stratified:
                strat_key = candidate
                break

        if strat_key:
            logger.info(f"Figure 10: Wasserstein heatmap ({strat_key})")
            plot_wasserstein_heatmap(stratified[strat_key], save_path=output_dir)

        # Figure 11: Gender landscape overlay
        if "gender_landscapes" in stratified:
            logger.info("Figure 11: Gender landscape comparison")
            # Restructure for plot function: needs {group: {t_values, landscapes}}
            gl = stratified["gender_landscapes"]
            landscape_data = {}
            for key_prefix, group_name in [
                ("Male_H1", "Male"),
                ("Female_H1", "Female"),
            ]:
                if key_prefix in gl:
                    landscape_data[group_name] = gl[key_prefix]
            if len(landscape_data) == 2:
                plot_landscape_comparison(landscape_data, save_path=output_dir)
    else:
        logger.info(
            "No stratified data found — run run_stratified.py first for Figures 10–11"
        )

    logger.info(f"All available figures saved to {output_dir}")


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s"
    )

    parser = argparse.ArgumentParser(description="Generate publication figures")
    parser.add_argument(
        "--results-dir", type=str, default="results/trajectory_tda_integration"
    )
    parser.add_argument("--output-dir", type=str, default="figures/trajectory_tda")
    args = parser.parse_args()

    generate_all_figures(args.results_dir, args.output_dir)
