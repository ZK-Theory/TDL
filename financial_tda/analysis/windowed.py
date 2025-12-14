"""
Sliding window analysis for time-evolving topological features.

This module provides tools for analyzing topological properties of time series
data using sliding windows, enabling detection of regime changes and tracking
of topological evolution over time.

References:
    Gidea, M., & Katz, Y. (2018). Topological data analysis of financial
        time series: Landscapes of crashes. Physica A, 491, 820-834.
"""

from __future__ import annotations

import logging
from typing import Generator

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from financial_tda.topology.embedding import takens_embedding
from financial_tda.topology.features import (
    extract_entropy_betti_features,
    extract_landscape_features,
)
from financial_tda.topology.filtration import compute_persistence_vr

logger = logging.getLogger(__name__)


def sliding_window_generator(
    data: NDArray[np.floating],
    window_size: int = 40,
    stride: int = 5,
) -> Generator[tuple[int, int, NDArray[np.floating]], None, None]:
    """
    Generate sliding windows over time series data.

    Yields consecutive windows of fixed size with specified stride (overlap).
    Each window is identified by its start and end indices.

    Args:
        data: Time series data of shape (n_samples,) or (n_samples, n_features).
        window_size: Number of data points per window. Default 40.
        stride: Number of points to advance between windows. Default 5.
            Smaller stride = more overlap = finer temporal resolution.

    Yields:
        Tuples of (start_idx, end_idx, window_data) where:
            - start_idx: Starting index of window in original data
            - end_idx: Ending index (exclusive) of window
            - window_data: Data slice [start_idx:end_idx]

    Examples:
        >>> data = np.random.randn(100)
        >>> gen = sliding_window_generator(data, window_size=20, stride=10)
        >>> for start, end, window in gen:
        ...     print(f"Window [{start}:{end}] has {len(window)} points")

    Notes:
        - If data length < window_size, yields single window with all data
        - Final window may be shorter than window_size if data doesn't divide evenly
        - For financial data, typical window_size=40 days, stride=5 days
    """
    data = np.asarray(data)

    if len(data) == 0:
        logger.warning("Empty data provided to sliding_window_generator")
        return

    # Handle case where data is shorter than window
    if len(data) < window_size:
        logger.warning(
            "Data length (%d) < window_size (%d), yielding single window",
            len(data),
            window_size,
        )
        yield (0, len(data), data)
        return

    # Generate windows
    start_idx = 0
    while start_idx + window_size <= len(data):
        end_idx = start_idx + window_size
        yield (start_idx, end_idx, data[start_idx:end_idx])
        start_idx += stride

    # Yield final partial window if remainder exists and is substantial
    # (at least 50% of window_size)
    if start_idx < len(data) and (len(data) - start_idx) >= window_size // 2:
        yield (start_idx, len(data), data[start_idx:])


