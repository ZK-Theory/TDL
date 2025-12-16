"""
Comparative Spatial Statistics Methods for Validation.

This module implements alternative spatial analysis methods (Local Moran's I,
Getis-Ord Gi*) to compare against Morse-Smale TDA for basin/cluster identification.

Purpose:
- Test whether TDA provides genuine advantages over simpler spatial methods
- Report honestly if TDA underperforms or offers no additional value
- Compute Adjusted Rand Index and other comparison metrics

Methods Implemented:
1. Local Moran's I (LISA) - Local spatial autocorrelation clusters
2. Getis-Ord Gi* - Hot spot detection
3. DBSCAN - Density-based spatial clustering
4. Watershed Transform - Similar to Morse-Smale but simpler

References:
- Anselin (1995) Local Indicators of Spatial Association—LISA
- Getis & Ord (1992) The Analysis of Spatial Association by Use of Distance Statistics
- Ester et al. (1996) A Density-Based Algorithm for Discovering Clusters

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial import cKDTree

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# LOCAL MORAN'S I (LISA)
# =============================================================================


def compute_lisa_clusters(
    gdf,
    value_column: str = "mobility",
    weight_type: Literal["queen", "rook", "knn", "distance"] = "queen",
    significance_level: float = 0.05,
    permutations: int = 999,
):
    """
    Compute Local Moran's I (LISA) clusters.

    Identifies spatial clusters:
    - High-High (HH): High values surrounded by high values
    - Low-Low (LL): Low values surrounded by low values
    - High-Low (HL): High values surrounded by low values (spatial outliers)
    - Low-High (LH): Low values surrounded by high values (spatial outliers)

    Args:
        gdf: GeoDataFrame with geometry and value column
        value_column: Column to analyze
        weight_type: Spatial weights type
        significance_level: p-value threshold for significance
        permutations: Number of permutations for inference

    Returns:
        GeoDataFrame with added columns:
        - lisa_i: Local Moran's I statistic
        - lisa_p: p-value from permutation test
        - lisa_cluster: Cluster type (HH, LL, HL, LH, NS)
        - lisa_significant: Boolean for p < significance_level

    Example:
        >>> import geopandas as gpd
        >>> gdf = gpd.read_file('lsoa_boundaries.shp')
        >>> gdf['mobility'] = mobility_scores
        >>> gdf = compute_lisa_clusters(gdf, 'mobility')
        >>> print(gdf['lisa_cluster'].value_counts())
    """
    try:
        from libpysal.weights import Queen, Rook, KNN, DistanceBand
        from esda.moran import Moran_Local
    except ImportError:
        raise ImportError("LISA analysis requires libpysal and esda. " "Install with: pip install libpysal esda")

    result = gdf.copy()

    # Create spatial weights
    logger.info(f"Creating {weight_type} spatial weights...")

    if weight_type == "queen":
        w = Queen.from_dataframe(gdf)
    elif weight_type == "rook":
        w = Rook.from_dataframe(gdf)
    elif weight_type == "knn":
        w = KNN.from_dataframe(gdf, k=8)
    elif weight_type == "distance":
        # Use 90th percentile of nearest neighbor distances
        from libpysal.weights import min_threshold_distance

        threshold = min_threshold_distance(gdf)
        w = DistanceBand.from_dataframe(gdf, threshold=threshold * 1.5)
    else:
        raise ValueError(f"Unknown weight type: {weight_type}")

    # Row standardize weights
    w.transform = "R"

    # Compute Local Moran's I
    logger.info(f"Computing LISA with {permutations} permutations...")
    y = result[value_column].values
    lisa = Moran_Local(y, w, permutations=permutations)

    # Add results
    result["lisa_i"] = lisa.Is
    result["lisa_p"] = lisa.p_sim
    result["lisa_significant"] = lisa.p_sim < significance_level

    # Classify clusters
    # quadrant: 1=HH, 2=LH, 3=LL, 4=HL
    quadrant_labels = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}
    result["lisa_cluster"] = "NS"  # Not significant

    for q, label in quadrant_labels.items():
        mask = (lisa.q == q) & (lisa.p_sim < significance_level)
        result.loc[mask, "lisa_cluster"] = label

    # Summary
    cluster_counts = result["lisa_cluster"].value_counts()
    logger.info(f"LISA cluster counts:\n{cluster_counts}")

    return result


# =============================================================================
# GETIS-ORD Gi*
# =============================================================================


def compute_getis_ord_hotspots(
    gdf,
    value_column: str = "mobility",
    weight_type: Literal["distance", "knn"] = "distance",
    significance_level: float = 0.05,
    permutations: int = 999,
):
    """
    Compute Getis-Ord Gi* hot spot analysis.

    Identifies:
    - Hot spots: Statistically significant clusters of high values
    - Cold spots: Statistically significant clusters of low values

    Unlike LISA, Gi* focuses on intensity of clustering, not pattern type.

    Args:
        gdf: GeoDataFrame with geometry and value column
        value_column: Column to analyze
        weight_type: Spatial weights type (distance-based recommended)
        significance_level: p-value threshold
        permutations: Number of permutations

    Returns:
        GeoDataFrame with added columns:
        - gi_z: Gi* z-score
        - gi_p: p-value
        - gi_classification: 'hot', 'cold', or 'not_significant'

    Example:
        >>> gdf = compute_getis_ord_hotspots(gdf, 'mobility')
        >>> hot = gdf[gdf['gi_classification'] == 'hot']
        >>> cold = gdf[gdf['gi_classification'] == 'cold']
    """
    try:
        from libpysal.weights import KNN, DistanceBand
        from esda.getisord import G_Local
    except ImportError:
        raise ImportError("Getis-Ord analysis requires libpysal and esda. " "Install with: pip install libpysal esda")

    result = gdf.copy()

    # Create spatial weights (binary, not row-standardized for Gi*)
    logger.info(f"Creating {weight_type} spatial weights for Gi*...")

    if weight_type == "knn":
        w = KNN.from_dataframe(gdf, k=8)
    elif weight_type == "distance":
        from libpysal.weights import min_threshold_distance

        threshold = min_threshold_distance(gdf)
        w = DistanceBand.from_dataframe(gdf, threshold=threshold * 1.5, binary=True)
    else:
        raise ValueError(f"Unknown weight type: {weight_type}")

    # Compute Getis-Ord Gi*
    logger.info(f"Computing Gi* with {permutations} permutations...")
    y = result[value_column].values
    gi = G_Local(y, w, permutations=permutations, star=True)

    # Add results
    result["gi_z"] = gi.Zs
    result["gi_p"] = gi.p_sim

    # Classify hot/cold spots
    result["gi_classification"] = "not_significant"

    # Hot spots: positive z, significant p
    hot_mask = (gi.Zs > 0) & (gi.p_sim < significance_level)
    result.loc[hot_mask, "gi_classification"] = "hot"

    # Cold spots: negative z, significant p
    cold_mask = (gi.Zs < 0) & (gi.p_sim < significance_level)
    result.loc[cold_mask, "gi_classification"] = "cold"

    # Summary
    classification_counts = result["gi_classification"].value_counts()
    logger.info(f"Gi* classification counts:\n{classification_counts}")

    return result


# =============================================================================
# DBSCAN CLUSTERING
# =============================================================================


def compute_dbscan_clusters(
    gdf,
    value_column: str = "mobility",
    eps: float | None = None,
    min_samples: int = 5,
    use_coordinates: bool = True,
    include_value: bool = True,
):
    """
    Compute DBSCAN density-based spatial clusters.

    Unlike LISA/Gi*, DBSCAN doesn't assume global stationarity and can
    find clusters of arbitrary shape.

    Args:
        gdf: GeoDataFrame with geometry and value column
        value_column: Column to include in clustering
        eps: Maximum distance between points in cluster (auto-computed if None)
        min_samples: Minimum points to form a cluster
        use_coordinates: Include x,y coordinates in clustering
        include_value: Include the value column in clustering features

    Returns:
        GeoDataFrame with added 'dbscan_cluster' column (-1 = noise)

    Example:
        >>> gdf = compute_dbscan_clusters(gdf, 'mobility', eps=5000)
        >>> print(f"Found {gdf['dbscan_cluster'].nunique() - 1} clusters")
    """
    try:
        from sklearn.cluster import DBSCAN
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        raise ImportError("DBSCAN requires scikit-learn. Install with: pip install scikit-learn")

    result = gdf.copy()

    # Build feature matrix
    features = []

    if use_coordinates:
        # Extract centroids
        centroids = gdf.geometry.centroid
        x = centroids.x.values
        y = centroids.y.values
        features.append(x.reshape(-1, 1))
        features.append(y.reshape(-1, 1))

    if include_value:
        values = gdf[value_column].values.reshape(-1, 1)
        features.append(values)

    X = np.hstack(features)

    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Auto-compute eps if not provided
    if eps is None:
        from sklearn.neighbors import NearestNeighbors

        nn = NearestNeighbors(n_neighbors=min_samples)
        nn.fit(X_scaled)
        distances, _ = nn.kneighbors(X_scaled)
        eps = np.percentile(distances[:, -1], 90)
        logger.info(f"Auto-computed eps: {eps:.4f} (90th percentile of {min_samples}-NN distances)")

    # Run DBSCAN
    logger.info(f"Running DBSCAN with eps={eps:.4f}, min_samples={min_samples}")
    db = DBSCAN(eps=eps, min_samples=min_samples)
    result["dbscan_cluster"] = db.fit_predict(X_scaled)

    # Summary
    n_clusters = len(set(result["dbscan_cluster"])) - (1 if -1 in result["dbscan_cluster"].values else 0)
    n_noise = (result["dbscan_cluster"] == -1).sum()
    logger.info(f"DBSCAN found {n_clusters} clusters, {n_noise} noise points")

    return result


# =============================================================================
# WATERSHED TRANSFORM (SIMPLE ALTERNATIVE TO MORSE-SMALE)
# =============================================================================


def compute_watershed_basins(
    grid_z: np.ndarray,
    min_depth: float = 0.05,
) -> np.ndarray:
    """
    Compute watershed basins using simple image-based algorithm.

    This is a simpler alternative to Morse-Smale that operates directly
    on regular grids. It's faster but less mathematically rigorous.

    Args:
        grid_z: 2D array of values (e.g., mobility surface)
        min_depth: Minimum basin depth to keep (as fraction of range)

    Returns:
        2D array of basin labels (-1 for NaN regions)

    Example:
        >>> basins = compute_watershed_basins(mobility_grid, min_depth=0.05)
        >>> n_basins = len(np.unique(basins[basins >= 0]))
    """
    try:
        from scipy import ndimage
        from skimage.segmentation import watershed
        from skimage.feature import peak_local_max
    except ImportError:
        raise ImportError("Watershed requires scipy and scikit-image. " "Install with: pip install scipy scikit-image")

    # Handle NaN
    mask = ~np.isnan(grid_z)
    grid_filled = np.nan_to_num(grid_z, nan=np.nanmax(grid_z))

    # For finding minima, we invert (watershed finds catchment from minima)
    # We want mobility basins, so low mobility = minima
    inverted = -grid_filled

    # Find local minima as basin seeds
    value_range = np.nanmax(grid_z) - np.nanmin(grid_z)
    min_distance = max(3, int(grid_z.shape[0] * 0.05))  # Minimum 3 points or 5% of grid dimension, whichever is larger

    local_min = peak_local_max(inverted, min_distance=min_distance, threshold_rel=min_depth, exclude_border=False)

    logger.info(f"Found {len(local_min)} local minima for watershed")

    # Create markers
    markers = np.zeros_like(grid_z, dtype=int)
    for i, (y, x) in enumerate(local_min):
        markers[y, x] = i + 1

    # Run watershed
    basins = watershed(inverted, markers, mask=mask)

    # Set NaN regions to -1
    basins[~mask] = -1

    n_basins = len(np.unique(basins[basins >= 0]))
    logger.info(f"Watershed produced {n_basins} basins")

    return basins


# =============================================================================
# METHOD COMPARISON
# =============================================================================


def compare_clustering_methods(
    gdf,
    tda_basin_column: str = "tda_basin",
    value_column: str = "mobility",
) -> pd.DataFrame:
    """
    Compare TDA basins against alternative spatial clustering methods.

    Runs all methods and computes agreement metrics.

    Args:
        gdf: GeoDataFrame with TDA basin assignments and value column
        tda_basin_column: Column with TDA basin labels
        value_column: Column with mobility values

    Returns:
        DataFrame with comparison metrics for each method pair
    """
    try:
        from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
    except ImportError:
        raise ImportError("Comparison requires scikit-learn")

    results = []

    # Run alternative methods
    gdf = compute_lisa_clusters(gdf, value_column)
    gdf = compute_getis_ord_hotspots(gdf, value_column)
    gdf = compute_dbscan_clusters(gdf, value_column)

    # Define cluster labels for each method
    method_columns = {
        "TDA": tda_basin_column,
        "LISA": "lisa_cluster",
        "Gi*": "gi_classification",
        "DBSCAN": "dbscan_cluster",
    }

    # Pairwise comparisons
    methods = list(method_columns.keys())
    for i, method1 in enumerate(methods):
        for method2 in methods[i + 1 :]:
            col1 = method_columns[method1]
            col2 = method_columns[method2]

            # Handle categorical to numeric
            labels1 = pd.Categorical(gdf[col1]).codes
            labels2 = pd.Categorical(gdf[col2]).codes

            # Adjusted Rand Index
            ari = adjusted_rand_score(labels1, labels2)

            # Normalized Mutual Information
            nmi = normalized_mutual_info_score(labels1, labels2)

            results.append(
                {
                    "method1": method1,
                    "method2": method2,
                    "adjusted_rand_index": ari,
                    "normalized_mutual_info": nmi,
                }
            )

    comparison_df = pd.DataFrame(results)

    # Interpretation
    tda_comparisons = comparison_df[comparison_df["method1"] == "TDA"]
    mean_ari = tda_comparisons["adjusted_rand_index"].mean()

    if mean_ari > 0.7:
        logger.info(
            f"TDA shows STRONG agreement with alternatives (mean ARI={mean_ari:.3f}). "
            "Methods find similar structures; TDA adds rigorous mathematical framework."
        )
    elif mean_ari > 0.4:
        logger.info(
            f"TDA shows MODERATE agreement with alternatives (mean ARI={mean_ari:.3f}). "
            "Some unique structures detected by TDA."
        )
    else:
        logger.info(
            f"TDA shows WEAK agreement with alternatives (mean ARI={mean_ari:.3f}). "
            "TDA finds substantially different structures. Investigate which predicts outcomes better."
        )

    return comparison_df


def evaluate_method_predictions(
    gdf,
    method_columns: dict,
    outcome_column: str,
) -> pd.DataFrame:
    """
    Evaluate which clustering method best predicts an outcome variable.

    This is the key validation: if TDA basins predict outcomes better than
    simpler methods, TDA adds genuine value.

    Args:
        gdf: GeoDataFrame with cluster assignments and outcome
        method_columns: Dict mapping method name to cluster column
        outcome_column: Column with outcome variable (e.g., life expectancy)

    Returns:
        DataFrame with R² and effect sizes for each method
    """
    from scipy import stats

    results = []

    y = gdf[outcome_column].values

    for method_name, cluster_col in method_columns.items():
        # One-way ANOVA: does cluster predict outcome?
        clusters = gdf[cluster_col].values
        unique_clusters = [c for c in np.unique(clusters) if pd.notna(c)]

        groups = [y[clusters == c] for c in unique_clusters]
        groups = [g for g in groups if len(g) > 0]

        if len(groups) < 2:
            continue

        # F-statistic and p-value
        f_stat, p_value = stats.f_oneway(*groups)

        # Eta-squared (effect size)
        # η² = SS_between / SS_total
        grand_mean = y.mean()
        ss_total = np.sum((y - grand_mean) ** 2)
        ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
        eta_squared = ss_between / ss_total if ss_total > 0 else 0

        results.append(
            {
                "method": method_name,
                "outcome": outcome_column,
                "n_clusters": len(unique_clusters),
                "f_statistic": f_stat,
                "p_value": p_value,
                "eta_squared": eta_squared,
                "interpretation": (
                    "Large effect" if eta_squared > 0.14 else "Medium effect" if eta_squared > 0.06 else "Small effect"
                ),
            }
        )

    return pd.DataFrame(results)


# =============================================================================
# K-MEANS CLUSTERING (Protocol A4)
# =============================================================================


def compute_kmeans_clusters(
    gdf,
    value_column: str = "mobility",
    n_clusters: int | None = None,
    use_coordinates: bool = True,
    include_value: bool = True,
    random_state: int = 42,
):
    """
    Compute K-means spatial clusters.

    Args:
        gdf: GeoDataFrame with geometry and value column
        value_column: Column to include in clustering
        n_clusters: Number of clusters (auto-determined if None using silhouette)
        use_coordinates: Include x,y coordinates in clustering
        include_value: Include the value column in clustering features
        random_state: Random state for reproducibility

    Returns:
        GeoDataFrame with added 'kmeans_cluster' column
    """
    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import silhouette_score
    except ImportError:
        raise ImportError("K-means requires scikit-learn. Install with: pip install scikit-learn")

    result = gdf.copy()

    # Build feature matrix
    features = []

    if use_coordinates:
        centroids = gdf.geometry.centroid
        x = centroids.x.values
        y = centroids.y.values
        features.append(x.reshape(-1, 1))
        features.append(y.reshape(-1, 1))

    if include_value:
        values = gdf[value_column].values.reshape(-1, 1)
        features.append(values)

    X = np.hstack(features)

    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Auto-determine k using silhouette score if not provided
    if n_clusters is None:
        best_k = 2
        best_silhouette = -1

        for k in range(2, min(15, len(X_scaled) // 10)):
            km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
            labels = km.fit_predict(X_scaled)
            score = silhouette_score(X_scaled, labels)
            if score > best_silhouette:
                best_silhouette = score
                best_k = k

        n_clusters = best_k
        logger.info(f"Auto-selected k={n_clusters} (silhouette={best_silhouette:.3f})")

    # Run K-means
    logger.info(f"Running K-means with k={n_clusters}")
    km = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    result["kmeans_cluster"] = km.fit_predict(X_scaled)

    return result


# =============================================================================
# TDA BASIN ASSIGNMENT (Bridge Morse-Smale to GeoDataFrame)
# =============================================================================


def assign_basins_to_lsoas(
    gdf,
    basin_grid: np.ndarray,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    basin_column: str = "tda_basin",
):
    """
    Assign each LSOA to a Morse-Smale basin based on centroid location.

    This bridges the gap between VTK-based Morse-Smale analysis and
    GeoDataFrame-based spatial statistics comparison.

    Args:
        gdf: GeoDataFrame with LSOA geometries
        basin_grid: 2D array of basin labels from Morse-Smale analysis
        grid_x: 1D array of x coordinates for grid
        grid_y: 1D array of y coordinates for grid
        basin_column: Name for the basin assignment column

    Returns:
        GeoDataFrame with added basin assignment column

    Example:
        >>> from poverty_tda.topology.morse_smale import compute_morse_smale
        >>> ms_result = compute_morse_smale(surface_vtk)
        >>> gdf = assign_basins_to_lsoas(lsoa_gdf, ms_result.ascending_manifold,
        ...                               grid_x, grid_y)
    """
    result = gdf.copy()

    # Get LSOA centroids
    centroids = gdf.geometry.centroid
    lsoa_x = centroids.x.values
    lsoa_y = centroids.y.values

    # Create interpolator for basin assignment
    # For each LSOA centroid, find nearest grid cell and assign its basin
    grid_xx, grid_yy = np.meshgrid(grid_x, grid_y)
    grid_points = np.column_stack([grid_xx.ravel(), grid_yy.ravel()])
    basin_values = basin_grid.ravel()

    # Build KD-tree for fast nearest neighbor lookup
    tree = cKDTree(grid_points)

    # Find nearest grid cell for each LSOA
    lsoa_points = np.column_stack([lsoa_x, lsoa_y])
    _, indices = tree.query(lsoa_points)

    # Assign basins
    result[basin_column] = basin_values[indices]

    # Summary
    n_basins = len(np.unique(result[basin_column][result[basin_column] >= 0]))
    logger.info(f"Assigned {len(result)} LSOAs to {n_basins} TDA basins")

    return result


def assign_basins_from_ms_result(
    gdf,
    ms_result,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    basin_column: str = "tda_basin",
):
    """
    Assign basins from MorseSmaleResult object.

    Convenience wrapper that extracts the ascending manifold from
    the MorseSmaleResult and calls assign_basins_to_lsoas.

    Args:
        gdf: GeoDataFrame with LSOA geometries
        ms_result: MorseSmaleResult from compute_morse_smale()
        grid_x: 1D array of x coordinates for grid
        grid_y: 1D array of y coordinates for grid
        basin_column: Name for the basin assignment column

    Returns:
        GeoDataFrame with added basin assignment column
    """
    if hasattr(ms_result, "ascending_manifold") and ms_result.ascending_manifold is not None:
        basin_grid = ms_result.ascending_manifold
    else:
        raise ValueError(
            "MorseSmaleResult does not contain ascending_manifold. "
            "Ensure compute_morse_smale was run with return_manifolds=True"
        )

    return assign_basins_to_lsoas(gdf, basin_grid, grid_x, grid_y, basin_column)


# =============================================================================
# BOOTSTRAP CONFIDENCE INTERVALS
# =============================================================================


@dataclass
class BootstrapResult:
    """Result of bootstrap analysis."""

    point_estimate: float
    ci_lower: float
    ci_upper: float
    std_error: float
    n_bootstrap: int
    confidence_level: float


def bootstrap_ari_ci(
    labels1: np.ndarray,
    labels2: np.ndarray,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    block_size: int | None = None,
    random_state: int = 42,
) -> BootstrapResult:
    """
    Compute bootstrap confidence interval for Adjusted Rand Index.

    Uses block bootstrap to preserve spatial autocorrelation when
    block_size is specified.

    Args:
        labels1: First set of cluster labels
        labels2: Second set of cluster labels
        n_bootstrap: Number of bootstrap iterations
        confidence: Confidence level (e.g., 0.95 for 95% CI)
        block_size: Size of spatial blocks for block bootstrap (None for standard)
        random_state: Random state for reproducibility

    Returns:
        BootstrapResult with point estimate and confidence interval

    Example:
        >>> result = bootstrap_ari_ci(tda_labels, lisa_labels)
        >>> print(f"ARI: {result.point_estimate:.3f} (95% CI: [{result.ci_lower:.3f}, {result.ci_upper:.3f}])")
    """
    try:
        from sklearn.metrics import adjusted_rand_score
    except ImportError:
        raise ImportError("Bootstrap ARI requires scikit-learn")

    np.random.seed(random_state)
    n = len(labels1)

    # Point estimate
    point_estimate = adjusted_rand_score(labels1, labels2)

    # Bootstrap resampling
    bootstrap_aris = []

    for _ in range(n_bootstrap):
        if block_size is not None and block_size > 1:
            # Block bootstrap: resample blocks of contiguous indices
            n_blocks = n // block_size + 1
            block_starts = np.random.randint(0, n, size=n_blocks)
            indices = np.concatenate([np.arange(start, min(start + block_size, n)) for start in block_starts])[:n]
        else:
            # Standard bootstrap
            indices = np.random.randint(0, n, size=n)

        sample_labels1 = labels1[indices]
        sample_labels2 = labels2[indices]

        try:
            ari = adjusted_rand_score(sample_labels1, sample_labels2)
            bootstrap_aris.append(ari)
        except Exception:
            # Skip samples that fail (e.g., all same label)
            continue

    bootstrap_aris = np.array(bootstrap_aris)

    # Compute confidence interval
    alpha = 1 - confidence
    ci_lower = np.percentile(bootstrap_aris, 100 * alpha / 2)
    ci_upper = np.percentile(bootstrap_aris, 100 * (1 - alpha / 2))
    std_error = np.std(bootstrap_aris)

    return BootstrapResult(
        point_estimate=point_estimate,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        std_error=std_error,
        n_bootstrap=n_bootstrap,
        confidence_level=confidence,
    )


def bootstrap_eta_squared_ci(
    cluster_labels: np.ndarray,
    outcome_values: np.ndarray,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    block_size: int | None = None,
    random_state: int = 42,
) -> BootstrapResult:
    """
    Compute bootstrap confidence interval for eta-squared (η²).

    Args:
        cluster_labels: Cluster assignments
        outcome_values: Outcome variable values
        n_bootstrap: Number of bootstrap iterations
        confidence: Confidence level
        block_size: Size of spatial blocks for block bootstrap
        random_state: Random state for reproducibility

    Returns:
        BootstrapResult with point estimate and confidence interval
    """
    np.random.seed(random_state)
    n = len(cluster_labels)

    # Point estimate
    def compute_eta_squared(labels, values):
        unique_labels = np.unique(labels)
        groups = [values[labels == c] for c in unique_labels]
        groups = [g for g in groups if len(g) > 0]

        if len(groups) < 2:
            return 0.0

        grand_mean = np.mean(values)
        ss_total = np.sum((values - grand_mean) ** 2)
        ss_between = sum(len(g) * (np.mean(g) - grand_mean) ** 2 for g in groups)

        return ss_between / ss_total if ss_total > 0 else 0.0

    point_estimate = compute_eta_squared(cluster_labels, outcome_values)

    # Bootstrap resampling
    bootstrap_etas = []

    for _ in range(n_bootstrap):
        if block_size is not None and block_size > 1:
            n_blocks = n // block_size + 1
            block_starts = np.random.randint(0, n, size=n_blocks)
            indices = np.concatenate([np.arange(start, min(start + block_size, n)) for start in block_starts])[:n]
        else:
            indices = np.random.randint(0, n, size=n)

        sample_labels = cluster_labels[indices]
        sample_values = outcome_values[indices]

        try:
            eta = compute_eta_squared(sample_labels, sample_values)
            bootstrap_etas.append(eta)
        except Exception:
            continue

    bootstrap_etas = np.array(bootstrap_etas)

    alpha = 1 - confidence
    ci_lower = np.percentile(bootstrap_etas, 100 * alpha / 2)
    ci_upper = np.percentile(bootstrap_etas, 100 * (1 - alpha / 2))
    std_error = np.std(bootstrap_etas)

    return BootstrapResult(
        point_estimate=point_estimate,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        std_error=std_error,
        n_bootstrap=n_bootstrap,
        confidence_level=confidence,
    )


# =============================================================================
# BARRIER-OUTCOME CORRELATION (TDA-Specific Metric 3)
# =============================================================================


@dataclass
class BarrierCorrelationResult:
    """Result of barrier-outcome correlation analysis."""

    pearson_r: float
    p_value: float
    n_pairs: int
    barrier_heights: np.ndarray
    outcome_gradients: np.ndarray
    interpretation: str


def compute_barrier_outcome_correlation(
    ms_result,
    gdf,
    outcome_column: str,
    basin_column: str = "tda_basin",
) -> BarrierCorrelationResult:
    """
    Correlate Morse-Smale barrier heights with outcome gradients.

    This tests TDA's unique value proposition: do topological barriers
    correspond to real discontinuities in outcomes?

    For each adjacent basin pair:
    - Compute barrier height (saddle value between basins)
    - Compute outcome gradient (mean outcome difference)
    - Return Pearson r correlation

    Args:
        ms_result: MorseSmaleResult with saddle points
        gdf: GeoDataFrame with basin assignments and outcome data
        outcome_column: Column with outcome variable (e.g., 'life_expectancy')
        basin_column: Column with TDA basin assignments

    Returns:
        BarrierCorrelationResult with correlation and interpretation

    Example:
        >>> result = compute_barrier_outcome_correlation(ms_result, gdf, 'life_expectancy')
        >>> print(f"Barrier-outcome correlation: r = {result.pearson_r:.3f}")
    """
    # Get saddle points (separatrix vertices between basins)
    saddles = ms_result.get_saddles() if hasattr(ms_result, "get_saddles") else []

    if len(saddles) == 0:
        return BarrierCorrelationResult(
            pearson_r=np.nan,
            p_value=np.nan,
            n_pairs=0,
            barrier_heights=np.array([]),
            outcome_gradients=np.array([]),
            interpretation="No saddle points found in Morse-Smale result",
        )

    # Compute mean outcome per basin
    basin_outcomes = gdf.groupby(basin_column)[outcome_column].mean()

    # For each saddle, find the adjacent basins and compute gradient
    barrier_heights = []
    outcome_gradients = []

    # Get separatrices to identify adjacent basin pairs
    if hasattr(ms_result, "separatrices_1d") and ms_result.separatrices_1d:
        # Extract unique basin pairs from separatrix connectivity
        basin_pairs = set()
        for sep in ms_result.separatrices_1d:
            if hasattr(sep, "source_id") and hasattr(sep, "destination_id"):
                pair = tuple(sorted([sep.source_id, sep.destination_id]))
                basin_pairs.add(pair)
                # Barrier height is the saddle value
                if hasattr(sep, "values") and sep.values is not None and len(sep.values) > 0:
                    barrier_height = np.max(sep.values)  # Saddle is max along separatrix
                    barrier_heights.append(barrier_height)

                    # Get outcome gradient between basins
                    if pair[0] in basin_outcomes.index and pair[1] in basin_outcomes.index:
                        gradient = abs(basin_outcomes[pair[0]] - basin_outcomes[pair[1]])
                        outcome_gradients.append(gradient)
    else:
        # Fallback: use saddle values directly
        for saddle in saddles:
            barrier_heights.append(saddle.value if hasattr(saddle, "value") else 0)

    if len(barrier_heights) < 3 or len(barrier_heights) != len(outcome_gradients):
        return BarrierCorrelationResult(
            pearson_r=np.nan,
            p_value=np.nan,
            n_pairs=len(barrier_heights),
            barrier_heights=np.array(barrier_heights),
            outcome_gradients=np.array(outcome_gradients),
            interpretation="Insufficient adjacent basin pairs for correlation",
        )

    barrier_heights = np.array(barrier_heights)
    outcome_gradients = np.array(outcome_gradients)

    # Compute Pearson correlation
    r, p = stats.pearsonr(barrier_heights, outcome_gradients)

    # Interpretation
    if r > 0.5 and p < 0.05:
        interpretation = (
            f"STRONG positive correlation (r={r:.3f}, p={p:.3f}): "
            "TDA barriers capture real outcome discontinuities. "
            "Higher topological barriers correspond to larger outcome differences."
        )
    elif r > 0.3 and p < 0.05:
        interpretation = (
            f"MODERATE positive correlation (r={r:.3f}, p={p:.3f}): "
            "TDA barriers partially reflect outcome structure."
        )
    elif abs(r) < 0.2:
        interpretation = (
            f"WEAK correlation (r={r:.3f}, p={p:.3f}): "
            "TDA barriers do not strongly predict outcome discontinuities. "
            "Topological structure may not align with outcome geography."
        )
    else:
        interpretation = f"Correlation r={r:.3f}, p={p:.3f}"

    return BarrierCorrelationResult(
        pearson_r=r,
        p_value=p,
        n_pairs=len(barrier_heights),
        barrier_heights=barrier_heights,
        outcome_gradients=outcome_gradients,
        interpretation=interpretation,
    )


# =============================================================================
# STABILITY ANALYSIS (Metric 4)
# =============================================================================


@dataclass
class StabilityResult:
    """Result of parameter stability analysis."""

    method: str
    parameter_name: str
    parameter_values: list
    n_clusters_per_param: list[int]
    top_k_stability: list[float]  # Jaccard overlap with baseline
    mean_stability: float
    interpretation: str


def compute_stability_analysis(
    gdf,
    value_column: str = "mobility",
    method: Literal["morse_smale", "dbscan"] = "dbscan",
    parameter_values: list | None = None,
    top_k: int = 10,
    baseline_index: int = 2,  # Use middle parameter as baseline
) -> StabilityResult:
    """
    Test stability of clustering across parameter choices.

    For Morse-Smale: varies persistence threshold
    For DBSCAN: varies epsilon

    Args:
        gdf: GeoDataFrame with geometry and value column
        value_column: Column to analyze
        method: Method to test ('morse_smale' or 'dbscan')
        parameter_values: List of parameter values to test
        top_k: Number of top clusters to track for stability
        baseline_index: Index of parameter to use as baseline for comparison

    Returns:
        StabilityResult with stability metrics
    """
    if method == "dbscan":
        if parameter_values is None:
            # Auto-compute eps percentiles
            from sklearn.neighbors import NearestNeighbors
            from sklearn.preprocessing import StandardScaler

            centroids = gdf.geometry.centroid
            X = np.column_stack([centroids.x.values, centroids.y.values, gdf[value_column].values])
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            nn = NearestNeighbors(n_neighbors=5)
            nn.fit(X_scaled)
            distances, _ = nn.kneighbors(X_scaled)
            knn_dist = distances[:, -1]

            parameter_values = [
                np.percentile(knn_dist, 5),
                np.percentile(knn_dist, 10),
                np.percentile(knn_dist, 25),
                np.percentile(knn_dist, 50),
            ]
            parameter_name = "eps"
        else:
            parameter_name = "eps"

        # Run DBSCAN at each parameter value
        all_labels = []
        n_clusters_list = []

        for eps in parameter_values:
            result = compute_dbscan_clusters(gdf.copy(), value_column, eps=eps)
            labels = result["dbscan_cluster"].values
            all_labels.append(labels)
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            n_clusters_list.append(n_clusters)

    elif method == "morse_smale":
        parameter_name = "persistence_threshold"
        if parameter_values is None:
            parameter_values = [0.01, 0.03, 0.05, 0.07, 0.10]

        # Note: Would need to re-run Morse-Smale at each threshold
        # This is a placeholder - actual implementation requires VTK surface
        logger.warning("Morse-Smale stability analysis requires VTK surface")
        return StabilityResult(
            method=method,
            parameter_name=parameter_name,
            parameter_values=parameter_values,
            n_clusters_per_param=[],
            top_k_stability=[],
            mean_stability=np.nan,
            interpretation="Morse-Smale stability requires VTK surface (not yet implemented)",
        )

    else:
        raise ValueError(f"Unknown method: {method}")

    # Compute stability: Jaccard overlap of top-k clusters with baseline
    baseline_labels = all_labels[baseline_index]

    # Identify top-k clusters by size
    def get_top_k_labels(labels, k):
        unique, counts = np.unique(labels[labels >= 0], return_counts=True)
        top_indices = np.argsort(counts)[-k:]
        return set(unique[top_indices])

    baseline_top_k = get_top_k_labels(baseline_labels, top_k)

    stability_scores = []
    for labels in all_labels:
        current_top_k = get_top_k_labels(labels, top_k)
        # Jaccard similarity
        intersection = len(baseline_top_k & current_top_k)
        union = len(baseline_top_k | current_top_k)
        jaccard = intersection / union if union > 0 else 0
        stability_scores.append(jaccard)

    mean_stability = np.mean(stability_scores)

    if mean_stability > 0.7:
        interpretation = (
            f"HIGH stability (mean Jaccard={mean_stability:.2f}): "
            f"Top {top_k} clusters are consistent across parameter choices."
        )
    elif mean_stability > 0.4:
        interpretation = (
            f"MODERATE stability (mean Jaccard={mean_stability:.2f}): "
            f"Some variation in top clusters across parameters."
        )
    else:
        interpretation = (
            f"LOW stability (mean Jaccard={mean_stability:.2f}): "
            f"Results are sensitive to parameter choice. Use caution."
        )

    return StabilityResult(
        method=method,
        parameter_name=parameter_name,
        parameter_values=parameter_values,
        n_clusters_per_param=n_clusters_list,
        top_k_stability=stability_scores,
        mean_stability=mean_stability,
        interpretation=interpretation,
    )


# =============================================================================
# REGRESSION COMPARISON (Metric 5)
# =============================================================================


@dataclass
class RegressionComparisonResult:
    """Result of regression model comparison."""

    models: dict[str, dict]  # Model name -> {r2, adj_r2, aic, bic, rmse}
    best_model_r2: str
    best_model_aic: str
    delta_r2_vs_baseline: dict[str, float]
    interpretation: str


def compare_regression_models(
    gdf,
    outcome_column: str,
    baseline_predictors: list[str],
    method_columns: dict[str, str],
    cv_folds: int = 5,
) -> RegressionComparisonResult:
    """
    Compare predictive models with different cluster/basin indicators.

    Tests whether adding TDA features improves prediction beyond baseline.

    Args:
        gdf: GeoDataFrame with outcome and predictors
        outcome_column: Column with outcome variable
        baseline_predictors: List of baseline predictor columns
        method_columns: Dict mapping method name to cluster column
        cv_folds: Number of cross-validation folds

    Returns:
        RegressionComparisonResult with model comparison metrics

    Example:
        >>> result = compare_regression_models(
        ...     gdf, 'life_expectancy',
        ...     baseline_predictors=['imd_score'],
        ...     method_columns={'LISA': 'lisa_cluster', 'TDA': 'tda_basin'}
        ... )
    """
    try:
        from sklearn.linear_model import LinearRegression
        from sklearn.model_selection import cross_val_score
        from sklearn.preprocessing import OneHotEncoder
    except ImportError:
        raise ImportError("Regression comparison requires scikit-learn")

    # Prepare data
    y = gdf[outcome_column].values

    # Handle missing values
    valid_mask = ~np.isnan(y)
    for col in baseline_predictors:
        valid_mask &= ~gdf[col].isna()

    y = y[valid_mask]

    models = {}

    # Baseline model
    X_baseline = gdf.loc[valid_mask, baseline_predictors].values
    lr = LinearRegression()
    cv_scores = cross_val_score(lr, X_baseline, y, cv=cv_folds, scoring="neg_mean_squared_error")
    lr.fit(X_baseline, y)
    y_pred = lr.predict(X_baseline)

    n = len(y)
    p = X_baseline.shape[1]
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - p - 1)
    rmse = np.sqrt(-np.mean(cv_scores))
    aic = n * np.log(ss_res / n) + 2 * p
    bic = n * np.log(ss_res / n) + p * np.log(n)

    models["Baseline"] = {"r2": r2, "adj_r2": adj_r2, "aic": aic, "bic": bic, "cv_rmse": rmse, "n_features": p}
    baseline_r2 = r2

    # Models with cluster indicators
    encoder = OneHotEncoder(sparse_output=False, drop="first", handle_unknown="ignore")

    for method_name, cluster_col in method_columns.items():
        if cluster_col not in gdf.columns:
            logger.warning(f"Column {cluster_col} not found, skipping {method_name}")
            continue

        # One-hot encode cluster labels
        cluster_labels = gdf.loc[valid_mask, cluster_col].values.reshape(-1, 1)

        try:
            cluster_encoded = encoder.fit_transform(cluster_labels.astype(str))
        except Exception as e:
            logger.warning(f"Failed to encode {method_name}: {e}")
            continue

        X_enhanced = np.hstack([X_baseline, cluster_encoded])

        lr = LinearRegression()
        cv_scores = cross_val_score(lr, X_enhanced, y, cv=cv_folds, scoring="neg_mean_squared_error")
        lr.fit(X_enhanced, y)
        y_pred = lr.predict(X_enhanced)

        p = X_enhanced.shape[1]
        ss_res = np.sum((y - y_pred) ** 2)
        r2 = 1 - ss_res / ss_tot
        adj_r2 = 1 - (1 - r2) * (n - 1) / (n - p - 1)
        rmse = np.sqrt(-np.mean(cv_scores))
        aic = n * np.log(ss_res / n) + 2 * p
        bic = n * np.log(ss_res / n) + p * np.log(n)

        models[f"Baseline + {method_name}"] = {
            "r2": r2,
            "adj_r2": adj_r2,
            "aic": aic,
            "bic": bic,
            "cv_rmse": rmse,
            "n_features": p,
        }

    # Find best models
    best_r2_model = max(models.keys(), key=lambda k: models[k]["r2"])
    best_aic_model = min(models.keys(), key=lambda k: models[k]["aic"])

    # Compute delta R² vs baseline
    delta_r2 = {name: models[name]["r2"] - baseline_r2 for name in models if name != "Baseline"}

    # Interpretation
    best_delta = max(delta_r2.values()) if delta_r2 else 0
    if best_delta > 0.05:
        best_method = max(delta_r2.keys(), key=lambda k: delta_r2[k])
        interpretation = (
            f"Adding {best_method} improves R² by {best_delta:.3f}. "
            f"Spatial structure adds meaningful predictive power."
        )
    elif best_delta > 0.01:
        interpretation = (
            f"Modest improvement (ΔR² = {best_delta:.3f}). " f"Cluster indicators add some predictive value."
        )
    else:
        interpretation = (
            f"Minimal improvement (ΔR² = {best_delta:.3f}). " f"Baseline predictors capture most outcome variance."
        )

    return RegressionComparisonResult(
        models=models,
        best_model_r2=best_r2_model,
        best_model_aic=best_aic_model,
        delta_r2_vs_baseline=delta_r2,
        interpretation=interpretation,
    )


# =============================================================================
# MAPPER INTEGRATION (Convert Mapper to partition for comparison)
# =============================================================================


def mapper_to_partition(
    mapper_graph,
    gdf,
    assignment_method: Literal["dominant", "first", "proportional"] = "dominant",
) -> np.ndarray:
    """
    Convert Mapper graph nodes to partition (cluster labels) for comparison.

    Since Mapper nodes can overlap (a point may be in multiple nodes),
    we need a strategy to assign each point to a single cluster.

    Args:
        mapper_graph: MapperGraph from topology.mapper
        gdf: GeoDataFrame to assign labels to
        assignment_method:
            - 'dominant': Assign to node containing most points from same area
            - 'first': Assign to first node encountered
            - 'proportional': Random assignment weighted by node membership

    Returns:
        Array of cluster labels (indices into mapper_graph.nodes)

    Example:
        >>> from poverty_tda.topology.mapper import compute_mapper
        >>> graph = compute_mapper(lsoa_data, filter_values)
        >>> labels = mapper_to_partition(graph, lsoa_data)
        >>> gdf['mapper_cluster'] = labels
    """
    n_points = len(gdf)
    labels = np.full(n_points, -1, dtype=int)

    if assignment_method == "first":
        # Simple: assign each point to first node it appears in
        for node in mapper_graph.nodes:
            for member in node.members:
                if labels[member] == -1:
                    labels[member] = node.node_id

    elif assignment_method == "dominant":
        # Assign to the largest node containing the point
        point_to_nodes = {i: [] for i in range(n_points)}
        for node in mapper_graph.nodes:
            for member in node.members:
                point_to_nodes[member].append((node.node_id, node.size))

        for point_idx, nodes in point_to_nodes.items():
            if nodes:
                # Choose node with largest size
                labels[point_idx] = max(nodes, key=lambda x: x[1])[0]

    elif assignment_method == "proportional":
        # Random assignment weighted by node size
        np.random.seed(42)
        point_to_nodes = {i: [] for i in range(n_points)}
        for node in mapper_graph.nodes:
            for member in node.members:
                point_to_nodes[member].append((node.node_id, node.size))

        for point_idx, nodes in point_to_nodes.items():
            if nodes:
                node_ids = [n[0] for n in nodes]
                weights = np.array([n[1] for n in nodes], dtype=float)
                weights /= weights.sum()
                labels[point_idx] = np.random.choice(node_ids, p=weights)

    else:
        raise ValueError(f"Unknown assignment method: {assignment_method}")

    # Count unassigned
    n_unassigned = (labels == -1).sum()
    if n_unassigned > 0:
        logger.warning(f"{n_unassigned} points not assigned to any Mapper node")

    return labels


# =============================================================================
# FULL PAIRWISE COMPARISON MATRIX
# =============================================================================


def compute_full_comparison_matrix(
    gdf,
    method_columns: dict[str, str],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
) -> pd.DataFrame:
    """
    Compute full pairwise ARI matrix with bootstrap CIs.

    Unlike compare_clustering_methods which only compares TDA to alternatives,
    this computes all pairwise comparisons.

    Args:
        gdf: GeoDataFrame with cluster columns
        method_columns: Dict mapping method name to column name
        n_bootstrap: Number of bootstrap iterations for CIs
        confidence: Confidence level for CIs

    Returns:
        DataFrame with columns: method1, method2, ari, ci_lower, ci_upper, nmi

    Example:
        >>> matrix = compute_full_comparison_matrix(gdf, {
        ...     'TDA': 'tda_basin', 'LISA': 'lisa_cluster',
        ...     'DBSCAN': 'dbscan_cluster', 'Mapper': 'mapper_cluster'
        ... })
    """
    try:
        from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
    except ImportError:
        raise ImportError("Comparison requires scikit-learn")

    results = []
    methods = list(method_columns.keys())

    for i, method1 in enumerate(methods):
        for method2 in methods[i + 1 :]:
            col1 = method_columns[method1]
            col2 = method_columns[method2]

            if col1 not in gdf.columns or col2 not in gdf.columns:
                continue

            labels1 = pd.Categorical(gdf[col1]).codes
            labels2 = pd.Categorical(gdf[col2]).codes

            # Bootstrap CI for ARI
            bootstrap_result = bootstrap_ari_ci(labels1, labels2, n_bootstrap=n_bootstrap, confidence=confidence)

            # NMI point estimate
            nmi = normalized_mutual_info_score(labels1, labels2)

            results.append(
                {
                    "method1": method1,
                    "method2": method2,
                    "ari": bootstrap_result.point_estimate,
                    "ari_ci_lower": bootstrap_result.ci_lower,
                    "ari_ci_upper": bootstrap_result.ci_upper,
                    "ari_se": bootstrap_result.std_error,
                    "nmi": nmi,
                }
            )

    return pd.DataFrame(results)
