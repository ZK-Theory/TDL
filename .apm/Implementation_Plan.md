# TDL (Topological Data Analysis Lab) – APM Implementation Plan
**Memory Strategy:** Dynamic-MD
**Last Modification:** Manager_5 - **PHASE 4 COMPLETE** (5/5 tasks). Financial: RegimeClassifier, ChangePointDetector, BacktestEngine. Poverty: InterventionPrioritizer, CounterfactualAnalyzer. 212 new tests.
**Project Overview:** Dual parallel TDA portfolio projects: (1) Financial Market Regime Detection via persistent homology on time series, and (2) Poverty Trap Detection via Morse-Smale analysis on UK economic mobility data. Monorepo with shared utilities. Deliverables include working dashboards, academic papers, and policy briefs targeting finance, NGO, and government audiences. Full ambition including deep learning integration (GNNs, VAEs, Perslay).


## Phase 0: Foundation & Standards

### Task 0.1 – Monorepo Structure Setup - Agent_Foundation
**Objective:** Establish the complete monorepo directory hierarchy for both TDA projects with shared utilities.
**Output:** Complete folder structure with placeholder files and .gitignore.
**Guidance:** Follow architecture specs from project docs. Reference: `docs/plans/strategy/project1_financial_tda.md` and `project2_poverty_tda.md` for directory structures.

- Create monorepo root structure: `financial_tda/`, `poverty_tda/`, `shared/`, `docs/`, `tests/`
- Create sub-directories per architecture specs: `data/`, `topology/`, `models/`, `viz/` for each project
- Create `.gitignore` with Python, IDE, data file exclusions
- Create placeholder `README.md` files for each major directory

### Task 0.2 – Development Environment Configuration - Agent_Foundation
**Objective:** Configure Python 3.13 environment with uv and complete dependency management.
**Output:** Working virtual environment with pyproject.toml and installed dependencies.
**Guidance:** Use uv as package manager. Include giotto-tda, gudhi as core TDA libraries. **Depends on: Task 0.1 Output**

1. Create `pyproject.toml` with project metadata, Python 3.13 requirement, and core dependencies (numpy, pandas, scipy, giotto-tda, gudhi)
2. Initialize virtual environment using `uv venv`
3. Install base dependencies and dev dependencies (ruff, pytest, pytest-cov)
4. Verify environment by running `python --version` and import test

### Task 0.3 – CI/CD Pipeline Setup - Agent_Foundation
**Objective:** Create GitHub Actions workflow for automated linting, testing, and quality checks.
**Output:** `.github/workflows/ci.yml` with working pipeline.
**Guidance:** Use ruff for linting with fail-on-error. Run pytest with coverage. **Depends on: Task 0.2 Output**

- Create `.github/workflows/ci.yml` with Python 3.13 matrix
- Configure ruff linting step with fail-on-error
- Configure pytest step with coverage reporting

### Task 0.4 – Testing Framework & Patterns - Agent_Foundation
**Objective:** Establish pytest configuration and mathematical validation test patterns.
**Output:** Test directory structure, conftest.py, and template validation tests.
**Guidance:** Mathematical validation tests are critical. Create patterns for verifying against known published results. **Depends on: Task 0.2 Output**

1. Create `pytest.ini` or `pyproject.toml` pytest section with test discovery settings
2. Create test directory structure: `tests/financial/`, `tests/poverty/`, `tests/shared/`
3. Create `conftest.py` with shared fixtures and mathematical validation helpers
4. Create template mathematical validation test demonstrating pattern for verifying against known results

### Task 0.5 – Documentation Standards & Templates - Agent_Foundation
**Objective:** Establish docstring conventions, type hints, and documentation templates.
**Output:** CONTRIBUTING.md, documentation templates, example documented module.
**Guidance:** Google-style docstrings. Type hints required for all public APIs.

- Create `CONTRIBUTING.md` with code style guide (ruff, type hints, docstrings)
- Define docstring template (Google style with Args, Returns, Raises, Examples)
- Document type hint requirements for all public APIs
- Create example module `shared/example.py` demonstrating all conventions

### Task 0.6 – Shared TDA Utilities Scaffold - Agent_Foundation
**Objective:** Create shared TDA utilities module with common interfaces for both projects.
**Output:** Scaffolded `shared/` module with interface definitions.
**Guidance:** Define interfaces only; implementation comes in later phases. **Depends on: Task 0.1 Output**

- Create `shared/__init__.py` with package exports
- Create `shared/persistence.py` with persistence diagram utility interfaces
- Create `shared/visualization.py` with common plotting utility stubs
- Create `shared/validation.py` with mathematical validation helper interfaces


## Phase 1: Data Infrastructure

### Task 1.1 – Financial Data Fetcher - Yahoo Finance - Agent_Financial_Data
**Objective:** Implement Yahoo Finance data fetcher for equities and indices.
**Output:** Working `financial_tda/data/fetchers/yahoo.py` with tests.
**Guidance:** Use yfinance library. Cover major indices (S&P 500, FTSE, STOXX Europe 600). Include specific crisis periods: 2008 Global Financial Crisis (Sep-Dec 2008), 2015 China Devaluation (Aug 2015), 2020 COVID Crash (Feb-Mar 2020), 2022 Rate Hike Volatility (Jan-Oct 2022).

1. Ad-Hoc Delegation – Research Yahoo Finance API patterns and rate limits
2. Implement `financial_tda/data/fetchers/yahoo.py` with configurable ticker lists, date ranges
3. Add error handling for rate limits, missing data, market closures
4. Create tests with known historical data validation covering all specified crisis periods

