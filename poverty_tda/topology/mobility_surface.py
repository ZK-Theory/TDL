"""
Mobility surface construction for TTK Morse-Smale analysis.

This module provides utilities for constructing continuous mobility surfaces
from LSOA point data using spatial interpolation, with VTK export for
Topology ToolKit (TTK) consumption.

Pipeline:
    1. Load LSOA boundaries → Extract centroids
    2. Load mobility proxy values per LSOA
    3. Interpolate to regular grid (scipy.griddata or IDW)
    4. Export to VTK format for TTK analysis

Integration:
    - census_shapes.py: get_lsoa_centroids() for point extraction
    - mobility_proxy.py: compute_mobility_proxy() for scalar values
    - geospatial.py: interpolate_idw(), export_to_vtk() for processing

Coordinate Reference System:
    - Uses EPSG:27700 (British National Grid) for metric grid spacing
    - England/Wales bounding box: ~82,000 x 656,000m to ~655,000 x 1,218,000m

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import geopandas as gpd

if TYPE_CHECKING:
    from poverty_tda.topology.morse_smale import MorseSmaleResult
import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import griddata

logger = logging.getLogger(__name__)

# Try to import optional pyvista
try:
    import pyvista as pv

    HAS_PYVISTA = True
except ImportError:
    HAS_PYVISTA = False
    logger.debug("pyvista not installed - VTK export will not be available")

# England/Wales bounding box in EPSG:27700 (British National Grid)
# Based on ONS LSOA 2021 data extent
ENGLAND_WALES_BOUNDS = {
    "x_min": 82672.0,
    "x_max": 655604.0,
    "y_min": 5337.0,
    "y_max": 657534.0,
}

# Default grid resolution (500x500 recommended for England/Wales)
DEFAULT_RESOLUTION = 500

# Memory warning threshold (approximately 8GB for 35000 points at 500x500)
MEMORY_WARNING_THRESHOLD = 10000

# CRS constants
CRS_BRITISH_NATIONAL_GRID = "EPSG:27700"


def create_mobility_grid(
    lsoa_gdf: gpd.GeoDataFrame,
    mobility_values: NDArray[np.float64] | None = None,
    mobility_column: str | None = None,
    resolution: int = DEFAULT_RESOLUTION,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], dict]:
    """
    Create a regular grid for mobility surface interpolation.

    Extracts LSOA centroids from the input GeoDataFrame and creates a
    regular grid covering the England/Wales bounding box for interpolation.

    Args:
        lsoa_gdf: GeoDataFrame with LSOA boundaries and geometry.
            Must have CRS set (preferably EPSG:27700).
        mobility_values: Optional array of mobility values per LSOA.
            Must match length of lsoa_gdf.
        mobility_column: Optional column name containing mobility values.
            Used if mobility_values is None.
        resolution: Number of grid cells in each dimension (default 500).

    Returns:
        Tuple of (centroids_xy, values, grid_xy, metadata):
        - centroids_xy: (N, 2) array of centroid coordinates
        - values: (N,) array of mobility values
        - grid_xy: (resolution, resolution, 2) meshgrid coordinates
        - metadata: dict with grid bounds, resolution, CRS info

    Raises:
        ValueError: If neither mobility_values nor mobility_column provided.
        ValueError: If mobility_values length doesn't match lsoa_gdf.
        ValueError: If CRS is not EPSG:27700 (will auto-transform with warning).

    Example:
        >>> lsoa = load_lsoa_boundaries()
        >>> mobility = compute_mobility_proxy(imd_df)
        >>> centroids, values, grid, meta = create_mobility_grid(
        ...     lsoa, mobility_values=mobility['mobility_proxy'].values
        ... )
    """
    # Validate inputs
    if mobility_values is None and mobility_column is None:
        raise ValueError(
            "Must provide either mobility_values array or mobility_column name"
        )

    if mobility_values is not None and len(mobility_values) != len(lsoa_gdf):
        raise ValueError(
            f"mobility_values length ({len(mobility_values)}) "
            f"doesn't match lsoa_gdf length ({len(lsoa_gdf)})"
        )

    if mobility_column is not None and mobility_column not in lsoa_gdf.columns:
        raise ValueError(f"Column '{mobility_column}' not found in lsoa_gdf")

    # Check and transform CRS if needed
    gdf = _ensure_british_national_grid(lsoa_gdf)

    # Extract values
    if mobility_values is not None:
        values = np.asarray(mobility_values, dtype=np.float64)
    else:
        values = gdf[mobility_column].values.astype(np.float64)

    # Memory warning for large datasets
    n_points = len(gdf)
    if n_points > MEMORY_WARNING_THRESHOLD:
        estimated_mem_mb = (n_points * resolution**2 * 8) / (1024**2)
        logger.warning(
            f"Large dataset: {n_points} points × {resolution}×{resolution} grid "
            f"may require ~{estimated_mem_mb:.0f} MB RAM for interpolation"
        )

    # Extract centroids
    logger.info(f"Extracting centroids from {n_points} LSOAs")
    centroids = gdf.geometry.centroid
    centroids_xy = np.column_stack([centroids.x, centroids.y])

    # Create grid covering England/Wales
    x_min = ENGLAND_WALES_BOUNDS["x_min"]
    x_max = ENGLAND_WALES_BOUNDS["x_max"]
    y_min = ENGLAND_WALES_BOUNDS["y_min"]
    y_max = ENGLAND_WALES_BOUNDS["y_max"]

    x_grid = np.linspace(x_min, x_max, resolution)
    y_grid = np.linspace(y_min, y_max, resolution)
    xx, yy = np.meshgrid(x_grid, y_grid)
    grid_xy = np.stack([xx, yy], axis=-1)

    # Metadata
    metadata = {
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "resolution": resolution,
        "cell_size_x": (x_max - x_min) / resolution,
        "cell_size_y": (y_max - y_min) / resolution,
        "crs": CRS_BRITISH_NATIONAL_GRID,
        "n_points": n_points,
    }

    logger.info(
        f"Created {resolution}×{resolution} grid covering England/Wales "
        f"({metadata['cell_size_x']:.1f}m × {metadata['cell_size_y']:.1f}m cells)"
    )

    return centroids_xy, values, grid_xy, metadata


def interpolate_surface(
    centroids: NDArray[np.float64],
    values: NDArray[np.float64],
    grid_x: NDArray[np.float64],
    grid_y: NDArray[np.float64],
    method: Literal["linear", "cubic", "nearest"] = "cubic",
    fill_value: float | None = None,
    use_idw_fallback: bool = True,
) -> NDArray[np.float64]:
    """
    Interpolate mobility values to a regular grid.

    Uses scipy.interpolate.griddata for interpolation with optional
    IDW fallback for extrapolation at grid edges.

    Args:
        centroids: (N, 2) array of point coordinates.
        values: (N,) array of mobility values at each point.
        grid_x: 2D array of x-coordinates (from meshgrid).
        grid_y: 2D array of y-coordinates (from meshgrid).
        method: Interpolation method:
            - 'linear': Linear interpolation (fast, may have edge NaNs)
            - 'cubic': Cubic spline interpolation (smoother, recommended)
            - 'nearest': Nearest neighbor (no NaNs but blocky)
        fill_value: Value to use for extrapolation. If None, uses
            nearest neighbor for edge filling.
        use_idw_fallback: If True, use IDW for NaN regions instead of
            simple fill_value (better edge behavior).

    Returns:
        2D array of interpolated values (same shape as grid_x/grid_y).

    Raises:
        ValueError: If inputs have mismatched shapes.
        ValueError: If all input values are NaN.

    Example:
        >>> surface = interpolate_surface(
        ...     centroids_xy, mobility_values, xx, yy, method='cubic'
        ... )
    """
    # Validate inputs
    if len(centroids) != len(values):
        raise ValueError(
            f"centroids length ({len(centroids)}) != values length ({len(values)})"
        )

    if grid_x.shape != grid_y.shape:
        raise ValueError(f"grid_x shape {grid_x.shape} != grid_y shape {grid_y.shape}")

    # Remove NaN values from input
    valid_mask = ~np.isnan(values)
    if not valid_mask.any():
        raise ValueError("All input values are NaN - cannot interpolate")

    n_valid = valid_mask.sum()
    if n_valid < len(values):
        logger.warning(
            f"Removed {len(values) - n_valid} NaN values from input "
            f"({n_valid} valid points remaining)"
        )

    coords = centroids[valid_mask]
    vals = values[valid_mask]

    logger.info(
        f"Interpolating {n_valid} points to {grid_x.shape[0]}×{grid_x.shape[1]} "
        f"grid using method='{method}'"
    )

    # Perform interpolation
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        surface = griddata(coords, vals, (grid_x, grid_y), method=method)

    # Handle NaN values at edges (extrapolation)
    nan_count = np.isnan(surface).sum()
    if nan_count > 0:
        nan_pct = 100 * nan_count / surface.size
        logger.info(f"Filling {nan_count} NaN values ({nan_pct:.1f}% of grid)")

        if use_idw_fallback and method != "nearest":
            # Use IDW for edge filling (better than constant)
            surface = _fill_nan_with_idw(surface, coords, vals, grid_x, grid_y)
        elif fill_value is not None:
            surface = np.where(np.isnan(surface), fill_value, surface)
        else:
            # Fall back to nearest neighbor
            nearest = griddata(coords, vals, (grid_x, grid_y), method="nearest")
            surface = np.where(np.isnan(surface), nearest, surface)

    # Validate output
    value_min, value_max = vals.min(), vals.max()
    surf_min, surf_max = np.nanmin(surface), np.nanmax(surface)
    logger.info(
        f"Interpolation complete: input range [{value_min:.4f}, {value_max:.4f}] "
        f"→ surface range [{surf_min:.4f}, {surf_max:.4f}]"
    )

    return surface


def _fill_nan_with_idw(
    surface: NDArray[np.float64],
    coords: NDArray[np.float64],
    values: NDArray[np.float64],
    grid_x: NDArray[np.float64],
    grid_y: NDArray[np.float64],
    power: float = 2.0,
) -> NDArray[np.float64]:
    """Fill NaN values in surface using inverse distance weighting."""
    nan_mask = np.isnan(surface)
    if not nan_mask.any():
        return surface

    # Get NaN positions
    nan_y, nan_x = np.where(nan_mask)
    nan_coords = np.column_stack([grid_x[nan_y, nan_x], grid_y[nan_y, nan_x]])

    # Compute IDW for NaN positions only
    from scipy.spatial import distance

    distances = distance.cdist(nan_coords, coords, metric="euclidean")
    distances = np.maximum(distances, 1e-10)  # Avoid division by zero

    weights = 1.0 / (distances**power)
    weights_normalized = weights / weights.sum(axis=1, keepdims=True)

    filled_values = weights_normalized @ values

    # Fill surface
    result = surface.copy()
    result[nan_y, nan_x] = filled_values

    return result


def export_mobility_vtk(
    grid_x: NDArray[np.float64],
    grid_y: NDArray[np.float64],
    surface_values: NDArray[np.float64],
    output_path: Path | str,
    scalar_name: str = "mobility",
) -> Path:
    """
    Export mobility surface to VTK format for TTK consumption.

    Creates a VTK ImageData (.vti) or StructuredGrid (.vts) file
    compatible with TTK Morse-Smale computation.

    Args:
        grid_x: 2D array of x-coordinates from meshgrid.
        grid_y: 2D array of y-coordinates from meshgrid.
        surface_values: 2D array of interpolated mobility values.
        output_path: Output file path. Use .vti for ImageData or
            .vts for StructuredGrid format.
        scalar_name: Name for the scalar field in VTK file (default "mobility").
            TTK will use this name to identify the scalar field.

    Returns:
        Path to the created VTK file.

    Raises:
        ImportError: If pyvista is not installed.
        ValueError: If input arrays have mismatched shapes.

    Example:
        >>> vtk_path = export_mobility_vtk(
        ...     xx, yy, surface, "mobility_surface.vti"
        ... )
    """
    # Validate inputs first (before checking pyvista)
    if grid_x.shape != grid_y.shape or grid_x.shape != surface_values.shape:
        raise ValueError(
            f"Shape mismatch: grid_x {grid_x.shape}, grid_y {grid_y.shape}, "
            f"surface_values {surface_values.shape}"
        )

    if not HAS_PYVISTA:
        raise ImportError(
            "pyvista is required for VTK export. Install with: pip install pyvista"
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ny, nx = surface_values.shape

    # Determine file format from extension
    suffix = output_path.suffix.lower()

    logger.info(f"Exporting {nx}×{ny} mobility surface to VTK: {output_path}")

    if suffix in (".vti", ".vtk"):
        # Create VTK ImageData (uniform grid) - preferred for TTK
        x_min, x_max = grid_x.min(), grid_x.max()
        y_min, y_max = grid_y.min(), grid_y.max()

        spacing_x = (x_max - x_min) / (nx - 1) if nx > 1 else 1.0
        spacing_y = (y_max - y_min) / (ny - 1) if ny > 1 else 1.0

        vtk_grid = pv.ImageData(
            dimensions=(nx, ny, 1),
            spacing=(spacing_x, spacing_y, 1.0),
            origin=(x_min, y_min, 0.0),
        )

        # Add scalar data (flatten in Fortran order for VTK)
        vtk_grid.point_data[scalar_name] = surface_values.flatten(order="F")

    elif suffix == ".vts":
        # Create VTK StructuredGrid - explicit point coordinates
        z = np.zeros_like(grid_x)
        points = np.column_stack(
            [
                grid_x.ravel(order="F"),
                grid_y.ravel(order="F"),
                z.ravel(order="F"),
            ]
        )

        vtk_grid = pv.StructuredGrid()
        vtk_grid.points = points
        vtk_grid.dimensions = (nx, ny, 1)
        vtk_grid.point_data[scalar_name] = surface_values.flatten(order="F")

    else:
        raise ValueError(f"Unsupported VTK format: {suffix}. Use .vti or .vts")

    # Save file
    vtk_grid.save(str(output_path))

    file_size = output_path.stat().st_size
    logger.info(
        f"Saved VTK file: {output_path.name} "
        f"({file_size / 1024:.1f} KB, {nx}×{ny} points, scalar='{scalar_name}')"
    )

    return output_path


def interpolate_chunked(
    centroids: NDArray[np.float64],
    values: NDArray[np.float64],
    grid_x: NDArray[np.float64],
    grid_y: NDArray[np.float64],
    chunk_size: int = 100,
    method: Literal["linear", "cubic", "nearest"] = "cubic",
    progress_callback: callable | None = None,
) -> NDArray[np.float64]:
    """
    Memory-efficient chunked interpolation for large datasets.

    Divides the grid into chunks and interpolates each separately,
    reducing peak memory usage for large datasets (~35,000 LSOAs).

    Args:
        centroids: (N, 2) array of point coordinates.
        values: (N,) array of mobility values.
        grid_x: 2D array of x-coordinates.
        grid_y: 2D array of y-coordinates.
        chunk_size: Size of each chunk in grid cells.
        method: Interpolation method ('linear', 'cubic', 'nearest').
        progress_callback: Optional callable(chunk_idx, total_chunks)
            for progress reporting.

    Returns:
        2D array of interpolated values.

    Note:
        This function uses more CPU time but less memory than
        interpolate_surface(). Use for systems with <8GB RAM.

    Example:
        >>> surface = interpolate_chunked(
        ...     centroids, values, xx, yy, chunk_size=100
        ... )
    """
    # Remove NaN values
    valid_mask = ~np.isnan(values)
    coords = centroids[valid_mask]
    vals = values[valid_mask]

    ny, nx = grid_x.shape
    surface = np.full((ny, nx), np.nan)

    # Calculate chunk grid
    n_chunks_x = int(np.ceil(nx / chunk_size))
    n_chunks_y = int(np.ceil(ny / chunk_size))
    total_chunks = n_chunks_x * n_chunks_y

    logger.info(
        f"Chunked interpolation: {n_chunks_x}×{n_chunks_y} chunks "
        f"(chunk_size={chunk_size})"
    )

    chunk_idx = 0
    for i in range(n_chunks_y):
        for j in range(n_chunks_x):
            # Chunk bounds
            y_start = i * chunk_size
            y_end = min((i + 1) * chunk_size, ny)
            x_start = j * chunk_size
            x_end = min((j + 1) * chunk_size, nx)

            chunk_x = grid_x[y_start:y_end, x_start:x_end]
            chunk_y = grid_y[y_start:y_end, x_start:x_end]

            # Get bounding box with buffer for points
            buffer = (
                chunk_size
                * 0.2
                * max(
                    (grid_x.max() - grid_x.min()) / nx,
                    (grid_y.max() - grid_y.min()) / ny,
                )
            )
            x_min, x_max = chunk_x.min() - buffer, chunk_x.max() + buffer
            y_min, y_max = chunk_y.min() - buffer, chunk_y.max() + buffer

            # Filter points to chunk region
            mask = (
                (coords[:, 0] >= x_min)
                & (coords[:, 0] <= x_max)
                & (coords[:, 1] >= y_min)
                & (coords[:, 1] <= y_max)
            )

            if mask.sum() >= 4:  # Need at least 4 points for cubic
                chunk_coords = coords[mask]
                chunk_vals = vals[mask]

                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        chunk_surface = griddata(
                            chunk_coords, chunk_vals, (chunk_x, chunk_y), method=method
                        )
                    surface[y_start:y_end, x_start:x_end] = chunk_surface
                except Exception as e:
                    logger.warning(f"Chunk ({i},{j}) failed: {e}")

            chunk_idx += 1
            if progress_callback:
                progress_callback(chunk_idx, total_chunks)

    # Fill remaining NaNs with nearest neighbor
    nan_count = np.isnan(surface).sum()
    if nan_count > 0:
        logger.info(f"Filling {nan_count} remaining NaN values with nearest neighbor")
        nearest = griddata(coords, vals, (grid_x, grid_y), method="nearest")
        surface = np.where(np.isnan(surface), nearest, surface)

    return surface


def _ensure_british_national_grid(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Ensure GeoDataFrame is in EPSG:27700 (British National Grid)."""
    if gdf.crs is None:
        logger.warning("No CRS set, assuming EPSG:27700 (British National Grid)")
        return gdf.set_crs(CRS_BRITISH_NATIONAL_GRID)

    if str(gdf.crs) != CRS_BRITISH_NATIONAL_GRID:
        logger.warning(
            f"CRS {gdf.crs} detected, transforming to EPSG:27700 "
            "for consistent metric grid spacing"
        )
        return gdf.to_crs(CRS_BRITISH_NATIONAL_GRID)

    return gdf


