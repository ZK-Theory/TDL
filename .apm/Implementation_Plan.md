# TDL (Topological Data Analysis Lab) – APM Implementation Plan
**Memory Strategy:** Dynamic-MD
**Last Modification:** Antigravity Session - **PHASE 9.5 COMPLETE**. TDA Comparison Protocol executed: MS explains 73-83% LE variance vs K-means 33-46% vs spatial methods 10-20%. Novel sex gap closure finding. Results framework created. Phase 9 (Documentation) still in progress.
**Project Overview:** Dual parallel TDA portfolio projects: (1) Financial Market Regime Detection via persistent homology on time series, and (2) Poverty Trap Detection via Morse-Smale analysis on UK economic mobility data. Monorepo with shared utilities. Deliverables include working dashboards, academic papers, and policy briefs targeting finance, NGO, and government audiences. Full ambition including deep learning integration (GNNs, VAEs, Perslay) and TTK acceleration.


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

### Task 5.1 – Perslay/PersFormer Integration - Financial - Agent_Financial_ML ✅
**Objective:** Integrate Perslay or PersFormer for learning on persistence diagrams.
**Output:** DL model for persistence diagram sequence prediction.
**Guidance:** Use PyTorch (consistent with other DL tasks). Reference TopoModelX docs at C:\Projects\TopoModelX\docs. Base implementation on giotto-tda's neural network utilities or PyTorch Geometric TopologyNet. Hyperparameters: start with hidden_dim=64, num_layers=2, learning_rate=1e-3. **CHECKPOINT** for architecture decisions. **Depends on: Tasks 3.1, 3.2, 3.3 Output by Agent_Financial_Topology**
**Completed:** Agent_Financial_ML - Perslay (DeepSet) + LSTM/Transformer architecture. persistence_layers.py (496 lines), tda_neural.py (1050+ lines), 24 tests (23 unit + 1 integration). Architecture: Perslay selected over PersFormer for O(n) efficiency. Temporal splitting prevents future leakage. 86-90% code coverage.

1. Ad-Hoc Delegation – Research Perslay/PersFormer architectures in TopoModelX and giotto-tda
2. Implement persistence diagram vectorization layer (PyTorch)
3. Create LSTM/Transformer architecture for sequence prediction (hidden_dim=64, num_layers=2)
4. Add training loop with proper validation methodology and early stopping
5. **CHECKPOINT**: Document architecture decisions for user review

### Task 5.2 – GNN on Rips Complex - Financial [CHECKPOINT] - Agent_Financial_ML ✅
**Objective:** Implement GNN learning edge weights for regime discrimination.
**Output:** GNN module with Rips complex input.
**Guidance:** Use PyTorch Geometric. Graph construction: nodes = points in embedding, edges = Rips complex edges at fixed filtration value (choose 90th percentile of pairwise distances). Architecture options: GCN (simpler), GAT (attention-based), GraphSAGE (sampling-based). **CHECKPOINT** for architecture selection. **Depends on: Task 2.2 Output by Agent_Financial_Topology**
**Completed:** Agent_Financial_ML - 3 architectures (GCN, GAT, GraphSAGE). rips_gnn.py (856 lines), 30 tests (91% coverage). GAT: 98%±4% accuracy (primary). GraphSAGE: 7x faster (real-time). RipsGNN +33% over Perslay. Temporal splitting prevents leakage.

1. Create Rips complex to PyTorch Geometric graph conversion (nodes from embedding, edges from filtration)
2. Implement GNN architecture options (GCN, GAT, GraphSAGE) using PyTorch Geometric
3. **CHECKPOINT**: Present architecture comparison for user selection before full training
4. Add edge weight learning objective for regime discrimination
5. Create training pipeline with regime labels
6. Create tests validating graph construction and forward pass

### Task 5.3 – Autoencoder Anomaly Detection - Financial - Agent_Financial_ML ✅
**Objective:** Implement autoencoder on persistence images for anomaly detection.
**Output:** Autoencoder module with anomaly scoring.
**Guidance:** Train on "normal" periods: 2004-2007 (pre-GFC), 2013-2019 (post-recovery, excluding Aug 2015). Reconstruction error for anomaly: threshold at 95th percentile of training error. CNN architecture: encoder 3 conv layers with pooling, symmetric decoder. **Depends on: Task 3.2 Output by Agent_Financial_Topology**
**Completed:** Agent_Financial_ML - PersistenceAutoencoder (CNN, 32D latent), persistence_autoencoder.py (1055 lines), 37 tests (94% coverage). TPR 100% on crisis periods (2008 GFC, 2020 COVID, 2022 crypto). Lead time: 14 days early warning. Threshold at 95th percentile.

1. Implement CNN autoencoder for persistence images (3-layer encoder/decoder)
2. Train on "normal" market period data (2004-2007, 2013-2019 excluding Aug 2015)
3. Implement reconstruction error anomaly scoring (threshold at 95th percentile)
4. Validate anomaly detection on crisis periods (2008, 2020, 2022)

### Task 5.4 – GNN for Census Tracts - Poverty - Agent_Poverty_ML ✅
**Objective:** Implement GNN with LSOAs as nodes for mobility prediction.
**Output:** GNN module for spatial poverty analysis.
**Guidance:** Use PyTorch Geometric. LSOA adjacency from shared boundaries (queen contiguity). Commuting data source: Census 2021 Origin-Destination data from NOMIS (WU03UK table) if available; fallback to geographic distance as edge weight. **Depends on: Task 1.5 Output by Agent_Poverty_Data**
**Completed:** Agent_Poverty_ML - SpatialGNN with GraphSAGE layers, spatial_gnn.py (992 lines), 52 tests (94% coverage). Queen/rook contiguity via libpysal. Spatial splitting prevents geographic leakage. Dependencies: torch, torch-geometric, libpysal.

1. Create LSOA adjacency graph from boundary data (queen contiguity)
2. Add edge features (commuting flows from Census OD data if available, else geographic distance)
3. Implement GNN for node-level mobility prediction
4. Add message passing layers appropriate for spatial data (GraphSAGE recommended for large graphs)
5. Create training pipeline with mobility proxy labels

### Task 5.5 – Spatial Transformer Network - Poverty - Agent_Poverty_ML ✅
**Objective:** Implement spatial transformer for attention over regions.
**Output:** Spatial attention module with visualization.
**Guidance:** Interpretable attention patterns. **Depends on: Task 2.4 Output by Agent_Poverty_Topology**
**Completed:** Agent_Poverty_ML - SpatialTransformerSTN + AttentionSpatialTransformer (patch-based), MobilitySurfaceModel, training pipeline with spatial regularization. spatial_transformer.py (1031 lines), 34 tests (32 pass, 2 skipped for dynamic positional encoding), 91% coverage. Visualization utilities for policy interpretation.

1. Implement spatial transformer architecture for gridded mobility surface
2. Add attention visualization for interpretability
3. Train on mobility prediction task
4. Analyze learned attention patterns for insight extraction

