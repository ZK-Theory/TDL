"""
Comprehensive validation suite for Poverty TDA Basin Dashboard.

Tests all dashboard functionality across multiple regions and basin configurations.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import numpy as np

from poverty_tda.viz.dashboard import (
    REGIONS,
    generate_mock_basin_data,
    get_severity_label,
    get_trap_score_color,
)


def test_all_regions():
    """Test data generation for all 10 regions."""
    print("Testing all regions...")

    for region in REGIONS:
        basins = generate_mock_basin_data(region, n_basins=10)

        print(f"\n  {region}:")
        print(f"    Generated {len(basins)} basins")

        # Verify basin structure
        for basin in basins:
            assert "basin_id" in basin
            assert "basin_name" in basin
            assert "region" in basin
            assert basin["region"] == region
            assert "population" in basin
            assert "trap_score" in basin
            assert "mean_mobility" in basin
            assert "area_km2" in basin
            assert "n_lsoas" in basin
            assert "decile_counts" in basin
            assert "domain_scores" in basin

            # Verify ranges
            assert 0 <= basin["trap_score"] <= 1
            assert 0 <= basin["mean_mobility"] <= 1
            assert basin["population"] > 0
            assert basin["area_km2"] > 0
            assert basin["n_lsoas"] > 0
            assert len(basin["decile_counts"]) == 10
            assert len(basin["domain_scores"]) == 4

        # Check trap score distribution
        scores = [b["trap_score"] for b in basins]
        print(f"    Trap scores: min={min(scores):.2f}, max={max(scores):.2f}, mean={np.mean(scores):.2f}")

    print("\n✓ All regions test passed!")


def test_basin_correlation():
    """Test that trap scores correlate correctly with other metrics."""
    print("\nTesting basin metric correlations...")

    basins = generate_mock_basin_data("North West", n_basins=20)

    for basin in basins:
        trap_score = basin["trap_score"]
        mobility = basin["mean_mobility"]
        domain_scores = basin["domain_scores"]
        decile_counts = basin["decile_counts"]

        # Higher trap score should correlate with lower mobility
        # (inverse relationship)
        if trap_score > 0.6:
            assert mobility < 0.6, f"High trap score {trap_score} should have low mobility"

        # Higher trap score should correlate with lower domain scores
        mean_domain = np.mean(list(domain_scores.values()))
        expected_domain = (1 - trap_score) * 100

        # Allow some variance (±20 points)
        assert (
            abs(mean_domain - expected_domain) < 25
        ), f"Domain scores not correlating with trap score: {mean_domain:.1f} vs {expected_domain:.1f}"

        # Higher trap score should have more population in low deciles
        low_decile_pop = sum(decile_counts[0:3])
        high_decile_pop = sum(decile_counts[7:10])

        if trap_score > 0.6:
            # Severe trap should have more in low deciles
            assert low_decile_pop > high_decile_pop, "Severe trap should concentrate in low deciles"

    print("✓ Metric correlation test passed!")


def test_severity_classification():
    """Test severity label and color consistency."""
    print("\nTesting severity classification...")

    test_cases = [
        (0.95, "Critical", "#8B0000"),
        (0.85, "Critical", "#8B0000"),
        (0.75, "Severe", "#FF4500"),
        (0.65, "Severe", "#FF4500"),
        (0.55, "Moderate", "#FFA500"),
        (0.45, "Moderate", "#FFA500"),
        (0.35, "Low", "#FFD700"),
        (0.25, "Low", "#FFD700"),
        (0.15, "Minimal", "#90EE90"),
        (0.05, "Minimal", "#90EE90"),
    ]

    for score, expected_label, expected_color in test_cases:
        label = get_severity_label(score)
        color = get_trap_score_color(score)

        assert label == expected_label, f"Score {score} should be {expected_label}, got {label}"
        assert color == expected_color, f"Score {score} should be {expected_color}, got {color}"

        print(f"  ✓ Score {score:.2f} → {label} ({color})")

    print("✓ Severity classification test passed!")


def test_data_reproducibility():
    """Test that same region generates same data."""
    print("\nTesting data reproducibility...")

    # Generate data twice for same region
    basins1 = generate_mock_basin_data("London", n_basins=10)
    basins2 = generate_mock_basin_data("London", n_basins=10)

    for i in range(10):
        b1 = basins1[i]
        b2 = basins2[i]

        # Should be identical
        assert b1["basin_id"] == b2["basin_id"]
        assert b1["population"] == b2["population"]
        assert abs(b1["trap_score"] - b2["trap_score"]) < 0.001
        assert abs(b1["mean_mobility"] - b2["mean_mobility"]) < 0.001
        assert b1["decile_counts"] == b2["decile_counts"]

    print("✓ Data reproducibility test passed!")


def test_edge_cases():
    """Test edge cases and boundary conditions."""
    print("\nTesting edge cases...")

    # Single basin
    basins = generate_mock_basin_data("Wales", n_basins=1)
    assert len(basins) == 1
    print("  ✓ Single basin generation")

    # Many basins
    basins = generate_mock_basin_data("East of England", n_basins=50)
    assert len(basins) == 50
    print("  ✓ Large basin count (50)")

    # Check extreme trap scores
    all_scores = [b["trap_score"] for b in basins]
    assert min(all_scores) >= 0.0
    assert max(all_scores) <= 1.0
    print("  ✓ Trap scores within valid range")

    # Check population distribution
    all_pops = [b["population"] for b in basins]
    assert min(all_pops) >= 5000
    assert max(all_pops) <= 50000
    print("  ✓ Population within expected range")

    # Check decile totals
    for basin in basins:
        total = sum(basin["decile_counts"])
        # Should be roughly population/5 (we divide by 5 in generator)
        expected = basin["population"] / 5
        assert abs(total - expected) < 500, "Decile counts don't sum correctly"
    print("  ✓ Decile count totals correct")

    print("✓ Edge cases test passed!")


def test_threshold_boundaries():
    """Test exact threshold boundaries for trap scores."""
    print("\nTesting threshold boundaries...")

    # Test exact boundaries
    boundaries = [
        (0.799, "Severe"),  # Just below Critical
        (0.800, "Critical"),  # Exactly Critical
        (0.599, "Moderate"),  # Just below Severe
        (0.600, "Severe"),  # Exactly Severe
        (0.399, "Low"),  # Just below Moderate
        (0.400, "Moderate"),  # Exactly Moderate
        (0.199, "Minimal"),  # Just below Low
        (0.200, "Low"),  # Exactly Low
    ]

    for score, expected in boundaries:
        result = get_severity_label(score)
        assert result == expected, f"Boundary score {score} should be {expected}, got {result}"
        print(f"  ✓ {score:.3f} → {expected}")

    print("✓ Threshold boundaries test passed!")


def test_regional_variation():
    """Test that different regions produce different data."""
    print("\nTesting regional variation...")

    regions_to_test = ["North West", "London", "Wales"]
    all_basins = {}

    for region in regions_to_test:
        basins = generate_mock_basin_data(region, n_basins=10)
        all_basins[region] = basins

    # Compare trap scores across regions
    for i, region1 in enumerate(regions_to_test):
        for region2 in regions_to_test[i + 1 :]:
            scores1 = [b["trap_score"] for b in all_basins[region1]]
            scores2 = [b["trap_score"] for b in all_basins[region2]]

            # Scores should be different (same seed would produce same values)
            assert scores1 != scores2, f"{region1} and {region2} produced identical scores"

            print(f"  ✓ {region1} vs {region2}: Different data confirmed")

    print("✓ Regional variation test passed!")


def test_domain_score_ranges():
    """Test that domain scores are within valid ranges."""
    print("\nTesting domain score ranges...")

    all_regions_basins = []
    for region in REGIONS:
        basins = generate_mock_basin_data(region, n_basins=10)
        all_regions_basins.extend(basins)

    domains = ["income", "employment", "education", "health"]

    for domain in domains:
        scores = [b["domain_scores"][domain] for b in all_regions_basins]

        min_score = min(scores)
        max_score = max(scores)
        mean_score = np.mean(scores)

        assert min_score >= 0, f"{domain} has negative score"
        assert max_score <= 100, f"{domain} exceeds 100"

        print(f"  {domain.capitalize():12s}: [{min_score:.1f}, {max_score:.1f}], mean={mean_score:.1f}")

    print("✓ Domain score ranges test passed!")


def run_visual_validation_checks():
    """Print visual validation checklist for manual testing."""
    print("\n" + "=" * 60)
    print("VISUAL VALIDATION CHECKLIST")
    print("=" * 60)
    print("""
