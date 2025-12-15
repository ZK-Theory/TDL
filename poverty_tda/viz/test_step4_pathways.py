"""Test Step 4: Pathway Arrows & Flow Visualization.

This test demonstrates adding escape pathway arrows to the map.
Uses mock pathway data generated from critical points.

Run: python poverty_tda/viz/test_step4_pathways.py
"""

import logging
from pathlib import Path

import folium
import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, Point

from poverty_tda.data.census_shapes import load_lsoa_boundaries
from poverty_tda.viz.maps import (
    add_basin_overlay,
    add_critical_points,
    add_lsoa_choropleth,
    add_pathway_arrows,
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

    np.random.seed(42)
    center_indices = np.random.choice(len(lsoa_gdf), n_basins, replace=False)
    centers = np.column_stack([centroids_x.iloc[center_indices], centroids_y.iloc[center_indices]])

    all_centroids = np.column_stack([centroids_x, centroids_y])
    distances = np.sqrt(((all_centroids[:, np.newaxis, :] - centers[np.newaxis, :, :]) ** 2).sum(axis=2))
    basin_assignments = np.argmin(distances, axis=1)

    basins = []
    for basin_id in range(n_basins):
        basin_lsoas = lsoa_gdf.iloc[basin_assignments == basin_id]
        if len(basin_lsoas) == 0:
            continue

        basin_geom = basin_lsoas.geometry.union_all().convex_hull
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
                "avg_mobility": avg_mobility,
            }
        )

    basin_gdf = gpd.GeoDataFrame(basins, crs=lsoa_gdf.crs)
    logger.info(f"✓ Created {len(basin_gdf)} basin polygons")
    return basin_gdf


