# TTK Distance Metrics for Persistence Diagrams

Comprehensive guide to persistence diagram distance metrics used in financial and poverty TDA analysis.

## Overview

Distance metrics quantify dissimilarity between persistence diagrams, enabling:
- **Regime classification** (financial markets)
- **Anomaly detection** (crisis identification)
- **Trap comparison** (poverty landscape similarity)
- **Time series clustering** (regime grouping)

## Mathematical Foundations

### Persistence Diagrams

A persistence diagram is a multiset of points in the extended plane:
```
D = {(b_i, d_i, dim_i) | i = 1, ..., n}
```

Where:
- `b_i` = birth time (scale at which feature appears)
- `d_i` = death time (scale at which feature disappears)
- `dim_i` = homology dimension (0, 1, or 2)
- `p_i = d_i - b_i` = persistence (feature lifetime)

**Convention:** All points lie above the diagonal (`d_i ≥ b_i`). The diagonal represents features with zero persistence (noise).

### Distance Metrics

Two main distance metrics are used:

1. **Bottleneck Distance** (`d_B`)
2. **Wasserstein Distance** (`d_W`)

Both are based on optimal matchings between diagrams.

## Bottleneck Distance

### Definition

The bottleneck distance between diagrams `D1` and `D2` is:

```
d_B(D1, D2) = inf_γ sup_{x ∈ D1} ||x - γ(x)||_∞
```

Where:
- `γ` ranges over all bijections (matchings) between `D1 ∪ Δ` and `D2 ∪ Δ`
- `Δ` is the diagonal (dummy points for unmatched features)
- `||·||_∞` is the infinity norm: `||(_b1, d1) - (b2, d2)||_∞ = max(|b1 - b2|, |d1 - d2|)`

**Intuition:** The bottleneck distance is the cost of the worst-matched pair of features.

### Properties

**Stability:**
- Stable with respect to input perturbations (Lipschitz continuous)
- Small changes in input → small changes in distance

**Robustness:**
- Focuses on most significant features
- Ignores small noise features (matched to diagonal)
- Single outlier can dominate distance

**Computational Complexity:**
- O(n^2.5 log n) using auction algorithm
- Fast for small-to-medium diagrams (<1000 points)

### Interpretation

**Small Bottleneck Distance (< 0.05):**
- Similar topological structure
- Few significant feature differences
- Same regime/landscape type

**Medium Bottleneck Distance (0.05 - 0.15):**
- Moderate structural differences
- Some key features differ
- Related but distinct regimes

**Large Bottleneck Distance (> 0.15):**
- Fundamentally different topology
- Major feature disparities
- Different regime classes

### Use Cases

**Financial Markets:**
- Crisis vs normal regime classification
- Anomaly detection in time series
- Regime shift identification

**Poverty Landscapes:**
- Trap type classification
- Basin similarity comparison
- Intervention impact assessment

## Wasserstein Distance

### Definition

The p-Wasserstein distance between diagrams `D1` and `D2` is:

```
d_W^p(D1, D2) = (inf_γ Σ_{x ∈ D1} ||x - γ(x)||_∞^p)^(1/p)
```

Commonly used: **p=1** (1-Wasserstein) and **p=2** (2-Wasserstein).

**Intuition:** The Wasserstein distance is the total transport cost to optimally match all features.

### Properties

**Sensitivity:**
- Sensitive to all features (not just worst match)
- Captures overall distribution differences
- Less robust to outliers than bottleneck

**Smoothness:**
- Smoother metric than bottleneck
- Better for statistical analysis
- Gradients exist (useful for optimization)

**Computational Complexity:**
- O(n^3) using Hungarian algorithm
- Can be approximated for large diagrams

### Interpretation

**Small Wasserstein Distance (< 0.03):**
- Very similar feature distributions
- Comparable topology across all scales
- Nearly identical regimes

**Medium Wasserstein Distance (0.03 - 0.10):**
- Moderate distribution differences
- Some scale-dependent variations
- Related regime types

**Large Wasserstein Distance (> 0.10):**
- Distinct feature distributions
- Different topology at multiple scales
- Separate regime categories

### Use Cases

**Financial Markets:**
- Gradual regime transition detection
- Market volatility comparison
- Risk similarity scoring

**Poverty Landscapes:**
- Smooth landscape evolution tracking
- Multi-scale trap comparison
- Counterfactual scenario analysis

## Comparison: Bottleneck vs Wasserstein

