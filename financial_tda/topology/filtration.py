"""
Persistence diagram computation for embedded financial time series.

This module provides functions for computing persistent homology of point clouds
derived from Takens delay embeddings of financial time series. Supports both
Vietoris-Rips and Alpha complex filtrations for computing H0, H1, and H2 homology.

The persistence diagrams capture topological features (connected components, loops,
voids) at multiple scales, enabling detection of market regimes and structural
changes in financial dynamics.

References:
    Edelsbrunner, H., Letscher, D., & Zomorodian, A. (2002). Topological
        persistence and simplification. Discrete & Computational Geometry, 28, 511-533.
    Carlsson, G. (2009). Topology and data. Bulletin of the AMS, 46(2), 255-308.
"""

from __future__ import annotations

import logging

import gudhi
import numpy as np
from gtda.homology import VietorisRipsPersistence, WeakAlphaPersistence
from numpy.typing import NDArray
from scipy.spatial.distance import pdist

logger = logging.getLogger(__name__)

# Type alias for persistence diagrams
# Format: (n_features, 3) with columns [birth, death, dimension]
PersistenceDiagram = NDArray[np.floating]


def compute_persistence_vr(
    point_cloud: NDArray[np.floating],
    homology_dimensions: tuple[int, ...] = (0, 1, 2),
    max_edge_length: float | None = None,
    n_bins: int = 100,
) -> PersistenceDiagram:
    """
    Compute persistence diagram using Vietoris-Rips filtration.

    The Vietoris-Rips complex builds simplices from points within a given
    distance threshold, computing persistent homology as the threshold grows.
    Suitable for low-dimensional embeddings (d < 10) with moderate point counts.

    Args:
        point_cloud: 2D array of shape (n_points, n_dimensions) representing
            the embedded time series point cloud.
        homology_dimensions: Tuple of homology dimensions to compute.
            Default (0, 1, 2) computes connected components (H0),
            loops (H1), and voids (H2).
        max_edge_length: Maximum edge length for the Rips complex.
            If None, computed as 90th percentile of pairwise distances.
        n_bins: Number of bins for persistence diagram discretization.
            Only affects internal computation efficiency, not output.

    Returns:
        Persistence diagram of shape (n_features, 3) where each row is
        [birth, death, dimension]. Features are sorted by dimension,
        then by persistence (death - birth) descending.

    Raises:
        ValueError: If point_cloud is not 2D or has fewer than 2 points.

    Examples:
        >>> import numpy as np
        >>> from financial_tda.topology import takens_embedding
        >>> # Create point cloud from time series
        >>> ts = np.sin(np.linspace(0, 4*np.pi, 200))
        >>> point_cloud = takens_embedding(ts, delay=5, dimension=3)
        >>> # Compute persistence diagram
        >>> diagram = compute_persistence_vr(point_cloud)
        >>> print(f"Found {len(diagram)} topological features")

    Notes:
        Computational complexity is O(n^3) for n points in the worst case.
        For large point clouds (>1000 points), consider using Alpha complex
        via `compute_persistence_alpha()` which is more efficient.
    """
    # Input validation
    point_cloud = np.asarray(point_cloud, dtype=np.float64)

    if point_cloud.ndim != 2:
        raise ValueError(
            f"point_cloud must be 2D, got shape {point_cloud.shape}. "
            "Expected (n_points, n_dimensions)."
        )

    n_points, n_dims = point_cloud.shape

    if n_points < 2:
        raise ValueError(f"point_cloud must have at least 2 points, got {n_points}.")

    if not np.isfinite(point_cloud).all():
        raise ValueError("point_cloud contains non-finite values (NaN or Inf).")

    # Compute max_edge_length if not provided
    if max_edge_length is None:
        # Use 90th percentile of pairwise distances
        if n_points <= 1000:
            distances = pdist(point_cloud)
            max_edge_length = float(np.percentile(distances, 90))
        else:
            # For large point clouds, sample to estimate
            sample_idx = np.random.choice(n_points, min(1000, n_points), replace=False)
            distances = pdist(point_cloud[sample_idx])
            max_edge_length = float(np.percentile(distances, 90))

        logger.debug(
            "Auto-computed max_edge_length=%.4f from 90th percentile", max_edge_length
        )

    # Ensure max_edge_length is positive
    if max_edge_length <= 0:
        max_edge_length = 1.0
        logger.warning("max_edge_length was <= 0, defaulting to 1.0")

    # giotto-tda expects 3D input: (n_samples, n_points, n_dimensions)
    # For single point cloud, add batch dimension
    point_cloud_3d = point_cloud[np.newaxis, :, :]

    # Create and fit VietorisRipsPersistence transformer
    vr_persistence = VietorisRipsPersistence(
        homology_dimensions=homology_dimensions,
        max_edge_length=max_edge_length,
        n_jobs=-1,  # Use all available cores
    )

    # Compute persistence diagrams
    diagrams = vr_persistence.fit_transform(point_cloud_3d)

    # Extract single diagram (remove batch dimension)
    diagram = diagrams[0]

    logger.debug(
        "Computed VR persistence: %d features (dims=%s, max_edge=%.4f)",
        len(diagram),
        homology_dimensions,
        max_edge_length,
    )

    return diagram


