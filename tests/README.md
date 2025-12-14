# Test Suite

## Overview
Comprehensive test suite for both TDA projects and shared utilities.

## Structure

### Organization
```
tests/
├── financial_tda/      # Tests for financial project modules
├── poverty_tda/        # Tests for poverty project modules
├── shared/             # Tests for shared utilities
├── integration/        # Cross-module integration tests
└── fixtures/           # Test data and fixtures
```

### Test Categories
- **Unit tests**: Individual function/class testing
- **Integration tests**: Module interaction testing
- **Data validation tests**: Input/output verification
- **Regression tests**: Ensure consistent results
- **Performance tests**: Computational efficiency checks

## Running Tests
```bash
# Run all tests
pytest

# Run specific project tests
pytest tests/financial_tda/
pytest tests/poverty_tda/

# Run with coverage
pytest --cov=financial_tda --cov=poverty_tda --cov=shared

# Run specific test categories
pytest -m unit
pytest -m integration
```

## Writing Tests
- Use `pytest` framework
- Place tests in corresponding project subdirectories
- Name test files as `test_*.py`
- Use descriptive test function names: `test_<function>_<scenario>_<expected_result>`
- Parametrize tests for multiple input scenarios
- Use fixtures for common test data

## Coverage Goals
- Maintain >80% code coverage
- Critical algorithms should have >95% coverage
- All public APIs must have tests