### Task 5.6 – VAE for Opportunity Landscapes [CHECKPOINT] - Agent_Poverty_ML ✅
**Objective:** Implement VAE for latent space of opportunity landscapes.
**Output:** VAE with counterfactual generation capability.
**Guidance:** **CRITICAL CHECKPOINT** - Latent space interpretability is key for policy insights. Topology-aware loss optional but valuable: reference "Topology-Preserving Deep Image Segmentation" (Hu et al. 2019) for Betti number regularization approach. Latent dim: start with 8-16 dimensions. **Depends on: Task 2.4 Output by Agent_Poverty_Topology**
**Completed:** Agent_Poverty_ML - OpportunityVAE (12D latent), β-VAE support, latent space analysis. opportunity_vae.py (1166 lines), 31 tests (87% coverage). Key interpretable dimensions: D11 (opportunity gradient r=-0.71 urban), D2 (spatial heterogeneity), D7 (deprivation). Counterfactual generation validated.

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


## Phase 6.5: TTK Integration

### Task 6.5.1 – TTK Installation & Environment Setup - Agent_Foundation
**Objective:** Install Topology ToolKit (TTK) with ParaView integration and resolve VTK version conflicts.
**Output:** Working TTK installation accessible from both ParaView and Python, environment documentation.
**Guidance:** TTK requires specific VTK version compatibility. Current project uses VTK 9.5.2, TTK may require different version. Consider conda environment isolation or ParaView-bundled TTK. Verify both pvpython and Python bindings work. Document installation steps for reproducibility.

1. Research TTK installation options: pre-built ParaView+TTK vs building from source vs conda
2. Resolve VTK version conflict (project VTK 9.5.2 vs TTK requirements)
3. Install TTK with ParaView plugin and Python bindings
4. Verify TTK filters available in pvpython: `TTKPersistenceDiagram`, `TTKBottleneckDistance`, `TTKMorseSmaleComplex`
5. Create `shared/ttk_utils.py` with availability detection and fallback logic
6. Document installation in `docs/TTK_SETUP.md`

### Task 6.5.2 – Financial TDA TTK Hybrid Implementation - Agent_Financial_Topology
**Objective:** Create hybrid persistence computation using TTK with GUDHI fallback for financial TDA.
**Output:** Updated `financial_tda/topology/filtration.py` with TTK integration and bottleneck distance computation.
**Guidance:** TTK provides 5-10× speedup for large point clouds (>1000 points). Implement graceful fallback to GUDHI when TTK unavailable. Add bottleneck/Wasserstein distance for quantitative regime comparison. **Depends on: Task 6.5.1 Output**

1. Update `financial_tda/topology/filtration.py` with TTK persistence computation option
2. Implement `compute_persistence_ttk()` using TTKPersistenceDiagram filter
3. Add `compute_bottleneck_distance()` using TTKBottleneckDistance for regime comparison
4. Create hybrid `compute_persistence()` that auto-selects backend based on availability and dataset size
5. Update tests to validate TTK vs GUDHI consistency
6. Benchmark performance: TTK vs GUDHI on various dataset sizes

### Task 6.5.3 – Poverty TDA TTK Direct Integration - Agent_Poverty_Topology
**Objective:** Replace TTK subprocess calls with direct Python API integration for poverty TDA.
**Output:** Updated `poverty_tda/topology/morse_smale.py` with direct TTK integration.
**Guidance:** Current implementation uses TTK via subprocess due to VTK version isolation. With unified environment, use direct TTK Python API for better performance and error handling. Enhance critical point extraction with persistence-based filtering. **Depends on: Task 6.5.1 Output**

1. Update `poverty_tda/topology/morse_smale.py` to use direct TTK Python API
2. Replace subprocess calls with `TTKMorseSmaleComplex` filter
3. Implement `TTKTopologicalSimplification` for noise removal
4. Add persistence-based critical point filtering (threshold parameter)
5. Update `poverty_tda/analysis/critical_points.py` to use enhanced TTK output
6. Benchmark: direct API vs subprocess performance comparison

### Task 6.5.4 – TTK Visualization Utilities - Agent_Financial_Viz
**Objective:** Create TTK-based interactive visualization utilities for both tracks.
**Output:** TTK visualization module with interactive ParaView state files and persistence curve generation.
**Guidance:** TTK provides native ParaView visualization for persistence diagrams, Morse-Smale complexes. Create reusable state files (.pvsm) for interactive exploration. Add persistence curve generation for publication figures. **Depends on: Tasks 6.5.2, 6.5.3 Output**

1. Create `shared/ttk_visualization.py` with TTK-based plotting utilities
2. Implement `create_persistence_diagram_view()` using TTK native rendering
3. Implement `create_persistence_curve()` for comparative analysis
4. Create interactive ParaView state files for:
   - Financial: regime comparison with bottleneck distance display
   - Poverty: Morse-Smale complex with basin coloring
5. Add `export_publication_figures()` for high-quality static exports
6. Update visualization READMEs with TTK usage instructions


## Phase 7: Validation & Backtesting

### Task 7.1 – Financial System Integration Test - Agent_Financial_ML ✅ COMPLETE
**Objective:** Run end-to-end integration tests for financial TDA pipeline.
**Output:** Passing integration test suite.
**Guidance:** Test full pipeline: data → embedding → persistence → features → detection. Multiple asset classes. Include TTK hybrid backend testing (Rips persistence, bottleneck/Wasserstein distances via persim). **Depends on: Phase 4-5 Financial tasks Output, Phase 6.5 TTK Integration Output**

1. Create integration test suite covering full pipeline: data → embedding → persistence → features → detection
2. Test TTK hybrid backend: verify TTK Rips persistence computation and persim distance metrics
3. Test on multiple asset classes (equities, crypto) with both giotto-tda and TTK backends
4. Verify consistent results across repeated runs and backend choices
5. Document any numerical stability issues or backend-specific behaviors

### Task 7.2 – Crisis Detection Validation [CHECKPOINT] - Agent_Financial_ML ✅ COMPLETE
**Objective:** Validate crisis detection against historical events.
**Output:** Validation report with quantitative metrics.
**Guidance:** **CRITICAL CHECKPOINT** - Present results for user validation. 2008, 2020, 2022 events. **Depends on: Task 7.1 Output**

**NOTE**: Task identified methodology realignment need. TDA implementation validated (G&K replication τ=0.814) but wrong task evaluated (per-day F1 vs trend detection). Phase 8 planned for literature alignment.

1. Run detection system on 2008 financial crisis period
2. Run detection system on 2020 COVID crash period
3. Run detection system on 2022 crypto winter period
4. Compile metrics: lead time, precision, recall, F1 per event
5. **CHECKPOINT**: Present results for user validation

