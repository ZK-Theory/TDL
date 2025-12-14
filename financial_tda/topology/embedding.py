"""
Takens delay embedding for financial time series.

This module provides functions for time-delay embedding of univariate time series,
a fundamental technique for reconstructing the phase space of dynamical systems.
The embedding transforms a 1D time series into a higher-dimensional representation
suitable for topological data analysis.

Implements the Takens embedding theorem with optimal parameter selection using
mutual information (for delay/tau) and false nearest neighbors (for dimension).

References:
    Takens, F. (1981). Detecting strange attractors in turbulence.
        Lecture Notes in Mathematics, 898, 366-381.
    Fraser, A. M., & Swinney, H. L. (1986). Independent coordinates for
        strange attractors from mutual information. Physical Review A, 33(2), 1134.
    Kennel, M. B., Brown, R., & Abarbanel, H. D. I. (1992). Determining
        embedding dimension for phase-space reconstruction. Physical Review A, 45, 3403.
"""

from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING, Literal

import numpy as np
from scipy.ndimage import gaussian_filter1d
from sklearn.metrics import mutual_info_score

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


def takens_embedding(
    time_series: NDArray[np.floating],
    delay: int,
    dimension: int,
) -> NDArray[np.floating]:
    """
    Construct Takens delay embedding of a univariate time series.

    Transforms a 1D time series into a higher-dimensional point cloud by
    creating delay vectors. Each point in the embedded space is a vector
    of consecutive samples separated by the delay parameter.

    The embedding preserves topological properties of the underlying
    dynamical system when dimension is sufficiently large (Takens theorem).

    Args:
        time_series: 1D array of time series values with shape (n_samples,).
        delay: Time delay (tau) between consecutive embedding coordinates.
            Must be a positive integer.
        dimension: Embedding dimension (d). The output will have d coordinates
            per point. Must be a positive integer >= 2.

    Returns:
        2D array of shape (n_embedded, dimension) where
        n_embedded = n_samples - (dimension - 1) * delay.
        Each row is a delay vector [x(t), x(t+tau), x(t+2*tau), ..., x(t+(d-1)*tau)].

    Raises:
        ValueError: If time_series is not 1D, or if delay/dimension are invalid,
            or if time_series is too short for the requested embedding.
        TypeError: If delay or dimension are not integers.

    Examples:
        >>> import numpy as np
        >>> ts = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        >>> embedded = takens_embedding(ts, delay=2, dimension=3)
        >>> embedded.shape
        (6, 3)
        >>> embedded[0]  # First delay vector: [x(0), x(2), x(4)]
        array([1., 3., 5.])

    Notes:
        The number of embedded points decreases as delay and dimension increase:
        n_embedded = n_samples - (dimension - 1) * delay

        For financial time series, typical values are:
        - delay (tau): 1-20 (selected via mutual information)
        - dimension (d): 3-10 (selected via false nearest neighbors)
    """
    # Input validation
    time_series = np.asarray(time_series, dtype=np.float64)

    if time_series.ndim != 1:
        raise ValueError(
            f"time_series must be 1D, got shape {time_series.shape}. "
            "Use .flatten() or .ravel() to convert."
        )

    if not isinstance(delay, (int, np.integer)):
        raise TypeError(f"delay must be an integer, got {type(delay).__name__}")

    if not isinstance(dimension, (int, np.integer)):
        raise TypeError(f"dimension must be an integer, got {type(dimension).__name__}")

    if delay < 1:
        raise ValueError(f"delay must be >= 1, got {delay}")

    if dimension < 2:
        raise ValueError(f"dimension must be >= 2, got {dimension}")

    n_samples = len(time_series)
    n_embedded = n_samples - (dimension - 1) * delay

    if n_embedded < 1:
        raise ValueError(
            f"Time series too short for embedding. "
            f"Got {n_samples} samples, need at least {(dimension - 1) * delay + 1} "
            f"for delay={delay} and dimension={dimension}."
        )

    # Check for NaN/Inf values
    if not np.isfinite(time_series).all():
        nan_count = np.isnan(time_series).sum()
        inf_count = np.isinf(time_series).sum()
        raise ValueError(
            f"time_series contains non-finite values: "
            f"{nan_count} NaN, {inf_count} Inf. "
            "Please handle missing/infinite values before embedding."
        )

    # Construct embedding matrix using stride tricks for efficiency
    # Each row i contains: [x[i], x[i+delay], x[i+2*delay], ..., x[i+(d-1)*delay]]
    embedded = np.empty((n_embedded, dimension), dtype=np.float64)

    for d in range(dimension):
        start_idx = d * delay
        end_idx = start_idx + n_embedded
        embedded[:, d] = time_series[start_idx:end_idx]

    logger.debug(
        "Created Takens embedding: %d samples -> %d points in %dD "
        "(delay=%d, dimension=%d)",
        n_samples,
        n_embedded,
        dimension,
        delay,
        dimension,
    )

    return embedded


