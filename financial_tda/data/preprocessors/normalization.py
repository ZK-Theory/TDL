"""
Data normalization utilities for financial time series.

This module provides various normalization methods suitable for financial data,
including methods robust to outliers which are common during crisis periods.
"""

import numpy as np
import pandas as pd


def normalize_zscore(
    data: pd.Series | pd.DataFrame,
    window: int | None = None,
) -> pd.Series | pd.DataFrame:
    """
    Normalize data using z-score (standard score).

    Z-score: (x - mean) / std

    Args:
        data: Series or DataFrame to normalize
        window: If provided, use rolling mean and std. If None, use global stats.

    Returns:
        Normalized data with mean ≈ 0 and std ≈ 1

    Examples:
        >>> data = pd.Series([100, 105, 110, 115, 120])
        >>> normalized = normalize_zscore(data)
        >>> # Mean ≈ 0, Std ≈ 1

        >>> # Rolling normalization
        >>> normalized = normalize_zscore(data, window=3)
    """
    if data.empty:
        return data.copy()

    if window is None:
        # Global normalization
        mean = data.mean()
        std = data.std()
        normalized = (data - mean) / std
    else:
        # Rolling normalization
        rolling_mean = data.rolling(window=window, min_periods=window).mean()
        rolling_std = data.rolling(window=window, min_periods=window).std()
        normalized = (data - rolling_mean) / rolling_std

    return normalized


def normalize_minmax(
    data: pd.Series | pd.DataFrame,
    window: int | None = None,
    feature_range: tuple[float, float] = (0, 1),
) -> pd.Series | pd.DataFrame:
    """
    Normalize data to a specific range using min-max scaling.

    Min-max: (x - min) / (max - min) * (range_max - range_min) + range_min

    Args:
        data: Series or DataFrame to normalize
        window: If provided, use rolling min and max. If None, use global values.
        feature_range: Target range (min, max) for normalized data

    Returns:
        Normalized data scaled to feature_range

    Examples:
        >>> data = pd.Series([100, 105, 110, 115, 120])
        >>> normalized = normalize_minmax(data)
        >>> # Range: [0, 1]

        >>> # Custom range
        >>> normalized = normalize_minmax(data, feature_range=(-1, 1))
        >>> # Range: [-1, 1]
    """
    if data.empty:
        return data.copy()

    range_min, range_max = feature_range

    if window is None:
        # Global normalization
        data_min = data.min()
        data_max = data.max()
        data_range = data_max - data_min

        # Handle case where all values are the same
        if isinstance(data_range, (int, float)) and data_range == 0:
            return data.copy() * 0 + range_min

        normalized = (data - data_min) / data_range

    else:
        # Rolling normalization
        rolling_min = data.rolling(window=window, min_periods=window).min()
        rolling_max = data.rolling(window=window, min_periods=window).max()
        data_range = rolling_max - rolling_min

        # Handle zero range
        data_range = data_range.replace(0, np.nan)
        normalized = (data - rolling_min) / data_range

    # Scale to target range
    normalized = normalized * (range_max - range_min) + range_min

    return normalized


def normalize_robust(
    data: pd.Series | pd.DataFrame,
    window: int | None = None,
) -> pd.Series | pd.DataFrame:
    """
    Normalize data using robust statistics (median and IQR).

    Robust normalization: (x - median) / IQR

    This method is more robust to outliers than z-score normalization,
    making it particularly useful for financial data during crisis periods.

    Args:
        data: Series or DataFrame to normalize
        window: If provided, use rolling median and IQR. If None, use global stats.

    Returns:
        Normalized data centered at 0 with IQR-based scaling

    Examples:
        >>> data = pd.Series([100, 105, 110, 115, 120, 200])  # 200 is outlier
        >>> normalized = normalize_robust(data)
        >>> # Outlier has less influence than with z-score
    """
    if data.empty:
        return data.copy()

    if window is None:
        # Global normalization
        median = data.median()
        q25 = data.quantile(0.25)
        q75 = data.quantile(0.75)
        iqr = q75 - q25

        # Handle zero IQR
        if isinstance(iqr, (int, float)) and iqr == 0:
            return data.copy() * 0

        normalized = (data - median) / iqr

    else:
        # Rolling normalization
        rolling_median = data.rolling(window=window, min_periods=window).median()
        rolling_q25 = data.rolling(window=window, min_periods=window).quantile(0.25)
        rolling_q75 = data.rolling(window=window, min_periods=window).quantile(0.75)
        rolling_iqr = rolling_q75 - rolling_q25

        # Handle zero IQR
        rolling_iqr = rolling_iqr.replace(0, np.nan)
        normalized = (data - rolling_median) / rolling_iqr

    return normalized


def normalize_log(
    data: pd.Series | pd.DataFrame,
) -> pd.Series | pd.DataFrame:
    """
    Apply logarithmic transformation to data.

    Useful for data with exponential growth patterns or heavy-tailed distributions.

    Args:
        data: Series or DataFrame to normalize (must be positive)

    Returns:
        Log-transformed data

    Raises:
        ValueError: If data contains non-positive values

    Examples:
        >>> data = pd.Series([100, 1000, 10000])
        >>> normalized = normalize_log(data)
        >>> # Reduces scale differences
    """
    if data.empty:
        return data.copy()

    if (data <= 0).any().any() if isinstance(data, pd.DataFrame) else (data <= 0).any():
        raise ValueError("Log normalization requires positive values")

    return np.log(data)


def normalize_log1p(
    data: pd.Series | pd.DataFrame,
) -> pd.Series | pd.DataFrame:
    """
    Apply log(1 + x) transformation to data.

    Similar to log normalization but handles zero values gracefully.

    Args:
        data: Series or DataFrame to normalize (must be non-negative)

    Returns:
        Log1p-transformed data

    Raises:
        ValueError: If data contains negative values

    Examples:
        >>> data = pd.Series([0, 10, 100, 1000])
        >>> normalized = normalize_log1p(data)
        >>> # Handles zero values unlike plain log
    """
    if data.empty:
        return data.copy()

    if (data < 0).any().any() if isinstance(data, pd.DataFrame) else (data < 0).any():
        raise ValueError("Log1p normalization requires non-negative values")

    return np.log1p(data)
