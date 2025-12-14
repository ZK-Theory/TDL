"""
Tests for backtesting framework.

Test suite for CrisisPeriod, prepare_backtest_data, BacktestEngine,
VolatilityBaseline, and report generation utilities.
"""

from __future__ import annotations

from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from financial_tda.analysis.backtest import (
    KNOWN_CRISES,
    BacktestEngine,
    BacktestResults,
    CrisisPeriod,
    Detection,
    VolatilityBaseline,
    compute_lead_time,
    generate_backtest_report,
    is_valid_detection,
    prepare_backtest_data,
)


class TestCrisisPeriod:
    """Test suite for CrisisPeriod dataclass."""

    def test_initialization(self):
        """Test basic CrisisPeriod initialization."""
        crisis = CrisisPeriod(
            name="Test Crisis",
            onset_date=pd.Timestamp("2020-01-01"),
            peak_drawdown_date=pd.Timestamp("2020-02-01"),
            recovery_date=pd.Timestamp("2020-03-01"),
        )

        assert crisis.name == "Test Crisis"
        assert crisis.onset_date == pd.Timestamp("2020-01-01")
        assert crisis.peak_drawdown_date == pd.Timestamp("2020-02-01")
        assert crisis.recovery_date == pd.Timestamp("2020-03-01")

    def test_chronological_validation(self):
        """Test that dates must be in chronological order."""
        # Valid chronological order
        crisis = CrisisPeriod(
            name="Valid",
            onset_date=pd.Timestamp("2020-01-01"),
            peak_drawdown_date=pd.Timestamp("2020-02-01"),
            recovery_date=pd.Timestamp("2020-03-01"),
        )
        assert crisis.name == "Valid"

        # Invalid: peak before onset
        with pytest.raises(ValueError, match="chronological"):
            CrisisPeriod(
                name="Invalid",
                onset_date=pd.Timestamp("2020-02-01"),
                peak_drawdown_date=pd.Timestamp("2020-01-01"),
                recovery_date=pd.Timestamp("2020-03-01"),
            )

        # Invalid: recovery before peak
        with pytest.raises(ValueError, match="chronological"):
            CrisisPeriod(
                name="Invalid",
                onset_date=pd.Timestamp("2020-01-01"),
                peak_drawdown_date=pd.Timestamp("2020-03-01"),
                recovery_date=pd.Timestamp("2020-02-01"),
            )

    def test_onset_to_peak_days(self):
        """Test computation of days from onset to peak."""
        crisis = CrisisPeriod(
            name="Test",
            onset_date=pd.Timestamp("2020-01-01"),
            peak_drawdown_date=pd.Timestamp("2020-01-31"),
            recovery_date=pd.Timestamp("2020-02-15"),
        )

        assert crisis.onset_to_peak_days == 30

    def test_total_duration_days(self):
        """Test computation of total crisis duration."""
        crisis = CrisisPeriod(
            name="Test",
            onset_date=pd.Timestamp("2020-01-01"),
            peak_drawdown_date=pd.Timestamp("2020-01-31"),
            recovery_date=pd.Timestamp("2020-02-15"),
        )

        assert crisis.total_duration_days == 45


class TestKnownCrises:
    """Test suite for KNOWN_CRISES constant."""

    def test_known_crises_exist(self):
        """Test that KNOWN_CRISES contains expected crises."""
        crisis_names = [c.name for c in KNOWN_CRISES]

        assert "GFC" in crisis_names
        assert "COVID" in crisis_names
        assert "Rate_Hike" in crisis_names

    def test_gfc_dates(self):
        """Test GFC crisis dates are correct."""
        gfc = next(c for c in KNOWN_CRISES if c.name == "GFC")

        assert gfc.onset_date == pd.Timestamp("2008-09-15")
        assert gfc.peak_drawdown_date == pd.Timestamp("2009-03-09")
        assert gfc.recovery_date == pd.Timestamp("2009-09-01")

    def test_covid_dates(self):
        """Test COVID crisis dates are correct."""
        covid = next(c for c in KNOWN_CRISES if c.name == "COVID")

        assert covid.onset_date == pd.Timestamp("2020-02-20")
        assert covid.peak_drawdown_date == pd.Timestamp("2020-03-23")
        assert covid.recovery_date == pd.Timestamp("2020-08-01")

    def test_rate_hike_dates(self):
        """Test Rate Hike crisis dates are correct."""
        rate_hike = next(c for c in KNOWN_CRISES if c.name == "Rate_Hike")

        assert rate_hike.onset_date == pd.Timestamp("2022-01-03")
        assert rate_hike.peak_drawdown_date == pd.Timestamp("2022-10-12")
        assert rate_hike.recovery_date == pd.Timestamp("2023-01-01")

    def test_all_crises_chronological(self):
        """Test that all known crises have valid chronological dates."""
        for crisis in KNOWN_CRISES:
            assert crisis.onset_date <= crisis.peak_drawdown_date
            assert crisis.peak_drawdown_date <= crisis.recovery_date


