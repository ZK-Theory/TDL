# TTK Setup Guide

## Overview

This guide documents the TTK (Topology ToolKit) installation for the TDL project on Windows and
explains the cross-Python-version subprocess-bridge architecture that makes it work alongside the
project's locked Python 3.13 environment.

## Current State (verified 2026-07-03)

| Component | Status | Notes |
|-----------|--------|-------|
| TTK compute (`topologytoolkit`) | **Working** | Via conda subprocess from project 3.13 venv |
| VTK in TTK env | **Working** | 9.3.20240617 |
| pvpython binary | **Working** | Requires `conda activate ttk_env` first |
| TTK filters via pvpython (`paraview.simple`) | **Working** | With activated env |
| TTK filters via conda python directly | **Not available** | `paraview.simple` TTK filters require pvpython, not the plain conda interpreter |
| `is_ttk_paraview_available()` | Returns `False` | Correct: tests the conda-python path (subprocess bridge); pvpython is a separate interactive path |

## Architecture: Why a Subprocess Bridge

The project's `.venv` uses **Python 3.13** (locked). TTK 1.3.0 requires **Python 3.11** and ships
with VTK 9.3.x. Importing both VTK versions in the same process causes a hard conflict.

The solution is a **conda subprocess bridge**: every TTK operation is dispatched as a child process
running under `~/miniconda3/envs/ttk_env/python.exe` (Python 3.11), keeping the two VTK versions
fully isolated. The bridge is implemented in `shared/ttk_utils.py` and follows the documented
cross-Python-version methodology — see the permanent note:

> `vault/02-Notes/Permanent/Persistent-subprocess-pool-bridges-a-pinned-python-version-blocker-but-threaded-dispatch-can-serialize-on-the-gil.md`

Rules most relevant to TTK:
- **Rule 2**: Interpreter path resolved cross-platform from `TTK_CONDA_PYTHON` (not bare `"python"`).
  `shared/ttk_utils.py` derives `_CONDA_EXECUTABLE` from `Path(TTK_CONDA_PYTHON).parents[2]` so
  conda is never assumed to be on PATH.
- **Rule 4**: Numerical correctness validated — persistence diagram round-trip + bottleneck distance
  invariant (`d(D, D) = 0`) confirmed against `ttk_env` subprocess.

## Environment Details

| Item | Value |
|------|-------|
| Conda env name | `ttk_env` |
| TTK version | 1.3.0 |
| Python in `ttk_env` | 3.11 |
| VTK in `ttk_env` | 9.3.20240617 |
| ParaView in `ttk_env` | 5.13.0 |
| Python in project `.venv` | 3.13 (do NOT change) |
| VTK in project `.venv` | 9.5.2 |
| `TTK_CONDA_PYTHON` (Windows) | `~/miniconda3/envs/ttk_env/python.exe` |
| `pvpython` location | `~/miniconda3/envs/ttk_env/Library/bin/pvpython.exe` |

## Installation

### 1. Create the conda environment

```bash
conda create -n ttk_env python=3.11 -y
```

### 2. Install TTK

```bash
conda install -n ttk_env -c conda-forge topologytoolkit -y
```

Installs TTK 1.3.0, ParaView 5.13.0 (bundled), VTK 9.3.x, NumPy.

### 3. Verify from the project venv

```powershell
# From project .venv (Python 3.13)
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

`ParaView Filters: ✗ Not Available` is **expected and correct** — `is_ttk_paraview_available()`
tests the conda-python interpreter path (the subprocess bridge); TTK filters via `paraview.simple`
require pvpython (see Interactive Use below).

## Usage

### Compute path (standard — from project venv)

```python
from shared.ttk_utils import is_ttk_available, run_ttk_subprocess

if not is_ttk_available():
    raise RuntimeError("TTK not available — see docs/TTK_SETUP.md")

code, stdout, stderr = run_ttk_subprocess(
    "my_ttk_script.py",
    args=["input.vtu", "output.json"],
    timeout=120,
)
```

### TTK script template (runs inside ttk_env)

```python
# my_ttk_script.py — executed by Python 3.11 in ttk_env, not the project 3.13 venv
import sys
import numpy as np
import vtk
from vtk.util import numpy_support
import topologytoolkit as ttk

