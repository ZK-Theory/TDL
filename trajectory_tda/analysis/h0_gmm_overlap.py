"""
H₀ component–GMM regime overlap analysis.

Compares two segmentations of the trajectory space:
1. H₀ connected components from VR persistent homology (single-linkage merge tree)
2. GMM regime labels from density-based clustering

Reports ARI, contingency table, and per-regime purity.

Note: In high-dimensional PCA embeddings, VR H₀ typically shows a single
dominant connected component with outlier singletons, while GMM identifies
density modes within that component. The overlap analysis quantifies this
discrepancy, which is itself an informative finding about the data geometry.
"""

from __future__ import annotations

import logging
from collections import Counter

import numpy as np
from sklearn.metrics import adjusted_rand_score

logger = logging.getLogger(__name__)


def extract_h0_components(
    ph_dgms: dict[int, np.ndarray],
    n_components: int = 7,
) -> tuple[float, list[tuple[float, float]]]:
    """Find the filtration scale where exactly n_components H₀ features are alive.

    Args:
        ph_dgms: {dim: (N, 2) birth-death array} from PHResult.dgms.
        n_components: Target number of connected components.

    Returns:
        scale: The filtration value (midpoint of the range where
               exactly n_components H₀ features are alive).
        components: List of (birth, death) pairs for the n_components
                    most persistent H₀ features.
    """
    h0 = ph_dgms.get(0, np.empty((0, 2)))
    if len(h0) == 0:
        raise ValueError("No H₀ features in persistence diagram")

    # Sort by persistence (death - birth) descending
    finite_mask = np.isfinite(h0[:, 1])
    h0_finite = h0[finite_mask]

    if len(h0_finite) < n_components:
        logger.warning(f"Only {len(h0_finite)} finite H₀ features, " f"fewer than requested {n_components} components")
        n_components = len(h0_finite)

    persistence = h0_finite[:, 1] - h0_finite[:, 0]
    order = np.argsort(-persistence)
    top_k = h0_finite[order[:n_components]]

    deaths_sorted = np.sort(h0_finite[:, 1])[::-1]
    if n_components < len(deaths_sorted):
        scale = float((deaths_sorted[n_components - 1] + deaths_sorted[n_components]) / 2)
    else:
        scale = float(deaths_sorted[-1] * 0.99)

    components = [(float(b), float(d)) for b, d in top_k]

    logger.info(
        f"H₀ components: {n_components} at scale {scale:.4f}, "
        f"persistence range [{persistence[order[n_components - 1]]:.4f}, "
        f"{persistence[order[0]]:.4f}]"
    )

    return scale, components


def assign_points_to_h0_components(
    embeddings: np.ndarray,
    landmark_indices: np.ndarray,
    n_components: int = 7,
) -> np.ndarray:
    """Assign each point to an H₀ component via the single-linkage merge tree.

    Single-linkage hierarchical clustering on landmarks exactly mirrors
    the H₀ merge tree from VR persistent homology. The dendrogram is cut
    at k = n_components. All N points are assigned to the component of
    their nearest landmark.

    Args:
        embeddings: (N, D) full point cloud.
        landmark_indices: Indices of landmarks used for PH.
        n_components: Target number of components.

    Returns:
        labels: (N,) component assignment for each point.
    """
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import pdist
    from sklearn.metrics import pairwise_distances

    landmarks = embeddings[landmark_indices]

    # Single-linkage on landmarks = exact VR H₀ merge tree
    D_condensed = pdist(landmarks)
    Z = linkage(D_condensed, method="single")
    lm_labels = fcluster(Z, t=n_components, criterion="maxclust") - 1  # 0-based

    comp_sizes = Counter(lm_labels.tolist())
    logger.info(
        f"Single-linkage k={n_components} on {len(landmarks)} landmarks: "
        f"component sizes = {sorted(comp_sizes.values(), reverse=True)}"
    )

    # Assign all points to nearest landmark's component
    D_full = pairwise_distances(embeddings, landmarks)
    nearest_lm = np.argmin(D_full, axis=1)
    point_labels = lm_labels[nearest_lm]

    return point_labels


