"""
TTK subprocess script for computing persistence curves.

This script runs in the isolated TTK conda environment to compute
persistence curves from persistence diagram VTK files.

Usage:
    python compute_persistence_curve.py <input.vti> <output.csv>

Note: This is a template. Actual TTK curve computation may require
      more complex pipeline setup or can be handled in numpy directly.
"""

import sys
from pathlib import Path


def compute_persistence_curve_ttk(input_path: str, output_path: str) -> int:
    """
    Compute persistence curve using TTK filters.

    Args:
        input_path: Path to input VTK file with persistence diagram.
        output_path: Path to output CSV file with curve data.

    Returns:
        Exit code (0 for success, 1 for error).

    Note:
        TTK does not have a direct "persistence curve" filter.
        This function is a placeholder for potential future TTK integration.
        Current implementation uses numpy-based computation in parent module.
    """
    try:
        import numpy as np

        # Try to import TTK
        try:
            import vtk
            from vtkmodules.util.numpy_support import vtk_to_numpy
        except ImportError:
            print("ERROR: VTK not available in TTK environment", file=sys.stderr)
            return 1

        # Read input VTK file
        reader = vtk.vtkXMLPolyDataReader()
        reader.SetFileName(input_path)
        reader.Update()
        poly_data = reader.GetOutput()

        if poly_data.GetNumberOfPoints() == 0:
            print("ERROR: No points in input VTK file", file=sys.stderr)
            return 1

        # Extract persistence values
        persistence_array = poly_data.GetPointData().GetArray("Persistence")
        if persistence_array is None:
            print("ERROR: No 'Persistence' array in input file", file=sys.stderr)
            return 1

        persistence_values = vtk_to_numpy(persistence_array)

        # Compute cumulative distribution
        sorted_values = np.sort(persistence_values)
        cumulative = np.arange(1, len(sorted_values) + 1) / len(sorted_values)

        # Save to CSV
        output_data = np.column_stack([sorted_values, cumulative])
        np.savetxt(
            output_path,
            output_data,
            delimiter=",",
            header="Persistence,CumulativeFraction",
            comments="",
        )

        print(f"SUCCESS: Wrote curve data to {output_path}")
        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Usage: python compute_persistence_curve.py <input.vti> <output.csv>",
            file=sys.stderr,
        )
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    # Validate input exists
    if not Path(input_path).exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    exit_code = compute_persistence_curve_ttk(input_path, output_path)
    sys.exit(exit_code)
