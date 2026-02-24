"""
Regime discovery: identify mobility regimes from H₀ persistent components.

Compares PH-based regime detection with GMM clustering on the same
embedding space. Regimes are characterised by dominant state composition,
income trajectory, and employment stability.
"""

from __future__ import annotations

import logging
from collections import Counter

import numpy as np
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture

from trajectory_tda.embedding.ngram_embed import STATES

logger = logging.getLogger(__name__)


def _characterise_cluster(
    trajectories: list[list[str]],
    indices: np.ndarray,
) -> dict:
    """Compute descriptive statistics for a cluster of trajectories."""
    cluster_trajs = [trajectories[i] for i in indices]

    # State composition
    all_states = [s for t in cluster_trajs for s in t]
    state_counts = Counter(all_states)
    total = sum(state_counts.values())
    composition = {s: state_counts.get(s, 0) / total for s in STATES}

    # Dominant state
    dominant = max(composition, key=composition.get)

    # Employment breakdown
    emp_frac = sum(v for k, v in composition.items() if k.startswith("E"))
    unemp_frac = sum(v for k, v in composition.items() if k.startswith("U"))
    inactive_frac = sum(v for k, v in composition.items() if k.startswith("I"))

    # Income breakdown
    low_frac = sum(v for k, v in composition.items() if k.endswith("L"))
    mid_frac = sum(v for k, v in composition.items() if k.endswith("M"))
    high_frac = sum(v for k, v in composition.items() if k.endswith("H"))

    # Stability: fraction of time in dominant state
    stability = composition[dominant]

    # Transition rate: distinct transitions per year
    transitions_per_year = []
    for t in cluster_trajs:
        n_transitions = sum(1 for i in range(len(t) - 1) if t[i] != t[i + 1])
        transitions_per_year.append(n_transitions / (len(t) - 1) if len(t) > 1 else 0)

    return {
        "n_members": len(indices),
        "dominant_state": dominant,
        "stability": float(stability),
        "composition": composition,
        "employment_rate": float(emp_frac),
        "unemployment_rate": float(unemp_frac),
        "inactivity_rate": float(inactive_frac),
        "low_income_rate": float(low_frac),
        "mid_income_rate": float(mid_frac),
        "high_income_rate": float(high_frac),
        "mean_transition_rate": float(np.mean(transitions_per_year)),
    }


def fit_gmm(
    embeddings: np.ndarray,
    k_range: range | None = None,
    random_state: int = 42,
) -> tuple[GaussianMixture, np.ndarray, dict]:
    """Fit GMM with BIC-selected number of components.

    Args:
        embeddings: (N, K) point cloud
        k_range: Range of K values to test (default: 2–8)
        random_state: Random seed

    Returns:
        best_gmm: Fitted GMM with optimal K
        labels: (N,) cluster assignments
        info: Dict with BIC scores and optimal K
    """
    if k_range is None:
        k_range = range(2, min(9, embeddings.shape[0] // 10 + 1))

    bic_scores = {}
    best_bic = np.inf
    best_gmm = None

    for k in k_range:
        gmm = GaussianMixture(
            n_components=k,
            random_state=random_state,
            max_iter=200,
            n_init=3,
        )
        gmm.fit(embeddings)
        bic = gmm.bic(embeddings)
        bic_scores[k] = float(bic)
        if bic < best_bic:
            best_bic = bic
            best_gmm = gmm

    labels = best_gmm.predict(embeddings)
    k_opt = best_gmm.n_components

    sil = float(silhouette_score(embeddings, labels)) if k_opt > 1 else 0.0

    info = {
        "k_optimal": k_opt,
        "bic_scores": bic_scores,
        "silhouette": sil,
    }
    logger.info(f"GMM: K*={k_opt}, BIC={best_bic:.1f}, silhouette={sil:.3f}")

    return best_gmm, labels, info


def discover_regimes(
    embeddings: np.ndarray,
    trajectories: list[list[str]],
    ph_result: dict | None = None,
    k_range: range | None = None,
    random_state: int = 42,
) -> dict:
    """Discover mobility regimes using GMM + PH comparison.

    Args:
        embeddings: (N, K) trajectory embeddings
        trajectories: Raw state sequences
        ph_result: Output from compute_trajectory_ph (optional)
        k_range: Range of GMM components to test
        random_state: Random seed

    Returns:
        Dict with:
            - gmm_labels: cluster assignments
            - k_optimal: selected number of clusters
            - regime_profiles: per-cluster characterisation
            - gmm_info: BIC/silhouette details
            - ph_comparison: H₀ component count vs GMM K (if ph_result given)
    """
    logger.info(f"Regime discovery: {embeddings.shape[0]} trajectories, {embeddings.shape[1]} dims")

    # Fit GMM
    gmm, labels, gmm_info = fit_gmm(embeddings, k_range, random_state)

    # Characterise each regime
    unique_labels = np.unique(labels)
    profiles = {}
    for label in unique_labels:
        indices = np.where(labels == label)[0]
        profiles[int(label)] = _characterise_cluster(trajectories, indices)

    result = {
        "gmm_labels": labels,
        "k_optimal": gmm_info["k_optimal"],
        "regime_profiles": profiles,
        "gmm_info": gmm_info,
    }

    # Compare with PH H₀ if available
    if ph_result is not None:
        summaries = ph_result.get("summaries", {})
        ph_comparison = {}
        for method, summary in summaries.items():
            h0 = summary.get("H0", {})
            # Count persistent components (above noise threshold)
            n_finite = h0.get("n_finite", 0)
            max_pers = h0.get("max_persistence", 0)
            # Components with persistence > 10% of max
            ph_comparison[method] = {
                "n_finite_h0": n_finite,
                "max_persistence_h0": max_pers,
            }
        result["ph_comparison"] = ph_comparison
        logger.info(f"  PH comparison: {ph_comparison}")

    # Log regime summary
    for label, profile in profiles.items():
        logger.info(
            f"  Regime {label}: n={profile['n_members']}, "
            f"dominant={profile['dominant_state']}, "
            f"emp={profile['employment_rate']:.1%}, "
            f"low_inc={profile['low_income_rate']:.1%}, "
            f"stability={profile['stability']:.2f}"
        )

    return result
