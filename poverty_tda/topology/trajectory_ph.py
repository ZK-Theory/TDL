"""
SIMD Data Loader and Trajectory PH (Phase C2).

Loads Scotland SIMD domain ranks for 2016 and 2020, constructs trajectory
representations, and computes PH on the trajectory point cloud.

Uses the 2016 → 2020 pair (both on 2011-based Data Zones, 100% overlap).
SIMD 2012 uses incompatible 2001-based Data Zone codes and is excluded.

Two trajectory representations are computed:
1. **Displacement vectors** (7D): Δ = ranks_2020 - ranks_2016 for each DZ.
   Tests whether the *pattern of deprivation change* has topological structure.
2. **Concatenated vectors** (14D): [ranks_2016, ranks_2020] for each DZ.
   Tests whether the joint static+trajectory space has loops.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from poverty_tda.topology.multidim_ph import (
    compute_rips_ph,
    permutation_test,
    persistence_summary,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "poverty_tda" / "data" / "raw" / "boundaries"

# SIMD domain rank columns (shared across 2016 and 2020)
SIMD_2016_RANK_COLS = {
    "Income_domain_2016_rank": "income",
    "Employment_domain_2016_rank": "employment",
    "Education_domain_2016_rank": "education",
    "Health_domain_2016_rank": "health",
    "Crime_domain_2016_rank": "crime",
    "Access_domain_2016_rank": "access",
    "Housing_domain_2016_rank": "housing",
}

SIMD_2020_RANK_COLS = {
    "SIMD2020v2_Income_Domain_Rank": "income",
    "SIMD2020_Employment_Domain_Rank": "employment",
    "SIMD2020_Education_Domain_Rank": "education",
    "SIMD2020_Health_Domain_Rank": "health",
    "SIMD2020_Crime_Domain_Rank": "crime",
    "SIMD2020_Access_Domain_Rank": "access",
    "SIMD2020_Housing_Domain_Rank": "housing",
}

DOMAIN_NAMES = ["income", "employment", "education", "health", "crime", "access", "housing"]

# Scottish council area groupings
SCOTLAND_CITY_REGIONS = {
    "glasgow": ["Glasgow City"],
    "edinburgh": ["City of Edinburgh"],
    "greater_glasgow": [
        "Glasgow City",
        "East Dunbartonshire",
        "East Renfrewshire",
        "Inverclyde",
        "Renfrewshire",
        "West Dunbartonshire",
    ],
}


def load_simd_ranks(year: int, council: str | None = None) -> tuple[pd.DataFrame, dict]:
    """Load SIMD domain ranks for a specific year."""
    if year == 2016:
        path = DATA_DIR / "lsoa_2016_SC" / "00534450.xlsx"
        sheet = "SIMD16 ranks"
        col_map = SIMD_2016_RANK_COLS
        dz_col = "Data_Zone"
        council_col = "Council_area"
    elif year == 2020:
        path = DATA_DIR / "lsoa_2020_SC" / "SIMD+2020v2+-+ranks.xlsx"
        sheet = "SIMD 2020v2 ranks"
        col_map = SIMD_2020_RANK_COLS
        dz_col = "Data_Zone"
        council_col = "Council_area"
    else:
        raise ValueError(f"Unsupported year: {year}. Use 2016 or 2020.")

    df = pd.read_excel(path, sheet_name=sheet)

    if council:
        if council in SCOTLAND_CITY_REGIONS:
            councils = SCOTLAND_CITY_REGIONS[council]
        else:
            councils = [council]
        df = df[df[council_col].isin(councils)]
        logger.info(f"Filtered SIMD {year} to {council}: {len(df)} Data Zones")

    # Extract and rename rank columns
    rank_df = df[[dz_col] + list(col_map.keys())].copy()
    rank_df = rank_df.rename(columns={dz_col: "data_zone", **col_map})

    return rank_df, {"year": year, "n_zones": len(rank_df)}


def build_trajectory_cloud(
    council: str | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str], list[str]]:
    """
    Build trajectory representations from SIMD 2016 → 2020.

    Returns:
        X_displacement: (N, 7) z-scored displacement vectors
        X_concat: (N, 14) z-scored concatenated [2016, 2020] vectors
        X_static_2020: (N, 7) z-scored 2020 ranks (for comparison)
        data_zones: matched Data Zone codes
        domain_names: 7 domain names
    """
    df16, _ = load_simd_ranks(2016, council=council)
    df20, _ = load_simd_ranks(2020, council=council)

    # Merge on data zone
    merged = pd.merge(
        df16,
        df20,
        on="data_zone",
        suffixes=("_16", "_20"),
    )
    logger.info(f"Matched Data Zones: {len(merged)} (2016 & 2020)")

    data_zones = merged["data_zone"].tolist()

    # Extract rank arrays
    cols_16 = [f"{d}_16" for d in DOMAIN_NAMES]
    cols_20 = [f"{d}_20" for d in DOMAIN_NAMES]

    ranks_16 = merged[cols_16].values.astype(float)
    ranks_20 = merged[cols_20].values.astype(float)

    # Compute displacement: how did each DZ change?
    displacement = ranks_20 - ranks_16

    # Concatenated: joint state at both time points
    concat = np.hstack([ranks_16, ranks_20])

    # Z-score each representation
    scaler_disp = StandardScaler()
    X_displacement = scaler_disp.fit_transform(displacement)

    scaler_concat = StandardScaler()
    X_concat = scaler_concat.fit_transform(concat)

    scaler_static = StandardScaler()
    X_static = scaler_static.fit_transform(ranks_20)

    logger.info(f"Displacement cloud: {X_displacement.shape}")
    logger.info(f"Concatenated cloud: {X_concat.shape}")

    return X_displacement, X_concat, X_static, data_zones, DOMAIN_NAMES


def run_trajectory_ph(
    council: str | None = None,
    max_dim: int = 1,
    do_permutation: int = 0,
) -> dict:
    """
    Full C2 pipeline: build trajectories, compute PH on displacement and
    concatenated clouds, compare with static 2020 snapshot.
    """
    t0 = time.time()

    X_disp, X_concat, X_static, data_zones, domain_names = build_trajectory_cloud(council=council)

    results = {"council": council or "all_scotland", "n_zones": len(data_zones)}

    # Compute PH on each representation
    clouds = {
        "static_2020": (X_static, "Static 2020 ranks (7D)"),
        "displacement": (X_disp, "Displacement Δ(2016→2020) (7D)"),
        "concatenated": (X_concat, "Concatenated [2016, 2020] (14D)"),
    }

    ph_objects = {}
    for key, (X, desc) in clouds.items():
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Computing PH: {desc} — {X.shape[0]} points × {X.shape[1]} dims")
        logger.info(f"{'=' * 60}")

        ph = compute_rips_ph(X, max_dim=max_dim)
        ph.domain_names = domain_names
        summary = persistence_summary(ph)

        for dim_key in ["H0", "H1"]:
            s = summary.get(dim_key, {})
            logger.info(
                f"  {dim_key}: {s.get('n_finite', 0)} features, "
                f"max={s.get('max_persistence', 0):.4f}, "
                f"total={s.get('total_persistence', 0):.3f}"
            )

        # Permutation test
        perm = None
        if do_permutation > 0:
            logger.info(f"  Permutation test ({do_permutation})...")
            perm = permutation_test(
                X,
                n_permutations=do_permutation,
                max_dim=max_dim,
                statistic="max_persistence",
            )

        results[key] = {
            "description": desc,
            "dimensions": int(X.shape[1]),
            "persistence_summary": {
                k: {kk: vv for kk, vv in v.items() if kk != "features"} for k, v in summary.items()
            },
            "permutation_test": perm,
        }
        ph_objects[key] = ph

    results["elapsed_seconds"] = time.time() - t0
    return results, ph_objects
