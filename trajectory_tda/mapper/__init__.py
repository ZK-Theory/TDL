"""KeplerMapper pipeline for trajectory space analysis (Paper 2)."""

from __future__ import annotations

from trajectory_tda.mapper.correlation_analysis import compute_outcome_correlation_matrix
from trajectory_tda.mapper.mapper_pipeline import (
    build_mapper_graph,
    save_mapper_graph,
)
from trajectory_tda.mapper.node_coloring import (
    color_nodes_by_outcome,
    compute_node_regime_distribution,
)
from trajectory_tda.mapper.parameter_search import mapper_parameter_search
from trajectory_tda.mapper.permutation_null import regime_shuffle_null, within_node_shuffle_null
from trajectory_tda.mapper.validation import (
    compute_node_membership_labels,
    validate_against_regimes,
)

__all__ = [
    "build_mapper_graph",
    "color_nodes_by_outcome",
    "compute_node_membership_labels",
    "compute_node_regime_distribution",
    "compute_outcome_correlation_matrix",
    "mapper_parameter_search",
    "regime_shuffle_null",
    "save_mapper_graph",
    "validate_against_regimes",
    "within_node_shuffle_null",
]
