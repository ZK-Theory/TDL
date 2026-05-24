# TDL Tech Stack

## Core Technologies
- **Python 3.13.5** (exact version pinned)
- **Package Manager**: `uv` (modern Python package manager)
- **Build System**: setuptools with pyproject.toml

## Key Libraries

### TDA Libraries
- `gudhi==3.11.0` - Lower-level TDA, simplex trees, cubical complexes, Mapper
- `ripser==0.6.14` - Fast Vietoris-Rips complex computation
- `persim==0.3.8` - Persistence image/landscape/silhouette vectorization
- `umap-learn>=0.5.0` - Dimensionality reduction and embedding

### Data Analysis
- `numpy==2.3.2` - Numerical computing (version 2.x for Python 3.13)
- `pandas>=2.0.0` - Data manipulation
- `scipy==1.16.1` - Scientific computing
- `scikit-learn==1.8.0` - Machine learning algorithms

### Financial Data
- `yfinance>=0.2.52` - Yahoo Finance data fetching
- `fredapi>=0.5.0` - FRED economic data

### Geospatial Analysis
- `geopandas>=0.14.0` - Geospatial data processing
- `shapely>=2.0.0` - Geometric operations
- `pyproj>=3.6.0` - Cartographic projections
- `libpysal>=4.9.0` - Spatial analysis library

### Deep Learning (Optional)
- `torch>=2.0.0` - PyTorch for neural networks
- `xgboost>=2.0.0` - Gradient boosting

### Visualization
- `pyvista>=0.42.0` - 3D visualization and VTK integration

### Development Tools
- `ruff>=0.8.0` - Fast Python linter and formatter
- `pytest>=8.3.0` - Testing framework
- `pytest-cov>=6.0.0` - Coverage reporting
- `pre-commit>=4.0.0` - Git pre-commit hooks

## Code Navigation
- **Serena MCP**: Symbol-level code intelligence and editing (primary tool for code navigation)