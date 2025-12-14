"""
Tests for UK IMD (Index of Multiple Deprivation) data acquisition.

This module contains both unit tests (mocked) and integration tests (real API calls).
Integration tests are marked with @pytest.mark.integration and validate against
known deprivation patterns from GOV.UK official statistics.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon

from poverty_tda.data.opportunity_atlas import (
    EXPECTED_ENGLAND_LSOA_COUNT,
    JAYWICK_LSOA_CODE,
    KNOWN_LEAST_DEPRIVED_LADS,
    KNOWN_MOST_DEPRIVED_LADS,
    download_imd_data,
    get_deprivation_decile,
    get_domain_scores,
    load_imd_data,
    merge_with_boundaries,
    parse_imd_domains,
    validate_deprivation_patterns,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_imd_df() -> pd.DataFrame:
    """Create a sample DataFrame mimicking IMD data structure."""
    return pd.DataFrame(
        {
            "lsoa_code": [
                "E01000001",
                "E01000002",
                "E01000003",
                "E01000004",
                "E01021988",  # Correct Jaywick LSOA code (IMD rank 1)
            ],
            "lsoa_name": [
                "City of London 001A",
                "City of London 001B",
                "City of London 001C",
                "City of London 001D",
                "Tendring 018A",  # Jaywick - most deprived LSOA in England
            ],
            "lad_code": [
                "E09000001",
                "E09000001",
                "E09000001",
                "E09000001",
                "E07000076",
            ],
            "lad_name": [
                "City of London",
                "City of London",
                "City of London",
                "City of London",
                "Tendring",
            ],
            "imd_score": [10.5, 15.2, 8.3, 12.1, 92.7],
            "imd_rank": [25000, 20000, 30000, 22000, 1],
            "imd_decile": [8, 7, 9, 7, 1],
            "income_score": [0.05, 0.08, 0.04, 0.06, 0.55],
            "income_rank": [25000, 20000, 30000, 22000, 1],
            "income_decile": [8, 7, 9, 7, 1],
            "employment_score": [0.04, 0.06, 0.03, 0.05, 0.42],
            "employment_rank": [26000, 21000, 31000, 23000, 2],
            "employment_decile": [8, 7, 10, 7, 1],
            "education_score": [12.0, 18.0, 8.0, 15.0, 65.0],
            "education_rank": [24000, 19000, 29000, 21000, 5],
            "education_decile": [8, 6, 9, 7, 1],
            "health_score": [-0.5, -0.3, -0.7, -0.4, 1.8],
            "health_rank": [27000, 22000, 30000, 25000, 3],
            "health_decile": [9, 7, 10, 8, 1],
            "crime_score": [0.2, 0.4, 0.1, 0.3, 1.5],
            "crime_rank": [20000, 15000, 25000, 18000, 100],
            "crime_decile": [7, 5, 8, 6, 1],
            "housing_score": [25.0, 30.0, 20.0, 28.0, 45.0],
            "housing_rank": [15000, 12000, 20000, 14000, 2000],
            "housing_decile": [5, 4, 7, 5, 1],
            "environment_score": [35.0, 40.0, 30.0, 38.0, 55.0],
            "environment_rank": [10000, 8000, 15000, 9000, 1000],
            "environment_decile": [4, 3, 5, 3, 1],
        }
    )


@pytest.fixture
def sample_boundaries_gdf() -> gpd.GeoDataFrame:
    """Create sample LSOA boundaries for merge testing."""
    polygons = [
        Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
        Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
        Polygon([(0, 1), (1, 1), (1, 2), (0, 2)]),
    ]

    return gpd.GeoDataFrame(
        {
            "LSOA21CD": ["E01000001", "E01000002", "E01000003"],
            "LSOA21NM": [
                "City of London 001A",
                "City of London 001B",
                "City of London 001C",
            ],
        },
        geometry=polygons,
        crs="EPSG:27700",
    )


@pytest.fixture
def temp_imd_csv(tmp_path: Path, sample_imd_df: pd.DataFrame) -> Path:
    """Create a temporary IMD CSV file for testing."""
    filepath = tmp_path / "test_imd.csv"
    sample_imd_df.to_csv(filepath, index=False)
    return filepath


# ============================================================================
# UNIT TESTS - DATA PARSING
# ============================================================================


class TestLoadImdData:
    """Unit tests for load_imd_data()."""

    def test_load_from_filepath(self, temp_imd_csv: Path, sample_imd_df: pd.DataFrame):
        """Test loading from explicit filepath."""
        df = load_imd_data(filepath=temp_imd_csv, standardize_columns=False)

        assert len(df) == len(sample_imd_df)
        assert "lsoa_code" in df.columns
        assert "imd_score" in df.columns

    def test_load_missing_file_raises_error(self, tmp_path: Path):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_imd_data(
                filepath=tmp_path / "nonexistent.csv", download_if_missing=False
            )


class TestParseImdDomains:
    """Unit tests for parse_imd_domains()."""

    def test_parse_extracts_all_domains(self, sample_imd_df: pd.DataFrame):
        """Test that all 7 domains are extracted."""
        domains_df = parse_imd_domains(sample_imd_df)

        required_domains = [
            "income",
            "employment",
            "education",
            "health",
            "crime",
            "housing",
            "environment",
        ]

        for domain in required_domains:
            assert f"{domain}_score" in domains_df.columns

    def test_parse_preserves_lsoa_ids(self, sample_imd_df: pd.DataFrame):
        """Test that LSOA identifiers are preserved."""
        domains_df = parse_imd_domains(sample_imd_df)

        assert "lsoa_code" in domains_df.columns
        assert len(domains_df) == len(sample_imd_df)

    def test_parse_missing_domain_raises_error(self, sample_imd_df: pd.DataFrame):
        """Test that missing domain raises ValueError."""
        df_missing = sample_imd_df.drop(columns=["income_score"])

        with pytest.raises(ValueError, match="Missing domain columns"):
            parse_imd_domains(df_missing)


# ============================================================================
# UNIT TESTS - DECILE CALCULATION
# ============================================================================


class TestGetDeprivationDecile:
    """Unit tests for get_deprivation_decile()."""

    def test_returns_existing_decile(self, sample_imd_df: pd.DataFrame):
        """Test that existing decile column is returned."""
        deciles = get_deprivation_decile(sample_imd_df)

        assert len(deciles) == len(sample_imd_df)
        assert deciles.iloc[0] == 8  # From fixture

    def test_calculates_decile_from_rank(self, sample_imd_df: pd.DataFrame):
        """Test decile calculation from rank column."""
        df = sample_imd_df.drop(columns=["imd_decile"])
        deciles = get_deprivation_decile(df, total_lsoas=32844)

        # Rank 1 should be decile 1 (most deprived)
        jaywick_idx = df[df["lsoa_code"] == JAYWICK_LSOA_CODE].index[0]
        assert deciles.loc[jaywick_idx] == 1

    def test_decile_range_valid(self, sample_imd_df: pd.DataFrame):
        """Test that all deciles are in range 1-10."""
        deciles = get_deprivation_decile(sample_imd_df)

        assert deciles.min() >= 1
        assert deciles.max() <= 10

    def test_missing_rank_column_raises_error(self, sample_imd_df: pd.DataFrame):
        """Test that missing rank column raises error."""
        df = sample_imd_df.drop(columns=["imd_rank", "imd_decile"])

        with pytest.raises(ValueError, match="Rank column"):
            get_deprivation_decile(df)


# ============================================================================
# UNIT TESTS - COLUMN STANDARDIZATION
# ============================================================================


class TestColumnStandardization:
    """Unit tests for column name standardization."""

    def test_standardized_column_names(self, sample_imd_df: pd.DataFrame):
        """Test that column names follow expected pattern."""
        expected_patterns = [
            "lsoa_code",
            "lsoa_name",
            "imd_score",
            "imd_rank",
            "imd_decile",
            "income_score",
            "income_rank",
        ]

        for pattern in expected_patterns:
            assert pattern in sample_imd_df.columns


# ============================================================================
# UNIT TESTS - DOMAIN SCORES
# ============================================================================


class TestGetDomainScores:
    """Unit tests for get_domain_scores()."""

    def test_extracts_seven_domains(self, sample_imd_df: pd.DataFrame):
        """Test that exactly 7 domain scores are extracted."""
        scores = get_domain_scores(sample_imd_df)

        domain_score_cols = [c for c in scores.columns if c.endswith("_score")]
        assert len(domain_score_cols) == 7

    def test_excludes_ranks_and_deciles(self, sample_imd_df: pd.DataFrame):
        """Test that ranks and deciles are excluded."""
        scores = get_domain_scores(sample_imd_df)

        assert not any(c.endswith("_rank") for c in scores.columns)
        assert not any(c.endswith("_decile") for c in scores.columns)


# ============================================================================
# UNIT TESTS - MERGE WITH BOUNDARIES
# ============================================================================


class TestMergeWithBoundaries:
    """Unit tests for merge_with_boundaries()."""

    def test_merge_creates_geodataframe(
        self, sample_imd_df: pd.DataFrame, sample_boundaries_gdf: gpd.GeoDataFrame
    ):
        """Test that merge produces a GeoDataFrame."""
        merged = merge_with_boundaries(sample_imd_df, sample_boundaries_gdf)

        assert isinstance(merged, gpd.GeoDataFrame)
        assert "geometry" in merged.columns

    def test_merge_preserves_imd_columns(
        self, sample_imd_df: pd.DataFrame, sample_boundaries_gdf: gpd.GeoDataFrame
    ):
        """Test that IMD columns are preserved in merge."""
        merged = merge_with_boundaries(sample_imd_df, sample_boundaries_gdf)

        assert "imd_score" in merged.columns
        assert "imd_decile" in merged.columns

    def test_merge_inner_join(
        self, sample_imd_df: pd.DataFrame, sample_boundaries_gdf: gpd.GeoDataFrame
    ):
        """Test that merge uses inner join (only matching records)."""
        merged = merge_with_boundaries(sample_imd_df, sample_boundaries_gdf)

        # Only 3 LSOAs match between fixtures
        assert len(merged) == 3

    def test_merge_invalid_column_raises_error(
        self, sample_imd_df: pd.DataFrame, sample_boundaries_gdf: gpd.GeoDataFrame
    ):
        """Test that invalid column name raises error."""
        with pytest.raises(ValueError, match="IMD code column"):
            merge_with_boundaries(
                sample_imd_df,
                sample_boundaries_gdf,
                imd_code_column="nonexistent",
            )


# ============================================================================
# UNIT TESTS - DOWNLOAD
# ============================================================================


class TestDownloadImdData:
    """Unit tests for download_imd_data()."""

    def test_unsupported_country_raises_error(self, tmp_path: Path):
        """Test that unsupported country raises ValueError."""
        with pytest.raises(ValueError, match="Country 'scotland' not supported"):
            download_imd_data(output_dir=tmp_path, country="scotland")

    def test_skip_existing_file(self, tmp_path: Path):
        """Test that existing file is not re-downloaded."""
        existing_file = tmp_path / "england_imd_2019.csv"
        existing_file.write_text("lsoa_code,imd_score\nE01000001,10.5")

        result = download_imd_data(output_dir=tmp_path, country="england")

        assert result == existing_file

    @patch("poverty_tda.data.opportunity_atlas.requests.get")
    def test_download_creates_file(self, mock_get, tmp_path: Path):
        """Test successful download creates file."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [
            b"lsoa_code,imd_score\nE01000001,10.5"
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = download_imd_data(output_dir=tmp_path)

        assert result.exists()
        assert result.name == "england_imd_2019.csv"