def main(input_file, output_file):
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(input_file)
    reader.Update()
    data = reader.GetOutput()

    persistence = ttk.ttkPersistenceDiagram()
    persistence.SetInputData(data)
    persistence.SetInputArrayToProcess(0, 0, 0, 0, "ScalarField")
    persistence.Update()

    output = persistence.GetOutput()
    print(f"Pairs: {output.GetNumberOfPoints()}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
```

### Interactive use via pvpython

pvpython gives access to TTK filters through `paraview.simple` (the ParaView Python client API).
Requires the conda env to be activated:

```powershell
conda activate ttk_env
pvpython my_visualization_script.py
```

Or for a one-off:
```powershell
conda run -n ttk_env pvpython -c "from paraview.simple import TTKPersistenceDiagram; print('OK')"
```

**Note on pvpython PATH**: `pvpython.exe` lives at
`~/miniconda3/envs/ttk_env/Library/bin/pvpython.exe`. It is only on PATH when the env is
activated — do not rely on a manual User PATH entry, as conda's init script rebuilds PATH on shell
start and may override it. `conda activate ttk_env` is the correct method.

## Available TTK Filters

See [`docs/TTK_FILTER_VERIFICATION.md`](TTK_FILTER_VERIFICATION.md) for the full verification run.

**Core filters (verified working via subprocess bridge)**:

| Filter | Class | Notes |
|--------|-------|-------|
| Persistence diagram | `ttk.ttkPersistenceDiagram` | Standard usage |
| Bottleneck distance | `ttk.ttkBottleneckDistance` | See API note below |
| Morse–Smale complex | `ttk.ttkMorseSmaleComplex` | Smoke-tested on synthetic field; 9 critical points in ~1.3 s |
| Topological simplification | `ttk.ttkTopologicalSimplification` | Standard usage |

150+ additional filters available — see the [TTK documentation](https://topology-tool-kit.github.io/doc/html/index.html).

### ttkBottleneckDistance API (TTK 1.3.0)

The bottleneck distance filter has a non-obvious API. Incorrect usage silently false-passes or
segfaults. The correct pattern:

```python
import vtk
import topologytoolkit as ttk

# Input: vtkMultiBlockDataSet containing >=2 vtkUnstructuredGrid blocks (diagram outputs)
mbd = vtk.vtkMultiBlockDataSet()
mbd.SetBlock(0, persistence1.GetOutput())   # first diagram
mbd.SetBlock(1, persistence2.GetOutput())   # second diagram

# vtkTrivialProducer wraps a data object for pipeline input
producer = vtk.vtkTrivialProducer()
producer.SetOutput(mbd)
producer.Update()

bottleneck = ttk.ttkBottleneckDistance()
bottleneck.SetPVAlgorithm(0)                # 0 = TTK solver; values 1-4 print "Not supported"
bottleneck.SetInputConnection(0, producer.GetOutputPort())  # single input port only
bottleneck.Update()

distance = bottleneck.Getresult()           # scalar result; -1.0 = failure sentinel
# NOTE: GetOutput() returns None with PVAlgorithm=0 — use Getresult() for the distance value
```

**Empty diagram guard**: passing an empty persistence diagram to `ttkBottleneckDistance` causes a
segfault (not a Python exception). Always check `GetNumberOfPoints() > 0` on both diagrams before
calling the filter. The fixed smoke test in `tests/shared/ttk_filter_verification.py` demonstrates
this guard and asserts the numerical invariant `d(D, D) = 0`.

## Testing

### Quick check

```powershell
# Set UTF-8 output (avoids checkmark encoding error on Windows console)
$env:PYTHONIOENCODING = "utf-8"
python shared/ttk_utils.py
```

### Unit tests

```powershell
uv run pytest tests/shared/test_ttk_utils.py -v --ignore=TDL
```

Expected: 20 passed, 1 skipped.

### Filter verification (runs inside ttk_env subprocess)

```powershell
uv run python -c "
from shared.ttk_utils import run_ttk_subprocess
code, out, err = run_ttk_subprocess('tests/shared/ttk_filter_verification.py')
print(out)
if err: print('STDERR:', err)
"
```

## Troubleshooting

### `is_ttk_available()` returns False

```powershell
# Check env exists
conda env list | Select-String ttk_env

# Check TTK installed
conda list -n ttk_env | Select-String topologytoolkit

# Recreate if needed
conda remove -n ttk_env --all -y
conda create -n ttk_env python=3.11 -y
conda install -n ttk_env -c conda-forge topologytoolkit -y
```

### `UnicodeEncodeError` on `✓`/`✗` characters (Windows console)

```powershell
$env:PYTHONIOENCODING = "utf-8"
python shared/ttk_utils.py
```

### pvpython not found

```powershell
conda activate ttk_env
pvpython --version   # should print "paraview version 5.13.0"
```

If `conda activate` fails, run `conda init powershell` in an admin shell, then restart.

### Import errors in TTK subprocess

Use `import topologytoolkit as ttk` (not `from paraview.simple import ...`) in scripts that run
under `run_ttk_subprocess()`. The plain conda python does not expose TTK via `paraview.simple` —
that requires pvpython.

### Subprocess timeout

```python
run_ttk_subprocess("script.py", timeout=300)   # increase from default
```

## Alternative: Pre-built ParaView-TTK bundle (not used)

A pre-built `.exe` installer (`docs/ttk_installers/ttk-paraview-v5.13.0.exe`) was downloaded and
tested but discarded — runtime DLL loading errors on Windows. The conda approach is more reliable.

## References

- **TTK documentation**: https://topology-tool-kit.github.io/doc/html/index.html
- **Subprocess bridge methodology**: `vault/02-Notes/Permanent/Persistent-subprocess-pool-bridges-a-pinned-python-version-blocker-but-threaded-dispatch-can-serialize-on-the-gil.md`
- **Bridge implementation**: `shared/ttk_utils.py`
- **Filter smoke tests**: `tests/shared/ttk_filter_verification.py`
- **Higher-level utilities**: `shared/ttk_visualization/`