def build_mobility_surface(
    lsoa_gdf: gpd.GeoDataFrame,
    mobility_values: NDArray[np.float64] | None = None,
    mobility_column: str | None = None,
    output_path: Path | str | None = None,
    resolution: int = DEFAULT_RESOLUTION,
    method: Literal["linear", "cubic", "nearest"] = "cubic",
    use_chunked: bool = False,
    chunk_size: int = 100,
) -> tuple[NDArray[np.float64], dict, Path | None]:
    """
    End-to-end pipeline: LSOA data → interpolated surface → VTK export.

    Convenience function that performs the complete workflow from
    LSOA boundary data with mobility values to an exported VTK file.

    Args:
        lsoa_gdf: GeoDataFrame with LSOA boundaries.
        mobility_values: Array of mobility values per LSOA.
        mobility_column: Column name containing mobility values.
        output_path: Optional path for VTK export. If None, no file created.
        resolution: Grid resolution (default 500x500).
        method: Interpolation method ('linear', 'cubic', 'nearest').
        use_chunked: If True, use memory-efficient chunked interpolation.
        chunk_size: Chunk size for chunked interpolation.

    Returns:
        Tuple of (surface, metadata, vtk_path):
        - surface: 2D array of interpolated mobility values
        - metadata: dict with grid bounds, resolution, etc.
        - vtk_path: Path to VTK file (or None if output_path not provided)

    Example:
        >>> surface, meta, vtk = build_mobility_surface(
        ...     lsoa_gdf, mobility_values=mobility['mobility_proxy'].values,
        ...     output_path='mobility.vti', resolution=500
        ... )
    """
    logger.info(f"Building mobility surface: {len(lsoa_gdf)} LSOAs → VTK")

    # Step 1: Create grid
    centroids, values, grid_xy, metadata = create_mobility_grid(
        lsoa_gdf, mobility_values, mobility_column, resolution
    )

    grid_x = grid_xy[:, :, 0]
    grid_y = grid_xy[:, :, 1]

    # Step 2: Interpolate
    if use_chunked:
        surface = interpolate_chunked(
            centroids, values, grid_x, grid_y, chunk_size=chunk_size, method=method
        )
    else:
        surface = interpolate_surface(centroids, values, grid_x, grid_y, method=method)

    # Update metadata
    metadata["method"] = method
    metadata["value_min"] = float(np.nanmin(surface))
    metadata["value_max"] = float(np.nanmax(surface))

    # Step 3: Export to VTK (optional)
    vtk_path = None
    if output_path is not None:
        vtk_path = export_mobility_vtk(
            grid_x, grid_y, surface, output_path, scalar_name="mobility"
        )

    return surface, metadata, vtk_path