def _compute_mutual_information(
    time_series: NDArray[np.floating],
    lag: int,
    n_bins: int,
) -> float:
    """
    Compute mutual information between time series and its lagged version.

    Uses histogram-based estimation via 2D contingency table.

    Args:
        time_series: 1D time series array.
        lag: Time lag (tau) for computing I(X(t), X(t+tau)).
        n_bins: Number of bins for histogram estimation.

    Returns:
        Mutual information value in nats.
    """
    # Create lagged pairs: (x[0], x[lag]), (x[1], x[lag+1]), ...
    x_current = time_series[:-lag]
    x_lagged = time_series[lag:]

    # Compute 2D histogram (contingency table)
    contingency, _, _ = np.histogram2d(x_current, x_lagged, bins=n_bins)

    # Compute MI from contingency table using sklearn
    return mutual_info_score(None, None, contingency=contingency)


def optimal_tau(
    time_series: NDArray[np.floating],
    max_lag: int = 100,
    *,
    n_bins: int | None = None,
    smoothing: Literal["gaussian", "moving_average", "none"] = "gaussian",
    sigma: float = 1.5,
    method: Literal["first_minimum", "global_minimum"] = "first_minimum",
    return_mi_curve: bool = False,
) -> int | tuple[int, NDArray[np.floating]]:
    """
    Compute optimal time delay for Takens embedding using mutual information.

    Finds the delay (tau) where mutual information between the time series
    and its lagged version first reaches a local minimum, indicating
    maximal independence between embedding coordinates.

    Based on Fraser & Swinney (1986) method with enhancements for
    numerical stability on short, noisy financial time series.

    Args:
        time_series: 1D array of time series values with shape (n_samples,).
        max_lag: Maximum time delay to consider. Should be < n_samples / 5
            to ensure sufficient data for embedding. Default is 100.
        n_bins: Number of bins for histogram-based MI estimation.
            If None, uses adaptive binning: max(10, min(100, sqrt(n))).
        smoothing: Smoothing method for MI curve before minimum detection.
            - "gaussian": Gaussian filter (recommended for noisy data)
            - "moving_average": Simple moving average
            - "none": No smoothing
        sigma: Standard deviation for Gaussian smoothing. Ignored if
            smoothing != "gaussian". Default is 1.5.
        method: Minimum detection method.
            - "first_minimum": Find first local minimum (recommended)
            - "global_minimum": Find global minimum (giotto-tda approach)
        return_mi_curve: If True, also return the MI values for all lags.

    Returns:
        If return_mi_curve is False:
            Optimal time delay tau (int).
        If return_mi_curve is True:
            Tuple of (tau, mi_values) where mi_values is array of MI
            for lags 1 to max_lag.

    Raises:
        ValueError: If time_series is too short, max_lag is invalid,
            or contains non-finite values.

    Examples:
        >>> import numpy as np
        >>> # Sinusoidal signal with period 20
        >>> t = np.arange(500)
        >>> signal = np.sin(2 * np.pi * t / 20)
        >>> tau = optimal_tau(signal, max_lag=30)
        >>> print(f"Optimal tau: {tau}")  # Expected: ~5 (period/4)
        Optimal tau: 5

        >>> # Get MI curve for visualization
        >>> tau, mi_curve = optimal_tau(signal, max_lag=30, return_mi_curve=True)
        >>> import matplotlib.pyplot as plt
        >>> plt.plot(range(1, 31), mi_curve)
        >>> plt.xlabel('Lag'); plt.ylabel('Mutual Information')

    Notes:
        For financial time series:
        - Daily data (100-500 pts): max_lag=20-30, n_bins=20-30
        - Intraday data (500-2000 pts): max_lag=50-100, n_bins=40-60

        If no clear minimum is found, falls back to:
        1. Global minimum if MI curve shows variation
        2. Conservative default: max(1, max_lag // 10)

    References:
        Fraser, A. M., & Swinney, H. L. (1986). Independent coordinates for
        strange attractors from mutual information. Physical Review A, 33(2), 1134.
    """
    # Input validation
    time_series = np.asarray(time_series, dtype=np.float64).flatten()
    n_samples = len(time_series)

    if n_samples < 50:
        raise ValueError(
            f"Time series too short for tau optimization. "
            f"Got {n_samples} samples, need at least 50."
        )

    if not np.isfinite(time_series).all():
        nan_count = np.isnan(time_series).sum()
        inf_count = np.isinf(time_series).sum()
        raise ValueError(
            f"time_series contains non-finite values: {nan_count} NaN, {inf_count} Inf."
        )

    # Constrain max_lag to ensure sufficient embedded points
    max_allowed_lag = n_samples // 5
    if max_lag >= max_allowed_lag:
        old_max_lag = max_lag
        max_lag = max(1, max_allowed_lag - 1)
        warnings.warn(
            f"max_lag={old_max_lag} too large for series of length {n_samples}. "
            f"Reduced to {max_lag} (< n/5).",
            UserWarning,
            stacklevel=2,
        )

    if max_lag < 1:
        raise ValueError(f"max_lag must be >= 1, got {max_lag}")

    # Adaptive binning based on series length
    if n_bins is None:
        n_bins = max(10, min(100, int(np.sqrt(n_samples))))

    # Compute MI for all lags
    mi_values = np.array(
        [
            _compute_mutual_information(time_series, lag, n_bins)
            for lag in range(1, max_lag + 1)
        ]
    )

    # Apply smoothing for numerical stability
    if smoothing == "gaussian":
        mi_smoothed = gaussian_filter1d(mi_values, sigma=sigma)
    elif smoothing == "moving_average":
        window_size = 5
        kernel = np.ones(window_size) / window_size
        # Use 'same' mode to preserve length
        mi_smoothed = np.convolve(mi_values, kernel, mode="same")
    else:  # "none"
        mi_smoothed = mi_values.copy()

    # Find optimal tau
    tau: int | None = None

    if method == "first_minimum":
        # Find first local minimum
        for i in range(1, len(mi_smoothed) - 1):
            is_local_min = (
                mi_smoothed[i] < mi_smoothed[i - 1]
                and mi_smoothed[i] < mi_smoothed[i + 1]
            )
            if is_local_min:
                tau = i + 1  # +1 because lag indexing starts at 1
                break

        # Fallback if no local minimum found
        if tau is None:
            # Check if MI curve has any variation
            mi_range = mi_smoothed.max() - mi_smoothed.min()
            if mi_range > 1e-10:
                # Use global minimum as fallback
                tau = int(np.argmin(mi_smoothed)) + 1
                logger.warning(
                    "No local minimum found in MI curve. "
                    "Using global minimum at tau=%d as fallback.",
                    tau,
                )
            else:
                # Flat MI curve - use conservative default
                tau = max(1, max_lag // 10)
                logger.warning(
                    "MI curve is flat (no structure detected). "
                    "Using conservative default tau=%d.",
                    tau,
                )
    else:  # "global_minimum"
        tau = int(np.argmin(mi_smoothed)) + 1

    # Validate tau and warn if at boundaries
    if tau >= max_lag - 1:
        warnings.warn(
            f"Optimal tau={tau} is near max_lag={max_lag}. "
            "Consider increasing max_lag for more reliable estimation.",
            UserWarning,
            stacklevel=2,
        )

    if tau <= 1:
        logger.info(
            "Optimal tau=%d is very small. This may indicate weak "
            "temporal structure in the data.",
            tau,
        )

    logger.debug(
        "Optimal tau selection: tau=%d (method=%s, smoothing=%s, n_bins=%d)",
        tau,
        method,
        smoothing,
        n_bins,
    )

    if return_mi_curve:
        return tau, mi_values
    return tau


def optimal_dimension(
    time_series: NDArray[np.floating],
    delay: int,
    max_dim: int = 15,
    *,
    fnn_threshold: float = 0.1,
    rtol: float = 15.0,
    atol: float = 2.0,
    return_fnn_curve: bool = False,
) -> int | tuple[int, NDArray[np.floating]]:
    """
    Compute optimal embedding dimension using False Nearest Neighbors (FNN).

    The FNN algorithm identifies the minimum embedding dimension where the
    attractor is fully unfolded, by detecting points that are neighbors due
    to projection rather than true dynamical proximity.

    Based on Kennel, Brown, & Abarbanel (1992) method.

    Args:
        time_series: 1D array of time series values with shape (n_samples,).
        delay: Time delay (tau) for embedding. Should be pre-computed using
            optimal_tau() or domain knowledge.
        max_dim: Maximum dimension to test. For financial time series,
            typical optimal dimensions are 3-10. Default is 15.
        fnn_threshold: Fraction of false nearest neighbors below which
            to declare the embedding sufficient. Default is 0.1 (10%).
        rtol: Relative distance tolerance for FNN criterion 1.
            A neighbor is "false" if distance increase exceeds rtol when
            going to dimension d+1. Default is 15.0 (standard value).
        atol: Absolute tolerance for FNN criterion 2, relative to
            attractor size. Default is 2.0 (standard value).
        return_fnn_curve: If True, also return the FNN fraction for each
            dimension tested.

    Returns:
        If return_fnn_curve is False:
            Optimal embedding dimension (int).
        If return_fnn_curve is True:
            Tuple of (dimension, fnn_fractions) where fnn_fractions is
            array of FNN fractions for dimensions 1 to max_dim.

    Raises:
        ValueError: If time_series is too short, delay is invalid,
            or contains non-finite values.

    Examples:
        >>> import numpy as np
        >>> # Lorenz attractor has dimension 3
        >>> # (using pre-generated Lorenz x-coordinate data)
        >>> tau = 10  # Pre-computed optimal delay
        >>> dim = optimal_dimension(lorenz_x, delay=tau, max_dim=10)
        >>> print(f"Optimal dimension: {dim}")  # Expected: 3

        >>> # With FNN curve for visualization
        >>> dim, fnn = optimal_dimension(data, delay=5, return_fnn_curve=True)
        >>> import matplotlib.pyplot as plt
        >>> plt.plot(range(1, len(fnn)+1), fnn)
        >>> plt.xlabel('Dimension'); plt.ylabel('FNN Fraction')

    Notes:
        The FNN algorithm uses two criteria to identify false neighbors:

        1. **Distance criterion**: A neighbor is false if the relative
           distance increase when going from dimension d to d+1 exceeds rtol:
           |x_{d+1}(i) - x_{d+1}(j)| / R_d(i,j) > rtol

        2. **Attractor size criterion**: A neighbor is false if the new
           distance exceeds a fraction (atol) of the attractor size:
           |x_{d+1}(i) - x_{d+1}(j)| / R_A > atol

        For financial time series, expect optimal dimensions of 3-10.
        Higher dimensions may indicate noise or insufficient data.

    References:
        Kennel, M. B., Brown, R., & Abarbanel, H. D. I. (1992). Determining
        embedding dimension for phase-space reconstruction using a
        geometrical construction. Physical Review A, 45, 3403-3411.
    """
    # Input validation
    time_series = np.asarray(time_series, dtype=np.float64).flatten()
    n_samples = len(time_series)

    if not isinstance(delay, (int, np.integer)):
        raise TypeError(f"delay must be an integer, got {type(delay).__name__}")

    if delay < 1:
        raise ValueError(f"delay must be >= 1, got {delay}")

    # Ensure enough points for embedding at max dimension
    min_samples_needed = (max_dim) * delay + 10  # Need at least 10 embedded points
    if n_samples < min_samples_needed:
        raise ValueError(
            f"Time series too short for dimension estimation. "
            f"Got {n_samples} samples, need at least {min_samples_needed} "
            f"for delay={delay} and max_dim={max_dim}."
        )

    if not np.isfinite(time_series).all():
        nan_count = np.isnan(time_series).sum()
        inf_count = np.isinf(time_series).sum()
        raise ValueError(
            f"time_series contains non-finite values: {nan_count} NaN, {inf_count} Inf."
        )

    # Compute attractor size (standard deviation as proxy)
    attractor_size = np.std(time_series)
    if attractor_size < 1e-10:
        raise ValueError(
            "Time series appears to be constant (std ≈ 0). "
            "Cannot compute embedding dimension for constant series."
        )

    # Compute FNN fraction for each dimension
    fnn_fractions = np.zeros(max_dim)

    for dim in range(1, max_dim + 1):
        fnn_fraction = _compute_fnn_fraction(
            time_series, delay, dim, rtol, atol, attractor_size
        )
        fnn_fractions[dim - 1] = fnn_fraction

        logger.debug("Dimension %d: FNN fraction = %.4f", dim, fnn_fraction)

        # Early stopping if FNN drops below threshold
        if fnn_fraction < fnn_threshold:
            optimal_dim = dim
            logger.debug(
                "FNN threshold %.2f reached at dimension %d", fnn_threshold, dim
            )
            break
    else:
        # No dimension met the threshold - use the minimum FNN dimension
        optimal_dim = int(np.argmin(fnn_fractions)) + 1
        logger.warning(
            "FNN fraction never dropped below threshold %.2f. "
            "Using dimension %d with minimum FNN fraction %.4f. "
            "Consider increasing max_dim or checking data quality.",
            fnn_threshold,
            optimal_dim,
            fnn_fractions[optimal_dim - 1],
        )

    logger.debug(
        "Optimal dimension selection: dim=%d (delay=%d, threshold=%.2f)",
        optimal_dim,
        delay,
        fnn_threshold,
    )

    if return_fnn_curve:
        return optimal_dim, fnn_fractions
    return optimal_dim


def _compute_fnn_fraction(
    time_series: NDArray[np.floating],
    delay: int,
    dimension: int,
    rtol: float,
    atol: float,
    attractor_size: float,
) -> float:
    """
    Compute the fraction of false nearest neighbors for a given dimension.

    Args:
        time_series: 1D time series array.
        delay: Time delay for embedding.
        dimension: Current embedding dimension to test.
        rtol: Relative tolerance for FNN criterion 1.
        atol: Absolute tolerance for FNN criterion 2.
        attractor_size: Standard deviation of time series (attractor size proxy).

    Returns:
        Fraction of points with false nearest neighbors (0.0 to 1.0).
    """
    n_samples = len(time_series)

    # Handle dimension=1 specially (1D embedding is just the time series itself)
    if dimension == 1:
        # For d=1, embedding is just the time series values
        n_points = n_samples - delay  # Points that have a "next" coordinate
        if n_points < 2:
            return 1.0

        embedded = time_series[:n_points].reshape(-1, 1)
        next_coords = time_series[delay : delay + n_points]
    else:
        # Create embedding at current dimension
        embedded = takens_embedding(time_series, delay, dimension)
        n_points = len(embedded)

        if n_points < 2:
            return 1.0  # Can't compute neighbors

        # Check if we can embed at dimension + 1 for FNN test
        n_points_next = n_samples - dimension * delay
        if n_points_next < 2:
            return 0.0  # Can't test higher dimension, assume sufficient

        # Get the next coordinate for each point (for d+1 embedding)
        # For point at index i, next coordinate is time_series[i + dimension * delay]
        next_coords = time_series[dimension * delay : dimension * delay + n_points]

    # Ensure shapes match (embedded and next_coords must have same length)
    n_points = len(embedded)
    if len(next_coords) != n_points:
        # Truncate to shorter length
        min_len = min(n_points, len(next_coords))
        embedded = embedded[:min_len]
        next_coords = next_coords[:min_len]
        n_points = min_len

    if n_points < 2:
        return 1.0

    # Compute pairwise distances efficiently using broadcasting
    # For large datasets, use approximate nearest neighbor, but for typical
    # financial series (< 10000 points), exact computation is feasible

    false_neighbor_count = 0
    total_valid_points = 0

    # For efficiency, use vectorized distance computation
    # Compute all pairwise squared distances
    diff = embedded[:, np.newaxis, :] - embedded[np.newaxis, :, :]
    distances_sq = np.sum(diff**2, axis=2)

    # Set diagonal to infinity to exclude self-matches
    np.fill_diagonal(distances_sq, np.inf)

    # Find nearest neighbor for each point
    nn_indices = np.argmin(distances_sq, axis=1)
    nn_distances = np.sqrt(distances_sq[np.arange(n_points), nn_indices])

    # Compute distance in the (d+1)th coordinate
    next_coord_diff = np.abs(next_coords - next_coords[nn_indices])

    for i in range(n_points):
        R_d = nn_distances[i]

        # Skip if distance is too small (numerical issues)
        if R_d < 1e-10:
            continue

        total_valid_points += 1
        delta_next = next_coord_diff[i]

        # FNN Criterion 1: Relative distance increase
        if delta_next / R_d > rtol:
            false_neighbor_count += 1
            continue

        # FNN Criterion 2: Absolute distance relative to attractor size
        if delta_next / attractor_size > atol:
            false_neighbor_count += 1

    if total_valid_points == 0:
        return 1.0

    return false_neighbor_count / total_valid_points
