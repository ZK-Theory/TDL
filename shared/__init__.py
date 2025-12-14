"""Shared TDA Utilities.

This package provides common utilities and interfaces for topological data
analysis shared between Financial TDA and Poverty TDA projects. It includes:

- Persistence diagram utilities (persistence module)
- Visualization helpers (visualization module)
- Mathematical validation tools (validation module)

The interfaces defined here establish contracts for TDA operations that will
be implemented in later development phases.
"""

from __future__ import annotations

__version__ = "0.1.0"

# Import public interfaces from submodules
from shared.persistence import (
    PersistenceDiagram,
    PersistencePair,
    compute_lifetimes,
    filter_by_dimension,
    merge_diagrams,
    normalize_diagram,
    validate_diagram,
)
from shared.validation import (
    assert_topological_consistency,
    compare_betti_numbers,
    compute_bottleneck_distance,
    compute_wasserstein_distance,
)
from shared.visualization import (
    plot_betti_curve,
    plot_persistence_barcode,
    plot_persistence_diagram,
)

# Define public API
__all__ = [
    # Version
    "__version__",
    # Type definitions
    "PersistenceDiagram",
    "PersistencePair",
    # Persistence utilities
    "validate_diagram",
    "merge_diagrams",
    "filter_by_dimension",
    "compute_lifetimes",
    "normalize_diagram",
    # Visualization
    "plot_persistence_diagram",
    "plot_betti_curve",
    "plot_persistence_barcode",
    # Validation
    "assert_topological_consistency",
    "compare_betti_numbers",
    "compute_bottleneck_distance",
    "compute_wasserstein_distance",
]
