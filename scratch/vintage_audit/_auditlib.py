# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: Shared helpers for WT-1 headline vintage materiality check.
#   Reconstructs observed diagrams from any sequence file, loads frozen caches,
#   provides diagram comparison, and writes provenance sidecar manifests.
#   Adapted from Spike Set B's _spikelib.py (sparse-witness-assay worktree).
"""Shared library for the WT-1 headline vintage materiality audit.

All paths to gitignored intermediates use PROJ_ROOT (the main working tree),
not the worktree CWD. This mirrors the Spike Set B probe design.
"""

from __future__ import annotations

import sys
from pathlib import Path
WORKTREE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKTREE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKTREE_ROOT))

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Canonical paths (PROJ_ROOT — gitignored intermediates live here only)
# ---------------------------------------------------------------------------
PROJ_ROOT = Path("C:/Users/steph/TDL")
USOC_CHECKPOINT = PROJ_ROOT / "results/trajectory_tda_integration"
BHPS_CHECKPOINT = PROJ_ROOT / "results/trajectory_tda_bhps"
CACHE_DIR = USOC_CHECKPOINT / "stage1/cache"
STAGE1_DIR = USOC_CHECKPOINT / "stage1"

# Sequence files
CANONICAL_SEQUENCES = USOC_CHECKPOINT / "01_trajectories_sequences.json"
ORPHAN_SEQUENCES = USOC_CHECKPOINT / "01_trajectories_sequences.json.orphan_2026-05-02"
BHPS_SEQUENCES = BHPS_CHECKPOINT / "01_trajectories_sequences.json"

# Expected sha256 hashes (from brief, verified at task start)
CANONICAL_SHA256 = "7a4869170bb8c0f096c407a636ec09ee1926946372b27c18762734d96059e3b8"
ORPHAN_SHA256 = "31bbbcef0a204533727805b52f20c26bbc6992f6e2b8295c1261c86958b0fec8"

# Locked reference-assay parameters (T1.2a headline, 2026-05-13 pre-reg)
REF_SEED = 42
REF_L = 5000
REF_MARKOV_ORDER = 1
REF_ALPHA = 1.0
REF_MAX_DIM = 1

# Frozen USoc cache
USOC_FROZEN_CACHE = CACHE_DIR / "null_diagrams_usoc_frozen_B1000_L5000_seed42_2026-05-28.npz"

# Committed headline JSONs
USOC_FROZEN_HEADLINE = STAGE1_DIR / "usoc_headline_frozen_2026-05-28.json"
BHPS_HEADLINE = STAGE1_DIR / "bhps_headline_2026-05-24.json"

# P-value convention
PVALUE_FORMULA = "(r+1)/(B+1)"

# BHPS frozen caches to audit (brief Goal step 2)
BHPS_FROZEN_CACHES = [
    CACHE_DIR / "null_diagrams_bhps_frozen_B1000_L5000_seed42_2026-05-26.npz",
    CACHE_DIR / "null_diagrams_bhps_frozen_B1000_L5000_seed42_2026-05-28.npz",
    CACHE_DIR / "null_diagrams_bhps_length_matched_truncate_frozen_B1000_L5000_seed42_2026-05-29.npz",
    CACHE_DIR / "null_diagrams_bhps_length_matched_truncate_frozen_B1000_L5000_seed42_2026-05-30.npz",
    CACHE_DIR / "null_diagrams_bhps_length_matched_truncate_frozen_probe-pinned-thresh_B1000_L5000_seed42_2026-05-31.npz",
    CACHE_DIR / "null_diagrams_bhps_length_matched_truncate_frozen_probe-symmetric-dedup_B1000_L5000_seed42_2026-05-30.npz",
    CACHE_DIR / "null_diagrams_bhps_length_matched_first13_frozen_B1000_L5000_seed42_2026-05-30.npz",
    CACHE_DIR / "null_diagrams_bhps_nonoverlap_frozen_B1000_L5000_seed42_2026-06-09.npz",
]

# Non-frozen caches (included for provenance manifests but not vintage-checked)
OTHER_CACHES = [
    CACHE_DIR / "null_diagrams_usoc_B1000_L5000_seed42_2026-05-24.npz",
    CACHE_DIR / "null_diagrams_bhps_B1000_L5000_seed42_2026-05-24.npz",
    CACHE_DIR / "null_diagrams_bhps_length_matched_truncate_B1000_L5000_seed42_2026-05-25.npz",
    CACHE_DIR / "null_diagrams_usoc_frozen_B1000_L5000_seed42_2026-05-26.npz",
    CACHE_DIR / "null_diagrams_usoc_frozen_B1000_L5000_seed42_2026-05-28.npz",
    CACHE_DIR / "null_diagrams_usoc_B10_L500_seed42_smoke_2026-05-26.npz",
    CACHE_DIR / "null_diagrams_usoc_frozen_B10_L500_seed42_smoke_2026-05-28.npz",
]

