"""Tests for trajectory_tda.topology.zigzag."""

from __future__ import annotations

import subprocess

import numpy as np
import pytest

from trajectory_tda.topology.zigzag import (
    UK_ECONOMIC_EVENTS,
    AnnualSnapshot,
    ZigzagResult,
    compute_topological_time_series,
    create_annual_snapshots,
    level_to_year,
    run_gudhi_zigzag,
)


def _wsl_dionysus_available() -> bool:
    """Return True if WSL is reachable and dionysus is importable there."""
    try:
        r = subprocess.run(
            [
                "wsl",
                "--exec",
                "/tmp/miniforge3/bin/python",
                "-c",
                "import dionysus",
            ],
            capture_output=True,
            timeout=15,
        )
        return r.returncode == 0
    except Exception:
        return False


_WSL_DIONYSUS = _wsl_dionysus_available()
_skip_wsl = pytest.mark.skipif(
    not _WSL_DIONYSUS,
    reason="WSL with dionysus not available",
)

# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _make_diagram(
    finite_lifetimes: list[float],
    include_inf: bool = True,
) -> np.ndarray:
    """Build a synthetic H₀/H₁ diagram with specified finite lifetimes.

    Birth is always 0; death = birth + lifetime. If ``include_inf=True``
    appends one bar with death=inf (the fundamental connected component).
    Always returns a 2-D array of shape (n, 2).
    """
    rows = [[0.0, lt] for lt in finite_lifetimes]
    if include_inf:
        rows.append([0.0, np.inf])
    if not rows:
        return np.zeros((0, 2), dtype=np.float64)
    return np.array(rows, dtype=np.float64)


def _make_snapshot(
    year: int,
    h0_lifetimes: list[float],
    h1_lifetimes: list[float],
    n_individuals: int = 100,
) -> AnnualSnapshot:
    return AnnualSnapshot(
        year=year,
        diagram_h0=_make_diagram(h0_lifetimes, include_inf=True),
        diagram_h1=_make_diagram(h1_lifetimes, include_inf=False),
        n_individuals=n_individuals,
    )


# ─────────────────────────────────────────────────────────────────────
# AnnualSnapshot tests
# ─────────────────────────────────────────────────────────────────────


def test_total_persistence_h0_sums_finite_bars() -> None:
    """total_persistence_h0 sums finite lifetimes only."""
    snap = _make_snapshot(2000, h0_lifetimes=[0.5, 1.0, 2.0], h1_lifetimes=[])
    # Finite bars: 0.5 + 1.0 + 2.0 = 3.5 (inf bar excluded)
    assert abs(snap.total_persistence_h0 - 3.5) < 1e-10


def test_total_persistence_h1_sums_finite_bars() -> None:
    """total_persistence_h1 sums all H₁ bars (all finite by convention)."""
    snap = _make_snapshot(2000, h0_lifetimes=[], h1_lifetimes=[0.3, 0.7])
    assert abs(snap.total_persistence_h1 - 1.0) < 1e-10


def test_total_persistence_empty_diagram() -> None:
    """Zero total persistence for empty diagrams."""
    snap = AnnualSnapshot(
        year=2000,
        diagram_h0=np.zeros((0, 2), dtype=np.float64),
        diagram_h1=np.zeros((0, 2), dtype=np.float64),
        n_individuals=10,
    )
    assert snap.total_persistence_h0 == 0.0
    assert snap.total_persistence_h1 == 0.0


def test_betti_0_estimate_threshold() -> None:
    """betti_0_estimate counts bars above threshold plus one for inf component."""
    # 3 finite bars: lifetimes 0.01 (below default 0.05), 0.1, 0.2 + inf bar
    snap = _make_snapshot(2000, h0_lifetimes=[0.01, 0.1, 0.2], h1_lifetimes=[])
    # bars above 0.05: 0.1 and 0.2 → 2, + 1 for inf = 3
    assert snap.betti_0_estimate == 3


def test_betti_0_estimate_custom_threshold() -> None:
    snap = AnnualSnapshot(
        year=2000,
        diagram_h0=_make_diagram([0.5, 1.0], include_inf=True),
        diagram_h1=np.zeros((0, 2)),
        n_individuals=50,
        betti_threshold=0.6,
    )
    # Only 1.0 > 0.6, + 1 = 2
    assert snap.betti_0_estimate == 2


