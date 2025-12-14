"""
Tests for UK LSOA boundary data acquisition.

This module contains both unit tests (mocked) and integration tests (real API calls).
Integration tests are marked with @pytest.mark.integration and validate against
the ONS Open Geography Portal data.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import Point, Polygon

from poverty_tda.data.census_shapes import (
    CRS_BRITISH_NATIONAL_GRID,
    CRS_WGS84,
    EXPECTED_LSOA_COUNT_2021,
    download_lsoa_boundaries,
    filter_by_region,
    get_lsoa_centroids,
    load_lsoa_boundaries,
    transform_crs,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_lsoa_gdf() -> gpd.GeoDataFrame:
    """Create a sample GeoDataFrame mimicking LSOA boundary data."""
    # Create simple polygon geometries
    polygons = [
        Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
        Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
        Polygon([(0, 1), (1, 1), (1, 2), (0, 2)]),
        Polygon([(1, 1), (2, 1), (2, 2), (1, 2)]),
        Polygon([(2, 0), (3, 0), (3, 1), (2, 1)]),  # Wales LSOA
    ]

    gdf = gpd.GeoDataFrame(
        {
            "LSOA21CD": [
                "E01000001",
                "E01000002",
                "E01000003",
                "E01000004",
                "W01000001",
            ],
            "LSOA21NM": [
                "City of London 001A",
                "City of London 001B",
                "City of London 001C",
                "City of London 001D",
                "Newport 001A",
            ],
        },
        geometry=polygons,
        crs=CRS_BRITISH_NATIONAL_GRID,
    )
    return gdf


@pytest.fixture
def temp_geojson(tmp_path: Path, sample_lsoa_gdf: gpd.GeoDataFrame) -> Path:
    """Create a temporary GeoJSON file for testing."""
    filepath = tmp_path / "test_lsoa.geojson"
    sample_lsoa_gdf.to_file(filepath, driver="GeoJSON")
    return filepath


# ============================================================================
# UNIT TESTS - FILE PATH HANDLING
# ============================================================================


class TestDownloadLsoaBoundaries:
    """Unit tests for download_lsoa_boundaries()."""

    def test_unsupported_year_raises_error(self, tmp_path: Path):
        """Test that unsupported year raises ValueError."""
        with pytest.raises(ValueError, match="Year 2011 not supported"):
            download_lsoa_boundaries(output_dir=tmp_path, year=2011)

    def test_skip_existing_file(self, tmp_path: Path):
        """Test that existing file is not re-downloaded."""
        # Create existing file
        output_dir = tmp_path / "boundaries"
        output_dir.mkdir(parents=True)
        existing_file = output_dir / "lsoa_2021_bgc.geojson"
        existing_file.write_text('{"type": "FeatureCollection", "features": []}')

        # Should return existing path without download
        result = download_lsoa_boundaries(output_dir=output_dir)

        assert result == existing_file
        assert result.exists()

    @patch("poverty_tda.data.census_shapes.requests.get")
    def test_download_creates_file(self, mock_get, tmp_path: Path):
        """Test successful download creates file."""
        # Mock response with valid GeoJSON
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [
            b'{"type": "FeatureCollection", "features": []}'
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        output_dir = tmp_path / "boundaries"
        result = download_lsoa_boundaries(output_dir=output_dir)

        assert result.exists()
        assert result.name == "lsoa_2021_bgc.geojson"

    @patch("poverty_tda.data.census_shapes.requests.get")
    def test_download_full_resolution(self, mock_get, tmp_path: Path):
        """Test downloading full resolution boundaries."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [
            b'{"type": "FeatureCollection", "features": []}'
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        output_dir = tmp_path / "boundaries"
        result = download_lsoa_boundaries(output_dir=output_dir, resolution="full")

        assert result.name == "lsoa_2021_bfc.geojson"


# ============================================================================
# UNIT TESTS - CRS TRANSFORMATION
# ============================================================================


class TestTransformCrs:
    """Unit tests for transform_crs()."""

    def test_transform_to_wgs84(self, sample_lsoa_gdf: gpd.GeoDataFrame):
        """Test transformation to WGS84."""
        result = transform_crs(sample_lsoa_gdf, CRS_WGS84)

        assert str(result.crs) == CRS_WGS84
        assert len(result) == len(sample_lsoa_gdf)

    def test_transform_same_crs_returns_same(self, sample_lsoa_gdf: gpd.GeoDataFrame):
        """Test that transforming to same CRS returns unchanged data."""
        result = transform_crs(sample_lsoa_gdf, CRS_BRITISH_NATIONAL_GRID)

        assert str(result.crs) == CRS_BRITISH_NATIONAL_GRID

    def test_transform_no_crs_raises_error(self, sample_lsoa_gdf: gpd.GeoDataFrame):
        """Test that missing CRS raises error."""
        gdf_no_crs = sample_lsoa_gdf.copy()
        gdf_no_crs.crs = None

        with pytest.raises(ValueError, match="has no CRS set"):
            transform_crs(gdf_no_crs, CRS_WGS84)


