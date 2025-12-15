# Financial Regime Comparison ParaView Visualization

This directory contains scripts for creating side-by-side visualizations comparing the topological structure of financial market regimes using Rips complex evolution and persistence diagrams.

## Overview

The visualization pipeline compares:
- **Crisis Period:** Aug-Oct 2008 (Global Financial Crisis / Lehman Brothers collapse)
- **Normal Period:** Apr-Jun 2007 (Pre-crisis normal market conditions)

## Generated Outputs

All outputs are saved to `financial_tda/viz/outputs/`:

### 1. Static Renders
- **`regime_compare_side_by_side.png`** - PyVista side-by-side Rips complex visualization
- **`regime_compare_side_by_side_paraview.png`** - ParaView native GPU-accelerated render
- **`persistence_overlay.png`** - Combined persistence diagram (crisis vs normal)

### 2. Animations
- **`filtration_animation.gif`** - Animated GIF showing Rips complex evolution (592KB, 30 frames)
- **`animation_frames/`** - Individual PNG frames for the animation

### 3. Interactive Files
- **`regime_compare_paraview.pvsm`** - ParaView state file for interactive 3D exploration
- **`crisis_rips_edges.vtp`** - VTK PolyData with crisis period edges
- **`normal_rips_edges.vtp`** - VTK PolyData with normal period edges
- **`crisis_embedding.vtp`** - VTK PolyData with crisis point cloud
- **`normal_embedding.vtp`** - VTK PolyData with normal point cloud

### 4. Metadata
- **`regime_metadata.json`** - Parameters and statistics for the analysis

## Scripts

- **`regime_compare.py`** - Main pipeline (Steps 1-3: data prep, visualization, persistence)
- **`regime_compare_paraview_only.py`** - ParaView-only rendering (requires pvpython)
- **`regime_animation.py`** - Filtration sweep animation generator
- **`TTK_INTEGRATION.md`** - Guide for Topology ToolKit integration

## Usage

### Quick Start (PyVista Fallback)

```bash
# Activate virtual environment
source .venv/Scripts/activate  # Git Bash on Windows
# or
.venv\Scripts\activate.ps1     # PowerShell

# Run the main script
python financial_tda/viz/paraview_scripts/regime_compare.py
```

This generates all visualizations using PyVista (no ParaView installation required).

### ParaView Native Rendering

For GPU-accelerated ParaView visualization:

```bash
# Step 1: Generate VTK data files with Python
python financial_tda/viz/paraview_scripts/regime_compare.py

# Step 2: Generate ParaView renders with pvpython
"C:/Program Files/ParaView 6.0.1/bin/pvpython.exe" \
  financial_tda/viz/paraview_scripts/regime_compare_paraview_only.py
```

### Interactive Exploration in ParaView GUI

1. Open ParaView application
2. **File → Load State** → Select `financial_tda/viz/outputs/regime_compare_paraview.pvsm`
3. Interact with the 3D visualization:
   - Rotate: Left-click drag
   - Zoom: Scroll wheel
   - Pan: Middle-click drag or Shift + Left-click drag
4. **File → Save Screenshot** to export high-resolution images

### Create Filtration Animation

Generate an animated GIF showing how the Rips complex evolves:

```bash
python financial_tda/viz/paraview_scripts/regime_animation.py \
  --output-dir financial_tda/viz/outputs \
  --n-frames 60 \
  --fps 10
```

Options:
- `--n-frames`: Number of animation frames (default: 60)
- `--fps`: Frames per second (default: 10)
- Output: `filtration_animation.gif` and individual frames in `animation_frames/`

## Command-Line Options

```bash
python regime_compare.py [OPTIONS]

Options:
  --output-dir PATH       Output directory (default: financial_tda/viz/outputs)
  --symbol TEXT          Market ticker (default: ^GSPC for S&P 500)
  --dimension INT        Takens embedding dimension (default: 3)
  --delay INT            Takens delay parameter (default: 5)
  --help                 Show help message
```

### Examples

```bash
# Use different time periods (modify CRISIS_PERIOD/NORMAL_PERIOD in script)
python regime_compare.py --output-dir custom_outputs/

# Analyze different market index
python regime_compare.py --symbol ^DJI  # Dow Jones

# Higher-dimensional embedding
python regime_compare.py --dimension 4 --delay 7
```

