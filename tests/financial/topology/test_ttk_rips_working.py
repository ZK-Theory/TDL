"""
Test TTK Rips complex persistence on point clouds.

TTK provides ttkRipsPersistenceDiagram filter for point cloud persistence,
NOT the standard ttkPersistenceDiagram (which is for scalar fields on meshes).
"""

import subprocess
import sys
from pathlib import Path

# Test with ttk_env directly
ttk_env_python = Path.home() / "miniconda3" / "envs" / "ttk_env" / "python.exe"

if not ttk_env_python.exists():
    # Try alternative conda location
    ttk_env_python = Path("C:/") / "ProgramData" / "miniconda3" / "envs" / "ttk_env" / "python.exe"

if not ttk_env_python.exists():
    print("TTK environment not found - skipping test")
    sys.exit(0)

# Create test script to run in TTK environment
test_script = """
import numpy as np
import topologytoolkit as ttk
import vtk
from vtk.util import numpy_support

# Create 2D point cloud
np.random.seed(42)
n_points = 50
point_cloud = np.random.randn(n_points, 2)

# Pad to 3D (TTK requires 3D points)
point_cloud_3d = np.column_stack([point_cloud, np.zeros(n_points)])

# Create VTK PolyData (point cloud structure)
points = vtk.vtkPoints()
for pt in point_cloud_3d:
    points.InsertNextPoint(pt)

polydata = vtk.vtkPolyData()
polydata.SetPoints(points)

print(f"Input: {n_points} points")
print(f"Data type: {polydata.GetClassName()}")

# Use ttkRipsPersistenceDiagram for point clouds!
rips_persistence = ttk.ttkRipsPersistenceDiagram()
rips_persistence.SetInputData(polydata)
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
"""

# Write temp script
temp_script = Path("temp_ttk_rips_test.py")
temp_script.write_text(test_script)

try:
    # Run in TTK environment
    result = subprocess.run(
        [str(ttk_env_python), str(temp_script)],
        capture_output=True,
        text=True,
        timeout=30,
    )

    print(result.stdout)

    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        sys.exit(1)

    print("\nTTK Rips persistence test PASSED!")

finally:
    # Cleanup
    if temp_script.exists():
        temp_script.unlink()
