"""
Quick test of TTK topological simplification functionality.

Creates a synthetic Gaussian surface and tests the simplification function.
"""

import tempfile
from pathlib import Path

import numpy as np
import pyvista as pv

from poverty_tda.topology.morse_smale import (
    simplify_scalar_field,
    compute_morse_smale,
)


def test_simplification():
    """Test topological simplification on Gaussian surface."""
    # Create Gaussian surface with noise
    n = 30
    grid = pv.ImageData(
        dimensions=(n, n, 1),
        spacing=(0.33, 0.33, 1.0),
        origin=(-5, -5, 0),
    )

    x = np.linspace(-5, 5, n)
    y = np.linspace(-5, 5, n)
    xx, yy = np.meshgrid(x, y)

    # Gaussian + small noise
    zz = np.exp(-(xx**2 + yy**2) / 4) + 0.05 * np.random.randn(n, n)

    grid["mobility"] = zz.ravel()

    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=".vti", delete=False) as tmp:
        input_path = Path(tmp.name)

    grid.save(str(input_path))

    try:
        # Test simplification
        print("Testing simplification with 5% threshold...")
        simplified_path = simplify_scalar_field(input_path, persistence_threshold=0.05, scalar_name="mobility")

        print(f"✓ Simplified file created: {simplified_path}")

        # Compute Morse-Smale on original
        print("\nComputing Morse-Smale on original (noisy) surface...")
        result_original = compute_morse_smale(input_path, scalar_name="mobility", persistence_threshold=0.0)
        print(
            f"  Original: {result_original.n_minima} minima, "
            f"{result_original.n_saddles} saddles, "
            f"{result_original.n_maxima} maxima"
        )

        # Compute Morse-Smale on simplified
        print("\nComputing Morse-Smale on simplified surface...")
        result_simplified = compute_morse_smale(simplified_path, scalar_name="mobility", persistence_threshold=0.0)
        print(
            f"  Simplified: {result_simplified.n_minima} minima, "
            f"{result_simplified.n_saddles} saddles, "
            f"{result_simplified.n_maxima} maxima"
        )

        # Should have fewer critical points after simplification
        total_original = len(result_original.critical_points)
        total_simplified = len(result_simplified.critical_points)

        print(f"\nTotal critical points reduced: {total_original} → {total_simplified}")

        if total_simplified < total_original:
            print("✓ Simplification successfully reduced topological noise!")
        else:
            print("⚠ Warning: Simplification did not reduce critical points")

        # Cleanup
        simplified_path.unlink(missing_ok=True)

    finally:
        input_path.unlink(missing_ok=True)


if __name__ == "__main__":
    test_simplification()
