# Financial Market Regime Detection via TDA

## Overview
This project applies Topological Data Analysis (TDA) to detect regime changes in financial markets. By analyzing the topological structure of financial time series through persistent homology, we identify and classify market states such as bull markets, bear markets, and crisis periods.

## Architecture

### Directory Structure
- `data/` - Financial data fetching and preprocessing
  - `fetchers/` - APIs for Yahoo Finance, FRED, cryptocurrency data
  - `preprocessors/` - Returns, log-returns, volatility calculations
- `topology/` - TDA computations
  - Takens embedding with optimal τ and dimension selection
  - Filtration methods (Rips, Alpha, custom market filtrations)
  - Feature extraction (persistence landscapes, images, statistics)
- `models/` - Machine learning models
  - Regime classification
  - Change point detection
- `viz/` - Visualization tools
  - ParaView/TTK scripts for interactive exploration
  - Streamlit dashboards
- `analysis/` - Analysis workflows and results

## Key Features
- Optimal Takens embedding using mutual information
- Multi-scale persistence feature extraction
- Integration with TTK (Topology ToolKit) for ParaView
- Deep learning on persistence diagrams (Perslay, PersFormer)
- Real-time regime detection

## Dependencies
See main project requirements and shared utilities in `/shared`.

## Usage
Refer to individual module documentation and examples in the analysis directory.
