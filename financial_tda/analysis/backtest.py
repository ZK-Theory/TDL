"""
Backtesting framework for historical crisis detection.

This module provides tools for evaluating regime classifier and change-point
detector performance on historical market crises, computing detection lead times,
and comparing against baseline methods.

References:
    Gidea, M., & Katz, Y. (2018). Topological data analysis of financial
        time series: Landscapes of crashes. Physica A, 491, 820-834.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from financial_tda.models.change_point_detector import ChangePointDetector
    from financial_tda.models.regime_classifier import RegimeClassifier

logger = logging.getLogger(__name__)


@dataclass
class CrisisPeriod:
    """
    Definition of a historical financial crisis period.

    Attributes:
        name: Human-readable crisis name (e.g., "GFC", "COVID").
        onset_date: First signal of trouble / market stress begins.
        peak_drawdown_date: Date of maximum drawdown (worst point).
        recovery_date: End of crisis / return to stability.

    Examples:
        >>> gfc = CrisisPeriod(
        ...     name="GFC",
        ...     onset_date=pd.Timestamp("2008-09-15"),
        ...     peak_drawdown_date=pd.Timestamp("2009-03-09"),
        ...     recovery_date=pd.Timestamp("2009-09-01")
        ... )
        >>> print(gfc.name, gfc.peak_drawdown_date)

    Notes:
        - onset_date: Crisis detection should occur before or near this date
        - peak_drawdown_date: Key reference for computing lead time
        - recovery_date: End of crisis window for evaluation
    """

    name: str
    onset_date: pd.Timestamp
    peak_drawdown_date: pd.Timestamp
    recovery_date: pd.Timestamp

    def __post_init__(self) -> None:
        """Validate crisis period dates are in correct chronological order."""
        if not (self.onset_date <= self.peak_drawdown_date <= self.recovery_date):
            raise ValueError(
                f"Crisis dates must be chronological: onset <= peak_drawdown <= recovery. "
                f"Got: {self.onset_date} <= {self.peak_drawdown_date} <= {self.recovery_date}"
            )

    @property
    def onset_to_peak_days(self) -> int:
        """
        Number of days from crisis onset to peak drawdown.

        Returns:
            Calendar days between onset and peak drawdown.

        Examples:
            >>> gfc.onset_to_peak_days
            175
        """
        return (self.peak_drawdown_date - self.onset_date).days

    @property
    def total_duration_days(self) -> int:
        """
        Total crisis duration from onset to recovery.

        Returns:
            Calendar days from onset to recovery.

        Examples:
            >>> gfc.total_duration_days
            351
        """
        return (self.recovery_date - self.onset_date).days


# Known historical crises with onset, peak drawdown, and recovery dates
KNOWN_CRISES = [
    CrisisPeriod(
        name="GFC",
        onset_date=pd.Timestamp("2008-09-15"),  # Lehman Brothers collapse
        peak_drawdown_date=pd.Timestamp("2009-03-09"),  # S&P 500 bottom at 676
        recovery_date=pd.Timestamp("2009-09-01"),  # Return to relative stability
    ),
    CrisisPeriod(
        name="COVID",
        onset_date=pd.Timestamp("2020-02-20"),  # Market starts rapid decline
        peak_drawdown_date=pd.Timestamp("2020-03-23"),  # S&P 500 bottom at 2,237
        recovery_date=pd.Timestamp("2020-08-01"),  # Recovery to pre-crisis levels
    ),
    CrisisPeriod(
        name="Rate_Hike",
        onset_date=pd.Timestamp("2022-01-03"),  # Market concerns begin
        peak_drawdown_date=pd.Timestamp("2022-10-12"),  # S&P 500 bottom at 3,577
        recovery_date=pd.Timestamp("2023-01-01"),  # Stabilization begins
    ),
]


def prepare_backtest_data(
    prices: pd.Series,
    vix: pd.Series | None = None,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Prepare and align price and VIX data for backtesting.

    Aligns time series data, handles missing values, and filters to specified
    date range. Ensures data is ready for regime classification and change-point
    detection.

    Args:
        prices: Price series (e.g., S&P 500 index) with DatetimeIndex.
        vix: Optional VIX index series. If None, VIX column will be omitted.
        start_date: Start date for backtest period. If None, uses earliest available.
        end_date: End date for backtest period. If None, uses latest available.

    Returns:
        DataFrame with columns:
            - 'price': Aligned price series
            - 'vix': Aligned VIX series (if provided)
            - 'returns': Log returns computed from prices
            - 'drawdown': Drawdown from running maximum
        Indexed by date.

    Raises:
        ValueError: If prices is empty or contains insufficient data.

    Examples:
        >>> data = prepare_backtest_data(
        ...     prices=sp500_prices,
        ...     vix=vix_index,
        ...     start_date="2008-01-01",
        ...     end_date="2023-12-31"
        ... )
        >>> print(data.columns)
        Index(['price', 'vix', 'returns', 'drawdown'], dtype='object')

    Notes:
        - Forward fills up to 5 days of missing data
        - Drops any remaining NaN values with warning
        - Returns are computed as log(price_t / price_{t-1})
        - Drawdown is percentage from running maximum
    """
    # Validate input
    if len(prices) == 0:
        raise ValueError("prices series is empty")

    # Copy to avoid modifying original
    prices = prices.copy()

    # Create result DataFrame
    result = pd.DataFrame(index=prices.index)
    result['price'] = prices

    # Add VIX if provided
    if vix is not None:
        vix = vix.copy()
        # Align VIX to price index
        common_index = prices.index.intersection(vix.index)
        if len(common_index) == 0:
            logger.warning("No overlapping dates between prices and VIX, omitting VIX column")
        else:
            result = result.loc[common_index]
            result['vix'] = vix.loc[common_index]

    # Compute returns (log returns for better statistical properties)
    result['returns'] = np.log(result['price'] / result['price'].shift(1))

    # Compute drawdown from running maximum
    running_max = result['price'].expanding(min_periods=1).max()
    result['drawdown'] = (result['price'] - running_max) / running_max

    # Handle missing values
    # Forward fill up to 5 days for weekends/holidays
    n_missing_before = result.isna().sum().sum()
    if n_missing_before > 0:
        logger.debug("Forward filling up to 5 days of missing values")
        result = result.ffill(limit=5)

    # Drop any remaining NaN values (e.g., first row with returns=NaN)
    n_missing_after = result.isna().sum().sum()
    if n_missing_after > 0:
        rows_before = len(result)
        result = result.dropna()
        rows_dropped = rows_before - len(result)
        if rows_dropped > 1:  # Only warn if more than just the first row
            logger.warning(
                "Dropped %d rows with NaN values after forward fill",
                rows_dropped
            )

    # Filter to date range
    if start_date is not None:
        start_date = pd.Timestamp(start_date)
        result = result[result.index >= start_date]

    if end_date is not None:
        end_date = pd.Timestamp(end_date)
        result = result[result.index <= end_date]

    # Validate result
    if len(result) == 0:
        raise ValueError("No data remaining after filtering and alignment")

    if len(result) < 50:
        logger.warning(
            "Only %d data points available - may be insufficient for backtesting",
            len(result)
        )

    logger.info(
        "Prepared backtest data: %d days from %s to %s",
        len(result),
        result.index[0].strftime("%Y-%m-%d"),
        result.index[-1].strftime("%Y-%m-%d"),
    )

    return result


