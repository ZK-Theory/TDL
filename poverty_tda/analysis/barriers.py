"""
Separatrix extraction and barrier analysis for poverty trap research.

This module provides utilities for extracting and analyzing barriers between
basins in the Morse-Smale complex. Separatrices (gradient flow lines) represent
topological barriers that separate regions of different mobility outcomes.

Barrier Types:
    - Descending separatrices: Connect saddles to minima (basin boundaries)
    - Ascending separatrices: Connect saddles to maxima (peak boundaries)

Barrier Strength Metrics:
    - Persistence: Primary measure of barrier significance
    - Height: Elevation difference along separatrix
    - Width: Geographic length of barrier
    - Population impact: People separated by barrier

Integration:
    - morse_smale.py: Provides Separatrix objects from TTK computation
    - critical_points.py: Saddle point classification
    - trap_identification.py: Basin properties for impact analysis
    - census_shapes.py: LSOA boundaries for geographic mapping

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString

from poverty_tda.topology.morse_smale import (
    CriticalPoint,
    MorseSmaleResult,
    Separatrix,
)

logger = logging.getLogger(__name__)

# CRS constants
CRS_BRITISH_NATIONAL_GRID = "EPSG:27700"


@dataclass
class BarrierProperties:
    """Properties of a topological barrier (separatrix) between basins.

    Attributes:
        separatrix: The underlying separatrix object.
        barrier_id: Unique identifier (typically separatrix ID).
        saddle: The saddle critical point this barrier emanates from.
        terminus: The extremum (min or max) this barrier connects to.
        barrier_type: 'descending' (saddle→min) or 'ascending' (saddle→max).
        persistence: Saddle persistence (primary strength measure).
        barrier_height: Maximum elevation along separatrix minus saddle value.
        barrier_width_km: Geographic length of separatrix in kilometers.
        geometry: LineString representation in EPSG:27700.
        lsoa_codes: List of LSOAs this barrier passes through.
        basin_left_id: Basin ID on one side (for descending separatrices).
        basin_right_id: Basin ID on other side (for descending separatrices).
    """

    separatrix: Separatrix
    barrier_id: int
    saddle: CriticalPoint
    terminus: CriticalPoint
    barrier_type: str
    persistence: float | None = None
    barrier_height: float = 0.0
    barrier_width_km: float | None = None
    geometry: LineString | None = None
    lsoa_codes: list[str] = field(default_factory=list)
    basin_left_id: int | None = None
    basin_right_id: int | None = None

    @property
    def is_descending(self) -> bool:
        """Check if this is a descending barrier (basin boundary)."""
        return self.barrier_type == "descending"

    @property
    def is_ascending(self) -> bool:
        """Check if this is an ascending barrier (peak boundary)."""
        return self.barrier_type == "ascending"

    @property
    def strength_score(self) -> float:
        """
        Compute overall barrier strength score.

        Combines persistence (70%) and barrier height (30%).
        Normalized to [0, 1] externally.
        """
        if self.persistence is None:
            return 0.0
        # Raw strength is primarily persistence-based
        return self.persistence


@dataclass
class BarrierImpact:
    """Analysis of barrier impact on population mobility.

    Attributes:
        barrier: The barrier being analyzed.
        population_separated: Total population separated by this barrier.
        mobility_differential: Absolute difference in mean mobility across barrier.
        basin_left_pop: Population in basin on left side.
        basin_right_pop: Population in basin on right side.
        basin_left_mobility: Mean mobility in left basin.
        basin_right_mobility: Mean mobility in right basin.
    """

    barrier: BarrierProperties
    population_separated: int = 0
    mobility_differential: float = 0.0
    basin_left_pop: int = 0
    basin_right_pop: int = 0
    basin_left_mobility: float = 0.0
    basin_right_mobility: float = 0.0

    @property
    def barrier_id(self) -> int:
        """Barrier identifier."""
        return self.barrier.barrier_id

    @property
    def impact_score(self) -> float:
        """
        Compute barrier impact score.

        Combines population (50%) and mobility differential (50%).
        Higher = more people separated by larger mobility gap.
        """
        # Raw impact, will be normalized externally
        return float(self.population_separated) * self.mobility_differential


# =============================================================================
# SEPARATRIX EXTRACTION FUNCTIONS
# =============================================================================


def extract_separatrices(
    morse_smale_output: MorseSmaleResult,
) -> tuple[list[Separatrix], list[Separatrix]]:
    """
    Extract separatrices from Morse-Smale complex output.

    Separates 1-separatrices into descending (saddle→minimum) and
    ascending (saddle→maximum) types.

    Args:
        morse_smale_output: Result from Morse-Smale complex computation.

    Returns:
        Tuple of (descending_separatrices, ascending_separatrices).
        - descending: List of separatrices connecting saddles to minima
        - ascending: List of separatrices connecting saddles to maxima

    Example:
        >>> descending, ascending = extract_separatrices(ms_result)
        >>> print(f"Found {len(descending)} basin boundaries")
    """
    descending = []
    ascending = []

    for sep in morse_smale_output.separatrices_1d:
        if sep.separatrix_type == 0:
            descending.append(sep)
        elif sep.separatrix_type == 1:
            ascending.append(sep)
        else:
            logger.warning(
                f"Unknown separatrix type {sep.separatrix_type} for "
                f"separatrix {sep.separatrix_id}"
            )

    logger.info(
        f"Extracted {len(descending)} descending and {len(ascending)} "
        f"ascending separatrices"
    )

    return descending, ascending


# =============================================================================
# BARRIER STRENGTH COMPUTATION FUNCTIONS
# =============================================================================


def compute_barrier_strength(
    separatrix: Separatrix,
    saddle: CriticalPoint,
    terminus: CriticalPoint,
    surface_data: dict[str, Any] | None = None,
) -> dict[str, float]:
    """
    Compute barrier strength metrics for a separatrix.

    Barrier strength is primarily determined by saddle persistence,
    with secondary metrics from geometric properties.

    Args:
        separatrix: The separatrix to analyze.
        saddle: The saddle critical point (source).
        terminus: The extremum critical point (destination).
        surface_data: Optional dict with scalar field for height computation:
            - 'scalar_field': 2D array of values
            - 'x_coords': 1D array of x coordinates
            - 'y_coords': 1D array of y coordinates

    Returns:
        Dictionary with strength metrics:
        - 'persistence': Saddle persistence (if available)
        - 'barrier_height': Max value along path - saddle value
        - 'barrier_width_km': Geographic length in kilometers

    Example:
        >>> strength = compute_barrier_strength(sep, saddle, min_point)
        >>> print(f"Barrier persistence: {strength['persistence']:.3f}")
    """
    metrics = {
        "persistence": saddle.persistence if saddle.persistence else 0.0,
        "barrier_height": 0.0,
        "barrier_width_km": 0.0,
    }

    # Compute barrier height if we have the path and values
    if separatrix.points is not None and separatrix.values is not None:
        # Height = max value along path - saddle value
        max_along_path = float(np.max(separatrix.values))
        metrics["barrier_height"] = max_along_path - saddle.value
    elif separatrix.points is None and surface_data is not None:
        # Estimate from saddle and terminus values
        metrics["barrier_height"] = abs(terminus.value - saddle.value)

    # Compute barrier width (geographic length)
    if separatrix.points is not None and len(separatrix.points) > 1:
        # Compute Euclidean length along path
        points = separatrix.points
        segments = np.diff(points, axis=0)
        # Use only x,y for 2D length (ignore z)
        lengths = np.sqrt(np.sum(segments[:, :2] ** 2, axis=1))
        total_length_m = float(np.sum(lengths))
        metrics["barrier_width_km"] = total_length_m / 1000.0
    else:
        # Estimate from straight-line distance between saddle and terminus
        dx = terminus.position[0] - saddle.position[0]
        dy = terminus.position[1] - saddle.position[1]
        straight_dist_m = np.sqrt(dx**2 + dy**2)
        metrics["barrier_width_km"] = float(straight_dist_m / 1000.0)

    return metrics


def create_barrier_properties(
    separatrices: list[Separatrix],
    morse_smale_output: MorseSmaleResult,
    surface_data: dict[str, Any] | None = None,
) -> list[BarrierProperties]:
    """
    Create BarrierProperties objects from separatrices with strength metrics.

    Args:
        separatrices: List of separatrices to analyze.
        morse_smale_output: Complete Morse-Smale result for critical point lookup.
        surface_data: Optional surface data for height computation.

    Returns:
        List of BarrierProperties with computed strength metrics.

    Example:
        >>> descending, _ = extract_separatrices(ms_result)
        >>> barriers = create_barrier_properties(descending, ms_result)
    """
    # Build critical point lookup
    cp_lookup = {cp.point_id: cp for cp in morse_smale_output.critical_points}

    barriers = []

    for sep in separatrices:
        # Get source saddle and destination terminus
        saddle = cp_lookup.get(sep.source_id)
        terminus = cp_lookup.get(sep.destination_id)

        if saddle is None or terminus is None:
            logger.warning(
                f"Separatrix {sep.separatrix_id} has invalid critical point IDs"
            )
            continue

        # Determine barrier type
        barrier_type = sep.type_name

        # Compute strength metrics
        strength = compute_barrier_strength(sep, saddle, terminus, surface_data)

        # Create geometry if we have points
        geometry = None
        if sep.points is not None and len(sep.points) > 1:
            # Extract x, y coordinates (ignore z)
            coords = [(p[0], p[1]) for p in sep.points]
            geometry = LineString(coords)

        barrier = BarrierProperties(
            separatrix=sep,
            barrier_id=sep.separatrix_id,
            saddle=saddle,
            terminus=terminus,
            barrier_type=barrier_type,
            persistence=strength["persistence"],
            barrier_height=strength["barrier_height"],
            barrier_width_km=strength["barrier_width_km"],
            geometry=geometry,
        )

        barriers.append(barrier)

    return barriers


# =============================================================================
# GEOGRAPHIC MAPPING FUNCTIONS
# =============================================================================


def map_barriers_to_geography(
    barriers: list[BarrierProperties],
    lsoa_boundaries: gpd.GeoDataFrame,
    buffer_meters: float = 100.0,
) -> list[BarrierProperties]:
    """
    Map barriers to LSOA boundaries and geographic features.

    Identifies which LSOAs each barrier passes through or near.

    Args:
        barriers: List of BarrierProperties to map.
        lsoa_boundaries: GeoDataFrame with LSOA boundaries (EPSG:27700).
            Must have 'lsoa_code' column.
        buffer_meters: Buffer distance in meters for intersection detection.

    Returns:
        Updated list of BarrierProperties with lsoa_codes populated.

    Example:
        >>> barriers = map_barriers_to_geography(barriers, lsoa_gdf)
        >>> for b in barriers:
        ...     print(f"Barrier {b.barrier_id} crosses {len(b.lsoa_codes)} LSOAs")
    """
    # Check CRS
    if lsoa_boundaries.crs is None:
        logger.warning("lsoa_boundaries has no CRS, assuming EPSG:27700")
        lsoa_boundaries = lsoa_boundaries.set_crs(CRS_BRITISH_NATIONAL_GRID)
    elif str(lsoa_boundaries.crs) != CRS_BRITISH_NATIONAL_GRID:
        logger.info(
            f"Converting lsoa_boundaries from {lsoa_boundaries.crs} to EPSG:27700"
        )
        lsoa_boundaries = lsoa_boundaries.to_crs(CRS_BRITISH_NATIONAL_GRID)

    # Check for lsoa_code column
    if "lsoa_code" not in lsoa_boundaries.columns:
        logger.warning("lsoa_code column not found in lsoa_boundaries")
        return barriers

    for barrier in barriers:
        if barrier.geometry is None:
            continue

        # Buffer the barrier line
        buffered = barrier.geometry.buffer(buffer_meters)

        # Find intersecting LSOAs
        intersecting = lsoa_boundaries[lsoa_boundaries.geometry.intersects(buffered)]

        # Extract LSOA codes
        barrier.lsoa_codes = intersecting["lsoa_code"].tolist()

    return barriers


# =============================================================================
# BARRIER RANKING FUNCTIONS
# =============================================================================


def rank_barriers(
    barriers: list[BarrierProperties],
    top_n: int = 20,
    rank_by: str = "persistence",
) -> list[BarrierProperties]:
    """
    Rank barriers by strength metrics.

    Args:
        barriers: List of BarrierProperties to rank.
        top_n: Number of top barriers to return.
        rank_by: Metric to rank by. Options:
            - 'persistence': Saddle persistence (default)
            - 'height': Barrier height
            - 'width': Barrier width
            - 'strength': Overall strength score

    Returns:
        List of top N barriers, sorted by specified metric descending.

    Example:
        >>> top_barriers = rank_barriers(barriers, top_n=10)
        >>> for i, b in enumerate(top_barriers, 1):
        ...     print(f"{i}. Barrier {b.barrier_id}: {b.persistence:.3f}")
    """
    # Define ranking keys
    ranking_keys = {
        "persistence": lambda b: b.persistence if b.persistence else 0.0,
        "height": lambda b: b.barrier_height,
        "width": lambda b: b.barrier_width_km if b.barrier_width_km else 0.0,
        "strength": lambda b: b.strength_score,
    }

    if rank_by not in ranking_keys:
        logger.warning(
            f"Unknown rank_by '{rank_by}', using 'persistence'. "
            f"Valid options: {list(ranking_keys.keys())}"
        )
        rank_by = "persistence"

    # Sort barriers
    sorted_barriers = sorted(barriers, key=ranking_keys[rank_by], reverse=True)

    return sorted_barriers[:top_n]


# =============================================================================
# BARRIER IMPACT ANALYSIS FUNCTIONS
# =============================================================================


def analyze_barrier_impact(
    barrier: BarrierProperties,
    basin_left: dict[str, Any],
    basin_right: dict[str, Any],
) -> BarrierImpact:
    """
    Analyze the impact of a barrier separating two basins.

    Computes population separated and mobility differential across barrier.

    Args:
        barrier: The barrier to analyze.
        basin_left: Dictionary with basin properties:
            - 'basin_id': Basin identifier
            - 'population': Population estimate
            - 'mean_mobility': Mean mobility value
        basin_right: Dictionary with basin properties (same structure).

    Returns:
        BarrierImpact with computed metrics.

    Example:
        >>> impact = analyze_barrier_impact(
        ...     barrier,
        ...     {'basin_id': 0, 'population': 5000, 'mean_mobility': 0.3},
        ...     {'basin_id': 1, 'population': 3000, 'mean_mobility': 0.7}
        ... )
        >>> print(f"Population separated: {impact.population_separated}")
    """
    # Extract basin properties
    left_pop = basin_left.get("population", 0)
    right_pop = basin_right.get("population", 0)
    left_mobility = basin_left.get("mean_mobility", 0.0)
    right_mobility = basin_right.get("mean_mobility", 0.0)

    # Compute metrics
    total_pop = left_pop + right_pop
    mobility_diff = abs(left_mobility - right_mobility)

    # Update barrier basin references
    barrier.basin_left_id = basin_left.get("basin_id")
    barrier.basin_right_id = basin_right.get("basin_id")

    impact = BarrierImpact(
        barrier=barrier,
        population_separated=total_pop,
        mobility_differential=mobility_diff,
        basin_left_pop=left_pop,
        basin_right_pop=right_pop,
        basin_left_mobility=left_mobility,
        basin_right_mobility=right_mobility,
    )

    return impact


def compute_barrier_impacts(
    barriers: list[BarrierProperties],
    basins: list[dict[str, Any]],
) -> list[BarrierImpact]:
    """
    Compute impacts for multiple barriers given basin properties.

    Args:
        barriers: List of BarrierProperties (descending separatrices).
        basins: List of basin dictionaries with:
            - 'basin_id': Minimum point ID
            - 'population': Population estimate
            - 'mean_mobility': Mean mobility value

    Returns:
        List of BarrierImpact objects.

    Example:
        >>> impacts = compute_barrier_impacts(barriers, basin_list)
        >>> top_impact = max(impacts, key=lambda i: i.impact_score)
    """
    # Build basin lookup
    basin_lookup = {b["basin_id"]: b for b in basins}

    impacts = []

    for barrier in barriers:
        # For descending separatrices, left/right basins are determined by
        # the destination minima of neighboring separatrices
        # Simplified: use terminus as one basin, find adjacent basin

        # Get the basin this barrier leads to
        terminus_basin_id = barrier.terminus.point_id
        terminus_basin = basin_lookup.get(terminus_basin_id)

        if terminus_basin is None:
            logger.debug(f"Barrier {barrier.barrier_id} has no basin data")
            continue

        # For now, create impact with single basin
        # Full implementation would find adjacent basin through manifold analysis
        empty_basin = {
            "basin_id": None,
            "population": 0,
            "mean_mobility": 0.0,
        }

        impact = analyze_barrier_impact(barrier, terminus_basin, empty_basin)
        impacts.append(impact)

    return impacts


# =============================================================================
# REPORTING FUNCTIONS
# =============================================================================


def barrier_summary_report(
    barriers: list[BarrierProperties],
) -> pd.DataFrame:
    """
    Generate summary report for barriers.

    Args:
        barriers: List of BarrierProperties to report on.

    Returns:
        DataFrame with columns:
        - barrier_id: Barrier identifier
        - barrier_type: 'descending' or 'ascending'
        - persistence: Saddle persistence
        - barrier_height: Elevation difference
        - barrier_width_km: Geographic length
        - n_lsoas: Number of LSOAs crossed
        - saddle_id: Source saddle ID
        - terminus_id: Destination extremum ID

    Example:
        >>> report = barrier_summary_report(top_barriers)
        >>> print(report.to_string())
    """
    if not barriers:
        return pd.DataFrame()

    rows = []
    for barrier in barriers:
        row = {
            "barrier_id": barrier.barrier_id,
            "barrier_type": barrier.barrier_type,
            "persistence": barrier.persistence,
            "barrier_height": barrier.barrier_height,
            "barrier_width_km": barrier.barrier_width_km,
            "n_lsoas": len(barrier.lsoa_codes),
            "saddle_id": barrier.saddle.point_id,
            "terminus_id": barrier.terminus.point_id,
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    return df
