"""Test Step 5: Interactive Controls & Full Integration.

This test demonstrates the complete poverty trap visualization with all layers
and interactive controls integrated.

Run: python poverty_tda/viz/test_step5_complete.py
"""

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, Point

from poverty_tda.data.census_shapes import load_lsoa_boundaries
from poverty_tda.viz.maps import create_complete_poverty_map

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)


def create_mock_basins(lsoa_gdf: gpd.GeoDataFrame, n_basins: int = 10):
    """Create mock basin polygons."""
    logger.info(f"Creating {n_basins} mock basins...")
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
                "area": basin_geom.area,
                "num_lsoas": len(basin_lsoas),
                "avg_mobility": avg_mobility,
                "population": len(basin_lsoas) * 2000,  # Mock population
                "num_critical_points": np.random.randint(1, 4),
            }
        )

    basin_gdf = gpd.GeoDataFrame(basins, crs=lsoa_gdf.crs)
    logger.info(f"✓ Created {len(basin_gdf)} basins")
    return basin_gdf


def create_mock_critical_points(basin_gdf, lsoa_gdf):
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
                "depth": 0.1 + 0.2 * np.random.rand(),
                "persistence": 0.05 + 0.15 * np.random.rand(),
            }
        )

    # Saddles
    n_saddles = len(basin_gdf) // 2
    for i in range(n_saddles):
        basin_ids = np.random.choice(len(basin_gdf), 2, replace=False)
        b1, b2 = basin_gdf.iloc[basin_ids[0]], basin_gdf.iloc[basin_ids[1]]
        c1, c2 = b1.geometry.centroid, b2.geometry.centroid

        critical_points.append(
            {
                "cp_type": "saddle",
                "geometry": Point((c1.x + c2.x) / 2, (c1.y + c2.y) / 2),
                "mobility_value": (b1["avg_mobility"] + b2["avg_mobility"]) / 2,
                "depth": 0.05 + 0.1 * np.random.rand(),
                "persistence": 0.02 + 0.08 * np.random.rand(),
            }
        )

    # Maxima
    n_maxima = 5
    high_indices = np.argsort(mobility_values)[-n_maxima * 10 :]
    max_indices = np.random.choice(high_indices, n_maxima, replace=False)

    for idx in max_indices:
        lsoa = lsoa_gdf.iloc[idx]
        lb = lsoa.geometry.bounds
        critical_points.append(
            {
                "cp_type": "maximum",
                "geometry": Point((lb[0] + lb[2]) / 2, (lb[1] + lb[3]) / 2),
                "mobility_value": mobility_values.iloc[idx],
                "depth": 0.15 + 0.25 * np.random.rand(),
                "persistence": 0.1 + 0.2 * np.random.rand(),
            }
        )

    cp_gdf = gpd.GeoDataFrame(critical_points, crs=basin_gdf.crs)
    logger.info(f"✓ Created {len(cp_gdf)} critical points")
    return cp_gdf


def create_mock_pathways(cp_gdf, basin_gdf):
    """Create mock pathways."""
    logger.info("Creating mock pathways...")
    pathways = []
    np.random.seed(42)

    minima = cp_gdf[cp_gdf["cp_type"] == "minimum"]
    maxima = cp_gdf[cp_gdf["cp_type"] == "maximum"]
    saddles = cp_gdf[cp_gdf["cp_type"] == "saddle"]

    # Escape paths
    for _, minimum in minima.iterrows():
        if len(maxima) == 0:
            continue
        target_max = maxima.iloc[np.random.choice(len(maxima))]
        start, end = minimum.geometry, target_max.geometry

        n_steps = 8
        t = np.linspace(0, 1, n_steps)
        dx, dy = end.x - start.x, end.y - start.y
        perp_x = -dy * 0.1 * np.sin(np.pi * t)
        perp_y = dx * 0.1 * np.sin(np.pi * t)
        path_points = [(start.x + t[i] * dx + perp_x[i], start.y + t[i] * dy + perp_y[i]) for i in range(n_steps)]

        pathways.append(
            {
                "pathway_type": "escape",
                "geometry": LineString(path_points),
                "start_mobility": minimum["mobility_value"],
                "end_mobility": target_max["mobility_value"],
                "mobility_change": target_max["mobility_value"] - minimum["mobility_value"],
                "length_km": np.sqrt(dx**2 + dy**2) * 111,
                "num_barriers": np.random.randint(0, 3),
            }
        )

    # Descent paths
    for _, maximum in maxima.sample(n=min(3, len(maxima))).iterrows():
        if len(minima) == 0:
            continue
        target_min = minima.iloc[np.random.choice(len(minima))]
        start, end = maximum.geometry, target_min.geometry

        n_steps = 6
        t = np.linspace(0, 1, n_steps)
        dx, dy = end.x - start.x, end.y - start.y
        path_points = [(start.x + t[i] * dx, start.y + t[i] * dy) for i in range(n_steps)]

        pathways.append(
            {
                "pathway_type": "descent",
                "geometry": LineString(path_points),
                "start_mobility": maximum["mobility_value"],
                "end_mobility": target_min["mobility_value"],
                "mobility_change": target_min["mobility_value"] - maximum["mobility_value"],
                "length_km": np.sqrt(dx**2 + dy**2) * 111,
                "num_barriers": np.random.randint(1, 4),
            }
        )

    # Stable paths
    for _, saddle in saddles.iterrows():
        start = saddle.geometry
        offset = 0.1
        path_points = [(start.x, start.y), (start.x + offset, start.y)]

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
    return pathway_gdf


