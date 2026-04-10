---
name: paper-repo-extract
version: 1.0.0
description: |
  Extract a paper-specific standalone GitHub repository from the TDL monorepo,
  suitable for Zenodo DOI minting and journal submission. Walks through the full
  checklist: import tracing, repo-manifest.yaml, standalone pyproject.toml,
  synthetic data generator, numbered reproduction scripts, smoke tests, and
  _project.md update with repo URL and DOI fields. Use after all computation
  for a paper is complete and before journal submission.
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - AskUserQuestion
---

# Paper Repo Extract: Create a Standalone Reproducibility Repository

You are preparing a standalone reproducibility repository for a paper in this
research programme. The repository will be hosted on GitHub and archived on
Zenodo for a permanent DOI, which is required in the paper's submission statements.

**Precondition:** All computation must be complete (all results JSON/NPY files exist).
Do not start this process if the paper is still actively iterating on results.

## Step 1 — Identify the paper and confirm readiness

Ask the user:
1. Which paper: `P01-A`, `P01-B`, `P04`, or other
2. Confirm all result files exist (check `results/trajectory_tda_integration/` or
   domain-specific `results/` directory)
3. Read `papers/PXX/_project.md` — is `status` appropriate for extraction?
   (should be `submitted` or nearly so; warn if `in-progress`)

## Step 2 — Trace imports from entry scripts

1. Find all entry-point scripts for the paper (ask user or scan for scripts that
   reference the paper in their module docstring or `# Paper:` comment)
2. Trace the import graph:
   - Direct imports from `trajectory_tda/`, `poverty_tda/`, `financial_tda/`, `shared/`
   - Indirect imports (modules that import other modules)
3. List every module file that is part of the dependency tree
4. Exclude: test files, notebooks, developer utilities, other papers' scripts

## Step 3 — Create the repo manifest

Create `papers/PXX/repo-manifest.yaml`:

```yaml
paper: PXX
title: "[paper title]"
repo-name: pXX-[slug]   # e.g. p01b-markov-memory-ladder
zenodo-concept-doi: null  # fill after Zenodo setup
github-url: null          # fill after repo creation

# Source files to copy into standalone repo src/
source-files:
  - src/: trajectory_tda/topology/permutation_nulls.py
  - src/: trajectory_tda/topology/rips_persistence.py
  # ... list all traced modules

# Entry scripts → become numbered reproduction scripts
scripts:
  - "01_embed.py": trajectory_tda/scripts/bhps_pipeline.py  # or relevant script
  - "02_null_battery.py": trajectory_tda/experiments/null_experiment.py

# Results files to include as pre-computed artifacts
results:
  - results/trajectory_tda_integration/null_markov_k1.json
  # ...

# Dependencies (only those actually used)
dependencies:
  - giotto-tda>=0.6
  - gudhi>=3.8
  - persim>=0.3
  - numpy>=1.26,<2.0
  - scipy>=1.12
  - umap-learn>=0.5
  - pandas>=2.2
  python: ">=3.13"
```

## Step 4 — Scaffold the standalone repo directory

Create the directory structure at `../pXX-[slug]/` (sibling of TDL):

```
pXX-[slug]/
├── README.md
├── LICENSE              # MIT
├── pyproject.toml       # minimal, standalone dependencies only
├── .gitignore
├── src/                 # copied source modules, imports rewritten
│   └── [module files]
├── data/
│   └── synthetic/       # synthetic data (see Step 5)
├── results/             # pre-computed artifacts from TDL results/
├── scripts/
│   ├── 01_[first_step].py
│   ├── 02_[second_step].py
│   └── ...              # numbered to match pipeline stages
└── tests/
    └── test_smoke.py    # smoke tests on synthetic data (see Step 6)
```

Use `papers/repo-template/` as the template source if it exists.

## Step 5 — Create the synthetic data generator

Create `data/synthetic/generate_synthetic_data.py`:

