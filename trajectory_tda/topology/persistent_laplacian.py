# Research context: TDA-Research/00-Meta/Discovery/c1-persistent-laplacian-gate-check-result-2026-07-03.md
# Purpose: Persistent-Laplacian non-harmonic spectrum (Fiedler curve lambda1(t)) on the
#   9-state BHPS employment-state transition graph. Extracted from the C1 gate-check
#   script (GO — ADDITIVE-CANDIDATE, 2026-07-03) into a reusable module. PETLS is the
#   primary backend when importable; the from-scratch numpy implementation (Memoli-Wan-
#   Wang Schur-complement formulation) is the validated fallback — Gate 2 proved it
#   correct (ker(L1) == ripser beta_1 bit-for-bit) at 35/35 real filtration thresholds,
#   and both backends were cross-validated to agree at 35/35 thresholds on 2026-07-07
#   before this module was written.
"""Persistent-Laplacian non-harmonic spectrum on a weighted graph's flag complex.

Backends:
    petls: C++ implementation (arXiv:2508.11560, Jones & Wei). Requires the MSYS2
        UCRT64 DLL directory on Windows — see ``_ensure_petls_dll_path``.
    numpy: from-scratch Schur-complement Laplacian (Memoli-Wan-Wang, arXiv:2012.02808).
        Always available; the validated fallback.

Both backends compute the same object: the ordinary combinatorial 1-Laplacian
``L1 = d1^T d1 + d2 d2^T`` of the flag complex ``K_t`` at filtration threshold ``t``
(a single-scale snapshot, not the two-complex persistent operator Delta_1^{K_a,K_b}
for a < b) — this is the object Gate 2 validated, and both backends must agree on it.

The float32 distance-matrix convention is mandatory: ripser uses float32 internally,
so ``betti_1_at_threshold``'s strict (epsilon-free) comparison is exact only because
thresholds are extracted from a float32 ``D``. Do not switch to float64 or add epsilon
"for safety" — see the gate-check note this module was extracted from.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

if sys.platform == "win32":
    # No-op on non-Windows. Mandatory guard: PETLS was compiled against the MSYS2
    # UCRT64 ecosystem (Boost, OpenBLAS, LAPACKE); Windows will not find those DLLs
    # without this, and any bare `import petls` crashes with a generic
    # "ImportError: DLL load failed while importing".
    _MSYS2_UCRT64_BIN = r"C:\msys64\ucrt64\bin"
    if os.path.isdir(_MSYS2_UCRT64_BIN):
        os.add_dll_directory(_MSYS2_UCRT64_BIN)

try:
    import petls as _petls

    PETLS_AVAILABLE = True
    PETLS_BACKEND_NAME = "petls"
except ImportError:
    try:
        import petls_pytorch as _petls  # type: ignore[no-redef]

        PETLS_AVAILABLE = True
        PETLS_BACKEND_NAME = "petls-pytorch"
    except ImportError:
        _petls = None
        PETLS_AVAILABLE = False
        PETLS_BACKEND_NAME = "none"

Backend = Literal["auto", "petls", "numpy"]


# ─────────────────────────────────────────────────────────────────────────────
# Transition graph construction
# ─────────────────────────────────────────────────────────────────────────────


def build_undirected_graph(counts: NDArray[np.int64]) -> NDArray[np.float32]:
    """Convert a directed count matrix to an undirected distance matrix.

    Edge weight = 1 / (symmetric_count + 1); absent edges get weight inf.
    Symmetrised count = count(i->j) + count(j->i). Self-loops excluded
    (diagonal = 0 for distance).

    Returns:
        A float32 matrix so thresholds and ripser birth/death values share the
        same representation — comparisons in ``betti_1_at_threshold`` are exact
        without epsilon fudging.
    """
    n = counts.shape[0]
    D = np.full((n, n), np.inf, dtype=np.float32)
    np.fill_diagonal(D, np.float32(0.0))
    for i in range(n):
        for j in range(i + 1, n):
            total = int(counts[i, j] + counts[j, i])
            if total > 0:
                w = np.float32(1.0 / (total + 1))
                D[i, j] = w
                D[j, i] = w
    return D


# ─────────────────────────────────────────────────────────────────────────────
# Simplicial complex at filtration threshold t
# ─────────────────────────────────────────────────────────────────────────────


def build_complex_at_threshold(
    D: NDArray[np.float32], t: float
) -> tuple[list[tuple[int, int]], list[tuple[int, int, int]]]:
    """Return edges and triangles of the flag complex at threshold ``t``.

    Edges: (i, j) with D[i,j] <= t and i < j.
    Triangles: (i, j, k) with all three edges present and i < j < k.
    """
    n = D.shape[0]
    edges: list[tuple[int, int]] = []
    edge_set: set[tuple[int, int]] = set()
    for i in range(n):
        for j in range(i + 1, n):
            if D[i, j] <= t:
                edges.append((i, j))
                edge_set.add((i, j))

    triangles: list[tuple[int, int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                if (i, j) in edge_set and (i, k) in edge_set and (j, k) in edge_set:
                    triangles.append((i, j, k))

    return edges, triangles


# ─────────────────────────────────────────────────────────────────────────────
# Boundary operators and 1-Laplacian (numpy backend)
# ─────────────────────────────────────────────────────────────────────────────


def build_boundary_1(n_nodes: int, edges: list[tuple[int, int]]) -> NDArray[np.float64]:
    """Build d_1: n_edges columns, n_nodes rows. Column e=(i,j): +1 at j, -1 at i."""
    n_e = len(edges)
    d1 = np.zeros((n_nodes, n_e), dtype=np.float64)
    for col, (i, j) in enumerate(edges):
        d1[i, col] = -1.0
        d1[j, col] = +1.0
    return d1


def build_boundary_2(edges: list[tuple[int, int]], triangles: list[tuple[int, int, int]]) -> NDArray[np.float64]:
    """Build d_2: n_triangles columns, n_edges rows.

    For triangle (i,j,k) with i<j<k: three oriented faces are
    (j,k), -(i,k), (i,j) with signs +1, -1, +1.
    """
    edge_idx = {e: idx for idx, e in enumerate(edges)}
    n_e = len(edges)
    n_t = len(triangles)
    d2 = np.zeros((n_e, n_t), dtype=np.float64)
    for col, (i, j, k) in enumerate(triangles):
        if (j, k) in edge_idx:
            d2[edge_idx[(j, k)], col] = +1.0
        if (i, k) in edge_idx:
            d2[edge_idx[(i, k)], col] = -1.0
        if (i, j) in edge_idx:
            d2[edge_idx[(i, j)], col] = +1.0
    return d2


def compute_laplacian_1(d1: NDArray[np.float64], d2: NDArray[np.float64]) -> NDArray[np.float64]:
    """1-Laplacian: L_1 = d1^T d1 + d2 d2^T, acting on 1-chains (edges)."""
    return d1.T @ d1 + d2 @ d2.T


def eigen_analysis(L: NDArray[np.float64], tol: float = 1e-8) -> tuple[int, float | None]:
    """Return (kernel_dim, lambda1) for a symmetric matrix L.

    kernel_dim = number of eigenvalues < tol.
    lambda1 = smallest eigenvalue >= tol, or None if all eigenvalues < tol.
    """
    if L.shape[0] == 0:
        return 0, None
    evals = np.linalg.eigvalsh(L)
    kernel_dim = int(np.sum(evals < tol))
    positives = evals[evals >= tol]
    lambda1 = float(positives[0]) if len(positives) > 0 else None
    return kernel_dim, lambda1


def _eigen_analysis_petls(
    d1: NDArray[np.float64], d2: NDArray[np.float64], tol: float = 1e-8
) -> tuple[int, float | None]:
    """PETLS-backed equivalent of ``eigen_analysis``.

    Builds a single-scale ``petls.Complex`` (all filtration values 0.0) from the
    same boundary operators the numpy path uses, and reads the dim=1 spectrum at
    (a=0, b=0) — the non-persistent L1 snapshot, matching ``compute_laplacian_1``
    exactly. Cross-validated against the numpy path on the real 9-node/35-threshold
    substrate: 0 mismatches (2026-07-07).
    """
    n_edges = d1.shape[1]
    n_triangles = d2.shape[1]
    if n_edges == 0:
        return 0, None
    filt_vertices = [0.0] * d1.shape[0]
    filt_edges = [0.0] * n_edges
    filt_triangles = [0.0] * n_triangles
    complex_ = _petls.Complex(boundaries=[d1, d2], filtrations=[filt_vertices, filt_edges, filt_triangles])
    evals, _evecs = complex_.eigenpairs(dim=1, a=0.0, b=0.0)
    evals_arr = np.sort(np.asarray(evals, dtype=np.float64))
    kernel_dim = int(np.sum(evals_arr < tol))
    positives = evals_arr[evals_arr >= tol]
    lambda1 = float(positives[0]) if len(positives) > 0 else None
    return kernel_dim, lambda1


# ─────────────────────────────────────────────────────────────────────────────
# Persistent homology via ripser (Betti validation, Gate 2)
# ─────────────────────────────────────────────────────────────────────────────


def compute_ph_barcodes(D: NDArray[np.float32], max_dim: int = 1) -> dict[int, NDArray[np.float64]]:
    """Run ripser on distance matrix; return barcodes up to ``max_dim``."""
    from ripser import ripser as _ripser

    # Replace inf with max finite + 1 for ripser; stay in float32.
    D_finite = D.copy()
    finite_vals = D_finite[np.isfinite(D_finite) & (D_finite > 0)]
    thresh = np.float32(float(finite_vals.max()) + 1.0) if len(finite_vals) > 0 else np.float32(2.0)
    D_finite[~np.isfinite(D_finite)] = thresh

    # D_finite is already float32; ripser uses float32 internally so birth/death
    # values will be exact float32 representations of our edge weights.
    result = _ripser(D_finite, maxdim=max_dim, distance_matrix=True)
    dgms: dict[int, NDArray[np.float64]] = {}
    for dim, pairs in enumerate(result["dgms"]):
        dgms[dim] = pairs
    return dgms


def betti_1_at_threshold(dgms: dict[int, NDArray[np.float64]], t: float) -> int:
    """Count H1 classes born <= t and still alive at t (death > t).

    Exact comparison is valid because t is extracted from a float32 D matrix
    and ripser also uses float32 internally — both sides of the comparison
    hold the same float32 value widened to float64. Do not add epsilon.
    """
    if 1 not in dgms or len(dgms[1]) == 0:
        return 0
    pairs = dgms[1]
    births = pairs[:, 0]
    deaths = pairs[:, 1]
    finite_mask = np.isfinite(deaths)
    return int(np.sum((births <= t) & (deaths > t) & finite_mask))


# ─────────────────────────────────────────────────────────────────────────────
# Public entrypoint: Fiedler curve across the filtration
# ─────────────────────────────────────────────────────────────────────────────


def compute_fiedler_curve(
    D: NDArray[np.float32],
    thresholds: list[float] | None = None,
    tol: float = 1e-8,
    backend: Backend = "auto",
    include_inactive: bool = False,
) -> dict[str, Any]:
    """Compute the persistent Fiedler curve lambda1(t) across the filtration.

    Args:
        D: Float32 undirected distance matrix (see ``build_undirected_graph``).
        thresholds: Filtration thresholds to evaluate. Defaults to the distinct
            finite entries of ``D``.
        tol: Kernel/positive-spectrum separation tolerance (see ``eigen_analysis``).
        backend: ``"auto"`` tries PETLS then falls back to numpy; ``"petls"`` and
            ``"numpy"`` force a specific backend (``"petls"`` raises ImportError
            if unavailable — used by cross-backend validation tests).
        include_inactive: When ``False`` (default) only active/non-trivial steps
            are returned (a step is active if it has at least one H1 feature or a
            defined lambda1 — mirrors the gate-check's Gate 3 filtering). When
            ``True`` every threshold in ``thresholds`` is retained, with
            ``lambda1 = 0.0`` at any step where the flag complex has no positive
            non-harmonic spectrum. This yields a curve aligned 1:1 with the input
            ``thresholds`` — required to compare an observed curve against null
            draws on a common fixed grid (the null-battery use case): distinct
            distance matrices produce distinct active-step sets, so only a
            fixed-grid, 0.0-padded curve is element-wise comparable and
            trapezoidally integrable over the same abscissa.

    Returns:
        Dict with ``backend`` (the backend that actually ran), ``thresholds``,
        ``lambda1``, ``ker_dim``, and ``n_active_steps``. With
        ``include_inactive=True`` the returned lists have length
        ``len(thresholds)`` (0.0-padded); otherwise they contain only the active
        steps.
    """
    n = D.shape[0]
    if thresholds is None:
        thresholds = sorted({float(D[i, j]) for i in range(n) for j in range(i + 1, n) if np.isfinite(D[i, j])})

    use_petls = backend == "petls" or (backend == "auto" and PETLS_AVAILABLE)
    if backend == "petls" and not PETLS_AVAILABLE:
        raise ImportError("backend='petls' requested but neither petls nor petls-pytorch is importable")
    backend_name = PETLS_BACKEND_NAME if use_petls else "numpy-schur-scratch"

    # beta1 (via ripser) only gates the active-step filter; with include_inactive
    # every grid threshold is retained regardless of beta1, so the barcode pass is
    # skipped (and the returned curve aligns 1:1 with ``thresholds``).
    dgms = None if include_inactive else compute_ph_barcodes(D, max_dim=1)

    grid_t: list[float] = []
    lambda1_traj: list[float] = []
    ker_dim_traj: list[int] = []
    for t_val in thresholds:
        edges, triangles = build_complex_at_threshold(D, t_val)
        if len(edges) == 0:
            if include_inactive:
                grid_t.append(t_val)
                lambda1_traj.append(0.0)
                ker_dim_traj.append(0)
            continue
        d1 = build_boundary_1(n, edges)
        d2 = build_boundary_2(edges, triangles)
        if use_petls:
            ker_dim, lam1 = _eigen_analysis_petls(d1, d2, tol=tol)
        else:
            L1 = compute_laplacian_1(d1, d2)
            ker_dim, lam1 = eigen_analysis(L1, tol=tol)
        if include_inactive:
            grid_t.append(t_val)
            lambda1_traj.append(lam1 if lam1 is not None else 0.0)
            ker_dim_traj.append(ker_dim)
        else:
            beta1 = betti_1_at_threshold(dgms, t_val)
            if beta1 > 0 or lam1 is not None:
                grid_t.append(t_val)
                lambda1_traj.append(lam1 if lam1 is not None else 0.0)
                ker_dim_traj.append(ker_dim)

    return {
        "backend": backend_name,
        "thresholds": grid_t,
        "lambda1": lambda1_traj,
        "ker_dim": ker_dim_traj,
        "n_active_steps": len(grid_t),
    }
