"""
Cross-National Topology Comparison (Phase C3).

Compares the topological structure of deprivation between England (IMD 2019)
and Scotland (SIMD 2020v2) using the 5 directly comparable domains:
Income, Employment, Education, Health, Crime.

Uses domain RANKS (z-scored) for both countries rather than raw scores, since
Scotland's raw domain scores are not consistently available across years.
Z-scoring ranks produces approximately standard-normal distributions in both
countries, making the point cloud geometry directly comparable.
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
DATA_DIR = PROJECT_ROOT / "poverty_tda" / "data" / "raw"

# 5 directly comparable domains (present in both IMD and SIMD)
SHARED_DOMAINS = ["income", "employment", "education", "health", "crime"]

# England IMD 2019 rank column mapping
ENGLAND_RANK_COLS = {
    "Income Rank (where 1 is most deprived)": "income",
    "Employment Rank (where 1 is most deprived)": "employment",
    "Education, Skills and Training Rank (where 1 is most deprived)": "education",
    "Health Deprivation and Disability Rank (where 1 is most deprived)": "health",
    "Crime Rank (where 1 is most deprived)": "crime",
}

# Scotland SIMD 2020v2 rank column mapping
SCOTLAND_RANK_COLS = {
    "SIMD2020v2_Income_Domain_Rank": "income",
    "SIMD2020_Employment_Domain_Rank": "employment",
    "SIMD2020_Education_Domain_Rank": "education",
    "SIMD2020_Health_Domain_Rank": "health",
    "SIMD2020_Crime_Domain_Rank": "crime",
}

# England regions for matched comparison
ENGLAND_REGIONS = {
    "birmingham": {
        "la_names": ["Birmingham"],
    },
    "west_midlands": {
        "la_names": [
            "Birmingham",
            "Coventry",
            "Dudley",
            "Sandwell",
            "Solihull",
            "Walsall",
            "Wolverhampton",
        ],
    },
}


def load_england_ranks(
    region: str | None = None,
) -> tuple[np.ndarray, list[str], list[str]]:
    """
    Load England IMD 2019 domain ranks for the 5 shared domains.

    Returns:
        X: (N, 5) z-scored rank array
        area_codes: list of LSOA codes
        domain_names: list of 5 short domain names
    """
    csv_path = DATA_DIR / "imd" / "england_imd_2019.csv"
    df = pd.read_csv(csv_path)

    if region and region in ENGLAND_REGIONS:
        la_names = ENGLAND_REGIONS[region]["la_names"]
        col = "Local Authority District name (2019)"
        df = df[df[col].isin(la_names)]
        logger.info(f"Filtered England to {region}: {len(df)} LSOAs")

    area_codes = df["LSOA code (2011)"].tolist()
    rank_data = df[list(ENGLAND_RANK_COLS.keys())].rename(columns=ENGLAND_RANK_COLS)

    # Z-score the ranks
    scaler = StandardScaler()
    X = scaler.fit_transform(rank_data[SHARED_DOMAINS].values)

    logger.info(f"Loaded England ranks: {X.shape[0]} LSOAs × {X.shape[1]} domains")
    return X, area_codes, SHARED_DOMAINS


def load_scotland_ranks(
    council: str | None = None,
) -> tuple[np.ndarray, list[str], list[str]]:
    """
    Load Scotland SIMD 2020v2 domain ranks for the 5 shared domains.

    Returns:
        X: (N, 5) z-scored rank array
        area_codes: list of Data Zone codes
        domain_names: list of 5 short domain names
    """
    xlsx_path = DATA_DIR / "boundaries" / "lsoa_2020_SC" / "SIMD+2020v2+-+ranks.xlsx"
    df = pd.read_excel(xlsx_path, sheet_name="SIMD 2020v2 ranks")

    if council:
        df = df[df["Council_area"] == council]
        logger.info(f"Filtered Scotland to {council}: {len(df)} Data Zones")

    area_codes = df["Data_Zone"].tolist()
    rank_data = df[list(SCOTLAND_RANK_COLS.keys())].rename(columns=SCOTLAND_RANK_COLS)

    # Z-score the ranks
    scaler = StandardScaler()
    X = scaler.fit_transform(rank_data[SHARED_DOMAINS].values)

    logger.info(f"Loaded Scotland ranks: {X.shape[0]} Data Zones × {X.shape[1]} domains")
    return X, area_codes, SHARED_DOMAINS


def wasserstein_distance_ph(dgm1: np.ndarray, dgm2: np.ndarray) -> float:
    """
    Compute the 1-Wasserstein distance between two persistence diagrams.

    Uses the simple bottleneck-like approximation: match features by sorted
    lifetime and compute L1 distance. For a more rigorous computation, use
    persim or gudhi.
    """
    try:
        from persim import wasserstein as persim_wasserstein

        return persim_wasserstein(dgm1, dgm2)
    except ImportError:
        pass

    # Fallback: compare sorted lifetime distributions
    lt1 = np.sort(dgm1[:, 1] - dgm1[:, 0])[::-1] if len(dgm1) > 0 else np.array([])
    lt2 = np.sort(dgm2[:, 1] - dgm2[:, 0])[::-1] if len(dgm2) > 0 else np.array([])

    # Pad to same length
    max_len = max(len(lt1), len(lt2))
    lt1 = np.pad(lt1, (0, max_len - len(lt1)), constant_values=0)
    lt2 = np.pad(lt2, (0, max_len - len(lt2)), constant_values=0)

    return float(np.sum(np.abs(lt1 - lt2)))


def run_cross_national(
    england_region: str | None = None,
    scotland_council: str | None = None,
    max_dim: int = 1,
    do_permutation: int = 0,
    subsample: int | None = None,
) -> dict:
    """
    Full C3 pipeline: load both countries, compute PH, compare.

    Args:
        england_region: Filter England to a specific region (or None for all).
        scotland_council: Filter Scotland to a specific council (or None for all).
        max_dim: Maximum homology dimension.
        do_permutation: Number of permutation test permutations (0 = skip).
        subsample: Random subsample size per country (None = use all).
    """
    t0 = time.time()

    # Load data
    X_eng, codes_eng, domains = load_england_ranks(region=england_region)
    X_scot, codes_scot, _ = load_scotland_ranks(council=scotland_council)

    # Subsample if requested
    rng = np.random.RandomState(42)
    if subsample and len(X_eng) > subsample:
        idx = rng.choice(len(X_eng), subsample, replace=False)
        X_eng = X_eng[idx]
        codes_eng = [codes_eng[i] for i in idx]
        logger.info(f"Subsampled England to {subsample}")
    if subsample and len(X_scot) > subsample:
        idx = rng.choice(len(X_scot), subsample, replace=False)
        X_scot = X_scot[idx]
        codes_scot = [codes_scot[i] for i in idx]
        logger.info(f"Subsampled Scotland to {subsample}")

    # --- England PH ---
    eng_label = england_region or "all_england"
    logger.info(f"\nComputing PH for England ({eng_label}): {len(X_eng)} points...")
    ph_eng = compute_rips_ph(X_eng, max_dim=max_dim)
    ph_eng.domain_names = domains
    summary_eng = persistence_summary(ph_eng)

    # --- Scotland PH ---
    scot_label = scotland_council or "all_scotland"
    logger.info(f"\nComputing PH for Scotland ({scot_label}): {len(X_scot)} points...")
    ph_scot = compute_rips_ph(X_scot, max_dim=max_dim)
    ph_scot.domain_names = domains
    summary_scot = persistence_summary(ph_scot)

    # --- Log comparison ---
    logger.info("\n" + "=" * 70)
    logger.info("CROSS-NATIONAL COMPARISON")
    logger.info("=" * 70)
    for dim_key in ["H0", "H1"]:
        e = summary_eng.get(dim_key, {})
        s = summary_scot.get(dim_key, {})
        logger.info(
            f"  {dim_key} ENG:  {e.get('n_finite', 0)} features, "
            f"max={e.get('max_persistence', 0):.4f}, "
            f"total={e.get('total_persistence', 0):.3f}"
        )
        logger.info(
            f"  {dim_key} SCOT: {s.get('n_finite', 0)} features, "
            f"max={s.get('max_persistence', 0):.4f}, "
            f"total={s.get('total_persistence', 0):.3f}"
        )

    # --- Wasserstein distance ---
    w_dist = {}
    for dim in range(max_dim + 1):
        if dim in ph_eng.dgms and dim in ph_scot.dgms:
            dgm_e = ph_eng.dgms[dim][ph_eng.dgms[dim][:, 1] != np.inf]
            dgm_s = ph_scot.dgms[dim][ph_scot.dgms[dim][:, 1] != np.inf]
            w = wasserstein_distance_ph(dgm_e, dgm_s)
            w_dist[f"H{dim}"] = w
            logger.info(f"  W₁(H{dim}) = {w:.4f}")

    # --- Permutation tests ---
    perm_eng = None
    perm_scot = None
    if do_permutation > 0:
        logger.info(f"\nPermutation tests ({do_permutation} permutations)...")
        perm_eng = permutation_test(
            X_eng,
            n_permutations=do_permutation,
            max_dim=max_dim,
            statistic="max_persistence",
        )
        perm_scot = permutation_test(
            X_scot,
            n_permutations=do_permutation,
            max_dim=max_dim,
            statistic="max_persistence",
        )

    elapsed = time.time() - t0

    def clean_summary(s):
        return {k: {kk: vv for kk, vv in v.items() if kk != "features"} for k, v in s.items()}

    results = {
        "england": {
            "label": eng_label,
            "n_areas": int(len(X_eng)),
            "persistence_summary": clean_summary(summary_eng),
            "permutation_test": perm_eng,
        },
        "scotland": {
            "label": scot_label,
            "n_areas": int(len(X_scot)),
            "persistence_summary": clean_summary(summary_scot),
            "permutation_test": perm_scot,
        },
        "comparison": {
            "wasserstein_distance": w_dist,
            "domains_used": domains,
            "method": "z-scored domain ranks, 5 shared domains",
        },
        "elapsed_seconds": elapsed,
    }

    return results, ph_eng, ph_scot
