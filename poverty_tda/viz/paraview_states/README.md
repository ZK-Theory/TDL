# 3D Opportunity Terrain Visualization

This directory contains scripts for generating 3D terrain visualizations of poverty opportunity landscapes across England and Wales.

## Scripts

### `terrain_3d_paraview.py` - Native ParaView Script (Recommended)
Uses ParaView's native Python API (pvpython) to create visualizations with proper ParaView state file (.pvsm) generation.

**Usage:**
```bash
pvpython poverty_tda/viz/paraview_states/terrain_3d_paraview.py \
    --vti-path data/mobility_surface.vti \
    --output-dir poverty_tda/viz/outputs
```

**Requires:** ParaView 5.x or 6.x with Python bindings

**Outputs:**
- PNG renders from multiple camera angles
- `.pvsm` ParaView state file for interactive visualization

### `terrain_3d.py` - PyVista Script (Standalone Alternative)
Uses PyVista for visualization without requiring ParaView installation. Can run in project's virtual environment.

**Usage:**
```bash
python poverty_tda/viz/paraview_states/terrain_3d.py \
    --resolution 100 \
    --show-critical-pts \
    --output-dir poverty_tda/viz/outputs
```

**Requires:** `pip install pyvista matplotlib numpy pandas scipy`

**Outputs:**
- PNG renders with mobility/basin coloring
- Critical point glyph annotations
- No ParaView state file

## Overview

The `terrain_3d.py` script creates 3D terrain visualizations where:
- **Height** represents mobility proxy values (higher terrain = better opportunity)
- **Color** can represent either:
  - Continuous mobility values (red-yellow-green colormap)
  - Categorical basin membership (distinct colors per poverty trap basin)
- **Glyphs** annotate critical points:
  - Red spheres = minima (poverty trap centers)
  - Green cones = maxima (opportunity peaks)
  - Orange cubes = saddles (barriers between basins)

## Requirements

```bash
pip install pyvista matplotlib numpy pandas scipy
```

## Basic Usage

### Generate Sample Terrain (Quick Test)

```bash
python poverty_tda/viz/paraview_states/terrain_3d.py \
    --resolution 100 \
    --output-dir poverty_tda/viz/outputs
```

This generates a synthetic mobility surface with 5 basins and renders from 3 camera angles.

### Render with Critical Points

```bash
python poverty_tda/viz/paraview_states/terrain_3d.py \
    --resolution 100 \
    --show-critical-pts \
    --persistence-threshold 0.08 \
    --output-dir poverty_tda/viz/outputs
```

Adds glyph markers and labels for significant critical points (minima, maxima, saddles).

### Use Real Data (VTI File)

```bash
python poverty_tda/viz/paraview_states/terrain_3d.py \
    --vti-path poverty_tda/data/processed/mobility_surface.vti \
    --critical-pts poverty_tda/data/processed/critical_points.csv \
    --show-critical-pts \
    --height-scale 0.0001 \
    --color-mode both \
    --output-dir poverty_tda/viz/outputs
```

## Command-Line Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--vti-path` | Path | None | Path to VTK ImageData file (`.vti`). If not provided, generates sample surface. |
| `--critical-pts` | Path | None | Path to critical points CSV. If not provided with `--show-critical-pts`, generates from surface. |
| `--basins-csv` | Path | None | Path to basin membership CSV (currently unused, basins embedded in VTI). |
| `--output-dir` | Path | `poverty_tda/viz/outputs` | Output directory for PNG renders. |
| `--height-scale` | Float | 0.0001 | Vertical exaggeration factor. Increase for more dramatic terrain. |
| `--resolution` | Int | 100 | Grid resolution for sample surface generation (50-200 recommended). |
| `--color-mode` | Choice | `both` | Color mode: `mobility`, `basins`, or `both`. |
| `--show-critical-pts` | Flag | False | Enable critical point glyphs and labels. |
| `--persistence-threshold` | Float | 0.05 | Minimum persistence value for critical point text labels. |
| `--enable-shadows` | Flag | False | Enable shadow rendering (slower but better depth perception). |

## Output Files

The script generates PNG renders for each camera view and color mode:

### Standard Renders (without `--show-critical-pts`)
- `terrain_overview_mobility.png` - Bird's eye view with mobility coloring
- `terrain_overview_basins.png` - Bird's eye view with basin coloring
- `terrain_oblique_mobility.png` - 45° angle with mobility coloring
- `terrain_oblique_basins.png` - 45° angle with basin coloring
- `terrain_north_west_mobility.png` - Regional zoom (Manchester/Liverpool area) with mobility
- `terrain_north_west_basins.png` - Regional zoom with basins

### With Critical Points (`--show-critical-pts`)
- `terrain_overview_with_cps.png` - Overview with annotated critical points
- `terrain_oblique_with_cps.png` - Oblique view with glyphs
- `terrain_north_west_with_cps.png` - Regional zoom with annotations

## Camera Views

### Overview
- **Description:** Bird's eye view directly above terrain center
- **Use case:** Full England/Wales extent visualization
- **Camera position:** Directly above at 1.2× terrain extent

### Oblique
- **Description:** 45-degree angled view showing terrain depth
- **Use case:** General presentation and depth perception
- **Camera position:** Southwest of center at 0.8× extent distance, 0.6× extent height

### North West
- **Description:** Regional zoom on North West England (Manchester/Liverpool area)
- **Use case:** Detailed regional analysis
- **Focus coordinates:** (350000, 400000) in EPSG:27700
- **Extent:** 150km × 150km region

## Data Formats

### Input VTI File
VTK ImageData (`.vti`) file with:
- **Scalar field:** `mobility` (required) - mobility proxy values [0, 1]
- **Scalar field:** `basin_id` (optional) - integer basin membership
- **Coordinates:** EPSG:27700 (British National Grid)
- **Dimensions:** Recommended 500×500 for England/Wales

