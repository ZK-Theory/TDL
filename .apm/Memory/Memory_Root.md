# TDL (Topological Data Analysis Lab) – APM Memory Root
**Memory Strategy:** Dynamic-MD
**Project Overview:** Dual parallel TDA portfolio projects: (1) Financial Market Regime Detection via persistent homology on time series to detect market regimes and predict crashes, and (2) Poverty Trap Detection via Morse-Smale analysis on UK LSOA-level economic mobility data to identify poverty traps and intervention points. Monorepo with shared utilities. Deliverables include working dashboards (Streamlit, Folium), academic papers, policy briefs, and technical blog posts targeting finance, NGO, and government audiences. Full deep learning integration (GNNs, VAEs, Perslay) with mathematical rigor and validation checkpoints.

---

## Phase 00 – Foundation & Standards Summary

**Outcome:** Successfully established complete development foundation for TDL monorepo. All 6 tasks completed with no blockers. Key deviation: Python version adjusted from 3.13 to 3.11 due to giotto-tda wheel availability (documented in Task 0.2 compatibility concerns). Development environment fully functional with all TDA libraries (giotto-tda 0.6.2, gudhi 3.11.0) installed and verified.

**Deliverables:**
- Monorepo structure with `financial_tda/`, `poverty_tda/`, `shared/` directories
- Python 3.11 environment via uv with 46 packages installed
- GitHub Actions CI/CD pipeline with ruff linting and pytest coverage
- Testing framework with mathematical validation patterns (7 template tests, 3 fixtures)
- Documentation standards (CONTRIBUTING.md, Google-style docstrings)
- Shared TDA utilities scaffold (12 interface functions, 2 type definitions)

**Agents Involved:** Agent_Foundation

**Task Logs:**
- [Task_0_1_Monorepo_Structure_Setup.md](.apm/Memory/Phase_00_Foundation/Task_0_1_Monorepo_Structure_Setup.md)
- [Task_0_2_Development_Environment_Configuration.md](.apm/Memory/Phase_00_Foundation/Task_0_2_Development_Environment_Configuration.md)
- [Task_0_3_CI_CD_Pipeline_Setup.md](.apm/Memory/Phase_00_Foundation/Task_0_3_CI_CD_Pipeline_Setup.md)
- [Task_0_4_Testing_Framework_Patterns.md](.apm/Memory/Phase_00_Foundation/Task_0_4_Testing_Framework_Patterns.md)
- [Task_0_5_Documentation_Standards_Templates.md](.apm/Memory/Phase_00_Foundation/Task_0_5_Documentation_Standards_Templates.md)
- [Task_0_6_Shared_TDA_Utilities_Scaffold.md](.apm/Memory/Phase_00_Foundation/Task_0_6_Shared_TDA_Utilities_Scaffold.md)

---

## Phase 01 – Data Infrastructure Summary

**Outcome:** Successfully implemented complete data acquisition and preprocessing infrastructure for both Financial and Poverty TDA projects. All 8 tasks completed with no blockers. Key adaptations: POLAR4 education data is postcode-level so IMD Education domain used as practical alternative for mobility proxy; geospatial module renamed from `preprocessors.py` to `geospatial.py` due to existing directory conflict.

**Financial Data Infrastructure (Tasks 1.1–1.4):**
- Yahoo Finance fetcher: 3 functions (ticker, multiple, index), 6 major indices, exponential backoff
- FRED fetcher: 6 macroeconomic series (VIX, Treasury yields, unemployment, Fed Funds), date alignment with forward-fill
- Crypto fetcher: CoinGecko API (no key required), BTC/ETH/SOL/ADA support, 2022 crypto winter validation
- Preprocessing pipeline: Log/simple returns, rolling/EWMA/realized volatility (Parkinson, Garman-Klass), normalization (z-score, minmax, robust IQR), sliding windows for TDA

