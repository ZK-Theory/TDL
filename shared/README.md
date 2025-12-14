# Shared TDA Utilities

## Overview
This directory contains common utilities and helper functions shared between the Financial TDA and Poverty TDA projects.

## Contents

### Planned Modules
- **Persistence utilities**: Common operations on persistence diagrams
  - Distance metrics (Wasserstein, bottleneck)
  - Diagram transformations and normalization
  - Persistence curve computation
  
- **Visualization helpers**: Reusable plotting functions
  - Persistence diagram plots
  - Betti curve visualization
  - Common matplotlib/plotly configurations
  
- **Data processing**: Generic preprocessing tools
  - Normalization and scaling
  - Missing data handling
  - Time series utilities
  
- **TTK wrappers**: Python interfaces to TTK modules
  - Simplified API for common TTK operations
  - ParaView script templates
  
- **IO utilities**: Common data loading/saving
  - VTK file handling
  - Persistence diagram serialization
  - Configuration management

## Usage
Import shared utilities in project code:
```python
from shared.persistence import compute_wasserstein_distance
from shared.viz import plot_persistence_diagram
```

## Contributing
When adding utilities that could benefit both projects, place them here rather than duplicating code.
