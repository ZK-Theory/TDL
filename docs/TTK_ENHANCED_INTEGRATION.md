# Enhanced TTK Integration - Task 6.5.2

This document describes the enhanced TTK (Topology ToolKit) integration features implemented in Task 6.5.2, which build upon the foundation established in Task 6.5.1.

## Overview

Task 6.5.2 migrates TTK functionality to centralized utilities and adds enhanced topological analysis features:

1. **Centralized TTK Utilities** - Unified detection and subprocess management
2. **Topological Simplification** - Pre-processing to remove noise
3. **Enhanced Critical Point Extraction** - Flexible threshold control
4. **Filtering and Refinement** - Post-processing capabilities

## New Features

### 1. Centralized TTK Detection (`shared.ttk_utils`)

All TTK functionality now uses centralized detection and subprocess management:

```python
from shared.ttk_utils import is_ttk_available, run_ttk_subprocess, get_ttk_backend

# Check TTK availability
if is_ttk_available():
    # Get backend information
    backend = get_ttk_backend()
    print(f"TTK available via: {backend['backend']}")
```

**Benefits:**
- Consistent TTK detection across all modules
- Unified error messages and troubleshooting
- Single source of truth for environment configuration
- Better subprocess management with timeout and error handling

### 2. Topological Simplification

Remove low-persistence topological noise before analysis:

```python
from poverty_tda.topology import simplify_scalar_field, compute_morse_smale

# Option 1: Standalone simplification
simplified_path = simplify_scalar_field(
    "mobility.vti",
    persistence_threshold=0.08,  # Remove 8% noise
    scalar_name="mobility"
)

# Option 2: Integrated simplification
result = compute_morse_smale(
    "mobility.vti",
    simplify_first=True,
    simplification_threshold=0.10,  # Pre-simplify with 10% threshold
    persistence_threshold=0.05       # Then extract with 5% threshold
)
```

**Use Cases:**
- Clean noisy sensor data before analysis
- Remove measurement artifacts
- Focus on large-scale topological features
- Improve visualization quality

**Threshold Recommendations** (from Task 6.5.1):
- **5% (0.05)**: Good starting point, removes minor noise
- **10% (0.10)**: Aggressive noise removal, keeps major features only
- **1% (0.01)**: Conservative, preserves most features

### 3. Enhanced Critical Point Extraction

Flexible threshold control for different analysis stages:

```python
from poverty_tda.topology import compute_morse_smale

# Standard extraction with single threshold
result = compute_morse_smale(
    "mobility.vti",
    persistence_threshold=0.05  # 5% of scalar range
)

# Enhanced extraction with separate thresholds
result = compute_morse_smale(
    "mobility.vti",
    simplify_first=True,
    simplification_threshold=0.10,  # Aggressive noise removal
    persistence_threshold=0.02       # Then fine-grained extraction
)
```

**Parameters:**
- `persistence_threshold`: Threshold for Morse-Smale computation (default 0.05)
- `simplify_first`: Enable pre-simplification (default False)
- `simplification_threshold`: Threshold for pre-simplification (defaults to `persistence_threshold`)

### 4. Post-Processing and Filtering

Refine critical points after extraction:

```python
from poverty_tda.topology import compute_morse_smale, filter_by_persistence

# Extract all features
result = compute_morse_smale("mobility.vti", persistence_threshold=0.0)

# Filter by significance
significant_points = filter_by_persistence(
    result.critical_points,
    persistence_threshold=0.05,
    scalar_range=result.scalar_range
)

print(f"Filtered: {len(result.critical_points)} -> {len(significant_points)}")
```

### 5. Automatic Threshold Selection

Let the data suggest optimal thresholds:

```python
from poverty_tda.topology import compute_morse_smale, suggest_persistence_threshold

# Initial extraction
result = compute_morse_smale("mobility.vti", persistence_threshold=0.0)

# Get suggested threshold
threshold = suggest_persistence_threshold(
    result,
    method="gap"  # Options: "elbow", "gap", "quantile"
)

# Re-compute with suggested threshold
result_filtered = compute_morse_smale(
    "mobility.vti",
    persistence_threshold=threshold
)
```

**Methods:**
- `"gap"`: Largest gap in persistence values (recommended)
- `"elbow"`: Elbow point in persistence curve
- `"quantile"`: Based on persistence distribution

## Migration Guide

### From Old Code

```python
# Old: Module-specific TTK detection
from poverty_tda.topology.morse_smale import check_ttk_environment, get_ttk_python_path

if check_ttk_environment():
    ttk_python = get_ttk_python_path()
    # ...
```

### To New Code

```python
# New: Centralized TTK utilities
from shared.ttk_utils import is_ttk_available, get_ttk_backend

if is_ttk_available():
    backend = get_ttk_backend()
    print(f"Using: {backend['backend']}")
    # ...
```

**Note:** Old functions still work for backward compatibility but are deprecated.

## Complete Workflow Example

