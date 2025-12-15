"""
Test script for Step 1: Map Foundation & LSOA Choropleth (Mock Data Version)

Creates a sample interactive map with synthetic LSOA-like polygons.
This version works without needing to download real LSOA boundaries.
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from poverty_tda.viz.maps import (
    add_lsoa_choropleth,
    create_base_map,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_mock_lsoa_grid(n_rows=20, n_cols=20):
    """Create a grid of mock LSOA polygons for testing."""
    logger.info(f"Creating {n_rows}×{n_cols} mock LSOA grid...")

    # England/Wales approximate center in lat/lon
    center_lat, center_lon = 52.8, -2.0

    # Create grid of cells (each ~0.1 degrees)
    cell_size = 0.1

    lsoas = []
    for i in range(n_rows):
        for j in range(n_cols):
            # Calculate cell bounds
            lon_min = center_lon + (j - n_cols / 2) * cell_size
            lon_max = lon_min + cell_size
            lat_min = center_lat + (i - n_rows / 2) * cell_size
            lat_max = lat_min + cell_size

            # Create polygon
            poly = Polygon(
                [
                    (lon_min, lat_min),
                    (lon_max, lat_min),
                    (lon_max, lat_max),
                    (lon_min, lat_max),
                ]
            )

            # Create LSOA code
            lsoa_code = f"E0100{i:02d}{j:02d}"

            lsoas.append(
                {
                    "LSOA21CD": lsoa_code,
                    "LSOA21NM": f"Mock LSOA {i},{j}",
                    "geometry": poly,
                }
            )

    gdf = gpd.GeoDataFrame(lsoas, crs="EPSG:4326")
    logger.info(f"✓ Created {len(gdf)} mock LSOAs")
    return gdf


def test_step1_map_foundation():
    """Test Step 1: Create base map with LSOA choropleth using mock data."""
    logger.info("=" * 60)
    logger.info("Step 1 Test: Map Foundation & LSOA Choropleth (Mock Data)")
    logger.info("=" * 60)

    # Create mock LSOA boundaries
    logger.info("\n1. Creating mock LSOA boundaries...")
    lsoa_gdf = create_mock_lsoa_grid(n_rows=20, n_cols=20)
    logger.info(f"  CRS: {lsoa_gdf.crs}")
    logger.info(f"  Columns: {list(lsoa_gdf.columns)}")

    # Create synthetic mobility proxy values
    logger.info("\n2. Creating synthetic mobility proxy values...")
    np.random.seed(42)

    # Create a gradient from north to south to simulate real patterns
    centroids = lsoa_gdf.geometry.centroid
    y_coords = centroids.y.values

    # Normalize y to [0, 1]
    y_norm = (y_coords - y_coords.min()) / (y_coords.max() - y_coords.min())

    # Create mobility proxy: higher values in south (higher y)
    # Add some random noise
    mobility_proxy = 0.3 + 0.5 * y_norm + 0.1 * np.random.randn(len(lsoa_gdf))
    mobility_proxy = np.clip(mobility_proxy, 0.0, 1.0)

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
        # Create base map
        m = create_base_map()

        # Add choropleth layer
        m = add_lsoa_choropleth(
            m,
            lsoa_gdf,
            value_column="mobility_proxy",
            layer_name="Mobility Proxy (Synthetic)",
            colormap="RdYlGn",
            legend_name="Mobility Proxy",
        )

        # Save map
        m.save(str(output_path))

        logger.info("✓ Map created successfully")
        logger.info(f"  Output: {output_path}")
        logger.info(f"  Map center: {m.location}")

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
    logger.info("  - Mock LSOA boundaries colored by mobility proxy")
    logger.info("  - Higher values (green) in the south")
    logger.info("  - Lower values (red) in the north")
    logger.info("  - OpenStreetMap base layer")
    logger.info("  - Layer control in top-right corner")
    logger.info("\nNote: Using mock LSOA data. Replace with real LSOA boundaries")
    logger.info("      from census_shapes.py when ONS API is available.")

    return True


if __name__ == "__main__":
    success = test_step1_map_foundation()
    sys.exit(0 if success else 1)