def extract_windowed_features(
    time_series: NDArray[np.floating],
    window_size: int = 40,
    stride: int = 5,
    embedding_dim: int | None = None,
    embedding_delay: int | None = None,
    homology_dimensions: tuple[int, ...] = (1,),
) -> pd.DataFrame:
    """
    Extract topological features from sliding windows of time series.

    Applies Takens embedding → persistence computation → feature extraction
    to each window, producing a time-indexed feature matrix suitable for
    machine learning or change detection.

    Args:
        time_series: Univariate time series of shape (n_samples,).
        window_size: Number of points per window. Default 40.
        stride: Stride between windows. Default 5.
        embedding_dim: Takens embedding dimension. If None, estimated from data.
        embedding_delay: Takens embedding delay. If None, estimated from data.
        homology_dimensions: Tuple of homology dimensions to compute. Default (1,).

    Returns:
        DataFrame with columns:
            - 'window_start': Starting index of window
            - 'window_end': Ending index (exclusive) of window
            - Feature columns from landscape, image, entropy/Betti extraction
              (e.g., 'L1', 'L2', 'entropy_H1', 'amplitude_H1', etc.)

    Examples:
        >>> returns = np.random.randn(200) * 0.02  # Simulated returns
        >>> features_df = extract_windowed_features(returns, window_size=40, stride=10)
        >>> print(features_df.columns)
        >>> # Plot features over time
        >>> features_df.plot(x='window_start', y='L1')

    Notes:
        - Each window is embedded using Takens embedding
        - VR persistence computed on embedded point cloud
        - Features include landscape L^p norms, image statistics, entropy, Betti curves
        - Windows with insufficient data for persistence return NaN features
        - Typical usage: 40-day windows with 5-day stride for daily financial data
    """
    time_series = np.asarray(time_series, dtype=np.float64)

    if time_series.ndim != 1:
        raise ValueError(f"time_series must be 1D array, got shape {time_series.shape}")

    results = []

    for start_idx, end_idx, window_data in sliding_window_generator(
        time_series, window_size, stride
    ):
        # Initialize feature dictionary for this window
        features = {
            "window_start": start_idx,
            "window_end": end_idx,
        }

        try:
            # Takens embedding
            if embedding_dim is None or embedding_delay is None:
                # Use default embedding parameters
                embedded = takens_embedding(window_data, dimension=3, delay=1)
            else:
                embedded = takens_embedding(
                    window_data, dimension=embedding_dim, delay=embedding_delay
                )

            # Skip if embedding produced insufficient points
            if len(embedded) < 4:
                logger.warning(
                    "Window [%d:%d] has insufficient embedded points (%d), skipping",
                    start_idx,
                    end_idx,
                    len(embedded),
                )
                # Fill with NaN features
                features.update(_create_nan_features())
                results.append(features)
                continue

            # Compute persistence diagram
            diagram = compute_persistence_vr(
                embedded, homology_dimensions=homology_dimensions
            )

            # Extract features
            # 1. Landscape features
            try:
                landscape_feats = extract_landscape_features(diagram)
                features.update(landscape_feats)
            except Exception as e:
                logger.warning(
                    "Landscape extraction failed for window [%d:%d]: %s",
                    start_idx,
                    end_idx,
                    e,
                )
                # Add NaN landscape features
                features.update(
                    {
                        "L1": np.nan,
                        "L2": np.nan,
                        "mean": np.nan,
                        "std": np.nan,
                        "max": np.nan,
                    }
                )

            # 2. Entropy/Betti features
            try:
                entropy_feats = extract_entropy_betti_features(
                    diagram, dimensions=homology_dimensions
                )
                features.update(entropy_feats)
            except Exception as e:
                logger.warning(
                    "Entropy/Betti extraction failed for window [%d:%d]: %s",
                    start_idx,
                    end_idx,
                    e,
                )

        except Exception as e:
            logger.warning(
                "Feature extraction failed for window [%d:%d]: %s",
                start_idx,
                end_idx,
                e,
            )
            # Fill with NaN features
            features.update(_create_nan_features())

        results.append(features)

    return pd.DataFrame(results)


def _create_nan_features() -> dict[str, float]:
    """Create dictionary of NaN features for failed windows."""
    return {
        "L1": np.nan,
        "L2": np.nan,
        "mean": np.nan,
        "std": np.nan,
        "max": np.nan,
        "entropy_H1": np.nan,
        "amplitude_H1": np.nan,
        "total_persistence_H1_p1": np.nan,
        "total_persistence_H1_p2": np.nan,
        "max_betti_H1": np.nan,
        "mean_betti_H1": np.nan,
        "betti_area_H1": np.nan,
    }


