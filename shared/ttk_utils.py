"""
TTK (Topology ToolKit) Availability Detection and Subprocess Utilities.

This module provides utilities to detect TTK availability and run TTK operations
in an isolated conda environment to avoid VTK version conflicts.

Pattern: Following poverty_tda/topology/morse_smale.py subprocess approach.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# TTK Environment Configuration
TTK_CONDA_ENV = "ttk_env"
TTK_CONDA_PYTHON = os.path.expanduser("~/miniconda3/envs/ttk_env/python.exe")
if sys.platform != "win32":
    TTK_CONDA_PYTHON = os.path.expanduser("~/miniconda3/envs/ttk_env/bin/python")


def is_ttk_available() -> bool:
    """
    Check if TTK Python bindings are available via conda environment.

    Returns:
        bool: True if TTK can be imported in conda environment.

    Examples:
        >>> if is_ttk_available():
        ...     result = run_ttk_subprocess("script.py", ["arg1"])
        ... else:
        ...     print("TTK not available, using fallback method")
    """
    if not Path(TTK_CONDA_PYTHON).exists():
        logger.debug(f"TTK conda python not found at {TTK_CONDA_PYTHON}")
        return False

    try:
        result = subprocess.run(
            [TTK_CONDA_PYTHON, "-c", "import topologytoolkit"],
            capture_output=True,
            timeout=5,
            text=True,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logger.debug(f"TTK availability check failed: {e}")
        return False


def is_ttk_paraview_available() -> bool:
    """
    Check if TTK ParaView filters are available in conda environment.

    Returns:
        bool: True if TTK ParaView filters can be imported.

    Note:
        This checks the conda environment's ParaView installation,
        not the standalone ParaView-TTK installation which has DLL issues.
    """
    if not Path(TTK_CONDA_PYTHON).exists():
        return False

    try:
        result = subprocess.run(
            [
                TTK_CONDA_PYTHON,
                "-c",
                "from paraview.simple import TTKPersistenceDiagram",
            ],
            capture_output=True,
            timeout=10,
            text=True,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logger.debug(f"TTK ParaView availability check failed: {e}")
        return False


def get_ttk_version() -> Optional[str]:
    """
    Get TTK version information from conda environment.

    Returns:
        Optional[str]: TTK version string, or None if unavailable.

    Examples:
        >>> version = get_ttk_version()
        >>> print(f"Using TTK {version}")
        Using TTK 1.3.0
    """
    if not Path(TTK_CONDA_PYTHON).exists():
        return None

    try:
        # TTK doesn't expose __version__, so get it from conda
        result = subprocess.run(
            ["conda", "list", "-n", TTK_CONDA_ENV, "topologytoolkit", "--json"],
            capture_output=True,
            timeout=5,
            text=True,
        )
        if result.returncode == 0:
            import json

            packages = json.loads(result.stdout)
            if packages:
                return packages[0].get("version", "unknown")
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as e:
        logger.debug(f"TTK version check failed: {e}")

    return None


def get_ttk_backend() -> Dict[str, Any]:
    """
    Get information about available TTK backend(s).

    Returns:
        Dict[str, Any]: Backend information including:
            - available (bool): Whether TTK is available
            - backend (str): Backend type ("conda_subprocess" or "none")
            - python_path (str): Path to TTK Python interpreter
            - vtk_version (str): VTK version in TTK environment
            - ttk_version (str): TTK version
            - paraview_filters (bool): Whether ParaView filters available

    Examples:
        >>> backend = get_ttk_backend()
        >>> if backend['available']:
        ...     print(f"TTK {backend['ttk_version']} available via {backend['backend']}")
        ... else:
        ...     print("TTK not available")
    """
    backend_info = {
        "available": False,
        "backend": "none",
        "python_path": None,
        "vtk_version": None,
        "ttk_version": None,
        "paraview_filters": False,
    }

    if not is_ttk_available():
        return backend_info

    backend_info["available"] = True
    backend_info["backend"] = "conda_subprocess"
    backend_info["python_path"] = TTK_CONDA_PYTHON
    backend_info["ttk_version"] = get_ttk_version()
    backend_info["paraview_filters"] = is_ttk_paraview_available()

    # Get VTK version
    try:
        result = subprocess.run(
            [
                TTK_CONDA_PYTHON,
                "-c",
                "import vtk; print(vtk.vtkVersion.GetVTKVersion())",
            ],
            capture_output=True,
            timeout=5,
            text=True,
        )
        if result.returncode == 0:
            backend_info["vtk_version"] = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return backend_info


def run_ttk_subprocess(
    script_path: str,
    args: Optional[list] = None,
    env_vars: Optional[Dict[str, str]] = None,
    timeout: int = 300,
) -> Tuple[int, str, str]:
    """
    Run a Python script in the TTK conda environment via subprocess.

    This is the primary method for running TTK operations while maintaining
    VTK version isolation from the main project environment.

    Args:
        script_path: Path to Python script to execute in TTK environment
        args: Optional list of command-line arguments for the script
        env_vars: Optional environment variables to set
        timeout: Timeout in seconds (default: 300)

    Returns:
        Tuple[int, str, str]: (return_code, stdout, stderr)

    Raises:
        FileNotFoundError: If TTK conda environment not found
        subprocess.TimeoutExpired: If execution exceeds timeout
        RuntimeError: If TTK is not available

    Examples:
        >>> # Run TTK persistence diagram computation
        >>> code, out, err = run_ttk_subprocess(
        ...     "compute_persistence.py",
        ...     args=["input.vtu", "output.json"],
        ...     timeout=60
        ... )
        >>> if code == 0:
        ...     print("TTK computation successful")
        ... else:
        ...     print(f"TTK error: {err}")
    """
    if not is_ttk_available():
        raise RuntimeError(
            f"TTK conda environment not available. "
            f"Expected at: {TTK_CONDA_PYTHON}\n"
            f"Install with: conda create -n {TTK_CONDA_ENV} python=3.11 && "
            f"conda install -n {TTK_CONDA_ENV} -c conda-forge topologytoolkit"
        )

    cmd = [TTK_CONDA_PYTHON, script_path]
    if args:
        cmd.extend(args)

    # Set up environment
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    logger.info(f"Running TTK subprocess: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)

        if result.returncode != 0:
            logger.warning(f"TTK subprocess returned non-zero: {result.returncode}")
            logger.warning(f"stderr: {result.stderr}")

        return result.returncode, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        logger.error(f"TTK subprocess timeout after {timeout}s")
        raise
    except FileNotFoundError:
        logger.error(f"TTK subprocess script not found: {script_path}")
        raise


def get_ttk_unavailable_message() -> str:
    """
    Get a helpful error message when TTK is not available.

    Returns:
        str: Installation instructions message.
    """
    return f"""
