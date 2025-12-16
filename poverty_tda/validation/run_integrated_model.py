"""
Task 9.5.4: Integrated Model Testing

Tests whether combining TDA features with traditional predictors 
improves outcome prediction.

Compares:
1. Traditional only: outcome ~ IMD_decile
2. TDA only: outcome ~ basin_id  
3. Combined: outcome ~ IMD_decile + basin_id

Reports R^2 improvement from adding TDA features.
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyvista as pv
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from poverty_tda.topology.morse_smale import compute_morse_smale

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def assign_basins(gdf, vti_path, persistence=0.05):
    """Assign LSOAs to MS basins."""
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
    
    # Also get mobility value at each LSOA location
    mobility = grid.point_data['mobility'].reshape(dims[1], dims[0])
    gdf['mobility'] = mobility[j, i]
    
    return gdf, ms_result


def load_wm_data():
    """Load West Midlands LSOA data with outcomes."""
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
    
    # Filter to WM
    wm_lads = ['E08000025', 'E08000026', 'E08000027', 'E08000028', 
               'E08000029', 'E08000030', 'E08000031']
    gdf = gdf[gdf['lad_code'].isin(wm_lads)]
    
    # Load LE data
    le = pd.read_csv("data/raw/outcomes/life_expectancy_processed.csv")
    le = le.rename(columns={'area_code': 'lad_code', 'life_expectancy_male': 'le_male'})
    gdf = gdf.merge(le[['lad_code', 'le_male']], on='lad_code', how='left')
    
    return gdf


def compute_regression_models(gdf, outcome_col):
    """Compare regression models: Traditional only, TDA only, Combined."""
    
    # Remove missing values
    df = gdf[[outcome_col, 'imd_score', 'imd_decile', 'ms_basin', 'mobility']].dropna()
    
    if len(df) < 50:
        return None
    
    y = df[outcome_col].values
    
    results = {}
    
    # 1. Traditional only (IMD score)
    X_trad = df[['imd_score']].values
    model_trad = LinearRegression().fit(X_trad, y)
    y_pred_trad = model_trad.predict(X_trad)
    results['traditional_r2'] = r2_score(y, y_pred_trad)
    
    # 2. TDA only (basin dummy variables + mobility)
    basin_dummies = pd.get_dummies(df['ms_basin'], prefix='basin', drop_first=True)
    X_tda = pd.concat([basin_dummies, df[['mobility']]], axis=1).values
    model_tda = LinearRegression().fit(X_tda, y)
    y_pred_tda = model_tda.predict(X_tda)
    results['tda_r2'] = r2_score(y, y_pred_tda)
    
    # 3. Combined (IMD + TDA features)
    X_combined = pd.concat([df[['imd_score']], basin_dummies, df[['mobility']]], axis=1).values
    model_combined = LinearRegression().fit(X_combined, y)
    y_pred_combined = model_combined.predict(X_combined)
    results['combined_r2'] = r2_score(y, y_pred_combined)
    
    # Compute improvement
    results['tda_improvement'] = results['combined_r2'] - results['traditional_r2']
    results['trad_improvement'] = results['combined_r2'] - results['tda_r2']
    
    results['n_obs'] = len(df)
    results['n_basins'] = df['ms_basin'].nunique()
    
    return results


def main():
    """Run integrated model testing."""
    
    print("=" * 70)
    print("TASK 9.5.4: Integrated Model Testing (TDA + Traditional Predictors)")
    print("=" * 70)
    
    vti_path = Path("poverty_tda/validation/mobility_surface_wm_150.vti")
    
    # Load data
    print("\n1. Loading data...")
    gdf = load_wm_data()
    print(f"   {len(gdf)} LSOAs loaded")
    
    # Assign basins
    print("\n2. Assigning MS basins...")
    gdf, ms_result = assign_basins(gdf, vti_path)
    print(f"   {gdf['ms_basin'].nunique()} basins")
    
    # Run regression comparison
    print("\n3. Running regression models...")
    
    outcomes = []
    if 'le_male' in gdf.columns and gdf['le_male'].notna().sum() > 50:
        outcomes.append(('Life Expectancy', 'le_male'))
    if 'imd_score' in gdf.columns:
        # Use IMD score as outcome, predict from decile + TDA
        # This tests if TDA adds info beyond simple IMD categorization
        pass
    
    all_results = []
    for name, col in outcomes:
        results = compute_regression_models(gdf, col)
        if results:
            results['outcome'] = name
            all_results.append(results)
            
            print(f"\n   {name}:")
            print(f"   - Traditional only (IMD): R2 = {results['traditional_r2']:.3f}")
            print(f"   - TDA only (basin+mobility): R2 = {results['tda_r2']:.3f}")
            print(f"   - Combined (IMD + TDA): R2 = {results['combined_r2']:.3f}")
            print(f"   - TDA improvement: +{results['tda_improvement']:.3f}")
    
    # Summary
    print("\n" + "=" * 70)
    print("INTEGRATED MODEL RESULTS")
    print("=" * 70)
    
    if all_results:
        for r in all_results:
            print(f"\n{r['outcome']} (n={r['n_obs']}, {r['n_basins']} basins):")
            print(f"   Model                          R2")
            print(f"   -----------------------------------")
            print(f"   Traditional (IMD)              {r['traditional_r2']:.3f}")
            print(f"   TDA (basin + mobility)         {r['tda_r2']:.3f}")
            print(f"   Combined (IMD + TDA)           {r['combined_r2']:.3f}")
            print(f"   TDA adds: +{r['tda_improvement']:.3f} R2")
            
            if r['tda_improvement'] > 0.05:
                print("   -> TDA adds SUBSTANTIAL predictive value beyond IMD")
            elif r['tda_improvement'] > 0.01:
                print("   -> TDA adds MODEST predictive value beyond IMD")
            else:
                print("   -> TDA adds MINIMAL predictive value beyond IMD")
    
    return all_results


if __name__ == "__main__":
    results = main()
