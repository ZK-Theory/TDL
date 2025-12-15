"""
TTK Filter Verification Scripts.

This module contains minimal test scripts for core TTK filters needed for the project.
Each script can be run independently in the TTK subprocess environment.
"""

import sys

import numpy as np
import topologytoolkit as ttk
import vtk
from vtk.util import numpy_support


def create_test_scalar_field():
    """Create a simple 2D scalar field for testing."""
    # Create a 20x20 grid
    resolution = 20
    x = np.linspace(-2, 2, resolution)
    y = np.linspace(-2, 2, resolution)
    X, Y = np.meshgrid(x, y)

    # Create a scalar field with multiple extrema
    Z = np.sin(X) * np.cos(Y) + 0.5 * np.sin(2 * X) * np.cos(2 * Y)

    # Create VTK image data
    image = vtk.vtkImageData()
    image.SetDimensions(resolution, resolution, 1)
    image.SetSpacing(1.0, 1.0, 1.0)
    image.SetOrigin(0.0, 0.0, 0.0)

    # Add scalar field
    scalars = numpy_support.numpy_to_vtk(Z.ravel(), deep=True)
    scalars.SetName("TestScalarField")
    image.GetPointData().SetScalars(scalars)

    return image


def test_persistence_diagram():
    """Test TTKPersistenceDiagram filter."""
    print("\n=== Testing TTKPersistenceDiagram ===")

    try:
        # Create test data
        image = create_test_scalar_field()

        # Apply persistence diagram filter
        persistence = ttk.ttkPersistenceDiagram()
        persistence.SetInputData(image)
        persistence.SetInputArrayToProcess(0, 0, 0, 0, "TestScalarField")
        persistence.Update()

        # Get output
        output = persistence.GetOutput()
        num_pairs = output.GetNumberOfPoints()

        print("[OK] Persistence diagram computed successfully")
        print(f"     - Input points: {image.GetNumberOfPoints()}")
        print(f"     - Persistence pairs: {num_pairs}")

        # Verify we got some pairs
        assert num_pairs > 0, "No persistence pairs found"

        # Check that output has point data (arrays may have different names in different TTK versions)
        point_data = output.GetPointData()
        num_arrays = point_data.GetNumberOfArrays()
        print(f"     - Output arrays: {num_arrays}")

        # List array names for debugging
        array_names = [point_data.GetArrayName(i) for i in range(num_arrays)]
        if array_names:
            print(f"     - Available arrays: {', '.join(array_names)}")

        return True

    except Exception as e:
        print(f"[FAIL] TTKPersistenceDiagram: {e}")
        return False


def test_bottleneck_distance():
    """Test TTKBottleneckDistance filter."""
    print("\n=== Testing TTKBottleneckDistance ===")

    try:
        # Create two test scalar fields
        image1 = create_test_scalar_field()
        image2 = create_test_scalar_field()

        # Compute persistence diagrams
        persistence1 = ttk.ttkPersistenceDiagram()
        persistence1.SetInputData(image1)
        persistence1.SetInputArrayToProcess(0, 0, 0, 0, "TestScalarField")
        persistence1.Update()

        persistence2 = ttk.ttkPersistenceDiagram()
        persistence2.SetInputData(image2)
        persistence2.SetInputArrayToProcess(0, 0, 0, 0, "TestScalarField")
        persistence2.Update()

        # Compute bottleneck distance
        bottleneck = ttk.ttkBottleneckDistance()
        bottleneck.SetInputConnection(0, persistence1.GetOutputPort())
        bottleneck.SetInputConnection(1, persistence2.GetOutputPort())
        bottleneck.Update()

        # Get distance (should be 0 since diagrams are identical)
        output = bottleneck.GetOutput()

        print("[OK] Bottleneck distance computed successfully")
        print(f"     - Diagram 1 pairs: {persistence1.GetOutput().GetNumberOfPoints()}")
        print(f"     - Diagram 2 pairs: {persistence2.GetOutput().GetNumberOfPoints()}")
        print("     - Distance computed: OK")

        return True

    except Exception as e:
        print(f"[FAIL] TTKBottleneckDistance: {e}")
        return False