@dataclass
class Detection:
    """
    Record of a single crisis detection event.

    Attributes:
        timestamp: Date/time of detection.
        method: Detection method ('classifier', 'detector', or 'baseline').
        confidence: Confidence score (0-1), higher = more confident.
        crisis_name: Name of associated crisis (if known), or None.

    Examples:
        >>> det = Detection(
        ...     timestamp=pd.Timestamp("2020-03-01"),
        ...     method="classifier",
        ...     confidence=0.95,
        ...     crisis_name="COVID"
        ... )
    """

    timestamp: pd.Timestamp
    method: str  # 'classifier', 'detector', 'baseline'
    confidence: float
    crisis_name: str | None = None


@dataclass
class BacktestResults:
    """
    Comprehensive results from backtesting across multiple crises.

    Attributes:
        detections: List of all detection events.
        lead_times: Dictionary mapping crisis name to lead time (trading days).
            Positive = early warning, negative = late detection.
        true_positives: Dictionary mapping crisis name to detection success boolean.
        false_positives: Count of detections outside crisis windows.
        crisis_periods: List of crisis periods evaluated.

    Examples:
        >>> results = BacktestResults(
        ...     detections=[det1, det2, det3],
        ...     lead_times={"GFC": 10, "COVID": 15},
        ...     true_positives={"GFC": True, "COVID": True},
        ...     false_positives=2,
        ...     crisis_periods=KNOWN_CRISES
        ... )
    """

    detections: list[Detection] = field(default_factory=list)
    lead_times: dict[str, int] = field(default_factory=dict)
    true_positives: dict[str, bool] = field(default_factory=dict)
    false_positives: int = 0
    crisis_periods: list[CrisisPeriod] = field(default_factory=list)


