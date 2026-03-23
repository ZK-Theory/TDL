# CLAUDE.md — TDL (Topological Data Lab)

## Project Purpose

Research platform applying **Topological Data Analysis (TDA)**, **topological deep learning**, and **geometric deep learning** to social science datasets. Produces novel insights for academic research papers. Primary domains:

- **financial_tda** — Market regime detection and crisis identification via persistent homology on time series
- **poverty_tda** — UK poverty trap detection via Morse-Smale complex analysis on socioeconomic mobility landscapes
- **trajectory_tda** — Employment/income career trajectory analysis via persistent homology on BHPS/UKHLS panel data

## Key Concepts (Domain Knowledge)

**TDA fundamentals used here:**
- Persistent homology: tracks topological features (connected components H0, loops H1, voids H2) across filtration scales
- Persistence diagrams / barcodes: birth-death pairs; points far from diagonal = significant features
- Wasserstein/bottleneck distance: metrics between persistence diagrams
- Mapper: graph-based topological summary via cover + clustering
- Morse-Smale complex: decomposes a function's domain into ascending/descending manifolds; basins = stable regions (poverty traps)

**Key libraries:**
- `giotto-tda`: Rips/Alpha filtrations, persistence diagrams, vectorisation (landscape, image, silhouette)
- `gudhi`: Lower-level TDA; simplex trees, cubical complexes, Mapper
- `ripser`: Fast Vietoris-Rips computation
- `torch-geometric`: GNNs on graph-structured data (spatial mobility graphs, persistence graphs)
- `geopandas` / `libpysal`: Spatial analysis on UK LSOAs

**Topology conventions in this codebase:**
- Persistence thresholds are tuned per domain (financial: shorter windows; poverty: geographic scale)
- Permutation nulls are the standard for hypothesis testing on persistence features
- Bootstrap resampling (n=1000) for confidence intervals on topological summaries
- FDR correction (Benjamini-Hochberg) for multiple comparisons

## Architecture

```
financial_tda/    poverty_tda/    trajectory_tda/
├── data/         ├── data/        ├── data/
├── topology/     ├── topology/    ├── topology/
├── models/       ├── models/      ├── analysis/
├── analysis/     ├── analysis/    ├── scripts/
├── validation/   ├── validation/  ├── viz/
└── viz/          └── viz/         └── paper/
shared/           tests/           .apm/
```

`shared/` contains cross-domain utilities: persistence diagram I/O, common validation patterns, TTK/ParaView integration.

## Code Conventions

- **Python 3.11**, 88-char line length, Ruff rules E/F/I/W
- **Type hints** mandatory on all public APIs; use `numpy.typing.NDArray` not bare `np.ndarray`
- **Docstrings**: Google-style on all public functions/classes
- **Imports**: standard → third-party → local; no wildcard imports
- **Pre-commit**: ruff linting/formatting runs on every commit; don't skip hooks

```python
# Correct pattern for typed numpy arrays
from numpy.typing import NDArray
import numpy as np

def compute_persistence(point_cloud: NDArray[np.float64], max_dim: int = 2) -> list[tuple]:
    """Compute persistent homology of a point cloud.

    Args:
        point_cloud: Shape (n_points, n_dims) array.
        max_dim: Maximum homology dimension to compute.

    Returns:
        List of (dimension, (birth, death)) persistence pairs.
    """
```

## Common Workflows

### Run the test suite
```bash
uv run pytest                           # all tests
uv run pytest -m "not slow"            # skip slow tests
uv run pytest tests/financial_tda/     # domain-specific
uv run pytest -m validation            # validation tests only
```

### Lint and format
```bash
uv run ruff check .                    # lint
uv run ruff format .                   # format
uv run ruff check --fix .              # auto-fix lint issues
```

### Add a new experiment
Follow the pattern in existing `experiments/` or `scripts/` subdirectories:
1. Data loading via domain `data/` modules
2. Topology computation via domain `topology/` modules
3. Analysis in domain `analysis/` modules
4. Output to `results/` or `outputs/` (domain-specific)

### Run a full pipeline
Each domain has scripts that chain data → topology → analysis:
- `trajectory_tda/scripts/bhps_pipeline.py` — full BHPS trajectory pipeline
- `financial_tda/experiments/` — multi-asset regime experiments
- `poverty_tda/validation/` — comparison runners

## Testing Conventions

- Test markers: `slow` (long-running), `integration` (external deps/data), `validation` (mathematical correctness)
- Tests live in `tests/<domain>/`
- Validation tests check against known published results (e.g., Gidea-Katz 2017 for financial TDA)
- Permutation null distributions require `--run-slow` or `-m slow` to run fully

## APM Workflow

This project uses APM (Agentic Project Management) v0.5.3. Phase plans live in `.apm/Implementation_Plan.md`. When implementing new phases:
- Check the plan before starting work
- Use the prompts in `.github/prompts/` to initiate manager/implementation agents
- Log progress in `.apm/Memory/`

## Deep Learning Integration Points

- GNNs: `torch-geometric`; spatial graphs in `poverty_tda/models/spatial_gnn.py`, persistence graphs in `financial_tda/models/rips_gnn.py`
- VAEs: `poverty_tda/models/opportunity_vae.py`
- Persistence-based DL: Perslay/PersFormer patterns for learning on persistence diagrams (partially implemented)
- TTK/ParaView: acceleration for large-scale topology; see `shared/ttk_utils.py`

## What NOT to Do

- Do not mock external data sources in integration tests — use real cached data or skip with `@pytest.mark.integration`
- Do not hardcode file paths; use `pathlib.Path` relative to the package root or a config
- Do not run `torch-geometric` imports without checking they are installed (optional dependency)
- Do not commit large data files; data lives outside the repo or in `.gitignore`d `data/` directories
- Do not skip pre-commit hooks (`--no-verify`)
- Do not amend published commits; create new commits instead

## Geometric / Topological Deep Learning (Emerging)

As the project expands into topological and geometric deep learning, the intended structure is:
- Domain-agnostic DL layers → `shared/deep_learning/` (e.g., persistence-based layers, simplicial convolutions)
- Domain-specific DL models → `<domain>/models/` (as now)
- Experiment scaffolds → `<domain>/experiments/` or `<domain>/scripts/`

Key frameworks to integrate: `torch-geometric`, `TopoModelX` (simplicial/cellular/hypergraph NNs), `Perslay`.