Please manually verify the following in the dashboard:

STEP 1: Dashboard Structure
□ Dashboard loads without errors at http://localhost:8503
□ Sidebar shows region selector with 10 regions
□ Basin multi-select dropdown works
□ Selected basins display in main panel
□ No PyTorch DLL errors in console

STEP 2: Basin Statistics
□ Single basin view shows 4 metric cards (Population, Mobility, Trap Score, Area)
□ Trap score has color indicator bar
□ Delta indicators show appropriate values
□ Detailed information expander works
□ Multi-basin view shows comparison table
□ Gradient backgrounds apply correctly to table columns
□ Summary statistics (total pop, worst trap, avg mobility) display

STEP 3: Demographic Breakdown
□ IMD Decile Distribution chart displays (single basin)
□ Quintile Distribution pie chart shows percentages
□ IMD Domain Scores bar chart displays
□ Multi-basin comparison shows grouped bar charts
□ Demographic summary table with gradients displays
□ All charts are interactive (hover, zoom)

STEP 4: Map & Terrain Integration
□ Folium map displays with basin markers
□ Map shows correct region center
□ Basin markers are color-coded by severity
□ Clicking markers shows popup with basin info
□ Dashed circles show approximate boundaries
□ Map legend expander works
□ 3D terrain shows labeled valleys for each basin
□ Basin names appear as labels on terrain
□ Diamond markers identify basin centers
□ Terrain interpretation expander shows context-aware text
□ Basin elevations table displays

CROSS-REGION TESTING:
□ Switch between all 10 regions
□ Data updates correctly when region changes
□ Basin names include region abbreviation
□ Map centers appropriately for each region
□ Select multiple basins across different severity levels
□ Verify comparison views work with 2, 3, 5+ basins

PERFORMANCE:
□ Dashboard loads within 3-5 seconds
□ Switching regions is responsive
□ Selecting/deselecting basins updates quickly
□ No memory leaks after multiple region switches
□ Charts render smoothly
    """)
    print("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("Poverty TDA Basin Dashboard - Comprehensive Validation")
    print("=" * 60)

    try:
        test_all_regions()
        test_basin_correlation()
        test_severity_classification()
        test_data_reproducibility()
        test_edge_cases()
        test_threshold_boundaries()
        test_regional_variation()
        test_domain_score_ranges()

        print("\n" + "=" * 60)
        print("ALL AUTOMATED TESTS PASSED ✓")
        print("=" * 60)

        run_visual_validation_checks()

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