class BacktestEngine:
    """
    Engine for backtesting crisis detection methods on historical data.

    Evaluates regime classifier and change-point detector performance across
    known crisis periods, computing detection lead times and false positive rates.

    Attributes:
        regime_classifier: Optional RegimeClassifier instance for regime-based detection.
        change_detector: Optional ChangePointDetector instance for topology-based detection.
        window_size: Number of data points per analysis window. Default 50.
        stride: Number of points to advance between windows. Default 5.

    Examples:
        >>> engine = BacktestEngine(
        ...     regime_classifier=clf,
        ...     change_detector=detector,
        ...     window_size=50,
        ...     stride=5
        ... )
        >>> results = engine.run_backtest(prices, features, KNOWN_CRISES)
    """

    def __init__(
        self,
        regime_classifier: RegimeClassifier | None = None,
        change_detector: ChangePointDetector | None = None,
        window_size: int = 50,
        stride: int = 5,
    ) -> None:
        """
        Initialize backtest engine.

        Args:
            regime_classifier: Fitted RegimeClassifier for regime detection.
            change_detector: Fitted ChangePointDetector for topology-based detection.
            window_size: Number of data points per window. Default 50.
            stride: Window stride (overlap). Default 5.

        Raises:
            ValueError: If both classifier and detector are None.
        """
        if regime_classifier is None and change_detector is None:
            raise ValueError("At least one of regime_classifier or change_detector must be provided")

        self.regime_classifier = regime_classifier
        self.change_detector = change_detector
        self.window_size = window_size
        self.stride = stride

        logger.info(
            "Initialized BacktestEngine: window_size=%d, stride=%d",
            window_size,
            stride,
        )

    def run_backtest(
        self,
        prices: pd.Series,
        features: pd.DataFrame | None = None,
        crisis_periods: list[CrisisPeriod] | None = None,
    ) -> BacktestResults:
        """
        Run backtest across crisis periods.

        Args:
            prices: Price series with DatetimeIndex.
            features: Optional windowed features DataFrame. Required if using regime_classifier.
                Should have 'window_start', 'window_end' columns and feature columns.
            crisis_periods: List of crisis periods to evaluate. If None, uses KNOWN_CRISES.

        Returns:
            BacktestResults containing all detections, lead times, and performance metrics.

        Raises:
            ValueError: If features is None but regime_classifier is provided.

        Examples:
            >>> results = engine.run_backtest(
            ...     prices=sp500_prices,
            ...     features=windowed_features,
            ...     crisis_periods=KNOWN_CRISES
            ... )
            >>> print(f"GFC lead time: {results.lead_times['GFC']} days")
        """
        if crisis_periods is None:
            crisis_periods = KNOWN_CRISES

        if self.regime_classifier is not None and features is None:
            raise ValueError("features required when using regime_classifier")

        results = BacktestResults(crisis_periods=crisis_periods)

        # Run regime classifier if available
        if self.regime_classifier is not None and features is not None:
            classifier_detections = self._run_classifier_backtest(features, crisis_periods)
            results.detections.extend(classifier_detections)

        # Run change detector if available
        if self.change_detector is not None:
            detector_detections = self._run_detector_backtest(prices, crisis_periods)
            results.detections.extend(detector_detections)

        # Compute lead times and true positives for each crisis
        for crisis in crisis_periods:
            detection = self._find_earliest_detection(
                results.detections,
                crisis.onset_date,
                crisis.peak_drawdown_date,
            )

            if detection is not None:
                # Compute lead time in trading days
                lead_time = compute_lead_time(
                    detection.timestamp,
                    crisis.peak_drawdown_date,
                )
                results.lead_times[crisis.name] = lead_time
                results.true_positives[crisis.name] = True

                logger.info(
                    "Crisis '%s' detected %d trading days before peak (method=%s, confidence=%.3f)",
                    crisis.name,
                    lead_time,
                    detection.method,
                    detection.confidence,
                )
            else:
                results.lead_times[crisis.name] = 0
                results.true_positives[crisis.name] = False
                logger.warning("Crisis '%s' NOT detected", crisis.name)

        # Count false positives
        results.false_positives = self._count_false_positives(
            results.detections,
            crisis_periods,
        )

        logger.info(
            "Backtest complete: %d crises, %d detections, %d false positives",
            len(crisis_periods),
            len(results.detections),
            results.false_positives,
        )

        return results

    def _run_classifier_backtest(
        self,
        features: pd.DataFrame,
        crisis_periods: list[CrisisPeriod],
    ) -> list[Detection]:
        """Run regime classifier and extract detections."""
        if self.regime_classifier is None:
            return []

        detections = []

        # Get predictions for all windows
        # Features should already be prepared with proper columns
        feature_cols = [col for col in features.columns if col not in ['window_start', 'window_end']]
        X = features[feature_cols].values

        try:
            predictions = self.regime_classifier.predict(X)
            probabilities = self.regime_classifier.predict_proba(X)[:, 1]  # Crisis probability
        except Exception as e:
            logger.error("Regime classifier prediction failed: %s", e)
            return []

        # Extract crisis predictions (label = 1)
        crisis_mask = predictions == 1

        for idx in np.where(crisis_mask)[0]:
            timestamp = pd.Timestamp(features.iloc[idx]['window_end'])
            confidence = float(probabilities[idx])

            # Associate with nearest crisis
            crisis_name = self._associate_with_crisis(timestamp, crisis_periods)

            detections.append(Detection(
                timestamp=timestamp,
                method="classifier",
                confidence=confidence,
                crisis_name=crisis_name,
            ))

        logger.debug("Classifier: %d crisis detections", len(detections))
        return detections

    def _run_detector_backtest(
        self,
        prices: pd.Series,
        crisis_periods: list[CrisisPeriod],
    ) -> list[Detection]:
        """Run change-point detector and extract detections."""
        if self.change_detector is None:
            return []

        detections = []

        # This is a placeholder - actual implementation would require:
        # 1. Computing persistence diagrams for sliding windows
        # 2. Computing bottleneck distances between consecutive windows
        # 3. Running change_detector.detect() on distances
        # This will be fully implemented once data fetchers are connected

        logger.debug("Detector: %d change-point detections", len(detections))
        return detections

    def _find_earliest_detection(
        self,
        detections: list[Detection],
        onset_date: pd.Timestamp,
        peak_drawdown_date: pd.Timestamp,
    ) -> Detection | None:
        """
        Find earliest detection within valid detection window for a crisis.

        Args:
            detections: List of all detection events.
            onset_date: Crisis onset date.
            peak_drawdown_date: Crisis peak drawdown date.

        Returns:
            Earliest detection within window, or None if no valid detection.

        Notes:
            Detection window: 10 trading days before onset to peak drawdown date.
        """
        # Detection window: 10 trading days before onset (~14 calendar days)
        window_start = onset_date - pd.Timedelta(days=14)
        window_end = peak_drawdown_date

        valid_detections = [
            d for d in detections
            if window_start <= d.timestamp <= window_end
        ]

        if len(valid_detections) == 0:
            return None

        # Return earliest detection
        return min(valid_detections, key=lambda d: d.timestamp)

    def _associate_with_crisis(
        self,
        timestamp: pd.Timestamp,
        crisis_periods: list[CrisisPeriod],
    ) -> str | None:
        """
        Associate a detection timestamp with nearest crisis period.

        Args:
            timestamp: Detection timestamp.
            crisis_periods: List of known crisis periods.

        Returns:
            Crisis name if within tolerance window, None otherwise.
        """
        tolerance_days = 30  # Calendar days

        for crisis in crisis_periods:
            window_start = crisis.onset_date - pd.Timedelta(days=tolerance_days)
            window_end = crisis.recovery_date + pd.Timedelta(days=tolerance_days)

            if window_start <= timestamp <= window_end:
                return crisis.name

        return None

    def _count_false_positives(
        self,
        detections: list[Detection],
        crisis_periods: list[CrisisPeriod],
    ) -> int:
        """
        Count detections outside crisis windows (false positives).

        Args:
            detections: List of all detection events.
            crisis_periods: List of known crisis periods.

        Returns:
            Count of false positive detections.
        """
        false_positive_count = 0
        tolerance_days = 30  # Calendar days

        for detection in detections:
            is_near_crisis = False

            for crisis in crisis_periods:
                window_start = crisis.onset_date - pd.Timedelta(days=tolerance_days)
                window_end = crisis.recovery_date + pd.Timedelta(days=tolerance_days)

                if window_start <= detection.timestamp <= window_end:
                    is_near_crisis = True
                    break

            if not is_near_crisis:
                false_positive_count += 1

        return false_positive_count


