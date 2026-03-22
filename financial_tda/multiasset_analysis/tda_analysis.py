"""
Multi-Asset TDA: Core Analysis Module
Implements the TDA pipeline for cross-asset topology analysis.

=============================================================================
⚠️ METHODOLOGY COMPLIANCE WARNING ⚠️
=============================================================================
This module implements the CANONICAL Gidea & Katz (2018) pipeline:
    Takens Delay Embedding → H₁ Persistence → L¹/L² Norms → Kendall-τ Trend

DO NOT MODIFY the core algorithms without explicit approval.
See: financial_tda/docs/METHODOLOGY_REFERENCE.md

Validated Parameter Sets:
    - Standard:  W=500, P=250 (gradual crises like 2008 GFC)
    - Fast:      W=450, P=200 (rapid shocks like 2020 COVID)
    - Sensitive: W=450, P=200 (COVID-optimized)

If an experiment FAILS to detect an event, REPORT THE FAILURE.
Do NOT optimize parameters to "fix" negative results — that is p-hacking.
=============================================================================

This module provides:
1. Point cloud construction from multi-asset returns (Takens embedding)
2. Persistent homology computation via GUDHI (H₁ dimension)
3. Kendall-tau trend detection on rolling variance
"""

import sys
import numpy as np
import pandas as pd
import gudhi as gd
from scipy.stats import kendalltau
from typing import Dict, Tuple
from dataclasses import dataclass

# =============================================================================
# CONFIGURATION
# =============================================================================


@dataclass
class TDAConfig:
    """Configuration for TDA analysis."""

    # Point cloud parameters
    point_cloud_window: int = 50  # Days to form point cloud
    delay_embedding: bool = True  # Use [t, t-1] embedding (doubles dimensions)

    # Rolling analysis parameters
    rolling_window: int = 500  # Days for rolling variance
    pre_crisis_window: int = 250  # Days before event to compute tau

    # Homology parameters
    max_homology_dim: int = 2  # H0 and H1

    # Thresholds
    tau_warning: float = 0.50  # Yellow zone
    tau_alert: float = 0.60  # Orange zone
    tau_critical: float = 0.70  # Red zone


# Preset configurations for different analysis goals
CONFIG_PRESETS = {
    "standard": TDAConfig(point_cloud_window=50, rolling_window=500, pre_crisis_window=250),
    "fast": TDAConfig(point_cloud_window=50, rolling_window=300, pre_crisis_window=150),
    "sensitive": TDAConfig(point_cloud_window=50, rolling_window=450, pre_crisis_window=200),
}

# =============================================================================
# POINT CLOUD CONSTRUCTION
# =============================================================================


def construct_point_cloud(
    data: pd.DataFrame, window_start: int, window_end: int, delay_embedding: bool = True
) -> np.ndarray:
    """
    Construct a point cloud from multi-asset return data.

    Args:
        data: DataFrame with assets as columns, dates as index
        window_start: Start index (inclusive)
        window_end: End index (exclusive)
        delay_embedding: If True, use [t, t-1] embedding

    Returns:
        Point cloud as numpy array, shape (n_points, n_dims)
    """
    window = data.iloc[window_start:window_end].values
    n_assets = data.shape[1]

    if not delay_embedding:
        return window

    # Delay embedding: each point is [asset1_t, asset1_{t-1}, asset2_t, asset2_{t-1}, ...]
    point_cloud = []
    for j in range(1, len(window)):
        point = []
        for col in range(n_assets):
            point.append(window[j, col])  # t
            point.append(window[j - 1, col])  # t-1
        point_cloud.append(point)

    return np.array(point_cloud)


# =============================================================================
# PERSISTENT HOMOLOGY
# =============================================================================


def compute_persistence(point_cloud: np.ndarray, max_dimension: int = 2) -> Dict[int, np.ndarray]:
    """
    Compute persistent homology using GUDHI.

    Args:
        point_cloud: Shape (n_points, n_dims)
        max_dimension: Maximum homology dimension

    Returns:
        Dictionary mapping dimension -> persistence intervals
    """
    rips = gd.RipsComplex(points=point_cloud)
    simplex_tree = rips.create_simplex_tree(max_dimension=max_dimension)
    simplex_tree.compute_persistence()

    result = {}
    for dim in range(max_dimension):
        intervals = simplex_tree.persistence_intervals_in_dimension(dim)
        # Filter out infinite intervals for Lp norms
        finite = intervals[np.isfinite(intervals[:, 1])] if len(intervals) > 0 else np.array([])
        result[dim] = finite

    return result


