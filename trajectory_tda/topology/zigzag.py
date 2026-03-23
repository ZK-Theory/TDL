"""Zigzag persistence for temporal topology tracking.

Paper 3: Track how the topological structure of the UK trajectory space
evolves across economic cycles (1991–2023). Zigzag persistence (Carlsson
& de Silva 2010) computes a *single* barcode over the full annual tower

    P_1991 ↪ P_1991∪P_1992 ↩ P_1992 ↪ P_1992∪P_1993 ↩ … ↩ P_2022

tracking which topological features (H₀ clusters, H₁ loops) persist
across multiple consecutive years.  A bar of length k in the H₀ zigzag
barcode corresponds to a cluster that remained a distinct connected
component across k calendar years — which is qualitatively different from
what per-year independent PH or image-persistence on year-pairs can detect.

Research question: Does the number of distinct trajectory clusters (H₀)
increase during recessions, indicating fragmentation? Do loops (H₁)
appear during recovery periods?

Economic regimes in the BHPS/USoc panel (1991–2023):
    - 1993: UK recession (ERM exit)
    - 1997–2007: Post-Black Wednesday expansion
    - 2008–2009: Global Financial Crisis
    - 2010–2015: Post-crisis austerity contraction
    - 2020: COVID-19 shock

Implementation
--------------
True zigzag is computed by :func:`run_gudhi_zigzag` via **dionysus 2**
(Edelsbrunner & Morozov), which requires a Linux environment.  On Windows
the function calls the bridge script
``trajectory_tda/scripts/zigzag_dionysus_bridge.py`` through WSL::

    wsl --exec /tmp/miniforge3/bin/python zigzag_dionysus_bridge.py \\
        filtration.npz barcode.json

The zigzag filtration is the standard diamond construction:
- Vertex I (individual with PCA embedding ``v_I``, active in years
  ``[s_I, e_I]``) is a vertex present at zigzag levels
  ``[max(0, 2(s_I-Y₀)-1), 2(e_I-Y₀)+2)`` — entering at the first union
  cloud containing year ``s_I`` and leaving after the last union containing
  year ``e_I``.
- An edge ``{I, J}`` with ``d(v_I, v_J) ≤ ε`` is present for the
  intersection of the vertex-level intervals (non-empty iff the individuals
  are co-active in at least one year or consecutive-year transition).
- Triangles are added when ``max_dim ≥ 2`` to fill H₁ boundaries.

References
----------
Carlsson, G., & de Silva, V. (2010). Zigzag persistence. Foundations
of Computational Mathematics.

Edelsbrunner, H., & Morozov, D. (2015). Persistent homology: theory
and practice. Proceedings of the European Congress of Mathematics.
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# Key recession/expansion years for annotation
UK_ECONOMIC_EVENTS: dict[int, str] = {
    1993: "UK recession (ERM)",
    2008: "Global Financial Crisis",
    2009: "GFC trough",
    2010: "Austerity begins",
    2020: "COVID-19 shock",
}


@dataclass
class AnnualSnapshot:
    """Persistence diagram for a single calendar year's trajectory cloud.

    Args:
        year: Calendar year.
        diagram_h0: H₀ persistence diagram (connected components).
        diagram_h1: H₁ persistence diagram (loops).
        n_individuals: Number of individuals active in this year.
        n_landmarks: Landmarks used (if subsampled).
    """

    year: int
    diagram_h0: NDArray[np.float64]
    diagram_h1: NDArray[np.float64]
    n_individuals: int
    n_landmarks: int | None = None
    betti_threshold: float = 0.05
    economic_event: str | None = None

    def __post_init__(self) -> None:
        self.economic_event = UK_ECONOMIC_EVENTS.get(self.year)

    @property
    def total_persistence_h0(self) -> float:
        """Sum of finite H₀ lifetimes."""
        finite = self.diagram_h0[np.isfinite(self.diagram_h0[:, 1])]
        if len(finite) == 0:
            return 0.0
        return float((finite[:, 1] - finite[:, 0]).sum())

    @property
    def total_persistence_h1(self) -> float:
        """Sum of finite H₁ lifetimes."""
        finite = self.diagram_h1[np.isfinite(self.diagram_h1[:, 1])]
        if len(finite) == 0:
            return 0.0
        return float((finite[:, 1] - finite[:, 0]).sum())

    @property
    def betti_0_estimate(self) -> int:
        """Approximate β₀ (number of connected components) from H₀ diagram.

        Counts H₀ pairs with lifetime exceeding ``betti_threshold`` to
        exclude trivial components from noise.
        """
        finite = self.diagram_h0[np.isfinite(self.diagram_h0[:, 1])]
        lifetimes = finite[:, 1] - finite[:, 0]
        return int((lifetimes > self.betti_threshold).sum()) + 1  # +1 for infinite component


@dataclass
class ZigzagResult:
    """Results from a zigzag persistence computation across annual snapshots.

    Attributes:
        snapshots: Ordered list of AnnualSnapshot objects (one per year).
        betti_0_series: Time series of β₀ estimates.
        betti_1_series: Time series of β₁ estimates.
        total_persistence_h0: Time series of total H₀ persistence.
        total_persistence_h1: Time series of total H₁ persistence.
        years: Calendar years corresponding to each snapshot.
        zigzag_diagram_h0: Full zigzag H₀ persistence diagram (if computed).
        zigzag_diagram_h1: Full zigzag H₁ persistence diagram (if computed).
    """

    snapshots: list[AnnualSnapshot]
    years: list[int] = field(default_factory=list)
    betti_0_series: NDArray[np.float64] = field(default_factory=lambda: np.array([]))
    betti_1_series: NDArray[np.float64] = field(default_factory=lambda: np.array([]))
    total_persistence_h0: NDArray[np.float64] = field(default_factory=lambda: np.array([]))
    total_persistence_h1: NDArray[np.float64] = field(default_factory=lambda: np.array([]))
    zigzag_diagram_h0: NDArray[np.float64] | None = None
    zigzag_diagram_h1: NDArray[np.float64] | None = None

    def __post_init__(self) -> None:
        if self.snapshots and not self.years:
            self.years = [s.year for s in self.snapshots]
        if self.snapshots and len(self.betti_0_series) == 0:
            self.betti_0_series = np.array([s.betti_0_estimate for s in self.snapshots])
            self.total_persistence_h0 = np.array([s.total_persistence_h0 for s in self.snapshots])
            self.total_persistence_h1 = np.array([s.total_persistence_h1 for s in self.snapshots])

    def recession_years_mask(self) -> NDArray[np.bool_]:
        """Boolean mask for years with known economic downturns."""
        return np.array([y in UK_ECONOMIC_EVENTS for y in self.years])


def create_annual_snapshots(
    embeddings_by_year: dict[int, NDArray[np.float64]],
    max_filtration: float = 2.0,
    n_landmarks: int | None = 500,
    random_seed: int = 42,
) -> list[AnnualSnapshot]:
    """Compute persistence diagrams for each annual trajectory snapshot.

    Each year's point cloud must use the same coordinate system (frozen
    PCA loadings from the full-sample fit) so that topological comparisons
    across years are meaningful.

    Args:
        embeddings_by_year: Dict mapping calendar year → embedding matrix
            of shape (n_active_individuals, n_dims). Must use frozen PCA.
        max_filtration: Maximum edge length for Vietoris-Rips filtration.
        n_landmarks: If set, subsample to this many landmarks per year.
            Required for computational tractability with large annual samples.
        random_seed: RNG seed for landmark subsampling.

    Returns:
        List of AnnualSnapshot objects ordered by year.
    """
    try:
        import ripser
    except ImportError as e:
        raise ImportError("ripser is required for persistence computation. " "Install with: pip install ripser") from e

    rng = np.random.default_rng(random_seed)
    snapshots = []

    for year in sorted(embeddings_by_year.keys()):
        points = embeddings_by_year[year]
        n_original = len(points)

        if n_landmarks is not None and len(points) > n_landmarks:
            idx = rng.choice(len(points), n_landmarks, replace=False)
            points = points[idx]

        result = ripser.ripser(points, maxdim=1, thresh=max_filtration)
        diag_h0 = np.array(result["dgms"][0], dtype=np.float64)
        diag_h1 = np.array(result["dgms"][1], dtype=np.float64) if len(result["dgms"]) > 1 else np.zeros((0, 2))

        snap = AnnualSnapshot(
            year=year,
            diagram_h0=diag_h0,
            diagram_h1=diag_h1,
            n_individuals=n_original,
            n_landmarks=len(points),
        )
        snapshots.append(snap)
        logger.info(
            "Year %d: %d individuals, %d H₀ pairs, %d H₁ pairs%s",
            year,
            n_original,
            len(diag_h0),
            len(diag_h1),
            f" [{snap.economic_event}]" if snap.economic_event else "",
        )

    return snapshots


def _wsl_path(win_path: Path) -> str:
    """Convert an absolute Windows path to its WSL ``/mnt/`` equivalent."""
    parts = win_path.parts
    drive = parts[0].rstrip(":\\").lower()
    rest = "/".join(p.replace("\\", "/") for p in parts[1:])
    return f"/mnt/{drive}/{rest}"


def _vertex_level_interval(
    s_year: int,
    e_year: int,
    y0: int,
    y_end: int,
) -> tuple[int, int]:
    """Compute the first and last zigzag levels at which a vertex is present.

    The diamond zigzag sequence over years ``[y0, y_end]`` has ``2n-1``
    levels (``n = y_end - y0 + 1``):

    - Level ``2k``   → individual year-cloud ``P_{y0+k}``
    - Level ``2k+1`` → union cloud ``P_{y0+k} ∪ P_{y0+k+1}``

    An individual active in ``[s_year, e_year]`` is a vertex in:

    - ``P_t`` for ``t ∈ [s_year, e_year]``  (even levels ```2(t-y0)```)
    - ``P_t ∪ P_{t+1}`` for all ``t`` where
      ``s_year ≤ t or t+1 ≤ e_year``, i.e. ``t ∈ [s_year-1, e_year]``

    Combined, the individual is present at all levels from
    ``max(0, 2(s_year-y0)-1)`` to ``min(2(y_end-y0), 2(e_year-y0)+1)``
    inclusive.

    Args:
        s_year: First calendar year individual is active.
        e_year: Last calendar year individual is active.
        y0: First year in the zigzag timeline.
        y_end: Last year in the zigzag timeline.

    Returns:
        ``(z_start, z_end)`` — inclusive zigzag level interval.
    """
    z_start = max(0, 2 * (s_year - y0) - 1)
    z_end = min(2 * (y_end - y0), 2 * (e_year - y0) + 1)
    return z_start, z_end


def _maxmin_landmarks(
    points: NDArray[np.float64],
    n_land: int,
    rng: np.random.Generator,
) -> NDArray[np.intp]:
    """Greedy maxmin (k-centre) landmark selection.

    Returns indices of ``n_land`` points in ``points`` chosen by
    iteratively selecting the point furthest from the current landmark set.
    The first landmark is chosen uniformly at random.

    Args:
        points: Array of shape ``(n, d)``.
        n_land: Number of landmarks to select.
        rng: NumPy random generator.

    Returns:
        Integer index array of shape ``(n_land,)``.
    """
    n = len(points)
    if n_land >= n:
        return np.arange(n)

    idx = [int(rng.integers(0, n))]
    min_dists = np.full(n, np.inf)

    for _ in range(n_land - 1):
        last = points[idx[-1]]
        dists = np.linalg.norm(points - last, axis=1)
        np.minimum(min_dists, dists, out=min_dists)
        idx.append(int(np.argmax(min_dists)))

    return np.array(idx, dtype=np.intp)


def run_gudhi_zigzag(
    embeddings_by_year: dict[int, NDArray[np.float64]],
    max_filtration: float = 2.0,
    n_landmarks: int | None = 200,
    sparse: float = 0.5,
    random_seed: int = 42,
    metadata: pd.DataFrame | None = None,
    max_dim: int = 1,
    wsl_python: str = "/tmp/miniforge3/bin/python",
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Compute true zigzag persistence on the annual trajectory tower.

    Builds the diamond zigzag

        P_{y0} ↪ P_{y0}∪P_{y0+1} ↩ P_{y0+1} ↪ … ↩ P_{y_end}

    and computes a *single* H₀ and H₁ barcode over the entire multi-year
    sequence via **dionysus 2** running under WSL.  A bar of length *k* in
    the H₀ barcode represents a cluster that was a distinct connected
    component for *k* years — qualitatively different from per-year or
    image-persistence results.

    Args:
        embeddings_by_year: Dict mapping calendar year → embedding matrix
            of shape ``(n_active, n_dims)``.  Row order need not be
            consistent across years (identity is tracked via ``metadata``).
        max_filtration: Rips threshold ``ε``.  Edges longer than this are
            excluded.  Set to ``"auto"`` to use the 30th percentile of
            pairwise landmark distances (not yet implemented).
        n_landmarks: Maximum number of landmarks selected per year via
            greedy MaxMin.  Landmarks are selected per year then deduplicated
            across years using ``metadata`` row indices.  Pass ``None`` to
            use all active individuals (slow for large panels).
        sparse: Unused — retained for API compatibility.
        random_seed: Seed for the MaxMin random initialisation.
        metadata: DataFrame with columns ``start_year``, ``end_year``,
            aligned row-for-row with the full embedding matrix (from
            ``embeddings.npy``).  If ``None``, all individuals are assumed
            active across all years in ``embeddings_by_year`` (useful for
            unit tests with synthetic data).
        max_dim: Maximum homology dimension.  ``1`` for H₀ and H₁ (requires
            triangles to be added to the filtration).  ``0`` for H₀ only,
            which is faster.
        wsl_python: Path inside WSL to the Python interpreter that has
            dionysus installed.

    Returns:
        ``(h0_diagram, h1_diagram)`` — float64 arrays of shape ``(n_bars, 2)``
        with columns ``[birth_level, death_level]``.  Birth and death are
        zigzag level indices; use :func:`level_to_year` to convert to
        calendar years.  Infinite deaths are encoded as ``np.inf``.

    Raises:
        ValueError: If fewer than 2 years are provided.
        RuntimeError: If the WSL bridge script fails.
    """
    years = sorted(embeddings_by_year.keys())
    if len(years) < 2:
        raise ValueError(f"run_gudhi_zigzag requires at least 2 years, got {len(years)}")

    y0 = years[0]
    y_end = years[-1]
    n_years = y_end - y0 + 1
    rng = np.random.default_rng(random_seed)

    # ── 1. Synthetic metadata when none provided (test / backward-compat) ──
    if metadata is None:
        # Assume: all rows in every year's cloud are the same N individuals,
        # each active from y0 to y_end.  Useful for unit tests where each
        # year's cloud has the same point set.
        n_pts = len(next(iter(embeddings_by_year.values())))
        metadata = pd.DataFrame(
            {
                "start_year": [y0] * n_pts,
                "end_year": [y_end] * n_pts,
            }
        )
        # Build embeddings matrix = first year's cloud (same across years)
        emb_all = np.array(next(iter(embeddings_by_year.values())), dtype=np.float64)
        row_indices_by_year = {y: np.arange(n_pts) for y in years}
    else:
        # Use the aligned metadata + embeddings.  We need to know which rows
        # in the full embeddings matrix are active per year.
        start_years_arr = metadata["start_year"].to_numpy()
        end_years_arr = metadata["end_year"].to_numpy()
        emb_list = list(embeddings_by_year.values())
        # The embeddings_by_year values are already the per-year sub-matrices;
        # we need the ORIGINAL row indices (into the full metadata) to track
        # individual identity.  recover them from the year masks.
        row_indices_by_year: dict[int, NDArray[np.intp]] = {}
        for year in years:
            mask = (start_years_arr <= year) & (year <= end_years_arr)
            row_indices_by_year[year] = np.where(mask)[0].astype(np.intp)
        # Rebuild a "compressed" embedding from embeddings_by_year
        # (we only need the embeddings for the selected rows)
        n_dims = emb_list[0].shape[1]
        emb_all = np.full((len(metadata), n_dims), np.nan, dtype=np.float64)
        for year, row_idx in row_indices_by_year.items():
            emb_all[row_idx] = embeddings_by_year[year]

    start_years_arr = metadata["start_year"].to_numpy()
    end_years_arr = metadata["end_year"].to_numpy()

    # ── 2. Select landmarks — one set per year, then union ──────────────────
    logger.info(
        "Building zigzag filtration: %d years (%d–%d), max_filtration=%.2f, " "n_landmarks=%s, max_dim=%d",
        n_years,
        y0,
        y_end,
        max_filtration,
        n_landmarks,
        max_dim,
    )

    selected_rows: set[int] = set()
    for year, row_idx in row_indices_by_year.items():
        pts = emb_all[row_idx]
        if n_landmarks is not None and len(pts) > n_landmarks:
            land_idx = _maxmin_landmarks(pts, n_landmarks, rng)
            selected_rows.update(int(row_idx[i]) for i in land_idx)
        else:
            selected_rows.update(int(r) for r in row_idx)

    landmark_rows = np.array(sorted(selected_rows), dtype=np.intp)
    N = len(landmark_rows)
    logger.info("Total unique landmarks across all years: %d", N)

    lm_embeddings = emb_all[landmark_rows]  # (N, n_dims)
    lm_start = start_years_arr[landmark_rows]
    lm_end = end_years_arr[landmark_rows]

    # ── 3. Compute vertex level intervals ───────────────────────────────────
    z_starts = np.empty(N, dtype=np.int32)
    z_ends = np.empty(N, dtype=np.int32)
    for i in range(N):
        z_starts[i], z_ends[i] = _vertex_level_interval(int(lm_start[i]), int(lm_end[i]), y0, y_end)

    # ── 4. Find edges within ε using KD-tree ────────────────────────────────
    from scipy.spatial import cKDTree  # noqa: PLC0415

    tree = cKDTree(lm_embeddings)
    pairs = tree.query_pairs(max_filtration, output_type="ndarray")
    logger.info("Vertex pairs within ε=%.2f: %d", max_filtration, len(pairs))

    # ── 5. Build filtration arrays ───────────────────────────────────────────
    # Pre-allocate conservatively
    max_simplices = N + len(pairs)
    if max_dim >= 2:
        # Rough upper bound for triangles: O(|edges|^1.5) heuristic — cap at 2M
        max_simplices += min(len(pairs) ** 2 // 2, 2_000_000)

    sv_list: list[list[int]] = []
    times_list: list[list[float]] = []

    # Vertices
    for i in range(N):
        sv_list.append([i, -1, -1])  # pad to width 3 (covers up to 2-simplices)
        times_list.append([float(z_starts[i]), float(z_ends[i] + 1)])

    # Edges
    valid_edges: list[tuple[int, int, int, int]] = []  # (u, v, z_s, z_e)
    for u, v in pairs:
        z_s = int(max(z_starts[u], z_starts[v]))
        z_e = int(min(z_ends[u], z_ends[v]))
        if z_s > z_e:
            continue  # vertices never co-present
        sv_list.append([int(u), int(v), -1])
        times_list.append([float(z_s), float(z_e + 1)])
        if max_dim >= 2:
            valid_edges.append((int(u), int(v), z_s, z_e))

    # Triangles (for H₁ boundary computation when max_dim >= 2)
    if max_dim >= 2 and len(valid_edges) > 0:
        # Build adjacency: vertex → set of (neighbour, z_start, z_end)
        from collections import defaultdict  # noqa: PLC0415

        adj: dict[int, dict[int, tuple[int, int]]] = defaultdict(dict)
        for u, v, z_s, z_e in valid_edges:
            adj[u][v] = (z_s, z_e)
            adj[v][u] = (z_s, z_e)

        n_triangles = 0
        for u in range(N):
            nbrs = sorted(adj[u].keys())
            for idx_j, w in enumerate(nbrs):
                if w <= u:
                    continue
                for x in nbrs[idx_j + 1 :]:
                    if x <= w:
                        continue
                    if x not in adj[w]:
                        continue
                    # Triangle {u, w, x} exists if all three edges exist
                    zu_w = adj[u][w]
                    zu_x = adj[u][x]
                    zw_x = adj[w][x]
                    z_s_tri = max(zu_w[0], zu_x[0], zw_x[0])
                    z_e_tri = min(zu_w[1], zu_x[1], zw_x[1])
                    if z_s_tri > z_e_tri:
                        continue
                    sv_list.append([u, w, x])
                    times_list.append([float(z_s_tri), float(z_e_tri + 1)])
                    n_triangles += 1
        logger.info("Triangles added: %d", n_triangles)

    logger.info(
        "Filtration: %d vertices, %d edges (+triangles if max_dim=2)",
        N,
        len(sv_list) - N,
    )

    # ── 6. Serialise filtration to temp .npz ────────────────────────────────
    sv_arr = np.array(sv_list, dtype=np.int32)
    times_arr = np.array(times_list, dtype=np.float64)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        filt_path = tmp / "filtration.npz"
        bcode_path = tmp / "barcode.json"

        np.savez_compressed(filt_path, simplex_vertices=sv_arr, times=times_arr)

        # ── 7. Call WSL bridge ───────────────────────────────────────────────
        bridge_script = Path(__file__).resolve().parent.parent / "scripts" / "zigzag_dionysus_bridge.py"
        wsl_bridge = _wsl_path(bridge_script)
        wsl_filt = _wsl_path(filt_path)
        wsl_bcode = _wsl_path(bcode_path)

        logger.info("Calling WSL dionysus bridge: %s", wsl_bridge)
        result = subprocess.run(
            ["wsl", "--exec", wsl_python, wsl_bridge, wsl_filt, wsl_bcode],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"WSL zigzag bridge failed (exit {result.returncode}):\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

        if result.stderr:
            for line in result.stderr.strip().splitlines():
                logger.debug("bridge: %s", line)

        # ── 8. Parse output ──────────────────────────────────────────────────
        with open(bcode_path) as f:
            barcodes = json.load(f)

    _INF_PROXY = 1e308

    def _to_array(bars: list[list[float]]) -> NDArray[np.float64]:
        if not bars:
            return np.zeros((0, 2), dtype=np.float64)
        arr = np.array(bars, dtype=np.float64)
        arr[arr >= _INF_PROXY] = np.inf
        return arr

    h0 = _to_array(barcodes.get("0", []))
    h1 = _to_array(barcodes.get("1", []))

    logger.info(
        "Zigzag complete: %d H₀ bars, %d H₁ bars over %d-year tower (%d–%d)",
        len(h0),
        len(h1),
        n_years,
        y0,
        y_end,
    )
    return h0, h1


def level_to_year(level: float, y0: int) -> float:
    """Approximate calendar year for a zigzag level coordinate.

    Even levels correspond to individual year clouds; odd levels to
    union clouds between consecutive years.  The mapping is::

        year(z) ≈ y0 + z / 2

    Args:
        level: Zigzag level (from a bar endpoint in the barcode).
        y0: First calendar year in the sequence.

    Returns:
        Approximate calendar year (may be fractional for union levels).
    """
    return y0 + level / 2.0


def compute_topological_time_series(snapshots: list[AnnualSnapshot]) -> ZigzagResult:
    """Summarise annual snapshots as a topological time series.

    A computationally light alternative to full zigzag: analyses each
    annual persistence diagram independently and assembles the results
    into a time series for comparison against economic cycle indicators.

    This is sufficient for the preliminary analysis and the Paper 3
    results section. Full zigzag adds the cross-year feature tracking.

    Args:
        snapshots: Ordered list of AnnualSnapshot objects.

    Returns:
        ZigzagResult with per-year topological summaries.
    """
    return ZigzagResult(snapshots=snapshots)
