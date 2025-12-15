"""
TTK-enhanced plotting utilities for persistence diagrams and curves.

Provides matplotlib-based visualization functions that integrate with
TTK-computed persistence curves and distance metrics.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from numpy.typing import NDArray

from shared.ttk_visualization.persistence_curves import PersistenceCurveData

logger = logging.getLogger(__name__)


def plot_persistence_curve(
    curve_data: PersistenceCurveData,
    curve_type: str = "persistence",
    figsize: tuple[float, float] = (10, 6),
    title: str | None = None,
    save_path: str | Path | None = None,
    **kwargs: Any,
) -> Figure:
    """
    Plot persistence curves for multiple datasets.

    Args:
        curve_data: PersistenceCurveData object from create_persistence_curve().
        curve_type: Type of curve to plot ("birth", "death", or "persistence").
        figsize: Figure size in inches (width, height).
        title: Optional plot title. Auto-generated if None.
        save_path: Optional path to save figure.
        **kwargs: Additional keyword arguments passed to plt.plot().

    Returns:
        matplotlib Figure object.

    Examples:
        >>> from shared.ttk_visualization import create_persistence_curve
        >>> curves = create_persistence_curve([diagram1, diagram2],
        ...                                    labels=['Crisis', 'Normal'])
        >>> fig = plot_persistence_curve(curves, curve_type='persistence')
        >>> plt.show()
    """
    # Select curves based on type
    if curve_type == "birth":
        curves = curve_data.birth_curves
        xlabel = "Birth Time"
    elif curve_type == "death":
        curves = curve_data.death_curves
        xlabel = "Death Time"
    elif curve_type == "persistence":
        curves = curve_data.persistence_curves
        xlabel = "Persistence Value"
    else:
        raise ValueError(f"Invalid curve_type: {curve_type}. Must be 'birth', 'death', or 'persistence'")

    if not curves:
        raise ValueError(f"No {curve_type} curves found in curve_data")

    # Create figure
    fig, ax = plt.subplots(figsize=figsize)

    # Plot each curve
    for i, (label, curve) in enumerate(zip(curve_data.labels, curves)):
        x = curve[:, 0]
        y = curve[:, 1]

        ax.plot(x, y, label=f"{label} (n={curve_data.n_features[i]})", linewidth=2, **kwargs)

    # Formatting
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel("Cumulative Fraction", fontsize=12)
    ax.set_ylim([0, 1.05])
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    if title is None:
        dims_str = ", ".join(f"H{d}" for d in curve_data.dimensions)
        title = f"{curve_type.capitalize()} Time Distribution ({dims_str})"

    ax.set_title(title, fontsize=14, fontweight="bold")

    plt.tight_layout()

    # Save if requested
    if save_path:
        save_path = Path(save_path)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        logger.info(f"Saved figure to {save_path}")

    return fig


def plot_persistence_comparison(
    curve_data: PersistenceCurveData,
    figsize: tuple[float, float] = (15, 5),
    title: str | None = None,
    save_path: str | Path | None = None,
) -> Figure:
    """
    Create side-by-side comparison of birth, death, and persistence curves.

    Args:
        curve_data: PersistenceCurveData object from create_persistence_curve().
        figsize: Figure size in inches (width, height).
        title: Optional overall plot title.
        save_path: Optional path to save figure.

    Returns:
        matplotlib Figure object.

    Examples:
        >>> curves = create_persistence_curve([crisis_diag, normal_diag],
        ...                                    labels=['Crisis', 'Normal'])
        >>> fig = plot_persistence_comparison(curves)
        >>> plt.show()
    """
    # Create subplots
    fig, axes = plt.subplots(1, 3, figsize=figsize)

    # Birth curves
    if curve_data.birth_curves:
        ax = axes[0]
        for i, (label, curve) in enumerate(zip(curve_data.labels, curve_data.birth_curves)):
            x = curve[:, 0]
            y = curve[:, 1]
            ax.plot(x, y, label=label, linewidth=2)

        ax.set_xlabel("Birth Time", fontsize=11)
        ax.set_ylabel("Cumulative Fraction", fontsize=11)
        ax.set_ylim([0, 1.05])
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)
        ax.set_title("Birth Time Distribution", fontsize=12, fontweight="bold")

    # Death curves
    if curve_data.death_curves:
        ax = axes[1]
        for i, (label, curve) in enumerate(zip(curve_data.labels, curve_data.death_curves)):
            x = curve[:, 0]
            y = curve[:, 1]
            ax.plot(x, y, label=label, linewidth=2)

        ax.set_xlabel("Death Time", fontsize=11)
        ax.set_ylabel("Cumulative Fraction", fontsize=11)
        ax.set_ylim([0, 1.05])
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)
        ax.set_title("Death Time Distribution", fontsize=12, fontweight="bold")

    # Persistence curves
    if curve_data.persistence_curves:
        ax = axes[2]
        for i, (label, curve) in enumerate(zip(curve_data.labels, curve_data.persistence_curves)):
            x = curve[:, 0]
            y = curve[:, 1]
            ax.plot(x, y, label=label, linewidth=2)

        ax.set_xlabel("Persistence Value", fontsize=11)
        ax.set_ylabel("Cumulative Fraction", fontsize=11)
        ax.set_ylim([0, 1.05])
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)
        ax.set_title("Persistence Distribution", fontsize=12, fontweight="bold")

    # Overall title
    if title:
        fig.suptitle(title, fontsize=14, fontweight="bold", y=1.02)

    plt.tight_layout()

    # Save if requested
    if save_path:
        save_path = Path(save_path)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        logger.info(f"Saved figure to {save_path}")

    return fig


def plot_distance_heatmap(
    distance_matrix: NDArray[np.floating],
    labels: list[str],
    metric: str = "Bottleneck",
    figsize: tuple[float, float] = (8, 7),
    title: str | None = None,
    save_path: str | Path | None = None,
    cmap: str = "YlOrRd",
) -> Figure:
    """
    Plot heatmap of pairwise persistence diagram distances.

    Args:
        distance_matrix: Symmetric matrix of pairwise distances.
        labels: Row/column labels for the matrix.
        metric: Name of distance metric (e.g., "Bottleneck", "Wasserstein").
        figsize: Figure size in inches (width, height).
        title: Optional plot title.
        save_path: Optional path to save figure.
        cmap: Matplotlib colormap name.

    Returns:
        matplotlib Figure object.

    Examples:
        >>> from financial_tda.topology import compute_bottleneck_distance
        >>> # Compute pairwise distances
        >>> diagrams = [diag_2008, diag_2015, diag_2020]
        >>> n = len(diagrams)
        >>> distances = np.zeros((n, n))
        >>> for i in range(n):
        ...     for j in range(n):
        ...         distances[i, j] = compute_bottleneck_distance(diagrams[i], diagrams[j])
        >>> # Plot heatmap
        >>> fig = plot_distance_heatmap(distances, ['2008', '2015', '2020'])
        >>> plt.show()
    """
    distance_matrix = np.asarray(distance_matrix, dtype=np.float64)

    if distance_matrix.shape[0] != distance_matrix.shape[1]:
        raise ValueError(f"distance_matrix must be square, got shape {distance_matrix.shape}")

    if len(labels) != distance_matrix.shape[0]:
        raise ValueError(f"Number of labels ({len(labels)}) must match matrix size ({distance_matrix.shape[0]})")

    # Create figure
    fig, ax = plt.subplots(figsize=figsize)

    # Plot heatmap
    im = ax.imshow(distance_matrix, cmap=cmap, aspect="auto")

    # Set ticks and labels
    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label(f"{metric} Distance", fontsize=11)

    # Annotate cells with values
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(
                j,
                i,
                f"{distance_matrix[i, j]:.3f}",
                ha="center",
                va="center",
                color="black",
                fontsize=9,
            )

    # Title
    if title is None:
        title = f"Pairwise {metric} Distances"

    ax.set_title(title, fontsize=14, fontweight="bold")

    plt.tight_layout()

    # Save if requested
    if save_path:
        save_path = Path(save_path)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        logger.info(f"Saved figure to {save_path}")

    return fig
