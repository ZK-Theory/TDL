"""
Minimal example: Computing persistence diagram with TTK.

This script demonstrates the basic usage of TTKPersistenceDiagram filter
for topological data analysis.
"""

import numpy as np
import topologytoolkit as ttk
import vtk
from vtk.util import numpy_support


def compute_persistence_diagram(scalar_field_data):
    """
    Compute persistence diagram from scalar field.

    Args:
        scalar_field_data: VTK dataset with scalar field

    Returns:
        VTK dataset containing persistence pairs
    """
    # Create persistence diagram filter
    persistence = ttk.ttkPersistenceDiagram()
    persistence.SetInputData(scalar_field_data)
    persistence.SetInputArrayToProcess(0, 0, 0, 0, scalar_field_data.GetPointData().GetScalars().GetName())
    persistence.Update()

    return persistence.GetOutput()


if __name__ == "__main__":
    # Create test 2D scalar field
    resolution = 20
    x = np.linspace(-2, 2, resolution)
    y = np.linspace(-2, 2, resolution)
    X, Y = np.meshgrid(x, y)
    Z = np.sin(X) * np.cos(Y)

    # Create VTK image data
    image = vtk.vtkImageData()
    image.SetDimensions(resolution, resolution, 1)
    scalars = numpy_support.numpy_to_vtk(Z.ravel(), deep=True)
    scalars.SetName("ScalarField")
    image.GetPointData().SetScalars(scalars)

    # Compute persistence diagram
    diagram = compute_persistence_diagram(image)

    print(f"Persistence pairs: {diagram.GetNumberOfPoints()}")
    print(
        "Available arrays:",
        [diagram.GetPointData().GetArrayName(i) for i in range(diagram.GetPointData().GetNumberOfArrays())],
    )