**Poverty Data Infrastructure (Tasks 1.5–1.8):**
- LSOA boundaries: ~33,755 LSOAs via ONS ArcGIS REST API, centroid extraction, CRS handling
- IMD 2019 data: All 7 deprivation domains (income, employment, education, health, crime, housing, environment), decile calculation, known pattern validation (Jaywick, Blackpool, Hart)
- Mobility proxy: Formula α×DeprivationChange + β×EducationalUpward + γ×IncomeGrowth (α=0.4, β=0.3, γ=0.3), Social Mobility Commission validation patterns
- Geospatial processing: Spatial joins, LAD aggregation, interpolation (IDW, Kriging optional, scipy), VTK export for TTK, chunked processing for memory efficiency

**Dependencies Added:** yfinance, fredapi, requests, geopandas, shapely, pyproj, pyvista, pykrige (optional)

**Agents Involved:** Agent_Financial_Data, Agent_Poverty_Data

**Task Logs:**
- [Task_1_1_Financial_Data_Fetcher_Yahoo_Finance.md](.apm/Memory/Phase_01_Data_Infrastructure/Task_1_1_Financial_Data_Fetcher_Yahoo_Finance.md)
- [Task_1_2_Financial_Data_Fetcher_FRED.md](.apm/Memory/Phase_01_Data_Infrastructure/Task_1_2_Financial_Data_Fetcher_FRED.md)
- [Task_1_3_Financial_Data_Fetcher_Crypto_APIs.md](.apm/Memory/Phase_01_Data_Infrastructure/Task_1_3_Financial_Data_Fetcher_Crypto_APIs.md)
- [Task_1_4_Financial_Data_Preprocessor.md](.apm/Memory/Phase_01_Data_Infrastructure/Task_1_4_Financial_Data_Preprocessor.md)
- [Task_1_5_UK_Boundary_Data_Acquisition.md](.apm/Memory/Phase_01_Data_Infrastructure/Task_1_5_UK_Boundary_Data_Acquisition.md)
- [Task_1_6_UK_Socioeconomic_Data_Acquisition.md](.apm/Memory/Phase_01_Data_Infrastructure/Task_1_6_UK_Socioeconomic_Data_Acquisition.md)
- [Task_1_7_UK_Education_Mobility_Proxy_Data.md](.apm/Memory/Phase_01_Data_Infrastructure/Task_1_7_UK_Education_Mobility_Proxy_Data.md)
- [Task_1_8_Geospatial_Data_Processor.md](.apm/Memory/Phase_01_Data_Infrastructure/Task_1_8_Geospatial_Data_Processor.md)

---

## Phase 02 – Core Topology Implementation Summary

**Outcome:** Successfully implemented complete topological analysis pipelines for both Financial and Poverty TDA projects. All 6 tasks completed with 2 critical checkpoints validated. Key strategic insight: Multi-index approach (Gidea & Katz) significantly outperforms Takens embedding for systemic risk detection; Takens retained for single-asset attractor analysis.

**Financial TDA Pipeline (Tasks 2.1–2.3):**
- Takens embedding: `optimal_tau()` (MI first minimum), `optimal_dimension()` (FNN), embedding validation on Lorenz attractor (d=3)
- Persistence diagrams: VR and Alpha complex via giotto-tda, GUDHI cross-validation, H0/H1/H2 homology
- **Gidea & Katz Replication [CHECKPOINT VALIDATED]:**
  - Multi-index methodology: 4 indices (S&P 500, DJIA, NASDAQ, Russell 2000) → 4D point cloud
  - Persistence landscapes with L¹/L² norms implemented (Task 3.1 scope pulled forward)
  - Dotcom crash: τ=0.833 (paper: 0.89) ✅
  - Lehman crash: τ=0.722 variance (paper: 1.00) ✅
  - Takens comparison: Multi-index Kendall-tau 0.303 vs Takens -0.039 → multi-index superior

**Poverty TDA Pipeline (Tasks 2.4–2.6):**
- Mobility surface: scipy.griddata interpolation, 500×500 grid, VTK export (.vti), chunked processing
- Morse-Smale: TTK integration via subprocess (conda isolation), critical point extraction, persistence simplification
- **Critical Point Validation [CHECKPOINT VALIDATED]:**
  - Classification: minima→poverty traps, maxima→opportunity peaks, saddles→barriers
  - Severity formula: 60% value + 40% persistence
  - Trap match rate: 100% (Blackpool, Knowsley, Middlesbrough, etc.)
  - Peak match rate: 85.7% (Westminster, Cambridge, Oxford, etc.)
  - Phase 3+ guidance: 1000×1000 grid for London zoom, LSOA-level validation preferred