### Task 1.2 – Financial Data Fetcher - FRED - Agent_Financial_Data
**Objective:** Implement FRED API fetcher for macroeconomic indicators.
**Output:** Working `financial_tda/data/fetchers/fred.py` with tests.
**Guidance:** Use fredapi library. Environment variable for API key. Required series: VIXCLS (VIX), DGS10 (10Y Treasury), DGS2 (2Y Treasury), T10Y2Y (yield spread), UNRATE (unemployment), FEDFUNDS (Fed Funds rate). Critical for cross-asset correlation analysis.

1. Implement `financial_tda/data/fetchers/fred.py` using fredapi library
2. Configure environment variable handling for API key (FRED_API_KEY)
3. Add fetchers for specified series IDs with proper date alignment
4. Create tests with known historical values for each series

### Task 1.3 – Financial Data Fetcher - Crypto APIs - Agent_Financial_Data
**Objective:** Implement cryptocurrency data fetcher using free APIs.
**Output:** Working `financial_tda/data/fetchers/crypto.py` with tests.
**Guidance:** Use CoinGecko or CryptoCompare free tier. Include 2022 crypto winter (May-Dec 2022, Terra/LUNA collapse). Handle rate limiting with exponential backoff.

1. Implement `financial_tda/data/fetchers/crypto.py` using free APIs (CoinGecko, CryptoCompare)
2. Add support for major cryptocurrencies (BTC, ETH) with OHLCV data
3. Implement rate limit handling with exponential backoff and request caching
4. Create tests including 2022 crypto winter period (May-Dec 2022) validation

### Task 1.4 – Financial Data Preprocessor - Agent_Financial_Data
**Objective:** Implement preprocessing pipeline for financial time series.
**Output:** Preprocessor module with returns, volatility calculations.
**Guidance:** Mathematical validation critical. Compare against known financial analysis results. **Depends on: Tasks 1.1, 1.2, 1.3 Output**

1. Create `financial_tda/data/preprocessors/returns.py` with log-returns, simple returns
2. Implement volatility calculations (rolling, GARCH-like)
3. Add normalization and windowing utilities
4. Create mathematical validation tests comparing against known financial analysis results

### Task 1.5 – UK Boundary Data Acquisition - Agent_Poverty_Data
**Objective:** Download and process UK LSOA boundary shapefiles.
**Output:** Boundary data files and `poverty_tda/data/census_shapes.py` loader.
**Guidance:** Use ONS Geography Portal. Expect ~35,000 LSOAs for England/Wales.

1. Create `poverty_tda/data/census_shapes.py` with LSOA boundary loader
2. Download LSOA boundaries from ONS Geography Portal
3. Implement GeoDataFrame construction with proper CRS handling
4. Create tests verifying expected LSOA count (~35,000 for England/Wales)

### Task 1.6 – UK Socioeconomic Data Acquisition - Agent_Poverty_Data
**Objective:** Download IMD and related socioeconomic data.
**Output:** IMD data files and `poverty_tda/data/opportunity_atlas.py` loader.
**Guidance:** Use gov.uk official sources. Parse income, education, employment domains.

1. Create `poverty_tda/data/opportunity_atlas.py` (UK equivalent loader)
2. Download IMD 2019 data from gov.uk
3. Parse income domain, education domain, employment domain scores
4. Create tests validating against known deprivation patterns

### Task 1.7 – UK Education & Mobility Proxy Data - Agent_Poverty_Data
**Objective:** Acquire education data and construct mobility proxy.
**Output:** Education data and mobility proxy calculator.
**Guidance:** Follow formula: α·DeprivationChange + β·EducationalUpward + γ·IncomeGrowth. Validate against Social Mobility Commission. **Depends on: Task 1.6 Output**

1. Download Key Stage 4 outcomes by LSOA from Department for Education
2. Download POLAR4 higher education participation data
3. Implement mobility proxy construction as specified: α·DeprivationChange + β·EducationalUpward + γ·IncomeGrowth
4. Create tests validating proxy against Social Mobility Commission LAD-level estimates

### Task 1.8 – Geospatial Data Processor - Agent_Poverty_Data
**Objective:** Implement geospatial processing utilities for UK data.
**Output:** `poverty_tda/data/preprocessors.py` with spatial operations.
**Guidance:** Use GeoPandas. Include interpolation methods (Kriging, IDW). **Depends on: Tasks 1.5, 1.6 Output**

1. Create `poverty_tda/data/preprocessors.py` with spatial join utilities
2. Implement LSOA-to-LAD aggregation functions
3. Add spatial interpolation for continuous surface creation (Kriging, IDW)
4. Create tests verifying geographic integrity and coverage


## Phase 2: Core Topology Implementation

### Task 2.1 – Takens Embedding Implementation - Agent_Financial_Topology
**Objective:** Implement Takens delay embedding with optimal parameter selection.
**Output:** `financial_tda/topology/embedding.py` with tau/dimension optimization.
**Guidance:** Reference giotto-tda docs at C:\Projects\giotto-tda. Mutual information for optimal tau. Expected dimension range for financial data: d=3-10. Note: mutual information computation can be numerically unstable for short series; implement smoothing. Mathematical validation critical.

1. Ad-Hoc Delegation – Research optimal tau selection via mutual information
2. Implement `financial_tda/topology/embedding.py` with basic Takens embedding
3. Implement `optimal_tau()` using mutual information first minimum method (with smoothing for stability)
4. Implement `optimal_dimension()` using false nearest neighbors or similar (typical range d=3-10 for financial data)
5. Create mathematical validation tests against known embedding results

