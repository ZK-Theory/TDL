"""Zigzag persistence for temporal topology tracking.

Paper 3: Track how the topological structure of the UK trajectory space
evolves across economic cycles (1991–2023). Zigzag persistence (Carlsson
& de Silva 2010) computes persistence across a sequence of point clouds,
tracking which features appear and disappear as the data is partitioned
by calendar year.

Research question: Does the number of distinct trajectory clusters (H₀)
increase during recessions, indicating fragmentation? Do loops (H₁)
appear during recovery periods?

Economic regimes in the BHPS/USoc panel (1991–2023):
    - 1993: UK recession (ERM exit)
    - 1997–2007: Post-Black Wednesday expansion
    - 2008–2009: Global Financial Crisis
    - 2010–2015: Post-crisis austerity contraction
    - 2020: COVID-19 shock

Implementation note: Full zigzag uses Gudhi's zigzag implementation.
The streaming algorithm (Kerber & Schreiber 2017) provides space complexity
independent of tower length — critical for 30+ annual snapshots.

References:
    Carlsson, G., & de Silva, V. (2010). Zigzag persistence. Foundations
    of Computational Mathematics.

    Kerber, M., & Schreiber, H. (2017). Barcodes of towers and a
    streaming algorithm for persistent homology. SoCG 2017.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
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


def run_gudhi_zigzag(
    snapshots: list[AnnualSnapshot],
    homology_dim: int = 1,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Run Gudhi's zigzag persistence on the sequence of annual diagrams.

    Tracks which topological features persist across the sequence of
    annual point cloud inclusions/exclusions. This is more informative
    than comparing annual diagrams independently — it identifies features
    that are born during recessions and die during recoveries.

    Uses the streaming algorithm for memory efficiency.

    Args:
        snapshots: Ordered list of AnnualSnapshot objects.
        homology_dim: Maximum homology dimension to compute.

    Returns:
        Tuple of (zigzag_h0_diagram, zigzag_h1_diagram) as (birth_year,
        death_year) arrays. Birth/death here refers to calendar years,
        not filtration values.

    Raises:
        ImportError: If gudhi is not installed or lacks zigzag support.
        NotImplementedError: If gudhi zigzag bindings are not available
            (gudhi >= 3.7 required).
    """
    try:
        import gudhi

        if not hasattr(gudhi, "RipsComplex"):
            raise ImportError("gudhi >= 3.7 required for zigzag support")

    except ImportError as e:
        raise ImportError(
            "gudhi is required for zigzag persistence. " "Install with: pip install gudhi (version >= 3.7)"
        ) from e

    logger.info("Running gudhi zigzag persistence on %d annual snapshots...", len(snapshots))
    logger.warning(
        "Full zigzag computation is hours-scale. "
        "Use create_annual_snapshots() independently for the scalar time series."
    )

    # Placeholder: gudhi zigzag API is version-specific.
    # This scaffold is ready for integration once the data pipeline is complete.
    # See: https://gudhi.inria.fr/python/latest/zigzag_persistence_user.html
    raise NotImplementedError(
        "Gudhi zigzag integration requires the data pipeline to be complete "
        "(frozen PCA embeddings per year). Implement after trajectory_tda/data/ "
        "module is built. The create_annual_snapshots() function is ready to use."
    )


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
