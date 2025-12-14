"""
UK LSOA boundary data acquisition and processing.

This module provides utilities for downloading and processing Lower Layer Super
Output Area (LSOA) boundary shapefiles from the ONS Open Geography Portal.

Data Source:
    ONS Open Geography Portal: https://geoportal.statistics.gov.uk/
    Dataset: Lower layer Super Output Areas (December 2021) Boundaries EW BGC
    Coverage: England and Wales (~33,755 LSOAs)
    License: Open Government Licence v3.0

Coordinate Reference Systems:
    - Native CRS: EPSG:27700 (British National Grid)
    - Alternative: EPSG:4326 (WGS84)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

import geopandas as gpd
import requests

logger = logging.getLogger(__name__)

# ONS Open Geography Portal ArcGIS REST API endpoints
# LSOA (December 2021) Boundaries EW BGC (Generalised Clipped 20m)
# This is the recommended version for analysis - balance of detail and performance
_LSOA_2021_GEOJSON_URL = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
    "LSOA_Dec_2021_Boundaries_Generalised_Clipped_EW_BGC_2022/FeatureServer/0/"
    "query?where=1%3D1&outFields=*&outSR=27700&f=geojson"
)

# Alternative: Full resolution boundaries (larger file, more detail)
_LSOA_2021_FULL_GEOJSON_URL = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
    "LSOA_Dec_2021_Boundaries_Full_Clipped_EW_BFC_2022/FeatureServer/0/"
    "query?where=1%3D1&outFields=*&outSR=27700&f=geojson"
)

# Expected LSOA count for validation (2021 Census)
EXPECTED_LSOA_COUNT_2021 = 33755

# Default data directory relative to this module
DEFAULT_DATA_DIR = Path(__file__).parent / "raw" / "boundaries" / "lsoa_2021"

# Coordinate Reference Systems
CRS_BRITISH_NATIONAL_GRID = "EPSG:27700"
CRS_WGS84 = "EPSG:4326"


def download_lsoa_boundaries(
    output_dir: Path | None = None,
    year: int = 2021,
    resolution: Literal["generalised", "full"] = "generalised",
    chunk_size: int = 8192,
    timeout: int = 300,
) -> Path:
    """
    Download LSOA boundary files from ONS Open Geography Portal.

    Downloads the LSOA boundaries for England and Wales from the ONS ArcGIS
    REST API in GeoJSON format. The generalised (20m) version is recommended
    for most analysis tasks as it balances detail with performance.

    Args:
        output_dir: Directory to save downloaded file. Defaults to
            poverty_tda/data/raw/boundaries/lsoa_2021/
        year: Census year for boundaries. Currently only 2021 is supported.
        resolution: Boundary resolution level:
            - "generalised": 20m generalised, clipped to coastline (recommended)
            - "full": Full resolution, clipped to coastline (larger file)
        chunk_size: Download chunk size in bytes.
        timeout: Request timeout in seconds.

    Returns:
        Path to the downloaded GeoJSON file.

    Raises:
        ValueError: If unsupported year is specified.
        requests.RequestException: If download fails.

    Example:
        >>> filepath = download_lsoa_boundaries()
        >>> print(filepath)
        PosixPath('.../lsoa_2021/lsoa_2021_bgc.geojson')
    """
    if year != 2021:
        raise ValueError(
            f"Year {year} not supported. Currently only 2021 boundaries are available."
        )

    if output_dir is None:
        output_dir = DEFAULT_DATA_DIR

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Select URL based on resolution
    if resolution == "generalised":
        url = _LSOA_2021_GEOJSON_URL
        filename = f"lsoa_{year}_bgc.geojson"
    else:
        url = _LSOA_2021_FULL_GEOJSON_URL
        filename = f"lsoa_{year}_bfc.geojson"

    output_path = output_dir / filename

    # Skip if already downloaded
    if output_path.exists():
        logger.info(f"LSOA boundaries already exist at {output_path}")
        return output_path

    logger.info(f"Downloading LSOA {year} boundaries ({resolution})...")
    logger.info("Source: ONS Open Geography Portal")

    try:
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()

        # Write to file in chunks for large files
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)

        # Validate the downloaded GeoJSON file
        try:
            import json

            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Verify it has the expected GeoJSON structure
            if not isinstance(data, dict):
                raise ValueError("Downloaded file is not a valid GeoJSON object")

            # Some ArcGIS REST APIs return FeatureCollection, others return raw features
            if "features" not in data and "type" not in data:
                raise ValueError("Downloaded file missing required GeoJSON structure")

            logger.info(
                f"Validated GeoJSON file: {len(data.get('features', []))} features"
            )

        except json.JSONDecodeError as json_err:
            logger.error(f"Downloaded file is not valid JSON: {json_err}")
            output_path.unlink()
            raise ValueError(f"Downloaded file is not valid JSON: {json_err}")

        logger.info(f"Downloaded LSOA boundaries to {output_path}")
        return output_path

    except requests.RequestException as e:
        # Clean up partial download
        if output_path.exists():
            output_path.unlink()
        logger.error(f"Failed to download LSOA boundaries: {e}")
        raise


def load_lsoa_boundaries(
    filepath: Path | None = None,
    simplify: bool = False,
    tolerance: float = 50.0,
    download_if_missing: bool = True,
    engine: str = "pyogrio",
) -> gpd.GeoDataFrame:
    """
    Load LSOA boundaries into a GeoDataFrame.

    Loads LSOA boundary data from a GeoJSON file. If no filepath is provided
    and download_if_missing is True, downloads the data to the default location.

    Args:
        filepath: Path to GeoJSON or Shapefile. If None, uses default location.
        simplify: Whether to simplify geometries for performance.
            Uses Douglas-Peucker algorithm.
        tolerance: Simplification tolerance in meters (only used if simplify=True).
            Default 50m provides good balance of detail and performance.
        download_if_missing: If True and filepath not provided, download data
            to default location.
        engine: Geopandas file reading engine. Options: "pyogrio" (default),
            "fiona". Automatically falls back to fiona if pyogrio fails.

    Returns:
        GeoDataFrame with LSOA boundaries. Contains columns:
            - LSOA21CD: LSOA 2021 code (e.g., "E01000001")
            - LSOA21NM: LSOA 2021 name
            - geometry: Polygon/MultiPolygon boundary

    Raises:
        FileNotFoundError: If filepath doesn't exist and download_if_missing=False.
        ValueError: If loaded data doesn't contain expected LSOA columns.

    Example:
        >>> gdf = load_lsoa_boundaries()
        >>> print(len(gdf))
        33755
        >>> print(gdf.crs)
        EPSG:27700
    """
    if filepath is None:
        default_path = DEFAULT_DATA_DIR / "lsoa_2021_bgc.geojson"

        if not default_path.exists():
            if download_if_missing:
                filepath = download_lsoa_boundaries()
            else:
                raise FileNotFoundError(
                    f"LSOA boundary file not found at {default_path}. "
                    "Set download_if_missing=True to download automatically."
                )
        else:
            filepath = default_path
    else:
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Boundary file not found: {filepath}")

    logger.info(f"Loading LSOA boundaries from {filepath}")

    # Try to load with specified engine, with automatic fallback
    try:
        gdf = gpd.read_file(filepath, engine=engine)
    except Exception as e:
        # If pyogrio fails on GeoJSON, try alternative approaches
        if engine == "pyogrio" and str(filepath).endswith(".geojson"):
            logger.warning(
                f"pyogrio failed to read GeoJSON ({e}), "
                "attempting alternative loading strategies"
            )

            # Try reading as JSON and reconstructing
            try:
                import json

                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Handle both FeatureCollection and raw features
                if isinstance(data, dict):
                    if "features" in data:
                        gdf = gpd.GeoDataFrame.from_features(data["features"])
                    elif "type" in data and data["type"] == "FeatureCollection":
                        gdf = gpd.GeoDataFrame.from_features(data)
                    else:
                        # Might be raw features array
                        gdf = gpd.GeoDataFrame.from_features(data)
                else:
                    raise ValueError("Unexpected GeoJSON structure")

                # Set CRS - ArcGIS REST API uses EPSG:27700
                gdf = gdf.set_crs(CRS_BRITISH_NATIONAL_GRID)
                logger.info("Successfully loaded GeoJSON via JSON parsing")
            except Exception as json_error:
                # Final fallback: try fiona if available
                try:
                    gdf = gpd.read_file(filepath, engine="fiona")
                    logger.info("Successfully loaded using fiona engine")
                except Exception as fiona_error:
                    raise IOError(
                        f"Failed to load {filepath} with all available methods. "
                        f"pyogrio error: {e}, json error: {json_error}, "
                        f"fiona error: {fiona_error}"
                    )
        else:
            raise

    # Validate expected columns exist
    _validate_lsoa_columns(gdf)

    # Ensure proper CRS
    if gdf.crs is None:
        logger.warning("No CRS found, assuming British National Grid (EPSG:27700)")
        gdf = gdf.set_crs(CRS_BRITISH_NATIONAL_GRID)

    # Simplify geometries if requested
    if simplify:
        logger.info(f"Simplifying geometries with tolerance {tolerance}m")
        gdf["geometry"] = gdf["geometry"].simplify(tolerance, preserve_topology=True)

    logger.info(f"Loaded {len(gdf)} LSOA boundaries (CRS: {gdf.crs})")
    return gdf


def _validate_lsoa_columns(gdf: gpd.GeoDataFrame) -> None:
    """
    Validate that GeoDataFrame contains expected LSOA columns.

    Args:
        gdf: GeoDataFrame to validate.

    Raises:
        ValueError: If required columns are missing.
    """
    # Check for 2021 Census column names
    required_cols = {"LSOA21CD", "LSOA21NM"}

    # Handle alternative column naming (older datasets)
    alt_cols = {"lsoa21cd", "lsoa21nm"}  # lowercase variants

    cols_lower = {c.lower() for c in gdf.columns}

    if not required_cols.issubset(gdf.columns):
        if alt_cols.issubset(cols_lower):
            # Rename to standard format
            rename_map = {}
            for col in gdf.columns:
                if col.lower() == "lsoa21cd":
                    rename_map[col] = "LSOA21CD"
                elif col.lower() == "lsoa21nm":
                    rename_map[col] = "LSOA21NM"
            gdf.rename(columns=rename_map, inplace=True)
        else:
            raise ValueError(
                f"GeoDataFrame missing required LSOA columns. "
                f"Expected {required_cols}, found {set(gdf.columns)}"
            )


def get_lsoa_centroids(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Extract LSOA centroids for point-based analysis.

    Computes the centroid of each LSOA polygon for use in point-based
    spatial analysis, distance calculations, or visualization.

    Args:
        gdf: GeoDataFrame with LSOA polygon geometries.

    Returns:
        GeoDataFrame with same attributes but centroid point geometries.
        Original polygon geometries are replaced with Point geometries.

    Example:
        >>> gdf = load_lsoa_boundaries()
        >>> centroids = get_lsoa_centroids(gdf)
        >>> print(centroids.geometry.geom_type.unique())
        ['Point']
    """
    logger.info(f"Extracting centroids for {len(gdf)} LSOAs")

    # Create copy to avoid modifying original
    centroids_gdf = gdf.copy()
    centroids_gdf["geometry"] = gdf.geometry.centroid

    return centroids_gdf


