# Research context: TDA-Research/03-Papers/P01-A-JRSSA/_project.md
# Purpose: Intrinsic-dimensionality estimate (TwoNN + MLE) for the USoc and
#   BHPS 20-D PCA-projected trajectory embeddings consumed by the Stage-1
#   matched-L W2 + landscape L2 battery. Diagnoses whether the PCA-20 cut at
#   49% explained variance is information-lossy in the sense of Damrich,
#   Berens, Kobak (arXiv:2311.03087v3, NeurIPS 2024) and Hiraoka et al. (2024)
#   — i.e. whether VR-PH on the embedding is operating in the high-D regime
#   where the methods are known to fail to detect correct topology.
"""Intrinsic dimensionality of the trajectory embeddings.

Two estimators (TwoNN, MLE) on two passes (full embedding, L=5000 maxmin
landmarks) for each of the USoc and BHPS 20-D PCA embeddings. The L=5000
landmark pass uses the same maxmin selection as the headline VR-PH pipeline
(seed=42), so the reported intrinsic d is the d the persistent homology
filtration actually sees.

Usage::

    uv run --env-file .env python trajectory_tda/scripts/estimate_intrinsic_dim.py \\
        --usoc-dir C:/Users/steph/TDL/results/trajectory_tda_integration \\
        --bhps-dir C:/Users/steph/TDL/results/trajectory_tda_bhps \\
        --landmark-L 5000 --seed 42

Defaults to the canonical PROJ_ROOT input paths so the script works in any
worktree out of the box (per T1.2a F1 finding).
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import time
from datetime import date
from pathlib import Path

import numpy as np
import skdim
from numpy.typing import NDArray
from sklearn.neighbors import NearestNeighbors

from trajectory_tda.topology.trajectory_ph import maxmin_landmarks

logger = logging.getLogger(__name__)


PROJ_ROOT = Path("C:/Users/steph/TDL")
DEFAULT_USOC_DIR = PROJ_ROOT / "results" / "trajectory_tda_integration"
DEFAULT_BHPS_DIR = PROJ_ROOT / "results" / "trajectory_tda_bhps"
DEFAULT_LANDMARK_L = 5000
DEFAULT_SEED = 42


def worktree_root() -> Path:
    """Return the current worktree root (cwd)."""
    return Path.cwd()


def git_head_sha() -> str:
    """Return the current branch HEAD SHA, or 'unknown' if git fails."""
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.STDOUT)
        return out.strip()
    except Exception:
        return "unknown"


def levina_bickel_mle(X: NDArray[np.float64], k: int = 10) -> float:
    """Levina-Bickel (2004) MLE intrinsic-dimension estimator.

    Standard formula averaged over points:
        d_hat_k(x_i) = [ (k-1)^{-1} sum_{j=1..k-1} log( T_k(x_i) / T_j(x_i) ) ]^{-1}
    where T_j(x_i) is the distance to x_i's j-th nearest neighbour.
    Average the per-point estimates.

    Inlined here because `skdim.id.MLE` triggers a Python 3.13 incompatibility
    in skdim 0.3.4 (`FrameLocalsProxy.pop()` is not supported).

    Args:
        X: (N, D) point cloud.
        k: Number of nearest neighbours (default 10, the Levina-Bickel
            recommended range is k in [10, 20]).

    Returns:
        Scalar intrinsic dimensionality estimate.
    """
    nbrs = NearestNeighbors(n_neighbors=k + 1).fit(X)
    dists, _ = nbrs.kneighbors(X)
    # dists[:, 0] is self (=0); use 1..k+1 → k true neighbours
    T = dists[:, 1 : k + 1]  # (N, k)
    # Per-point MLE: 1 / ( (1/(k-1)) * sum_{j=1..k-1} log(T_k / T_j) )
    log_ratios = np.log(T[:, -1:] / T[:, :-1])  # (N, k-1)
    per_point = 1.0 / (log_ratios.mean(axis=1) + 1e-12)
    return float(per_point.mean())


def estimate_id(X: NDArray[np.float64], label: str) -> dict:
    """Estimate intrinsic dimensionality with TwoNN and Levina-Bickel MLE.

    Args:
        X: (N, D) point cloud.
        label: Human-readable label for log messages.

    Returns:
        Dict with d_twonn, d_mle, n_points, walltime per estimator.
    """
    n, d = X.shape
    logger.info("[%s] estimating intrinsic d on %d points in %dD", label, n, d)

    t0 = time.perf_counter()
    twonn = skdim.id.TwoNN()
    twonn.fit(X)
    d_twonn = float(twonn.dimension_)
    t_twonn = time.perf_counter() - t0
    logger.info("[%s] TwoNN d=%.4f (wall=%.2fs)", label, d_twonn, t_twonn)

    t0 = time.perf_counter()
    d_mle = levina_bickel_mle(X, k=10)
    t_mle = time.perf_counter() - t0
    logger.info("[%s] MLE   d=%.4f (wall=%.2fs, k=10)", label, d_mle, t_mle)

    return {
        "d_twonn": d_twonn,
        "d_mle": d_mle,
        "mle_k": 10,
        "n_points": n,
        "walltime_twonn_seconds": t_twonn,
        "walltime_mle_seconds": t_mle,
    }


def diagnostic_verdict(d_twonn: float, d_ambient: int = 20) -> str:
    """Apply the Task Prompt's decision rule to a TwoNN estimate.

    Args:
        d_twonn: TwoNN intrinsic dimensionality estimate (full embedding).
        d_ambient: Ambient PCA dimensionality (default 20).

    Returns:
        One of: 'OVER-DIMENSIONAL', 'WELL-ALIGNED', 'POTENTIALLY UNDER-DIMENSIONAL'.
    """
    if d_twonn <= 10:
        return "OVER-DIMENSIONAL"
    if d_twonn <= 18:
        return "WELL-ALIGNED"
    return "POTENTIALLY UNDER-DIMENSIONAL"


def run_for_dataset(
    name: str,
    checkpoint_dir: Path,
    landmark_L: int,
    seed: int,
    out_path: Path,
    script_commit: str,
) -> dict:
    """Run TwoNN + MLE on full embedding and L=landmark_L maxmin landmarks."""
    emb_path = checkpoint_dir / "embeddings.npy"
    info_path = checkpoint_dir / "02_embedding.json"
    if not emb_path.exists():
        raise FileNotFoundError(f"Embeddings not found: {emb_path}")
    if not info_path.exists():
        raise FileNotFoundError(f"Embedding metadata not found: {info_path}")

    with open(info_path) as f:
        info = json.load(f)
    info_inner = info.get("info", {})

    embeddings = np.load(emb_path).astype(np.float64)
    n, d = embeddings.shape
    explained_variance = float(info_inner.get("explained_variance", float("nan")))
    n_trajectories = int(info_inner.get("n_trajectories", n))
    raw_dims = int(info_inner.get("raw_dims", -1))

    # Deduplicate: TwoNN/MLE break on zero pairwise distances. The embeddings
    # contain a non-trivial fraction of identical rows (different career
    # trajectories that map to the same bigram-count vector and therefore the
    # same PCA-projected point). The intrinsic-d question is well-posed only
    # over the unique support; duplication rate is itself reported.
    unique_embeddings = np.unique(embeddings, axis=0)
    n_unique = unique_embeddings.shape[0]
    n_duplicates = n - n_unique
    duplicate_rate = n_duplicates / n if n > 0 else 0.0

    logger.info(
        "[%s] loaded %d trajectories x %dD, EV=%.4f, raw_dims=%d, unique=%d (%.2f%% duplicates)",
        name,
        n,
        d,
        explained_variance,
        raw_dims,
        n_unique,
        100 * duplicate_rate,
    )

    # Pass A: full embedding, deduplicated to unique support
    full_result = estimate_id(unique_embeddings, f"{name}-full-unique")

    # Pass B: L maxmin landmarks (matching headline pipeline). Maxmin selection
    # naturally avoids duplicates because zero-distance candidates rank last;
    # confirm and dedupe defensively before estimation.
    _, landmarks = maxmin_landmarks(embeddings, landmark_L, seed=seed)
    landmark_unique = np.unique(landmarks, axis=0)
    n_landmark_unique = landmark_unique.shape[0]
    landmark_result = estimate_id(landmark_unique, f"{name}-L{landmark_L}-unique")
    landmark_result["maxmin_seed"] = seed
    landmark_result["n_unique_landmarks"] = n_landmark_unique
    landmark_result["n_duplicate_landmarks"] = landmark_L - n_landmark_unique

    # Headline verdict from full-embedding TwoNN
    verdict = diagnostic_verdict(full_result["d_twonn"], d_ambient=d)
    twonn_mle_gap = abs(full_result["d_twonn"] - full_result["d_mle"])

    payload = {
        "dataset": name,
        "n_trajectories": n_trajectories,
        "D_ambient": d,
        "raw_dims": raw_dims,
        "explained_variance_at_D": explained_variance,
        "n_unique_embeddings": n_unique,
        "duplicate_rate": duplicate_rate,
        "full_embedding": full_result,
        "landmark_L5000": landmark_result,
        "diagnostic_verdict": verdict,
        "twonn_mle_abs_gap_full": twonn_mle_gap,
        "scikit_dimension_version": skdim.__version__,
        "random_seed": seed,
        "script_commit_at_runtime": script_commit,
        "date": date.today().isoformat(),
        "citations": [
            "Damrich, Berens, Kobak (2024, arXiv:2311.03087v3, NeurIPS) — VR-PH fails in high ambient D",
            "Hiraoka et al. (2024) — PCA preprocessing critique for VR-PH",
            "Facco, Rodriguez, Cestelli Guidi, Laio (2017) — TwoNN estimator",
            "Levina, Bickel (2004) — MLE estimator",
        ],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    logger.info("[%s] wrote %s", name, out_path)
    logger.info(
        "[%s] verdict=%s (TwoNN-full=%.3f, MLE-full=%.3f, |gap|=%.3f)",
        name,
        verdict,
        full_result["d_twonn"],
        full_result["d_mle"],
        twonn_mle_gap,
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate intrinsic dimensionality of the USoc + BHPS embeddings.")
    parser.add_argument(
        "--usoc-dir",
        type=Path,
        default=DEFAULT_USOC_DIR,
        help="USoc checkpoint dir (default: canonical PROJ_ROOT path).",
    )
    parser.add_argument(
        "--bhps-dir",
        type=Path,
        default=DEFAULT_BHPS_DIR,
        help="BHPS checkpoint dir (default: canonical PROJ_ROOT path).",
    )
    parser.add_argument(
        "--landmark-L",
        type=int,
        default=DEFAULT_LANDMARK_L,
        help="Number of maxmin landmarks for the landmark pass (default 5000).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Random seed for maxmin landmark selection (default 42).",
    )
    parser.add_argument(
        "--usoc-out",
        type=Path,
        default=None,
        help="Output JSON for USoc (default: WORKTREE/results/trajectory_tda_integration/stage1/intrinsic_dim_<date>.json).",
    )
    parser.add_argument(
        "--bhps-out",
        type=Path,
        default=None,
        help="Output JSON for BHPS (default: WORKTREE/results/trajectory_tda_bhps/stage1/intrinsic_dim_<date>.json).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    script_commit = git_head_sha()
    today = date.today().isoformat()
    wt = worktree_root()

    usoc_out = args.usoc_out or (
        wt / "results" / "trajectory_tda_integration" / "stage1" / f"intrinsic_dim_{today}.json"
    )
    bhps_out = args.bhps_out or (wt / "results" / "trajectory_tda_bhps" / "stage1" / f"intrinsic_dim_{today}.json")

    t_total = time.perf_counter()
    usoc_payload = run_for_dataset("usoc", args.usoc_dir, args.landmark_L, args.seed, usoc_out, script_commit)
    bhps_payload = run_for_dataset("bhps", args.bhps_dir, args.landmark_L, args.seed, bhps_out, script_commit)
    total_wall = time.perf_counter() - t_total

    # Stamp total wall time on each payload retroactively
    for payload, out_path in ((usoc_payload, usoc_out), (bhps_payload, bhps_out)):
        payload["walltime_seconds_total"] = total_wall
        with open(out_path, "w") as f:
            json.dump(payload, f, indent=2)

    logger.info("Total walltime: %.2fs", total_wall)
    print(f"USoc JSON: {usoc_out}")
    print(f"BHPS JSON: {bhps_out}")
    print(
        f"USoc verdict: {usoc_payload['diagnostic_verdict']} "
        f"(TwoNN={usoc_payload['full_embedding']['d_twonn']:.3f}, "
        f"MLE={usoc_payload['full_embedding']['d_mle']:.3f})"
    )
    print(
        f"BHPS verdict: {bhps_payload['diagnostic_verdict']} "
        f"(TwoNN={bhps_payload['full_embedding']['d_twonn']:.3f}, "
        f"MLE={bhps_payload['full_embedding']['d_mle']:.3f})"
    )


if __name__ == "__main__":
    main()
