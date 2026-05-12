# TDL Code Style & Conventions

## Language Standards
- **Python 3.13** with exact version requirements
- **Line Length**: 88 characters maximum
- **Import Organization**: Standard → Third-party → Local (financial_tda, poverty_tda, shared, trajectory_tda)

## Type Hints (Mandatory)
- **All public APIs** must have complete type annotations
- Use `numpy.typing.NDArray` for numpy arrays, not bare `np.ndarray`
- Example:
```python
from numpy.typing import NDArray
import numpy as np

def compute_persistence(point_cloud: NDArray[np.float64], max_dim: int = 2) -> list[tuple]:
    """Compute persistent homology of a point cloud."""
    pass
```

## Docstrings (Google Style)
- **All public functions/classes** require Google-style docstrings
- Required sections: Args, Returns, Raises (if applicable)
- Recommended: Examples, Notes, References for TDA methods

```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """Short one-line description.

    Args:
        param1: Description of first parameter.
        param2: Description of second parameter.

    Returns:
        Description of return value.

    Raises:
        ValueError: When invalid input is provided.

    Examples:
        >>> result = function_name(arg1, arg2)
        >>> print(result)
        expected_output
    """
```

## Research Context Comments
Every new script must include research context header:
```python
# Research context: TDA-Research/03-Papers/P01/_project.md
# Purpose: [what this script does in the research context]
```

## Linting & Formatting
- **Ruff** for linting and formatting (configured in pyproject.toml)
- Rules: E (pycodestyle errors), F (pyflakes), I (isort), W (warnings)
- **Pre-commit hooks** automatically enforce style on every commit
- Commands:
  - `uv run ruff check .` - Check for issues
  - `uv run ruff check . --fix` - Auto-fix issues
  - `uv run ruff format .` - Format code

## Random Seeds
- **Always specify and record** seeds for any stochastic process
- Log seeds in script and vault Computational-Log entry
- Example: `np.random.seed(42)  # Reproducibility`

## Import Restrictions
- **No wildcard imports** (`from module import *`)
- Use explicit imports for clarity