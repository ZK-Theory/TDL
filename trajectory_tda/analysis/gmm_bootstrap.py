"""
GMM bootstrap stability: assess robustness of k=7 regime assignments.

Resamples trajectories with replacement, refits GMM k=7, and computes
ARI between bootstrap and full-sample regime assignments.
"""

from __future__ import annotations

import logging

import numpy as np
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import GaussianMixture

logger = logging.getLogger(__name__)


def gmm_bootstrap_stability(
    embeddings: np.ndarray,
    full_labels: np.ndarray,
    k: int = 7,
    n_bootstrap: int = 200,
    random_state: int = 42,
) -> dict:
    """Assess GMM assignment stability via bootstrap resampling.

    Args:
        embeddings: (N, D) trajectory embeddings.
        full_labels: (N,) regime labels from the full-sample GMM.
        k: Number of GMM components (fixed to match full-sample).
        n_bootstrap: Number of bootstrap iterations.
        random_state: Base random seed.

    Returns:
        Dict with:
            ari_values: list of per-bootstrap ARI scores
            ari_mean: mean ARI
            ari_std: std of ARI
            ari_ci_lower: 2.5th percentile
            ari_ci_upper: 97.5th percentile
            n_bootstrap: number of iterations
            k: number of components
    """
    n = embeddings.shape[0]
    rng = np.random.RandomState(random_state)
    ari_values: list[float] = []

    for b in range(n_bootstrap):
        # Resample with replacement
        idx = rng.choice(n, size=n, replace=True)
        X_boot = embeddings[idx]
        labels_boot_ref = full_labels[idx]

        # Fit GMM with fixed k
        gmm = GaussianMixture(
            n_components=k,
            random_state=random_state + b,
            max_iter=100,
            n_init=1,
        )
        gmm.fit(X_boot)
        labels_boot = gmm.predict(X_boot)

        # ARI between bootstrap and full-sample labels (on resampled points)
        ari = adjusted_rand_score(labels_boot_ref, labels_boot)
        ari_values.append(float(ari))

        if (b + 1) % 50 == 0:
            logger.info(
                f"  Bootstrap {b + 1}/{n_bootstrap}: " f"ARI = {ari:.3f} (running mean = {np.mean(ari_values):.3f})"
            )

    ari_arr = np.array(ari_values)
    result = {
        "ari_values": ari_values,
        "ari_mean": float(ari_arr.mean()),
        "ari_std": float(ari_arr.std()),
        "ari_ci_lower": float(np.percentile(ari_arr, 2.5)),
        "ari_ci_upper": float(np.percentile(ari_arr, 97.5)),
        "n_bootstrap": n_bootstrap,
        "k": k,
    }

    logger.info(
        f"GMM bootstrap stability: ARI = {result['ari_mean']:.3f} "
        f"± {result['ari_std']:.3f} "
        f"(95% CI: [{result['ari_ci_lower']:.3f}, {result['ari_ci_upper']:.3f}])"
    )

    return result