| Aspect | Bottleneck | Wasserstein |
|--------|-----------|-------------|
| **Focus** | Worst match | All matches |
| **Robustness** | Outlier-robust | Outlier-sensitive |
| **Sensitivity** | Major features | All features |
| **Computation** | Faster | Slower |
| **Smoothness** | Non-smooth | Smooth |
| **Use Case** | Classification | Regression |

**Rule of Thumb:**
- Use **Bottleneck** for regime classification and anomaly detection
- Use **Wasserstein** for similarity scoring and statistical analysis

## Implementation in TDL

### Financial TDA

Located in `financial_tda/topology/filtration.py`:

```python
from financial_tda.topology import (
    compute_bottleneck_distance,
    compute_wasserstein_distance
)

# Compute distances
bn_dist = compute_bottleneck_distance(
    diag1, diag2,
    dimension=1  # Compare H1 features only
)

ws_dist = compute_wasserstein_distance(
    diag1, diag2,
    dimension=1,
    p=2  # 2-Wasserstein
)
```

**Backend:** Uses `persim` library (stable, well-tested)

### Visualization

```python
from financial_tda.viz.ttk_plots import plot_bottleneck_distance_matrix

# Visualize pairwise distances
fig = plot_bottleneck_distance_matrix(
    diagrams=[d1, d2, d3, d4],
    labels=['Crisis 2008', 'Normal 2007', 'Crisis 2020', 'Normal 2019'],
    dimension=1,
    metric='bottleneck',
    add_dendrogram=True  # Hierarchical clustering
)
```

## Practical Guidelines

### Choosing the Right Metric

**Use Bottleneck When:**
- Focusing on most significant features
- Classifying regime types
- Detecting anomalies or outliers
- Need computational efficiency
- Dealing with noisy data

**Use Wasserstein When:**
- Interested in overall distribution
- Performing statistical tests
- Tracking smooth transitions
- Need differentiable metric
- Comparing similar regimes

### Threshold Selection

**Bottleneck Distance Thresholds:**
- **< 0.05**: Same regime/trap type
- **0.05 - 0.10**: Similar regimes
- **0.10 - 0.20**: Related regimes
- **> 0.20**: Different regimes

**Wasserstein Distance Thresholds (p=2):**
- **< 0.03**: Nearly identical
- **0.03 - 0.07**: Comparable
- **0.07 - 0.15**: Moderately different
- **> 0.15**: Distinct

*Note: Thresholds depend on data normalization and scale. Always validate with domain knowledge.*

### Dimension Filtering

Distances can be computed for specific homology dimensions:

```python
# H0: Connected components (financial: regime stability)
bn_h0 = compute_bottleneck_distance(d1, d2, dimension=0)

# H1: Loops (financial: cyclical patterns, poverty: transition zones)
bn_h1 = compute_bottleneck_distance(d1, d2, dimension=1)

# H2: Voids (rare in 2D/3D embeddings)
bn_h2 = compute_bottleneck_distance(d1, d2, dimension=2)

# All dimensions combined
bn_all = compute_bottleneck_distance(d1, d2, dimension=None)
```

**Recommendation:** Start with dimension-specific distances for interpretability, then consider combined distance if needed.

## Advanced Topics

### Persistence Landscapes

An alternative representation enabling statistical analysis:

```python
# Not yet implemented - future extension
from shared.ttk_visualization import compute_persistence_landscape

landscape1 = compute_persistence_landscape(diag1, resolution=100)
landscape2 = compute_persistence_landscape(diag2, resolution=100)

# L^p norm distance
lp_dist = np.linalg.norm(landscape1 - landscape2, ord=2)
```

### Kernel Methods

Persistence diagrams can be embedded in Hilbert space:

```python
# Future extension - requires kernel implementation
from gtda.diagrams import PersistenceImage

pi = PersistenceImage(sigma=0.1, n_bins=50)
pi1 = pi.fit_transform([diag1])
pi2 = pi.fit_transform([diag2])

# Euclidean distance in image space
img_dist = np.linalg.norm(pi1 - pi2)
```

### Statistical Testing

Test significance of distance differences:

```python
# Permutation test (future extension)
from scipy.stats import permutation_test

def distance_stat(x, y):
    return compute_bottleneck_distance(x, y, dimension=1)

result = permutation_test(
    (crisis_diagrams, normal_diagrams),
    distance_stat,
    n_resamples=1000
)

print(f"p-value: {result.pvalue}")
```

## Performance Optimization

### Bottleneck Distance

**For Large Diagrams (>1000 points):**
- Use approximation algorithms (not yet implemented)
- Sample diagrams before comparison
- Parallelize pairwise distance computation