## Visualization Components

### 1. Side-by-Side Rips Complex (Step 2)

**Purpose:** Compare the graph structure of embedded financial time series

**Features:**
- Crisis period (left, red): Higher filtration threshold (0.0725)
- Normal period (right, green): Lower filtration threshold (0.0144)
- Point glyphs show Takens embedding coordinates
- Edge network reveals topological connectivity

**Interpretation:**
- Crisis shows **more dispersed phase space** (higher threshold needed)
- Normal shows **more compact, clustered structure**
- Visual difference indicates fundamental change in market dynamics

### 2. Persistence Diagram Overlay (Step 3)

**Purpose:** Quantify topological features across regimes

**Features:**
- **H₀ (Components):** Connected regions in phase space
- **H₁ (Loops):** Cyclic patterns in market dynamics
- **H₂ (Voids):** Higher-dimensional topological holes

**Interpretation:**
- Points above diagonal = persistent features (signal)
- Points near diagonal = short-lived features (noise)
- Crisis shows:
  - **6× higher H₀ persistence** (1.49 vs 0.24)
  - **3× higher H₁ persistence** (0.047 vs 0.015)
  - **3 H₂ voids** vs 1 in normal period

### Statistics Summary

**Crisis Period (Aug-Oct 2008):**
- H₀: 52 features, total persistence: 1.4912
- H₁: 12 loops, total persistence: 0.0467
- H₂: 3 voids, total persistence: 0.0013
- Rips complex: 689 edges at threshold 0.0725

**Normal Period (Apr-Jun 2007):**
- H₀: 51 features, total persistence: 0.2446
- H₁: 15 loops, total persistence: 0.0146
- H₂: 1 void, total persistence: 0.0000
- Rips complex: 663 edges at threshold 0.0144

## Technical Details

### Pipeline Architecture

```
Market Data → Takens Embedding → Rips Complex → Persistence Computation
    ↓              ↓                   ↓                ↓
  yfinance    delay=5, dim=3    edges @ threshold    H₀, H₁, H₂
```

### Dependencies

- **Python Libraries:** numpy, pandas, yfinance, pyvista, matplotlib, gudhi, giotto-tda
- **Optional:** ParaView 6.x with pvpython for native rendering
- **Financial TDA:** Project modules (`financial_tda.topology`)

### Performance Notes

- Point cloud size: ~50-53 points per regime
- Persistence computation: ~1-2 seconds per regime
- PyVista rendering: ~2-3 seconds per view
- ParaView rendering: ~1-2 seconds per view (GPU-accelerated)

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'yfinance'"

```bash
pip install yfinance
```

### Issue: "ParaView Python modules not available"

This is expected when running with standard Python. The script automatically falls back to PyVista. To use ParaView:

```bash
# Install ParaView 6.x from paraview.org
# Then run with pvpython instead of python
pvpython regime_compare.py
```

### Issue: "No data returned for ^GSPC"

Check internet connection. yfinance requires network access to download market data.

### Issue: Blank PNG outputs

- Check that PyVista is installed: `pip install pyvista`
- Ensure off_screen=True is set in Plotter initialization
- Try running with `--output-dir` to specify writable directory

## File Structure

```
financial_tda/viz/
├── paraview_scripts/
│   ├── regime_compare.py              # Main script (PyVista + data prep)
│   ├── regime_compare_paraview_only.py  # ParaView-only rendering
│   └── README.md                      # This file
└── outputs/
    ├── regime_compare_side_by_side.png
    ├── regime_compare_side_by_side_paraview.png
    ├── persistence_overlay.png
    ├── regime_compare_paraview.pvsm
    ├── *.vtp                          # VTK PolyData files
    └── regime_metadata.json
```

## References

- **Takens Embedding:** Takens, F. (1981). Detecting strange attractors in turbulence.
- **Persistent Homology:** Edelsbrunner, H., et al. (2002). Topological persistence and simplification.
- **Rips Complex:** Vietoris, L. (1927). Über den höheren Zusammenhang kompakter Räume.
- **Financial TDA:** Gidea, M., & Katz, Y. (2018). Topological data analysis of financial time series.

## License

MIT License - See project root for details.

## Contact

For questions or issues, please refer to the main project documentation or open an issue on GitHub.