**Key Strategic Decisions:**
1. Multi-index approach primary for crisis detection; Takens for single-asset dynamics
2. TTK via subprocess for VTK version isolation (project VTK 9.5.2 vs TTK requirements)
3. Persistence landscapes pulled forward from Task 3.1 into Task 2.3

**Tests Added:** 147 new tests (25 features, 33 filtration, 33 embedding, 28 mobility_surface, 46 morse_smale, 29 critical_points) - all passing

**Agents Involved:** Agent_Financial_Topology, Agent_Poverty_Topology

**Task Logs:**
- [Task_2_1_Takens_Embedding_Implementation.md](.apm/Memory/Phase_02_Core_Topology/Task_2_1_Takens_Embedding_Implementation.md)
- [Task_2_2_Persistence_Diagram_Computation_Financial.md](.apm/Memory/Phase_02_Core_Topology/Task_2_2_Persistence_Diagram_Computation_Financial.md)
- [Task_2_3_Gidea_Katz_Replication.md](.apm/Memory/Phase_02_Core_Topology/Task_2_3_Gidea_Katz_Replication.md) **[CHECKPOINT]**
- [Task_2_4_Mobility_Surface_Construction.md](.apm/Memory/Phase_02_Core_Topology/Task_2_4_Mobility_Surface_Construction.md)
- [Task_2_5_Morse_Smale_TTK_Integration.md](.apm/Memory/Phase_02_Core_Topology/Task_2_5_Morse_Smale_TTK_Integration.md)
- [Task_2_6_Critical_Point_Extraction_Validation.md](.apm/Memory/Phase_02_Core_Topology/Task_2_6_Critical_Point_Extraction_Validation.md) **[CHECKPOINT]**

---

## Phase 03 – Feature Engineering & Analysis Summary

**Outcome:** Successfully implemented complete feature extraction pipelines for both Financial and Poverty TDA projects. All 7 tasks completed with comprehensive test coverage. Financial pipeline provides sliding window analysis with topology change detection. Poverty pipeline provides gateway LSOA identification for intervention targeting.

**Financial TDA Feature Engineering (Tasks 3.1–3.4):**
- Persistence landscapes: `landscape_statistics()`, `extract_landscape_features()`, stability tests (42 tests)
- Persistence images: Multi-resolution vectorization, weighting functions (linear, persistence-power) (64 tests)
- Betti curves & entropy: `persistence_amplitude()` (Wasserstein/bottleneck), `betti_curve_statistics()`, mathematical validation (90 tests)
- Sliding window pipeline: `extract_windowed_features()`, `compute_window_distances()`, `detect_topology_changes()` with synthetic regime change detection (30 tests)

**Poverty TDA Feature Engineering (Tasks 3.5–3.7):**
- Basin analysis: `compute_trap_score()` formula (0.4×mobility + 0.3×size + 0.3×barrier), population estimation (17 tests)
- Barrier analysis: Separatrix extraction, barrier strength (persistence, height, width), geographic mapping (18 tests)
- Integral lines: Gradient flow paths, gateway LSOA identification at separatrix crossings, impact scoring (21 tests)

**Key Deliverables:**
- `financial_tda/topology/features.py` - 10+ feature extraction functions
- `financial_tda/analysis/windowed.py` - Complete sliding window pipeline
- `poverty_tda/analysis/trap_identification.py` - Basin scoring and ranking
- `poverty_tda/analysis/barriers.py` - Separatrix extraction and barrier analysis
- `poverty_tda/analysis/pathways.py` - Integral lines and gateway identification

**Tests Added:** 282 new tests across Phase 3 (all passing)

**Agents Involved:** Agent_Financial_Topology, Agent_Poverty_Topology

