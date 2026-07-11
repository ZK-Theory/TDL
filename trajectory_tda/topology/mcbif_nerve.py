# Research context: TDA-Research/00-Meta/Discovery (Discovery spike set A;
#   brief at .apm/memory/handoffs/2026-07-10-discovery-spikes-mcbif-brief.md)
# Purpose: Exact nerve-based MCbiF backend (Spike 1) computing HF0/HF1 Hilbert
#   function grids for a sequence of partitions, replacing the memory-blocked
#   individual-level MCbiF/RIVET construction (T-MCBIF-2 preflight: >10.8 GiB
#   RSS). Toy/feasibility code path — no paper results produced directly.
"""Nerve-based MCbiF Hilbert functions HF0/HF1 for a sequence of partitions.

For scales ``start <= m <= end``, the nerve cell ``K_{start,end}`` has one
vertex per cluster ``(m, label)``, an edge where two clusters share a member,
and a triangle where three clusters share a member. ``HF0[start, end]`` and
``HF1[start, end]`` are ``beta0`` and ``beta1`` of that 2-skeleton over F2.

Cluster membership is encoded as Python-int bit masks over the (shared) unit
set, so intersection tests are single big-int ``&`` operations. Because the
nerve condition depends only on the masks, ``K_{s,t}`` is the induced
subcomplex of the full-range nerve on the vertices with ``s <= m <= t`` —
``hilbert_grid_h0_h1`` therefore enumerates edges and triangles once on the
full range and filters per cell (``test_hilbert_grid_matches_per_cell_nerve``
pins equality with the direct per-cell construction).

Full multiparameter barcodes are intentionally out of scope for the spikes:
HF0/HF1 grids are sufficient (plan mandate).
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from trajectory_tda.topology.f2_betti import _rank_f2_int_rows


def masks_from_partitions(
    partitions: list[NDArray[np.int64]],
) -> dict[tuple[int, int], int]:
    """Bit-mask encoding of cluster membership per (scale, label).

    Args:
        partitions: ``partitions[m][i]`` is the integer cluster label of unit
            ``i`` at scale/wave ``m``. All arrays must share the same length.

    Returns:
        Mapping ``(m, label) -> mask`` where bit ``i`` of ``mask`` is set iff
        unit ``i`` has ``label`` at scale ``m``. Labels are Python ints.

    Raises:
        ValueError: If ``partitions`` is empty or lengths differ.
    """
    if not partitions:
        msg = "partitions must be non-empty"
        raise ValueError(msg)
    n_units = len(partitions[0])
    masks: dict[tuple[int, int], int] = {}
    for m, part in enumerate(partitions):
        arr = np.asarray(part)
        if arr.ndim != 1 or len(arr) != n_units:
            msg = f"partitions[{m}] has shape {arr.shape}; expected 1D length " f"{n_units}"
            raise ValueError(msg)
        for label in np.unique(arr):
            packed = np.packbits(arr == label, bitorder="little")
            masks[(m, int(label))] = int.from_bytes(packed.tobytes(), "little")
    return masks


def nerve_cell_skeleton(
    masks: dict[tuple[int, int], int],
    start: int,
    end: int,
    max_dim: int = 2,
) -> tuple[
    list[tuple[int, int]],
    list[tuple[int, int]],
    list[tuple[int, int, int]],
]:
    """Build the 2-skeleton of the nerve cell ``K_{start,end}``.

    Vertices are cluster vertices ``(m, label)`` for ``start <= m <= end``,
    sorted; an edge (pair of vertex indices) is included when the two masks
    intersect; a triangle (triple of vertex indices) when all three masks
    intersect.

    Note: the plan's sketch annotates the return as (vertices, triangles,
    edges); its docstring says "Return vertices, edges, triangles". The
    docstring order is implemented — it is the only one consistent with
    consuming the skeleton downstream.

    Args:
        masks: Output of :func:`masks_from_partitions`.
        start: First scale of the cell (inclusive).
        end: Last scale of the cell (inclusive); ``start <= end``.
        max_dim: 2 to include triangles, 1 for edges only.

    Returns:
        ``(vertices, edges, triangles)`` — vertices as sorted ``(m, label)``
        pairs; edges/triangles as index pairs/triples into ``vertices``.

    Raises:
        ValueError: If ``start > end``.
    """
    if start > end:
        msg = f"start ({start}) must be <= end ({end})"
        raise ValueError(msg)
    vertices = sorted(key for key in masks if start <= key[0] <= end)
    vmasks = [masks[v] for v in vertices]
    n = len(vertices)

    edges: list[tuple[int, int]] = []
    edge_masks: list[int] = []
    for i in range(n):
        mi = vmasks[i]
        for j in range(i + 1, n):
            inter = mi & vmasks[j]
            if inter:
                edges.append((i, j))
                edge_masks.append(inter)

    triangles: list[tuple[int, int, int]] = []
    if max_dim >= 2:
        for (i, j), mij in zip(edges, edge_masks, strict=True):
            for k in range(j + 1, n):
                if mij & vmasks[k]:
                    triangles.append((i, j, k))

    return vertices, edges, triangles


def hilbert_grid_h0_h1(
    partitions: list[NDArray[np.int64]],
) -> dict[str, NDArray[np.float64]]:
    """Triangular M x M Hilbert function grids HF0 and HF1.

    ``HF0[s, t]`` / ``HF1[s, t]`` are beta0 / beta1 of the nerve cell
    ``K_{s,t}``; cells with ``s > t`` are ``np.nan``.

    Implementation: the full-range nerve is enumerated once; each cell is its
    induced subcomplex on vertices with ``s <= m <= t`` (vertices are sorted
    by scale, so a cell's vertices form a contiguous slice).

    Args:
        partitions: ``partitions[m][i]`` = cluster label of unit ``i`` at
            scale ``m``; all arrays share the same length.

    Returns:
        ``{"HF0": hf0, "HF1": hf1}`` with float64 M x M arrays.
    """
    masks = masks_from_partitions(partitions)
    n_scales = len(partitions)
    vertices, edges, triangles = nerve_cell_skeleton(masks, 0, n_scales - 1)
    scales = [m for m, _ in vertices]

    # First vertex index at each scale; scales are contiguous in `vertices`.
    offset = np.searchsorted(scales, np.arange(n_scales + 1), side="left")

    # Bucket simplices by wave span (vertex indices are sorted within a
    # simplex, and vertices are sorted by scale, so endpoints give the span);
    # cell (s, t) is the union of buckets with s <= a <= b <= t. Each triangle
    # is stored as its three global edge IDs; per cell those are remapped to
    # compact local bit positions (narrow ints keep the F2 elimination fast —
    # global bit positions were measured 1.4x slower on the 19,912 x 13 run).
    edge_index = {e: k for k, e in enumerate(edges)}
    edge_buckets: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for i, j in edges:
        edge_buckets.setdefault((scales[i], scales[j]), []).append((i, j))
    tri_buckets: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
    for i, j, k in triangles:
        triple = (edge_index[(i, j)], edge_index[(i, k)], edge_index[(j, k)])
        tri_buckets.setdefault((scales[i], scales[k]), []).append(triple)

    hf0 = np.full((n_scales, n_scales), np.nan)
    hf1 = np.full((n_scales, n_scales), np.nan)
    for s in range(n_scales):
        for t in range(s, n_scales):
            lo, hi = int(offset[s]), int(offset[t + 1])
            n_verts = hi - lo

            # beta0 via union-find over the cell's edges (rank B1 implicit).
            # `_find` and `_rows` are plain closures over this iteration's
            # bindings; both are consumed before the next iteration rebinds.
            parent = list(range(n_verts))

            def _find(x: int) -> int:
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x

            n_comp = n_verts
            n_edges_cell = 0
            for a in range(s, t + 1):
                for b in range(a, t + 1):
                    for i, j in edge_buckets.get((a, b), ()):
                        n_edges_cell += 1
                        ri, rj = _find(i - lo), _find(j - lo)
                        if ri != rj:
                            parent[ri] = rj
                            n_comp -= 1

            rank_b1 = n_verts - n_comp

            local: dict[int, int] = {}
            _idx = local.setdefault

            def _rows():
                for a in range(s, t + 1):
                    for b in range(a, t + 1):
                        for e1, e2, e3 in tri_buckets.get((a, b), ()):
                            yield (
                                (1 << _idx(e1, len(local))) | (1 << _idx(e2, len(local))) | (1 << _idx(e3, len(local)))
                            )

            rank_b2 = _rank_f2_int_rows(_rows())
            hf0[s, t] = n_comp
            hf1[s, t] = n_edges_cell - rank_b1 - rank_b2
    return {"HF0": hf0, "HF1": hf1}


def _lag_sum(grid: NDArray[np.float64], lag: int) -> float:
    """Sum of grid values over cells with ``t - s == lag``."""
    n = grid.shape[0]
    if lag >= n:
        return 0.0
    return float(np.nansum(np.diagonal(grid, offset=lag)))


def hf_statistics(
    hf0: NDArray[np.float64],
    hf1: NDArray[np.float64],
) -> dict[str, float]:
    """Scalar summaries of the HF0/HF1 grids.

    "Area" is the plain sum over valid cells (unit cell area); the lag of a
    cell ``(s, t)`` is ``t - s``.

    Args:
        hf0: M x M HF0 grid (NaN below the diagonal).
        hf1: M x M HF1 grid (NaN below the diagonal).

    Returns:
        Dict with keys ``h1_total_area``, ``h1_lag1_area``, ``h1_lag2_area``,
        ``h1_lag3_area``, ``h1_lag_weighted_area`` (weight ``1 / (1 + lag)``),
        ``h1_endpoint`` (cell ``(0, M-1)``), ``h1_max``, ``h0_total_area``,
        ``h0_lag1_area``.
    """
    n = hf1.shape[0]
    weighted = 0.0
    for lag in range(n):
        weighted += _lag_sum(hf1, lag) / (1.0 + lag)
    return {
        "h1_total_area": float(np.nansum(hf1)),
        "h1_lag1_area": _lag_sum(hf1, 1),
        "h1_lag2_area": _lag_sum(hf1, 2),
        "h1_lag3_area": _lag_sum(hf1, 3),
        "h1_lag_weighted_area": weighted,
        "h1_endpoint": float(hf1[0, n - 1]),
        "h1_max": float(np.nanmax(hf1)),
        "h0_total_area": float(np.nansum(hf0)),
        "h0_lag1_area": _lag_sum(hf0, 1),
    }
