# TDL Project Overview

## Purpose
TDL (Topological Data Lab) is a research platform applying **Topological Data Analysis (TDA)**, **topological deep learning**, and **geometric deep learning** to social science datasets. The project produces novel insights for academic research papers.

## Primary Research Domains

### 1. Financial TDA (`financial_tda/`)
- Market regime detection and crisis identification
- Persistent homology analysis on financial time series
- Crisis event validation (2000 dot-com, 2008 GFC, 2020 COVID, 2022 crypto)

### 2. Poverty TDA (`poverty_tda/`) 
- UK poverty trap detection via Morse-Smale complex analysis
- Socioeconomic mobility landscape analysis
- Spatial analysis on UK LSOAs using geospatial data

### 3. Trajectory TDA (`trajectory_tda/`)
- Employment/income career trajectory analysis
- Persistent homology on BHPS/UKHLS panel data
- Longitudinal social data analysis

## Key Research Outputs
The project produces academic papers tracked in `papers/` directory:
- P01-A: The Geometry of UK Career Inequality (JRSS-A)
- P01-B: Structured Hypothesis Testing for Persistent Homology (JRSS-B) 
- P04: Multi-Parameter Persistent Homology Reveals Income-Stratified Career Topology
- FIN-01: Market Regime Detection (financial domain)

## Integration with Obsidian Vault
Research record lives in a separate Obsidian vault at `{LOCAL_VAULT_PATH}` containing:

Collaborators should set `LOCAL_VAULT_PATH` or configure their local vault path in the project README/setup guide.
- Theory, methodology, literature
- Project management and status tracking
- Computational logs and decisions
- Must stay in sync with code repository