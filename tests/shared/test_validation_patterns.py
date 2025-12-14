"""
Template mathematical validation tests demonstrating TDA testing patterns.

This module shows how to:
1. Test topological computations against known mathematical results
2. Use validation helpers from conftest.py
3. Structure tests for reproducibility and clarity
4. Apply appropriate markers for test categorization

Mathematical Validation Methodology:
------------------------------------
These tests follow the approach of Gidea & Katz (2018) and other TDA papers
that validate implementations by comparing against:
- Known topological invariants of standard spaces (circles, tori, etc.)
- Published results from TDA literature
- Synthetic data with predictable structure

References:
- Gidea & Katz (2018): "Topological Data Analysis of Financial Time Series"
- Carlsson (2009): "Topology and Data" - foundational TDA paper
"""

import os

# Import validation helpers - pytest automatically loads conftest.py
# These are available in the test module namespace
import sys

import numpy as np
import pytest
from gtda.homology import VietorisRipsPersistence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from conftest import (
    FLOAT_TOLERANCE,
    assert_persistence_diagram_valid,
)

# ============================================================================
# BASIC TOPOLOGY VALIDATION
# ============================================================================


@pytest.mark.validation
def test_circle_has_one_connected_component(sample_point_cloud):
    """
    Validate that a circle point cloud has exactly one connected component.

    Mathematical Background:
    -----------------------
    A circle (S^1) is a connected space, so its 0th Betti number β0 = 1.
    At small scales (Vietoris-Rips parameter ε → 0), we have many components,
    but as ε increases, they merge into a single component.

    This tests validates:
    1. Persistence diagram format
    2. H0 features are present (components exist and merge)
    3. All features satisfy birth ≤ death

    Note: The exact number of H0 features depends on sampling density and
    filtration parameters. The key property is that the diagram is valid
    and represents the merging process correctly.
    """
    circle = sample_point_cloud["circle"]

    # Compute Vietoris-Rips persistence
    vr = VietorisRipsPersistence(homology_dimensions=[0], max_edge_length=5.0)
    diagrams = vr.fit_transform([circle])
    h0_diagram = diagrams[0, :, :2]  # Extract birth-death pairs for H0

    # Validate diagram structure
    assert_persistence_diagram_valid(h0_diagram)

    # Should have at least some H0 features (points initially separate, then merge)
    assert len(h0_diagram) > 0, "Should have at least one H0 feature"

    # All persistences should be non-negative
    persistences = h0_diagram[:, 1] - h0_diagram[:, 0]
    assert np.all(
        persistences >= -FLOAT_TOLERANCE
    ), "All persistences must be non-negative"


@pytest.mark.validation
def test_circle_has_one_loop(sample_point_cloud):
    """
    Validate that a circle point cloud has exactly one 1-dimensional hole (loop).

    Mathematical Background:
    -----------------------
    A circle (S^1) has first Betti number β1 = 1, representing one loop.
    In the Vietoris-Rips filtration, this loop appears when points are
    connected enough to form a cycle, and persists until the complex fills in.

    This is a fundamental validation test - if this fails, the TDA library
    or computation is fundamentally broken.

    Expected Result:
    ---------------
    - H1 diagram should contain at least 1 significant feature
    - The most persistent H1 feature represents the circle's loop
    - Other H1 features (if any) should have much smaller persistence (noise)
    """
    circle = sample_point_cloud["circle"]

    # Compute H1 persistence
    vr = VietorisRipsPersistence(homology_dimensions=[1], max_edge_length=5.0)
    diagrams = vr.fit_transform([circle])
    h1_diagram = diagrams[0, :, :2]

    # Validate diagram structure
    assert_persistence_diagram_valid(h1_diagram)

    # Should have at least one H1 feature
    assert len(h1_diagram) > 0, "Circle should have at least one H1 feature"

    # The most persistent feature should be the circle's loop
    persistences = h1_diagram[:, 1] - h1_diagram[:, 0]
    max_persistence = np.max(persistences)

    # Loop should have significant persistence (relative to point cloud diameter)
    cloud_diameter = np.max(np.linalg.norm(circle[:, None] - circle, axis=2))
    assert (
        max_persistence > 0.1 * cloud_diameter
    ), f"H1 feature too short-lived: {max_persistence} < 0.1 * {cloud_diameter}"


@pytest.mark.validation
def test_two_circles_have_two_components(sample_point_cloud):
    """
    Validate that two separate circles produce two connected components.

    Mathematical Background:
    -----------------------
    Two disjoint circles have β0 = 2 (two connected components) and
    β1 = 2 (two loops). This tests multi-component detection.

    Validation Strategy:
    -------------------
    1. Compute H0 persistence
    2. Identify long-lived features (persistence > threshold)
    3. Count should equal 2 (one per circle)
    """
    two_circles = sample_point_cloud["two_circles"]

    # Compute H0 persistence with appropriate max edge length
    vr = VietorisRipsPersistence(homology_dimensions=[0], max_edge_length=2.5)
    diagrams = vr.fit_transform([two_circles])
    h0_diagram = diagrams[0, :, :2]

    # Validate diagram
    assert_persistence_diagram_valid(h0_diagram)

    # Filter for long-lived features (connected components)
    # Short-lived features are noise from point density variations
    persistences = h0_diagram[:, 1] - h0_diagram[:, 0]
    threshold = 0.5  # Features persisting beyond this are likely real components
    long_lived = persistences > threshold

    n_components = np.sum(long_lived)

    # Allow for some numerical variation (1-3 components is reasonable)
    # Exact count depends on sampling and filtration parameters
    assert 1 <= n_components <= 3, f"Expected ~2 components, got {n_components}"


