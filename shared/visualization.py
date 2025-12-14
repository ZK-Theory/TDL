"""Visualization utilities for persistence diagrams and TDA results.

This module provides common plotting interfaces for visualizing topological
features, including persistence diagrams, barcodes, and Betti curves.
These utilities produce matplotlib figures for analysis and reporting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from matplotlib.axes import Axes

from shared.persistence import PersistenceDiagram


def plot_persistence_diagram(
    diagram: PersistenceDiagram,
    ax: Axes | None = None,
    **kwargs,
) -> Axes:
    """Create a standard persistence diagram plot.

    Plots topological features as points in the (birth, death) plane,
    with the diagonal line representing features with zero persistence.
    Different colors can represent different homological dimensions.

    Args:
        diagram: Persistence diagram as array of shape (n, 2) or (n, 3).
        ax: Matplotlib axes object to plot on. If None, creates new figure.
        **kwargs: Additional keyword arguments passed to matplotlib scatter plot.
            Common options: color, alpha, s (size), marker, label.

    Returns:
        Matplotlib axes object containing the plot.

    Raises:
        NotImplementedError: This is a stub interface to be implemented later.

    Examples:
        >>> import numpy as np
        >>> import matplotlib.pyplot as plt
        >>> diagram = np.array([[0.0, 1.0], [0.5, 2.0], [1.0, 3.0]])
        >>> ax = plot_persistence_diagram(diagram, alpha=0.7)
        >>> plt.show()

    Notes:
        The plot includes:
        - Points at (birth, death) coordinates for each feature
        - Diagonal line y = x (features with zero persistence)
        - Axes labels and title
        - Legend if multiple dimensions are present

        Points above the diagonal represent topological features, while
        the distance from the diagonal indicates feature persistence.
    """
    raise NotImplementedError(
        "plot_persistence_diagram will be implemented in later phases"
    )


def plot_betti_curve(
    diagram: PersistenceDiagram,
    filtration_values: NDArray[np.float64],
    ax: Axes | None = None,
) -> Axes:
    """Plot Betti number curve over filtration parameter.

    Creates a curve showing how Betti numbers (counts of topological features)
    change as the filtration parameter increases. Useful for understanding
    topological structure evolution.

    Args:
        diagram: Persistence diagram as array of shape (n, 2) or (n, 3).
        filtration_values: Array of filtration parameter values at which
            to compute Betti numbers. Should be sorted in ascending order.
        ax: Matplotlib axes object to plot on. If None, creates new figure.

    Returns:
        Matplotlib axes object containing the plot.

    Raises:
        ValueError: If filtration_values is not sorted or is empty.
        NotImplementedError: This is a stub interface to be implemented later.

    Examples:
        >>> import numpy as np
        >>> import matplotlib.pyplot as plt
        >>> diagram = np.array([[0.0, 2.0], [0.5, 1.5], [1.0, 3.0]])
        >>> filtration = np.linspace(0, 3, 100)
        >>> ax = plot_betti_curve(diagram, filtration)
        >>> plt.show()

    Notes:
        Betti numbers represent counts of topological features:
        - β₀: number of connected components
        - β₁: number of loops (1-cycles)
        - β₂: number of voids (2-cycles)

        The curve shows how these counts change as the filtration scale
        increases, revealing topological structure at different scales.
    """
    raise NotImplementedError("plot_betti_curve will be implemented in later phases")


def plot_persistence_barcode(
    diagram: PersistenceDiagram,
    ax: Axes | None = None,
) -> Axes:
    """Create a barcode representation of persistence diagram.

    Plots each topological feature as a horizontal bar from birth to death,
    providing an alternative visualization that emphasizes feature lifetimes.

    Args:
        diagram: Persistence diagram as array of shape (n, 2) or (n, 3).
        ax: Matplotlib axes object to plot on. If None, creates new figure.

    Returns:
        Matplotlib axes object containing the plot.

    Raises:
        NotImplementedError: This is a stub interface to be implemented later.

    Examples:
        >>> import numpy as np
        >>> import matplotlib.pyplot as plt
        >>> diagram = np.array([[0.0, 1.0], [0.5, 2.0], [1.0, 3.0]])
        >>> ax = plot_persistence_barcode(diagram)
        >>> plt.show()

    Notes:
        The barcode plot displays:
        - Each feature as a horizontal line segment from birth to death
        - Features sorted by birth time (or by dimension if available)
        - Color coding by dimension if dimension info is present
        - X-axis showing filtration scale
        - Y-axis showing individual features (indexed)

        Longer bars indicate more persistent features. This representation
        is particularly useful for identifying significant topological
        features and comparing feature lifetimes visually.
    """
    raise NotImplementedError(
        "plot_persistence_barcode will be implemented in later phases"
    )
