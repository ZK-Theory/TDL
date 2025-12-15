"""Test Step 2: Basin Overlay & Color Coding.

This test demonstrates adding poverty trap basin overlays to the map.
Uses mock basin data generated from LSOA centroids for demonstration.

Run: python poverty_tda/viz/test_step2_basins.py
"""

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np

from poverty_tda.data.census_shapes import load_lsoa_boundaries
from poverty_tda.viz.maps import add_basin_overlay, add_lsoa_choropleth, create_base_map

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)


def create_mock_basins(lsoa_gdf: gpd.GeoDataFrame, n_basins: int = 10) -> gpd.GeoDataFrame:
    """
    Create mock basin polygons for testing.

    Generates basins by:
    1. Selecting random LSOA centroids as basin centers
    2. Assigning LSOAs to nearest center
    3. Creating convex hulls around each group

    Args:
        lsoa_gdf: GeoDataFrame with LSOA boundaries.
        n_basins: Number of basins to create.

    Returns:
        GeoDataFrame with basin polygons and metadata.
    """
    logger.info(f"Creating {n_basins} mock basins from {len(lsoa_gdf)} LSOAs")

    # Get LSOA bounds to work in geographic CRS
    bounds = lsoa_gdf.geometry.bounds
    centroids_x = (bounds["minx"] + bounds["maxx"]) / 2
    centroids_y = (bounds["miny"] + bounds["maxy"]) / 2

    # Select random basin centers
    np.random.seed(42)
    center_indices = np.random.choice(len(lsoa_gdf), n_basins, replace=False)
    centers = np.column_stack([centroids_x.iloc[center_indices], centroids_y.iloc[center_indices]])

    # Assign each LSOA to nearest basin center
    all_centroids = np.column_stack([centroids_x, centroids_y])
    distances = np.sqrt(((all_centroids[:, np.newaxis, :] - centers[np.newaxis, :, :]) ** 2).sum(axis=2))
    basin_assignments = np.argmin(distances, axis=1)

    # Create basin polygons from assigned LSOAs
    basins = []
    for basin_id in range(n_basins):
        basin_lsoas = lsoa_gdf.iloc[basin_assignments == basin_id]

        if len(basin_lsoas) == 0:
            continue

        # Create convex hull from basin LSOAs
        # Use unary_union to merge all geometries, then convex_hull
        basin_geom = basin_lsoas.geometry.unary_union.convex_hull

        # Calculate basin statistics
        basin_bounds = basin_lsoas.geometry.bounds
        avg_y = ((basin_bounds["miny"] + basin_bounds["maxy"]) / 2).mean()  # Average latitude

        # Create synthetic mobility proxy (higher in south)
        y_norm = (avg_y - centroids_y.min()) / (centroids_y.max() - centroids_y.min())
        avg_mobility = 0.3 + 0.5 * y_norm + 0.1 * np.random.randn()
        avg_mobility = np.clip(avg_mobility, 0.0, 1.0)

        basins.append(
            {
                "basin_id": basin_id,
                "label": f"Basin {basin_id}",
                "geometry": basin_geom,
                "area": basin_geom.area,
                "num_lsoas": len(basin_lsoas),
                "avg_mobility": avg_mobility,
                "num_critical_points": np.random.randint(1, 5),
            }
        )

    basin_gdf = gpd.GeoDataFrame(basins, crs=lsoa_gdf.crs)
    logger.info(f"✓ Created {len(basin_gdf)} basin polygons")

    return basin_gdf


def test_step2_basin_overlay():
    """Test Step 2: Basin overlay with color coding."""
    logger.info("=" * 60)
    logger.info("Step 2 Test: Basin Overlay & Color Coding")
    logger.info("=" * 60)

    # Output directory
    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "poverty_map_step2.html"

    try:
        # Step 1: Load LSOA boundaries
        logger.info("\n1. Loading LSOA boundaries...")
        lsoa_gdf = load_lsoa_boundaries()
        logger.info(f"✓ Loaded {len(lsoa_gdf)} LSOAs")
        logger.info(f"  CRS: {lsoa_gdf.crs}")

        # Step 2: Create synthetic mobility proxy values
        logger.info("\n2. Creating synthetic mobility proxy values...")
        np.random.seed(42)
        bounds = lsoa_gdf.geometry.bounds
        y_coords = (bounds["miny"] + bounds["maxy"]) / 2
        y_norm = (y_coords - y_coords.min()) / (y_coords.max() - y_coords.min())
        mobility_proxy = 0.3 + 0.5 * y_norm + 0.1 * np.random.randn(len(lsoa_gdf))
        mobility_proxy = np.clip(mobility_proxy, 0.0, 1.0)
        lsoa_gdf["mobility_proxy"] = mobility_proxy

        logger.info(f"  Generated {len(mobility_proxy)} mobility values")
        logger.info(f"  Range: [{np.min(mobility_proxy):.3f}, {np.max(mobility_proxy):.3f}]")

        # Step 3: Create mock basin polygons
        logger.info("\n3. Creating mock poverty basins...")
        basin_gdf = create_mock_basins(lsoa_gdf, n_basins=10)
        logger.info(f"  Number of basins: {len(basin_gdf)}")
        logger.info(
            f"  Avg mobility range: [{basin_gdf['avg_mobility'].min():.3f}, {basin_gdf['avg_mobility'].max():.3f}]"
        )

        # Step 4: Create map with LSOA choropleth
        logger.info("\n4. Creating interactive map with basins...")
        m = create_base_map()

        # Add LSOA mobility choropleth
        m = add_lsoa_choropleth(
            m,
            lsoa_gdf,
            value_column="mobility_proxy",
            layer_name="Mobility Surface",
            fill_opacity=0.7,
        )

        # Add basin overlay
        m = add_basin_overlay(
            m,
            basin_gdf,
            basin_id_column="basin_id",
            basin_label_column="label",
            layer_name="Poverty Basins",
            color_scheme="qualitative",
            show_labels=True,
            fill_opacity=0.2,
        )

        # Add layer control
        folium.LayerControl(position="topright").add_to(m)

        # Save map
        m.save(str(output_path))
        logger.info("✓ Map created successfully")
        logger.info(f"  Output: {output_path}")

        logger.info("\n" + "=" * 60)
        logger.info("Step 2 Test Complete!")
        logger.info("=" * 60)
        logger.info(f"\nMap saved to: {output_path}")
        logger.info("\nOpen the HTML file in a browser to view the interactive map.")
        logger.info("You should see:")
        logger.info("  - LSOA mobility surface (base layer)")
        logger.info("  - 10 colored basin polygons overlaid")
        logger.info("  - Basin labels at centroids")
        logger.info("  - Clickable basins with statistics")
        logger.info("  - Layer control to toggle basins on/off")

        return True

    except Exception as e:
        logger.error(f"✗ Failed to create map: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Need to import folium here for the LayerControl
    import folium

    success = test_step2_basin_overlay()
    exit(0 if success else 1)
