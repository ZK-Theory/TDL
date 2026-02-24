"""
N-gram embedding: convert state sequences to fixed-dimension vectors.

Each trajectory is represented as a point in R^K where K depends on
the n-gram configuration:
  - Unigrams only: 9D (frequency of each state)
  - Unigrams + bigrams: 90D (9 + 81 transition pairs)

Optional dimensionality reduction via PCA or UMAP.
Optional TF-IDF weighting to handle rare transition dominance.
"""

from __future__ import annotations

import logging
from collections import Counter

import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# Canonical state ordering (consistent across all modules)
STATES = ["EL", "EM", "EH", "UL", "UM", "UH", "IL", "IM", "IH"]

# State-to-index mapping for reproducibility
STATE_TO_IDX = {s: i for i, s in enumerate(STATES)}

# Number of states
N_STATES = len(STATES)


def _compute_unigrams(trajectory: list[str]) -> np.ndarray:
    """Compute unigram (state frequency) vector for a single trajectory.

    Returns:
        (N_STATES,) array of normalised state frequencies.
    """
    counts = Counter(trajectory)
    total = len(trajectory)
    vec = np.zeros(N_STATES, dtype=np.float64)
    for state, count in counts.items():
        idx = STATE_TO_IDX.get(state)
        if idx is not None:
            vec[idx] = count / total
    return vec


def _compute_bigrams(trajectory: list[str]) -> np.ndarray:
    """Compute bigram (transition frequency) vector for a single trajectory.

    Returns:
        (N_STATES * N_STATES,) = (81,) array of normalised transition
        frequencies.  bigram[i * N_STATES + j] = freq(state_i → state_j).
    """
    n_transitions = len(trajectory) - 1
    if n_transitions <= 0:
        return np.zeros(N_STATES * N_STATES, dtype=np.float64)

    counts = Counter((trajectory[t], trajectory[t + 1]) for t in range(n_transitions))
    vec = np.zeros(N_STATES * N_STATES, dtype=np.float64)
    for (s_from, s_to), count in counts.items():
        i = STATE_TO_IDX.get(s_from)
        j = STATE_TO_IDX.get(s_to)
        if i is not None and j is not None:
            vec[i * N_STATES + j] = count / n_transitions
    return vec


def _apply_tfidf(
    embeddings: np.ndarray,
) -> np.ndarray:
    """Apply TF-IDF-style weighting to embedding matrix.

    TF is the raw frequency (already in embeddings).
    IDF = log(N / (1 + df_j)) where df_j = number of trajectories
    with non-zero value in dimension j.

    This downweights dimensions common across all trajectories (e.g., EH)
    and upweights rare transitions (e.g., UH→IL).
    """
    n_docs = embeddings.shape[0]
    # Document frequency: how many trajectories have non-zero in each dim
    df = np.sum(embeddings > 0, axis=0).astype(np.float64)
    idf = np.log(n_docs / (1 + df))
    return embeddings * idf


def ngram_embed(
    trajectories: list[list[str]],
    include_bigrams: bool = True,
    tfidf: bool = False,
    pca_dim: int | None = 20,
    umap_dim: int | None = None,
    standardize: bool = True,
    random_state: int = 42,
) -> tuple[np.ndarray, dict]:
    """Embed state trajectories as fixed-dimension vectors.

    Args:
        trajectories: List of state sequences (each a list of state labels)
        include_bigrams: Whether to include bigram (transition) features
        tfidf: Apply TF-IDF weighting to handle rare transition dominance
        pca_dim: Reduce to this many PCA dimensions (None = no PCA)
        umap_dim: Reduce to this many UMAP dimensions (None = no UMAP).
                  If both pca_dim and umap_dim are set, UMAP takes precedence.
        standardize: Z-score standardise before reduction
        random_state: Random seed for reproducibility

    Returns:
        embeddings: (N, K) array — one row per trajectory
        info: Dict with metadata:
            - state_to_idx: mapping from state labels to indices
            - n_unigram_dims: number of unigram dimensions (9)
            - n_bigram_dims: number of bigram dimensions (81 or 0)
            - raw_dims: raw embedding dimensionality before reduction
            - final_dims: final embedding dimensionality
            - method: 'raw', 'pca', or 'umap'
            - explained_variance: (PCA only) cumulative explained variance
    """
    n = len(trajectories)
    if n == 0:
        raise ValueError("No trajectories to embed")

    logger.info(f"Embedding {n} trajectories...")

    # Compute unigrams
    unigrams = np.array([_compute_unigrams(t) for t in trajectories])
    logger.info(f"  Unigrams: {unigrams.shape}")

    if include_bigrams:
        bigrams = np.array([_compute_bigrams(t) for t in trajectories])
        embeddings = np.hstack([unigrams, bigrams])
        logger.info(f"  Bigrams: {bigrams.shape}")
    else:
        embeddings = unigrams

    raw_dims = embeddings.shape[1]
    logger.info(f"  Raw embedding: {embeddings.shape}")

    # TF-IDF weighting
    if tfidf:
        embeddings = _apply_tfidf(embeddings)
        logger.info("  Applied TF-IDF weighting")

    # Standardise (center for PCA; scale variance only if not using TF-IDF,
    # since variance scaling would exactly cancel out the TF-IDF column weights)
    if standardize:
        scaler = StandardScaler(with_std=not tfidf)
        embeddings = scaler.fit_transform(embeddings)

    # Dimensionality reduction
    method = "raw"
    explained_var = None

    if umap_dim is not None:
        try:
            import umap

            reducer = umap.UMAP(
                n_components=umap_dim,
                random_state=random_state,
                n_neighbors=min(15, n - 1),
                min_dist=0.1,
            )
            embeddings = reducer.fit_transform(embeddings)
            method = "umap"
            logger.info(f"  UMAP reduction: {embeddings.shape}")
        except ImportError:
            logger.warning("umap-learn not installed, falling back to PCA")
            if pca_dim is None:
                pca_dim = umap_dim

    if method != "umap" and pca_dim is not None:
        n_components = min(pca_dim, raw_dims, n)
        pca = PCA(n_components=n_components, random_state=random_state)
        embeddings = pca.fit_transform(embeddings)
        explained_var = float(np.sum(pca.explained_variance_ratio_))
        method = "pca"
        logger.info(f"  PCA reduction: {embeddings.shape} (explained variance: {explained_var:.3f})")

    info = {
        "state_to_idx": STATE_TO_IDX.copy(),
        "n_unigram_dims": N_STATES,
        "n_bigram_dims": N_STATES * N_STATES if include_bigrams else 0,
        "raw_dims": raw_dims,
        "final_dims": embeddings.shape[1],
        "method": method,
        "explained_variance": explained_var,
        "tfidf": tfidf,
        "n_trajectories": n,
    }

    logger.info(f"  Final: {embeddings.shape[0]} points × {embeddings.shape[1]} dims (method={method})")

    return embeddings, info
