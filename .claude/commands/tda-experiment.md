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
- Include `metadata` dict in results JSON: `{n_permutations, n_landmarks, runtime_s, date}`
- PCA loadings **frozen** from full-sample fit — do not refit on surrogates
- Maxmin landmarks re-selected on each surrogate (do not couple landmark geometry to observed data)
- Permutation nulls use fixed seeds when reproducibility matters: `np.random.seed(42)`

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
