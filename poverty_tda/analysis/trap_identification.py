"""
Basin analysis and poverty trap scoring for intervention prioritization.

This module provides utilities for extracting basin properties from
Morse-Smale complex descending manifolds and scoring poverty traps based
on their severity, size, and barrier characteristics.

Scoring Formula:
    trap_score = 0.4×mobility_score + 0.3×size_score + 0.3×barrier_score

Where:
    - mobility_score: Normalized (inverted) mean basin mobility - lower = worse
    - size_score: Normalized basin size - larger = more people affected
    - barrier_score: Normalized saddle persistence - higher = harder to escape

Integration:
    - morse_smale.py: Provides MorseSmaleResult with descending manifolds
    - critical_points.py: Critical point classification
    - opportunity_atlas.py: LSOA population data
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
from numpy.typing import NDArray
from shapely.geometry import Polygon
from shapely.ops import unary_union

from poverty_tda.topology.morse_smale import CriticalPoint, MorseSmaleResult

logger = logging.getLogger(__name__)

# CRS constants
CRS_BRITISH_NATIONAL_GRID = "EPSG:27700"


@dataclass
class BasinProperties:
    """Properties of a poverty trap basin from Morse-Smale analysis.

    Attributes:
        basin_id: Unique identifier for the basin (typically minimum point ID).
        minimum: The critical point (minimum) at the center of this basin.
        area_cells: Basin area in number of grid cells.
        area_km2: Basin area in square kilometers (if grid spacing known).
        mean_mobility: Mean mobility value within the basin.
        min_mobility: Minimum mobility value in the basin.
        bounding_saddles: List of saddle points on the basin boundary.
        barrier_heights: List of barrier heights (saddle value - minimum value).
        grid_mask: Boolean mask indicating basin cells in the grid.
        centroid: (x, y) coordinates of basin centroid in EPSG:27700.
    """

    basin_id: int
    minimum: CriticalPoint
    area_cells: int
    area_km2: float | None = None
    mean_mobility: float = 0.0
    min_mobility: float = 0.0
    bounding_saddles: list[CriticalPoint] = field(default_factory=list)
    barrier_heights: list[float] = field(default_factory=list)
    grid_mask: NDArray[np.bool_] | None = None
    centroid: tuple[float, float] | None = None

    @property
    def n_saddles(self) -> int:
        """Number of saddle points bounding this basin."""
        return len(self.bounding_saddles)

    @property
    def max_barrier_height(self) -> float:
        """Maximum barrier height (hardest escape route)."""
        return max(self.barrier_heights) if self.barrier_heights else 0.0

    @property
    def mean_barrier_height(self) -> float:
        """Mean barrier height."""
        return float(np.mean(self.barrier_heights)) if self.barrier_heights else 0.0


@dataclass
class TrapScore:
    """Poverty trap score with component breakdown.

    Attributes:
        basin: The basin properties this score is based on.
        total_score: Overall trap score (0-1, higher = more severe).
        mobility_score: Component score from mobility values (0-1).
        size_score: Component score from basin size (0-1).
        barrier_score: Component score from barrier heights (0-1).
        population_estimate: Estimated population in this basin.
        lsoa_codes: List of LSOA codes intersecting this basin.
        lad_name: Local Authority District name (primary LAD).
        region_name: Region name (primary region).
    """

    basin: BasinProperties
    total_score: float
    mobility_score: float
    size_score: float
    barrier_score: float
    population_estimate: int = 0
    lsoa_codes: list[str] = field(default_factory=list)
    lad_name: str | None = None
    region_name: str | None = None

    @property
    def basin_id(self) -> int:
        """Basin identifier."""
        return self.basin.basin_id

    @property
    def severity_rank(self) -> str:
        """Human-readable severity category."""
        if self.total_score >= 0.8:
            return "Critical"
        elif self.total_score >= 0.6:
            return "Severe"
        elif self.total_score >= 0.4:
            return "Moderate"
        elif self.total_score >= 0.2:
            return "Low"
        else:
            return "Minimal"


# =============================================================================
# BASIN EXTRACTION FUNCTIONS
# =============================================================================


def extract_basin_properties(
    morse_smale_output: MorseSmaleResult,
    surface_data: dict[str, Any],
    grid_spacing_km: float | None = None,
) -> list[BasinProperties]:
    """
    Extract basin properties from Morse-Smale descending manifolds.

    Each basin is a region that flows to the same local minimum. We extract
    the area, mean mobility, and bounding saddles for each basin.

    Args:
        morse_smale_output: Result from Morse-Smale complex computation.
        surface_data: Dictionary with:
            - 'scalar_field': 2D array of mobility values
            - 'x_coords': 1D array of x coordinates
            - 'y_coords': 1D array of y coordinates
        grid_spacing_km: Grid cell size in kilometers (for area calculation).

    Returns:
        List of BasinProperties, one per minimum in the Morse-Smale complex.

    Raises:
        ValueError: If descending_manifold is not available.
        ValueError: If surface_data is missing required keys.

    Example:
        >>> basins = extract_basin_properties(ms_result, surface_dict, 1.0)
        >>> print(f"Found {len(basins)} basins")
    """
    # Validate inputs
    if morse_smale_output.descending_manifold is None:
        raise ValueError("descending_manifold not available in MorseSmaleResult")

    required_keys = ["scalar_field", "x_coords", "y_coords"]
    missing = [k for k in required_keys if k not in surface_data]
    if missing:
        raise ValueError(f"surface_data missing keys: {missing}")

    scalar_field = surface_data["scalar_field"]
    x_coords = surface_data["x_coords"]
    y_coords = surface_data["y_coords"]
    descending = morse_smale_output.descending_manifold

    # Get all minima
    minima = morse_smale_output.get_minima()
    saddles = morse_smale_output.get_saddles()

    basins = []

    for minimum in minima:
        # Extract basin mask for this minimum
        # descending_manifold[i, j] == point_id means cell (i,j) flows to point_id
        basin_mask = descending == minimum.point_id

        # Skip empty basins (shouldn't happen but defensive)
        if not np.any(basin_mask):
            logger.warning(f"Empty basin for minimum {minimum.point_id}")
            continue

        # Compute basin properties
        area_cells = int(np.sum(basin_mask))

        # Compute area in km² if grid spacing provided
        area_km2 = None
        if grid_spacing_km is not None:
            area_km2 = area_cells * (grid_spacing_km**2)

        # Extract mobility values in basin
        basin_values = scalar_field[basin_mask]
        mean_mobility = float(np.mean(basin_values))
        min_mobility = float(np.min(basin_values))

        # Find centroid of basin
        basin_indices = np.argwhere(basin_mask)
        if len(basin_indices) > 0:
            mean_i = int(np.mean(basin_indices[:, 0]))
            mean_j = int(np.mean(basin_indices[:, 1]))
            centroid = (float(x_coords[mean_j]), float(y_coords[mean_i]))
        else:
            centroid = None

        # Find bounding saddles - saddles adjacent to this basin
        # A saddle bounds this basin if it connects to this minimum
        bounding_saddles = []
        barrier_heights = []

        for saddle in saddles:
            # Check separatrices connecting this saddle to our minimum
            for sep in morse_smale_output.separatrices_1d:
                # Descending separatrix from saddle to minimum
                if (
                    sep.separatrix_type == 0
                    and sep.source_id == saddle.point_id
                    and sep.destination_id == minimum.point_id
                ):
                    bounding_saddles.append(saddle)
                    # Barrier height = how much you need to climb
                    barrier_height = saddle.value - minimum.value
                    barrier_heights.append(barrier_height)
                    break

        basin = BasinProperties(
            basin_id=minimum.point_id,
            minimum=minimum,
            area_cells=area_cells,
            area_km2=area_km2,
            mean_mobility=mean_mobility,
            min_mobility=min_mobility,
            bounding_saddles=bounding_saddles,
            barrier_heights=barrier_heights,
            grid_mask=basin_mask,
            centroid=centroid,
        )

        basins.append(basin)

    logger.info(f"Extracted {len(basins)} basins from Morse-Smale complex")
    return basins


# =============================================================================
# TRAP SCORING FUNCTIONS
# =============================================================================


def compute_trap_score(
    basin_properties: list[BasinProperties],
) -> list[TrapScore]:
    """
    Compute poverty trap scores for basins.

    Scoring formula: 0.4×mobility_score + 0.3×size_score + 0.3×barrier_score

    Each component is normalized to [0, 1]:
    - mobility_score: Inverted normalized mobility (lower mobility = higher score)
    - size_score: Normalized basin area (larger = higher score)
    - barrier_score: Normalized max barrier height (higher = higher score)

    Args:
        basin_properties: List of basin properties from extract_basin_properties.

    Returns:
        List of TrapScore objects with component scores.

    Example:
        >>> scores = compute_trap_score(basins)
        >>> top_trap = max(scores, key=lambda s: s.total_score)
        >>> print(f"Worst trap score: {top_trap.total_score:.3f}")
    """
    if not basin_properties:
        return []

    # Extract values for normalization
    mean_mobilities = np.array([b.mean_mobility for b in basin_properties])
    areas = np.array([b.area_cells for b in basin_properties])
    max_barriers = np.array([b.max_barrier_height for b in basin_properties])

    # Normalize each component to [0, 1]
    # For mobility: invert so lower mobility = higher score
    mobility_min, mobility_max = mean_mobilities.min(), mean_mobilities.max()
    if mobility_max > mobility_min:
        mobility_scores = 1.0 - (mean_mobilities - mobility_min) / (
            mobility_max - mobility_min
        )
    else:
        mobility_scores = np.ones_like(mean_mobilities) * 0.5

    # For size: larger = higher score
    area_min, area_max = areas.min(), areas.max()
    if area_max > area_min:
        size_scores = (areas - area_min) / (area_max - area_min)
    else:
        size_scores = np.ones_like(areas) * 0.5

    # For barriers: higher = higher score
    barrier_min, barrier_max = max_barriers.min(), max_barriers.max()
    if barrier_max > barrier_min:
        barrier_scores = (max_barriers - barrier_min) / (barrier_max - barrier_min)
    else:
        barrier_scores = np.ones_like(max_barriers) * 0.5

    # Compute weighted total scores
    weights = {"mobility": 0.4, "size": 0.3, "barrier": 0.3}
    total_scores = (
        weights["mobility"] * mobility_scores
        + weights["size"] * size_scores
        + weights["barrier"] * barrier_scores
    )

    # Create TrapScore objects
    trap_scores = []
    for i, basin in enumerate(basin_properties):
        score = TrapScore(
            basin=basin,
            total_score=float(total_scores[i]),
            mobility_score=float(mobility_scores[i]),
            size_score=float(size_scores[i]),
            barrier_score=float(barrier_scores[i]),
        )
        trap_scores.append(score)

    return trap_scores


# =============================================================================
# POPULATION ESTIMATION FUNCTIONS
# =============================================================================


def estimate_basin_population(
    basin_mask: NDArray[np.bool_],
    grid_bounds: dict[str, float],
    lsoa_data: gpd.GeoDataFrame,
) -> tuple[int, list[str]]:
    """
    Estimate population in a basin by mapping to LSOA boundaries.

    Maps basin grid cells back to LSOA geometries and sums population
    from intersecting LSOAs (weighted by overlap area).

    Args:
        basin_mask: Boolean mask of basin cells in grid.
        grid_bounds: Dictionary with 'x_min', 'x_max', 'y_min', 'y_max',
            and 'resolution' defining the grid in EPSG:27700.
        lsoa_data: GeoDataFrame with LSOA boundaries and 'population' column.
            Must be in EPSG:27700 CRS.

    Returns:
        Tuple of (estimated_population, list_of_lsoa_codes).

    Example:
        >>> pop, lsoas = estimate_basin_population(mask, bounds, lsoa_gdf)
        >>> print(f"Basin covers {len(lsoas)} LSOAs with ~{pop} people")
    """
    # Validate inputs
    if "population" not in lsoa_data.columns:
        logger.warning("Population column not found in lsoa_data, returning 0")
        return 0, []

    # Check CRS
    if lsoa_data.crs is None:
        logger.warning("lsoa_data has no CRS, assuming EPSG:27700")
        lsoa_data = lsoa_data.set_crs(CRS_BRITISH_NATIONAL_GRID)
    elif str(lsoa_data.crs) != CRS_BRITISH_NATIONAL_GRID:
        logger.info(f"Converting lsoa_data from {lsoa_data.crs} to EPSG:27700")
        lsoa_data = lsoa_data.to_crs(CRS_BRITISH_NATIONAL_GRID)

    # Create basin polygon from grid mask
    x_min = grid_bounds["x_min"]
    x_max = grid_bounds["x_max"]
    y_min = grid_bounds["y_min"]
    y_max = grid_bounds["y_max"]
    resolution = grid_bounds["resolution"]

    x_coords = np.linspace(x_min, x_max, resolution)
    y_coords = np.linspace(y_min, y_max, resolution)

    # Grid cell size
    dx = (x_max - x_min) / resolution
    dy = (y_max - y_min) / resolution

    # Convert basin mask to polygons
    basin_cells = []
    basin_indices = np.argwhere(basin_mask)

    for i, j in basin_indices:
        # Create cell polygon
        x0 = x_coords[j]
        y0 = y_coords[i]
        cell_poly = Polygon(
            [
                (x0, y0),
                (x0 + dx, y0),
                (x0 + dx, y0 + dy),
                (x0, y0 + dy),
            ]
        )
        basin_cells.append(cell_poly)

    if not basin_cells:
        return 0, []

    # Union all cells into basin polygon
    basin_polygon = unary_union(basin_cells)

    # Find intersecting LSOAs
    intersecting = lsoa_data[lsoa_data.geometry.intersects(basin_polygon)].copy()

    if len(intersecting) == 0:
        return 0, []

    # Compute overlap areas and weighted population
    total_population = 0
    lsoa_codes = []

    for idx, row in intersecting.iterrows():
        lsoa_geom = row.geometry
        overlap = lsoa_geom.intersection(basin_polygon)
        overlap_area = overlap.area
        lsoa_area = lsoa_geom.area

        # Weight population by overlap fraction
        if lsoa_area > 0:
            weight = overlap_area / lsoa_area
            pop_contribution = row["population"] * weight
            total_population += pop_contribution

        # Track LSOA codes
        if "lsoa_code" in row:
            lsoa_codes.append(row["lsoa_code"])

    return int(total_population), lsoa_codes


# =============================================================================
# RANKING AND REPORTING FUNCTIONS
# =============================================================================


def rank_poverty_traps(
    trap_scores: list[TrapScore],
    top_n: int = 20,
) -> list[TrapScore]:
    """
    Rank poverty traps by total score and return top N.

    Args:
        trap_scores: List of TrapScore objects from compute_trap_score.
        top_n: Number of top traps to return (default 20).

    Returns:
        List of top N TrapScore objects, sorted by total_score descending.

    Example:
        >>> top_traps = rank_poverty_traps(scores, top_n=10)
        >>> for i, trap in enumerate(top_traps, 1):
        ...     print(f"{i}. Basin {trap.basin_id}: {trap.total_score:.3f}")
    """
    # Sort by total score descending
    sorted_traps = sorted(trap_scores, key=lambda s: s.total_score, reverse=True)

    # Return top N
    return sorted_traps[:top_n]


def trap_summary_report(
    ranked_traps: list[TrapScore],
) -> pd.DataFrame:
    """
    Generate summary report for ranked poverty traps.

    Args:
        ranked_traps: List of TrapScore objects from rank_poverty_traps.

    Returns:
        DataFrame with columns:
        - rank: Rank (1 = worst trap)
        - basin_id: Basin identifier
        - total_score: Overall trap score
        - severity: Human-readable severity category
        - population: Estimated population
        - area_km2: Basin area in km²
        - mean_mobility: Mean mobility value
        - max_barrier: Maximum barrier height
        - lad_name: Primary LAD name
        - region: Primary region name

    Example:
        >>> report = trap_summary_report(top_traps)
        >>> print(report.to_string())
    """
    if not ranked_traps:
        return pd.DataFrame()

    rows = []
    for rank, trap in enumerate(ranked_traps, 1):
        row = {
            "rank": rank,
            "basin_id": trap.basin_id,
            "total_score": trap.total_score,
            "severity": trap.severity_rank,
            "population": trap.population_estimate,
            "area_km2": trap.basin.area_km2,
            "mean_mobility": trap.basin.mean_mobility,
            "max_barrier": trap.basin.max_barrier_height,
            "lad_name": trap.lad_name,
            "region": trap.region_name,
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    return df