### Task 2.2 – Persistence Diagram Computation - Financial - Agent_Financial_Topology
**Objective:** Implement persistence diagram computation for embedded time series.
**Output:** `financial_tda/topology/filtration.py` with Vietoris-Rips and Alpha complex.
**Guidance:** Use giotto-tda VietorisRipsPersistence. Include H0, H1, H2. Cross-validate with GUDHI. Filtration parameters: start with max_edge_length based on data diameter, use n_bins=100 as baseline. Alpha complex for computational efficiency on larger embeddings. **Depends on: Task 2.1 Output**

1. Implement `financial_tda/topology/filtration.py` using giotto-tda VietorisRipsPersistence
2. Configure for homology dimensions H0, H1, H2 with appropriate filtration parameters
3. Add Alpha complex alternative for computational efficiency on larger embeddings
4. Create tests comparing giotto-tda output against GUDHI for consistency

### Task 2.3 – Gidea & Katz Replication [CHECKPOINT] - Agent_Financial_Topology
**Objective:** Replicate results from Gidea & Katz (2018) paper as mathematical validation, AND test our Takens embedding approach on same data.
**Output:** Reproduction notebook with documented comparison to published results, plus comparative Takens analysis.
**Guidance:** **CRITICAL CHECKPOINT** - Pause for user mathematical validation before completion. Paper uses multi-index methodology (4 indices → 4D point cloud, NOT Takens embedding) with persistence landscapes. Implements both approaches for comparison. Pulls Task 3.1 (Persistence Landscapes) scope forward. **Depends on: Tasks 2.1, 2.2 Output**

**Part A - Paper Replication (Multi-Index Methodology):**
1. Ad-Hoc Delegation – Research Gidea & Katz (2018) methodology (COMPLETED - paper in docs/Research Papers/)
2. Fetch data: S&P 500 (^GSPC), DJIA (^DJI), NASDAQ (^IXIC), Russell 2000 (^RUT) daily closes 1987-2016
3. Compute daily log-returns for each index: r = ln(P_t / P_{t-1})
4. Implement persistence landscapes (from Task 3.1) in `financial_tda/topology/features.py`
5. Implement sliding window analysis: w=50 days, stride=1 day, 4D point cloud per window
6. Compute H1 persistence diagrams per window (VR filtration)
7. Compute L¹ and L² norms of persistence landscapes per window
8. Validate against paper benchmarks: Kendall-tau ≥0.89 for spectral density trend 250 days pre-crash

**Part B - Takens Embedding Comparison:**
9. Apply Takens embedding (from Task 2.1) to S&P 500 log-returns for same period
10. Compute persistence diagrams and landscape norms
11. Compare signal timing and quality vs multi-index approach
12. Document relative strengths of each methodology

13. **CHECKPOINT**: Document findings and pause for user mathematical validation

### Task 2.4 – Mobility Surface Construction - Agent_Poverty_Topology
**Objective:** Implement mobility surface interpolation from LSOA data to scalar field.
**Output:** `poverty_tda/topology/mobility_surface.py` with VTK export.
**Guidance:** Use scipy griddata. Export VTK for TTK consumption. Recommended grid resolution: 500x500 for England/Wales (balance detail vs computation). Memory note: ~35,000 LSOAs with full resolution may require 8GB+ RAM; implement chunked processing option. **Depends on: Phase 1 Poverty tasks (1.5-1.8) Output by Agent_Poverty_Data**

1. Create `poverty_tda/topology/mobility_surface.py` with grid construction (default 500x500)
2. Implement centroid extraction and griddata interpolation (cubic, linear methods)
3. Add VTK export for TTK consumption using pyvista or vtk library
4. Create tests validating surface coverage, value ranges, and memory handling

### Task 2.5 – Morse-Smale Decomposition - TTK Integration - Agent_Poverty_Topology
**Objective:** Integrate TTK for Morse-Smale complex computation.
**Output:** `poverty_tda/topology/morse_smale.py` TTK wrapper.
**Guidance:** Reference TTK docs at C:\Projects\ttk-1.3.0\ttk-1.3.0\doc. Include topological simplification. Recommended persistence threshold range: 1-10% of scalar range for meaningful simplification. TTK compatibility note: verify Python bindings version matches VTK version. Simple test cases: 2D Gaussian (single max), saddle function z=x²-y² (known critical point structure). **Depends on: Task 2.4 Output**

1. Ad-Hoc Delegation – Research TTK Python API for Morse-Smale complex
2. Create `poverty_tda/topology/morse_smale.py` TTK wrapper (verify TTK-VTK compatibility)
3. Implement Morse-Smale complex extraction (ascending/descending separatrices)
4. Add topological simplification with persistence threshold parameter (default 5% of range)
5. Create tests validating output on simple cases (2D Gaussian, z=x²-y²)

### Task 2.6 – Critical Point Extraction & Validation [CHECKPOINT] - Agent_Poverty_Topology
**Objective:** Extract critical points and validate against known UK mobility patterns.
**Output:** Critical point classifier with geographic mapping.
**Guidance:** **CRITICAL CHECKPOINT** - Pause for user validation. Map minima to poverty traps, maxima to opportunity peaks, saddles to barriers. Validation regions: expect minima in Blackpool, Jaywick, parts of Middlesbrough (known deprived areas); expect maxima in parts of London (Westminster, City), Cambridge, Oxford (known high-mobility areas). **Depends on: Task 2.5 Output**

