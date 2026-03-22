# GitHub Copilot Instructions — TDL

## Project Domain

This is a **Topological Data Analysis (TDA) research platform** for social science. It applies persistent homology, Morse-Smale analysis, and geometric/topological deep learning to:
- Financial market regime detection (equities, crypto, macroeconomic indicators)
- UK poverty trap identification (LSOA-level socioeconomic mobility)
- Career trajectory analysis (BHPS/UKHLS employment and income sequences)

## Language and Runtime

- **Python 3.11** exclusively
- Package manager: `uv`
- Linter/formatter: `ruff` (88-char lines, rules E/F/I/W)
- Testing: `pytest` with markers `slow`, `integration`, `validation`

## Code Style Expectations

Always produce code that:
- Uses **Google-style docstrings** on all public functions and classes
- Has **type hints** on all function signatures; use `numpy.typing.NDArray[np.float64]` not bare `np.ndarray`
- Imports are ordered: stdlib → third-party → local (isort-compatible)
- Follows 88-character line length
- Uses `pathlib.Path` for all file paths (never `os.path`)

```python
from numpy.typing import NDArray
import numpy as np

def compute_betti_numbers(diagram: NDArray[np.float64], threshold: float = 0.1) -> dict[int, int]:
    """Count Betti numbers from a persistence diagram.

    Args:
        diagram: Array of shape (n, 3) with columns [dimension, birth, death].
        threshold: Minimum persistence (death - birth) to count as significant.

    Returns:
        Dict mapping homology dimension to Betti number.
    """
```

## Key Libraries and Their Usage

| Library | Purpose | Import |
|---------|---------|--------|
| `giotto-tda` | Rips filtrations, persistence, vectorisation | `from gtda.homology import VietorisRipsPersistence` |
| `gudhi` | Low-level TDA, Mapper, simplex trees | `import gudhi` |
| `ripser` | Fast Vietoris-Rips | `from ripser import ripser` |
| `torch-geometric` | GNNs on graphs/manifolds | `import torch_geometric` |
| `geopandas` | Spatial data (UK LSOAs) | `import geopandas as gpd` |
| `libpysal` | Spatial weights/lags | `import libpysal` |

## TDA Conventions

- Persistence thresholds: always expose as parameters, never hardcode
- Permutation nulls: standard for significance testing on topological features; default n_permutations=1000
- Bootstrap resampling: n=1000, report 95% CI
- FDR correction: Benjamini-Hochberg for multiple comparisons
- Infinity bars: replace `np.inf` deaths with `max_filtration * 1.1` before vectorisation
- Dimension naming: H0 = connected components, H1 = loops, H2 = voids

## Architecture Pattern

Each domain package (`financial_tda`, `poverty_tda`, `trajectory_tda`) follows:
```
data/       → fetchers and preprocessors
topology/   → TDA computations (filtrations, diagrams, features)
models/     → ML/DL models (GNNs, VAEs, classifiers)
analysis/   → domain analysis modules
validation/ → correctness and robustness checks
viz/        → plotting and dashboards
```

Shared utilities are in `shared/` (persistence I/O, plotting helpers, TTK integration).

## Deep Learning Context

- GNN models use `torch-geometric`; spatial graphs (poverty_tda), persistence graphs (financial_tda)
- Persistence-based DL: aim to integrate Perslay/PersFormer patterns
- Topological DL expansion planned: simplicial complexes, cellular complexes via `TopoModelX`
- All DL models should be device-agnostic (`device = torch.device("cuda" if torch.cuda.is_available() else "cpu")`)

## Testing Guidance

- Integration tests must not mock external data — skip with `@pytest.mark.integration` if data unavailable
- Validation tests check against known published results (cite the paper in the docstring)
- Use `@pytest.mark.slow` for tests running >30s

## What to Avoid

- Wildcard imports (`from x import *`)
- `os.path` (use `pathlib.Path`)
- Bare `np.ndarray` in type hints (use `NDArray`)
- Hardcoded file paths
- `torch-geometric` unconditional imports (it's an optional dep; guard with try/except)
