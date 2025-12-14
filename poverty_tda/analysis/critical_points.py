"""
Critical point classification and geographic mapping for poverty analysis.

This module provides utilities for classifying Morse-Smale critical points
into meaningful socioeconomic categories and mapping them to UK LSOA geography.

Classification Schema:
    - **Poverty Traps** (minima): Low mobility areas where residents struggle
      to escape deprivation. Characterized by low scalar values in the
      mobility surface.
    - **Opportunity Peaks** (maxima): High mobility areas with good outcomes
      and pathways out of deprivation.
    - **Barriers** (saddles): Transition zones between basins that may
      represent invisible boundaries or intervention targets.

Coordinate Reference System:
    - Uses EPSG:27700 (British National Grid) for spatial operations
    - Critical point coordinates from mobility_surface are in BNG meters

Data Integration:
    - census_shapes.py: LSOA boundaries for spatial joins
    - opportunity_atlas.py: IMD data for validation
    - morse_smale.py: Critical points from topological analysis

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from poverty_tda.topology.morse_smale import CriticalPoint, MorseSmaleResult

logger = logging.getLogger(__name__)

# CRS constants
CRS_BRITISH_NATIONAL_GRID = "EPSG:27700"

# Classification types
ClassificationType = Literal["poverty_trap", "opportunity_peak", "barrier"]


@dataclass
class CriticalPointClassification:
    """A classified critical point with geographic context.

    Combines topological information from Morse-Smale analysis with
    geographic mapping to UK administrative boundaries.

    Attributes:
        point: (x, y) grid coordinates in EPSG:27700.
        classification: Socioeconomic classification of the point:
            - 'poverty_trap': minimum in mobility surface (low mobility)
            - 'opportunity_peak': maximum in mobility surface (high mobility)
            - 'barrier': saddle point (transition zone)
        severity: Normalized score (0-1) indicating significance.
            For traps: higher = more severe deprivation.
            For peaks: higher = stronger opportunity.
            For barriers: higher = more significant boundary.
        lsoa_code: LSOA 2021 code containing the point (e.g., 'E01000001').
        lad_name: Local Authority District name (e.g., 'Westminster').
        region_name: Region name (e.g., 'London').
        scalar_value: Raw mobility value at this point.
        persistence: Topological persistence (feature significance).
        original_point: Reference to the original CriticalPoint object.
    """

    point: tuple[float, float]
    classification: ClassificationType
    severity: float
    lsoa_code: str | None = None
    lad_name: str | None = None
    region_name: str | None = None
    scalar_value: float = 0.0
    persistence: float | None = None
    original_point: CriticalPoint | None = None

    @property
    def is_poverty_trap(self) -> bool:
        """Check if this is a poverty trap (minimum)."""
        return self.classification == "poverty_trap"

    @property
    def is_opportunity_peak(self) -> bool:
        """Check if this is an opportunity peak (maximum)."""
        return self.classification == "opportunity_peak"

    @property
    def is_barrier(self) -> bool:
        """Check if this is a barrier (saddle)."""
        return self.classification == "barrier"


@dataclass
class LADSummary:
    """Aggregated critical point statistics for a Local Authority District.

    Attributes:
        lad_name: Local Authority District name.
        lad_code: LAD code (if available).
        trap_count: Number of poverty traps in this LAD.
        peak_count: Number of opportunity peaks in this LAD.
        barrier_count: Number of barriers in this LAD.
        trap_density: Traps per km² (if area available).
        mean_trap_severity: Average severity of traps.
        mean_peak_severity: Average severity of peaks.
        points: List of classified points in this LAD.
    """

    lad_name: str
    lad_code: str | None = None
    trap_count: int = 0
    peak_count: int = 0
    barrier_count: int = 0
    trap_density: float | None = None
    mean_trap_severity: float = 0.0
    mean_peak_severity: float = 0.0
    points: list[CriticalPointClassification] = field(default_factory=list)

    @property
    def total_points(self) -> int:
        """Total number of critical points in this LAD."""
        return self.trap_count + self.peak_count + self.barrier_count

    @property
    def deprivation_ratio(self) -> float:
        """Ratio of traps to peaks. Higher = more deprived area."""
        if self.peak_count == 0:
            return float("inf") if self.trap_count > 0 else 0.0
        return self.trap_count / self.peak_count


# =============================================================================
# CLASSIFICATION FUNCTIONS
# =============================================================================


def classify_critical_points(
    morse_smale_result: MorseSmaleResult,
) -> list[CriticalPointClassification]:
    """
    Classify Morse-Smale critical points into socioeconomic categories.

    Maps topological critical point types to meaningful socioeconomic
    interpretations:
    - Minima → Poverty traps (low mobility, hard to escape)
    - Maxima → Opportunity peaks (high mobility, good outcomes)
    - Saddles → Barriers (boundaries between basins)

    Severity is computed based on:
    - Persistence: How topologically significant the feature is
    - Scalar value: How extreme the mobility value is

    Args:
        morse_smale_result: Result from compute_morse_smale() or
            analyze_mobility_topology().

    Returns:
        List of CriticalPointClassification objects.

    Example:
        >>> from poverty_tda.topology import analyze_mobility_topology
        >>> surface, meta, ms_result = analyze_mobility_topology(lsoa_gdf, ...)
        >>> classifications = classify_critical_points(ms_result)
        >>> traps = [c for c in classifications if c.is_poverty_trap]
        >>> print(f"Found {len(traps)} poverty traps")
    """
    scalar_min, scalar_max = morse_smale_result.scalar_range
    scalar_range = scalar_max - scalar_min if scalar_max > scalar_min else 1.0

    # Get persistence range for normalization
    persistence_values = [
        cp.persistence
        for cp in morse_smale_result.critical_points
        if cp.persistence is not None
    ]
    if persistence_values:
        max_persistence = max(persistence_values)
    else:
        max_persistence = scalar_range  # Fallback

    classifications = []

    for cp in morse_smale_result.critical_points:
        # Determine classification based on critical point type
        if cp.is_minimum:
            classification: ClassificationType = "poverty_trap"
        elif cp.is_maximum:
            classification = "opportunity_peak"
        elif cp.is_saddle:
            classification = "barrier"
        else:
            logger.warning(f"Unknown critical point type: {cp.point_type}")
            continue

        # Compute severity score (0-1)
        severity = _compute_severity(
            cp,
            classification,
            scalar_min,
            scalar_max,
            scalar_range,
            max_persistence,
        )

        classified = CriticalPointClassification(
            point=(cp.position[0], cp.position[1]),
            classification=classification,
            severity=severity,
            scalar_value=cp.value,
            persistence=cp.persistence,
            original_point=cp,
        )
        classifications.append(classified)

    logger.info(
        f"Classified {len(classifications)} critical points: "
        f"{sum(1 for c in classifications if c.is_poverty_trap)} traps, "
        f"{sum(1 for c in classifications if c.is_opportunity_peak)} peaks, "
        f"{sum(1 for c in classifications if c.is_barrier)} barriers"
    )

    return classifications


def _compute_severity(
    cp: CriticalPoint,
    classification: ClassificationType,
    scalar_min: float,
    scalar_max: float,
    scalar_range: float,
    max_persistence: float,
) -> float:
    """
    Compute severity score for a critical point.

    Severity combines:
    - Value extremity: How extreme the scalar value is
    - Persistence: How topologically significant the feature is

    For poverty traps: severity = (1 - normalized_value) × persistence_weight
    For opportunity peaks: severity = normalized_value × persistence_weight
    For barriers: severity = persistence_weight (saddles are transition zones)

    Args:
        cp: The critical point.
        classification: The point's classification type.
        scalar_min: Minimum value in scalar field.
        scalar_max: Maximum value in scalar field.
        scalar_range: Range of scalar values.
        max_persistence: Maximum persistence for normalization.

    Returns:
        Severity score in range [0, 1].
    """
    # Normalize scalar value to [0, 1]
    if scalar_range > 0:
        normalized_value = (cp.value - scalar_min) / scalar_range
    else:
        normalized_value = 0.5

    # Normalize persistence to [0, 1]
    if cp.persistence is not None and max_persistence > 0:
        persistence_weight = min(cp.persistence / max_persistence, 1.0)
    else:
        persistence_weight = 0.5  # Default if no persistence info

    # Compute severity based on classification
    if classification == "poverty_trap":
        # Lower value = more severe trap
        value_score = 1.0 - normalized_value
    elif classification == "opportunity_peak":
        # Higher value = stronger opportunity
        value_score = normalized_value
    else:  # barrier
        # Saddles: use persistence as primary indicator
        value_score = 0.5

    # Combine value and persistence (weighted average)
    # Value contributes 60%, persistence 40%
    severity = 0.6 * value_score + 0.4 * persistence_weight

    return float(np.clip(severity, 0.0, 1.0))


# =============================================================================
# GEOGRAPHIC MAPPING
# =============================================================================


def map_to_lsoa(
    classified_points: list[CriticalPointClassification],
    lsoa_gdf: gpd.GeoDataFrame,
    lsoa_code_column: str = "LSOA21CD",
    lad_name_column: str = "LAD22NM",
    region_column: str | None = None,
) -> list[CriticalPointClassification]:
    """
    Map classified critical points to their containing LSOAs.

    Performs a spatial join between point geometries (from grid coordinates)
    and LSOA polygon boundaries to identify which LSOA each critical point
    falls within.

    Args:
        classified_points: List of classified critical points.
        lsoa_gdf: GeoDataFrame with LSOA boundaries (EPSG:27700).
            Must contain LSOA code and LAD name columns.
        lsoa_code_column: Column name for LSOA 2021 codes.
        lad_name_column: Column name for Local Authority District names.
        region_column: Optional column for region names.

    Returns:
        Updated list with lsoa_code, lad_name, and region_name populated.
        Points outside England/Wales boundaries will have None values.

    Raises:
        ValueError: If required columns not found in lsoa_gdf.

    Example:
        >>> classifications = classify_critical_points(ms_result)
        >>> lsoa = load_lsoa_boundaries()
        >>> mapped = map_to_lsoa(classifications, lsoa)
        >>> westminster = [c for c in mapped if c.lad_name == 'Westminster']
    """
    if len(classified_points) == 0:
        return classified_points

    # Validate required columns
    if lsoa_code_column not in lsoa_gdf.columns:
        raise ValueError(f"Column '{lsoa_code_column}' not found in lsoa_gdf")
    if lad_name_column not in lsoa_gdf.columns:
        raise ValueError(f"Column '{lad_name_column}' not found in lsoa_gdf")

    # Ensure CRS is EPSG:27700
    if lsoa_gdf.crs is None:
        logger.warning("LSOA GeoDataFrame has no CRS, assuming EPSG:27700")
        lsoa_gdf = lsoa_gdf.set_crs(CRS_BRITISH_NATIONAL_GRID)
    elif str(lsoa_gdf.crs).upper() != CRS_BRITISH_NATIONAL_GRID:
        logger.info(f"Transforming LSOA from {lsoa_gdf.crs} to EPSG:27700")
        lsoa_gdf = lsoa_gdf.to_crs(CRS_BRITISH_NATIONAL_GRID)

    # Create GeoDataFrame from classified points
    points_data = []
    for i, cp in enumerate(classified_points):
        points_data.append(
            {
                "idx": i,
                "geometry": Point(cp.point[0], cp.point[1]),
            }
        )

    points_gdf = gpd.GeoDataFrame(points_data, crs=CRS_BRITISH_NATIONAL_GRID)

    # Perform spatial join (point in polygon)
    columns_to_keep = [lsoa_code_column, lad_name_column]
    if region_column and region_column in lsoa_gdf.columns:
        columns_to_keep.append(region_column)

    joined = gpd.sjoin(
        points_gdf,
        lsoa_gdf[["geometry"] + columns_to_keep],
        how="left",
        predicate="within",
    )

    # Handle duplicate matches (point on boundary) - take first match
    joined = joined.drop_duplicates(subset=["idx"], keep="first")

    # Update classifications with geographic info
    for _, row in joined.iterrows():
        idx = int(row["idx"])
        cp = classified_points[idx]

        # Extract LSOA code (may be NaN if outside boundaries)
        lsoa_code = row.get(lsoa_code_column)
        if pd.notna(lsoa_code):
            cp.lsoa_code = str(lsoa_code)

        # Extract LAD name
        lad_name = row.get(lad_name_column)
        if pd.notna(lad_name):
            cp.lad_name = str(lad_name)

        # Extract region if available
        if region_column and region_column in row.index:
            region_name = row.get(region_column)
            if pd.notna(region_name):
                cp.region_name = str(region_name)

    # Count mapped vs unmapped
    mapped_count = sum(1 for cp in classified_points if cp.lsoa_code is not None)
    unmapped_count = len(classified_points) - mapped_count

    logger.info(
        f"Mapped {mapped_count}/{len(classified_points)} points to LSOAs. "
        f"{unmapped_count} points outside boundaries."
    )

    return classified_points


def aggregate_by_lad(
    classified_points: list[CriticalPointClassification],
    lad_areas: dict[str, float] | None = None,
) -> list[LADSummary]:
    """
    Aggregate classified critical points by Local Authority District.

    Groups points by LAD and computes summary statistics including
    trap/peak counts, densities, and average severities.

    Args:
        classified_points: List of classified points with lad_name populated.
        lad_areas: Optional dict mapping LAD names to area in km².
            If provided, trap_density will be computed.

    Returns:
        List of LADSummary objects, sorted by trap_count descending.

    Example:
        >>> mapped = map_to_lsoa(classifications, lsoa)
        >>> lad_summaries = aggregate_by_lad(mapped)
        >>> for lad in lad_summaries[:10]:
        ...     print(f"{lad.lad_name}: {lad.trap_count} traps")
    """
    # Group by LAD
    lad_groups: dict[str, list[CriticalPointClassification]] = {}

    for cp in classified_points:
        if cp.lad_name is None:
            continue  # Skip unmapped points

        if cp.lad_name not in lad_groups:
            lad_groups[cp.lad_name] = []
        lad_groups[cp.lad_name].append(cp)

    # Compute summaries
    summaries = []

    for lad_name, points in lad_groups.items():
        traps = [p for p in points if p.is_poverty_trap]
        peaks = [p for p in points if p.is_opportunity_peak]
        barriers = [p for p in points if p.is_barrier]

        # Compute mean severities
        mean_trap_severity = (
            float(np.mean([t.severity for t in traps])) if traps else 0.0
        )
        mean_peak_severity = (
            float(np.mean([p.severity for p in peaks])) if peaks else 0.0
        )

        # Compute density if area available
        trap_density = None
        if lad_areas and lad_name in lad_areas and lad_areas[lad_name] > 0:
            trap_density = len(traps) / lad_areas[lad_name]

        summary = LADSummary(
            lad_name=lad_name,
            trap_count=len(traps),
            peak_count=len(peaks),
            barrier_count=len(barriers),
            trap_density=trap_density,
            mean_trap_severity=mean_trap_severity,
            mean_peak_severity=mean_peak_severity,
            points=points,
        )
        summaries.append(summary)

    # Sort by trap count (most deprived first)
    summaries.sort(key=lambda s: s.trap_count, reverse=True)

    logger.info(
        f"Aggregated to {len(summaries)} LADs. "
        f"Most traps: {summaries[0].lad_name if summaries else 'N/A'} "
        f"({summaries[0].trap_count if summaries else 0})"
    )

    return summaries


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def get_points_by_classification(
    classified_points: list[CriticalPointClassification],
    classification: ClassificationType,
) -> list[CriticalPointClassification]:
    """
    Filter classified points by classification type.

    Args:
        classified_points: List of classified points.
        classification: Type to filter by.

    Returns:
        Filtered list of points.
    """
    return [cp for cp in classified_points if cp.classification == classification]


def get_points_in_lad(
    classified_points: list[CriticalPointClassification],
    lad_name: str,
) -> list[CriticalPointClassification]:
    """
    Get all classified points in a specific LAD.

    Args:
        classified_points: List of classified points with lad_name populated.
        lad_name: LAD name to filter by.

    Returns:
        List of points in the specified LAD.
    """
    return [cp for cp in classified_points if cp.lad_name == lad_name]


def get_severity_ranking(
    classified_points: list[CriticalPointClassification],
    classification: ClassificationType | None = None,
    top_n: int | None = None,
) -> list[CriticalPointClassification]:
    """
    Rank classified points by severity.

    Args:
        classified_points: List of classified points.
        classification: Optional type filter.
        top_n: Optional limit on number of results.

    Returns:
        List sorted by severity (highest first).
    """
    points = classified_points
    if classification is not None:
        points = get_points_by_classification(points, classification)

    sorted_points = sorted(points, key=lambda p: p.severity, reverse=True)

    if top_n is not None:
        sorted_points = sorted_points[:top_n]

    return sorted_points


def to_dataframe(
    classified_points: list[CriticalPointClassification],
) -> pd.DataFrame:
    """
    Convert classified points to a pandas DataFrame.

    Useful for analysis, export, and visualization.

    Args:
        classified_points: List of classified points.

    Returns:
        DataFrame with columns: x, y, classification, severity,
        lsoa_code, lad_name, region_name, scalar_value, persistence.
    """
    data = []
    for cp in classified_points:
        data.append(
            {
                "x": cp.point[0],
                "y": cp.point[1],
                "classification": cp.classification,
                "severity": cp.severity,
                "lsoa_code": cp.lsoa_code,
                "lad_name": cp.lad_name,
                "region_name": cp.region_name,
                "scalar_value": cp.scalar_value,
                "persistence": cp.persistence,
            }
        )

    return pd.DataFrame(data)


def to_geodataframe(
    classified_points: list[CriticalPointClassification],
    crs: str = CRS_BRITISH_NATIONAL_GRID,
) -> gpd.GeoDataFrame:
    """
    Convert classified points to a GeoDataFrame.

    Useful for spatial analysis and mapping.

    Args:
        classified_points: List of classified points.
        crs: Coordinate reference system for output.

    Returns:
        GeoDataFrame with Point geometries and classification attributes.
    """
    df = to_dataframe(classified_points)
    geometry = [Point(x, y) for x, y in zip(df["x"], df["y"])]

    return gpd.GeoDataFrame(df, geometry=geometry, crs=crs)


# =============================================================================
# VALIDATION AGAINST KNOWN PATTERNS
# =============================================================================

# Known deprivation patterns from IMD 2019 and Social Mobility Commission
# These are expected locations for poverty traps (minima in mobility surface)
KNOWN_DEPRIVED_LADS = [
    "Blackpool",  # Coastal deprivation, consistently ranked most deprived
    "Knowsley",  # Persistent deprivation in Merseyside
    "Kingston upon Hull, City of",  # Post-industrial decline
    "Liverpool",  # Multiple deprived LSOAs
    "Middlesbrough",  # Post-industrial Teesside
    "Hartlepool",  # Industrial decline
    "Manchester",  # Urban deprivation pockets
    "Burnley",  # Lancashire mill town decline
    "Stoke-on-Trent",  # Industrial decline
    "Tendring",  # Contains Jaywick - most deprived LSOA in England
]

# Known affluent areas - expected locations for opportunity peaks (maxima)
KNOWN_AFFLUENT_LADS = [
    "Westminster",  # Central London, high income
    "City of London",  # Financial center
    "Kensington and Chelsea",  # Affluent inner London
    "Richmond upon Thames",  # Affluent outer London
    "Camden",  # Gentrified inner London
    "Wandsworth",  # Affluent south London
    "Cambridge",  # University town, high education mobility
    "Oxford",  # University town
    "Hart",  # Consistently least deprived LAD
    "Wokingham",  # Affluent commuter belt
    "Surrey Heath",  # Affluent Surrey
    "Elmbridge",  # Affluent Surrey
    "Waverley",  # Affluent Surrey
    "Buckinghamshire",  # Affluent commuter belt
]

# Jaywick LSOA - the single most deprived LSOA in England (IMD 2019)
JAYWICK_LSOA_CODE = "E01021437"


@dataclass
class ValidationResult:
    """Result of validation against known patterns.

    Attributes:
        region: The region/LAD being validated.
        expected_type: 'trap' or 'peak' based on known patterns.
        found_type: What was actually found ('trap', 'peak', 'barrier', None).
        found_count: Number of critical points found.
        match: Whether the expectation was met.
        severity_mean: Mean severity of found points.
        notes: Additional context or explanation.
    """

    region: str
    expected_type: Literal["trap", "peak"]
    found_type: str | None
    found_count: int
    match: bool
    severity_mean: float | None = None
    notes: str = ""


@dataclass
class ValidationSummary:
    """Summary of all validation results.

    Attributes:
        total_validations: Number of regions validated.
        matches: Number of successful matches.
        match_rate: Percentage of successful matches.
        trap_match_rate: Match rate for expected traps.
        peak_match_rate: Match rate for expected peaks.
        results: List of individual ValidationResult objects.
        deprived_lads_found: LADs with identified traps.
        affluent_lads_found: LADs with identified peaks.
    """

    total_validations: int
    matches: int
    match_rate: float
    trap_match_rate: float
    peak_match_rate: float
    results: list[ValidationResult]
    deprived_lads_found: list[str]
    affluent_lads_found: list[str]


def validate_against_known_patterns(
    classified_points: list[CriticalPointClassification],
    deprived_lads: list[str] | None = None,
    affluent_lads: list[str] | None = None,
) -> ValidationSummary:
    """
    Validate classified critical points against known UK patterns.

    Checks whether identified poverty traps (minima) overlap with known
    deprived areas and opportunity peaks (maxima) overlap with known
    affluent areas.

    Args:
        classified_points: List of classified points with lad_name populated.
        deprived_lads: List of known deprived LAD names. If None, uses
            KNOWN_DEPRIVED_LADS constant.
        affluent_lads: List of known affluent LAD names. If None, uses
            KNOWN_AFFLUENT_LADS constant.

    Returns:
        ValidationSummary with match rates and individual results.

    Example:
        >>> mapped = map_to_lsoa(classifications, lsoa)
        >>> validation = validate_against_known_patterns(mapped)
        >>> print(f"Overall match rate: {validation.match_rate:.1%}")
        >>> for r in validation.results:
        ...     print(f"{r.region}: expected={r.expected_type}, match={r.match}")
    """
    if deprived_lads is None:
        deprived_lads = KNOWN_DEPRIVED_LADS
    if affluent_lads is None:
        affluent_lads = KNOWN_AFFLUENT_LADS

    # Get LAD summaries
    lad_summaries = aggregate_by_lad(classified_points)
    lad_dict = {s.lad_name: s for s in lad_summaries}

    results = []
    trap_validations = 0
    trap_matches = 0
    peak_validations = 0
    peak_matches = 0

    # Validate deprived LADs - expect traps
    for lad_name in deprived_lads:
        trap_validations += 1
        summary = lad_dict.get(lad_name)

        if summary is None:
            # LAD not in data - could be outside analysis area
            results.append(
                ValidationResult(
                    region=lad_name,
                    expected_type="trap",
                    found_type=None,
                    found_count=0,
                    match=False,
                    notes="LAD not found in classified points",
                )
            )
        elif summary.trap_count > 0:
            # Found traps as expected
            trap_matches += 1
            results.append(
                ValidationResult(
                    region=lad_name,
                    expected_type="trap",
                    found_type="trap",
                    found_count=summary.trap_count,
                    match=True,
                    severity_mean=summary.mean_trap_severity,
                    notes=f"Found {summary.trap_count} poverty traps",
                )
            )
        elif summary.peak_count > 0:
            # Found peaks instead - unexpected
            results.append(
                ValidationResult(
                    region=lad_name,
                    expected_type="trap",
                    found_type="peak",
                    found_count=summary.peak_count,
                    match=False,
                    severity_mean=summary.mean_peak_severity,
                    notes="Expected traps but found peaks - investigate",
                )
            )
        else:
            # Only barriers or no significant points
            results.append(
                ValidationResult(
                    region=lad_name,
                    expected_type="trap",
                    found_type="barrier" if summary.barrier_count > 0 else None,
                    found_count=summary.barrier_count,
                    match=False,
                    notes="No traps found, only barriers or no points",
                )
            )

    # Validate affluent LADs - expect peaks
    for lad_name in affluent_lads:
        peak_validations += 1
        summary = lad_dict.get(lad_name)

        if summary is None:
            results.append(
                ValidationResult(
                    region=lad_name,
                    expected_type="peak",
                    found_type=None,
                    found_count=0,
                    match=False,
                    notes="LAD not found in classified points",
                )
            )
        elif summary.peak_count > 0:
            # Found peaks as expected
            peak_matches += 1
            results.append(
                ValidationResult(
                    region=lad_name,
                    expected_type="peak",
                    found_type="peak",
                    found_count=summary.peak_count,
                    match=True,
                    severity_mean=summary.mean_peak_severity,
                    notes=f"Found {summary.peak_count} opportunity peaks",
                )
            )
        elif summary.trap_count > 0:
            # Found traps instead - unexpected
            results.append(
                ValidationResult(
                    region=lad_name,
                    expected_type="peak",
                    found_type="trap",
                    found_count=summary.trap_count,
                    match=False,
                    severity_mean=summary.mean_trap_severity,
                    notes="Expected peaks but found traps - investigate",
                )
            )
        else:
            results.append(
                ValidationResult(
                    region=lad_name,
                    expected_type="peak",
                    found_type="barrier" if summary.barrier_count > 0 else None,
                    found_count=summary.barrier_count,
                    match=False,
                    notes="No peaks found, only barriers or no points",
                )
            )

    # Compute summary statistics
    total_matches = trap_matches + peak_matches
    total_validations = trap_validations + peak_validations

    match_rate = total_matches / total_validations if total_validations > 0 else 0.0
    trap_match_rate = trap_matches / trap_validations if trap_validations > 0 else 0.0
    peak_match_rate = peak_matches / peak_validations if peak_validations > 0 else 0.0

    # Get unique LADs found
    deprived_lads_found = [
        r.region for r in results if r.expected_type == "trap" and r.match
    ]
    affluent_lads_found = [
        r.region for r in results if r.expected_type == "peak" and r.match
    ]

    logger.info(
        f"Validation complete: {match_rate:.1%} overall match rate "
        f"({trap_match_rate:.1%} traps, {peak_match_rate:.1%} peaks)"
    )

    return ValidationSummary(
        total_validations=total_validations,
        matches=total_matches,
        match_rate=match_rate,
        trap_match_rate=trap_match_rate,
        peak_match_rate=peak_match_rate,
        results=results,
        deprived_lads_found=deprived_lads_found,
        affluent_lads_found=affluent_lads_found,
    )


def generate_validation_report(
    validation: ValidationSummary,
    include_all: bool = False,
) -> str:
    """
    Generate a markdown-formatted validation report.

    Args:
        validation: ValidationSummary from validate_against_known_patterns.
        include_all: If True, include all validation results.
            If False, only show mismatches and summary.

    Returns:
        Markdown-formatted string with validation report.
    """
    lines = []
    lines.append("# Critical Point Validation Report\n")

    # Summary section
    lines.append("## Summary\n")
    lines.append(f"- **Total validations**: {validation.total_validations}")
    lines.append(f"- **Matches**: {validation.matches}")
    lines.append(f"- **Overall match rate**: {validation.match_rate:.1%}")
    lines.append(f"- **Trap match rate**: {validation.trap_match_rate:.1%}")
    lines.append(f"- **Peak match rate**: {validation.peak_match_rate:.1%}")
    lines.append("")

    # Success criteria check
    lines.append("## Success Criteria\n")
    trap_pass = "✓ PASS" if validation.trap_match_rate >= 0.70 else "✗ FAIL"
    peak_pass = "✓ PASS" if validation.peak_match_rate >= 0.70 else "✗ FAIL"
    trap_rate = validation.trap_match_rate
    peak_rate = validation.peak_match_rate
    lines.append(f"- Trap match rate ≥70%: {trap_pass} ({trap_rate:.1%})")
    lines.append(f"- Peak match rate ≥70%: {peak_pass} ({peak_rate:.1%})")
    lines.append("")

    # Validation table
    lines.append("## Validation Results\n")
    lines.append("| Region | Expected | Found | Count | Match | Notes |")
    lines.append("|--------|----------|-------|-------|-------|-------|")

    for r in validation.results:
        if include_all or not r.match:
            match_str = "✓" if r.match else "✗"
            found_str = r.found_type or "-"
            lines.append(
                f"| {r.region} | {r.expected_type} | {found_str} | "
                f"{r.found_count} | {match_str} | {r.notes} |"
            )

    lines.append("")

    # LADs found
    if validation.deprived_lads_found:
        lines.append("## Deprived LADs with Identified Traps\n")
        for lad in validation.deprived_lads_found:
            lines.append(f"- {lad}")
        lines.append("")

    if validation.affluent_lads_found:
        lines.append("## Affluent LADs with Identified Peaks\n")
        for lad in validation.affluent_lads_found:
            lines.append(f"- {lad}")
        lines.append("")

    return "\n".join(lines)


def compute_imd_overlap(
    classified_points: list[CriticalPointClassification],
    imd_df: pd.DataFrame,
    decile_column: str = "imd_decile",
    lsoa_column: str = "lsoa_code",
) -> dict[str, float]:
    """
    Compute overlap between classified points and IMD deciles.

    Checks how well poverty traps align with most deprived deciles (1-2)
    and opportunity peaks align with least deprived deciles (9-10).

    Args:
        classified_points: Classified points with lsoa_code populated.
        imd_df: DataFrame with IMD data including deciles.
        decile_column: Column name for IMD decile.
        lsoa_column: Column name for LSOA code.

    Returns:
        Dict with overlap statistics:
        - trap_in_deprived: % of traps in deciles 1-2
        - trap_in_least_deprived: % of traps in deciles 9-10 (should be low)
        - peak_in_affluent: % of peaks in deciles 9-10
        - peak_in_most_deprived: % of peaks in deciles 1-2 (should be low)
    """
    # Create LSOA to decile mapping
    lsoa_decile = dict(zip(imd_df[lsoa_column], imd_df[decile_column]))

    traps = [c for c in classified_points if c.is_poverty_trap and c.lsoa_code]
    peaks = [c for c in classified_points if c.is_opportunity_peak and c.lsoa_code]

    # Count traps in different decile ranges
    traps_in_1_2 = sum(1 for t in traps if lsoa_decile.get(t.lsoa_code, 5) <= 2)
    traps_in_9_10 = sum(1 for t in traps if lsoa_decile.get(t.lsoa_code, 5) >= 9)

    # Count peaks in different decile ranges
    peaks_in_9_10 = sum(1 for p in peaks if lsoa_decile.get(p.lsoa_code, 5) >= 9)
    peaks_in_1_2 = sum(1 for p in peaks if lsoa_decile.get(p.lsoa_code, 5) <= 2)

    n_traps = len(traps) or 1  # Avoid division by zero
    n_peaks = len(peaks) or 1

    return {
        "trap_in_deprived": traps_in_1_2 / n_traps,
        "trap_in_least_deprived": traps_in_9_10 / n_traps,
        "peak_in_affluent": peaks_in_9_10 / n_peaks,
        "peak_in_most_deprived": peaks_in_1_2 / n_peaks,
        "n_traps": len(traps),
        "n_peaks": len(peaks),
    }