1. Implement critical point classification from Morse-Smale output
2. Extract minima (poverty traps), maxima (opportunity peaks), saddles (barriers)
3. Map critical points back to LSOA geography
4. Create validation tests against known regions (e.g., Blackpool as trap, Westminster as peak)
5. **CHECKPOINT**: Document critical point distribution and pause for user validation


## Phase 3: Feature Engineering & Analysis

### Task 3.1 – Persistence Landscape Computation - Agent_Financial_Topology
**Objective:** Implement persistence landscape computation for diagram vectorization.
**Output:** Landscape computation in `financial_tda/topology/features.py`.
**Guidance:** Use giotto-tda PersistenceLandscape. Include L^p norms. **Depends on: Task 2.2 Output**

- Implement `financial_tda/topology/features.py` with PersistenceLandscape from giotto-tda
- Configure L^p norm computation for various p values
- Add statistical summaries (mean, std, max of landscapes)
- Create tests validating landscape properties (stability, etc.)

### Task 3.2 – Persistence Image Computation - Agent_Financial_Topology
**Objective:** Implement persistence images for alternative vectorization.
**Output:** Persistence image computation added to features module.
**Guidance:** Configure resolution and weighting functions. **Depends on: Task 2.2 Output**

- Add PersistenceImage computation to `financial_tda/topology/features.py`
- Configure resolution and weighting function parameters
- Create tests comparing image representations across different data

### Task 3.3 – Betti Curve & Entropy Features - Agent_Financial_Topology
**Objective:** Implement Betti curves and persistence entropy.
**Output:** Betti and entropy extractors in features module.
**Guidance:** Entropy formula: E = -Σ p_i log(p_i). Mathematical validation required. **Depends on: Task 2.2 Output**

- Implement `compute_betti_curve()` tracking Betti numbers across filtration values
- Implement persistence entropy: E = -Σ p_i log(p_i) where p_i = (d_i - b_i) / Σ(d_j - b_j)
- Add persistence amplitude (Wasserstein distance) features
- Create mathematical validation tests for entropy calculations

### Task 3.4 – Sliding Window Analysis Pipeline - Agent_Financial_Topology
**Objective:** Implement sliding window analysis for time-evolving features.
**Output:** `financial_tda/analysis/windowed.py` pipeline.
**Guidance:** Configurable window size/stride. Recommended window sizes: 20-60 trading days for regime detection (start with 40-day window, 5-day stride). Include bottleneck distance between windows. Computational note: bottleneck distance is O(n³) – consider Wasserstein as faster alternative for large datasets. Synthetic data for testing: sine wave with period change (clear topology shift), random walk with variance regime change. **Depends on: Tasks 3.1, 3.2, 3.3 Output**

1. Create `financial_tda/analysis/windowed.py` with configurable window size (default 40 days) and stride (default 5 days)
2. Implement feature extraction per window (landscapes, images, entropy, Betti)
3. Add bottleneck distance computation between consecutive windows (with Wasserstein alternative)
4. Create tests validating change detection on synthetic data (sine wave period change, variance regime change)

### Task 3.5 – Basin Analysis & Trap Scoring - Agent_Poverty_Topology
**Objective:** Implement poverty trap scoring based on basin properties.
**Output:** `poverty_tda/analysis/trap_identification.py` scorer.
**Guidance:** Scoring: 0.4×mobility + 0.3×size + 0.3×barrier. Validate against known traps. **Depends on: Task 2.6 Output**

1. Create `poverty_tda/analysis/trap_identification.py` with basin property extraction
2. Implement trap scoring: 0.4×mobility_score + 0.3×size_score + 0.3×barrier_score
3. Add basin population calculation using LSOA population data
4. Create tests validating scoring against known poverty trap areas

### Task 3.6 – Separatrix Extraction & Barrier Analysis - Agent_Poverty_Topology
**Objective:** Extract separatrices and analyze barriers between basins.
**Output:** Barrier analysis module.
**Guidance:** Map to geographic boundaries. Compute persistence as barrier strength. **Depends on: Task 2.5 Output**

1. Extract 1-separatrices from Morse-Smale output (ascending and descending)
2. Compute separatrix persistence (barrier strength)
3. Map separatrices to geographic boundaries (LSOA edges, roads, rivers)
4. Create tests validating separatrix topology properties

### Task 3.7 – Integral Line Computation - Agent_Poverty_Topology
**Objective:** Compute integral lines (flow paths) from LSOAs to basins.
**Output:** `poverty_tda/analysis/pathways.py` flow module.
**Guidance:** Identify gateway LSOAs as intervention targets. **Depends on: Tasks 3.5, 3.6 Output**

1. Create `poverty_tda/analysis/pathways.py` with integral line computation
2. Trace gradient flow from each LSOA centroid to eventual basin
3. Identify "gateway" LSOAs on separatrices (intervention targets)
4. Create tests validating flow connectivity and basin coverage


## Phase 4: Detection & ML Systems

### Task 4.1 – Regime Classifier - Financial - Agent_Financial_ML ✅
**Objective:** Implement regime classifier (crisis vs normal) using topological features.
**Output:** `financial_tda/models/regime_classifier.py` with training pipeline.
**Guidance:** Use time-series aware train/test split (no look-ahead). Crisis labels: VIX > 25 for ≥5 consecutive days, or drawdown > 15% from recent peak. Normal: VIX < 20 for ≥20 consecutive days. Multiple classifier options for comparison. **Depends on: Task 3.4 Output by Agent_Financial_Topology**
**Completed:** Agent_Financial_ML - RegimeClassifier with 4 classifier types (RF, SVM, XGBoost, GB), time-series CV, balanced class weights. 43 tests (40 pass, 3 skip due to gtda env). Added xgboost, joblib dependencies.

