"""
Shared pytest fixtures and validation helpers for TDA testing.

This module provides:
- Synthetic data fixtures for reproducible testing
- Mathematical validation helpers for topological computations
- Numerical tolerance constants for floating-point comparisons
"""

import numpy as np
import pytest

# ============================================================================
# NUMERICAL TOLERANCE CONSTANTS
# ============================================================================

# Floating-point comparison tolerance for general numerical checks
FLOAT_TOLERANCE = 1e-10

# Betti number comparison tolerance (10% per Gidea & Katz checkpoint)
# Used when comparing computed Betti curves to expected values
BETTI_TOLERANCE = 0.1


# ============================================================================
# DATA GENERATION FIXTURES
# ============================================================================


@pytest.fixture
def sample_time_series() -> dict:
    """
    Generate synthetic time series for testing TDA computations.

    Returns:
        Dictionary with different time series types:
        - 'sine': Pure sine wave (period=2π, length=100)
        - 'random_walk': Cumulative sum of random steps (length=100)
        - 'noisy_sine': Sine wave with Gaussian noise (SNR~10)
    """
    np.random.seed(42)  # Reproducibility
    t = np.linspace(0, 4 * np.pi, 100)

    return {
        "sine": np.sin(t),
        "random_walk": np.cumsum(np.random.randn(100)),
        "noisy_sine": np.sin(t) + 0.1 * np.random.randn(100),
    }


@pytest.fixture
def sample_point_cloud() -> dict:
    """
    Generate simple geometric point clouds with known topology.

    Returns:
        Dictionary with different point cloud types:
        - 'circle': Points sampled from unit circle (H0=1, H1=1)
        - 'torus': Points sampled from torus surface (H0=1, H1=2, H2=1)
        - 'two_circles': Two separate circles (H0=2, H1=2)
    """
    np.random.seed(42)  # Reproducibility
    n_points = 100

    # Circle: parametric sampling from S^1
    theta = np.linspace(0, 2 * np.pi, n_points)
    circle = np.column_stack([np.cos(theta), np.sin(theta)])

    # Torus: parametric sampling from S^1 × S^1
    u = np.random.uniform(0, 2 * np.pi, n_points)
    v = np.random.uniform(0, 2 * np.pi, n_points)
    R, r = 2.0, 1.0  # Major and minor radii
    torus = np.column_stack(
        [
            (R + r * np.cos(v)) * np.cos(u),
            (R + r * np.cos(v)) * np.sin(u),
            r * np.sin(v),
        ]
    )

    # Two circles: offset horizontally
    circle2 = circle + np.array([3, 0])
    two_circles = np.vstack([circle, circle2])

    return {
        "circle": circle,
        "torus": torus,
        "two_circles": two_circles,
    }


# ============================================================================
# MATHEMATICAL VALIDATION HELPERS
# ============================================================================


def assert_persistence_diagram_valid(diagram: np.ndarray) -> None:
    """
    Validate persistence diagram format and mathematical constraints.

    A valid persistence diagram must satisfy:
    1. Shape: (n_features, 2) array
    2. Birth ≤ Death for all features
    3. All values are finite (no NaN/Inf)

    Args:
        diagram: Persistence diagram as (n_features, 2) array
                 where each row is [birth, death]

    Raises:
        AssertionError: If any validation check fails
    """
    assert diagram.ndim == 2, f"Diagram must be 2D array, got shape {diagram.shape}"
    assert diagram.shape[1] == 2, (
        f"Diagram must have 2 columns [birth, death], got {diagram.shape[1]}"
    )

    # Check birth ≤ death
    births, deaths = diagram[:, 0], diagram[:, 1]
    invalid_features = births > deaths
    assert not np.any(invalid_features), (
        f"Found {np.sum(invalid_features)} features with birth > death"
    )

    # Check for NaN/Inf
    assert np.all(np.isfinite(diagram)), "Diagram contains NaN or Inf values"


