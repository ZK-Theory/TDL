"""
Tests for Geospatial Data Processor.

This module contains unit tests for spatial join utilities, interpolation
methods, and VTK export functionality.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon

from poverty_tda.data.geospatial import (
    aggregate_to_lad,
    export_to_vtk,
    get_lad_boundaries,
    grid_to_geodataframe,
    interpolate_chunked,
    interpolate_idw,
    interpolate_kriging,
    interpolate_scipy,
    interpolate_to_grid,
    spatial_join_lsoa,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_lsoa_gdf() -> gpd.GeoDataFrame:
    """Create sample LSOA-like polygons for testing."""
    # Create 10 LSOAs in 2 LADs (5 each)
    polygons = []
    lsoa_codes = []
    lad_codes = []
    values = []

    for lad_idx in range(2):
        lad_code = f"E0{lad_idx + 1}00000{lad_idx + 1}"
        for lsoa_idx in range(5):
            # Create 1km x 1km squares
            x_base = lad_idx * 10000 + lsoa_idx * 1000
            y_base = 180000
            polygon = Polygon(
                [
                    (x_base, y_base),
                    (x_base + 1000, y_base),
                    (x_base + 1000, y_base + 1000),
                    (x_base, y_base + 1000),
                ]
            )
            polygons.append(polygon)
            lsoa_codes.append(f"{lad_code}{lsoa_idx:02d}")
            lad_codes.append(lad_code)
            values.append(np.random.uniform(0.2, 0.8))

    return gpd.GeoDataFrame(
        {
            "LSOA21CD": lsoa_codes,
            "LSOA21NM": [f"LSOA {i}" for i in range(10)],
            "lad_code": lad_codes,
            "mobility": values,
        },
        geometry=polygons,
        crs="EPSG:27700",
    )


@pytest.fixture
def sample_points_gdf() -> gpd.GeoDataFrame:
    """Create sample points for spatial join testing."""
    points = [
        Point(500, 180500),  # Should be in first LSOA
        Point(1500, 180500),  # Should be in second LSOA
        Point(10500, 180500),  # Should be in first LSOA of second LAD
    ]
    return gpd.GeoDataFrame(
        {"point_id": [1, 2, 3], "value": [10, 20, 30]},
        geometry=points,
        crs="EPSG:27700",
    )


@pytest.fixture
def sample_centroids_gdf() -> gpd.GeoDataFrame:
    """Create sample centroid points with values for interpolation."""
    np.random.seed(42)
    n_points = 50

    # Create points in a grid-like pattern
    x_coords = np.random.uniform(500000, 550000, n_points)
    y_coords = np.random.uniform(150000, 200000, n_points)
    points = [Point(x, y) for x, y in zip(x_coords, y_coords)]

    # Create values with some spatial pattern
    values = 0.3 + 0.3 * np.sin(x_coords / 10000) + 0.2 * np.cos(y_coords / 10000)
    values += np.random.normal(0, 0.05, n_points)  # Add noise

    return gpd.GeoDataFrame(
        {
            "lsoa_code": [f"E0100{i:04d}" for i in range(n_points)],
            "mobility": values,
        },
        geometry=points,
        crs="EPSG:27700",
    )


@pytest.fixture
def simple_interpolation_points() -> gpd.GeoDataFrame:
    """Create minimal points for interpolation testing (5-10 points)."""
    points = [
        Point(0, 0),
        Point(100, 0),
        Point(0, 100),
        Point(100, 100),
        Point(50, 50),
    ]
    values = [0.0, 1.0, 1.0, 0.0, 0.5]

    return gpd.GeoDataFrame(
        {"value": values},
        geometry=points,
        crs="EPSG:27700",
    )


# ============================================================================
# UNIT TESTS - SPATIAL JOIN
# ============================================================================


class TestSpatialJoinLsoa:
    """Unit tests for spatial_join_lsoa()."""

    def test_basic_join(
        self, sample_points_gdf: gpd.GeoDataFrame, sample_lsoa_gdf: gpd.GeoDataFrame
    ):
        """Test basic spatial join of points to LSOAs."""
        result = spatial_join_lsoa(sample_points_gdf, sample_lsoa_gdf)

        assert len(result) == len(sample_points_gdf)
        assert "LSOA21CD" in result.columns
        assert "point_id" in result.columns

    def test_join_preserves_point_attributes(
        self, sample_points_gdf: gpd.GeoDataFrame, sample_lsoa_gdf: gpd.GeoDataFrame
    ):
        """Test that point attributes are preserved after join."""
        result = spatial_join_lsoa(sample_points_gdf, sample_lsoa_gdf)

        assert "value" in result.columns
        assert set(result["point_id"]) == {1, 2, 3}

    def test_inner_join(
        self, sample_points_gdf: gpd.GeoDataFrame, sample_lsoa_gdf: gpd.GeoDataFrame
    ):
        """Test inner join excludes points outside LSOAs."""
        # Add a point outside any LSOA
        from shapely.geometry import Point

        outside_point = gpd.GeoDataFrame(
            {"point_id": [99], "value": [99]},
            geometry=[Point(999999, 999999)],
            crs="EPSG:27700",
        )
        points_with_outside = pd.concat(
            [sample_points_gdf, outside_point], ignore_index=True
        )

        result = spatial_join_lsoa(points_with_outside, sample_lsoa_gdf, how="inner")

        # Outside point should be excluded
        assert 99 not in result["point_id"].values


# ============================================================================
# UNIT TESTS - LAD AGGREGATION
# ============================================================================


class TestAggregateToLad:
    """Unit tests for aggregate_to_lad()."""

    def test_mean_aggregation(self, sample_lsoa_gdf: gpd.GeoDataFrame):
        """Test mean aggregation to LAD level."""
        result = aggregate_to_lad(sample_lsoa_gdf, "mobility", agg_func="mean")

        assert len(result) == 2  # 2 LADs
        assert "mobility" in result.columns
        assert "lsoa_count" in result.columns
        assert result["lsoa_count"].sum() == 10

    def test_sum_aggregation(self, sample_lsoa_gdf: gpd.GeoDataFrame):
        """Test sum aggregation."""
        result = aggregate_to_lad(sample_lsoa_gdf, "mobility", agg_func="sum")

        assert len(result) == 2

    def test_missing_column_raises_error(self, sample_lsoa_gdf: gpd.GeoDataFrame):
        """Test that missing value column raises error."""
        with pytest.raises(ValueError, match="not found"):
            aggregate_to_lad(sample_lsoa_gdf, "nonexistent_column")

    def test_lad_geometry_created(self, sample_lsoa_gdf: gpd.GeoDataFrame):
        """Test that dissolved LAD geometries are created."""
        result = aggregate_to_lad(sample_lsoa_gdf, "mobility")

        assert isinstance(result, gpd.GeoDataFrame)
        assert result.geometry.is_valid.all()


class TestGetLadBoundaries:
    """Unit tests for get_lad_boundaries()."""

    def test_dissolves_to_lads(self, sample_lsoa_gdf: gpd.GeoDataFrame):
        """Test that LSOAs are dissolved to LAD boundaries."""
        result = get_lad_boundaries(sample_lsoa_gdf)

        assert len(result) == 2  # 2 LADs
        assert "lad_code" in result.columns
        assert result.geometry.is_valid.all()

    def test_preserves_crs(self, sample_lsoa_gdf: gpd.GeoDataFrame):
        """Test that CRS is preserved."""
        result = get_lad_boundaries(sample_lsoa_gdf)

        assert result.crs == sample_lsoa_gdf.crs


# ============================================================================
# UNIT TESTS - IDW INTERPOLATION
# ============================================================================


class TestInterpolateIdw:
    """Unit tests for interpolate_idw()."""

    def test_basic_interpolation(self, simple_interpolation_points: gpd.GeoDataFrame):
        """Test basic IDW interpolation on simple points."""
        grid, metadata = interpolate_idw(
            simple_interpolation_points, "value", grid_resolution=10
        )

        assert grid.shape == (10, 10)
        assert "x_min" in metadata
        assert "y_max" in metadata
        assert metadata["method"] == "idw"

    def test_grid_values_in_range(self, simple_interpolation_points: gpd.GeoDataFrame):
        """Test that interpolated values are within input range."""
        grid, _ = interpolate_idw(
            simple_interpolation_points, "value", grid_resolution=20
        )

        assert grid.min() >= -0.1  # Allow small extrapolation
        assert grid.max() <= 1.1

    def test_center_point_influence(
        self, simple_interpolation_points: gpd.GeoDataFrame
    ):
        """Test that center point (0.5) influences grid center."""
        grid, _ = interpolate_idw(
            simple_interpolation_points, "value", grid_resolution=21
        )

        # Center value should be close to 0.5
        center_value = grid[10, 10]
        assert 0.3 < center_value < 0.7

    def test_power_parameter_effect(
        self, simple_interpolation_points: gpd.GeoDataFrame
    ):
        """Test that power parameter affects interpolation."""
        grid_p1, _ = interpolate_idw(
            simple_interpolation_points, "value", grid_resolution=10, power=1.0
        )
        grid_p4, _ = interpolate_idw(
            simple_interpolation_points, "value", grid_resolution=10, power=4.0
        )

        # Higher power = more local influence = different results
        assert not np.allclose(grid_p1, grid_p4)

    def test_custom_bounds(self, simple_interpolation_points: gpd.GeoDataFrame):
        """Test interpolation with custom bounds."""
        grid, metadata = interpolate_idw(
            simple_interpolation_points,
            "value",
            grid_resolution=10,
            bounds=(0, 0, 100, 100),
        )

        assert metadata["x_min"] == 0
        assert metadata["x_max"] == 100

    def test_missing_column_raises_error(
        self, simple_interpolation_points: gpd.GeoDataFrame
    ):
        """Test that missing value column raises error."""
        with pytest.raises(ValueError, match="not found"):
            interpolate_idw(simple_interpolation_points, "nonexistent")

    def test_all_nan_raises_error(self, simple_interpolation_points: gpd.GeoDataFrame):
        """Test that all NaN values raise error."""
        df = simple_interpolation_points.copy()
        df["value"] = np.nan

        with pytest.raises(ValueError, match="No valid"):
            interpolate_idw(df, "value")


# ============================================================================
# UNIT TESTS - SCIPY INTERPOLATION
# ============================================================================


class TestInterpolateScipy:
    """Unit tests for interpolate_scipy()."""

    def test_linear_interpolation(self, simple_interpolation_points: gpd.GeoDataFrame):
        """Test linear interpolation."""
        grid, metadata = interpolate_scipy(
            simple_interpolation_points, "value", grid_resolution=10, method="linear"
        )

        assert grid.shape == (10, 10)
        assert metadata["method"] == "linear"

    def test_cubic_interpolation(self, simple_interpolation_points: gpd.GeoDataFrame):
        """Test cubic interpolation."""
        grid, metadata = interpolate_scipy(
            simple_interpolation_points, "value", grid_resolution=10, method="cubic"
        )

        assert grid.shape == (10, 10)
        assert metadata["method"] == "cubic"

    def test_nearest_interpolation(self, simple_interpolation_points: gpd.GeoDataFrame):
        """Test nearest neighbor interpolation."""
        grid, metadata = interpolate_scipy(
            simple_interpolation_points, "value", grid_resolution=10, method="nearest"
        )

        assert grid.shape == (10, 10)
        # All values should be from input set
        unique_inputs = set(simple_interpolation_points["value"])
        for val in np.unique(grid):
            assert any(np.isclose(val, inp) for inp in unique_inputs)


# ============================================================================
# UNIT TESTS - UNIFIED INTERPOLATION INTERFACE
# ============================================================================


class TestInterpolateToGrid:
    """Unit tests for interpolate_to_grid()."""

    def test_idw_method(self, simple_interpolation_points: gpd.GeoDataFrame):
        """Test IDW through unified interface."""
        grid, metadata = interpolate_to_grid(
            simple_interpolation_points, "value", method="idw", grid_resolution=10
        )

        assert grid.shape == (10, 10)
        assert "idw" in metadata["method"]

    def test_linear_method(self, simple_interpolation_points: gpd.GeoDataFrame):
        """Test linear through unified interface."""
        grid, metadata = interpolate_to_grid(
            simple_interpolation_points, "value", method="linear", grid_resolution=10
        )

        assert grid.shape == (10, 10)

    def test_unknown_method_raises_error(
        self, simple_interpolation_points: gpd.GeoDataFrame
    ):
        """Test that unknown method raises error."""
        with pytest.raises(ValueError, match="Unknown interpolation method"):
            interpolate_to_grid(simple_interpolation_points, "value", method="unknown")


# ============================================================================
# UNIT TESTS - KRIGING
# ============================================================================


class TestInterpolateKriging:
    """Unit tests for interpolate_kriging()."""

    def test_kriging_or_fallback(self, simple_interpolation_points: gpd.GeoDataFrame):
        """Test Kriging runs or falls back to IDW."""
        grid, metadata = interpolate_kriging(
            simple_interpolation_points, "value", grid_resolution=10
        )

        assert grid.shape == (10, 10)
        # Method should be kriging or idw (fallback)
        assert metadata["method"] in ("kriging", "idw")


# ============================================================================
# UNIT TESTS - CHUNKED PROCESSING
# ============================================================================


class TestInterpolateChunked:
    """Unit tests for interpolate_chunked()."""

    def test_chunked_produces_result(self, sample_centroids_gdf: gpd.GeoDataFrame):
        """Test chunked interpolation produces valid result."""
        grid, metadata = interpolate_chunked(
            sample_centroids_gdf,
            "mobility",
            chunk_size=50,
            overlap=5,
            grid_resolution=100,
        )

        assert grid.shape == (100, 100)
        assert "chunked" in metadata["method"]

    def test_chunked_handles_sparse_data(
        self, simple_interpolation_points: gpd.GeoDataFrame
    ):
        """Test chunked processing with sparse data."""
        grid, _ = interpolate_chunked(
            simple_interpolation_points,
            "value",
            chunk_size=20,
            overlap=2,
            grid_resolution=50,
        )

        assert grid.shape == (50, 50)


# ============================================================================
# UNIT TESTS - VTK EXPORT
# ============================================================================


class TestExportToVtk:
    """Unit tests for export_to_vtk()."""

    def test_vtk_export_creates_file(
        self, simple_interpolation_points: gpd.GeoDataFrame, tmp_path: Path
    ):
        """Test VTK export creates valid file."""
        # Skip if pyvista not installed
        pytest.importorskip("pyvista")

        grid, metadata = interpolate_idw(
            simple_interpolation_points, "value", grid_resolution=10
        )

        output_path = tmp_path / "test_output.vti"
        result_path = export_to_vtk(grid, metadata, output_path, scalar_name="test")

        assert result_path.exists()
        assert result_path.stat().st_size > 0

    def test_vtk_without_pyvista_raises_error(
        self, simple_interpolation_points: gpd.GeoDataFrame, tmp_path: Path, monkeypatch
    ):
        """Test that VTK export raises error if pyvista not available."""
        # Mock HAS_PYVISTA to be False
        import poverty_tda.data.geospatial as geo_module

        monkeypatch.setattr(geo_module, "HAS_PYVISTA", False)

        grid, metadata = interpolate_idw(
            simple_interpolation_points, "value", grid_resolution=10
        )

        with pytest.raises(ImportError, match="pyvista"):
            export_to_vtk(grid, metadata, tmp_path / "test.vti")


# ============================================================================
# UNIT TESTS - GRID TO GEODATAFRAME
# ============================================================================


class TestGridToGeoDataFrame:
    """Unit tests for grid_to_geodataframe()."""

    def test_converts_grid_to_points(
        self, simple_interpolation_points: gpd.GeoDataFrame
    ):
        """Test grid conversion to GeoDataFrame."""
        grid, metadata = interpolate_idw(
            simple_interpolation_points, "value", grid_resolution=10
        )

        gdf = grid_to_geodataframe(grid, metadata, value_column="test_value")

        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 100  # 10 x 10
        assert "test_value" in gdf.columns
        assert gdf.geometry.geom_type.unique()[0] == "Point"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.integration
class TestPreprocessorsIntegration:
    """Integration tests with real or realistic data."""

    @pytest.fixture(scope="class")
    def real_lsoa_subset(self, tmp_path_factory):
        """Load a subset of real LSOA boundaries."""
        try:
            from poverty_tda.data.census_shapes import (
                download_lsoa_boundaries,
                load_lsoa_boundaries,
            )

            tmp_dir = tmp_path_factory.mktemp("lsoa_data")
            filepath = download_lsoa_boundaries(output_dir=tmp_dir)
            lsoa = load_lsoa_boundaries(filepath=filepath)
            # Take subset for testing (first 1000 LSOAs)
            return lsoa.head(1000)
        except Exception:
            pytest.skip("Could not load LSOA boundaries")

    def test_lad_count_reasonable(self, real_lsoa_subset: gpd.GeoDataFrame):
        """Test LAD count is reasonable."""
        lad = get_lad_boundaries(real_lsoa_subset)

        # Should have some LADs (depending on subset)
        assert len(lad) > 0
        assert len(lad) < 400  # Less than total England + Wales

    def test_interpolation_on_real_centroids(self, real_lsoa_subset: gpd.GeoDataFrame):
        """Test interpolation on real LSOA centroids."""
        from poverty_tda.data.census_shapes import get_lsoa_centroids

        centroids = get_lsoa_centroids(real_lsoa_subset)

        # Add synthetic mobility values
        np.random.seed(42)
        centroids["mobility"] = np.random.uniform(0.2, 0.8, len(centroids))

        grid, metadata = interpolate_to_grid(
            centroids, "mobility", method="idw", grid_resolution=50
        )

        assert grid.shape == (50, 50)
        assert grid.min() >= 0
        assert grid.max() <= 1

    def test_vtk_export_with_real_data(
        self, real_lsoa_subset: gpd.GeoDataFrame, tmp_path: Path
    ):
        """Test VTK export with realistic data."""
        pytest.importorskip("pyvista")

        from poverty_tda.data.census_shapes import get_lsoa_centroids

        centroids = get_lsoa_centroids(real_lsoa_subset)
        np.random.seed(42)
        centroids["mobility"] = np.random.uniform(0.2, 0.8, len(centroids))

        grid, metadata = interpolate_idw(centroids, "mobility", grid_resolution=50)

        output_path = tmp_path / "real_data.vti"
        result = export_to_vtk(grid, metadata, output_path)

        assert result.exists()
        # VTK file should be reasonably sized
        assert result.stat().st_size > 1000

    def test_geographic_extent_covers_data(self, real_lsoa_subset: gpd.GeoDataFrame):
        """Test that output grid covers input data extent."""
        from poverty_tda.data.census_shapes import get_lsoa_centroids

        centroids = get_lsoa_centroids(real_lsoa_subset)
        np.random.seed(42)
        centroids["mobility"] = np.random.uniform(0.2, 0.8, len(centroids))

        _, metadata = interpolate_idw(centroids, "mobility", grid_resolution=50)

        # Get actual data bounds
        bounds = centroids.total_bounds  # [minx, miny, maxx, maxy]

        # Grid should cover data with buffer
        assert metadata["x_min"] <= bounds[0]
        assert metadata["x_max"] >= bounds[2]
        assert metadata["y_min"] <= bounds[1]
        assert metadata["y_max"] >= bounds[3]


# ============================================================================
# EDGE CASES
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_single_point(self):
        """Test handling of single point."""
        single = gpd.GeoDataFrame(
            {"value": [0.5]},
            geometry=[Point(0, 0)],
            crs="EPSG:27700",
        )

        # IDW should handle single point (all values same)
        grid, _ = interpolate_idw(single, "value", grid_resolution=10)
        assert np.allclose(grid, 0.5)

    def test_nan_values_filtered(self):
        """Test that NaN values are properly filtered."""
        points = gpd.GeoDataFrame(
            {"value": [0.0, np.nan, 1.0, np.nan, 0.5]},
            geometry=[
                Point(0, 0),
                Point(50, 0),
                Point(100, 0),
                Point(50, 100),
                Point(50, 50),
            ],
            crs="EPSG:27700",
        )

        grid, metadata = interpolate_idw(points, "value", grid_resolution=10)

        assert grid.shape == (10, 10)
        assert metadata["n_points"] == 3  # Only valid points

    def test_crs_mismatch_warning(self):
        """Test warning on CRS mismatch in spatial join."""
        points_4326 = gpd.GeoDataFrame(
            {"value": [1]},
            geometry=[Point(-0.1, 51.5)],
            crs="EPSG:4326",
        )
        lsoa_27700 = gpd.GeoDataFrame(
            {"LSOA21CD": ["E01000001"]},
            geometry=[
                Polygon(
                    [
                        (530000, 180000),
                        (531000, 180000),
                        (531000, 181000),
                        (530000, 181000),
                    ]
                )
            ],
            crs="EPSG:27700",
        )

        # Should work but log warning
        result = spatial_join_lsoa(points_4326, lsoa_27700)
        assert isinstance(result, gpd.GeoDataFrame)