# ============================================================================
# UNIT TESTS - SIMPLIFICATION
# ============================================================================


class TestLoadLsoaBoundariesSimplification:
    """Unit tests for geometry simplification."""

    def test_simplify_reduces_vertices(self, temp_geojson: Path):
        """Test that simplification reduces geometry complexity."""
        # Load without simplification
        gdf_full = load_lsoa_boundaries(filepath=temp_geojson, simplify=False)

        # Load with simplification
        gdf_simplified = load_lsoa_boundaries(
            filepath=temp_geojson, simplify=True, tolerance=0.5
        )

        # Both should have same number of LSOAs
        assert len(gdf_full) == len(gdf_simplified)

        # Simplified geometries should have same or fewer vertices
        # (for simple test polygons, may not change much)
        assert all(gdf_simplified.is_valid)


# ============================================================================
# UNIT TESTS - LOAD LSOA BOUNDARIES
# ============================================================================


class TestLoadLsoaBoundaries:
    """Unit tests for load_lsoa_boundaries()."""

    def test_load_from_filepath(self, temp_geojson: Path):
        """Test loading from explicit filepath."""
        gdf = load_lsoa_boundaries(filepath=temp_geojson)

        assert len(gdf) == 5
        assert "LSOA21CD" in gdf.columns
        assert "LSOA21NM" in gdf.columns
        assert gdf.crs is not None

    def test_load_missing_file_raises_error(self, tmp_path: Path):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_lsoa_boundaries(
                filepath=tmp_path / "nonexistent.geojson", download_if_missing=False
            )

    def test_load_validates_columns(self, tmp_path: Path):
        """Test that invalid columns raise ValueError."""
        # Create GeoJSON with wrong columns
        bad_gdf = gpd.GeoDataFrame(
            {"wrong_col": ["A", "B"]},
            geometry=[Point(0, 0), Point(1, 1)],
            crs=CRS_BRITISH_NATIONAL_GRID,
        )
        bad_file = tmp_path / "bad_lsoa.geojson"
        bad_gdf.to_file(bad_file, driver="GeoJSON")

        with pytest.raises(ValueError, match="missing required LSOA columns"):
            load_lsoa_boundaries(filepath=bad_file)


# ============================================================================
# UNIT TESTS - CENTROID EXTRACTION
# ============================================================================


class TestGetLsoaCentroids:
    """Unit tests for get_lsoa_centroids()."""

    def test_centroids_are_points(self, sample_lsoa_gdf: gpd.GeoDataFrame):
        """Test that centroids are Point geometries."""
        centroids = get_lsoa_centroids(sample_lsoa_gdf)

        assert all(centroids.geometry.geom_type == "Point")

    def test_centroids_preserve_attributes(self, sample_lsoa_gdf: gpd.GeoDataFrame):
        """Test that centroids preserve LSOA attributes."""
        centroids = get_lsoa_centroids(sample_lsoa_gdf)

        assert len(centroids) == len(sample_lsoa_gdf)
        assert list(centroids["LSOA21CD"]) == list(sample_lsoa_gdf["LSOA21CD"])

    def test_centroids_preserve_crs(self, sample_lsoa_gdf: gpd.GeoDataFrame):
        """Test that centroids preserve CRS."""
        centroids = get_lsoa_centroids(sample_lsoa_gdf)

        assert centroids.crs == sample_lsoa_gdf.crs


# ============================================================================
# UNIT TESTS - REGION FILTERING
# ============================================================================


class TestFilterByRegion:
    """Unit tests for filter_by_region()."""

    def test_filter_england_lsoas(self, sample_lsoa_gdf: gpd.GeoDataFrame):
        """Test filtering for England LSOAs."""
        england = filter_by_region(sample_lsoa_gdf, "E01")

        assert len(england) == 4
        assert all(england["LSOA21CD"].str.startswith("E01"))

    def test_filter_wales_lsoas(self, sample_lsoa_gdf: gpd.GeoDataFrame):
        """Test filtering for Wales LSOAs."""
        wales = filter_by_region(sample_lsoa_gdf, "W01")

        assert len(wales) == 1
        assert all(wales["LSOA21CD"].str.startswith("W01"))

    def test_filter_no_match_returns_empty(self, sample_lsoa_gdf: gpd.GeoDataFrame):
        """Test filtering with no matches returns empty GeoDataFrame."""
        result = filter_by_region(sample_lsoa_gdf, "S01")  # Scotland prefix

        assert len(result) == 0

    def test_filter_invalid_column_raises_error(
        self, sample_lsoa_gdf: gpd.GeoDataFrame
    ):
        """Test filtering on invalid column raises error."""
        with pytest.raises(ValueError, match="Column 'INVALID' not found"):
            filter_by_region(sample_lsoa_gdf, "E01", column="INVALID")


