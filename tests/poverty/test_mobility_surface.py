"""
Tests for mobility surface construction module.

This module tests the interpolation pipeline from LSOA point data
to continuous mobility surfaces with VTK export.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import Polygon

from poverty_tda.topology.mobility_surface import (
    CRS_BRITISH_NATIONAL_GRID,
    ENGLAND_WALES_BOUNDS,
    build_mobility_surface,
    create_mobility_grid,
    export_mobility_vtk,
    interpolate_chunked,
    interpolate_surface,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_lsoa_gdf() -> gpd.GeoDataFrame:
    """Create a sample GeoDataFrame with LSOA-like polygons."""
    # Create grid of polygons in British National Grid coordinates
    # Using a small subset of the England/Wales bounding box
    base_x = 400000  # Central England
    base_y = 300000

    polygons = []
    codes = []
    names = []

    for i in range(10):
        for j in range(10):
            x = base_x + i * 1000
            y = base_y + j * 1000
            poly = Polygon([(x, y), (x + 1000, y), (x + 1000, y + 1000), (x, y + 1000)])
            polygons.append(poly)
            codes.append(f"E01{i:02d}{j:03d}")
            names.append(f"Test LSOA {i:02d}{j:03d}")

    return gpd.GeoDataFrame(
        {"LSOA21CD": codes, "LSOA21NM": names},
        geometry=polygons,
        crs=CRS_BRITISH_NATIONAL_GRID,
    )


@pytest.fixture
def sample_mobility_values() -> np.ndarray:
    """Create sample mobility values for 100 LSOAs."""
    # Create a gradient pattern for predictable interpolation
    np.random.seed(42)
    # Base gradient + some noise
    base = np.linspace(0.3, 0.7, 100)
    noise = np.random.normal(0, 0.05, 100)
    return np.clip(base + noise, 0.0, 1.0)


@pytest.fixture
def sample_centroids() -> np.ndarray:
    """Create sample centroid coordinates."""
    base_x = 400000
    base_y = 300000
    centroids = []

    for i in range(10):
        for j in range(10):
            x = base_x + i * 1000 + 500  # Center of each 1000m cell
            y = base_y + j * 1000 + 500
            centroids.append([x, y])

    return np.array(centroids)


@pytest.fixture
def sample_grid() -> tuple[np.ndarray, np.ndarray]:
    """Create sample meshgrid for interpolation tests."""
    x = np.linspace(400000, 410000, 50)
    y = np.linspace(300000, 310000, 50)
    return np.meshgrid(x, y)


# ============================================================================
# TESTS - create_mobility_grid
# ============================================================================


class TestCreateMobilityGrid:
    """Tests for create_mobility_grid function."""

    def test_creates_grid_with_mobility_values(
        self,
        sample_lsoa_gdf: gpd.GeoDataFrame,
        sample_mobility_values: np.ndarray,
    ):
        """Test grid creation with explicit mobility values array."""
        centroids, values, grid_xy, metadata = create_mobility_grid(
            sample_lsoa_gdf,
            mobility_values=sample_mobility_values,
            resolution=100,
        )

        # Check centroids shape
        assert centroids.shape == (100, 2)
        assert values.shape == (100,)

        # Check grid shape
        assert grid_xy.shape == (100, 100, 2)

        # Check metadata
        assert metadata["resolution"] == 100
        assert metadata["n_points"] == 100
        assert metadata["crs"] == CRS_BRITISH_NATIONAL_GRID

    def test_creates_grid_with_mobility_column(
        self,
        sample_lsoa_gdf: gpd.GeoDataFrame,
        sample_mobility_values: np.ndarray,
    ):
        """Test grid creation with mobility column name."""
        gdf = sample_lsoa_gdf.copy()
        gdf["mobility"] = sample_mobility_values

        centroids, values, grid_xy, metadata = create_mobility_grid(
            gdf,
            mobility_column="mobility",
            resolution=100,
        )

        assert centroids.shape == (100, 2)
        assert values.shape == (100,)
        np.testing.assert_array_almost_equal(values, sample_mobility_values)

    def test_grid_covers_england_wales_bounds(
        self,
        sample_lsoa_gdf: gpd.GeoDataFrame,
        sample_mobility_values: np.ndarray,
    ):
        """Test that grid covers the full England/Wales bounding box."""
        _, _, grid_xy, metadata = create_mobility_grid(
            sample_lsoa_gdf,
            mobility_values=sample_mobility_values,
            resolution=50,
        )

        # Check bounds match expected
        assert metadata["x_min"] == ENGLAND_WALES_BOUNDS["x_min"]
        assert metadata["x_max"] == ENGLAND_WALES_BOUNDS["x_max"]
        assert metadata["y_min"] == ENGLAND_WALES_BOUNDS["y_min"]
        assert metadata["y_max"] == ENGLAND_WALES_BOUNDS["y_max"]

        # Check grid coordinates match bounds
        grid_x = grid_xy[:, :, 0]
        grid_y = grid_xy[:, :, 1]
        assert np.isclose(grid_x.min(), ENGLAND_WALES_BOUNDS["x_min"])
        assert np.isclose(grid_x.max(), ENGLAND_WALES_BOUNDS["x_max"])
        assert np.isclose(grid_y.min(), ENGLAND_WALES_BOUNDS["y_min"])
        assert np.isclose(grid_y.max(), ENGLAND_WALES_BOUNDS["y_max"])

    def test_raises_without_mobility_source(
        self,
        sample_lsoa_gdf: gpd.GeoDataFrame,
    ):
        """Test error when no mobility source provided."""
        with pytest.raises(ValueError, match="Must provide either"):
            create_mobility_grid(sample_lsoa_gdf)

    def test_raises_on_length_mismatch(
        self,
        sample_lsoa_gdf: gpd.GeoDataFrame,
    ):
        """Test error when mobility values length doesn't match GDF."""
        wrong_length = np.random.rand(50)  # 50 instead of 100

        with pytest.raises(ValueError, match="doesn't match"):
            create_mobility_grid(sample_lsoa_gdf, mobility_values=wrong_length)

    def test_raises_on_missing_column(
        self,
        sample_lsoa_gdf: gpd.GeoDataFrame,
    ):
        """Test error when mobility column doesn't exist."""
        with pytest.raises(ValueError, match="not found"):
            create_mobility_grid(sample_lsoa_gdf, mobility_column="nonexistent")

    def test_transforms_crs_if_needed(
        self,
        sample_lsoa_gdf: gpd.GeoDataFrame,
        sample_mobility_values: np.ndarray,
        caplog,
    ):
        """Test CRS transformation from WGS84 to BNG."""
        import logging

        # Transform to WGS84
        gdf_wgs84 = sample_lsoa_gdf.to_crs("EPSG:4326")

        with caplog.at_level(logging.WARNING):
            centroids, _, _, metadata = create_mobility_grid(
                gdf_wgs84,
                mobility_values=sample_mobility_values,
                resolution=50,
            )

        # Check that CRS warning was logged
        assert any("CRS" in record.message for record in caplog.records)

        # Centroids should be in BNG coordinates
        assert metadata["crs"] == CRS_BRITISH_NATIONAL_GRID