### Task 7.3 – Poverty System Integration Test - Agent_Poverty_ML ✅ COMPLETE
**Objective:** Run end-to-end integration tests for poverty TDA pipeline.
**Output:** Passing integration test suite.
**Guidance:** Test full pipeline: data → surface → Morse-Smale → analysis. Verify Morse inequality. Include TTK topological simplification and persistence filtering. **Depends on: Phase 4-5 Poverty tasks Output, Phase 6.5 TTK Integration Output**

1. Create integration test suite: data → surface → Morse-Smale → analysis
2. Test TTK topological simplification: verify scalar field noise removal and persistence-based filtering
3. Test on sample UK region with different simplification thresholds (1%, 5%, 10%)
4. Verify topological properties (Morse inequality, correct basin count) with and without simplification
5. Document any data quality issues or simplification threshold recommendations

### Task 7.4 – UK Mobility Validation [CHECKPOINT] - Agent_Poverty_ML ✅ COMPLETE
**Objective:** Validate poverty trap identification against known UK patterns.
**Output:** Validation report with geographic findings.
**Guidance:** **CRITICAL CHECKPOINT** - Compare with Social Mobility Commission, levelling up areas. **Depends on: Task 7.3 Output**
**Completed:** Agent_Poverty_ML - 357 poverty traps identified (31,810 LSOAs, 96.9% coverage). SMC validation: 61.5% match in bottom quartile (2.5x random, p<0.01). Effect size Cohen's d=-0.74. Regional patterns validated (post-industrial North, coastal).

1. Compare identified traps with Social Mobility Commission reports
2. Validate against known deprived areas (post-industrial North, coastal towns)
3. Cross-reference with "levelling up" target areas
4. Compute correlation with official mobility indices
5. **CHECKPOINT**: Present geographic findings for user validation

### Task 7.5 – Cross-System Comparison & Metrics - Agent_Docs ✅ COMPLETE
**Objective:** Compile overall system performance metrics.
**Output:** Comprehensive metrics report for both systems.
**Guidance:** Compare against baselines. Document key claims with evidence. **Depends on: Task 8.1 Output by Agent_Financial_ML**
**Completed:** Agent_Docs - Comprehensive metrics framework across 4 documents. 14 key claims supported. Financial: 100% success (avg tau=0.7931). Poverty: 96.9% coverage, 61.5% SMC match. Phase 9 roadmap created.

- Compile comprehensive metrics for both systems
- Compare against baseline methods where applicable
- Document key claims supported by evidence
- Create summary tables for paper inclusion


## Phase 8: Methodology Realignment ✅ COMPLETE

### Task 8.1 – Financial Trend Detection Validator - Agent_Financial_ML ✅ COMPLETE
**Objective:** Implement literature-aligned trend detection using L^p norms and Kendall-tau correlation (Gidea & Katz 2018 methodology).
**Output:** `financial_tda/validation/trend_analysis_validator.py` with trend detection achieving τ ≥ 0.70.
**Guidance:** Leverage existing G&K replication code from Task 7.2 (L^p norm computation already working). Implement Kendall-tau trend correlation on 250-day pre-crisis windows. Target events: 2008 GFC (already τ=0.814), 2000 dotcom, 2020 COVID. Update validation reports and methodology documentation. **Depends on: Task 7.2 Output (G&K replication code)**
**Completed:** Agent_Financial_ML - 100% validation success across 3 events + **Six Market Global Validation**.
- US Only: 2008 GFC (τ=0.9165), 2000 Dotcom (τ=0.7504), 2020 COVID (τ=0.7123).
- **Global 6-Market**: 2008 GFC (τ=0.9294 - stronger signal), 2023 Validation (τ=0.8270 trend but low magnitude <0.20 ratio).
- **Critical Outcome**: Established "Trend vs Magnitude" taxonomy distinguishing Structural Crises (2008) from Velocity Shocks (2020) and Stable Volatility (2023).
- Parameter optimization framework validated.

1. Create `financial_tda/validation/trend_analysis_validator.py` with Kendall-tau trend detection
2. Implement `compute_trend_indicator()` function: compute kendall-tau correlation between time indices and L^p norms for 250-day pre-crisis windows
3. Validate on 2008 GFC (verify τ≥0.70, already achieved 0.814 in G&K replication)
4. Validate on 2000 dotcom crash (new event, target τ≥0.70)
5. Validate on 2020 COVID crash (target τ≥0.70)
6. **[NEW] Six-Market Validation**: Confirm robustness on global basket (S&P, FTSE, DAX, CAC, Nikkei, Hang Seng)
7. Update `financial_tda/validation/CHECKPOINT_REPORT.md` with revised validation criteria (trend detection)
8. Create `docs/METHODOLOGY_ALIGNMENT.md` explaining task difference

