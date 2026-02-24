"""
Extract employment status (E/U/I) from BHPS and USoc panel data.

Sources:
- BHPS (SN5151): jbstat variable, waves a-r (1991-2008)
- USoc (SN6614): harmonised jbstat, waves a-n (2009-2023)

Harmonisation note: BHPS jbstat codes are fully harmonised in the
SN6614 user guide. Pre-harmonised BHPS waves (a-p) verified for
alignment with the unified coding below.

Reference: Understanding Society User Guide
https://www.understandingsociety.ac.uk/wp-content/uploads/documentation/
user-guides/6614_main_survey_bhps_harmonised_user_guide.pdf
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# jbstat code → Employment Status mapping (shared across BHPS/USoc)
# ─────────────────────────────────────────────────────────────────────

# E = Employed (full/part/self-employed, govt training)
# U = Unemployed (actively seeking)
# I = Inactive (retired, family care, student, LT sick, other)
JBSTAT_TO_STATUS: dict[int, str] = {
    1: "E",  # Self-employed
    2: "E",  # Paid employment (full/part time)
    3: "U",  # Unemployed
    4: "I",  # Retired
    5: "I",  # On maternity leave
    6: "I",  # Looking after family/home
    7: "I",  # Full-time student
    8: "I",  # Long-term sick or disabled
    9: "I",  # On a government training scheme (BHPS-era)
    10: "E",  # Unpaid family business / govt training (USoc)
    97: "I",  # Doing something else
}

# BHPS waves a-r → letters used in variable prefixes
BHPS_WAVES = list("abcdefghijklmnopqr")  # 18 waves (1991-2008)

# USoc waves a-n → variable prefixes
USOC_WAVES = list("abcdefghijklmn")  # 14 waves (2009-2023)

# Wave letter → approximate calendar year (BHPS)
BHPS_WAVE_YEAR = {letter: 1991 + i for i, letter in enumerate(BHPS_WAVES)}

# Wave letter → approximate calendar year (USoc)
USOC_WAVE_YEAR = {letter: 2009 + i for i, letter in enumerate(USOC_WAVES)}


def _load_bhps_wave(
    data_dir: Path,
    wave_letter: str,
) -> pd.DataFrame | None:
    """Load jbstat from a single BHPS wave TAB file.

    BHPS indresp files follow the pattern:
        b{wave}_indresp.tab  (e.g., ba_indresp.tab)

    Key variables:
        {wave}pid   → person identifier (convert to pidp via xwaveid)
        {wave}jbstat → current economic activity
    """
    # BHPS indresp filename pattern
    pattern = f"b{wave_letter}_indresp.tab"
    candidates = list(data_dir.rglob(pattern))
    if not candidates:
        # Also try the SN5151 directory structure
        alt_pattern = f"{wave_letter}_indresp.tab"
        candidates = list(data_dir.rglob(alt_pattern))

    if not candidates:
        logger.debug(f"BHPS wave {wave_letter}: no file found matching {pattern}")
        return None

    fpath = candidates[0]
    logger.debug(f"Loading BHPS wave {wave_letter} from {fpath}")

    try:
        df = pd.read_csv(fpath, sep="\t", low_memory=False)
    except Exception:
        logger.warning(f"Could not read {fpath}")
        return None

    # Identify columns (case-insensitive matching)
    cols_lower = {c.lower(): c for c in df.columns}

    # Person ID: {wave}pid (BHPS) — we'll need xwaveid for pidp later
    pid_col = cols_lower.get(f"b{wave_letter}_pid") or cols_lower.get(f"{wave_letter}pid")
    jbstat_col = cols_lower.get(f"b{wave_letter}_jbstat") or cols_lower.get(f"{wave_letter}jbstat")

    # Try pidp directly (some BHPS files have it)
    pidp_col = cols_lower.get("pidp")

    if jbstat_col is None:
        logger.debug(f"BHPS wave {wave_letter}: jbstat column not found")
        return None

    # Build output
    id_col = pidp_col if pidp_col else pid_col
    if id_col is None:
        logger.debug(f"BHPS wave {wave_letter}: no person ID column found")
        return None

    result = pd.DataFrame(
        {
            "pidp": df[id_col],
            "jbstat_raw": pd.to_numeric(df[jbstat_col], errors="coerce"),
            "year": BHPS_WAVE_YEAR[wave_letter],
            "source": "bhps",
            "wave": wave_letter,
        }
    )

    return result.dropna(subset=["jbstat_raw"])


def _load_usoc_wave(
    data_dir: Path,
    wave_letter: str,
) -> pd.DataFrame | None:
    """Load jbstat from a single USoc wave TAB file.

    USoc indresp files follow the pattern:
        {wave}_indresp.tab  (e.g., a_indresp.tab)

    Key variables:
        pidp      → cross-wave person identifier
        {wave}_jbstat → current economic activity
    """
    pattern = f"{wave_letter}_indresp.tab"
    candidates = list(data_dir.rglob(pattern))

    if not candidates:
        logger.debug(f"USoc wave {wave_letter}: no file found matching {pattern}")
        return None

    fpath = candidates[0]
    logger.debug(f"Loading USoc wave {wave_letter} from {fpath}")

    try:
        df = pd.read_csv(fpath, sep="\t", low_memory=False)
    except Exception:
        logger.warning(f"Could not read {fpath}")
        return None

    cols_lower = {c.lower(): c for c in df.columns}

    pidp_col = cols_lower.get("pidp")
    jbstat_col = cols_lower.get(f"{wave_letter}_jbstat")

    if pidp_col is None or jbstat_col is None:
        logger.debug(f"USoc wave {wave_letter}: missing pidp or jbstat column")
        return None

    result = pd.DataFrame(
        {
            "pidp": df[pidp_col],
            "jbstat_raw": pd.to_numeric(df[jbstat_col], errors="coerce"),
            "year": USOC_WAVE_YEAR[wave_letter],
            "source": "usoc",
            "wave": wave_letter,
        }
    )

    return result.dropna(subset=["jbstat_raw"])


def _map_jbstat_to_status(jbstat: int) -> str | None:
    """Map a raw jbstat code to E/U/I. Returns None for invalid codes."""
    return JBSTAT_TO_STATUS.get(int(jbstat))


def _assign_annual_status(group: pd.DataFrame) -> pd.Series:
    """For a person-year with multiple observations, take modal status.

    Returns a Series with emp_status and fflag columns.
    """
    statuses = group["emp_status"].dropna()
    if statuses.empty:
        return pd.Series({"emp_status": None, "fflag": None})

    mode = statuses.mode()
    status = mode.iloc[0] if len(mode) > 0 else None

    # Flag if multiple distinct statuses observed in the year
    n_distinct = statuses.nunique()
    fflag = "mixed" if n_distinct > 1 else None

    return pd.Series({"emp_status": status, "fflag": fflag})


def extract_employment_status(
    data_dir: str | Path,
    bhps_subdir: str = "UKDA-5151",
    usoc_subdir: str = "UKDA-6614",
    bhps_waves: list[str] | None = None,
    usoc_waves: list[str] | None = None,
) -> pd.DataFrame:
    """Extract per-person-year employment status from BHPS and USoc.

    Args:
        data_dir: Root data directory (e.g., 'data/')
        bhps_subdir: Subdirectory for BHPS files
        usoc_subdir: Subdirectory for USoc files
        bhps_waves: Specific BHPS waves to load (default: all a-r)
        usoc_waves: Specific USoc waves to load (default: all a-n)

    Returns:
        DataFrame with columns [pidp, year, emp_status, fflag, source]
        where emp_status ∈ {'E', 'U', 'I'} and fflag='mixed' when
        multiple distinct statuses were observed in the reference year.
    """
    data_dir = Path(data_dir)
    bhps_dir = data_dir / bhps_subdir
    usoc_dir = data_dir / usoc_subdir

    waves_bhps = bhps_waves or BHPS_WAVES
    waves_usoc = usoc_waves or USOC_WAVES

    all_dfs = []

    # Load BHPS waves
    for wl in waves_bhps:
        df = _load_bhps_wave(bhps_dir, wl)
        if df is not None and len(df) > 0:
            all_dfs.append(df)
            logger.info(f"BHPS wave {wl} ({BHPS_WAVE_YEAR[wl]}): {len(df)} obs")

    # Load USoc waves
    for wl in waves_usoc:
        df = _load_usoc_wave(usoc_dir, wl)
        if df is not None and len(df) > 0:
            all_dfs.append(df)
            logger.info(f"USoc wave {wl} ({USOC_WAVE_YEAR[wl]}): {len(df)} obs")

    if not all_dfs:
        logger.warning("No data loaded from BHPS or USoc")
        return pd.DataFrame(columns=["pidp", "year", "emp_status", "fflag", "source"])

    combined = pd.concat(all_dfs, ignore_index=True)
    logger.info(f"Combined: {len(combined)} person-year observations")

    # Map jbstat codes to E/U/I
    combined["emp_status"] = combined["jbstat_raw"].apply(_map_jbstat_to_status)

    # Drop unmappable codes
    n_unmapped = combined["emp_status"].isna().sum()
    if n_unmapped > 0:
        logger.info(f"Dropped {n_unmapped} observations with unmappable jbstat codes")
    combined = combined.dropna(subset=["emp_status"])

    # Resolve multiple observations per person-year (modal status)
    if combined.duplicated(subset=["pidp", "year"]).any():
        logger.info("Resolving multiple obs per person-year (modal status)")
        resolved = combined.groupby(["pidp", "year"]).apply(_assign_annual_status, include_groups=False).reset_index()
        # Merge back source info (take first)
        source_info = combined.groupby(["pidp", "year"])["source"].first().reset_index()
        result = resolved.merge(source_info, on=["pidp", "year"], how="left")
    else:
        result = combined[["pidp", "year", "emp_status", "source"]].copy()
        result["fflag"] = None

    result = result[["pidp", "year", "emp_status", "fflag", "source"]]
    logger.info(f"Final: {len(result)} person-year records, {result['pidp'].nunique()} unique persons")

    return result