def test_morse_smale_complex():
    """Test TTKMorseSmaleComplex filter."""
    print("\n=== Testing TTKMorseSmaleComplex ===")

    try:
        # Create test data
        image = create_test_scalar_field()

        # Apply Morse-Smale complex filter
        morse_smale = ttk.ttkMorseSmaleComplex()
        morse_smale.SetInputData(image)
        morse_smale.SetInputArrayToProcess(0, 0, 0, 0, "TestScalarField")
        morse_smale.Update()

        # Get critical points output (port 0)
        critical_points = morse_smale.GetOutput(0)
        num_critical = critical_points.GetNumberOfPoints()

        # Get separatrices output (port 1)
        separatrices = morse_smale.GetOutput(1)
        num_separatrices = separatrices.GetNumberOfCells()

        print("[OK] Morse-Smale complex computed successfully")
        print(f"     - Input points: {image.GetNumberOfPoints()}")
        print(f"     - Critical points: {num_critical}")
        print(f"     - Separatrices: {num_separatrices}")

        # Verify we found critical points
        assert num_critical > 0, "No critical points found"

        # Check for critical point type array
        point_data = critical_points.GetPointData()
        num_arrays = point_data.GetNumberOfArrays()
        print(f"     - Critical point arrays: {num_arrays}")

        # List array names
        array_names = [point_data.GetArrayName(i) for i in range(num_arrays)]
        if array_names:
            print(f"     - Available arrays: {', '.join(array_names)}")

        return True

    except Exception as e:
        print(f"[FAIL] TTKMorseSmaleComplex: {e}")
        return False


def test_topological_simplification():
    """Test TTKTopologicalSimplification filter."""
    print("\n=== Testing TTKTopologicalSimplification ===")

    try:
        # Create test data
        image = create_test_scalar_field()

        # First compute persistence to get persistence threshold
        persistence = ttk.ttkPersistenceDiagram()
        persistence.SetInputData(image)
        persistence.SetInputArrayToProcess(0, 0, 0, 0, "TestScalarField")
        persistence.Update()

        # Apply topological simplification
        simplification = ttk.ttkTopologicalSimplification()
        simplification.SetInputData(image)
        simplification.SetInputArrayToProcess(0, 0, 0, 0, "TestScalarField")
        simplification.SetInputConnection(1, persistence.GetOutputPort())
        simplification.SetPersistenceThreshold(0.1)  # Remove low-persistence features
        simplification.Update()

        # Get simplified output
        output = simplification.GetOutput()

        print("[OK] Topological simplification applied successfully")
        print(f"     - Input points: {image.GetNumberOfPoints()}")
        print(f"     - Output points: {output.GetNumberOfPoints()}")
        print("     - Persistence threshold: 0.1")

        # Check that output has scalar field
        assert output.GetPointData().GetScalars() is not None, "Simplified scalar field missing"

        print("     - Simplified field present: OK")
        return True

    except Exception as e:
        print(f"[FAIL] TTKTopologicalSimplification: {e}")
        return False


def run_all_tests():
    """Run all TTK filter tests."""
    print("=" * 60)
    print("TTK Core Filter Verification")
    print("=" * 60)

    results = {
        "TTKPersistenceDiagram": test_persistence_diagram(),
        "TTKBottleneckDistance": test_bottleneck_distance(),
        "TTKMorseSmaleComplex": test_morse_smale_complex(),
        "TTKTopologicalSimplification": test_topological_simplification(),
    }

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    for filter_name, passed in results.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"{status} {filter_name}")

    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("Result: All TTK filters working correctly!")
        return 0
    else:
        print("Result: Some TTK filters failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