# ============================================================================
# TESTS - interpolate_surface
# ============================================================================


class TestInterpolateSurface:
    """Tests for interpolate_surface function."""

    def test_linear_interpolation(
        self,
        sample_centroids: np.ndarray,
        sample_mobility_values: np.ndarray,
        sample_grid: tuple[np.ndarray, np.ndarray],
    ):
        """Test linear interpolation produces valid surface."""
        grid_x, grid_y = sample_grid

        surface = interpolate_surface(
            sample_centroids,
            sample_mobility_values,
            grid_x,
            grid_y,
            method="linear",
        )

        # Check shape matches grid
        assert surface.shape == grid_x.shape

        # Check no NaN values (after filling)
        assert not np.isnan(surface).any()

    def test_cubic_interpolation(
        self,
        sample_centroids: np.ndarray,
        sample_mobility_values: np.ndarray,
        sample_grid: tuple[np.ndarray, np.ndarray],
    ):
        """Test cubic interpolation produces smooth surface."""
        grid_x, grid_y = sample_grid

        surface = interpolate_surface(
            sample_centroids,
            sample_mobility_values,
            grid_x,
            grid_y,
            method="cubic",
        )

        assert surface.shape == grid_x.shape
        assert not np.isnan(surface).any()

    def test_nearest_interpolation(
        self,
        sample_centroids: np.ndarray,
        sample_mobility_values: np.ndarray,
        sample_grid: tuple[np.ndarray, np.ndarray],
    ):
        """Test nearest neighbor interpolation."""
        grid_x, grid_y = sample_grid

        surface = interpolate_surface(
            sample_centroids,
            sample_mobility_values,
            grid_x,
            grid_y,
            method="nearest",
        )

        assert surface.shape == grid_x.shape
        # Nearest should never have NaN
        assert not np.isnan(surface).any()

    def test_preserves_value_range(
        self,
        sample_centroids: np.ndarray,
        sample_grid: tuple[np.ndarray, np.ndarray],
    ):
        """Test that interpolated values stay within reasonable bounds."""
        # Known values with specific range
        values = np.linspace(0.2, 0.8, len(sample_centroids))
        grid_x, grid_y = sample_grid

        surface = interpolate_surface(
            sample_centroids,
            values,
            grid_x,
            grid_y,
            method="linear",
        )

        # Values should be within [0, 1] (may slightly exceed due to interpolation)
        assert surface.min() >= -0.1
        assert surface.max() <= 1.1

    def test_handles_nan_input_values(
        self,
        sample_centroids: np.ndarray,
        sample_mobility_values: np.ndarray,
        sample_grid: tuple[np.ndarray, np.ndarray],
    ):
        """Test that NaN input values are handled correctly."""
        values_with_nan = sample_mobility_values.copy()
        values_with_nan[::10] = np.nan  # Set every 10th value to NaN

        grid_x, grid_y = sample_grid

        surface = interpolate_surface(
            sample_centroids,
            values_with_nan,
            grid_x,
            grid_y,
            method="linear",
        )

        # Surface should still be valid
        assert not np.isnan(surface).any()

    def test_raises_on_all_nan_values(
        self,
        sample_centroids: np.ndarray,
        sample_grid: tuple[np.ndarray, np.ndarray],
    ):
        """Test error when all input values are NaN."""
        all_nan = np.full(len(sample_centroids), np.nan)
        grid_x, grid_y = sample_grid

        with pytest.raises(ValueError, match="All input values are NaN"):
            interpolate_surface(sample_centroids, all_nan, grid_x, grid_y)

    def test_raises_on_shape_mismatch(
        self,
        sample_centroids: np.ndarray,
        sample_mobility_values: np.ndarray,
    ):
        """Test error when centroids and values have different lengths."""
        grid_x, grid_y = np.meshgrid(np.linspace(0, 1, 10), np.linspace(0, 1, 10))

        with pytest.raises(ValueError, match="centroids length"):
            interpolate_surface(
                sample_centroids[:-5],  # 95 points
                sample_mobility_values,  # 100 values
                grid_x,
                grid_y,
            )