1. Create `financial_tda/models/regime_classifier.py` with feature preprocessing
2. Implement crisis/normal labeling (VIX-based and drawdown-based definitions)
3. Implement multiple classifier options (Random Forest, SVM, XGBoost)
4. Add proper train/validation/test split with time-series aware methodology (no future leakage)
5. Implement cross-validation with appropriate metrics (precision, recall, F1)
6. Create tests with synthetic regime data

### Task 4.2 – Change-Point Detection - Bottleneck Distance - Agent_Financial_ML ✅
**Objective:** Implement change-point detection using bottleneck distance.
**Output:** `financial_tda/models/change_point_detector.py`.
**Guidance:** Calibrate thresholds on historical normal periods (2004-2007, 2013-2019 excluding Aug 2015). Statistical significance testing. Validation crisis onset dates: 2008-09-15 (Lehman), 2015-08-11 (China devaluation), 2020-02-20 (COVID first drop), 2022-01-03 (rate hike sell-off). **Depends on: Task 3.4 Output by Agent_Financial_Topology**
**Completed:** Agent_Financial_ML - NormalPeriodCalibrator with bootstrap CI, ChangePointDetector with z-scores/p-values, crisis validation framework. 42 tests (all pass).

1. Create `financial_tda/models/change_point_detector.py` with bottleneck-based detection
2. Implement threshold calibration using historical "normal" periods (2004-2007, 2013-2019)
3. Add confidence intervals and statistical significance testing
4. Create tests validating detection on known crisis onset dates (Lehman 2008-09-15, China 2015-08-11, COVID 2020-02-20, Rate hike 2022-01-03)

### Task 4.3 – Backtest Framework - Historical Crises - Agent_Financial_ML ✅
**Objective:** Implement backtesting on historical crises (2008, 2020, 2022).
**Output:** `financial_tda/analysis/backtest.py` with results.
**Guidance:** Compute lead time before crisis. Compare against volatility baseline. Crisis periods: GFC (2008-09-15 to 2009-03-09), COVID (2020-02-20 to 2020-03-23), Rate Hike (2022-01-03 to 2022-10-12). Success metric: detect regime change ≥5 trading days before peak drawdown. **Depends on: Tasks 4.1, 4.2 Output**
**Completed:** Agent_Financial_ML - BacktestEngine with CrisisPeriod definitions, VolatilityBaseline comparison, lead time computation via np.busday_count(). 52 tests (all pass), 91% coverage.

1. Create `financial_tda/analysis/backtest.py` with crisis period definitions (GFC, COVID, Rate Hike dates)
2. Implement rolling window evaluation across historical data
3. Compute lead time (days before crisis detection triggers) – target: ≥5 days before peak drawdown
4. Generate precision/recall metrics per crisis event
5. Create comparison against baseline (volatility-only) detection

### Task 4.4 – Intervention Analysis Framework - Poverty - Agent_Poverty_ML ✅
**Objective:** Implement intervention targeting based on topological analysis.
**Output:** `poverty_tda/analysis/interventions.py` module.
**Guidance:** Prioritize gateway LSOAs by impact. Cost-benefit framework. Example scenarios: school quality improvement (+10% KS4 in gateway LSOA), transport link addition (reduce barrier height by 50%), job creation hub (flatten saddle point). **Depends on: Task 3.7 Output by Agent_Poverty_Topology**
**Completed:** Agent_Poverty_ML - InterventionPrioritizer with 4 intervention types, ImpactModel, cost-benefit framework, scenario simulation. 38 tests (all pass), 99% coverage.

1. Create `poverty_tda/analysis/interventions.py` with intervention targeting
2. Implement gateway LSOA prioritization by impact potential
3. Add intervention cost-benefit analysis based on topology
4. Create tests with simulated scenarios (school improvement, transport link, job creation hub)

### Task 4.5 – Counterfactual Analysis Module - Agent_Poverty_ML ✅
**Objective:** Implement counterfactual analysis ("what if barrier removed").
**Output:** Counterfactual module with surface modification.
**Guidance:** Recompute topology after modifications. Surface modification approach: Gaussian smoothing around saddle (increase values to "fill" barrier), linear interpolation to flatten saddle region. Measure: change in basin size, flow redistribution, population affected. Visualize before/after. **Depends on: Tasks 3.5, 3.6 Output by Agent_Poverty_Topology**
**Completed:** Agent_Poverty_ML - SurfaceModifier with Gaussian/linear barrier removal, CounterfactualAnalyzer with topology comparison and population impact, visualization + reporting. 37 tests (all pass), 95% coverage.

1. Implement surface modification utilities (Gaussian smoothing to remove saddles, linear interpolation for flattening)
2. Recompute Morse-Smale complex on modified surface
3. Calculate flow redistribution under counterfactual (basin size change, population affected)
4. Create visualization of before/after topology


## Phase 5: Deep Learning Integration

### Task 5.1 – Perslay/PersFormer Integration - Financial - Agent_Financial_ML
**Objective:** Integrate Perslay or PersFormer for learning on persistence diagrams.
**Output:** DL model for persistence diagram sequence prediction.
**Guidance:** Use PyTorch (consistent with other DL tasks). Reference TopoModelX docs at C:\Projects\TopoModelX\docs. Base implementation on giotto-tda's neural network utilities or PyTorch Geometric TopologyNet. Hyperparameters: start with hidden_dim=64, num_layers=2, learning_rate=1e-3. **CHECKPOINT** for architecture decisions. **Depends on: Tasks 3.1, 3.2, 3.3 Output by Agent_Financial_Topology**