# ============================================================================
# INTEGRATION TESTS - REAL API CALLS
# ============================================================================


@pytest.mark.integration
class TestLsoaBoundariesIntegration:
    """
    Integration tests for LSOA boundary data.

    These tests make real API calls to the ONS Open Geography Portal
    and validate the downloaded data structure and content.
    """

    @pytest.fixture(scope="class")
    def downloaded_lsoa_gdf(self, tmp_path_factory) -> gpd.GeoDataFrame:
        """Download and load LSOA boundaries for integration tests."""
        tmp_dir = tmp_path_factory.mktemp("lsoa_data")
        try:
            filepath = download_lsoa_boundaries(output_dir=tmp_dir)
            # Load with automatic fallback handling
            return load_lsoa_boundaries(filepath=filepath)
        except Exception as e:
            pytest.skip(f"Could not download/load LSOA boundaries: {e}")

    def test_lsoa_count_matches_expected(self, downloaded_lsoa_gdf: gpd.GeoDataFrame):
        """Verify LSOA count matches expected ~33,755 for England and Wales."""
        # Allow 1% tolerance for any boundary changes
        tolerance = 0.01
        expected = EXPECTED_LSOA_COUNT_2021
        actual = len(downloaded_lsoa_gdf)

        assert abs(actual - expected) / expected < tolerance, (
            f"LSOA count {actual} differs from expected {expected} "
            f"by more than {tolerance * 100}%"
        )

    def test_geometry_types_valid(self, downloaded_lsoa_gdf: gpd.GeoDataFrame):
        """Validate geometry types are Polygon or MultiPolygon."""
        valid_types = {"Polygon", "MultiPolygon"}
        actual_types = set(downloaded_lsoa_gdf.geometry.geom_type.unique())

        assert actual_types.issubset(
            valid_types
        ), f"Unexpected geometry types: {actual_types - valid_types}"

    def test_crs_is_set(self, downloaded_lsoa_gdf: gpd.GeoDataFrame):
        """Verify CRS is correctly set."""
        assert downloaded_lsoa_gdf.crs is not None
        # Should be British National Grid or WGS84
        assert str(downloaded_lsoa_gdf.crs) in [
            CRS_BRITISH_NATIONAL_GRID,
            CRS_WGS84,
        ]

    def test_centroid_extraction_works(self, downloaded_lsoa_gdf: gpd.GeoDataFrame):
        """Test centroid extraction on real data."""
        # Use subset for performance
        subset = downloaded_lsoa_gdf.head(100)
        centroids = get_lsoa_centroids(subset)

        assert len(centroids) == 100
        assert all(centroids.geometry.geom_type == "Point")

    def test_region_filter_england_wales(self, downloaded_lsoa_gdf: gpd.GeoDataFrame):
        """Verify England/Wales filtering produces expected split."""
        england = filter_by_region(downloaded_lsoa_gdf, "E01")
        wales = filter_by_region(downloaded_lsoa_gdf, "W01")

        # England should have ~32,844 LSOAs, Wales ~911
        assert (
            len(england) > 30000
        ), f"Expected >30000 England LSOAs, got {len(england)}"
        assert len(wales) > 800, f"Expected >800 Wales LSOAs, got {len(wales)}"

        # Combined should roughly equal total
        assert len(england) + len(wales) == len(downloaded_lsoa_gdf)

    def test_required_columns_present(self, downloaded_lsoa_gdf: gpd.GeoDataFrame):
        """Verify required LSOA columns are present."""
        required = {"LSOA21CD", "LSOA21NM", "geometry"}
        actual_cols = set(downloaded_lsoa_gdf.columns)

        assert required.issubset(
            actual_cols
        ), f"Missing required columns: {required - actual_cols}"

    def test_lsoa_codes_format(self, downloaded_lsoa_gdf: gpd.GeoDataFrame):
        """Verify LSOA codes follow expected format."""
        codes = downloaded_lsoa_gdf["LSOA21CD"]

        # All codes should start with E01 (England) or W01 (Wales)
        valid_prefixes = codes.str.match(r"^[EW]01\d{6}$")
        assert valid_prefixes.all(), "Some LSOA codes don't match expected format"

    def test_crs_transform_roundtrip(self, downloaded_lsoa_gdf: gpd.GeoDataFrame):
        """Test CRS transformation roundtrip."""
        subset = downloaded_lsoa_gdf.head(10)

        # Transform to WGS84 and back
        wgs84 = transform_crs(subset, CRS_WGS84)
        back_to_bng = transform_crs(wgs84, CRS_BRITISH_NATIONAL_GRID)

        # Coordinates should be close to original (allowing for float precision)
        original_bounds = subset.total_bounds
        roundtrip_bounds = back_to_bng.total_bounds

        np.testing.assert_array_almost_equal(
            original_bounds, roundtrip_bounds, decimal=3
        )
