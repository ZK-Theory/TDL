"""
Morse-Smale complex computation for mobility surfaces.

This module provides TTK-based Morse-Smale complex extraction from
mobility surfaces, enabling topological analysis of deprivation landscapes.

The Morse-Smale complex partitions a scalar field into regions of
uniform gradient flow, identifying:
- Critical points (minima, maxima, saddles)
- Ascending/descending manifolds
- Separatrices (gradient paths connecting saddles to extrema)

Integration:
    - mobility_surface.py: Provides VTK files via export_mobility_vtk()
    - shared.ttk_utils: Centralized TTK subprocess utilities and detection

TTK Environment:
    TTK operations run in isolated conda environment via shared.ttk_utils
    to avoid VTK version conflicts with the main project environment.

    See docs/TTK_SETUP.md for installation instructions.

License: Open Government Licence v3.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from shared.ttk_utils import is_ttk_available, run_ttk_subprocess

logger = logging.getLogger(__name__)

# Try to import pyvista for VTK file handling
try:
    import pyvista as pv

    HAS_PYVISTA = True
except ImportError:
    HAS_PYVISTA = False
    logger.debug("pyvista not installed - VTK loading limited")

# Try to import VTK directly
try:
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy

    HAS_VTK = True
except ImportError:
    HAS_VTK = False
    logger.debug("vtk not installed")

# Try to import TTK (only available in TTK conda environment)
try:
    from topologytoolkit.ttkMorseSmaleComplex import ttkMorseSmaleComplex

    HAS_TTK = True
except ImportError:
    HAS_TTK = False
    logger.debug(
        "TTK not available in current environment. " "TTK operations will run via subprocess in conda environment."
    )


# =============================================================================
# DATA CLASSES FOR RESULTS
# =============================================================================


@dataclass
class CriticalPoint:
    """A critical point in the Morse-Smale complex.

    TTK classifies critical points by their cell dimension (index):
    - For 2D surfaces: 0=minimum, 1=saddle, 2=maximum
    - For 3D volumes: 0=minimum, 1=1-saddle, 2=2-saddle, 3=maximum

    Attributes:
        point_id: Unique identifier for the point.
        position: (x, y, z) coordinates in the original CRS.
        value: Scalar field value at the critical point.
        point_type: TTK CellDimension value (0, 1, 2, or 3).
        manifold_dim: Dimension of the manifold (2 for surfaces, 3 for volumes).
            Used to interpret point_type correctly.
        cell_id: Cell ID in the original mesh (if applicable).
        persistence: Persistence value (lifetime) of the critical point pair.
    """

    point_id: int
    position: tuple[float, float, float]
    value: float
    point_type: int
    manifold_dim: int = 2  # Default to 2D surface
    cell_id: int | None = None
    persistence: float | None = None

    @property
    def type_name(self) -> str:
        """Human-readable name for the critical point type."""
        if self.manifold_dim == 2:
            # 2D surface: 0=min, 1=saddle, 2=max
            type_names = {0: "minimum", 1: "saddle", 2: "maximum"}
        else:
            # 3D volume: 0=min, 1=1-saddle, 2=2-saddle, 3=max
            type_names = {0: "minimum", 1: "1-saddle", 2: "2-saddle", 3: "maximum"}
        return type_names.get(self.point_type, f"unknown({self.point_type})")

    @property
    def is_minimum(self) -> bool:
        """Check if this is a local minimum."""
        return self.point_type == 0

    @property
    def is_maximum(self) -> bool:
        """Check if this is a local maximum."""
        # In 2D: type 2 is max; in 3D: type 3 is max
        if self.manifold_dim == 2:
            return self.point_type == 2
        return self.point_type == 3

    @property
    def is_saddle(self) -> bool:
        """Check if this is a saddle point."""
        # In 2D: type 1 is saddle; in 3D: types 1 and 2 are saddles
        if self.manifold_dim == 2:
            return self.point_type == 1
        return self.point_type in (1, 2)


@dataclass
class Separatrix:
    """A separatrix (gradient path) in the Morse-Smale complex.

    Attributes:
        separatrix_id: Unique identifier.
        source_id: ID of the source critical point.
        destination_id: ID of the destination critical point.
        separatrix_type: Type of separatrix:
            - 0: Descending 1-separatrix (saddle → minimum)
            - 1: Ascending 1-separatrix (saddle → maximum)
        points: Array of (x, y, z) coordinates along the path.
        values: Scalar values along the path.
    """

    separatrix_id: int
    source_id: int
    destination_id: int
    separatrix_type: int
    points: NDArray[np.float64] | None = None
    values: NDArray[np.float64] | None = None

    @property
    def type_name(self) -> str:
        """Human-readable name for the separatrix type."""
        type_names = {
            0: "descending",
            1: "ascending",
        }
        return type_names.get(self.separatrix_type, f"unknown({self.separatrix_type})")


@dataclass
class MorseSmaleResult:
    """Complete Morse-Smale complex computation result.

    Attributes:
        critical_points: List of all critical points.
        separatrices_1d: List of 1-separatrices (gradient paths).
        ascending_manifold: 2D array of ascending manifold IDs per cell.
        descending_manifold: 2D array of descending manifold IDs per cell.
        persistence_threshold: Persistence threshold used for simplification.
        scalar_range: (min, max) of the input scalar field.
        metadata: Additional metadata from computation.
    """

    critical_points: list[CriticalPoint] = field(default_factory=list)
    separatrices_1d: list[Separatrix] = field(default_factory=list)
    ascending_manifold: NDArray[np.int32] | None = None
    descending_manifold: NDArray[np.int32] | None = None
    persistence_threshold: float = 0.0
    scalar_range: tuple[float, float] = (0.0, 1.0)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def n_minima(self) -> int:
        """Count of local minima."""
        return sum(1 for cp in self.critical_points if cp.is_minimum)

    @property
    def n_maxima(self) -> int:
        """Count of local maxima."""
        return sum(1 for cp in self.critical_points if cp.is_maximum)

    @property
    def n_saddles(self) -> int:
        """Count of saddle points."""
        return sum(1 for cp in self.critical_points if cp.is_saddle)

    def get_minima(self) -> list[CriticalPoint]:
        """Get all local minima."""
        return [cp for cp in self.critical_points if cp.is_minimum]

    def get_maxima(self) -> list[CriticalPoint]:
        """Get all local maxima."""
        return [cp for cp in self.critical_points if cp.is_maximum]

    def get_saddles(self) -> list[CriticalPoint]:
        """Get all saddle points."""
        return [cp for cp in self.critical_points if cp.is_saddle]


# =============================================================================
# VTK DATA LOADING
# =============================================================================


def load_vtk_data(
    vtk_path: Path | str,
) -> Any:
    """
    Load VTK file (.vti, .vts, .vtk, .vtp) for Morse-Smale analysis.

    Supports VTK ImageData, StructuredGrid, and PolyData formats
    produced by the mobility_surface module.

    Args:
        vtk_path: Path to the VTK file.

    Returns:
        VTK data object (pyvista mesh or vtk.vtkDataSet).

    Raises:
        FileNotFoundError: If the VTK file doesn't exist.
        ValueError: If the file format is not supported.
        ImportError: If neither pyvista nor vtk is available.

    Example:
        >>> vtk_data = load_vtk_data("mobility.vti")
        >>> print(vtk_data.n_points)
        250000
    """
    vtk_path = Path(vtk_path)

    if not vtk_path.exists():
        raise FileNotFoundError(f"VTK file not found: {vtk_path}")

    suffix = vtk_path.suffix.lower()
    supported_formats = {".vti", ".vts", ".vtk", ".vtp"}

    if suffix not in supported_formats:
        raise ValueError(f"Unsupported VTK format: {suffix}. Supported formats: {supported_formats}")

    logger.info(f"Loading VTK file: {vtk_path}")

    if HAS_PYVISTA:
        # Use pyvista for convenient loading
        mesh = pv.read(str(vtk_path))
        logger.info(
            f"Loaded VTK data: {mesh.n_points} points, " f"{mesh.n_cells} cells, arrays: {list(mesh.point_data.keys())}"
        )
        return mesh

    elif HAS_VTK:
        # Use direct VTK readers
        reader = _get_vtk_reader(suffix)
        reader.SetFileName(str(vtk_path))
        reader.Update()
        output = reader.GetOutput()
        logger.info(f"Loaded VTK data: {output.GetNumberOfPoints()} points")
        return output

    else:
        raise ImportError("Neither pyvista nor vtk is available. Install with: pip install pyvista")


def _get_vtk_reader(suffix: str) -> Any:
    """Get appropriate VTK reader for file extension."""
    if not HAS_VTK:
        raise ImportError("VTK not available")

    readers = {
        ".vti": vtk.vtkXMLImageDataReader,
        ".vts": vtk.vtkXMLStructuredGridReader,
        ".vtp": vtk.vtkXMLPolyDataReader,
        ".vtk": vtk.vtkDataSetReader,
    }

    reader_class = readers.get(suffix)
    if reader_class is None:
        raise ValueError(f"No reader for format: {suffix}")

    return reader_class()


def validate_scalar_field(
    vtk_data: Any,
    scalar_name: str,
) -> tuple[float, float]:
    """
    Validate that a scalar field exists and return its range.

    Args:
        vtk_data: VTK data object (pyvista mesh or vtk.vtkDataSet).
        scalar_name: Name of the scalar field to validate.

    Returns:
        Tuple of (min_value, max_value) for the scalar field.

    Raises:
        ValueError: If the scalar field doesn't exist or has no valid values.

    Example:
        >>> vtk_data = load_vtk_data("mobility.vti")
        >>> vmin, vmax = validate_scalar_field(vtk_data, "mobility")
        >>> print(f"Scalar range: [{vmin:.3f}, {vmax:.3f}]")
    """
    if HAS_PYVISTA and isinstance(vtk_data, pv.DataSet):
        # pyvista mesh
        if scalar_name not in vtk_data.point_data:
            available = list(vtk_data.point_data.keys())
            raise ValueError(f"Scalar field '{scalar_name}' not found. Available fields: {available}")

        values = vtk_data.point_data[scalar_name]
        valid_values = values[~np.isnan(values)]

        if len(valid_values) == 0:
            raise ValueError(f"Scalar field '{scalar_name}' contains only NaN values")

        return float(valid_values.min()), float(valid_values.max())

    elif HAS_VTK:
        # Direct VTK object
        point_data = vtk_data.GetPointData()
        array = point_data.GetArray(scalar_name)

        if array is None:
            available = [point_data.GetArrayName(i) for i in range(point_data.GetNumberOfArrays())]
            raise ValueError(f"Scalar field '{scalar_name}' not found. Available fields: {available}")

        values = vtk_to_numpy(array)
        valid_values = values[~np.isnan(values)]

        if len(valid_values) == 0:
            raise ValueError(f"Scalar field '{scalar_name}' contains only NaN values")

        return float(valid_values.min()), float(valid_values.max())

    else:
        raise ImportError("Neither pyvista nor vtk is available")


def get_scalar_array(
    vtk_data: Any,
    scalar_name: str,
) -> NDArray[np.float64]:
    """
    Extract scalar array from VTK data as numpy array.

    Args:
        vtk_data: VTK data object.
        scalar_name: Name of the scalar field.

    Returns:
        1D numpy array of scalar values.

    Raises:
        ValueError: If scalar field doesn't exist.
    """
    if HAS_PYVISTA and isinstance(vtk_data, pv.DataSet):
        if scalar_name not in vtk_data.point_data:
            raise ValueError(f"Scalar field '{scalar_name}' not found")
        return np.asarray(vtk_data.point_data[scalar_name], dtype=np.float64)

    elif HAS_VTK:
        point_data = vtk_data.GetPointData()
        array = point_data.GetArray(scalar_name)
        if array is None:
            raise ValueError(f"Scalar field '{scalar_name}' not found")
        return vtk_to_numpy(array).astype(np.float64)

    else:
        raise ImportError("Neither pyvista nor vtk is available")


def vtk_to_numpy_points(vtk_data: Any) -> NDArray[np.float64]:
    """
    Extract point coordinates from VTK data as numpy array.

    Args:
        vtk_data: VTK data object.

    Returns:
        (N, 3) array of point coordinates.
    """
    if HAS_PYVISTA and isinstance(vtk_data, pv.DataSet):
        return np.asarray(vtk_data.points, dtype=np.float64)

    elif HAS_VTK:
        points = vtk_data.GetPoints()
        return vtk_to_numpy(points.GetData()).astype(np.float64)

    else:
        raise ImportError("Neither pyvista nor vtk is available")


# =============================================================================
# TTK ENVIRONMENT UTILITIES
# =============================================================================


def check_ttk_available() -> bool:
    """
    Check if TTK is available in the current Python environment.

    Returns:
        True if TTK can be imported, False otherwise.

    Note:
        This checks the CURRENT environment. For subprocess availability,
        use is_ttk_available() from shared.ttk_utils.
    """
    return HAS_TTK


def check_ttk_environment() -> bool:
    """
    Check if the TTK conda environment exists and is functional.

    Returns:
        True if TTK environment is available and working via subprocess.

    Note:
        This uses centralized TTK detection from shared.ttk_utils.
    """
    return is_ttk_available()


# =============================================================================
# TTK COMPUTATION SCRIPT (for subprocess execution)
# =============================================================================

# This script is executed in the TTK conda environment via subprocess
TTK_COMPUTE_SCRIPT = '''
"""TTK Morse-Smale computation script - runs in TTK conda environment."""
import json
import sys
from pathlib import Path

import numpy as np

# Import VTK and TTK
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from topologytoolkit.ttkMorseSmaleComplex import ttkMorseSmaleComplex


def load_vtk_file(vtk_path: str):
    """Load VTK file using appropriate reader."""
    path = Path(vtk_path)
    suffix = path.suffix.lower()

    readers = {
        ".vti": vtk.vtkXMLImageDataReader,
        ".vts": vtk.vtkXMLStructuredGridReader,
        ".vtp": vtk.vtkXMLPolyDataReader,
        ".vtk": vtk.vtkDataSetReader,
    }

    reader_class = readers.get(suffix)
    if reader_class is None:
        raise ValueError(f"Unsupported format: {suffix}")

    reader = reader_class()
    reader.SetFileName(vtk_path)
    reader.Update()
    return reader.GetOutput()


def compute_morse_smale_ttk(
    vtk_path: str,
    scalar_name: str,
    persistence_threshold: float,
    compute_ascending: bool,
    compute_descending: bool,
    compute_separatrices: bool,
):
    """Compute Morse-Smale complex using TTK."""
    # Load VTK data
    vtk_data = load_vtk_file(vtk_path)

    # Get scalar range
    point_data = vtk_data.GetPointData()
    scalar_array = point_data.GetArray(scalar_name)
    if scalar_array is None:
        available = [
            point_data.GetArrayName(i)
            for i in range(point_data.GetNumberOfArrays())
        ]
        raise ValueError(f"Scalar '{scalar_name}' not found. Available: {available}")

    scalars = vtk_to_numpy(scalar_array)
    scalar_min, scalar_max = float(scalars.min()), float(scalars.max())
    scalar_range = scalar_max - scalar_min

    # Set active scalars
    point_data.SetActiveScalars(scalar_name)

    # Compute absolute persistence threshold
    abs_threshold = persistence_threshold * scalar_range

    # Create and configure Morse-Smale filter
    ms_filter = ttkMorseSmaleComplex()
    ms_filter.SetInputData(vtk_data)
    ms_filter.SetInputArrayToProcess(0, 0, 0, 0, scalar_name)

    # Configure outputs
    ms_filter.SetComputeCriticalPoints(True)
    ms_filter.SetComputeAscendingSeparatrices1(compute_separatrices)
    ms_filter.SetComputeDescendingSeparatrices1(compute_separatrices)
    ms_filter.SetComputeAscendingSegmentation(compute_ascending)
    ms_filter.SetComputeDescendingSegmentation(compute_descending)

    # Set persistence threshold
    ms_filter.SetSaddleConnectorsPersistenceThreshold(abs_threshold)
    ms_filter.SetThresholdIsAbsolute(True)

    # Compute
    ms_filter.Update()

    # Extract results
    result = {
        "critical_points": [],
        "separatrices": [],
        "scalar_range": (scalar_min, scalar_max),
        "persistence_threshold": persistence_threshold,
        "abs_threshold": abs_threshold,
    }

    # Port 0: Critical Points
    critical_points_output = ms_filter.GetOutput(0)
    if critical_points_output:
        n_points = critical_points_output.GetNumberOfPoints()
        cp_data = critical_points_output.GetPointData()

        # Get critical type array
        type_array = cp_data.GetArray("CellDimension")
        value_array = cp_data.GetArray(scalar_name)

        for i in range(n_points):
            pos = critical_points_output.GetPoint(i)
            cp_type = int(type_array.GetValue(i)) if type_array else -1
            value = float(value_array.GetValue(i)) if value_array else 0.0

            result["critical_points"].append({
                "point_id": i,
                "position": [pos[0], pos[1], pos[2]],
                "value": value,
                "point_type": cp_type,
            })

    # Port 1: 1-Separatrices
    if compute_separatrices:
        separatrices_output = ms_filter.GetOutput(1)
        if separatrices_output and separatrices_output.GetNumberOfCells() > 0:
            sep_data = separatrices_output.GetCellData()
            sep_id_array = sep_data.GetArray("SeparatrixId")
            sep_type_array = sep_data.GetArray("SeparatrixType")
            source_array = sep_data.GetArray("SourceId")
            dest_array = sep_data.GetArray("DestinationId")

            # Group cells by separatrix ID
            sep_dict = {}
            for i in range(separatrices_output.GetNumberOfCells()):
                sep_id = int(sep_id_array.GetValue(i)) if sep_id_array else i
                if sep_id not in sep_dict:
                    sep_type = (
                        int(sep_type_array.GetValue(i)) if sep_type_array else 0
                    )
                    src_id = int(source_array.GetValue(i)) if source_array else -1
                    dst_id = int(dest_array.GetValue(i)) if dest_array else -1
                    sep_dict[sep_id] = {
                        "separatrix_id": sep_id,
                        "separatrix_type": sep_type,
                        "source_id": src_id,
                        "destination_id": dst_id,
                    }

            result["separatrices"] = list(sep_dict.values())

    # Port 3: Segmentation (manifolds)
    segmentation_output = ms_filter.GetOutput(3)
    if segmentation_output:
        seg_data = segmentation_output.GetPointData()

        if compute_ascending:
            asc_array = seg_data.GetArray("AscendingManifold")
            if asc_array:
                result["ascending_manifold"] = vtk_to_numpy(asc_array).tolist()

        if compute_descending:
            desc_array = seg_data.GetArray("DescendingManifold")
            if desc_array:
                result["descending_manifold"] = vtk_to_numpy(desc_array).tolist()

    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--vtk-path", required=True)
    parser.add_argument("--scalar-name", default="mobility")
    parser.add_argument("--persistence-threshold", type=float, default=0.05)
    parser.add_argument("--compute-ascending", type=int, default=1)
    parser.add_argument("--compute-descending", type=int, default=1)
    parser.add_argument("--compute-separatrices", type=int, default=1)
    parser.add_argument("--output-json", required=True)

    args = parser.parse_args()

    try:
        result = compute_morse_smale_ttk(
            args.vtk_path,
            args.scalar_name,
            args.persistence_threshold,
            bool(args.compute_ascending),
            bool(args.compute_descending),
            bool(args.compute_separatrices),
        )

        with open(args.output_json, "w") as f:
            json.dump(result, f)

        print("SUCCESS")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
'''


# =============================================================================
# MORSE-SMALE COMPUTATION
# =============================================================================


def _run_ttk_subprocess(
    vtk_path: Path,
    scalar_name: str,
    persistence_threshold: float,
    compute_ascending: bool,
    compute_descending: bool,
    compute_separatrices: bool,
) -> dict[str, Any]:
    """
    Run TTK computation in the TTK conda environment via subprocess.

    Uses centralized subprocess utilities from shared.ttk_utils for
    consistent error handling and environment management.

    Args:
        vtk_path: Path to VTK file.
        scalar_name: Scalar field name.
        persistence_threshold: Persistence threshold (fraction of range).
        compute_ascending: Compute ascending manifolds.
        compute_descending: Compute descending manifolds.
        compute_separatrices: Compute 1-separatrices.

    Returns:
        Dictionary with computation results.

    Raises:
        RuntimeError: If TTK computation fails or is unavailable.
    """
    import json
    import tempfile

    # Check TTK availability using centralized utilities
    if not is_ttk_available():
        from shared.ttk_utils import get_ttk_unavailable_message

        raise RuntimeError(get_ttk_unavailable_message())

    # Create temporary files for script and output
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as script_file:
        script_file.write(TTK_COMPUTE_SCRIPT)
        script_path = Path(script_file.name)

    output_json = Path(tempfile.mktemp(suffix=".json"))

    try:
        # Prepare script arguments
        args = [
            "--vtk-path",
            str(vtk_path),
            "--scalar-name",
            scalar_name,
            "--persistence-threshold",
            str(persistence_threshold),
            "--compute-ascending",
            str(int(compute_ascending)),
            "--compute-descending",
            str(int(compute_descending)),
            "--compute-separatrices",
            str(int(compute_separatrices)),
            "--output-json",
            str(output_json),
        ]

        logger.info("Running TTK Morse-Smale computation via subprocess...")

        # Use centralized TTK subprocess utility
        returncode, stdout, stderr = run_ttk_subprocess(
            str(script_path),
            args=args,
            timeout=300,  # 5 minute timeout
        )

        if returncode != 0:
            raise RuntimeError(
                f"TTK computation failed (exit code {returncode}):\n" f"stderr: {stderr}\n" f"stdout: {stdout}"
            )

        if not output_json.exists():
            raise RuntimeError(f"TTK computation produced no output file.\n" f"stdout: {stdout}\n" f"stderr: {stderr}")

        with open(output_json) as f:
            return json.load(f)

    finally:
        # Cleanup temporary files
        script_path.unlink(missing_ok=True)
        output_json.unlink(missing_ok=True)


def _run_ttk_native(
    vtk_path: Path,
    scalar_name: str,
    persistence_threshold: float,
    compute_ascending: bool,
    compute_descending: bool,
    compute_separatrices: bool,
) -> dict[str, Any]:
    """
    Run TTK computation natively (when running in TTK environment).

    This is used when the code is executed directly in the TTK conda
    environment, avoiding subprocess overhead.
    """
    if not HAS_TTK:
        raise RuntimeError("TTK not available in current environment")

    # Load VTK data
    vtk_data = load_vtk_data(vtk_path)

    # Get scalar range
    scalar_min, scalar_max = validate_scalar_field(vtk_data, scalar_name)
    scalar_range = scalar_max - scalar_min
    abs_threshold = persistence_threshold * scalar_range

    # Convert pyvista to VTK if needed
    if HAS_PYVISTA and isinstance(vtk_data, pv.DataSet):
        vtk_data = vtk_data.cast_to_unstructured_grid()

    # Set active scalars
    vtk_data.GetPointData().SetActiveScalars(scalar_name)

    # Create and configure Morse-Smale filter
    ms_filter = ttkMorseSmaleComplex()
    ms_filter.SetInputData(vtk_data)
    ms_filter.SetInputArrayToProcess(0, 0, 0, 0, scalar_name)

    # Configure outputs
    ms_filter.SetComputeCriticalPoints(True)
    ms_filter.SetComputeAscendingSeparatrices1(compute_separatrices)
    ms_filter.SetComputeDescendingSeparatrices1(compute_separatrices)
    ms_filter.SetComputeAscendingSegmentation(compute_ascending)
    ms_filter.SetComputeDescendingSegmentation(compute_descending)

    # Set persistence threshold
    ms_filter.SetSaddleConnectorsPersistenceThreshold(abs_threshold)
    ms_filter.SetThresholdIsAbsolute(True)

    # Compute
    logger.info(f"Computing Morse-Smale complex (persistence={persistence_threshold:.2%})...")
    ms_filter.Update()

    # Extract results
    result: dict[str, Any] = {
        "critical_points": [],
        "separatrices": [],
        "scalar_range": (scalar_min, scalar_max),
        "persistence_threshold": persistence_threshold,
        "abs_threshold": abs_threshold,
    }

    # Port 0: Critical Points
    critical_points_output = ms_filter.GetOutput(0)
    if critical_points_output:
        n_points = critical_points_output.GetNumberOfPoints()
        cp_data = critical_points_output.GetPointData()

        type_array = cp_data.GetArray("CellDimension")
        value_array = cp_data.GetArray(scalar_name)

        for i in range(n_points):
            pos = critical_points_output.GetPoint(i)
            cp_type = int(type_array.GetValue(i)) if type_array else -1
            value = float(value_array.GetValue(i)) if value_array else 0.0

            result["critical_points"].append(
                {
                    "point_id": i,
                    "position": [pos[0], pos[1], pos[2]],
                    "value": value,
                    "point_type": cp_type,
                }
            )

    # Port 1: 1-Separatrices
    if compute_separatrices:
        separatrices_output = ms_filter.GetOutput(1)
        if separatrices_output and separatrices_output.GetNumberOfCells() > 0:
            sep_data = separatrices_output.GetCellData()
            sep_id_array = sep_data.GetArray("SeparatrixId")
            sep_type_array = sep_data.GetArray("SeparatrixType")
            source_array = sep_data.GetArray("SourceId")
            dest_array = sep_data.GetArray("DestinationId")

            sep_dict: dict[int, dict[str, Any]] = {}
            for i in range(separatrices_output.GetNumberOfCells()):
                sep_id = int(sep_id_array.GetValue(i)) if sep_id_array else i
                if sep_id not in sep_dict:
                    sep_type = int(sep_type_array.GetValue(i)) if sep_type_array else 0
                    src_id = int(source_array.GetValue(i)) if source_array else -1
                    dst_id = int(dest_array.GetValue(i)) if dest_array else -1
                    sep_dict[sep_id] = {
                        "separatrix_id": sep_id,
                        "separatrix_type": sep_type,
                        "source_id": src_id,
                        "destination_id": dst_id,
                    }

            result["separatrices"] = list(sep_dict.values())

    # Port 3: Segmentation
    segmentation_output = ms_filter.GetOutput(3)
    if segmentation_output:
        seg_data = segmentation_output.GetPointData()

        if compute_ascending:
            asc_array = seg_data.GetArray("AscendingManifold")
            if asc_array:
                result["ascending_manifold"] = vtk_to_numpy(asc_array).tolist()

        if compute_descending:
            desc_array = seg_data.GetArray("DescendingManifold")
            if desc_array:
                result["descending_manifold"] = vtk_to_numpy(desc_array).tolist()

    return result


def _parse_ttk_result(
    raw_result: dict[str, Any],
    manifold_dim: int = 2,
) -> MorseSmaleResult:
    """Convert raw TTK output dictionary to MorseSmaleResult.

    Args:
        raw_result: Dictionary from TTK computation.
        manifold_dim: Dimension of the manifold (2 for surfaces, 3 for volumes).
            Used to correctly interpret critical point types.
    """
    # Parse critical points
    critical_points = [
        CriticalPoint(
            point_id=cp["point_id"],
            position=tuple(cp["position"]),
            value=cp["value"],
            point_type=cp["point_type"],
            manifold_dim=manifold_dim,
        )
        for cp in raw_result.get("critical_points", [])
    ]

    # Parse separatrices
    separatrices = [
        Separatrix(
            separatrix_id=sep["separatrix_id"],
            source_id=sep["source_id"],
            destination_id=sep["destination_id"],
            separatrix_type=sep["separatrix_type"],
        )
        for sep in raw_result.get("separatrices", [])
    ]

    # Parse manifolds
    ascending = None
    if "ascending_manifold" in raw_result:
        ascending = np.array(raw_result["ascending_manifold"], dtype=np.int32)

    descending = None
    if "descending_manifold" in raw_result:
        descending = np.array(raw_result["descending_manifold"], dtype=np.int32)

    return MorseSmaleResult(
        critical_points=critical_points,
        separatrices_1d=separatrices,
        ascending_manifold=ascending,
        descending_manifold=descending,
        persistence_threshold=raw_result.get("persistence_threshold", 0.0),
        scalar_range=tuple(raw_result.get("scalar_range", (0.0, 1.0))),
        metadata={
            "abs_threshold": raw_result.get("abs_threshold", 0.0),
            "manifold_dim": manifold_dim,
        },
    )


# =============================================================================
# TOPOLOGICAL SIMPLIFICATION
# =============================================================================


def simplify_scalar_field(
    vtk_path: Path | str,
    persistence_threshold: float,
    scalar_name: str = "mobility",
    output_path: Path | str | None = None,
) -> Path:
    """
    Simplify a scalar field by removing low-persistence topological noise.

    Uses TTK's topological simplification filter to remove critical point pairs
    with persistence below the threshold, effectively denoising the scalar field
    while preserving significant topological features.

    Args:
        vtk_path: Path to input VTK file containing scalar field
        persistence_threshold: Persistence threshold as fraction of scalar range.
            Features with persistence below this are removed.
            Recommended starting value: 0.05 (5% of scalar range).
            Range: 0.0 to 1.0.
        scalar_name: Name of scalar field to simplify (default "mobility")
        output_path: Optional path for simplified VTK file.
            If None, creates temporary file with "_simplified" suffix.

    Returns:
        Path to simplified VTK file

    Raises:
        FileNotFoundError: If input VTK file doesn't exist
        ValueError: If scalar field doesn't exist or threshold invalid
        RuntimeError: If TTK simplification fails or TTK unavailable

    Example:
        >>> # Remove low-persistence noise before Morse-Smale extraction
        >>> simplified = simplify_scalar_field(
        ...     "mobility.vti",
        ...     persistence_threshold=0.05,
        ...     scalar_name="mobility"
        ... )
        >>> result = compute_morse_smale(simplified, persistence_threshold=0.0)

    Notes:
        Persistence Threshold Recommendations (from Task 6.5.1 findings):
        - 5% (0.05): Good starting point, removes minor noise
        - 1% (0.01): Conservative, preserves more features
        - 10% (0.10): Aggressive, keeps only major features

        The threshold is relative to the scalar range. For a field with
        range [0.2, 0.8] (range=0.6), threshold=0.05 means absolute
        threshold of 0.03.
    """
    import tempfile

    vtk_path = Path(vtk_path)

    if not vtk_path.exists():
        raise FileNotFoundError(f"VTK file not found: {vtk_path}")

    # Validate persistence threshold
    if not 0.0 <= persistence_threshold <= 1.0:
        raise ValueError(f"persistence_threshold must be in [0, 1], got {persistence_threshold}")

    # Check TTK availability
    if not is_ttk_available():
        from shared.ttk_utils import get_ttk_unavailable_message

        raise RuntimeError(get_ttk_unavailable_message())

    # Validate scalar field and get range
    vtk_data = load_vtk_data(vtk_path)
    scalar_min, scalar_max = validate_scalar_field(vtk_data, scalar_name)
    scalar_range = scalar_max - scalar_min

    if scalar_range <= 0:
        raise ValueError(f"Invalid scalar range [{scalar_min}, {scalar_max}]. " "Cannot simplify constant field.")

    # Compute absolute threshold
    abs_threshold = persistence_threshold * scalar_range

    # Prepare output path
    if output_path is None:
        # Create temporary file with same extension
        suffix = vtk_path.suffix
        with tempfile.NamedTemporaryFile(mode="w", suffix=f"_simplified{suffix}", delete=False) as tmp:
            output_path = Path(tmp.name)
    else:
        output_path = Path(output_path)

    # Get TTK simplification script path
    script_path = Path(__file__).parent / "ttk_scripts" / "simplify_scalar_field.py"

    if not script_path.exists():
        raise FileNotFoundError(
            f"TTK simplification script not found: {script_path}\n"
            "Expected location: poverty_tda/topology/ttk_scripts/simplify_scalar_field.py"
        )

    # Prepare subprocess arguments
    args = [
        "--input",
        str(vtk_path),
        "--output",
        str(output_path),
        "--scalar-name",
        scalar_name,
        "--persistence-threshold",
        str(abs_threshold),
    ]

    logger.info(
        f"Simplifying scalar field '{scalar_name}' " f"(threshold={persistence_threshold:.2%} = {abs_threshold:.4f})..."
    )

    # Run TTK simplification via subprocess
    returncode, stdout, stderr = run_ttk_subprocess(str(script_path), args=args, timeout=300)

    if returncode != 0:
        raise RuntimeError(
            f"TTK simplification failed (exit code {returncode}):\n" f"stderr: {stderr}\n" f"stdout: {stdout}"
        )

    if not output_path.exists():
        raise RuntimeError(f"TTK simplification produced no output file.\n" f"stdout: {stdout}\n" f"stderr: {stderr}")

    logger.info(f"Scalar field simplified: {output_path}")

    return output_path


def compute_morse_smale(
    vtk_path: Path | str,
    scalar_name: str = "mobility",
    persistence_threshold: float = 0.05,
    compute_ascending: bool = True,
    compute_descending: bool = True,
    compute_separatrices: bool = True,
) -> MorseSmaleResult:
    """
    Compute Morse-Smale complex for a mobility surface.

    Uses TTK (Topology ToolKit) to compute the Morse-Smale complex,
    extracting critical points, separatrices, and manifold segmentation.

    The function automatically detects whether TTK is available in the
    current environment. If not, it uses subprocess to call the TTK
    conda environment.

    Args:
        vtk_path: Path to the VTK file containing the mobility surface.
            Supports .vti (ImageData), .vts (StructuredGrid), .vtp (PolyData).
        scalar_name: Name of the scalar field to analyze (default "mobility").
        persistence_threshold: Persistence threshold as fraction of scalar range.
            Features with persistence below this threshold are simplified.
            Default 0.05 (5% of range). Range: 0.0 to 1.0.
        compute_ascending: Whether to compute ascending manifolds.
        compute_descending: Whether to compute descending manifolds.
        compute_separatrices: Whether to compute 1-separatrices.

    Returns:
        MorseSmaleResult containing:
        - critical_points: List of CriticalPoint objects
        - separatrices_1d: List of Separatrix objects
        - ascending_manifold: Array of manifold IDs per point
        - descending_manifold: Array of manifold IDs per point

    Raises:
        FileNotFoundError: If VTK file doesn't exist.
        ValueError: If scalar field doesn't exist or is invalid.
        RuntimeError: If TTK computation fails.

    Example:
        >>> result = compute_morse_smale("mobility.vti", persistence_threshold=0.05)
        >>> print(f"Found {result.n_maxima} maxima, {result.n_saddles} saddles")
        Found 12 maxima, 23 saddles

        >>> for cp in result.get_maxima():
        ...     print(f"Maximum at {cp.position[:2]}, value={cp.value:.3f}")
    """
    vtk_path = Path(vtk_path)

    if not vtk_path.exists():
        raise FileNotFoundError(f"VTK file not found: {vtk_path}")

    # Validate persistence threshold
    if not 0.0 <= persistence_threshold <= 1.0:
        raise ValueError(f"persistence_threshold must be in [0, 1], got {persistence_threshold}")

    # Validate scalar field exists (also loads data for quick check)
    vtk_data = load_vtk_data(vtk_path)
    scalar_min, scalar_max = validate_scalar_field(vtk_data, scalar_name)
    logger.info(f"Scalar field '{scalar_name}': range [{scalar_min:.4f}, {scalar_max:.4f}]")

    # Choose computation method based on environment
    if HAS_TTK:
        logger.info("Using native TTK computation")
        raw_result = _run_ttk_native(
            vtk_path,
            scalar_name,
            persistence_threshold,
            compute_ascending,
            compute_descending,
            compute_separatrices,
        )
    else:
        logger.info("Using TTK subprocess (conda environment)")
        raw_result = _run_ttk_subprocess(
            vtk_path,
            scalar_name,
            persistence_threshold,
            compute_ascending,
            compute_descending,
            compute_separatrices,
        )

    # Parse and return result
    result = _parse_ttk_result(raw_result)

    logger.info(
        f"Morse-Smale complex: {result.n_minima} minima, "
        f"{result.n_saddles} saddles, {result.n_maxima} maxima, "
        f"{len(result.separatrices_1d)} separatrices"
    )

    return result


# =============================================================================
# TOPOLOGICAL SIMPLIFICATION
# =============================================================================


@dataclass
class PersistencePair:
    """A persistence pair representing a topological feature.

    In Morse theory, critical points are paired based on their topological
    connection. The persistence of a pair is the absolute difference in
    scalar values between the two critical points.

    Attributes:
        birth_id: ID of the critical point where the feature is born.
        death_id: ID of the critical point where the feature dies.
        birth_value: Scalar value at birth.
        death_value: Scalar value at death.
        persistence: Absolute difference |death_value - birth_value|.
        feature_type: Type of topological feature:
            - "min-saddle": Minimum paired with saddle
            - "saddle-max": Saddle paired with maximum
    """

    birth_id: int
    death_id: int
    birth_value: float
    death_value: float
    persistence: float
    feature_type: str

    @property
    def relative_persistence(self) -> float:
        """Persistence relative to scalar range (requires external range)."""
        # This is set externally after creation
        return getattr(self, "_relative_persistence", self.persistence)


def compute_persistence_pairs(
    result: MorseSmaleResult,
) -> list[PersistencePair]:
    """
    Compute persistence pairs from Morse-Smale complex.

    Pairs critical points based on the separatrices connecting them.
    Each pair represents a topological feature with a lifetime (persistence).

    Args:
        result: MorseSmaleResult from compute_morse_smale.

    Returns:
        List of PersistencePair objects sorted by persistence (ascending).

    Example:
        >>> result = compute_morse_smale("mobility.vti")
        >>> pairs = compute_persistence_pairs(result)
        >>> for p in pairs[:5]:
        ...     print(f"{p.feature_type}: persistence={p.persistence:.4f}")
    """
    pairs: list[PersistencePair] = []

    # Use separatrices to identify connected pairs
    # Each separatrix connects a saddle to an extremum
    saddle_connections: dict[int, list[int]] = {}

    for sep in result.separatrices_1d:
        source_id = sep.source_id
        dest_id = sep.destination_id

        if source_id not in saddle_connections:
            saddle_connections[source_id] = []
        saddle_connections[source_id].append(dest_id)

        if dest_id not in saddle_connections:
            saddle_connections[dest_id] = []
        saddle_connections[dest_id].append(source_id)

    # For each saddle, find the closest extremum to pair with
    saddles = result.get_saddles()
    minima = result.get_minima()
    maxima = result.get_maxima()

    # Create min-saddle pairs
    for saddle in saddles:
        # Find closest minimum by value difference
        closest_min = None
        min_diff = float("inf")

        for m in minima:
            diff = abs(saddle.value - m.value)
            if diff < min_diff:
                min_diff = diff
                closest_min = m

        if closest_min is not None:
            pairs.append(
                PersistencePair(
                    birth_id=closest_min.point_id,
                    death_id=saddle.point_id,
                    birth_value=closest_min.value,
                    death_value=saddle.value,
                    persistence=abs(saddle.value - closest_min.value),
                    feature_type="min-saddle",
                )
            )

    # Create saddle-max pairs
    for saddle in saddles:
        # Find closest maximum by value difference
        closest_max = None
        min_diff = float("inf")

        for m in maxima:
            diff = abs(m.value - saddle.value)
            if diff < min_diff:
                min_diff = diff
                closest_max = m

        if closest_max is not None:
            pairs.append(
                PersistencePair(
                    birth_id=saddle.point_id,
                    death_id=closest_max.point_id,
                    birth_value=saddle.value,
                    death_value=closest_max.value,
                    persistence=abs(closest_max.value - saddle.value),
                    feature_type="saddle-max",
                )
            )

    # Sort by persistence (ascending - lowest first)
    pairs.sort(key=lambda p: p.persistence)

    # Compute relative persistence
    scalar_range = result.scalar_range[1] - result.scalar_range[0]
    if scalar_range > 0:
        for p in pairs:
            p._relative_persistence = p.persistence / scalar_range

    logger.debug(f"Computed {len(pairs)} persistence pairs")
    return pairs


def simplify_topology(
    result: MorseSmaleResult,
    persistence_threshold: float,
    return_pairs: bool = False,
) -> MorseSmaleResult | tuple[MorseSmaleResult, list[PersistencePair]]:
    """
    Simplify Morse-Smale complex by removing low-persistence features.

    This function filters critical points based on persistence, removing
    those that form pairs with persistence below the threshold. This is
    useful for removing noise and focusing on significant topological features.

    The simplification follows the principle that low-persistence features
    represent noise or small-scale variations, while high-persistence
    features represent significant structures in the data.

    Args:
        result: MorseSmaleResult from compute_morse_smale.
        persistence_threshold: Persistence threshold as fraction of scalar range.
            Features with relative persistence below this are removed.
            Recommended range: 0.01 to 0.10 (1% to 10% of scalar range).
        return_pairs: If True, also return the list of persistence pairs.

    Returns:
        If return_pairs is False:
            Simplified MorseSmaleResult with fewer critical points.
        If return_pairs is True:
            Tuple of (simplified MorseSmaleResult, list of PersistencePair).

    Example:
        >>> result = compute_morse_smale("mobility.vti", persistence_threshold=0.01)
        >>> print(f"Before: {len(result.critical_points)} critical points")
        Before: 45 critical points

        >>> simplified = simplify_topology(result, persistence_threshold=0.05)
        >>> print(f"After: {len(simplified.critical_points)} critical points")
        After: 12 critical points

        >>> # With persistence pairs
        >>> simplified, pairs = simplify_topology(result, 0.05, return_pairs=True)
        >>> low_pers = [p for p in pairs if p.relative_persistence < 0.05]
        >>> print(f"Removed {len(low_pers)} pairs")
    """
    if not 0.0 <= persistence_threshold <= 1.0:
        raise ValueError(f"persistence_threshold must be in [0, 1], got {persistence_threshold}")

    # If threshold is the same or lower, return original
    if persistence_threshold <= result.persistence_threshold:
        logger.info(
            f"Threshold {persistence_threshold:.2%} <= original "
            f"{result.persistence_threshold:.2%}, returning original"
        )
        if return_pairs:
            return result, compute_persistence_pairs(result)
        return result

    # Compute persistence pairs
    pairs = compute_persistence_pairs(result)

    # Compute absolute threshold
    scalar_range = result.scalar_range[1] - result.scalar_range[0]
    abs_threshold = persistence_threshold * scalar_range

    # Identify critical points to remove (those in low-persistence pairs)
    points_to_remove: set[int] = set()
    removed_pairs: list[PersistencePair] = []
    kept_pairs: list[PersistencePair] = []

    for pair in pairs:
        if pair.persistence < abs_threshold:
            points_to_remove.add(pair.birth_id)
            points_to_remove.add(pair.death_id)
            removed_pairs.append(pair)
        else:
            kept_pairs.append(pair)

    # Log simplification details
    logger.info(f"Simplifying topology: threshold={persistence_threshold:.2%} " f"(abs={abs_threshold:.4f})")
    logger.info(f"Removing {len(removed_pairs)} pairs, keeping {len(kept_pairs)} pairs")

    if removed_pairs:
        removed_by_type = {}
        for p in removed_pairs:
            removed_by_type[p.feature_type] = removed_by_type.get(p.feature_type, 0) + 1
        logger.debug(f"Removed pairs by type: {removed_by_type}")

    # Filter critical points
    # Keep essential points (those not in any removed pair, or in a kept pair)
    essential_points: set[int] = set()
    for pair in kept_pairs:
        essential_points.add(pair.birth_id)
        essential_points.add(pair.death_id)

    # Also keep any point not in any pair (isolated extrema)
    all_paired_points = {p.birth_id for p in pairs} | {p.death_id for p in pairs}
    for cp in result.critical_points:
        if cp.point_id not in all_paired_points:
            essential_points.add(cp.point_id)

    # Filter critical points - keep points that aren't paired with low-persistence
    simplified_cps = [cp for cp in result.critical_points if cp.point_id not in points_to_remove]

    # Log results
    n_removed = len(result.critical_points) - len(simplified_cps)
    logger.info(f"Critical points: {len(result.critical_points)} -> {len(simplified_cps)} " f"(removed {n_removed})")

    # Create simplified result
    simplified = MorseSmaleResult(
        critical_points=simplified_cps,
        separatrices_1d=result.separatrices_1d,  # Keep all separatrices
        ascending_manifold=result.ascending_manifold,
        descending_manifold=result.descending_manifold,
        persistence_threshold=persistence_threshold,
        scalar_range=result.scalar_range,
        metadata={
            **result.metadata,
            "original_critical_points": len(result.critical_points),
            "removed_critical_points": n_removed,
            "removed_pairs": len(removed_pairs),
        },
    )

    if return_pairs:
        return simplified, pairs
    return simplified


def get_persistence_diagram(
    result: MorseSmaleResult,
) -> NDArray[np.float64]:
    """
    Extract persistence diagram from Morse-Smale result.

    Returns a 2D array where each row is [birth, death] for a topological
    feature. This can be used for persistence-based machine learning
    or visualization.

    Args:
        result: MorseSmaleResult from compute_morse_smale.

    Returns:
        (N, 2) array of [birth, death] pairs.

    Example:
        >>> result = compute_morse_smale("mobility.vti")
        >>> diagram = get_persistence_diagram(result)
        >>> print(f"Diagram has {len(diagram)} points")
    """
    pairs = compute_persistence_pairs(result)

    if not pairs:
        return np.array([], dtype=np.float64).reshape(0, 2)

    diagram = np.array(
        [[p.birth_value, p.death_value] for p in pairs],
        dtype=np.float64,
    )

    return diagram


def suggest_persistence_threshold(
    result: MorseSmaleResult,
    target_features: int | None = None,
    method: Literal["elbow", "gap", "quantile"] = "elbow",
) -> float:
    """
    Suggest an optimal persistence threshold for simplification.

    This function analyzes the persistence distribution and suggests
    a threshold that separates noise from significant features.

    Args:
        result: MorseSmaleResult from compute_morse_smale.
        target_features: Optional target number of features to retain.
            If provided, returns threshold that yields approximately this many.
        method: Method for threshold selection:
            - "elbow": Find elbow in sorted persistence values
            - "gap": Find largest gap in persistence values
            - "quantile": Use 25th percentile (remove bottom quartile)

    Returns:
        Suggested persistence threshold as fraction of scalar range.

    Example:
        >>> result = compute_morse_smale("mobility.vti", persistence_threshold=0.0)
        >>> threshold = suggest_persistence_threshold(result, method="gap")
        >>> print(f"Suggested threshold: {threshold:.2%}")
    """
    pairs = compute_persistence_pairs(result)

    if not pairs:
        return 0.0

    scalar_range = result.scalar_range[1] - result.scalar_range[0]
    if scalar_range <= 0:
        return 0.0

    # Get sorted persistence values (relative)
    persistences = np.array([p.persistence / scalar_range for p in pairs])
    persistences.sort()

    if target_features is not None:
        # Return threshold that keeps approximately target_features
        if target_features >= len(pairs):
            return 0.0
        idx = len(pairs) - target_features
        return float(persistences[idx])

    if method == "elbow":
        # Find elbow using second derivative
        if len(persistences) < 3:
            return float(persistences[0]) if len(persistences) > 0 else 0.0

        # Compute differences
        diffs = np.diff(persistences)
        if len(diffs) < 2:
            return float(persistences[len(persistences) // 2])

        # Find maximum curvature (elbow)
        second_diff = np.diff(diffs)
        elbow_idx = np.argmax(second_diff) + 1
        return float(persistences[elbow_idx])

    elif method == "gap":
        # Find largest gap between consecutive values
        if len(persistences) < 2:
            return 0.0

        gaps = np.diff(persistences)
        gap_idx = np.argmax(gaps)
        # Return threshold just above the gap
        return float(persistences[gap_idx + 1])

    elif method == "quantile":
        # Use 25th percentile
        return float(np.percentile(persistences, 25))

    else:
        raise ValueError(f"Unknown method: {method}. Use 'elbow', 'gap', or 'quantile'")