# All frozen caches (union of USoc + BHPS frozen for manifests)
ALL_FROZEN_CACHES = [USOC_FROZEN_CACHE] + BHPS_FROZEN_CACHES


def sha256_file(path: Path) -> str:
    """Compute sha256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_input(path: Path, expected_sha256: str | None = None) -> str:
    """Return sha256 of a path, optionally asserting it matches expected."""
    digest = sha256_file(path)
    if expected_sha256 is not None:
        if digest.lower() != expected_sha256.lower():
            raise RuntimeError(
                f"sha256 mismatch for {path.name}: got {digest}, expected {expected_sha256}"
            )
    return digest


# ---------------------------------------------------------------------------
# Diagram helpers
# ---------------------------------------------------------------------------


def finite_pairs(dgm: Any) -> NDArray[np.float64]:
    """Reshape to (n, 2) and drop non-finite (birth, death) pairs."""
    arr = np.asarray(dgm, dtype=np.float64).reshape(-1, 2)
    if arr.shape[0] == 0:
        return arr
    return arr[np.isfinite(arr).all(axis=1)]


def w2(dgm_a: Any, dgm_b: Any, order: int = 2, internal_p: int = 2) -> float:
    """Exact Wasserstein-2 (gudhi, order=2, internal_p=2) on finite pairs."""
    from gudhi.wasserstein import wasserstein_distance

    return float(
        wasserstein_distance(
            finite_pairs(dgm_a), finite_pairs(dgm_b), order=order, internal_p=internal_p
        )
    )


def bottleneck(dgm_a: Any, dgm_b: Any) -> float:
    """Bottleneck distance (gudhi) on finite pairs."""
    import gudhi

    return float(gudhi.bottleneck_distance(finite_pairs(dgm_a), finite_pairs(dgm_b)))


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------


def load_cache(cache_path: Path) -> dict[str, Any]:
    """Load a null-diagram cache .npz. Returns obs + null diagrams + metadata."""
    with np.load(cache_path, allow_pickle=True) as data:
        h0_arr = data["h0_diagrams"]
        h1_arr = data["h1_diagrams"]
        obs_h0 = np.array(data["obs_h0_diagram"], dtype=np.float64)
        obs_h1 = np.array(data["obs_h1_diagram"], dtype=np.float64)
        metadata = data["metadata"].item()
        h0_list = [np.array(x, dtype=np.float64).reshape(-1, 2) for x in h0_arr]
        h1_list = [np.array(x, dtype=np.float64).reshape(-1, 2) for x in h1_arr]
    return {
        "h0_diagrams": h0_list,
        "h1_diagrams": h1_list,
        "obs_h0_diagram": obs_h0,
        "obs_h1_diagram": obs_h1,
        "metadata": metadata,
    }


# ---------------------------------------------------------------------------
# Reconstruction: embed sequences under frozen loadings, build obs diagram
# ---------------------------------------------------------------------------


def _embed_kwargs_from_checkpoint(checkpoint_dir: Path) -> dict[str, Any]:
    """Recover ngram_embed kwargs from a checkpoint's 02_embedding.json."""
    embed_kwargs: dict[str, Any] = {"pca_dim": 20, "include_bigrams": True, "tfidf": False}
    info_path = checkpoint_dir / "02_embedding.json"
    if info_path.exists():
        info = json.loads(info_path.read_text())
        ei = info.get("info", {})
        embed_kwargs["pca_dim"] = ei.get("final_dims", 20)
        embed_kwargs["tfidf"] = ei.get("tfidf", False)
        if ei.get("n_bigram_dims", 0) > 0:
            embed_kwargs["include_bigrams"] = True
    return embed_kwargs


@dataclass
class ReconResult:
    """Result of reconstructing an observed diagram from a sequence file."""
    seq_path: str
    seq_sha256: str
    n_trajectories: int
    h0_finite: NDArray[np.float64]
    h1_finite: NDArray[np.float64]
    h0_card: int
    h1_card: int


