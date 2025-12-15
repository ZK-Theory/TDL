"""
Quick test: Verify TTK persistence computation works.
"""

import numpy as np

from financial_tda.topology.filtration import compute_persistence_ttk
from shared.ttk_utils import is_ttk_available

if __name__ == "__main__":
    print("Checking TTK availability...")
    if not is_ttk_available():
        print("TTK not available - skipping test")
        exit(0)

    print("TTK available! Testing persistence computation...")

    # Create simple 2D point cloud
    np.random.seed(42)
    n_points = 50
    point_cloud = np.random.randn(n_points, 2)

    print(f"Computing persistence for {n_points} points...")
    try:
        diagram = compute_persistence_ttk(point_cloud)
        print(f"✓ Success! Found {len(diagram)} persistence features")
        print(f"  Dimensions: {np.unique(diagram[:, 2])}")
        print(f"  Max persistence: {(diagram[:, 1] - diagram[:, 0]).max():.4f}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback

        traceback.print_exc()
        exit(1)

    print("\n✓ TTK persistence integration test passed!")
