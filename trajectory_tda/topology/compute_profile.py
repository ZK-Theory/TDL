# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: Per-cell compute-profile instrumentation for the persistent-homology
#   battery (Simplicial-Assay-Plan amendments B3/B7). Records the cost split that
#   Task 1 never captured: complex-construction wall, PH wall, and the W2-aggregation
#   bill (pair count x per-pair wall) SEPARATELY, plus peak RSS, simplex counts by
#   dimension, diagram cardinality by dimension, and backend + version. Standalone and
#   dependency-light so it can be dropped into any battery result JSON later; this
#   worktree only *uses* it (no existing battery module is modified).
"""Compute-profile instrumentation for topological batteries.

The core object is :class:`ComputeProfile`, a serialisable record of the cost of
one battery cell. Amendment B3 requires the PH-construction cost and the
Wasserstein-2 aggregation cost to be reported *separately*, because sparse Rips
reduces only the former while witness complexes (m < L) are the only lever on the
latter. Callers time each phase with :class:`wall_timer`, count diagram features
with :func:`diagram_cardinalities`, sample peak memory with :func:`peak_rss_bytes`,
and assemble the record.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from types import TracebackType
from typing import Any

import numpy as np
from numpy.typing import NDArray


class wall_timer:
    """Context manager measuring wall-clock seconds for a code block.

    Example:
        >>> with wall_timer() as t:
        ...     _ = sum(range(1000))
        >>> t.elapsed >= 0.0
        True
    """

    def __init__(self) -> None:
        self.elapsed: float = 0.0
        self._t0: float = 0.0

    def __enter__(self) -> wall_timer:
        self._t0 = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.elapsed = time.perf_counter() - self._t0


def peak_rss_bytes() -> int | None:
    """Peak resident set size of the current process, in bytes.

    Uses the Win32 ``GetProcessMemoryInfo`` ``PeakWorkingSetSize`` on Windows
    (where ``resource``/``psutil`` are unavailable), falling back to
    ``resource.getrusage`` on POSIX. Returns ``None`` if neither is available.
    """
    import ctypes

    if hasattr(ctypes, "windll"):
        try:
            from ctypes import wintypes

            class _PMC(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = _PMC()
            counters.cb = ctypes.sizeof(_PMC)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ok = ctypes.windll.psapi.GetProcessMemoryInfo(
                handle, ctypes.byref(counters), counters.cb
            )
            if ok:
                return int(counters.PeakWorkingSetSize)
        except Exception:
            pass

    try:
        import resource

        # ru_maxrss is KiB on Linux, bytes on macOS; assume KiB (Linux) here.
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    except Exception:
        return None


def diagram_cardinalities(
    dgms: Mapping[int, NDArray[np.float64]],
) -> tuple[dict[int, int], dict[int, int]]:
    """Count finite and infinite (birth, death) pairs per homology dimension.

    Args:
        dgms: Mapping of homology dimension to an ``(n, 2)`` array of pairs.

    Returns:
        Tuple ``(finite, infinite)`` of dicts keyed by dimension.
    """
    finite: dict[int, int] = {}
    infinite: dict[int, int] = {}
    for dim, dgm in dgms.items():
        arr = np.asarray(dgm, dtype=np.float64).reshape(-1, 2)
        if arr.shape[0] == 0:
            finite[int(dim)] = 0
            infinite[int(dim)] = 0
            continue
        finite_mask = np.isfinite(arr).all(axis=1)
        finite[int(dim)] = int(finite_mask.sum())
        infinite[int(dim)] = int((~finite_mask).sum())
    return finite, infinite


def backend_version(backend: str) -> str:
    """Best-effort version string for a PH backend (``'ripser'``/``'gudhi'``)."""
    key = backend.lower()
    try:
        if "gudhi" in key:
            import gudhi

            return str(gudhi.__version__)
        if "ripser" in key:
            import ripser

            return str(getattr(ripser, "__version__", "unknown"))
    except Exception:
        return "unknown"
    return "unknown"


@dataclass
class ComputeProfile:
    """Per-cell PH + W2 cost record (amendment B3/B7).

    Attributes:
        method: Candidate label (e.g. ``"vr_ripser"``, ``"sparse_rips_eps0.10"``,
            ``"witness_m500_maxmin"``).
        dataset: Short dataset tag (e.g. ``"usoc"``).
        n_points: Number of vertices the complex is built on.
        n_landmarks: Landmark count ``L`` (equals ``n_points`` for Rips on landmarks;
            equals the witness landmark count ``m`` for witness complexes).
        n_dims: Ambient embedding dimension of the point cloud.
        max_edge_length: Filtration threshold / ``max_edge_length`` (``None`` if the
            backend resolves it internally without exposing it).
        backend: PH backend name.
        backend_version: Backend version string.
        complex_construction_wall_s: Wall seconds to build the complex (simplex tree
            / distance structure) *before* boundary reduction.
        ph_wall_s: Wall seconds for persistence computation.
        simplex_counts: Simplices by dimension (``{}`` or ``{"total": N}`` when the
            backend does not expose a per-dimension breakdown, e.g. ripser).
        diagram_cardinality: Finite (birth, death) pairs by homology dimension.
        diagram_cardinality_infinite: Infinite pairs by homology dimension.
        peak_rss_bytes: Peak resident set size in bytes (``None`` if unavailable).
        w2_pair_count: Number of W2 distances contributing to this cell's aggregation.
        w2_total_wall_s: Total wall seconds spent in W2 aggregation.
        w2_per_pair_wall_s: ``w2_total_wall_s / w2_pair_count`` (``None`` if no pairs).
        extra: Free-form provenance (seed, epsilon, landmark policy, ...).
    """

    method: str
    dataset: str
    n_points: int
    n_landmarks: int
    n_dims: int
    max_edge_length: float | None
    backend: str
    backend_version: str
    complex_construction_wall_s: float
    ph_wall_s: float
    simplex_counts: dict[str, int] = field(default_factory=dict)
    diagram_cardinality: dict[int, int] = field(default_factory=dict)
    diagram_cardinality_infinite: dict[int, int] = field(default_factory=dict)
    peak_rss_bytes: int | None = None
    w2_pair_count: int = 0
    w2_total_wall_s: float = 0.0
    w2_per_pair_wall_s: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.w2_per_pair_wall_s is None and self.w2_pair_count > 0:
            self.w2_per_pair_wall_s = self.w2_total_wall_s / self.w2_pair_count

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable dict with string keys (dims cast to str)."""
        d = asdict(self)
        d["simplex_counts"] = {str(k): int(v) for k, v in self.simplex_counts.items()}
        d["diagram_cardinality"] = {str(k): int(v) for k, v in self.diagram_cardinality.items()}
        d["diagram_cardinality_infinite"] = {
            str(k): int(v) for k, v in self.diagram_cardinality_infinite.items()
        }
        return d