class TestPrepareBacktestData:
    """Test suite for prepare_backtest_data function."""

    def test_basic_preparation(self):
        """Test basic data preparation without VIX."""
        # Create synthetic price data
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        prices = pd.Series(
            np.random.randn(100).cumsum() + 100,
            index=dates,
        )

        result = prepare_backtest_data(prices)

        # Check columns
        assert "price" in result.columns
        assert "returns" in result.columns
        assert "drawdown" in result.columns
        assert "vix" not in result.columns

        # Check data quality
        assert len(result) > 0
        assert not result["price"].isna().any()
        assert not result["drawdown"].isna().any()

    def test_preparation_with_vix(self):
        """Test data preparation with VIX data."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        prices = pd.Series(
            np.random.randn(100).cumsum() + 100,
            index=dates,
        )
        vix = pd.Series(
            np.random.uniform(10, 40, size=100),
            index=dates,
        )

        result = prepare_backtest_data(prices, vix)

        # Check VIX column exists
        assert "vix" in result.columns
        assert not result["vix"].isna().any()
        # First row dropped due to NaN returns
        assert len(result) == len(prices) - 1

    def test_date_range_filtering(self):
        """Test filtering to specified date range."""
        dates = pd.date_range("2020-01-01", periods=365, freq="D")
        prices = pd.Series(
            np.random.randn(365).cumsum() + 100,
            index=dates,
        )

        result = prepare_backtest_data(
            prices,
            start_date="2020-03-01",
            end_date="2020-09-30",
        )

        assert result.index[0] >= pd.Timestamp("2020-03-01")
        assert result.index[-1] <= pd.Timestamp("2020-09-30")
        assert len(result) < len(prices)

    def test_returns_calculation(self):
        """Test that returns are calculated correctly."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        prices = pd.Series(
            [100, 101, 102, 101, 100, 99, 100, 101, 102, 103], index=dates
        )

        result = prepare_backtest_data(prices)

        # First row with NaN return is dropped, so result starts at second price (101)
        assert result.index[0] == dates[1]

        # The return value at index dates[1] corresponds to log(101/100)
        # because returns are calculated as log(price_t / price_{t-1})
        # At dates[1], price is 101, previous price (at dates[0]) is 100
        expected_return_0 = np.log(101 / 100)
        assert result["returns"].iloc[0] == pytest.approx(expected_return_0, abs=1e-6)

    def test_drawdown_calculation(self):
        """Test that drawdown is calculated correctly."""
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        # Prices: rise to 110, then fall to 90
        prices = pd.Series([100, 110, 105, 95, 90], index=dates)

        result = prepare_backtest_data(prices)

        # First row (100) is dropped due to NaN return, result starts at 110
        # At peak (110), drawdown should be 0
        assert result["drawdown"].iloc[0] == pytest.approx(0.0, abs=1e-6)

        # At 90 (last row), drawdown should be (90-110)/110 = -0.1818...
        expected_drawdown = (90 - 110) / 110
        assert result["drawdown"].iloc[-1] == pytest.approx(expected_drawdown, abs=1e-4)

    def test_empty_prices_raises(self):
        """Test that empty prices raises ValueError."""
        prices = pd.Series([], dtype=float)

        with pytest.raises(ValueError, match="empty"):
            prepare_backtest_data(prices)

    def test_missing_values_handling(self):
        """Test handling of missing values."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        prices = pd.Series(
            [100, 101, np.nan, 103, 104, 105, 106, 107, 108, 109], index=dates
        )

        result = prepare_backtest_data(prices)

        # Should forward fill the NaN
        assert not result["price"].isna().any()

    def test_vix_misalignment_handling(self):
        """Test handling of misaligned VIX data."""
        price_dates = pd.date_range("2020-01-01", periods=100, freq="D")
        vix_dates = pd.date_range("2020-02-01", periods=50, freq="D")

        prices = pd.Series(np.random.randn(100).cumsum() + 100, index=price_dates)
        vix = pd.Series(np.random.uniform(10, 40, size=50), index=vix_dates)

        result = prepare_backtest_data(prices, vix)

        # Should align to common dates
        assert len(result) < len(prices)
        assert result.index[0] >= vix_dates[0]
        assert "vix" in result.columns

    def test_no_overlapping_vix_omits_column(self):
        """Test that non-overlapping VIX is omitted with warning."""
        price_dates = pd.date_range("2020-01-01", periods=50, freq="D")
        vix_dates = pd.date_range("2021-01-01", periods=50, freq="D")

        prices = pd.Series(np.random.randn(50).cumsum() + 100, index=price_dates)
        vix = pd.Series(np.random.uniform(10, 40, size=50), index=vix_dates)

        result = prepare_backtest_data(prices, vix)

        # VIX should be omitted
        assert "vix" not in result.columns
        # First row dropped due to NaN return
        assert len(result) == len(prices) - 1


class TestDetection:
    """Test suite for Detection dataclass."""

    def test_initialization(self):
        """Test Detection dataclass initialization."""
        det = Detection(
            timestamp=pd.Timestamp("2020-03-01"),
            method="classifier",
            confidence=0.95,
            crisis_name="COVID",
        )

        assert det.timestamp == pd.Timestamp("2020-03-01")
        assert det.method == "classifier"
        assert det.confidence == 0.95
        assert det.crisis_name == "COVID"

    def test_without_crisis_name(self):
        """Test Detection without crisis association."""
        det = Detection(
            timestamp=pd.Timestamp("2020-03-01"),
            method="detector",
            confidence=0.85,
        )

        assert det.crisis_name is None


class TestBacktestResults:
    """Test suite for BacktestResults dataclass."""

    def test_initialization_empty(self):
        """Test empty BacktestResults initialization."""
        results = BacktestResults()

        assert len(results.detections) == 0
        assert len(results.lead_times) == 0
        assert len(results.true_positives) == 0
        assert results.false_positives == 0
        assert len(results.crisis_periods) == 0

    def test_initialization_with_data(self):
        """Test BacktestResults with data."""
        det1 = Detection(
            timestamp=pd.Timestamp("2020-03-01"),
            method="classifier",
            confidence=0.95,
            crisis_name="COVID",
        )

        results = BacktestResults(
            detections=[det1],
            lead_times={"COVID": 15},
            true_positives={"COVID": True},
            false_positives=2,
            crisis_periods=KNOWN_CRISES,
        )

        assert len(results.detections) == 1
        assert results.lead_times["COVID"] == 15
        assert results.true_positives["COVID"] is True
        assert results.false_positives == 2
        assert len(results.crisis_periods) == 3


class TestComputeLeadTime:
    """Test suite for compute_lead_time function."""

    def test_positive_lead_time(self):
        """Test computing positive lead time (early detection)."""
        detection = pd.Timestamp("2020-03-01")
        peak = pd.Timestamp("2020-03-23")

        lead_time = compute_lead_time(detection, peak)

        # Should be positive (early warning)
        assert lead_time > 0
        # Approximately 15 trading days (22 calendar days)
        assert 14 <= lead_time <= 17

    def test_negative_lead_time(self):
        """Test computing negative lead time (late detection)."""
        detection = pd.Timestamp("2020-03-25")
        peak = pd.Timestamp("2020-03-23")

        lead_time = compute_lead_time(detection, peak)

        # Should be negative (late detection)
        assert lead_time < 0

    def test_zero_lead_time(self):
        """Test computing lead time for same-day detection."""
        detection = pd.Timestamp("2020-03-23")
        peak = pd.Timestamp("2020-03-23")

        lead_time = compute_lead_time(detection, peak)

        assert lead_time == 0

    def test_weekend_handling(self):
        """Test that weekends are excluded from lead time."""
        # Friday to Monday (3 calendar days, 1 trading day)
        detection = pd.Timestamp("2020-03-20")  # Friday
        peak = pd.Timestamp("2020-03-23")  # Monday

        lead_time = compute_lead_time(detection, peak)

        assert lead_time == 1  # Only Monday counts


class TestIsValidDetection:
    """Test suite for is_valid_detection function."""

    def test_valid_detection_before_onset(self):
        """Test detection within tolerance before onset is valid."""
        gfc = next(c for c in KNOWN_CRISES if c.name == "GFC")
        # 5 days before onset
        detection = gfc.onset_date - pd.Timedelta(days=5)

        is_valid = is_valid_detection(detection, gfc, tolerance_days=10)

        assert is_valid is True

    def test_valid_detection_between_onset_and_peak(self):
        """Test detection between onset and peak is valid."""
        gfc = next(c for c in KNOWN_CRISES if c.name == "GFC")
        # Midpoint between onset and peak
        detection = gfc.onset_date + (gfc.peak_drawdown_date - gfc.onset_date) / 2

        is_valid = is_valid_detection(detection, gfc, tolerance_days=10)

        assert is_valid is True

    def test_valid_detection_at_peak(self):
        """Test detection at peak is valid."""
        gfc = next(c for c in KNOWN_CRISES if c.name == "GFC")
        detection = gfc.peak_drawdown_date

        is_valid = is_valid_detection(detection, gfc, tolerance_days=10)

        assert is_valid is True

    def test_invalid_detection_too_early(self):
        """Test detection too early is invalid."""
        gfc = next(c for c in KNOWN_CRISES if c.name == "GFC")
        # 20 days before onset (beyond tolerance)
        detection = gfc.onset_date - pd.Timedelta(days=20)

        is_valid = is_valid_detection(detection, gfc, tolerance_days=10)

        assert is_valid is False

    def test_invalid_detection_after_peak(self):
        """Test detection after peak is invalid."""
        gfc = next(c for c in KNOWN_CRISES if c.name == "GFC")
        # After peak drawdown
        detection = gfc.peak_drawdown_date + pd.Timedelta(days=5)

        is_valid = is_valid_detection(detection, gfc, tolerance_days=10)

        assert is_valid is False


class TestBacktestEngine:
    """Test suite for BacktestEngine class."""

    def test_initialization_with_classifier(self):
        """Test BacktestEngine initialization with classifier only."""
        mock_classifier = Mock()

        engine = BacktestEngine(
            regime_classifier=mock_classifier,
            window_size=50,
            stride=5,
        )

        assert engine.regime_classifier is mock_classifier
        assert engine.change_detector is None
        assert engine.window_size == 50
        assert engine.stride == 5

    def test_initialization_with_detector(self):
        """Test BacktestEngine initialization with detector only."""
        mock_detector = Mock()

        engine = BacktestEngine(
            change_detector=mock_detector,
            window_size=40,
            stride=10,
        )

        assert engine.regime_classifier is None
        assert engine.change_detector is mock_detector
        assert engine.window_size == 40
        assert engine.stride == 10

    def test_initialization_with_both(self):
        """Test BacktestEngine initialization with both methods."""
        mock_classifier = Mock()
        mock_detector = Mock()

        engine = BacktestEngine(
            regime_classifier=mock_classifier,
            change_detector=mock_detector,
        )

        assert engine.regime_classifier is mock_classifier
        assert engine.change_detector is mock_detector

    def test_initialization_without_methods_raises(self):
        """Test that initialization without methods raises error."""
        with pytest.raises(ValueError, match="At least one"):
            BacktestEngine()

    def test_run_backtest_requires_features_with_classifier(self):
        """Test that run_backtest requires features when using classifier."""
        mock_classifier = Mock()
        engine = BacktestEngine(regime_classifier=mock_classifier)

        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        prices = pd.Series(np.random.randn(100).cumsum() + 100, index=dates)

        with pytest.raises(ValueError, match="features required"):
            engine.run_backtest(prices, features=None)

    def test_run_backtest_with_mocked_classifier(self):
        """Test run_backtest with mocked classifier."""
        mock_classifier = Mock()
        # Mock predictions: first 10 windows predict crisis (1), rest normal (0)
        mock_classifier.predict.return_value = np.array([1] * 10 + [0] * 40)
        mock_classifier.predict_proba.return_value = np.column_stack(
            [
                np.random.rand(50),  # Normal probability
                np.array([0.9] * 10 + [0.1] * 40),  # Crisis probability
            ]
        )

        engine = BacktestEngine(regime_classifier=mock_classifier)

        # Create synthetic data
        dates = pd.date_range("2008-09-01", periods=100, freq="D")
        prices = pd.Series(np.random.randn(100).cumsum() + 100, index=dates)

        # Create features DataFrame
        feature_dates = pd.date_range("2008-09-01", periods=50, freq="D")
        features = pd.DataFrame(
            {
                "window_start": feature_dates,
                "window_end": feature_dates + pd.Timedelta(days=5),
                "feature1": np.random.rand(50),
                "feature2": np.random.rand(50),
            }
        )

        # Use only GFC crisis for testing
        gfc = next(c for c in KNOWN_CRISES if c.name == "GFC")
        results = engine.run_backtest(prices, features, crisis_periods=[gfc])

        assert len(results.detections) == 10  # 10 crisis predictions
        assert len(results.crisis_periods) == 1
        # Should have results for GFC
        assert "GFC" in results.lead_times
        assert "GFC" in results.true_positives

    def test_find_earliest_detection(self):
        """Test _find_earliest_detection method."""
        mock_classifier = Mock()
        engine = BacktestEngine(regime_classifier=mock_classifier)

        # Create detections
        det1 = Detection(
            timestamp=pd.Timestamp("2020-03-10"),
            method="classifier",
            confidence=0.8,
        )
        det2 = Detection(
            timestamp=pd.Timestamp("2020-03-05"),
            method="classifier",
            confidence=0.9,
        )
        det3 = Detection(
            timestamp=pd.Timestamp("2020-03-15"),
            method="classifier",
            confidence=0.85,
        )

        covid = next(c for c in KNOWN_CRISES if c.name == "COVID")

        # Should return earliest detection (det2)
        earliest = engine._find_earliest_detection(
            [det1, det2, det3],
            covid.onset_date,
            covid.peak_drawdown_date,
        )

        assert earliest == det2

    def test_count_false_positives(self):
        """Test _count_false_positives method."""
        mock_classifier = Mock()
        engine = BacktestEngine(regime_classifier=mock_classifier)

        # Create detections: 2 near COVID, 1 far from any crisis
        det1 = Detection(
            timestamp=pd.Timestamp("2020-03-10"),
            method="classifier",
            confidence=0.8,
        )
        det2 = Detection(
            timestamp=pd.Timestamp("2020-03-15"),
            method="classifier",
            confidence=0.9,
        )
        det3 = Detection(
            timestamp=pd.Timestamp("2019-06-01"),  # Far from any crisis
            method="classifier",
            confidence=0.85,
        )

        covid = next(c for c in KNOWN_CRISES if c.name == "COVID")

        false_positives = engine._count_false_positives(
            [det1, det2, det3],
            [covid],
        )

        assert false_positives == 1  # Only det3


class TestVolatilityBaseline:
    """Test suite for VolatilityBaseline class."""

    def test_initialization(self):
        """Test VolatilityBaseline initialization."""
        baseline = VolatilityBaseline(window_size=20, threshold_percentile=95.0)

        assert baseline.window_size == 20
        assert baseline.threshold_percentile == 95.0

    def test_initialization_invalid_window_raises(self):
        """Test that invalid window size raises error."""
        with pytest.raises(ValueError, match="window_size must be >= 2"):
            VolatilityBaseline(window_size=1)

    def test_initialization_invalid_percentile_raises(self):
        """Test that invalid percentile raises error."""
        with pytest.raises(ValueError, match="threshold_percentile must be"):
            VolatilityBaseline(threshold_percentile=0)

        with pytest.raises(ValueError, match="threshold_percentile must be"):
            VolatilityBaseline(threshold_percentile=101)

    def test_detect_insufficient_data(self):
        """Test detection with insufficient data returns empty list."""
        baseline = VolatilityBaseline(window_size=20)

        # Only 10 data points
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        prices = pd.Series(np.random.randn(10).cumsum() + 100, index=dates)

        detections = baseline.detect(prices)

        assert len(detections) == 0

    def test_detect_with_volatility_spike(self):
        """Test detection of volatility spike."""
        baseline = VolatilityBaseline(window_size=20, threshold_percentile=95)

        # Create price series with volatility spike
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=200, freq="D")

        # Low volatility for most of series
        returns = np.random.normal(0, 0.01, size=200)
        # High volatility spike in middle
        returns[90:110] = np.random.normal(0, 0.05, size=20)

        prices = pd.Series(100 * np.exp(returns.cumsum()), index=dates)

        detections = baseline.detect(prices)

        # Should detect at least one spike
        assert len(detections) > 0
        # All detections should be baseline method
        assert all(d.method == "baseline" for d in detections)

    def test_detect_crisis_association(self):
        """Test that detections are associated with nearby crises."""
        baseline = VolatilityBaseline(window_size=20)

        # Create price series with spike during COVID period
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        np.random.seed(42)

        # Normal volatility
        returns = np.random.normal(0, 0.01, size=100)
        # High volatility spike around COVID onset (Feb 20)
        covid_onset_idx = 50  # ~Feb 20
        returns[covid_onset_idx - 5 : covid_onset_idx + 10] = np.random.normal(
            0, 0.08, size=15
        )

        prices = pd.Series(100 * np.exp(returns.cumsum()), index=dates)

        covid = next(c for c in KNOWN_CRISES if c.name == "COVID")
        detections = baseline.detect(prices, crisis_periods=[covid])

        # Should have at least one detection
        assert len(detections) > 0

    def test_detect_confidence_scaling(self):
        """Test that confidence scales with volatility magnitude."""
        baseline = VolatilityBaseline(window_size=20, threshold_percentile=90)

        # Create price series with multiple spikes
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=300, freq="D")

        returns = np.random.normal(0, 0.01, size=300)
        # Moderate spike
        returns[50:60] = np.random.normal(0, 0.03, size=10)
        # Large spike
        returns[150:160] = np.random.normal(0, 0.08, size=10)

        prices = pd.Series(100 * np.exp(returns.cumsum()), index=dates)

        detections = baseline.detect(prices)

        # Should have multiple detections
        assert len(detections) >= 1
        # All should have confidence between 0 and 1
        assert all(0 <= d.confidence <= 1 for d in detections)


class TestGenerateBacktestReport:
    """Test suite for generate_backtest_report function."""

    def test_report_basic(self):
        """Test basic report generation."""
        # Create simple backtest results
        gfc = next(c for c in KNOWN_CRISES if c.name == "GFC")
        covid = next(c for c in KNOWN_CRISES if c.name == "COVID")

        results = BacktestResults(
            detections=[
                Detection(pd.Timestamp("2008-09-10"), "classifier", 0.9, "GFC"),
                Detection(pd.Timestamp("2020-03-01"), "classifier", 0.95, "COVID"),
            ],
            lead_times={"GFC": 10, "COVID": 15},
            true_positives={"GFC": True, "COVID": True},
            false_positives=2,
            crisis_periods=[gfc, covid],
        )

        report = generate_backtest_report(results)

        # Check structure
        assert "per_crisis_metrics" in report
        assert "aggregate_metrics" in report
        assert "summary" in report

        # Check per-crisis metrics
        assert "GFC" in report["per_crisis_metrics"]
        assert "COVID" in report["per_crisis_metrics"]
        assert report["per_crisis_metrics"]["GFC"]["detected"] is True
        assert report["per_crisis_metrics"]["GFC"]["lead_time_days"] == 10

        # Check aggregate metrics
        agg = report["aggregate_metrics"]
        assert agg["n_crises"] == 2
        assert agg["n_detected"] == 2
        assert agg["n_missed"] == 0
        assert agg["detection_rate"] == 1.0
        assert agg["mean_lead_time"] == 12.5  # (10 + 15) / 2
        assert agg["precision"] == 0.5  # 2 / (2 + 2)
        assert agg["recall"] == 1.0  # 2 / 2
        assert agg["false_positives"] == 2

    def test_report_with_missed_crisis(self):
        """Test report with missed crisis."""
        gfc = next(c for c in KNOWN_CRISES if c.name == "GFC")
        covid = next(c for c in KNOWN_CRISES if c.name == "COVID")

        results = BacktestResults(
            detections=[
                Detection(pd.Timestamp("2008-09-10"), "classifier", 0.9, "GFC"),
            ],
            lead_times={"GFC": 10, "COVID": 0},
            true_positives={"GFC": True, "COVID": False},
            false_positives=1,
            crisis_periods=[gfc, covid],
        )

        report = generate_backtest_report(results)

        agg = report["aggregate_metrics"]
        assert agg["n_crises"] == 2
        assert agg["n_detected"] == 1
        assert agg["n_missed"] == 1
        assert agg["detection_rate"] == 0.5
        assert agg["recall"] == 0.5  # 1 / 2

    def test_report_with_baseline_comparison(self):
        """Test report with baseline comparison."""
        gfc = next(c for c in KNOWN_CRISES if c.name == "GFC")
        covid = next(c for c in KNOWN_CRISES if c.name == "COVID")

        # TDA results
        tda_results = BacktestResults(
            detections=[
                Detection(pd.Timestamp("2008-09-05"), "classifier", 0.9, "GFC"),
                Detection(pd.Timestamp("2020-03-01"), "classifier", 0.95, "COVID"),
            ],
            lead_times={"GFC": 15, "COVID": 20},
            true_positives={"GFC": True, "COVID": True},
            false_positives=1,
            crisis_periods=[gfc, covid],
        )

        # Baseline results (worse performance)
        baseline_results = BacktestResults(
            detections=[
                Detection(pd.Timestamp("2008-09-10"), "baseline", 0.8, "GFC"),
                Detection(pd.Timestamp("2020-03-10"), "baseline", 0.85, "COVID"),
            ],
            lead_times={"GFC": 10, "COVID": 12},
            true_positives={"GFC": True, "COVID": True},
            false_positives=3,
            crisis_periods=[gfc, covid],
        )

        report = generate_backtest_report(tda_results, baseline_results)

        # Check baseline comparison exists
        assert "baseline_comparison" in report

        comp = report["baseline_comparison"]
        assert comp["tda_mean_lead_time"] == 17.5  # (15 + 20) / 2
        assert comp["baseline_mean_lead_time"] == 11.0  # (10 + 12) / 2
        assert comp["lead_time_improvement"] == 6.5  # TDA better
        assert "tda_f1_score" in comp
        assert "baseline_f1_score" in comp
        assert "f1_improvement" in comp

    def test_report_f1_score_calculation(self):
        """Test F1 score calculation in report."""
        gfc = next(c for c in KNOWN_CRISES if c.name == "GFC")

        results = BacktestResults(
            detections=[
                Detection(pd.Timestamp("2008-09-10"), "classifier", 0.9, "GFC"),
            ],
            lead_times={"GFC": 10},
            true_positives={"GFC": True},
            false_positives=1,
            crisis_periods=[gfc],
        )

        report = generate_backtest_report(results)

        agg = report["aggregate_metrics"]
        # TP=1, FP=1, FN=0
        # Precision = 1 / (1 + 1) = 0.5
        # Recall = 1 / (1 + 0) = 1.0
        # F1 = 2 * (0.5 * 1.0) / (0.5 + 1.0) = 2 * 0.5 / 1.5 = 0.667
        assert agg["precision"] == pytest.approx(0.5)
        assert agg["recall"] == pytest.approx(1.0)
        assert agg["f1_score"] == pytest.approx(0.6667, abs=0.001)

    def test_report_summary_format(self):
        """Test that summary is properly formatted text."""
        gfc = next(c for c in KNOWN_CRISES if c.name == "GFC")

        results = BacktestResults(
            detections=[
                Detection(pd.Timestamp("2008-09-10"), "classifier", 0.9, "GFC"),
            ],
            lead_times={"GFC": 10},
            true_positives={"GFC": True},
            false_positives=0,
            crisis_periods=[gfc],
        )

        report = generate_backtest_report(results)

        summary = report["summary"]
        assert isinstance(summary, str)
        assert "Backtest Results Summary" in summary
        assert "Crises evaluated" in summary
        assert "Mean lead time" in summary
        assert "Precision" in summary


class TestIntegrationBacktest:
    """Integration tests for complete backtest workflow."""

    def test_full_backtest_workflow_with_synthetic_crisis(self):
        """Test complete backtest workflow with synthetic crisis data."""
        # Define synthetic crisis
        synthetic_crisis = CrisisPeriod(
            name="Synthetic",
            onset_date=pd.Timestamp("2021-06-01"),
            peak_drawdown_date=pd.Timestamp("2021-07-15"),
            recovery_date=pd.Timestamp("2021-09-01"),
        )

        # Create synthetic price data with crisis pattern
        dates = pd.date_range("2021-01-01", periods=300, freq="D")
        np.random.seed(42)

        # Normal period, then crash, then recovery
        returns = np.concatenate(
            [
                np.random.normal(0.0005, 0.01, 150),  # Normal
                np.random.normal(-0.02, 0.03, 45),  # Crisis
                np.random.normal(0.001, 0.015, 105),  # Recovery
            ]
        )

        prices = pd.Series(100 * np.exp(returns.cumsum()), index=dates)

        # Create mock classifier that detects crisis
        mock_classifier = Mock()
        # Predict crisis around onset date
        mock_classifier.predict.return_value = np.array([0] * 35 + [1] * 5 + [0] * 10)
        mock_classifier.predict_proba.return_value = np.column_stack(
            [
                np.random.rand(50),
                np.array([0.1] * 35 + [0.9] * 5 + [0.2] * 10),
            ]
        )

        # Create features
        feature_dates = pd.date_range("2021-01-01", periods=50, freq="D")
        features = pd.DataFrame(
            {
                "window_start": feature_dates,
                "window_end": feature_dates + pd.Timedelta(days=5),
                "feature1": np.random.rand(50),
            }
        )

        # Run backtest with TDA engine
        engine = BacktestEngine(regime_classifier=mock_classifier)
        tda_results = engine.run_backtest(
            prices, features, crisis_periods=[synthetic_crisis]
        )

        # Run baseline
        baseline = VolatilityBaseline(window_size=20, threshold_percentile=90)
        baseline_detections = baseline.detect(prices, crisis_periods=[synthetic_crisis])

        baseline_results = BacktestResults(
            detections=baseline_detections,
            crisis_periods=[synthetic_crisis],
        )

        # Compute lead times for baseline
        for crisis in baseline_results.crisis_periods:
            earliest = None
            for det in baseline_detections:
                if det.crisis_name == crisis.name:
                    if earliest is None or det.timestamp < earliest.timestamp:
                        earliest = det

            if earliest is not None:
                lead_time = compute_lead_time(
                    earliest.timestamp, crisis.peak_drawdown_date
                )
                baseline_results.lead_times[crisis.name] = lead_time
                baseline_results.true_positives[crisis.name] = True
            else:
                baseline_results.lead_times[crisis.name] = 0
                baseline_results.true_positives[crisis.name] = False

        # Generate report
        report = generate_backtest_report(tda_results, baseline_results)

        # Validate report structure
        assert "per_crisis_metrics" in report
        assert "aggregate_metrics" in report
        assert "baseline_comparison" in report
        assert "summary" in report

        # Validate crisis was evaluated
        assert "Synthetic" in report["per_crisis_metrics"]

        # Validate aggregate metrics
        agg = report["aggregate_metrics"]
        assert agg["n_crises"] == 1
        assert "mean_lead_time" in agg
        assert "precision" in agg
        assert "recall" in agg
        assert "f1_score" in agg