# =============================================================================
# MORSE-SMALE INTEGRATION
# =============================================================================


def analyze_mobility_topology(
    lsoa_gdf: gpd.GeoDataFrame,
    mobility_values: NDArray[np.float64] | None = None,
    mobility_column: str | None = None,
    output_path: Path | str | None = None,
    resolution: int = DEFAULT_RESOLUTION,
    method: Literal["linear", "cubic", "nearest"] = "cubic",
    persistence_threshold: float = 0.05,
    use_chunked: bool = False,
    chunk_size: int = 100,
) -> tuple[NDArray[np.float64], dict, "MorseSmaleResult"]:
    """
    Complete pipeline: LSOA data → mobility surface → Morse-Smale analysis.

    This is the main entry point for topological analysis of mobility
    landscapes. It combines surface construction with Morse-Smale complex
    computation to identify critical points (mobility hotspots and barriers).

    The Morse-Smale complex identifies:
    - **Maxima**: Areas of highest mobility (opportunity hotspots)
    - **Minima**: Areas of lowest mobility (mobility barriers/deprivation)
    - **Saddles**: Transition zones between regions of different mobility
    - **Separatrices**: Boundaries between mobility basins

    Args:
        lsoa_gdf: GeoDataFrame with LSOA boundaries (EPSG:27700).
        mobility_values: Array of mobility values per LSOA.
            Mutually exclusive with mobility_column.
        mobility_column: Column name containing mobility values.
            Mutually exclusive with mobility_values.
        output_path: Optional path for VTK export. If None, uses temp file.
        resolution: Grid resolution (default 500x500).
        method: Interpolation method ('linear', 'cubic', 'nearest').
        persistence_threshold: Fraction of scalar range for simplification.
            Higher values remove more noise. Range: 0.0 to 1.0.
            Default 0.05 (5% of range).
        use_chunked: If True, use memory-efficient chunked interpolation.
        chunk_size: Chunk size for chunked interpolation.

    Returns:
        Tuple of (surface, metadata, morse_smale_result):
        - surface: 2D array of interpolated mobility values
        - metadata: dict with grid bounds, resolution, critical point count
        - morse_smale_result: MorseSmaleResult with critical points

    Raises:
        FileNotFoundError: If TTK environment is not available.
        ValueError: If scalar field is invalid or parameters out of range.

    Example:
        >>> from poverty_tda.data import load_lsoa_boundaries
        >>> from poverty_tda.data import compute_mobility_proxy
        >>>
        >>> # Load data
        >>> lsoa_gdf = load_lsoa_boundaries()
        >>> mobility = compute_mobility_proxy(lsoa_gdf)
        >>>
        >>> # Full topological analysis
        >>> surface, meta, ms_result = analyze_mobility_topology(
        ...     lsoa_gdf,
        ...     mobility_values=mobility['mobility_proxy'].values,
        ...     resolution=500,
        ...     persistence_threshold=0.05,
        ... )
        >>>
        >>> # Inspect results
        >>> print(f"Found {ms_result.n_maxima} opportunity hotspots")
        >>> print(f"Found {ms_result.n_minima} mobility barriers")
        >>>
        >>> for m in ms_result.get_maxima():
        ...     print(f"Hotspot at ({m.position[0]:.0f}, {m.position[1]:.0f})")

    See Also:
        - build_mobility_surface: Surface construction without Morse-Smale
        - compute_morse_smale: Direct Morse-Smale computation on VTK file
        - simplify_topology: Post-hoc simplification of results
    """
    from poverty_tda.topology.morse_smale import (
        check_ttk_environment,
        compute_morse_smale,
    )

    # Verify TTK is available
    if not check_ttk_environment():
        raise FileNotFoundError(
            "TTK environment not available. Install with:\n"
            "  conda create -n ttk-env python=3.10\n"
            "  conda activate ttk-env\n"
            "  conda install -c conda-forge topologytoolkit"
        )

    # Determine VTK output path
    if output_path is None:
        import tempfile

        vtk_file = tempfile.NamedTemporaryFile(suffix=".vti", delete=False)
        vtk_path = Path(vtk_file.name)
        vtk_file.close()
        cleanup_vtk = True
    else:
        vtk_path = Path(output_path)
        cleanup_vtk = False

    try:
        # Step 1: Build mobility surface and export to VTK
        logger.info("Step 1/2: Building mobility surface...")
        surface, metadata, _ = build_mobility_surface(
            lsoa_gdf,
            mobility_values=mobility_values,
            mobility_column=mobility_column,
            output_path=vtk_path,
            resolution=resolution,
            method=method,
            use_chunked=use_chunked,
            chunk_size=chunk_size,
        )

        # Step 2: Compute Morse-Smale complex
        logger.info("Step 2/2: Computing Morse-Smale complex...")
        ms_result = compute_morse_smale(
            vtk_path,
            scalar_name="mobility",
            persistence_threshold=persistence_threshold,
            compute_ascending=True,
            compute_descending=True,
            compute_separatrices=True,
        )

        # Update metadata with topological information
        metadata["n_critical_points"] = len(ms_result.critical_points)
        metadata["n_maxima"] = ms_result.n_maxima
        metadata["n_minima"] = ms_result.n_minima
        metadata["n_saddles"] = ms_result.n_saddles
        metadata["persistence_threshold"] = persistence_threshold

        logger.info(
            f"Analysis complete: {ms_result.n_maxima} maxima, "
            f"{ms_result.n_minima} minima, {ms_result.n_saddles} saddles"
        )

        return surface, metadata, ms_result

    finally:
        # Cleanup temp file if needed
        if cleanup_vtk and vtk_path.exists():
            vtk_path.unlink()