### Task 8.2 – Poverty TDA Paper Draft - Agent_Docs ✅ COMPLETE
**Objective:** Draft academic paper for poverty TDA results targeting economics/policy journals.
**Output:** Paper draft (LaTeX/Markdown) ready for journal submission.
**Guidance:** **HEAVY REVIEW required.** Target: Journal of Economic Geography or Regional Studies. Use validation results from Task 7.4 (357 traps, 61.5% SMC match, Cohen's d=-0.74). Connect to UK "Levelling Up" agenda and Social Mobility Commission framework. Include policy implications with concrete recommendations. Can execute in parallel with Task 8.1. **Depends on: Task 7.4 Output by Agent_Poverty_ML**
**Completed:** Agent_Docs - 9,850-word manuscript "UK Poverty Traps: A Topological Data Analysis Approach" targeting Journal of Economic Geography. Strong validation integration (61.5% SMC p<0.01, Cohen's d=-0.74 p<0.001). Gateway LSOA intervention strategy, basin partnership framework, 6 policy recommendations (immediate + medium-term). Figures specification (6 figures + 3 tables), supplementary materials outlined (5 files), 75 citations formatted. Interdisciplinary synthesis successful (Morse theory + regional economics + policy).

1. Create paper outline following target journal format (Journal of Economic Geography style)
2. Write methodology section emphasizing Morse theory applications and topological interpretation
3. Write results section with UK geographic findings (357 traps, statistical validation metrics)
4. Connect findings to UK Levelling Up target areas and Social Mobility Commission reports
5. Write policy implications section with concrete recommendations (gateway LSOA interventions, barrier reduction)
6. **HEAVY REVIEW**: Submit draft for user revision


## Phase 9: Documentation & Publication

### Task 9.1 – Financial TDA Paper Finalization - Agent_Docs
**Objective:** Finalize academic paper for financial TDA results using Task 8.1 validated methodology.
**Output:** Paper draft (LaTeX/Markdown) for journal submission.
**Guidance:** **HEAVY REVIEW required.** Primary target: Quantitative Finance or Journal of Financial Data Science. Alternatives: arXiv preprint (q-fin.ST), SSRN working paper for faster dissemination. Include mathematical formulations with full proofs in appendix. Use Task 8.1 validation results (100% success, τ=0.7931, 3 events validated). **Depends on: Task 8.1 Output (Financial Trend Detection Validator)**

1. Create paper outline following target journal format (Quantitative Finance style)
2. Write methodology section with mathematical formulations (Takens embedding, persistence diagrams, Kendall-tau trend detection)
3. Write results section with Task 8.1 validation metrics and visualizations (GFC, Dotcom, COVID)
4. Write discussion comparing to prior work (Gidea & Katz, other TDA finance papers) and parameter optimization findings
5. **HEAVY REVIEW**: Submit draft for user revision

### Task 9.2 – Policy Brief - Poverty Traps - Agent_Docs
**Objective:** Create policy brief for NGO/government audiences.
**Output:** 2-4 page policy brief with recommendations.
**Guidance:** **HEAVY REVIEW required.** Target audiences: UK government departments (DLUHC, DfE), think tanks (Resolution Foundation, Social Mobility Foundation), charities (Joseph Rowntree Foundation). Non-technical executive summary, actionable recommendations with clear next steps. **Depends on: Task 8.2 Output**

1. Create 2-4 page policy brief structure (executive summary, key findings, recommendations, methodology appendix)
2. Write executive summary with key findings (non-technical, accessible language)
3. Add actionable recommendations with topological backing (gateway LSOA interventions, barrier reduction)
4. **HEAVY REVIEW**: Submit draft for user revision

### Task 9.3 – Technical Blog - Financial - Agent_Docs
**Objective:** Create technical blog posts for financial TDA.
**Output:** Blog post drafts (2 posts).
**Guidance:** Lower priority than papers. "What Shape is a Market Crash?" + tutorial. **Depends on: Task 8.1 Output (Financial Trend Detection Validator)**

1. Create "What Shape is a Market Crash?" introductory post
2. Create technical tutorial "Building a Topological Early Warning System"
3. Add code snippets and visualizations
4. Submit drafts for user review

### Task 9.4 – Technical Blog - Poverty - Agent_Docs
**Objective:** Create technical blog posts for poverty TDA.
**Output:** Blog post drafts (2 posts).
**Guidance:** Lower priority than papers. "The Shape of Opportunity" + methodology. **Depends on: Task 8.2 Output (Poverty Paper Draft)**

1. Create "The Shape of Opportunity" introductory post
2. Create methodology post "Finding Poverty Traps with Topology"
3. Add geographic visualizations and maps
4. Submit drafts for user review

### Task 9.5 – API Documentation - Agent_Docs
**Objective:** Create comprehensive API documentation.
**Output:** API reference and usage guides.
**Guidance:** Use Sphinx with autodoc extension for automatic API reference generation from docstrings. Host on ReadTheDocs or GitHub Pages. Example notebooks using Jupyter with nbsphinx integration. **Depends on: All implementation phases Output**

1. Configure Sphinx with autodoc, napoleon (Google-style docstrings), and nbsphinx
2. Generate API reference from docstrings automatically
3. Write usage guides for key modules (data fetching, topology computation, detection)
4. Add example notebooks demonstrating end-to-end workflows
5. Submit for user review

### Task 9.6 – Supplementary Materials & Figures - Agent_Docs
**Objective:** Complete poverty paper figures production and supplementary materials.
**Output:** 6 figures + 3 tables + 5 supplementary files.
**Guidance:** Per `poverty_tda/figures_specification.md` and `poverty_tda/supplementary_outline.md`. **Depends on: Task 8.2 Output**

1. Generate 6 main figures (mobility surface, trap distribution, SMC validation, regional patterns, case studies, basin structure)
2. Create 3 tables (trap characteristics, validation metrics, regional breakdown)
3. Compile 5 supplementary files (extended methodology PDF, complete trap rankings CSV+GeoJSON, replication code, extended validation PDF, case studies PDF)
4. LaTeX conversion and formatting for Journal of Economic Geography submission
5. Submit for user review


## Phase 9.5: Empirical Validation ✅ COMPLETE

### Task 9.5.1 – TDA Comparison Protocol - Agent_Poverty_Topology ✅ COMPLETE
**Objective:** Execute empirical comparison of TDA methods (Morse-Smale, Mapper) vs traditional spatial statistics (K-means, LISA, Gi*, DBSCAN) using η² variance explained.
**Output:** Validated results showing TDA superiority, results framework, regional mobility surfaces.
**Guidance:** Compare methods on life expectancy prediction. Bootstrap CIs for statistical rigor. Cross-region replication (West Midlands, Greater Manchester). **Depends on: Task 2.5 Output, Phase 6.5 TTK Integration**
**Completed:** Agent_Poverty_Topology (via Antigravity) - 100% validation success. MS explains 73-83% of LE variance vs K-means 33-46% vs spatial methods 10-20%. Novel finding: TDA closes sex gap (male/female equally explained). Results framework created. Total 3,274 LSOAs validated across 2 regions.

1. Create high-resolution (100×100) regional mobility surfaces for WM and GM
2. Apply all methods: Morse-Smale, K-means, DBSCAN, LISA, Gi*, Mapper
3. Compute η² with bootstrap 95% CIs (n=1,000) for each method
4. Replicate across West Midlands and Greater Manchester regions
5. Compare male vs female life expectancy outcomes
6. Create results framework for standardized storage and reporting
7. Benchmark against Liverpool study (IMD → LE regression)

**Key Results:**
- Morse-Smale: η² = 0.73-0.83 (best)
- K-means: η² = 0.33-0.46 (2nd)
- Spatial methods: η² = 0.10-0.20 (3rd)
- Sex gap closed: <2pp difference vs benchmark 24pp
- CIs do not overlap: statistically significant

### Task 9.5.2 – Boundary Analysis (Barrier-Gradient Correlation) - Agent_Poverty_Topology ⭐ HIGH PRIORITY
**Objective:** Test whether Morse-Smale barrier heights predict real outcome gradients across boundaries.
**Output:** Correlation analysis showing barriers capture (or don't capture) real discontinuities.
**Guidance:** This is TDA's unique value proposition. Extract saddle heights, compute outcome gradients across adjacent basins, test correlation. **Depends on: Task 9.5.1 Output**

1. Extract Morse-Smale separatrices and saddle heights from regional surfaces
2. Identify adjacent basin pairs and compute outcome gradients (ΔLE, ΔKS4)
3. Correlate barrier heights with outcome gradients: r(barrier, gradient)
4. Test: r > 0.5 means barriers capture real discontinuities
5. Document findings - do TDA boundaries have policy meaning?

**Success Criterion:** r > 0.5 validates TDA barriers as meaningful.

### Task 9.5.3 – Agreement Analysis (ARI Matrix) - Agent_Poverty_Topology
**Objective:** Compute Adjusted Rand Index between all method pairs to assess agreement.
**Output:** ARI matrix showing which methods find similar structures.
**Guidance:** Tests whether TDA finds "new" structures or replicates traditional findings. **Depends on: Task 9.5.1 Output**

1. For each region, compute ARI between all pairs: MS, K-means, LISA, Gi*, DBSCAN, Mapper
2. Hierarchical cluster methods by output similarity
3. Identify: High ARI (>0.7) = replication; Low ARI (<0.4) = different structures
4. Key comparison: ARI(MS, LISA LL clusters)

### Task 9.5.3.5 – Migration Validation (Behavioral Outcomes) - Agent_Poverty_Topology
**Objective:** Test whether Morse-Smale basins predict internal migration patterns (fully independent outcome).
**Output:** Migration η² comparison, escape rate analysis, barrier-gradient correlation.
**Guidance:** ONS internal migration is NOT derived from IMD. Validates basins as behavioral constraints. **Depends on: Task 9.5.1 Output**
**Implementation:** `poverty_tda/data/process_migration.py`, `poverty_tda/validation/migration_validation.py`

1. Process `internal_migration_by_lad.xlsx` into LAD-level metrics (net rate, churn, directional flows)
2. Join to LSOA data via LAD containment
3. Compute η² for migration ~ ms_basin vs k-means vs LISA
4. Compute escape rate by basin severity (expect: high-severity basins → lower escape rates)
5. Test correlation(barrier_height, migration_gradient) if barrier data available
6. Document: Do high-severity basins show expected migration patterns?

**Success Criteria:**
- MS η² > K-means η² for migration (same pattern as LE/KS4)
- High-severity basins show lower escape rates (behavioral validation)

### Task 9.5.4 – Integrated Model Testing (Regression) - Agent_Poverty_Topology
**Objective:** Test whether TDA features add predictive power in regression models.
**Output:** Model comparison table showing incremental R² from TDA features.
**Guidance:** Answers: "Does MS add value beyond raw deprivation score?" **Depends on: Task 9.5.1 Output**

1. Fit baseline: outcome ~ mean_imd_score
2. Fit Model A: outcome ~ mean_imd + lisa_cluster
3. Fit Model B: outcome ~ mean_imd + ms_basin + basin_persistence
4. Compare ΔR², AIC, cross-validated RMSE
5. Document: Does TDA provide incremental predictive value?

### Task 9.5.5 – Persistence Threshold Sensitivity - Agent_Poverty_Topology
**Objective:** Test Morse-Smale stability across persistence threshold choices.
**Output:** Stability analysis showing robustness to parameter choice.
**Guidance:** Complete the partial stability analysis. Test 1%, 3%, 5%, 7%, 10% thresholds. **Depends on: Task 9.5.1 Output**

1. Run MS at persistence thresholds: [1%, 3%, 5%, 7%, 10%]
2. Count basins at each threshold
3. Identify top 10 most severe basins at each threshold
4. Compute Jaccard overlap with 5% baseline
5. Compare parameter sensitivity: MS vs DBSCAN ε variation


## Phase 10: Deployment & Enhancement


### Task 10.1 – User Acceptance Testing (Optional) - Agent_QA
**Objective:** Optional external UAT with 3-5 testers before public deployment.
**Output:** UAT feedback report.
**Guidance:** Optional task - can skip if internal validation sufficient. Recruit from target audience (finance professionals, policy analysts). **Depends on: Phase 6 Output (dashboards validated)**

1. Recruit 3-5 external testers (finance, policy backgrounds)
2. Conduct UAT sessions (dashboard testing, feedback collection)
3. Compile feedback and prioritize fixes
4. Implement high-priority improvements

### Task 10.2 – Streamlit Cloud Deployment - Agent_DevOps
**Objective:** Deploy financial and poverty dashboards to Streamlit Cloud.
**Output:** Production URLs with monitoring.
**Guidance:** Phase 6 visual validation complete - ready to deploy. Configure secrets management for API keys. **Depends on: Phase 6 Output, Phase 9 API docs complete**

1. Create Streamlit Cloud account and configure deployment settings
2. Deploy financial TDA dashboard (`financial_tda/viz/streamlit_app.py`)
3. Deploy poverty TDA dashboard (`poverty_tda/viz/dashboard.py`)
4. Deploy interactive maps application (`poverty_tda/viz/maps.py`)
5. Configure secrets management (FRED_API_KEY, data sources)
6. Test production deployments and document URLs

### Task 10.3 – Monitoring & Analytics Integration - Agent_DevOps
**Objective:** Add error tracking and usage analytics to deployed applications.
**Output:** Sentry error tracking + usage metrics dashboard.
**Guidance:** Track errors, performance, user behavior for continuous improvement. **Depends on: Task 10.2 Output**

1. Integrate Sentry for error tracking and performance monitoring
2. Add usage analytics (page views, feature usage, session duration)
3. Create monitoring dashboard for application health
4. Configure alert thresholds (error rates, response times)

### Task 10.4 – Real-time Enhancements - Agent_Financial_Viz
**Objective:** Add email/SMS alerts and WebSocket integration for real-time updates.
**Output:** Alert system + live data streaming.
**Guidance:** Enhance real-time monitoring with notification system. **Depends on: Task 10.2 Output**

1. Implement email alert system (SendGrid/AWS SES) for crisis detection
2. Add SMS alerts (Twilio) for critical threshold crossings (optional)
3. Integrate WebSocket for live data streaming (reduce polling overhead)
4. Test alert delivery and notification timing

### Task 10.5 – Dashboard Refinement Post-Deployment - Agent_Financial_Viz + Agent_Poverty_Viz
**Objective:** Post-deployment improvements based on user feedback.
**Output:** Enhanced dashboard features.
**Guidance:** Address user feedback from production usage. **Depends on: Task 10.2-10.4 Output**

1. Collect user feedback from production deployment (2 weeks)
2. Prioritize enhancement requests
3. Implement high-priority improvements
4. Deploy updates to production


## Phase 11: Testing & Quality Assurance

### Task 11.1 – Unit Test Completion - Agent_Financial_ML
**Objective:** Add unit tests for trend_analysis_validator.py and realtime detection scripts.
**Output:** Unit test suite with 90%+ coverage.
**Guidance:** Deferred from Task 8.1 - close testing gap. **Depends on: Task 8.1 Output**

1. Add unit tests for `financial_tda/validation/trend_analysis_validator.py`
2. Add unit tests for realtime detection scripts (`step2_validate_2008_gfc.py`, etc.)
3. Add unit tests for `analyze_tau_discrepancies.py`
4. Achieve 90%+ code coverage for validation module
5. Add tests to CI/CD pipeline

### Task 11.2 – Cross-Browser & Performance Testing - Agent_QA
**Objective:** Cross-browser testing and TDA performance benchmarking.
**Output:** Browser compatibility matrix + performance benchmarks.
**Guidance:** Test Chrome, Firefox, Safari, Edge. Benchmark VR persistence, Morse-Smale computation. **Depends on: Task 10.2 Output**

1. Test dashboards on browser matrix (Chrome, Firefox, Safari, Edge)
2. Document compatibility issues and implement fixes
3. Benchmark TDA computations (VR persistence, Morse-Smale) on various dataset sizes
4. Profile memory usage and optimize bottlenecks
5. Document performance characteristics

### Task 11.3 – False Positive Analysis - Agent_Financial_ML
**Objective:** Test financial detection system on 5+ non-crisis periods.
**Output:** False positive rate report with recommendations.
**Guidance:** Critical for production credibility. Test periods: 2004-2007, 2013-2014, 2017-2019, 2021, 2023-early 2024. **Depends on: Task 8.1 Output**

1. Define 5+ non-crisis test periods (sustained normal markets)
2. Run detection system on each period with standard parameters
3. Analyze false positive rate (false alarm rate vs lead time tradeoff)
4. Recommend threshold adjustments if FPR > 10%
5. Document validation results

### Task 11.4 – Data Provider Robustness Testing - Agent_Financial_Data
**Objective:** Test alternative data providers for data source redundancy.
**Output:** Data provider comparison report.
**Guidance:** Test Alpha Vantage, IEX Cloud, Polygon.io as Yahoo Finance backups. **Depends on: Phase 1 Output**

1. Test alternative data providers (Alpha Vantage, IEX Cloud, Polygon.io)
2. Compare data quality, coverage, rate limits, costs
3. Implement fallback logic for Yahoo Finance failures
4. Add tests for multi-provider data fetching
5. Document provider selection recommendations

### Task 11.5 – Docker Containerization - Agent_DevOps
**Objective:** Create Docker containers for reproducibility and CI/CD.
**Output:** Dockerfiles + docker-compose + CI/CD integration.
**Guidance:** Reproducible environments for development, testing, production. **Depends on: Phase 0 Output**

1. Create Dockerfiles for financial TDA, poverty TDA, shared utilities
2. Add docker-compose for multi-container orchestration
3. Integrate Docker builds into CI/CD pipeline
4. Add Docker deployment documentation
5. Test container builds on clean environments


## Phase 12: Extended Financial Validation

### Task 12.1 – Historical Crisis Extension - Agent_Financial_ML
**Objective:** Validate on 4 additional historical crises (1987, 1998, 2011, 2015).
**Output:** Extended validation report with 7 total crises.
**Guidance:** Strengthen financial paper validation. Target: τ ≥ 0.70 for at least 5/7 events. **Depends on: Task 8.1 Output**

1. Validate 1998 LTCM collapse (August-September 1998) - P1
2. Validate 2011 EU debt crisis (July-August 2011) - P1
3. Validate 2015 China devaluation (August 2015) - P1
4. Validate 1987 Black Monday (October 1987) - P2
5. Compile extended validation report (7 crises total)
6. Update financial paper with extended validation results

### Task 12.2 – Crypto Crisis Multi-Asset Analysis - Agent_Financial_ML
**Objective:** Full validation of 2022 crypto crashes using multi-asset approach.
**Output:** Crypto crisis validation report.
**Guidance:** Single-asset (BTC) approach failed in Task 7.2. Try multi-crypto portfolio (BTC, ETH, SOL, ADA). **Depends on: Task 8.1 Output**

1. Fetch multi-crypto data (BTC, ETH, SOL, ADA) for 2022
2. Apply multi-asset G&K methodology (4D point cloud from 4 cryptos)
3. Validate Terra/LUNA collapse (May 2022) and FTX collapse (November 2022)
4. Compare multi-asset vs single-asset detection performance
5. Document crypto-specific parameter requirements

### Task 12.3 – Multi-Asset Expansion - Agent_Financial_ML
**Objective:** Extend to bonds, commodities, FX for cross-asset crisis detection.
**Output:** Multi-asset TDA framework.
**Guidance:** Test if topological signals strengthen with cross-asset correlations. **Depends on: Task 8.1 Output**

1. Fetch bond data (10Y Treasury, corporate bonds via FRED)
2. Fetch commodity data (gold, oil via Yahoo Finance)
3. Fetch FX data (major currency pairs)
4. Construct multi-asset point clouds (equities + bonds + commodities + FX)
5. Validate on 2008 GFC with multi-asset approach
6. Compare multi-asset vs equity-only detection quality

### Task 12.4 – Sector-Specific Models - Agent_Financial_ML
**Objective:** Develop sector-specific crisis detection models (tech, finance, energy).
**Output:** Sector-specific parameter sets.
**Guidance:** Different sectors may require different parameters (e.g., tech more volatile, requires longer windows). **Depends on: Task 8.1 Output**

1. Identify sector-specific indices (tech: XLK, finance: XLF, energy: XLE)
2. Run parameter sensitivity analysis per sector
3. Identify optimal parameters for each sector (rolling window, precrash window)
4. Validate sector models on historical sector-specific crises
5. Document sector-specific guidance

### Task 12.5 – International Markets Validation - Agent_Financial_ML
**Objective:** Validate on European and Asian indices.
**Output:** International validation report.
**Guidance:** Test generalization beyond US markets. May require paid data providers (Bloomberg, Refinitiv). **Depends on: Task 8.1 Output**

1. Fetch European indices (STOXX 50, DAX, FTSE) for 2008, 2011, 2020
2. Fetch Asian indices (Nikkei, Hang Seng, Shanghai) for 1997, 2008, 2020
3. Apply G&K methodology to international multi-index portfolios
4. Validate on region-specific crises (1997 Asian financial crisis, 2011 EU debt)
5. Document cross-market generalization results

### Task 12.6 – Ensemble Detection System - Agent_Financial_ML
**Objective:** Combine L¹/L² variance + spectral density for robust ensemble detection.
**Output:** Ensemble detector with voting/weighted averaging.
**Guidance:** G&K paper suggests variance AND spectral density together. Current implementation uses variance only. **Depends on: Task 8.1 Output**

1. Implement spectral density computation from persistence landscapes
2. Apply Kendall-tau trend detection to spectral density time series
3. Create ensemble voting system (L¹ variance, L² variance, L¹ spectral, L² spectral)
4. Test ensemble on 3 validated crises (2008, 2000, 2020)
5. Compare ensemble vs single-metric detection performance


## Phase 13: Real-time Production Systems

### Task 13.1 – Production Monitoring Deployment - Agent_DevOps
**Objective:** Deploy real-time monitoring system to AWS/Azure.
**Output:** Production monitoring infrastructure.
**Guidance:** Automated daily/hourly detection runs with alert system. **Depends on: Phase 10 Output, Task 11.3 Output**

1. Design production monitoring architecture (AWS Lambda + S3 or Azure Functions + Blob Storage)
2. Implement automated data fetching and TDA computation pipeline
3. Deploy detection system with configurable schedule (daily/hourly)
4. Integrate with alert system (email/SMS/Slack)
5. Add monitoring dashboard for system health

### Task 13.2 – 2023-2025 Real-time Validation - Agent_Financial_ML ⚠️ PARTIAL COMPLETE (Ad-Hoc)
**Objective:** Validate detection system on recent 2023-2025 period.
**Output:** Real-time validation report.
**Guidance:** `realtime_detection_2023_2025.py` script exists - complete validation. Test on 2023 banking crisis (March), 2024 events. **Depends on: Task 8.1 Output**
**Status:** Preliminary analysis complete (991 days 2022-2025, τ=0.36 no crisis signal, ZERO false positives). Formal validation with 2023 banking crisis focus pending.

1. Complete `realtime_detection_2023_2025.py` script execution
2. Validate on 2023 banking crisis (Silicon Valley Bank, March 2023)
3. Analyze 2024 market events (if any volatility spikes)
4. Compare real-time detection vs historical backtest performance
5. Document findings in `2023_2025_realtime_analysis.md`

### Task 13.3 – Automated Parameter Optimization Pipeline - Agent_Financial_ML
**Objective:** Automate grid search parameter optimization for new events.
**Output:** Parameter optimization automation framework.
**Guidance:** Current manual process (Task 8.1 bonus work). Automate for production use. **Depends on: Task 8.1 Output**

1. Extract parameter optimization code from `analyze_tau_discrepancies.py`
2. Create automated grid search framework (rolling window, precrash window combinations)
3. Add early stopping for computational efficiency
4. Implement caching for repeated computations
5. Create CLI tool for parameter optimization on new datasets

### Task 13.4 – Alert System Implementation - Agent_DevOps
**Objective:** Implement production alert system (email/SMS/Slack).
**Output:** Multi-channel alert delivery system.
**Guidance:** Configurable thresholds, alert fatigue management. **Depends on: Task 13.1 Output**

1. Implement email alerts (SendGrid/AWS SES) with HTML templates
2. Add SMS alerts (Twilio) for critical thresholds
3. Integrate Slack webhooks for team notifications
4. Add alert fatigue management (cooldown periods, escalation rules)
5. Create alert configuration dashboard

### Task 13.5 – Crisis Severity Prediction - Agent_Financial_ML
**Objective:** Predict crisis severity (drawdown magnitude) from Kendall-tau magnitude.
**Output:** Severity prediction model.
**Guidance:** Research extension - can τ magnitude predict peak drawdown? Train on historical crises. **Depends on: Task 12.1 Output**

1. Extract τ magnitude and peak drawdown from 7 historical crises
2. Train regression model (τ → peak drawdown prediction)
3. Validate on out-of-sample crisis events
4. Add severity prediction to monitoring dashboard
5. Document prediction accuracy and limitations

### Task 13.6 – Intraday Detection Research - Agent_Financial_ML
**Objective:** Feasibility study for hourly/minute-level crisis detection.
**Output:** Intraday detection research report.
**Guidance:** Research extension - high computational cost. Test on Flash Crash (2010) if feasible. **Depends on: Task 8.1 Output**

1. Fetch intraday data (hourly/minute) for test period (e.g., 2010 Flash Crash)
2. Apply G&K methodology with adjusted window sizes (hours instead of days)
3. Analyze computational cost vs detection quality tradeoff
4. Document feasibility findings and recommendations
5. Prototype intraday detection if feasible


## Phase 14: International & Cross-Asset Extensions

### Task 14.1 – US Opportunity Atlas Application - Agent_Poverty_ML
**Objective:** Apply Morse-Smale analysis to US Opportunity Atlas (73,000 census tracts).
**Output:** US poverty trap identification report.
**Guidance:** High-value extension for US policy engagement. Prototype on single state (e.g., California) before full-scale. **Depends on: Phase 7 Poverty Output**

1. Download US Opportunity Atlas data (census tract level)
2. Prototype on single state (California ~8,000 tracts) for workflow validation
3. Scale to full US (73,000 tracts) with chunked processing
4. Apply Morse-Smale decomposition and trap identification
5. Validate against known disadvantaged regions (Appalachia, Deep South, Rust Belt)
6. Compare UK vs US trap characteristics

### Task 14.2 – Temporal Poverty Analysis - Agent_Poverty_ML
**Objective:** Analyze IMD 2015 vs IMD 2019 evolution to identify trap dynamics.
**Output:** Temporal trap evolution report.
**Guidance:** Longitudinal analysis - which traps persist, strengthen, weaken, or disappear? **Depends on: Phase 7 Poverty Output**

1. Download IMD 2015 data
2. Construct 2015 mobility surface and trap identification
3. Compare 2015 vs 2019 trap structures (persistent, emerged, disappeared)
4. Analyze trap strengthening/weakening patterns
5. Correlate with policy interventions (if data available)

### Task 14.3 – Wales & UK-Wide Coverage - Agent_Poverty_ML
**Objective:** Complete UK analysis by including Wales (currently England-only).
**Output:** Complete UK trap identification.
**Guidance:** Simple extension - Wales adds ~2,000 LSOAs. **Depends on: Phase 7 Poverty Output**

1. Include Wales LSOAs in dataset (~2,000 additional)
2. Recompute mobility surface and Morse-Smale complex
3. Validate trap identification in Welsh deprived areas (Valleys)
4. Update poverty paper with complete UK coverage

### Task 14.4 – Adaptive Mesh Refinement - Agent_Poverty_Topology
**Objective:** Implement variable grid resolution (fine in urban, coarse in rural).
**Output:** Adaptive mesh refinement module.
**Guidance:** Current 75×75 uniform grid masks urban heterogeneity. Use 1-2 km urban, 10+ km rural. **Depends on: Task 2.4 Output**

1. Implement adaptive mesh refinement algorithm (quadtree-based)
2. Configure resolution rules (1-2 km urban areas, 10+ km rural areas)
3. Recompute mobility surface with adaptive mesh
4. Compare trap identification accuracy vs uniform grid
5. Document computational cost vs precision tradeoff

### Task 14.5 – Basin-to-LAD Precise Mapping - Agent_Poverty_Topology
**Objective:** Compute precise basin-to-LAD spatial overlap using polygon intersection.
**Output:** Basin-LAD mapping with percentage overlap.
**Guidance:** Current approach uses LSOA-to-LAD lookup. Compute actual spatial overlap for precise basin population. **Depends on: Phase 7 Poverty Output**

1. Implement polygon intersection (basin boundaries ∩ LAD boundaries)
2. Compute percentage overlap for each basin-LAD pair
3. Calculate weighted basin population by LAD
4. Update validation reports with precise overlap statistics
5. Add visualization of basin-LAD boundaries

### Task 14.6 – Cross-Country Comparison - Agent_Poverty_ML
**Objective:** Compare UK vs US vs EU poverty trap characteristics.
**Output:** Cross-country comparison paper.
**Guidance:** Research extension - requires international datasets. Compare trap density, severity, regional patterns. **Depends on: Task 14.1 Output, Task 14.3 Output**

1. Apply Morse-Smale analysis to EU regional data (if available)
2. Compare trap characteristics across UK, US, EU
3. Analyze cultural/policy differences correlating with trap patterns
4. Document cross-country findings
5. Write comparative analysis paper

### Task 14.7 – Gateway Intervention Transfer - Agent_Docs
**Objective:** Transfer gateway intervention concept from poverty to financial TDA.
**Output:** Gateway intervention framework paper.
**Guidance:** Conceptual transfer - "gateway stocks" before crisis, "gateway LSOAs" before poverty. **Depends on: Phase 7 Output (both tracks)**

1. Conceptualize "gateway stocks" analogy (periphery of crisis basin)
2. Identify gateway stocks in historical crises (stocks at separatrices)
3. Analyze if targeting gateway stocks provides early warning
4. Write methodology paper on cross-domain gateway concept
5. Submit to interdisciplinary journal


## Phase 15: Advanced Research Extensions

### Task 15.1 – Crisis-Type Classifier - Agent_Financial_ML
**Objective:** ML classifier to predict optimal metric (L¹ vs L² variance vs spectral density) per crisis type.
**Output:** Crisis-type classifier model.
**Guidance:** Task 8.1 found L² works for GFC/COVID, L¹ for dotcom. Can ML predict best metric? **Depends on: Task 12.1 Output**

1. Extract features from historical crises (volatility regime, sector leadership, etc.)
2. Train classifier (crisis features → optimal metric selection)
3. Validate on out-of-sample crises
4. Integrate classifier into ensemble detection system
5. Document metric selection automation

### Task 15.2 – Principled Threshold Selection - Agent_Poverty_Topology
**Objective:** Develop information-theoretic or bootstrap-based threshold selection method.
**Output:** Principled threshold selection framework.
**Guidance:** Current 5% persistence threshold is data-driven but lacks theoretical foundation. **Depends on: Phase 7 Poverty Output**

1. Research information-theoretic threshold selection methods
2. Implement bootstrap-based confidence regions for persistence
3. Test threshold selection on synthetic data with known structure
4. Compare principled methods vs empirical 5% threshold
5. Document theoretical foundation and recommendations

### Task 15.3 – Alternative Homology Exploration - Agent_Financial_Topology
**Objective:** Explore H₀ (connected components) and H₂ (voids) for additional crisis signals.
**Output:** Alternative homology research report.
**Guidance:** Current focus on H₁ (loops). Test if H₀/H₂ provide complementary information. **Depends on: Phase 2 Financial Output**

1. Compute H₀ and H₂ persistence diagrams for historical crises
2. Analyze H₀/H₂ landscape trends with Kendall-tau
3. Compare H₀/H₂ detection performance vs H₁
4. Test ensemble combining H₀, H₁, H₂
5. Document findings and recommendations

### Task 15.4 – Topology-Aware VAE Loss - Agent_Poverty_ML
**Objective:** Implement Betti number regularization for topology-preserving VAE.
**Output:** Topology-aware VAE implementation.
**Guidance:** Research from Hu et al. (2019). Preserve topological features in latent space. **Depends on: Task 5.6 Output**

1. Research Betti number regularization methods (Hu et al. 2019)
2. Implement topological loss component (Betti matching between input and reconstruction)
3. Train topology-aware VAE on mobility surfaces
4. Evaluate topological preservation vs standard VAE
5. Document research findings

### Task 15.5 – ML Integration Research - Agent_Financial_ML
**Objective:** Integrate topological features as inputs to LSTM/Transformer for hybrid detection.
**Output:** Hybrid TDA+ML detection system.
**Guidance:** Research extension - combine topological features with deep learning. **Depends on: Task 5.1 Output**

1. Extract topological features as time series (landscape norms, entropy, Betti curves)
2. Train LSTM on topological features + raw returns
3. Train Transformer on topological features + raw returns
4. Compare hybrid TDA+ML vs pure TDA detection
5. Document hybrid approach performance and complexity

### Task 15.6 – Agent-Based Modeling - Agent_Poverty_ML
**Objective:** Simulate mobility dynamics with agent-based modeling for counterfactual validation.
**Output:** Agent-based mobility simulation framework.
**Guidance:** Research extension - simulate intervention effects (e.g., remove barrier → mobility improves?). **Depends on: Phase 4 Poverty Output**

1. Design agent-based model of mobility dynamics on surface
2. Implement mobility rules (agents move up gradient, barriers slow movement)
3. Simulate baseline dynamics (no intervention)
4. Simulate counterfactual (barrier removal, gateway strengthening)
5. Compare simulated outcomes vs actual intervention data (if available)

### Task 15.7 – Methods Comparison Paper - Agent_Docs
**Objective:** Write comparative methods paper on temporal vs spatial TDA validation.
**Output:** Methods paper draft.
**Guidance:** Use Task 7.5 cross-system framework. Target: Journal of Computational Science. **Depends on: Task 7.5 Output**

1. Extract content from Task 7.5 cross-system comparison
2. Write methods comparison paper (temporal Kendall-tau vs spatial statistical tests)
3. Document when each approach is appropriate
4. Add case studies (financial, poverty, hypothetical domains)
5. Submit to Journal of Computational Science

### Task 15.8 – Unified TDA Methodology Template - Agent_Docs
**Objective:** Create reusable TDA methodology template for future applications.
**Output:** Methodology template document + codebase.
**Guidance:** Generalize financial and poverty pipelines into domain-agnostic template. **Depends on: Phase 7 Output (both tracks)**

1. Extract common patterns from financial and poverty TDA pipelines
2. Create domain-agnostic template (data → embedding/surface → filtration → features → validation)
3. Document template with decision tree (when to use Takens vs surface, VR vs Morse-Smale, etc.)
4. Add example applications (hypothetical use cases)
5. Publish template as methodological contribution


---

## Phases 0-8, 9.5 Status: ✅ COMPLETE

**For detailed task breakdowns of Phases 0-8 and 9.5, see above sections.**

---

## Timeline Summary

**Phase 9:** 6-8 weeks (Documentation & Publication) - **IN PROGRESS**  
**Phase 10:** 3-4 weeks (Deployment & Enhancement)  
**Phase 11:** 3-4 weeks (Testing & QA) - *Can run parallel to Phase 12*  
**Phase 12:** 4-6 weeks (Extended Financial Validation) - *Can run parallel to Phase 11*  
**Phase 13:** 5-6 weeks (Real-time Production Systems)  
**Phase 14:** 6-8 weeks (International & Cross-Asset Extensions)  
**Phase 15:** 8-10 weeks (Advanced Research Extensions)

**Total Duration:** 35-46 weeks (8.5-11 months)  
**Target Completion:** October-November 2026

**Production Release Timeline:**
- Documentation complete: ~8 weeks (mid-March 2026)
- Deployment + QA: ~7 weeks (early May 2026)
- Public production release: **Early May 2026**
- Enhanced production (Phase 12+13): **July 2026**
