"""
Windowing utilities for time series data.

This module provides functions for creating sliding windows from time series data,
which is essential for topological data analysis and other moving-window analyses.
"""

from typing import Any

import pandas as pd


def create_sliding_windows(
    data: pd.DataFrame,
    window_size: int,
    stride: int = 1,
) -> list[pd.DataFrame]:
    """
    Create overlapping sliding windows from a DataFrame.

    Args:
        data: Input DataFrame with time series data
        window_size: Number of time steps in each window
        stride: Step size between consecutive windows (default: 1)

    Returns:
        List of DataFrames, each representing one window

    Examples:
        >>> df = pd.DataFrame({'price': [100, 101, 102, 103, 104]})
        >>> windows = create_sliding_windows(df, window_size=3, stride=1)
        >>> len(windows)
        3
        >>> windows[0].shape
        (3, 1)

    Notes:
        - Windows that would extend beyond the data length are not created
        - Each window preserves the original DataFrame index
        - For stride=1, windows overlap by (window_size - 1) time steps
    """
    if data.empty:
        return []

    if window_size <= 0:
        raise ValueError("window_size must be positive")

    if stride <= 0:
        raise ValueError("stride must be positive")

    if window_size > len(data):
        raise ValueError(
            f"window_size ({window_size}) cannot be larger than "
            f"data length ({len(data)})"
        )

    windows = []
    num_windows = (len(data) - window_size) // stride + 1

    for i in range(num_windows):
        start_idx = i * stride
        end_idx = start_idx + window_size
        window = data.iloc[start_idx:end_idx].copy()
        windows.append(window)

    return windows


def create_labeled_windows(
    data: pd.DataFrame,
    labels: pd.Series,
    window_size: int,
    stride: int = 1,
    label_position: str = "last",
) -> list[tuple[pd.DataFrame, Any]]:
    """
    Create sliding windows with associated labels.

    Useful for supervised learning where each window needs a corresponding label
    (e.g., future price movement, market regime classification).

    Args:
        data: Input DataFrame with time series data
        labels: Series of labels aligned with data index
        window_size: Number of time steps in each window
        stride: Step size between consecutive windows (default: 1)
        label_position: Which label to use ('last', 'first', 'middle')
                       - 'last': Label from last timestamp in window
                       - 'first': Label from first timestamp in window
                       - 'middle': Label from middle timestamp in window

    Returns:
        List of (window_dataframe, label) tuples

    Examples:
        >>> df = pd.DataFrame({'price': [100, 101, 102, 103, 104]})
        >>> labels = pd.Series(['up', 'up', 'down', 'up', 'down'])
        >>> windows = create_labeled_windows(df, labels, window_size=3, stride=1)
        >>> len(windows)
        3
        >>> window, label = windows[0]
        >>> label
        'down'

    Raises:
        ValueError: If labels index doesn't match data index
        ValueError: If invalid label_position specified
    """
    if data.empty:
        return []

    if window_size <= 0:
        raise ValueError("window_size must be positive")

    if stride <= 0:
        raise ValueError("stride must be positive")

    if window_size > len(data):
        raise ValueError(
            f"window_size ({window_size}) cannot be larger than "
            f"data length ({len(data)})"
        )

    if not data.index.equals(labels.index):
        raise ValueError("labels index must match data index")

    if label_position not in {"last", "first", "middle"}:
        raise ValueError("label_position must be 'last', 'first', or 'middle'")

    labeled_windows = []
    num_windows = (len(data) - window_size) // stride + 1

    for i in range(num_windows):
        start_idx = i * stride
        end_idx = start_idx + window_size

        # Extract window
        window = data.iloc[start_idx:end_idx].copy()

        # Extract label based on position
        if label_position == "last":
            label_idx = end_idx - 1
        elif label_position == "first":
            label_idx = start_idx
        else:  # middle
            label_idx = start_idx + window_size // 2

        label = labels.iloc[label_idx]

        labeled_windows.append((window, label))

    return labeled_windows


def create_expanding_windows(
    data: pd.DataFrame,
    min_window_size: int,
    max_window_size: int | None = None,
) -> list[pd.DataFrame]:
    """
    Create expanding windows that grow from min to max size.

    Useful for analyzing how topological features evolve as more data is included.

    Args:
        data: Input DataFrame with time series data
        min_window_size: Minimum window size
        max_window_size: Maximum window size (if None, uses full data length)

    Returns:
        List of DataFrames with expanding window sizes

    Examples:
        >>> df = pd.DataFrame({'price': [100, 101, 102, 103, 104]})
        >>> windows = create_expanding_windows(df, min_window_size=2, max_window_size=4)
        >>> [len(w) for w in windows]
        [2, 3, 4]

    Notes:
        - Creates one window for each size from min_window_size to max_window_size
        - All windows start from the beginning of the data
        - Useful for analyzing temporal evolution of topological features
    """
    if data.empty:
        return []

    if min_window_size <= 0:
        raise ValueError("min_window_size must be positive")

    if max_window_size is None:
        max_window_size = len(data)

    if max_window_size > len(data):
        raise ValueError(
            f"max_window_size ({max_window_size}) cannot be larger than "
            f"data length ({len(data)})"
        )

    if min_window_size > max_window_size:
        raise ValueError("min_window_size cannot be larger than max_window_size")

    windows = []
    for size in range(min_window_size, max_window_size + 1):
        window = data.iloc[:size].copy()
        windows.append(window)

    return windows


def create_future_window_pairs(
    data: pd.DataFrame,
    window_size: int,
    forecast_horizon: int,
    stride: int = 1,
) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    """
    Create pairs of (current_window, future_window) for forecasting tasks.

    Useful for predicting future topological features or market conditions
    based on current window.

    Args:
        data: Input DataFrame with time series data
        window_size: Number of time steps in each window
        forecast_horizon: Number of time steps ahead for future window
        stride: Step size between consecutive window pairs (default: 1)

    Returns:
        List of (current_window, future_window) DataFrame tuples

    Examples:
        >>> df = pd.DataFrame({'price': [100, 101, 102, 103, 104, 105, 106]})
        >>> pairs = create_future_window_pairs(df, window_size=3, forecast_horizon=2)
        >>> current, future = pairs[0]
        >>> current.shape, future.shape
        ((3, 1), (2, 1))

    Notes:
        - Future window starts immediately after current window ends
        - Pairs where future window would extend beyond data are not created
    """
    if data.empty:
        return []

    if window_size <= 0 or forecast_horizon <= 0:
        raise ValueError("window_size and forecast_horizon must be positive")

    if stride <= 0:
        raise ValueError("stride must be positive")

    total_span = window_size + forecast_horizon
    if total_span > len(data):
        raise ValueError(
            f"window_size + forecast_horizon ({total_span}) cannot exceed "
            f"data length ({len(data)})"
        )

    pairs = []
    num_pairs = (len(data) - total_span) // stride + 1

    for i in range(num_pairs):
        start_idx = i * stride
        current_end_idx = start_idx + window_size
        future_end_idx = current_end_idx + forecast_horizon

        current_window = data.iloc[start_idx:current_end_idx].copy()
        future_window = data.iloc[current_end_idx:future_end_idx].copy()

        pairs.append((current_window, future_window))

    return pairs
