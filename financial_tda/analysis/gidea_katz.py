"""
Gidea & Katz (2018) replication module.

This module implements the methodology from:
"Topological Data Analysis of Financial Time Series: Landscapes of Crashes"
by Marian Gidea and Yuri Katz, Physica A (2018).

The key methodology:
1. Use 4 market indices simultaneously (S&P 500, DJIA, NASDAQ, Russell 2000)
2. Compute daily log-returns for each index
3. Apply sliding window (w=50 days) to create point clouds in R^4
4. Compute H1 persistence diagrams using Vietoris-Rips filtration
5. Extract persistence landscapes and compute L^p norms
6. Analyze time series of norms for early warning signals

References:
    Gidea, M., & Katz, Y. (2018). Topological data analysis of financial
        time series: Landscapes of crashes. Physica A, 491, 820-834.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from scipy import signal
from scipy.stats import kendalltau

from financial_tda.topology.features import compute_landscape_norms
from financial_tda.topology.filtration import compute_persistence_vr

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# Key crash dates from paper
CRASH_DATES = {
    "dotcom": pd.Timestamp("2000-03-10"),
    "lehman": pd.Timestamp("2008-09-15"),
}

# Default parameters from paper
DEFAULT_WINDOW_SIZE = 50
DEFAULT_STRIDE = 1
DEFAULT_N_LAYERS = 5
DEFAULT_N_BINS = 100


@dataclass
class SlidingWindowResult:
    """Results from sliding window persistence analysis.

    Attributes:
        dates: End dates for each window.
        l1_norms: L^1 norms of persistence landscapes.
        l2_norms: L^2 norms of persistence landscapes.
        window_size: Size of sliding window used.
        stride: Stride between windows.
    """

    dates: pd.DatetimeIndex
    l1_norms: NDArray[np.floating]
    l2_norms: NDArray[np.floating]
    window_size: int
    stride: int

    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to DataFrame."""
        return pd.DataFrame(
            {"L1": self.l1_norms, "L2": self.l2_norms},
            index=self.dates,
        )

    def get_pre_crash_window(
        self, crash_date: pd.Timestamp, days_before: int = 250
    ) -> pd.DataFrame:
        """Get data for window before a crash date.

        Args:
            crash_date: Date of crash.
            days_before: Number of trading days before crash.

        Returns:
            DataFrame with L1, L2 norms for the pre-crash period.
        """
        df = self.to_dataframe()
        mask = (df.index <= crash_date) & (
            df.index >= crash_date - pd.Timedelta(days=days_before * 2)
        )
        pre_crash = df[mask].tail(days_before)
        return pre_crash


def load_returns_data(
    filepath: str | Path | None = None,
) -> pd.DataFrame:
    """Load log-returns data for multi-index analysis.

    Args:
        filepath: Path to CSV file with log-returns.
            If None, uses default processed data location.

    Returns:
        DataFrame with columns [SP500, DJIA, NASDAQ, RUT] indexed by date.

    Raises:
        FileNotFoundError: If data file doesn't exist.
    """
    if filepath is None:
        base = Path(__file__).parent.parent
        filepath = base / "data/processed/gidea_katz_returns.csv"

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(
            f"Returns data not found at {filepath}. Run data fetch script first."
        )

    df = pd.read_csv(filepath, index_col=0, parse_dates=True)
    logger.info("Loaded returns data: %d rows, %d columns", len(df), len(df.columns))

    return df


def sliding_window_persistence(
    returns_df: pd.DataFrame,
    window_size: int = DEFAULT_WINDOW_SIZE,
    stride: int = DEFAULT_STRIDE,
    n_layers: int = DEFAULT_N_LAYERS,
    n_bins: int = DEFAULT_N_BINS,
    homology_dimensions: tuple[int, ...] = (1,),
    verbose: bool = True,
) -> SlidingWindowResult:
    """
    Compute persistence landscape norms using sliding window.

    Following Gidea & Katz (2018):
    - Each window of w consecutive days forms a point cloud of w points in R^d
    - d = number of indices (typically 4)
    - Compute H1 persistence using Vietoris-Rips filtration
    - Extract persistence landscape and compute L^1, L^2 norms

    Args:
        returns_df: DataFrame of log-returns with shape (n_days, n_indices).
            Index should be DatetimeIndex.
        window_size: Number of days in each window (paper uses 50 or 100).
        stride: Number of days between consecutive windows.
        n_layers: Number of landscape layers to compute.
        n_bins: Resolution of landscape sampling.
        homology_dimensions: Homology dimensions to compute (default H1 only).
        verbose: Whether to log progress.

    Returns:
        SlidingWindowResult containing dates and L^p norm time series.

    Examples:
        >>> returns = load_returns_data()
        >>> result = sliding_window_persistence(returns, window_size=50)
        >>> print(f"Computed {len(result.dates)} windows")
    """
    n_samples, n_dims = returns_df.shape
    n_windows = (n_samples - window_size) // stride + 1

    if n_windows <= 0:
        raise ValueError(
            f"Not enough data: {n_samples} samples, window_size={window_size}"
        )

    dates = []
    l1_norms = []
    l2_norms = []

    if verbose:
        logger.info(
            "Computing sliding window persistence: %d windows, size=%d, stride=%d",
            n_windows,
            window_size,
            stride,
        )

    for i in range(n_windows):
        start_idx = i * stride
        end_idx = start_idx + window_size

        # Extract window data as point cloud
        window_data = returns_df.iloc[start_idx:end_idx].values
        window_end_date = returns_df.index[end_idx - 1]

        try:
            # Compute persistence diagram (H1 for loops)
            diagram = compute_persistence_vr(
                window_data,
                homology_dimensions=homology_dimensions,
            )

            # Compute landscape norms
            norms = compute_landscape_norms(diagram, n_layers=n_layers, n_bins=n_bins)

            dates.append(window_end_date)
            l1_norms.append(norms["L1"])
            l2_norms.append(norms["L2"])

        except Exception as e:
            logger.warning("Window %d failed: %s", i, e)
            dates.append(window_end_date)
            l1_norms.append(0.0)
            l2_norms.append(0.0)

        if verbose and (i + 1) % 500 == 0:
            logger.info("Processed %d / %d windows", i + 1, n_windows)

    return SlidingWindowResult(
        dates=pd.DatetimeIndex(dates),
        l1_norms=np.array(l1_norms),
        l2_norms=np.array(l2_norms),
        window_size=window_size,
        stride=stride,
    )


