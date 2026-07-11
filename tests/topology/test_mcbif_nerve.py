# Research context: TDA-Research/00-Meta/Discovery (Discovery spike set A)
# Purpose: Deterministic unit tests for the nerve-based MCbiF HF0/HF1 backend,
#   including the three plan-mandated cases (empty-discrete, constant
#   one-cluster, and the paper's 3-element 1-conflict example).
"""Tests for trajectory_tda.topology.mcbif_nerve."""

from __future__ import annotations

import numpy as np
import pytest

from trajectory_tda.topology.f2_betti import betti_0_1_from_skeleton
from trajectory_tda.topology.mcbif_nerve import (
    hf_statistics,
    hilbert_grid_h0_h1,
    masks_from_partitions,
    nerve_cell_skeleton,
)

# 3-element example from the MCbiF paper: theta(0) = {{1},{2},{3}},
# theta(1) = {{1,2},{3}}, theta(2) = {{1},{2,3}}, theta(3) = {{1,3},{2}},
# theta(4) = {{1,2,3}}. Units ordered (1, 2, 3).
PAPER_EXAMPLE = [
    np.array([0, 1, 2]),
    np.array([0, 0, 1]),
    np.array([0, 1, 1]),
    np.array([0, 1, 0]),
    np.array([0, 0, 0]),
]


def test_masks_from_partitions_bits() -> None:
    masks = masks_from_partitions([np.array([0, 1, 0, 1])])
    assert masks[(0, 0)] == 0b0101
    assert masks[(0, 1)] == 0b1010


def test_masks_from_partitions_rejects_ragged_input() -> None:
    with pytest.raises(ValueError, match="expected 1D length"):
        masks_from_partitions([np.array([0, 1]), np.array([0, 1, 2])])


def test_nerve_cell_skeleton_paper_example_cell_1_3() -> None:
    """Hand-checked cell (1, 3): 6 vertices, 9 edges, 3 triangles."""
    masks = masks_from_partitions(PAPER_EXAMPLE)
    vertices, edges, triangles = nerve_cell_skeleton(masks, 1, 3)
    assert vertices == [(1, 0), (1, 1), (2, 0), (2, 1), (3, 0), (3, 1)]
    assert len(edges) == 9
    assert len(triangles) == 3
    assert betti_0_1_from_skeleton(len(vertices), edges, triangles) == (1, 1)


def test_nerve_cell_skeleton_max_dim_1_skips_triangles() -> None:
    masks = masks_from_partitions(PAPER_EXAMPLE)
    _, edges, triangles = nerve_cell_skeleton(masks, 1, 3, max_dim=1)
    assert len(edges) == 9
    assert triangles == []


def test_empty_discrete_partitions_have_zero_h1_area() -> None:
    """Plan test 1: all-singleton partitions at every scale -> HF1 area 0."""
    n_units, n_scales = 4, 3
    partitions = [np.arange(n_units) for _ in range(n_scales)]
    grids = hilbert_grid_h0_h1(partitions)
    stats = hf_statistics(grids["HF0"], grids["HF1"])
    assert stats["h1_total_area"] == 0.0
    # Each unit's clusters form one contractible component per cell.
    valid = ~np.isnan(grids["HF0"])
    assert np.all(grids["HF0"][valid] == n_units)


def test_constant_one_cluster_partition_is_a_point() -> None:
    """Plan test 2: one cluster at every scale -> HF0 = 1, HF1 = 0."""
    partitions = [np.zeros(5, dtype=np.int64) for _ in range(4)]
    grids = hilbert_grid_h0_h1(partitions)
    valid = ~np.isnan(grids["HF0"])
    assert np.all(grids["HF0"][valid] == 1)
    assert np.all(grids["HF1"][valid] == 0)


def test_paper_three_element_example_has_a_positive_h1_cell() -> None:
    """Plan test 3: the paper's 1-conflict example has a positive H1 cell."""
    grids = hilbert_grid_h0_h1(PAPER_EXAMPLE)
    hf1 = grids["HF1"]
    assert np.nansum(hf1) > 0
    # The conflict is visible on the interval [1, 3] (hand-checked).
    assert hf1[1, 3] == 1
    # Diagonal cells are single partitions: no 1-conflict possible.
    assert all(hf1[m, m] == 0 for m in range(len(PAPER_EXAMPLE)))


def test_hilbert_grid_matches_per_cell_nerve() -> None:
    """Induced-subcomplex optimisation equals the direct per-cell nerve."""
    rng = np.random.default_rng(42)
    partitions = [rng.integers(0, 3, size=12) for _ in range(5)]
    grids = hilbert_grid_h0_h1(partitions)
    masks = masks_from_partitions(partitions)
    for s in range(5):
        for t in range(s, 5):
            vertices, edges, triangles = nerve_cell_skeleton(masks, s, t)
            beta0, beta1 = betti_0_1_from_skeleton(len(vertices), edges, triangles)
            assert grids["HF0"][s, t] == beta0, (s, t)
            assert grids["HF1"][s, t] == beta1, (s, t)


def test_hilbert_grid_nan_below_diagonal() -> None:
    grids = hilbert_grid_h0_h1(PAPER_EXAMPLE)
    for s in range(5):
        for t in range(s):
            assert np.isnan(grids["HF0"][s, t])
            assert np.isnan(grids["HF1"][s, t])


def test_hf_statistics_on_handmade_grids() -> None:
    hf0 = np.full((3, 3), np.nan)
    hf1 = np.full((3, 3), np.nan)
    # Valid cells: (0,0) (0,1) (0,2) (1,1) (1,2) (2,2).
    hf0[0, 0], hf0[0, 1], hf0[0, 2] = 2, 2, 1
    hf0[1, 1], hf0[1, 2], hf0[2, 2] = 3, 2, 2
    hf1[0, 0], hf1[0, 1], hf1[0, 2] = 0, 1, 2
    hf1[1, 1], hf1[1, 2], hf1[2, 2] = 0, 3, 0
    stats = hf_statistics(hf0, hf1)
    assert stats["h1_total_area"] == 6.0
    assert stats["h1_lag1_area"] == 4.0
    assert stats["h1_lag2_area"] == 2.0
    assert stats["h1_lag3_area"] == 0.0
    assert stats["h1_lag_weighted_area"] == pytest.approx(0.0 + 4.0 / 2 + 2.0 / 3)
    assert stats["h1_endpoint"] == 2.0
    assert stats["h1_max"] == 3.0
    assert stats["h0_total_area"] == 12.0
    assert stats["h0_lag1_area"] == 4.0