**Optimization:**
```python
from joblib import Parallel, delayed

def compute_distance_pair(i, j):
    return compute_bottleneck_distance(diagrams[i], diagrams[j])

# Parallel computation
distances = Parallel(n_jobs=-1)(
    delayed(compute_distance_pair)(i, j)
    for i in range(n)
    for j in range(i+1, n)
)
```

### Wasserstein Distance

**For Very Large Diagrams:**
- Use Sinkhorn approximation (entropy-regularized optimal transport)
- Subsample features by persistence threshold
- Cache distance matrix for repeated use

## References

### Academic Papers

**Bottleneck Distance:**
- Cohen-Steiner, D., Edelsbrunner, H., & Harer, J. (2007). "Stability of persistence diagrams." *Discrete & Computational Geometry*, 37(1), 103-120.

**Wasserstein Distance:**
- Turner, K., Mileyko, Y., Mukherjee, S., & Harer, J. (2014). "Fréchet means for distributions of persistence diagrams." *Discrete & Computational Geometry*, 52(1), 44-70.

**Computational Methods:**
- Kerber, M., Morozov, D., & Nigmetov, A. (2017). "Geometry helps to compare persistence diagrams." *Journal of Experimental Algorithmics*, 22, 1-4.

### Software Libraries

**persim** (used in TDL):
- Documentation: https://persim.scikit-tda.org/
- Stable bottleneck and Wasserstein implementations
- Well-tested, widely used

**TTK** (alternative, not used for distances):
- Provides `ttkBottleneckDistance` and `ttkPersistenceMatching` filters
- Requires subprocess isolation in TDL
- More complex setup for same results

**gudhi** (alternative):
- Python bindings: https://gudhi.inria.fr/python/latest/
- Comprehensive TDA toolkit
- Not used in TDL to minimize dependencies

## Examples

### Financial Regime Classification

```python
from financial_tda.topology import compute_persistence_vr, compute_bottleneck_distance
from financial_tda.topology.embedding import takens_embedding

# Embed time series
crisis_emb = takens_embedding(crisis_returns, delay=5, dimension=3)
normal_emb = takens_embedding(normal_returns, delay=5, dimension=3)

# Compute persistence
crisis_diag = compute_persistence_vr(crisis_emb)
normal_diag = compute_persistence_vr(normal_emb)

# Distance
dist = compute_bottleneck_distance(crisis_diag, normal_diag, dimension=1)

if dist > 0.10:
    print("Different regime detected!")
else:
    print("Similar topological structure")
```

### Poverty Trap Comparison

```python
from poverty_tda.topology import compute_morse_smale
from financial_tda.topology import compute_bottleneck_distance

# Compute Morse-Smale for two regions
result1 = compute_morse_smale('region1_mobility.vti', persistence_threshold=0.05)
result2 = compute_morse_smale('region2_mobility.vti', persistence_threshold=0.05)

# Extract minima (traps) as persistence diagrams
traps1 = [(cp.value, cp.value + cp.persistence, 0) 
          for cp in result1.critical_points if cp.is_minimum]
traps2 = [(cp.value, cp.value + cp.persistence, 0)
          for cp in result2.critical_points if cp.is_minimum]

# Compare trap distributions
trap_dist = compute_wasserstein_distance(
    np.array(traps1), np.array(traps2), dimension=0, p=2
)

print(f"Trap similarity: {1 / (1 + trap_dist):.2%}")
```

## Troubleshooting

### Common Issues

**Issue:** Distance always zero
- **Cause:** Empty diagrams or dimension mismatch
- **Solution:** Check diagram has features for specified dimension

**Issue:** Distance extremely large
- **Cause:** Different scale/normalization
- **Solution:** Normalize diagrams to [0, 1] range before comparison

**Issue:** Slow computation
- **Cause:** Very large diagrams (>5000 points)
- **Solution:** Filter by persistence threshold or subsample

### Validation Checks

```python
# Check diagram validity
assert len(diagram) > 0, "Empty diagram"
assert np.all(diagram[:, 1] >= diagram[:, 0]), "Death < Birth"

# Check dimension range
valid_dims = diagram[:, 2].astype(int)
assert np.all((valid_dims >= 0) & (valid_dims <= 2)), "Invalid dimension"

# Normalize if needed
max_val = np.max(diagram[:, :2])
diagram_norm = diagram.copy()
diagram_norm[:, :2] /= max_val
```

## Future Work

- **GPU acceleration** for large-scale distance matrix computation
- **Parallel bottleneck** algorithm implementation
- **Persistence landscape** distance metrics
- **Statistical testing** framework for distance significance
- **Interactive exploration** tools for distance matrices

## License

Documentation: MIT License
Implementation: See project LICENSE file