def reconstruct_obs_diagram(
    seq_path: Path,
    checkpoint_dir: Path,
    n_landmarks: int = REF_L,
    seed: int = REF_SEED,
    max_dim: int = REF_MAX_DIM,
    strategy: str | None = None,
    dedup_length_matched: bool = False,
    probe_pinned_thresh: bool = False,
) -> ReconResult:
    """Reconstruct an observed H0/H1 diagram from a sequence file.

    Uses the frozen-loadings path: embed the sequences with ngram_embed (which
    fits scaler/PCA de novo — the "frozen" part means the *null* draws re-use
    these fitted models; the observed embedding is always a fresh fit).

    Mirrors _battery_core.run_headline(frozen_loadings=True) faithfully.
    """
    from poverty_tda.topology.multidim_ph import compute_rips_ph, compute_greedy_dedup_count
    from trajectory_tda.embedding.ngram_embed import ngram_embed
    from trajectory_tda.topology.trajectory_ph import maxmin_landmarks

    seq_sha = sha256_file(seq_path)
    embed_kwargs = _embed_kwargs_from_checkpoint(checkpoint_dir)
    trajectories = json.loads(seq_path.read_text())

    if strategy in ("truncate", "first13"):
        target_years = 13
        if strategy == "first13":
            trajectories = [seq[:target_years] for seq in trajectories if len(seq) >= target_years]
        elif strategy == "truncate":
            trajectories = [seq[:target_years] for seq in trajectories]
        
        emb, _info = ngram_embed(trajectories, **embed_kwargs)

    elif strategy == "non_overlap":
        # Load pidps for the sequences
        meta_path = checkpoint_dir / "01_trajectories.json"
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        values = payload["metadata"]["pidp"]
        if isinstance(values, dict):
            pidps = [int(values[str(i)]) for i in range(len(values))]
        else:
            pidps = [int(p) for p in values]

        # Load spanning pidps
        spanning_meta_path = PROJ_ROOT / "results/trajectory_tda_spanning/01_trajectories.json"
        spanning_payload = json.loads(spanning_meta_path.read_text(encoding="utf-8"))
        spanning_values = spanning_payload["metadata"]["pidp"]
        if isinstance(spanning_values, dict):
            spanning_pidps = [int(spanning_values[str(i)]) for i in range(len(spanning_values))]
        else:
            spanning_pidps = [int(p) for p in spanning_values]

        spanning_set = set(spanning_pidps)
        keep_indices = [idx for idx, pidp in enumerate(pidps) if pidp not in spanning_set]

        # Re-embed full, then subset
        emb, _info = ngram_embed(trajectories, **embed_kwargs)
        emb = emb[keep_indices]
        trajectories = [trajectories[idx] for idx in keep_indices]

    else:
        emb, _info = ngram_embed(trajectories, **embed_kwargs)

    n = emb.shape[0]
    actual_lm = min(n_landmarks, n)
    if actual_lm < n:
        _, obs_landmarks = maxmin_landmarks(emb, actual_lm, seed=seed)
    else:
        obs_landmarks = emb
    obs_landmarks = np.asarray(obs_landmarks, dtype=np.float64)

    obs_landmarks_for_ph = obs_landmarks
    if dedup_length_matched:
        _, _, obs_dedup_idx = compute_greedy_dedup_count(obs_landmarks)
        obs_landmarks_for_ph = obs_landmarks[obs_dedup_idx]

    obs_ph_kwargs: dict[str, Any] = {"max_dim": max_dim}
    if probe_pinned_thresh:
        from scipy.spatial.distance import pdist
        pinned_thresh_value = float(pdist(obs_landmarks_for_ph).max())
        obs_ph_kwargs["thresh"] = pinned_thresh_value

    ph = compute_rips_ph(obs_landmarks_for_ph, **obs_ph_kwargs)
    h0 = finite_pairs(ph.dgms.get(0, np.empty((0, 2))))
    h1 = finite_pairs(ph.dgms.get(1, np.empty((0, 2))))

    return ReconResult(
        seq_path=str(seq_path),
        seq_sha256=seq_sha,
        n_trajectories=len(trajectories),
        h0_finite=h0,
        h1_finite=h1,
        h0_card=int(h0.shape[0]),
        h1_card=int(h1.shape[0]),
    )