def profile_from_diagrams(
    method: str,
    dataset: str,
    points: NDArray[np.float64],
    dgms: Mapping[int, NDArray[np.float64]],
    *,
    backend: str,
    n_landmarks: int | None = None,
    max_edge_length: float | None = None,
    complex_construction_wall_s: float = 0.0,
    ph_wall_s: float = 0.0,
    simplex_counts: Mapping[str, int] | None = None,
    peak_rss: int | None = None,
    w2_pair_count: int = 0,
    w2_total_wall_s: float = 0.0,
    extra: Mapping[str, Any] | None = None,
) -> ComputeProfile:
    """Assemble a :class:`ComputeProfile` from a computed diagram + timings.

    Convenience constructor: derives ``n_points``/``n_dims`` from ``points`` and the
    diagram cardinalities from ``dgms`` so callers pass only the measured timings.
    """
    pts = np.asarray(points, dtype=np.float64).reshape(len(points), -1) if len(points) else np.empty((0, 0))
    finite, infinite = diagram_cardinalities(dgms)
    return ComputeProfile(
        method=method,
        dataset=dataset,
        n_points=int(pts.shape[0]),
        n_landmarks=int(n_landmarks if n_landmarks is not None else pts.shape[0]),
        n_dims=int(pts.shape[1]) if pts.ndim == 2 else 0,
        max_edge_length=None if max_edge_length is None else float(max_edge_length),
        backend=backend,
        backend_version=backend_version(backend),
        complex_construction_wall_s=float(complex_construction_wall_s),
        ph_wall_s=float(ph_wall_s),
        simplex_counts=dict(simplex_counts or {}),
        diagram_cardinality=finite,
        diagram_cardinality_infinite=infinite,
        peak_rss_bytes=peak_rss,
        w2_pair_count=int(w2_pair_count),
        w2_total_wall_s=float(w2_total_wall_s),
        extra=dict(extra or {}),
    )
