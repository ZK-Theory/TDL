Let’s treat these as two distinct, production-grade projects built around the same core stack:

* **GitHub Copilot** → code scaffolding, refactors, tests, boilerplate
* **ParaView + TTK + Claude MCP** → interactive, agent-assisted topology exploration + figure production
* **Deep learning** → models that *consume or are constrained by* topological structure
* **Python TDA stack (e.g. giotto-tda / scikit-tda)** → persistent homology, landscapes, diagrams 

---

## Project 1 – Early Warning System for Financial Regime Changes (Option 1)

### 1. Objective & outputs

**Goal:** Build a pipeline that ingests market time series, computes topological signatures of sliding windows, and flags impending regime changes (crashes, volatility spikes, structural shifts).

**Concrete outputs:**

* Python package: `tda_regime_detector/`
* ParaView state files (`.pvsm`) + scripts for 3D Takens embeddings & TTK diagrams
* A few trained DL models benchmarked vs baselines
* One longform blog post + a short paper-style preprint

---

### 2. Stack & tool strategy

**Languages / core libs**

* Python: `pandas`, `numpy`, `scipy`, `giotto-tda` (or `scikit-tda`), `matplotlib/plotly`
* DL: `pytorch` (optionally `pytorch-lightning` for training loops)
* Market data: `yfinance`, `ccxt` or direct HTTP API clients

**GitHub Copilot**

Use Copilot aggressively for:

* ETL + data loaders:

  * generating functions for pulling + caching multi-asset daily/5m OHLCV from Yahoo/CoinGecko
  * writing windowing utilities: sliding windows, multi-asset embedding, normalisation
* Boilerplate experiment code:

  * training loops, metrics, early stopping
  * config-driven experiment runner (`hydra` style) – Copilot is good at generating arg-parsing and config handling
* Test generation:

  * property-based tests for invariances (e.g., “rescaling prices by a constant factor shouldn’t change Betti curves”)

**ParaView + TTK + Claude MCP**

* Use a Claude-backed MCP tool to:

  * Load VTK files exported from Python.
  * Script: `TTKDimensionReduction`, `TTKPersistenceDiagram`, `TTKMorseSmaleComplex` filters.
  * Automate camera paths, colour maps, time sliders; Claude can generate `.py` trace scripts from natural language prompts (“animate the Takens embedding rotating around the attractor over time”).
* Keep a tight loop:

  * Python → export `.vtp` / `.vtu` via `pyvista` or `itk`
  * ParaView (agent-assisted) → explore parameters + produce canonical scenes
  * Record the “good” states as `.pvsm` and export screenshots/videos

**Deep learning**

Two levels:

1. **Topological-feature models (simpler, robust):**

   * Features: persistence images/landscapes, Betti curves, Wasserstein distances to “calm” template.
   * Models: 1D CNN / small Transformer over time-sequence of topological features.

2. **Topology-aware models (more advanced):**

   * Use differentiable PH libraries (e.g. `torchph`, `giotto-tda`’s torch hooks, `TopologyLayer`) to:

     * regularise embeddings (e.g. encourage certain Betti numbers in “calm” vs “crisis” embeddings),
     * or include a topological loss term for stability across noise.

---

### 3. Architecture & code ideas

**Package layout**

```text
tda_regime_detector/
  data/
    loader.py          # market data download/cache
    windows.py         # sliding window logic
  tda/
    embedding.py       # Takens embedding, distance metrics
    persistence.py     # PH computation, landscapes/images
    features.py        # feature vectors per window
  models/
    baseline_stats.py  # volatility, Hurst exponent baselines
    dl_models.py       # CNN/Transformer models
  viz/
    export_vtk.py      # write VTK for ParaView
    plots.py           # quick matplotlib/plotly plots
  experiments/
    train_model.py
    detect_regimes.py
  config/
    *.yaml
```

**Code sketch: Takens + PH**

```python
# tda/embedding.py
def takens_embedding(series, dim=3, delay=5):
    n = len(series) - (dim - 1) * delay
    return np.stack([series[i:i+n:1] for i in range(0, dim*delay, delay)], axis=1)

# tda/persistence.py
from gtda.homology import VietorisRipsPersistence
from gtda.diagrams import PersistenceLandscape

vr = VietorisRipsPersistence(homology_dimensions=[0, 1, 2])
pl = PersistenceLandscape()

def window_to_landscape(X, max_edge_length=None):
    diagrams = vr.fit_transform([X])
    landscapes = pl.fit_transform(diagrams)
    return landscapes[0]  # (n_landscapes, n_samples)
```

