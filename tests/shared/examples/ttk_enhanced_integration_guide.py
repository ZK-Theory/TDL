"""
Comprehensive Guide: Enhanced TTK Integration for Morse-Smale Analysis

This example demonstrates the complete workflow for using the enhanced
TTK integration features implemented in Task 6.5.2, including:

1. Basic Morse-Smale computation
2. Pre-simplification for noise removal
3. Post-filtering by persistence
4. Threshold recommendation
5. Complete workflow for mobility surface analysis

Prerequisites:
- TTK installed in conda environment (see docs/TTK_SETUP.md)
- Sample VTK data or ability to create synthetic surfaces

License: Open Government Licence v3.0
"""

import tempfile
from pathlib import Path

import numpy as np
import pyvista as pv

from poverty_tda.topology.morse_smale import (
    compute_morse_smale,
    filter_by_persistence,
    simplify_scalar_field,
    suggest_persistence_threshold,
)

# =============================================================================
# EXAMPLE 1: Basic Morse-Smale Computation
# =============================================================================


def example_basic_morse_smale():
    """
    Example 1: Basic Morse-Smale complex computation.

    Demonstrates standard usage for extracting critical points from
    a scalar field.
    """
    print("=" * 70)
    print("EXAMPLE 1: Basic Morse-Smale Computation")
    print("=" * 70)

    # Create synthetic mobility surface (Gaussian with small noise)
    n = 30
    grid = pv.ImageData(dimensions=(n, n, 1), spacing=(0.33, 0.33, 1.0), origin=(-5, -5, 0))

    x = np.linspace(-5, 5, n)
    y = np.linspace(-5, 5, n)
    xx, yy = np.meshgrid(x, y)
    zz = np.exp(-(xx**2 + yy**2) / 4) + 0.03 * np.random.randn(n, n)

    grid["mobility"] = zz.ravel()

    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=".vti", delete=False) as tmp:
        vtk_path = Path(tmp.name)
    grid.save(str(vtk_path))

    try:
        # Compute Morse-Smale complex with 5% persistence threshold
        result = compute_morse_smale(
            vtk_path,
            scalar_name="mobility",
            persistence_threshold=0.05,  # Remove features < 5% of range
        )

        print("\nCritical Points Extracted:")
        print(f"  Minima:   {result.n_minima}")
        print(f"  Saddles:  {result.n_saddles}")
        print(f"  Maxima:   {result.n_maxima}")
        print(f"  Total:    {len(result.critical_points)}")

        print("\nTopological Features:")
        print(f"  Separatrices: {len(result.separatrices_1d)}")
        print(f"  Scalar range: [{result.scalar_range[0]:.4f}, {result.scalar_range[1]:.4f}]")

        # Access critical points by type
        maxima = result.get_maxima()
        print("\nTop 3 Maxima by value:")
        for i, cp in enumerate(sorted(maxima, key=lambda x: x.value, reverse=True)[:3]):
            print(f"  {i + 1}. Position: ({cp.position[0]:.2f}, {cp.position[1]:.2f}), " f"Value: {cp.value:.4f}")

    finally:
        vtk_path.unlink(missing_ok=True)


# =============================================================================
# EXAMPLE 2: Pre-Simplification for Noise Removal
# =============================================================================


