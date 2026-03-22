# Project 2: Poverty Trap Detection via Topological Landscape Analysis

## Toolchain Integration

### GitHub Copilot
- **GeoJSON/shapefile processing**: Census tract boundary manipulation
- **Spatial interpolation**: Kriging, IDW for missing tract data
- **Vectorized operations**: Numpy/pandas patterns for large mobility matrices

### ParaView + Claude MCP
Core application—this is fundamentally a **terrain analysis** problem:
- **"Find all critical points where mobility probability < 0.05"**: Direct Morse theory query
- **"Show the separatrices between high and low mobility basins"**: Morse-Smale decomposition
- **"Compute the persistence of this poverty trap"**: Quantify barrier robustness
- **"What percentage of tracts flow into each basin?"**: Integral lines / flow analysis

### TTK Modules
| Module | Application |
|--------|-------------|
| `ScalarFieldCriticalPoints` | Local extrema of mobility surface |
| `MorseSmaleComplex` | Basin decomposition, separatrix extraction |
| `PersistentHomology` | Robustness of barriers to mobility |
| `IntegralLines` | "Flow" paths from low to high opportunity |
| `ContourTree` | Hierarchical structure of opportunity landscape |
| `TopologicalSimplification` | Remove noise, find robust features |

### Deep Learning Integration
- **Graph Neural Networks**: Census tracts as nodes, adjacency + commuting as edges
- **Spatial Transformer Networks**: Learn attention over geographic regions
- **Variational Autoencoder**: Learn latent space of "opportunity landscapes", sample counterfactuals
- **Causal inference**: Instrument variables with topological features

---

## Code Architecture

```
poverty_tda/
├── data/
│   ├── opportunity_atlas.py   # Census/Harvard data loader
│   ├── census_shapes.py       # Tract geometries
│   └── covariates.py          # Income, education, demographics
├── topology/
│   ├── mobility_surface.py    # Interpolate tract data to scalar field
│   ├── morse_smale.py         # TTK wrapper for basin analysis
│   └── persistence.py         # Barrier robustness quantification
├── analysis/
│   ├── trap_identification.py # Define and score poverty traps
│   ├── pathways.py            # Integral lines, escape routes
│   └── interventions.py       # Counterfactual analysis
├── viz/
│   ├── paraview_states/       # Pre-built TTK pipelines
│   ├── maps.py                # Folium/Plotly geographic viz
│   └── report_generator.py
└── tests/
```

### Key Code Snippets

**Mobility Surface Construction**:
```python
import numpy as np
from scipy.interpolate import griddata

def build_mobility_surface(tracts_gdf, resolution=0.01):
    """Interpolate tract-level mobility to continuous scalar field."""
    # Extract centroids and mobility values
    points = np.array([[g.centroid.x, g.centroid.y] 
                       for g in tracts_gdf.geometry])
    values = tracts_gdf['kfr_pooled_pooled_p25'].values  # income rank at 35
    
    # Create regular grid
    x = np.arange(points[:,0].min(), points[:,0].max(), resolution)
    y = np.arange(points[:,1].min(), points[:,1].max(), resolution)
    X, Y = np.meshgrid(x, y)
    
    # Interpolate (Copilot: try different methods)
    Z = griddata(points, values, (X, Y), method='cubic')
    return X, Y, Z
```

**TTK Morse-Smale Analysis**:
```python
# paraview_scripts/morse_smale_analysis.py
from paraview.simple import *

def analyze_mobility_landscape(vtk_file):
    """Extract basins and separatrices from mobility surface."""
    # Load scalar field
    reader = XMLImageDataReader(FileName=vtk_file)
    
    # Topological simplification (remove noise < persistence threshold)
    simplify = TTKTopologicalSimplification(Input=reader)
    simplify.PersistenceThreshold = 0.05  # MCP: "What threshold removes noise but keeps poverty traps?"
    
    # Morse-Smale complex
    ms = TTKMorseSmaleComplex(Input=simplify)
    ms.ComputeAscendingSeparatrices1 = 1
    ms.ComputeDescendingSeparatrices1 = 1
    
    # Extract 2-cells (basins)
    basins = TTKMorseSmaleComplex_GetOutput(ms, 3)
    
    # MCP interaction: "Color basins by mean mobility value"
    # MCP interaction: "Show only separatrices with persistence > 0.1"
    
    return ms
```

**Poverty Trap Scoring**:
```python
def score_poverty_trap(basin_data: dict) -> float:
    """
    Score a basin as a poverty trap based on:
    - Mean mobility in basin (lower = worse)
    - Basin size (larger = more people affected)
    - Persistence of surrounding saddles (higher = harder to escape)
    - Connectivity to high-mobility basins
    """
    mobility_score = 1.0 - basin_data['mean_mobility']  # Inverse of mobility
    size_score = np.log1p(basin_data['population'])
    barrier_score = basin_data['min_saddle_persistence']
    
    # Weighted combination (tune empirically)
    return 0.4 * mobility_score + 0.3 * size_score + 0.3 * barrier_score
```