**Task Logs:**
- [Task_3_1_Persistence_Landscape_Computation.md](.apm/Memory/Phase_03_Feature_Engineering/Task_3_1_Persistence_Landscape_Computation.md)
- [Task_3_2_Persistence_Image_Computation.md](.apm/Memory/Phase_03_Feature_Engineering/Task_3_2_Persistence_Image_Computation.md)
- [Task_3_3_Betti_Curve_Entropy_Features.md](.apm/Memory/Phase_03_Feature_Engineering/Task_3_3_Betti_Curve_Entropy_Features.md)
- [Task_3_4_Sliding_Window_Analysis_Pipeline.md](.apm/Memory/Phase_03_Feature_Engineering/Task_3_4_Sliding_Window_Analysis_Pipeline.md)
- [Task_3_5_Basin_Analysis_Trap_Scoring.md](.apm/Memory/Phase_03_Feature_Engineering/Task_3_5_Basin_Analysis_Trap_Scoring.md)
- [Task_3_6_Separatrix_Extraction_Barrier_Analysis.md](.apm/Memory/Phase_03_Feature_Engineering/Task_3_6_Separatrix_Extraction_Barrier_Analysis.md)
- [Task_3_7_Integral_Line_Computation.md](.apm/Memory/Phase_03_Feature_Engineering/Task_3_7_Integral_Line_Computation.md)
- [Task_2_5_Morse_Smale_TTK_Integration.md](.apm/Memory/Phase_02_Core_Topology/Task_2_5_Morse_Smale_TTK_Integration.md)
- [Task_2_6_Critical_Point_Extraction_Validation.md](.apm/Memory/Phase_02_Core_Topology/Task_2_6_Critical_Point_Extraction_Validation.md) **[CHECKPOINT]**

---

## Phase 04 – Detection & ML Systems Summary

**Outcome:** Successfully implemented complete detection and ML systems for both Financial and Poverty TDA projects. All 5 tasks completed plus 2 ad-hoc fixes (external API failures, CI linting prevention). Total 212 new tests added.

**Financial TDA ML Systems (Tasks 4.1–4.3):**
- Regime Classifier: `RegimeClassifier` with 4 ML backends (RF, SVM, XGBoost, GB), time-series CV, balanced class handling
- Change-Point Detector: `ChangePointDetector` with bottleneck distance calibration, statistical significance (z-scores, p-values), bootstrap CI
- Backtest Framework: `BacktestEngine` with crisis period definitions (GFC, COVID, Rate Hike), `VolatilityBaseline` comparison, lead time computation

**Poverty TDA ML Systems (Tasks 4.4–4.5):**
- Intervention Analysis: `InterventionPrioritizer` with 4 intervention types, `ImpactModel`, cost-benefit framework
- Counterfactual Analysis: `SurfaceModifier` for barrier removal/trap filling, `CounterfactualAnalyzer` for topology recomputation

**Ad-Hoc Fixes:**
- External API test failures: CoinGecko auth support, Yahoo Finance exception signatures updated
- CI linting prevention: Pre-commit hooks, VS Code settings, CONTRIBUTING.md workflow documentation

**Dependencies Added:** xgboost, joblib, pre-commit

**Agents Involved:** Agent_Financial_ML, Agent_Poverty_ML, Agent_Debug

**Task Logs:**
- [Task_4_1_Regime_Classifier_Financial.md](.apm/Memory/Phase_04/Task_4_1_Regime_Classifier_Financial.md)
- [Task_4_2_Change_Point_Detection.md](.apm/Memory/Phase_04/Task_4_2_Change_Point_Detection.md)
- [Task_4_3_Backtest_Framework.md](.apm/Memory/Phase_04/Task_4_3_Backtest_Framework.md)
- [Task_4_4_Intervention_Analysis_Framework.md](.apm/Memory/Phase_04/Task_4_4_Intervention_Analysis_Framework.md)
- [Task_4_5_Counterfactual_Analysis.md](.apm/Memory/Phase_04/Task_4_5_Counterfactual_Analysis.md)
- [AdHoc_External_API_Test_Fixes.md](.apm/Memory/Phase_04/AdHoc_External_API_Test_Fixes.md)
- [AdHoc_CI_Linting_Fixes.md](.apm/Memory/Phase_04/AdHoc_CI_Linting_Fixes.md)