def example_pre_simplification():
    """
    Example 2: Using pre-simplification to remove topological noise.

    Demonstrates the simplify_first feature for cleaner critical point
    extraction from noisy data.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Pre-Simplification for Noise Removal")
    print("=" * 70)

    # Create noisy mobility surface
    n = 30
    grid = pv.ImageData(dimensions=(n, n, 1), spacing=(0.33, 0.33, 1.0), origin=(-5, -5, 0))

    x = np.linspace(-5, 5, n)
    y = np.linspace(-5, 5, n)
    xx, yy = np.meshgrid(x, y)

    # Signal + significant noise
    signal = np.exp(-(xx**2 + yy**2) / 4)
    noise = 0.10 * np.random.randn(n, n)
    zz = signal + noise

    grid["mobility"] = zz.ravel()

    with tempfile.NamedTemporaryFile(suffix=".vti", delete=False) as tmp:
        vtk_path = Path(tmp.name)
    grid.save(str(vtk_path))

    try:
        # Standard extraction (without simplification)
        result_standard = compute_morse_smale(
            vtk_path,
            scalar_name="mobility",
            persistence_threshold=0.0,
            simplify_first=False,
        )

        # Enhanced extraction (with pre-simplification)
        result_enhanced = compute_morse_smale(
            vtk_path,
            scalar_name="mobility",
            persistence_threshold=0.0,
            simplify_first=True,
            simplification_threshold=0.12,  # Remove 12% noise
        )

        print("\nComparison:")
        print(f"  Standard extraction:  {len(result_standard.critical_points)} critical points")
        print(f"  Enhanced extraction:  {len(result_enhanced.critical_points)} critical points")

        reduction = len(result_standard.critical_points) - len(result_enhanced.critical_points)
        if reduction > 0:
            pct = 100 * reduction / len(result_standard.critical_points)
            print(f"  Reduction:            {reduction} points ({pct:.1f}%)")

        print("\nMetadata from enhanced extraction:")
        print(f"  Simplified: {result_enhanced.metadata.get('simplified')}")
        print(f"  Threshold:  {result_enhanced.metadata.get('simplification_threshold'):.2%}")

    finally:
        vtk_path.unlink(missing_ok=True)


# =============================================================================
# EXAMPLE 3: Standalone Scalar Field Simplification
# =============================================================================


def example_standalone_simplification():
    """
    Example 3: Standalone scalar field simplification.

    Demonstrates using simplify_scalar_field() independently for
    preprocessing or creating smoothed versions of data.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Standalone Scalar Field Simplification")
    print("=" * 70)

    # Create noisy surface
    n = 25
    grid = pv.ImageData(dimensions=(n, n, 1), spacing=(0.4, 0.4, 1.0), origin=(-5, -5, 0))

    x = np.linspace(-5, 5, n)
    y = np.linspace(-5, 5, n)
    xx, yy = np.meshgrid(x, y)
    zz = np.sin(xx) * np.cos(yy) + 0.15 * np.random.randn(n, n)

    grid["mobility"] = zz.ravel()

    with tempfile.NamedTemporaryFile(suffix=".vti", delete=False) as tmp:
        input_path = Path(tmp.name)
    grid.save(str(input_path))

    try:
        # Apply topological simplification
        print("\nSimplifying scalar field with 8% threshold...")
        simplified_path = simplify_scalar_field(
            input_path,
            persistence_threshold=0.08,
            scalar_name="mobility",
        )

        print(f"OK: Simplified file created: {simplified_path.name}")

        # Load both versions for comparison
        original = pv.read(str(input_path))
        simplified = pv.read(str(simplified_path))

        original_values = original["mobility"]
        simplified_values = simplified["mobility"]

        # Compare statistics
        print("\nScalar field comparison:")
        print(f"  Original range:    [{original_values.min():.4f}, {original_values.max():.4f}]")
        print(f"  Simplified range:  [{simplified_values.min():.4f}, {simplified_values.max():.4f}]")
        print(f"  Max difference:    {np.max(np.abs(original_values - simplified_values)):.6f}")
        print(f"  Mean difference:   {np.mean(np.abs(original_values - simplified_values)):.6f}")

        # You can now use the simplified field for further analysis
        print("\nThe simplified field can be used for:")
        print("  - Cleaner Morse-Smale extraction")
        print("  - Visualization without noise")
        print("  - Downstream topological analysis")

        # Cleanup
        simplified_path.unlink(missing_ok=True)

    finally:
        input_path.unlink(missing_ok=True)


# =============================================================================
# EXAMPLE 4: Post-Filtering by Persistence
# =============================================================================