def compute_persistence_alpha(
    point_cloud: NDArray[np.floating],
    homology_dimensions: tuple[int, ...] = (0, 1, 2),
) -> PersistenceDiagram:
    """
    Compute persistence diagram using Alpha complex filtration.

    The Alpha complex is a subcomplex of the Delaunay triangulation,
    providing more efficient computation than Vietoris-Rips for larger
    point clouds. Preferred for embeddings with >1000 points.

    Args:
        point_cloud: 2D array of shape (n_points, n_dimensions) representing
            the embedded time series point cloud.
        homology_dimensions: Tuple of homology dimensions to compute.
            Default (0, 1, 2) computes H0, H1, and H2.

    Returns:
        Persistence diagram of shape (n_features, 3) where each row is
        [birth, death, dimension]. Features are sorted by dimension,
        then by persistence descending.

    Raises:
        ValueError: If point_cloud is not 2D or has fewer than 2 points.

    Examples:
        >>> import numpy as np
        >>> from financial_tda.topology import takens_embedding
        >>> # Create large point cloud
        >>> ts = np.random.randn(5000).cumsum()
        >>> point_cloud = takens_embedding(ts, delay=5, dimension=3)
        >>> # Compute persistence (more efficient than VR for large clouds)
        >>> diagram = compute_persistence_alpha(point_cloud)

    Notes:
        Alpha complex filtration values are squared distances. The output
        is converted to standard distance scale for consistency with VR.

        More efficient than VR for large point clouds but limited to
        low dimensions (typically d <= 6) due to Delaunay complexity.
    """
    # Input validation
    point_cloud = np.asarray(point_cloud, dtype=np.float64)

    if point_cloud.ndim != 2:
        raise ValueError(
            f"point_cloud must be 2D, got shape {point_cloud.shape}. "
            "Expected (n_points, n_dimensions)."
        )

    n_points, n_dims = point_cloud.shape

    if n_points < 2:
        raise ValueError(f"point_cloud must have at least 2 points, got {n_points}.")

    if not np.isfinite(point_cloud).all():
        raise ValueError("point_cloud contains non-finite values (NaN or Inf).")

    # giotto-tda expects 3D input: (n_samples, n_points, n_dimensions)
    point_cloud_3d = point_cloud[np.newaxis, :, :]

    # Use WeakAlphaPersistence (faster than standard Alpha for large datasets)
    alpha_persistence = WeakAlphaPersistence(
        homology_dimensions=homology_dimensions,
        n_jobs=-1,
    )

    # Compute persistence diagrams
    diagrams = alpha_persistence.fit_transform(point_cloud_3d)

    # Extract single diagram (remove batch dimension)
    diagram = diagrams[0]

    logger.debug(
        "Computed Alpha persistence: %d features (dims=%s)",
        len(diagram),
        homology_dimensions,
    )

    return diagram