# ============================================================================
# TESTS - interpolate_chunked
# ============================================================================


class TestInterpolateChunked:
    """Tests for memory-efficient chunked interpolation."""

    def test_chunked_produces_valid_surface(
        self,
        sample_centroids: np.ndarray,
        sample_mobility_values: np.ndarray,
        sample_grid: tuple[np.ndarray, np.ndarray],
    ):
        """Test chunked interpolation produces valid output."""
        grid_x, grid_y = sample_grid

        surface = interpolate_chunked(
            sample_centroids,
            sample_mobility_values,
            grid_x,
            grid_y,
            chunk_size=20,
            method="linear",
        )

        assert surface.shape == grid_x.shape
        assert not np.isnan(surface).any()

    def test_chunked_similar_to_full(
        self,
        sample_centroids: np.ndarray,
        sample_mobility_values: np.ndarray,
        sample_grid: tuple[np.ndarray, np.ndarray],
    ):
        """Test chunked interpolation produces similar results to full."""
        grid_x, grid_y = sample_grid

        full_surface = interpolate_surface(
            sample_centroids,
            sample_mobility_values,
            grid_x,
            grid_y,
            method="linear",
        )

        chunked_surface = interpolate_chunked(
            sample_centroids,
            sample_mobility_values,
            grid_x,
            grid_y,
            chunk_size=25,
            method="linear",
        )

        # Results should be similar (not identical due to edge effects)
        correlation = np.corrcoef(full_surface.ravel(), chunked_surface.ravel())[0, 1]
        assert correlation > 0.95

    def test_progress_callback(
        self,
        sample_centroids: np.ndarray,
        sample_mobility_values: np.ndarray,
        sample_grid: tuple[np.ndarray, np.ndarray],
    ):
        """Test progress callback is called correctly."""
        grid_x, grid_y = sample_grid
        progress_calls = []

        def callback(current, total):
            progress_calls.append((current, total))

        interpolate_chunked(
            sample_centroids,
            sample_mobility_values,
            grid_x,
            grid_y,
            chunk_size=25,
            progress_callback=callback,
        )

        # Should have been called multiple times
        assert len(progress_calls) > 0
        # Last call should have current == total
        assert progress_calls[-1][0] == progress_calls[-1][1]


