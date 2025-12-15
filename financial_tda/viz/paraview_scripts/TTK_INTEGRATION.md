# Topology ToolKit (TTK) Integration Guide

## Overview

The Topology ToolKit (TTK) is an open-source library and ParaView plugin for topological data analysis. When available, TTK provides advanced persistent homology computation and visualization capabilities that complement our custom Python-based approach.

## Current Implementation Status

**Python/GUDHI Implementation (Active):**
- ✅ Persistent homology via GUDHI/giotto-tda
- ✅ Rips complex computation with scipy
- ✅ PyVista visualization
- ✅ Works in standard Python environments

**TTK Integration (Optional Enhancement):**
- ⚠️ Not currently detected in ParaView 6.0.1 installation
- 📋 Documentation for future integration provided below

## Installing TTK

### Option 1: Pre-built ParaView with TTK

Download ParaView with TTK pre-installed:
- **Linux/macOS:** https://topology-tool-kit.github.io/installation.html
- **Windows:** Build from source (see TTK documentation)

### Option 2: Build TTK Plugin

```bash
# Clone TTK
git clone https://github.com/topology-tool-kit/ttk.git
cd ttk

# Build TTK ParaView plugin
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=~/ttk ../
make -j4
make install
```

Then configure ParaView to load the TTK plugin:
1. Open ParaView
2. Tools → Manage Plugins
3. Load New → Select TTK plugin .so/.dll
4. Check "Auto Load"

## TTK Features for Financial TDA

### 1. Persistence Diagram Computation

**TTK Alternative:**
```python
# Instead of GUDHI
from paraview.simple import *

# Load point cloud
reader = XMLPolyDataReader(FileName='crisis_embedding.vtp')

# Compute persistence diagram with TTK
persistenceDiagram = TTKPersistenceDiagram(Input=reader)
persistenceDiagram.InputOffsetField = 'Elevation'
persistenceDiagram.ComputeSaddleConnectors = 1
```

**Benefits:**
- Native ParaView integration
- Interactive visualization
- Real-time parameter tuning
- Better performance on large datasets

### 2. Persistence Curve

**TTK Feature:**
```python
persistenceCurve = TTKPersistenceCurve(Input=persistenceDiagram)
persistenceCurve.XAxisType = 'Persistence'
persistenceCurve.YAxisType = 'Number of Pairs'
```

**Use Case:**
- Compare topological complexity between regimes
- Identify significant persistence thresholds
- Publication-quality plots

### 3. Topological Simplification

**TTK Feature:**
```python
simplification = TTKTopologicalSimplification(Input=reader)
simplification.InputOffsetField = 'Distance'
simplification.PersistenceThreshold = 0.01
```

**Use Case:**
- Remove noise from Rips complex
- Focus on significant topological features
- Reduce visualization clutter

### 4. Morse-Smale Complex

**TTK Feature:**
```python
morseSmale = TTKMorseSmaleComplex(Input=reader)
morseSmale.InputOffsetField = 'Filtration'
morseSmale.ComputeAscendingSegmentation = 1
morseSmale.ComputeDescendingSegmentation = 1
```

**Use Case:**
- Identify market regime basins
- Segment phase space by topological structure
- Visualize gradient flow of financial indicators

## Recommended Workflow with TTK

### Step 1: Data Preparation (Python)
```python
# Use our existing regime_compare.py
python financial_tda/viz/paraview_scripts/regime_compare.py
```

### Step 2: TTK Analysis (ParaView GUI)
1. Open ParaView
2. Load `crisis_embedding.vtp` and `normal_embedding.vtp`
3. Apply TTK filters:
   - Filters → TTK → TTKPersistenceDiagram
   - Filters → TTK → TTKPersistenceCurve
4. Compare persistence curves between regimes

### Step 3: Advanced Visualization
```python
# In pvpython with TTK
from paraview.simple import *

# Load both embeddings
crisis = XMLPolyDataReader(FileName='crisis_embedding.vtp')
normal = XMLPolyDataReader(FileName='normal_embedding.vtp')

# Compute persistence diagrams
crisis_pd = TTKPersistenceDiagram(Input=crisis)
normal_pd = TTKPersistenceDiagram(Input=normal)

# Bottleneck distance
distance = TTKBottleneckDistance(Input1=crisis_pd, Input2=normal_pd)
print(f"Bottleneck distance: {distance.BottleneckDistance}")
```

## Checking TTK Availability

### In pvpython:
```python
from paraview.simple import *
sources = dir()
ttk_filters = [s for s in sources if 'TTK' in s]
print(f"Available TTK filters: {ttk_filters}")
```

### In Python script:
```python
try:
    from paraview.simple import TTKPersistenceDiagram
    HAS_TTK = True
except ImportError:
    HAS_TTK = False
    print("TTK not available, using GUDHI fallback")
```

## Performance Comparison

| Operation | GUDHI/Python | TTK/ParaView | Notes |
|-----------|-------------|--------------|-------|
| Persistence (100 pts) | ~1-2 sec | ~0.5 sec | TTK faster |
| Persistence (1000 pts) | ~10-20 sec | ~2-3 sec | TTK significantly faster |
| Visualization | Static PNG | Interactive 3D | TTK more flexible |
| Bottleneck Distance | giotto-tda | Native | TTK better integration |
| Learning Curve | Lower | Higher | Python easier for beginners |

## Integration Priority

1. **High Priority:**
   - Persistence diagram computation (faster than GUDHI)
   - Bottleneck/Wasserstein distance between regimes
   - Real-time filtration parameter tuning

2. **Medium Priority:**
   - Morse-Smale complex for regime segmentation
   - Topological simplification for noise removal
   - Persistence curve for comparative analysis

3. **Low Priority:**
   - Advanced TTK features (Reeb graphs, contour trees)
   - Integration with TTK's web viewer

## Current Recommendation

**For now, continue using the Python/GUDHI implementation because:**
- ✅ Works out-of-the-box with pip install
- ✅ Easier to automate and script
- ✅ Better for batch processing
- ✅ Generates publication-ready static figures

**Consider TTK when:**
- Need interactive exploration
- Working with very large datasets (>1000 points)
- Want to compute bottleneck/Wasserstein distances
- Collaborating with domain experts who prefer GUI tools

## Future Work

- [ ] Detect TTK availability and provide hybrid implementation
- [ ] Create TTK state files (.pvsm) for interactive analysis
- [ ] Implement bottleneck distance computation when TTK available
- [ ] Create TTK macros for automated batch processing
- [ ] Add TTK-based filtration animation

## References

- **TTK Website:** https://topology-tool-kit.github.io/
- **TTK Tutorial:** https://topology-tool-kit.github.io/tutorials.html
- **TTK Paper:** Tierny & Favelier, "The Topology ToolKit" (2018)
- **ParaView TTK Plugin:** https://github.com/topology-tool-kit/ttk-paraview

---

**Note:** This guide assumes TTK 1.0+ and ParaView 5.9+. Older versions may have different API.
