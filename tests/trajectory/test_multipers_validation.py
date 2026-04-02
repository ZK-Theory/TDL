"""Validate multipers library on synthetic bifiltrations.

Tests that multipers can:
1. Construct a 2-parameter simplex tree via RipsLowerstar
2. Compute signed measures for H0 and H1
3. Detect known topological structure (circle vs blob)
4. Handle the bifiltration construction pattern P04 will use

These tests do NOT require real data — they use synthetic point clouds
with known topology.
"""

from __future__ import annotations

import warnings

import numpy as np
import pytest

# Gate the entire module on multipers availability
mp = pytest.importorskip("multipers", reason="multipers not installed")


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────


def _make_circle_blob(
    n_circle: int = 60,
    n_blob: int = 60,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate a circle (has H1) at low income + a blob (no H1) at high income.

    Returns:
        points: (n_circle + n_blob, 2) point cloud.
        income: (n_circle + n_blob,) per-point scalar function.
    """
    rng = np.random.RandomState(seed)

    # Circle: radius ~1, centered at origin
    theta = rng.uniform(0, 2 * np.pi, n_circle)
    r = 1.0 + rng.normal(0, 0.08, n_circle)
    pts_circle = np.column_stack([r * np.cos(theta), r * np.sin(theta)])
    income_low = rng.uniform(0.10, 0.35, n_circle)

    # Blob: Gaussian cloud, centered far from circle
    pts_blob = rng.normal(5, 0.3, (n_blob, 2))
    income_high = rng.uniform(0.65, 1.0, n_blob)

    points = np.vstack([pts_circle, pts_blob])
    income = np.concatenate([income_low, income_high])
    return points, income


def _suppress_keops_warnings():
    """Suppress KeOps C++ compiler warnings on Windows."""
    warnings.filterwarnings("ignore", message=".*KeOps.*")
    warnings.filterwarnings("ignore", message=".*pykeops.*")


# ──────────────────────────────────────────────────────────────────────
# 1. SimplexTree construction
# ──────────────────────────────────────────────────────────────────────


class TestBifiltrationConstruction:
    """Verify RipsLowerstar produces a valid 2-parameter simplex tree."""

    def setup_method(self):
        _suppress_keops_warnings()

    def test_simplex_tree_created(self):
        """RipsLowerstar returns a SimplexTreeMulti object."""
        from multipers.filtrations import RipsLowerstar

        pts, income = _make_circle_blob(n_circle=30, n_blob=30)
        st = RipsLowerstar(
            points=pts,
            function=income.reshape(-1, 1),
            threshold_radius=3.0,
        )
        assert st is not None
        assert st.num_parameters == 2  # noqa: PLR2004

    def test_simplex_count_positive(self):
        """The bifiltration contains simplices."""
        from multipers.filtrations import RipsLowerstar

        pts, income = _make_circle_blob(n_circle=30, n_blob=30)
        st = RipsLowerstar(
            points=pts,
            function=income.reshape(-1, 1),
            threshold_radius=3.0,
        )
        assert st.num_simplices > 60  # At least #vertices worth

    def test_two_parameters(self):
        """The simplex tree has exactly 2 filtration parameters."""
        from multipers.filtrations import RipsLowerstar

        pts, income = _make_circle_blob(n_circle=20, n_blob=20)
        st = RipsLowerstar(
            points=pts,
            function=income.reshape(-1, 1),
            threshold_radius=2.0,
        )
        assert st.num_parameters == 2  # noqa: PLR2004

    def test_higher_dimension_points(self):
        """RipsLowerstar works with 20D points (like P01 embedding)."""
        from multipers.filtrations import RipsLowerstar

        rng = np.random.RandomState(42)
        pts = rng.randn(50, 20)  # 20D like P01 PCA embedding
        income = rng.uniform(0, 1, 50)
        st = RipsLowerstar(
            points=pts,
            function=income.reshape(-1, 1),
            threshold_radius=5.0,
        )
        assert st.num_parameters == 2  # noqa: PLR2004
        assert st.num_simplices > 50


# ──────────────────────────────────────────────────────────────────────
# 2. Signed measure computation
# ──────────────────────────────────────────────────────────────────────


class TestSignedMeasure:
    """Verify signed_measure computes for H0 and H1."""

    def setup_method(self):
        _suppress_keops_warnings()

    @pytest.fixture()
    def bifiltration(self):
        from multipers.filtrations import RipsLowerstar

        pts, income = _make_circle_blob(n_circle=50, n_blob=50)
        return RipsLowerstar(
            points=pts,
            function=income.reshape(-1, 1),
            threshold_radius=3.0,
        )

    def test_h0_signed_measure(self, bifiltration):
        """H0 signed measure is computable and non-empty."""
        sm = mp.signed_measure(
            bifiltration, degree=0, grid_strategy="regular", resolution=10
        )
        pts_sm, weights_sm = sm[0]
        assert len(pts_sm) > 0
        assert len(weights_sm) > 0
        assert pts_sm.shape[1] == 2  # noqa: PLR2004  # 2 filtration parameters

    def test_h1_signed_measure(self, bifiltration):
        """H1 signed measure is computable and non-empty."""
        sm = mp.signed_measure(
            bifiltration, degree=1, grid_strategy="regular", resolution=10
        )
        pts_sm, weights_sm = sm[0]
        assert len(pts_sm) > 0
        assert len(weights_sm) > 0

    def test_signed_measure_weights_are_integers(self, bifiltration):
        """Signed measure weights should be integer-valued (multiplicities)."""
        sm = mp.signed_measure(
            bifiltration, degree=0, grid_strategy="regular", resolution=10
        )
        _, weights_sm = sm[0]
        # Weights are signed integers (positive = birth, negative = death)
        np.testing.assert_array_equal(weights_sm, np.round(weights_sm))


# ──────────────────────────────────────────────────────────────────────
# 3. Topological detection on known structure
# ──────────────────────────────────────────────────────────────────────


class TestTopologicalDetection:
    """Verify multipers detects known topology in synthetic bifiltration."""

    def setup_method(self):
        _suppress_keops_warnings()

    def test_circle_has_h1_features(self):
        """A circle-only point cloud should produce H1 signed measure mass."""
        from multipers.filtrations import RipsLowerstar

        rng = np.random.RandomState(42)
        theta = rng.uniform(0, 2 * np.pi, 60)
        r = 1.0 + rng.normal(0, 0.05, 60)
        pts = np.column_stack([r * np.cos(theta), r * np.sin(theta)])
        income = rng.uniform(0.1, 0.5, 60)  # All low income

        st = RipsLowerstar(
            points=pts,
            function=income.reshape(-1, 1),
            threshold_radius=2.0,
        )
        sm = mp.signed_measure(st, degree=1, grid_strategy="regular", resolution=10)
        _, weights = sm[0]
        total_h1_mass = np.sum(np.abs(weights))
        assert total_h1_mass > 0, "Circle should produce H1 features"

    def test_blob_has_no_h1_at_tight_radius(self):
        """A Gaussian blob at very tight Rips radius should have few/no H1 features."""
        from multipers.filtrations import RipsLowerstar

        rng = np.random.RandomState(42)
        pts = rng.normal(0, 0.2, (40, 2))
        income = rng.uniform(0.5, 1.0, 40)

        st = RipsLowerstar(
            points=pts,
            function=income.reshape(-1, 1),
            threshold_radius=0.05,  # Very tight — only nearest neighbours
        )
        sm = mp.signed_measure(st, degree=1, grid_strategy="regular", resolution=10)
        _, weights = sm[0]
        total_h1_mass = np.sum(np.abs(weights))
        # At radius 0.05, few edges form so H1 should be zero or trivial
        assert total_h1_mass < 10, (
            f"Blob at tight radius should have <10 H1 mass (got {total_h1_mass})"
        )

    def test_h0_detects_two_components(self):
        """Two well-separated clusters should produce H0 features."""
        from multipers.filtrations import RipsLowerstar

        rng = np.random.RandomState(42)
        pts1 = rng.normal(0, 0.2, (30, 2))
        pts2 = rng.normal(10, 0.2, (30, 2))
        pts = np.vstack([pts1, pts2])
        income = rng.uniform(0, 1, 60)

        st = RipsLowerstar(
            points=pts,
            function=income.reshape(-1, 1),
            threshold_radius=1.0,
        )
        sm = mp.signed_measure(st, degree=0, grid_strategy="regular", resolution=10)
        _, weights = sm[0]
        total_h0_mass = np.sum(np.abs(weights))
        assert total_h0_mass > 0, "Two clusters should produce H0 features"


# ──────────────────────────────────────────────────────────────────────
# 4. P04 bifiltration pattern: Rips × income threshold
# ──────────────────────────────────────────────────────────────────────


class TestP04BifiltrationPattern:
    """Test the exact bifiltration pattern P04 will use on trajectory data."""

    def setup_method(self):
        _suppress_keops_warnings()

    def test_20d_embedding_with_income(self):
        """Simulate P01 embedding (20D) + income scalar → bifiltration → signed measure."""
        from multipers.filtrations import RipsLowerstar

        rng = np.random.RandomState(42)

        # Simulate two trajectory regimes in 20D
        n_per = 40
        pts_poor = rng.randn(n_per, 20) * 0.5  # Tight cluster
        pts_rich = rng.randn(n_per, 20) * 0.5 + 3.0  # Shifted cluster

        points = np.vstack([pts_poor, pts_rich])
        income = np.concatenate(
            [
                rng.uniform(0.1, 0.4, n_per),  # Low income
                rng.uniform(0.6, 1.0, n_per),  # High income
            ]
        )

        st = RipsLowerstar(
            points=points,
            function=income.reshape(-1, 1),
            threshold_radius=5.0,
        )

        assert st.num_parameters == 2  # noqa: PLR2004

        # H0 signed measure should work
        sm_h0 = mp.signed_measure(st, degree=0, grid_strategy="regular", resolution=10)
        pts_h0, weights_h0 = sm_h0[0]
        assert len(pts_h0) > 0

    def test_income_permutation_produces_different_result(self):
        """Shuffling income labels changes the signed measure.

        This validates the permutation test design for P04.
        """
        from multipers.filtrations import RipsLowerstar

        rng = np.random.RandomState(42)
        pts, income = _make_circle_blob(n_circle=40, n_blob=40)

        # Original bifiltration
        st_orig = RipsLowerstar(
            points=pts,
            function=income.reshape(-1, 1),
            threshold_radius=3.0,
        )
        sm_orig = mp.signed_measure(
            st_orig, degree=0, grid_strategy="regular", resolution=8
        )
        pts_orig, w_orig = sm_orig[0]

        # Permuted income
        income_perm = rng.permutation(income)
        st_perm = RipsLowerstar(
            points=pts,
            function=income_perm.reshape(-1, 1),
            threshold_radius=3.0,
        )
        sm_perm = mp.signed_measure(
            st_perm, degree=0, grid_strategy="regular", resolution=8
        )
        pts_perm, w_perm = sm_perm[0]

        # The two signed measures should differ (different (ε,τ) grids or weights)
        if len(pts_orig) == len(pts_perm):
            differ = not (
                np.allclose(pts_orig, pts_perm) and np.allclose(w_orig, w_perm)
            )
        else:
            differ = True
        assert differ, "Permuting income should change the signed measure"

    def test_landmark_subsampling_compatible(self):
        """Maxmin landmarking + bifiltration works (simulating P04 landmark strategy)."""
        from multipers.filtrations import RipsLowerstar

        rng = np.random.RandomState(42)
        # Full cloud: 200 points in 20D
        pts_full = rng.randn(200, 20)
        income_full = rng.uniform(0, 1, 200)

        # Maxmin subsampling (simplified: just random subset for this test)
        landmark_idx = rng.choice(200, size=50, replace=False)
        pts_sub = pts_full[landmark_idx]
        income_sub = income_full[landmark_idx]

        st = RipsLowerstar(
            points=pts_sub,
            function=income_sub.reshape(-1, 1),
            threshold_radius=5.0,
        )

        sm = mp.signed_measure(st, degree=0, grid_strategy="regular", resolution=8)
        pts_sm, weights_sm = sm[0]
        assert len(pts_sm) > 0, (
            "Landmark subsampled bifiltration should produce signed measure"
        )
