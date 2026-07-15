---
paths:
  - "**/*.py"
---

# Python Conventions (detail)

- **Python 3.13**, 120-char line length (enforced by the root `.ruff.toml`, which takes precedence over `pyproject.toml`), Ruff rules E/F/I/W.
- **Type hints** mandatory on all public APIs; use `numpy.typing.NDArray`, not bare `np.ndarray`.
- **Docstrings:** Google-style on all public functions/classes.
- **Imports:** standard → third-party → local; no wildcard imports.
- **Pre-commit:** ruff lint/format + the contract validator run on every commit; never skip hooks. **Hooks live in `.githooks/` (tracked), because the repo sets `core.hooksPath=.githooks` — anything placed in `.git/hooks/` is IGNORED by git and silently never runs.** That is not hypothetical: the contract validator sat in `.git/hooks/pre-commit` from 2026-05-27 and never executed once, because the redirect had been in force since 2026-04-10. Never install a hook to `.git/hooks`. Verify the gate is live with `uv run python .claude/hooks/install-git-hooks.py`.
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