def assert_betti_numbers_match(
    computed: np.ndarray, expected: np.ndarray, tolerance: float = BETTI_TOLERANCE
) -> None:
    """
    Compare computed Betti numbers/curves to expected values.

    Uses relative tolerance for comparison to account for numerical
    variations and different implementations. Default 10% tolerance
    follows Gidea & Katz (2018) validation methodology.

    Args:
        computed: Computed Betti numbers (can be single values or curves)
        expected: Expected Betti numbers (same shape as computed)
        tolerance: Relative tolerance for comparison (default: 0.1 = 10%)

    Raises:
        AssertionError: If computed and expected differ by more than tolerance
    """
    computed = np.asarray(computed)
    expected = np.asarray(expected)

    assert computed.shape == expected.shape, (
        f"Shape mismatch: computed {computed.shape} vs expected {expected.shape}"
    )

    # For exact zeros in expected, use absolute tolerance
    zero_mask = expected == 0
    if np.any(zero_mask):
        assert np.allclose(computed[zero_mask], 0, atol=FLOAT_TOLERANCE), (
            "Computed values differ from expected zeros"
        )

    # For non-zero values, use relative tolerance
    nonzero_mask = ~zero_mask
    if np.any(nonzero_mask):
        relative_error = np.abs(
            (computed[nonzero_mask] - expected[nonzero_mask]) / expected[nonzero_mask]
        )
        max_error = np.max(relative_error)
        assert max_error <= tolerance, (
            f"Betti numbers exceed tolerance: "
            f"max relative error = {max_error:.3f} > {tolerance}"
        )


def assert_bottleneck_distance_within(
    diagram1: np.ndarray, diagram2: np.ndarray, threshold: float
) -> None:
    """
    Verify bottleneck distance between two persistence diagrams is within threshold.

    The bottleneck distance is the infimum over all bijections between
    features of the maximum distance between matched features. This is
    useful for validating stability of persistence computations.

    Note: This is a simplified implementation. For production use,
    prefer gudhi.bottleneck_distance or gtda.diagrams.BinaryDistance.

    Args:
        diagram1: First persistence diagram (n1, 2)
        diagram2: Second persistence diagram (n2, 2)
        threshold: Maximum allowed bottleneck distance

    Raises:
        AssertionError: If bottleneck distance exceeds threshold
    """
    try:
        from gudhi.wasserstein import wasserstein_distance

        # Use Wasserstein-∞ (bottleneck) distance
        distance = wasserstein_distance(diagram1, diagram2, order=np.inf, internal_p=2)

        assert distance <= threshold, (
            f"Bottleneck distance {distance:.6f} exceeds threshold {threshold}"
        )

    except ImportError:
        # Fallback: simplified implementation for testing
        # Compute maximum persistence for both diagrams
        pers1 = np.max(diagram1[:, 1] - diagram1[:, 0]) if len(diagram1) > 0 else 0
        pers2 = np.max(diagram2[:, 1] - diagram2[:, 0]) if len(diagram2) > 0 else 0

        # Rough approximation: if max persistences are similar, diagrams are close
        approx_distance = abs(pers1 - pers2)
        assert approx_distance <= threshold, (
            f"Approximate bottleneck distance {approx_distance:.6f} "
            f"exceeds threshold {threshold}"
        )


# ============================================================================
# EXAMPLE USAGE IN TESTS
# ============================================================================
#
# def test_circle_topology(sample_point_cloud):
#     """Test that circle point cloud has correct Betti numbers."""
#     from gtda.homology import VietorisRipsPersistence
#
#     circle = sample_point_cloud['circle']
#     vr = VietorisRipsPersistence(homology_dimensions=[0, 1])
#     diagram = vr.fit_transform([circle])[0]
#
#     # Validate diagram structure
#     assert_persistence_diagram_valid(diagram)
#
#     # Check expected topology: H0=1, H1=1
#     h0_features = diagram[diagram[:, 2] == 0]
#     h1_features = diagram[diagram[:, 2] == 1]
#
#     assert_betti_numbers_match(
#         computed=[len(h0_features), len(h1_features)],
#         expected=[1, 1],
#         tolerance=0.2  # Allow some variation
#     )