Generated by `poverty_tda.topology.mobility_surface.export_mobility_vtk()`.

### Critical Points CSV
CSV file with columns:
- `x`, `y`, `z` - Coordinates (EPSG:27700 + scaled z)
- `value` - Scalar field value at critical point
- `point_type` - Integer type: 0=minimum, 1=saddle, 2=maximum
- `persistence` - Topological persistence value (optional)

Generated by `poverty_tda.topology.morse_smale.compute_morse_smale()`.

## Visualization Parameters

### Height Scaling
The `--height-scale` parameter controls vertical exaggeration:
- **Default:** 0.0001 (mobility [0,1] → 0-100m visual height)
- **Increase** for more dramatic terrain (e.g., 0.0002)
- **Decrease** for subtler elevation changes (e.g., 0.00005)

### Glyph Sizing
Critical point glyph sizes scale with persistence:
```python
radius = GLYPH_BASE_SCALE × (1.0 + persistence × GLYPH_PERSISTENCE_FACTOR)
```
- `GLYPH_BASE_SCALE = 5000.0` meters
- `GLYPH_PERSISTENCE_FACTOR = 2.0`

Modify these constants in `terrain_3d.py` for different glyph sizes.

### Lighting Configuration
Three-point lighting setup:
- **Key light:** Main illumination from above-left (-5e5, 5e5, 8e5), intensity 0.8
- **Fill light:** Softer right illumination (5e5, 3e5, 5e5), intensity 0.3
- **Rim light:** Subtle backlighting (0, -5e5, 4e5), intensity 0.2

## Performance Tips

1. **Resolution:** Start with `--resolution 50` for testing, use 100-200 for final renders
2. **Shadows:** Omit `--enable-shadows` for faster rendering (10-20% speedup)
3. **Color mode:** Use `--color-mode mobility` or `--color-mode basins` instead of `both` to halve render time
4. **Window size:** Modify `DEFAULT_WINDOW_SIZE = (1920, 1080)` in script for different resolutions

## Integration with Pipeline

### Step 1: Generate Mobility Surface
```python
from poverty_tda.topology.mobility_surface import (
    create_mobility_grid,
    interpolate_surface,
    export_mobility_vtk,
)

# Create grid and interpolate
centroids, values, grid_xy, meta = create_mobility_grid(lsoa_gdf, mobility_values)
surface = interpolate_surface(centroids, values, grid_xy[..., 0], grid_xy[..., 1])

# Export to VTI
vtk_path = export_mobility_vtk(
    grid_xy[..., 0], grid_xy[..., 1], surface,
    "poverty_tda/data/processed/mobility_surface.vti"
)
```

### Step 2: Compute Critical Points
```python
from poverty_tda.topology.morse_smale import compute_morse_smale

# Compute Morse-Smale complex
ms_result = compute_morse_smale(vtk_path, persistence_threshold=0.01)

# Extract critical points to CSV
import pandas as pd
cp_data = []
for cp in ms_result.critical_points:
    cp_data.append({
        "x": cp.position[0],
        "y": cp.position[1],
        "z": cp.position[2],
        "value": cp.value,
        "point_type": cp.point_type,
        "persistence": cp.persistence,
    })

df = pd.DataFrame(cp_data)
df.to_csv("poverty_tda/data/processed/critical_points.csv", index=False)
```

### Step 3: Render 3D Terrain
```bash
python poverty_tda/viz/paraview_states/terrain_3d.py \
    --vti-path poverty_tda/data/processed/mobility_surface.vti \
    --critical-pts poverty_tda/data/processed/critical_points.csv \
    --show-critical-pts \
    --color-mode both \
    --output-dir poverty_tda/viz/outputs
```

## Troubleshooting

### PyVista Installation Issues
If you encounter VTK/PyVista installation errors:
```bash
# Try installing from conda-forge
conda install -c conda-forge pyvista

# Or use pip with specific version
pip install pyvista==0.43.0
```

### Off-screen Rendering Errors
If running on a headless server without display:
```python
# Ensure Xvfb is installed (Linux)
sudo apt-get install xvfb

# Or use Mesa software rendering
export PYVISTA_OFF_SCREEN=true
```

### Memory Issues
For high-resolution surfaces (>500×500):
```bash
# Reduce resolution or use chunked rendering
python terrain_3d.py --resolution 200  # Instead of 500
```

### Critical Points Not Visible
If glyphs are too small or large:
- Adjust `GLYPH_BASE_SCALE` in `terrain_3d.py` (line 78)
- Modify `--height-scale` to match glyph scaling

## Examples

### Minimal Example (Fast)
```bash
python terrain_3d.py --resolution 50
```
**Output:** 6 renders (3 views × 2 color modes), ~10 seconds

### Standard Example (Production)
```bash
python terrain_3d.py \
    --resolution 100 \
    --show-critical-pts \
    --color-mode both
```
**Output:** 6 renders with critical point annotations, ~30 seconds

### High-Quality Example (Publication)
```bash
python terrain_3d.py \
    --vti-path data/mobility_surface_500x500.vti \
    --critical-pts data/critical_points_ttk.csv \
    --show-critical-pts \
    --persistence-threshold 0.1 \
    --height-scale 0.00015 \
    --enable-shadows \
    --color-mode both \
    --resolution 500
```
**Output:** High-resolution renders with shadows, ~2-3 minutes

## Citation

When using this visualization in publications, please cite:

> TDL: Topological Data Analysis for Poverty and Financial Markets
> https://github.com/stephendor/TDL

## License

Open Government Licence v3.0

## Contact

For questions or issues, please open an issue on the GitHub repository.
