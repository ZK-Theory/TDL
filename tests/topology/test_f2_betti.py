# Research context: TDA-Research/00-Meta/Discovery (Discovery spike set A)
# Purpose: Deterministic unit tests for the exact F2 rank/Betti utilities
#   backing the nerve-MCbiF spikes.
"""Tests for trajectory_tda.topology.f2_betti."""

from __future__ import annotations

import numpy as np
import pytest

from trajectory_tda.topology.f2_betti import betti_0_1_from_skeleton, rank_mod2


def _rank_mod2_reference(matrix: np.ndarray) -> int:
    """Slow dense Gaussian elimination over F2 (independent oracle)."""
    a = (np.asarray(matrix).astype(np.uint8) & 1).copy()
    rank = 0
    n_rows, n_cols = a.shape
    for col in range(n_cols):
        pivot = None
        for r in range(rank, n_rows):
            if a[r, col]:
                pivot = r
                break
        if pivot is None:
            continue
        a[[rank, pivot]] = a[[pivot, rank]]
        for r in range(n_rows):
            if r != rank and a[r, col]:
                a[r] ^= a[rank]
        rank += 1
    return rank


def test_rank_mod2_known_cases() -> None:
    assert rank_mod2(np.eye(4, dtype=np.uint8)) == 4
    assert rank_mod2(np.zeros((3, 5), dtype=np.uint8)) == 0
    # Two identical rows: rank 1 over F2.
    assert rank_mod2(np.array([[1, 0, 1], [1, 0, 1]], dtype=np.uint8)) == 1
    # Row 3 = row 1 + row 2 over F2: rank 2.
    m = np.array([[1, 1, 0], [0, 1, 1], [1, 0, 1]], dtype=np.uint8)
    assert rank_mod2(m) == 2


def test_rank_mod2_matches_reference_on_random_matrices() -> None:
    rng = np.random.default_rng(42)
    for _ in range(20):
        m = rng.integers(0, 2, size=(17, 23), dtype=np.uint8)
        assert rank_mod2(m) == _rank_mod2_reference(m)


def test_rank_mod2_does_not_mutate_input() -> None:
    m = np.array([[1, 1], [1, 1]], dtype=np.uint8)
    copy = m.copy()
    rank_mod2(m)
    assert np.array_equal(m, copy)


def test_rank_mod2_rejects_non_2d() -> None:
    with pytest.raises(ValueError, match="2D"):
        rank_mod2(np.ones(3, dtype=np.uint8))


def test_betti_hollow_triangle_has_one_loop() -> None:
    edges = [(0, 1), (1, 2), (0, 2)]
    assert betti_0_1_from_skeleton(3, edges, []) == (1, 1)


def test_betti_filled_triangle_is_contractible() -> None:
    edges = [(0, 1), (1, 2), (0, 2)]
    assert betti_0_1_from_skeleton(3, edges, [(0, 1, 2)]) == (1, 0)


def test_betti_counts_components_and_isolated_vertices() -> None:
    # Two disjoint edges plus one isolated vertex: beta0 = 3, beta1 = 0.
    assert betti_0_1_from_skeleton(5, [(0, 1), (2, 3)], []) == (3, 0)


def test_betti_two_hollow_triangles_sharing_a_vertex() -> None:
    # Wedge of two circles: beta0 = 1, beta1 = 2.
    edges = [(0, 1), (1, 2), (0, 2), (2, 3), (3, 4), (2, 4)]
    assert betti_0_1_from_skeleton(5, edges, []) == (1, 2)


def test_betti_duplicate_simplices_collapse() -> None:
    edges = [(0, 1), (1, 0), (1, 2), (0, 2)]
    tris = [(0, 1, 2), (2, 1, 0)]
    assert betti_0_1_from_skeleton(3, edges, tris) == (1, 0)


def test_betti_rejects_triangle_with_missing_edge() -> None:
    with pytest.raises(ValueError, match="missing edge"):
        betti_0_1_from_skeleton(3, [(0, 1), (1, 2)], [(0, 1, 2)])


def test_betti_rank_b1_matches_rank_mod2_on_boundary_matrix() -> None:
    """Union-find rank(B1) equals the F2 matrix rank of B1."""
    rng = np.random.default_rng(42)
    n_vertices = 12
    all_pairs = [(i, j) for i in range(n_vertices) for j in range(i + 1, n_vertices)]
    idx = rng.choice(len(all_pairs), size=20, replace=False)
    edges = [all_pairs[i] for i in idx]

    b1 = np.zeros((n_vertices, len(edges)), dtype=np.uint8)
    for col, (u, v) in enumerate(edges):
        b1[u, col] = 1
        b1[v, col] = 1

    beta0, _ = betti_0_1_from_skeleton(n_vertices, edges, [])
    assert beta0 == n_vertices - rank_mod2(b1)