def create_mock_critical_points(basin_gdf: gpd.GeoDataFrame, lsoa_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Create mock critical points."""
    logger.info("Creating mock critical points...")

    critical_points = []
    np.random.seed(42)

    bounds = lsoa_gdf.geometry.bounds
    centroids_y = (bounds["miny"] + bounds["maxy"]) / 2
    y_norm = (centroids_y - centroids_y.min()) / (centroids_y.max() - centroids_y.min())
    mobility_values = 0.3 + 0.5 * y_norm + 0.1 * np.random.randn(len(lsoa_gdf))
    mobility_values = np.clip(mobility_values, 0.0, 1.0)

    # Minima per basin
    for _, basin in basin_gdf.iterrows():
        centroid = basin.geometry.centroid
        critical_points.append(
            {
                "cp_type": "minimum",
                "geometry": Point(centroid.x, centroid.y),
                "basin_id": basin["basin_id"],
                "mobility_value": basin["avg_mobility"],
            }
        )

    # Saddles between basins
    n_saddles = len(basin_gdf) // 2
    for i in range(n_saddles):
        basin_ids = np.random.choice(len(basin_gdf), 2, replace=False)
        basin1 = basin_gdf.iloc[basin_ids[0]]
        basin2 = basin_gdf.iloc[basin_ids[1]]

        c1 = basin1.geometry.centroid
        c2 = basin2.geometry.centroid
        saddle_x = (c1.x + c2.x) / 2
        saddle_y = (c1.y + c2.y) / 2
        saddle_mobility = (basin1["avg_mobility"] + basin2["avg_mobility"]) / 2

        critical_points.append(
            {
                "cp_type": "saddle",
                "geometry": Point(saddle_x, saddle_y),
                "mobility_value": saddle_mobility,
            }
        )

    # Maxima in high-mobility regions
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
                "mobility_value": mobility_values.iloc[idx],
            }
        )

    cp_gdf = gpd.GeoDataFrame(critical_points, crs=basin_gdf.crs)
    logger.info(f"✓ Created {len(cp_gdf)} critical points")
    return cp_gdf


def create_mock_pathways(cp_gdf: gpd.GeoDataFrame, basin_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Create mock escape pathways between critical points.

    Generates pathways showing:
    - Escape paths from minima to maxima (upward mobility)
    - Descent paths from maxima to minima (downward)
    - Stable paths along saddles

    Args:
        cp_gdf: GeoDataFrame with critical points.
        basin_gdf: GeoDataFrame with basins.

    Returns:
        GeoDataFrame with pathway LineStrings.
    """
    logger.info("Creating mock pathways...")

    pathways = []
    np.random.seed(42)

    minima = cp_gdf[cp_gdf["cp_type"] == "minimum"]
    maxima = cp_gdf[cp_gdf["cp_type"] == "maximum"]
    saddles = cp_gdf[cp_gdf["cp_type"] == "saddle"]

    # 1. Create escape paths from minima to maxima
    for _, minimum in minima.iterrows():
        # Pick a random maximum to connect to
        if len(maxima) == 0:
            continue

        target_max = maxima.iloc[np.random.choice(len(maxima))]

        # Create curved path using intermediate points
        start = minimum.geometry
        end = target_max.geometry

        # Generate intermediate points with some curvature
        n_steps = 8
        t = np.linspace(0, 1, n_steps)

        # Add perpendicular offset for curvature
        dx = end.x - start.x
        dy = end.y - start.y
        perp_x = -dy * 0.1 * np.sin(np.pi * t)
        perp_y = dx * 0.1 * np.sin(np.pi * t)

        path_points = [(start.x + t[i] * dx + perp_x[i], start.y + t[i] * dy + perp_y[i]) for i in range(n_steps)]

        # Calculate pathway statistics
        mobility_change = target_max["mobility_value"] - minimum["mobility_value"]
        path_length = np.sqrt(dx**2 + dy**2) * 111  # Approx km

        pathways.append(
            {
                "pathway_type": "escape",
                "geometry": LineString(path_points),
                "start_mobility": minimum["mobility_value"],
                "end_mobility": target_max["mobility_value"],
                "mobility_change": mobility_change,
                "length_km": path_length,
                "num_barriers": np.random.randint(0, 3),
            }
        )

    # 2. Create descent paths from some maxima
    for _, maximum in maxima.sample(n=min(3, len(maxima))).iterrows():
        if len(minima) == 0:
            continue

        target_min = minima.iloc[np.random.choice(len(minima))]

        start = maximum.geometry
        end = target_min.geometry

        n_steps = 6
        t = np.linspace(0, 1, n_steps)
        dx = end.x - start.x
        dy = end.y - start.y

        path_points = [(start.x + t[i] * dx, start.y + t[i] * dy) for i in range(n_steps)]

        mobility_change = target_min["mobility_value"] - maximum["mobility_value"]
        path_length = np.sqrt(dx**2 + dy**2) * 111

        pathways.append(
            {
                "pathway_type": "descent",
                "geometry": LineString(path_points),
                "start_mobility": maximum["mobility_value"],
                "end_mobility": target_min["mobility_value"],
                "mobility_change": mobility_change,
                "length_km": path_length,
                "num_barriers": np.random.randint(1, 4),
            }
        )

    # 3. Create stable paths along some saddles
    for _, saddle in saddles.iterrows():
        # Create a short horizontal path through the saddle
        start = saddle.geometry
        offset = 0.1  # degrees
        end_x = start.x + offset
        end_y = start.y

        path_points = [(start.x, start.y), (end_x, end_y)]

        pathways.append(
            {
                "pathway_type": "stable",
                "geometry": LineString(path_points),
                "start_mobility": saddle["mobility_value"],
                "end_mobility": saddle["mobility_value"],
                "mobility_change": 0.0,
                "length_km": offset * 111,
                "num_barriers": 1,
            }
        )

    pathway_gdf = gpd.GeoDataFrame(pathways, crs=cp_gdf.crs)
    logger.info(f"✓ Created {len(pathway_gdf)} pathways")
    logger.info(
        f"  Escape: {(pathway_gdf['pathway_type'] == 'escape').sum()}, "
        f"Descent: {(pathway_gdf['pathway_type'] == 'descent').sum()}, "
        f"Stable: {(pathway_gdf['pathway_type'] == 'stable').sum()}"
    )

    return pathway_gdf


def test_step4_pathways():
    """Test Step 4: Pathway arrows and flow visualization."""
    logger.info("=" * 60)
    logger.info("Step 4 Test: Pathway Arrows & Flow Visualization")
    logger.info("=" * 60)

    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "poverty_map_step4.html"

    try:
        # Load LSOA boundaries
        logger.info("\n1. Loading LSOA boundaries...")
        lsoa_gdf = load_lsoa_boundaries()
        logger.info(f"✓ Loaded {len(lsoa_gdf)} LSOAs")

        # Create synthetic mobility
        logger.info("\n2. Creating synthetic mobility proxy...")
        np.random.seed(42)
        bounds = lsoa_gdf.geometry.bounds
        y_coords = (bounds["miny"] + bounds["maxy"]) / 2
        y_norm = (y_coords - y_coords.min()) / (y_coords.max() - y_coords.min())
        mobility_proxy = 0.3 + 0.5 * y_norm + 0.1 * np.random.randn(len(lsoa_gdf))
        mobility_proxy = np.clip(mobility_proxy, 0.0, 1.0)
        lsoa_gdf["mobility_proxy"] = mobility_proxy
        logger.info("  Generated mobility values")

        # Create basins
        logger.info("\n3. Creating mock basins...")
        basin_gdf = create_mock_basins(lsoa_gdf, n_basins=10)

        # Create critical points
        logger.info("\n4. Creating mock critical points...")
        cp_gdf = create_mock_critical_points(basin_gdf, lsoa_gdf)

        # Create pathways
        logger.info("\n5. Creating mock pathways...")
        pathway_gdf = create_mock_pathways(cp_gdf, basin_gdf)

        # Create map
        logger.info("\n6. Creating interactive map with pathways...")
        m = create_base_map()

        m = add_lsoa_choropleth(m, lsoa_gdf, value_column="mobility_proxy", fill_opacity=0.5)

        m = add_basin_overlay(m, basin_gdf, fill_opacity=0.1)

        m = add_critical_points(m, cp_gdf, marker_size=8)

        m = add_pathway_arrows(m, pathway_gdf, pathway_type_column="pathway_type", arrow_weight=3.0)

        folium.LayerControl(position="topright").add_to(m)

        m.save(str(output_path))
        logger.info("✓ Map created successfully")
        logger.info(f"  Output: {output_path}")

        logger.info("\n" + "=" * 60)
        logger.info("Step 4 Test Complete!")
        logger.info("=" * 60)
        logger.info(f"\nMap saved to: {output_path}")
        logger.info("\nYou should see:")
        logger.info("  - LSOA mobility surface")
        logger.info("  - Basin polygons")
        logger.info("  - Critical point markers")
        logger.info("  - Green arrows = Escape paths (upward mobility)")
        logger.info("  - Red dashed = Descent paths (downward)")
        logger.info("  - Blue dashed = Stable paths")
        logger.info("  - Click arrows for pathway details")
        logger.info("  - Layer control for all elements")

        return True

    except Exception as e:
        logger.error(f"✗ Failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_step4_pathways()
    exit(0 if success else 1)