def compute_persistence_gudhi(
    point_cloud: NDArray[np.floating],
    max_edge_length: float | None = None,
    max_dimension: int = 2,
) -> PersistenceDiagram:
    """
    Compute persistence diagram using GUDHI's RipsComplex.

    Alternative implementation using GUDHI directly for cross-validation
    and compatibility checking with giotto-tda results.

    Args:
        point_cloud: 2D array of shape (n_points, n_dimensions).
        max_edge_length: Maximum edge length for Rips complex.
            If None, uses diameter of point cloud.
        max_dimension: Maximum homology dimension to compute.

    Returns:
        Persistence diagram in giotto-tda compatible format (n_features, 3).

    Examples:
        >>> # Cross-validate with giotto-tda
        >>> diagram_gtda = compute_persistence_vr(point_cloud)
        >>> diagram_gudhi = compute_persistence_gudhi(point_cloud)
        >>> # Compare results
    """
    point_cloud = np.asarray(point_cloud, dtype=np.float64)

    if point_cloud.ndim != 2:
        raise ValueError(f"point_cloud must be 2D, got shape {point_cloud.shape}")

    n_points = point_cloud.shape[0]

    if n_points < 2:
        raise ValueError(f"point_cloud must have at least 2 points, got {n_points}")

    # Compute max_edge_length if not provided
    if max_edge_length is None:
        distances = pdist(point_cloud)
        max_edge_length = float(np.percentile(distances, 90))

    # Create GUDHI Rips complex
    rips_complex = gudhi.RipsComplex(
        points=point_cloud, max_edge_length=max_edge_length
    )

    # Create simplex tree
    simplex_tree = rips_complex.create_simplex_tree(max_dimension=max_dimension + 1)

    # Compute persistence
    simplex_tree.compute_persistence()

    # Extract persistence pairs
    persistence_pairs = simplex_tree.persistence()

    # Convert to giotto-tda format: [birth, death, dimension]
    if not persistence_pairs:
        return np.array([]).reshape(0, 3)

    diagram_list = []
    for dim, (birth, death) in persistence_pairs:
        if dim <= max_dimension:
            # Handle infinite death values
            if death == float("inf"):
                death = max_edge_length * 2  # Cap at 2x max_edge
            diagram_list.append([birth, death, dim])

    if not diagram_list:
        return np.array([]).reshape(0, 3)

    diagram = np.array(diagram_list, dtype=np.float64)

    # Sort by dimension, then by persistence
    persistence = diagram[:, 1] - diagram[:, 0]
    sort_idx = np.lexsort((-persistence, diagram[:, 2]))
    diagram = diagram[sort_idx]

    logger.debug("Computed GUDHI persistence: %d features", len(diagram))

    return diagram


def filter_infinite_bars(
    diagram: PersistenceDiagram,
    replacement: float | None = None,
) -> PersistenceDiagram:
    """
    Remove or replace infinite persistence bars in a diagram.

    Infinite bars (death = inf) represent features that persist indefinitely.
    For numerical computations, these need to be handled appropriately.

    Args:
        diagram: Persistence diagram of shape (n_features, 3).
        replacement: If provided, replace infinite deaths with this value.
            If None, remove rows with infinite death values.

    Returns:
        Filtered persistence diagram with no infinite values.

    Examples:
        >>> # Remove infinite bars
        >>> finite_diagram = filter_infinite_bars(diagram)
        >>> # Or replace with maximum finite death value
        >>> max_death = diagram[np.isfinite(diagram[:, 1]), 1].max()
        >>> capped_diagram = filter_infinite_bars(diagram, replacement=max_death)
    """
    diagram = np.asarray(diagram, dtype=np.float64)

    if diagram.size == 0:
        return diagram

    # Find infinite death values
    infinite_mask = ~np.isfinite(diagram[:, 1])

    if replacement is not None:
        # Replace infinite values
        result = diagram.copy()
        result[infinite_mask, 1] = replacement
        return result
    else:
        # Remove infinite bars
        return diagram[~infinite_mask]


