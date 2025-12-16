"""
Quick test to verify the migration validation groupby fix.
"""

import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from poverty_tda.validation.migration_validation import compute_escape_rate_by_severity

# Create synthetic test data
np.random.seed(42)
n = 100

# Create GeoDataFrame
points = [Point(x, y) for x, y in zip(np.random.rand(n), np.random.rand(n))]
gdf = gpd.GeoDataFrame(
    {
        "geometry": points,
        "ms_basin": np.random.randint(0, 5, size=n),
        "mean_imd": np.random.rand(n) * 100,
        "escape_ratio": np.random.rand(n),
    }
)

try:
    result = compute_escape_rate_by_severity(
        gdf, basin_column="ms_basin", severity_column="mean_imd", escape_column="escape_ratio", n_quantiles=4
    )

    print("✅ compute_escape_rate_by_severity() works correctly!")
    print(f"\nResult shape: {result.shape}")
    print(f"Columns: {result.columns.tolist()}")
    print("\nFirst few rows:")
    print(result.head())

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
