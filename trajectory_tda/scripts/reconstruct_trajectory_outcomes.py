"""Reconstruct per-trajectory outcome variables from state sequences.

Reads the raw 9-state sequences from the P01 integration results and
computes derived outcome variables for each of the 27,280 trajectories.
These are saved as a single .npz file, aligned with the embedding rows,
for use in Mapper node colouring.

Derived variables:
  - employment_rate:  fraction of years in E states (EL/EM/EH)
  - unemployment_rate: fraction of years in U states (UL/UM/UH)
  - inactivity_rate:  fraction of years in I states (IL/IM/IH)
  - high_income_rate: fraction of years in high-income states (EH/UH/IH)
  - low_income_rate:  fraction of years in low-income states (EL/UL/IL)
  - final_emp_status: last state's employment category (0=E, 1=U, 2=I)
  - final_income_band: last state's income band (0=L, 1=M, 2=H)
  - initial_emp_status: first state's employment category
  - initial_income_band: first state's income band
  - emp_improvement: final_income_band - initial_income_band (positive = improvement)
  - escape_to_employment: 1 if started non-E and ended E, else 0
  - trajectory_length: number of observed years
  - n_state_changes: number of year-to-year state transitions
  - churning_rate: n_state_changes / (trajectory_length - 1)

Usage:
    python -m trajectory_tda.scripts.reconstruct_trajectory_outcomes
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# State classification
EMPLOYED_STATES = {"EL", "EM", "EH"}
UNEMPLOYED_STATES = {"UL", "UM", "UH"}
INACTIVE_STATES = {"IL", "IM", "IH"}

HIGH_INCOME_STATES = {"EH", "UH", "IH"}
MID_INCOME_STATES = {"EM", "UM", "IM"}
LOW_INCOME_STATES = {"EL", "UL", "IL"}

EMP_STATUS_MAP = {s: 0 for s in EMPLOYED_STATES}
EMP_STATUS_MAP.update({s: 1 for s in UNEMPLOYED_STATES})
EMP_STATUS_MAP.update({s: 2 for s in INACTIVE_STATES})

INCOME_BAND_MAP = {s: 0 for s in LOW_INCOME_STATES}
INCOME_BAND_MAP.update({s: 1 for s in MID_INCOME_STATES})
INCOME_BAND_MAP.update({s: 2 for s in HIGH_INCOME_STATES})


def compute_trajectory_outcomes(sequences: list[list[str]]) -> dict[str, np.ndarray]:
    """Compute per-trajectory outcome variables from state sequences.

    Args:
        sequences: List of N trajectories, each a list of state strings.

    Returns:
        Dict mapping variable names to (N,) arrays.
    """
    n = len(sequences)

    employment_rate = np.zeros(n, dtype=np.float64)
    unemployment_rate = np.zeros(n, dtype=np.float64)
    inactivity_rate = np.zeros(n, dtype=np.float64)
    high_income_rate = np.zeros(n, dtype=np.float64)
    low_income_rate = np.zeros(n, dtype=np.float64)
    final_emp_status = np.zeros(n, dtype=np.int32)
    final_income_band = np.zeros(n, dtype=np.int32)
    initial_emp_status = np.zeros(n, dtype=np.int32)
    initial_income_band = np.zeros(n, dtype=np.int32)
    emp_improvement = np.zeros(n, dtype=np.int32)
    escape_to_employment = np.zeros(n, dtype=np.int32)
    trajectory_length = np.zeros(n, dtype=np.int32)
    n_state_changes = np.zeros(n, dtype=np.int32)
    churning_rate = np.zeros(n, dtype=np.float64)

    for i, seq in enumerate(sequences):
        t = len(seq)
        trajectory_length[i] = t

        # Rate variables
        n_emp = sum(1 for s in seq if s in EMPLOYED_STATES)
        n_unemp = sum(1 for s in seq if s in UNEMPLOYED_STATES)
        n_inact = sum(1 for s in seq if s in INACTIVE_STATES)
        n_high = sum(1 for s in seq if s in HIGH_INCOME_STATES)
        n_low = sum(1 for s in seq if s in LOW_INCOME_STATES)

        employment_rate[i] = n_emp / t
        unemployment_rate[i] = n_unemp / t
        inactivity_rate[i] = n_inact / t
        high_income_rate[i] = n_high / t
        low_income_rate[i] = n_low / t

        # Initial and final states
        initial_emp_status[i] = EMP_STATUS_MAP[seq[0]]
        initial_income_band[i] = INCOME_BAND_MAP[seq[0]]
        final_emp_status[i] = EMP_STATUS_MAP[seq[-1]]
        final_income_band[i] = INCOME_BAND_MAP[seq[-1]]

        # Improvement
        emp_improvement[i] = INCOME_BAND_MAP[seq[-1]] - INCOME_BAND_MAP[seq[0]]

        # Escape: started non-employed, ended employed
        escape_to_employment[i] = int(
            seq[0] not in EMPLOYED_STATES and seq[-1] in EMPLOYED_STATES
        )

        # Churning
        changes = sum(1 for j in range(1, t) if seq[j] != seq[j - 1])
        n_state_changes[i] = changes
        churning_rate[i] = changes / (t - 1) if t > 1 else 0.0

    return {
        "employment_rate": employment_rate,
        "unemployment_rate": unemployment_rate,
        "inactivity_rate": inactivity_rate,
        "high_income_rate": high_income_rate,
        "low_income_rate": low_income_rate,
        "final_emp_status": final_emp_status,
        "final_income_band": final_income_band,
        "initial_emp_status": initial_emp_status,
        "initial_income_band": initial_income_band,
        "emp_improvement": emp_improvement,
        "escape_to_employment": escape_to_employment,
        "trajectory_length": trajectory_length,
        "n_state_changes": n_state_changes,
        "churning_rate": churning_rate,
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="Reconstruct trajectory outcomes from state sequences."
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/trajectory_tda_integration"),
    )
    args = parser.parse_args()

    results_dir = args.results_dir

    # Load sequences
    seq_path = results_dir / "01_trajectories_sequences.json"
    logger.info("Loading sequences from %s", seq_path)
    with open(seq_path) as f:
        sequences = json.load(f)
    logger.info("Loaded %d sequences", len(sequences))

    # Verify alignment with embeddings
    emb = np.load(results_dir / "embeddings.npy")
    if len(sequences) != emb.shape[0]:
        msg = f"Sequence count ({len(sequences)}) != embedding rows ({emb.shape[0]})"
        raise ValueError(msg)

    # Compute outcomes
    logger.info("Computing trajectory outcomes...")
    outcomes = compute_trajectory_outcomes(sequences)

    # Save
    output_path = results_dir / "trajectory_outcomes.npz"
    np.savez(output_path, **outcomes)
    logger.info("Saved %d variables to %s", len(outcomes), output_path)

    # Print summary
    logger.info("=" * 60)
    logger.info("TRAJECTORY OUTCOME SUMMARY (N=%d)", len(sequences))
    logger.info("=" * 60)
    for name, arr in sorted(outcomes.items()):
        if arr.dtype in (np.float64, np.float32):
            logger.info(
                "  %-22s mean=%.3f std=%.3f min=%.3f max=%.3f",
                name,
                arr.mean(),
                arr.std(),
                arr.min(),
                arr.max(),
            )
        else:
            unique, counts = np.unique(arr, return_counts=True)
            dist = ", ".join(f"{u}:{c}" for u, c in zip(unique, counts))
            logger.info("  %-22s values: %s", name, dist)

    # Per-regime breakdown
    with open(results_dir / "05_analysis.json") as f:
        analysis = json.load(f)
    gmm_labels = np.array(analysis["gmm_labels"], dtype=np.int64)

    logger.info("")
    logger.info("PER-REGIME MEANS")
    logger.info(
        "%-24s %8s %8s %8s %8s %8s %8s",
        "Regime",
        "EmpRate",
        "UnRate",
        "InRate",
        "HiInc",
        "LoInc",
        "Churn",
    )
    logger.info("-" * 80)
    for r in range(analysis["regimes"]["k_optimal"]):
        mask = gmm_labels == r
        logger.info(
            "R%d %-21s %8.3f %8.3f %8.3f %8.3f %8.3f %8.3f",
            r,
            "",
            outcomes["employment_rate"][mask].mean(),
            outcomes["unemployment_rate"][mask].mean(),
            outcomes["inactivity_rate"][mask].mean(),
            outcomes["high_income_rate"][mask].mean(),
            outcomes["low_income_rate"][mask].mean(),
            outcomes["churning_rate"][mask].mean(),
        )


if __name__ == "__main__":
    main()