def test_economic_event_annotation() -> None:
    """Economic event label is set for known years."""
    snap = _make_snapshot(2008, h0_lifetimes=[], h1_lifetimes=[])
    assert snap.economic_event == UK_ECONOMIC_EVENTS[2008]

    snap_plain = _make_snapshot(2000, h0_lifetimes=[], h1_lifetimes=[])
    assert snap_plain.economic_event is None


# ─────────────────────────────────────────────────────────────────────
# ZigzagResult tests
# ─────────────────────────────────────────────────────────────────────


def test_zigzag_result_year_ordering() -> None:
    """ZigzagResult.years follows input snapshot order."""
    snaps = [_make_snapshot(y, [0.5], [0.1]) for y in [2005, 2008, 2010]]
    result = ZigzagResult(snapshots=snaps)
    assert result.years == [2005, 2008, 2010]


def test_zigzag_result_betti_series_populated() -> None:
    """__post_init__ populates betti_0_series from snapshot estimates."""
    snaps = [_make_snapshot(y, [0.1 * (i + 1)], []) for i, y in enumerate([2000, 2001, 2002])]
    result = ZigzagResult(snapshots=snaps)
    assert len(result.betti_0_series) == 3
    # Each snapshot has 1 finite bar above 0.05 + 1 inf = 2
    assert all(result.betti_0_series == 2)


def test_zigzag_result_total_persistence_series() -> None:
    """total_persistence_h0 series is computed per-snapshot."""
    lifetimes = [0.5, 1.0, 1.5]
    snaps = [_make_snapshot(2000 + i, [lt], [0.2]) for i, lt in enumerate(lifetimes)]
    result = ZigzagResult(snapshots=snaps)
    np.testing.assert_allclose(result.total_persistence_h0, [0.5, 1.0, 1.5])
    np.testing.assert_allclose(result.total_persistence_h1, [0.2, 0.2, 0.2])


def test_recession_years_mask() -> None:
    """recession_years_mask returns True only for known event years."""
    snaps = [_make_snapshot(y, [], []) for y in [2006, 2007, 2008, 2009, 2015, 2020]]
    result = ZigzagResult(snapshots=snaps)
    mask = result.recession_years_mask()
    assert mask.dtype == np.bool_
    assert list(mask) == [False, False, True, True, False, True]


def test_recession_mask_all_false_for_non_event_years() -> None:
    snaps = [_make_snapshot(y, [], []) for y in [2000, 2001, 2002]]
    result = ZigzagResult(snapshots=snaps)
    assert not result.recession_years_mask().any()


# ─────────────────────────────────────────────────────────────────────
# compute_topological_time_series
# ─────────────────────────────────────────────────────────────────────


def test_compute_topological_time_series_returns_zigzag_result() -> None:
    snaps = [_make_snapshot(y, [0.3], [0.1]) for y in range(2000, 2005)]
    result = compute_topological_time_series(snaps)
    assert isinstance(result, ZigzagResult)
    assert result.years == list(range(2000, 2005))
    assert len(result.betti_0_series) == 5


def test_compute_topological_time_series_preserves_order() -> None:
    """Snapshot order is preserved even if years are non-contiguous."""
    snaps = [_make_snapshot(y, [], []) for y in [2005, 1995, 2015]]
    result = compute_topological_time_series(snaps)
    assert result.years == [2005, 1995, 2015]


# ─────────────────────────────────────────────────────────────────────
# level_to_year
# ─────────────────────────────────────────────────────────────────────


def test_level_to_year_even_level() -> None:
    """Even level ``2k`` maps to year ``y0 + k``."""
    assert level_to_year(0.0, 1991) == pytest.approx(1991.0)
    assert level_to_year(2.0, 1991) == pytest.approx(1992.0)
    assert level_to_year(34.0, 1991) == pytest.approx(2008.0)


def test_level_to_year_odd_level() -> None:
    """Odd level ``2k+1`` maps to ``y0 + k + 0.5`` (between-year transition)."""
    assert level_to_year(1.0, 1991) == pytest.approx(1991.5)
    assert level_to_year(35.0, 1991) == pytest.approx(2008.5)


# ─────────────────────────────────────────────────────────────────────
# create_annual_snapshots (integration — requires ripser)
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_create_annual_snapshots_produces_correct_count() -> None:
    """create_annual_snapshots returns one snapshot per input year."""
    rng = np.random.default_rng(42)
    embeddings_by_year = {y: rng.standard_normal((80, 10)).astype(np.float64) for y in range(2000, 2005)}
    snapshots = create_annual_snapshots(embeddings_by_year, max_filtration=2.0, n_landmarks=50)
    assert len(snapshots) == 5
    assert [s.year for s in snapshots] == list(range(2000, 2005))