def _compute_gmm_per_h0(
    embeddings: np.ndarray,
    gmm_labels: np.ndarray,
    h0_labels: np.ndarray,
) -> dict:
    """Compute per-component and per-regime purity metrics."""
    n_gmm = len(np.unique(gmm_labels))
    n_h0 = len(np.unique(h0_labels))

    # Contingency table
    contingency = np.zeros((n_h0, n_gmm), dtype=int)
    for h0, gmm in zip(h0_labels, gmm_labels):
        contingency[h0, gmm] += 1

    # Per-regime purity
    per_regime_purity = {}
    for r in range(n_gmm):
        mask = gmm_labels == r
        if mask.sum() == 0:
            continue
        counts = Counter(h0_labels[mask].tolist())
        dominant_count = max(counts.values())
        per_regime_purity[int(r)] = float(dominant_count / mask.sum())

    # Per-component purity
    per_component_purity = {}
    for c in range(n_h0):
        mask = h0_labels == c
        if mask.sum() == 0:
            continue
        counts = Counter(gmm_labels[mask].tolist())
        dominant_count = max(counts.values())
        per_component_purity[int(c)] = float(dominant_count / mask.sum())

    return {
        "contingency": contingency,
        "per_regime_purity": per_regime_purity,
        "per_component_purity": per_component_purity,
    }


def compute_h0_gmm_overlap(
    embeddings: np.ndarray,
    gmm_labels: np.ndarray,
    landmark_indices: np.ndarray,
    n_components: int = 7,
) -> dict:
    """Compute contingency table and ARI between H₀ components and GMM regimes.

    In high-dimensional PCA embeddings, the VR complex typically shows a
    single dominant connected component with outlier singletons, while GMM
    identifies density modes within that component. This function quantifies
    the agreement and discrepancy between the two segmentations.

    Args:
        embeddings: (N, D) point cloud.
        gmm_labels: (N,) GMM regime assignments.
        landmark_indices: Indices used for PH computation.
        n_components: Target number of H₀ components.

    Returns:
        Dict with h0_labels, contingency, ari, purity metrics, and
        structural diagnostics.
    """
    h0_labels = assign_points_to_h0_components(embeddings, landmark_indices, n_components=n_components)

    n_h0 = len(np.unique(h0_labels))
    n_gmm = len(np.unique(gmm_labels))

    metrics = _compute_gmm_per_h0(embeddings, gmm_labels, h0_labels)

    ari = float(adjusted_rand_score(h0_labels, gmm_labels))

    # Structural diagnostics
    h0_sizes = Counter(h0_labels.tolist())
    dominant_component = max(h0_sizes, key=h0_sizes.get)
    dominant_frac = h0_sizes[dominant_component] / len(h0_labels)
    n_singleton = sum(1 for s in h0_sizes.values() if s <= 1)

    result = {
        "h0_labels": h0_labels,
        "contingency": metrics["contingency"],
        "ari": ari,
        "n_h0_components": n_h0,
        "n_gmm_regimes": n_gmm,
        "per_regime_purity": metrics["per_regime_purity"],
        "per_component_purity": metrics["per_component_purity"],
        "dominant_component_fraction": dominant_frac,
        "n_singleton_components": n_singleton,
        "component_sizes": {int(k): int(v) for k, v in h0_sizes.items()},
    }

    logger.info(f"H₀–GMM overlap: ARI = {ari:.4f}, {n_h0} H₀ components × {n_gmm} GMM regimes")
    logger.info(f"  Dominant component: {dominant_frac:.1%} of points, " f"{n_singleton} singleton components")
    for r, p in metrics["per_regime_purity"].items():
        logger.info(f"  Regime {r}: purity = {p:.2%}")

    return result