def compute_rolling_variance(
    norm_series: NDArray[np.floating],
    window: int = 500,
) -> NDArray[np.floating]:
    """Compute rolling variance of norm time series.

    Args:
        norm_series: Array of L^p norm values.
        window: Rolling window size in days.

    Returns:
        Array of rolling variance values (NaN for initial window).
    """
    series = pd.Series(norm_series)
    rolling_var = series.rolling(window=window, min_periods=window).var()
    return rolling_var.values


def compute_spectral_density_low_freq(
    norm_series: NDArray[np.floating],
    fs: float = 1.0,
    nperseg: int = 256,
    low_freq_cutoff: float = 0.1,
) -> tuple[NDArray[np.floating], NDArray[np.floating], float]:
    """Compute power spectral density and average at low frequencies.

    Args:
        norm_series: Array of L^p norm values.
        fs: Sampling frequency (1.0 for daily data).
        nperseg: Length of each segment for Welch's method.
        low_freq_cutoff: Frequency below which to average (relative to Nyquist).

    Returns:
        Tuple of (frequencies, psd, average_low_freq_power).
    """
    # Remove NaN values
    clean_series = norm_series[~np.isnan(norm_series)]

    if len(clean_series) < nperseg:
        nperseg = max(len(clean_series) // 4, 8)

    frequencies, psd = signal.welch(clean_series, fs=fs, nperseg=nperseg)

    # Average power at low frequencies
    low_freq_mask = frequencies <= low_freq_cutoff
    avg_low_freq = np.mean(psd[low_freq_mask]) if low_freq_mask.any() else 0.0

    return frequencies, psd, float(avg_low_freq)


def compute_kendall_trend(
    values: NDArray[np.floating],
    days: int | None = None,
) -> tuple[float, float]:
    """Compute Kendall-tau rank correlation for trend detection.

    Following Gidea & Katz (2018), this measures monotonic trend
    in the time series (e.g., of spectral density).

    Args:
        values: Array of values to test for trend.
        days: If specified, use only last N days.

    Returns:
        Tuple of (kendall_tau, p_value).
    """
    if days is not None:
        values = values[-days:]

    # Remove NaN
    clean = values[~np.isnan(values)]

    if len(clean) < 3:
        return 0.0, 1.0

    # Time index
    time_idx = np.arange(len(clean))

    tau, p_value = kendalltau(time_idx, clean)

    return float(tau), float(p_value)


def compute_rolling_spectral_density(
    norm_series: NDArray[np.floating],
    rolling_window: int = 500,
    stride: int = 1,
    low_freq_cutoff: float = 0.1,
) -> NDArray[np.floating]:
    """Compute rolling average spectral density at low frequencies.

    Args:
        norm_series: Array of L^p norm values.
        rolling_window: Size of rolling window for spectral analysis.
        stride: Stride between windows.
        low_freq_cutoff: Frequency cutoff for low-frequency averaging.

    Returns:
        Array of rolling low-frequency spectral density values.
    """
    n = len(norm_series)
    n_windows = (n - rolling_window) // stride + 1

    spectral_densities = np.full(n, np.nan)

    for i in range(n_windows):
        start = i * stride
        end = start + rolling_window
        window_data = norm_series[start:end]

        _, _, avg_low = compute_spectral_density_low_freq(
            window_data, low_freq_cutoff=low_freq_cutoff
        )
        spectral_densities[end - 1] = avg_low

    return spectral_densities


@dataclass
class ValidationResult:
    """Results from validating against Gidea & Katz benchmarks.

    Attributes:
        crash_name: Name of crash event.
        crash_date: Date of crash.
        kendall_tau_variance: Kendall-tau for variance trend.
        kendall_tau_spectral: Kendall-tau for spectral density trend.
        p_value_spectral: P-value for spectral trend.
        days_before: Number of days before crash analyzed.
        expected_tau_spectral: Expected Kendall-tau from paper.
        meets_benchmark: Whether result meets paper benchmark.
    """

    crash_name: str
    crash_date: pd.Timestamp
    kendall_tau_variance: float
    kendall_tau_spectral: float
    p_value_spectral: float
    days_before: int
    expected_tau_spectral: float
    meets_benchmark: bool


def validate_against_paper(
    result: SlidingWindowResult,
    crash_name: str = "lehman",
    days_before: int = 250,
    rolling_window: int = 500,
    tolerance: float = 0.1,
) -> ValidationResult:
    """
    Validate results against Gidea & Katz (2018) benchmarks.

    The paper reports Kendall-tau correlation for rising spectral
    density at low frequencies:
    - Dotcom crash (2000-03-10): τ = 0.89
    - Lehman bankruptcy (2008-09-15): τ = 1.00

    Args:
        result: SlidingWindowResult from sliding_window_persistence.
        crash_name: Name of crash ("dotcom" or "lehman").
        days_before: Number of trading days before crash to analyze.
        rolling_window: Window for rolling statistics.
        tolerance: Tolerance for meeting benchmark.

    Returns:
        ValidationResult with comparison to paper benchmarks.
    """
    if crash_name not in CRASH_DATES:
        raise ValueError(f"Unknown crash: {crash_name}. Use 'dotcom' or 'lehman'.")

    crash_date = CRASH_DATES[crash_name]

    # Expected Kendall-tau from paper
    expected_tau = {"dotcom": 0.89, "lehman": 1.00}[crash_name]

    # Get pre-crash data
    df = result.to_dataframe()
    mask = df.index <= crash_date
    pre_crash_df = df[mask].tail(days_before + rolling_window)

    if len(pre_crash_df) < days_before:
        logger.warning(
            "Insufficient data before %s: got %d, need %d",
            crash_name,
            len(pre_crash_df),
            days_before,
        )

    # Compute rolling variance
    l1_values = pre_crash_df["L1"].values
    rolling_var = compute_rolling_variance(l1_values, window=rolling_window)

    # Get last `days_before` values (after rolling window warmup)
    var_for_trend = rolling_var[-days_before:]
    tau_var, _ = compute_kendall_trend(var_for_trend)

    # Compute rolling spectral density at low frequencies
    spectral_densities = compute_rolling_spectral_density(
        l1_values, rolling_window=rolling_window
    )
    spectral_for_trend = spectral_densities[-days_before:]
    tau_spectral, p_spectral = compute_kendall_trend(spectral_for_trend)

    # Check if meets benchmark
    meets = tau_spectral >= (expected_tau - tolerance)

    return ValidationResult(
        crash_name=crash_name,
        crash_date=crash_date,
        kendall_tau_variance=tau_var,
        kendall_tau_spectral=tau_spectral,
        p_value_spectral=p_spectral,
        days_before=days_before,
        expected_tau_spectral=expected_tau,
        meets_benchmark=meets,
    )


def run_full_analysis(
    filepath: str | Path | None = None,
    window_size: int = DEFAULT_WINDOW_SIZE,
    save_results: bool = True,
) -> tuple[SlidingWindowResult, dict[str, ValidationResult]]:
    """
    Run full Gidea & Katz replication analysis.

    Args:
        filepath: Path to returns data CSV.
        window_size: Sliding window size.
        save_results: Whether to save results to CSV.

    Returns:
        Tuple of (SlidingWindowResult, dict of ValidationResults).
    """
    # Load data
    returns = load_returns_data(filepath)
    logger.info("Data period: %s to %s", returns.index[0], returns.index[-1])

    # Run sliding window analysis
    result = sliding_window_persistence(
        returns,
        window_size=window_size,
        verbose=True,
    )

    # Validate against paper benchmarks
    validations = {}
    for crash_name in ["dotcom", "lehman"]:
        try:
            val = validate_against_paper(result, crash_name=crash_name)
            validations[crash_name] = val
            logger.info(
                "%s crash - Kendall-tau spectral: %.3f (expected: %.2f, meets: %s)",
                crash_name.title(),
                val.kendall_tau_spectral,
                val.expected_tau_spectral,
                val.meets_benchmark,
            )
        except Exception as e:
            logger.warning("Validation for %s failed: %s", crash_name, e)

    # Save results
    if save_results:
        output_dir = Path(__file__).parent.parent / "data/processed"
        output_path = output_dir / f"gidea_katz_norms_w{window_size}.csv"
        result.to_dataframe().to_csv(output_path)
        logger.info("Saved results to %s", output_path)

    return result, validations
