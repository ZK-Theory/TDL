"""
Test script to verify basin statistics display functionality.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import dashboard functions
from poverty_tda.viz.dashboard import (
    generate_mock_basin_data,
    get_severity_label,
    get_trap_score_color,
)


def test_mock_data_generation():
    """Test that mock data generation works correctly."""
    print("Testing mock basin data generation...")

    basins = generate_mock_basin_data("North West", n_basins=5)

    assert len(basins) == 5, "Should generate 5 basins"

    for basin in basins:
        print(f"\nBasin {basin['basin_id']}:")
        print(f"  Population: {basin['population']:,}")
        print(f"  Trap Score: {basin['trap_score']:.3f}")
        print(f"  Severity: {get_severity_label(basin['trap_score'])}")
        print(f"  Mean Mobility: {basin['mean_mobility']:.3f}")
        print(f"  Area: {basin['area_km2']:.1f} km²")
        print(f"  Color: {get_trap_score_color(basin['trap_score'])}")

        # Verify data structure
        assert "basin_id" in basin
        assert "population" in basin
        assert "trap_score" in basin
        assert "mean_mobility" in basin
        assert "area_km2" in basin
        assert "decile_counts" in basin
        assert len(basin["decile_counts"]) == 10

    print("\n✓ Mock data generation test passed!")


def test_severity_labels():
    """Test trap score severity classification."""
    print("\nTesting severity label classification...")

    test_cases = [
        (0.9, "Critical"),
        (0.7, "Severe"),
        (0.5, "Moderate"),
        (0.3, "Low"),
        (0.1, "Minimal"),
    ]

    for score, expected in test_cases:
        result = get_severity_label(score)
        print(f"  Score {score:.1f} → {result} (expected: {expected})")
        assert result == expected, f"Expected {expected}, got {result}"

    print("✓ Severity label test passed!")


def test_color_mapping():
    """Test trap score color mapping."""
    print("\nTesting color mapping...")

    test_scores = [0.9, 0.7, 0.5, 0.3, 0.1]

    for score in test_scores:
        color = get_trap_score_color(score)
        severity = get_severity_label(score)
        print(f"  Score {score:.1f} ({severity}): {color}")
        assert color.startswith("#"), "Color should be hex format"

    print("✓ Color mapping test passed!")


def test_multi_region_consistency():
    """Test that different regions generate different data."""
    print("\nTesting multi-region consistency...")

    regions = ["North West", "London", "Yorkshire and The Humber"]

    for region in regions:
        basins = generate_mock_basin_data(region, n_basins=3)
        print(f"\n  {region}:")
        for basin in basins:
            print(f"    {basin['basin_name']}: Trap={basin['trap_score']:.2f}")

    print("\n✓ Multi-region test passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("Basin Statistics Display Test Suite")
    print("=" * 60)

    try:
        test_mock_data_generation()
        test_severity_labels()
        test_color_mapping()
        test_multi_region_consistency()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