1. Ad-Hoc Delegation – Research Perslay/PersFormer architectures in TopoModelX and giotto-tda
2. Implement persistence diagram vectorization layer (PyTorch)
3. Create LSTM/Transformer architecture for sequence prediction (hidden_dim=64, num_layers=2)
4. Add training loop with proper validation methodology and early stopping
5. **CHECKPOINT**: Document architecture decisions for user review

### Task 5.2 – GNN on Rips Complex - Financial [CHECKPOINT] - Agent_Financial_ML
**Objective:** Implement GNN learning edge weights for regime discrimination.
**Output:** GNN module with Rips complex input.
**Guidance:** Use PyTorch Geometric. Graph construction: nodes = points in embedding, edges = Rips complex edges at fixed filtration value (choose 90th percentile of pairwise distances). Architecture options: GCN (simpler), GAT (attention-based), GraphSAGE (sampling-based). **CHECKPOINT** for architecture selection. **Depends on: Task 2.2 Output by Agent_Financial_Topology**

1. Create Rips complex to PyTorch Geometric graph conversion (nodes from embedding, edges from filtration)
2. Implement GNN architecture options (GCN, GAT, GraphSAGE) using PyTorch Geometric
3. **CHECKPOINT**: Present architecture comparison for user selection before full training
4. Add edge weight learning objective for regime discrimination
5. Create training pipeline with regime labels
6. Create tests validating graph construction and forward pass

### Task 5.3 – Autoencoder Anomaly Detection - Financial - Agent_Financial_ML
**Objective:** Implement autoencoder on persistence images for anomaly detection.
**Output:** Autoencoder module with anomaly scoring.
**Guidance:** Train on "normal" periods: 2004-2007 (pre-GFC), 2013-2019 (post-recovery, excluding Aug 2015). Reconstruction error for anomaly: threshold at 95th percentile of training error. CNN architecture: encoder 3 conv layers with pooling, symmetric decoder. **Depends on: Task 3.2 Output by Agent_Financial_Topology**

1. Implement CNN autoencoder for persistence images (3-layer encoder/decoder)
2. Train on "normal" market period data (2004-2007, 2013-2019 excluding Aug 2015)
3. Implement reconstruction error anomaly scoring (threshold at 95th percentile)
4. Validate anomaly detection on crisis periods (2008, 2020, 2022)

### Task 5.4 – GNN for Census Tracts - Poverty - Agent_Poverty_ML
**Objective:** Implement GNN with LSOAs as nodes for mobility prediction.
**Output:** GNN module for spatial poverty analysis.
**Guidance:** Use PyTorch Geometric. LSOA adjacency from shared boundaries (queen contiguity). Commuting data source: Census 2021 Origin-Destination data from NOMIS (WU03UK table) if available; fallback to geographic distance as edge weight. **Depends on: Task 1.5 Output by Agent_Poverty_Data**

1. Create LSOA adjacency graph from boundary data (queen contiguity)
2. Add edge features (commuting flows from Census OD data if available, else geographic distance)
3. Implement GNN for node-level mobility prediction
4. Add message passing layers appropriate for spatial data (GraphSAGE recommended for large graphs)
5. Create training pipeline with mobility proxy labels

### Task 5.5 – Spatial Transformer Network - Poverty - Agent_Poverty_ML
**Objective:** Implement spatial transformer for attention over regions.
**Output:** Spatial attention module with visualization.
**Guidance:** Interpretable attention patterns. **Depends on: Task 2.4 Output by Agent_Poverty_Topology**

1. Implement spatial transformer architecture for gridded mobility surface
2. Add attention visualization for interpretability
3. Train on mobility prediction task
4. Analyze learned attention patterns for insight extraction

### Task 5.6 – VAE for Opportunity Landscapes [CHECKPOINT] - Agent_Poverty_ML
**Objective:** Implement VAE for latent space of opportunity landscapes.
**Output:** VAE with counterfactual generation capability.
**Guidance:** **CRITICAL CHECKPOINT** - Latent space interpretability is key for policy insights. Topology-aware loss optional but valuable: reference "Topology-Preserving Deep Image Segmentation" (Hu et al. 2019) for Betti number regularization approach. Latent dim: start with 8-16 dimensions. **Depends on: Task 2.4 Output by Agent_Poverty_Topology**

1. Implement VAE architecture for mobility surface encoding (latent_dim=8-16)
2. Train on regional mobility surfaces
3. Implement latent space interpolation for counterfactual generation
4. Add topology-aware loss component (optional: Betti number regularization per Hu et al. 2019)
5. **CHECKPOINT**: Document latent space interpretability for user review


## Phase 6: Visualization & Dashboards

### Task 6.1 – Streamlit Dashboard - Financial - Agent_Financial_Viz
**Objective:** Implement Streamlit dashboard for financial TDA analysis.
**Output:** Working `financial_tda/viz/streamlit_app.py` dashboard.
**Guidance:** **Human visual check required.** Interactive persistence diagrams using plotly. Regime timeline. Deployment: local first (streamlit run), cloud deployment (Streamlit Cloud or similar) as Phase 8 stretch goal. **Depends on: Tasks 4.1, 4.2, 4.3 Output by Agent_Financial_ML**

