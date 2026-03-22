"""
Escape path archetypes: identify and cluster mobility escape trajectories.

Selects individuals who start in disadvantaged regimes and eventually reach
a favourable regime. Computes per-path features and clusters them to
discover archetypal escape routes.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


def select_escapers(
    regime_sequences: dict[int | str, list[dict]],
    disadvantaged_regimes: set[int],
    good_regimes: set[int],
) -> list[dict]:
    """Select individuals who escape from disadvantaged to good regimes.

    Args:
        regime_sequences: pidp → sorted list of {regime, start_year, end_year}.
        disadvantaged_regimes: Regime indices considered disadvantaged.
        good_regimes: Regime indices considered favourable.

    Returns:
        List of escape records with keys:
            pidp, path (list of regime ints), path_length,
            start_year, escape_year
    """
    escapers = []

    for pidp, seq in regime_sequences.items():
        if not seq or seq[0]["regime"] not in disadvantaged_regimes:
            continue

        for step, entry in enumerate(seq):
            if step == 0:
                continue
            if entry["regime"] in good_regimes:
                path = [s["regime"] for s in seq[: step + 1]]
                escapers.append(
                    {
                        "pidp": pidp,
                        "path": path,
                        "path_length": step,
                        "start_year": seq[0]["start_year"],
                        "escape_year": entry["start_year"],
                    }
                )
                break

    logger.info(f"Selected {len(escapers)} escapers")
    return escapers


def compute_escape_features(
    escapers: list[dict],
    regime_profiles: dict[int | str, dict] | None = None,
) -> pd.DataFrame:
    """Compute feature vectors for each escape path.

    Features:
        path_length: number of windows to escape.
        n_regime_changes: count of transitions where r_t != r_{t+1}.
        n_unique_regimes: distinct regimes visited.
        pct_disadvantaged: fraction of path in disadvantaged regimes.
        start_regime: initial regime label.

    Args:
        escapers: List of escape records from select_escapers().
        regime_profiles: Optional regime characterisation dicts (adds income/
                         employment features from per-regime profiles).

    Returns:
        DataFrame with one row per escaper and numeric features.
    """
    rows = []
    for esc in escapers:
        path = esc["path"]
        n_changes = sum(1 for i in range(len(path) - 1) if path[i] != path[i + 1])

        row = {
            "pidp": esc["pidp"],
            "path_length": esc["path_length"],
            "n_regime_changes": n_changes,
            "n_unique_regimes": len(set(path)),
            "start_regime": path[0],
            "end_regime": path[-1],
            "start_year": esc["start_year"],
            "escape_year": esc["escape_year"],
        }

        # Add regime-profile-derived features if available
        if regime_profiles is not None:
            # Mean employment rate across path
            emp_rates = []
            low_inc_rates = []
            for r in path[:-1]:  # exclude final (good) regime
                profile = regime_profiles.get(r) or regime_profiles.get(str(r), {})
                emp_rates.append(profile.get("employment_rate", 0))
                low_inc_rates.append(profile.get("low_income_rate", 0))
            row["mean_emp_rate_on_path"] = float(np.mean(emp_rates)) if emp_rates else 0
            row["mean_low_inc_on_path"] = float(np.mean(low_inc_rates)) if low_inc_rates else 0

        rows.append(row)

    df = pd.DataFrame(rows)
    logger.info(f"Computed features for {len(df)} escape paths")
    return df


def cluster_escape_paths(
    features_df: pd.DataFrame,
    k_range: range | None = None,
    random_state: int = 42,
) -> dict:
    """Cluster escape paths by their feature vectors.

    Args:
        features_df: DataFrame from compute_escape_features().
        k_range: Range of cluster counts to test (default: 2–5).
        random_state: Random seed.

    Returns:
        Dict with:
            labels: cluster assignment per escaper
            k_optimal: best number of clusters
            silhouette: silhouette score
            cluster_profiles: per-cluster mean features
    """
    feature_cols = [
        "path_length",
        "n_regime_changes",
        "n_unique_regimes",
    ]
    # Add optional profile-derived columns if present
    for col in ["mean_emp_rate_on_path", "mean_low_inc_on_path"]:
        if col in features_df.columns:
            feature_cols.append(col)

    X = features_df[feature_cols].values.astype(np.float64)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    if k_range is None:
        max_k = min(6, len(X) // 5 + 1)
        k_range = range(2, max(3, max_k))

    best_sil = -1
    best_k = 2
    best_labels = None

    for k in k_range:
        if k >= len(X):
            continue
        km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = km.fit_predict(X_scaled)
        n_unique = len(set(labels))
        if n_unique < 2:
            continue
        sil = float(silhouette_score(X_scaled, labels))
        if sil > best_sil:
            best_sil = sil
            best_k = k
            best_labels = labels

    if best_labels is None:
        logger.warning("Clustering failed — all points collapsed to 1 cluster")
        return {
            "labels": [0] * len(X),
            "k_optimal": 1,
            "silhouette": 0.0,
            "cluster_profiles": {0: {"n_members": len(X)}},
        }

    # Refit with best k
    km_final = KMeans(n_clusters=best_k, random_state=random_state, n_init=10)
    best_labels = km_final.fit_predict(X_scaled)
    n_unique_final = len(set(best_labels))
    if n_unique_final < 2:
        best_sil = 0.0
    else:
        best_sil = float(silhouette_score(X_scaled, best_labels))

    # Cluster profiles
    features_df = features_df.copy()
    features_df["cluster"] = best_labels
    cluster_profiles = {}
    for c in range(best_k):
        mask = features_df["cluster"] == c
        cluster_profiles[c] = {
            "n_members": int(mask.sum()),
            "mean_path_length": float(features_df.loc[mask, "path_length"].mean()),
            "mean_regime_changes": float(features_df.loc[mask, "n_regime_changes"].mean()),
            "mean_unique_regimes": float(features_df.loc[mask, "n_unique_regimes"].mean()),
        }

    logger.info(f"Escape clustering: k*={best_k}, silhouette={best_sil:.3f}")
    for c, p in cluster_profiles.items():
        logger.info(
            f"  Cluster {c}: n={p['n_members']}, "
            f"path_len={p['mean_path_length']:.1f}, "
            f"changes={p['mean_regime_changes']:.1f}"
        )

    return {
        "labels": best_labels.tolist(),
        "k_optimal": best_k,
        "silhouette": best_sil,
        "cluster_profiles": cluster_profiles,
    }
