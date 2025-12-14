# Contributing to TDL

Thank you for contributing to the Topological Data Analysis (TDL) project! This document outlines the code style, documentation standards, and development workflow for the project.

## Code Style

### Linting and Formatting

- **Linter**: We use [ruff](https://github.com/astral-sh/ruff) for linting and import sorting
- **Configuration**: All ruff settings are defined in `pyproject.toml`
- **Line Length**: Maximum 88 characters per line
- **Target Python**: Python 3.11
- **Selected Rules**: E (pycodestyle errors), F (pyflakes), I (isort), W (pycodestyle warnings)

#### Pre-Commit Hooks (Automatic)

Pre-commit hooks are configured to automatically run linting and formatting on every commit. These hooks will:
- Run ruff linting with auto-fix
- Format code with ruff
- Block commits if errors remain

The hooks are **automatically installed** when you run:
```bash
pip install -e ".[dev]"
pre-commit install
```

Your commits will now be automatically checked. If auto-fixes are applied, you'll need to stage the changes and commit again.

#### Manual Linting (When Needed)

To manually check or fix linting issues:

**Check for issues:**
```bash
ruff check .
```

**Auto-fix issues:**
```bash
ruff check . --fix
```

**Format code:**
```bash
ruff format .
```

**Check and format together:**
```bash
ruff check . --fix && ruff format .
```

#### VS Code Integration (Recommended)

Install the [Ruff VS Code extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) for real-time linting and format-on-save:

1. Install extension: `charliermarsh.ruff`
2. The repository's `.vscode/settings.json` is pre-configured with:
   - Format on save
   - Auto-fix on save
   - Import organization on save

With this setup, your code will be automatically formatted and fixed as you work, preventing linting errors before commit.

### Import Organization

Imports are automatically sorted by ruff following these rules:
- Standard library imports first
- Third-party imports second
- First-party imports last (financial_tda, poverty_tda, shared)

Ruff will automatically organize imports using isort-compatible rules already configured in `pyproject.toml`.

## Type Hints

Type hints are **mandatory** for all public APIs to ensure code clarity and enable static analysis.

### Requirements

- **Public function signatures**: All functions exported in `__init__.py` files must have complete type annotations
- **Class attributes**: All public class attributes must be typed
- **Forward references**: Use `from __future__ import annotations` at the top of modules for forward references
- **Array types**: Use `numpy.typing.NDArray` for numpy arrays
  ```python
  from numpy.typing import NDArray
  import numpy as np
  
  def process_data(data: NDArray[np.float64]) -> NDArray[np.float64]:
      ...
  ```
- **Complex types**: Define type aliases for complex or repeated type signatures
  ```python
  from typing import TypeAlias
  
  PersistenceDiagram: TypeAlias = NDArray[np.float64]  # Shape (n, 2)
  ```

### Public API Definition

Modules are considered "public" if their functions/classes are:
1. Exported via `__init__.py` at the package level (`financial_tda`, `poverty_tda`, or `shared`)
2. Intended for use by end users or other modules

All public functions must have:
- Full type hints on parameters
- Return type annotations
- Documented exceptions in docstrings

## Docstrings

We use **Google-style docstrings** for all public functions, classes, and modules.

### Required Sections

- **Short description**: One-line summary of what the function/class does
- **Args**: Description of each parameter (if any)
- **Returns**: Description of return value (if not None)
- **Raises**: Exceptions that may be raised (if applicable)

### Recommended Sections

- **Examples**: Code examples showing typical usage (highly recommended for public APIs)
- **Notes**: Mathematical details, algorithmic complexity, or implementation notes
- **References**: Citations for papers, algorithms, or external resources

### Docstring Template

```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """Short one-line description.

    Longer description if needed, explaining the mathematical
    or algorithmic approach.

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

    Notes:
        Mathematical details, complexity analysis, or
        implementation notes.

    References:
        - Author et al. (Year). "Paper Title". Journal.
    """
    pass
```

### Class Docstrings

```python
class ClassName:
    """Short one-line description of the class.

    Longer description explaining the purpose and usage of the class.

    Attributes:
        attr1: Description of first attribute.
        attr2: Description of second attribute.

    Examples:
        >>> obj = ClassName(param1, param2)
        >>> result = obj.method()
    """

    attr1: Type1
    attr2: Type2

    def __init__(self, param1: Type1, param2: Type2) -> None:
        """Initialize the class.

        Args:
            param1: Description of first parameter.
            param2: Description of second parameter.
        """
        self.attr1 = param1
        self.attr2 = param2
```

### Module Docstrings

All modules should have a docstring at the top explaining their purpose:

```python
"""Module for computing persistent homology from point clouds.

This module provides utilities for TDA analysis including:
- Vietoris-Rips complex construction
- Persistence diagram computation
- Bottleneck distance calculations
"""
```

## Testing

We use `pytest` for testing with custom markers for test categorization.

### Test Markers

Tests should be marked appropriately using pytest markers defined in `pyproject.toml`:

- **`@pytest.mark.slow`**: Tests that take more than 1 second to run
- **`@pytest.mark.integration`**: Tests that involve multiple modules or external systems
- **`@pytest.mark.validation`**: Mathematical validation tests for TDA functions

Example:
```python
import pytest

@pytest.mark.validation
def test_persistence_diagram_properties():
    """Verify mathematical properties of persistence diagrams."""
    # Test that birth <= death for all points
    pass

@pytest.mark.slow
@pytest.mark.integration
def test_full_pipeline():
    """Test the complete TDA pipeline on real data."""
    pass
```

### Mathematical Validation Tests

For TDA functions, include validation tests that verify:
- Mathematical invariants (e.g., birth ≤ death in persistence diagrams)
- Topological properties (e.g., Betti numbers for known shapes)
- Consistency with established libraries (e.g., comparing results with gudhi or giotto-tda)

### Running Tests

```bash
# Run all tests
pytest

# Run specific markers
pytest -m "not slow"              # Skip slow tests
pytest -m validation              # Only validation tests
pytest -m "integration and slow"  # Integration tests that are slow

# With coverage
pytest --cov=financial_tda --cov=poverty_tda --cov=shared
```

## Git Workflow

### Branch Naming Conventions

Use descriptive branch names following these patterns:

- **Feature**: `feature/<short-description>` (e.g., `feature/persistence-diagrams`)
- **Bugfix**: `bugfix/<issue-description>` (e.g., `bugfix/null-pointer-in-vr-complex`)
- **Documentation**: `docs/<description>` (e.g., `docs/api-reference`)
- **Refactor**: `refactor/<description>` (e.g., `refactor/topology-module`)

### Commit Message Format

Follow the conventional commits format:

```
<type>(<scope>): <short summary>

<optional detailed description>

<optional footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(topology): add Vietoris-Rips complex computation

Implements VR complex construction using scipy.spatial for
efficient distance matrix computation.

Refs: #42
```

```
fix(data): handle NaN values in time series preprocessing

Adds validation to detect and remove NaN values before
TDA pipeline execution.

Closes: #38
```

### Pull Request Requirements

Before submitting a PR:

1. **Code Quality**:
   - [ ] Code passes `ruff check .` with no errors
   - [ ] Code is formatted with `ruff format .`
   - [ ] All new code has type hints
   - [ ] All public functions have Google-style docstrings

2. **Testing**:
   - [ ] New features have corresponding tests
   - [ ] All tests pass (`pytest`)
   - [ ] Mathematical validation tests added for TDA functions
   - [ ] Coverage maintained or improved

3. **Documentation**:
   - [ ] Public API changes documented in docstrings
   - [ ] README.md updated if needed
   - [ ] Examples provided for new features

4. **Git**:
   - [ ] Branch is up to date with main
   - [ ] Commits follow conventional commit format
   - [ ] Commit messages are clear and descriptive

5. **PR Description**:
   - Clearly describe what the PR does
   - Reference related issues
   - Highlight any breaking changes
   - Include examples or screenshots if applicable

## Questions?

If you have questions about contributing, please:
- Review existing code for examples
- Check the documentation in `README.md`
- Open an issue for clarification

Thank you for helping improve TDL!
