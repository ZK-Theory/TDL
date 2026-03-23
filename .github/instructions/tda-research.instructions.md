---
applyTo: "**/*.py"
---

# TDA Research Coding Instructions

## Persistence Diagram Conventions

When working with persistence diagrams in this codebase:
- Shape is always `(n_points, 3)` with columns `[dimension, birth, death]` unless using giotto-tda's format `(n_points, 2)` per dimension
- Infinite bars (H0 connected components) have `death = np.inf`; replace before vectorisation: `np.where(np.isinf(dgm), max_val, dgm)`
- Always sort by dimension before processing
- Significant features: `persistence = death - birth > threshold` (expose threshold as parameter)

## Statistical Testing on Topological Features

Permutation null testing is the standard approach:

```python
def permutation_test(
    observed_stat: float,
    null_distribution: NDArray[np.float64],
    alternative: str = "greater",
) -> float:
    """Compute p-value from permutation null distribution.

    Args:
        observed_stat: Test statistic from real data.
        null_distribution: Array of test statistics under null.
        alternative: 'greater', 'less', or 'two-sided'.

    Returns:
        Empirical p-value.
    """
    n = len(null_distribution)
    if alternative == "greater":
        return np.sum(null_distribution >= observed_stat) / n
    elif alternative == "less":
        return np.sum(null_distribution <= observed_stat) / n
    else:
        return np.sum(np.abs(null_distribution) >= np.abs(observed_stat)) / n
```

## GNN Patterns for Topology

When building GNNs that consume persistence diagrams or simplicial data:
- Use `torch_geometric.data.Data` for graph representation
- Persistence-based features as node attributes: `data.x = persistence_features`
- Edge attributes from filtration values: `data.edge_attr = filtration_weights`
- Always handle empty graphs (0 simplices) gracefully

## Spatial Analysis (poverty_tda)

- UK LSOA data uses EPSG:27700 (British National Grid); reproject before distance calculations
- Spatial weights: use Queen contiguity from libpysal (`Queen.from_dataframe(gdf)`)
- Moran's I for spatial autocorrelation; report both statistic and p-value
- Morse-Smale basins correspond to poverty trap regions; basin ID → LSOA membership

## Time Series TDA (financial_tda)

- Takens embedding: optimal delay τ via mutual information; embedding dimension via FNN
- Sliding window: `window_size` and `stride` always exposed as parameters
- Returns vs prices: always work in log-returns for stationarity
- Regime labels: H0 count drops at phase transitions; H1 count rises in turbulent regimes

## Trajectory TDA (trajectory_tda)

- Employment sequences encoded as integer arrays (state space defined in `data/employment_status.py`)
- Point clouds from trajectory embeddings: rows = individuals, cols = topological features
- Age stratification: always report results by cohort (early career, mid career, late career)
- Markov transition matrices: row-stochastic; validate with `np.testing.assert_allclose(M.sum(axis=1), 1.0)`

## Output and Results

- Save computed persistence diagrams to disk (they are expensive); use `shared/persistence.py` I/O utilities
- Results go to `results/<domain>/` or `outputs/<domain>/`; never commit results to git
- Figures go to `figures/<domain>/`; use matplotlib with the project's shared style
- Log experiment parameters using `logging` module; not `print()`