def compute_lp_norms(persistence: Dict[int, np.ndarray], dimension: int = 1) -> Tuple[float, float]:
    """
    Compute L1 and L2 norms of persistence landscape.

    Args:
        persistence: Output from compute_persistence
        dimension: Homology dimension to use (default: 1 for loops)

    Returns:
        Tuple of (L1, L2) norms
    """
    intervals = persistence.get(dimension, np.array([]))

    if len(intervals) == 0:
        return 0.0, 0.0

    lifetimes = intervals[:, 1] - intervals[:, 0]
    l1 = np.sum(lifetimes)
    l2 = np.sqrt(np.sum(lifetimes**2))

    return l1, l2


# =============================================================================
# ROLLING ANALYSIS
# =============================================================================


def rolling_tda_analysis(data: pd.DataFrame, config: TDAConfig = None, verbose: bool = True) -> pd.DataFrame:
    """
    Run TDA analysis on rolling windows.

    Args:
        data: Standardized returns DataFrame
        config: TDAConfig object (uses standard preset if None)
        verbose: Print progress

    Returns:
        DataFrame with columns: Date, L1, L2, H1_Count
    """
    if config is None:
        config = CONFIG_PRESETS["standard"]

    results = []
    n = len(data)
    pc_window = config.point_cloud_window

    if verbose:
        print(f"Running TDA on {n} observations...")
        print(f"  Point cloud window: {pc_window}")
        print(f"  Dimensions: {data.shape[1]} assets x 2 (delay) = {data.shape[1] * 2}D")

    for i in range(pc_window, n):
        # Construct point cloud
        point_cloud = construct_point_cloud(
            data, window_start=i - pc_window, window_end=i, delay_embedding=config.delay_embedding
        )

        # Compute persistence
        persistence = compute_persistence(point_cloud, config.max_homology_dim)

        # Extract features
        l1, l2 = compute_lp_norms(persistence, dimension=1)
        h1_count = len(persistence.get(1, []))

        results.append({"Date": data.index[i], "L1": l1, "L2": l2, "H1_Count": h1_count})

        if verbose and i % 500 == 0:
            sys.stdout.write(f"\r  Processed {i}/{n}")

    if verbose:
        print(f"\r  Processed {n}/{n} - Complete")

    return pd.DataFrame(results).set_index("Date")


def compute_variance_tau(
    norms: pd.DataFrame, event_date: str, config: TDAConfig = None, metric: str = "L2"
) -> Tuple[float, float]:
    """
    Compute Kendall-tau trend in variance leading up to an event.

    Args:
        norms: Output from rolling_tda_analysis
        event_date: Date string (YYYY-MM-DD)
        config: TDAConfig for window sizes
        metric: 'L1' or 'L2'

    Returns:
        Tuple of (tau, p-value)
    """
    if config is None:
        config = CONFIG_PRESETS["standard"]

    event_dt = pd.to_datetime(event_date)

    # Find nearest date in index
    if event_dt not in norms.index:
        locs = norms.index.get_indexer([event_dt], method="nearest")
        event_dt = norms.index[locs[0]]

    end_loc = norms.index.get_loc(event_dt)
    start_loc = end_loc - config.pre_crisis_window

    if start_loc < config.rolling_window:
        raise ValueError(f"Insufficient data before event {event_date}")

    # Compute rolling variance
    var_col = f"{metric}_Var"
    if var_col not in norms.columns:
        norms[var_col] = norms[metric].rolling(window=config.rolling_window).var()

    segment = norms[var_col].iloc[start_loc:end_loc].dropna()

    if len(segment) < 50:
        raise ValueError(f"Segment too short: {len(segment)} points")

    tau, p = kendalltau(np.arange(len(segment)), segment.values)
    return tau, p


# =============================================================================
# REGIME FEATURES
# =============================================================================


def extract_regime_features(norms: pd.DataFrame, window_size: int = 60) -> pd.DataFrame:
    """
    Extract features for regime classification.

    Features:
    - L1_mean, L2_mean: Average persistence norms
    - L1_var, L2_var: Variance of norms
    - H1_mean: Average loop count
    - L1_L2_ratio: Ratio of L1 to L2 (indicates topology "character")
    """
    features = pd.DataFrame(index=norms.index)

    # Rolling statistics
    features["L1_mean"] = norms["L1"].rolling(window=window_size).mean()
    features["L2_mean"] = norms["L2"].rolling(window=window_size).mean()
    features["L1_var"] = norms["L1"].rolling(window=window_size).var()
    features["L2_var"] = norms["L2"].rolling(window=window_size).var()
    features["H1_mean"] = norms["H1_Count"].rolling(window=window_size).mean()

    # Derived features
    features["L1_L2_ratio"] = features["L1_mean"] / (features["L2_mean"] + 1e-8)

    return features.dropna()


# =============================================================================
# MAIN: Demo
# =============================================================================

if __name__ == "__main__":
    print("Multi-Asset TDA Analysis Module")
    print("This module provides the core TDA pipeline.")
    print("See experiment_macro_manifold.py for usage example.")