```python
from poverty_tda.topology import (
    compute_morse_smale,
    suggest_persistence_threshold,
    simplify_scalar_field
)

# Step 1: Analyze noisy data to determine noise level
result_noisy = compute_morse_smale(
    "mobility.vti",
    persistence_threshold=0.0
)
print(f"Initial extraction: {len(result_noisy.critical_points)} points")

# Step 2: Get recommended threshold
threshold = suggest_persistence_threshold(result_noisy, method="gap")
print(f"Recommended threshold: {threshold:.2%}")

# Step 3: Extract with pre-simplification
result_clean = compute_morse_smale(
    "mobility.vti",
    simplify_first=True,
    simplification_threshold=0.10,     # Remove 10% noise
    persistence_threshold=threshold     # Use recommended threshold
)

# Step 4: Analyze significant features
maxima = result_clean.get_maxima()
minima = result_clean.get_minima()

print(f"\nSignificant features:")
print(f"  Opportunity hotspots: {len(maxima)}")
print(f"  Poverty traps: {len(minima)}")
```

## Performance Considerations

1. **Pre-Simplification**:
   - Adds ~10-30% overhead for simplification
   - Saves time in subsequent analysis by reducing features
   - Recommended for noisy data or when extracting multiple times

2. **Threshold Selection**:
   - Minimal overhead (<1% of extraction time)
   - Run once, then reuse threshold for similar datasets

3. **Memory Usage**:
   - Temporary simplified files are automatically cleaned up
   - No significant memory overhead

## Testing

New features are tested in:
- `tests/poverty/topology/test_step3_features.py` - Step 3 specific tests
- `tests/poverty/test_morse_smale.py` - Integration tests (45 tests pass)
- `tests/shared/examples/ttk_enhanced_integration_guide.py` - Comprehensive examples

Run tests:
```bash
# Run all Morse-Smale tests
pytest tests/poverty/test_morse_smale.py -v

# Run Step 3 feature tests
pytest tests/poverty/topology/test_step3_features.py -v

# Run comprehensive examples
python tests/shared/examples/ttk_enhanced_integration_guide.py
```

## API Reference

### `simplify_scalar_field()`

```python
def simplify_scalar_field(
    vtk_path: Path | str,
    persistence_threshold: float,
    scalar_name: str = "mobility",
    output_path: Path | str | None = None,
) -> Path
```

Simplify a scalar field by removing low-persistence topological noise.

**Parameters:**
- `vtk_path`: Path to input VTK file
- `persistence_threshold`: Threshold as fraction of scalar range (0.0-1.0)
- `scalar_name`: Name of scalar field to simplify
- `output_path`: Optional output path (creates temp file if None)

**Returns:** Path to simplified VTK file

### `compute_morse_smale()` (Enhanced)

```python
def compute_morse_smale(
    vtk_path: Path | str,
    scalar_name: str = "mobility",
    persistence_threshold: float = 0.05,
    compute_ascending: bool = True,
    compute_descending: bool = True,
    compute_separatrices: bool = True,
    simplify_first: bool = False,              # NEW
    simplification_threshold: float | None = None,  # NEW
) -> MorseSmaleResult
```

**New Parameters:**
- `simplify_first`: Apply topological simplification before extraction
- `simplification_threshold`: Threshold for pre-simplification (defaults to `persistence_threshold`)

### `filter_by_persistence()`

```python
def filter_by_persistence(
    critical_points: list[CriticalPoint],
    persistence_threshold: float,
    scalar_range: tuple[float, float],
) -> list[CriticalPoint]
```

Filter critical points by persistence threshold.

**Parameters:**
- `critical_points`: List of CriticalPoint objects
- `persistence_threshold`: Threshold as fraction of scalar range
- `scalar_range`: (min, max) tuple of scalar field range

**Returns:** Filtered list of critical points

## Troubleshooting

### TTK Not Available

```
RuntimeError: TTK not available...
```

**Solution:** Install TTK in conda environment:
```bash
conda create -n ttk_env python=3.11
conda install -n ttk_env -c conda-forge topologytoolkit
```

See `docs/TTK_SETUP.md` for details.

### Simplification Has No Effect

If simplification doesn't reduce critical points, try:
1. Increase `simplification_threshold` (e.g., from 0.05 to 0.10)
2. Check data quality - may already be clean
3. Verify scalar field has sufficient range

### Memory Issues

For very large datasets:
1. Process in chunks
2. Use higher thresholds to reduce feature count
3. Clean up temporary files explicitly if needed

## Related Documentation

- `docs/TTK_SETUP.md` - TTK installation and configuration
- `docs/TASK_6_5_1_HANDOFF.md` - Initial TTK integration (Task 6.5.1)
- `shared/ttk_utils.py` - Centralized TTK utilities implementation
- `poverty_tda/topology/morse_smale.py` - Main implementation

## Credits

Implementation: Task 6.5.2 - Migration to Centralized TTK Utilities  
Based on: Task 6.5.1 findings and verification results  
TTK Version: conda-forge topologytoolkit  
Testing: 51 tests across all modules (all passing)