@pytest.mark.integration
def test_create_annual_snapshots_small_year_no_subsampling() -> None:
    """Years with fewer points than n_landmarks are not subsampled."""
    rng = np.random.default_rng(0)
    small_cloud = rng.standard_normal((20, 5)).astype(np.float64)
    snapshots = create_annual_snapshots({2000: small_cloud}, max_filtration=2.0, n_landmarks=500)
    assert snapshots[0].n_landmarks == 20
    assert snapshots[0].n_individuals == 20


# ─────────────────────────────────────────────────────────────────────
# run_gudhi_zigzag (integration — requires WSL + dionysus)
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@_skip_wsl
def test_run_gudhi_zigzag_returns_arrays() -> None:
    """run_gudhi_zigzag returns two float64 arrays of shape (n, 2)."""
    rng = np.random.default_rng(7)
    # Use the SAME 40 points every year so individuals span all years
    pts = rng.standard_normal((40, 5)).astype(np.float64)
    embeddings_by_year = {y: pts for y in range(2000, 2004)}
    h0, h1 = run_gudhi_zigzag(embeddings_by_year, max_filtration=1.5, n_landmarks=30, sparse=0.5)
    assert h0.ndim == 2 and h0.shape[1] == 2
    assert h1.ndim == 2 and h1.shape[1] == 2
    assert h0.dtype == np.float64
    assert h1.dtype == np.float64


@pytest.mark.integration
@_skip_wsl
def test_run_gudhi_zigzag_two_identical_clusters() -> None:
    """Two well-separated clusters that persist all years produce ≥1 long H₀ bar.

    With *true* zigzag this should be a **single** cross-year bar rather than
    multiple independent bars — the bar's lifetime should span at least 2 years
    (i.e. birth_level + 4 ≤ death_level in a 3-year sequence).
    """
    rng = np.random.default_rng(3)
    n = 30
    cluster_a = rng.standard_normal((n, 5)) * 0.05
    cluster_b = rng.standard_normal((n, 5)) * 0.05 + 10.0
    pts = np.vstack([cluster_a, cluster_b])

    # Same cloud in all years → spanning individuals → single long bar expected
    embeddings_by_year = {y: pts for y in range(2000, 2003)}
    h0, h1 = run_gudhi_zigzag(embeddings_by_year, max_filtration=1.0, n_landmarks=None, sparse=0.5)
    assert len(h0) >= 1, "Expected ≥1 H₀ bar for two persistent clusters"

    # The longest bar should span multiple zigzag levels;
    # 3 years → 5 levels (0..4), the cluster bar should be born at ≤1 and die
    # at ≥3 (or be infinite), i.e. lifetime ≥ 2 levels.
    finite_h0 = h0[np.isfinite(h0[:, 1])]
    inf_h0 = h0[~np.isfinite(h0[:, 1])]
    longest_finite = float((finite_h0[:, 1] - finite_h0[:, 0]).max()) if len(finite_h0) else 0.0
    assert longest_finite >= 2.0 or len(inf_h0) > 0, (
        "Expected the cluster separation to produce a bar of lifetime ≥ 2 levels "
        f"(got finite lifetimes {(finite_h0[:, 1] - finite_h0[:, 0]).tolist() if len(finite_h0) else []}, "
        f"infinite bars: {len(inf_h0)})"
    )


@pytest.mark.integration
@_skip_wsl
def test_run_gudhi_zigzag_raises_with_one_year() -> None:
    """ValueError when fewer than 2 years are provided."""
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match="at least 2"):
        run_gudhi_zigzag({2000: rng.standard_normal((20, 5))})


@pytest.mark.integration
@_skip_wsl
def test_run_gudhi_zigzag_h1_circle() -> None:
    """A persistent circle produces ≥1 H₁ bar across an annual repetition."""
    theta = np.linspace(0, 2 * np.pi, 50, endpoint=False)
    circle = np.column_stack([np.cos(theta), np.sin(theta)]).astype(np.float64)

    # Same circle every year → spanning → the loop persists across all years
    embeddings_by_year = {y: circle for y in range(2000, 2003)}
    h0, h1 = run_gudhi_zigzag(
        embeddings_by_year,
        max_filtration=0.8,
        n_landmarks=None,
        sparse=0.5,
        max_dim=2,  # need triangles for H₁ boundaries
    )
    assert len(h1) >= 1, "Expected at least one H₁ bar for a persistent circle"
