# Research context: TDA-Research/00-Meta/Discovery (Discovery spike set A)
# Purpose: Deterministic unit tests for the Spike 6 Mapper graph construction.
"""Tests for trajectory_tda.topology.mapper_graph."""

from __future__ import annotations

import numpy as np

from trajectory_tda.topology.mapper_graph import mapper_graph, mapper_statistics


def _ring(n: int = 400, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    theta = rng.uniform(0, 2 * np.pi, n)
    r = 1.0 + rng.normal(0, 0.05, n)
    return np.column_stack([r * np.cos(theta), r * np.sin(theta)])


def test_mapper_ring_recovers_a_cycle() -> None:
    """The ring's loop survives (beta1 is the spike's decision statistic).

    Component counts are NOT asserted: the median-5NN eps rule drops DBSCAN
    noise, which legitimately leaves small satellite components.
    """
    X = _ring()
    g = mapper_graph(X, X[:, :2], n_intervals=10, overlap=0.40, min_samples=5)
    stats = mapper_statistics(g)
    assert stats["n_nodes"] > 0
    assert stats["beta1"] >= 1


def test_mapper_two_blobs_have_no_cycle_and_split() -> None:
    rng = np.random.default_rng(42)
    a = rng.normal(0, 0.1, size=(200, 2))
    b = rng.normal(5, 0.1, size=(200, 2))
    X = np.vstack([a, b])
    g = mapper_graph(X, X, n_intervals=8, overlap=0.30, min_samples=5)
    stats = mapper_statistics(g)
    assert stats["beta0"] >= 2
    assert stats["beta1"] == 0


def test_mapper_is_deterministic() -> None:
    X = _ring()
    g1 = mapper_graph(X, X[:, :2], n_intervals=10, overlap=0.40, min_samples=5)
    g2 = mapper_graph(X, X[:, :2], n_intervals=10, overlap=0.40, min_samples=5)
    assert mapper_statistics(g1) == mapper_statistics(g2)


def test_mapper_is_invariant_to_row_permutation() -> None:
    """The graph depends on the point SET — row order must not matter.

    This is also why Spike 6's literal nulls (permuting labels or vectors
    without a spatial-smoothing step) cannot perturb the statistic.
    """
    X = _ring()
    perm = np.random.default_rng(0).permutation(len(X))
    g1 = mapper_graph(X, X[:, :2], n_intervals=10, overlap=0.40, min_samples=5)
    g2 = mapper_graph(X[perm], X[perm][:, :2], n_intervals=10, overlap=0.40, min_samples=5)
    s1, s2 = mapper_statistics(g1), mapper_statistics(g2)
    assert s1 == s2


def test_mapper_statistics_empty_graph() -> None:
    X = np.zeros((4, 2))  # 4 points, all identical: bins too small for k=5
    stats = mapper_statistics(mapper_graph(X, X, n_intervals=10, overlap=0.40, min_samples=5))
    assert stats["n_nodes"] == 0
    assert stats["beta1"] == 0
