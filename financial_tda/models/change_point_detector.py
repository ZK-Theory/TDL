"""
Change-point detection using bottleneck distance between persistence diagrams.

This module provides statistical change-point detection for topological time series,
with threshold calibration on historical "normal" periods and significance testing
for anomaly detection. Designed to detect regime changes in financial markets by
identifying significant deviations in topological structure.

References:
    Gidea, M., & Katz, Y. (2018). Topological data analysis of financial
        time series: Landscapes of crashes. Physica A, 491, 820-834.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy import stats

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class NormalPeriodCalibrator:
    """
    Compute baseline statistics from "normal" market periods for threshold calibration.

    Establishes expected distribution of bottleneck distances during stable market
    conditions. These baseline statistics enable statistical significance testing
    for anomaly detection during crisis periods.

    Normal periods are defined as:
        - Pre-GFC: 2004-01-01 to 2007-06-30
        - Post-recovery: 2013-01-01 to 2019-12-31
          (excluding 2015-08-01 to 2015-09-30 China devaluation)

    Attributes:
        mean_: Mean bottleneck distance during normal periods.
        std_: Standard deviation of distances during normal periods.
        percentiles_: Dictionary of percentile values (50, 75, 90, 95, 99).
        n_samples_: Number of distance samples used for calibration.
        is_fitted_: Whether calibrator has been fitted to data.

    Examples:
        >>> calibrator = NormalPeriodCalibrator()
        >>> # distances from normal periods only
        >>> normal_distances = distances[normal_period_mask]
        >>> calibrator.fit(normal_distances)
        >>> threshold = calibrator.get_threshold(percentile=95)
        >>> is_anomaly = calibrator.is_anomaly(new_distance)
    """

    def __init__(self) -> None:
        """Initialize an unfitted calibrator."""
        self.mean_: float = 0.0
        self.std_: float = 0.0
        self.percentiles_: dict[int, float] = {}
        self.n_samples_: int = 0
        self.is_fitted_: bool = False
        self._distances_cache: NDArray[np.floating] | None = None

    def fit(self, distances: NDArray[np.floating]) -> None:
        """
        Compute baseline statistics from normal period distances.

        Args:
            distances: Array of bottleneck distances from normal market periods.
                Should exclude crisis periods and transitional periods.

        Raises:
            ValueError: If distances is empty or contains non-finite values.

        Notes:
            - Removes NaN and infinite values automatically
            - Requires at least 10 samples for stable statistics
            - Logs warning if standard deviation is unusually low
        """
        distances = np.asarray(distances, dtype=np.float64).ravel()

        # Filter out non-finite values
        finite_mask = np.isfinite(distances)
        distances = distances[finite_mask]

        if len(distances) == 0:
            raise ValueError("distances array is empty or contains only non-finite values")

        if len(distances) < 10:
            logger.warning(
                "Only %d samples for calibration, statistics may be unstable",
                len(distances)
            )

        # Compute statistics
        self.mean_ = float(np.mean(distances))
        self.std_ = float(np.std(distances, ddof=1))
        self.n_samples_ = len(distances)

        # Compute key percentiles
        percentile_levels = [50, 75, 90, 95, 99]
        self.percentiles_ = {
            p: float(np.percentile(distances, p)) for p in percentile_levels
        }

        # Cache distances for bootstrap confidence intervals
        self._distances_cache = distances.copy()

        self.is_fitted_ = True

        # Validation checks
        if self.std_ < 1e-10:
            logger.warning(
                "Standard deviation very small (%.2e), may indicate constant distances",
                self.std_
            )

        logger.info(
            "Calibrated on %d samples: mean=%.4f, std=%.4f, 95th=%.4f",
            self.n_samples_,
            self.mean_,
            self.std_,
            self.percentiles_[95],
        )

    def get_threshold(self, percentile: float = 95.0) -> float:
        """
        Get threshold for anomaly detection at specified percentile.

        Args:
            percentile: Percentile level for threshold (0-100). Default 95.
                Higher values = more conservative (fewer false positives).
                Lower values = more sensitive (higher recall).

        Returns:
            Threshold value for anomaly detection.

        Raises:
            ValueError: If calibrator not fitted or percentile out of range.

        Examples:
            >>> threshold_95 = calibrator.get_threshold(95)  # Conservative
            >>> threshold_90 = calibrator.get_threshold(90)  # More sensitive
        """
        if not self.is_fitted_:
            raise ValueError("Calibrator must be fitted before getting threshold")

        if not 0 < percentile <= 100:
            raise ValueError(f"percentile must be in (0, 100], got {percentile}")

        # For common percentiles, use precomputed values
        percentile_int = int(percentile)
        if percentile == percentile_int and percentile_int in self.percentiles_:
            return self.percentiles_[percentile_int]

        # For arbitrary percentile, use normal approximation
        # threshold = mean + z * std, where z is z-score for percentile
        z_score = stats.norm.ppf(percentile / 100)
        threshold = self.mean_ + z_score * self.std_

        return float(threshold)

    def is_anomaly(self, distance: float) -> bool:
        """
        Test if a distance value is anomalous (exceeds 95th percentile threshold).

        Args:
            distance: Bottleneck distance value to test.

        Returns:
            True if distance exceeds 95th percentile threshold, False otherwise.

        Raises:
            ValueError: If calibrator not fitted.

        Examples:
            >>> if calibrator.is_anomaly(distance):
            ...     print("Anomaly detected!")
        """
        if not self.is_fitted_:
            raise ValueError("Calibrator must be fitted before anomaly detection")

        threshold = self.get_threshold(percentile=95.0)
        return float(distance) > threshold

    def compute_threshold_confidence_interval(
        self,
        percentile: float = 95.0,
        confidence_level: float = 0.95,
        n_bootstrap: int = 1000,
        random_state: int | None = None,
    ) -> tuple[float, float, float]:
        """
        Compute confidence interval for threshold using bootstrap resampling.

        Provides uncertainty quantification for the calibrated threshold,
        useful for understanding threshold stability and robustness.

        Args:
            percentile: Percentile level for threshold. Default 95.
            confidence_level: Confidence level for interval (0-1). Default 0.95 (95% CI).
            n_bootstrap: Number of bootstrap samples. Default 1000.
            random_state: Random seed for reproducibility.

        Returns:
            Tuple of (lower_bound, threshold, upper_bound) where:
                - lower_bound: Lower confidence interval bound
                - threshold: Point estimate of threshold
                - upper_bound: Upper confidence interval bound

        Raises:
            ValueError: If calibrator not fitted.

        Examples:
            >>> lower, threshold, upper = calibrator.compute_threshold_confidence_interval()
            >>> print(f"Threshold: {threshold:.4f} [{lower:.4f}, {upper:.4f}]")

        Notes:
            - Uses percentile bootstrap method
            - Wider intervals indicate less stable thresholds
            - Requires cached distances from fit() call
        """
        if not self.is_fitted_:
            raise ValueError("Calibrator must be fitted before computing confidence intervals")

        if self._distances_cache is None:
            raise ValueError("No cached distances available for bootstrap")

        if not 0 < confidence_level < 1:
            raise ValueError(f"confidence_level must be in (0, 1), got {confidence_level}")

        # Set random seed for reproducibility
        rng = np.random.default_rng(random_state)

        # Point estimate
        threshold = self.get_threshold(percentile)

        # Bootstrap resampling
        bootstrap_thresholds = []
        n_samples = len(self._distances_cache)

        for _ in range(n_bootstrap):
            # Resample with replacement
            bootstrap_sample = rng.choice(
                self._distances_cache, size=n_samples, replace=True
            )
            # Compute threshold for bootstrap sample
            bootstrap_threshold = float(np.percentile(bootstrap_sample, percentile))
            bootstrap_thresholds.append(bootstrap_threshold)

        # Compute confidence interval
        alpha = 1 - confidence_level
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100

        lower_bound = float(np.percentile(bootstrap_thresholds, lower_percentile))
        upper_bound = float(np.percentile(bootstrap_thresholds, upper_percentile))

        logger.debug(
            "Bootstrap CI for threshold (%.0f%% confidence): [%.4f, %.4f, %.4f]",
            confidence_level * 100,
            lower_bound,
            threshold,
            upper_bound,
        )

        return (lower_bound, threshold, upper_bound)

    def get_threshold_statistics(
        self, percentile: float = 95.0
    ) -> dict[str, float]:
        """
        Get comprehensive statistics for threshold at specified percentile.

        Args:
            percentile: Percentile level for threshold. Default 95.

        Returns:
            Dictionary containing:
                - threshold: Threshold value
                - z_score: Z-score corresponding to threshold
                - relative_to_mean: Threshold as multiple of mean
                - relative_to_std: Threshold in standard deviations

        Raises:
            ValueError: If calibrator not fitted.

        Examples:
            >>> stats = calibrator.get_threshold_statistics(95)
            >>> print(f"Threshold is {stats['relative_to_std']:.1f} std above mean")
        """
        if not self.is_fitted_:
            raise ValueError("Calibrator must be fitted before getting statistics")

        threshold = self.get_threshold(percentile)
        z_score = (threshold - self.mean_) / self.std_ if self.std_ > 0 else 0.0

        return {
            "threshold": threshold,
            "z_score": z_score,
            "relative_to_mean": threshold / self.mean_ if self.mean_ > 0 else 0.0,
            "relative_to_std": z_score,
        }

    def save_calibration(self, filepath: str | Path) -> None:
        """
        Save calibrator state to JSON file for persistence.

        Args:
            filepath: Path to save calibration data (will create .json file).

        Raises:
            ValueError: If calibrator not fitted.
            IOError: If file cannot be written.

        Examples:
            >>> calibrator.fit(normal_distances)
            >>> calibrator.save_calibration("models/calibration.json")
            >>> # Later...
            >>> new_calibrator = NormalPeriodCalibrator()
            >>> new_calibrator.load_calibration("models/calibration.json")
        """
        if not self.is_fitted_:
            raise ValueError("Cannot save unfitted calibrator")

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Prepare data for serialization
        data = {
            "mean": self.mean_,
            "std": self.std_,
            "percentiles": self.percentiles_,
            "n_samples": self.n_samples_,
            # Don't save cached distances (potentially large)
        }

        # Write to file
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info("Saved calibration to %s", filepath)

    def load_calibration(self, filepath: str | Path) -> None:
        """
        Load calibrator state from JSON file.

        Args:
            filepath: Path to calibration JSON file.

        Raises:
            FileNotFoundError: If calibration file doesn't exist.
            ValueError: If file format is invalid.

        Examples:
            >>> calibrator = NormalPeriodCalibrator()
            >>> calibrator.load_calibration("models/calibration.json")
            >>> threshold = calibrator.get_threshold(95)
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Calibration file not found: {filepath}")

        # Load from file
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Validate required fields
        required_fields = ["mean", "std", "percentiles", "n_samples"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise ValueError(f"Invalid calibration file, missing fields: {missing}")

        # Restore state
        self.mean_ = float(data["mean"])
        self.std_ = float(data["std"])
        self.percentiles_ = {int(k): float(v) for k, v in data["percentiles"].items()}
        self.n_samples_ = int(data["n_samples"])
        self.is_fitted_ = True
        self._distances_cache = None  # Cache not saved

        logger.info("Loaded calibration from %s (n_samples=%d)", filepath, self.n_samples_)


class ChangePointDetector:
    """
    Detect change points in topological time series with statistical significance.

    Uses calibrated threshold from normal periods to identify statistically
    significant deviations in bottleneck distances between persistence diagrams.
    Requires consecutive anomalies to reduce false positives.

    Attributes:
        calibrator: NormalPeriodCalibrator instance with fitted statistics.
        min_consecutive: Minimum consecutive anomalies required for detection.

    Examples:
        >>> calibrator = NormalPeriodCalibrator()
        >>> calibrator.fit(normal_distances)
        >>> detector = ChangePointDetector(calibrator, min_consecutive=2)
        >>> changes = detector.detect(distances, timestamps)
        >>> print(f"Detected {len(changes)} change points")
    """

    def __init__(
        self,
        calibrator: NormalPeriodCalibrator,
        min_consecutive: int = 2,
    ) -> None:
        """
        Initialize change point detector.

        Args:
            calibrator: Fitted NormalPeriodCalibrator with baseline statistics.
            min_consecutive: Minimum consecutive anomalies required for detection.
                Default 2 reduces false positives from isolated spikes.

        Raises:
            ValueError: If calibrator not fitted or min_consecutive < 1.
        """
        if not calibrator.is_fitted_:
            raise ValueError("Calibrator must be fitted before creating detector")

        if min_consecutive < 1:
            raise ValueError(f"min_consecutive must be >= 1, got {min_consecutive}")

        self.calibrator = calibrator
        self.min_consecutive = min_consecutive

        logger.info(
            "Initialized ChangePointDetector with min_consecutive=%d",
            min_consecutive
        )

    def detect(
        self,
        distances: NDArray[np.floating],
        timestamps: pd.DatetimeIndex,
    ) -> pd.DataFrame:
        """
        Detect change points with statistical significance testing.

        Args:
            distances: Array of bottleneck distances between consecutive windows.
            timestamps: DatetimeIndex corresponding to distance measurements.
                Must have same length as distances.

        Returns:
            DataFrame with detected change points, containing columns:
                - timestamp: Detection time
                - distance: Bottleneck distance value
                - z_score: Standardized deviation from normal baseline
                - p_value: Statistical significance (one-tailed test)
                - confidence: 1 - p_value

        Raises:
            ValueError: If timestamps and distances have different lengths.

        Examples:
            >>> changes = detector.detect(distances, timestamps)
            >>> # Filter high-confidence detections
            >>> high_conf = changes[changes['confidence'] > 0.99]

        Notes:
            - P-values assume normal distribution of distances
            - Lower p-value = more statistically significant
            - Confidence > 0.95 corresponds to p-value < 0.05
            - Only consecutive anomalies reported (per min_consecutive)
        """
        distances = np.asarray(distances, dtype=np.float64).ravel()
        timestamps = pd.DatetimeIndex(timestamps)

        if len(distances) != len(timestamps):
            raise ValueError(
                f"distances and timestamps must have same length, "
                f"got {len(distances)} and {len(timestamps)}"
            )

        if len(distances) == 0:
            return pd.DataFrame(
                columns=['timestamp', 'distance', 'z_score', 'p_value', 'confidence']
            )

        # Compute z-scores and p-values for all distances
        z_scores = (distances - self.calibrator.mean_) / self.calibrator.std_
        # One-tailed test: P(Z > z) = 1 - CDF(z)
        p_values = stats.norm.sf(z_scores)
        confidences = 1.0 - p_values

        # Identify anomalies exceeding threshold
        threshold = self.calibrator.get_threshold(percentile=95.0)
        is_anomaly = distances > threshold

        # Find consecutive anomaly runs
        change_points = []
        i = 0
        while i < len(distances):
            if is_anomaly[i]:
                # Start of potential consecutive run
                run_start = i
                run_end = i

                # Extend run while consecutive anomalies
                while run_end + 1 < len(distances) and is_anomaly[run_end + 1]:
                    run_end += 1

                # Check if run meets minimum consecutive requirement
                run_length = run_end - run_start + 1
                if run_length >= self.min_consecutive:
                    # Record first detection in run (earliest warning)
                    change_points.append({
                        'timestamp': timestamps[run_start],
                        'distance': distances[run_start],
                        'z_score': z_scores[run_start],
                        'p_value': p_values[run_start],
                        'confidence': confidences[run_start],
                    })

                # Move past this run
                i = run_end + 1
            else:
                i += 1

        result_df = pd.DataFrame(change_points)

        logger.info(
            "Detected %d change points (min_consecutive=%d)",
            len(result_df),
            self.min_consecutive
        )

        return result_df

    def detect_with_lookahead(
        self,
        distances: NDArray[np.floating],
        timestamps: pd.DatetimeIndex,
        lookahead_days: int = 5,
    ) -> pd.DataFrame:
        """
        Detect change points with lookahead buffer for early warning signals.

        Similar to detect(), but reports change points only if the anomaly
        persists for a specified lookahead period. Useful for reducing
        false alarms and providing lead time before crisis events.

        Args:
            distances: Array of bottleneck distances.
            timestamps: DatetimeIndex corresponding to distances.
            lookahead_days: Number of days to look ahead for confirmation.
                Default 5 days provides early warning while filtering noise.

        Returns:
            DataFrame with same structure as detect(), but only includes
            change points confirmed by subsequent anomalies within lookahead.

        Examples:
            >>> # Detect with 5-day confirmation window
            >>> early_warnings = detector.detect_with_lookahead(
            ...     distances, timestamps, lookahead_days=5
            ... )

        Notes:
            - Lookahead reduces false positives but may miss rapid transitions
            - Appropriate lookahead depends on data frequency and use case
            - For daily data, 5-10 days is typical
        """
        # Get standard detections
        detections = self.detect(distances, timestamps)

        if len(detections) == 0:
            return detections

        # Filter detections with lookahead confirmation
        confirmed = []

        for _, detection in detections.iterrows():
            detection_time = detection['timestamp']

            # Find lookahead window
            lookahead_end = detection_time + pd.Timedelta(days=lookahead_days)
            lookahead_mask = (timestamps >= detection_time) & (timestamps <= lookahead_end)

            # Check if anomalies persist in lookahead window
            lookahead_distances = distances[lookahead_mask]
            threshold = self.calibrator.get_threshold(percentile=95.0)
            anomaly_count = np.sum(lookahead_distances > threshold)

            # Confirm if at least 50% of lookahead period has anomalies
            lookahead_length = len(lookahead_distances)
            if lookahead_length > 0 and anomaly_count >= lookahead_length * 0.5:
                confirmed.append(detection)

        result_df = pd.DataFrame(confirmed)

        logger.info(
            "Detected %d change points with lookahead=%d days (filtered from %d)",
            len(result_df),
            lookahead_days,
            len(detections)
        )

        return result_df

    def compute_detection_power(
        self,
        distances: NDArray[np.floating],
        true_change_points: list[int],
        tolerance: int = 3,
    ) -> dict[str, float]:
        """
        Compute statistical power metrics for change-point detection.

        Evaluates detector performance by comparing detected change points
        against known ground truth change points.

        Args:
            distances: Array of bottleneck distances.
            true_change_points: List of indices where true change points occur.
            tolerance: Number of indices within which detection is considered correct.
                Default 3 (±3 positions).

        Returns:
            Dictionary containing:
                - true_positive_rate: Proportion of true changes detected (recall)
                - false_positive_rate: Proportion of detections that are false alarms
                - precision: Proportion of detections that are true positives
                - f1_score: Harmonic mean of precision and recall

        Examples:
            >>> # Known change points at indices [50, 100, 150]
            >>> power = detector.compute_detection_power(distances, [50, 100, 150])
            >>> print(f"Detection recall: {power['true_positive_rate']:.2%}")

        Notes:
            - Requires known ground truth for validation
            - Useful for synthetic data experiments
            - tolerance parameter accounts for temporal uncertainty
        """
        timestamps = pd.date_range('2000-01-01', periods=len(distances), freq='D')
        detections = self.detect(distances, timestamps)
        detected_indices = [
            np.where(timestamps == det_time)[0][0]
            for det_time in detections['timestamp']
        ]

        # Compute true positives: detections near true change points
        true_positives = 0
        for true_idx in true_change_points:
            if any(abs(det_idx - true_idx) <= tolerance for det_idx in detected_indices):
                true_positives += 1

        # Compute false positives: detections not near any true change point
        false_positives = 0
        for det_idx in detected_indices:
            if not any(abs(det_idx - true_idx) <= tolerance for true_idx in true_change_points):
                false_positives += 1

        # Compute metrics
        n_true_changes = len(true_change_points)
        n_detections = len(detected_indices)

        true_positive_rate = true_positives / n_true_changes if n_true_changes > 0 else 0.0
        false_positive_rate = false_positives / n_detections if n_detections > 0 else 0.0
        precision = true_positives / n_detections if n_detections > 0 else 0.0
        recall = true_positive_rate

        # F1 score
        if precision + recall > 0:
            f1 = 2 * (precision * recall) / (precision + recall)
        else:
            f1 = 0.0

        return {
            "true_positive_rate": true_positive_rate,
            "false_positive_rate": false_positive_rate,
            "precision": precision,
            "f1_score": f1,
        }

    def validate_normality_assumption(
        self,
        distances: NDArray[np.floating],
        alpha: float = 0.05,
    ) -> dict[str, float | bool]:
        """
        Validate normality assumption for distance distribution using statistical tests.

        Tests whether the calibration distances follow a normal distribution,
        which is assumed for z-score and p-value calculations.

        Args:
            distances: Array of distances to test (typically calibration data).
            alpha: Significance level for normality tests. Default 0.05.

        Returns:
            Dictionary containing:
                - shapiro_statistic: Shapiro-Wilk test statistic
                - shapiro_pvalue: Shapiro-Wilk p-value
                - is_normal_shapiro: Whether data passes Shapiro test (p > alpha)
                - ks_statistic: Kolmogorov-Smirnov test statistic
                - ks_pvalue: KS test p-value
                - is_normal_ks: Whether data passes KS test (p > alpha)
                - skewness: Distribution skewness
                - kurtosis: Distribution excess kurtosis

        Examples:
            >>> validation = detector.validate_normality_assumption(normal_distances)
            >>> if not validation['is_normal_shapiro']:
            ...     print("Warning: Normality assumption violated")

        Notes:
            - Shapiro-Wilk test: Most powerful for small samples (n < 2000)
            - KS test: Better for large samples
            - Non-normal distributions may require non-parametric alternatives
            - Skewness near 0 and kurtosis near 0 indicate normality
        """
        distances = np.asarray(distances, dtype=np.float64).ravel()

        # Remove non-finite values
        finite_mask = np.isfinite(distances)
        distances = distances[finite_mask]

        if len(distances) < 3:
            raise ValueError("Need at least 3 samples for normality tests")

        # Shapiro-Wilk test (best for n < 5000)
        shapiro_stat, shapiro_pval = stats.shapiro(distances)

        # Kolmogorov-Smirnov test against normal distribution
        # Standardize data first
        standardized = (distances - np.mean(distances)) / np.std(distances, ddof=1)
        ks_stat, ks_pval = stats.kstest(standardized, 'norm')

        # Compute moments
        skewness = float(stats.skew(distances))
        kurtosis = float(stats.kurtosis(distances))

        results = {
            "shapiro_statistic": float(shapiro_stat),
            "shapiro_pvalue": float(shapiro_pval),
            "is_normal_shapiro": shapiro_pval > alpha,
            "ks_statistic": float(ks_stat),
            "ks_pvalue": float(ks_pval),
            "is_normal_ks": ks_pval > alpha,
            "skewness": skewness,
            "kurtosis": kurtosis,
        }

        if not results["is_normal_shapiro"] or not results["is_normal_ks"]:
            logger.warning(
                "Normality assumption may be violated (Shapiro p=%.4f, KS p=%.4f)",
                shapiro_pval,
                ks_pval,
            )

        return results


def validate_on_crisis_dates(
    detector: ChangePointDetector,
    distances: NDArray[np.floating],
    timestamps: pd.DatetimeIndex,
    crisis_dates: dict[str, str] | None = None,
) -> dict[str, dict[str, float | bool | str | None]]:
    """
    Validate change-point detector against known crisis onset dates.

    Measures detector's ability to provide early warning signals before major
    market crises. Computes lead time (days before crisis) and detection accuracy
    (true positive within tolerance window).

    Args:
        detector: Fitted ChangePointDetector instance.
        distances: Array of bottleneck distances.
        timestamps: DatetimeIndex corresponding to distances.
        crisis_dates: Dictionary mapping crisis names to onset dates (YYYY-MM-DD format).
            If None, uses default crisis dates:
            - Lehman: 2008-09-15
            - China devaluation: 2015-08-11
            - COVID: 2020-02-20
            - Rate hike: 2022-01-03

    Returns:
        Dictionary mapping crisis names to validation metrics:
            - detected: Whether crisis was detected (±10 trading days)
            - lead_time_days: Days before crisis onset (negative = late)
            - detection_date: Date of earliest detection before crisis
            - crisis_date: Official crisis onset date
            - distance_at_crisis: Bottleneck distance value at detection

    Examples:
        >>> results = validate_on_crisis_dates(detector, distances, timestamps)
        >>> for crisis, metrics in results.items():
        ...     if metrics['detected']:
        ...         print(f"{crisis}: {metrics['lead_time_days']} days lead time")

    Notes:
        - Detection window: ±10 trading days from crisis onset
        - Lead time is positive for early detection, negative for late
        - Uses detector's standard detect() method with min_consecutive parameter
    """
    if crisis_dates is None:
        # Default known crisis onset dates
        crisis_dates = {
            "Lehman_Collapse": "2008-09-15",
            "China_Devaluation": "2015-08-11",
            "COVID_Crash": "2020-02-20",
            "Rate_Hike_Crash": "2022-01-03",
        }

    # Get all detections
    detections = detector.detect(distances, timestamps)

    # Handle case with no detections
    if len(detections) == 0:
        logger.warning("No detections found - all crises will be marked as not detected")
        # Return all crises as not detected
        return {
            crisis_name: {
                "detected": False,
                "lead_time_days": 0,
                "detection_date": None,
                "crisis_date": pd.Timestamp(crisis_date_str).strftime("%Y-%m-%d"),
                "distance_at_crisis": None,
                "confidence": 0.0,
            }
            for crisis_name, crisis_date_str in crisis_dates.items()
        }

    results = {}

    for crisis_name, crisis_date_str in crisis_dates.items():
        crisis_date = pd.Timestamp(crisis_date_str)

        # Find detection window: ±10 trading days
        # Approximate 10 trading days as 14 calendar days
        window_start = crisis_date - pd.Timedelta(days=14)
        window_end = crisis_date + pd.Timedelta(days=14)

        # Find detections within window
        detections_in_window = detections[
            (detections['timestamp'] >= window_start) &
            (detections['timestamp'] <= window_end)
        ]

        if len(detections_in_window) > 0:
            # Find earliest detection before or near crisis
            earliest_detection = detections_in_window.iloc[0]
            detection_date = earliest_detection['timestamp']

            # Compute lead time (positive = early warning)
            lead_time = (crisis_date - detection_date).days

            # Get distance value at detection
            detection_idx = timestamps.get_loc(detection_date)
            distance_value = float(distances[detection_idx])

            results[crisis_name] = {
                "detected": True,
                "lead_time_days": lead_time,
                "detection_date": detection_date.strftime("%Y-%m-%d"),
                "crisis_date": crisis_date.strftime("%Y-%m-%d"),
                "distance_at_crisis": distance_value,
                "confidence": float(earliest_detection['confidence']),
            }

            logger.info(
                "Crisis '%s' detected %d days before onset (confidence=%.3f)",
                crisis_name,
                lead_time,
                earliest_detection['confidence'],
            )
        else:
            results[crisis_name] = {
                "detected": False,
                "lead_time_days": 0,
                "detection_date": None,
                "crisis_date": crisis_date.strftime("%Y-%m-%d"),
                "distance_at_crisis": None,
                "confidence": 0.0,
            }

            logger.warning("Crisis '%s' NOT detected", crisis_name)

    return results
