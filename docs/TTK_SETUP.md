# TTK Setup Guide

## Overview
This guide provides complete instructions for installing and configuring the Topology ToolKit (TTK) for the TDL project on Windows.

## Installation Summary

**Current Setup (Completed)**:
- TTK Version: 1.3.0
- Backend: Conda subprocess (isolated environment)
- VTK Version: 9.3.20240617 (TTK env) vs 9.5.2 (project env)
- Status: ✓ Fully functional

## Prerequisites

- Windows 10/11
- Conda/Miniconda installed
- Python 3.11 in project virtual environment

## Installation Steps

### 1. Create TTK Conda Environment

```bash
# Create isolated Python 3.11 environment for TTK
conda create -n ttk_env python=3.11 -y
```

### 2. Install TTK from Conda-Forge

```bash
# Install TTK with all dependencies
conda install -n ttk_env -c conda-forge topologytoolkit -y
```

This installs:
- TTK 1.3.0
- ParaView 5.13.0 (bundled)
- VTK 9.3.x
- NumPy and other dependencies

### 3. Verify Installation

```bash
# Test TTK Python bindings
conda run -n ttk_env python -c "import topologytoolkit; print('TTK OK')"

# Check VTK version
conda run -n ttk_env python -c "import vtk; print(vtk.vtkVersion.GetVTKVersion())"
```

Expected output:
```
TTK OK
9.3.20240617
```

### 4. Test from Project Environment

From the project's `.venv`:

```python
# Check TTK status
python shared/ttk_utils.py
```

Expected output:
```
============================================================
TTK Installation Status
============================================================
TTK Status: ✓ Available
Backend: conda_subprocess
Python Path: C:\Users\<user>/miniconda3/envs/ttk_env/python.exe
TTK Version: 1.3.0
VTK Version: 9.3.20240617
ParaView Filters: ✗ Not Available
============================================================
```

Note: "ParaView Filters: ✗ Not Available" is expected and does not affect functionality.

## Environment Configuration

### Python Path Configuration

The TTK Python interpreter is located at:
- **Windows**: `~/miniconda3/envs/ttk_env/python.exe`
- **Linux/Mac**: `~/miniconda3/envs/ttk_env/bin/python`

This path is automatically detected by `shared/ttk_utils.py`.

### VTK Version Isolation

The project uses **two separate VTK environments**:

| Environment | VTK Version | Purpose | Access |
|-------------|-------------|---------|--------|
| **Project `.venv/`** | 9.5.2 | Main project (PyVista, GUDHI, giotto-tda) | Direct import |
| **TTK `ttk_env`** | 9.3.x | TTK operations only | Subprocess |

This isolation prevents version conflicts and is the recommended approach.

## Usage Patterns

### Basic TTK Usage

```python
from shared.ttk_utils import is_ttk_available, run_ttk_subprocess

# Check availability
if not is_ttk_available():
    print("TTK not available - install following TTK_SETUP.md")
    return

# Run TTK analysis script
code, stdout, stderr = run_ttk_subprocess(
    "my_ttk_analysis.py",
    args=["input.vtu", "output.json"],
    timeout=120  # seconds
)

if code == 0:
    print("Analysis successful")
    print(stdout)
else:
    print(f"Analysis failed: {stderr}")
```

### TTK Analysis Script Template

Create a script that runs in the TTK environment:

```python
# my_ttk_analysis.py
import sys
import numpy as np
import vtk
from vtk.util import numpy_support
import topologytoolkit as ttk

def main(input_file, output_file):
    # Load data
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(input_file)
    reader.Update()
    data = reader.GetOutput()
    
    # Compute persistence diagram
    persistence = ttk.ttkPersistenceDiagram()
    persistence.SetInputData(data)
    persistence.SetInputArrayToProcess(0, 0, 0, 0, "ScalarField")
    persistence.Update()
    
    # Save results
    writer = vtk.vtkXMLUnstructuredGridWriter()
    writer.SetFileName(output_file)
    writer.SetInputData(persistence.GetOutput())
    writer.Write()
    
    print(f"Processed {data.GetNumberOfPoints()} points")
    print(f"Found {persistence.GetOutput().GetNumberOfPoints()} persistence pairs")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
```

Call from project code:

```python
from shared.ttk_utils import run_ttk_subprocess

code, out, err = run_ttk_subprocess(
    "my_ttk_analysis.py",
    args=["input.vti", "output.vtu"]
)
```

### Using TTK Detection Utilities

```python
from shared.ttk_utils import get_ttk_backend, check_ttk_status

# Get detailed backend information
backend = get_ttk_backend()
print(f"TTK available: {backend['available']}")
print(f"TTK version: {backend['ttk_version']}")
print(f"VTK version: {backend['vtk_version']}")

# Display full status report
check_ttk_status(verbose=True)
```

## Available TTK Filters