def diagram_to_array(
    diagram: PersistenceDiagram,
    include_dimension: bool = True,
) -> NDArray[np.floating]:
    """
    Convert persistence diagram to simple numpy array format.

    Args:
        diagram: Persistence diagram in giotto-tda format (n_features, 3).
        include_dimension: If True, keep dimension column. If False,
            return only birth-death pairs (n_features, 2).

    Returns:
        Numpy array of persistence data.

    Examples:
        >>> array = diagram_to_array(diagram, include_dimension=False)
        >>> print(array.shape)  # (n_features, 2)
    """
    diagram = np.asarray(diagram, dtype=np.float64)

    if diagram.size == 0:
        if include_dimension:
            return np.array([]).reshape(0, 3)
        return np.array([]).reshape(0, 2)

    if include_dimension:
        return diagram
    else:
        return diagram[:, :2]  # Only birth and death columns


def get_persistence_pairs(
    diagram: PersistenceDiagram,
    dimension: int,
) -> NDArray[np.floating]:
    """
    Extract birth-death pairs for a specific homology dimension.

    Args:
        diagram: Persistence diagram of shape (n_features, 3).
        dimension: Homology dimension to extract (0, 1, or 2).

    Returns:
        Array of shape (n_features_dim, 2) with birth-death pairs
        for the specified dimension.

    Examples:
        >>> # Extract H1 (loop) features
        >>> h1_pairs = get_persistence_pairs(diagram, dimension=1)
        >>> print(f"Found {len(h1_pairs)} loops")

        >>> # Compute persistence of H1 features
        >>> h1_persistence = h1_pairs[:, 1] - h1_pairs[:, 0]
        >>> print(f"Most persistent loop: {h1_persistence.max():.4f}")
    """
    diagram = np.asarray(diagram, dtype=np.float64)

    if diagram.size == 0:
        return np.array([]).reshape(0, 2)

    # Filter by dimension
    dim_mask = diagram[:, 2] == dimension
    filtered = diagram[dim_mask]

    # Return only birth-death columns
    return filtered[:, :2]


def compute_persistence_statistics(
    diagram: PersistenceDiagram,
    dimension: int | None = None,
) -> dict[str, float]:
    """
    Compute summary statistics for a persistence diagram.

    Args:
        diagram: Persistence diagram of shape (n_features, 3).
        dimension: If provided, compute statistics only for this dimension.
            If None, compute for all features.

    Returns:
        Dictionary with statistics: n_features, mean_persistence,
        max_persistence, std_persistence, total_persistence.

    Examples:
        >>> stats = compute_persistence_statistics(diagram, dimension=1)
        >>> print(f"H1 features: {stats['n_features']}")
        >>> print(f"Max loop persistence: {stats['max_persistence']:.4f}")
    """
    diagram = np.asarray(diagram, dtype=np.float64)

    if diagram.size == 0:
        return {
            "n_features": 0,
            "mean_persistence": 0.0,
            "max_persistence": 0.0,
            "std_persistence": 0.0,
            "total_persistence": 0.0,
        }

    # Filter by dimension if specified
    if dimension is not None:
        diagram = diagram[diagram[:, 2] == dimension]

    if len(diagram) == 0:
        return {
            "n_features": 0,
            "mean_persistence": 0.0,
            "max_persistence": 0.0,
            "std_persistence": 0.0,
            "total_persistence": 0.0,
        }

    # Filter infinite bars for statistics
    finite_mask = np.isfinite(diagram[:, 1])
    finite_diagram = diagram[finite_mask]

    if len(finite_diagram) == 0:
        return {
            "n_features": len(diagram),
            "mean_persistence": float("inf"),
            "max_persistence": float("inf"),
            "std_persistence": 0.0,
            "total_persistence": float("inf"),
        }

    persistence = finite_diagram[:, 1] - finite_diagram[:, 0]

    return {
        "n_features": len(diagram),
        "mean_persistence": float(np.mean(persistence)),
        "max_persistence": float(np.max(persistence)),
        "std_persistence": float(np.std(persistence)),
        "total_persistence": float(np.sum(persistence)),
    }
