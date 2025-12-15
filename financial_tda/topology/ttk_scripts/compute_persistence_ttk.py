"""
TTK subprocess script: Compute persistence diagram from structured scalar field.

This script runs in the isolated TTK conda environment to compute
persistence diagrams using TTK's PersistenceDiagram filter on structured grids.

Usage:
    python compute_persistence_ttk.py <input_vtk> <output_vtk> <max_dimension>
"""

import sys
from pathlib import Path

import numpy as np
import topologytoolkit as ttk
import vtk
from vtk.util import numpy_support


def compute_persistence_from_vtk(input_path, output_path, max_dimension=2):
    """
    Compute persistence diagram from VTK structured scalar field.

    Args:
        input_path: Path to input VTK file containing structured grid with scalar field
        output_path: Path to save output VTK file with persistence diagram
        max_dimension: Maximum homology dimension to compute

    Returns:
        Exit code: 0 on success, 1 on error
    """
    try:
        # Read input structured grid
        reader = vtk.vtkGenericDataObjectReader()
        reader.SetFileName(str(input_path))
        reader.Update()
        scalar_field = reader.GetOutput()

        if scalar_field.GetNumberOfPoints() == 0:
            print("ERROR: Input scalar field is empty", file=sys.stderr)
            return 1

        # Check for scalar field
        scalar_array = scalar_field.GetPointData().GetScalars()
        if scalar_array is None:
            print("ERROR: No scalar field found in input", file=sys.stderr)
            return 1

        scalar_name = scalar_array.GetName()
        print(f"Computing persistence for scalar field: {scalar_name}")
        print(f"  Points: {scalar_field.GetNumberOfPoints()}")
        print(f"  Data type: {scalar_field.GetClassName()}")

        # Create persistence diagram filter
        persistence = ttk.ttkPersistenceDiagram()
        persistence.SetInputData(scalar_field)
        persistence.SetInputArrayToProcess(0, 0, 0, 0, scalar_name)
        persistence.Update()

        # Get output
        diagram = persistence.GetOutput()
        n_pairs = diagram.GetNumberOfPoints()

        print(f"Computed {n_pairs} persistence pairs")

        # Query and report available arrays
        n_arrays = diagram.GetPointData().GetNumberOfArrays()
        print(f"Output contains {n_arrays} arrays:")
        for i in range(n_arrays):
            arr = diagram.GetPointData().GetArray(i)
            print(f"  - {arr.GetName()} (components: {arr.GetNumberOfComponents()})")

        # Write output
        writer = vtk.vtkGenericDataObjectWriter()
        writer.SetFileName(str(output_path))
        writer.SetInputData(diagram)
        writer.Write()

        print(f"Saved persistence diagram to {output_path}")
        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Usage: python compute_persistence_ttk.py <input_file> <output_file> <max_dimension>",
            file=sys.stderr,
        )
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    max_dimension = int(sys.argv[3])

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    exit_code = compute_persistence_from_vtk(input_path, output_path, max_dimension)
    sys.exit(exit_code)
