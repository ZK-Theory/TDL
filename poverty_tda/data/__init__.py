"""
Census and mobility data loading utilities.

This module provides data acquisition and processing utilities for:
- UK LSOA boundary data from ONS Open Geography Portal
- Census demographic and deprivation data
- IMD (Index of Multiple Deprivation) socioeconomic data
- Education and POLAR4 higher education participation data
- Social mobility proxy calculation
- Geospatial processing and interpolation
"""

from poverty_tda.data.census_shapes import (
    CRS_BRITISH_NATIONAL_GRID,
    CRS_WGS84,
    EXPECTED_LSOA_COUNT_2021,
    download_lsoa_boundaries,
    filter_by_region,
    get_lsoa_centroids,
    load_lsoa_boundaries,
    transform_crs,
)
from poverty_tda.data.education import (
    compute_educational_upward,
    download_polar4_data,
    get_education_from_imd,
    load_ks4_outcomes,
    load_polar4_data,
)
from poverty_tda.data.geospatial import (
    create_mobility_surface,
    export_to_vtk,
    get_lad_boundaries,
    grid_to_geodataframe,
    interpolate_chunked,
    interpolate_idw,
    interpolate_kriging,
    interpolate_to_grid,
    spatial_join_lsoa,
)
from poverty_tda.data.mobility_proxy import (
    aggregate_to_lad,
    compute_deprivation_change,
    compute_income_growth,
    compute_mobility_proxy,
    get_mobility_quintiles,
    validate_against_smc,
)
from poverty_tda.data.opportunity_atlas import (
    EXPECTED_ENGLAND_LSOA_COUNT,
    EXPECTED_WALES_LSOA_COUNT,
    download_imd_data,
    get_deprivation_decile,
    get_domain_scores,
    load_imd_data,
    merge_with_boundaries,
    parse_imd_domains,
    validate_deprivation_patterns,
)

# Note: aggregate_to_lad is imported from both mobility_proxy and preprocessors
# The preprocessors version works with GeoDataFrames and returns geometry
# The mobility_proxy version works with DataFrames and returns aggregated values
# We export the mobility_proxy version for backwards compatibility
# Use preprocessors.aggregate_to_lad for spatial aggregation with geometry

__all__ = [
    # LSOA boundary functions
    "download_lsoa_boundaries",
    "load_lsoa_boundaries",
    "get_lsoa_centroids",
    "filter_by_region",
    "transform_crs",
    # IMD data functions
    "download_imd_data",
    "load_imd_data",
    "parse_imd_domains",
    "get_deprivation_decile",
    "get_domain_scores",
    "merge_with_boundaries",
    "validate_deprivation_patterns",
    # Education data functions
    "download_polar4_data",
    "load_polar4_data",
    "load_ks4_outcomes",
    "get_education_from_imd",
    "compute_educational_upward",
    # Mobility proxy functions
    "compute_deprivation_change",
    "compute_income_growth",
    "compute_mobility_proxy",
    "aggregate_to_lad",
    "get_mobility_quintiles",
    "validate_against_smc",
    # Geospatial processing functions
    "spatial_join_lsoa",
    "get_lad_boundaries",
    "interpolate_idw",
    "interpolate_kriging",
    "interpolate_to_grid",
    "interpolate_chunked",
    "export_to_vtk",
    "create_mobility_surface",
    "grid_to_geodataframe",
    # Constants
    "CRS_BRITISH_NATIONAL_GRID",
    "CRS_WGS84",
    "EXPECTED_LSOA_COUNT_2021",
    "EXPECTED_ENGLAND_LSOA_COUNT",
    "EXPECTED_WALES_LSOA_COUNT",
]
