"""
Tests for UK Mobility Proxy Calculator.

This module contains unit tests for the mobility proxy formula components
and integration/validation tests against Social Mobility Commission data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from poverty_tda.data.education import (
    compute_educational_upward,
    get_education_from_imd,
)
from poverty_tda.data.mobility_proxy import (
    INDUSTRIAL_NORTH_LADS,
    SMC_BOTTOM_MOBILITY_LADS,
    SMC_TOP_MOBILITY_LADS,
    aggregate_to_lad,
    compute_deprivation_change,
    compute_income_growth,
    compute_mobility_proxy,
    get_mobility_quintiles,
    validate_against_smc,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_imd_df() -> pd.DataFrame:
    """Create sample IMD data with all required columns."""
    np.random.seed(42)
    n_lsoas = 100

    return pd.DataFrame(
        {
            "lsoa_code": [f"E0100{i:04d}" for i in range(n_lsoas)],
            "lsoa_name": [f"Test LSOA {i}" for i in range(n_lsoas)],
            "lad_code": [f"E0{(i // 10):05d}" for i in range(n_lsoas)],
            "lad_name": [f"Test LAD {i // 10}" for i in range(n_lsoas)],
            "imd_score": np.random.uniform(5, 80, n_lsoas),
            "imd_rank": np.random.permutation(n_lsoas) + 1,
            "imd_decile": np.random.randint(1, 11, n_lsoas),
            "income_score": np.random.uniform(0, 0.5, n_lsoas),
            "income_rank": np.random.permutation(n_lsoas) + 1,
            "education_score": np.random.uniform(5, 60, n_lsoas),
            "education_rank": np.random.permutation(n_lsoas) + 1,
            "education_decile": np.random.randint(1, 11, n_lsoas),
        }
    )


@pytest.fixture
def sample_baseline_imd_df(sample_imd_df: pd.DataFrame) -> pd.DataFrame:
    """Create sample baseline IMD data (simulating IMD 2015)."""
    baseline = sample_imd_df.copy()
    # Add some random change to ranks
    np.random.seed(123)
    rank_change = np.random.randint(-20, 20, len(baseline))
    baseline["imd_rank"] = np.clip(
        baseline["imd_rank"] + rank_change, 1, len(baseline)
    ).astype(int)
    return baseline


@pytest.fixture
def sample_polar4_df() -> pd.DataFrame:
    """Create sample POLAR4 data."""
    np.random.seed(42)
    n = 100
    return pd.DataFrame(
        {
            "lsoa_code": [f"E0100{i:04d}" for i in range(n)],
            "polar4_quintile": np.random.randint(1, 6, n),
        }
    )


# ============================================================================
# UNIT TESTS - DEPRIVATION CHANGE
# ============================================================================


class TestComputeDeprivationChange:
    """Unit tests for compute_deprivation_change()."""

    def test_without_baseline_normalized(self, sample_imd_df: pd.DataFrame):
        """Test deprivation change without baseline, normalized."""
        result = compute_deprivation_change(
            sample_imd_df, imd_baseline=None, normalize=True
        )

        assert len(result) == len(sample_imd_df)
        assert result.min() >= -1
        assert result.max() <= 1

    def test_without_baseline_raw(self, sample_imd_df: pd.DataFrame):
        """Test deprivation change without baseline, raw values."""
        result = compute_deprivation_change(
            sample_imd_df, imd_baseline=None, normalize=False
        )

        assert len(result) == len(sample_imd_df)
        # Should be rank values

    def test_with_baseline(
        self, sample_imd_df: pd.DataFrame, sample_baseline_imd_df: pd.DataFrame
    ):
        """Test deprivation change with baseline data."""
        result = compute_deprivation_change(
            sample_imd_df, imd_baseline=sample_baseline_imd_df, normalize=True
        )

        assert len(result) == len(sample_imd_df)
        # Some positive (improvement), some negative (worsening)
        assert result.sum() != 0  # Not all zeros

    def test_missing_column_raises_error(self, sample_imd_df: pd.DataFrame):
        """Test that missing rank column raises error."""
        df = sample_imd_df.drop(columns=["imd_rank"])

        with pytest.raises(ValueError, match="not found"):
            compute_deprivation_change(df)


# ============================================================================
# UNIT TESTS - INCOME GROWTH
# ============================================================================


class TestComputeIncomeGrowth:
    """Unit tests for compute_income_growth()."""

    def test_from_rank_normalized(self, sample_imd_df: pd.DataFrame):
        """Test income growth from rank, normalized."""
        result = compute_income_growth(sample_imd_df, normalize=True)

        assert len(result) == len(sample_imd_df)
        assert result.min() >= 0
        assert result.max() <= 1

    def test_from_score_normalized(self, sample_imd_df: pd.DataFrame):
        """Test income growth from score when rank unavailable."""
        df = sample_imd_df.drop(columns=["income_rank"])
        result = compute_income_growth(df, normalize=True)

        assert len(result) == len(df)
        # Lower score = better, inverted to [0, 1]

    def test_missing_columns_raises_error(self, sample_imd_df: pd.DataFrame):
        """Test that missing both columns raises error."""
        df = sample_imd_df.drop(columns=["income_rank", "income_score"])

        with pytest.raises(ValueError, match="must contain"):
            compute_income_growth(df)


# ============================================================================
# UNIT TESTS - EDUCATIONAL UPWARD
# ============================================================================


class TestComputeEducationalUpward:
    """Unit tests for compute_educational_upward()."""

    def test_from_imd_only(self, sample_imd_df: pd.DataFrame):
        """Test educational upward from IMD education domain only."""
        result = compute_educational_upward(sample_imd_df, polar_df=None)

        assert len(result) == len(sample_imd_df)
        assert result.min() >= 0
        assert result.max() <= 1

    def test_with_polar4_data(
        self, sample_imd_df: pd.DataFrame, sample_polar4_df: pd.DataFrame
    ):
        """Test educational upward with POLAR4 data."""
        result = compute_educational_upward(sample_imd_df, polar_df=sample_polar4_df)

        assert len(result) == len(sample_imd_df)
        assert result.min() >= 0
        assert result.max() <= 1


class TestGetEducationFromImd:
    """Unit tests for get_education_from_imd()."""

    def test_extracts_education_columns(self, sample_imd_df: pd.DataFrame):
        """Test education extraction from IMD."""
        result = get_education_from_imd(sample_imd_df)

        assert "lsoa_code" in result.columns
        assert "education_normalized" in result.columns
        assert len(result) == len(sample_imd_df)

    def test_normalized_range(self, sample_imd_df: pd.DataFrame):
        """Test normalized values are in [0, 1]."""
        result = get_education_from_imd(sample_imd_df)

        assert result["education_normalized"].min() >= 0
        assert result["education_normalized"].max() <= 1


# ============================================================================
# UNIT TESTS - MOBILITY PROXY
# ============================================================================


class TestComputeMobilityProxy:
    """Unit tests for compute_mobility_proxy()."""

    def test_default_weights(self, sample_imd_df: pd.DataFrame):
        """Test mobility proxy with default weights."""
        result = compute_mobility_proxy(sample_imd_df)

        assert "lsoa_code" in result.columns
        assert "mobility_proxy" in result.columns
        assert "deprivation_change" in result.columns
        assert "educational_upward" in result.columns
        assert "income_growth" in result.columns
        assert len(result) == len(sample_imd_df)

    def test_custom_weights(self, sample_imd_df: pd.DataFrame):
        """Test mobility proxy with custom weights."""
        result = compute_mobility_proxy(sample_imd_df, alpha=0.5, beta=0.25, gamma=0.25)

        assert len(result) == len(sample_imd_df)
        # Proxy values should be in reasonable range
        assert result["mobility_proxy"].min() >= 0
        assert result["mobility_proxy"].max() <= 1

    def test_invalid_weights_raises_error(self, sample_imd_df: pd.DataFrame):
        """Test that weights not summing to 1 raises error."""
        with pytest.raises(ValueError, match="sum to 1.0"):
            compute_mobility_proxy(sample_imd_df, alpha=0.5, beta=0.5, gamma=0.5)

    def test_with_baseline(
        self, sample_imd_df: pd.DataFrame, sample_baseline_imd_df: pd.DataFrame
    ):
        """Test mobility proxy with baseline IMD data."""
        result = compute_mobility_proxy(
            sample_imd_df, imd_baseline=sample_baseline_imd_df
        )

        assert len(result) == len(sample_imd_df)
        assert "mobility_proxy" in result.columns

    def test_preserves_lad_columns(self, sample_imd_df: pd.DataFrame):
        """Test that LAD columns are preserved for aggregation."""
        result = compute_mobility_proxy(sample_imd_df)

        assert "lad_name" in result.columns
        assert "lad_code" in result.columns

    def test_missing_lsoa_code_raises_error(self, sample_imd_df: pd.DataFrame):
        """Test that missing LSOA code raises error."""
        df = sample_imd_df.drop(columns=["lsoa_code"])

        with pytest.raises(ValueError, match="lsoa_code"):
            compute_mobility_proxy(df)


# ============================================================================
# UNIT TESTS - AGGREGATION
# ============================================================================


class TestAggregateToLad:
    """Unit tests for aggregate_to_lad()."""

    def test_mean_aggregation(self, sample_imd_df: pd.DataFrame):
        """Test mean aggregation to LAD level."""
        mobility = compute_mobility_proxy(sample_imd_df)
        result = aggregate_to_lad(mobility, method="mean")

        assert "lad_name" in result.columns
        assert "mobility_proxy" in result.columns
        assert "lsoa_count" in result.columns
        assert "mobility_rank" in result.columns
        # Should have fewer rows than LSOA-level
        assert len(result) < len(mobility)

    def test_median_aggregation(self, sample_imd_df: pd.DataFrame):
        """Test median aggregation to LAD level."""
        mobility = compute_mobility_proxy(sample_imd_df)
        result = aggregate_to_lad(mobility, method="median")

        assert len(result) > 0

    def test_missing_lad_column_raises_error(self, sample_imd_df: pd.DataFrame):
        """Test that missing LAD column raises error."""
        mobility = compute_mobility_proxy(sample_imd_df)
        mobility = mobility.drop(columns=["lad_name"])

        with pytest.raises(ValueError, match="LAD column"):
            aggregate_to_lad(mobility)


# ============================================================================
# UNIT TESTS - QUINTILES
# ============================================================================


class TestGetMobilityQuintiles:
    """Unit tests for get_mobility_quintiles()."""

    def test_quintile_range(self, sample_imd_df: pd.DataFrame):
        """Test quintiles are in range 1-5."""
        mobility = compute_mobility_proxy(sample_imd_df)
        quintiles = get_mobility_quintiles(mobility)

        assert quintiles.min() == 1
        assert quintiles.max() == 5

    def test_quintile_distribution(self, sample_imd_df: pd.DataFrame):
        """Test quintiles are roughly evenly distributed."""
        mobility = compute_mobility_proxy(sample_imd_df)
        quintiles = get_mobility_quintiles(mobility)

        # Each quintile should have ~20% of values
        for q in range(1, 6):
            count = (quintiles == q).sum()
            expected = len(mobility) / 5
            assert abs(count - expected) <= expected * 0.5  # Within 50% of expected


# ============================================================================
# UNIT TESTS - VALIDATION
# ============================================================================


class TestValidateAgainstSmc:
    """Unit tests for validate_against_smc()."""

    def test_returns_expected_keys(self, sample_imd_df: pd.DataFrame):
        """Test validation returns expected dictionary keys."""
        mobility = compute_mobility_proxy(sample_imd_df)
        result = validate_against_smc(mobility)

        assert "correlation" in result
        assert "top_lads_check" in result
        assert "bottom_lads_check" in result
        assert "industrial_north_check" in result
        assert "validation_passed" in result
        assert "details" in result

    def test_with_known_lads(self):
        """Test validation with known LAD names from SMC data."""
        # Create synthetic data with known LAD patterns
        np.random.seed(42)
        n_lsoas = 200

        # Create LADs with known mobility patterns
        lad_names = (
            SMC_TOP_MOBILITY_LADS[:2] * 20  # 40 LSOAs in top LADs
            + SMC_BOTTOM_MOBILITY_LADS[:2] * 20  # 40 LSOAs in bottom LADs
            + [f"Other LAD {i}" for i in range(12)] * 10  # 120 other LSOAs
        )

        df = pd.DataFrame(
            {
                "lsoa_code": [f"E0100{i:04d}" for i in range(n_lsoas)],
                "lad_name": lad_names,
                "mobility_proxy": np.concatenate(
                    [
                        np.random.uniform(0.7, 0.9, 40),  # Top LADs: high mobility
                        np.random.uniform(0.1, 0.3, 40),  # Bottom LADs: low mobility
                        np.random.uniform(0.4, 0.6, 120),  # Others: medium
                    ]
                ),
            }
        )

        result = validate_against_smc(df)

        # Should find top LADs with high values
        assert len(result["top_lads_check"]) > 0
        # Should find bottom LADs with low values
        assert len(result["bottom_lads_check"]) > 0


# ============================================================================
# INTEGRATION TESTS - REAL DATA
# ============================================================================


@pytest.mark.integration
class TestMobilityProxyIntegration:
    """
    Integration tests using real IMD data.

    These tests validate the mobility proxy against known patterns
    and Social Mobility Commission estimates.
    """

    @pytest.fixture(scope="class")
    def real_imd_df(self, tmp_path_factory):
        """Load real IMD data for integration tests."""
        from poverty_tda.data.opportunity_atlas import load_imd_data

        tmp_dir = tmp_path_factory.mktemp("imd_data")
        from poverty_tda.data.opportunity_atlas import download_imd_data

        filepath = download_imd_data(output_dir=tmp_dir)
        return load_imd_data(filepath=filepath)

    def test_compute_for_all_lsoas(self, real_imd_df: pd.DataFrame):
        """Test mobility proxy computation for all England LSOAs."""
        result = compute_mobility_proxy(real_imd_df)

        assert len(result) > 30000  # Should have ~32,844 LSOAs
        assert result["mobility_proxy"].notna().all()

    def test_proxy_values_reasonable(self, real_imd_df: pd.DataFrame):
        """Test mobility proxy values are in reasonable range."""
        result = compute_mobility_proxy(real_imd_df)

        assert result["mobility_proxy"].min() >= 0
        assert result["mobility_proxy"].max() <= 1
        # Mean should be around 0.5
        assert 0.3 < result["mobility_proxy"].mean() < 0.7

    def test_lad_aggregation(self, real_imd_df: pd.DataFrame):
        """Test LAD-level aggregation works correctly."""
        mobility = compute_mobility_proxy(real_imd_df)
        lad_result = aggregate_to_lad(mobility)

        # Should have ~317 LADs in England
        assert len(lad_result) > 300
        assert len(lad_result) < 350

    @pytest.mark.validation
    def test_smc_validation_patterns(self, real_imd_df: pd.DataFrame):
        """
        Validate mobility proxy against SMC patterns.

        Checks:
        1. Top mobility LADs (London boroughs) have high proxy values
        2. Bottom mobility LADs (industrial areas) have low proxy values
        3. Industrial North shows below-average mobility
        """
        mobility = compute_mobility_proxy(real_imd_df)
        result = validate_against_smc(mobility)

        # Log detailed results
        print("\nSMC Validation Results:")
        print(f"  Top LADs found: {len(result['top_lads_check'])}")
        for lad, data in result["top_lads_check"].items():
            print(f"    {lad}: {data['percentile']:.1f}th percentile")

        print(f"  Bottom LADs found: {len(result['bottom_lads_check'])}")
        for lad, data in result["bottom_lads_check"].items():
            print(f"    {lad}: {data['percentile']:.1f}th percentile")

        if result["industrial_north_check"]:
            north = result["industrial_north_check"]
            print(f"  Industrial North avg: {north['avg_industrial_north']:.3f}")
            print(f"  National avg: {north['avg_all_lads']:.3f}")
            print(f"  Below average: {north['below_average']}")

        # Validation should pass (patterns match expected)
        # Note: This may fail if weights need adjustment
        assert result["validation_passed"], f"SMC validation failed. Details: {result}"

    @pytest.mark.validation
    def test_industrial_north_pattern(self, real_imd_df: pd.DataFrame):
        """Test that industrial North areas show below-average mobility."""
        mobility = compute_mobility_proxy(real_imd_df)
        lad_mobility = aggregate_to_lad(mobility)

        lad_values = lad_mobility.set_index("lad_name")["mobility_proxy"]

        north_values = [
            lad_values[lad] for lad in INDUSTRIAL_NORTH_LADS if lad in lad_values.index
        ]

        assert len(north_values) > 0, "No industrial North LADs found"

        avg_north = np.mean(north_values)
        avg_all = lad_values.mean()

        print("\nIndustrial North vs National:")
        print(f"  Industrial North avg: {avg_north:.3f}")
        print(f"  National avg: {avg_all:.3f}")

        # Industrial areas should be below national average
        assert avg_north < avg_all, (
            f"Industrial North ({avg_north:.3f}) should be below "
            f"national average ({avg_all:.3f})"
        )

    @pytest.mark.validation
    def test_london_pattern(self, real_imd_df: pd.DataFrame):
        """Test that London boroughs show varied but generally higher mobility."""
        mobility = compute_mobility_proxy(real_imd_df)
        lad_mobility = aggregate_to_lad(mobility)

        # Find London boroughs (contain "London" or specific boroughs)
        london_lads = lad_mobility[
            lad_mobility["lad_name"].str.contains(
                "Westminster|Camden|Kensington|City of London",
                case=False,
                na=False,
            )
        ]

        if len(london_lads) > 0:
            avg_london = london_lads["mobility_proxy"].mean()
            avg_all = lad_mobility["mobility_proxy"].mean()

            print("\nLondon vs National:")
            print(f"  Central London avg: {avg_london:.3f}")
            print(f"  National avg: {avg_all:.3f}")

            # Central London should be above average
            assert avg_london > avg_all


# ============================================================================
# EDGE CASES
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        df = pd.DataFrame(columns=["lsoa_code", "imd_rank"])

        with pytest.raises((ValueError, KeyError)):
            compute_mobility_proxy(df)

    def test_single_lsoa(self):
        """Test handling of single LSOA."""
        df = pd.DataFrame(
            {
                "lsoa_code": ["E01000001"],
                "lsoa_name": ["Test LSOA"],
                "lad_name": ["Test LAD"],
                "lad_code": ["E09000001"],
                "imd_rank": [1],
                "income_rank": [1],
                "education_rank": [1],
            }
        )

        result = compute_mobility_proxy(df)
        assert len(result) == 1

    def test_extreme_weights(self):
        """Test with extreme but valid weights."""
        # Use different rank patterns to ensure components differ
        df = pd.DataFrame(
            {
                "lsoa_code": [f"E0100{i:04d}" for i in range(10)],
                "lad_name": ["Test LAD"] * 10,
                "imd_rank": list(range(1, 11)),  # 1,2,3...10
                "income_rank": list(range(10, 0, -1)),  # 10,9,8...1 (reversed)
                "education_rank": [5, 1, 8, 3, 10, 2, 7, 4, 9, 6],  # shuffled
            }
        )

        # All weight on deprivation
        result1 = compute_mobility_proxy(df, alpha=1.0, beta=0.0, gamma=0.0)
        # All weight on education
        result2 = compute_mobility_proxy(df, alpha=0.0, beta=1.0, gamma=0.0)
        # All weight on income
        result3 = compute_mobility_proxy(df, alpha=0.0, beta=0.0, gamma=1.0)

        # Results should differ because components use different rank patterns
        assert not np.allclose(result1["mobility_proxy"], result2["mobility_proxy"])
        assert not np.allclose(result2["mobility_proxy"], result3["mobility_proxy"])