def example_post_filtering():
    """
    Example 4: Post-filtering critical points by persistence.

    Demonstrates using filter_by_persistence() to refine results
    after extraction.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Post-Filtering by Persistence")
    print("=" * 70)

    # Create surface with multiple features
    n = 30
    grid = pv.ImageData(dimensions=(n, n, 1), spacing=(0.33, 0.33, 1.0), origin=(-5, -5, 0))

    x = np.linspace(-5, 5, n)
    y = np.linspace(-5, 5, n)
    xx, yy = np.meshgrid(x, y)

    # Two Gaussians + noise
    zz = (
        np.exp(-((xx - 1.5) ** 2 + (yy - 1.5) ** 2) / 2)
        + 0.5 * np.exp(-((xx + 1.5) ** 2 + (yy + 1.5) ** 2) / 2)
        + 0.05 * np.random.randn(n, n)
    )

    grid["mobility"] = zz.ravel()

    with tempfile.NamedTemporaryFile(suffix=".vti", delete=False) as tmp:
        vtk_path = Path(tmp.name)
    grid.save(str(vtk_path))

    try:
        # Extract all features (no filtering)
        result = compute_morse_smale(
            vtk_path,
            scalar_name="mobility",
            persistence_threshold=0.0,
        )

        print(f"\nInitial extraction: {len(result.critical_points)} critical points")

        # Apply progressive filtering
        thresholds = [0.02, 0.05, 0.10]
        for threshold in thresholds:
            # Note: This example shows the API, but filter_by_persistence
            # requires persistence values to be set on critical points.
            # In practice, use suggest_persistence_threshold for guidance.
            filtered = filter_by_persistence(
                result.critical_points,
                persistence_threshold=threshold,
                scalar_range=result.scalar_range,
            )
            print(f"  Threshold {threshold:.0%}: {len(filtered)} points remaining")

    finally:
        vtk_path.unlink(missing_ok=True)


# =============================================================================
# EXAMPLE 5: Automatic Threshold Selection
# =============================================================================


def example_threshold_selection():
    """
    Example 5: Automatic persistence threshold selection.

    Demonstrates using suggest_persistence_threshold() to automatically
    determine optimal simplification thresholds.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Automatic Threshold Selection")
    print("=" * 70)

    # Create surface
    n = 30
    grid = pv.ImageData(dimensions=(n, n, 1), spacing=(0.33, 0.33, 1.0), origin=(-5, -5, 0))

    x = np.linspace(-5, 5, n)
    y = np.linspace(-5, 5, n)
    xx, yy = np.meshgrid(x, y)
    zz = np.sin(xx) * np.cos(yy) + 0.1 * np.random.randn(n, n)

    grid["mobility"] = zz.ravel()

    with tempfile.NamedTemporaryFile(suffix=".vti", delete=False) as tmp:
        vtk_path = Path(tmp.name)
    grid.save(str(vtk_path))

    try:
        # First extraction with no filtering
        result = compute_morse_smale(
            vtk_path,
            scalar_name="mobility",
            persistence_threshold=0.0,
        )

        print(f"\nInitial features: {len(result.critical_points)} critical points")

        # Try different threshold selection methods
        methods = ["elbow", "gap", "quantile"]
        print("\nSuggested thresholds:")

        for method in methods:
            threshold = suggest_persistence_threshold(result, method=method)
            print(f"  {method:8s} method: {threshold:.2%}")

        # Use suggested threshold
        recommended_threshold = suggest_persistence_threshold(result, method="gap")
        print(f"\nUsing 'gap' method threshold: {recommended_threshold:.2%}")

        # Re-compute with suggested threshold
        result_filtered = compute_morse_smale(
            vtk_path,
            scalar_name="mobility",
            persistence_threshold=recommended_threshold,
        )

        print(f"Filtered features: {len(result_filtered.critical_points)} critical points")
        print(f"Reduction: {len(result.critical_points) - len(result_filtered.critical_points)} points")

    finally:
        vtk_path.unlink(missing_ok=True)


# =============================================================================
# EXAMPLE 6: Complete Workflow
# =============================================================================


