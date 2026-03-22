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
| `gudhi` | Low-level TDA, Mapper, simplex trees, zigzag, Wasserstein distances | `import gudhi` |
| `ripser` | Fast Vietoris-Rips | `from ripser import ripser` |
| `kmapper` | Mapper algorithm for interior trajectory structure (Paper 2) | `import kmapper as km` |
| `multipers` | Multi-parameter persistent homology, PyTorch-autodiff (Paper 4) | `import multipers` |
| `torch-geometric` | GNNs on graphs/manifolds (Papers 7, 8) | `import torch_geometric` |
| `TopoModelX` | Simplicial/cellular/combinatorial complex NNs (Paper 9) | `import topomodelx` |
| `geopandas` | Spatial data (UK LSOAs) | `import geopandas as gpd` |
| `libpysal` | Spatial weights/lags | `import libpysal` |

**Import guards:** `torch-geometric` and `TopoModelX` are optional deps. Always guard:
```python
try:
    from torch_geometric.data import Data
    HAS_TORCH_GEOMETRIC = True
except ImportError:
    HAS_TORCH_GEOMETRIC = False
```

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


## vexp context tools <!-- vexp v1.2.30 -->

**MANDATORY: use `run_pipeline` — do NOT grep, glob, or read files manually.**
vexp returns pre-indexed, graph-ranked context in a single call.

### Workflow
1. `run_pipeline` with your task description — ALWAYS FIRST (replaces all other tools)
2. Make targeted changes based on the context returned
3. `run_pipeline` again only if you need more context

### Available MCP tools
- `run_pipeline` — **PRIMARY TOOL**. Runs capsule + impact + memory in 1 call.
  Auto-detects intent. Includes file content. Example: `run_pipeline({ "task": "fix auth bug" })`
- `get_context_capsule` — lightweight, for simple questions only
- `get_impact_graph` — impact analysis of a specific symbol
- `search_logic_flow` — execution paths between functions
- `get_skeleton` — compact file structure
- `index_status` — indexing status
- `get_session_context` — recall observations from sessions
- `search_memory` — cross-session search
- `save_observation` — persist insights (prefer run_pipeline's observation param)

### Agentic search
- Do NOT use built-in file search, grep, or codebase indexing — always call `run_pipeline` first
- If you spawn sub-agents or background tasks, pass them the context from `run_pipeline`
  rather than letting them search the codebase independently

### Smart Features
Intent auto-detection, hybrid ranking, session memory, auto-expanding budget.

### Multi-Repo
`run_pipeline` auto-queries all indexed repos. Use `repos: ["alias"]` to scope. Run `index_status` to see aliases.
<!-- /vexp -->

---

## 10-Paper Research Programme

This is a PhD/postdoc-scale programme running ~48 months. Before scaffolding new code, check which stage it belongs to. **Do not build Stage 2/3 infrastructure until Stage 0 is complete.**

### Current priority (Stage 0)
Upgrade Paper 1 test statistic from total persistence (scalar) to diagram-level Wasserstein distance using `gudhi`/`hera`. File: `trajectory_tda/validation/wasserstein_null_tests.py`. CPU-only, minutes of runtime.

### Stage 0 — Paper 1 (months 0–3)
- **What:** Markov memory ladder + Wasserstein null tests on BHPS/USoc trajectory topology
- **Key upgrade:** `gudhi.wasserstein.wasserstein_distance()` replacing total-persistence scalar
- **Target:** Sociological Methodology
- **Status:** Draft complete; needs Wasserstein upgrade before submission

### Stage 1 — Papers 2 & 3 (months 3–12, parallel)
- **Paper 2 — Mapper:** `kmapper` on existing PCA-20D embedding; colour nodes by escape probability. File: `trajectory_tda/topology/mapper.py`. CPU-only, minutes.
- **Paper 3 — Zigzag persistence:** Annual cohort snapshots 1991–2023; frozen PCA loadings; `gudhi` zigzag (Kerber-Schreiber streaming). File: `trajectory_tda/topology/zigzag.py`. Hours, local i7/32GB.

### Stage 2 — Papers 4–6 (months 12–24)
- **Paper 4 — Multi-parameter PH:** `multipers` bifiltration (distance + income); development local, full-scale A100 (~4–8 GPU-hrs). `trajectory_tda/topology/multipers_bifiltration.py`
- **Paper 5 — Cross-national:** Same pipeline on SOEP/PSID/CNEF; start data access requests at month 12. Highest sociological impact paper.
- **Paper 6 — Intergenerational:** BHPS-USoc household IDs for parent-child linkage; Wasserstein between regime-conditional child diagrams.

### Stage 3 — Papers 7–10 (months 24–48)
- **Paper 7 — Geometric forecasting:** 9-state graph + GRU/GNN on PyTorch Geometric; topological counterfactuals. `trajectory_tda/models/geometric_forecaster.py`. RTX 3080, hours.
- **Paper 8 — Household GNNs:** Individual nodes + household/neighbourhood edges; GNN representations → TDA pipeline. `shared/deep_learning/graph_utils.add_household_edges()`
- **Paper 9 — CCNNs / cell complexes:** `TopoModelX`; individual→household→neighbourhood→LA. 2-level local; 3–4 level needs A100 (20–40 GPU-hrs). `shared/deep_learning/combinatorial.py`
- **Paper 10 — Topological fairness:** Wasserstein between subgroup residual persistence diagrams; requires Paper 7 model. `TopologicalFairnessLoss` in `shared/deep_learning/losses.py`. CPU-only, minutes.

### Submission sequence
Paper 1 → (Papers 2 + 3 simultaneous) → (Papers 5 + 4) → (Papers 7 + 10) → (Papers 8 + 9)

### Computational resource map (local i7/32GB/RTX 3080)
| Paper | Local feasible? | Cloud needed? | Runtime |
|-------|----------------|---------------|---------|
| 1–3, 5, 6, 10 | Yes, fully | No | Minutes–hours |
| 4 (full scale) | Dev only | A100, 4–8 hrs | Hours locally |
| 7, 8 (2-level) | Yes | No | Hours |
| 9 (3–4 level) | No | A100, 20–40 hrs | Cloud only |

---

## shared/deep_learning Package

Domain-agnostic DL building blocks in `shared/deep_learning/`. Use these before writing domain-specific equivalents:

| Module | Contents | Used by |
|--------|---------|---------|
| `base_trainer.py` | `BaseTrainer` (ABC), `EarlyStopping` | All domain trainers |
| `losses.py` | `VAELoss`, `PersistenceLoss`, `TopologicalFairnessLoss` | poverty_tda, trajectory_tda (Paper 10) |
| `persistence_layers.py` | `GaussianPersLayer`, `RationalHatPersLayer`, `LifetimeWeightedSum`, `PersFormerLayer`, `PersLayWeight` | Any Perslay/PersFormer-based model |
| `graph_utils.py` | `build_state_transition_graph`, `build_knn_graph`, `persistence_diagram_to_graph`, `add_household_edges` | Papers 7, 8 |
| `combinatorial.py` | `SocialCellComplex`, `build_incidence_matrix`, `complex_to_topomodelx` | Paper 9 |

When writing a new DL trainer, subclass `BaseTrainer` and implement `train_epoch()` and `validate()`.

---

## Skills

Use `/paper-draft` to initiate academic writing assistance. It reads existing paper files and drafts/extends/critiques sections following field journal conventions (JEG, Sociological Methodology, JRSS-A etc).