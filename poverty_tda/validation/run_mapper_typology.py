"""
Phase 2: Mapper Typology Discovery

Uses Mapper algorithm to identify distinct poverty "types" from 7 IMD domains.
Characterizes each branch by dominant deprivation profile.
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from poverty_tda.topology.mapper import compute_mapper, MapperGraph

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# IMD domain columns (2019 structure)
IMD_DOMAINS = [
    'Income Score (rate)',
    'Employment Score (rate)', 
    'Education, Skills and Training Score',
    'Health Deprivation and Disability Score',
    'Crime Score',
    'Barriers to Housing and Services Score',
    'Living Environment Score'
]

SHORT_NAMES = ['Income', 'Employment', 'Education', 'Health', 'Crime', 'Housing', 'Environment']


def load_wm_with_domains():
    """Load WM LSOAs with all 7 IMD domain scores."""
    gdf = gpd.read_file("poverty_tda/data/raw/boundaries/lsoa_2021/lsoa_2021_boundaries.geojson")
    
    imd = pd.read_csv("poverty_tda/validation/data/england_imd_2019.csv")
    
    # Get 2011 LSOA code for merge
    gdf['lsoa_code_2011'] = gdf['LSOA21CD'].str[:9]
    
    # Rename IMD columns for easier access
    rename_map = {
        'LSOA code (2011)': 'lsoa_code_2011',
        'Local Authority District code (2019)': 'lad_code',
        'Index of Multiple Deprivation (IMD) Score': 'imd_score'
    }
    for i, dom in enumerate(IMD_DOMAINS):
        if dom in imd.columns:
            rename_map[dom] = SHORT_NAMES[i]
    
    imd = imd.rename(columns=rename_map)
    
    # Merge
    merge_cols = ['lsoa_code_2011', 'lad_code', 'imd_score'] + [sn for sn in SHORT_NAMES if sn in imd.columns]
    gdf = gdf.merge(imd[merge_cols], on='lsoa_code_2011', how='left')
    
    # Filter to WM
    wm_lads = ['E08000025', 'E08000026', 'E08000027', 'E08000028', 
               'E08000029', 'E08000030', 'E08000031']
    gdf = gdf[gdf['lad_code'].isin(wm_lads)]
    
    return gdf


def characterize_node(node_members, domain_data):
    """Characterize a Mapper node by its z-scored domain profile."""
    subset = domain_data.iloc[list(node_members)]
    mean_profile = subset.mean()
    
    # Standardize relative to full dataset
    zscore = (mean_profile - domain_data.mean()) / domain_data.std()
    
    return zscore


def assign_typology_label(zscore_profile, threshold=0.5):
    """Assign a descriptive label based on dominant domains."""
    high_domains = [d for d, z in zscore_profile.items() if z > threshold]
    low_domains = [d for d, z in zscore_profile.items() if z < -threshold]
    
    # Priority labels
    if 'Employment' in high_domains and 'Income' in high_domains:
        return "Post-Industrial Decline"
    elif 'Crime' in high_domains and 'Housing' in high_domains:
        return "Urban Concentrated"  
    elif 'Environment' in high_domains and 'Housing' in high_domains:
        return "Coastal/Rural Decline"
    elif 'Health' in high_domains:
        return "Health Disadvantaged"
    elif all(z < -threshold for z in zscore_profile.values()):
        return "Affluent"
    elif all(abs(z) < threshold for z in zscore_profile.values()):
        return "Mixed/Average"
    elif len(high_domains) >= 4:
        return "Multi-Domain Deprived"
    else:
        return "Moderate Deprivation"


def main():
    """Run Mapper typology discovery."""
    
    print("=" * 75)
    print("PHASE 2: MAPPER TYPOLOGY DISCOVERY")
    print("=" * 75)
    
    # Load data with 7 domains
    print("\n1. Loading data with 7 IMD domains...")
    gdf = load_wm_with_domains()
    print(f"   {len(gdf)} LSOAs in West Midlands")
    
    # Check available domains
    available_domains = [d for d in SHORT_NAMES if d in gdf.columns]
    print(f"   Available domains: {available_domains}")
    
    if len(available_domains) < 3:
        print("   ERROR: Not enough domain columns found")
        return
    
    # Prepare data for Mapper
    domain_data = gdf[available_domains].dropna()
    valid_idx = domain_data.index
    print(f"   {len(valid_idx)} LSOAs with complete domain data")
    
    # Create DataFrame for Mapper
    df = domain_data.reset_index(drop=True).copy()
    
    # Use IMD score as filter function
    filter_values = gdf.loc[valid_idx, 'imd_score'].values.reshape(-1, 1)
    
    print("\n2. Running Mapper algorithm...")
    print("   Parameters: n_cubes=15, overlap=0.5, clustering=single_linkage")
    
    mapper_graph = compute_mapper(
        data=df,
        filter_values=filter_values,
        feature_columns=available_domains,
        n_cubes=15,
        overlap=0.5,
        clustering='single_linkage',
        filter_name='imd_score'
    )
    
    stats = mapper_graph.summary()
    print(f"   Created {stats['n_nodes']} nodes, {stats['n_edges']} edges")
    print(f"   Connected components: {stats['n_connected_components']}")
    print(f"   Has cycles: {stats['has_cycles']}")
    
    # Characterize each node
    print("\n3. Characterizing Mapper nodes by domain profile...")
    
    typologies = {}
    node_profiles = []
    
    for node in mapper_graph.nodes:
        zscore = characterize_node(node.members, domain_data.reset_index(drop=True))
        label = assign_typology_label(zscore.to_dict())
        typologies[node.node_id] = label
        
        node_profiles.append({
            'node_id': node.node_id,
            'size': node.size,
            'label': label,
            **{f'z_{d}': zscore[d] for d in available_domains}
        })
    
    profiles_df = pd.DataFrame(node_profiles).sort_values('size', ascending=False)
    
    # Summary
    print("\n" + "=" * 75)
    print("MAPPER TYPOLOGY RESULTS")
    print("=" * 75)
    
    print(f"\n{'Node':>6} {'Size':>6} {'Label':<25} {'Dominant Domains'}")
    print("-" * 75)
    
    for _, row in profiles_df.head(20).iterrows():
        z_cols = [c for c in row.index if c.startswith('z_')]
        dom_scores = {c[2:]: row[c] for c in z_cols}
        top_doms = sorted(dom_scores.items(), key=lambda x: -x[1])[:2]
        dom_str = ', '.join([f"{d}({v:.1f})" for d, v in top_doms if v > 0.3])
        print(f"{int(row['node_id']):>6} {int(row['size']):>6} {row['label']:<25} {dom_str}")
    
    # Typology distribution
    print("\n\nTYPOLOGY DISTRIBUTION:")
    print("-" * 40)
    for label in profiles_df['label'].unique():
        count = (profiles_df['label'] == label).sum()
        total_lsoas = profiles_df[profiles_df['label'] == label]['size'].sum()
        print(f"  {label:<25}: {count:>3} nodes, {total_lsoas:>5} LSOAs")
    
    # Graph structure
    print("\n\nGRAPH STRUCTURE ANALYSIS:")
    print("-" * 40)
    G = mapper_graph.to_networkx()
    
    # Find branches (nodes with degree 1)
    endpoints = [n for n in G.nodes() if G.degree(n) == 1]
    print(f"  Endpoints (branch tips): {len(endpoints)}")
    
    # Find hubs (high degree nodes)
    hubs = [(n, G.degree(n)) for n in G.nodes() if G.degree(n) >= 3]
    hubs.sort(key=lambda x: -x[1])
    print(f"  Hubs (degree >= 3): {len(hubs)}")
    
    if hubs:
        for n, deg in hubs[:5]:
            label = typologies.get(n, "Unknown")
            print(f"    Node {n}: degree={deg}, {label}")
    
    return mapper_graph, profiles_df


if __name__ == "__main__":
    graph, profiles = main()