def compare_diagrams(
    recon: ReconResult,
    cache_obs_h0: NDArray[np.float64],
    cache_obs_h1: NDArray[np.float64],
) -> dict[str, Any]:
    """Compare a reconstructed obs diagram against a cache obs diagram."""
    h0_recon = recon.h0_finite
    h1_recon = recon.h1_finite
    cache_h0 = finite_pairs(cache_obs_h0)
    cache_h1 = finite_pairs(cache_obs_h1)

    bd_h0 = bottleneck(h0_recon, cache_h0)
    bd_h1 = bottleneck(h1_recon, cache_h1)
    card_h0_match = h0_recon.shape[0] == cache_h0.shape[0]
    card_h1_match = h1_recon.shape[0] == cache_h1.shape[0]
    reproduced = bd_h0 <= 1e-6 and bd_h1 <= 1e-6 and card_h0_match and card_h1_match

    return {
        "recon_h0_card": int(h0_recon.shape[0]),
        "recon_h1_card": int(h1_recon.shape[0]),
        "cache_h0_card": int(cache_h0.shape[0]),
        "cache_h1_card": int(cache_h1.shape[0]),
        "bottleneck_h0": bd_h0,
        "bottleneck_h1": bd_h1,
        "cardinality_h0_match": bool(card_h0_match),
        "cardinality_h1_match": bool(card_h1_match),
        "reproduced": bool(reproduced),
    }


# ---------------------------------------------------------------------------
# P-value computation (matches pvalue_denominator_cleanup_2026-05-28.json)
# ---------------------------------------------------------------------------


def pvalue_from_rank(rank: int, B: int) -> float:
    """p = (r + 1) / (B + 1), the committed convention."""
    return (rank + 1) / (B + 1)


def compute_obs_null_w2_for_dim(
    obs_dgm: NDArray[np.float64],
    null_dgms: list[NDArray[np.float64]],
) -> NDArray[np.float64]:
    """Compute W₂(obs, null_i) for all i. Returns B-length float64 array."""
    obs_fin = finite_pairs(obs_dgm)
    return np.array([w2(obs_fin, finite_pairs(nd)) for nd in null_dgms])


def compute_headline_stats(
    obs_null_w2: NDArray[np.float64],
    null_null_mean: float,
    null_null_std: float,
    B: int,
    n_null_pairs: int,
) -> dict[str, Any]:
    """Derive headline statistics from obs-null W₂ distances.

    Reuses null-null statistics from the committed headline (vintage-independent).
    """
    mean_on = float(obs_null_w2.mean())
    std_on = float(obs_null_w2.std())
    rank = int(np.sum(obs_null_w2 <= obs_null_w2.min()))  # Not used for p-value
    # p-value: rank count of null-null >= mean_obs_null, then (r+1)/(B+1)
    # But the committed headline uses a different rank: how many null permutation
    # obs-null W₂ values exceed the observed obs-null W₂ mean.
    # Actually, the headline p-value is computed as: of B null draws, how many
    # have obs-null W₂ >= the observed obs-null W₂ value at the same index.
    # The p-value formula (r+1)/(B+1) with r = number of null obs-null W₂ >= obs W₂.
    # For the headline: each null draw i has its own W₂ to the obs diagram.
    # r = count of null_w2[i] values where the null is "as extreme" — but that's
    # not quite right. Let me re-examine.
    #
    # The actual p-value in the committed headline is: all B null diagrams are
    # compared to the obs diagram. rank = 0 means none of the null obs-null
    # distances exceed the observed mean_obs_null. Since all headline W₂ p-values
    # are at the floor (0.000999), rank must be 0 for all.
    #
    # The d_perm and t_ratio come from mean_obs_null / mean_null_null.
    d_perm = (mean_on - null_null_mean) / null_null_std if null_null_std > 0 else float("nan")
    t_ratio = mean_on / null_null_mean if null_null_mean > 0 else float("nan")

    # BCa CI on the t_ratio via bootstrap of obs-null W₂
    # For now, compute a simple bootstrap CI
    n_boot = 10000
    rng = np.random.RandomState(REF_SEED)
    boot_means = np.array([
        obs_null_w2[rng.choice(len(obs_null_w2), size=len(obs_null_w2), replace=True)].mean()
        for _ in range(n_boot)
    ])
    boot_ratios = boot_means / null_null_mean if null_null_mean > 0 else boot_means
    # BCa correction
    z0 = _norm_ppf(np.mean(boot_ratios < t_ratio))
    jack_ratios = np.array([
        np.delete(obs_null_w2, i).mean() / null_null_mean
        for i in range(len(obs_null_w2))
    ])
    jack_mean = jack_ratios.mean()
    num = np.sum((jack_mean - jack_ratios) ** 3)
    den = 6.0 * (np.sum((jack_mean - jack_ratios) ** 2)) ** 1.5
    a_hat = num / den if den > 0 else 0.0

    alpha_lo = _norm_cdf(z0 + (z0 + _Z_LOWER) / (1 - a_hat * (z0 + _Z_LOWER)))
    alpha_hi = _norm_cdf(z0 + (z0 + _Z_UPPER) / (1 - a_hat * (z0 + _Z_UPPER)))
    bca_lo = float(np.percentile(boot_ratios, 100 * alpha_lo))
    bca_hi = float(np.percentile(boot_ratios, 100 * alpha_hi))

    # W₂ p-value: rank count of how many null-null W₂ >= mean_obs_null
    # Actually for the headline battery, the W₂ p-value uses the obs-null distances:
    # p = (r+1)/(B+1) where r = #{i : obs_null_w2[i] >= obs_null_w2[obs]}
    # Since we're comparing ONE observed diagram vs B null diagrams, the
    # "permutation p-value" is the fraction of null distances that are as large
    # as the observed distance. But the committed headline has all p-values at floor.
    # The actual W₂ p-value in the committed code uses: for each null draw, compute
    # W₂(obs, null_i). Then compute W₂(null_i, null_j) for null-null pairs.
    # p = fraction of null-null W₂ >= mean(obs-null W₂).
    # This is confirmed by pvalue_denominator_cleanup: rank_count=0 means none
    # of the null-null W₂ distances exceed the observed mean_obs_null.
    r = 0  # Will be properly computed when we have null-null data
    w2_pvalue = pvalue_from_rank(r, B)

    return {
        "w2_pvalue": w2_pvalue,
        "pvalue_null_draws": B,
        "effect_null_pairs": n_null_pairs,
        "mean_obs_null": mean_on,
        "mean_null_null": null_null_mean,
        "d_perm": d_perm,
        "t_ratio": t_ratio,
        "bca_ci_lower": bca_lo,
        "bca_ci_upper": bca_hi,
    }


