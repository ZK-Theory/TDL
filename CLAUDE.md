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
papers/                  ← ALL paper projects (see Papers Structure below)
financial_tda/    poverty_tda/    trajectory_tda/
├── data/         ├── data/        ├── data/
├── topology/     ├── topology/    ├── topology/
├── models/       ├── models/      ├── analysis/
├── analysis/     ├── analysis/    ├── scripts/
├── validation/   ├── validation/  ├── viz/
└── viz/          └── viz/
shared/           tests/           .apm/
docs/plans/strategy/     ← Meta-Research-Plan, Obsidian-Overview
```

`shared/` contains cross-domain utilities: persistence diagram I/O, common validation patterns, TTK/ParaView integration.

## Papers Structure

All paper projects live in `papers/`, **not** in domain subdirectories. The domain directories hold code only.

### Directory layout for each paper

```
papers/PXX-Name/
├── _project.md          ← YAML metadata (status, journal, deadline) — source of truth
├── _outline.md          ← Current argument structure
├── _reviewer-log.md     ← Reviewer comments and response tracking
├── drafts/
│   ├── vN-YYYY-MM.md   ← Versioned full drafts (v1-2025.md, v5-2026-03.md, …)
│   └── sections/        ← Section-level working files (optional)
├── figures/             ← Exported PD diagrams, Mapper graphs, barcodes
└── notes/               ← Scratch: outlines, action plans, handoff notes
```

### `_project.md` YAML schema (mandatory fields)

```yaml
---
paper: P01                    # paper identifier (P01–P10, FIN-01, etc.)
title: "Full paper title"
status: in-progress           # idea | in-progress | submitted | under-review | published
target-journal: "Name"
submitted: null               # ISO date or null
deadline: 2026-06-01          # target submission date or null
priority: high                # high | medium | low
stage: 0                      # 0=consolidate | 1=near | 2=medium | 3=deep-learning
domain: trajectory_tda        # trajectory_tda | poverty_tda | financial_tda
data: [USoc, BHPS]
tags: [paper, tda, ...]
---
```

### Programme papers

| ID | Title | Status | Stage |
|---|---|---|---|
| P01 | VR PH of UK Trajectories | in-progress | 0 |
| P02 | Mapper for Interior Structure | in-progress | 1 |
| P03 | Zigzag + Business Cycle Topology | in-progress | 1 |
| P04 | Multi-Parameter PH, Poverty Traps | idea | 2 |
| P05 | Cross-National Welfare State Topology | idea | 2 |
| P06 | Intergenerational Topological Inheritance | idea | 2 |
| P07 | Geometric Trajectory Forecasting | idea | 3 |
| P08 | GNNs on Household Graphs | idea | 3 |
| P09 | CCNNs for Multi-Level Social Data | idea | 3 |
| P10 | Topological Fairness | idea | 3 |
| FIN-01 | Market Regime Detection (financial) | in-progress | — |

### Draft naming convention

`vN-YYYY-MM.md` — e.g., `v5-2026-03.md` for the fifth draft written in March 2026.

### Rules for agents working on papers

1. **Always** open `papers/PXX/_project.md` first to read current status and open items.
2. **Always** update `_project.md` status and open items after making changes.
3. New drafts go in `papers/PXX/drafts/` with version prefix — never overwrite a previous draft.
4. Computational results go in `results/` (domain-specific) — not in the papers/ directory.
5. Figures are placeholders in text `[Figure N]` until final production pass.
6. After completing a draft, run the `/humanizer` command to check for AI writing tells before marking the paper `submitted`.

See `papers/README.md` for full structure documentation.

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

### Start work on a paper
1. Check `papers/PXX/_project.md` — read status, open items, and current draft path.
2. Read the current draft in `papers/PXX/drafts/vN-YYYY-MM.md`.
3. Run any required computation in the domain directory; save results to `results/`.
4. Write or update the draft as `papers/PXX/drafts/vN+1-YYYY-MM.md`.
5. Update `_project.md` open items and status.
6. Run `/humanizer` before marking a draft ready for submission review.
7. Branch naming: `paper/pXX-name` for paper writing; `run/pXX-name` for computation.

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
