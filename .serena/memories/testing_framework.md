# TDL Testing Framework

## Testing Tool
- **pytest** with custom markers and configuration
- Configuration in `pyproject.toml` under `[tool.pytest.ini_options]`

## Test Markers
Mark tests appropriately using pytest markers:

### @pytest.mark.slow
- Tests that take more than 1 second to run
- Run tests without slow: `uv run pytest -m "not slow"`

### @pytest.mark.integration  
- Tests involving multiple modules or external systems
- Run integration tests: `uv run pytest -m integration`

### @pytest.mark.validation
- Mathematical validation tests for TDA functions
- Run validation tests: `uv run pytest -m validation`

## Test Commands

```bash
# Run all tests
uv run pytest

# Skip slow tests (default for development)
uv run pytest -m "not slow"

# Only validation tests (mathematical correctness)
uv run pytest -m validation

# Domain-specific tests
uv run pytest tests/financial_tda/
uv run pytest tests/poverty_tda/
uv run pytest tests/trajectory/

# With coverage
uv run pytest --cov=financial_tda --cov=poverty_tda --cov=shared --cov=trajectory_tda
```

## Mathematical Validation Requirements

### For TDA Functions
Tests should verify:
- **Mathematical invariants** (e.g., birth ≤ death in persistence diagrams)
- **Topological properties** (e.g., Betti numbers for known shapes)
- **Consistency with established libraries** (gudhi, giotto-tda comparisons)

### Test Helpers (from conftest.py)
- `assert_persistence_diagram_valid()` - Validates diagram format
- `assert_betti_numbers_match()` - Compares computed vs expected Betti numbers
- `assert_bottleneck_distance_within()` - Validates diagram stability

### Numerical Tolerances
- `FLOAT_TOLERANCE = 1e-10` - General floating-point comparisons
- `BETTI_TOLERANCE = 0.1` - 10% tolerance for Betti number comparisons (follows Gidea & Katz methodology)

## Test Data Fixtures
- `sample_time_series()` - Synthetic time series (sine, random walk, noisy sine)
- `sample_point_cloud()` - Geometric shapes with known topology (circle, torus, two circles)