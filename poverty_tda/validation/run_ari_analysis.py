"""
Task 9.5.3: Agreement Analysis (ARI)

Computes Adjusted Rand Index between Morse-Smale basins and
alternative clustering methods to assess method agreement.
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyvista as pv
from scipy import stats
from sklearn.metrics import adjusted_rand_score

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from poverty_tda.topology.morse_smale import compute_morse_smale
from poverty_tda.validation.spatial_comparison import (
    compute_kmeans_clusters,
    compute_lisa_clusters,
    compute_getis_ord_hotspots,
    compute_dbscan_clusters,
    bootstrap_ari_ci,
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def assign_lsoas_to_ms_basins(gdf: gpd.GeoDataFrame, vti_path: Path, persistence: float = 0.05):
    """Assign LSOAs to Morse-Smale basins."""
    # Load VTI
    grid = pv.read(str(vti_path))
    origin = np.array(grid.origin[:2])
    spacing = np.array(grid.spacing[:2])
    dims = np.array(grid.dimensions[:2])
    
    # Compute MS
    ms_result = compute_morse_smale(vti_path, scalar_name="mobility", persistence_threshold=persistence)
    
    # Reproject to BNG if needed
    if gdf.crs and gdf.crs.to_epsg() != 27700:
        gdf = gdf.to_crs(epsg=27700)
    
    # Get centroids and assign basins
    centroids = gdf.geometry.centroid
    x = centroids.x.values
    y = centroids.y.values
    
    i = np.clip(((x - origin[0]) / spacing[0]).astype(int), 0, dims[0] - 1)
    j = np.clip(((y - origin[1]) / spacing[1]).astype(int), 0, dims[1] - 1)
    flat_idx = np.clip(i + j * dims[0], 0, dims[0] * dims[1] - 1)
    
    gdf = gdf.copy()
    gdf['ms_basin'] = ms_result.descending_manifold[flat_idx]
    
    return gdf, ms_result


def load_region_data(region: str):
    """Load LSOA data for a region."""
    gdf = gpd.read_file("poverty_tda/data/raw/boundaries/lsoa_2021/lsoa_2021_boundaries.geojson")
    
    # Load IMD
    imd = pd.read_csv("poverty_tda/validation/data/england_imd_2019.csv")
    imd = imd.rename(columns={
        'LSOA code (2011)': 'lsoa_code_2011',
        'Local Authority District code (2019)': 'lad_code',
        'Index of Multiple Deprivation (IMD) Score': 'imd_score'
    })
    
    gdf['lsoa_code_2011'] = gdf['LSOA21CD'].str[:9]
    gdf = gdf.merge(imd[['lsoa_code_2011', 'lad_code', 'imd_score']], on='lsoa_code_2011', how='left')
    
    # Filter by region
    if region == 'west_midlands':
        lads = ['E08000025', 'E08000026', 'E08000027', 'E08000028', 
                'E08000029', 'E08000030', 'E08000031']
        vti = Path("poverty_tda/validation/mobility_surface_wm_150.vti")
    elif region == 'greater_manchester':
        lads = ['E08000001', 'E08000002', 'E08000003', 'E08000004', 'E08000005',
                'E08000006', 'E08000007', 'E08000008', 'E08000009', 'E08000010']
        vti = Path("poverty_tda/validation/mobility_surface_greater_manchester.vti")
    else:
        raise ValueError(f"Unknown region: {region}")
    
    gdf = gdf[gdf['lad_code'].isin(lads)]
    return gdf, vti


def compute_ari_matrix(gdf, method_columns: dict):
    """Compute pairwise ARI between all methods."""
    methods = list(method_columns.keys())
    results = []
    
    for i, m1 in enumerate(methods):
        for m2 in methods[i+1:]:
            col1 = method_columns[m1]
            col2 = method_columns[m2]
            
            labels1 = pd.Categorical(gdf[col1]).codes
            labels2 = pd.Categorical(gdf[col2]).codes
            
            # Bootstrap ARI
            bootstrap = bootstrap_ari_ci(labels1, labels2, n_bootstrap=500)
            
            results.append({
                'method1': m1,
                'method2': m2,
                'ari': bootstrap.point_estimate,
                'ci_lower': bootstrap.ci_lower,
                'ci_upper': bootstrap.ci_upper,
                'se': bootstrap.std_error
            })
    
    return pd.DataFrame(results)


def main():
    """Run ARI agreement analysis."""
    
    print("=" * 70)
    print("TASK 9.5.3: Method Agreement Analysis (Adjusted Rand Index)")
    print("=" * 70)
    
    all_results = []
    
    for region in ['west_midlands', 'greater_manchester']:
        print(f"\n{'='*70}")
        print(f"Region: {region.upper()}")
        print(f"{'='*70}")
        
        # Load data
        print("\n1. Loading data...")
        gdf, vti_path = load_region_data(region)
        print(f"   {len(gdf)} LSOAs loaded")
        
        if not vti_path.exists():
            print(f"   VTI not found: {vti_path}, skipping region")
            continue
        
        # Assign MS basins
        print("\n2. Computing MS basins...")
        gdf, ms_result = assign_lsoas_to_ms_basins(gdf, vti_path)
        n_ms = gdf['ms_basin'].nunique()
        print(f"   {n_ms} MS basins")
        
        # Compute alternative methods
        print("\n3. Computing alternative clusterings...")
        
        # K-means with same n_clusters as MS
        gdf = compute_kmeans_clusters(gdf, 'imd_score', n_clusters=n_ms, use_coordinates=True)
        print(f"   K-means: {gdf['kmeans_cluster'].nunique()} clusters")
        
        # K-means with default (auto) n_clusters
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        
        centroids = gdf.geometry.centroid
        X = np.column_stack([centroids.x, centroids.y, gdf['imd_score'].fillna(gdf['imd_score'].median())])
        X_scaled = StandardScaler().fit_transform(X)
        gdf['kmeans_10'] = KMeans(n_clusters=10, random_state=42, n_init=10).fit_predict(X_scaled)
        
        # LISA & Gi* (these produce few categories)
        try:
            gdf = compute_lisa_clusters(gdf, 'imd_score')
            gdf = compute_getis_ord_hotspots(gdf, 'imd_score')
        except Exception as e:
            logger.warning(f"Spatial methods failed: {e}")
            gdf['lisa_cluster'] = 0
            gdf['gi_classification'] = 0
        
        # DBSCAN
        gdf = compute_dbscan_clusters(gdf, 'imd_score')
        print(f"   DBSCAN: {gdf['dbscan_cluster'].nunique()} clusters")
        
        # Compute ARI matrix
        print("\n4. Computing ARI matrix...")
        method_cols = {
            'MS': 'ms_basin',
            'K-means(MS)': 'kmeans_cluster',  # Same n as MS
            'K-means(10)': 'kmeans_10',       # Fixed k=10
            'LISA': 'lisa_cluster',
            'Gi*': 'gi_classification',
            'DBSCAN': 'dbscan_cluster'
        }
        
        ari_df = compute_ari_matrix(gdf, method_cols)
        ari_df['region'] = region
        all_results.append(ari_df)
        
        # Print key results
        print("\n   Method Pair                     ARI       95% CI")
        print("   " + "-" * 55)
        for _, row in ari_df.iterrows():
            pair = f"{row['method1']} vs {row['method2']}"
            ci = f"[{row['ci_lower']:.3f}, {row['ci_upper']:.3f}]"
            print(f"   {pair:<30} {row['ari']:.3f}   {ci}")
    
    # Combined summary
    combined = pd.concat(all_results, ignore_index=True)
    
    print("\n" + "=" * 70)
    print("SUMMARY: MS vs K-means Agreement")
    print("=" * 70)
    
    ms_kmeans = combined[combined['method2'].str.startswith('K-means')]
    ms_kmeans = ms_kmeans[ms_kmeans['method1'] == 'MS']
    
    for _, row in ms_kmeans.iterrows():
        print(f"   {row['region']}: MS vs {row['method2']}: ARI = {row['ari']:.3f}")
    
    # Interpretation
    mean_ari = ms_kmeans['ari'].mean()
    print(f"\n   Mean ARI(MS, K-means): {mean_ari:.3f}")
    
    if mean_ari > 0.7:
        print("   -> STRONG agreement: methods find similar structure")
    elif mean_ari > 0.4:
        print("   -> MODERATE agreement: some unique structure in each")
    else:
        print("   -> WEAK agreement: methods find different structures")
        print("   -> TDA captures fundamentally different partitions than K-means")
    
    return combined


if __name__ == "__main__":
    results = main()
