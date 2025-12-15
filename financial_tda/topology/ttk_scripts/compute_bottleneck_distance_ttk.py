"""
TTK subprocess script: Compute bottleneck distance between two persistence diagrams.

This script runs in the isolated TTK conda environment to compute
bottleneck distance using TTK's BottleneckDistance filter.

Usage:
    python compute_bottleneck_distance_ttk.py <diagram1_vtk> <diagram2_vtk> <output_json>
"""

import json
import sys
from pathlib import Path

import topologytoolkit as ttk
import vtk


def compute_bottleneck_distance(diagram1_path, diagram2_path, output_path):
    """
    Compute bottleneck distance between two persistence diagrams.

    Args:
        diagram1_path: Path to first persistence diagram VTK file
        diagram2_path: Path to second persistence diagram VTK file
        output_path: Path to save JSON output with distance value

    Returns:
        Exit code: 0 on success, 1 on error
    """
    try:
        # Read persistence diagrams
        reader1 = vtk.vtkGenericDataObjectReader()
        reader1.SetFileName(str(diagram1_path))
        reader1.Update()
        diag1 = reader1.GetOutput()

        reader2 = vtk.vtkGenericDataObjectReader()
        reader2.SetFileName(str(diagram2_path))
        reader2.Update()
        diag2 = reader2.GetOutput()

        print(f"Diagram 1: {diag1.GetNumberOfPoints()} pairs")
        print(f"Diagram 2: {diag2.GetNumberOfPoints()} pairs")

        # TTK bottleneck distance requires MultiBlockDataSet input
        # Create multiblock dataset containing both diagrams
        mb_dataset = vtk.vtkMultiBlockDataSet()
        mb_dataset.SetNumberOfBlocks(2)
        mb_dataset.SetBlock(0, diag1)
        mb_dataset.SetBlock(1, diag2)

        # Create bottleneck distance filter
        bottleneck = ttk.ttkBottleneckDistance()
        bottleneck.SetInputData(mb_dataset)
        bottleneck.Update()

        # Extract distance value from output
        output = bottleneck.GetOutput()

        if output is None:
            print("ERROR: TTK bottleneck distance returned None", file=sys.stderr)
            return 1

        # TTK returns distance in field data
        field_data = output.GetFieldData()
        distance = None

        # Try to find distance value in field data
        for i in range(field_data.GetNumberOfArrays()):
            arr = field_data.GetArray(i)
            arr_name = arr.GetName() if arr.GetName() else ""
            print(
                f"Field array {i}: '{arr_name}' (tuples: {arr.GetNumberOfTuples()}, components: {arr.GetNumberOfComponents()})"
            )

            # TTK stores bottleneck distance in field data array
            if arr.GetNumberOfTuples() > 0:
                distance = arr.GetValue(0)
                print(f"Found distance in array '{arr_name}': {distance}")
                break

        if distance is None:
            print(
                "ERROR: Could not extract bottleneck distance from TTK output",
                file=sys.stderr,
            )
            print(f"Output type: {output.GetClassName()}", file=sys.stderr)
            print(f"Field arrays: {field_data.GetNumberOfArrays()}", file=sys.stderr)
            return 1

        # Save result to JSON
        result = {
            "bottleneck_distance": float(distance),
            "diagram1_pairs": diag1.GetNumberOfPoints(),
            "diagram2_pairs": diag2.GetNumberOfPoints(),
        }

        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

        print(f"Bottleneck distance: {distance}")
        print(f"Saved result to {output_path}")
        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Usage: python compute_bottleneck_distance_ttk.py <diagram1_vtk> <diagram2_vtk> <output_json>",
            file=sys.stderr,
        )
        sys.exit(1)

    diagram1_path = Path(sys.argv[1])
    diagram2_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])

    if not diagram1_path.exists():
        print(f"ERROR: First diagram not found: {diagram1_path}", file=sys.stderr)
        sys.exit(1)

    if not diagram2_path.exists():
        print(f"ERROR: Second diagram not found: {diagram2_path}", file=sys.stderr)
        sys.exit(1)

    exit_code = compute_bottleneck_distance(diagram1_path, diagram2_path, output_path)
    sys.exit(exit_code)