See [`docs/TTK_FILTER_VERIFICATION.md`](TTK_FILTER_VERIFICATION.md) for verified filters.

**Core filters (verified working)**:
- `ttkPersistenceDiagram` - Persistence diagram computation
- `ttkBottleneckDistance` - Diagram comparison
- `ttkMorseSmaleComplex` - Critical point extraction
- `ttkTopologicalSimplification` - Noise removal

**150+ additional filters available** - see [TTK documentation](https://topology-tool-kit.github.io/doc/html/index.html)

## Troubleshooting

### Issue: "TTK not available"

**Symptom**: `is_ttk_available()` returns `False`

**Solutions**:
1. Verify conda environment exists:
   ```bash
   conda env list | grep ttk_env
   ```

2. Verify TTK installed:
   ```bash
   conda list -n ttk_env | grep topologytoolkit
   ```

3. Recreate environment if needed:
   ```bash
   conda remove -n ttk_env --all -y
   conda create -n ttk_env python=3.11 -y
   conda install -n ttk_env -c conda-forge topologytoolkit -y
   ```

### Issue: Import errors in TTK subprocess

**Symptom**: `ImportError` when running TTK scripts

**Solution**: Ensure script imports are compatible with TTK environment:
- Use `import topologytoolkit as ttk` (not `from paraview.simple import ...`)
- Import `vtk` before TTK filters
- Use `numpy_support` for VTK-NumPy conversions

### Issue: Subprocess timeout

**Symptom**: `subprocess.TimeoutExpired` exception

**Solutions**:
1. Increase timeout parameter:
   ```python
   run_ttk_subprocess("script.py", timeout=300)  # 5 minutes
   ```

2. Profile TTK operations to identify slow filters
3. Consider processing data in smaller chunks

### Issue: VTK version conflicts

**Symptom**: VTK import errors or unexpected behavior

**Solution**: This should not occur due to subprocess isolation. If it does:
1. Verify using subprocess pattern (not direct import)
2. Check Python interpreter path in error messages
3. Ensure not mixing project venv and TTK env imports

## Alternative Installation: Pre-built ParaView-TTK (Not Recommended)

A pre-built ParaView+TTK bundle is available but has DLL issues on Windows.

**Downloaded but not used**: `docs/ttk_installers/ttk-paraview-v5.13.0.exe`

This was tested but has runtime DLL loading errors. The conda approach is more reliable.

## Testing TTK Installation

### Quick Test

```bash
# From project directory
python shared/ttk_utils.py
```

Should show "TTK Status: ✓ Available"

### Comprehensive Test

```bash
# Run full filter verification
python -c "from shared.ttk_utils import run_ttk_subprocess; run_ttk_subprocess('tests/shared/ttk_filter_verification.py')"
```

Should show all filters passing.

### Unit Tests

```bash
# Run TTK utilities test suite
pytest tests/shared/test_ttk_utils.py -v
```

Expected: 20 passed, 1 skipped

## Integration with Existing Code

### Poverty TDA Pattern

TTK usage matches the existing pattern in `poverty_tda/topology/morse_smale.py`:
- Subprocess calls to isolated environment
- VTK version isolation
- Error handling and graceful fallbacks

### Example Integration

```python
# In your analysis module
from shared.ttk_utils import is_ttk_available, run_ttk_subprocess, get_ttk_unavailable_message

def compute_persistence(data_path, output_path):
    """Compute persistence diagram using TTK."""
    if not is_ttk_available():
        print(get_ttk_unavailable_message())
        return None
    
    # Create TTK script dynamically or use pre-written script
    code, stdout, stderr = run_ttk_subprocess(
        "compute_persistence_script.py",
        args=[data_path, output_path],
        timeout=60
    )
    
    if code != 0:
        raise RuntimeError(f"TTK computation failed: {stderr}")
    
    return output_path
```

## CI/CD Considerations

**TTK in CI**: Optional, not required for project tests

If adding TTK to CI:
1. Add conda installation step
2. Create ttk_env in CI pipeline
3. Install topologytoolkit
4. Run TTK-dependent tests separately

Currently not implemented as TTK tests can be run locally when needed.

## References

- **TTK Official Website**: https://topology-tool-kit.github.io/
- **TTK Documentation**: https://topology-tool-kit.github.io/doc/html/index.html
- **TTK Examples**: https://topology-tool-kit.github.io/examples/
- **Project TTK Utilities**: `shared/ttk_utils.py`
- **Filter Verification**: `docs/TTK_FILTER_VERIFICATION.md`

## Summary

TTK 1.3.0 is successfully installed and integrated using a conda subprocess approach that:
- ✓ Isolates VTK versions (9.3.x for TTK, 9.5.2 for project)
- ✓ Prevents import conflicts
- ✓ Provides access to 150+ TTK filters
- ✓ Works reliably on Windows
- ✓ Matches proven poverty_tda pattern

All core filters are verified and ready for use in Phase 6.5 TTK integration tasks.