1. Create `financial_tda/viz/streamlit_app.py` with main dashboard structure
2. Implement data upload/selection interface
3. Add persistence diagram visualization (interactive, using plotly)
4. Add regime detection results display with timeline
5. **VISUAL CHECK**: Deploy locally (streamlit run) for user review

### Task 6.2 – ParaView Pipeline - Financial Regime Comparison - Agent_Financial_Viz
**Objective:** Create ParaView state files for comparing regimes.
**Output:** `financial_tda/viz/paraview_scripts/regime_compare.py`.
**Guidance:** **Human visual check required.** Side-by-side Rips evolution. **Depends on: Task 2.2 Output by Agent_Financial_Topology**

1. Create `financial_tda/viz/paraview_scripts/regime_compare.py`
2. Implement side-by-side Rips complex evolution visualization
3. Add persistence diagram overlay for different periods
4. **VISUAL CHECK**: Generate sample outputs for user review

### Task 6.3 – Real-time Monitoring Interface - Financial - Agent_Financial_Viz
**Objective:** Add real-time monitoring to financial dashboard.
**Output:** Live monitoring features in dashboard.
**Guidance:** **Human visual check required.** Alert thresholds configurable. Live data simulation: replay historical data at accelerated speed (1 trading day = 1 second) for testing. Production: integrate with Task 1.1 fetchers for delayed quotes. **Depends on: Task 6.1 Output**

1. Add live Betti curve display with configurable refresh (default 5 seconds)
2. Implement bottleneck distance monitoring from reference state
3. Add alert threshold configuration and notification display
4. Implement simulated live data replay (historical data at accelerated speed) for testing
5. **VISUAL CHECK**: Test with simulated live data for user review

### Task 6.4 – Interactive Map - Poverty - Agent_Poverty_Viz
**Objective:** Implement interactive geographic map for poverty analysis.
**Output:** `poverty_tda/viz/maps.py` Folium/Plotly application.
**Guidance:** **Human visual check required.** Click → show basin, escape routes. Library selection: use Folium for web embedding (lighter, OSM base), Plotly for interactive analysis (richer interactivity but heavier). Implement Folium first for portability. **Depends on: Tasks 3.5, 3.7 Output by Agent_Poverty_Topology**

1. Create `poverty_tda/viz/maps.py` with LSOA choropleth base (Folium first)
2. Implement click interaction: select LSOA → show basin, escape routes
3. Add layer toggles for different data (mobility, trap score, barriers)
4. Add basin overlay with color coding
5. **VISUAL CHECK**: Generate sample maps for user review

### Task 6.5 – ParaView 3D Terrain - Poverty - Agent_Poverty_Viz
**Objective:** Create 3D opportunity terrain in ParaView.
**Output:** `poverty_tda/viz/paraview_states/terrain_3d.py`.
**Guidance:** **Human visual check required.** Height = mobility, color = basin. **Depends on: Task 2.4 Output by Agent_Poverty_Topology**

1. Create `poverty_tda/viz/paraview_states/terrain_3d.py`
2. Implement 3D surface with height = mobility, color = basin
3. Add critical point annotations (minima, maxima, saddles)
4. **VISUAL CHECK**: Generate terrain renders for user review

### Task 6.6 – Basin Dashboard - Poverty - Agent_Poverty_Viz
**Objective:** Implement basin comparison dashboard.
**Output:** `poverty_tda/viz/dashboard.py` application.
**Guidance:** **Human visual check required.** Statistics, demographics per basin. Scope: implement for single region first (e.g., Manchester metro or North West), add cross-region comparison as extension. Use Streamlit for consistency with financial dashboard. **Depends on: Tasks 3.5, 3.6 Output by Agent_Poverty_Topology**

1. Create `poverty_tda/viz/dashboard.py` with basin selection interface (Streamlit)
2. Implement basin statistics display (population, mean mobility, trap score)
3. Add demographic breakdown per basin (IMD decile distribution, education levels)
4. Enable cross-region comparison (after single-region implementation validated)
5. **VISUAL CHECK**: Deploy locally for user review


## Phase 7: Validation & Backtesting

### Task 7.1 – Financial System Integration Test - Agent_Financial_ML
**Objective:** Run end-to-end integration tests for financial TDA pipeline.
**Output:** Passing integration test suite.
**Guidance:** Test full pipeline: data → embedding → persistence → features → detection. Multiple asset classes. **Depends on: Phase 4-5 Financial tasks Output**

1. Create integration test suite covering full pipeline: data → embedding → persistence → features → detection
2. Test on multiple asset classes (equities, crypto)
3. Verify consistent results across repeated runs
4. Document any numerical stability issues

### Task 7.2 – Crisis Detection Validation [CHECKPOINT] - Agent_Financial_ML
**Objective:** Validate crisis detection against historical events.
**Output:** Validation report with quantitative metrics.
**Guidance:** **CRITICAL CHECKPOINT** - Present results for user validation. 2008, 2020, 2022 events. **Depends on: Task 7.1 Output**

1. Run detection system on 2008 financial crisis period
2. Run detection system on 2020 COVID crash period
3. Run detection system on 2022 crypto winter period
4. Compile metrics: lead time, precision, recall, F1 per event
5. **CHECKPOINT**: Present results for user validation

### Task 7.3 – Poverty System Integration Test - Agent_Poverty_ML
**Objective:** Run end-to-end integration tests for poverty TDA pipeline.
**Output:** Passing integration test suite.
**Guidance:** Test full pipeline: data → surface → Morse-Smale → analysis. Verify Morse inequality. **Depends on: Phase 4-5 Poverty tasks Output**

