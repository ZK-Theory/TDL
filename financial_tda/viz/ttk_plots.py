"""
TTK-enhanced visualization utilities for financial TDA.

This module provides TTK-based visualization functions specifically
designed for financial market regime analysis, including:

- Persistence curve comparison between market regimes
- Bottleneck distance matrix visualization for regime clustering
- Integration with shared.ttk_visualization utilities

Examples:
    >>> from financial_tda.viz.ttk_plots import (
    ...     plot_persistence_curve_comparison,
    ...     plot_bottleneck_distance_matrix
    ... )
    >>> from financial_tda.topology import compute_persistence_vr
    >>>
    >>> # Compare crisis vs normal regime
    >>> crisis_diagram = compute_persistence_vr(crisis_embedding)
    >>> normal_diagram = compute_persistence_vr(normal_embedding)
    >>>
    >>> fig = plot_persistence_curve_comparison(
    ...     [crisis_diagram, normal_diagram],
    ...     labels=['Crisis 2008', 'Normal 2007']
    ... )

License: MIT
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from numpy.typing import NDArray
from scipy.cluster import hierarchy
from scipy.spatial.distance import squareform

from shared.ttk_visualization import (
    create_persistence_curve,
    plot_persistence_comparison,
)

logger = logging.getLogger(__name__)


def plot_persistence_curve_comparison(
    diagrams: list[NDArray[np.floating]],
    labels: list[str] | None = None,
    dimensions: list[int] | None = None,
    figsize: tuple[float, float] = (15, 5),
    title: str = "Market Regime Comparison",
    save_path: str | Path | None = None,
    highlight_differences: bool = True,
) -> Figure:
    """
    Compare persistence curves between multiple market regimes.

    Creates side-by-side persistence curve comparison with optional
    statistical annotations highlighting significant differences.

    Args:
        diagrams: List of persistence diagrams from different regimes.
        labels: Optional regime labels (e.g., ['Crisis 2008', 'Normal 2007']).
        dimensions: Homology dimensions to include (default: all).
        figsize: Figure size in inches (width, height).
        title: Overall plot title.
        save_path: Optional path to save figure.
        highlight_differences: If True, annotate significant differences.

    Returns:
        matplotlib Figure object.

    Examples:
        >>> from financial_tda.topology import compute_persistence_vr
        >>> from financial_tda.topology.embedding import takens_embedding
        >>>
        >>> # Create embeddings for different regimes
        >>> crisis_embedding = takens_embedding(crisis_returns, delay=5, dimension=3)
        >>> normal_embedding = takens_embedding(normal_returns, delay=5, dimension=3)
        >>>
        >>> # Compute persistence diagrams
        >>> crisis_diag = compute_persistence_vr(crisis_embedding)
        >>> normal_diag = compute_persistence_vr(normal_embedding)
        >>>
        >>> # Plot comparison
        >>> fig = plot_persistence_curve_comparison(
        ...     [crisis_diag, normal_diag],
        ...     labels=['Crisis 2008', 'Normal 2007'],
        ...     dimensions=[0, 1]
        ... )

    Notes:
        Uses shared.ttk_visualization for curve generation and plotting.
        Statistical annotations compare persistence distributions using
        median and percentile differences.
    """
    # Input validation
    if not diagrams:
        raise ValueError("diagrams list cannot be empty")

    if labels is None:
        labels = [f"Regime {i}" for i in range(len(diagrams))]

    if len(labels) != len(diagrams):
        raise ValueError(f"Number of labels ({len(labels)}) must match number of diagrams ({len(diagrams)})")

    # Generate persistence curves
    curves = create_persistence_curve(diagrams, labels=labels, dimensions=dimensions, curve_type="all")

    # Create comparison plot
    fig = plot_persistence_comparison(curves, figsize=figsize, title=title)

    # Add statistical annotations if requested
    if highlight_differences and len(diagrams) >= 2:
        _add_statistical_annotations(fig, curves)

    # Save if requested
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        logger.info(f"Saved regime comparison to {save_path}")

    return fig


def plot_bottleneck_distance_matrix(
    diagrams: list[NDArray[np.floating]],
    labels: list[str],
    dimension: int | None = None,
    metric: str = "bottleneck",
    figsize: tuple[float, float] = (12, 10),
    title: str | None = None,
    save_path: str | Path | None = None,
    add_dendrogram: bool = True,
) -> Figure:
    """
    Visualize pairwise bottleneck distances between market regimes.

    Creates a heatmap of pairwise persistence diagram distances with
    optional hierarchical clustering dendrogram to identify regime groups.

    Args:
        diagrams: List of persistence diagrams from different regimes.
        labels: Regime labels for matrix rows/columns.
        dimension: Optional homology dimension filter (0, 1, or 2).
        metric: Distance metric ('bottleneck' or 'wasserstein').
        figsize: Figure size in inches (width, height).
        title: Optional plot title.
        save_path: Optional path to save figure.
        add_dendrogram: If True, add hierarchical clustering dendrogram.

    Returns:
        matplotlib Figure object.

    Examples:
        >>> from financial_tda.topology import (
        ...     compute_persistence_vr,
        ...     compute_bottleneck_distance
        ... )
        >>>
        >>> # Compute diagrams for multiple regimes
        >>> diagrams = [diag_2008, diag_2015, diag_2020, diag_2022]
        >>> labels = ['2008 Crisis', '2015 Flash Crash', '2020 COVID', '2022 Inflation']
        >>>
        >>> # Plot distance matrix with clustering
        >>> fig = plot_bottleneck_distance_matrix(
        ...     diagrams, labels, dimension=1, add_dendrogram=True
        ... )

    Notes:
        Uses scipy hierarchical clustering with average linkage.
        Distance computation uses financial_tda.topology distance functions.
    """
    # Input validation
    if not diagrams:
        raise ValueError("diagrams list cannot be empty")

    if len(labels) != len(diagrams):
        raise ValueError(f"Number of labels ({len(labels)}) must match number of diagrams ({len(diagrams)})")

    # Import distance functions
    if metric == "bottleneck":
        from financial_tda.topology.filtration import compute_bottleneck_distance

        distance_func = compute_bottleneck_distance
    elif metric == "wasserstein":
        from financial_tda.topology.filtration import compute_wasserstein_distance

        distance_func = compute_wasserstein_distance
    else:
        raise ValueError(f"Invalid metric: {metric}. Must be 'bottleneck' or 'wasserstein'")

    # Compute pairwise distance matrix
    n = len(diagrams)
    distances = np.zeros((n, n))

    logger.info(f"Computing {n}x{n} {metric} distance matrix...")

    for i in range(n):
        for j in range(i, n):  # Upper triangle only (symmetric)
            if i == j:
                distances[i, j] = 0.0
            else:
                dist = distance_func(diagrams[i], diagrams[j], dimension=dimension)
                distances[i, j] = dist
                distances[j, i] = dist  # Symmetry

    logger.info(f"Distance matrix computed. Range: [{distances.min():.3f}, {distances.max():.3f}]")

    # Create figure with optional dendrogram
    if add_dendrogram and n > 2:
        fig = plt.figure(figsize=figsize)
        gs = fig.add_gridspec(2, 2, width_ratios=[1, 4], height_ratios=[1, 4], hspace=0.05, wspace=0.05)

        # Compute hierarchical clustering
        condensed_dist = squareform(distances)
        linkage_matrix = hierarchy.linkage(condensed_dist, method="average")

        # Dendrogram (top)
        ax_dend_top = fig.add_subplot(gs[0, 1])
        dendro = hierarchy.dendrogram(linkage_matrix, ax=ax_dend_top, no_labels=True)
        ax_dend_top.set_xticks([])
        ax_dend_top.set_yticks([])
        ax_dend_top.spines["top"].set_visible(False)
        ax_dend_top.spines["right"].set_visible(False)
        ax_dend_top.spines["bottom"].set_visible(False)
        ax_dend_top.spines["left"].set_visible(False)

        # Reorder matrix according to dendrogram
        order = dendro["leaves"]
        distances_reordered = distances[order, :][:, order]
        labels_reordered = [labels[i] for i in order]

        # Heatmap
        ax_heatmap = fig.add_subplot(gs[1, 1])
        im = ax_heatmap.imshow(distances_reordered, cmap="YlOrRd", aspect="auto")

        # Labels
        ax_heatmap.set_xticks(np.arange(n))
        ax_heatmap.set_yticks(np.arange(n))
        ax_heatmap.set_xticklabels(labels_reordered, rotation=45, ha="right", fontsize=9)
        ax_heatmap.set_yticklabels(labels_reordered, fontsize=9)

        # Annotate cells
        for i in range(n):
            for j in range(n):
                ax_heatmap.text(
                    j,
                    i,
                    f"{distances_reordered[i, j]:.3f}",
                    ha="center",
                    va="center",
                    color="black",
                    fontsize=8,
                )

        # Colorbar
        cbar = plt.colorbar(im, ax=ax_heatmap, fraction=0.046, pad=0.04)
        cbar.set_label(f"{metric.capitalize()} Distance", fontsize=10)

        # Empty subplot for spacing
        ax_empty = fig.add_subplot(gs[0, 0])
        ax_empty.axis("off")

        ax_corner = fig.add_subplot(gs[1, 0])
        ax_corner.axis("off")

    else:
        # Simple heatmap without dendrogram
        fig, ax_heatmap = plt.subplots(figsize=figsize)

        im = ax_heatmap.imshow(distances, cmap="YlOrRd", aspect="auto")

        ax_heatmap.set_xticks(np.arange(n))
        ax_heatmap.set_yticks(np.arange(n))
        ax_heatmap.set_xticklabels(labels, rotation=45, ha="right", fontsize=10)
        ax_heatmap.set_yticklabels(labels, fontsize=10)

        # Annotate cells
        for i in range(n):
            for j in range(n):
                ax_heatmap.text(
                    j,
                    i,
                    f"{distances[i, j]:.3f}",
                    ha="center",
                    va="center",
                    color="black",
                    fontsize=9,
                )

        # Colorbar
        cbar = plt.colorbar(im, ax=ax_heatmap)
        cbar.set_label(f"{metric.capitalize()} Distance", fontsize=11)

    # Title
    if title is None:
        dim_str = f"H{dimension}" if dimension is not None else "All dims"
        title = f"Market Regime Similarity Matrix ({metric.capitalize()}, {dim_str})"

    fig.suptitle(title, fontsize=14, fontweight="bold", y=0.98)

    # Save if requested
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        logger.info(f"Saved distance matrix to {save_path}")

    return fig


def _add_statistical_annotations(fig: Figure, curves) -> None:
    """
    Add statistical annotations to persistence curve comparison.

    Annotates significant differences between the first two datasets
    (typically crisis vs normal regime).

    Args:
        fig: matplotlib Figure to annotate.
        curves: PersistenceCurveData object.
    """
    if len(curves.persistence_curves) < 2:
        return

    # Extract first two persistence curves
    curve1 = curves.persistence_curves[0]
    curve2 = curves.persistence_curves[1]

    # Compute median persistence
    median1 = curve1[len(curve1) // 2, 0]
    median2 = curve2[len(curve2) // 2, 0]

    # Compute 75th percentile (high persistence features)
    _p75_1 = curve1[int(0.75 * len(curve1)), 0]  # noqa: F841
    _p75_2 = curve2[int(0.75 * len(curve2)), 0]  # noqa: F841

    # Add annotation to persistence subplot (rightmost)
    axes = fig.axes
    if len(axes) >= 3:
        ax = axes[2]  # Persistence subplot

        # Annotation text
        diff_pct = abs(median1 - median2) / max(median1, median2) * 100

        annotation = f"Median difference: {diff_pct:.1f}%\n"
        annotation += f"{curves.labels[0]}: {median1:.3f}\n"
        annotation += f"{curves.labels[1]}: {median2:.3f}"

        # Add text box
        ax.text(
            0.98,
            0.02,
            annotation,
            transform=ax.transAxes,
            fontsize=8,
            verticalalignment="bottom",
            horizontalalignment="right",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
        )

        logger.debug(f"Added statistical annotation: median diff = {diff_pct:.1f}%")
