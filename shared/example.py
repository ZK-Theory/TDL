"""Utilities for working with persistence diagrams in TDA.

This module demonstrates documentation standards and provides simple utilities
for handling persistence diagrams, which are fundamental structures in
Topological Data Analysis.

A persistence diagram is a multiset of points in the plane, where each point
(birth, death) represents a topological feature that appears at scale 'birth'
and disappears at scale 'death'.
"""

from __future__ import annotations

from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

# Type alias for persistence diagrams: array of shape (n, 2)
# Each row is (birth, death) for a topological feature
PersistenceDiagram: TypeAlias = NDArray[np.float64]


def filter_by_lifetime(
    diagram: PersistenceDiagram, min_lifetime: float
) -> PersistenceDiagram:
    """Filter persistence diagram by minimum feature lifetime.

    Removes topological features with persistence (death - birth) less than
    the specified threshold. This is useful for filtering noise in TDA analysis.

    Args:
        diagram: Persistence diagram as array of shape (n, 2), where each row
            contains (birth, death) values for a topological feature.
        min_lifetime: Minimum persistence threshold. Features with
            death - birth < min_lifetime will be removed.

    Returns:
        Filtered persistence diagram with the same structure as input,
        containing only features with persistence >= min_lifetime.

    Raises:
        ValueError: If diagram has invalid shape or contains birth > death.
        ValueError: If min_lifetime is negative.

    Examples:
        >>> diagram = np.array([[0.0, 1.0], [0.5, 0.6], [1.0, 3.0]])
        >>> filtered = filter_by_lifetime(diagram, min_lifetime=0.5)
        >>> print(filtered)
        [[0.  1. ]
         [1.  3. ]]

    Notes:
        The persistence (lifetime) of a feature is defined as death - birth.
        Features on or near the diagonal (birth ≈ death) are typically
        considered topological noise.

        Time complexity: O(n) where n is the number of features.

    References:
        - Edelsbrunner, H., & Harer, J. (2010). "Computational Topology:
          An Introduction". American Mathematical Society.
    """
    # Validate inputs
    if diagram.ndim != 2 or diagram.shape[1] != 2:
        raise ValueError(f"Diagram must have shape (n, 2), got {diagram.shape}")

    if min_lifetime < 0:
        raise ValueError(f"min_lifetime must be non-negative, got {min_lifetime}")

    # Check birth <= death for all features
    if np.any(diagram[:, 0] > diagram[:, 1]):
        raise ValueError("Invalid diagram: some features have birth > death")

    # Compute lifetimes and filter
    lifetimes = diagram[:, 1] - diagram[:, 0]
    mask = lifetimes >= min_lifetime

    return diagram[mask]


def compute_lifetimes(diagram: PersistenceDiagram) -> NDArray[np.float64]:
    """Compute persistence (lifetime) for each feature in a diagram.

    Args:
        diagram: Persistence diagram as array of shape (n, 2).

    Returns:
        Array of shape (n,) containing persistence values (death - birth)
        for each feature.

    Raises:
        ValueError: If diagram has invalid shape.

    Examples:
        >>> diagram = np.array([[0.0, 1.0], [0.5, 2.0], [1.0, 1.5]])
        >>> lifetimes = compute_lifetimes(diagram)
        >>> print(lifetimes)
        [1.  1.5 0.5]

    Notes:
        Longer persistence values indicate more significant topological
        features that are less likely to be noise.
    """
    if diagram.ndim != 2 or diagram.shape[1] != 2:
        raise ValueError(f"Diagram must have shape (n, 2), got {diagram.shape}")

    return diagram[:, 1] - diagram[:, 0]


class PersistenceDiagramStats:
    """Statistical summary of a persistence diagram.

    Computes and stores basic statistics about the topological features
    in a persistence diagram, useful for feature engineering and analysis.

    Attributes:
        num_features: Number of topological features in the diagram.
        mean_lifetime: Average persistence across all features.
        max_lifetime: Maximum persistence (most persistent feature).
        total_persistence: Sum of all feature lifetimes.

    Examples:
        >>> diagram = np.array([[0.0, 1.0], [0.5, 2.0], [1.0, 1.5]])
        >>> stats = PersistenceDiagramStats(diagram)
        >>> print(stats.mean_lifetime)
        1.0
        >>> print(stats.max_lifetime)
        1.5
    """

    num_features: int
    mean_lifetime: float
    max_lifetime: float
    total_persistence: float

    def __init__(self, diagram: PersistenceDiagram) -> None:
        """Initialize statistics from a persistence diagram.

        Args:
            diagram: Persistence diagram as array of shape (n, 2).

        Raises:
            ValueError: If diagram has invalid shape or is empty.
        """
        if diagram.ndim != 2 or diagram.shape[1] != 2:
            raise ValueError(f"Diagram must have shape (n, 2), got {diagram.shape}")

        if diagram.shape[0] == 0:
            raise ValueError("Cannot compute statistics for empty diagram")

        lifetimes = compute_lifetimes(diagram)

        self.num_features = len(lifetimes)
        self.mean_lifetime = float(np.mean(lifetimes))
        self.max_lifetime = float(np.max(lifetimes))
        self.total_persistence = float(np.sum(lifetimes))

    def __repr__(self) -> str:
        """Return string representation of statistics."""
        return (
            f"PersistenceDiagramStats("
            f"num_features={self.num_features}, "
            f"mean_lifetime={self.mean_lifetime:.3f}, "
            f"max_lifetime={self.max_lifetime:.3f})"
        )


if __name__ == "__main__":
    # Example usage demonstrating the module functionality
    print("=== Persistence Diagram Utilities Demo ===\n")

    # Create a sample persistence diagram
    # Features: (birth, death) pairs
    diagram = np.array(
        [
            [0.0, 1.0],  # Persistence: 1.0
            [0.5, 0.6],  # Persistence: 0.1 (noise)
            [1.0, 3.0],  # Persistence: 2.0 (significant)
            [1.5, 1.8],  # Persistence: 0.3 (weak)
        ]
    )

    print("Original persistence diagram:")
    print(diagram)
    print()

    # Compute lifetimes
    lifetimes = compute_lifetimes(diagram)
    print("Feature lifetimes:")
    print(lifetimes)
    print()

    # Filter by minimum lifetime
    filtered = filter_by_lifetime(diagram, min_lifetime=0.5)
    print("Filtered diagram (min_lifetime=0.5):")
    print(filtered)
    print()

    # Compute statistics
    stats = PersistenceDiagramStats(diagram)
    print("Diagram statistics:")
    print(stats)
    print(f"  Total persistence: {stats.total_persistence:.3f}")
    print()

    # Statistics for filtered diagram
    stats_filtered = PersistenceDiagramStats(filtered)
    print("Filtered diagram statistics:")
    print(stats_filtered)
