"""
P1.1: Optimal Matching (OM) baseline comparison.

Computes dynamic Hamming distance OM on all 27,280 trajectories,
clusters with Ward's linkage, selects k via silhouette, and compares
to GMM regimes via Adjusted Rand Index (ARI).

Saves:
    results/trajectory_tda_robustness/om_baseline/
        01_distance_matrix.npy         – (N, N) pairwise DHD distances
        02_ward_linkage.npy            – Ward linkage matrix
        03_silhouette_scores.json      – silhouette by k (2–12)
        04_om_labels.npy               – OM cluster labels at best k
        05_om_baseline_results.json    – ARI, profiles, comparison summary

Usage:
    python -m trajectory_tda.scripts.run_om_baseline \
        --checkpoint-dir results/trajectory_tda_integration \
        --output-dir results/trajectory_tda_robustness/om_baseline
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.metrics import adjusted_rand_score, silhouette_score

logger = logging.getLogger(__name__)

# Canonical state ordering
STATES = ["EL", "EM", "EH", "UL", "UM", "UH", "IL", "IM", "IH"]
STATE_TO_IDX = {s: i for i, s in enumerate(STATES)}
N_STATES = len(STATES)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _save_json(data: dict, path: Path) -> None:
    """Save dict as JSON with numpy-safe conversion."""

    def convert(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, dict):
            return {str(k): convert(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [convert(v) for v in obj]
        return obj

    with open(path, "w") as f:
        json.dump(convert(data), f, indent=2)
    logger.info(f"Saved: {path}")


def dynamic_hamming_distance(traj_a: list[str], traj_b: list[str]) -> float:
    """Compute Dynamic Hamming Distance (Lesnard 2010) between two trajectories.

    For equal-length sequences this is the normalised Hamming distance.
    For unequal-length sequences, we align from the start and compute
    over the overlapping window, then add a penalty of 1.0 per extra
    time-step in the longer sequence.

    Returns a value in [0, max_len] (unnormalised).
    """
    min_len = min(len(traj_a), len(traj_b))
    max_len = max(len(traj_a), len(traj_b))

    if max_len == 0:
        return 0.0

    mismatches = sum(1 for t in range(min_len) if traj_a[t] != traj_b[t])
    # Penalty for unequal length: unaligned positions count as mismatches
    mismatches += max_len - min_len

    return float(mismatches)


def compute_pairwise_dhd(
    trajectories: list[list[str]],
    n_jobs: int = -1,
    batch_size: int = 500,
) -> np.ndarray:
    """Compute pairwise Dynamic Hamming Distance matrix.

    Uses vectorised computation with batching for memory efficiency.
    The full (N, N) matrix is symmetric so we compute only the upper
    triangle via pdist-style indexing.

    Args:
        trajectories: List of state sequences.
        n_jobs: Ignored (kept for interface compat). Computation is vectorised.
        batch_size: Not used directly but kept for future chunked I/O.

    Returns:
        Condensed distance vector (for scipy), shape (N*(N-1)/2,).
    """
    n = len(trajectories)
    logger.info(f"Computing pairwise DHD for {n} trajectories...")

    # Pre-convert trajectories to integer arrays for speed
    max_len = max(len(t) for t in trajectories)
    # Pad shorter trajectories with -1 (sentinel for "missing")
    int_trajs = np.full((n, max_len), -1, dtype=np.int16)
    lengths = np.zeros(n, dtype=np.int32)

    for i, traj in enumerate(trajectories):
        length = len(traj)
        lengths[i] = length
        for t in range(length):
            idx = STATE_TO_IDX.get(traj[t], -1)
            int_trajs[i, t] = idx

    # Compute condensed distance vector
    # For N=27280, condensed vector has ~372M entries → ~2.8GB float32
    # We'll compute in chunks to manage memory
    n_pairs = n * (n - 1) // 2
    logger.info(f"  Total pairs: {n_pairs:,}")

    condensed = np.zeros(n_pairs, dtype=np.float32)

    idx = 0
    report_every = max(1, n // 20)
    for i in range(n):
        if i % report_every == 0:
            logger.info(f"  Row {i}/{n} ({100 * i / n:.0f}%)")

        # Vectorised: compare trajectory i against all j > i
        n_remaining = n - i - 1
        if n_remaining == 0:
            break

        # Mismatch matrix: compare row i with rows i+1..n-1
        others = int_trajs[i + 1 :]  # (n_remaining, max_len)
        row_i = int_trajs[i]  # (max_len,)

        # Element-wise comparison (broadcasting)
        mismatches = (others != row_i).astype(np.float32)  # (n_remaining, max_len)

        # Positions where BOTH are valid (not sentinel -1)
        valid_i = row_i >= 0  # (max_len,)
        valid_others = others >= 0  # (n_remaining, max_len)
        both_valid = valid_i & valid_others  # (n_remaining, max_len)

        # Positions where one is valid and other is not → automatic mismatch
        one_valid = (valid_i & ~valid_others) | (~valid_i & valid_others)

        # Mismatches only count where both are valid
        aligned_mismatches = (mismatches * both_valid).sum(axis=1)
        # Add length-mismatch penalty
        length_penalty = one_valid.sum(axis=1).astype(np.float32)

        dists = aligned_mismatches + length_penalty
        condensed[idx : idx + n_remaining] = dists
        idx += n_remaining

    logger.info(f"  DHD computation complete. Mean distance: {condensed.mean():.2f}")
    return condensed


def compute_om_clusters(
    condensed_dists: np.ndarray,
    k_range: range = range(2, 13),
    sample_size: int | None = 10000,
    seed: int = 42,
) -> dict:
    """Compute Ward's hierarchical clustering and select k via silhouette.

    Args:
        condensed_dists: Condensed distance vector from pdist.
        k_range: Range of k values to evaluate.
        sample_size: If set, subsample for silhouette (full matrix is too large).
        seed: Random seed.

    Returns:
        Dict with linkage, silhouette scores, best k, labels.
    """
    logger.info("Computing Ward's linkage...")
    Z = linkage(condensed_dists, method="ward")
    logger.info(f"  Linkage complete. Shape: {Z.shape}")

    # Silhouette evaluation
    dist_matrix = squareform(condensed_dists)
    n = dist_matrix.shape[0]

    # Subsample for silhouette if n is large
    rng = np.random.RandomState(seed)
    if sample_size is not None and n > sample_size:
        sample_idx = rng.choice(n, size=sample_size, replace=False)
        sample_idx.sort()
        dist_sub = dist_matrix[np.ix_(sample_idx, sample_idx)]
    else:
        sample_idx = np.arange(n)
        dist_sub = dist_matrix

    silhouette_scores = {}
    best_k = k_range.start
    best_score = -1.0

    for k in k_range:
        labels_full = fcluster(Z, t=k, criterion="maxclust")
        labels_sub = labels_full[sample_idx]

        # Need at least 2 clusters in sample
        if len(np.unique(labels_sub)) < 2:
            silhouette_scores[k] = -1.0
            continue

        score = silhouette_score(dist_sub, labels_sub, metric="precomputed")
        silhouette_scores[k] = float(score)
        logger.info(f"  k={k}: silhouette={score:.4f}")

        if score > best_score:
            best_score = score
            best_k = k

    labels = fcluster(Z, t=best_k, criterion="maxclust")
    # Convert to 0-indexed
    labels = labels - 1

    return {
        "linkage": Z,
        "silhouette_scores": silhouette_scores,
        "best_k": best_k,
        "best_silhouette": best_score,
        "labels": labels,
    }


def compute_regime_profiles(
    trajectories: list[list[str]],
    labels: np.ndarray,
    k: int,
) -> dict:
    """Compute state-frequency profiles for each cluster."""
    profiles = {}
    for cluster_id in range(k):
        mask = labels == cluster_id
        cluster_trajs = [trajectories[i] for i in range(len(trajectories)) if mask[i]]
        n_in_cluster = len(cluster_trajs)

        # Compute mean state frequencies
        state_freqs = np.zeros(N_STATES)
        for traj in cluster_trajs:
            counts = Counter(traj)
            total = len(traj)
            for state, count in counts.items():
                idx = STATE_TO_IDX.get(state)
                if idx is not None:
                    state_freqs[idx] += count / total

        state_freqs /= max(n_in_cluster, 1)

        profiles[cluster_id] = {
            "n": n_in_cluster,
            "fraction": n_in_cluster / len(trajectories),
            "state_frequencies": {STATES[i]: float(state_freqs[i]) for i in range(N_STATES)},
            "dominant_state": STATES[int(np.argmax(state_freqs))],
        }

    return profiles


def compare_with_gmm(
    om_labels: np.ndarray,
    gmm_labels: np.ndarray,
    om_profiles: dict,
    trajectories: list[list[str]],
    gmm_k: int,
) -> dict:
    """Compare OM clustering with GMM regimes via ARI and profile correlation.

    Computes GMM state-frequency profiles from labels + trajectories directly,
    since the stored GMM profiles use aggregated rates (employment_rate etc.)
    rather than per-state frequencies.
    """
    ari = adjusted_rand_score(gmm_labels, om_labels)
    logger.info(f"ARI (GMM vs OM): {ari:.4f}")

    # Build GMM state-frequency profiles from labels + raw trajectories
    gmm_profiles_freq = compute_regime_profiles(trajectories, gmm_labels, gmm_k)

    # Build state-frequency matrices
    om_k = len(om_profiles)

    om_freq_matrix = np.zeros((om_k, N_STATES))
    for cid, prof in om_profiles.items():
        for si, state in enumerate(STATES):
            om_freq_matrix[cid][si] = prof["state_frequencies"].get(state, 0)

    gmm_freq_matrix = np.zeros((gmm_k, N_STATES))
    for cid, prof in gmm_profiles_freq.items():
        if cid < gmm_k:
            for si, state in enumerate(STATES):
                gmm_freq_matrix[cid][si] = prof["state_frequencies"].get(state, 0)

    # Cross-correlation matrix
    from scipy.stats import pearsonr

    corr_matrix = np.zeros((om_k, gmm_k))
    for i in range(om_k):
        for j in range(gmm_k):
            if np.std(om_freq_matrix[i]) > 0 and np.std(gmm_freq_matrix[j]) > 0:
                r, _ = pearsonr(om_freq_matrix[i], gmm_freq_matrix[j])
                corr_matrix[i, j] = r
            else:
                corr_matrix[i, j] = 0.0

    # Best match for each OM cluster
    best_matches = {}
    for i in range(om_k):
        best_j = int(np.argmax(corr_matrix[i]))
        best_matches[i] = {
            "gmm_regime": best_j,
            "correlation": float(corr_matrix[i, best_j]),
        }

    return {
        "ari": float(ari),
        "correlation_matrix": corr_matrix.tolist(),
        "best_matches": best_matches,
        "om_k": om_k,
        "gmm_k": gmm_k,
        "gmm_profiles_freq": gmm_profiles_freq,
    }


def run_om_baseline(args: argparse.Namespace) -> dict:
    """Execute the OM baseline comparison pipeline."""
    t0 = time.time()
    cp_dir = Path(args.checkpoint_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ─── Load data ───
    logger.info("=" * 60)
    logger.info("OM Baseline: Loading data")
    logger.info("=" * 60)

    with open(cp_dir / "01_trajectories_sequences.json") as f:
        trajectories = json.load(f)
    logger.info(f"Loaded {len(trajectories)} trajectories")

    with open(cp_dir / "05_analysis.json") as f:
        analysis = json.load(f)
    gmm_labels = np.array(analysis["gmm_labels"])
    gmm_k = analysis["regimes"]["k_optimal"]
    logger.info(f"GMM: k={gmm_k}, {len(gmm_labels)} labels")

    # ─── Step 1: Pairwise DHD distances ───
    dist_path = out_dir / "01_distance_matrix.npy"
    if dist_path.exists() and not args.force:
        logger.info(f"Loading cached distance matrix from {dist_path}")
        condensed = np.load(dist_path)
    else:
        logger.info("=" * 60)
        logger.info("OM Baseline Step 1: Computing DHD distance matrix")
        logger.info("=" * 60)
        condensed = compute_pairwise_dhd(trajectories)
        np.save(dist_path, condensed)
        logger.info(f"Saved distance matrix: {dist_path} ({condensed.nbytes / 1e9:.2f} GB)")

    # ─── Step 2: Ward's linkage ───
    linkage_path = out_dir / "02_ward_linkage.npy"
    if linkage_path.exists() and not args.force:
        logger.info(f"Loading cached linkage from {linkage_path}")
        Z = np.load(linkage_path)
        # Still need to compute silhouette
        sil_path = out_dir / "03_silhouette_scores.json"
        if sil_path.exists():
            with open(sil_path) as f:
                sil_data = json.load(f)
            cluster_result = {
                "linkage": Z,
                "silhouette_scores": {int(k): v for k, v in sil_data["silhouette_scores"].items()},
                "best_k": sil_data["best_k"],
                "best_silhouette": sil_data["best_silhouette"],
                "labels": np.load(out_dir / "04_om_labels.npy"),
            }
        else:
            cluster_result = compute_om_clusters(condensed, sample_size=args.silhouette_sample)
    else:
        logger.info("=" * 60)
        logger.info("OM Baseline Step 2: Ward's linkage + silhouette selection")
        logger.info("=" * 60)
        cluster_result = compute_om_clusters(condensed, sample_size=args.silhouette_sample)
        np.save(linkage_path, cluster_result["linkage"])
        logger.info(f"Saved linkage: {linkage_path}")

    # Save silhouette scores
    sil_data = {
        "silhouette_scores": cluster_result["silhouette_scores"],
        "best_k": cluster_result["best_k"],
        "best_silhouette": cluster_result["best_silhouette"],
    }
    _save_json(sil_data, out_dir / "03_silhouette_scores.json")

    # Save OM labels
    np.save(out_dir / "04_om_labels.npy", cluster_result["labels"])
    logger.info(f"Best k: {cluster_result['best_k']} (silhouette={cluster_result['best_silhouette']:.4f})")

    # ─── Step 3: Regime profiles ───
    logger.info("=" * 60)
    logger.info("OM Baseline Step 3: Computing OM cluster profiles")
    logger.info("=" * 60)
    om_profiles = compute_regime_profiles(trajectories, cluster_result["labels"], cluster_result["best_k"])

    # ─── Step 4: Compare with GMM ───
    logger.info("=" * 60)
    logger.info("OM Baseline Step 4: Comparing with GMM regimes")
    logger.info("=" * 60)
    comparison = compare_with_gmm(
        cluster_result["labels"],
        gmm_labels,
        om_profiles,
        trajectories,
        cluster_result["best_k"],
    )

    # Also compute ARI at k=7 (matching GMM) for direct comparison
    labels_k7 = fcluster(cluster_result["linkage"], t=gmm_k, criterion="maxclust") - 1
    ari_k7 = adjusted_rand_score(gmm_labels, labels_k7)
    logger.info(f"ARI at k={gmm_k} (matching GMM): {ari_k7:.4f}")

    om_profiles_k7 = compute_regime_profiles(trajectories, labels_k7, gmm_k)
    comparison_k7 = compare_with_gmm(labels_k7, gmm_labels, om_profiles_k7, trajectories, gmm_k)

    # ─── Save results ───
    results = {
        "om_best_k": cluster_result["best_k"],
        "om_best_silhouette": cluster_result["best_silhouette"],
        "silhouette_scores": cluster_result["silhouette_scores"],
        "om_profiles": om_profiles,
        "comparison_best_k": comparison,
        "comparison_at_gmm_k": {
            "k": gmm_k,
            "ari": float(ari_k7),
            "profiles": om_profiles_k7,
            "details": comparison_k7,
        },
        "n_trajectories": len(trajectories),
        "gmm_k": gmm_k,
        "elapsed_seconds": time.time() - t0,
    }
    _save_json(results, out_dir / "05_om_baseline_results.json")

    # ─── Summary ───
    logger.info("=" * 60)
    logger.info("OM Baseline Complete")
    logger.info(f"  Best k (silhouette): {cluster_result['best_k']}")
    logger.info(f"  ARI (best k vs GMM): {comparison['ari']:.4f}")
    logger.info(f"  ARI (k={gmm_k} vs GMM): {ari_k7:.4f}")
    logger.info(f"  Elapsed: {time.time() - t0:.1f}s")
    logger.info("=" * 60)

    return results


def main():
    parser = argparse.ArgumentParser(description="P1.1: OM/DHD baseline comparison with GMM regimes")
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="results/trajectory_tda_integration",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/trajectory_tda_robustness/om_baseline",
    )
    parser.add_argument(
        "--silhouette-sample",
        type=int,
        default=10000,
        help="Subsample size for silhouette evaluation (default: 10000)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute even if cached results exist",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()
    setup_logging(args.verbose)
    run_om_baseline(args)


if __name__ == "__main__":
    main()
