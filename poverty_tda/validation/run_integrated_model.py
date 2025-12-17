"""
Task 9.5.4 EXTENDED: Comprehensive Integrated Model Testing

Tests whether TDA features add predictive value beyond traditional predictors,
across multiple outcomes, regions, and with bootstrap CIs.
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyvista as pv
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from poverty_tda.topology.morse_smale import compute_morse_smale

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def assign_basins(gdf, vti_path, persistence=0.05):
    """Assign LSOAs to MS basins and extract mobility values."""
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
    
    mobility = grid.point_data['mobility'].reshape(dims[1], dims[0])
    gdf['mobility'] = mobility[j, i]
    
    return gdf, ms_result


def load_region_data(region: str):
    """Load LSOA data with multiple outcomes for a region."""
    gdf = gpd.read_file("poverty_tda/data/raw/boundaries/lsoa_2021/lsoa_2021_boundaries.geojson")
    
    # Load IMD
    imd = pd.read_csv("poverty_tda/validation/data/england_imd_2019.csv")
    imd = imd.rename(columns={
        'LSOA code (2011)': 'lsoa_code_2011',
        'Local Authority District code (2019)': 'lad_code',
        'Index of Multiple Deprivation (IMD) Score': 'imd_score',
        'Index of Multiple Deprivation (IMD) Decile (where 1 is most deprived 10% of LSOAs)': 'imd_decile'
    })
    
    gdf['lsoa_code_2011'] = gdf['LSOA21CD'].str[:9]
    gdf = gdf.merge(imd[['lsoa_code_2011', 'lad_code', 'imd_score', 'imd_decile']], on='lsoa_code_2011', how='left')
    
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
    
    # Load LE data
    le = pd.read_csv("data/raw/outcomes/life_expectancy_processed.csv")
    le = le.rename(columns={'area_code': 'lad_code', 'life_expectancy_male': 'le_male'})
    gdf = gdf.merge(le[['lad_code', 'le_male']], on='lad_code', how='left')
    
    # Load KS4 data
    ks4_path = Path("data/raw/outcomes/ks4_2024.csv")
    if ks4_path.exists():
        ks4 = pd.read_csv(ks4_path)
        for col in ['avgatt8', 'pt_l2basics_94', 'att8']:
            if col in ks4.columns:
                la_col = 'new_la_code' if 'new_la_code' in ks4.columns else 'la_code'
                ks4 = ks4.rename(columns={col: 'ks4_score'})
                gdf = gdf.merge(ks4[[la_col, 'ks4_score']], left_on='lad_code', right_on=la_col, how='left')
                break
    
    return gdf, vti


def bootstrap_r2_ci(X, y, n_bootstrap=500, confidence=0.95):
    """Bootstrap confidence interval for R²."""
    np.random.seed(42)
    n = len(y)
    bootstrap_r2s = []
    
    for _ in range(n_bootstrap):
        idx = np.random.randint(0, n, size=n)
        X_boot = X[idx]
        y_boot = y[idx]
        
        try:
            model = LinearRegression().fit(X_boot, y_boot)
            y_pred = model.predict(X_boot)
            r2 = r2_score(y_boot, y_pred)
            bootstrap_r2s.append(r2)
        except:
            continue
    
    alpha = 1 - confidence
    ci_lower = np.percentile(bootstrap_r2s, 100 * alpha / 2)
    ci_upper = np.percentile(bootstrap_r2s, 100 * (1 - alpha / 2))
    point = np.mean(bootstrap_r2s)
    se = np.std(bootstrap_r2s)
    
    return {'r2': point, 'ci_lower': ci_lower, 'ci_upper': ci_upper, 'se': se}


def compute_models_with_bootstrap(gdf, outcome_col):
    """Compare regression models with bootstrap CIs."""
    df = gdf[[outcome_col, 'imd_score', 'imd_decile', 'ms_basin', 'mobility']].dropna()
    
    if len(df) < 100:
        return None
    
    y = df[outcome_col].values
    results = {'outcome': outcome_col, 'n_obs': len(df)}
    
    # 1. Traditional only (IMD score)
    X_trad = df[['imd_score']].values
    trad_boot = bootstrap_r2_ci(X_trad, y)
    results['traditional'] = trad_boot
    
    # 2. TDA only (basin dummies + mobility)
    basin_dummies = pd.get_dummies(df['ms_basin'], prefix='basin', drop_first=True)
    X_tda = pd.concat([basin_dummies, df[['mobility']]], axis=1).values
    tda_boot = bootstrap_r2_ci(X_tda, y)
    results['tda'] = tda_boot
    
    # 3. Combined
    X_combined = pd.concat([df[['imd_score']], basin_dummies, df[['mobility']]], axis=1).values
    combined_boot = bootstrap_r2_ci(X_combined, y)
    results['combined'] = combined_boot
    
    # Compute TDA improvement with bootstrap
    results['tda_improvement'] = combined_boot['r2'] - trad_boot['r2']
    results['improvement_se'] = np.sqrt(trad_boot['se']**2 + combined_boot['se']**2)
    
    return results


def main():
    """Run comprehensive integrated model testing."""
    
    print("=" * 75)
    print("TASK 9.5.4 EXTENDED: Comprehensive Integrated Model Testing")
    print("=" * 75)
    
    all_results = []
    
    for region in ['west_midlands', 'greater_manchester']:
        print(f"\n{'='*75}")
        print(f"Region: {region.upper()}")
        print(f"{'='*75}")
        
        # Load data
        gdf, vti_path = load_region_data(region)
        if not vti_path.exists():
            print(f"   VTI not found, skipping")
            continue
        
        gdf, ms = assign_basins(gdf, vti_path)
        print(f"   {len(gdf)} LSOAs, {gdf['ms_basin'].nunique()} basins")
        
        # Test multiple outcomes
        outcomes = []
        if 'le_male' in gdf.columns and gdf['le_male'].notna().sum() > 100:
            outcomes.append(('Life Expectancy', 'le_male'))
        if 'ks4_score' in gdf.columns and gdf['ks4_score'].notna().sum() > 100:
            outcomes.append(('KS4 (GCSE)', 'ks4_score'))
        if 'imd_decile' in gdf.columns:
            # Use IMD decile to predict mobility itself (reverse direction)
            outcomes.append(('Mobility', 'mobility'))
        
        for name, col in outcomes:
            print(f"\n   {name}:")
            result = compute_models_with_bootstrap(gdf, col)
            if result:
                result['region'] = region
                result['outcome_name'] = name
                all_results.append(result)
                
                t = result['traditional']
                d = result['tda']
                c = result['combined']
                
                print(f"      Traditional (IMD): R2 = {t['r2']:.3f} [{t['ci_lower']:.3f}, {t['ci_upper']:.3f}]")
                print(f"      TDA (basin+mob):   R2 = {d['r2']:.3f} [{d['ci_lower']:.3f}, {d['ci_upper']:.3f}]")
                print(f"      Combined:          R2 = {c['r2']:.3f} [{c['ci_lower']:.3f}, {c['ci_upper']:.3f}]")
                print(f"      TDA improvement:   +{result['tda_improvement']:.3f} (+/- {result['improvement_se']:.3f})")
    
    # Summary table
    print("\n" + "=" * 75)
    print("SUMMARY: R2 COMPARISON WITH 95% BOOTSTRAP CIs")
    print("=" * 75)
    print(f"\n{'Region':<20} {'Outcome':<15} {'Trad R2':>10} {'TDA R2':>10} {'Combined R2':>12} {'TDA +':>8}")
    print("-" * 75)
    
    for r in all_results:
        reg = r['region'][:12]
        out = r['outcome_name'][:12]
        trad = f"{r['traditional']['r2']:.3f}"
        tda = f"{r['tda']['r2']:.3f}"
        comb = f"{r['combined']['r2']:.3f}"
        imp = f"+{r['tda_improvement']:.3f}"
        print(f"{reg:<20} {out:<15} {trad:>10} {tda:>10} {comb:>12} {imp:>8}")
    
    return all_results


if __name__ == "__main__":
    results = main()
