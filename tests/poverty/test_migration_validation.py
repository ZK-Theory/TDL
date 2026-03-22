"""
Tests for migration validation modules.

Tests both data processing (process_migration.py) and
validation logic (migration_validation.py).
"""

import numpy as np
import pandas as pd
import pytest


class TestLoadMigrationFlows:
    """Tests for load_migration_flows function."""

    def test_load_returns_dataframe(self):
        """Should return a DataFrame with expected columns."""
        from poverty_tda.data.process_migration import load_migration_flows

        df = load_migration_flows()

        assert isinstance(df, pd.DataFrame)
        assert "origin_lad" in df.columns
        assert "dest_lad" in df.columns
        assert "total_flow" in df.columns
        assert "working_age_flow" in df.columns

    def test_load_has_valid_flows(self):
        """Flow values should be non-negative."""
        from poverty_tda.data.process_migration import load_migration_flows

        df = load_migration_flows()

        assert (df["total_flow"] >= 0).all()
        assert (df["working_age_flow"] >= 0).all()

    def test_load_covers_expected_lads(self):
        """Should have data for a reasonable number of LADs."""
        from poverty_tda.data.process_migration import load_migration_flows

        df = load_migration_flows()

        unique_origins = df["origin_lad"].nunique()
        unique_dests = df["dest_lad"].nunique()

        # Should have 300+ LADs (England: ~309, + Scotland, Wales, NI)
        assert unique_origins >= 300
        assert unique_dests >= 300


class TestComputeLadMigrationMetrics:
    """Tests for compute_lad_migration_metrics function."""

    @pytest.fixture
    def sample_flows(self):
        """Create sample flow data for testing."""
        return pd.DataFrame(
            {
                "origin_lad": ["LAD1", "LAD1", "LAD2", "LAD2"],
                "dest_lad": ["LAD2", "LAD3", "LAD1", "LAD3"],
                "total_flow": [100, 50, 80, 30],
                "working_age_flow": [60, 25, 40, 15],
            }
        )

    def test_computes_net_migration(self, sample_flows):
        """Should compute correct net migration."""
        from poverty_tda.data.process_migration import compute_lad_migration_metrics

        metrics = compute_lad_migration_metrics(sample_flows)

        # LAD1: outflow=150, inflow=80 -> net=-70
        lad1 = metrics[metrics["lad_code"] == "LAD1"].iloc[0]
        assert lad1["total_outflow"] == 150
        assert lad1["total_inflow"] == 80
        assert lad1["net_migration"] == -70

    def test_computes_churn(self, sample_flows):
        """Should compute migration churn."""
        from poverty_tda.data.process_migration import compute_lad_migration_metrics

        metrics = compute_lad_migration_metrics(sample_flows)

        # LAD1: churn = 150 + 80 = 230
        lad1 = metrics[metrics["lad_code"] == "LAD1"].iloc[0]
        assert lad1["migration_churn"] == 230

    def test_computes_net_migration_rate(self, sample_flows):
        """Should compute normalized net migration rate."""
        from poverty_tda.data.process_migration import compute_lad_migration_metrics

        metrics = compute_lad_migration_metrics(sample_flows)

        # LAD1: rate = -70 / 230 ≈ -0.304
        lad1 = metrics[metrics["lad_code"] == "LAD1"].iloc[0]
        assert abs(lad1["net_migration_rate"] - (-70 / 230)) < 0.001


class TestMigrationEtaSquared:
    """Tests for η² computation."""

    @pytest.fixture
    def sample_gdf(self):
        """Create sample GeoDataFrame for testing."""
        return pd.DataFrame(
            {
                "lsoa_code": [f"LSOA_{i}" for i in range(100)],
                "ms_basin": [i // 10 for i in range(100)],  # 10 basins x 10 each
                "kmeans_cluster": [i // 20 for i in range(100)],  # 5 clusters x 20 each
                "net_migration_rate": np.random.randn(100) + [i // 10 * 0.1 for i in range(100)],
            }
        )

    def test_eta_squared_returns_valid_values(self, sample_gdf):
        """η² should be between 0 and 1."""
        from poverty_tda.validation.migration_validation import compute_migration_eta_squared

        result = compute_migration_eta_squared(sample_gdf, "ms_basin", "net_migration_rate", n_bootstrap=100)

        assert 0 <= result["eta_squared"] <= 1
        assert 0 <= result["eta_squared_ci_lower"] <= result["eta_squared"]
        assert result["eta_squared"] <= result["eta_squared_ci_upper"] <= 1

    def test_eta_squared_handles_missing_data(self):
        """Should handle NaN values gracefully."""
        from poverty_tda.validation.migration_validation import compute_migration_eta_squared

        df = pd.DataFrame({"cluster": [1, 1, 2, 2, np.nan], "value": [1.0, 2.0, np.nan, 4.0, 5.0]})

        result = compute_migration_eta_squared(df, "cluster", "value", n_bootstrap=50)

        # Should still return a result (using valid rows only)
        assert result["n_observations"] == 3  # 2 rows have valid cluster AND value


class TestCompareMethods:
    """Tests for compare_methods_migration function."""

    def test_returns_sorted_dataframe(self):
        """Should return methods sorted by η²."""
        from poverty_tda.validation.migration_validation import compare_methods_migration

        df = pd.DataFrame(
            {
                "ms_basin": [1, 1, 1, 2, 2, 2],
                "kmeans": [1, 1, 2, 2, 3, 3],
                "net_migration_rate": [1.0, 1.1, 1.0, 5.0, 5.1, 5.0],
            }
        )

        result = compare_methods_migration(df, ["ms_basin", "kmeans"], "net_migration_rate", n_bootstrap=50)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        # Should be sorted descending by η²
        assert result.iloc[0]["eta_squared"] >= result.iloc[1]["eta_squared"]


class TestEscapeRateBySeverity:
    """Tests for escape rate stratification."""

    def test_computes_quantiles(self):
        """Should stratify basins by severity quartiles."""
        from poverty_tda.validation.migration_validation import compute_escape_rate_by_severity

        df = pd.DataFrame(
            {
                "ms_basin": list(range(20)),
                "mean_imd": np.linspace(0.1, 1.0, 20),  # Severity gradient
                "escape_ratio": np.linspace(0.8, 0.2, 20),  # Higher severity → lower escape
            }
        )

        result = compute_escape_rate_by_severity(df, n_quantiles=4)

        assert len(result) == 4
        assert "Q1" in result["severity_quantile"].values
        assert "Q4" in result["severity_quantile"].values


class TestIntegration:
    """Integration tests for full migration validation pipeline."""

    @pytest.mark.slow
    def test_full_pipeline_loads_real_data(self):
        """Should successfully load and process real migration data."""
        from poverty_tda.data.process_migration import load_migration_flows, compute_lad_migration_metrics

        flows = load_migration_flows()
        metrics = compute_lad_migration_metrics(flows)

        # Basic sanity checks
        assert len(metrics) >= 300  # Should have 300+ LADs
        assert "net_migration" in metrics.columns
        assert "net_migration_rate" in metrics.columns

        # Net migration should sum to ~0 nationally (closed system ignoring international)
        # Allow for some rounding
        total_net = metrics["net_migration"].sum()
        assert abs(total_net) < 1  # Should be very close to 0
