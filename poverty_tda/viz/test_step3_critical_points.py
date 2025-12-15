"""Test Step 3: Critical Points & Barrier Markers.

This test demonstrates adding critical points (minima, maxima, saddles) to the map.
Uses mock critical point data for demonstration.

Run: python poverty_tda/viz/test_step3_critical_points.py
"""

import logging
from pathlib import Path

import folium
import geopandas as gpd
import numpy as np
from shapely.geometry import Point

from poverty_tda.data.census_shapes import load_lsoa_boundaries
from poverty_tda.viz.maps import (
    add_basin_overlay,
    add_critical_points,
    add_lsoa_choropleth,
    create_base_map,
)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)


def create_mock_basins(lsoa_gdf: gpd.GeoDataFrame, n_basins: int = 10) -> gpd.GeoDataFrame:
    """Create mock basin polygons from LSOA clustering."""
    logger.info(f"Creating {n_basins} mock basins from {len(lsoa_gdf)} LSOAs")

    bounds = lsoa_gdf.geometry.bounds
    centroids_x = (bounds["minx"] + bounds["maxx"]) / 2
    centroids_y = (bounds["miny"] + bounds["maxy"]) / 2

    # Select random basin centers
    np.random.seed(42)
    center_indices = np.random.choice(len(lsoa_gdf), n_basins, replace=False)
    centers = np.column_stack([centroids_x.iloc[center_indices], centroids_y.iloc[center_indices]])

    # Assign each LSOA to nearest basin
    all_centroids = np.column_stack([centroids_x, centroids_y])
    distances = np.sqrt(((all_centroids[:, np.newaxis, :] - centers[np.newaxis, :, :]) ** 2).sum(axis=2))
    basin_assignments = np.argmin(distances, axis=1)

    # Create basin polygons
    basins = []
    for basin_id in range(n_basins):
        basin_lsoas = lsoa_gdf.iloc[basin_assignments == basin_id]
        if len(basin_lsoas) == 0:
            continue

        basin_geom = basin_lsoas.geometry.union_all().convex_hull

        # Calculate statistics
        basin_bounds = basin_lsoas.geometry.bounds
        avg_y = ((basin_bounds["miny"] + basin_bounds["maxy"]) / 2).mean()
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


