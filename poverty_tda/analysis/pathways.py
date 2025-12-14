"""
Integral line computation and gateway LSOA identification.

This module provides utilities for computing gradient flow paths from LSOAs
to their eventual poverty trap basins, and identifying "gateway" LSOAs as
high-impact intervention targets.

Integral Lines (Flow Paths):
    - Follow gradient descent from any point to eventual minimum
    - Show how mobility outcomes "flow" through the landscape
    - Connect LSOAs to their destination trap basins

Gateway LSOAs:
    - LSOAs whose flow paths cross separatrices (basin boundaries)
    - Intervention targets: improving these can redirect flows
    - High-impact gateways affect many downstream LSOAs

Integration:
    - mobility_surface.py: Provides scalar field for gradient computation
    - trap_identification.py: Basin properties and trap scores
    - barriers.py: Separatrices defining basin boundaries
    - census_shapes.py: LSOA centroids as starting points

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from numpy.typing import NDArray
from shapely.geometry import LineString

logger = logging.getLogger(__name__)

# CRS constants
CRS_BRITISH_NATIONAL_GRID = "EPSG:27700"

# Integration parameters
DEFAULT_MAX_STEPS = 1000
DEFAULT_STEP_SIZE = 0.1  # Fraction of grid spacing
CONVERGENCE_THRESHOLD = 1e-6


@dataclass
class IntegralLine:
    """A gradient flow path (integral line) from start to destination.

    Attributes:
        line_id: Unique identifier.
        start_point: (x, y) starting coordinates.
        end_point: (x, y) ending coordinates (minimum).
        path: Array of (x, y) coordinates along the path.
        values: Scalar values along the path.
        destination_basin_id: ID of basin this line flows to.
        converged: Whether line reached a minimum (True) or max_steps (False).
        n_steps: Number of integration steps taken.
    """

    line_id: int
    start_point: tuple[float, float]
    end_point: tuple[float, float]
    path: NDArray[np.float64]
    values: NDArray[np.float64] | None = None
    destination_basin_id: int | None = None
    converged: bool = True
    n_steps: int = 0

    @property
    def path_length(self) -> float:
        """Compute total path length in coordinate units."""
        if len(self.path) < 2:
            return 0.0
        segments = np.diff(self.path, axis=0)
        lengths = np.sqrt(np.sum(segments**2, axis=1))
        return float(np.sum(lengths))


@dataclass
class GatewayLSOA:
    """A gateway LSOA whose flow path crosses a basin boundary.

    Gateway LSOAs are intervention targets: improving them can redirect
    population flows away from poverty traps.

    Attributes:
        lsoa_code: LSOA 2021 code.
        lad_name: Local Authority District name.
        region_name: Region name.
        flow_path: Integral line from this LSOA.
        barrier_crossed: The separatrix this flow path crosses.
        crossing_point: (x, y) where flow path crosses separatrix.
        source_basin_id: Basin ID before crossing.
        destination_basin_id: Basin ID after crossing (final destination).
        population: Population in this LSOA.
        current_mobility: Current mobility value.
        impact_score: Intervention impact score (higher = higher priority).
    """

    lsoa_code: str
    lad_name: str | None = None
    region_name: str | None = None
    flow_path: IntegralLine | None = None
    barrier_crossed: Any = None  # BarrierProperties from barriers.py
    crossing_point: tuple[float, float] | None = None
    source_basin_id: int | None = None
    destination_basin_id: int | None = None
    population: int = 0
    current_mobility: float = 0.0
    impact_score: float = 0.0


# =============================================================================
# GRADIENT FIELD COMPUTATION
# =============================================================================


def compute_gradient_field(
    surface_data: dict[str, Any],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """
    Compute discrete gradient field from mobility surface.

    Uses numpy gradient to compute partial derivatives with respect to
    x and y coordinates.

    Args:
        surface_data: Dictionary with:
            - 'scalar_field': 2D array of mobility values (shape: ny × nx)
            - 'x_coords': 1D array of x coordinates (length: nx)
            - 'y_coords': 1D array of y coordinates (length: ny)

    Returns:
        Tuple of (grad_x, grad_y):
        - grad_x: 2D array of ∂f/∂x (shape: ny × nx)
        - grad_y: 2D array of ∂f/∂y (shape: ny × nx)

    Example:
        >>> grad_x, grad_y = compute_gradient_field(surface_dict)
        >>> # Gradient descent direction: -grad
    """
    scalar_field = surface_data["scalar_field"]
    x_coords = surface_data["x_coords"]
    y_coords = surface_data["y_coords"]

    # Compute grid spacing
    dx = float(x_coords[1] - x_coords[0]) if len(x_coords) > 1 else 1.0
    dy = float(y_coords[1] - y_coords[0]) if len(y_coords) > 1 else 1.0

    # Compute gradients using numpy
    # gradient returns [df/dy, df/dx] for 2D arrays
    grad_y, grad_x = np.gradient(scalar_field, dy, dx)

    return grad_x, grad_y


# =============================================================================
# INTEGRAL LINE COMPUTATION
# =============================================================================


def trace_integral_line(
    start_point: tuple[float, float],
    gradient_field: tuple[NDArray[np.float64], NDArray[np.float64]],
    surface_data: dict[str, Any],
    max_steps: int = DEFAULT_MAX_STEPS,
    step_size: float = DEFAULT_STEP_SIZE,
) -> IntegralLine:
    """
    Trace integral line (gradient descent path) from start point.

    Follows negative gradient to reach local minimum. Uses Euler integration
    with adaptive termination when gradient magnitude falls below threshold.

    Args:
        start_point: (x, y) starting coordinates in surface CRS.
        gradient_field: Tuple of (grad_x, grad_y) arrays from compute_gradient_field.
        surface_data: Dictionary with scalar_field, x_coords, y_coords.
        max_steps: Maximum integration steps (safety limit).
        step_size: Step size as fraction of grid spacing.

    Returns:
        IntegralLine with path from start to minimum.

    Example:
        >>> line = trace_integral_line((100.0, 200.0), grad_field, surface_dict)
        >>> print(f"Reached minimum at {line.end_point}")
    """
    grad_x, grad_y = gradient_field
    scalar_field = surface_data["scalar_field"]
    x_coords = surface_data["x_coords"]
    y_coords = surface_data["y_coords"]

    # Grid parameters
    x_min, x_max = x_coords[0], x_coords[-1]
    y_min, y_max = y_coords[0], y_coords[-1]
    nx, ny = len(x_coords), len(y_coords)
    dx = (x_max - x_min) / (nx - 1) if nx > 1 else 1.0
    dy = (y_max - y_min) / (ny - 1) if ny > 1 else 1.0

    # Integration step size in coordinate units
    h = step_size * min(dx, dy)

    # Initialize path
    path = [start_point]
    values = []
    current = np.array(start_point, dtype=np.float64)

    # Helper function to interpolate gradient at arbitrary point
    def get_gradient_at_point(x: float, y: float) -> tuple[float, float]:
        """Bilinear interpolation of gradient at (x, y)."""
        # Clamp to grid bounds
        x = np.clip(x, x_min, x_max)
        y = np.clip(y, y_min, y_max)

        # Find grid indices
        i = int((x - x_min) / dx)
        j = int((y - y_min) / dy)
        i = np.clip(i, 0, nx - 2)
        j = np.clip(j, 0, ny - 2)

        # Bilinear interpolation weights
        fx = (x - x_coords[i]) / dx
        fy = (y - y_coords[j]) / dy

        # Interpolate grad_x
        gx = (
            (1 - fx) * (1 - fy) * grad_x[j, i]
            + fx * (1 - fy) * grad_x[j, i + 1]
            + (1 - fx) * fy * grad_x[j + 1, i]
            + fx * fy * grad_x[j + 1, i + 1]
        )

        # Interpolate grad_y
        gy = (
            (1 - fx) * (1 - fy) * grad_y[j, i]
            + fx * (1 - fy) * grad_y[j, i + 1]
            + (1 - fx) * fy * grad_y[j + 1, i]
            + fx * fy * grad_y[j + 1, i + 1]
        )

        return float(gx), float(gy)

    # Helper function to get scalar value at point
    def get_value_at_point(x: float, y: float) -> float:
        """Bilinear interpolation of scalar at (x, y)."""
        x = np.clip(x, x_min, x_max)
        y = np.clip(y, y_min, y_max)

        i = int((x - x_min) / dx)
        j = int((y - y_min) / dy)
        i = np.clip(i, 0, nx - 2)
        j = np.clip(j, 0, ny - 2)

        fx = (x - x_coords[i]) / dx
        fy = (y - y_coords[j]) / dy

        val = (
            (1 - fx) * (1 - fy) * scalar_field[j, i]
            + fx * (1 - fy) * scalar_field[j, i + 1]
            + (1 - fx) * fy * scalar_field[j + 1, i]
            + fx * fy * scalar_field[j + 1, i + 1]
        )

        return float(val)

    # Integrate using Euler method with gradient descent
    converged = False
    for step in range(max_steps):
        # Get gradient at current point
        gx, gy = get_gradient_at_point(current[0], current[1])
        grad_magnitude = np.sqrt(gx**2 + gy**2)

        # Check convergence
        if grad_magnitude < CONVERGENCE_THRESHOLD:
            converged = True
            break

        # Gradient descent: move in -gradient direction
        current = current - h * np.array([gx, gy])

        # Clamp to grid bounds
        current[0] = np.clip(current[0], x_min, x_max)
        current[1] = np.clip(current[1], y_min, y_max)

        # Record path
        path.append(tuple(current))

        # Get value at current point
        val = get_value_at_point(current[0], current[1])
        values.append(val)

    # Create IntegralLine object
    path_array = np.array(path)
    values_array = np.array(values) if values else None

    line = IntegralLine(
        line_id=0,  # Will be set by caller
        start_point=start_point,
        end_point=tuple(current),
        path=path_array,
        values=values_array,
        converged=converged,
        n_steps=len(path) - 1,
    )

    return line


def compute_lsoa_flow_paths(
    lsoa_centroids: dict[str, tuple[float, float]],
    gradient_field: tuple[NDArray[np.float64], NDArray[np.float64]],
    surface_data: dict[str, Any],
    descending_manifold: NDArray[np.int32] | None = None,
) -> dict[str, IntegralLine]:
    """
    Compute flow paths from LSOA centroids to basin minima.

    Args:
        lsoa_centroids: Dictionary mapping LSOA_code → (x, y) centroid.
        gradient_field: Tuple of (grad_x, grad_y) from compute_gradient_field.
        surface_data: Dictionary with scalar_field, x_coords, y_coords.
        descending_manifold: Optional 2D array of basin IDs for destination lookup.

    Returns:
        Dictionary mapping LSOA_code → IntegralLine with destination basin.

    Example:
        >>> flow_paths = compute_lsoa_flow_paths(centroids, grad, surface_dict)
        >>> for lsoa, line in flow_paths.items():
        ...     print(f"{lsoa} flows to basin {line.destination_basin_id}")
    """
    flow_paths = {}

    x_coords = surface_data["x_coords"]
    y_coords = surface_data["y_coords"]
    x_min, x_max = x_coords[0], x_coords[-1]
    y_min, y_max = y_coords[0], y_coords[-1]
    nx, ny = len(x_coords), len(y_coords)

    for i, (lsoa_code, centroid) in enumerate(lsoa_centroids.items()):
        # Trace integral line
        line = trace_integral_line(centroid, gradient_field, surface_data)
        line.line_id = i

        # Determine destination basin from descending manifold
        if descending_manifold is not None:
            # Get basin ID at endpoint
            end_x, end_y = line.end_point
            # Convert to grid indices
            i_x = int((end_x - x_min) / (x_max - x_min) * (nx - 1))
            i_y = int((end_y - y_min) / (y_max - y_min) * (ny - 1))
            i_x = np.clip(i_x, 0, nx - 1)
            i_y = np.clip(i_y, 0, ny - 1)

            line.destination_basin_id = int(descending_manifold[i_y, i_x])

        flow_paths[lsoa_code] = line

    logger.info(f"Computed flow paths for {len(flow_paths)} LSOAs")
    return flow_paths


# =============================================================================
# GATEWAY LSOA IDENTIFICATION
# =============================================================================


def identify_gateway_lsoas(
    flow_paths: dict[str, IntegralLine],
    separatrices: list[Any],  # List of BarrierProperties
    lsoa_boundaries: gpd.GeoDataFrame | None = None,
    crossing_tolerance: float = 50.0,
) -> list[GatewayLSOA]:
    """
    Identify gateway LSOAs whose flow paths cross separatrices.

    Gateway LSOAs are intervention targets because improving them can
    redirect flows away from poverty traps.

    Args:
        flow_paths: Dictionary of LSOA_code → IntegralLine.
        separatrices: List of BarrierProperties with geometry (LineString).
        lsoa_boundaries: Optional GeoDataFrame with LSOA metadata.
        crossing_tolerance: Distance threshold for crossing detection (meters).

    Returns:
        List of GatewayLSOA objects for LSOAs that cross barriers.

    Example:
        >>> gateways = identify_gateway_lsoas(flow_paths, barriers)
        >>> print(f"Found {len(gateways)} gateway LSOAs")
    """
    gateways = []

    for lsoa_code, flow_line in flow_paths.items():
        # Create LineString from flow path
        if len(flow_line.path) < 2:
            continue

        flow_geometry = LineString(flow_line.path)

        # Check for intersections with separatrices
        for barrier in separatrices:
            if barrier.geometry is None:
                continue

            # Check if flow path intersects barrier
            if flow_geometry.intersects(barrier.geometry):
                # Find crossing point
                intersection = flow_geometry.intersection(barrier.geometry)

                # Extract crossing point (may be multipoint, take first)
                if intersection.is_empty:
                    continue

                if hasattr(intersection, "geoms"):
                    # MultiPoint or GeometryCollection
                    crossing_point = (intersection.geoms[0].x, intersection.geoms[0].y)
                else:
                    # Single Point
                    crossing_point = (intersection.x, intersection.y)

                # Get LSOA metadata if available
                lad_name = None
                region_name = None
                has_lsoa_code = (
                    lsoa_boundaries is not None
                    and "lsoa_code" in lsoa_boundaries.columns
                )
                if has_lsoa_code:
                    lsoa_row = lsoa_boundaries[
                        lsoa_boundaries["lsoa_code"] == lsoa_code
                    ]
                    if not lsoa_row.empty:
                        lad_name = lsoa_row.iloc[0].get("lad_name")
                        region_name = lsoa_row.iloc[0].get("region_name")

                # Create gateway LSOA
                gateway = GatewayLSOA(
                    lsoa_code=lsoa_code,
                    lad_name=lad_name,
                    region_name=region_name,
                    flow_path=flow_line,
                    barrier_crossed=barrier,
                    crossing_point=crossing_point,
                    destination_basin_id=flow_line.destination_basin_id,
                )

                gateways.append(gateway)
                break  # Only count first barrier crossing per LSOA

    logger.info(f"Identified {len(gateways)} gateway LSOAs")
    return gateways


# =============================================================================
# GATEWAY IMPACT SCORING
# =============================================================================


def score_gateway_impact(
    gateway: GatewayLSOA,
    basin_properties: dict[int, Any],  # basin_id → properties dict
    barrier_properties: dict[int, Any] | None = None,  # barrier_id → properties
) -> float:
    """
    Compute intervention impact score for a gateway LSOA.

    Impact based on:
    - Population in gateway LSOA (30%)
    - Destination trap severity (40%)
    - Barrier strength crossed (30%)

    Higher score = higher intervention priority.

    Args:
        gateway: GatewayLSOA object to score.
        basin_properties: Dictionary mapping basin_id → properties with:
            - 'trap_score': Trap severity score (0-1)
            - 'population': Basin population
        barrier_properties: Optional dictionary of barrier properties.

    Returns:
        Impact score (higher = higher priority).

    Example:
        >>> score = score_gateway_impact(gateway, basin_dict)
        >>> print(f"Impact score: {score:.3f}")
    """
    # Default components
    pop_score = 0.0
    trap_score = 0.0
    barrier_score = 0.0

    # Population component (normalized externally)
    if gateway.population > 0:
        pop_score = float(gateway.population)

    # Destination trap severity
    if gateway.destination_basin_id is not None:
        basin = basin_properties.get(gateway.destination_basin_id)
        if basin:
            trap_score = basin.get("trap_score", 0.0)

    # Barrier strength (persistence-based)
    if gateway.barrier_crossed is not None:
        barrier_score = gateway.barrier_crossed.persistence or 0.0

    # Weighted combination (will be normalized across all gateways)
    impact = 0.3 * pop_score + 0.4 * trap_score + 0.3 * barrier_score

    return float(impact)


def compute_gateway_impacts(
    gateways: list[GatewayLSOA],
    basin_properties: dict[int, Any],
    lsoa_data: gpd.GeoDataFrame | None = None,
) -> list[GatewayLSOA]:
    """
    Compute and normalize impact scores for all gateway LSOAs.

    Args:
        gateways: List of GatewayLSOA objects.
        basin_properties: Dictionary of basin properties.
        lsoa_data: Optional GeoDataFrame with population data.

    Returns:
        Updated list of gateways with impact_score populated.

    Example:
        >>> gateways = compute_gateway_impacts(gateways, basins, lsoa_gdf)
    """
    # Add population data from LSOA dataset
    if lsoa_data is not None and "population" in lsoa_data.columns:
        for gateway in gateways:
            lsoa_row = lsoa_data[lsoa_data["lsoa_code"] == gateway.lsoa_code]
            if not lsoa_row.empty:
                gateway.population = int(lsoa_row.iloc[0]["population"])

    # Compute raw impact scores
    raw_scores = []
    for gateway in gateways:
        score = score_gateway_impact(gateway, basin_properties)
        raw_scores.append(score)

    # Normalize scores to [0, 1]
    if raw_scores:
        min_score = min(raw_scores)
        max_score = max(raw_scores)
        if max_score > min_score:
            for i, gateway in enumerate(gateways):
                gateway.impact_score = (raw_scores[i] - min_score) / (
                    max_score - min_score
                )
        else:
            for gateway in gateways:
                gateway.impact_score = 0.5

    return gateways


# =============================================================================
# GATEWAY RANKING AND REPORTING
# =============================================================================


def rank_gateway_lsoas(
    gateways: list[GatewayLSOA],
    top_n: int = 50,
) -> list[GatewayLSOA]:
    """
    Rank gateway LSOAs by impact score.

    Args:
        gateways: List of GatewayLSOA objects with impact_score computed.
        top_n: Number of top gateways to return.

    Returns:
        List of top N gateways sorted by impact_score descending.

    Example:
        >>> top_gateways = rank_gateway_lsoas(gateways, top_n=20)
        >>> for i, gw in enumerate(top_gateways, 1):
        ...     print(f"{i}. {gw.lsoa_code}: {gw.impact_score:.3f}")
    """
    sorted_gateways = sorted(gateways, key=lambda g: g.impact_score, reverse=True)
    return sorted_gateways[:top_n]


def gateway_summary_report(
    ranked_gateways: list[GatewayLSOA],
) -> pd.DataFrame:
    """
    Generate summary report for ranked gateway LSOAs.

    Args:
        ranked_gateways: List of GatewayLSOA objects from rank_gateway_lsoas.

    Returns:
        DataFrame with columns:
        - rank: Rank (1 = highest priority)
        - lsoa_code: LSOA 2021 code
        - lad_name: Local Authority District
        - region: Region name
        - impact_score: Intervention impact score
        - population: LSOA population
        - destination_basin: Destination trap basin ID
        - barrier_id: Barrier crossed

    Example:
        >>> report = gateway_summary_report(top_gateways)
        >>> print(report.to_string())
    """
    if not ranked_gateways:
        return pd.DataFrame()

    rows = []
    for rank, gateway in enumerate(ranked_gateways, 1):
        row = {
            "rank": rank,
            "lsoa_code": gateway.lsoa_code,
            "lad_name": gateway.lad_name,
            "region": gateway.region_name,
            "impact_score": gateway.impact_score,
            "population": gateway.population,
            "destination_basin": gateway.destination_basin_id,
            "barrier_id": (
                gateway.barrier_crossed.barrier_id if gateway.barrier_crossed else None
            ),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    return df