Copilot can fill in most of the convenience wrappers once you define clear signatures.

**Export to ParaView/TTK**

```python
# viz/export_vtk.py
import pyvista as pv

def export_takens_vtk(embedding, timestamps, output_path):
    cloud = pv.PolyData(embedding)
    cloud["time"] = timestamps[:embedding.shape[0]]
    cloud.save(output_path)  # .vtp
```

Then, in ParaView (via Claude MCP): load `.vtp` → apply `TTKPersistenceDiagram` + `TTKDimensionReduction` as needed.

---

### 4. Sprint plan (6–8 weeks)

Assume 1-week sprints; adjust to taste.

**Sprint 0 – Environment + replication (Week 1)**

* Set up repo, CI, Copilot, experiment logging (e.g., Weights & Biases).
* Implement basic data download for 3–5 assets (e.g., SPY, QQQ, BTC-USD, ETH-USD).
* Replicate a simple result from one PH-on-finance paper: e.g., Betti curves around 2008 or 2020 crash.

**Sprint 1 – TDA pipeline (Week 2)**

* Implement robust windowing + Takens embeddings (with config: dim, delay, window size).
* Add PH + landscape/image computation.
* Build feature store (HDF5/Parquet) for 10–20 years of daily data.

**Sprint 2 – Baselines & detection logic (Weeks 3–4)**

* Statistical baselines: Z-scores on volatility, rolling Sharpe, realised variance.
* ML baselines: small MLP / logistic regression on simple features.
* Define regime-change labels (e.g., large drawdowns, volatility spikes, structural breaks using Chow tests).

**Sprint 3 – DL models with topological features (Weeks 5–6)**

* Sequence models over sliding windows of topological features.
* Compare:

  * (A) pure statistical features
  * (B) pure TDA features
  * (C) combined
* Evaluate predictive lead time (e.g., can the model flag a regime change 3–5 days ahead with acceptable precision-recall?).

**Sprint 4 – ParaView + agentic workflow + story (Weeks 7–8)**

* Export representative windows (calm vs crisis) as VTK.
* Use Claude MCP to:

  * Script camera paths, colour maps, label overlays.
  * Automate parameter sweeps in TTK, then summarise in markdown.
* Lock in a small set of canonical scenes for the blog/paper.
* Finalise README, demo notebook, and one “push-button” demo script.

---

### 5. Mathematical directions

* **Parameter studies:**

  * Vary Takens dimension/delay; measure topological stability (e.g., bottleneck distances between diagrams for calm vs crisis).
* **Null models:**

  * Randomise returns (shuffled or block-resampled) to test whether observed topological differences survive surrogate tests.
* **Cross-asset structure:**

  * Joint embedding of multiple assets; study how Betti-1/2 features change when cross-correlations spike.
* **Metrics to explore:**

  * Persistence entropy, Wasserstein distances to reference diagrams, time-varying Betti curves.

These become natural axes for figures and ablations in a paper.

---

### 6. Visualisation strategy

**ParaView / TTK**

* 3D scatter of Takens embedding coloured by time → “geometry of calm vs crisis”.
* TTK Persistence Diagram overlaid on these embeddings.
* Animate the embedding across time windows; highlight windows where model predicts high “crash probability”.

**Web / notebooks**

* Ridge-plots of persistence landscapes over time.
* Heatmaps of topological distances to baseline vs calendar time.
* Overlay predicted regime-change probabilities on price charts.

---

### 7. Blog / paper directions

* **Blog title idea:**
  *“Detecting Market Regime Changes with Topological Data Analysis”*
* Structure:

  1. Intuition: markets as moving shapes, not just numbers.
  2. Takens embedding + PH primer (minimal).
  3. Pipeline overview (clear diagrams).
  4. Results on 2008 / 2020 / 2022.
  5. Limitations and failure cases (regimes it *doesn’t* catch).
* **Paper angle:** emphasise:

  * Comparison with classical change-point methods.
  * Role of topology as a robust descriptor under noise and rescaling.
  * Reproducible pipeline + public code.

---

## Project 2 – Poverty Trap Detection via Economic Mobility Topology (Option 2)

