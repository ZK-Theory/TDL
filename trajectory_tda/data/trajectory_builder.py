"""
Build employment-income state trajectories from BHPS/USoc panel data.

Merges employment status (E/U/I) and income band (L/M/H) per person-year
into 9-state sequences, filters for minimum trajectory length, handles gaps,
and attaches covariates for stratified analysis.

The 9 combined states are:
    EL, EM, EH  (Employed: low/mid/high income)
    UL, UM, UH  (Unemployed: low/mid/high income)
    IL, IM, IH  (Inactive: low/mid/high income)
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from trajectory_tda.data.employment_status import extract_employment_status
from trajectory_tda.data.income_band import extract_income_bands

logger = logging.getLogger(__name__)

# The 9 valid combined states
STATES = ["EL", "EM", "EH", "UL", "UM", "UH", "IL", "IM", "IH"]


def _interpolate_gaps(
    years: list[int],
    states: list[str],
    max_gap: int = 2,
) -> tuple[list[int], list[str]] | None:
    """Fill gaps of ≤ max_gap years using nearest-neighbour interpolation.

    Returns None if any gap exceeds max_gap.
    """
    if len(years) <= 1:
        return years, states

    filled_years = []
    filled_states = []

    sorted_pairs = sorted(zip(years, states))
    prev_year, prev_state = sorted_pairs[0]
    filled_years.append(prev_year)
    filled_states.append(prev_state)

    for curr_year, curr_state in sorted_pairs[1:]:
        gap = curr_year - prev_year - 1
        if gap > max_gap:
            return None  # Trajectory broken by gap > max_gap
        elif gap > 0:
            # Fill with nearest-neighbour (previous state)
            for fill_year in range(prev_year + 1, curr_year):
                filled_years.append(fill_year)
                filled_states.append(prev_state)

        filled_years.append(curr_year)
        filled_states.append(curr_state)
        prev_year = curr_year
        prev_state = curr_state

    return filled_years, filled_states


def _find_longest_consecutive_run(
    years: list[int],
    states: list[str],
    min_years: int,
) -> tuple[list[int], list[str]] | None:
    """Find the longest consecutive run of ≥ min_years in the trajectory.

    Returns the longest consecutive sub-trajectory, or None if no run
    meets the minimum length.
    """
    if len(years) < min_years:
        return None

    # Find consecutive runs
    best_start = 0
    best_len = 1
    curr_start = 0
    curr_len = 1

    sorted_pairs = sorted(zip(years, states))
    sorted_years = [p[0] for p in sorted_pairs]
    sorted_states = [p[1] for p in sorted_pairs]

    for i in range(1, len(sorted_years)):
        if sorted_years[i] == sorted_years[i - 1] + 1:
            curr_len += 1
        else:
            if curr_len > best_len:
                best_start = curr_start
                best_len = curr_len
            curr_start = i
            curr_len = 1

    if curr_len > best_len:
        best_start = curr_start
        best_len = curr_len

    if best_len < min_years:
        return None

    return (
        sorted_years[best_start : best_start + best_len],
        sorted_states[best_start : best_start + best_len],
    )


def build_trajectories(
    emp_df: pd.DataFrame | None = None,
    inc_df: pd.DataFrame | None = None,
    data_dir: str | Path | None = None,
    min_years: int = 10,
    max_gap: int = 2,
    bhps_subdir: str = "UKDA-5151",
    usoc_subdir: str = "UKDA-6614",
    income_threshold: float = 0.6,
) -> tuple[list[list[str]], pd.DataFrame]:
    """Build per-person state trajectories from employment + income data.

    Can either accept pre-computed DataFrames or extract from raw files.

    Args:
        emp_df: Pre-extracted employment status DataFrame
                (columns: pidp, year, emp_status)
        inc_df: Pre-extracted income band DataFrame
                (columns: pidp, year, income_band)
        data_dir: Root data directory (used if emp_df/inc_df not provided)
        min_years: Minimum trajectory length after gap-filling
        max_gap: Maximum allowable gap (years) for interpolation
        bhps_subdir: BHPS data subdirectory
        usoc_subdir: USoc data subdirectory
        income_threshold: Poverty threshold for income classification

    Returns:
        trajectories: List of state sequences (one per person)
        metadata: DataFrame with per-person covariates:
            [pidp, n_years, start_year, end_year, n_imputed,
             pct_imputed, dominant_state]
    """
    # Extract if not provided
    if emp_df is None:
        if data_dir is None:
            raise ValueError("Provide emp_df/inc_df or data_dir")
        emp_df = extract_employment_status(data_dir, bhps_subdir, usoc_subdir)

    if inc_df is None:
        if data_dir is None:
            raise ValueError("Provide emp_df/inc_df or data_dir")
        inc_df = extract_income_bands(
            data_dir,
            bhps_subdir,
            usoc_subdir,
            threshold=income_threshold,
        )

    # Merge employment and income on (pidp, year) — inner join
    merged = pd.merge(
        emp_df[["pidp", "year", "emp_status"]],
        inc_df[["pidp", "year", "income_band"]],
        on=["pidp", "year"],
        how="inner",
    )
    logger.info(f"Merged employment + income: {len(merged)} person-year obs, {merged['pidp'].nunique()} unique persons")

    # Construct combined state label
    merged["state"] = merged["emp_status"] + merged["income_band"]

    # Validate all states are valid
    invalid = ~merged["state"].isin(STATES)
    if invalid.any():
        n_inv = invalid.sum()
        logger.warning(f"Dropping {n_inv} obs with invalid states")
        merged = merged[~invalid]

    # Build trajectories per person
    trajectories = []
    metadata_rows = []
    n_dropped_short = 0
    n_dropped_gap = 0
    total_imputed = 0

    for pidp, group in merged.groupby("pidp"):
        years = group["year"].tolist()
        states = group["state"].tolist()

        # Deduplicate years (take first if multiple)
        seen = {}
        unique_years = []
        unique_states = []
        for y, s in zip(years, states):
            if y not in seen:
                seen[y] = True
                unique_years.append(y)
                unique_states.append(s)

        # Try gap interpolation
        n_before = len(unique_years)
        result = _interpolate_gaps(unique_years, unique_states, max_gap)
        if result is None:
            n_dropped_gap += 1
            continue

        filled_years, filled_states = result
        n_imputed = len(filled_years) - n_before

        # Find longest consecutive run
        run = _find_longest_consecutive_run(filled_years, filled_states, min_years)
        if run is None:
            n_dropped_short += 1
            continue

        final_years, final_states = run

        trajectories.append(final_states)
        total_imputed += n_imputed

        # Compute dominant state
        from collections import Counter

        state_counts = Counter(final_states)
        dominant = state_counts.most_common(1)[0][0]

        metadata_rows.append(
            {
                "pidp": pidp,
                "n_years": len(final_states),
                "start_year": min(final_years),
                "end_year": max(final_years),
                "n_imputed": n_imputed,
                "pct_imputed": (n_imputed / len(final_states) * 100 if len(final_states) > 0 else 0),
                "dominant_state": dominant,
            }
        )

    metadata = pd.DataFrame(metadata_rows)

    logger.info(
        f"Built {len(trajectories)} trajectories (dropped: {n_dropped_short} too short, {n_dropped_gap} broken gaps)"
    )
    if len(metadata) > 0:
        logger.info(
            f"Trajectory lengths: "
            f"mean={metadata['n_years'].mean():.1f}, "
            f"min={metadata['n_years'].min()}, "
            f"max={metadata['n_years'].max()}"
        )
        logger.info(
            f"Total imputed person-years: {total_imputed} ({total_imputed / metadata['n_years'].sum() * 100:.1f}%)"
        )

        # State distribution
        all_states = [s for traj in trajectories for s in traj]
        state_dist = pd.Series(all_states).value_counts(normalize=True)
        logger.info("State distribution:")
        for state in STATES:
            logger.info(f"  {state}: {state_dist.get(state, 0):.1%}")

    return trajectories, metadata


def build_trajectories_from_raw(
    data_dir: str | Path,
    min_years: int = 10,
    max_gap: int = 2,
    income_threshold: float = 0.6,
) -> tuple[list[list[str]], pd.DataFrame]:
    """Convenience function: extract data and build trajectories in one call.

    Args:
        data_dir: Root data directory containing SN5151/ and SN6614/
        min_years: Minimum trajectory length
        max_gap: Maximum gap for interpolation
        income_threshold: HBAI poverty line threshold

    Returns:
        (trajectories, metadata) — same as build_trajectories()
    """
    return build_trajectories(
        data_dir=data_dir,
        min_years=min_years,
        max_gap=max_gap,
        income_threshold=income_threshold,
    )
