"""
Regime switching analysis: transition matrices and escape probabilities.

Given per-window regime assignments, constructs individual regime sequences,
computes empirical transition matrices, and estimates escape probabilities
from disadvantaged regimes.
"""

from __future__ import annotations

import logging
from collections import defaultdict

import numpy as np

logger = logging.getLogger(__name__)


def build_regime_sequences(
    windows: list[dict],
    window_regimes: np.ndarray,
) -> dict[int | str, list[dict]]:
    """Build per-individual regime sequences from windowed assignments.

    Args:
        windows: Window records from build_windows() (must have pidp,
                 window_id, start_year, end_year).
        window_regimes: (N_windows,) regime label per window.

    Returns:
        Dict mapping pidp → list of {regime, start_year, end_year},
        sorted by start_year.
    """
    by_pidp: dict[int | str, list[dict]] = defaultdict(list)

    for w, regime in zip(windows, window_regimes):
        by_pidp[w["pidp"]].append(
            {
                "regime": int(regime),
                "start_year": w["start_year"],
                "end_year": w["end_year"],
            }
        )

    # Sort each individual's windows by start_year
    for pidp in by_pidp:
        by_pidp[pidp].sort(key=lambda x: x["start_year"])

    logger.info(
        f"Built regime sequences for {len(by_pidp)} individuals "
        f"(mean length {np.mean([len(v) for v in by_pidp.values()]):.1f} windows)"
    )
    return dict(by_pidp)


def compute_transition_matrix(
    regime_sequences: dict[int | str, list[dict]],
    n_regimes: int = 7,
) -> np.ndarray:
    """Compute empirical transition matrix P(r_{t+1} | r_t).

    Args:
        regime_sequences: pidp → sorted list of {regime, ...} dicts.
        n_regimes: Number of distinct regimes.

    Returns:
        (n_regimes, n_regimes) row-stochastic matrix.
    """
    counts = np.zeros((n_regimes, n_regimes), dtype=np.float64)

    for seq in regime_sequences.values():
        for i in range(len(seq) - 1):
            r_from = seq[i]["regime"]
            r_to = seq[i + 1]["regime"]
            if 0 <= r_from < n_regimes and 0 <= r_to < n_regimes:
                counts[r_from, r_to] += 1

    # Row-normalise
    row_sums = counts.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1  # avoid division by zero for empty rows
    transition_matrix = counts / row_sums

    total_transitions = int(counts.sum())
    logger.info(f"Transition matrix: {total_transitions} transitions across {n_regimes} regimes")

    return transition_matrix


def compute_escape_probabilities(
    regime_sequences: dict[int | str, list[dict]],
    disadvantaged_regimes: set[int],
    good_regimes: set[int],
    max_horizon: int = 5,
) -> dict:
    """Compute escape probabilities from disadvantaged to good regimes.

    Args:
        regime_sequences: pidp → sorted list of {regime, ...} dicts.
        disadvantaged_regimes: Set of regime indices considered disadvantaged.
        good_regimes: Set of regime indices considered "escaped to".
        max_horizon: Maximum number of windows to look ahead.

    Returns:
        Dict with:
            n_starting_disadvantaged: count of individuals starting in bad regimes
            n_ever_escape: count that ever reach a good regime
            escape_by_horizon: {horizon: fraction escaped within that many windows}
            path_lengths: list of window counts to reach first good regime
    """
    n_starting = 0
    n_ever_escape = 0
    path_lengths: list[int] = []
    escape_by_horizon: dict[int, int] = {h: 0 for h in range(1, max_horizon + 1)}

    for seq in regime_sequences.values():
        if not seq or seq[0]["regime"] not in disadvantaged_regimes:
            continue

        n_starting += 1
        escaped = False

        for step, entry in enumerate(seq[1:], start=1):
            if entry["regime"] in good_regimes:
                n_ever_escape += 1
                path_lengths.append(step)
                escaped = True
                for h in range(step, max_horizon + 1):
                    escape_by_horizon[h] += 1
                break

        if not escaped:
            # Check if they stayed disadvantaged (no escape within sequence)
            pass

    escape_fractions = {}
    for h, count in escape_by_horizon.items():
        escape_fractions[h] = count / n_starting if n_starting > 0 else 0.0

    result = {
        "n_starting_disadvantaged": n_starting,
        "n_ever_escape": n_ever_escape,
        "ever_escape_rate": n_ever_escape / n_starting if n_starting > 0 else 0.0,
        "escape_by_horizon": escape_fractions,
        "path_lengths": path_lengths,
        "mean_path_length": float(np.mean(path_lengths)) if path_lengths else 0.0,
        "median_path_length": float(np.median(path_lengths)) if path_lengths else 0.0,
    }

    logger.info(
        f"Escape analysis: {n_starting} start disadvantaged, "
        f"{n_ever_escape} ever escape ({result['ever_escape_rate']:.1%}), "
        f"mean path length {result['mean_path_length']:.1f} windows"
    )

    return result
