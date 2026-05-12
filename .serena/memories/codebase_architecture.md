# TDL Codebase Architecture

## Top-Level Structure
```
TDL/
├── papers/                  # ALL paper projects (P01, P02, etc.)
├── financial_tda/          # Market regime detection domain
├── poverty_tda/            # UK poverty trap analysis domain  
├── trajectory_tda/         # Career trajectory analysis domain
├── shared/                 # Cross-domain utilities
├── tests/                  # Domain-organized test suites
├── data/                   # Data files (gitignored)
├── results/                # Computational outputs
├── docs/                   # Documentation and methodology
└── figures/                # Generated visualizations
```

## Domain Structure Pattern
Each domain follows consistent organization:
```
<domain>/
├── data/           # Domain-specific data processing
├── topology/       # TDA computations (persistence, mapper, etc.)
├── models/         # ML models and neural networks
├── analysis/       # Statistical analysis and interpretation
├── validation/     # Mathematical validation and testing
├── viz/           # Visualization and dashboard tools
└── scripts/       # Pipeline scripts and experiments
```

## Key Modules

### shared/ (Cross-Domain Utilities)
- `persistence.py` - Core persistence diagram utilities
- `validation.py` - Mathematical validation helpers  
- `ttk_utils.py` - TTK/ParaView integration for large-scale topology
- `deep_learning/` - Domain-agnostic neural network layers

### financial_tda/
- `topology/` - Financial time series TDA (Vietoris-Rips, embedding)
- `data/fetchers/` - Yahoo Finance, FRED data acquisition
- `validation/` - Crisis event validation (2000, 2008, 2020, 2022)
- `experiments/` - Multi-asset analysis scripts

### trajectory_tda/  
- `data/trajectory_builder.py` - BHPS/UKHLS data processing
- `topology/trajectory_ph.py` - Career trajectory persistent homology
- `embedding/ngram_embed.py` - Sequence embedding methods
- `scripts/bhps_pipeline.py` - Main pipeline script

### poverty_tda/
- `topology/` - Morse-Smale complex, spatial analysis
- `data/` - UK geospatial data processing
- `models/` - Spatial VAEs and GNNs
- `validation/` - Known deprived area validation

## Papers Integration
All paper projects in `papers/` directory:
- Each paper has `_project.md` (YAML metadata)
- Drafts versioned as `vN-YYYY-MM.md` 
- Results stored in domain-specific `results/` directories
- Figures generated to `figures/` with domain organization

## Data Management
- Raw data in `data/raw/` (gitignored)
- Processed data in `data/processed/` (gitignored) 
- UKDA data in `data/UKDA-6614-tab/` (gitignored but accessible)
- Results in `results/` with date-suffixed JSON files

## Testing Structure
- `tests/<domain>/` - Domain-specific tests
- `tests/shared/` - Cross-domain utility tests
- `conftest.py` - Shared fixtures and validation helpers
- Mathematical validation tests for all TDA functions