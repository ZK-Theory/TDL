"""
TTK subprocess script: Compute Rips persistence diagram from point cloud.

This script runs in the isolated TTK conda environment to compute
persistence diagrams using TTK's RipsPersistenceDiagram filter on point clouds.

Usage:
    python compute_persistence_ttk.py <input_vtk> <output_vtk> <max_dimension>
"""

import sys
from pathlib import Path

import numpy as np
import topologytoolkit as ttk
import vtk


def compute_persistence_from_vtk(input_path, output_path, max_dimension=2):
    """
    Compute Rips persistence diagram from point cloud.

    Args:
        input_path: Path to input VTK file containing point cloud coordinates
        output_path: Path to save output VTK file with persistence diagram
        max_dimension: Maximum homology dimension to compute

    Returns:
        Exit code: 0 on success, 1 on error
    """
    try:
        # Read input point cloud
        reader = vtk.vtkGenericDataObjectReader()
        reader.SetFileName(str(input_path))
        reader.Update()
        point_data = reader.GetOutput()

        if point_data.GetNumberOfPoints() == 0:
            print("ERROR: Input point cloud is empty", file=sys.stderr)
            return 1

        n_points = point_data.GetNumberOfPoints()
        print("Computing Rips persistence for point cloud:")
        print(f"  Points: {n_points}")
        print(f"  Max dimension: {max_dimension}")

        # Extract point coordinates
        points = np.zeros((n_points, 3))
        for i in range(n_points):
            points[i] = point_data.GetPoint(i)

        print(f"  Point cloud shape: {points.shape}")

        # Compute pairwise distance matrix (required by ttkRipsPersistenceDiagram)
        print("Computing distance matrix...")
        distances = np.zeros((n_points, n_points))
        for i in range(n_points):
            for j in range(n_points):
                distances[i, j] = np.linalg.norm(points[i] - points[j])

        # Create VTK table from distance matrix
        table = vtk.vtkTable()
        for i in range(n_points):
            col = vtk.vtkFloatArray()
            col.SetName(f"Point_{i}")
            col.SetNumberOfTuples(n_points)
            for j in range(n_points):
                col.SetValue(j, distances[i, j])
            table.AddColumn(col)

        # Create Rips persistence diagram filter (CORRECT filter for point clouds)
        persistence = ttk.ttkRipsPersistenceDiagram()

        # TTK requires TrivialProducer for table input
        producer = vtk.vtkTrivialProducer()
        producer.SetOutput(table)

        persistence.SetInputConnection(producer.GetOutputPort())
        persistence.SetInputIsDistanceMatrix(1)  # Flag input as distance matrix
        persistence.SetSimplexMaximumDimension(max_dimension)
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