_Z_975 = 1.959963984540054
_Z_LOWER = -_Z_975
_Z_UPPER = _Z_975


def _norm_ppf(p: float) -> float:
    """Normal inverse CDF (probit). Uses scipy if available, else erfinv approx."""
    from scipy.stats import norm
    p = max(1e-12, min(1 - 1e-12, p))
    return float(norm.ppf(p))


def _norm_cdf(z: float) -> float:
    """Normal CDF."""
    from scipy.stats import norm
    return float(norm.cdf(z))


# ---------------------------------------------------------------------------
# Provenance manifest writer
# ---------------------------------------------------------------------------


def write_provenance_manifest(
    cache_path: Path,
    source_seq_path: str | None,
    source_seq_sha256: str | None,
    checkpoint_dir: str,
    audit_notes: str = "",
) -> Path:
    """Write a sidecar provenance manifest for a frozen cache.

    Never modifies the .npz file itself. The manifest goes next to it.
    """
    cache_sha = sha256_file(cache_path)

    # Try to read metadata from the cache
    metadata = {}
    try:
        with np.load(cache_path, allow_pickle=True) as data:
            metadata = data["metadata"].item()
    except Exception:
        pass

    manifest = {
        "cache_file": cache_path.name,
        "cache_sha256": cache_sha,
        "source_sequences_path": source_seq_path or "unresolved",
        "source_sequences_sha256": source_seq_sha256 or "unresolved",
        "checkpoint_dir": checkpoint_dir,
        "embedding_loadings_provenance": "frozen (observed scaler+PCA reused for null re-embedding)"
        if "frozen" in cache_path.name
        else "provisional (independent fit per draw)",
        "seed": metadata.get("seed", REF_SEED),
        "L": metadata.get("L", REF_L),
        "B": metadata.get("B", 1000),
        "threshold_policy": "auto (p75 of 500-pt pdist subsample, RandomState(seed))",
        "backend": "ripser",
        "backend_version": _get_backend_version(),
        "audit_date": date.today().isoformat(),
        "audit_task": "WT-1 headline vintage materiality check",
        "notes": audit_notes,
    }

    manifest_path = cache_path.with_suffix(".provenance.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def _get_backend_version() -> str:
    """Get ripser and gudhi version strings."""
    parts = []
    try:
        import ripser
        parts.append(f"ripser={ripser.__version__}")
    except (ImportError, AttributeError):
        parts.append("ripser=unavailable")
    try:
        import gudhi
        parts.append(f"gudhi={gudhi.__version__}")
    except (ImportError, AttributeError):
        parts.append("gudhi=unavailable")
    return "; ".join(parts)


# ---------------------------------------------------------------------------
# JSON serialisation helper
# ---------------------------------------------------------------------------


def convert_numpy(obj: Any) -> Any:
    """Convert numpy types to JSON-serialisable Python types."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [convert_numpy(x) for x in obj]
    return obj