def compute_lead_time(
    detection_date: pd.Timestamp,
    peak_drawdown_date: pd.Timestamp,
) -> int:
    """
    Compute lead time in trading days from detection to peak drawdown.

    Args:
        detection_date: Date of crisis detection signal.
        peak_drawdown_date: Date of maximum drawdown (crisis peak).

    Returns:
        Lead time in trading days. Positive = early warning, negative = late.

    Examples:
        >>> detection = pd.Timestamp("2020-03-01")
        >>> peak = pd.Timestamp("2020-03-23")
        >>> lead_time = compute_lead_time(detection, peak)
        >>> print(f"Lead time: {lead_time} trading days")

    Notes:
        Uses np.busday_count for accurate trading day calculation.
        Excludes weekends but includes holidays for simplicity.
    """
    # Convert to numpy datetime64 for busday_count
    detection_np = np.datetime64(detection_date.date())
    peak_np = np.datetime64(peak_drawdown_date.date())

    # Compute business days between dates
    lead_time = int(np.busday_count(detection_np, peak_np))

    return lead_time


def is_valid_detection(
    detection_date: pd.Timestamp,
    crisis_period: CrisisPeriod,
    tolerance_days: int = 10,
) -> bool:
    """
    Check if detection is within valid window for a crisis.

    Args:
        detection_date: Date of detection signal.
        crisis_period: Crisis period to validate against.
        tolerance_days: Trading days tolerance before onset. Default 10.

    Returns:
        True if detection is within valid window, False otherwise.

    Examples:
        >>> gfc = KNOWN_CRISES[0]
        >>> detection = pd.Timestamp("2008-09-10")
        >>> is_valid = is_valid_detection(detection, gfc, tolerance_days=10)

    Notes:
        Valid window: tolerance_days before onset to peak drawdown date.
        Approximate trading days as 1.4 * calendar days for tolerance.
    """
    # Convert tolerance to approximate calendar days
    tolerance_calendar = tolerance_days * 14 // 10  # ~1.4x for weekends

    window_start = crisis_period.onset_date - pd.Timedelta(days=tolerance_calendar)
    window_end = crisis_period.peak_drawdown_date

    return window_start <= detection_date <= window_end