# ============================================================================
# TESTS - export_mobility_vtk
# ============================================================================


class TestExportMobilityVtk:
    """Tests for VTK export functionality."""

    @pytest.fixture
    def sample_surface_data(
        self,
        sample_grid: tuple[np.ndarray, np.ndarray],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Create sample surface data for VTK export tests."""
        grid_x, grid_y = sample_grid
        # Create a simple gradient surface
        surface = (grid_x - grid_x.min()) / (grid_x.max() - grid_x.min())
        return grid_x, grid_y, surface

    def test_export_vti_format(
        self,
        sample_surface_data: tuple[np.ndarray, np.ndarray, np.ndarray],
        tmp_path: Path,
    ):
        """Test export to VTI (ImageData) format."""
        pytest.importorskip("pyvista", reason="pyvista not installed")

        grid_x, grid_y, surface = sample_surface_data
        output_path = tmp_path / "test_mobility.vti"

        result = export_mobility_vtk(grid_x, grid_y, surface, output_path)

        assert result.exists()
        assert result.suffix == ".vti"
        assert result.stat().st_size > 0

    def test_export_vts_format(
        self,
        sample_surface_data: tuple[np.ndarray, np.ndarray, np.ndarray],
        tmp_path: Path,
    ):
        """Test export to VTS (StructuredGrid) format."""
        pytest.importorskip("pyvista", reason="pyvista not installed")

        grid_x, grid_y, surface = sample_surface_data
        output_path = tmp_path / "test_mobility.vts"

        result = export_mobility_vtk(grid_x, grid_y, surface, output_path)

        assert result.exists()
        assert result.suffix == ".vts"
        assert result.stat().st_size > 0

    def test_vtk_file_readable(
        self,
        sample_surface_data: tuple[np.ndarray, np.ndarray, np.ndarray],
        tmp_path: Path,
    ):
        """Test that exported VTK file can be read back."""
        pv = pytest.importorskip("pyvista", reason="pyvista not installed")

        grid_x, grid_y, surface = sample_surface_data
        output_path = tmp_path / "test_mobility.vti"

        export_mobility_vtk(
            grid_x, grid_y, surface, output_path, scalar_name="mobility"
        )

        # Read back
        loaded = pv.read(str(output_path))

        # Check scalar field exists
        assert "mobility" in loaded.point_data
        assert len(loaded.point_data["mobility"]) == surface.size

    def test_custom_scalar_name(
        self,
        sample_surface_data: tuple[np.ndarray, np.ndarray, np.ndarray],
        tmp_path: Path,
    ):
        """Test custom scalar name in VTK export."""
        pv = pytest.importorskip("pyvista", reason="pyvista not installed")

        grid_x, grid_y, surface = sample_surface_data
        output_path = tmp_path / "test_mobility.vti"

        export_mobility_vtk(
            grid_x, grid_y, surface, output_path, scalar_name="my_mobility"
        )

        loaded = pv.read(str(output_path))
        assert "my_mobility" in loaded.point_data

    def test_raises_without_pyvista(
        self,
        sample_surface_data: tuple[np.ndarray, np.ndarray, np.ndarray],
        tmp_path: Path,
    ):
        """Test error when pyvista not available."""
        grid_x, grid_y, surface = sample_surface_data
        output_path = tmp_path / "test.vti"

        with patch("poverty_tda.topology.mobility_surface.HAS_PYVISTA", False):
            with pytest.raises(ImportError, match="pyvista is required"):
                export_mobility_vtk(grid_x, grid_y, surface, output_path)

    def test_raises_on_shape_mismatch(self, tmp_path: Path):
        """Test error when array shapes don't match."""
        grid_x = np.zeros((10, 10))
        grid_y = np.zeros((10, 10))
        surface = np.zeros((20, 20))  # Wrong shape

        with pytest.raises(ValueError, match="Shape mismatch"):
            export_mobility_vtk(grid_x, grid_y, surface, tmp_path / "test.vti")


# ============================================================================
# TESTS - build_mobility_surface (end-to-end)
# ============================================================================


class TestBuildMobilitySurface:
    """Tests for end-to-end pipeline."""

    def test_full_pipeline_with_vtk(
        self,
        sample_lsoa_gdf: gpd.GeoDataFrame,
        sample_mobility_values: np.ndarray,
        tmp_path: Path,
    ):
        """Test complete pipeline with VTK export."""
        pytest.importorskip("pyvista", reason="pyvista not installed")

        output_path = tmp_path / "mobility.vti"

        surface, metadata, vtk_path = build_mobility_surface(
            sample_lsoa_gdf,
            mobility_values=sample_mobility_values,
            output_path=output_path,
            resolution=50,
            method="linear",
        )

        # Check surface
        assert surface.shape == (50, 50)
        assert not np.isnan(surface).any()

        # Check metadata
        assert metadata["resolution"] == 50
        assert metadata["method"] == "linear"
        assert "value_min" in metadata
        assert "value_max" in metadata

        # Check VTK file
        assert vtk_path is not None
        assert vtk_path.exists()

    def test_pipeline_without_vtk(
        self,
        sample_lsoa_gdf: gpd.GeoDataFrame,
        sample_mobility_values: np.ndarray,
    ):
        """Test pipeline without VTK export."""
        surface, metadata, vtk_path = build_mobility_surface(
            sample_lsoa_gdf,
            mobility_values=sample_mobility_values,
            output_path=None,  # No VTK
            resolution=50,
        )

        assert surface.shape == (50, 50)
        assert vtk_path is None

    def test_pipeline_with_chunked(
        self,
        sample_lsoa_gdf: gpd.GeoDataFrame,
        sample_mobility_values: np.ndarray,
    ):
        """Test pipeline with chunked interpolation."""
        surface, metadata, _ = build_mobility_surface(
            sample_lsoa_gdf,
            mobility_values=sample_mobility_values,
            output_path=None,
            resolution=50,
            use_chunked=True,
            chunk_size=25,
        )

        assert surface.shape == (50, 50)
        assert not np.isnan(surface).any()


# ============================================================================
# TESTS - Synthetic data validation
# ============================================================================


class TestSyntheticDataValidation:
    """Tests using synthetic data with known properties."""

    def test_interpolation_accuracy_on_known_surface(self):
        """Test interpolation accuracy on a known analytical surface."""
        # Create known surface: z = x + y (linear gradient)
        np.random.seed(42)

        # Generate random points in a square
        n_points = 200
        x = np.random.uniform(0, 100, n_points)
        y = np.random.uniform(0, 100, n_points)
        z = x + y  # Known function

        centroids = np.column_stack([x, y])

        # Create grid
        grid_x, grid_y = np.meshgrid(
            np.linspace(10, 90, 50),  # Interior to avoid extrapolation
            np.linspace(10, 90, 50),
        )

        # Expected values
        expected = grid_x + grid_y

        # Interpolate
        surface = interpolate_surface(centroids, z, grid_x, grid_y, method="linear")

        # Check accuracy
        rmse = np.sqrt(np.mean((surface - expected) ** 2))
        assert rmse < 5.0  # Should be very accurate for linear function

    def test_interpolation_preserves_statistics(
        self,
        sample_centroids: np.ndarray,
        sample_grid: tuple[np.ndarray, np.ndarray],
    ):
        """Test that interpolation preserves basic statistics."""
        values = np.linspace(0.3, 0.7, len(sample_centroids))
        grid_x, grid_y = sample_grid

        surface = interpolate_surface(
            sample_centroids, values, grid_x, grid_y, method="linear"
        )

        # Mean should be similar to input mean
        input_mean = values.mean()
        output_mean = surface.mean()
        assert abs(output_mean - input_mean) < 0.15

        # Range should be approximately preserved (may slightly exceed)
        assert surface.min() > 0.0
        assert surface.max() < 1.0


# ============================================================================
# INTEGRATION WITH MORSE-SMALE TESTS
# ============================================================================


# Check if TTK environment is available
try:
    from poverty_tda.topology.morse_smale import check_ttk_environment

    TTK_AVAILABLE = check_ttk_environment()
except ImportError:
    TTK_AVAILABLE = False


@pytest.mark.skipif(not TTK_AVAILABLE, reason="TTK environment not available")
class TestMorseSmaleIntegration:
    """Tests for analyze_mobility_topology integration."""

    @pytest.fixture
    def synthetic_lsoa_gdf(self) -> gpd.GeoDataFrame:
        """Create synthetic LSOA data with clear topological features."""
        from shapely.geometry import box

        np.random.seed(42)
        n_lsoas = 200

        # Create grid of points
        x = np.random.uniform(100000, 200000, n_lsoas)
        y = np.random.uniform(100000, 200000, n_lsoas)

        # Create small polygons
        polygons = [box(xi - 100, yi - 100, xi + 100, yi + 100) for xi, yi in zip(x, y)]

        gdf = gpd.GeoDataFrame(
            {"lsoa_code": [f"E0{i:07d}" for i in range(n_lsoas)], "geometry": polygons},
            crs="EPSG:27700",
        )

        # Add mobility values with Gaussian peak at center
        cx, cy = 150000, 150000
        mobility = np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (20000**2))
        gdf["mobility_proxy"] = mobility

        return gdf

    def test_analyze_mobility_topology(self, synthetic_lsoa_gdf: gpd.GeoDataFrame):
        """Test the complete analysis pipeline."""
        from poverty_tda.topology import analyze_mobility_topology

        surface, meta, ms_result = analyze_mobility_topology(
            synthetic_lsoa_gdf,
            mobility_column="mobility_proxy",
            resolution=30,
            persistence_threshold=0.05,
        )

        # Check surface
        assert surface.shape == (30, 30)
        # Allow small negative values from cubic interpolation artifacts
        assert surface.min() >= -0.01
        assert surface.max() <= 1.5  # Some extrapolation allowed

        # Check metadata
        assert "n_maxima" in meta
        assert "n_minima" in meta
        assert "n_saddles" in meta

        # Check Morse-Smale result
        assert ms_result is not None
        assert len(ms_result.critical_points) >= 0

    def test_get_opportunity_hotspots(self, synthetic_lsoa_gdf: gpd.GeoDataFrame):
        """Test extracting opportunity hotspots."""
        from poverty_tda.topology import (
            analyze_mobility_topology,
            get_opportunity_hotspots,
        )

        _, _, ms_result = analyze_mobility_topology(
            synthetic_lsoa_gdf,
            mobility_column="mobility_proxy",
            resolution=30,
            persistence_threshold=0.0,
        )

        hotspots = get_opportunity_hotspots(ms_result, top_n=5)

        # Should return list of tuples
        assert isinstance(hotspots, list)
        for item in hotspots:
            assert len(item) == 3
            x, y, val = item
            assert isinstance(x, float)
            assert isinstance(y, float)
            assert isinstance(val, float)

    def test_get_mobility_barriers(self, synthetic_lsoa_gdf: gpd.GeoDataFrame):
        """Test extracting mobility barriers."""
        from poverty_tda.topology import (
            analyze_mobility_topology,
            get_mobility_barriers,
        )

        _, _, ms_result = analyze_mobility_topology(
            synthetic_lsoa_gdf,
            mobility_column="mobility_proxy",
            resolution=30,
            persistence_threshold=0.0,
        )

        barriers = get_mobility_barriers(ms_result, top_n=5)

        # Should return list of tuples
        assert isinstance(barriers, list)
        for item in barriers:
            assert len(item) == 3

        # Barriers should be sorted by value (lowest first)
        if len(barriers) > 1:
            values = [v for _, _, v in barriers]
            assert values == sorted(values)

    def test_analyze_with_output_path(
        self, synthetic_lsoa_gdf: gpd.GeoDataFrame, tmp_path: Path
    ):
        """Test analysis with VTK file output."""
        from poverty_tda.topology import analyze_mobility_topology

        vtk_path = tmp_path / "test_mobility.vti"

        surface, meta, ms_result = analyze_mobility_topology(
            synthetic_lsoa_gdf,
            mobility_column="mobility_proxy",
            output_path=vtk_path,
            resolution=25,
            persistence_threshold=0.05,
        )

        # VTK file should exist
        assert vtk_path.exists()

        # File should be readable
        import pyvista as pv

        grid = pv.read(str(vtk_path))
        assert "mobility" in grid.point_data
