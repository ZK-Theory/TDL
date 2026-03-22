"""
Cycle detection: identify H₁ loops as poverty / unemployment traps.

Extracts persistent H₁ features, identifies representative trajectories
closest to loop generators, and characterises the cyclic state patterns
they correspond to.
"""

from __future__ import annotations

import logging
from collections import Counter

import numpy as np

from poverty_tda.topology.multidim_ph import PHResult, persistence_summary
from trajectory_tda.embedding.ngram_embed import STATES

logger = logging.getLogger(__name__)


def _find_representative_trajectories(
    embeddings: np.ndarray,
    center: np.ndarray,
    k: int = 5,
) -> np.ndarray:
    """Find k trajectories closest to a given point in embedding space."""
    dists = np.linalg.norm(embeddings - center, axis=1)
    return np.argsort(dists)[:k]


def _characterise_cycles(
    trajectories: list[list[str]],
    indices: np.ndarray,
) -> dict:
    """Analyse cyclic patterns in representative trajectories.

    Identifies state transitions that form cycles (a→b→...→a).
    """
    # Count transitions
    transition_counts: Counter = Counter()
    state_counts: Counter = Counter()
    cycle_lengths = []

    for idx in indices:
        traj = trajectories[idx]
        for s in traj:
            state_counts[s] += 1
        for t in range(len(traj) - 1):
            transition_counts[(traj[t], traj[t + 1])] += 1

        # Detect cycles: find repeated visits to same state
        seen_at: dict[str, list[int]] = {}
        for t, s in enumerate(traj):
            if s not in seen_at:
                seen_at[s] = []
            seen_at[s].append(t)

        for s, positions in seen_at.items():
            if len(positions) > 1:
                for i in range(len(positions) - 1):
                    cycle_len = positions[i + 1] - positions[i]
                    if cycle_len > 1:  # Non-trivial cycle
                        cycle_lengths.append(cycle_len)

    # Top transitions
    total_trans = sum(transition_counts.values())
    top_transitions = [
        {
            "from": t[0],
            "to": t[1],
            "frequency": c / total_trans if total_trans > 0 else 0,
        }
        for t, c in transition_counts.most_common(10)
    ]

    # State composition
    total_states = sum(state_counts.values())
    composition = {s: state_counts.get(s, 0) / total_states for s in STATES}

    return {
        "n_representatives": len(indices),
        "top_transitions": top_transitions,
        "composition": composition,
        "mean_cycle_length": (float(np.mean(cycle_lengths)) if cycle_lengths else 0),
        "median_cycle_length": (float(np.median(cycle_lengths)) if cycle_lengths else 0),
        "n_cycles_detected": len(cycle_lengths),
    }


def detect_cycles(
    ph_result: dict,
    embeddings: np.ndarray,
    trajectories: list[list[str]],
    min_persistence_ratio: float = 0.1,
    n_representatives: int = 10,
    method_key: str | None = None,
) -> dict:
    """Detect and characterise H₁ loops (cycles / traps).

    Args:
        ph_result: Output from compute_trajectory_ph
        embeddings: (N, K) trajectory embeddings
        trajectories: Raw state sequences
        min_persistence_ratio: Include H₁ features with persistence >
            this fraction of max persistence
        n_representatives: Number of representative trajectories per loop
        method_key: Which PH method to use ('witness', 'maxmin_vr');
            default: first available

    Returns:
        Dict with:
            - n_persistent_loops: count of significant H₁ features
            - loop_profiles: per-loop characterisation
            - h1_summary: persistence diagram statistics
    """
    # Get PHResult
    if method_key is None:
        for k in ["witness", "maxmin_vr"]:
            if k in ph_result:
                method_key = k
                break
    if method_key is None or method_key not in ph_result:
        logger.warning("No PH result available for cycle detection")
        return {"n_persistent_loops": 0, "loop_profiles": [], "method": None}

    ph: PHResult = ph_result[method_key]
    summary = persistence_summary(ph)
    h1_summary = summary.get("H1", {})

    max_pers = h1_summary.get("max_persistence", 0)
    threshold = max_pers * min_persistence_ratio

    logger.info(f"Cycle detection ({method_key}): max H₁ persistence = {max_pers:.4f}, threshold = {threshold:.4f}")

    # Extract significant H₁ features
    h1_features = ph.h_features(1, min_persistence=threshold)
    h1_features = np.array(h1_features) if len(h1_features) > 0 else np.empty((0, 2))
    finite_mask = np.isfinite(h1_features[:, 1]) if len(h1_features) > 0 else []
    if len(h1_features) > 0:
        h1_features = h1_features[finite_mask]

    n_loops = len(h1_features)
    logger.info(f"  {n_loops} persistent H₁ features above threshold")

    # For each loop, find representative trajectories
    loop_profiles = []
    if n_loops > 0 and embeddings.shape[0] > 0:
        # Use centroid of embedding space as approximate loop location
        # (proper cocycle representatives would require more infrastructure)
        centroid = embeddings.mean(axis=0)

        for i, (birth, death) in enumerate(h1_features):
            # Approximate: find trajectories at the scale of this feature
            # Use points near the midpoint of the embedding
            midpoint = centroid  # Simplified; could use cocycle info
            rep_indices = _find_representative_trajectories(embeddings, midpoint, k=n_representatives)

            profile = _characterise_cycles(trajectories, rep_indices)
            profile["birth"] = float(birth)
            profile["death"] = float(death)
            profile["persistence"] = float(death - birth)
            loop_profiles.append(profile)

            logger.info(
                f"  Loop {i}: persistence={death - birth:.4f}, "
                f"mean_cycle_len={profile['mean_cycle_length']:.1f}, "
                f"n_cycles={profile['n_cycles_detected']}"
            )

    return {
        "n_persistent_loops": n_loops,
        "loop_profiles": loop_profiles,
        "h1_summary": {k: v for k, v in h1_summary.items() if k != "features"},
        "method": method_key,
        "min_persistence_ratio": min_persistence_ratio,
    }