# ============================================================================
# UNIT TESTS - VALIDATION
# ============================================================================


class TestValidateDeprivationPatterns:
    """Unit tests for validate_deprivation_patterns()."""

    def test_jaywick_detection(self, sample_imd_df: pd.DataFrame):
        """Test that Jaywick LSOA is detected and validated."""
        results = validate_deprivation_patterns(sample_imd_df)

        assert results["jaywick_decile"] == 1
        assert results["validation_passed"] is True

    def test_validation_fails_for_wrong_jaywick_decile(
        self, sample_imd_df: pd.DataFrame
    ):
        """Test that validation fails if Jaywick is not in decile 1."""
        df = sample_imd_df.copy()
        jaywick_idx = df[df["lsoa_code"] == JAYWICK_LSOA_CODE].index[0]
        df.loc[jaywick_idx, "imd_decile"] = 5

        results = validate_deprivation_patterns(df)

        assert results["jaywick_decile"] == 5
        assert results["validation_passed"] is False


# ============================================================================
# INTEGRATION TESTS - REAL API CALLS
# ============================================================================


@pytest.mark.integration
class TestImdDataIntegration:
    """
    Integration tests for IMD data.

    These tests make real API calls to GOV.UK and validate
    the downloaded data against known deprivation patterns.
    """

    @pytest.fixture(scope="class")
    def downloaded_imd_df(self, tmp_path_factory) -> pd.DataFrame:
        """Download and load IMD data for integration tests."""
        tmp_dir = tmp_path_factory.mktemp("imd_data")
        filepath = download_imd_data(output_dir=tmp_dir, country="england")
        return load_imd_data(filepath=filepath)

    def test_lsoa_count_matches_expected(self, downloaded_imd_df: pd.DataFrame):
        """Verify LSOA count matches expected ~32,844 for England."""
        tolerance = 0.01
        expected = EXPECTED_ENGLAND_LSOA_COUNT
        actual = len(downloaded_imd_df)

        assert abs(actual - expected) / expected < tolerance, (
            f"LSOA count {actual} differs from expected {expected} "
            f"by more than {tolerance * 100}%"
        )

    def test_all_seven_domains_present(self, downloaded_imd_df: pd.DataFrame):
        """Verify all 7 IMD domains are present."""
        required_domains = [
            "income",
            "employment",
            "education",
            "health",
            "crime",
            "housing",
            "environment",
        ]

        for domain in required_domains:
            score_col = f"{domain}_score"
            assert score_col in downloaded_imd_df.columns, f"Missing domain: {domain}"

    def test_domain_scores_valid_ranges(self, downloaded_imd_df: pd.DataFrame):
        """Verify domain scores are within expected ranges."""
        # Income and Employment are rates (0-1)
        assert downloaded_imd_df["income_score"].between(0, 1).all()
        assert downloaded_imd_df["employment_score"].between(0, 1).all()

        # Deciles should be 1-10
        assert downloaded_imd_df["imd_decile"].between(1, 10).all()

    def test_jaywick_is_most_deprived(self, downloaded_imd_df: pd.DataFrame):
        """Verify Jaywick (Tendring) is in decile 1 (most deprived)."""
        jaywick = downloaded_imd_df[downloaded_imd_df["lsoa_code"] == JAYWICK_LSOA_CODE]

        assert len(jaywick) == 1, "Jaywick LSOA not found"
        assert (
            jaywick["imd_decile"].iloc[0] == 1
        ), "Jaywick should be in decile 1 (most deprived)"

    def test_known_most_deprived_lads(self, downloaded_imd_df: pd.DataFrame):
        """Verify known deprived LADs have low average deciles."""
        lad_avg = downloaded_imd_df.groupby("lad_name")["imd_decile"].mean()

        for lad in KNOWN_MOST_DEPRIVED_LADS:
            if lad in lad_avg.index:
                avg_decile = lad_avg[lad]
                assert avg_decile < 5, (
                    f"{lad} should have below-average deprivation "
                    f"(decile < 5), got {avg_decile:.2f}"
                )

    def test_known_least_deprived_lads(self, downloaded_imd_df: pd.DataFrame):
        """Verify known affluent LADs have high average deciles."""
        lad_avg = downloaded_imd_df.groupby("lad_name")["imd_decile"].mean()

        for lad in KNOWN_LEAST_DEPRIVED_LADS:
            if lad in lad_avg.index:
                avg_decile = lad_avg[lad]
                assert avg_decile > 5, (
                    f"{lad} should have above-average affluence "
                    f"(decile > 5), got {avg_decile:.2f}"
                )

    def test_domain_parsing_works(self, downloaded_imd_df: pd.DataFrame):
        """Test domain parsing on real data."""
        domains = parse_imd_domains(downloaded_imd_df)

        assert len(domains) == len(downloaded_imd_df)
        # Should have 7 score columns + 7 rank columns + 7 decile columns + id columns
        domain_cols = [c for c in domains.columns if "_score" in c]
        assert len(domain_cols) == 7

    def test_decile_distribution(self, downloaded_imd_df: pd.DataFrame):
        """Verify deciles are roughly evenly distributed."""
        decile_counts = downloaded_imd_df["imd_decile"].value_counts()

        # Each decile should have ~10% of LSOAs (±2%)
        expected_per_decile = len(downloaded_imd_df) / 10
        tolerance = 0.02 * len(downloaded_imd_df)

        for decile in range(1, 11):
            count = decile_counts.get(decile, 0)
            assert abs(count - expected_per_decile) < tolerance, (
                f"Decile {decile} has {count} LSOAs, "
                f"expected ~{expected_per_decile:.0f} ±{tolerance:.0f}"
            )

    def test_validation_patterns_pass(self, downloaded_imd_df: pd.DataFrame):
        """Test that validation against known patterns passes."""
        results = validate_deprivation_patterns(downloaded_imd_df)

        assert results["validation_passed"], (
            f"Validation failed. Jaywick decile: {results['jaywick_decile']}, "
            f"Most deprived LADs: {results['most_deprived_lads']}, "
            f"Least deprived LADs: {results['least_deprived_lads']}"
        )
