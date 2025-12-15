# Poverty Trap Visualization Module

Interactive geographic maps for visualizing poverty traps, basin memberships, escape routes, and intervention gateways across England and Wales at LSOA level.

## Overview

This module provides Folium-based interactive HTML maps that combine:
- **LSOA Choropleth**: Mobility surface colored by mobility proxy values
- **Basin Overlays**: Poverty trap basins with distinct colors
- **Critical Points**: Morse-Smale critical points (minima, maxima, saddles)
- **Escape Pathways**: Gradient flow lines showing potential escape routes
- **Interactive Controls**: Layer toggles, popups, and tooltips

## Files

### Core Module
- **`maps.py`**: Main visualization functions
  - `create_base_map()`: Initialize Folium map centered on England/Wales
  - `add_lsoa_choropleth()`: Add LSOA mobility surface layer
  - `add_basin_overlay()`: Add poverty basin polygons
  - `add_critical_points()`: Add critical point markers
  - `add_pathway_arrows()`: Add escape pathway arrows
  - `create_complete_poverty_map()`: **Main integration function**

### Test Files
- **`test_step1_map.py`**: LSOA choropleth foundation
- **`test_step2_basins.py`**: Basin overlays
- **`test_step3_critical_points.py`**: Critical point markers
- **`test_step4_pathways.py`**: Pathway arrows
- **`test_step5_complete.py`**: **Complete integration with all layers**

### Outputs
- **`outputs/poverty_map_step1.html`**: Step 1 output
- **`outputs/poverty_map_step2.html`**: Step 2 output
- **`outputs/poverty_map_step3.html`**: Step 3 output
- **`outputs/poverty_map_step4.html`**: Step 4 output
- **`outputs/poverty_map_complete.html`**: **Final complete map**

## Usage

### Quick Start

```python
from poverty_tda.viz.maps import create_complete_poverty_map
from poverty_tda.data.census_shapes import load_lsoa_boundaries

# Load LSOA boundaries
lsoa_gdf = load_lsoa_boundaries()

# Add your mobility values
lsoa_gdf["mobility_proxy"] = your_mobility_values

# Create complete map with all layers
m = create_complete_poverty_map(
    lsoa_gdf=lsoa_gdf,
    basin_gdf=your_basins,           # Optional
    critical_points_gdf=your_cps,    # Optional
    pathways_gdf=your_pathways,      # Optional
    output_path="poverty_map.html",
)
```

### Step-by-Step Usage

```python
from poverty_tda.viz.maps import (
    create_base_map,
    add_lsoa_choropleth,
    add_basin_overlay,
    add_critical_points,
    add_pathway_arrows,
)

# 1. Create base map
m = create_base_map()

# 2. Add LSOA mobility surface
m = add_lsoa_choropleth(
    m, lsoa_gdf,
    value_column="mobility_proxy",
    layer_name="Mobility Surface",
)

# 3. Add basin overlays
m = add_basin_overlay(
    m, basin_gdf,
    basin_id_column="basin_id",
    layer_name="Poverty Basins",
)

# 4. Add critical points
m = add_critical_points(
    m, critical_points_gdf,
    point_type_column="cp_type",
    layer_name="Critical Points",
)

# 5. Add pathways
m = add_pathway_arrows(
    m, pathways_gdf,
    pathway_type_column="pathway_type",
    layer_name="Escape Pathways",
)

# 6. Add layer control and save
import folium
folium.LayerControl(position="topright").add_to(m)
m.save("poverty_map.html")
```

## Data Requirements

### LSOA GeoDataFrame
Required columns:
- `geometry`: Polygon/MultiPolygon boundaries
- `LSOA21CD`: LSOA code
- `[value_column]`: Numeric mobility/trap values

### Basin GeoDataFrame (Optional)
Required columns:
- `geometry`: Polygon boundaries
- `basin_id`: Unique basin identifier
- `label`: Optional basin name/label
- `avg_mobility`, `area`, `population`: Optional statistics

### Critical Points GeoDataFrame (Optional)
Required columns:
- `geometry`: Point locations
- `cp_type`: One of "minimum", "maximum", "saddle"
- `mobility_value`: Value at critical point
- `depth`, `persistence`: Optional topology measures

### Pathways GeoDataFrame (Optional)
Required columns:
- `geometry`: LineString paths
- `pathway_type`: One of "escape", "descent", "stable"
- `start_mobility`, `end_mobility`: Optional endpoint values
- `length_km`, `num_barriers`: Optional path statistics

## Running Tests

```bash
# Individual steps
python poverty_tda/viz/test_step1_map.py
python poverty_tda/viz/test_step2_basins.py
python poverty_tda/viz/test_step3_critical_points.py
python poverty_tda/viz/test_step4_pathways.py

# Complete integration
python poverty_tda/viz/test_step5_complete.py
```

All tests use mock data and generate HTML maps in `outputs/` directory.

## Map Features

### Interactive Elements
- **Pan & Zoom**: Explore different regions
- **Layer Control**: Toggle layers on/off (top-right)
- **Popups**: Click elements for detailed information
- **Tooltips**: Hover for quick labels

### Color Schemes
- **Mobility Surface**: RdYlGn (red=low, green=high)
- **Basins**: Distinct qualitative colors (tab20/hsv)
- **Critical Points**:
  - Red circles = Minima (poverty traps)
  - Orange circles = Saddles (barriers)
  - Green circles = Maxima (opportunities)
- **Pathways**:
  - Green solid = Escape paths (upward mobility)
  - Red dashed = Descent paths (downward)
  - Blue dashed = Stable paths

## Integration with Other Modules

- **`census_shapes.py`**: LSOA boundary loading
- **`trap_identification.py`**: Basin computation and trap scoring
- **`pathways.py`**: Integral line computation
- **`mobility_surface.py`**: Scalar field generation
- **`morse_smale.py`**: Critical point extraction

## Technical Details

- **Coordinate System**: All data reprojected to EPSG:4326 (WGS84) for Folium
- **Map Library**: Folium (Leaflet.js wrapper)
- **Base Map**: OpenStreetMap tiles
- **Output Format**: Interactive HTML files

## Development Status

✅ **Task 6.4 Complete** - All 5 visualization steps implemented:
1. ✅ Map Foundation & LSOA Choropleth
2. ✅ Basin Overlay & Color Coding
3. ✅ Critical Points & Barrier Markers
4. ✅ Pathway Arrows & Flow Visualization
5. ✅ Interactive Controls & Full Integration

## Future Enhancements

Potential additions (not currently implemented):
- Heatmap layers for density visualization
- Animated temporal changes
- 3D terrain representation
- Custom marker icons
- Export to static images
- Integration with web frameworks (Dash, Streamlit)

## License

Open Government Licence v3.0

## References

- Folium documentation: https://python-visualization.github.io/folium/
- ONS Geography: https://geoportal.statistics.gov.uk/
- Leaflet.js: https://leafletjs.com/
