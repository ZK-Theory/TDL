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
    """Load household income from a single BHPS wave.

    BHPS uses fihhmn (monthly net household income) from the household
    questionnaire. We link to individuals via household ID.
    """
    # Try indresp first (has both pid and income for some waves)
    for prefix in [f"b{wave_letter}", wave_letter]:
        pattern = f"{prefix}_indresp.tab"
        candidates = list(data_dir.rglob(pattern))
        if candidates:
            break
    else:
        logger.debug(f"BHPS income wave {wave_letter}: no indresp file found")
        return None

    fpath = candidates[0]
    try:
        df = pd.read_csv(fpath, sep="\t", low_memory=False)
    except Exception:
        logger.warning(f"Could not read {fpath}")
        return None

    cols_lower = {c.lower(): c for c in df.columns}

    # Person ID
    pidp_col = cols_lower.get("pidp") or cols_lower.get(f"b{wave_letter}_pid")
    if pidp_col is None:
        return None

    # Income: try fihhmnnet1_dv (derived), fihhmn (raw), or wave-prefixed
    income_col = None
    for candidate in [
        f"b{wave_letter}_fihhmnnet1_dv",
        f"{wave_letter}_fihhmnnet1_dv",
        f"b{wave_letter}_fihhmn",
        f"{wave_letter}_fihhmn",
        "fihhmnnet1_dv",
        "fihhmn",
    ]:
        if candidate in cols_lower:
            income_col = cols_lower[candidate]
            break

    if income_col is None:
        logger.debug(f"BHPS wave {wave_letter}: no income column found")
        return None

    result = pd.DataFrame(
        {
            "pidp": df[pidp_col],
            "income_raw": pd.to_numeric(df[income_col], errors="coerce"),
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
    pattern = f"{wave_letter}_indresp.tab"
    candidates = list(data_dir.rglob(pattern))

    if not candidates:
        logger.debug(f"USoc income wave {wave_letter}: no file found")
        return None

    fpath = candidates[0]
    try:
        df = pd.read_csv(fpath, sep="\t", low_memory=False)
    except Exception:
        logger.warning(f"Could not read {fpath}")
        return None

    cols_lower = {c.lower(): c for c in df.columns}

    pidp_col = cols_lower.get("pidp")

    # Income: fihhmnnet1_dv (primary) or fihhmngrs_dv (gross)
    income_col = None
    for candidate in [
        f"{wave_letter}_fihhmnnet1_dv",
        "fihhmnnet1_dv",
        f"{wave_letter}_fihhmngrs_dv",
    ]:
        if candidate in cols_lower:
            income_col = cols_lower[candidate]
            break

    if pidp_col is None or income_col is None:
        logger.debug(f"USoc wave {wave_letter}: missing pidp or income column")
        return None

    result = pd.DataFrame(
        {
            "pidp": df[pidp_col],
            "income_raw": pd.to_numeric(df[income_col], errors="coerce"),
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
    bhps_subdir: str = "UKDA-5151",
    usoc_subdir: str = "UKDA-6614",
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

    waves_bhps = bhps_waves or BHPS_WAVES
    waves_usoc = usoc_waves or USOC_WAVES

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
        lambda row: _classify_income_band(row["income_raw"], medians[row["year"]], threshold),
        axis=1,
    )

    # If duplicate person-years, take first (shouldn't happen with indresp)
    if combined.duplicated(subset=["pidp", "year"]).any():
        logger.info("Deduplicating person-year income records (taking first)")
        combined = combined.drop_duplicates(subset=["pidp", "year"], keep="first")

    result = combined[["pidp", "year", "income_band", "source"]]
    logger.info(f"Final: {len(result)} person-year records, {result['pidp'].nunique()} unique persons")

    # Report band distribution
    dist = result["income_band"].value_counts(normalize=True)
    for band in ["L", "M", "H"]:
        logger.info(f"  {band}: {dist.get(band, 0):.1%}")

    return result
