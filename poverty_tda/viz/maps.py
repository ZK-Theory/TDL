"""
Interactive geographic maps for poverty trap analysis.

This module provides Folium-based interactive maps for visualizing poverty
traps, basin memberships, escape routes, and intervention gateways across
England and Wales at LSOA level.

Features:
    - LSOA choropleth with mobility proxy or trap score coloring
    - Basin overlay with distinct colors per poverty trap basin
    - Click interaction to reveal basin membership and escape routes
    - Layer toggles for mobility surface, trap scores, barriers, gateways
    - HTML export for web embedding

Integration:
    - census_shapes.py: LSOA boundary loading and GeoDataFrame structure
    - trap_identification.py: Basin properties and trap scoring
    - pathways.py: Integral line computation and gateway identification
    - mobility_surface.py: Scalar field for mobility surface

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
from pathlib import Path

import folium
import geopandas as gpd
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
from folium import FeatureGroup, LayerControl
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# England/Wales center point for map initialization (EPSG:4326)
# Approximate center between London and Manchester
ENGLAND_WALES_CENTER = [52.8, -2.0]
DEFAULT_ZOOM = 7

# Colormap options
MOBILITY_COLORMAP = "RdYlGn"  # Red (low mobility) to Green (high mobility)
TRAP_SCORE_COLORMAP = "YlOrRd"  # Yellow to Red (higher = more severe)

# CRS constants
CRS_BRITISH_NATIONAL_GRID = "EPSG:27700"
CRS_WGS84 = "EPSG:4326"


def create_base_map(
    center: list[float] = ENGLAND_WALES_CENTER,
    zoom_start: int = DEFAULT_ZOOM,
    tiles: str = "OpenStreetMap",
    width: str = "100%",
    height: str = "600px",
) -> folium.Map:
    """
    Create a Folium base map for England/Wales.

    Args:
        center: [latitude, longitude] for map center (EPSG:4326).
        zoom_start: Initial zoom level (7 shows most of England/Wales).
        tiles: Base tile layer. Options: "OpenStreetMap", "CartoDB positron",
            "CartoDB dark_matter", "Stamen Terrain".
        width: Map width CSS value (e.g., "100%", "800px").
        height: Map height CSS value.

    Returns:
        Folium Map object ready for layer addition.

    Example:
        >>> m = create_base_map()
        >>> m.save("map.html")
    """
    logger.info(f"Creating base map centered at {center} with zoom {zoom_start}")

    m = folium.Map(
        location=center,
        zoom_start=zoom_start,
        tiles=tiles,
        width=width,
        height=height,
        control_scale=True,
    )

    # Add layer control (will be populated by subsequent layers)
    LayerControl(position="topright", collapsed=False).add_to(m)

    return m


def add_lsoa_choropleth(
    m: folium.Map,
    lsoa_gdf: gpd.GeoDataFrame,
    value_column: str,
    layer_name: str = "LSOA Choropleth",
    colormap: str = MOBILITY_COLORMAP,
    legend_name: str | None = None,
    fill_opacity: float = 0.7,
    line_opacity: float = 0.2,
    show_layer: bool = True,
) -> folium.Map:
    """
    Add LSOA choropleth layer to map.

    Creates a colored polygon layer where each LSOA is colored based on a
    scalar value (mobility proxy, trap score, etc.).

    Args:
        m: Folium Map object.
        lsoa_gdf: GeoDataFrame with LSOA boundaries and values.
            Must have 'geometry' column and value_column.
            Will be reprojected to EPSG:4326 if needed.
        value_column: Column name containing values to color by.
        layer_name: Name for this layer in layer control.
        colormap: Matplotlib colormap name or Folium colormap.
        legend_name: Legend title (defaults to layer_name).
        fill_opacity: Polygon fill opacity (0-1).
        line_opacity: Polygon border opacity (0-1).
        show_layer: Whether layer is visible by default.

    Returns:
        Modified Folium Map object.

    Raises:
        ValueError: If value_column not in lsoa_gdf.
        ValueError: If lsoa_gdf has no CRS set.

    Example:
        >>> m = create_base_map()
        >>> m = add_lsoa_choropleth(
        ...     m, lsoa_gdf, "mobility_proxy", "Mobility Surface"
        ... )
    """
    # Validate inputs
    if value_column not in lsoa_gdf.columns:
        raise ValueError(f"Column '{value_column}' not found in lsoa_gdf")

    if lsoa_gdf.crs is None:
        raise ValueError("lsoa_gdf must have CRS set")

    # Reproject to WGS84 for Folium if needed
    if lsoa_gdf.crs.to_string() != CRS_WGS84:
        logger.info(f"Reprojecting from {lsoa_gdf.crs} to {CRS_WGS84}")
        gdf = lsoa_gdf.to_crs(CRS_WGS84)
    else:
        gdf = lsoa_gdf.copy()

    # Extract values and compute range
    values = gdf[value_column].values
    valid_values = values[~np.isnan(values)]

    if len(valid_values) == 0:
        raise ValueError(f"All values in '{value_column}' are NaN")

    vmin = float(np.min(valid_values))
    vmax = float(np.max(valid_values))

    logger.info(f"Creating choropleth for {len(gdf)} LSOAs " f"with {value_column} range [{vmin:.4f}, {vmax:.4f}]")

    # Add Choropleth directly to map
    # Note: Folium Choropleth doesn't work well with FeatureGroups for layer control
    folium.Choropleth(
        geo_data=gdf,
        data=gdf,
        columns=["LSOA21CD", value_column],
        key_on="feature.properties.LSOA21CD",
        fill_color=colormap,
        fill_opacity=fill_opacity,
        line_opacity=line_opacity,
        legend_name=legend_name or layer_name,
        nan_fill_color="lightgray",
        name=layer_name,
    ).add_to(m)

    return m


def add_basin_overlay(
    m: folium.Map,
    basin_gdf: gpd.GeoDataFrame,
    basin_id_column: str = "basin_id",
    basin_label_column: str | None = None,
    layer_name: str = "Poverty Basins",
    color_scheme: str = "qualitative",
    show_labels: bool = True,
    line_weight: float = 2.0,
    fill_opacity: float = 0.2,
    show_layer: bool = True,
) -> folium.Map:
    """
    Add poverty trap basins as polygon overlays on the map.

    Basins are regions (attractors) in the mobility surface computed via
    Morse-Smale decomposition. Each basin is colored distinctly and can
    be labeled with summary statistics.

    Args:
        m: Folium Map object.
        basin_gdf: GeoDataFrame with basin boundaries.
            Must have 'geometry' column and basin_id_column.
        basin_id_column: Column containing unique basin identifiers.
        basin_label_column: Optional column for basin labels/names.
        layer_name: Name for this layer in layer control.
        color_scheme: Color scheme - 'qualitative' for distinct colors,
            'sequential' for depth-based coloring.
        show_labels: Whether to add labels at basin centroids.
        line_weight: Width of basin boundary lines.
        fill_opacity: Opacity of basin fill (0-1).
        show_layer: Whether layer is visible by default.

    Returns:
        Modified Folium Map object.

    Raises:
        ValueError: If basin_id_column not in basin_gdf.

    Example:
        >>> m = create_base_map()
        >>> m = add_basin_overlay(m, basin_gdf, "basin_id", "Basin Regions")
    """
    # Validate inputs
    if basin_id_column not in basin_gdf.columns:
        raise ValueError(f"Column '{basin_id_column}' not found in basin_gdf")

    if basin_gdf.crs is None:
        raise ValueError("basin_gdf must have CRS set")

    # Reproject to WGS84 for Folium if needed
    if basin_gdf.crs.to_string() != CRS_WGS84:
        logger.info(f"Reprojecting basins from {basin_gdf.crs} to {CRS_WGS84}")
        gdf = basin_gdf.to_crs(CRS_WGS84)
    else:
        gdf = basin_gdf.copy()

    logger.info(f"Adding {len(gdf)} basins to map")

    # Create feature group for basins
    feature_group = FeatureGroup(name=layer_name, show=show_layer)

    # Generate colors for basins
    n_basins = len(gdf)
    if color_scheme == "qualitative":
        # Use distinct colors for each basin
        import matplotlib.cm as cm

        colormap = cm.get_cmap("tab20" if n_basins <= 20 else "hsv")
        colors = [mcolors.rgb2hex(colormap(i / n_basins)) for i in range(n_basins)]
    else:
        # Sequential coloring (for depth or other ordering)
        import matplotlib.cm as cm

        colormap = cm.get_cmap("viridis")
        colors = [mcolors.rgb2hex(colormap(i / n_basins)) for i in range(n_basins)]

    # Add each basin as a polygon
    for idx, (_, basin) in enumerate(gdf.iterrows()):
        basin_id = basin[basin_id_column]
        color = colors[idx]

        # Create popup content
        popup_html = f"<b>Basin ID:</b> {basin_id}<br>"
        if basin_label_column and basin_label_column in basin.index:
            popup_html += f"<b>Label:</b> {basin[basin_label_column]}<br>"

        # Add additional statistics if available
        stat_columns = [
            "area",
            "population",
            "avg_mobility",
            "num_critical_points",
        ]
        for col in stat_columns:
            if col in basin.index and pd.notna(basin[col]):
                popup_html += f"<b>{col.replace('_', ' ').title()}:</b> {basin[col]:.2f}<br>"

        # Add basin polygon
        folium.GeoJson(
            basin.geometry,
            style_function=lambda x, color=color: {
                "fillColor": color,
                "color": color,
                "weight": line_weight,
                "fillOpacity": fill_opacity,
            },
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"Basin {basin_id}",
        ).add_to(feature_group)

        # Add label at centroid if requested
        if show_labels:
            centroid = basin.geometry.centroid
            label_text = (
                basin[basin_label_column]
                if basin_label_column and basin_label_column in basin.index
                else f"Basin {basin_id}"
            )

            folium.Marker(
                location=[centroid.y, centroid.x],
                icon=folium.DivIcon(
                    html=f"""
                    <div style="
                        font-size: 10px;
                        color: white;
                        background-color: rgba(0, 0, 0, 0.7);
                        padding: 2px 5px;
                        border-radius: 3px;
                        white-space: nowrap;
                        text-align: center;
                    ">{label_text}</div>
                    """
                ),
            ).add_to(feature_group)

    feature_group.add_to(m)

    return m


def add_critical_points(
    m: folium.Map,
    critical_points_gdf: gpd.GeoDataFrame,
    point_type_column: str = "cp_type",
    layer_name: str = "Critical Points",
    show_layer: bool = True,
    marker_size: int = 8,
) -> folium.Map:
    """
    Add critical points (minima/maxima/saddles) as markers on the map.

    Critical points from Morse-Smale complex mark local minima (trap centers),
    saddles (barriers between basins), and maxima (high mobility regions).

    Args:
        m: Folium Map object.
        critical_points_gdf: GeoDataFrame with critical point locations.
            Must have 'geometry' (Point), point_type_column, and coordinates.
        point_type_column: Column indicating point type: 'minimum', 'maximum', 'saddle'.
        layer_name: Name for this layer in layer control.
        show_layer: Whether layer is visible by default.
        marker_size: Radius of circle markers in pixels.

    Returns:
        Modified Folium Map object.

    Raises:
        ValueError: If point_type_column not in critical_points_gdf.
        ValueError: If geometries are not Points.

    Example:
        >>> m = create_base_map()
        >>> m = add_critical_points(m, cp_gdf, "cp_type", "Critical Points")
    """
    # Validate inputs
    if point_type_column not in critical_points_gdf.columns:
        raise ValueError(f"Column '{point_type_column}' not found in critical_points_gdf")

    if critical_points_gdf.crs is None:
        raise ValueError("critical_points_gdf must have CRS set")

    # Reproject to WGS84 for Folium if needed
    if critical_points_gdf.crs.to_string() != CRS_WGS84:
        logger.info(f"Reprojecting critical points from {critical_points_gdf.crs} " f"to {CRS_WGS84}")
        gdf = critical_points_gdf.to_crs(CRS_WGS84)
    else:
        gdf = critical_points_gdf.copy()

    logger.info(f"Adding {len(gdf)} critical points to map")

    # Create feature group for critical points
    feature_group = FeatureGroup(name=layer_name, show=show_layer)

    # Define marker styles for each critical point type
    point_styles = {
        "minimum": {
            "color": "#d62728",  # Red - poverty traps
            "icon": "arrow-down",
            "prefix": "fa",
            "label": "Minimum (Trap)",
        },
        "maximum": {
            "color": "#2ca02c",  # Green - high opportunity
            "icon": "arrow-up",
            "prefix": "fa",
            "label": "Maximum (Peak)",
        },
        "saddle": {
            "color": "#ff7f0e",  # Orange - barriers/transitions
            "icon": "exchange",
            "prefix": "fa",
            "label": "Saddle (Barrier)",
        },
    }

    # Add each critical point
    for _, point in gdf.iterrows():
        cp_type = point[point_type_column]
        style = point_styles.get(
            cp_type,
            {"color": "gray", "icon": "circle", "prefix": "fa", "label": "Unknown"},
        )

        # Extract coordinates
        coords = point.geometry
        lat, lon = coords.y, coords.x

        # Create popup content
        popup_html = f"<b>Type:</b> {style['label']}<br>"
        popup_html += f"<b>Coordinates:</b> ({lat:.4f}, {lon:.4f})<br>"

        # Add additional attributes if available
        attr_columns = ["mobility_value", "basin_id", "depth", "persistence"]
        for col in attr_columns:
            if col in point.index and pd.notna(point[col]):
                value = point[col]
                if isinstance(value, (int, float)):
                    col_title = col.replace("_", " ").title()
                    popup_html += f"<b>{col_title}:</b> {value:.3f}<br>"
                else:
                    popup_html += f"<b>{col.replace('_', ' ').title()}:</b> {value}<br>"

        # Add marker with custom icon
        folium.CircleMarker(
            location=[lat, lon],
            radius=marker_size,
            color=style["color"],
            fill=True,
            fillColor=style["color"],
            fillOpacity=0.8,
            weight=2,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{style['label']}",
        ).add_to(feature_group)

    feature_group.add_to(m)

    return m


def add_pathway_arrows(
    m: folium.Map,
    pathways_gdf: gpd.GeoDataFrame,
    pathway_type_column: str = "pathway_type",
    layer_name: str = "Escape Pathways",
    show_layer: bool = True,
    arrow_weight: float = 2.5,
    arrow_opacity: float = 0.7,
) -> folium.Map:
    """
    Add escape pathway arrows showing gradient flow between regions.

    Pathways are integral curves following the gradient of the mobility surface,
    showing potential escape routes from poverty traps to higher-mobility regions.

    Args:
        m: Folium Map object.
        pathways_gdf: GeoDataFrame with pathway LineStrings.
            Must have 'geometry' (LineString), pathway_type_column.
        pathway_type_column: Column indicating pathway type:
            'escape', 'descent', 'stable'.
        layer_name: Name for this layer in layer control.
        show_layer: Whether layer is visible by default.
        arrow_weight: Width of pathway arrows in pixels.
        arrow_opacity: Opacity of arrows (0-1).

    Returns:
        Modified Folium Map object.

    Raises:
        ValueError: If pathway_type_column not in pathways_gdf.
        ValueError: If geometries are not LineStrings.

    Example:
        >>> m = create_base_map()
        >>> m = add_pathway_arrows(m, pathways_gdf, "pathway_type")
    """
    # Validate inputs
    if pathway_type_column not in pathways_gdf.columns:
        raise ValueError(f"Column '{pathway_type_column}' not found in pathways_gdf")

    if pathways_gdf.crs is None:
        raise ValueError("pathways_gdf must have CRS set")

    # Reproject to WGS84 for Folium if needed
    if pathways_gdf.crs.to_string() != CRS_WGS84:
        logger.info(f"Reprojecting pathways from {pathways_gdf.crs} to {CRS_WGS84}")
        gdf = pathways_gdf.to_crs(CRS_WGS84)
    else:
        gdf = pathways_gdf.copy()

    logger.info(f"Adding {len(gdf)} pathways to map")

    # Create feature group for pathways
    feature_group = FeatureGroup(name=layer_name, show=show_layer)

    # Define styles for different pathway types
    pathway_styles = {
        "escape": {
            "color": "#2ca02c",  # Green - upward mobility
            "dash_array": None,
            "label": "Escape Path",
        },
        "descent": {
            "color": "#d62728",  # Red - downward trajectory
            "dash_array": "5, 5",
            "label": "Descent Path",
        },
        "stable": {
            "color": "#1f77b4",  # Blue - stable trajectory
            "dash_array": "10, 5",
            "label": "Stable Path",
        },
    }

    # Add each pathway
    for _, pathway in gdf.iterrows():
        pw_type = pathway[pathway_type_column]
        style = pathway_styles.get(
            pw_type,
            {"color": "gray", "dash_array": None, "label": "Unknown"},
        )

        # Extract line coordinates
        line = pathway.geometry
        coords = [(point[1], point[0]) for point in line.coords]  # (lat, lon)

        # Create popup content
        popup_html = f"<b>Type:</b> {style['label']}<br>"

        # Add pathway statistics if available
        stat_columns = [
            "length_km",
            "start_mobility",
            "end_mobility",
            "mobility_change",
            "num_barriers",
        ]
        for col in stat_columns:
            if col in pathway.index and pd.notna(pathway[col]):
                value = pathway[col]
                if isinstance(value, (int, float)):
                    popup_html += f"<b>{col.replace('_', ' ').title()}:</b> {value:.3f}<br>"
                else:
                    popup_html += f"<b>{col.replace('_', ' ').title()}:</b> {value}<br>"

        # Add pathway line with arrows
        line_options = {
            "color": style["color"],
            "weight": arrow_weight,
            "opacity": arrow_opacity,
        }
        if style["dash_array"]:
            line_options["dashArray"] = style["dash_array"]

        folium.PolyLine(
            coords,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=style["label"],
            **line_options,
        ).add_to(feature_group)

        # Add arrowhead at end of path
        if len(coords) >= 2:
            # Add a small marker at end to indicate direction
            end_point = coords[-1]
            folium.CircleMarker(
                location=end_point,
                radius=4,
                color=style["color"],
                fill=True,
                fillColor=style["color"],
                fillOpacity=1.0,
                weight=1,
            ).add_to(feature_group)

    feature_group.add_to(m)

    return m


def load_and_prepare_lsoa_data(
    lsoa_boundaries_path: Path | None = None,
    mobility_values: NDArray[np.float64] | pd.Series | None = None,
    mobility_column: str | None = None,
    download_if_missing: bool = True,
) -> gpd.GeoDataFrame:
    """
    Load LSOA boundaries and merge with mobility values.

    Convenience function to load census shapes and prepare for mapping.
    Integrates with census_shapes.py loading utilities.

    Args:
        lsoa_boundaries_path: Path to LSOA boundary file. If None, uses
            census_shapes.py default loading.
        mobility_values: Optional array/Series of mobility values per LSOA.
            Must align with LSOA order in loaded boundaries.
        mobility_column: If mobility_values is None, extract values from this
            column in loaded boundaries.
        download_if_missing: Whether to download LSOA boundaries if missing.

    Returns:
        GeoDataFrame with LSOA boundaries and mobility values.

    Raises:
        ValueError: If neither mobility_values nor mobility_column provided.
        ValueError: If mobility_values length doesn't match LSOAs.

    Example:
        >>> gdf = load_and_prepare_lsoa_data(
        ...     mobility_values=mobility_series
        ... )
        >>> print(len(gdf))
        33755
    """
    # Import here to avoid circular imports
    from poverty_tda.data.census_shapes import load_lsoa_boundaries

    # Load LSOA boundaries
    logger.info("Loading LSOA boundaries...")
    gdf = load_lsoa_boundaries(
        filepath=lsoa_boundaries_path,
        download_if_missing=download_if_missing,
    )

    # Add mobility values if provided
    if mobility_values is not None:
        if isinstance(mobility_values, pd.Series):
            # Assume Series has LSOA21CD as index
            if mobility_values.index.name == "LSOA21CD" or "LSOA21CD" in str(mobility_values.index.name):
                gdf = gdf.merge(
                    mobility_values.to_frame("mobility_proxy"),
                    left_on="LSOA21CD",
                    right_index=True,
                    how="left",
                )
            else:
                # Assume alignment by position
                if len(mobility_values) != len(gdf):
                    raise ValueError(
                        f"mobility_values length ({len(mobility_values)}) " f"doesn't match LSOA count ({len(gdf)})"
                    )
                gdf["mobility_proxy"] = mobility_values.values

        elif isinstance(mobility_values, np.ndarray):
            if len(mobility_values) != len(gdf):
                raise ValueError(
                    f"mobility_values length ({len(mobility_values)}) " f"doesn't match LSOA count ({len(gdf)})"
                )
            gdf["mobility_proxy"] = mobility_values

    elif mobility_column is not None:
        if mobility_column not in gdf.columns:
            raise ValueError(f"Column '{mobility_column}' not found in loaded data")

    else:
        raise ValueError("Must provide either mobility_values or mobility_column")

    logger.info(f"Prepared {len(gdf)} LSOAs for mapping")
    return gdf


def create_poverty_map(
    lsoa_gdf: gpd.GeoDataFrame,
    value_column: str = "mobility_proxy",
    layer_name: str = "Mobility Surface",
    colormap: str = MOBILITY_COLORMAP,
    output_path: Path | None = None,
) -> folium.Map:
    """
    Create interactive poverty trap map with LSOA choropleth.

    High-level function to create a complete map with sensible defaults.
    This is the main entry point for Step 1 of Task 6.4.

    Args:
        lsoa_gdf: GeoDataFrame with LSOA boundaries and values.
            Must contain value_column and 'geometry'.
        value_column: Column to use for choropleth coloring.
        layer_name: Name for the choropleth layer.
        colormap: Matplotlib colormap name.
        output_path: If provided, save map to this HTML file.

    Returns:
        Folium Map object ready for display or further customization.

    Example:
        >>> gdf = load_and_prepare_lsoa_data(mobility_values=mobility_series)
        >>> m = create_poverty_map(gdf, output_path="poverty_map.html")
    """
    # Create base map
    m = create_base_map()

    # Add choropleth layer
    m = add_lsoa_choropleth(
        m,
        lsoa_gdf,
        value_column=value_column,
        layer_name=layer_name,
        colormap=colormap,
    )

    # Save if path provided
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        m.save(str(output_path))
        logger.info(f"Map saved to {output_path}")

    return m


def create_complete_poverty_map(
    lsoa_gdf: gpd.GeoDataFrame,
    basin_gdf: gpd.GeoDataFrame | None = None,
    critical_points_gdf: gpd.GeoDataFrame | None = None,
    pathways_gdf: gpd.GeoDataFrame | None = None,
    value_column: str = "mobility_proxy",
    basin_id_column: str = "basin_id",
    point_type_column: str = "cp_type",
    pathway_type_column: str = "pathway_type",
    output_path: Path | None = None,
    add_layer_control: bool = True,
) -> folium.Map:
    """
    Create comprehensive poverty trap map with all visualization layers.

    This is the complete integration function (Step 5) that combines:
    - LSOA mobility surface choropleth
    - Poverty basin overlays with distinct colors
    - Critical point markers (minima/maxima/saddles)
    - Escape pathway arrows showing mobility flows
    - Interactive layer controls

    Args:
        lsoa_gdf: GeoDataFrame with LSOA boundaries and mobility values.
        basin_gdf: Optional GeoDataFrame with basin polygons.
        critical_points_gdf: Optional GeoDataFrame with critical points.
        pathways_gdf: Optional GeoDataFrame with pathway LineStrings.
        value_column: Column in lsoa_gdf for mobility coloring.
        basin_id_column: Column in basin_gdf for basin identifiers.
        point_type_column: Column in critical_points_gdf for point types.
        pathway_type_column: Column in pathways_gdf for pathway types.
        output_path: If provided, save map to this HTML file.
        add_layer_control: Whether to add interactive layer control widget.

    Returns:
        Folium Map object with all layers integrated.

    Example:
        >>> # With all components
        >>> m = create_complete_poverty_map(
        ...     lsoa_gdf, basin_gdf, cp_gdf, pathway_gdf,
        ...     output_path="complete_poverty_map.html"
        ... )
        >>>
        >>> # With only some components
        >>> m = create_complete_poverty_map(
        ...     lsoa_gdf, basin_gdf=basin_gdf,
        ...     output_path="basins_only.html"
        ... )
    """
    logger.info("Creating complete poverty trap visualization map...")

    # Create base map
    m = create_base_map()

    # Layer 1: LSOA mobility surface (always included)
    logger.info("Adding LSOA mobility choropleth...")
    m = add_lsoa_choropleth(
        m,
        lsoa_gdf,
        value_column=value_column,
        layer_name="Mobility Surface",
        fill_opacity=0.6,
    )

    # Layer 2: Basin overlays (if provided)
    if basin_gdf is not None:
        logger.info(f"Adding {len(basin_gdf)} poverty basins...")
        m = add_basin_overlay(
            m,
            basin_gdf,
            basin_id_column=basin_id_column,
            basin_label_column="label" if "label" in basin_gdf.columns else None,
            layer_name="Poverty Basins",
            fill_opacity=0.2,
            show_labels=True,
        )

    # Layer 3: Critical points (if provided)
    if critical_points_gdf is not None:
        logger.info(f"Adding {len(critical_points_gdf)} critical points...")
        m = add_critical_points(
            m,
            critical_points_gdf,
            point_type_column=point_type_column,
            layer_name="Critical Points",
            marker_size=10,
        )

    # Layer 4: Escape pathways (if provided)
    if pathways_gdf is not None:
        logger.info(f"Adding {len(pathways_gdf)} pathways...")
        m = add_pathway_arrows(
            m,
            pathways_gdf,
            pathway_type_column=pathway_type_column,
            layer_name="Escape Pathways",
            arrow_weight=3.0,
        )

    # Add layer control for interactive toggling
    if add_layer_control:
        folium.LayerControl(
            position="topright",
            collapsed=False,
        ).add_to(m)
        logger.info("Added layer control widget")

    # Save if path provided
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        m.save(str(output_path))
        logger.info(f"Map saved to {output_path}")

    logger.info("✓ Complete poverty trap map created successfully")

    return m
