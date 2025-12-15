"""
TTK-enhanced visualization utilities for poverty TDA.

This module provides TTK-based visualization functions specifically
designed for poverty landscape analysis, including:

- Topological simplification comparison
- Critical point persistence visualization
- Geographic overlays for spatial analysis

Examples:
    >>> from poverty_tda.viz.ttk_plots import (
    ...     plot_simplification_comparison,
    ...     plot_critical_point_persistence
    ... )
    >>> from poverty_tda.topology import compute_morse_smale, simplify_scalar_field
    >>>
    >>> # Compute Morse-Smale with simplification
    >>> result = compute_morse_smale(
    ...     "mobility.vti",
    ...     simplify_first=True,
    ...     simplification_threshold=0.10
    ... )
    >>>
    >>> # Visualize simplification impact
    >>> fig = plot_simplification_comparison(
    ...     "mobility.vti",
    ...     result,
    ...     simplification_threshold=0.10
    ... )

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# Try to import pyvista for VTK visualization
try:
    import pyvista as pv

    HAS_PYVISTA = True
except ImportError:
    HAS_PYVISTA = False
    logger.warning("PyVista not available - VTK visualization limited")


def plot_simplification_comparison(
    original_vti_path: str | Path,
    morse_smale_result: Any,
    simplification_threshold: float | None = None,
    figsize: tuple[float, float] = (16, 7),
    title: str | None = None,
    save_path: str | Path | None = None,
    scalar_name: str = "mobility",
) -> Figure:
    """
    Compare original vs simplified scalar field with critical points overlay.

    Creates side-by-side visualization showing the impact of topological
    simplification on the mobility surface and critical point detection.

    Args:
        original_vti_path: Path to original VTI file.
        morse_smale_result: MorseSmaleResult from compute_morse_smale().
        simplification_threshold: Threshold used for simplification (for display).
        figsize: Figure size in inches (width, height).
        title: Optional plot title.
        save_path: Optional path to save figure.
        scalar_name: Name of scalar field in VTI file.

    Returns:
        matplotlib Figure object.

    Examples:
        >>> from poverty_tda.topology import compute_morse_smale
        >>>
        >>> # Compute with simplification
        >>> result = compute_morse_smale(
        ...     "mobility.vti",
        ...     simplify_first=True,
        ...     simplification_threshold=0.10
        ... )
        >>>
        >>> # Visualize impact
        >>> fig = plot_simplification_comparison(
        ...     "mobility.vti",
        ...     result,
        ...     simplification_threshold=0.10
        ... )

    Notes:
        Requires PyVista for VTK file loading. Falls back to placeholder
        visualization if PyVista unavailable.
    """
    if not HAS_PYVISTA:
        logger.warning("PyVista not available - creating placeholder visualization")
        fig, axes = plt.subplots(1, 2, figsize=figsize)
        for ax in axes:
            ax.text(0.5, 0.5, "PyVista Required", ha="center", va="center")
            ax.axis("off")
        return fig

    # Load original VTI
    original_vti_path = Path(original_vti_path)
    if not original_vti_path.exists():
        raise FileNotFoundError(f"VTI file not found: {original_vti_path}")

    mesh = pv.read(original_vti_path)

    # Extract scalar field
    if scalar_name not in mesh.array_names:
        available = ", ".join(mesh.array_names)
        raise ValueError(f"Scalar '{scalar_name}' not found. Available: {available}")


    # Create figure
    fig = plt.figure(figsize=figsize)
    gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)

    # Original scalar field (top left)
    ax1 = fig.add_subplot(gs[0, 0])
    _plot_scalar_slice(ax1, mesh, scalar_name, title="Original Scalar Field")

    # Simplified scalar field (top right)
    ax2 = fig.add_subplot(gs[0, 1])
    if hasattr(morse_smale_result, "simplified_data") and morse_smale_result.simplified_data is not None:
        simplified_mesh = pv.read(morse_smale_result.simplified_data)
        _plot_scalar_slice(ax2, simplified_mesh, scalar_name, title="Simplified Scalar Field")
    else:
        # Use original if no simplified version available
        _plot_scalar_slice(ax2, mesh, scalar_name, title="No Simplification Applied")

    # Critical points before/after (bottom row)
    ax3 = fig.add_subplot(gs[1, :])
    _plot_critical_points_comparison(ax3, mesh, morse_smale_result, scalar_name, simplification_threshold)

    # Overall title
    if title is None:
        threshold_str = f"{simplification_threshold:.1%}" if simplification_threshold else "N/A"
        title = f"Topological Simplification Impact (Threshold: {threshold_str})"

    fig.suptitle(title, fontsize=14, fontweight="bold")

    # Save if requested
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        logger.info(f"Saved simplification comparison to {save_path}")

    return fig


def plot_critical_point_persistence(
    critical_points: list,
    figsize: tuple[float, float] = (12, 8),
    title: str = "Critical Point Persistence",
    save_path: str | Path | None = None,
    color_by_type: bool = True,
    geographic_overlay: bool = False,
    bounds: tuple[float, float, float, float] | None = None,
) -> Figure:
    """
    Plot persistence diagram for critical points with type-based coloring.

    Creates persistence diagram (birth-death plot) with critical points
    color-coded by type (minima, maxima, saddles). Optionally overlays
    geographic positions.

    Args:
        critical_points: List of CriticalPoint objects from Morse-Smale complex.
        figsize: Figure size in inches (width, height).
        title: Plot title.
        save_path: Optional path to save figure.
        color_by_type: If True, color points by type (min/max/saddle).
        geographic_overlay: If True, add geographic position subplot.
        bounds: Geographic bounds (xmin, xmax, ymin, ymax) for overlay.

    Returns:
        matplotlib Figure object.

    Examples:
        >>> from poverty_tda.topology import compute_morse_smale
        >>>
        >>> result = compute_morse_smale("mobility.vti", persistence_threshold=0.05)
        >>>
        >>> # Plot persistence diagram
        >>> fig = plot_critical_point_persistence(
        ...     result.critical_points,
        ...     color_by_type=True,
        ...     geographic_overlay=True
        ... )

    Notes:
        Critical point types (2D surfaces):
        - Type 0: Minima (poverty traps)
        - Type 1: Saddles (transition points)
        - Type 2: Maxima (opportunity peaks)
    """
    if not critical_points:
        raise ValueError("No critical points provided")

    # Extract data from critical points
    values = np.array([cp.value for cp in critical_points])
    persistence_vals = np.array([cp.persistence for cp in critical_points])
    types = np.array([cp.point_type for cp in critical_points])
    positions = np.array([cp.position for cp in critical_points])

    # Calculate birth/death for persistence diagram
    births = values
    deaths = values + persistence_vals

    # Define colors by type
    type_colors = {0: "blue", 1: "green", 2: "red"}
    type_labels = {0: "Minima (Traps)", 1: "Saddles", 2: "Maxima (Peaks)"}

    # Create figure
    if geographic_overlay and bounds is not None:
        fig = plt.figure(figsize=figsize)
        gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3, height_ratios=[2, 1])
        ax_persist = fig.add_subplot(gs[0, :])
        ax_geo = fig.add_subplot(gs[1, :])
    else:
        fig, ax_persist = plt.subplots(figsize=figsize)
        ax_geo = None

    # Plot persistence diagram
    for point_type in np.unique(types):
        mask = types == point_type
        color = type_colors.get(point_type, "gray")
        label = type_labels.get(point_type, f"Type {point_type}")

        ax_persist.scatter(
            births[mask],
            deaths[mask],
            c=color,
            label=label,
            s=100,
            alpha=0.7,
            edgecolors="black",
            linewidths=0.5,
        )

    # Add diagonal line (birth = death)
    diag_min = min(births.min(), deaths.min())
    diag_max = max(births.max(), deaths.max())
    ax_persist.plot(
        [diag_min, diag_max],
        [diag_min, diag_max],
        "k--",
        alpha=0.3,
        label="Birth = Death",
    )

    ax_persist.set_xlabel("Birth (Scalar Value)", fontsize=12)
    ax_persist.set_ylabel("Death (Scalar Value)", fontsize=12)
    ax_persist.set_title("Persistence Diagram", fontsize=13, fontweight="bold")
    ax_persist.legend(fontsize=10, loc="upper left")
    ax_persist.grid(True, alpha=0.3)

    # Geographic overlay if requested
    if geographic_overlay and ax_geo is not None:
        for point_type in np.unique(types):
            mask = types == point_type
            color = type_colors.get(point_type, "gray")
            label = type_labels.get(point_type, f"Type {point_type}")

            ax_geo.scatter(
                positions[mask, 0],
                positions[mask, 1],
                c=color,
                label=label,
                s=100,
                alpha=0.7,
                edgecolors="black",
                linewidths=0.5,
            )

        ax_geo.set_xlabel("Longitude", fontsize=11)
        ax_geo.set_ylabel("Latitude", fontsize=11)
        ax_geo.set_title("Geographic Distribution of Critical Points", fontsize=12, fontweight="bold")
        ax_geo.legend(fontsize=9)
        ax_geo.grid(True, alpha=0.3)

        if bounds:
            ax_geo.set_xlim(bounds[0], bounds[1])
            ax_geo.set_ylim(bounds[2], bounds[3])

    # Overall title
    fig.suptitle(title, fontsize=14, fontweight="bold", y=0.98)

    # Save if requested
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        logger.info(f"Saved persistence diagram to {save_path}")

    return fig


def _plot_scalar_slice(ax: plt.Axes, mesh: pv.DataSet, scalar_name: str, title: str = "") -> None:
    """
    Plot 2D slice of scalar field from VTK mesh.

    Helper function for visualizing scalar fields in matplotlib.

    Args:
        ax: Matplotlib axes to plot on.
        mesh: PyVista mesh with scalar data.
        scalar_name: Name of scalar field.
        title: Subplot title.
    """
    # Get scalar data
    scalar_data = mesh[scalar_name]

    # For structured grid, reshape to 2D for plotting
    if hasattr(mesh, "dimensions"):
        dims = mesh.dimensions
        if len(dims) == 3 and dims[2] == 1:
            # 2D data stored as 3D
            scalar_2d = scalar_data.reshape((dims[1], dims[0]))
        else:
            # Take middle slice
            scalar_2d = scalar_data.reshape(dims)[dims[2] // 2, :, :]
    else:
        # Unstructured - use points projection
        points = mesh.points
        scalar_2d = _project_to_2d(points, scalar_data)

    # Plot
    im = ax.imshow(scalar_2d, cmap="viridis", origin="lower", aspect="auto")
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_xlabel("X", fontsize=10)
    ax.set_ylabel("Y", fontsize=10)


def _project_to_2d(points: NDArray, values: NDArray, resolution: int = 100) -> NDArray:
    """
    Project 3D unstructured points to 2D grid.

    Args:
        points: Point coordinates (n, 3).
        values: Scalar values at points (n,).
        resolution: Grid resolution.

    Returns:
        2D array of interpolated values.
    """
    from scipy.interpolate import griddata

    # Use X, Y coordinates
    x = points[:, 0]
    y = points[:, 1]

    # Create grid
    xi = np.linspace(x.min(), x.max(), resolution)
    yi = np.linspace(y.min(), y.max(), resolution)
    xi_grid, yi_grid = np.meshgrid(xi, yi)

    # Interpolate
    zi = griddata((x, y), values, (xi_grid, yi_grid), method="linear")

    return zi


def _plot_critical_points_comparison(
    ax: plt.Axes,
    mesh: pv.DataSet,
    morse_smale_result: Any,
    scalar_name: str,
    threshold: float | None,
) -> None:
    """
    Plot critical points with persistence filtering comparison.

    Helper function showing critical points before/after persistence filtering.

    Args:
        ax: Matplotlib axes to plot on.
        mesh: Original VTK mesh.
        morse_smale_result: Morse-Smale computation result.
        scalar_name: Name of scalar field.
        threshold: Persistence threshold used.
    """
    critical_points = morse_smale_result.critical_points

    if not critical_points:
        ax.text(
            0.5,
            0.5,
            "No critical points found",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.axis("off")
        return

    # Extract positions and types
    positions = np.array([cp.position for cp in critical_points])
    types = np.array([cp.point_type for cp in critical_points])

    # Type colors
    type_colors = {0: "blue", 1: "green", 2: "red"}
    type_labels = {0: "Minima", 1: "Saddles", 2: "Maxima"}

    # Plot critical points
    for point_type in np.unique(types):
        mask = types == point_type
        color = type_colors.get(point_type, "gray")
        label = type_labels.get(point_type, f"Type {point_type}")

        ax.scatter(
            positions[mask, 0],
            positions[mask, 1],
            c=color,
            label=label,
            s=80,
            alpha=0.7,
            edgecolors="black",
            linewidths=0.5,
        )

    # Add persistence info
    if threshold is not None:
        n_filtered = len(critical_points)
        ax.text(
            0.02,
            0.98,
            f"Threshold: {threshold:.1%}\nCritical Points: {n_filtered}",
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
        )

    ax.set_xlabel("X Coordinate", fontsize=10)
    ax.set_ylabel("Y Coordinate", fontsize=10)
    ax.set_title("Critical Points Distribution", fontsize=11, fontweight="bold")
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, alpha=0.3)
