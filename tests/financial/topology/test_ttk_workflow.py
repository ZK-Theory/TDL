"""
Test complete TTK Rips workflow: point cloud -> distance matrix -> persistence.
"""

import subprocess
import sys
from pathlib import Path

import pytest

# Test with ttk_env directly
ttk_env_python = Path.home() / "miniconda3" / "envs" / "ttk_env" / "python.exe"

if not ttk_env_python.exists():
    # Try alternative conda location
    ttk_env_python = Path("C:/") / "ProgramData" / "miniconda3" / "envs" / "ttk_env" / "python.exe"

if not ttk_env_python.exists():
    pytest.skip("TTK environment not found - skipping test", allow_module_level=True)

# Create test script to run in TTK environment
test_script = """
import numpy as np
import topologytoolkit as ttk
import vtk
from vtk.util import numpy_support

# Create 2D point cloud
np.random.seed(42)
n_points = 30  # Smaller for testing
point_cloud = np.random.randn(n_points, 2)

print(f"Input: {n_points} points")

# Compute pairwise distance matrix manually
distances = np.zeros((n_points, n_points))
for i in range(n_points):
    for j in range(n_points):
        distances[i, j] = np.linalg.norm(point_cloud[i] - point_cloud[j])
print(f"Distance matrix shape: {distances.shape}")

# Create VTK table from distance matrix
table = vtk.vtkTable()
for i in range(n_points):
    col = vtk.vtkFloatArray()
    col.SetName(f"Point_{i}")
    col.SetNumberOfTuples(n_points)
    for j in range(n_points):
        col.SetValue(j, distances[i, j])
    table.AddColumn(col)

print(f"VTK table: {table.GetNumberOfRows()} rows, {table.GetNumberOfColumns()} cols")

# Use ttkRipsPersistenceDiagram with distance matrix input
# Need to use algorithm input connection for tables
rips_persistence = ttk.ttkRipsPersistenceDiagram()

# Create trivial producer for table
producer = vtk.vtkTrivialProducer()
producer.SetOutput(table)

rips_persistence.SetInputConnection(producer.GetOutputPort())
rips_persistence.SetInputIsDistanceMatrix(1)  # Flag as distance matrix
rips_persistence.SetSimplexMaximumDimension(2)  # Compute H0, H1, H2
rips_persistence.Update()

diagram = rips_persistence.GetOutput()
n_pairs = diagram.GetNumberOfPoints()

print(f"Success! Computed {n_pairs} persistence pairs")

# Analyze dimensions
if n_pairs > 0:
    # Extract arrays
    n_arrays = diagram.GetPointData().GetNumberOfArrays()
    print(f"Output contains {n_arrays} arrays:")
    for i in range(n_arrays):
        arr = diagram.GetPointData().GetArray(i)
        print(f"  - {arr.GetName()}")
else:
    print("WARNING: No persistence pairs found")
"""

# Write temp script
temp_script = Path("temp_ttk_workflow_test.py")
temp_script.write_text(test_script, encoding="utf-8")

try:
    # Run in TTK environment
    result = subprocess.run(
        [str(ttk_env_python), str(temp_script)],
        capture_output=True,
        text=True,
        timeout=60,
    )

    print(result.stdout)

    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        sys.exit(1)

    print("\nTTK Rips workflow test PASSED!")

finally:
    # Cleanup
    if temp_script.exists():
        temp_script.unlink()
