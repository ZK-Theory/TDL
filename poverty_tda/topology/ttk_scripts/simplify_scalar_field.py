"""
TTK Topological Simplification Script.

This script runs in the TTK conda environment to simplify scalar fields
by removing low-persistence topological noise using TTKTopologicalSimplification.

Persistence-based simplification removes critical point pairs with persistence
below a threshold, effectively denoising the scalar field while preserving
significant topological features.

Usage:
    python simplify_scalar_field.py --input input.vti --output simplified.vti \\
        --scalar-name mobility --persistence-threshold 0.05

License: Open Government Licence v3.0
"""

import argparse
import sys
from pathlib import Path


def simplify_scalar_field(
    input_path: str,
    output_path: str,
    scalar_name: str,
    persistence_threshold: float,
) -> None:
    """
    Simplify a VTK scalar field using TTK topological simplification.

    Args:
        input_path: Path to input VTK file
        output_path: Path to output simplified VTK file
        scalar_name: Name of scalar field to simplify
        persistence_threshold: Persistence threshold (absolute value)

    Raises:
        ImportError: If TTK is not available
        FileNotFoundError: If input file doesn't exist
        ValueError: If scalar field doesn't exist or is invalid
    """
    # Import VTK and TTK (only available in TTK conda environment)
    try:
        import vtk
        from topologytoolkit.ttkTopologicalSimplification import (
            ttkTopologicalSimplification,
        )
    except ImportError as e:
        raise ImportError(
            f"TTK not available in current environment: {e}\n" "This script must run in the TTK conda environment."
        )

    # Validate input file
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Load VTK file using appropriate reader
    suffix = input_file.suffix.lower()
    readers = {
        ".vti": vtk.vtkXMLImageDataReader,
        ".vts": vtk.vtkXMLStructuredGridReader,
        ".vtp": vtk.vtkXMLPolyDataReader,
        ".vtk": vtk.vtkDataSetReader,
    }

    reader_class = readers.get(suffix)
    if reader_class is None:
        raise ValueError(f"Unsupported VTK format: {suffix}")

    reader = reader_class()
    reader.SetFileName(str(input_file))
    reader.Update()
    vtk_data = reader.GetOutput()

    # Validate scalar field exists
    point_data = vtk_data.GetPointData()
    scalar_array = point_data.GetArray(scalar_name)
    if scalar_array is None:
        available = [point_data.GetArrayName(i) for i in range(point_data.GetNumberOfArrays())]
        raise ValueError(f"Scalar field '{scalar_name}' not found. Available: {available}")

    # Set active scalars
    point_data.SetActiveScalars(scalar_name)

    # Create and configure TTK topological simplification filter
    simplification = ttkTopologicalSimplification()
    simplification.SetInputData(vtk_data)
    simplification.SetInputArrayToProcess(0, 0, 0, 0, scalar_name)
    simplification.SetPersistenceThreshold(persistence_threshold)

    # Execute simplification
    simplification.Update()
    simplified_data = simplification.GetOutput()

    # Write simplified data to output file
    output_file = Path(output_path)
    writers = {
        ".vti": vtk.vtkXMLImageDataWriter,
        ".vts": vtk.vtkXMLStructuredGridWriter,
        ".vtp": vtk.vtkXMLPolyDataWriter,
        ".vtk": vtk.vtkDataSetWriter,
    }

    output_suffix = output_file.suffix.lower()
    writer_class = writers.get(output_suffix)
    if writer_class is None:
        raise ValueError(f"Unsupported output format: {output_suffix}")

    writer = writer_class()
    writer.SetFileName(str(output_file))
    writer.SetInputData(simplified_data)
    writer.Write()

    print(f"SUCCESS: Simplified field written to {output_path}")


def main():
    """Command-line interface for TTK topological simplification."""
    parser = argparse.ArgumentParser(description="Simplify VTK scalar field using TTK topological simplification")
    parser.add_argument("--input", required=True, help="Input VTK file path")
    parser.add_argument("--output", required=True, help="Output VTK file path")
    parser.add_argument("--scalar-name", default="mobility", help="Scalar field name (default: mobility)")
    parser.add_argument(
        "--persistence-threshold",
        type=float,
        required=True,
        help="Absolute persistence threshold for simplification",
    )

    args = parser.parse_args()

    try:
        simplify_scalar_field(
            args.input,
            args.output,
            args.scalar_name,
            args.persistence_threshold,
        )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