---

## Sprint Plan (12 weeks)

### Sprint 1 (Week 1-3): Data Infrastructure
- [ ] Download Opportunity Atlas data (all tracts, key covariates)
- [ ] Set up PostGIS database for spatial queries
- [ ] Build tract-level GeoDataFrame with geometries
- [ ] Implement mobility surface interpolation
- [ ] Export to VTK format for TTK
- **Deliverable**: Clean, queryable mobility dataset + VTK scalar fields

### Sprint 2 (Week 4-6): Topological Analysis Core
- [ ] TTK pipeline for Morse-Smale decomposition
- [ ] Identify critical points (minima = traps, maxima = opportunity peaks)
- [ ] Extract separatrices (barriers between basins)
- [ ] Compute persistence diagrams of the landscape
- [ ] Validate against known high/low mobility areas
- **Deliverable**: Working TTK analysis pipeline with MCP integration

### Sprint 3 (Week 7-9): Intervention Analysis
- [ ] Compute integral lines from each tract to eventual basin
- [ ] Identify "gateway" tracts on separatrices
- [ ] Counterfactual analysis: what if barrier was removed?
- [ ] Correlate with policy interventions (EITC, housing programs)
- **Deliverable**: Intervention prioritization framework

### Sprint 4 (Week 10-12): Visualization & Communication
- [ ] Interactive map: click tract → show basin, escape routes
- [ ] Comparative analysis across metro areas
- [ ] ParaView animations of opportunity landscape
- [ ] Policy brief + academic paper draft
- **Deliverable**: Complete visualization suite + paper

---

## Mathematical Insights

### Morse Theory Application
The mobility surface $f: \mathbb{R}^2 \to \mathbb{R}$ (where $f(x,y)$ = expected adult income for child from that location) has:
- **Minima**: Poverty traps (stable equilibria of low opportunity)
- **Maxima**: Opportunity peaks
- **Saddles**: Transition points, potential intervention targets

The **Morse-Smale complex** partitions the domain into cells where all flow goes to the same min/max pair.

### Key Concepts
1. **Persistence Pairing**: $(b, d)$ pairs a saddle with the minimum it creates—persistence $d - b$ measures trap depth
2. **Separatrix Thickness**: Width of the barrier region, correlates with difficulty of crossing
3. **Basin Volume**: $\int_{\text{basin}} \rho(x,y) dx dy$ where $\rho$ = population density

### Research Directions
- **Time-varying analysis**: How has the topology changed 1980 → 2020?
- **Multi-field analysis**: Separate surfaces for race, parent income quintile
- **Stochastic Morse theory**: Account for uncertainty in mobility estimates
- **Reeb graphs**: Simplified skeleton of the opportunity landscape

### Useful Formulas
- **Morse Inequality**: $\#\text{minima} - \#\text{saddles} + \#\text{maxima} = \chi$ (Euler characteristic)
- **Gradient flow**: $\dot{x} = \nabla f(x)$ → integral lines
- **Persistence ordering**: Features with higher persistence are more robust

---

## Visualization Ideas

1. **3D Opportunity Terrain**: Actual 3D surface with height = mobility, colored by basin membership
2. **Separatrix Map**: 2D map with thick lines showing barriers, colored by persistence
3. **Flow Animation**: Particles starting in low-mobility tracts, flowing along integral lines
4. **Basin Dashboard**: 
   - Select basin → show statistics, demographics, policy history
   - Compare basins across cities
5. **Counterfactual Animation**: "Remove" a saddle, show how flow patterns change
6. **Historical Timelapse**: Topology evolution decade by decade

---

## Blog/Paper Ideas

### Blog Posts
1. **"The Shape of Opportunity"** - Visual introduction to Morse theory on mobility data
2. **"Finding Poverty Traps with Topology"** - Technical methodology
3. **"Which Neighborhoods are Stuck? A Topological Analysis"** - Results for specific cities

### Paper Targets
1. **Economics journal** (AER: Insights, QJE): Novel methodology for spatial mobility analysis
2. **Computational social science** (Science Advances, PNAS): Interdisciplinary framing
3. **Visualization venue** (IEEE VIS): TTK/ParaView pipeline as contribution

### Key Claims to Support
- Topological features (persistence, basin size) predict neighborhood outcomes better than simple statistics
- Separatrix locations identify actionable intervention targets
- Method reveals hidden structure invisible to standard spatial analysis

### Policy Relevance
- **Site selection**: Where to place new schools, transit, housing programs
- **Barrier identification**: What geographic/institutional features create traps
- **Resource allocation**: Prioritize interventions by topological impact