```python
# Research context: TDA-Research/03-Papers/PXX/_project.md
# Purpose: Generate synthetic trajectory data reproducing statistical properties
#          of the real BHPS/USoc data for smoke testing. Does NOT contain real data.

"""Synthetic data generator for [paper title] reproduction tests.

Generates trajectory data with the same statistical properties as the
BHPS/USoc panel data used in the paper:
  - N trajectories, T time steps
  - 9-state employment state space (same as real data)
  - Transition matrix estimated from real data summary statistics
  - State frequency distribution matches real data marginals

This generator is intended for testing the pipeline code only.
Results on synthetic data will not replicate the paper's findings.
"""
import numpy as np
from numpy.typing import NDArray

# State space (matches BHPS/USoc coding from trajectory_tda)
STATES = [...]  # fill from real code

def generate_synthetic_trajectories(
    n_trajectories: int = 500,
    n_time_steps: int = 16,
    seed: int = 42,
) -> list[list[str]]:
    """Generate synthetic trajectories matching real data marginals."""
    rng = np.random.RandomState(seed)
    # ... implementation
```

Key requirements for the synthetic data generator:
- Must reproduce **statistical properties**, not real data values
- State space must match the real state space exactly
- Transition probabilities based on published summary statistics only
- Clearly documented as synthetic in module docstring and README
- Seed must be specified as a parameter, not hardcoded

## Step 6 — Rewrite imports

For every copied source file, rewrite imports:
- `from trajectory_tda.topology.X import Y` → `from src.X import Y`
- `from shared.X import Y` → `from src.shared_X import Y` (rename to avoid conflict)
- Remove any domain-agnostic utility re-imports that are not needed

Check that no file in `src/` imports anything from the TDL monorepo after rewriting.

## Step 7 — Write smoke tests

Create `tests/test_smoke.py`:

```python
"""Smoke tests for [paper title] reproducibility repo.

These tests run on synthetic data and verify the pipeline code executes
without errors. They do not replicate the paper's numerical results.
"""
import pytest
from data.synthetic.generate_synthetic_data import generate_synthetic_trajectories

def test_synthetic_data_generation():
    trajs = generate_synthetic_trajectories(n_trajectories=50, seed=42)
    assert len(trajs) == 50
    assert all(isinstance(t, list) for t in trajs)

def test_permutation_test_runs():
    """Smoke test: permutation test completes without error on synthetic data."""
    from src.permutation_nulls import permutation_test_trajectories
    trajs = generate_synthetic_trajectories(n_trajectories=50, seed=42)
    # ... embed and run with n_permutations=2 for speed
    assert "H0" in results
    assert "p_value" in results["H0"]
```

## Step 8 — Checklist and handoff

Confirm each item:

- [ ] `papers/PXX/repo-manifest.yaml` created
- [ ] All source files copied with imports rewritten
- [ ] `pyproject.toml` has only required dependencies; Python 3.13 specified
- [ ] Synthetic data generator created and documented
- [ ] Numbered reproduction scripts created (01–NN)
- [ ] Smoke tests pass: `cd pXX-[slug] && uv run pytest tests/ -v`
- [ ] README.md explains: paper, data note (BHPS/USoc not included), how to run
- [ ] `.gitignore` excludes real data paths

Then instruct the user on the GitHub + Zenodo steps:

```
Next steps (manual):
1. Create GitHub repo: github.com/stephendor/pXX-[slug]
2. Push the directory
3. Go to zenodo.org → GitHub → enable repo for archiving
4. Create release tag v1.0.0 on GitHub → Zenodo auto-mints DOI
5. Update papers/PXX/_project.md with:
   repo: https://github.com/stephendor/pXX-[slug]
   doi: https://doi.org/10.5281/zenodo.[ID]
6. Update papers/shared/submission-statements.md with DOI
```

## Important constraints

- Do **not** copy any real data files into the standalone repo
- Do **not** include personally identifiable information (BHPS/USoc respondents)
- Always include the UKDA-BHPS and USoc data access disclaimer in README.md
- The repo must be self-contained: `uv run pytest tests/` must pass without TDL installed
