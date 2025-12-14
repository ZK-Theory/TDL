"""
Persistence-based feature extraction for financial time series.

This module provides functions for extracting topological features from
persistence diagrams, including persistence landscapes and their L^p norms
following the methodology of Gidea & Katz (2018).

References:
    Bubenik, P. (2015). Statistical topological data analysis using
        persistence landscapes. JMLR, 16, 77-102.
    Gidea, M., & Katz, Y. (2018). Topological data analysis of financial
        time series: Landscapes of crashes. Physica A, 491, 820-834.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from gtda.diagrams import PersistenceImage, PersistenceLandscape
from numpy.typing import NDArray

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Type aliases
PersistenceDiagram = NDArray[np.floating]
LandscapeArray = NDArray[np.floating]
PersistenceImageArray = NDArray[np.floating]


def compute_persistence_landscape(
    diagram: PersistenceDiagram,
    n_layers: int = 5,
    n_bins: int = 100,
    homology_dimensions: tuple[int, ...] | None = None,
) -> LandscapeArray:
    """
    Compute persistence landscape from a persistence diagram.

    The persistence landscape is a functional summary of a persistence diagram
    that lives in a Banach space, enabling statistical analysis. For each
    birth-death pair (b, d), a tent function is created with apex at
    ((b+d)/2, (d-b)/2). The k-th landscape function λ_k(t) is the k-th largest
    value of these tent functions at filtration value t.

    Args:
        diagram: Persistence diagram of shape (n_features, 3) with columns
            [birth, death, dimension].
        n_layers: Number of landscape layers (λ_1, λ_2, ..., λ_n) to compute.
            Default 5 captures main topological features.
        n_bins: Resolution of the landscape (number of filtration samples).
            Higher values give finer resolution but increase computation.
        homology_dimensions: Tuple of homology dimensions to include.
            If None, uses all dimensions present in the diagram.

    Returns:
        Landscape array of shape (n_layers, n_homology_dims, n_bins).
        For single homology dimension: (n_layers, 1, n_bins).

    Raises:
        ValueError: If diagram is empty or has invalid shape.

    Examples:
        >>> import numpy as np
        >>> # Create sample persistence diagram
        >>> diagram = np.array([[0.1, 0.5, 1], [0.2, 0.8, 1], [0.3, 0.4, 1]])
        >>> landscape = compute_persistence_landscape(diagram, n_layers=3)
        >>> print(landscape.shape)  # (3, 1, 100)

    Notes:
        Uses giotto-tda's PersistenceLandscape transformer internally.
        The landscape is sampled uniformly between min(birth) and max(death).
    """
    diagram = np.asarray(diagram, dtype=np.float64)

    if diagram.size == 0:
        raise ValueError("Empty persistence diagram")

    if diagram.ndim != 2 or diagram.shape[1] != 3:
        raise ValueError(
            f"Diagram must have shape (n_features, 3), got {diagram.shape}"
        )

    # Filter out infinite death values
    finite_mask = np.isfinite(diagram[:, 1])
    if not finite_mask.any():
        raise ValueError("All death values are infinite")

    diagram = diagram[finite_mask]

    # Determine homology dimensions
    if homology_dimensions is None:
        homology_dimensions = tuple(sorted(set(diagram[:, 2].astype(int))))

    if len(homology_dimensions) == 0:
        raise ValueError("No valid homology dimensions found")

    # giotto-tda expects 3D input: (n_samples, n_features, 3)
    diagram_3d = diagram[np.newaxis, :, :]

    # Create and fit PersistenceLandscape transformer
    landscape_transformer = PersistenceLandscape(
        n_layers=n_layers,
        n_bins=n_bins,
        n_jobs=1,
    )

    # Compute landscapes
    landscapes = landscape_transformer.fit_transform(diagram_3d)

    # Output shape: (1, n_homology_dims, n_layers * n_bins)
    # Reshape to (n_layers, n_homology_dims, n_bins)
    n_dims = len(landscape_transformer.homology_dimensions_)
    result = landscapes[0].reshape(n_dims, n_layers, n_bins)

    # Transpose to (n_layers, n_dims, n_bins) for intuitive indexing
    result = result.transpose(1, 0, 2)

    logger.debug(
        "Computed persistence landscape: %d layers, %d dims, %d bins",
        n_layers,
        n_dims,
        n_bins,
    )

    return result


def landscape_lp_norm(
    landscape: LandscapeArray,
    p: int = 1,
    resolution: float | None = None,
) -> float:
    """
    Compute L^p norm of a persistence landscape.

    The L^p norm measures the "size" of the landscape:
    - L¹ norm: ∫|λ(t)|dt = total area under landscape curves
    - L² norm: √(∫|λ(t)|²dt) = root mean square

    For the multi-layer landscape λ = (λ_1, λ_2, ...), the norm is computed
    as the sum over all layers: ||λ||_p = (Σ_k ||λ_k||_p^p)^(1/p)

    Args:
        landscape: Landscape array of shape (n_layers, n_dims, n_bins) or
            (n_layers, n_bins) for single homology dimension.
        p: Norm order (1 for L¹, 2 for L²). Must be >= 1.
        resolution: Grid spacing for numerical integration. If None,
            assumes uniform spacing with total range = 1.

    Returns:
        L^p norm of the landscape (float >= 0).

    Examples:
        >>> landscape = compute_persistence_landscape(diagram)
        >>> l1_norm = landscape_lp_norm(landscape, p=1)
        >>> l2_norm = landscape_lp_norm(landscape, p=2)
        >>> print(f"L1={l1_norm:.4f}, L2={l2_norm:.4f}")

    Notes:
        Following Gidea & Katz (2018), both L¹ and L² norms are computed
        to track changes in persistence landscape magnitude over time.
    """
    landscape = np.asarray(landscape, dtype=np.float64)

    if p < 1:
        raise ValueError(f"p must be >= 1, got {p}")

    if landscape.size == 0:
        return 0.0

    # Flatten to 1D for norm computation (sum over all layers and dimensions)
    flat = landscape.ravel()

    # Compute discretized L^p norm
    # For uniform grid: ||f||_p ≈ (Σ |f_i|^p * Δt)^(1/p)
    if resolution is None:
        # Assume uniform spacing, normalize by number of bins
        n_bins = landscape.shape[-1]
        resolution = 1.0 / n_bins

    if p == 1:
        # L¹ norm: sum of absolute values × resolution
        return float(np.sum(np.abs(flat)) * resolution)
    elif p == 2:
        # L² norm: sqrt of sum of squares × resolution
        return float(np.sqrt(np.sum(flat**2) * resolution))
    else:
        # General L^p norm
        return float((np.sum(np.abs(flat) ** p) * resolution) ** (1 / p))


def compute_landscape_norms(
    diagram: PersistenceDiagram,
    n_layers: int = 5,
    n_bins: int = 100,
) -> dict[str, float]:
    """
    Compute L¹ and L² norms of persistence landscape from a diagram.

    Convenience function that combines landscape computation and norm
    calculation, following Gidea & Katz (2018) methodology.

    Args:
        diagram: Persistence diagram of shape (n_features, 3).
        n_layers: Number of landscape layers to compute.
        n_bins: Resolution of landscape sampling.

    Returns:
        Dictionary with keys 'L1' and 'L2' containing norm values.

    Examples:
        >>> norms = compute_landscape_norms(diagram)
        >>> print(f"L1 norm: {norms['L1']:.4f}")
        >>> print(f"L2 norm: {norms['L2']:.4f}")
    """
    try:
        landscape = compute_persistence_landscape(
            diagram, n_layers=n_layers, n_bins=n_bins
        )
        l1 = landscape_lp_norm(landscape, p=1)
        l2 = landscape_lp_norm(landscape, p=2)
    except ValueError as e:
        # Handle edge cases (empty diagram, all infinite, etc.)
        logger.warning("Could not compute landscape norms: %s", e)
        l1 = 0.0
        l2 = 0.0

    return {"L1": l1, "L2": l2}


def persistence_entropy(diagram: PersistenceDiagram) -> float:
    """
    Compute persistence entropy of a persistence diagram.

    Persistence entropy measures the complexity/disorder of the persistence
    diagram. Defined as: E = -Σ p_i log(p_i) where p_i = (d_i - b_i) / Σ(d_j - b_j)

    Args:
        diagram: Persistence diagram of shape (n_features, 3).

    Returns:
        Persistence entropy (float >= 0). Higher values indicate more
        evenly distributed persistence, lower values indicate dominance
        by few features.

    Examples:
        >>> entropy = persistence_entropy(diagram)
        >>> print(f"Persistence entropy: {entropy:.4f}")
    """
    diagram = np.asarray(diagram, dtype=np.float64)

    if diagram.size == 0:
        return 0.0

    # Filter finite values
    finite_mask = np.isfinite(diagram[:, 1])
    diagram = diagram[finite_mask]

    if len(diagram) == 0:
        return 0.0

    # Compute lifetimes
    lifetimes = diagram[:, 1] - diagram[:, 0]
    lifetimes = lifetimes[lifetimes > 0]

    if len(lifetimes) == 0:
        return 0.0

    # Normalize to probability distribution
    total = np.sum(lifetimes)
    if total <= 0:
        return 0.0

    probs = lifetimes / total

    # Compute entropy (handling numerical issues)
    probs = probs[probs > 0]
    entropy = -np.sum(probs * np.log(probs))

    return float(entropy)


def betti_curve(
    diagram: PersistenceDiagram,
    dimension: int,
    n_bins: int = 100,
    filtration_range: tuple[float, float] | None = None,
) -> tuple[NDArray[np.floating], NDArray[np.integer]]:
    """
    Compute Betti curve (Betti numbers as function of filtration parameter).

    The Betti curve β_k(ε) counts the number of k-dimensional features
    alive at filtration value ε.

    Args:
        diagram: Persistence diagram of shape (n_features, 3).
        dimension: Homology dimension to compute Betti curve for.
        n_bins: Number of filtration values to sample.
        filtration_range: Tuple (min, max) for filtration values.
            If None, uses range from diagram.

    Returns:
        Tuple of (filtration_values, betti_numbers) arrays.

    Examples:
        >>> filtration, betti = betti_curve(diagram, dimension=1)
        >>> plt.plot(filtration, betti)
        >>> plt.xlabel('Filtration parameter')
        >>> plt.ylabel('β₁')
    """
    diagram = np.asarray(diagram, dtype=np.float64)

    if diagram.size == 0:
        if filtration_range is None:
            filtration_range = (0.0, 1.0)
        filtration = np.linspace(filtration_range[0], filtration_range[1], n_bins)
        return filtration, np.zeros(n_bins, dtype=np.int64)

    # Filter to specified dimension
    dim_mask = diagram[:, 2] == dimension
    dim_diagram = diagram[dim_mask]

    # Filter infinite values
    finite_mask = np.isfinite(dim_diagram[:, 1])
    dim_diagram = dim_diagram[finite_mask]

    if len(dim_diagram) == 0:
        if filtration_range is None:
            filtration_range = (0.0, 1.0)
        filtration = np.linspace(filtration_range[0], filtration_range[1], n_bins)
        return filtration, np.zeros(n_bins, dtype=np.int64)

    # Determine filtration range
    if filtration_range is None:
        min_val = dim_diagram[:, 0].min()
        max_val = dim_diagram[:, 1].max()
        # Add small margin
        margin = (max_val - min_val) * 0.05
        filtration_range = (min_val - margin, max_val + margin)

    filtration = np.linspace(filtration_range[0], filtration_range[1], n_bins)

    # Count alive features at each filtration value
    births = dim_diagram[:, 0]
    deaths = dim_diagram[:, 1]

    betti = np.zeros(n_bins, dtype=np.int64)
    for i, eps in enumerate(filtration):
        # Feature is alive if birth <= eps < death
        betti[i] = np.sum((births <= eps) & (eps < deaths))

    return filtration, betti


def total_persistence(
    diagram: PersistenceDiagram,
    dimension: int | None = None,
    p: float = 1.0,
) -> float:
    """
    Compute total persistence (sum of lifetimes raised to power p).

    Total persistence is a simple summary statistic:
    TP_p = Σ (d_i - b_i)^p

    Args:
        diagram: Persistence diagram of shape (n_features, 3).
        dimension: If specified, only include features of this dimension.
        p: Power to raise lifetimes to. Default 1.0 gives sum of lifetimes.

    Returns:
        Total persistence value (float >= 0).

    Examples:
        >>> tp1 = total_persistence(diagram, dimension=1, p=1)  # H1 lifetimes
        >>> tp2 = total_persistence(diagram, dimension=1, p=2)  # Squared
    """
    diagram = np.asarray(diagram, dtype=np.float64)

    if diagram.size == 0:
        return 0.0

    # Filter by dimension if specified
    if dimension is not None:
        diagram = diagram[diagram[:, 2] == dimension]

    # Filter infinite values
    finite_mask = np.isfinite(diagram[:, 1])
    diagram = diagram[finite_mask]

    if len(diagram) == 0:
        return 0.0

    lifetimes = diagram[:, 1] - diagram[:, 0]
    lifetimes = lifetimes[lifetimes > 0]

    return float(np.sum(lifetimes**p))


def landscape_statistics(landscape: LandscapeArray) -> dict[str, float | dict]:
    """
    Compute statistical summaries of a persistence landscape.

    Extracts mean, standard deviation, and maximum amplitude across all
    landscape layers and bins, as well as per-layer statistics.

    Args:
        landscape: Landscape array of shape (n_layers, n_dims, n_bins) or
            (n_layers, n_bins) for single homology dimension.

    Returns:
        Dictionary containing:
            - 'mean': Mean amplitude across all layers and bins
            - 'std': Standard deviation of amplitudes
            - 'max': Maximum amplitude (peak persistence)
            - 'per_layer': Dict with per-layer statistics (mean, std, max)
                Format: {0: {'mean': ..., 'std': ..., 'max': ...}, 1: {...}, ...}

    Examples:
        >>> landscape = compute_persistence_landscape(diagram)
        >>> stats = landscape_statistics(landscape)
        >>> print(f"Mean amplitude: {stats['mean']:.4f}")
        >>> print(f"Peak persistence: {stats['max']:.4f}")
        >>> print(f"Layer 0 mean: {stats['per_layer'][0]['mean']:.4f}")

    Notes:
        Statistical summaries provide complementary information to L^p norms,
        capturing different aspects of landscape shape and distribution.
    """
    landscape = np.asarray(landscape, dtype=np.float64)

    if landscape.size == 0:
        return {
            "mean": 0.0,
            "std": 0.0,
            "max": 0.0,
            "per_layer": {},
        }

    # Global statistics across all layers/dims/bins
    flat = landscape.ravel()
    global_stats = {
        "mean": float(np.mean(flat)),
        "std": float(np.std(flat)),
        "max": float(np.max(flat)),
    }

    # Per-layer statistics
    per_layer_stats = {}
    n_layers = landscape.shape[0]

    for k in range(n_layers):
        layer_data = landscape[k].ravel()
        per_layer_stats[k] = {
            "mean": float(np.mean(layer_data)),
            "std": float(np.std(layer_data)),
            "max": float(np.max(layer_data)),
        }

    global_stats["per_layer"] = per_layer_stats

    return global_stats


def extract_landscape_features(
    diagram: PersistenceDiagram,
    n_layers: int = 5,
    n_bins: int = 100,
    n_top_layers: int = 3,
) -> dict[str, float]:
    """
    Extract complete feature dictionary from persistence diagram.

    Convenience function that computes a comprehensive set of landscape-based
    features suitable for machine learning pipelines.

    Args:
        diagram: Persistence diagram of shape (n_features, 3).
        n_layers: Number of landscape layers to compute.
        n_bins: Resolution of landscape sampling.
        n_top_layers: Number of top layers to include per-layer statistics for.

    Returns:
        Dictionary containing:
            - 'L1': L¹ norm of landscape
            - 'L2': L² norm of landscape
            - 'mean': Mean amplitude across all layers
            - 'std': Standard deviation of amplitudes
            - 'max': Maximum amplitude
            - 'layer_k_mean': Mean for layer k (k=0 to n_top_layers-1)
            - 'layer_k_std': Std for layer k
            - 'layer_k_max': Max for layer k

    Examples:
        >>> features = extract_landscape_features(diagram)
        >>> print(f"Feature vector size: {len(features)}")
        >>> # Use in ML pipeline
        >>> feature_vector = np.array(list(features.values()))

    Notes:
        This function provides a ready-to-use feature dictionary for
        downstream tasks like classification or regression.
    """
    features = {}

    try:
        # Compute landscape
        landscape = compute_persistence_landscape(
            diagram, n_layers=n_layers, n_bins=n_bins
        )

        # L^p norms
        norms = compute_landscape_norms(diagram, n_layers=n_layers, n_bins=n_bins)
        features["L1"] = norms["L1"]
        features["L2"] = norms["L2"]

        # Statistical summaries
        stats = landscape_statistics(landscape)
        features["mean"] = stats["mean"]
        features["std"] = stats["std"]
        features["max"] = stats["max"]

        # Per-layer statistics for top N layers
        for k in range(min(n_top_layers, n_layers)):
            if k in stats["per_layer"]:
                layer_stats = stats["per_layer"][k]
                features[f"layer_{k}_mean"] = layer_stats["mean"]
                features[f"layer_{k}_std"] = layer_stats["std"]
                features[f"layer_{k}_max"] = layer_stats["max"]

    except ValueError as e:
        # Handle edge cases (empty diagram, all infinite, etc.)
        logger.warning("Could not extract landscape features: %s", e)

        # Return zero features
        features = {
            "L1": 0.0,
            "L2": 0.0,
            "mean": 0.0,
            "std": 0.0,
            "max": 0.0,
        }

        # Add per-layer zero features
        for k in range(n_top_layers):
            features[f"layer_{k}_mean"] = 0.0
            features[f"layer_{k}_std"] = 0.0
            features[f"layer_{k}_max"] = 0.0

    return features


def compute_persistence_image(
    diagram: PersistenceDiagram,
    resolution: tuple[int, int] = (50, 50),
    sigma: float | None = None,
    weight_function: str | None = "linear",
    weight_power: float = 1.0,
) -> PersistenceImageArray:
    """
    Compute persistence image from a persistence diagram.

    Persistence images provide a stable vectorization of persistence diagrams
    by applying a Gaussian kernel to each point (birth, persistence) and
    summing contributions on a grid. This creates a fixed-size representation
    suitable for machine learning.

    Args:
        diagram: Persistence diagram of shape (n_features, 3) with columns
            [birth, death, dimension].
        resolution: Image grid size as (n_bins_x, n_bins_y). Default (50, 50).
        sigma: Gaussian kernel bandwidth. If None, automatically selected
            based on diagram spread (approximately 1/10 of diagram range).
        weight_function: Weighting scheme for persistence points:
            - 'linear': Weight by persistence (death - birth)
            - 'persistence': Weight by persistence^weight_power
            - None: No weighting (all points equally weighted)
        weight_power: Power for 'persistence' weighting. Default 1.0.

    Returns:
        Persistence image of shape (n_homology_dims, n_bins_x * n_bins_y).
        For single homology dimension: (1, n_bins_x * n_bins_y).

    Raises:
        ValueError: If diagram is empty or has invalid shape.

    Examples:
        >>> import numpy as np
        >>> diagram = np.array([[0.1, 0.5, 1], [0.2, 0.8, 1], [0.3, 0.4, 1]])
        >>> image = compute_persistence_image(diagram, resolution=(50, 50))
        >>> print(image.shape)  # (1, 2500)
        >>> # Reshape for visualization
        >>> img_2d = image[0].reshape(50, 50)

    Notes:
        Uses giotto-tda's PersistenceImage transformer. The image is computed
        in birth-persistence coordinates, where y = death - birth (persistence).
        Higher persistence features receive higher weights with 'linear' or
        'persistence' weighting schemes.

    References:
        Adams, H., et al. (2017). Persistence images: A stable vector
            representation of persistent homology. JMLR, 18(1), 218-252.
    """
    diagram = np.asarray(diagram, dtype=np.float64)

    if diagram.size == 0:
        raise ValueError("Empty persistence diagram")

    if diagram.ndim != 2 or diagram.shape[1] != 3:
        raise ValueError(
            f"Diagram must have shape (n_features, 3), got {diagram.shape}"
        )

    # Filter out infinite death values
    finite_mask = np.isfinite(diagram[:, 1])
    if not finite_mask.any():
        raise ValueError("All death values are infinite")

    diagram = diagram[finite_mask]

    # Auto-select sigma if not provided
    if sigma is None:
        # Use approximately 1/10 of diagram range
        birth_range = diagram[:, 1].max() - diagram[:, 0].min()
        sigma = birth_range / 10.0
        if sigma <= 0:
            sigma = 0.1  # Fallback value

    # Prepare weight function for giotto-tda
    # giotto-tda's PersistenceImage calls weight_function with persistence
    # values (1D array), not with full birth-death pairs
    def _linear_weight(x):
        """Linear weighting: w(persistence) = persistence."""
        return x  # x is already persistence = death - birth

    def _persistence_weight(x):
        """Persistence-power weighting: w(persistence) = persistence^p."""
        return x**weight_power

    if weight_function == "linear":
        weight_fn = _linear_weight
    elif weight_function == "persistence":
        weight_fn = _persistence_weight
    else:
        # No weighting
        weight_fn = None

    # giotto-tda expects 3D input: (n_samples, n_features, 3)
    diagram_3d = diagram[np.newaxis, :, :]

    # Create PersistenceImage transformer
    image_transformer = PersistenceImage(
        n_bins=resolution[0],  # giotto-tda uses square grids with n_bins parameter
        sigma=sigma,
        weight_function=weight_fn,
        n_jobs=1,
    )

    # Compute persistence image
    images = image_transformer.fit_transform(diagram_3d)

    # Output shape: (1, n_homology_dims, n_bins_x, n_bins_y)
    # giotto-tda returns 2D images (not flattened), reshape to (n_dims, n_bins*n_bins)
    n_dims = images.shape[1]
    n_bins_x = resolution[0]
    n_bins_y = resolution[1]

    # Reshape from (1, n_dims, n_bins_x, n_bins_y) to (n_dims, n_bins_x * n_bins_y)
    result = images[0].reshape(n_dims, n_bins_x * n_bins_y)

    logger.debug(
        "Computed persistence image: resolution=%s, sigma=%.4f, weighting=%s",
        resolution,
        sigma,
        weight_function,
    )

    return result


def extract_image_features(
    image: PersistenceImageArray,
    include_raw: bool = False,
) -> dict[str, float | NDArray[np.floating]]:
    """
    Extract feature dictionary from persistence image.

    Computes summary statistics and optionally includes flattened image as
    feature vector for machine learning pipelines.

    Args:
        image: Persistence image of shape (n_dims, n_bins) or (n_bins,).
        include_raw: If True, include flattened image in features under 'raw'.
            Default False to reduce feature dimensionality.

    Returns:
        Dictionary containing:
            - 'mean': Mean pixel intensity
            - 'std': Standard deviation of intensities
            - 'max': Maximum intensity
            - 'sum': Total intensity (sum of all pixels)
            - 'p50', 'p75', 'p90', 'p95': Intensity percentiles
            - 'raw': Flattened image (if include_raw=True)

    Examples:
        >>> image = compute_persistence_image(diagram)
        >>> features = extract_image_features(image)
        >>> print(f"Mean intensity: {features['mean']:.4f}")
        >>> # For ML with raw image
        >>> features_with_raw = extract_image_features(image, include_raw=True)
        >>> raw_vector = features_with_raw['raw']

    Notes:
        Summary statistics capture global image properties and are typically
        more robust than raw pixel values for small sample sizes. For large
        datasets, including raw pixels may improve model performance.
    """
    image = np.asarray(image, dtype=np.float64)

    if image.size == 0:
        features = {
            "mean": 0.0,
            "std": 0.0,
            "max": 0.0,
            "sum": 0.0,
            "p50": 0.0,
            "p75": 0.0,
            "p90": 0.0,
            "p95": 0.0,
        }
        if include_raw:
            features["raw"] = np.array([])
        return features

    # Flatten to 1D for statistics
    flat = image.ravel()

    # Compute summary statistics
    features = {
        "mean": float(np.mean(flat)),
        "std": float(np.std(flat)),
        "max": float(np.max(flat)),
        "sum": float(np.sum(flat)),
        "p50": float(np.percentile(flat, 50)),
        "p75": float(np.percentile(flat, 75)),
        "p90": float(np.percentile(flat, 90)),
        "p95": float(np.percentile(flat, 95)),
    }

    # Optionally include raw flattened image
    if include_raw:
        features["raw"] = flat

    return features


def compute_multiscale_persistence_images(
    diagram: PersistenceDiagram,
    resolutions: list[tuple[int, int]] | None = None,
    sigma: float | None = None,
    weight_function: str | None = "linear",
) -> dict[str, PersistenceImageArray]:
    """
    Compute persistence images at multiple resolutions for multi-scale analysis.

    Multi-scale representations can capture both coarse and fine topological
    structure, improving robustness to resolution parameter selection.

    Args:
        diagram: Persistence diagram of shape (n_features, 3).
        resolutions: List of (n_bins_x, n_bins_y) tuples. If None, uses
            default scales: [(20, 20), (50, 50), (100, 100)].
        sigma: Gaussian kernel bandwidth (shared across scales).
        weight_function: Weighting scheme ('linear', 'persistence', or None).

    Returns:
        Dictionary with resolution tuple keys and image arrays as values.
        Example: {(20, 20): array(...), (50, 50): array(...), ...}

    Examples:
        >>> multiscale_images = compute_multiscale_persistence_images(diagram)
        >>> for resolution, image in multiscale_images.items():
        ...     print(f"Resolution {resolution}: shape {image.shape}")

    Notes:
        Multi-scale analysis is particularly useful when optimal resolution
        is unknown or when robustness to parameter choice is desired.
    """
    if resolutions is None:
        resolutions = [(20, 20), (50, 50), (100, 100)]

    multiscale_images = {}

    for resolution in resolutions:
        try:
            image = compute_persistence_image(
                diagram,
                resolution=resolution,
                sigma=sigma,
                weight_function=weight_function,
            )
            multiscale_images[resolution] = image
        except ValueError as e:
            logger.warning(
                "Could not compute image at resolution %s: %s", resolution, e
            )
            # Create zero image
            n_bins = resolution[0] * resolution[1]
            multiscale_images[resolution] = np.zeros((1, n_bins))

    return multiscale_images


def persistence_amplitude(
    diagram: PersistenceDiagram,
    dimension: int | None = None,
    metric: str = "wasserstein",
    p: float = 2.0,
) -> float:
    """
    Compute persistence amplitude (distance from empty diagram).

    Persistence amplitude measures how far a persistence diagram is from
    the trivial (empty) diagram, quantifying the overall significance of
    topological features. This is equivalent to computing the Wasserstein
    or bottleneck distance between the diagram and an empty diagram.

    Args:
        diagram: Persistence diagram of shape (n_features, 3).
        dimension: If specified, only include features of this dimension.
        metric: Distance metric to use:
            - 'wasserstein': Wasserstein p-distance (default)
            - 'bottleneck': Bottleneck distance (infinity norm)
        p: Order of Wasserstein distance. Default 2.0 (W_2 distance).

    Returns:
        Amplitude value (float >= 0). Higher values indicate more significant
        topological features.

    Examples:
        >>> amplitude = persistence_amplitude(
        ...     diagram, dimension=1, metric='wasserstein'
        ... )
        >>> print(f"H1 amplitude: {amplitude:.4f}")
        >>> # Empty diagram has zero amplitude
        >>> empty = np.array([]).reshape(0, 3)
        >>> assert persistence_amplitude(empty) == 0.0

    Notes:
        For Wasserstein distance, amplitude is sum of (persistence/2)^p raised to 1/p.
        For bottleneck distance, amplitude is max(persistence/2).
        The factor of 2 comes from the distance to the diagonal in birth-death space.

    References:
        Kerber, M., Morozov, D., & Nigmetov, A. (2017). Geometry helps to
            compare persistence diagrams. ACM Journal of Experimental Algorithmics.
    """
    diagram = np.asarray(diagram, dtype=np.float64)

    if diagram.size == 0:
        return 0.0

    # Filter by dimension if specified
    if dimension is not None:
        diagram = diagram[diagram[:, 2] == dimension]

    # Filter infinite values
    finite_mask = np.isfinite(diagram[:, 1])
    diagram = diagram[finite_mask]

    if len(diagram) == 0:
        return 0.0

    # Compute lifetimes (persistence values)
    lifetimes = diagram[:, 1] - diagram[:, 0]
    lifetimes = lifetimes[lifetimes > 0]

    if len(lifetimes) == 0:
        return 0.0

    # Amplitude is distance from diagonal
    # Each point (b, d) has distance (d-b)/2 to diagonal
    distances = lifetimes / 2.0

    if metric == "wasserstein":
        # W_p distance: (Σ dist^p)^(1/p)
        amplitude = float((np.sum(distances**p)) ** (1 / p))
    elif metric == "bottleneck":
        # Bottleneck distance: max dist
        amplitude = float(np.max(distances))
    else:
        raise ValueError(
            f"Unknown metric '{metric}'. Use 'wasserstein' or 'bottleneck'"
        )

    return amplitude


def betti_curve_statistics(
    diagram: PersistenceDiagram,
    dimension: int,
    n_bins: int = 100,
) -> dict[str, float]:
    """
    Compute statistical summaries of Betti curve.

    Extracts key features from the Betti curve β_k(ε), which tracks the
    number of k-dimensional topological features as a function of filtration
    parameter ε.

    Args:
        diagram: Persistence diagram of shape (n_features, 3).
        dimension: Homology dimension to analyze.
        n_bins: Number of filtration samples for curve computation.

    Returns:
        Dictionary containing:
            - 'max_betti': Maximum Betti number (peak)
            - 'mean_betti': Mean Betti number (temporal average)
            - 'max_betti_location': Filtration value where max occurs
            - 'area_under_curve': Integrated Betti number (sum over filtration)

    Examples:
        >>> stats = betti_curve_statistics(diagram, dimension=1)
        >>> print(f"Peak H1 features: {stats['max_betti']}")
        >>> print(f"Average H1 features: {stats['mean_betti']:.2f}")

    Notes:
        These statistics capture the temporal evolution of topological features,
        useful for understanding when features appear and disappear during
        filtration.
    """
    # Compute Betti curve
    filtration, betti = betti_curve(diagram, dimension, n_bins=n_bins)

    if len(betti) == 0:
        return {
            "max_betti": 0.0,
            "mean_betti": 0.0,
            "max_betti_location": 0.0,
            "area_under_curve": 0.0,
        }

    # Find maximum Betti number and its location
    max_betti = int(np.max(betti))
    max_idx = int(np.argmax(betti))
    max_location = float(filtration[max_idx])

    # Mean Betti number (average over filtration)
    mean_betti = float(np.mean(betti))

    # Area under curve (trapezoidal integration)
    # This represents the total "lifetime" of features weighted by count
    area = float(np.trapz(betti, filtration))

    return {
        "max_betti": float(max_betti),
        "mean_betti": mean_betti,
        "max_betti_location": max_location,
        "area_under_curve": area,
    }


def extract_entropy_betti_features(
    diagram: PersistenceDiagram,
    dimensions: tuple[int, ...] | None = None,
) -> dict[str, float]:
    """
    Extract comprehensive entropy, Betti, and amplitude features.

    Convenience function that computes all entropy-based and Betti curve
    features for specified homology dimensions, providing a complete
    feature dictionary for ML pipelines.

    Args:
        diagram: Persistence diagram of shape (n_features, 3).
        dimensions: Tuple of dimensions to analyze. If None, uses all
            dimensions present in diagram (typically (0, 1)).

    Returns:
        Dictionary containing features for each dimension:
            - 'entropy_H{k}': Persistence entropy for dimension k
            - 'amplitude_H{k}': Persistence amplitude (Wasserstein) for dimension k
            - 'total_persistence_H{k}_p1': Sum of lifetimes for dimension k
            - 'total_persistence_H{k}_p2': Sum of squared lifetimes for dimension k
            - 'max_betti_H{k}': Maximum Betti number for dimension k
            - 'mean_betti_H{k}': Mean Betti number for dimension k
            - 'betti_area_H{k}': Area under Betti curve for dimension k

    Examples:
        >>> features = extract_entropy_betti_features(diagram)
        >>> print(f"H1 entropy: {features['entropy_H1']:.4f}")
        >>> print(f"H1 amplitude: {features['amplitude_H1']:.4f}")
        >>> # Use in ML pipeline
        >>> feature_vector = np.array(list(features.values()))

    Notes:
        This function provides a comprehensive set of statistics that
        complement landscape and image features. Entropy and amplitude
        capture global diagram properties, while Betti curves track
        temporal evolution of features.
    """
    diagram = np.asarray(diagram, dtype=np.float64)

    # Determine dimensions to analyze
    if dimensions is None:
        if diagram.size > 0:
            dimensions = tuple(sorted(set(diagram[:, 2].astype(int))))
        else:
            dimensions = (0, 1)  # Default dimensions

    features = {}

    for dim in dimensions:
        dim_key = f"H{dim}"

        # Filter diagram to this dimension
        dim_diagram = diagram[diagram[:, 2] == dim] if diagram.size > 0 else diagram

        try:
            # Entropy
            entropy = persistence_entropy(dim_diagram)
            features[f"entropy_{dim_key}"] = entropy

            # Amplitude (Wasserstein distance)
            amplitude = persistence_amplitude(
                dim_diagram, dimension=dim, metric="wasserstein"
            )
            features[f"amplitude_{dim_key}"] = amplitude

            # Total persistence (p=1 and p=2)
            tp1 = total_persistence(dim_diagram, dimension=dim, p=1.0)
            tp2 = total_persistence(dim_diagram, dimension=dim, p=2.0)
            features[f"total_persistence_{dim_key}_p1"] = tp1
            features[f"total_persistence_{dim_key}_p2"] = tp2

            # Betti curve statistics
            betti_stats = betti_curve_statistics(diagram, dimension=dim)
            features[f"max_betti_{dim_key}"] = betti_stats["max_betti"]
            features[f"mean_betti_{dim_key}"] = betti_stats["mean_betti"]
            features[f"betti_area_{dim_key}"] = betti_stats["area_under_curve"]

        except (ValueError, Exception) as e:
            # Handle edge cases gracefully
            logger.warning("Could not extract features for %s: %s", dim_key, e)
            features[f"entropy_{dim_key}"] = 0.0
            features[f"amplitude_{dim_key}"] = 0.0
            features[f"total_persistence_{dim_key}_p1"] = 0.0
            features[f"total_persistence_{dim_key}_p2"] = 0.0
            features[f"max_betti_{dim_key}"] = 0.0
            features[f"mean_betti_{dim_key}"] = 0.0
            features[f"betti_area_{dim_key}"] = 0.0

    return features
