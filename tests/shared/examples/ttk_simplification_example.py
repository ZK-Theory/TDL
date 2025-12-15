"""
Minimal example: Topological simplification with TTK.

This script demonstrates noise removal using persistence-based
topological simplification.
"""

import numpy as np
import topologytoolkit as ttk
import vtk
from vtk.util import numpy_support


def simplify_scalar_field(scalar_field_data, persistence_threshold=0.1):
    """
    Apply topological simplification to remove low-persistence features.

    Args:
        scalar_field_data: VTK dataset with scalar field
        persistence_threshold: Persistence value below which features are removed

    Returns:
        VTK dataset with simplified scalar field
    """
    scalar_name = scalar_field_data.GetPointData().GetScalars().GetName()

    # First compute persistence diagram
    persistence = ttk.ttkPersistenceDiagram()
    persistence.SetInputData(scalar_field_data)
    persistence.SetInputArrayToProcess(0, 0, 0, 0, scalar_name)
    persistence.Update()

    # Apply topological simplification
    simplification = ttk.ttkTopologicalSimplification()
    simplification.SetInputData(scalar_field_data)
    simplification.SetInputArrayToProcess(0, 0, 0, 0, scalar_name)
    simplification.SetInputConnection(1, persistence.GetOutputPort())
    simplification.SetPersistenceThreshold(persistence_threshold)
    simplification.Update()

    return simplification.GetOutput()


if __name__ == "__main__":
    # Create test 2D scalar field with noise
    resolution = 30
    x = np.linspace(-2, 2, resolution)
    y = np.linspace(-2, 2, resolution)
    X, Y = np.meshgrid(x, y)

    # Signal + noise
    signal = np.sin(X) * np.cos(Y)
    noise = 0.2 * np.random.randn(resolution, resolution)
    Z = signal + noise

    # Create VTK image data
    image = vtk.vtkImageData()
    image.SetDimensions(resolution, resolution, 1)
    scalars = numpy_support.numpy_to_vtk(Z.ravel(), deep=True)
    scalars.SetName("NoisyField")
    image.GetPointData().SetScalars(scalars)

    # Apply simplification with different thresholds
    for threshold in [0.05, 0.1, 0.2]:
        simplified = simplify_scalar_field(image, persistence_threshold=threshold)
        print(f"Persistence threshold {threshold}: " f"{simplified.GetNumberOfPoints()} points processed")
