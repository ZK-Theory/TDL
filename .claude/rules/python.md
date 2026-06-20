---
paths:
  - "**/*.py"
---

# Python Conventions (detail)

- **Python 3.13**, 88-char line length, Ruff rules E/F/I/W.
- **Type hints** mandatory on all public APIs; use `numpy.typing.NDArray`, not bare `np.ndarray`.
- **Docstrings:** Google-style on all public functions/classes.
- **Imports:** standard → third-party → local; no wildcard imports.
- **Pre-commit:** ruff lint/format runs on every commit; never skip hooks.
- **Research context comment** at the top of every new script:

  ```python
  # Research context: TDA-Research/03-Papers/P01/_project.md
  # Purpose: [what this script does in the research context]
  ```

- **Random seeds:** always specify and record for any stochastic process (Markov simulation, permutation tests, bootstrap); log them in the script and in the vault's Computational-Log entry.

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
