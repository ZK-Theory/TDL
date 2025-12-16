"""Run Greater Manchester comparison."""

import time
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import vtk
from esda.getisord import G_Local
from esda.moran import Moran_Local
from libpysal.weights import KNN, Queen
from scipy.interpolate import griddata
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler
from vtk.util import numpy_support

from poverty_tda.topology.mapper import compute_mapper
from poverty_tda.topology.morse_smale import compute_morse_smale
from poverty_tda.validation.spatial_comparison import mapper_to_partition

warnings.filterwarnings("ignore")

print("=== GREATER MANCHESTER FULL COMPARISON ===")
t0 = time.time()

# 1. Load data
print("1. Loading data...", flush=True)
gdf = gpd.read_file("poverty_tda/data/raw/boundaries/lsoa_2021/lsoa_2021_boundaries.geojson")
imd = pd.read_csv("poverty_tda/validation/data/england_imd_2019.csv")
imd_cols = [
    "LSOA code (2011)",
    "Index of Multiple Deprivation (IMD) Score",
    "Local Authority District code (2019)",
    "Local Authority District name (2019)",
]
imd_subset = imd[imd_cols].copy()
imd_subset.columns = ["lsoa_code", "imd_score", "lad_code", "lad_name"]
gdf = gdf.merge(imd_subset, left_on="LSOA21CD", right_on="lsoa_code", how="inner")

# Greater Manchester LADs
gm_lads = [
    "Bolton",
    "Bury",
    "Manchester",
    "Oldham",
    "Rochdale",
    "Salford",
    "Stockport",
    "Tameside",
    "Trafford",
    "Wigan",
]
gdf = gdf[gdf["lad_name"].isin(gm_lads)].reset_index(drop=True)
gdf["mobility"] = -gdf["imd_score"]
gdf["mobility"] = (gdf["mobility"] - gdf["mobility"].min()) / (gdf["mobility"].max() - gdf["mobility"].min())

le = pd.read_csv(str(Path(__file__).parent.parent.parent / "data/raw/outcomes/life_expectancy_processed.csv"))
gdf = gdf.merge(
    le[["area_code", "life_expectancy_male"]],
    left_on="lad_code",
    right_on="area_code",
    how="left",
)
gdf = gdf.dropna(subset=["life_expectancy_male"])
gdf = gdf.to_crs("EPSG:27700")
print(f"   {len(gdf)} LSOAs loaded ({time.time() - t0:.1f}s)", flush=True)

# 2. Create mobility surface
print("2. Creating 100x100 mobility surface...", flush=True)
centroids = gdf.geometry.centroid
x, y = centroids.x.values, centroids.y.values
z = gdf["mobility"].values

buffer = 1000
x_min, x_max = x.min() - buffer, x.max() + buffer
y_min, y_max = y.min() - buffer, y.max() + buffer

grid_size = 100
xi = np.linspace(x_min, x_max, grid_size)
yi = np.linspace(y_min, y_max, grid_size)
xi_grid, yi_grid = np.meshgrid(xi, yi)

zi = griddata((x, y), z, (xi_grid, yi_grid), method="cubic")
zi_nn = griddata((x, y), z, (xi_grid, yi_grid), method="nearest")
zi = np.where(np.isnan(zi), zi_nn, zi)

image = vtk.vtkImageData()
image.SetDimensions(grid_size, grid_size, 1)
image.SetSpacing((x_max - x_min) / (grid_size - 1), (y_max - y_min) / (grid_size - 1), 1.0)
image.SetOrigin(x_min, y_min, 0.0)
mobility_array = numpy_support.numpy_to_vtk(zi.ravel("F").astype(np.float32))
mobility_array.SetName("mobility")
image.GetPointData().AddArray(mobility_array)
image.GetPointData().SetActiveScalars("mobility")

vtk_path = Path("poverty_tda/validation/mobility_surface_greater_manchester.vti")
writer = vtk.vtkXMLImageDataWriter()
writer.SetFileName(str(vtk_path))
writer.SetInputData(image)
writer.Write()
print(f"   Surface saved ({time.time() - t0:.1f}s)", flush=True)

# 3. Compute Morse-Smale
print("3. Computing Morse-Smale basins...", flush=True)
ms_result = compute_morse_smale(vtk_path, persistence_threshold=0.05)

reader = vtk.vtkXMLImageDataReader()
reader.SetFileName(str(vtk_path))
reader.Update()
img = reader.GetOutput()
dims, origin, spacing = img.GetDimensions(), img.GetOrigin(), img.GetSpacing()

