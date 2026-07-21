---
name: tda-experiment
description: Use when scaffolding and running a new TDA experiment — follows codebase conventions (domain data/topology/analysis modules, results output, seed recording).
metadata:
  version: "1.0.0"
  tier: domain
  lanes:
    - topology
    - output-provenance
  roles:
    - implementer
  runtime: agnostic
---

# /tda-experiment — Run a TDA Experiment

Scaffold a new TDA experiment following codebase conventions.

## Usage

```
/tda-experiment [domain] [experiment-name]
```

Example: `/tda-experiment trajectory_tda wasserstein-bhps-validation`

---

## Standard experiment structure

```python
# trajectory_tda/experiments/[experiment_name].py

"""[One-line description of what this experiment tests.]

Experiment: [experiment name]
Paper: PXX
Branch: run/pXX-[name]
Results: results/trajectory_tda_integration/[output].json
"""

from pathlib import Path
from numpy.typing import NDArray
import numpy as np
import json

RESULTS_DIR = Path("results/trajectory_tda_integration")

def main() -> None:
    """Run experiment and save results to RESULTS_DIR."""
    ...

if __name__ == "__main__":
    main()
```

## Conventions

- All numeric outputs serialised to JSON in `results/`
- Include `metadata` dict in results JSON: `{n_permutations, n_landmarks, seed, runtime_s, date}` — record `seed` so any seeded stochastic run is reproducible from the results file alone
- PCA loadings **frozen** from full-sample fit — do not refit on surrogates
- Maxmin landmarks re-selected on each surrogate (do not couple landmark geometry to observed data)
- Permutation nulls use fixed seeds when reproducibility matters: `np.random.seed(42)`

## Execution pre-flight

Before launching compute:

1. **Classify the changed stage.** State whether the request changes persistence-
   diagram generation, pairwise metric aggregation, or downstream summary /
   provenance. A downstream metric correction must reuse valid cached diagrams
   and preserve the pre-registered B/cell design. Do not expand robustness cells
   or regenerate PH unless the dispatch explicitly authorizes that design change.
2. **Check process ownership.** On Windows, do not call
   `compute_rips_ph(timeout_seconds=...)` from inside a joblib `loky` worker.
   Use the joblib worker timeout as the wall-time guard; reserve the PH child-
   process timeout for observed or otherwise serial calls.
3. **Bound feasibility modes.** Benchmark-only and feasibility runs must cap
   every expensive prerequisite, including shared null-null banks and observed-
   to-bank distances. Write a launch/progress marker before the first PH or W2
   batch, and report both sampled work and the projected full-design distance
   count.

## Pre-delivery verification

- The corrected analysis stage and cache reuse boundary are explicit.
- Parameters still match the governing pre-registration or authorized amendment.
- No nested child-process timeout is used inside a `loky` worker.
- A benchmark cannot silently perform a full-design prerequisite before its first
  checkpoint.

## Null model parameters by test type

| Null | n (standard) | n (publication) | Landmarks |
|---|---|---|---|
| Total persistence | 100 | 500 | 5,000 |
| Wasserstein | 100 | 200 | 2,000 |
| Stratified Wasserstein | 50 | 200 | 2,000 |
| Phase-order shuffle | 500 | 500 | 3,000 |

## Output JSON schema

```json
{
  "metadata": {
    "experiment": "name",
    "paper": "P01",
    "date": "2026-03-24",
    "n_permutations": 100,
    "n_landmarks": 2000,
    "seed": 42,
    "runtime_s": 471.2,
    "hardware": "i7/32GB"
  },
  "results": {
    "null_type": {
      "dim": {
        "obs_null_mean": 11.22,
        "obs_null_std": 1.52,
        "null_null_mean": 6.62,
        "null_null_std": 2.37,
        "p_value": 0.058
      }
    }
  }
}
```