def compute_window_distances(
    diagrams: list[NDArray[np.floating]],
    metric: str = "wasserstein",
    p: float = 2.0,
) -> NDArray[np.floating]:
    """
    Compute distances between consecutive persistence diagrams.

    Tracks topological dissimilarity across sliding windows, useful for
    detecting regime changes or market transitions.

    Args:
        diagrams: List of persistence diagrams, each of shape (n_features, 3).
            Diagrams should be in chronological order.
        metric: Distance metric to use:
            - 'wasserstein': Wasserstein p-distance (default)
            - 'bottleneck': Bottleneck distance (slower, O(n³))
        p: Order for Wasserstein distance. Default 2.0.

    Returns:
        Array of distances of shape (n_diagrams-1,), where
        distances[i] = distance(diagrams[i], diagrams[i+1])

    Examples:
        >>> diagrams = [compute_persistence_vr(data) for data in windows]
        >>> distances = compute_window_distances(diagrams, metric='wasserstein')
        >>> # Large distances indicate topology changes
        >>> change_points = np.where(distances > threshold)[0]

    Notes:
        - Bottleneck distance is exact but O(n³), avoid for large diagrams (>500 points)
        - Wasserstein distance is faster and captures more subtle changes
        - Distance of 0 indicates identical topology
        - Uses giotto-tda's pairwise distance implementation

    Warnings:
        If using bottleneck metric with diagrams containing >500 points,
        logs performance warning.
    """
    if len(diagrams) < 2:
        logger.warning("Need at least 2 diagrams to compute distances")
        return np.array([])

    # Check for bottleneck performance warning
    if metric == "bottleneck":
        max_points = max(len(d) for d in diagrams)
        if max_points > 500:
            logger.warning(
                "Bottleneck distance on large diagrams (>500 points) is slow (O(n³)). "
                "Consider using 'wasserstein' metric for better performance."
            )

    # Import distance computation from giotto-tda
    from gtda.diagrams import PairwiseDistance

    # Create distance transformer with appropriate parameters
    if metric == "wasserstein":
        distance_calc = PairwiseDistance(metric=metric, metric_params={"p": p})
    elif metric == "bottleneck":
        # Bottleneck uses 'delta' parameter (approximation threshold)
        distance_calc = PairwiseDistance(metric=metric, metric_params={})
    else:
        distance_calc = PairwiseDistance(metric=metric, metric_params={"p": p})

    distances = []

    for i in range(len(diagrams) - 1):
        diagram_i = diagrams[i]
        diagram_j = diagrams[i + 1]

        # Ensure diagrams are 2D numpy arrays
        diagram_i = np.asarray(diagram_i, dtype=np.float64)
        diagram_j = np.asarray(diagram_j, dtype=np.float64)

        # Reshape for giotto-tda: needs (n_samples, n_features, 3)
        # Stack two diagrams as a batch
        batch = np.array([diagram_i, diagram_j])  # Shape: (2, n_features, 3)

        # Compute pairwise distance matrix
        # fit_transform expects 3D input (n_samples, n_features, 3)
        dist_matrix = distance_calc.fit_transform(batch)

        # Extract distance between the two diagrams
        # dist_matrix has shape (2, 2) for a batch of 2 diagrams
        # We want distance[0, 1] (distance from diagram 0 to diagram 1)
        distance = float(dist_matrix[0, 1])

        distances.append(distance)

    return np.array(distances)


def detect_topology_changes(
    distances: NDArray[np.floating],
    threshold: float | None = None,
    method: str = "zscore",
) -> NDArray[np.intp]:
    """
    Detect significant topological changes from distance sequence.

    Identifies time points where persistence diagrams change significantly,
    indicating regime shifts or structural changes in the underlying data.

    Args:
        distances: Array of consecutive diagram distances from compute_window_distances.
        threshold: Threshold for change detection. If None, auto-computed.
        method: Method for auto-threshold computation:
            - 'zscore': mean + 2*std (default)
            - 'percentile': 95th percentile
            - 'iqr': Q3 + 1.5*IQR

    Returns:
        Array of indices where changes detected. Indices correspond to
        positions in the distances array (i.e., transition points between windows).

    Examples:
        >>> distances = compute_window_distances(diagrams)
        >>> change_indices = detect_topology_changes(distances, method='zscore')
        >>> print(f"Detected {len(change_indices)} regime changes")
        >>> for idx in change_indices:
        ...     print(f"Change at window transition {idx}")

    Notes:
        - Returns empty array if no changes exceed threshold
        - Auto-thresholding assumes distances follow approximately normal distribution
        - For financial data, changes often correspond to market regime shifts
        - Consider smoothing distances before change detection for noisy data
    """
    distances = np.asarray(distances, dtype=np.float64)

    if len(distances) == 0:
        return np.array([], dtype=np.intp)

    # Compute threshold if not provided
    if threshold is None:
        if method == "zscore":
            threshold = float(np.mean(distances) + 2 * np.std(distances))
        elif method == "percentile":
            threshold = float(np.percentile(distances, 95))
        elif method == "iqr":
            q1 = np.percentile(distances, 25)
            q3 = np.percentile(distances, 75)
            iqr = q3 - q1
            threshold = float(q3 + 1.5 * iqr)
        else:
            raise ValueError(
                f"Unknown method '{method}'. Use 'zscore', 'percentile', or 'iqr'"
            )

        logger.debug(
            "Auto-computed threshold=%.4f using method='%s'", threshold, method
        )

    # Detect changes
    change_indices = np.where(distances > threshold)[0]

    logger.info(
        "Detected %d topology changes (threshold=%.4f)",
        len(change_indices),
        threshold,
    )

    return change_indices
