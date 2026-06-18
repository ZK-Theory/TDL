"""
Multidimensional Persistent Homology for Deprivation Analysis (Approach B).

Computes Vietoris-Rips persistent homology on the 7D IMD domain score
point cloud. Each LSOA is a point in R^7 (one coordinate per deprivation
domain). PH reveals:
  - H0: Connected components (clusters / types of deprivation)
  - H1: Loops (trade-off cycles between domains)
  - H2: Voids (impossible combinations of deprivation)

Uses ripser for fast implicit Rips complex computation.

Usage:
    from poverty_tda.topology.multidim_ph import (
        load_deprivation_cloud,
        compute_rips_ph,
        persistence_summary,
    )

    X, lsoa_codes, domain_names = load_deprivation_cloud(region="west_midlands")
    ph = compute_rips_ph(X, max_dim=2)
    summary = persistence_summary(ph)
"""

from __future__ import annotations

import importlib.metadata
import logging
import math
import multiprocessing as mp
import queue
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import ripser
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger("trajectory_tda.topology.multidim_ph")

H2_CANDIDATE_TETRA_BUDGET: float = 2.0e10

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "poverty_tda" / "validation" / "data"
FALLBACK_DATA_DIR = PROJECT_ROOT / "data" / "imd"

# The 7 canonical IMD domains (these are the coordinates of our point cloud)
IMD_DOMAIN_COLS = {
    "Income Score (rate)": "income",
    "Employment Score (rate)": "employment",
    "Education, Skills and Training Score": "education",
    "Health Deprivation and Disability Score": "health",
    "Crime Score": "crime",
    "Barriers to Housing and Services Score": "housing_barriers",
    "Living Environment Score": "living_environment",
}

# Region configs (reused from diagnostic script)
REGION_CONFIGS = {
    "west_midlands": {
        "lad_names": [
            "Birmingham",
            "Coventry",
            "Dudley",
            "Sandwell",
            "Solihull",
            "Walsall",
            "Wolverhampton",
        ],
    },
    "greater_manchester": {
        "lad_names": [
            "Bolton",
            "Bury",
            "Manchester",
            "Oldham",
            "Rochdale",
            "Salford",
            "Stockport",
            "Tameside",
            "Trafford",
            "Wigan",
        ],
    },
}


@dataclass
class PHResult:
    """Container for persistent homology results."""

    # dgms: dict mapping dimension -> (N, 2) array of (birth, death) pairs
    dgms: dict[int, np.ndarray] = field(default_factory=dict)
    n_points: int = 0
    n_dimensions: int = 0
    domain_names: list[str] = field(default_factory=list)
    lsoa_codes: np.ndarray | None = None
    point_cloud: np.ndarray | None = None
    elapsed_seconds: float = 0.0
    # cocycles from ripser (for representative cycle extraction)
    cocycles: dict | None = None
    ph_method: str = "ripser"
    do_cocycles: bool = True
    threshold_rule: str | None = None
    threshold_value: float | None = None
    edge_prop_at_thresh: float | None = None
    candidate_tetrahedra_burden: float | None = None
    backend_versions: dict[str, str] = field(default_factory=dict)
    preflight: dict[str, Any] = field(default_factory=dict)

    def h_features(self, dim: int, min_persistence: float = 0.0) -> list[tuple[float, float]]:
        """Get (birth, death) pairs for a specific homology dimension."""
        if dim not in self.dgms:
            return []
        dgm = self.dgms[dim]
        features = []
        for b, d in dgm:
            if d != np.inf and (d - b) > min_persistence:
                features.append((float(b), float(d)))
        return features

    def betti_at_scale(self, epsilon: float) -> dict[int, int]:
        """Compute Betti numbers at a specific filtration scale."""
        betti = {}
        for dim in range(max(self.dgms.keys()) + 1 if self.dgms else 0):
            if dim not in self.dgms:
                betti[dim] = 0
                continue
            count = 0
            for b, d in self.dgms[dim]:
                if b <= epsilon and (d > epsilon or d == np.inf):
                    count += 1
            betti[dim] = count
        return betti


