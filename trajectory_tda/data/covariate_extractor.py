"""
Extract demographic covariates (sex, birth year, parental NS-SEC)
for trajectory respondents from raw BHPS/USoc data files.

Maps pidp → {sex, birth_year, cohort_decade, parental_nssec} by reading
wave a of USoc (covering most respondents) and BHPS wave 1 as fallback.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# NS-SEC 8-class labels (Understanding Society derived variable coding)
NSSEC8_LABELS = {
    1: "Higher managerial",
    2: "Lower managerial/professional",
    3: "Intermediate",
    4: "Small employers",
    5: "Lower supervisory/technical",
    6: "Semi-routine",
    7: "Routine",
    8: "Never worked/long-term unemployed",
}

# Simplified 3-class for analysis
NSSEC3_MAP = {
    1: "Professional/Managerial",
    2: "Professional/Managerial",
    3: "Intermediate",
    4: "Intermediate",
    5: "Intermediate",
    6: "Routine/Manual",
    7: "Routine/Manual",
    8: "Routine/Manual",
}


def extract_covariates(
    data_dir: str | Path,
    pidps: np.ndarray | list[int],
    bhps_subdir: str = "UKDA-5151-tab",
    usoc_subdir: str = "UKDA-6614-tab",
) -> pd.DataFrame:
    """Extract demographic covariates for a set of respondent pidps.

    Reads sex, birth year, and parental NS-SEC from USoc wave a (primary)
    and BHPS wave 1 (fallback). Derives cohort_decade and simplified
    3-class parental NS-SEC.

    Args:
        data_dir: Root data directory containing BHPS/USoc subdirectories
        pidps: Array of person identifiers to match
        bhps_subdir: BHPS data subdirectory name
        usoc_subdir: USoc data subdirectory name

    Returns:
        DataFrame indexed by pidp with columns:
            sex (str: 'Male'/'Female'), birth_year (int),
            cohort_decade (str: e.g. '1960s'), parental_nssec8 (int 1-8),
            parental_nssec3 (str: simplified 3-class)
    """
    data_dir = Path(data_dir)
    pidp_set = set(int(p) for p in pidps)

    # ─── USoc wave a (primary source) ───
    usoc_covs = _load_usoc_covariates(data_dir / usoc_subdir, pidp_set)
    logger.info(f"USoc wave a: matched {len(usoc_covs)} of {len(pidp_set)} pidps")

    # ─── BHPS wave 1 (fallback for sex/birth_year) ───
    missing = pidp_set - set(usoc_covs["pidp"])
    if missing:
        bhps_covs = _load_bhps_covariates(data_dir / bhps_subdir, missing)
        logger.info(f"BHPS wave 1 fallback: matched {len(bhps_covs)} of {len(missing)} remaining")
        covs = pd.concat([usoc_covs, bhps_covs], ignore_index=True)
    else:
        covs = usoc_covs

    # ─── Try additional USoc waves for missing sex/birth_year ───
    still_missing = pidp_set - set(covs["pidp"])
    if still_missing:
        extra = _load_usoc_later_waves(data_dir / usoc_subdir, still_missing)
        if len(extra) > 0:
            logger.info(f"USoc later waves: matched {len(extra)} more")
            covs = pd.concat([covs, extra], ignore_index=True)

    # ─── Derive cohort decade ───
    covs["cohort_decade"] = covs["birth_year"].apply(
        lambda y: f"{int(y // 10) * 10}s" if pd.notna(y) and y > 0 else None
    )

    # ─── Derive 3-class parental NS-SEC ───
    covs["parental_nssec3"] = covs["parental_nssec8"].map(NSSEC3_MAP)

    matched = covs["pidp"].isin(pidp_set).sum()
    logger.info(
        f"Covariates extracted: {matched}/{len(pidp_set)} pidps matched, "
        f"sex coverage: {covs['sex'].notna().sum()}, "
        f"birth_year coverage: {(covs['birth_year'] > 0).sum()}, "
        f"parental_nssec coverage: {covs['parental_nssec8'].notna().sum()}"
    )

    return covs


def _load_usoc_covariates(usoc_dir: Path, pidp_set: set[int]) -> pd.DataFrame:
    """Load sex, birth year, parental NS-SEC from USoc wave a."""
    pattern = "a_indresp.tab"
    candidates = list(usoc_dir.rglob(pattern))
    if not candidates:
        return pd.DataFrame(columns=["pidp", "sex", "birth_year", "parental_nssec8"])

    fpath = candidates[0]
    cols_needed = ["pidp", "a_sex", "a_doby_dv", "a_panssec8_dv", "a_manssec8_dv"]

    try:
        df = pd.read_csv(fpath, sep="\t", usecols=cols_needed, low_memory=False)
    except (ValueError, KeyError):
        # Try without parental columns
        try:
            df = pd.read_csv(
                fpath,
                sep="\t",
                usecols=["pidp", "a_sex", "a_doby_dv"],
                low_memory=False,
            )
            df["a_panssec8_dv"] = np.nan
            df["a_manssec8_dv"] = np.nan
        except Exception:
            return pd.DataFrame(columns=["pidp", "sex", "birth_year", "parental_nssec8"])

    df = df[df["pidp"].isin(pidp_set)]

    result = pd.DataFrame({"pidp": df["pidp"]})
    result["sex"] = df["a_sex"].map({1: "Male", 2: "Female"})
    result["birth_year"] = df["a_doby_dv"].where(df["a_doby_dv"] > 0)

    # Parental NS-SEC: take father's (pa), fall back to mother's (ma)
    pa = df["a_panssec8_dv"].where(df["a_panssec8_dv"] > 0)
    ma = df["a_manssec8_dv"].where(df["a_manssec8_dv"] > 0)
    result["parental_nssec8"] = pa.fillna(ma)

    return result


def _load_bhps_covariates(bhps_dir: Path, pidp_set: set[int]) -> pd.DataFrame:
    """Load sex and birth year from BHPS wave 1 (aindresp or ba_indresp)."""
    # Try both naming conventions
    for pattern in ["ba_indresp.tab", "aindresp.tab"]:
        candidates = list(bhps_dir.rglob(pattern))
        if candidates:
            break
    else:
        return pd.DataFrame(columns=["pidp", "sex", "birth_year", "parental_nssec8"])

    fpath = candidates[0]
    try:
        df = pd.read_csv(fpath, sep="\t", low_memory=False)
    except Exception:
        return pd.DataFrame(columns=["pidp", "sex", "birth_year", "parental_nssec8"])

    cols_lower = {c.lower(): c for c in df.columns}

    # BHPS can have pid or pidp
    pid_col = cols_lower.get("pidp") or cols_lower.get("pid") or cols_lower.get("bapid") or cols_lower.get("apid")
    sex_col = cols_lower.get("basex") or cols_lower.get("asex") or cols_lower.get("ba_sex")
    dob_col = cols_lower.get("badoby") or cols_lower.get("adoby") or cols_lower.get("ba_doby")

    if pid_col is None:
        return pd.DataFrame(columns=["pidp", "sex", "birth_year", "parental_nssec8"])

    df_sub = df[[c for c in [pid_col, sex_col, dob_col] if c is not None]].copy()
    df_sub = df_sub.rename(columns={pid_col: "pidp"})
    df_sub = df_sub[df_sub["pidp"].isin(pidp_set)]

    result = pd.DataFrame({"pidp": df_sub["pidp"]})

    if sex_col and sex_col in df_sub.columns:
        result["sex"] = df_sub[sex_col].map({1: "Male", 2: "Female"})
    else:
        result["sex"] = None

    if dob_col and dob_col in df_sub.columns:
        result["birth_year"] = pd.to_numeric(df_sub[dob_col], errors="coerce")
        result["birth_year"] = result["birth_year"].where(result["birth_year"] > 0)
    else:
        result["birth_year"] = None

    result["parental_nssec8"] = np.nan  # BHPS wave 1 doesn't have derived parental NS-SEC

    return result


def _load_usoc_later_waves(usoc_dir: Path, pidp_set: set[int]) -> pd.DataFrame:
    """Try USoc waves b-d as fallback for sex and birth year."""
    for wl in "bcd":
        pattern = f"{wl}_indresp.tab"
        candidates = list(usoc_dir.rglob(pattern))
        if not candidates:
            continue
        try:
            df = pd.read_csv(
                candidates[0],
                sep="\t",
                usecols=["pidp", f"{wl}_sex", f"{wl}_doby_dv"],
                low_memory=False,
            )
        except (ValueError, KeyError):
            continue

        df = df[df["pidp"].isin(pidp_set)]
        if len(df) == 0:
            continue

        result = pd.DataFrame({"pidp": df["pidp"]})
        result["sex"] = df[f"{wl}_sex"].map({1: "Male", 2: "Female"})
        by_col = f"{wl}_doby_dv"
        result["birth_year"] = df[by_col].where(df[by_col] > 0)
        result["parental_nssec8"] = np.nan

        # Remove any that are still in pidp_set after matching
        pidp_set -= set(result["pidp"])
        return result

    return pd.DataFrame(columns=["pidp", "sex", "birth_year", "parental_nssec8"])


# ─── GOR (Government Office Region) extraction ───

GOR_LABELS = {
    1: "North East",
    2: "North West",
    3: "Yorkshire & Humber",
    4: "East Midlands",
    5: "West Midlands",
    6: "East of England",
    7: "London",
    8: "South East",
    9: "South West",
    10: "Wales",
    11: "Scotland",
    12: "Northern Ireland",
}

# BHPS 18-region → USoc 12-region GOR mapping
_BHPS_REGION_TO_GOR = {
    1: 7,  # Inner London → London
    2: 7,  # Outer London → London
    3: 8,  # Rest of South East → South East
    4: 9,  # South West → South West
    5: 6,  # East Anglia → East of England
    6: 4,  # East Midlands → East Midlands
    7: 5,  # West Midlands Conurbation → West Midlands
    8: 5,  # Rest of West Midlands → West Midlands
    9: 2,  # Greater Manchester → North West
    10: 2,  # Merseyside → North West
    11: 2,  # Rest of North West → North West
    12: 3,  # South Yorkshire → Yorkshire & Humber
    13: 3,  # West Yorkshire → Yorkshire & Humber
    14: 3,  # Rest of Yorkshire & Humber → Yorkshire & Humber
    15: 1,  # Tyne & Wear → North East
    16: 1,  # Rest of North → North East
    17: 10,  # Wales → Wales
    18: 11,  # Scotland → Scotland
}


def extract_gor(
    data_dir: str | Path,
    pidps: np.ndarray | list[int],
    bhps_subdir: str = "UKDA-5151-tab",
    usoc_subdir: str = "UKDA-6614-tab",
) -> pd.DataFrame:
    """Extract Government Office Region for trajectory respondents.

    Reads GOR from USoc wave a (primary), falls back to BHPS wave 1
    via the xwavedat cross-walk, then tries later USoc waves.

    Returns:
        DataFrame with columns: pidp, gor_code (int 1-12), gor_label (str)
    """
    data_dir = Path(data_dir)
    pidp_set = set(int(p) for p in pidps)
    matched = pd.DataFrame(columns=["pidp", "gor_code"])

    # ─── USoc wave a (primary) ───
    usoc_dir = data_dir / usoc_subdir
    usoc_a = _load_usoc_gor(usoc_dir, "a", pidp_set)
    if len(usoc_a) > 0:
        matched = pd.concat([matched, usoc_a], ignore_index=True)
        logger.info(f"USoc wave a GOR: matched {len(usoc_a)} of {len(pidp_set)}")

    # ─── BHPS wave 1 fallback via cross-walk ───
    remaining = pidp_set - set(matched["pidp"])
    if remaining:
        bhps_gor = _load_bhps_gor(data_dir / bhps_subdir, usoc_dir, remaining)
        if len(bhps_gor) > 0:
            matched = pd.concat([matched, bhps_gor], ignore_index=True)
            logger.info(f"BHPS wave 1 GOR fallback: matched {len(bhps_gor)} more")

    # ─── Later USoc waves fallback ───
    remaining = pidp_set - set(matched["pidp"])
    if remaining:
        for wl in "bcdefghijklmn":
            extra = _load_usoc_gor(usoc_dir, wl, remaining)
            if len(extra) > 0:
                matched = pd.concat([matched, extra], ignore_index=True)
                remaining -= set(extra["pidp"])
                logger.info(f"USoc wave {wl} GOR fallback: matched {len(extra)} more")
            if not remaining:
                break

    # ─── Add labels ───
    matched["gor_code"] = matched["gor_code"].astype(int)
    matched["gor_label"] = matched["gor_code"].map(GOR_LABELS)
    matched = matched.drop_duplicates(subset="pidp", keep="first")

    total = matched["pidp"].isin(pidp_set).sum()
    logger.info(f"GOR extracted: {total}/{len(pidp_set)} pidps matched")
    return matched


def _load_usoc_gor(usoc_dir: Path, wave: str, pidp_set: set[int]) -> pd.DataFrame:
    """Load GOR from a single USoc wave."""
    col = f"{wave}_gor_dv"
    candidates = list(usoc_dir.rglob(f"{wave}_indresp.tab"))
    if not candidates:
        return pd.DataFrame(columns=["pidp", "gor_code"])

    try:
        df = pd.read_csv(candidates[0], sep="\t", usecols=["pidp", col], low_memory=False)
    except (ValueError, KeyError):
        return pd.DataFrame(columns=["pidp", "gor_code"])

    df = df[df["pidp"].isin(pidp_set)]
    df = df[df[col] > 0]  # filter out missing/inapplicable codes
    result = pd.DataFrame({"pidp": df["pidp"], "gor_code": df[col]})
    return result


def _load_bhps_gor(bhps_dir: Path, usoc_dir: Path, pidp_set: set[int]) -> pd.DataFrame:
    """Load region from BHPS wave 1 and map to GOR via cross-walk."""
    # Load cross-walk to map pidp → pid
    xwave_candidates = list(usoc_dir.rglob("xwavedat.tab"))
    if not xwave_candidates:
        return pd.DataFrame(columns=["pidp", "gor_code"])

    try:
        xwave = pd.read_csv(xwave_candidates[0], sep="\t", usecols=["pidp", "pid"], low_memory=False)
    except (ValueError, KeyError):
        return pd.DataFrame(columns=["pidp", "gor_code"])

    xwave = xwave[xwave["pidp"].isin(pidp_set)]
    xwave = xwave[xwave["pid"] > 0]
    if len(xwave) == 0:
        return pd.DataFrame(columns=["pidp", "gor_code"])

    # Load BHPS wave 1 region
    bhps_w1 = list(bhps_dir.rglob("aindresp.tab"))
    if not bhps_w1:
        return pd.DataFrame(columns=["pidp", "gor_code"])

    try:
        bhps_df = pd.read_csv(bhps_w1[0], sep="\t", usecols=["pid", "aregion"], low_memory=False)
    except (ValueError, KeyError):
        # Try with pidp column instead
        try:
            bhps_df = pd.read_csv(bhps_w1[0], sep="\t", usecols=["pidp", "aregion"], low_memory=False)
            bhps_df = bhps_df.rename(columns={"pidp": "pid"})
        except (ValueError, KeyError):
            return pd.DataFrame(columns=["pidp", "gor_code"])

    bhps_df = bhps_df[bhps_df["aregion"] > 0]
    bhps_df["gor_code"] = bhps_df["aregion"].map(_BHPS_REGION_TO_GOR)
    bhps_df = bhps_df.dropna(subset=["gor_code"])

    # Merge via cross-walk: pidp → pid → region → gor_code
    merged = xwave.merge(bhps_df[["pid", "gor_code"]], on="pid", how="inner")
    result = pd.DataFrame({"pidp": merged["pidp"], "gor_code": merged["gor_code"].astype(int)})
    return result
