# Project 1: Financial Market Regime Detection via TDA

## Toolchain Integration

### GitHub Copilot
- **Takens embedding generation**: Copilot excels at boilerplate for sliding window embeddings
- **Feature extraction pipelines**: Autocomplete for giotto-tda/GUDHI API patterns
- **Test scaffolding**: Generate parametrized tests for persistence computation edge cases

### ParaView + Claude MCP
Use the existing MCP integration for:
- **Interactive persistence diagram exploration**: "Show me features that persist across >2 standard deviations of the filtration"
- **Regime comparison**: "Overlay the Rips complex evolution from 2008-09 vs 2020-03"
- **Anomaly highlighting**: "Color-code simplices by their contribution to H1 generators"

### TTK Modules
| Module | Application |
|--------|-------------|
| `PersistenceDiagram` | Core homology computation |
| `BottleneckDistance` | Regime similarity scoring |
| `PersistenceCurve` | Time-windowed feature tracking |
| `MergeTree` | Market structure decomposition |

### Deep Learning Integration
- **Perslay/PersFormer**: Vectorize persistence diagrams → LSTM/Transformer for sequence prediction
- **GNN on Rips complex**: Learn edge weights that optimize regime discrimination
- **Autoencoder on persistence images**: Anomaly detection via reconstruction error

---

## Code Architecture

```
financial_tda/
├── data/
│   ├── fetchers/           # Yahoo Finance, FRED, crypto APIs
│   └── preprocessors/      # Returns, log-returns, volatility
├── topology/
│   ├── embedding.py        # Takens embedding with optimal τ, d selection
│   ├── filtration.py       # Rips, Alpha, custom market filtrations
│   └── features.py         # Persistence landscapes, images, statistics
├── models/
│   ├── regime_classifier.py
│   └── change_point_detector.py
├── viz/
│   ├── paraview_scripts/   # Python scripts for TTK pipelines
│   └── streamlit_app.py
└── tests/
```

### Key Code Snippets

**Optimal Takens Embedding** (use Copilot for mutual information calculation):
```python
def takens_embed(series: np.ndarray, tau: int, dim: int) -> np.ndarray:
    """Delay embedding with mutual-information-optimal τ."""
    n = len(series) - (dim - 1) * tau
    return np.array([series[i:i + dim * tau:tau] for i in range(n)])

def optimal_tau(series: np.ndarray, max_lag: int = 50) -> int:
    """First minimum of mutual information."""
    # Copilot: implement using sklearn.feature_selection.mutual_info_regression
    ...
```

**Persistence Feature Extraction**:
```python
from gtda.homology import VietorisRipsPersistence
from gtda.diagrams import PersistenceEntropy, Amplitude

def extract_tda_features(point_cloud: np.ndarray) -> dict:
    vr = VietorisRipsPersistence(homology_dimensions=[0, 1, 2])
    dgm = vr.fit_transform([point_cloud])[0]
    
    return {
        'entropy_h0': PersistenceEntropy().fit_transform([dgm])[0, 0],
        'entropy_h1': PersistenceEntropy().fit_transform([dgm])[0, 1],
        'amplitude': Amplitude(metric='wasserstein').fit_transform([dgm])[0],
        'betti_curve': compute_betti_curve(dgm),  # custom
    }
```

**TTK ParaView Pipeline** (for MCP interaction):
```python
# paraview_scripts/regime_compare.py
from paraview.simple import *
import ttkmodule

def compare_regimes(data_2008, data_2020):
    """Generate side-by-side Rips complex evolution."""
    for data, label in [(data_2008, '2008'), (data_2020, '2020')]:
        rips = TTKRipsComplex(Input=data)
        rips.MaximumDimension = 2
        pd = TTKPersistenceDiagram(Input=rips)
        # MCP prompt: "Annotate the three longest-lived H1 features"
```

---

## Sprint Plan (8 weeks)

### Sprint 1 (Week 1-2): Foundation
- [ ] Set up repo with Poetry/uv, pre-commit, CI
- [ ] Implement data fetchers (Yahoo Finance, FRED)
- [ ] Takens embedding with optimal parameter selection
- [ ] Replicate one result from Gidea & Katz (2018)
- **Deliverable**: Verified reproduction of published result

### Sprint 2 (Week 3-4): Feature Engineering
- [ ] Implement persistence landscapes, images, Betti curves
- [ ] Sliding window analysis over historical data
- [ ] Feature stability analysis across different filtrations
- [ ] TTK integration for advanced visualizations
- **Deliverable**: Feature extraction pipeline with tests

### Sprint 3 (Week 5-6): Detection System
- [ ] Train regime classifier (crisis vs. normal)
- [ ] Implement change-point detection using bottleneck distance
- [ ] Backtest on 2008, 2015 (China), 2020, 2022 events
- [ ] Calibrate warning thresholds
- **Deliverable**: Validated detection system with precision/recall metrics

### Sprint 4 (Week 7-8): Interface & Documentation
- [ ] Streamlit dashboard for real-time monitoring
- [ ] ParaView state files for key visualizations
- [ ] Blog post with methodology explanation
- [ ] API for programmatic access
- **Deliverable**: Deployable system with documentation

---

## Mathematical Insights

### Key Theoretical Points
1. **Takens' Theorem**: For generic diffeomorphisms, delay embedding with $d > 2 \cdot \text{dim}(M)$ reconstructs attractor topology
2. **Stability Theorem**: Bottleneck distance between persistence diagrams is Lipschitz-continuous w.r.t. Hausdorff distance on point clouds
3. **Persistent Entropy**: $E = -\sum_i p_i \log p_i$ where $p_i = \frac{d_i - b_i}{\sum_j (d_j - b_j)}$ measures complexity of diagram

### Research Directions
- **Multi-scale analysis**: Use wavelet decomposition before embedding to separate time scales
- **Cross-correlation topology**: Build simplicial complex from correlation matrix, track H1 (cycles = correlated clusters)
- **Information-theoretic filtration**: Use transfer entropy as edge weights

### Useful Inequalities
- $d_B(D_1, D_2) \leq d_H(X_1, X_2)$ (bottleneck stability)
- For Rips with max radius $r$: $\text{rank}(H_k) \leq \binom{n}{k+1}$

---

## Visualization Ideas

1. **Regime Phase Space**: 3D scatter of (entropy_H0, entropy_H1, amplitude) colored by date, animated through time
2. **Persistence Barcode Timeline**: Horizontal timeline with barcode at each window, crisis periods highlighted
3. **Topological Early Warning Dashboard**:
   - Live Betti curves
   - Bottleneck distance from "normal" reference state
   - Alert thresholds with confidence intervals
4. **Comparative Rips Evolution**: Side-by-side animation of Rips complex growth during 2008 vs 2020

---

## Blog/Paper Ideas

### Blog Posts
1. **"What Shape is a Market Crash?"** - Visual introduction to TDA on financial time series
2. **"Building a Topological Early Warning System"** - Technical tutorial with code
3. **"Why Topology Beats Statistics for Regime Detection"** - Comparative analysis

### Paper Targets
1. **Applied journal** (Quantitative Finance, SSRN preprint): Focus on empirical performance, practitioner audience
2. **ML venue** (NeurIPS workshop, ICML workshop): Deep learning + TDA angle, novel architecture for persistence diagrams
3. **Arxiv/blog first**: Build visibility, then submit refined version

### Key Claims to Support
- TDA features provide X days earlier warning than volatility-based indicators
- Topological signatures of different crisis types are distinguishable
- Method generalizes across asset classes