def filter_by_region(
    gdf: gpd.GeoDataFrame,
    region: str,
    column: str = "LSOA21CD",
) -> gpd.GeoDataFrame:
    """
    Filter LSOAs by region name or code prefix.

    Filters the GeoDataFrame to include only LSOAs matching the specified
    region. Can filter by LSOA code prefix (e.g., "E01" for England) or
    by matching a specific column value.

    Args:
        gdf: GeoDataFrame with LSOA boundaries.
        region: Region identifier. Can be:
            - LSOA code prefix (e.g., "E01" for England, "W01" for Wales)
            - Full region name to match against specified column
        column: Column to filter on. Defaults to LSOA21CD.

    Returns:
        Filtered GeoDataFrame containing only LSOAs in specified region.

    Example:
        >>> gdf = load_lsoa_boundaries()
        >>> england = filter_by_region(gdf, "E01")  # England LSOAs
        >>> wales = filter_by_region(gdf, "W01")    # Wales LSOAs
        >>> print(len(england), len(wales))
        32844 911
    """
    if column not in gdf.columns:
        raise ValueError(f"Column '{column}' not found in GeoDataFrame")

    # Filter by prefix match
    mask = gdf[column].str.startswith(region, na=False)
    filtered = gdf[mask].copy()

    logger.info(f"Filtered to {len(filtered)} LSOAs matching region '{region}'")
    return filtered


def transform_crs(
    gdf: gpd.GeoDataFrame,
    target_crs: str = CRS_WGS84,
) -> gpd.GeoDataFrame:
    """
    Transform GeoDataFrame to a different coordinate reference system.

    Args:
        gdf: GeoDataFrame to transform.
        target_crs: Target CRS as EPSG code string (e.g., "EPSG:4326").
            Common options:
            - "EPSG:27700": British National Grid (meters)
            - "EPSG:4326": WGS84 (lat/lon degrees)

    Returns:
        GeoDataFrame transformed to target CRS.

    Example:
        >>> gdf = load_lsoa_boundaries()  # Returns in EPSG:27700
        >>> gdf_wgs84 = transform_crs(gdf, "EPSG:4326")
        >>> print(gdf_wgs84.crs)
        EPSG:4326
    """
    if gdf.crs is None:
        raise ValueError("GeoDataFrame has no CRS set. Cannot transform.")

    if str(gdf.crs) == target_crs:
        logger.debug(f"GeoDataFrame already in {target_crs}")
        return gdf

    logger.info(f"Transforming CRS from {gdf.crs} to {target_crs}")
    return gdf.to_crs(target_crs)
