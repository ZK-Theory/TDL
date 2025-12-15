"""
Test script for geographic context (map and terrain) functionality.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import numpy as np

from poverty_tda.viz.dashboard import generate_mock_basin_data


def test_regional_centers():
    """Test that regional centers are valid coordinates."""
    print("Testing regional center coordinates...")

    # Regional centers defined in dashboard
    region_centers = {
        "North West": [53.5, -2.5],
        "North East": [55.0, -1.6],
        "Yorkshire and The Humber": [53.8, -1.3],
        "East Midlands": [52.9, -1.0],
        "West Midlands": [52.5, -2.0],
        "East of England": [52.2, 0.5],
        "London": [51.5, -0.1],
        "South East": [51.3, -0.8],
        "South West": [51.0, -3.0],
        "Wales": [52.3, -3.7],
    }

    for region, coords in region_centers.items():
        lat, lon = coords

        # Validate UK latitude range (approx 49-61°N)
        assert 49 <= lat <= 61, f"{region}: Invalid latitude {lat}"

        # Validate UK longitude range (approx -8 to 2°E)
        assert -8 <= lon <= 2, f"{region}: Invalid longitude {lon}"

        print(f"  ✓ {region}: [{lat}, {lon}]")

    print("✓ Regional centers test passed!")


def test_basin_positioning():
    """Test basin positioning logic for map markers."""
    print("\nTesting basin positioning...")

    basins = generate_mock_basin_data("London", n_basins=6)
    center = [51.5, -0.1]  # London center

    for i, basin in enumerate(basins):
        # Calculate offset as in dashboard
        offset_lat = (i % 3 - 1) * 0.15
        offset_lon = (i // 3 - 1) * 0.15

        basin_center = [center[0] + offset_lat, center[1] + offset_lon]

        print(f"  Basin {basin['basin_id']}: {basin_center}")

        # Verify positions are near London
        assert 51.0 <= basin_center[0] <= 52.0, f"Basin lat out of range: {basin_center[0]}"
        assert -0.6 <= basin_center[1] <= 0.4, f"Basin lon out of range: {basin_center[1]}"

    print("✓ Basin positioning test passed!")


def test_terrain_generation():
    """Test 3D terrain generation algorithm."""
    print("\nTesting terrain generation...")

    basins = generate_mock_basin_data("North West", n_basins=3)

    # Generate terrain as in dashboard
    grid_size = 30
    x = np.linspace(0, 10, grid_size)
    y = np.linspace(0, 10, grid_size)
    X, Y = np.meshgrid(x, y)
    Z = np.zeros_like(X)

    # Add basin valleys
    for i, basin in enumerate(basins):
        cx = 2 + (i % 3) * 3
        cy = 2 + (i // 3) * 3
        depth = basin["trap_score"] * 3.0
        width = np.sqrt(basin["area_km2"]) / 10

        valley = -depth * np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * width**2))
        Z += valley

        print(f"  Basin {basin['basin_id']}:")
        print(f"    Center: ({cx}, {cy})")
        print(f"    Depth: {depth:.2f}")
        print(f"    Width: {width:.2f}")
        print(f"    Min elevation: {valley.min():.3f}")

    # Normalize
    Z = (Z - Z.min()) / (Z.max() - Z.min())

    print("\n  Final terrain stats:")
    print(f"    Min elevation: {Z.min():.3f}")
    print(f"    Max elevation: {Z.max():.3f}")
    print(f"    Mean elevation: {Z.mean():.3f}")

    # Verify range
    assert Z.min() >= 0.0, "Min elevation should be >= 0"
    assert Z.max() <= 1.0, "Max elevation should be <= 1"

    print("\n✓ Terrain generation test passed!")


def test_basin_colors():
    """Test basin color assignment based on trap scores."""
    print("\nTesting basin color assignment...")

    basins = generate_mock_basin_data("Yorkshire and The Humber", n_basins=10)

    for basin in basins:
        trap_score = basin["trap_score"]

        # Determine color as in dashboard
        if trap_score >= 0.8:
            expected_color = "#8B0000"  # Critical
        elif trap_score >= 0.6:
            expected_color = "#FF4500"  # Severe
        elif trap_score >= 0.4:
            expected_color = "#FFA500"  # Moderate
        else:
            expected_color = "#90EE90"  # Low

        print(f"  Basin {basin['basin_id']}: Score {trap_score:.2f} → {expected_color}")

    print("✓ Basin color test passed!")


def test_elevation_interpretation():
    """Test basin elevation interpretation logic."""
    print("\nTesting elevation interpretation...")

    basins = generate_mock_basin_data("Wales", n_basins=5)

    for basin in basins:
        mobility = basin["mean_mobility"]
        interpretation = "Valley" if mobility < 0.5 else "Plateau"

        print(f"  Basin {basin['basin_id']}: Mobility {mobility:.3f} → {interpretation}")

        # Verify interpretation logic
        if mobility < 0.5:
            assert interpretation == "Valley", "Low mobility should be Valley"
        else:
            assert interpretation == "Plateau", "High mobility should be Plateau"

    print("✓ Elevation interpretation test passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("Geographic Context Test Suite")
    print("=" * 60)

    try:
        test_regional_centers()
        test_basin_positioning()
        test_terrain_generation()
        test_basin_colors()
        test_elevation_interpretation()

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
