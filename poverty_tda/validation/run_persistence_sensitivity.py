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


def bootstrap_eta_squared_ci(cluster_labels, outcome_values, n_bootstrap=500, confidence=0.95):
    """Bootstrap CI for eta-squared."""
    np.random.seed(42)
    n = len(outcome_values)
    eta_boots = []
    
    for _ in range(n_bootstrap):
        idx = np.random.randint(0, n, size=n)
        eta = compute_eta_squared(cluster_labels[idx], outcome_values[idx])
        eta_boots.append(eta)
    
    alpha = 1 - confidence
    ci_lower = np.percentile(eta_boots, 100 * alpha / 2)
    ci_upper = np.percentile(eta_boots, 100 * (1 - alpha / 2))
    point = compute_eta_squared(cluster_labels, outcome_values)
    se = np.std(eta_boots)
    
    return {'eta2': point, 'ci_lower': ci_lower, 'ci_upper': ci_upper, 'se': se}


def load_wm_data():
    """Load West Midlands LSOA data with LE, KS4, and Migration."""
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
    
    # Load LE data
    le = pd.read_csv("data/raw/outcomes/life_expectancy_processed.csv")
    le = le.rename(columns={'area_code': 'lad_code', 'life_expectancy_male': 'le_male'})
    gdf = gdf.merge(le[['lad_code', 'le_male']], on='lad_code', how='left')
    
    # Load KS4 data
    ks4_path = Path("data/raw/outcomes/gcse_attainment_processed.csv")
    if ks4_path.exists():
        ks4 = pd.read_csv(ks4_path)
        if 'gcse_attainment8' in ks4.columns and 'lad_code' in ks4.columns:
            ks4 = ks4.rename(columns={'gcse_attainment8': 'ks4_score'})
            gdf = gdf.merge(ks4[['lad_code', 'ks4_score']].drop_duplicates(), on='lad_code', how='left')
            logger.info(f"Loaded KS4: {gdf['ks4_score'].notna().sum()} LSOAs")
    
    # Load Migration data
    migration_path = Path("data/raw/outcomes/internal_migration_by_lad.xlsx")
    if migration_path.exists():
        try:
            from poverty_tda.data.process_migration import load_migration_flows, compute_lad_migration_metrics
            flows = load_migration_flows(migration_path)
            migration = compute_lad_migration_metrics(flows)
            gdf = gdf.merge(migration[['lad_code', 'net_migration_rate']], on='lad_code', how='left')
            logger.info(f"Loaded Migration: {gdf['net_migration_rate'].notna().sum()} LSOAs")
        except Exception as e:
            logger.warning(f"Could not load migration: {e}")
    
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
    
    # Define outcomes to test
    outcomes = [
        ('LE', 'le_male'),
        ('KS4', 'ks4_score'),
        ('Migration', 'net_migration_rate')
    ]
    
    all_results = []
    
    for thresh in thresholds:
        print(f"\n   Persistence = {thresh}...")
        
        gdf, ms = assign_basins_with_persistence(gdf_base.copy(), vti_path, thresh)
        
        n_minima = ms.n_minima
        n_basins = gdf['ms_basin'].nunique()
        
        row = {'persistence': thresh, 'n_minima': n_minima, 'n_basins': n_basins}
        
        # Compute eta-squared for each outcome
        for name, col in outcomes:
            if col in gdf.columns:
                df = gdf[[col, 'ms_basin']].dropna()
                if len(df) > 50:
                    eta_boot = bootstrap_eta_squared_ci(df['ms_basin'].values, df[col].values)
                    row[f'eta_{name}'] = eta_boot['eta2']
                    row[f'ci_lower_{name}'] = eta_boot['ci_lower']
                    row[f'ci_upper_{name}'] = eta_boot['ci_upper']
                else:
                    row[f'eta_{name}'] = np.nan
        
        all_results.append(row)
        
        # Print summary
        eta_strs = []
        for name, col in outcomes:
            if f'eta_{name}' in row and not np.isnan(row.get(f'eta_{name}', np.nan)):
                eta_strs.append(f"{name}={row[f'eta_{name}']:.3f}")
        print(f"      Minima: {n_minima}, Basins: {n_basins}, " + ", ".join(eta_strs))
    
    # Summary table
    results_df = pd.DataFrame(all_results)
    
    print("\n" + "=" * 90)
    print("PERSISTENCE SENSITIVITY RESULTS - ALL OUTCOMES WITH 95% BOOTSTRAP CIs")
    print("=" * 90)
    print(f"\n{'Thresh':>8} {'Minima':>8} {'Basins':>8} {'LE eta2':>10} {'KS4 eta2':>10} {'Mig eta2':>10}")
    print("-" * 70)
    
    for _, r in results_df.iterrows():
        le = f"{r.get('eta_LE', np.nan):.3f}" if not np.isnan(r.get('eta_LE', np.nan)) else "N/A"
        ks4 = f"{r.get('eta_KS4', np.nan):.3f}" if not np.isnan(r.get('eta_KS4', np.nan)) else "N/A"
        mig = f"{r.get('eta_Migration', np.nan):.3f}" if not np.isnan(r.get('eta_Migration', np.nan)) else "N/A"
        print(f"{r['persistence']:>8.2f} {r['n_minima']:>8.0f} {r['n_basins']:>8.0f} {le:>10} {ks4:>10} {mig:>10}")
    
    # Analysis for each outcome
    print("\n" + "-" * 70)
    print("ROBUSTNESS ANALYSIS:")
    for name, col in outcomes:
        eta_col = f'eta_{name}'
        if eta_col in results_df.columns:
            vals = results_df[eta_col].dropna().values
            if len(vals) > 0:
                variation = vals.max() - vals.min()
                status = "ROBUST" if variation < 0.10 else "MODERATE" if variation < 0.20 else "SENSITIVE"
                print(f"   {name:12}: mean={vals.mean():.3f}, variation={variation:.3f} -> {status}")
    
    return results_df


if __name__ == "__main__":
    results = main()