class VolatilityBaseline:
    """
    Baseline crisis detection using rolling realized volatility.

    Simple benchmark method that detects crises when realized volatility
    exceeds a threshold percentile. Provides comparison baseline for
    TDA-based methods.

    Attributes:
        window_size: Rolling window for volatility calculation. Default 20.
        threshold_percentile: Percentile for detection threshold. Default 95.

    Examples:
        >>> baseline = VolatilityBaseline(window_size=20, threshold_percentile=95)
        >>> detections = baseline.detect(prices)
    """

    def __init__(
        self,
        window_size: int = 20,
        threshold_percentile: float = 95.0,
    ) -> None:
        """
        Initialize volatility baseline detector.

        Args:
            window_size: Rolling window for volatility computation. Default 20 days.
            threshold_percentile: Percentile for detection threshold (0-100). Default 95.

        Raises:
            ValueError: If window_size < 2 or threshold_percentile not in (0, 100].
        """
        if window_size < 2:
            raise ValueError(f"window_size must be >= 2, got {window_size}")

        if not 0 < threshold_percentile <= 100:
            raise ValueError(
                f"threshold_percentile must be in (0, 100], got {threshold_percentile}"
            )

        self.window_size = window_size
        self.threshold_percentile = threshold_percentile

        logger.info(
            "Initialized VolatilityBaseline: window_size=%d, threshold=%.1f%%",
            window_size,
            threshold_percentile,
        )

    def detect(
        self,
        prices: pd.Series,
        crisis_periods: list[CrisisPeriod] | None = None,
    ) -> list[Detection]:
        """
        Detect crisis periods using rolling volatility threshold.

        Args:
            prices: Price series with DatetimeIndex.
            crisis_periods: Optional list of crisis periods for association.

        Returns:
            List of Detection objects where volatility exceeds threshold.

        Examples:
            >>> baseline = VolatilityBaseline(window_size=20)
            >>> detections = baseline.detect(sp500_prices, crisis_periods=KNOWN_CRISES)
            >>> print(f"Detected {len(detections)} high-volatility events")

        Notes:
            - Realized volatility computed as std of log returns
            - Detections at local volatility peaks (to avoid consecutive signals)
            - Returns empty list if insufficient data for volatility calculation
        """
        # Compute log returns
        returns = np.log(prices / prices.shift(1)).dropna()

        if len(returns) < self.window_size:
            logger.warning(
                "Insufficient data for volatility baseline: %d < %d",
                len(returns),
                self.window_size,
            )
            return []

        # Compute rolling realized volatility (annualized)
        volatility = returns.rolling(window=self.window_size).std() * np.sqrt(252)

        # Compute threshold from entire series
        threshold = np.percentile(volatility.dropna(), self.threshold_percentile)

        # Find volatility spikes exceeding threshold
        high_vol_mask = volatility > threshold

        # Extract local peaks to avoid consecutive detections
        detections = []
        in_spike = False
        spike_start_idx = None
        spike_max_vol = -np.inf
        spike_max_idx = None

        for i, (date, is_high) in enumerate(high_vol_mask.items()):
            if pd.isna(is_high):
                continue

            if is_high and not in_spike:
                # Start of new spike
                in_spike = True
                spike_start_idx = i
                spike_max_vol = volatility.iloc[i]
                spike_max_idx = i

            elif is_high and in_spike:
                # Continue spike, track maximum
                if volatility.iloc[i] > spike_max_vol:
                    spike_max_vol = volatility.iloc[i]
                    spike_max_idx = i

            elif not is_high and in_spike:
                # End of spike, record detection at peak
                peak_date = volatility.index[spike_max_idx]
                confidence = min((spike_max_vol - threshold) / threshold, 1.0)

                # Associate with crisis if provided
                crisis_name = None
                if crisis_periods is not None:
                    for crisis in crisis_periods:
                        # Within 30 days of crisis window
                        window_start = crisis.onset_date - pd.Timedelta(days=30)
                        window_end = crisis.recovery_date + pd.Timedelta(days=30)
                        if window_start <= peak_date <= window_end:
                            crisis_name = crisis.name
                            break

                detections.append(Detection(
                    timestamp=peak_date,
                    method="baseline",
                    confidence=confidence,
                    crisis_name=crisis_name,
                ))

                # Reset spike tracking
                in_spike = False
                spike_start_idx = None
                spike_max_vol = -np.inf
                spike_max_idx = None

        # Handle case where spike extends to end of series
        if in_spike and spike_max_idx is not None:
            peak_date = volatility.index[spike_max_idx]
            confidence = min((spike_max_vol - threshold) / threshold, 1.0)

            crisis_name = None
            if crisis_periods is not None:
                for crisis in crisis_periods:
                    window_start = crisis.onset_date - pd.Timedelta(days=30)
                    window_end = crisis.recovery_date + pd.Timedelta(days=30)
                    if window_start <= peak_date <= window_end:
                        crisis_name = crisis.name
                        break

            detections.append(Detection(
                timestamp=peak_date,
                method="baseline",
                confidence=confidence,
                crisis_name=crisis_name,
            ))

        logger.info(
            "VolatilityBaseline detected %d events (threshold=%.4f)",
            len(detections),
            threshold,
        )

        return detections


