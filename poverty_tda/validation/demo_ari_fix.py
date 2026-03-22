"""
Simple demonstration that the ARI matrix fix works.
Run this to verify the fix is working correctly.
"""

import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from poverty_tda.validation.results_framework import record_comparison_result

print("=" * 70)
print("ARI MATRIX FIX DEMONSTRATION")
print("=" * 70)

# Create synthetic test data
np.random.seed(42)
n = 100

print(f"\nCreating test data with {n} observations...")

points = [Point(x, y) for x, y in zip(np.random.rand(n), np.random.rand(n))]

# Create different cluster assignments
base_labels = np.array([0] * 33 + [1] * 33 + [2] * 34)
ms_labels = base_labels.copy()
km_labels = base_labels.copy()

# Swap some labels to make them similar but not identical
swap_idx = np.random.choice(n, size=15, replace=False)
km_labels[swap_idx] = (km_labels[swap_idx] + 1) % 3

gdf = gpd.GeoDataFrame(
    {
        "geometry": points,
        "ms_basin": ms_labels,
        "kmeans": km_labels,
        "life_expectancy": np.random.rand(n) * 20 + 70,
    }
)

print("✓ Test data created")

# Call the fixed function
print("\nCalling record_comparison_result()...")

result = record_comparison_result(
    name="demo_ari_fix",
    description="Demonstration that ARI matrix is now populated",
    region="Test Region",
    gdf=gdf,
    method_columns={
        "Morse-Smale": "ms_basin",
        "K-means": "kmeans",
    },
    outcome_column="life_expectancy",
    random_seed=42,
)

print("✓ Function executed successfully")

# Display results
print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)

print(f"\n📊 Methods analyzed: {len(result.methods)}")
for method in result.methods:
    print(f"  - {method.name}: {method.n_clusters} clusters, η² = {method.eta_squared:.4f}")

print(f"\n🔗 ARI Matrix entries: {len(result.ari_matrix)}")
if result.ari_matrix:
    for pair, ari in result.ari_matrix.items():
        print(f"  ✓ {pair}: ARI = {ari:.4f}")
else:
    print("  ❌ EMPTY (bug not fixed)")

print("\n📈 Per-Method ARI Scores:")
for method in result.methods:
    print(f"\n  {method.name}:")
    if method.ari_vs_others:
        for other, ari in method.ari_vs_others.items():
            print(f"    ✓ vs {other}: {ari:.4f}")
    else:
        print("    ❌ No ARI scores (bug not fixed)")

# Validation
print("\n" + "=" * 70)
print("VALIDATION CHECKS")
print("=" * 70)

checks = []

# Check 1: ARI matrix populated
if result.ari_matrix and len(result.ari_matrix) > 0:
    print("✅ Check 1: ARI matrix is populated")
    checks.append(True)
else:
    print("❌ Check 1: ARI matrix is empty")
    checks.append(False)

# Check 2: All methods have ari_vs_others
if all(m.ari_vs_others for m in result.methods):
    print("✅ Check 2: All methods have ari_vs_others populated")
    checks.append(True)
else:
    print("❌ Check 2: Some methods missing ari_vs_others")
    checks.append(False)

# Check 3: ARI values in valid range
ari_values = list(result.ari_matrix.values())
if ari_values and all(-1 <= v <= 1 for v in ari_values):
    print("✅ Check 3: ARI values in valid range [-1, 1]")
    checks.append(True)
else:
    print("❌ Check 3: ARI values out of range")
    checks.append(False)

# Check 4: Symmetry
if len(result.methods) == 2:
    m1_ari = result.methods[0].ari_vs_others.get(result.methods[1].name)
    m2_ari = result.methods[1].ari_vs_others.get(result.methods[0].name)
    if m1_ari is not None and m2_ari is not None and m1_ari == m2_ari:
        print("✅ Check 4: ARI scores are symmetric")
        checks.append(True)
    else:
        print("❌ Check 4: ARI scores not symmetric")
        checks.append(False)

# Summary
print("\n" + "=" * 70)
passed = sum(checks)
total = len(checks)
print(f"RESULT: {passed}/{total} checks passed")
print("=" * 70)

if passed == total:
    print("\n🎉 SUCCESS! All checks passed - the ARI matrix bug is FIXED!")
    print("\nThe Liverpool comparison can now be re-run to generate")
    print("proper ARI-based agreement analysis as required.")
else:
    print(f"\n⚠️  WARNING: {total - passed} check(s) failed")
    print("Review the output above for details.")

print("\n" + "=" * 70)