def example_complete_workflow():
    """
    Example 6: Complete workflow for mobility surface analysis.

    Demonstrates end-to-end pipeline: simplification → extraction → analysis
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Complete Workflow for Mobility Surface Analysis")
    print("=" * 70)

    # Create realistic mobility surface
    n = 40
    grid = pv.ImageData(dimensions=(n, n, 1), spacing=(0.25, 0.25, 1.0), origin=(-5, -5, 0))

    x = np.linspace(-5, 5, n)
    y = np.linspace(-5, 5, n)
    xx, yy = np.meshgrid(x, y)

    # Simulated mobility: high in center, low at edges, with noise
    distance = np.sqrt(xx**2 + yy**2)
    mobility = 1.0 - 0.15 * distance + 0.08 * np.random.randn(n, n)
    mobility = np.clip(mobility, 0, 1)

    grid["mobility"] = mobility.ravel()

    with tempfile.NamedTemporaryFile(suffix=".vti", delete=False) as tmp:
        vtk_path = Path(tmp.name)
    grid.save(str(vtk_path))

    try:
        print("\nStep 1: Extract features without simplification")
        result_noisy = compute_morse_smale(
            vtk_path,
            scalar_name="mobility",
            persistence_threshold=0.0,
        )
        print(f"  Extracted {len(result_noisy.critical_points)} critical points")

        print("\nStep 2: Suggest optimal threshold")
        threshold = suggest_persistence_threshold(result_noisy, method="gap")
        print(f"  Suggested threshold: {threshold:.2%}")

        print("\nStep 3: Extract with pre-simplification and filtering")
        result_clean = compute_morse_smale(
            vtk_path,
            scalar_name="mobility",
            persistence_threshold=threshold,
            simplify_first=True,
            simplification_threshold=0.10,
        )
        print(f"  Extracted {len(result_clean.critical_points)} critical points")

        print("\nStep 4: Analyze significant features")
        maxima = result_clean.get_maxima()
        minima = result_clean.get_minima()
        saddles = result_clean.get_saddles()

        print(f"\n  Opportunity Hotspots (Maxima): {len(maxima)}")
        for i, cp in enumerate(sorted(maxima, key=lambda x: x.value, reverse=True)[:3]):
            print(f"    {i + 1}. Position ({cp.position[0]:.2f}, {cp.position[1]:.2f}), " f"Mobility: {cp.value:.3f}")

        print(f"\n  Poverty Traps (Minima): {len(minima)}")
        for i, cp in enumerate(sorted(minima, key=lambda x: x.value)[:3]):
            print(f"    {i + 1}. Position ({cp.position[0]:.2f}, {cp.position[1]:.2f}), " f"Mobility: {cp.value:.3f}")

        print(f"\n  Transition Points (Saddles): {len(saddles)}")
        print("    These represent critical decision points in mobility pathways")

        print("\nStep 5: Topological summary")
        print(f"  Separatrices: {len(result_clean.separatrices_1d)} paths")
        print(f"  Scalar range: [{result_clean.scalar_range[0]:.3f}, {result_clean.scalar_range[1]:.3f}]")
        print(f"  Simplification applied: {result_clean.metadata.get('simplified', False)}")

    finally:
        vtk_path.unlink(missing_ok=True)


# =============================================================================
# MAIN: Run All Examples
# =============================================================================


def main():
    """Run all examples demonstrating enhanced TTK integration."""
    print("\n")
    print("=" * 70)
    print("  Enhanced TTK Integration - Comprehensive Examples")
    print("=" * 70)
    print("\nTask 6.5.2: Migration to Centralized TTK Utilities")
    print("Demonstrates new features for cleaner topological analysis\n")

    # Check TTK availability
    from shared.ttk_utils import is_ttk_available

    if not is_ttk_available():
        print("WARNING: TTK not available!")
        print("\nPlease install TTK first:")
        print("  conda create -n ttk_env python=3.11")
        print("  conda install -n ttk_env -c conda-forge topologytoolkit")
        print("\nSee docs/TTK_SETUP.md for details.")
        return

    print("OK: TTK environment detected\n")
    # Run examples
    try:
        example_basic_morse_smale()
        example_pre_simplification()
        example_standalone_simplification()
        example_post_filtering()
        example_threshold_selection()
        example_complete_workflow()

        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70)
        print("\nNext steps:")
        print("  - Adapt these patterns to your mobility data")
        print("  - Experiment with different threshold values")
        print("  - Combine with visualization (see poverty_tda/viz/)")
        print("  - Use results for intervention analysis")
        print("\nFor more information:")
        print("  - docs/TTK_SETUP.md - Installation guide")
        print("  - docs/TASK_6_5_1_HANDOFF.md - TTK integration details")
        print("  - tests/poverty/topology/ - Additional test examples")

    except Exception as e:
        print(f"\nERROR running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
