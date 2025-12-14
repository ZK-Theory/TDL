"""
Geospatial data processing utilities for UK poverty/mobility analysis.

This module provides:
- Spatial join utilities for LSOA/LAD data
- Interpolation methods for creating continuous surfaces (IDW, Kriging)
- VTK export for Topology ToolKit (TTK) / Morse-Smale analysis
- Memory-efficient chunked processing for large datasets

Integration with:
- Census boundaries (Task 1.5): load_lsoa_boundaries, get_lsoa_centroids
- IMD data (Task 1.6): load_imd_data, merge_with_boundaries
- Mobility proxy (Task 1.7): compute_mobility_proxy

Coordinate Reference Systems:
- Native CRS: EPSG:27700 (British National Grid) - meters
- For interpolation, use BNG to maintain distance accuracy

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import Literal

import geopandas as gpd
import numpy as np
from scipy.interpolate import griddata
from scipy.spatial import distance

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import pyvista as pv

    HAS_PYVISTA = True
except ImportError:
    HAS_PYVISTA = False
    logger.debug("pyvista not installed - VTK export will not be available")

try:
    from pykrige.ok import OrdinaryKriging

    HAS_PYKRIGE = True
except ImportError:
    HAS_PYKRIGE = False
    logger.debug("pykrige not installed - Kriging interpolation will use IDW fallback")


# Expected LAD count for England (~317) + Wales (~22)
EXPECTED_LAD_COUNT_ENGLAND = 317
EXPECTED_LAD_COUNT_WALES = 22

# Default grid resolution
DEFAULT_GRID_RESOLUTION = 500


# =============================================================================
# SPATIAL JOIN UTILITIES
# =============================================================================


def spatial_join_lsoa(
    points_gdf: gpd.GeoDataFrame,
    lsoa_gdf: gpd.GeoDataFrame,
    how: Literal["inner", "left", "right"] = "left",
    predicate: Literal["within", "intersects", "contains"] = "within",
) -> gpd.GeoDataFrame:
    """
    Join point data to LSOA polygons.

    Performs a spatial join to associate point features with the LSOA
    polygons they fall within. Useful for aggregating point data to LSOAs.

    Args:
        points_gdf: GeoDataFrame with point geometries to join.
        lsoa_gdf: GeoDataFrame with LSOA polygon boundaries.
        how: Join type ('inner', 'left', 'right').
        predicate: Spatial predicate ('within', 'intersects', 'contains').

    Returns:
        GeoDataFrame with points joined to LSOA attributes.

    Example:
        >>> from poverty_tda.data import load_lsoa_boundaries
        >>> lsoa = load_lsoa_boundaries()
        >>> points = gpd.GeoDataFrame(geometry=[Point(530000, 180000)])
        >>> joined = spatial_join_lsoa(points, lsoa)
    """
    if points_gdf.crs != lsoa_gdf.crs:
        logger.warning(
            f"CRS mismatch: points ({points_gdf.crs}) vs LSOA ({lsoa_gdf.crs}). "
            "Reprojecting points to LSOA CRS."
        )
        points_gdf = points_gdf.to_crs(lsoa_gdf.crs)

    logger.info(
        f"Spatial join: {len(points_gdf)} points to {len(lsoa_gdf)} LSOAs "
        f"(predicate={predicate}, how={how})"
    )

    result = gpd.sjoin(points_gdf, lsoa_gdf, how=how, predicate=predicate)

    logger.info(f"Joined result: {len(result)} records")
    return result


def aggregate_to_lad(
    lsoa_gdf: gpd.GeoDataFrame,
    value_column: str,
    agg_func: Literal["mean", "median", "sum", "std", "min", "max"] = "mean",
    lsoa_code_column: str = "LSOA21CD",
) -> gpd.GeoDataFrame:
    """
    Aggregate LSOA-level data to Local Authority District (LAD) level.

    LAD codes are derived from LSOA codes - the first 9 characters of
    LSOA21CD contain the LAD identifier (e.g., E01000001 → E09000001).

    For 2021 LSOAs, the LAD code prefix pattern is:
    - E09: London boroughs
    - E08: Metropolitan districts
    - E07: Non-metropolitan districts
    - E06: Unitary authorities
    - W06: Welsh unitary authorities

    Args:
        lsoa_gdf: GeoDataFrame with LSOA-level data and geometry.
        value_column: Column to aggregate.
        agg_func: Aggregation function ('mean', 'median', 'sum', 'std').
        lsoa_code_column: Column containing LSOA codes.

    Returns:
        GeoDataFrame with LAD-level aggregated values and dissolved geometries.

    Example:
        >>> lsoa = load_lsoa_boundaries()
        >>> lsoa['mobility'] = compute_mobility_proxy(...)['mobility_proxy']
        >>> lad = aggregate_to_lad(lsoa, 'mobility', agg_func='mean')
    """
    if lsoa_code_column not in lsoa_gdf.columns:
        raise ValueError(f"LSOA code column '{lsoa_code_column}' not found")

    if value_column not in lsoa_gdf.columns:
        raise ValueError(f"Value column '{value_column}' not found")

    # Extract LAD code from LSOA code
    # LSOA21CD format: E01000001 (9 chars for LAD + sequence)
    # LAD prefix is first 9 characters, but we need to map to actual LAD code
    # Use lookup from lad_code column if available, otherwise extract prefix
    if "lad_code" in lsoa_gdf.columns:
        lad_col = "lad_code"
    elif "LAD21CD" in lsoa_gdf.columns:
        lad_col = "LAD21CD"
    else:
        # Derive LAD from LSOA code prefix
        lsoa_gdf = lsoa_gdf.copy()
        lsoa_gdf["_lad_prefix"] = lsoa_gdf[lsoa_code_column].str[:9]
        lad_col = "_lad_prefix"
        logger.info("LAD code derived from LSOA code prefix (first 9 chars)")

    # Validate aggregation function
    valid_agg_funcs = {"mean", "median", "sum", "std", "min", "max"}

    if agg_func not in valid_agg_funcs:
        raise ValueError(f"Unsupported agg_func: {agg_func}")

    logger.info(f"Aggregating '{value_column}' to LAD level using {agg_func}")

    # Aggregate values using string names to avoid pandas FutureWarning
    agg_values = lsoa_gdf.groupby(lad_col)[value_column].agg(agg_func)
    lsoa_counts = lsoa_gdf.groupby(lad_col).size()

    # Dissolve geometries to LAD level
    lad_boundaries = get_lad_boundaries(lsoa_gdf, lsoa_code_column, lad_col)

    # Merge aggregated values with boundaries
    lad_boundaries[value_column] = lad_boundaries["lad_code"].map(agg_values)
    lad_boundaries["lsoa_count"] = lad_boundaries["lad_code"].map(lsoa_counts)

    logger.info(f"Aggregated to {len(lad_boundaries)} LADs")
    return lad_boundaries


def get_lad_boundaries(
    lsoa_gdf: gpd.GeoDataFrame,
    lsoa_code_column: str = "LSOA21CD",
    lad_code_column: str | None = None,
) -> gpd.GeoDataFrame:
    """
    Dissolve LSOA boundaries to Local Authority District (LAD) level.

    Groups LSOAs by LAD code and dissolves (merges) their geometries
    to create LAD-level boundary polygons.

    Args:
        lsoa_gdf: GeoDataFrame with LSOA boundaries.
        lsoa_code_column: Column containing LSOA codes.
        lad_code_column: Column containing LAD codes. If None, derives
            from LSOA code prefix.

    Returns:
        GeoDataFrame with dissolved LAD boundaries.

    Example:
        >>> lsoa = load_lsoa_boundaries()
        >>> lad = get_lad_boundaries(lsoa)
        >>> print(len(lad))  # ~317 for England
    """
    if lad_code_column is None:
        if "lad_code" in lsoa_gdf.columns:
            lad_code_column = "lad_code"
        elif "LAD21CD" in lsoa_gdf.columns:
            lad_code_column = "LAD21CD"
        else:
            # Derive from LSOA code prefix
            lsoa_gdf = lsoa_gdf.copy()
            lsoa_gdf["_lad_prefix"] = lsoa_gdf[lsoa_code_column].str[:9]
            lad_code_column = "_lad_prefix"

    logger.info(f"Dissolving LSOA boundaries to LAD level using '{lad_code_column}'")

    # Dissolve geometries
    lad_gdf = lsoa_gdf.dissolve(by=lad_code_column, as_index=False)

    # Rename code column for consistency
    if lad_code_column != "lad_code":
        lad_gdf = lad_gdf.rename(columns={lad_code_column: "lad_code"})

    # Keep only essential columns
    keep_cols = ["lad_code", "geometry"]
    if "lad_name" in lad_gdf.columns:
        keep_cols.insert(1, "lad_name")
    elif "LAD21NM" in lsoa_gdf.columns:
        # Get first LAD name for each code
        lad_names = lsoa_gdf.groupby(lad_code_column)["LAD21NM"].first()
        lad_gdf["lad_name"] = lad_gdf["lad_code"].map(lad_names)
        keep_cols.insert(1, "lad_name")

    available_cols = [c for c in keep_cols if c in lad_gdf.columns]
    lad_gdf = lad_gdf[available_cols]

    logger.info(f"Created {len(lad_gdf)} LAD boundaries")
    return lad_gdf


# =============================================================================
# SPATIAL INTERPOLATION
# =============================================================================


def interpolate_idw(
    points: gpd.GeoDataFrame,
    value_column: str,
    grid_resolution: int = DEFAULT_GRID_RESOLUTION,
    power: float = 2.0,
    bounds: tuple[float, float, float, float] | None = None,
) -> tuple[np.ndarray, dict]:
    """
    Inverse Distance Weighting (IDW) interpolation.

    Creates a regular grid covering the point extent and interpolates
    values using inverse distance weighting.

    Args:
        points: GeoDataFrame with point geometries and values.
        value_column: Column containing values to interpolate.
        grid_resolution: Number of cells in each dimension.
        power: Power parameter for IDW (higher = more local influence).
        bounds: Optional (x_min, y_min, x_max, y_max) for grid extent.
            If None, uses point extent with 5% buffer.

    Returns:
        Tuple of (grid_values, metadata):
        - grid_values: 2D numpy array of interpolated values
        - metadata: dict with x_min, x_max, y_min, y_max, resolution,
          cell_size_x, cell_size_y

    Example:
        >>> centroids = get_lsoa_centroids(load_lsoa_boundaries())
        >>> centroids['mobility'] = compute_mobility_proxy(...)['mobility_proxy']
        >>> grid, meta = interpolate_idw(centroids, 'mobility')
    """
    if value_column not in points.columns:
        raise ValueError(f"Value column '{value_column}' not found")

    # Extract coordinates and values
    coords = np.array([(geom.x, geom.y) for geom in points.geometry])
    values = points[value_column].values

    # Remove NaN values
    valid_mask = ~np.isnan(values)
    coords = coords[valid_mask]
    values = values[valid_mask]

    if len(coords) == 0:
        raise ValueError("No valid (non-NaN) values to interpolate")

    logger.info(
        f"IDW interpolation: {len(coords)} points → {grid_resolution}x{grid_resolution}"
    )

    # Determine grid bounds
    if bounds is None:
        x_min, y_min = coords.min(axis=0)
        x_max, y_max = coords.max(axis=0)
        # Add 5% buffer
        x_buffer = (x_max - x_min) * 0.05
        y_buffer = (y_max - y_min) * 0.05
        x_min -= x_buffer
        x_max += x_buffer
        y_min -= y_buffer
        y_max += y_buffer
    else:
        x_min, y_min, x_max, y_max = bounds

    # Create grid
    x_grid = np.linspace(x_min, x_max, grid_resolution)
    y_grid = np.linspace(y_min, y_max, grid_resolution)
    xx, yy = np.meshgrid(x_grid, y_grid)
    grid_points = np.column_stack([xx.ravel(), yy.ravel()])

    # Compute IDW
    distances = distance.cdist(grid_points, coords, metric="euclidean")

    # Avoid division by zero
    distances = np.maximum(distances, 1e-10)

    weights = 1.0 / (distances**power)
    weights_sum = weights.sum(axis=1, keepdims=True)
    weights_normalized = weights / weights_sum

    interpolated = (weights_normalized @ values).reshape(
        grid_resolution, grid_resolution
    )

    # Metadata
    metadata = {
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "resolution": grid_resolution,
        "cell_size_x": (x_max - x_min) / grid_resolution,
        "cell_size_y": (y_max - y_min) / grid_resolution,
        "method": "idw",
        "power": power,
        "n_points": len(coords),
    }

    logger.info(
        f"IDW complete: grid shape {interpolated.shape}, "
        f"value range [{interpolated.min():.3f}, {interpolated.max():.3f}]"
    )

    return interpolated, metadata


def interpolate_kriging(
    points: gpd.GeoDataFrame,
    value_column: str,
    grid_resolution: int = DEFAULT_GRID_RESOLUTION,
    variogram_model: str = "spherical",
    bounds: tuple[float, float, float, float] | None = None,
) -> tuple[np.ndarray, dict]:
    """
    Kriging interpolation for spatially correlated data.

    Uses Ordinary Kriging to interpolate values, which accounts for
    spatial correlation structure. Better for geospatial data but
    computationally more expensive than IDW.

    Args:
        points: GeoDataFrame with point geometries and values.
        value_column: Column containing values to interpolate.
        grid_resolution: Number of cells in each dimension.
        variogram_model: Variogram model ('spherical', 'exponential',
            'gaussian', 'linear').
        bounds: Optional (x_min, y_min, x_max, y_max) for grid extent.

    Returns:
        Tuple of (grid_values, metadata).

    Note:
        Requires pykrige package. Falls back to IDW if not installed.
        For large datasets (>10,000 points), consider using IDW or
        subsetting the data.

    Example:
        >>> grid, meta = interpolate_kriging(centroids, 'mobility',
        ...                                  variogram_model='spherical')
    """
    if not HAS_PYKRIGE:
        logger.warning(
            "pykrige not installed - falling back to IDW interpolation. "
            "Install with: pip install pykrige"
        )
        return interpolate_idw(points, value_column, grid_resolution, bounds=bounds)

    if value_column not in points.columns:
        raise ValueError(f"Value column '{value_column}' not found")

    # Extract coordinates and values
    coords = np.array([(geom.x, geom.y) for geom in points.geometry])
    values = points[value_column].values

    # Remove NaN values
    valid_mask = ~np.isnan(values)
    coords = coords[valid_mask]
    values = values[valid_mask]

    if len(coords) == 0:
        raise ValueError("No valid (non-NaN) values to interpolate")

    # Warn if dataset is large
    if len(coords) > 10000:
        logger.warning(
            f"Large dataset ({len(coords)} points) - Kriging may be slow. "
            "Consider using IDW or subsampling."
        )

    logger.info(
        f"Kriging interpolation: {len(coords)} points → "
        f"{grid_resolution}x{grid_resolution} (model={variogram_model})"
    )

    # Determine grid bounds
    if bounds is None:
        x_min, y_min = coords.min(axis=0)
        x_max, y_max = coords.max(axis=0)
        x_buffer = (x_max - x_min) * 0.05
        y_buffer = (y_max - y_min) * 0.05
        x_min -= x_buffer
        x_max += x_buffer
        y_min -= y_buffer
        y_max += y_buffer
    else:
        x_min, y_min, x_max, y_max = bounds

    # Create grid
    x_grid = np.linspace(x_min, x_max, grid_resolution)
    y_grid = np.linspace(y_min, y_max, grid_resolution)

    # Perform Kriging
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ok = OrdinaryKriging(
            coords[:, 0],
            coords[:, 1],
            values,
            variogram_model=variogram_model,
            verbose=False,
            enable_plotting=False,
        )
        interpolated, _ = ok.execute("grid", x_grid, y_grid)

    metadata = {
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "resolution": grid_resolution,
        "cell_size_x": (x_max - x_min) / grid_resolution,
        "cell_size_y": (y_max - y_min) / grid_resolution,
        "method": "kriging",
        "variogram_model": variogram_model,
        "n_points": len(coords),
    }

    logger.info(
        f"Kriging complete: grid shape {interpolated.shape}, "
        f"value range [{interpolated.min():.3f}, {interpolated.max():.3f}]"
    )

    return interpolated, metadata


def interpolate_scipy(
    points: gpd.GeoDataFrame,
    value_column: str,
    grid_resolution: int = DEFAULT_GRID_RESOLUTION,
    method: Literal["linear", "cubic", "nearest"] = "linear",
    bounds: tuple[float, float, float, float] | None = None,
) -> tuple[np.ndarray, dict]:
    """
    Scipy-based interpolation (linear, cubic, nearest).

    Uses scipy.interpolate.griddata for interpolation. Faster than
    Kriging but doesn't model spatial correlation.

    Args:
        points: GeoDataFrame with point geometries and values.
        value_column: Column containing values to interpolate.
        grid_resolution: Number of cells in each dimension.
        method: Interpolation method ('linear', 'cubic', 'nearest').
        bounds: Optional (x_min, y_min, x_max, y_max) for grid extent.

    Returns:
        Tuple of (grid_values, metadata).
    """
    if value_column not in points.columns:
        raise ValueError(f"Value column '{value_column}' not found")

    coords = np.array([(geom.x, geom.y) for geom in points.geometry])
    values = points[value_column].values

    valid_mask = ~np.isnan(values)
    coords = coords[valid_mask]
    values = values[valid_mask]

    if len(coords) == 0:
        raise ValueError("No valid (non-NaN) values to interpolate")

    logger.info(
        f"Scipy {method} interpolation: {len(coords)} points → "
        f"{grid_resolution}x{grid_resolution}"
    )

    if bounds is None:
        x_min, y_min = coords.min(axis=0)
        x_max, y_max = coords.max(axis=0)
        x_buffer = (x_max - x_min) * 0.05
        y_buffer = (y_max - y_min) * 0.05
        x_min -= x_buffer
        x_max += x_buffer
        y_min -= y_buffer
        y_max += y_buffer
    else:
        x_min, y_min, x_max, y_max = bounds

    x_grid = np.linspace(x_min, x_max, grid_resolution)
    y_grid = np.linspace(y_min, y_max, grid_resolution)
    xx, yy = np.meshgrid(x_grid, y_grid)

    interpolated = griddata(coords, values, (xx, yy), method=method)

    # Fill NaN values at edges with nearest neighbor
    if np.isnan(interpolated).any():
        nearest = griddata(coords, values, (xx, yy), method="nearest")
        interpolated = np.where(np.isnan(interpolated), nearest, interpolated)

    metadata = {
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "resolution": grid_resolution,
        "cell_size_x": (x_max - x_min) / grid_resolution,
        "cell_size_y": (y_max - y_min) / grid_resolution,
        "method": method,
        "n_points": len(coords),
    }

    return interpolated, metadata


def interpolate_to_grid(
    points: gpd.GeoDataFrame,
    value_column: str,
    method: Literal["idw", "kriging", "linear", "cubic", "nearest"] = "idw",
    grid_resolution: int = DEFAULT_GRID_RESOLUTION,
    **kwargs,
) -> tuple[np.ndarray, dict]:
    """
    Unified interface for spatial interpolation methods.

    Provides a single entry point for all interpolation methods with
    automatic fallback behavior.

    Args:
        points: GeoDataFrame with point geometries and values.
        value_column: Column containing values to interpolate.
        method: Interpolation method:
            - 'idw': Inverse Distance Weighting (fast, local)
            - 'kriging': Ordinary Kriging (accounts for spatial correlation)
            - 'linear': Linear interpolation (scipy)
            - 'cubic': Cubic interpolation (scipy)
            - 'nearest': Nearest neighbor (scipy)
        grid_resolution: Number of cells in each dimension.
        **kwargs: Additional arguments passed to specific interpolator.

    Returns:
        Tuple of (grid_values, metadata).

    Example:
        >>> centroids = get_lsoa_centroids(lsoa_gdf)
        >>> grid, meta = interpolate_to_grid(centroids, 'mobility', method='idw')
    """
    logger.info(f"Interpolating '{value_column}' using method='{method}'")

    if method == "idw":
        power = kwargs.pop("power", 2.0)
        bounds = kwargs.pop("bounds", None)
        return interpolate_idw(
            points, value_column, grid_resolution, power=power, bounds=bounds
        )

    elif method == "kriging":
        variogram_model = kwargs.pop("variogram_model", "spherical")
        bounds = kwargs.pop("bounds", None)
        return interpolate_kriging(
            points,
            value_column,
            grid_resolution,
            variogram_model=variogram_model,
            bounds=bounds,
        )

    elif method in ("linear", "cubic", "nearest"):
        bounds = kwargs.pop("bounds", None)
        return interpolate_scipy(
            points, value_column, grid_resolution, method=method, bounds=bounds
        )

    else:
        raise ValueError(
            f"Unknown interpolation method: {method}. "
            "Choose from: 'idw', 'kriging', 'linear', 'cubic', 'nearest'"
        )


# =============================================================================
# CHUNKED PROCESSING FOR MEMORY EFFICIENCY
# =============================================================================


def interpolate_chunked(
    points: gpd.GeoDataFrame,
    value_column: str,
    chunk_size: int = 100,
    overlap: int = 10,
    method: str = "idw",
    **kwargs,
) -> tuple[np.ndarray, dict]:
    """
    Process interpolation in spatial chunks for memory efficiency.

    Divides the study area into chunks, interpolates each separately,
    then stitches results together. Useful for very large datasets
    or limited memory situations.

    Args:
        points: GeoDataFrame with point geometries and values.
        value_column: Column containing values to interpolate.
        chunk_size: Size of each chunk in grid cells.
        overlap: Overlap between chunks in cells (for blending).
        method: Interpolation method ('idw', 'kriging', etc.).
        **kwargs: Additional arguments for interpolation.

    Returns:
        Tuple of (grid_values, metadata).

    Note:
        For ~35,000 LSOAs with default settings, this uses significantly
        less peak memory than processing all at once.
    """
    coords = np.array([(geom.x, geom.y) for geom in points.geometry])
    x_min, y_min = coords.min(axis=0)
    x_max, y_max = coords.max(axis=0)

    # Add buffer
    x_buffer = (x_max - x_min) * 0.05
    y_buffer = (y_max - y_min) * 0.05
    x_min -= x_buffer
    x_max += x_buffer
    y_min -= y_buffer
    y_max += y_buffer

    # Calculate full grid dimensions
    full_resolution = kwargs.get("grid_resolution", DEFAULT_GRID_RESOLUTION)
    cell_size_x = (x_max - x_min) / full_resolution
    cell_size_y = (y_max - y_min) / full_resolution

    # Calculate number of chunks needed
    n_chunks_x = int(np.ceil(full_resolution / (chunk_size - overlap)))
    n_chunks_y = int(np.ceil(full_resolution / (chunk_size - overlap)))

    logger.info(
        f"Chunked interpolation: {n_chunks_x}x{n_chunks_y} chunks, "
        f"chunk_size={chunk_size}, overlap={overlap}"
    )

    # Initialize output grid
    full_grid = np.zeros((full_resolution, full_resolution))
    weight_grid = np.zeros((full_resolution, full_resolution))

    for i in range(n_chunks_x):
        for j in range(n_chunks_y):
            # Calculate chunk bounds in grid coordinates
            start_x = i * (chunk_size - overlap)
            start_y = j * (chunk_size - overlap)
            end_x = min(start_x + chunk_size, full_resolution)
            end_y = min(start_y + chunk_size, full_resolution)

            # Convert to real coordinates
            chunk_x_min = x_min + start_x * cell_size_x
            chunk_x_max = x_min + end_x * cell_size_x
            chunk_y_min = y_min + start_y * cell_size_y
            chunk_y_max = y_min + end_y * cell_size_y

            # Filter points within chunk (with buffer)
            buffer = max(cell_size_x, cell_size_y) * overlap
            mask = (
                (coords[:, 0] >= chunk_x_min - buffer)
                & (coords[:, 0] <= chunk_x_max + buffer)
                & (coords[:, 1] >= chunk_y_min - buffer)
                & (coords[:, 1] <= chunk_y_max + buffer)
            )

            if mask.sum() < 3:
                continue

            chunk_points = points.iloc[mask].copy()
            chunk_resolution = end_x - start_x

            try:
                chunk_grid, _ = interpolate_to_grid(
                    chunk_points,
                    value_column,
                    method=method,
                    grid_resolution=chunk_resolution,
                    bounds=(chunk_x_min, chunk_y_min, chunk_x_max, chunk_y_max),
                )

                # Create weight matrix for blending (fade at edges)
                weight = np.ones((end_y - start_y, end_x - start_x))
                if overlap > 0:
                    fade = np.linspace(0, 1, overlap)
                    if i > 0:
                        weight[:, :overlap] *= fade
                    if j > 0:
                        weight[:overlap, :] *= fade[np.newaxis].T

                # Add to full grid
                full_grid[start_y:end_y, start_x:end_x] += chunk_grid * weight
                weight_grid[start_y:end_y, start_x:end_x] += weight

            except (ValueError, RuntimeError) as e:
                logger.warning(f"Chunk ({i},{j}) failed: {e}")
                continue

    # Normalize by weights
    weight_grid = np.maximum(weight_grid, 1e-10)
    full_grid /= weight_grid

    metadata = {
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "resolution": full_resolution,
        "cell_size_x": cell_size_x,
        "cell_size_y": cell_size_y,
        "method": f"chunked_{method}",
        "chunk_size": chunk_size,
        "overlap": overlap,
        "n_points": len(points),
    }

    return full_grid, metadata


# =============================================================================
# VTK EXPORT FOR TTK / MORSE-SMALE ANALYSIS
# =============================================================================


def export_to_vtk(
    grid: np.ndarray,
    metadata: dict,
    output_path: Path | str,
    scalar_name: str = "mobility",
) -> Path:
    """
    Export grid to VTK ImageData format for TTK analysis.

    Creates a VTK structured grid file compatible with the Topology
    ToolKit (TTK) for Morse-Smale complex computation.

    Args:
        grid: 2D numpy array of interpolated values.
        metadata: Grid metadata from interpolation (must contain
            x_min, x_max, y_min, y_max, resolution).
        output_path: Output file path (.vti or .vtk extension).
        scalar_name: Name for the scalar field in VTK file.

    Returns:
        Path to the created VTK file.

    Raises:
        ImportError: If pyvista is not installed.

    Example:
        >>> grid, meta = interpolate_to_grid(centroids, 'mobility')
        >>> vtk_path = export_to_vtk(grid, meta, 'mobility.vti')
    """
    if not HAS_PYVISTA:
        raise ImportError(
            "pyvista is required for VTK export. Install with: pip install pyvista"
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Exporting {grid.shape} grid to VTK: {output_path}")

    # Create VTK ImageData (UniformGrid in pyvista)
    nx, ny = grid.shape
    x_min = metadata["x_min"]
    x_max = metadata["x_max"]
    y_min = metadata["y_min"]
    y_max = metadata["y_max"]

    # Calculate spacing
    spacing_x = (x_max - x_min) / (nx - 1) if nx > 1 else 1.0
    spacing_y = (y_max - y_min) / (ny - 1) if ny > 1 else 1.0

    # Create uniform grid
    vtk_grid = pv.ImageData(
        dimensions=(nx, ny, 1),
        spacing=(spacing_x, spacing_y, 1.0),
        origin=(x_min, y_min, 0.0),
    )

    # Add scalar data
    # Flatten in Fortran order to match VTK convention
    vtk_grid.point_data[scalar_name] = grid.flatten(order="F")

    # Save
    vtk_grid.save(str(output_path))

    logger.info(f"Saved VTK file: {output_path} ({output_path.stat().st_size} bytes)")
    return output_path


def create_mobility_surface(
    lsoa_gdf: gpd.GeoDataFrame,
    mobility_column: str,
    output_path: Path | str,
    resolution: int = DEFAULT_GRID_RESOLUTION,
    method: str = "idw",
) -> Path:
    """
    End-to-end pipeline: LSOA data → centroids → interpolation → VTK.

    Convenience function that performs the complete workflow from
    LSOA polygon data to a VTK surface for TTK analysis.

    Args:
        lsoa_gdf: GeoDataFrame with LSOA boundaries and mobility data.
        mobility_column: Column containing mobility values.
        output_path: Output path for VTK file.
        resolution: Grid resolution (default 500x500).
        method: Interpolation method ('idw', 'kriging', etc.).

    Returns:
        Path to the created VTK file.

    Example:
        >>> from poverty_tda.data import load_lsoa_boundaries
        >>> lsoa = load_lsoa_boundaries()
        >>> lsoa['mobility'] = compute_mobility_proxy(imd_df)['mobility_proxy']
        >>> vtk_path = create_mobility_surface(lsoa, 'mobility', 'output.vti')
    """
    from poverty_tda.data.census_shapes import get_lsoa_centroids

    logger.info(f"Creating mobility surface: {len(lsoa_gdf)} LSOAs → VTK")

    # Step 1: Extract centroids
    centroids = get_lsoa_centroids(lsoa_gdf)

    # Copy mobility values to centroids
    if mobility_column not in centroids.columns:
        raise ValueError(
            f"Mobility column '{mobility_column}' not found in GeoDataFrame"
        )

    # Step 2: Interpolate
    grid, metadata = interpolate_to_grid(
        centroids, mobility_column, method=method, grid_resolution=resolution
    )

    # Step 3: Export to VTK
    output_path = export_to_vtk(
        grid, metadata, output_path, scalar_name=mobility_column
    )

    return output_path


def grid_to_geodataframe(
    grid: np.ndarray,
    metadata: dict,
    value_column: str = "value",
) -> gpd.GeoDataFrame:
    """
    Convert interpolated grid back to GeoDataFrame of points.

    Useful for joining interpolated values back to polygon data
    or for further spatial analysis.

    Args:
        grid: 2D numpy array of interpolated values.
        metadata: Grid metadata from interpolation.
        value_column: Column name for values in output.

    Returns:
        GeoDataFrame with point geometries and values.
    """
    from shapely.geometry import Point

    x_min = metadata["x_min"]
    x_max = metadata["x_max"]
    y_min = metadata["y_min"]
    y_max = metadata["y_max"]
    resolution = metadata["resolution"]

    x_coords = np.linspace(x_min, x_max, resolution)
    y_coords = np.linspace(y_min, y_max, resolution)

    points = []
    values = []

    for i, y in enumerate(y_coords):
        for j, x in enumerate(x_coords):
            points.append(Point(x, y))
            values.append(grid[i, j])

    gdf = gpd.GeoDataFrame(
        {value_column: values},
        geometry=points,
        crs="EPSG:27700",  # Assume British National Grid
    )

    return gdf
