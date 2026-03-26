"""Correlation analysis between embedding dimensions and outcome variables.

Addresses the reviewer concern about potential circularity: outcome variables
are derived from the same n-gram state sequences used to construct the
embedding, so high correlations between PC1/L2 and outcomes would indicate
overlapping information rather than genuinely new structure.
"""

from __future__ import annotations

import logging

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


def compute_outcome_correlation_matrix(
    embeddings: NDArray[np.float64],
    outcome_dict: dict[str, NDArray[np.float64]],
) -> dict:
    """Compute Pearson correlations between embedding features and outcomes.

    Computes correlations between:
      - PC1 (first column of embeddings)
      - L2 norm of embedding vector
      - Each outcome variable in *outcome_dict*

    Args:
        embeddings: (N, D) point cloud (e.g. PCA-20D).
        outcome_dict: Mapping of outcome name to (N,) array.

    Returns:
        Dict with:
            - names: list of variable names in order
            - matrix: (K, K) correlation matrix as nested lists
            - pc1_correlations: dict mapping outcome name to r with PC1
            - l2_correlations: dict mapping outcome name to r with L2
    """
    n = embeddings.shape[0]
    pc1 = embeddings[:, 0]
    l2 = np.linalg.norm(embeddings, axis=1)

    names = ["PC1", "L2_norm"]
    arrays = [pc1, l2]

    for name, arr in sorted(outcome_dict.items()):
        if len(arr) != n:
            logger.warning(
                "Outcome '%s' has length %d, expected %d; skipping",
                name,
                len(arr),
                n,
            )
            continue
        names.append(name)
        arrays.append(arr)

    # Build (K, N) matrix and compute correlation
    stacked = np.vstack(arrays)  # (K, N)
    corr = np.corrcoef(stacked)  # (K, K)

    # Extract PC1 and L2 correlations with outcomes
    pc1_corrs = {}
    l2_corrs = {}
    for i, name in enumerate(names):
        if name not in ("PC1", "L2_norm"):
            pc1_corrs[name] = float(corr[0, i])
            l2_corrs[name] = float(corr[1, i])

    # Flag high correlations
    for name, r in pc1_corrs.items():
        if abs(r) > 0.7:
            logger.warning("High PC1--%s correlation: r=%.3f", name, r)

    logger.info(
        "Correlation matrix: %d variables, max |PC1-outcome|=%.3f",
        len(names),
        max(abs(v) for v in pc1_corrs.values()) if pc1_corrs else 0.0,
    )

    return {
        "names": names,
        "matrix": corr.tolist(),
        "pc1_correlations": pc1_corrs,
        "l2_correlations": l2_corrs,
    }