def create_mock_critical_points(basin_gdf: gpd.GeoDataFrame, lsoa_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Create mock critical points based on basins.

    Generates:
    - 1 minimum (trap center) per basin at centroid
    - 1-2 saddles (barriers) between adjacent basins
    - A few maxima (peaks) in high-mobility areas

    Args:
        basin_gdf: GeoDataFrame with basin polygons.
        lsoa_gdf: GeoDataFrame with LSOA boundaries (for mobility values).

    Returns:
        GeoDataFrame with critical points.
    """
    logger.info("Creating mock critical points...")

    critical_points = []
    np.random.seed(42)

    # Get LSOA mobility values
    bounds = lsoa_gdf.geometry.bounds
    centroids_y = (bounds["miny"] + bounds["maxy"]) / 2
    y_norm = (centroids_y - centroids_y.min()) / (centroids_y.max() - centroids_y.min())
    mobility_values = 0.3 + 0.5 * y_norm + 0.1 * np.random.randn(len(lsoa_gdf))
    mobility_values = np.clip(mobility_values, 0.0, 1.0)

    # 1. Add one minimum (trap center) per basin
    for _, basin in basin_gdf.iterrows():
        centroid = basin.geometry.centroid
        critical_points.append(
            {
                "cp_type": "minimum",
                "geometry": Point(centroid.x, centroid.y),
                "basin_id": basin["basin_id"],
                "mobility_value": basin["avg_mobility"],
                "depth": 0.1 + 0.2 * np.random.rand(),
                "persistence": 0.05 + 0.15 * np.random.rand(),
            }
        )

    # 2. Add saddle points between some basins
    n_saddles = len(basin_gdf) // 2  # Roughly half as many saddles as basins
    for i in range(n_saddles):
        # Pick two random basins
        basin_ids = np.random.choice(len(basin_gdf), 2, replace=False)
        basin1 = basin_gdf.iloc[basin_ids[0]]
        basin2 = basin_gdf.iloc[basin_ids[1]]

        # Place saddle point between their centroids
        c1 = basin1.geometry.centroid
        c2 = basin2.geometry.centroid
        saddle_x = (c1.x + c2.x) / 2
        saddle_y = (c1.y + c2.y) / 2

        # Mobility at saddle is average of the two basins
        saddle_mobility = (basin1["avg_mobility"] + basin2["avg_mobility"]) / 2

        critical_points.append(
            {
                "cp_type": "saddle",
                "geometry": Point(saddle_x, saddle_y),
                "basin_id": None,  # Saddles are between basins
                "mobility_value": saddle_mobility,
                "depth": 0.05 + 0.1 * np.random.rand(),
                "persistence": 0.02 + 0.08 * np.random.rand(),
            }
        )

    # 3. Add a few maxima in high-mobility regions
    n_maxima = 5
    high_mobility_indices = np.argsort(mobility_values)[-n_maxima * 10 :]
    max_indices = np.random.choice(high_mobility_indices, n_maxima, replace=False)

    for idx in max_indices:
        lsoa = lsoa_gdf.iloc[idx]
        lsoa_bounds = lsoa.geometry.bounds
        max_x = (lsoa_bounds[0] + lsoa_bounds[2]) / 2
        max_y = (lsoa_bounds[1] + lsoa_bounds[3]) / 2

        critical_points.append(
            {
                "cp_type": "maximum",
                "geometry": Point(max_x, max_y),
                "basin_id": None,
                "mobility_value": mobility_values.iloc[idx],
                "depth": 0.15 + 0.25 * np.random.rand(),
                "persistence": 0.1 + 0.2 * np.random.rand(),
            }
        )

    cp_gdf = gpd.GeoDataFrame(critical_points, crs=basin_gdf.crs)
    logger.info(f"✓ Created {len(cp_gdf)} critical points")
    logger.info(
        f"  Minima: {(cp_gdf['cp_type'] == 'minimum').sum()}, "
        f"Saddles: {(cp_gdf['cp_type'] == 'saddle').sum()}, "
        f"Maxima: {(cp_gdf['cp_type'] == 'maximum').sum()}"
    )

    return cp_gdf


def test_step3_critical_points():
    """Test Step 3: Critical points and barrier markers."""
    logger.info("=" * 60)
    logger.info("Step 3 Test: Critical Points & Barrier Markers")
    logger.info("=" * 60)

    # Output directory
    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "poverty_map_step3.html"

    try:
        # Step 1: Load LSOA boundaries
        logger.info("\n1. Loading LSOA boundaries...")
        lsoa_gdf = load_lsoa_boundaries()
        logger.info(f"✓ Loaded {len(lsoa_gdf)} LSOAs")

        # Step 2: Create synthetic mobility proxy
        logger.info("\n2. Creating synthetic mobility proxy values...")
        np.random.seed(42)
        bounds = lsoa_gdf.geometry.bounds
        y_coords = (bounds["miny"] + bounds["maxy"]) / 2
        y_norm = (y_coords - y_coords.min()) / (y_coords.max() - y_coords.min())
        mobility_proxy = 0.3 + 0.5 * y_norm + 0.1 * np.random.randn(len(lsoa_gdf))
        mobility_proxy = np.clip(mobility_proxy, 0.0, 1.0)
        lsoa_gdf["mobility_proxy"] = mobility_proxy
        logger.info(f"  Generated {len(mobility_proxy)} mobility values")

        # Step 3: Create mock basins
        logger.info("\n3. Creating mock poverty basins...")
        basin_gdf = create_mock_basins(lsoa_gdf, n_basins=10)
        logger.info(f"  Number of basins: {len(basin_gdf)}")

        # Step 4: Create mock critical points
        logger.info("\n4. Creating mock critical points...")
        cp_gdf = create_mock_critical_points(basin_gdf, lsoa_gdf)
        logger.info(f"  Total critical points: {len(cp_gdf)}")

        # Step 5: Create map with all layers
        logger.info("\n5. Creating interactive map with critical points...")
        m = create_base_map()

        # Add LSOA mobility choropleth
        m = add_lsoa_choropleth(
            m,
            lsoa_gdf,
            value_column="mobility_proxy",
            layer_name="Mobility Surface",
            fill_opacity=0.6,
        )

        # Add basin overlay
        m = add_basin_overlay(
            m,
            basin_gdf,
            basin_id_column="basin_id",
            basin_label_column="label",
            layer_name="Poverty Basins",
            fill_opacity=0.15,
        )

        # Add critical points
        m = add_critical_points(
            m,
            cp_gdf,
            point_type_column="cp_type",
            layer_name="Critical Points",
            marker_size=10,
        )

        # Add layer control
        folium.LayerControl(position="topright").add_to(m)

        # Save map
        m.save(str(output_path))
        logger.info("✓ Map created successfully")
        logger.info(f"  Output: {output_path}")

        logger.info("\n" + "=" * 60)
        logger.info("Step 3 Test Complete!")
        logger.info("=" * 60)
        logger.info(f"\nMap saved to: {output_path}")
        logger.info("\nOpen the HTML file in a browser to view the interactive map.")
        logger.info("You should see:")
        logger.info("  - LSOA mobility surface (base layer)")
        logger.info("  - Colored basin polygons")
        logger.info("  - Red circles = Minima (poverty trap centers)")
        logger.info("  - Orange circles = Saddles (barriers between basins)")
        logger.info("  - Green circles = Maxima (high opportunity peaks)")
        logger.info("  - Click markers for detailed information")
        logger.info("  - Layer control to toggle all layers")

        return True

    except Exception as e:
        logger.error(f"✗ Failed to create map: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_step3_critical_points()
    exit(0 if success else 1)