def get_opportunity_hotspots(
    ms_result: "MorseSmaleResult",
    top_n: int | None = None,
) -> list[tuple[float, float, float]]:
    """
    Extract opportunity hotspots (maxima) from Morse-Smale result.

    Returns coordinates of local maxima in the mobility surface,
    which represent areas of high social mobility opportunity.

    Args:
        ms_result: MorseSmaleResult from analyze_mobility_topology.
        top_n: If provided, return only the top N hotspots by value.

    Returns:
        List of (x, y, mobility_value) tuples for each maximum.
        Sorted by value (highest first).

    Example:
        >>> surface, meta, ms_result = analyze_mobility_topology(...)
        >>> hotspots = get_opportunity_hotspots(ms_result, top_n=10)
        >>> for x, y, val in hotspots:
        ...     print(f"Hotspot at ({x:.0f}, {y:.0f}): mobility={val:.3f}")
    """
    maxima = ms_result.get_maxima()

    # Sort by value (highest first)
    maxima_sorted = sorted(maxima, key=lambda m: m.value, reverse=True)

    if top_n is not None:
        maxima_sorted = maxima_sorted[:top_n]

    return [(m.position[0], m.position[1], m.value) for m in maxima_sorted]


def get_mobility_barriers(
    ms_result: "MorseSmaleResult",
    top_n: int | None = None,
) -> list[tuple[float, float, float]]:
    """
    Extract mobility barriers (minima) from Morse-Smale result.

    Returns coordinates of local minima in the mobility surface,
    which represent areas of low social mobility (deprivation traps).

    Args:
        ms_result: MorseSmaleResult from analyze_mobility_topology.
        top_n: If provided, return only the top N barriers by severity
            (lowest value = most severe barrier).

    Returns:
        List of (x, y, mobility_value) tuples for each minimum.
        Sorted by value (lowest first = most severe).

    Example:
        >>> surface, meta, ms_result = analyze_mobility_topology(...)
        >>> barriers = get_mobility_barriers(ms_result, top_n=10)
        >>> for x, y, val in barriers:
        ...     print(f"Barrier at ({x:.0f}, {y:.0f}): mobility={val:.3f}")
    """
    minima = ms_result.get_minima()

    # Sort by value (lowest first = most severe barriers)
    minima_sorted = sorted(minima, key=lambda m: m.value)

    if top_n is not None:
        minima_sorted = minima_sorted[:top_n]

    return [(m.position[0], m.position[1], m.value) for m in minima_sorted]
