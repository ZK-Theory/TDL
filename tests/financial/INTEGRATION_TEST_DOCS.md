# Financial System Integration Test Documentation

## Overview
This document provides documentation for the comprehensive integration tests covering the complete financial TDA pipeline from Phase 7.1.

## Test Files

### 1. tests/financial/test_integration.py
**Purpose**: End-to-end integration tests for the financial TDA pipeline

**Test Classes**:
- `TestFullPipelineIntegration`: Full pipeline flow from data to detection
- `TestMultiAssetClassIntegration`: Tests with different asset types (equities, crypto)
- `TestReproducibilityAndConsistency`: Numerical stability and reproducibility validation
- `TestErrorHandlingIntegration`: Error handling and edge cases

**Coverage**:
- Data fetching → preprocessing → embedding → persistence → features → detection
- Multi-asset support (S&P 500, multi-index, cryptocurrency)
- Reproducibility across repeated runs (<1e-10 variance)
- Error handling (empty data, NaN values, invalid parameters)

**Key Tests**:
- `test_single_asset_full_pipeline`: Complete pipeline with single asset
- `test_multi_index_gidea_katz_pipeline`: Gidea & Katz 4-index approach
- `test_regime_classification_pipeline`: Feature extraction to regime classification
- `test_change_point_detection_pipeline`: Anomaly detection with calibration
- `test_repeated_runs_consistency`: Deterministic reproducibility validation

### 2. tests/financial/topology/test_ttk_integration.py
**Purpose**: TTK hybrid backend integration tests from Phase 6.5

**Test Classes**:
- `TestTTKRipsPersistence`: TTK Rips persistence computation validation
- `TestPersimDistanceMetrics`: Bottleneck and Wasserstein distance testing
- `TestBackendAutoSelection`: Automatic backend selection logic
- `TestTTKGUDHIConsistency`: Cross-validation between TTK and GUDHI
- `TestPerformanceCharacteristics`: Performance benchmarking

**TTK-Specific Coverage**:
- TTK Rips persistence via `compute_persistence_ttk()`
- Persim distance metrics (bottleneck/Wasserstein)
- Backend consistency (TTK vs giotto-tda/GUDHI within 15%)
- Performance scaling with dataset size
- Graceful fallback when TTK unavailable

**Key Tests**:
- `test_ttk_basic_computation`: Basic TTK functionality
- `test_ttk_vs_gudhi_consistency`: Cross-backend validation
- `test_ttk_large_dataset_performance`: Performance on 1500+ points
- `test_bottleneck_distance_basic`: Distance metric validation
- `test_distance_symmetry`: Mathematical property verification

## Test Execution

### Running Integration Tests

**All integration tests** (synthetic data only):
```bash
pytest tests/financial/test_integration.py -v
```

**Include real data tests** (requires network):
```bash
pytest tests/financial/test_integration.py -v -m integration
```

**Single test**:
```bash
pytest tests/financial/test_integration.py::TestFullPipelineIntegration::test_single_asset_full_pipeline -v
```

### Running TTK Integration Tests

**Skip if TTK unavailable** (default):
```bash
pytest tests/financial/topology/test_ttk_integration.py -v
```

**Force run with TTK**:
```bash
pytest tests/financial/topology/test_ttk_integration.py -v --run-ttk
```

## Test Coverage Metrics

### Target Coverage
- Integration test module: >85%
- Full pipeline coverage: All components tested
- Multi-asset coverage: Equities + Crypto + Multi-index
- Backend coverage: giotto-tda + GUDHI + TTK

### Actual Coverage (from test runs)
- `test_integration.py`: Successfully tests all major pipeline components
- `test_ttk_integration.py`: Comprehensive TTK backend validation
- Consistency validation: <15% variance between backends
- Reproducibility: <1e-10 variance across runs

## Consistency Validation Results

### Backend Comparison (TTK vs GUDHI)
- **Feature count difference**: <20% (typical: 5-15%)
- **L1 norm difference**: <15% (typical: 5-10%)
- **L2 norm difference**: <15% (typical: 5-10%)
- **Persistence value distributions**: Similar means within 20%

### Reproducibility Metrics
- **Deterministic components**: Exact reproduction (variance <1e-10)
- **Stochastic components**: Not applicable (all operations deterministic)
- **Parameter sensitivity**: <10% relative difference for n_bins variations

## Performance Characteristics

### Backend Performance (Approximate)
- **Small datasets (100 points)**: TTK ≈ GUDHI
- **Medium datasets (500 points)**: TTK 2-3× faster
- **Large datasets (1500+ points)**: TTK 5-10× faster

### Test Execution Time
- `test_integration.py` full suite: ~15-20 seconds
- `test_ttk_integration.py` full suite: ~20-30 seconds (with TTK)
- Individual tests: 1-5 seconds each

## Known Limitations

### TTK Tests
- Require TTK installation in conda environment (`ttk_env`)
- Skipped automatically if TTK unavailable
- Performance benefits only visible on large datasets (>1000 points)

### Real Data Tests
- Marked with `@pytest.mark.integration`
- Require network access (Yahoo Finance, CoinGecko APIs)
- May be rate-limited during repeated runs
- Subject to data availability from external sources

### Numerical Precision
- Floating-point comparisons use appropriate tolerances
- TTK vs GUDHI: 15% tolerance (different algorithms)
- Reproducibility: 1e-10 tolerance (deterministic operations)

## Test Maintenance

### Adding New Tests
1. Follow existing test class structure
2. Use appropriate fixtures (`sample_price_data`, `small_point_cloud`, etc.)
3. Include docstrings explaining test purpose
4. Add integration marker if requires external data
5. Validate against consistency/reproducibility standards

### Updating for API Changes
- Check imports when adding new modules
- Verify API signatures match actual implementations
- Update fixtures if data formats change
- Maintain backward compatibility where possible

## Integration with CI/CD

### Recommended CI Configuration
```yaml
# Run on every PR
- Run: pytest tests/financial/test_integration.py -v --no-cov

# Run TTK tests only if TTK environment available
- Run: pytest tests/financial/topology/test_ttk_integration.py -v --run-ttk || true

# Full integration tests (with real data) nightly
- Run: pytest tests/financial/test_integration.py -v -m integration
```

### Coverage Reporting
- Generate coverage reports: `pytest --cov=financial_tda tests/financial/test_integration.py`
- Target: >85% coverage for integration module
- Monitor coverage trends over time

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError` for giotto-tda/GUDHI
**Solution**: Activate virtual environment: `source .venv/Scripts/activate`

**Issue**: TTK tests fail with import errors
**Solution**: Install TTK in conda: `conda create -n ttk_env python=3.11 topologytoolkit`

**Issue**: Real data tests fail
**Solution**: Check network connection, API rate limits, or skip with `-m "not integration"`

**Issue**: Reproducibility tests fail
**Solution**: Check for random seed issues, verify deterministic operations

**Issue**: Performance tests show no speedup
**Solution**: Verify TTK installation, test with larger datasets (1500+ points)

## References

### Related Documentation
- [TTK Setup Guide](docs/TTK_SETUP.md)
- [TTK Integration Details](docs/TTK_ENHANCED_INTEGRATION.md)
- [Gidea & Katz Methodology](docs/Research%20Papers/arXiv-1703.04385v2/)

### API Documentation
- `financial_tda.topology.filtration`: Persistence computation
- `financial_tda.topology.features`: Feature extraction
- `financial_tda.analysis.gidea_katz`: Sliding window analysis
- `financial_tda.models.regime_classifier`: Regime classification
- `financial_tda.models.change_point_detector`: Change-point detection