### 1. Objective & outputs

**Goal:** Build a “mobility landscape” over geographic space, use Morse–Smale + PH (via TTK) to identify persistent low-mobility basins (“poverty traps”) and robust high-mobility ridges, and tie this to covariates (race, education, policy variables where ethical/appropriate). 

**Concrete outputs:**

* Python package: `mobility_topology/`
* VTK representations of the mobility field; ParaView + TTK state files.
* GNN / spatial DL models that integrate topological features.
* One visually rich blog post + a policy-facing technical note.

---

### 2. Stack & tool strategy

**Core stack**

* Python: `pandas`, `geopandas`, `numpy`, `xarray`, `networkx`
* Spatial: `shapely`, `pyproj`, possibly `pysal` for spatial stats
* TDA: `giotto-tda` (for PH), TTK via ParaView for Morse–Smale, scalar-field simplification
* DL: `pytorch` + `pytorch-geometric` or `dgl` for graph-based models

**GitHub Copilot**

* Schema-aware parsing of Opportunity Atlas and similar datasets (often messy CSV + codebooks).
* Geometry handling:

  * generating `GeoDataFrame` joins, projections (EPSG codes), adjacency graphs from polygons (Queen/rook contiguity).
* GNN boilerplate:

  * Graph building, edge index tensors, message-passing layers.
* Unit tests:

  * e.g., tests that graph is connected, contiguity is symmetric, etc.

**ParaView + TTK + Claude MCP**

* Represent mobility as a scalar field over a 2D spatial mesh:

  * Option 1: Convert tracts to points (centroids) and interpolate to regular grid.
  * Option 2: Use unstructured grid with one cell per tract, scalar = mobility metric.
* Use Claude to:

  * Generate scripts that import the grid, apply `TTKMorseSmaleComplex`, and filter for most persistent basins/ridges.
  * Tune simplification thresholds for interpretable segmentation (e.g., “show only basins corresponding to the top 10% most persistent low-mobility regions”).
* Capture canonical visualisations as `.pvsm` scenes and high-res PNG/SVG.

**Deep learning**

Two main roles:

1. **Representation learning of the mobility field:**

   * Build a tract-level graph; train GNNs to predict mobility from covariates.
   * Use topological features of the learned field (from TTK + PH) as constraints or features.

2. **Topology-aware regularisation:**

   * Encourage models to avoid unrealistic fragmented basins by penalising excessive Betti-0 components in low-mobility regions.
   * Compare performance with/without topological regularisation on predictive accuracy + qualitative structure.

---

### 3. Architecture & code ideas

**Package layout**

```text
mobility_topology/
  data/
    download.py      # Opportunity Atlas, WID, etc.
    preprocess.py    # clean, align, aggregate
  spatial/
    geography.py     # shapefiles, centroids, projections
    graph.py         # adjacency graphs
    interpolation.py # grid interpolation
  tda/
    scalar_field.py  # mobility field generation
    export_vtk.py    # VTK writer
    diagrams.py      # PH on scalar field slices
  models/
    gnn.py           # tract-level GNNs
    topo_reg.py      # topology-regularised loss functions
  viz/
    plots.py         # choropleths, line plots
```

**Code sketch: build adjacency + VTK**

```python
# spatial/graph.py
def build_adjacency(gdf):
    # queen contiguity
    from libpysal.weights import Queen
    w = Queen.from_dataframe(gdf)
    edges = np.array(list(w.neighbors.items()))
    # expand dict form into edge list...
    return edge_index  # shape (2, n_edges)

# tda/export_vtk.py
import pyvista as pv

def export_mobility_field(gdf, value_col, out_path):
    centroids = gdf.geometry.centroid
    points = np.column_stack([centroids.x, centroids.y, np.zeros(len(gdf))])
    mesh = pv.PolyData(points)
    mesh["mobility"] = gdf[value_col].values
    mesh.save(out_path)
```

Use Copilot for the “obvious” loops and type plumbing.

---

### 4. Sprint plan (8–10 weeks)

**Sprint 0 – Data + geography (Week 1)**

* Download core Opportunity Atlas dataset for one state or small multi-state region.
* Load tract polygons with `geopandas`, clean codes, join mobility metrics.
* Build adjacency graphs; visual sanity checks.

**Sprint 1 – Mobility field + basic topology (Week 2)**