def load_deprivation_cloud(
    region: str | None = None,
    subsample: int | None = None,
    random_state: int = 42,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Load IMD 2019 domain scores as a point cloud in R^7.

    Args:
        region: Optional region name to filter to (e.g. "west_midlands").
                If None, loads all English LSOAs.
        subsample: Optional number of points to subsample (for large datasets).
        random_state: Random seed for reproducible subsampling.

    Returns:
        X: (N, 7) array of z-score standardised domain scores
        lsoa_codes: (N,) array of LSOA codes
        domain_names: list of 7 short domain names
    """
    # Find data
    imd_path = DATA_DIR / "england_imd_2019.csv"
    if not imd_path.exists():
        imd_path = FALLBACK_DATA_DIR / "england_imd_2019.csv"
    if not imd_path.exists():
        raise FileNotFoundError(f"IMD 2019 data not found at {imd_path}")

    imd = pd.read_csv(imd_path)

    # Filter to region if specified
    if region is not None:
        if region not in REGION_CONFIGS:
            raise ValueError(f"Unknown region '{region}'. Available: {list(REGION_CONFIGS.keys())}")
        lad_col = "Local Authority District name (2019)"
        imd = imd[imd[lad_col].isin(REGION_CONFIGS[region]["lad_names"])].copy()
        logger.info(f"Filtered to {region}: {len(imd)} LSOAs")

    # Extract domain scores
    csv_cols = list(IMD_DOMAIN_COLS.keys())
    missing = [c for c in csv_cols if c not in imd.columns]
    if missing:
        raise ValueError(f"Missing columns in IMD data: {missing}")

    X_raw = imd[csv_cols].values.astype(np.float64)
    lsoa_codes = imd["LSOA code (2011)"].values
    domain_names = list(IMD_DOMAIN_COLS.values())

    # Drop any rows with NaN
    valid = ~np.isnan(X_raw).any(axis=1)
    if not valid.all():
        logger.warning(f"Dropping {(~valid).sum()} rows with NaN values")
        X_raw = X_raw[valid]
        lsoa_codes = lsoa_codes[valid]

    # Subsample if requested
    if subsample is not None and subsample < len(X_raw):
        rng = np.random.RandomState(random_state)
        idx = rng.choice(len(X_raw), subsample, replace=False)
        idx.sort()
        X_raw = X_raw[idx]
        lsoa_codes = lsoa_codes[idx]
        logger.info(f"Subsampled to {subsample} points")

    # Z-score standardise (critical — domains have very different scales)
    scaler = StandardScaler()
    X = scaler.fit_transform(X_raw)

    logger.info(f"Loaded deprivation cloud: {X.shape[0]} points × {X.shape[1]} dimensions")
    for i, name in enumerate(domain_names):
        logger.info(
            f"  {name}: raw [{X_raw[:, i].min():.3f}, {X_raw[:, i].max():.3f}] "
            f"→ z [{X[:, i].min():.2f}, {X[:, i].max():.2f}]"
        )

    return X, lsoa_codes, domain_names


# Numerical tolerance for the length-matched external-dedup scheme per the
# length-matched-dedup-via-n-perm formula contract. A greedy-permutation
# covering radius at or below this value is treated as exact coverage:
# duplicate landmarks contribute zero geometric information to Rips PH, so
# PD on the externally deduplicated sample equals PD on the full sample
# modulo points on the diagonal.
DEDUP_TOLERANCE: float = 1e-10


def compute_greedy_dedup_count(
    X: np.ndarray,
    tolerance: float = DEDUP_TOLERANCE,
) -> tuple[int, float, np.ndarray]:
    """Greedy-permutation deduplication count and selected indices.

    Runs a greedy (farthest-point) permutation starting from row 0 with
    Euclidean (l2) metric, returning the smallest N for which the covering
    radius (max distance from any row to the nearest of the first N
    selected) falls at or below ``tolerance``, together with the
    permutation indices. Used by length-matched Stage-1 cells per the
    length-matched-dedup-via-n-perm formula contract: callers build the
    deduplicated landmark sample as ``X[selected_indices]`` and pass it to
    ripser without ``n_perm``, so ripser computes exact Rips PH on the
    externally deduplicated subset rather than relying on its internal
    greedy permutation (which need not agree with this one).

    Args:
        X: (n, d) point cloud, typically a maxmin landmark sample.
        tolerance: Numerical tolerance for "exact coverage". Default
            ``DEDUP_TOLERANCE`` (1e-10).

    Returns:
        Tuple ``(n_unique, covering_radius_at_n_unique, selected_indices)``:
            * ``n_unique``: smallest N with covering radius at or below
              tolerance, or ``X.shape[0]`` if no such N exists (fallback
              to no dedup — ripser is called on the full sample).
            * ``covering_radius_at_n_unique``: observed covering radius at
              ``N == n_unique``. At or below tolerance for the dedup path;
              the actual covering radius at ``X.shape[0]`` for the fallback.
            * ``selected_indices``: shape ``(n_unique,)`` int64 array of
              row indices into ``X`` selected by the greedy permutation,
              in selection order. ``X[selected_indices]`` is the
              deduplicated landmark sample on which exact Rips PH should
              be computed.

    Notes:
        See Cavanna, Jahanseir & Sheehy (2015) "A geometric perspective on
        sparse filtrations" (Proc. CCCG). The bottleneck distance between
        PD(full point cloud) and PD(greedy size-N subsample) is bounded by
        the covering radius at N; when zero (within tolerance), the bound
        is exact identity — verified by the dedup-equivalence-canary
        invariant contract.
    """
    from scipy.spatial.distance import cdist

    n = X.shape[0]
    if n <= 1:
        return n, 0.0, np.arange(n, dtype=np.int64)
    D = cdist(X, X)
    min_dists = D[0].copy()
    selected: list[int] = [0]
    for k in range(1, n):
        eps_k = float(min_dists.max())
        if eps_k <= tolerance:
            return k, eps_k, np.asarray(selected, dtype=np.int64)
        next_idx = int(np.argmax(min_dists))
        selected.append(next_idx)
        min_dists = np.minimum(min_dists, D[next_idx])
    return n, float(min_dists.max()), np.asarray(selected, dtype=np.int64)


def greedy_first_k_indices_with_radius(
    X: np.ndarray,
    k: int,
) -> tuple[np.ndarray, float]:
    """Greedy-permutation first-k indices, ignoring covering-radius termination.

    Returns the first ``k`` indices of the greedy permutation starting from
    row 0 with Euclidean (l2) metric, regardless of whether the covering
    radius drops below any tolerance. Used by probe-mode forced-dedup runs
    where a fixed ``k`` (e.g. the observed-PD dedup count) is imposed on
    null PDs to eliminate the observed-vs-null vertex-count asymmetry that
    emerges from the natural per-sample dedup.

    Args:
        X: (n, d) point cloud.
        k: Number of indices to return. Clamped to ``[1, n]``.

    Returns:
        Tuple ``(indices, covering_radius_at_k)``:
            * ``indices``: shape ``(min(k, n),)`` int64 array of greedy-
              permutation indices in selection order.
            * ``covering_radius_at_k``: observed covering radius after the
              first ``k`` indices are selected. For probe provenance only;
              not used to make termination decisions.
    """
    from scipy.spatial.distance import cdist

    n = X.shape[0]
    k_clamped = max(1, min(int(k), n))
    if n == 1:
        return np.asarray([0], dtype=np.int64), 0.0
    D = cdist(X, X)
    min_dists = D[0].copy()
    selected: list[int] = [0]
    for _ in range(k_clamped - 1):
        next_idx = int(np.argmax(min_dists))
        selected.append(next_idx)
        min_dists = np.minimum(min_dists, D[next_idx])
    return np.asarray(selected, dtype=np.int64), float(min_dists.max())


def _compute_rips_ph_legacy(
    X: np.ndarray,
    max_dim: int = 2,
    thresh: float | None = None,
) -> PHResult:
    """
    Compute Vietoris-Rips persistent homology on a point cloud using ripser.

    Ripser uses an implicit Rips representation — no simplex tree in memory —
    making it orders of magnitude faster than gudhi for point cloud PH.

    Args:
        X: (N, D) point cloud array (should be standardised)
        max_dim: Maximum homology dimension to compute (2 = H0+H1+H2)
        thresh: Maximum edge length (ripser default: enclosing radius)

    Returns:
        PHResult with persistence diagrams

    Note:
        Length-matched dedup happens *outside* this function: callers compute
        the dedup index set via ``compute_greedy_dedup_count`` and pass
        ``X[selected_indices]`` here, so ripser sees the externally
        deduplicated sample directly rather than relying on its internal
        greedy permutation (see length-matched-dedup-via-n-perm contract).
    """
    import time

    n, d = X.shape
    logger.info(f"Computing Rips PH (ripser): {n} points, {d} dims, max_dim={max_dim}")

    t0 = time.time()

    if thresh is None:
        n_sample = min(500, n)
        rng = np.random.RandomState(42)
        idx = rng.choice(n, n_sample, replace=False)
        from scipy.spatial.distance import pdist

        dists = pdist(X[idx])
        # 75th percentile captures structure without full combinatorial explosion
        thresh = float(np.percentile(dists, 75))
        logger.info(f"  Auto thresh = {thresh:.3f} (75th percentile)")

    # Run ripser — do_cocycles=True enables representative cycle extraction
    rips_kwargs = {"X": X, "maxdim": max_dim, "do_cocycles": True}
    if thresh is not None:
        rips_kwargs["thresh"] = thresh

    result = ripser.ripser(**rips_kwargs)
    elapsed = time.time() - t0

    logger.info(f"  Completed in {elapsed:.1f}s")

    # Parse results
    dgms = {}
    for dim in range(max_dim + 1):
        dgm = result["dgms"][dim]
        dgms[dim] = dgm
        finite = dgm[dgm[:, 1] != np.inf]
        inf_count = len(dgm) - len(finite)
        if len(finite) > 0:
            lifetimes = finite[:, 1] - finite[:, 0]
            top = sorted(lifetimes, reverse=True)[:5]
            logger.info(
                f"  H{dim}: {len(finite)} finite + {inf_count} infinite, "
                f"top lifetimes: {[round(float(lifetime), 3) for lifetime in top]}"
            )
        else:
            logger.info(f"  H{dim}: 0 finite + {inf_count} infinite")

    ph = PHResult(
        dgms=dgms,
        n_points=n,
        n_dimensions=d,
        elapsed_seconds=elapsed,
        cocycles=result.get("cocycles"),
    )
    return ph


def _package_version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def _backend_versions() -> dict[str, str]:
    return {"ripser": _package_version("ripser"), "gudhi": _package_version("gudhi")}


def _resolve_rips_threshold(X: np.ndarray, thresh: float | None) -> tuple[float, str]:
    if thresh is not None:
        return float(thresh), "explicit"

    n = X.shape[0]
    n_sample = min(500, n)
    rng = np.random.RandomState(42)
    idx = rng.choice(n, n_sample, replace=False)
    from scipy.spatial.distance import pdist

    dists = pdist(X[idx])
    threshold = float(np.percentile(dists, 75))
    logger.info("  Auto thresh = %.3f (75th percentile)", threshold)
    return threshold, "random-500-pairwise-pdist-p75-seed42"


def _estimate_edge_prop_at_thresh(
    X: np.ndarray,
    thresh: float,
    *,
    max_exact_pairs: int = 5_000_000,
    sample_pairs: int = 1_000_000,
) -> tuple[float, int, str]:
    """Estimate the Rips graph edge density at the chosen threshold."""
    from scipy.spatial.distance import pdist

    n = X.shape[0]
    n_pairs = n * (n - 1) // 2
    if n_pairs == 0:
        return 0.0, 0, "degenerate"
    if n_pairs <= max_exact_pairs:
        dists = pdist(X)
        return float(np.mean(dists <= thresh)), int(n_pairs), "exact-pdist"

    rng = np.random.RandomState(42)
    i = rng.randint(0, n, size=sample_pairs)
    j = rng.randint(0, n - 1, size=sample_pairs)
    j = j + (j >= i)
    distances = np.linalg.norm(X[i] - X[j], axis=1)
    return float(np.mean(distances <= thresh)), int(sample_pairs), "sampled-pairs-seed42"


def _candidate_tetrahedra_burden(n_points: int, edge_prop: float) -> float:
    if n_points < 4:
        return 0.0
    return float(math.comb(int(n_points), 4) * float(edge_prop) ** 6)


def _assert_h2_feasible_from_density(
    n_points: int,
    edge_prop: float,
    *,
    tetra_budget: float = H2_CANDIDATE_TETRA_BUDGET,
) -> dict[str, float | int | bool]:
    burden = _candidate_tetrahedra_burden(n_points, edge_prop)
    feasible = burden <= tetra_budget
    metrics: dict[str, float | int | bool] = {
        "n_points": int(n_points),
        "edge_prop_at_thresh": float(edge_prop),
        "candidate_tetrahedra_burden": float(burden),
        "tetra_budget": float(tetra_budget),
        "feasible": bool(feasible),
    }
    if not feasible:
        raise RuntimeError(
            "H2 Rips feasibility gate rejected this call: "
            f"n={n_points}, edge_prop={edge_prop:.6f}, "
            f"candidate_tetrahedra_burden={burden:.3e}, budget={tetra_budget:.3e}. "
            "Use a smaller L, a lower threshold, or an amended backend plan."
        )
    return metrics


def _assert_h2_feasible(
    X: np.ndarray,
    thresh: float,
    *,
    tetra_budget: float = H2_CANDIDATE_TETRA_BUDGET,
) -> dict[str, Any]:
    edge_prop, edge_sample_n, edge_density_method = _estimate_edge_prop_at_thresh(X, thresh)
    metrics = _assert_h2_feasible_from_density(X.shape[0], edge_prop, tetra_budget=tetra_budget)
    metrics["edge_density_sample_n"] = int(edge_sample_n)
    metrics["edge_density_method"] = edge_density_method
    return metrics


def _log_diagram_summary(dgms: dict[int, np.ndarray], max_dim: int) -> None:
    for dim in range(max_dim + 1):
        dgm = dgms.get(dim, np.empty((0, 2)))
        finite = dgm[dgm[:, 1] != np.inf] if len(dgm) else np.empty((0, 2))
        inf_count = len(dgm) - len(finite)
        if len(finite) > 0:
            lifetimes = finite[:, 1] - finite[:, 0]
            top = sorted(lifetimes, reverse=True)[:5]
            logger.info(
                "  H%d: %d finite + %d infinite, top lifetimes: %s",
                dim,
                len(finite),
                inf_count,
                [round(float(lifetime), 3) for lifetime in top],
            )
        else:
            logger.info("  H%d: 0 finite + %d infinite", dim, inf_count)


def _compute_rips_ph_direct(
    X: np.ndarray,
    max_dim: int = 2,
    thresh: float | None = None,
    *,
    do_cocycles: bool = True,
    method: str = "ripser",
    feasibility_tetra_budget: float | None = None,
    collapse_iterations: int = 1,
) -> PHResult:
    """Compute Rips PH directly in the current process."""
    import time

    if method not in {"ripser", "collapse"}:
        raise ValueError("method must be 'ripser' or 'collapse'")

    n, d = X.shape
    logger.info("Computing Rips PH (%s): %d points, %d dims, max_dim=%d", method, n, d, max_dim)
    t0 = time.time()
    threshold, threshold_rule = _resolve_rips_threshold(X, thresh)
    preflight: dict[str, Any] = {}
    if max_dim >= 2 and (method == "collapse" or feasibility_tetra_budget is not None):
        budget = H2_CANDIDATE_TETRA_BUDGET if feasibility_tetra_budget is None else float(feasibility_tetra_budget)
        preflight = _assert_h2_feasible(X, threshold, tetra_budget=budget)
        logger.info(
            "  H2 preflight: edge_prop=%.4f candidate_tetrahedra=%.3e budget=%.3e",
            preflight["edge_prop_at_thresh"],
            preflight["candidate_tetrahedra_burden"],
            preflight["tetra_budget"],
        )

    if method == "ripser":
        result = ripser.ripser(X=X, maxdim=max_dim, do_cocycles=do_cocycles, thresh=threshold)
        dgms = {dim: result["dgms"][dim] for dim in range(max_dim + 1)}
        cocycles = result.get("cocycles")
    else:
        import gudhi

        rips_complex = gudhi.RipsComplex(points=np.asarray(X, dtype=np.float64), max_edge_length=threshold)
        simplex_tree = rips_complex.create_simplex_tree(max_dimension=1)
        if collapse_iterations > 0:
            simplex_tree.collapse_edges(nb_iterations=int(collapse_iterations))
        simplex_tree.expansion(max_dim + 1)
        simplex_tree.compute_persistence()
        dgms = {
            dim: np.asarray(simplex_tree.persistence_intervals_in_dimension(dim), dtype=np.float64).reshape(-1, 2)
            for dim in range(max_dim + 1)
        }
        cocycles = None

    elapsed = time.time() - t0
    logger.info("  Completed in %.1fs", elapsed)
    _log_diagram_summary(dgms, max_dim)

    return PHResult(
        dgms=dgms,
        n_points=n,
        n_dimensions=d,
        elapsed_seconds=elapsed,
        cocycles=cocycles,
        ph_method=method,
        do_cocycles=bool(do_cocycles),
        threshold_rule=threshold_rule,
        threshold_value=float(threshold),
        edge_prop_at_thresh=None if not preflight else float(preflight["edge_prop_at_thresh"]),
        candidate_tetrahedra_burden=None if not preflight else float(preflight["candidate_tetrahedra_burden"]),
        backend_versions=_backend_versions(),
        preflight=preflight,
    )


def _compute_rips_ph_child(
    result_queue: mp.Queue,
    X: np.ndarray,
    kwargs: dict[str, Any],
) -> None:
    try:
        result_queue.put(("ok", _compute_rips_ph_direct(X, **kwargs)))
    except BaseException:
        result_queue.put(("error", traceback.format_exc()))


def _compute_rips_ph_in_child(
    X: np.ndarray,
    kwargs: dict[str, Any],
    timeout_seconds: float,
) -> PHResult:
    ctx = mp.get_context("spawn")
    result_queue: mp.Queue = ctx.Queue(maxsize=1)
    proc = ctx.Process(target=_compute_rips_ph_child, args=(result_queue, X, kwargs))
    proc.start()
    deadline = time.time() + float(timeout_seconds)
    status: str | None = None
    payload: Any = None
    while time.time() < deadline:
        try:
            status, payload = result_queue.get(timeout=0.5)
            break
        except queue.Empty:
            if not proc.is_alive():
                break
    if status is None:
        if proc.is_alive():
            proc.terminate()
            proc.join(5)
            raise TimeoutError(f"Rips PH child process exceeded timeout_seconds={timeout_seconds}")
        proc.join(5)
        raise RuntimeError(f"Rips PH child process exited without a result; exitcode={proc.exitcode}")
    proc.join(5)
    if proc.is_alive():
        proc.terminate()
        proc.join(5)
    try:
        result_queue.close()
    except Exception:
        pass
    if status == "error":
        raise RuntimeError(f"Rips PH child process failed:\n{payload}")
    return payload


def compute_rips_ph(
    X: np.ndarray,
    max_dim: int = 2,
    thresh: float | None = None,
    *,
    do_cocycles: bool = True,
    method: str = "ripser",
    feasibility_tetra_budget: float | None = None,
    collapse_iterations: int = 1,
    timeout_seconds: float | None = None,
) -> PHResult:
    """
    Compute Vietoris-Rips persistent homology on a point cloud.

    Defaults preserve the historical ripser path with cocycles enabled. H2
    production runs can opt into ``method='collapse'`` plus the feasibility
    gate and a child-process timeout.
    """
    kwargs = {
        "max_dim": max_dim,
        "thresh": thresh,
        "do_cocycles": do_cocycles,
        "method": method,
        "feasibility_tetra_budget": feasibility_tetra_budget,
        "collapse_iterations": collapse_iterations,
    }
    if timeout_seconds is not None:
        return _compute_rips_ph_in_child(X, kwargs, float(timeout_seconds))
    return _compute_rips_ph_direct(X, **kwargs)


def persistence_summary(ph: PHResult, min_persistence: float = 0.0) -> dict:
    """
    Compute summary statistics of persistence diagram.

    Returns dict with:
        - n_features, n_finite, n_infinite per dimension
        - total_persistence: sum of finite lifetimes
        - max_persistence: longest-lived finite feature
        - persistence_entropy: Shannon entropy of normalised lifetimes
        - features: top 20 (birth, death, lifetime) tuples
    """
    summary = {}

    for dim in range(max(ph.dgms.keys()) + 1 if ph.dgms else 0):
        if dim not in ph.dgms:
            summary[f"H{dim}"] = {
                "n_features": 0,
                "n_finite": 0,
                "n_infinite": 0,
                "total_persistence": 0.0,
                "max_persistence": 0.0,
                "persistence_entropy": 0.0,
                "features": [],
            }
            continue

        dgm = ph.dgms[dim]
        features = []
        for b, d in dgm:
            lifetime = float(d - b) if d != np.inf else float("inf")
            if lifetime > min_persistence:
                features.append((float(b), float(d), lifetime))
        # Sort by lifetime descending
        features.sort(key=lambda x: x[2] if x[2] != float("inf") else 1e10, reverse=True)

        finite_lifetimes = [lt for (_, _, lt) in features if lt != float("inf")]

        total_pers = sum(finite_lifetimes) if finite_lifetimes else 0.0
        max_pers = max(finite_lifetimes) if finite_lifetimes else 0.0

        # Persistence entropy
        entropy = 0.0
        if finite_lifetimes and total_pers > 0:
            probs = np.array(finite_lifetimes) / total_pers
            probs = probs[probs > 0]
            entropy = float(-np.sum(probs * np.log(probs)))

        summary[f"H{dim}"] = {
            "n_features": len(features),
            "n_finite": len(finite_lifetimes),
            "n_infinite": len(features) - len(finite_lifetimes),
            "total_persistence": total_pers,
            "max_persistence": max_pers,
            "persistence_entropy": entropy,
            "features": features[:20],  # Top 20 for brevity
        }

    return summary


def betti_curve(ph: PHResult, n_points: int = 200) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    """
    Compute Betti curves β_k(ε) for k = 0, 1, 2.

    Returns:
        {dim: (epsilon_values, betti_values)} for each dimension
    """
    # Determine epsilon range from all birth/death values
    all_values = []
    for dim in ph.dgms:
        for b, d in ph.dgms[dim]:
            all_values.append(b)
            if d != np.inf:
                all_values.append(d)
    if not all_values:
        eps = np.linspace(0, 1, n_points)
    else:
        eps = np.linspace(0, max(all_values) * 1.1, n_points)

    curves = {}
    max_dim = max(ph.dgms.keys()) if ph.dgms else -1
    for dim in range(max_dim + 1):
        betti = np.zeros(n_points, dtype=int)
        if dim in ph.dgms:
            for b, d in ph.dgms[dim]:
                born = np.searchsorted(eps, b)
                if d == np.inf:
                    died = n_points
                else:
                    died = np.searchsorted(eps, d)
                betti[born:died] += 1
        curves[dim] = (eps, betti)

    return curves


def permutation_test(
    X: np.ndarray,
    n_permutations: int = 100,
    max_dim: int = 1,
    statistic: str = "total_persistence",
    **rips_kwargs,
) -> dict:
    """
    Permutation test: is the topology of the deprivation cloud
    significantly different from what you'd get by independently
    shuffling each domain?

    This preserves marginal distributions but destroys correlations
    between domains — and hence destroys any genuine topology.

    Args:
        X: (N, D) standardised point cloud
        n_permutations: Number of permutations
        max_dim: Max homology dimension to test (1 = test H1 only)
        statistic: "total_persistence" or "max_persistence"
        **rips_kwargs: Passed to compute_rips_ph

    Returns:
        Dict with observed statistic, null distribution, p-value
    """
    logger.info(f"Permutation test: {n_permutations} permutations, testing H0-H{max_dim}")

    # Observed
    ph_obs = compute_rips_ph(X, max_dim=max_dim, **rips_kwargs)
    obs_summary = persistence_summary(ph_obs)

    observed = {}
    for dim in range(max_dim + 1):
        observed[dim] = obs_summary[f"H{dim}"][statistic]
    logger.info(f"  Observed {statistic}: {observed}")

    # Null distribution
    rng = np.random.RandomState(42)
    null_stats = {dim: [] for dim in range(max_dim + 1)}

    for i in range(n_permutations):
        if (i + 1) % 10 == 0:
            logger.info(f"  Permutation {i + 1}/{n_permutations}")
        # Shuffle each column independently
        X_perm = X.copy()
        for col in range(X.shape[1]):
            rng.shuffle(X_perm[:, col])

        ph_perm = compute_rips_ph(X_perm, max_dim=max_dim, **rips_kwargs)
        perm_summary = persistence_summary(ph_perm)
        for dim in range(max_dim + 1):
            null_stats[dim].append(perm_summary[f"H{dim}"][statistic])

    # P-values
    results = {}
    for dim in range(max_dim + 1):
        null = np.array(null_stats[dim])
        obs_val = observed[dim]
        p_value = float(np.mean(null >= obs_val))
        results[f"H{dim}"] = {
            "observed": obs_val,
            "null_mean": float(null.mean()),
            "null_std": float(null.std()),
            "null_p95": float(np.percentile(null, 95)),
            "p_value": p_value,
            "significant_at_005": p_value < 0.05,
        }
        logger.info(f"  H{dim}: observed={obs_val:.4f}, null={null.mean():.4f}±{null.std():.4f}, p={p_value:.4f}")

    return results