def generate_backtest_report(
    results: BacktestResults,
    baseline_results: BacktestResults | None = None,
) -> dict[str, Any]:
    """
    Generate comprehensive backtest performance report.

    Computes per-crisis and aggregate metrics, with optional comparison
    to baseline method.

    Args:
        results: BacktestResults from TDA-based methods (classifier/detector).
        baseline_results: Optional BacktestResults from baseline method for comparison.

    Returns:
        Dictionary containing:
            - per_crisis_metrics: Dict[crisis_name, metrics_dict]
            - aggregate_metrics: Overall performance metrics
            - baseline_comparison: Comparison metrics (if baseline provided)
            - summary: Text summary of key findings

    Examples:
        >>> report = generate_backtest_report(tda_results, baseline_results)
        >>> print(report['summary'])
        >>> print(f"Mean lead time: {report['aggregate_metrics']['mean_lead_time']} days")

    Notes:
        - Lead time improvement: positive = TDA better than baseline
        - Precision = TP / (TP + FP)
        - Recall = TP / (TP + FN)
        - F1 = 2 * (Precision * Recall) / (Precision + Recall)
    """
    report: dict[str, Any] = {
        "per_crisis_metrics": {},
        "aggregate_metrics": {},
    }

    # Per-crisis metrics
    for crisis in results.crisis_periods:
        crisis_name = crisis.name

        detected = results.true_positives.get(crisis_name, False)
        lead_time = results.lead_times.get(crisis_name, 0)

        crisis_metrics = {
            "detected": detected,
            "lead_time_days": lead_time,
            "onset_to_peak_days": crisis.onset_to_peak_days,
            "detection_accuracy": detected,
        }

        # Add baseline comparison if available
        if baseline_results is not None:
            baseline_detected = baseline_results.true_positives.get(crisis_name, False)
            baseline_lead_time = baseline_results.lead_times.get(crisis_name, 0)

            crisis_metrics["baseline_detected"] = baseline_detected
            crisis_metrics["baseline_lead_time_days"] = baseline_lead_time
            crisis_metrics["lead_time_improvement"] = lead_time - baseline_lead_time

        report["per_crisis_metrics"][crisis_name] = crisis_metrics

    # Aggregate metrics
    n_crises = len(results.crisis_periods)
    n_detected = sum(results.true_positives.values())
    n_missed = n_crises - n_detected

    detected_lead_times = [
        lt for crisis_name, lt in results.lead_times.items()
        if results.true_positives.get(crisis_name, False) and lt > 0
    ]

    mean_lead_time = float(np.mean(detected_lead_times)) if detected_lead_times else 0.0
    median_lead_time = float(np.median(detected_lead_times)) if detected_lead_times else 0.0

    # Precision, Recall, F1
    true_positives = n_detected
    false_positives = results.false_positives
    false_negatives = n_missed

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    report["aggregate_metrics"] = {
        "n_crises": n_crises,
        "n_detected": n_detected,
        "n_missed": n_missed,
        "detection_rate": n_detected / n_crises if n_crises > 0 else 0.0,
        "mean_lead_time": mean_lead_time,
        "median_lead_time": median_lead_time,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "false_positives": false_positives,
    }

    # Baseline comparison
    if baseline_results is not None:
        baseline_n_detected = sum(baseline_results.true_positives.values())
        baseline_detected_lead_times = [
            lt for crisis_name, lt in baseline_results.lead_times.items()
            if baseline_results.true_positives.get(crisis_name, False) and lt > 0
        ]

        baseline_mean_lead_time = float(np.mean(baseline_detected_lead_times)) if baseline_detected_lead_times else 0.0

        baseline_fp = baseline_results.false_positives
        baseline_precision = baseline_n_detected / (baseline_n_detected + baseline_fp) if (baseline_n_detected + baseline_fp) > 0 else 0.0
        baseline_recall = baseline_n_detected / n_crises if n_crises > 0 else 0.0
        baseline_f1 = 2 * (baseline_precision * baseline_recall) / (baseline_precision + baseline_recall) if (baseline_precision + baseline_recall) > 0 else 0.0

        report["baseline_comparison"] = {
            "tda_mean_lead_time": mean_lead_time,
            "baseline_mean_lead_time": baseline_mean_lead_time,
            "lead_time_improvement": mean_lead_time - baseline_mean_lead_time,
            "tda_f1_score": f1_score,
            "baseline_f1_score": baseline_f1,
            "f1_improvement": f1_score - baseline_f1,
            "tda_precision": precision,
            "baseline_precision": baseline_precision,
            "tda_recall": recall,
            "baseline_recall": baseline_recall,
        }

    # Generate text summary
    summary_lines = [
        f"Backtest Results Summary:",
        f"  Crises evaluated: {n_crises}",
        f"  Detected: {n_detected}/{n_crises} ({n_detected/n_crises*100:.1f}%)",
        f"  Mean lead time: {mean_lead_time:.1f} days",
        f"  Median lead time: {median_lead_time:.1f} days",
        f"  Precision: {precision:.3f}",
        f"  Recall: {recall:.3f}",
        f"  F1 Score: {f1_score:.3f}",
        f"  False positives: {false_positives}",
    ]

    if baseline_results is not None:
        improvement = report["baseline_comparison"]["lead_time_improvement"]
        f1_improvement = report["baseline_comparison"]["f1_improvement"]
        summary_lines.extend([
            f"",
            f"Comparison to Baseline:",
            f"  Lead time improvement: {improvement:+.1f} days",
            f"  F1 improvement: {f1_improvement:+.3f}",
        ])

    report["summary"] = "\n".join(summary_lines)

    logger.info("Generated backtest report: %d crises, %d detected", n_crises, n_detected)

    return report
