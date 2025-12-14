# UK Poverty Trap Detection via Topological Landscape Analysis

## Overview
This project uses Topological Data Analysis (TDA) to identify and characterize poverty traps in the UK using the Opportunity Atlas framework. By treating economic mobility as a scalar field over geographic regions, we apply Morse theory and persistent homology to detect stable low-mobility basins and barriers to upward mobility.

## Architecture

### Directory Structure
- `data/` - Census and mobility data
  - `preprocessors/` - Census tract data processing and interpolation
  - Opportunity Atlas integration
  - Geographic boundary handling (GeoJSON/shapefiles)
- `topology/` - TDA computations
  - Mobility surface construction via spatial interpolation
  - Morse-Smale complex computation for basin identification
  - Persistence analysis for barrier robustness
- `models/` - Predictive models
  - GNN-based mobility prediction
  - Causal inference with topological features
- `viz/` - Visualization and reporting
  - ParaView/TTK scripts for terrain analysis
  - Interactive maps (Folium/Plotly)
  - Report generation
- `analysis/` - Policy analysis and interventions
  - Poverty trap identification and scoring
  - Escape pathway analysis
  - Counterfactual intervention modeling

## Key Features
- Continuous mobility surface interpolation from discrete census tract data
- Critical point identification (local minima = poverty traps)
- Basin decomposition via Morse-Smale complex
- Separatrix extraction showing mobility barriers
- Integral line analysis for escape routes
- Topological persistence for robustness quantification

## Dependencies
See main project requirements and shared utilities in `/shared`.

## Usage
Refer to individual module documentation and examples in the analysis directory.
