"""
Minimal example: Computing Morse-Smale complex with TTK.

This script demonstrates extraction of critical points and separatrices
using the TTKMorseSmaleComplex filter.
"""

import numpy as np
import topologytoolkit as ttk
import vtk
from vtk.util import numpy_support


def compute_morse_smale_complex(scalar_field_data):
    """
    Compute Morse-Smale complex from scalar field.

    Args:
        scalar_field_data: VTK dataset with scalar field

    Returns:
        Tuple of (critical_points, separatrices) as VTK datasets
    """
    # Create Morse-Smale complex filter
    morse_smale = ttk.ttkMorseSmaleComplex()
    morse_smale.SetInputData(scalar_field_data)
    morse_smale.SetInputArrayToProcess(0, 0, 0, 0, scalar_field_data.GetPointData().GetScalars().GetName())
    morse_smale.Update()

    # Output port 0: critical points
    # Output port 1: separatrices (1-cells)
    # Output port 2: separatrices (2-cells, for 3D data)
    critical_points = morse_smale.GetOutput(0)
    separatrices = morse_smale.GetOutput(1)

    return critical_points, separatrices


if __name__ == "__main__":
    # Create test 2D scalar field with multiple extrema
    resolution = 20
    x = np.linspace(-2, 2, resolution)
    y = np.linspace(-2, 2, resolution)
    X, Y = np.meshgrid(x, y)
    Z = np.sin(X) * np.cos(Y) + 0.3 * np.sin(2 * X) * np.cos(2 * Y)

    # Create VTK image data
    image = vtk.vtkImageData()
    image.SetDimensions(resolution, resolution, 1)
    scalars = numpy_support.numpy_to_vtk(Z.ravel(), deep=True)
    scalars.SetName("ScalarField")
    image.GetPointData().SetScalars(scalars)

    # Compute Morse-Smale complex
    critical_points, separatrices = compute_morse_smale_complex(image)

    print(f"Critical points: {critical_points.GetNumberOfPoints()}")
    print(f"Separatrices: {separatrices.GetNumberOfCells()}")

    # Show available arrays on critical points
    point_data = critical_points.GetPointData()
    print(
        "Critical point arrays:",
        [point_data.GetArrayName(i) for i in range(point_data.GetNumberOfArrays())],
    )
