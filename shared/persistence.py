"""Core persistence diagram utilities for TDA.

This module provides common interfaces for working with persistence diagrams,
including validation, merging, filtering, and normalization operations.
These utilities are shared across financial and poverty TDA analysis modules.
"""

from __future__ import annotations

from typing import NamedTuple, TypeAlias

import numpy as np
from numpy.typing import NDArray

# Type alias for persistence diagrams: array of shape (n, 2) or (n, 3)
# Each row contains (birth, death) or (birth, death, dimension)
PersistenceDiagram: TypeAlias = NDArray[np.float64]


class PersistencePair(NamedTuple):
    """A single persistence pair representing a topological feature.

    Attributes:
        birth: Scale at which the topological feature appears.
        death: Scale at which the topological feature disappears.
        dimension: Homological dimension (0 for components, 1 for loops, etc.).
    """

    birth: float
    death: float
    dimension: int


def validate_diagram(diagram: PersistenceDiagram) -> bool:
    """Check if a persistence diagram is valid.

    Validates that the diagram has the correct shape and satisfies
    mathematical constraints (birth <= death for all features).

    Args:
        diagram: Persistence diagram as array of shape (n, 2) or (n, 3),
            where each row contains (birth, death) or (birth, death, dimension).

    Returns:
        True if diagram is valid, False otherwise.

    Raises:
        NotImplementedError: This is a stub interface to be implemented later.

    Examples:
        >>> import numpy as np
        >>> diagram = np.array([[0.0, 1.0], [0.5, 2.0]])
        >>> validate_diagram(diagram)
        True

    Notes:
        Valid persistence diagrams must satisfy:
        - Shape is (n, 2) or (n, 3)
        - birth[i] <= death[i] for all features i
        - All values are finite (no NaN or Inf)
    """
    raise NotImplementedError("validate_diagram will be implemented in later phases")


def merge_diagrams(diagrams: list[PersistenceDiagram]) -> PersistenceDiagram:
    """Combine multiple persistence diagrams into a single diagram.

    Concatenates persistence diagrams, useful for aggregating TDA results
    from multiple samples or time windows.

    Args:
        diagrams: List of persistence diagrams to merge. All diagrams must
            have the same number of columns (either 2 or 3).

    Returns:
        Merged persistence diagram containing all features from input diagrams.

    Raises:
        ValueError: If diagrams have inconsistent shapes.
        NotImplementedError: This is a stub interface to be implemented later.

    Examples:
        >>> import numpy as np
        >>> d1 = np.array([[0.0, 1.0], [0.5, 2.0]])
        >>> d2 = np.array([[1.0, 3.0]])
        >>> merged = merge_diagrams([d1, d2])
        >>> merged.shape
        (3, 2)

    Notes:
        The merge operation does not deduplicate or filter features.
        If dimension information is present, it is preserved.
    """
    raise NotImplementedError("merge_diagrams will be implemented in later phases")


def filter_by_dimension(diagram: PersistenceDiagram, dim: int) -> PersistenceDiagram:
    """Extract features of a specific homological dimension.

    Filters a persistence diagram to retain only features from the specified
    dimension (0 for connected components, 1 for loops, 2 for voids, etc.).

    Args:
        diagram: Persistence diagram with shape (n, 3), where the third
            column contains dimension information.
        dim: Homological dimension to extract (0, 1, 2, etc.).

    Returns:
        Filtered persistence diagram containing only features with the
        specified dimension. Returns array of shape (m, 3) where m <= n.

    Raises:
        ValueError: If diagram does not have dimension information (shape != (n, 3)).
        NotImplementedError: This is a stub interface to be implemented later.

    Examples:
        >>> import numpy as np
        >>> diagram = np.array([[0.0, 1.0, 0], [0.5, 2.0, 1], [1.0, 3.0, 0]])
        >>> h0_features = filter_by_dimension(diagram, dim=0)
        >>> h0_features.shape[0]  # Two H0 features
        2

    Notes:
        This function requires dimension information in the third column.
        For diagrams without dimension info, use other filtering methods.
    """
    raise NotImplementedError("filter_by_dimension will be implemented in later phases")


def compute_lifetimes(diagram: PersistenceDiagram) -> NDArray[np.float64]:
    """Calculate persistence (lifetime) for each feature.

    Computes death - birth for each topological feature, which represents
    the persistence or lifetime of that feature across filtration scales.

    Args:
        diagram: Persistence diagram as array of shape (n, 2) or (n, 3).
            First two columns must be (birth, death).

    Returns:
        Array of shape (n,) containing persistence values for each feature.

    Raises:
        ValueError: If diagram has invalid shape.
        NotImplementedError: This is a stub interface to be implemented later.

    Examples:
        >>> import numpy as np
        >>> diagram = np.array([[0.0, 1.0], [0.5, 2.0], [1.0, 1.5]])
        >>> lifetimes = compute_lifetimes(diagram)
        >>> lifetimes
        array([1. , 1.5, 0.5])

    Notes:
        Longer persistence values indicate more significant topological
        features that are less likely to be noise. Features with very short
        lifetimes (near the diagonal birth ≈ death) are often filtered out.

        Time complexity: O(n) where n is the number of features.
    """
    raise NotImplementedError("compute_lifetimes will be implemented in later phases")


def normalize_diagram(diagram: PersistenceDiagram) -> PersistenceDiagram:
    """Scale persistence diagram to [0, 1] range.

    Normalizes both birth and death values to the unit interval, preserving
    the relative structure of the persistence diagram. Useful for comparing
    diagrams from different scales or for ML feature extraction.

    Args:
        diagram: Persistence diagram as array of shape (n, 2) or (n, 3).

    Returns:
        Normalized persistence diagram with same shape as input, where all
        birth and death values are scaled to [0, 1].

    Raises:
        ValueError: If diagram is empty or all values are identical.
        NotImplementedError: This is a stub interface to be implemented later.

    Examples:
        >>> import numpy as np
        >>> diagram = np.array([[0.0, 2.0], [1.0, 4.0]])
        >>> normalized = normalize_diagram(diagram)
        >>> normalized.min(), normalized.max()
        (0.0, 1.0)

    Notes:
        Normalization uses min-max scaling: x' = (x - min) / (max - min).
        The transformation is applied to both birth and death columns.
        Dimension information (if present) is preserved unchanged.

        This operation changes absolute scale but preserves topological
        structure and relative persistence values.
    """
    raise NotImplementedError("normalize_diagram will be implemented in later phases")
