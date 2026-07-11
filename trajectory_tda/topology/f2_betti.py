# Research context: TDA-Research/00-Meta/Discovery (Discovery spike set A;
#   brief at .apm/memory/handoffs/2026-07-10-discovery-spikes-mcbif-brief.md)
# Purpose: Exact finite-field (F2) rank and Betti-number utilities for the
#   nerve-based MCbiF backend (Spikes 1-4 of the amended
#   GPT-Prepared-Spike-Plan-2026-07-09). Toy/feasibility code path — no paper
#   results are produced by this module directly.
"""Exact Betti numbers of a finite 2-skeleton over the field F2.

The nerve-MCbiF backend needs only ``beta0`` and ``beta1`` of small cell
complexes (at most a few hundred vertices), computed exactly:

    beta0 = n_vertices - rank(B1)
    beta1 = n_edges - rank(B1) - rank(B2)

where ``B1`` and ``B2`` are the boundary matrices of the 2-skeleton over F2.
``rank(B1)`` equals ``n_vertices - n_components`` of the 1-skeleton graph and
is computed via union-find; ``rank(B2)`` is computed by greedy Gaussian
elimination on bit-packed rows (Python integers), which is exact and fast for
the sparse 3-bits-per-row boundary columns a triangle contributes.

Orientation is irrelevant over F2; edges and triangles are canonicalised by
sorting vertex IDs.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
from numpy.typing import NDArray


def _rank_f2_int_rows(rows: Iterable[int]) -> int:
    """Rank over F2 of a set of bit-packed row vectors.

    Greedy elimination: each row is reduced against the current pivot set
    (keyed by lowest set bit) until it is zero or contributes a new pivot.

    Args:
        rows: Iterable of non-negative Python integers, each encoding one row
            vector over F2 (bit ``i`` set means entry ``i`` is 1).

    Returns:
        The F2 rank of the row set.
    """
    pivots: dict[int, int] = {}
    rank = 0
    for row in rows:
        while row:
            low = (row & -row).bit_length() - 1
            pivot = pivots.get(low)
            if pivot is None:
                pivots[low] = row
                rank += 1
                break
            row ^= pivot
    return rank


def rank_mod2(matrix: NDArray[np.uint8]) -> int:
    """Return the rank of a binary matrix over F2.

    Args:
        matrix: 2D uint8/bool array with entries in {0, 1}. A copy is
            consumed; the input is never mutated.

    Returns:
        The rank of ``matrix`` over F2.

    Raises:
        ValueError: If ``matrix`` is not 2-dimensional.
    """
    arr = np.asarray(matrix)
    if arr.ndim != 2:
        msg = f"rank_mod2 expects a 2D array, got ndim={arr.ndim}"
        raise ValueError(msg)
    if arr.size == 0:
        return 0
    bits = (arr.astype(np.uint8) & 1).copy()
    packed = np.packbits(bits, axis=1, bitorder="little")
    rows = (int.from_bytes(row.tobytes(), "little") for row in packed)
    return _rank_f2_int_rows(rows)


def _n_components(n_vertices: int, edges: list[tuple[int, int]]) -> int:
    """Number of connected components of the 1-skeleton via union-find."""
    parent = list(range(n_vertices))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    n_comp = n_vertices
    for u, v in edges:
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[ru] = rv
            n_comp -= 1
    return n_comp


def betti_0_1_from_skeleton(
    n_vertices: int,
    edges: list[tuple[int, int]],
    triangles: list[tuple[int, int, int]],
) -> tuple[int, int]:
    """Compute (beta0, beta1) of a finite 2-skeleton over F2.

    beta0 = n_vertices - rank(B1); beta1 = n_edges - rank(B1) - rank(B2).
    rank(B1) is computed as ``n_vertices - n_components`` (union-find), which
    equals the F2 matrix rank of the graph boundary matrix. rank(B2) is
    computed by bit-packed elimination on triangle boundary columns.

    Edge orientation is arbitrary but fixed by sorted vertex IDs; the triangle
    boundary is its three incident edges, mod 2. Duplicate edges/triangles are
    collapsed.

    Args:
        n_vertices: Number of vertices (IDs ``0 .. n_vertices - 1``).
        edges: Vertex-ID pairs; canonicalised to sorted tuples.
        triangles: Vertex-ID triples; canonicalised to sorted tuples. Every
            triangle's three edges must be present in ``edges``.

    Returns:
        Tuple ``(beta0, beta1)``.

    Raises:
        ValueError: If a vertex ID is out of range, an edge/triangle is
            degenerate, or a triangle references a missing edge.
    """
    if n_vertices < 0:
        msg = f"n_vertices must be non-negative, got {n_vertices}"
        raise ValueError(msg)

    canon_edges: set[tuple[int, int]] = set()
    for u, v in edges:
        if u == v:
            msg = f"Degenerate edge ({u}, {v})"
            raise ValueError(msg)
        if not (0 <= u < n_vertices and 0 <= v < n_vertices):
            msg = f"Edge ({u}, {v}) out of vertex range [0, {n_vertices})"
            raise ValueError(msg)
        canon_edges.add((u, v) if u < v else (v, u))

    edge_list = sorted(canon_edges)
    edge_index = {e: i for i, e in enumerate(edge_list)}
    n_edges = len(edge_list)

    rank_b1 = n_vertices - _n_components(n_vertices, edge_list)
    beta0 = n_vertices - rank_b1

    canon_tris: set[tuple[int, int, int]] = set()
    for tri in triangles:
        a, b, c = sorted(tri)
        if a == b or b == c:
            msg = f"Degenerate triangle {tri}"
            raise ValueError(msg)
        canon_tris.add((a, b, c))

    tri_rows: list[int] = []
    for a, b, c in sorted(canon_tris):
        row = 0
        for e in ((a, b), (a, c), (b, c)):
            idx = edge_index.get(e)
            if idx is None:
                msg = f"Triangle ({a}, {b}, {c}) references missing edge {e}"
                raise ValueError(msg)
            row |= 1 << idx
        tri_rows.append(row)

    rank_b2 = _rank_f2_int_rows(tri_rows)
    beta1 = n_edges - rank_b1 - rank_b2
    return beta0, beta1