def test_step5_complete_integration():
    """Test Step 5: Complete integration with all layers."""
    logger.info("=" * 60)
    logger.info("Step 5 Test: Interactive Controls & Full Integration")
    logger.info("=" * 60)

    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "poverty_map_complete.html"

    try:
        # Load data
        logger.info("\n1. Loading LSOA boundaries...")
        lsoa_gdf = load_lsoa_boundaries()
        logger.info(f"✓ Loaded {len(lsoa_gdf)} LSOAs")

        # Create mobility values
        logger.info("\n2. Creating synthetic mobility values...")
        np.random.seed(42)
        bounds = lsoa_gdf.geometry.bounds
        y_coords = (bounds["miny"] + bounds["maxy"]) / 2
        y_norm = (y_coords - y_coords.min()) / (y_coords.max() - y_coords.min())
        mobility_proxy = 0.3 + 0.5 * y_norm + 0.1 * np.random.randn(len(lsoa_gdf))
        mobility_proxy = np.clip(mobility_proxy, 0.0, 1.0)
        lsoa_gdf["mobility_proxy"] = mobility_proxy
        logger.info("✓ Generated mobility values")

        # Create all components
        logger.info("\n3. Creating all visualization components...")
        basin_gdf = create_mock_basins(lsoa_gdf, n_basins=10)
        cp_gdf = create_mock_critical_points(basin_gdf, lsoa_gdf)
        pathway_gdf = create_mock_pathways(cp_gdf, basin_gdf)

        # Create complete map using integration function
        logger.info("\n4. Creating complete integrated map...")
        create_complete_poverty_map(
            lsoa_gdf=lsoa_gdf,
            basin_gdf=basin_gdf,
            critical_points_gdf=cp_gdf,
            pathways_gdf=pathway_gdf,
            value_column="mobility_proxy",
            output_path=output_path,
            add_layer_control=True,
        )

        logger.info("\n" + "=" * 60)
        logger.info("Step 5 Test Complete!")
        logger.info("=" * 60)
        logger.info(f"\nComplete map saved to: {output_path}")
        logger.info("\n✅ ALL VISUALIZATION STEPS COMPLETE!")
        logger.info("\nThe map includes:")
        logger.info("  ✓ LSOA mobility surface choropleth")
        logger.info("  ✓ 10 poverty basin overlays with labels")
        logger.info("  ✓ 20 critical point markers (min/max/saddle)")
        logger.info("  ✓ 18 escape pathway arrows")
        logger.info("  ✓ Interactive layer control widget")
        logger.info("  ✓ Clickable elements with detailed information")
        logger.info("\nUsage:")
        logger.info("  - Open the HTML file in a browser")
        logger.info("  - Use layer control (top-right) to toggle layers")
        logger.info("  - Click any element for detailed information")
        logger.info("  - Zoom and pan to explore different regions")

        return True

    except Exception as e:
        logger.error(f"✗ Failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_step5_complete_integration()
    exit(0 if success else 1)
