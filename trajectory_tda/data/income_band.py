"""
Extract income band (L/M/H) from BHPS and USoc derived net income.

Implements HBAI-standard thresholds against contemporary national medians:
  L (Low):    <60% national median (poverty line)
  M (Middle): 60-100% median
  H (High):   >100% median

Sources:
  - USoc: fihhmnnet1_dv (monthly net household income, equivalised BHC)
  - BHPS: fihhmn (monthly net household income)

Reference: HBAI Quality & Methodology Report
https://assets.publishing.service.gov.uk/media/5e7b3b3986650c743e9c7abe/
households-below-average-income-quality-methodology-2018-2019.pdf
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Wave letters for each survey
BHPS_WAVES = list("abcdefghijklmnopqr")
USOC_WAVES = list("abcdefghijklmn")

BHPS_WAVE_YEAR = {letter: 1991 + i for i, letter in enumerate(BHPS_WAVES)}
USOC_WAVE_YEAR = {letter: 2009 + i for i, letter in enumerate(USOC_WAVES)}

# Default HBAI poverty threshold (proportion of median)
DEFAULT_THRESHOLD = 0.6


def _load_bhps_income_wave(
    data_dir: Path,
    wave_letter: str,
) -> pd.DataFrame | None:
    """Load equivalised household income from a single BHPS wave.

    BHPS uses fihhmn (raw monthly net household income). We equivalise
    using the modified OECD scale (eq_moecd) from hhresp, matching the
    approach used for USoc's fihhmnnet1_dv (which is already equivalised).
    """
    # Find indresp file
    for prefix in [f"b{wave_letter}_", f"{wave_letter}_", f"{wave_letter}"]:
        pattern = f"{prefix}indresp.tab"
        candidates = list(data_dir.rglob(pattern))
        if candidates:
            break
    else:
        logger.debug(f"BHPS income wave {wave_letter}: no indresp file found")
        return None

    fpath_ind = candidates[0]
    try:
        df_ind = pd.read_csv(fpath_ind, sep="\t", low_memory=False)
    except Exception:
        logger.warning(f"Could not read {fpath_ind}")
        return None

    cols_ind = {c.lower(): c for c in df_ind.columns}

    # Person ID
    pidp_col = (
        cols_ind.get("pidp")
        or cols_ind.get(f"b{wave_letter}_pid")
        or cols_ind.get("pid")
    )
    if pidp_col is None:
        return None

    # Household ID for hhresp merge
    hid_col_ind = (
        cols_ind.get(f"b{wave_letter}_hidp")
        or cols_ind.get(f"{wave_letter}hid")
        or cols_ind.get(f"b{wave_letter}_hid")
    )

    # Income: try equivalised first, then raw (BHPS SN5151 format: {wave}fihhmn)
    income_col = None
    for candidate in [
        f"b{wave_letter}_fihhmnnet1_dv",
        f"{wave_letter}_fihhmnnet1_dv",
        f"b{wave_letter}_fihhmn",
        f"{wave_letter}_fihhmn",
        f"{wave_letter}fihhmn",
        "fihhmnnet1_dv",
        "fihhmn",
    ]:
        if candidate in cols_ind:
            income_col = cols_ind[candidate]
            break

    if income_col is None:
        logger.debug(f"BHPS wave {wave_letter}: no income column found")
        return None

    income_values = pd.to_numeric(df_ind[income_col], errors="coerce")

    # Equivalise raw BHPS income using modified OECD scale from hhresp
    is_equivalised = "fihhmnnet1_dv" in income_col.lower()
    if not is_equivalised and hid_col_ind is not None:
        # Find hhresp file
        for prefix in [f"b{wave_letter}_", f"{wave_letter}_", f"{wave_letter}"]:
            hh_pattern = f"{prefix}hhresp.tab"
            hh_candidates = list(data_dir.rglob(hh_pattern))
            if hh_candidates:
                break
        else:
            hh_candidates = []

        if hh_candidates:
            try:
                df_hh = pd.read_csv(hh_candidates[0], sep="\t", low_memory=False)
                cols_hh = {c.lower(): c for c in df_hh.columns}

                # Find equivalence scale column
                eq_col = None
                for eq_candidate in [
                    f"b{wave_letter}_eq_moecd",
                    f"{wave_letter}eq_moecd",
                    f"{wave_letter}_eq_moecd",
                    "eq_moecd",
                ]:
                    if eq_candidate in cols_hh:
                        eq_col = cols_hh[eq_candidate]
                        break

                # Find household ID in hhresp
                hid_col_hh = (
                    cols_hh.get(f"b{wave_letter}_hidp")
                    or cols_hh.get(f"{wave_letter}hid")
                    or cols_hh.get(f"b{wave_letter}_hid")
                )

                if eq_col is not None and hid_col_hh is not None:
                    eq_scale = pd.to_numeric(df_hh[eq_col], errors="coerce")
                    hh_lookup = pd.DataFrame(
                        {
                            "hid": df_hh[hid_col_hh],
                            "eq_moecd": eq_scale,
                        }
                    ).dropna(subset=["eq_moecd"])
                    hh_lookup = hh_lookup[hh_lookup["eq_moecd"] > 0]

                    ind_hid = df_ind[hid_col_ind]
                    merged = pd.DataFrame(
                        {
                            "idx": range(len(df_ind)),
                            "hid": ind_hid,
                        }
                    ).merge(hh_lookup, on="hid", how="left")

                    eq_values = merged.set_index("idx")["eq_moecd"]
                    valid_eq = eq_values.reindex(range(len(df_ind)))
                    income_values = income_values / valid_eq
                    logger.debug(
                        f"BHPS wave {wave_letter}: equivalised income using eq_moecd"
                    )
                else:
                    logger.warning(
                        f"BHPS wave {wave_letter}: eq_moecd not found, using raw income"
                    )
            except Exception:
                logger.warning(
                    f"BHPS wave {wave_letter}: could not load hhresp for equivalisation"
                )

    result = pd.DataFrame(
        {
            "pidp": df_ind[pidp_col],
            "income_raw": income_values,
            "year": BHPS_WAVE_YEAR[wave_letter],
            "source": "bhps",
        }
    )

    return result.dropna(subset=["income_raw"])


def _load_usoc_income_wave(
    data_dir: Path,
    wave_letter: str,
) -> pd.DataFrame | None:
    """Load household income from a single USoc wave.

    USoc uses fihhmnnet1_dv (derived monthly net HH income, equivalised BHC)
    from the individual response file or household response file.
    """
    pattern_ind = f"{wave_letter}_indresp.tab"
    candidates_ind = list(data_dir.rglob(pattern_ind))
    pattern_hh = f"{wave_letter}_hhresp.tab"
    candidates_hh = list(data_dir.rglob(pattern_hh))

    if not candidates_ind or not candidates_hh:
        logger.debug(f"USoc income wave {wave_letter}: missing indresp or hhresp")
        return None

    try:
        df_ind = pd.read_csv(candidates_ind[0], sep="\t", low_memory=False)
        df_hh = pd.read_csv(candidates_hh[0], sep="\t", low_memory=False)
    except Exception:
        logger.warning(f"Could not read USoc wave {wave_letter} files")
        return None

    cols_ind = {c.lower(): c for c in df_ind.columns}
    cols_hh = {c.lower(): c for c in df_hh.columns}

    pidp_col = cols_ind.get("pidp")
    hidp_col_ind = cols_ind.get(f"{wave_letter}_hidp")
    hidp_col_hh = cols_hh.get(f"{wave_letter}_hidp")

    # Income: fihhmnnet1_dv (primary) or fihhmngrs_dv (gross)
    inc_col = None
    for candidate in [
        f"{wave_letter}_fihhmnnet1_dv",
        "fihhmnnet1_dv",
        f"{wave_letter}_fihhmngrs_dv",
    ]:
        if candidate in cols_hh:
            inc_col = cols_hh[candidate]
            break

    if (
        pidp_col is None
        or hidp_col_ind is None
        or hidp_col_hh is None
        or inc_col is None
    ):
        logger.debug(f"USoc wave {wave_letter}: missing pidp, hidp or income column")
        return None

    # Merge individual to household on hidp
    df_merged = df_ind[[pidp_col, hidp_col_ind]].merge(
        df_hh[[hidp_col_hh, inc_col]],
        left_on=hidp_col_ind,
        right_on=hidp_col_hh,
        how="inner",
    )

    result = pd.DataFrame(
        {
            "pidp": df_merged[pidp_col],
            "income_raw": pd.to_numeric(df_merged[inc_col], errors="coerce"),
            "year": USOC_WAVE_YEAR[wave_letter],
            "source": "usoc",
        }
    )

    return result.dropna(subset=["income_raw"])


def _classify_income_band(
    income: float,
    median: float,
    threshold: float = DEFAULT_THRESHOLD,
) -> str:
    """Classify income into L/M/H relative to national median.

    L: < threshold × median  (default 60%, HBAI poverty line)
    M: threshold–100% of median
    H: > 100% of median
    """
    if income < threshold * median:
        return "L"
    elif income <= median:
        return "M"
    else:
        return "H"


def extract_income_bands(
    data_dir: str | Path,
    bhps_subdir: str = "UKDA-5151-tab",
    usoc_subdir: str = "UKDA-6614-tab",
    bhps_waves: list[str] | None = None,
    usoc_waves: list[str] | None = None,
    threshold: float = DEFAULT_THRESHOLD,
) -> pd.DataFrame:
    """Extract per-person-year income band from BHPS and USoc.

    Args:
        data_dir: Root data directory
        bhps_subdir: Subdirectory for BHPS files
        usoc_subdir: Subdirectory for USoc files
        bhps_waves: Specific BHPS waves (default: all a-r)
        usoc_waves: Specific USoc waves (default: all a-n)
        threshold: Low-income threshold as proportion of median
                   (default 0.6 = HBAI standard)

    Returns:
        DataFrame with columns [pidp, year, income_band, source]
        where income_band ∈ {'L', 'M', 'H'}
    """
    data_dir = Path(data_dir)
    bhps_dir = data_dir / bhps_subdir
    usoc_dir = data_dir / usoc_subdir

    waves_bhps = bhps_waves if bhps_waves is not None else BHPS_WAVES
    waves_usoc = usoc_waves if usoc_waves is not None else USOC_WAVES

    all_dfs = []

    # Load BHPS waves
    for wl in waves_bhps:
        df = _load_bhps_income_wave(bhps_dir, wl)
        if df is not None and len(df) > 0:
            all_dfs.append(df)
            logger.info(f"BHPS income wave {wl} ({BHPS_WAVE_YEAR[wl]}): {len(df)} obs")

    # Load USoc waves
    for wl in waves_usoc:
        df = _load_usoc_income_wave(usoc_dir, wl)
        if df is not None and len(df) > 0:
            all_dfs.append(df)
            logger.info(f"USoc income wave {wl} ({USOC_WAVE_YEAR[wl]}): {len(df)} obs")

    if not all_dfs:
        logger.warning("No income data loaded from BHPS or USoc")
        return pd.DataFrame(columns=["pidp", "year", "income_band", "source"])

    combined = pd.concat(all_dfs, ignore_index=True)
    logger.info(f"Combined income: {len(combined)} person-year obs")

    # Clip negative incomes to zero (standard HBAI practice)
    n_negative = (combined["income_raw"] < 0).sum()
    if n_negative > 0:
        logger.info(f"Clipping {n_negative} negative incomes to zero")
    combined["income_raw"] = combined["income_raw"].clip(lower=0)

    # Compute national median per wave from FULL sample (avoid selection bias)
    medians = combined.groupby("year")["income_raw"].median()
    logger.info("National medians per wave:")
    for year, med in medians.items():
        logger.info(f"  {year}: £{med:.2f}/month")

    # Classify income bands
    combined["income_band"] = combined.apply(
        lambda row: _classify_income_band(
            row["income_raw"], medians[row["year"]], threshold
        ),
        axis=1,
    )

    # If duplicate person-years, take first (shouldn't happen with indresp)
    if combined.duplicated(subset=["pidp", "year"]).any():
        logger.info("Deduplicating person-year income records (taking first)")
        combined = combined.drop_duplicates(subset=["pidp", "year"], keep="first")

    result = combined[["pidp", "year", "income_band", "source"]]
    logger.info(
        f"Final: {len(result)} person-year records, {result['pidp'].nunique()} unique persons"
    )

    # Report band distribution
    dist = result["income_band"].value_counts(normalize=True)
    for band in ["L", "M", "H"]:
        logger.info(f"  {band}: {dist.get(band, 0):.1%}")

    return result