* Define scalar fields:

  * `M1 = P(move from bottom to top quartile)`
  * `M2 = expected income rank given parents in bottom quartile`
* Export per-state VTK fields; run TTK manually to get first Morse–Smale decomposition.

**Sprint 2 – Systematic TTK pipeline (Weeks 3–4)**

* Script (with Claude’s help) a ParaView Python pipeline:

  * Load VTK → normalise scalar field.
  * Apply `TTKPersistenceDiagram` + `TTKTopologicalSimplification`.
  * Apply `TTKMorseSmaleComplex`.
* Extract segmentation labels (basin IDs) back into Python via CSV/VTK export.

**Sprint 3 – Topological analysis & sanity checks (Weeks 5–6)**

* Quantify:

  * size distribution of low-mobility basins,
  * their persistence vs simplification threshold,
  * correlation with demographic/policy covariates.
* Null models:

  * randomising mobility values permuting within state;
  * spatially smoothed noise fields.
* Check that identified basins are not artefacts of tract resolution.

**Sprint 4 – DL models (Weeks 7–8)**

* Build baseline GNN predicting mobility from covariates (education, race, income, etc.).
* Add topological features per tract (e.g., basin ID, basin depth, local Morse index).
* Optionally: add topological regulariser penalising fragmented low-mobility regions.

**Sprint 5 – Visual story + documentation (Weeks 9–10)**

* Use ParaView to:

  * show basins as coloured patches over map,
  * draw gradient flow lines (integral lines of Morse–Smale) as “paths out of poverty”.
* Assemble choropleths + small multiples across states / quantiles.
* Finalise repo docs and write blog / policy note.

---

### 5. Mathematical directions

* **Discrete Morse theory interpretation:**

  * Mobility field `f` over geographic domain; descending manifolds = basins of attraction.
  * Depth of basin ≈ difficulty of escaping poverty trap; persistence quantifies robustness to noise.
* **Comparative topology:**

  * Compare Betti-0/1 of low-mobility regions across states/countries; correlate with macro measures (Gini, policy indices).
* **Sensitivity analysis:**

  * Add noise to `f`, re-run Morse–Smale, measure stability of basin structure.
  * Explore coarsening (aggregation to counties) vs tract-level detail.

This yields meaty content for a methods appendix.

---

### 6. Visualisation strategy

**ParaView / TTK**

* 2.5D surface: x,y = geography; z = mobility; colour by mobility or basin ID.
* TTK Morse–Smale segmentation overlaid on map; low-mobility basins highlighted.
* Animations of:

  * increasing simplification threshold → how basin structure simplifies,
  * morphing between states/regions for comparison.

**Maps / static plots**

* Basemap + choropleths with semi-transparent basin boundaries.
* Scatterplots: basin depth vs average educational spending, or vs racial segregation indices.
* Small multiples grid: one panel per state/region.

---

### 7. Blog / paper directions

* **Blog title idea:**
  *“Topological Poverty Traps: Mapping Economic Mobility with Morse–Smale Complexes”*

* Narrative structure:

  1. Motivation: mobility as a landscape with valleys and ridges.
  2. Data: Opportunity Atlas; how we build the scalar field.
  3. Topological tools: persistence + Morse–Smale (short, visual).
  4. Results: a few striking regions; policy-relevant interpretations.
  5. Limitations + ethical considerations.

* **Paper angle (methodologically focused):**

  * Formalise mobility landscape construction.
  * Define a “Topological Poverty Trap Index” based on basin persistence + depth.
  * Compare with standard inequality metrics; show cases where topology reveals structure Gini/mean income miss.

---

## Coordinating both projects

If you run these in parallel:

* **Common infrastructure:**

  * Shared `tda_utils/` mini-lib (Takens, PH wrappers, VTK exports).
  * Shared experiment harness (logging, config).
  * One `paraview_scripts/` folder (with Claude-written scripts) re-used for both domains.

* **Cross-fertilisation:**

  * Techniques for null models, stability, and PH feature engineering learned in Project 1 will transfer almost directly to Project 2.
  * Visual idioms (landscapes, basins, topological timelines) can be reused.

If you’d like, next step could be to pick **one** of these and I can sketch a concrete 2-week “starting block” with task-level granularity (Git issues), including prompts/templates for Copilot and Claude MCP.
