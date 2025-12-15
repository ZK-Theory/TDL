"""
TTK Basin Analysis Example for Poverty TDA.

This script demonstrates the use of TTK topological simplification and
Morse-Smale complex computation for identifying poverty traps and
opportunity basins in mobility landscapes.

Shows:
1. Impact of topological simplification on trap identification
2. Critical point filtering workflow
3. Persistence-based basin hierarchy

Usage:
    python poverty_tda/viz/examples/ttk_basin_analysis.py

Requirements:
    - TTK environment configured (see docs/TTK_SETUP.md)
    - Sample mobility data (or synthetic data will be generated)

License: Open Government Licence v3.0
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from poverty_tda.topology import compute_morse_smale, filter_by_persistence  # noqa: E402
from poverty_tda.viz.ttk_plots import (  # noqa: E402
    plot_critical_point_persistence,
    plot_simplification_comparison,
)
from shared.ttk_utils import is_ttk_available  # noqa: E402

# Try to import pyvista
try:
    import pyvista as pv

    HAS_PYVISTA = True
except ImportError:
    HAS_PYVISTA = False
    print("WARNING: PyVista not available. VTK visualization limited.")


def create_synthetic_mobility_surface(output_path: Path, nx: int = 50, ny: int = 50) -> Path:
    """
    Create synthetic mobility surface for demonstration.

    Creates a 2D scalar field representing economic mobility with:
    - Multiple local minima (poverty traps)
    - Saddle points (transition zones)
    - Local maxima (opportunity peaks)

    Args:
        output_path: Path to save VTI file.
        nx, ny: Grid resolution.

    Returns:
        Path to created VTI file.
    """
    if not HAS_PYVISTA:
        raise ImportError("PyVista required for synthetic data generation")

    print(f"Creating synthetic mobility surface ({nx}×{ny})...")

    # Create coordinate grids
    x = np.linspace(0, 10, nx)
    y = np.linspace(0, 10, ny)
    X, Y = np.meshgrid(x, y)

    # Create synthetic mobility landscape
    # Multiple Gaussian peaks and valleys
    mobility = np.zeros_like(X)

    # Add peaks (opportunities)
    mobility += 0.8 * np.exp(-((X - 2) ** 2 + (Y - 2) ** 2) / 2)
    mobility += 0.6 * np.exp(-((X - 8) ** 2 + (Y - 7) ** 2) / 3)

    # Add valleys (traps)
    mobility -= 0.5 * np.exp(-((X - 5) ** 2 + (Y - 5) ** 2) / 1.5)
    mobility -= 0.4 * np.exp(-((X - 7) ** 2 + (Y - 3) ** 2) / 2)

    # Add some noise
    np.random.seed(42)
    mobility += 0.05 * np.random.randn(*X.shape)

    # Normalize to [0, 1]
    mobility = (mobility - mobility.min()) / (mobility.max() - mobility.min())

    # Create VTK structured grid
    grid = pv.StructuredGrid()
    grid.points = np.c_[X.ravel(), Y.ravel(), np.zeros(X.size)].astype(np.float32)
    grid.dimensions = (nx, ny, 1)
    grid["mobility"] = mobility.ravel()

    # Save to VTI
    output_path.parent.mkdir(parents=True, exist_ok=True)
    grid.save(output_path)

    print(f"Synthetic surface saved to {output_path}")
    return output_path


def analyze_simplification_impact(vti_path: Path, thresholds: list[float]) -> None:
    """
    Demonstrate impact of different simplification thresholds.

    Args:
        vti_path: Path to mobility VTI file.
        thresholds: List of persistence thresholds to test.
    """
    print("\n" + "=" * 60)
    print("STEP 1: Simplification Impact Analysis")
    print("=" * 60)

    for threshold in thresholds:
        print(f"\nSimplification threshold: {threshold:.1%}")

        # Compute Morse-Smale with simplification
        result = compute_morse_smale(
            vti_path,
            simplify_first=True,
            simplification_threshold=threshold,
            persistence_threshold=0.02,  # Fine-grained extraction
        )

        print(f"  Critical points found: {len(result.critical_points)}")

        # Count by type
        n_minima = sum(1 for cp in result.critical_points if cp.point_type == 0)
        n_saddles = sum(1 for cp in result.critical_points if cp.point_type == 1)
        n_maxima = sum(1 for cp in result.critical_points if cp.point_type == 2)

        print(f"    Minima (traps): {n_minima}")
        print(f"    Saddles: {n_saddles}")
        print(f"    Maxima (peaks): {n_maxima}")

        # Visualize if first threshold
        if threshold == thresholds[0]:
            print("  Generating visualization...")
            fig = plot_simplification_comparison(vti_path, result, simplification_threshold=threshold, figsize=(16, 7))
            plt.savefig(
                Path("poverty_tda/viz/outputs") / f"simplification_{threshold:.0%}.png",
                dpi=150,
                bbox_inches="tight",
            )
            plt.close(fig)
            print("  Visualization saved.")


def demonstrate_critical_point_filtering(vti_path: Path) -> None:
    """
    Show critical point filtering workflow.

    Args:
        vti_path: Path to mobility VTI file.
    """
    print("\n" + "=" * 60)
    print("STEP 2: Critical Point Filtering Workflow")
    print("=" * 60)

    # Extract all critical points (no threshold)
    print("\nExtracting all critical points...")
    result_all = compute_morse_smale(vti_path, persistence_threshold=0.0)

    print(f"  Total critical points: {len(result_all.critical_points)}")

    # Apply post-processing filters
    filter_thresholds = [0.01, 0.05, 0.10]

    for threshold in filter_thresholds:
        filtered_points = filter_by_persistence(
            result_all.critical_points,
            persistence_threshold=threshold,
            scalar_range=result_all.scalar_range,
        )

        print(f"\nFiltered with threshold {threshold:.1%}: {len(filtered_points)} points")

        # Count by type
        n_minima = sum(1 for cp in filtered_points if cp.point_type == 0)
        n_saddles = sum(1 for cp in filtered_points if cp.point_type == 1)
        n_maxima = sum(1 for cp in filtered_points if cp.point_type == 2)

        print(f"    Minima: {n_minima}, Saddles: {n_saddles}, Maxima: {n_maxima}")


def visualize_persistence_hierarchy(vti_path: Path) -> None:
    """
    Visualize persistence-based basin hierarchy.

    Args:
        vti_path: Path to mobility VTI file.
    """
    print("\n" + "=" * 60)
    print("STEP 3: Persistence-Based Basin Hierarchy")
    print("=" * 60)

    # Compute with moderate threshold
    print("\nComputing Morse-Smale complex...")
    result = compute_morse_smale(vti_path, persistence_threshold=0.05)

    print(f"  Critical points: {len(result.critical_points)}")

    # Create persistence diagram
    print("  Generating persistence diagram...")
    fig = plot_critical_point_persistence(
        result.critical_points,
        title="Poverty Trap Persistence Hierarchy",
        color_by_type=True,
        geographic_overlay=True,
        bounds=(0, 10, 0, 10),  # Synthetic data bounds
        figsize=(14, 9),
    )

    output_path = Path("poverty_tda/viz/outputs/persistence_hierarchy.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Persistence diagram saved to {output_path}")

    # Analyze persistence distribution
    persistence_values = [cp.persistence for cp in result.critical_points]
    print("\nPersistence Statistics:")
    print(f"  Min: {np.min(persistence_values):.4f}")
    print(f"  Median: {np.median(persistence_values):.4f}")
    print(f"  Max: {np.max(persistence_values):.4f}")

    # Identify most significant traps (high persistence minima)
    minima = [cp for cp in result.critical_points if cp.point_type == 0]
    if minima:
        minima_sorted = sorted(minima, key=lambda cp: cp.persistence, reverse=True)
        print("\nTop 3 Most Significant Poverty Traps:")
        for i, cp in enumerate(minima_sorted[:3], 1):
            print(f"  {i}. Value: {cp.value:.4f}, Persistence: {cp.persistence:.4f}")
            print(f"     Position: ({cp.position[0]:.2f}, {cp.position[1]:.2f})")


def main():
    """Main execution function."""
    print("=" * 60)
    print("TTK Basin Analysis Example")
    print("=" * 60)

    # Check TTK availability
    if not is_ttk_available():
        print("\nWARNING: TTK not available.")
        print("Some features will be limited. See docs/TTK_SETUP.md for setup.")

    if not HAS_PYVISTA:
        print("\nERROR: PyVista is required for this example.")
        print("Install: pip install pyvista")
        return 1

    # Create or use synthetic data
    vti_path = Path("poverty_tda/viz/outputs/synthetic_mobility.vti")

    if not vti_path.exists():
        print("\nGenerating synthetic mobility surface...")
        vti_path = create_synthetic_mobility_surface(vti_path)
    else:
        print(f"\nUsing existing data: {vti_path}")

    # Run analyses
    try:
        # Step 1: Simplification impact
        analyze_simplification_impact(vti_path, thresholds=[0.05, 0.10, 0.15])

        # Step 2: Filtering workflow
        demonstrate_critical_point_filtering(vti_path)

        # Step 3: Persistence hierarchy
        visualize_persistence_hierarchy(vti_path)

        print("\n" + "=" * 60)
        print("Analysis Complete!")
        print("=" * 60)
        print("\nOutputs saved to: poverty_tda/viz/outputs/")
        print("\nKey Findings:")
        print("- Simplification removes noise while preserving significant features")
        print("- Persistence filtering enables multi-scale trap identification")
        print("- High-persistence minima indicate deep, stable poverty traps")
        print("\nNext Steps:")
        print("- Apply to real mobility data (Opportunity Atlas)")
        print("- Integrate with intervention analysis")
        print("- Develop trap classification models")

        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
