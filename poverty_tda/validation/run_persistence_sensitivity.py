"""
Task 9.5.5: Persistence Threshold Sensitivity Analysis

Tests how Morse-Smale results change with persistence threshold.
Key question: Is eta-squared robust or threshold-dependent?
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyvista as pv

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from poverty_tda.topology.morse_smale import compute_morse_smale

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def compute_eta_squared(cluster_labels, outcome_values):
    """Compute eta-squared (variance explained by clusters)."""
    y = np.array(outcome_values)
    labels = np.array(cluster_labels)
    
    grand_mean = y.mean()
    ss_total = np.sum((y - grand_mean) ** 2)
    
    unique_clusters = np.unique(labels)
    ss_between = 0
    for c in unique_clusters:
        mask = labels == c
        group = y[mask]
        if len(group) > 0:
            ss_between += len(group) * (group.mean() - grand_mean) ** 2
    
    return ss_between / ss_total if ss_total > 0 else 0


def load_wm_data():
    """Load West Midlands LSOA data with LE."""
    gdf = gpd.read_file("poverty_tda/data/raw/boundaries/lsoa_2021/lsoa_2021_boundaries.geojson")
    
    imd = pd.read_csv("poverty_tda/validation/data/england_imd_2019.csv")
    imd = imd.rename(columns={
        'LSOA code (2011)': 'lsoa_code_2011',
        'Local Authority District code (2019)': 'lad_code',
    })
    
    gdf['lsoa_code_2011'] = gdf['LSOA21CD'].str[:9]
    gdf = gdf.merge(imd[['lsoa_code_2011', 'lad_code']], on='lsoa_code_2011', how='left')
    
    wm_lads = ['E08000025', 'E08000026', 'E08000027', 'E08000028', 
               'E08000029', 'E08000030', 'E08000031']
    gdf = gdf[gdf['lad_code'].isin(wm_lads)]
    
    le = pd.read_csv("data/raw/outcomes/life_expectancy_processed.csv")
    le = le.rename(columns={'area_code': 'lad_code', 'life_expectancy_male': 'le_male'})
    gdf = gdf.merge(le[['lad_code', 'le_male']], on='lad_code', how='left')
    
    return gdf


def assign_basins_with_persistence(gdf, vti_path, persistence):
    """Assign basins with given persistence threshold."""
    grid = pv.read(str(vti_path))
    origin = np.array(grid.origin[:2])
    spacing = np.array(grid.spacing[:2])
    dims = np.array(grid.dimensions[:2])
    
    ms_result = compute_morse_smale(vti_path, scalar_name="mobility", persistence_threshold=persistence)
    
    if gdf.crs and gdf.crs.to_epsg() != 27700:
        gdf = gdf.to_crs(epsg=27700)
    
    centroids = gdf.geometry.centroid
    i = np.clip(((centroids.x.values - origin[0]) / spacing[0]).astype(int), 0, dims[0] - 1)
    j = np.clip(((centroids.y.values - origin[1]) / spacing[1]).astype(int), 0, dims[1] - 1)
    flat_idx = np.clip(i + j * dims[0], 0, dims[0] * dims[1] - 1)
    
    gdf = gdf.copy()
    gdf['ms_basin'] = ms_result.descending_manifold[flat_idx]
    
    return gdf, ms_result


def main():
    """Run persistence threshold sensitivity analysis."""
    
    print("=" * 70)
    print("TASK 9.5.5: Persistence Threshold Sensitivity Analysis")
    print("=" * 70)
    
    vti_path = Path("poverty_tda/validation/mobility_surface_wm_150.vti")
    
    # Load base data
    print("\n1. Loading WM data...")
    gdf_base = load_wm_data()
    print(f"   {len(gdf_base)} LSOAs loaded")
    
    # Test range of persistence thresholds
    thresholds = [0.01, 0.02, 0.05, 0.10, 0.15, 0.20]
    
    print("\n2. Testing persistence thresholds...")
    print(f"   Thresholds: {thresholds}")
    
    results = []
    
    for thresh in thresholds:
        print(f"\n   Persistence = {thresh}...")
        
        gdf, ms = assign_basins_with_persistence(gdf_base.copy(), vti_path, thresh)
        
        n_minima = ms.n_minima
        n_basins = gdf['ms_basin'].nunique()
        
        # Compute eta-squared
        df = gdf[['le_male', 'ms_basin']].dropna()
        if len(df) > 50:
            eta_sq = compute_eta_squared(df['ms_basin'].values, df['le_male'].values)
        else:
            eta_sq = np.nan
        
        results.append({
            'persistence': thresh,
            'n_minima': n_minima,
            'n_basins': n_basins,
            'eta_squared': eta_sq
        })
        
        print(f"      Minima: {n_minima}, Basins: {n_basins}, eta^2: {eta_sq:.3f}")
    
    # Summary
    results_df = pd.DataFrame(results)
    
    print("\n" + "=" * 70)
    print("PERSISTENCE SENSITIVITY RESULTS")
    print("=" * 70)
    print(f"\n{'Threshold':>10} {'Minima':>8} {'Basins':>8} {'eta^2':>8}")
    print("-" * 40)
    for _, r in results_df.iterrows():
        print(f"{r['persistence']:>10.2f} {r['n_minima']:>8} {r['n_basins']:>8} {r['eta_squared']:>8.3f}")
    
    # Analysis
    eta_values = results_df['eta_squared'].values
    eta_range = eta_values.max() - eta_values.min()
    eta_mean = eta_values.mean()
    
    print(f"\n   eta^2 range: {eta_values.min():.3f} - {eta_values.max():.3f}")
    print(f"   eta^2 mean: {eta_mean:.3f}")
    print(f"   eta^2 variation: {eta_range:.3f}")
    
    if eta_range < 0.10:
        print("\n   -> eta^2 is ROBUST to persistence threshold (variation < 0.10)")
    elif eta_range < 0.20:
        print("\n   -> eta^2 is MODERATELY SENSITIVE to persistence threshold")
    else:
        print("\n   -> eta^2 is HIGHLY SENSITIVE to persistence threshold")
    
    return results_df


if __name__ == "__main__":
    results = main()