TTK (Topology ToolKit) is not available.

To install TTK:

1. Create conda environment:
   conda create -n {TTK_CONDA_ENV} python=3.11 -y

2. Install TTK from conda-forge:
   conda install -n {TTK_CONDA_ENV} -c conda-forge topologytoolkit -y

3. Verify installation:
   conda run -n {TTK_CONDA_ENV} python -c "import topologytoolkit; print('TTK OK')"

Expected TTK Python path: {TTK_CONDA_PYTHON}
Current availability: {is_ttk_available()}

For more information, see: docs/TTK_SETUP.md
"""


def check_ttk_status(verbose: bool = True) -> Dict[str, Any]:
    """
    Check and display TTK installation status.

    Args:
        verbose: If True, print status information

    Returns:
        Dict[str, Any]: Status information dictionary

    Examples:
        >>> status = check_ttk_status(verbose=True)
        TTK Status: ✓ Available
        Backend: conda_subprocess
        TTK Version: 1.3.0
        VTK Version: 9.3.20240617
        ParaView Filters: ✓ Available
    """
    backend = get_ttk_backend()

    if verbose:
        print("=" * 60)
        print("TTK Installation Status")
        print("=" * 60)

        if backend["available"]:
            print("TTK Status: ✓ Available")
            print(f"Backend: {backend['backend']}")
            print(f"Python Path: {backend['python_path']}")
            print(f"TTK Version: {backend['ttk_version']}")
            print(f"VTK Version: {backend['vtk_version']}")
            print(f"ParaView Filters: {'✓ Available' if backend['paraview_filters'] else '✗ Not Available'}")
        else:
            print("TTK Status: ✗ Not Available")
            print(get_ttk_unavailable_message())

        print("=" * 60)

    return backend


if __name__ == "__main__":
    # Command-line interface for checking TTK status
    check_ttk_status(verbose=True)
