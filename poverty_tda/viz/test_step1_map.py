"""
Test script for Step 1: Map Foundation & LSOA Choropleth

Creates a sample interactive map with mobility proxy values.
"""

import logging
import sys
from pathlib import Path

import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from poverty_tda.viz.maps import (
    create_poverty_map,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_step1_map_foundation():
    """Test Step 1: Create base map with LSOA choropleth."""
    logger.info("=" * 60)
    logger.info("Step 1 Test: Map Foundation & LSOA Choropleth")
    logger.info("=" * 60)

    # Load LSOA boundaries (will download if missing)
    logger.info("\n1. Loading LSOA boundaries...")
    try:
        from poverty_tda.data.census_shapes import load_lsoa_boundaries

        lsoa_gdf = load_lsoa_boundaries(download_if_missing=True)
        logger.info(f"✓ Loaded {len(lsoa_gdf)} LSOAs")
        logger.info(f"  CRS: {lsoa_gdf.crs}")
        logger.info(f"  Columns: {list(lsoa_gdf.columns)}")

    except Exception as e:
        logger.error(f"✗ Failed to load LSOA boundaries: {e}")
        return False

    # Create synthetic mobility proxy values for testing
    logger.info("\n2. Creating synthetic mobility proxy values...")
    np.random.seed(42)

    # Create a gradient from north to south to simulate real patterns
    # (higher mobility in south/London, lower in north)
    # Use bounds instead of centroids to avoid geographic CRS warning
    bounds = lsoa_gdf.geometry.bounds
    y_coords = (bounds["miny"] + bounds["maxy"]) / 2

    # Normalize y to [0, 1]
    y_norm = (y_coords - y_coords.min()) / (y_coords.max() - y_coords.min())

    # Create mobility proxy: higher values in south (higher y)
    # Add some random noise
    mobility_proxy = 0.3 + 0.5 * y_norm + 0.1 * np.random.randn(len(lsoa_gdf))
    mobility_proxy = np.clip(mobility_proxy, 0.0, 1.0)  # Clip to [0, 1]

    logger.info(f"  Generated {len(mobility_proxy)} mobility values")
    logger.info(f"  Range: [{mobility_proxy.min():.3f}, {mobility_proxy.max():.3f}]")
    logger.info(f"  Mean: {mobility_proxy.mean():.3f}")

    # Add to GeoDataFrame
    lsoa_gdf["mobility_proxy"] = mobility_proxy

    # Create map
    logger.info("\n3. Creating interactive map...")
    output_dir = project_root / "poverty_tda" / "viz" / "outputs"
    output_path = output_dir / "poverty_map_step1.html"

    try:
        m = create_poverty_map(
            lsoa_gdf,
            value_column="mobility_proxy",
            layer_name="Mobility Proxy (Synthetic)",
            colormap="RdYlGn",
            output_path=output_path,
        )

        logger.info("✓ Map created successfully")
        logger.info(f"  Output: {output_path}")
        logger.info(f"  Map center: {m.location}")
        logger.info(f"  Zoom level: {m.options['zoom']}")

    except Exception as e:
        logger.error(f"✗ Failed to create map: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Step 1 Test Complete!")
    logger.info("=" * 60)
    logger.info(f"\nMap saved to: {output_path}")
    logger.info("\nOpen the HTML file in a browser to view the interactive map.")
    logger.info("You should see:")
    logger.info("  - LSOA boundaries colored by mobility proxy")
    logger.info("  - Higher values (green) in the south")
    logger.info("  - Lower values (red) in the north")
    logger.info("  - OpenStreetMap base layer")
    logger.info("  - Layer control in top-right corner")

    return True


if __name__ == "__main__":
    success = test_step1_map_foundation()
    sys.exit(0 if success else 1)