x_idx = np.clip(((x - origin[0]) / spacing[0]).astype(int), 0, dims[0] - 1)
y_idx = np.clip(((y - origin[1]) / spacing[1]).astype(int), 0, dims[1] - 1)
gdf["ms_basin"] = ms_result.ascending_manifold.reshape(dims[1], dims[0])[y_idx, x_idx]
print(f"   {gdf['ms_basin'].nunique()} basins ({time.time() - t0:.1f}s)", flush=True)

# 4. All methods
print("4. Applying all methods...", flush=True)

X = np.column_stack([x, y, gdf["mobility"].values])
X_scaled = StandardScaler().fit_transform(X)

# K-means
gdf["kmeans"] = KMeans(n_clusters=10, random_state=42, n_init=10).fit_predict(X_scaled)

# DBSCAN
gdf["dbscan"] = DBSCAN(eps=0.3, min_samples=10).fit_predict(X_scaled)

# LISA
w = Queen.from_dataframe(gdf, use_index=False)
w.transform = "R"
lisa = Moran_Local(gdf["mobility"].values, w, permutations=99)
gdf["lisa"] = "NS"
for q, label in {1: "HH", 2: "LH", 3: "LL", 4: "HL"}.items():
    mask = (lisa.q == q) & (lisa.p_sim < 0.05)
    gdf.loc[mask, "lisa"] = label

# Gi*
w_knn = KNN.from_dataframe(gdf, k=8)
gi = G_Local(gdf["mobility"].values, w_knn, permutations=99, star=True)
gdf["gi"] = "NS"
gdf.loc[(gi.Zs > 0) & (gi.p_sim < 0.05), "gi"] = "Hot"
gdf.loc[(gi.Zs < 0) & (gi.p_sim < 0.05), "gi"] = "Cold"

# Mapper
features_df = pd.DataFrame(X_scaled, columns=["x", "y", "mobility"])
mapper_graph = compute_mapper(
    features_df,
    features_df["mobility"].values,
    feature_columns=["x", "y", "mobility"],
    n_cubes=15,
    overlap=0.5,
    clustering="single_linkage",
)
gdf["mapper"] = mapper_to_partition(mapper_graph, features_df, assignment_method="dominant")

print(f"   Methods applied ({time.time() - t0:.1f}s)", flush=True)

# 5. Bootstrap CIs
print("5. Bootstrap CIs (1000 iterations)...", flush=True)
outcome = gdf["life_expectancy_male"].values


def eta_sq(labels, values):
    unique = np.unique(labels)
    groups = [values[labels == c] for c in unique if np.sum(labels == c) > 0]
    if len(groups) < 2:
        return 0.0
    gm = np.mean(values)
    ss_t = np.sum((values - gm) ** 2)
    ss_b = sum(len(g) * (np.mean(g) - gm) ** 2 for g in groups)
    return ss_b / ss_t if ss_t > 0 else 0.0


def bootstrap_ci(labels, values, n_boot=1000):
    n = len(labels)
    point = eta_sq(labels, values)
    etas = []
    rng = np.random.default_rng(42)
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        etas.append(eta_sq(labels[idx], values[idx]))
    return point, np.percentile(etas, 2.5), np.percentile(etas, 97.5), np.std(etas)


methods = [
    ("Morse-Smale (TDA)", gdf["ms_basin"].values, gdf["ms_basin"].nunique()),
    ("K-means", gdf["kmeans"].values, 10),
    ("DBSCAN", gdf["dbscan"].values, gdf["dbscan"].nunique()),
    ("Mapper (TDA)", gdf["mapper"].values, gdf["mapper"].nunique()),
    ("LISA", pd.Categorical(gdf["lisa"]).codes, gdf["lisa"].nunique()),
    ("Gi*", pd.Categorical(gdf["gi"]).codes, gdf["gi"].nunique()),
]

print("\n=== GREATER MANCHESTER FULL RESULTS ===")
print(f"LSOAs: {len(gdf)}")
print(f"\n{'Method':<20} | {'n':>4} | {'eta2':>7} | {'95% CI':<20} | {'SE':>6}")
print("-" * 70)

results = []
for name, labels, ncl in methods:
    eta2, lo, hi, se = bootstrap_ci(labels, outcome, 1000)
    print(f"{name:<20} | {ncl:>4} | {eta2:>7.4f} | [{lo:.4f}, {hi:.4f}] | {se:>6.4f}")
    results.append((name, ncl, eta2, lo, hi, se))

print(f"\nTotal time: {time.time() - t0:.1f}s")
