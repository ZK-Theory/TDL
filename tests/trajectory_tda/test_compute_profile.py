# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: Deterministic unit tests for trajectory_tda.topology.compute_profile
#   (Spike Set B, amendment B7). Pin the PH-vs-W2 cost-split record's behaviour:
#   cardinality counting, W2 per-pair derivation, serialisation, and the peak-RSS /
#   backend-version helpers.
"""Unit tests for the compute-profile instrumentation module."""

from __future__ import annotations

import numpy as np

from trajectory_tda.topology.compute_profile import (
    ComputeProfile,
    backend_version,
    diagram_cardinalities,
    peak_rss_bytes,
    profile_from_diagrams,
    wall_timer,
)


def test_diagram_cardinalities_finite_and_infinite() -> None:
    dgms = {
        0: np.array([[0.0, 1.0], [0.0, np.inf], [0.0, 2.0]]),
        1: np.array([[0.5, 1.5]]),
        2: np.empty((0, 2)),
    }
    finite, infinite = diagram_cardinalities(dgms)
    assert finite == {0: 2, 1: 1, 2: 0}
    assert infinite == {0: 1, 1: 0, 2: 0}


def test_diagram_cardinalities_handles_nan_as_nonfinite() -> None:
    dgms = {0: np.array([[0.0, 1.0], [np.nan, 1.0]])}
    finite, infinite = diagram_cardinalities(dgms)
    assert finite == {0: 1}
    assert infinite == {0: 1}


def test_w2_per_pair_derivation_when_pairs_present() -> None:
    p = ComputeProfile(
        method="vr_ripser",
        dataset="usoc",
        n_points=5000,
        n_landmarks=5000,
        n_dims=20,
        max_edge_length=17.0,
        backend="ripser",
        backend_version="0.6.0",
        complex_construction_wall_s=1.0,
        ph_wall_s=23.0,
        w2_pair_count=100,
        w2_total_wall_s=700.0,
    )
    assert p.w2_per_pair_wall_s == 7.0


def test_w2_per_pair_none_when_no_pairs() -> None:
    p = ComputeProfile(
        method="m",
        dataset="d",
        n_points=10,
        n_landmarks=10,
        n_dims=2,
        max_edge_length=None,
        backend="gudhi",
        backend_version="3.11.0",
        complex_construction_wall_s=0.0,
        ph_wall_s=0.0,
        w2_pair_count=0,
        w2_total_wall_s=0.0,
    )
    assert p.w2_per_pair_wall_s is None


def test_to_dict_stringifies_dimension_keys() -> None:
    p = ComputeProfile(
        method="sparse_rips_eps0.10",
        dataset="usoc",
        n_points=5000,
        n_landmarks=5000,
        n_dims=20,
        max_edge_length=17.0,
        backend="gudhi",
        backend_version="3.11.0",
        complex_construction_wall_s=2.5,
        ph_wall_s=4.0,
        simplex_counts={"0": 5000, "1": 120000, "2": 800000},
        diagram_cardinality={0: 4999, 1: 30},
        diagram_cardinality_infinite={0: 1, 1: 0},
        w2_pair_count=50,
        w2_total_wall_s=350.0,
        extra={"epsilon": 0.10, "seed": 42},
    )
    d = p.to_dict()
    assert d["diagram_cardinality"] == {"0": 4999, "1": 30}
    assert d["diagram_cardinality_infinite"] == {"0": 1, "1": 0}
    assert d["simplex_counts"] == {"0": 5000, "1": 120000, "2": 800000}
    assert d["w2_per_pair_wall_s"] == 7.0
    assert d["extra"]["epsilon"] == 0.10


def test_profile_from_diagrams_derives_shape_and_cardinality() -> None:
    rng = np.random.RandomState(0)
    points = rng.rand(200, 20)
    dgms = {
        0: np.array([[0.0, 1.0], [0.0, np.inf]]),
        1: np.array([[0.3, 0.7], [0.4, 0.9]]),
    }
    prof = profile_from_diagrams(
        "vr_ripser",
        "usoc",
        points,
        dgms,
        backend="ripser",
        max_edge_length=1.0,
        complex_construction_wall_s=0.1,
        ph_wall_s=0.2,
        w2_pair_count=4,
        w2_total_wall_s=8.0,
    )
    assert prof.n_points == 200
    assert prof.n_dims == 20
    assert prof.n_landmarks == 200
    assert prof.diagram_cardinality == {0: 1, 1: 2}
    assert prof.diagram_cardinality_infinite == {0: 1, 1: 0}
    assert prof.w2_per_pair_wall_s == 2.0


def test_peak_rss_bytes_returns_int_or_none() -> None:
    val = peak_rss_bytes()
    assert val is None or (isinstance(val, int) and val > 0)


def test_backend_version_nonempty_string() -> None:
    assert isinstance(backend_version("gudhi"), str)
    assert backend_version("gudhi") != ""
    assert isinstance(backend_version("ripser"), str)


def test_wall_timer_measures_nonnegative() -> None:
    with wall_timer() as t:
        _ = sum(range(10000))
    assert t.elapsed >= 0.0
