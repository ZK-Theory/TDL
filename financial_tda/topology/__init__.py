"""
Topological data analysis computations for financial time series.
"""

from financial_tda.topology.embedding import (
    optimal_dimension,
    optimal_tau,
    takens_embedding,
)
from financial_tda.topology.features import (
    betti_curve,
    betti_curve_statistics,
    compute_landscape_norms,
    compute_multiscale_persistence_images,
    compute_persistence_image,
    compute_persistence_landscape,
    extract_entropy_betti_features,
    extract_image_features,
    extract_landscape_features,
    landscape_lp_norm,
    landscape_statistics,
    persistence_amplitude,
    persistence_entropy,
    total_persistence,
)
from financial_tda.topology.filtration import (
    compute_persistence_alpha,
    compute_persistence_gudhi,
    compute_persistence_statistics,
    compute_persistence_vr,
    diagram_to_array,
    filter_infinite_bars,
    get_persistence_pairs,
)

__all__ = [
    # Embedding functions
    "optimal_dimension",
    "optimal_tau",
    "takens_embedding",
    # Persistence computation
    "compute_persistence_vr",
    "compute_persistence_alpha",
    "compute_persistence_gudhi",
    # Diagram utilities
    "filter_infinite_bars",
    "diagram_to_array",
    "get_persistence_pairs",
    "compute_persistence_statistics",
    # Feature extraction
    "compute_persistence_landscape",
    "landscape_lp_norm",
    "compute_landscape_norms",
    "landscape_statistics",
    "extract_landscape_features",
    "compute_persistence_image",
    "extract_image_features",
    "compute_multiscale_persistence_images",
    "persistence_entropy",
    "betti_curve",
    "betti_curve_statistics",
    "total_persistence",
    "persistence_amplitude",
    "extract_entropy_betti_features",
]