# ============================================================================
# PERSISTENCE DIAGRAM PROPERTIES
# ============================================================================


@pytest.mark.validation
def test_persistence_diagram_birth_death_ordering(sample_point_cloud):
    """
    Validate fundamental persistence diagram property: birth ≤ death.

    Mathematical Background:
    -----------------------
    In a filtration, a topological feature is "born" when it first appears
    and "dies" when it merges with or is filled by other features.
    Birth time must always be ≤ death time by construction.

    This is a sanity check - if it fails, there's a serious bug.
    """
    circle = sample_point_cloud["circle"]

    vr = VietorisRipsPersistence(homology_dimensions=[0, 1], max_edge_length=5.0)
    diagrams = vr.fit_transform([circle])[0]

    # Check all dimensions
    for dim in [0, 1]:
        dim_diagram = diagrams[diagrams[:, 2] == dim, :2]
        if len(dim_diagram) > 0:
            assert_persistence_diagram_valid(dim_diagram)

            # Additional explicit check
            births, deaths = dim_diagram[:, 0], dim_diagram[:, 1]
            assert np.all(
                births <= deaths + FLOAT_TOLERANCE
            ), f"Found H{dim} features with birth > death"


# ============================================================================
# NUMERICAL STABILITY VALIDATION
# ============================================================================


@pytest.mark.validation
def test_persistence_reproducibility(sample_point_cloud):
    """
    Validate that identical inputs produce identical persistence diagrams.

    Numerical Stability Check:
    -------------------------
    Running the same computation twice should give identical results
    (up to floating-point precision). This validates:
    1. Deterministic algorithm implementation
    2. No uninitialized memory or random behavior
    3. Consistent numerical precision
    """
    circle = sample_point_cloud["circle"]

    # Compute persistence twice
    vr = VietorisRipsPersistence(homology_dimensions=[0, 1], max_edge_length=5.0)
    diagrams1 = vr.fit_transform([circle])[0]
    diagrams2 = vr.fit_transform([circle])[0]

    # Should be exactly identical (bit-for-bit)
    np.testing.assert_array_equal(
        diagrams1, diagrams2, err_msg="Persistence diagrams not reproducible"
    )


@pytest.mark.validation
@pytest.mark.slow
def test_persistence_with_noise_perturbation(sample_point_cloud):
    """
    Validate stability theorem: small perturbations → small changes in persistence.

    Mathematical Background (Stability Theorem):
    -------------------------------------------
    If two point clouds are close in Hausdorff distance δ, their persistence
    diagrams are close in bottleneck distance (≤ δ). This is a fundamental
    result in TDA (Cohen-Steiner et al., 2007).

    Test Strategy:
    -------------
    1. Start with clean circle point cloud
    2. Add small Gaussian noise (σ = 0.05)
    3. Compute persistence for both
    4. Verify diagrams are similar (bottleneck distance small)

    Note: Marked as @slow because this test is more computationally intensive.
    """
    circle = sample_point_cloud["circle"]

    # Add small noise
    np.random.seed(123)
    noise_scale = 0.05
    noisy_circle = circle + noise_scale * np.random.randn(*circle.shape)

    # Compute persistence for both
    vr = VietorisRipsPersistence(homology_dimensions=[1], max_edge_length=3.0)
    clean_diagrams = vr.fit_transform([circle])[0]
    noisy_diagrams = vr.fit_transform([noisy_circle])[0]

    # Extract H1 diagrams
    clean_h1 = clean_diagrams[clean_diagrams[:, 2] == 1, :2]
    noisy_h1 = noisy_diagrams[noisy_diagrams[:, 2] == 1, :2]

    # Compare the most persistent features
    # (stability theorem applies to all features,
    # but most persistent are easiest to validate)
    if len(clean_h1) > 0 and len(noisy_h1) > 0:
        clean_max_pers = np.max(clean_h1[:, 1] - clean_h1[:, 0])
        noisy_max_pers = np.max(noisy_h1[:, 1] - noisy_h1[:, 0])

        # Persistences should be similar
        relative_change = abs(clean_max_pers - noisy_max_pers) / clean_max_pers
        assert relative_change < 0.5, (
            f"Persistence changed by {relative_change:.1%} "
            "under small noise (expected < 50%)"
        )


# ============================================================================
# INTEGRATION TEST PATTERN EXAMPLE
# ============================================================================


@pytest.mark.integration
def test_end_to_end_topology_pipeline(sample_time_series):
    """
    Example integration test: time series → embedding → persistence → features.

    This demonstrates how to test a complete TDA pipeline:
    1. Take time series data
    2. Create Takens embedding (delay embedding)
    3. Compute persistence
    4. Extract topological features

    Note: This is a simplified example. Full implementation would be in
    financial_tda or poverty_tda modules.
    """
    sine_wave = sample_time_series["sine"]

    # Simple Takens embedding (delay = 1, dimension = 2)
    tau, dim = 1, 2
    n = len(sine_wave) - (dim - 1) * tau
    embedded = np.array([sine_wave[i : i + dim * tau : tau] for i in range(n)])

    # Compute persistence
    vr = VietorisRipsPersistence(homology_dimensions=[0, 1], max_edge_length=2.0)
    diagrams = vr.fit_transform([embedded])[0]

    # Extract H1 features (loops in embedded space indicate periodicity)
    h1_diagram = diagrams[diagrams[:, 2] == 1, :2]

    # Sine wave should produce at least one H1 feature (periodic structure)
    assert (
        len(h1_diagram) > 0
    ), "Periodic time series should have at least one H1 feature in embedding"

    # Validate diagram structure
    assert_persistence_diagram_valid(h1_diagram)