1. Create integration test suite: data → surface → Morse-Smale → analysis
2. Test on sample UK region
3. Verify topological properties (Morse inequality, correct basin count)
4. Document any data quality issues

### Task 7.4 – UK Mobility Validation [CHECKPOINT] - Agent_Poverty_ML
**Objective:** Validate poverty trap identification against known UK patterns.
**Output:** Validation report with geographic findings.
**Guidance:** **CRITICAL CHECKPOINT** - Compare with Social Mobility Commission, levelling up areas. **Depends on: Task 7.3 Output**

1. Compare identified traps with Social Mobility Commission reports
2. Validate against known deprived areas (post-industrial North, coastal towns)
3. Cross-reference with "levelling up" target areas
4. Compute correlation with official mobility indices
5. **CHECKPOINT**: Present geographic findings for user validation

### Task 7.5 – Cross-System Comparison & Metrics - Agent_Docs
**Objective:** Compile overall system performance metrics.
**Output:** Comprehensive metrics report for both systems.
**Guidance:** Compare against baselines. Document key claims with evidence. **Depends on: Task 7.2 Output by Agent_Financial_ML, Task 7.4 Output by Agent_Poverty_ML**

- Compile comprehensive metrics for both systems
- Compare against baseline methods where applicable
- Document key claims supported by evidence
- Create summary tables for paper inclusion


## Phase 8: Documentation & Publication

### Task 8.1 – Financial TDA Paper Draft - Agent_Docs
**Objective:** Draft academic paper for financial TDA results.
**Output:** Paper draft (LaTeX/Markdown) for journal submission.
**Guidance:** **HEAVY REVIEW required.** Primary target: Quantitative Finance or Journal of Financial Data Science. Alternatives: arXiv preprint (q-fin.ST), SSRN working paper for faster dissemination. Include mathematical formulations with full proofs in appendix. **Depends on: Task 7.2 Output by Agent_Financial_ML**

1. Create paper outline following target journal format (Quantitative Finance style)
2. Write methodology section with mathematical formulations (Takens embedding, persistence diagrams, detection algorithm)
3. Write results section with metrics and visualizations
4. Write discussion comparing to prior work (Gidea & Katz, other TDA finance papers)
5. **HEAVY REVIEW**: Submit draft for user revision

### Task 8.2 – Poverty TDA Paper Draft - Agent_Docs
**Objective:** Draft academic paper for poverty TDA results.
**Output:** Paper draft for economics/policy journal.
**Guidance:** **HEAVY REVIEW required.** Primary target: Journal of Economic Geography or Regional Studies. Policy context: explicitly connect to UK "Levelling Up" agenda and Social Mobility Commission framework. Include policy implications with concrete recommendations. **Depends on: Task 7.4 Output by Agent_Poverty_ML**

1. Create paper outline for policy/economics audience
2. Write methodology emphasizing Morse theory applications and topological interpretation
3. Write results with UK geographic findings (connect to Levelling Up target areas)
4. Write policy implications section with concrete recommendations
5. **HEAVY REVIEW**: Submit draft for user revision

### Task 8.3 – Policy Brief - Poverty Traps - Agent_Docs
**Objective:** Create policy brief for NGO/government audiences.
**Output:** 2-4 page policy brief with recommendations.
**Guidance:** **HEAVY REVIEW required.** Target audiences: UK government departments (DLUHC, DfE), think tanks (Resolution Foundation, Social Mobility Foundation), charities (Joseph Rowntree Foundation). Non-technical executive summary, actionable recommendations with clear next steps. **Depends on: Task 8.2 Output**

1. Create 2-4 page policy brief structure (executive summary, key findings, recommendations, methodology appendix)
2. Write executive summary with key findings (non-technical, accessible language)
3. Add actionable recommendations with topological backing (gateway LSOA interventions, barrier reduction)
4. **HEAVY REVIEW**: Submit draft for user revision

### Task 8.4 – Technical Blog - Financial - Agent_Docs
**Objective:** Create technical blog posts for financial TDA.
**Output:** Blog post drafts (2 posts).
**Guidance:** Lower priority than papers. "What Shape is a Market Crash?" + tutorial. **Depends on: Task 7.2 Output by Agent_Financial_ML**

1. Create "What Shape is a Market Crash?" introductory post
2. Create technical tutorial "Building a Topological Early Warning System"
3. Add code snippets and visualizations
4. Submit drafts for user review

### Task 8.5 – Technical Blog - Poverty - Agent_Docs
**Objective:** Create technical blog posts for poverty TDA.
**Output:** Blog post drafts (2 posts).
**Guidance:** Lower priority than papers. "The Shape of Opportunity" + methodology. **Depends on: Task 7.4 Output by Agent_Poverty_ML**

1. Create "The Shape of Opportunity" introductory post
2. Create methodology post "Finding Poverty Traps with Topology"
3. Add geographic visualizations and maps
4. Submit drafts for user review

### Task 8.6 – API Documentation - Agent_Docs
**Objective:** Create comprehensive API documentation.
**Output:** API reference and usage guides.
**Guidance:** Use Sphinx with autodoc extension for automatic API reference generation from docstrings. Host on ReadTheDocs or GitHub Pages. Example notebooks using Jupyter with nbsphinx integration. **Depends on: All implementation phases Output**

1. Configure Sphinx with autodoc, napoleon (Google-style docstrings), and nbsphinx
2. Generate API reference from docstrings automatically
3. Write usage guides for key modules (data fetching, topology computation, detection)
4. Add example notebooks demonstrating end-to-end workflows
5. Submit for user review

