"""
Phase 6 orchestrator: career-phase regime switching analysis.

Steps:
    1. Load Phase 1–5 artefacts (trajectories, scaler, PCA, GMM).
    2. Build overlapping windows from trajectories.
    3. Embed windows via saved Scaler + PCA transforms.
    4. Assign windows to regimes via saved GMM.
    5. Build regime sequences and transition matrix.
    6. Compute PH on phase embeddings + phase-order shuffle nulls.
    7. Escape path archetype analysis.

Usage:
    python -m trajectory_tda.scripts.run_phase6 \\
        --checkpoint-dir results/trajectory_tda_integration \\
        --phase6-dir results/trajectory_tda_phase6
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Regime labels from Phase 1–5 results (see viz/constants.py)
DISADVANTAGED_REGIMES = {2, 6}  # Inactive Low, Low-Income Churn
GOOD_REGIMES = {1, 4}  # Secure EH, Employed Mid


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _save(data: dict, path: Path, name: str) -> None:
    """Save checkpoint JSON."""
    path.mkdir(parents=True, exist_ok=True)
    fpath = path / f"{name}.json"

    def convert(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        if isinstance(obj, dict):
            return {str(k): convert(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [convert(v) for v in obj]
        return obj

    with open(fpath, "w") as f:
        json.dump(convert(data), f, indent=2)
    logger.info(f"Saved: {fpath}")


def run_phase6(args: argparse.Namespace) -> dict:
    """Execute the full Phase 6 pipeline."""
    from trajectory_tda.analysis.escape_paths import (
        cluster_escape_paths,
        compute_escape_features,
        select_escapers,
    )
    from trajectory_tda.analysis.regime_switching import (
        build_regime_sequences,
        compute_escape_probabilities,
        compute_transition_matrix,
    )
    from trajectory_tda.data.trajectory_builder import build_windows
    from trajectory_tda.embedding.ngram_embed import (
        _compute_bigrams,
        _compute_unigrams,
    )
    from trajectory_tda.topology.permutation_nulls import phase_order_shuffle_test
    from trajectory_tda.topology.trajectory_ph import compute_trajectory_ph
    from trajectory_tda.utils.model_io import load_model

    t0 = time.time()
    cp_dir = Path(args.checkpoint_dir)
    out_dir = Path(args.phase6_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict = {}

    # ─── Step 1: Load Phase 1–5 artefacts ───
    logger.info("=" * 60)
    logger.info("Phase 6 Step 1: Loading Phase 1–5 artefacts")
    logger.info("=" * 60)

    # Trajectories
    seq_path = cp_dir / "01_trajectories_sequences.json"
    with open(seq_path) as f:
        trajectories = json.load(f)
    logger.info(f"Loaded {len(trajectories)} trajectories")

    # Metadata
    meta_path = cp_dir / "01_trajectories.json"
    with open(meta_path) as f:
        meta_raw = json.load(f)
    metadata = pd.DataFrame(meta_raw["metadata"])
    logger.info(f"Loaded metadata: {len(metadata)} rows, columns={list(metadata.columns)}")

    # Models
    scaler = load_model(cp_dir / "02_scaler.joblib")
    pca = load_model(cp_dir / "02_pca.joblib")
    gmm = load_model(cp_dir / "05_gmm.joblib")
    logger.info(f"Models loaded: Scaler, PCA ({pca.n_components_} dims), GMM (k={gmm.n_components})")

    # Regime profiles from Phase 1–5 analysis
    analysis_path = cp_dir / "05_analysis.json"
    regime_profiles = {}
    if analysis_path.exists():
        with open(analysis_path) as f:
            analysis_data = json.load(f)
        regime_profiles = analysis_data.get("regimes", {}).get("profiles", {})

    # ─── Step 2: Build overlapping windows ───
    logger.info("=" * 60)
    logger.info("Phase 6 Step 2: Building overlapping windows")
    logger.info("=" * 60)

    windows = build_windows(
        trajectories,
        metadata,
        window_years=args.window_years,
        window_step=args.window_step,
    )
    results["n_windows"] = len(windows)

    # Save windows (without states to keep JSON small)
    window_meta = [{k: v for k, v in w.items() if k != "states"} for w in windows]
    _save({"windows": window_meta, "n_windows": len(windows)}, out_dir, "01_windows")

    # ─── Step 3: Embed windows using saved PCA/Scaler ───
    logger.info("=" * 60)
    logger.info("Phase 6 Step 3: Embedding windows via saved transforms")
    logger.info("=" * 60)

    # Build raw n-gram features for each window (same as ngram_embed but
    # using saved transforms instead of fitting new ones)
    n_windows = len(windows)
    raw_features = np.zeros((n_windows, 90), dtype=np.float64)  # 9 + 81

    for i, w in enumerate(windows):
        uni = _compute_unigrams(w["states"])
        bi = _compute_bigrams(w["states"])
        raw_features[i] = np.concatenate([uni, bi])

    # Apply saved transforms
    scaled = scaler.transform(raw_features)
    window_embeddings = pca.transform(scaled)

    logger.info(f"Window embeddings: {window_embeddings.shape}")
    np.save(out_dir / "02_window_embeddings.npy", window_embeddings)

    # ─── Step 4: Assign windows to regimes ───
    logger.info("=" * 60)
    logger.info("Phase 6 Step 4: Assigning windows to regimes via GMM")
    logger.info("=" * 60)

    window_regimes = gmm.predict(window_embeddings)
    regime_counts = {int(r): int((window_regimes == r).sum()) for r in range(gmm.n_components)}
    logger.info(f"Window regime distribution: {regime_counts}")
    results["window_regime_distribution"] = regime_counts

    # Save regime assignments alongside window metadata
    regime_records = []
    for i, w in enumerate(windows):
        regime_records.append(
            {
                "window_id": w["window_id"],
                "pidp": w["pidp"],
                "traj_idx": w["traj_idx"],
                "start_year": w["start_year"],
                "end_year": w["end_year"],
                "regime": int(window_regimes[i]),
            }
        )
    _save({"window_regimes": regime_records}, out_dir, "02_window_regimes")
    np.save(out_dir / "02_window_regime_labels.npy", window_regimes)

    # ─── Step 5: Regime sequences and transition matrix ───
    logger.info("=" * 60)
    logger.info("Phase 6 Step 5: Regime sequences and transitions")
    logger.info("=" * 60)

    regime_sequences = build_regime_sequences(windows, window_regimes)
    results["n_individuals_with_sequences"] = len(regime_sequences)

    transition_matrix = compute_transition_matrix(regime_sequences, n_regimes=gmm.n_components)
    results["transition_matrix"] = transition_matrix.tolist()

    # Verify row sums
    row_sums = transition_matrix.sum(axis=1)
    logger.info(f"Transition matrix row sums: {row_sums}")

    escape_probs = compute_escape_probabilities(
        regime_sequences,
        disadvantaged_regimes=DISADVANTAGED_REGIMES,
        good_regimes=GOOD_REGIMES,
        max_horizon=5,
    )
    results["escape_probabilities"] = {k: v for k, v in escape_probs.items() if k != "path_lengths"}

    _save(
        {
            "regime_sequences": {str(k): v for k, v in regime_sequences.items()},
        },
        out_dir,
        "03_regime_sequences",
    )
    _save(
        {
            "transition_matrix": transition_matrix.tolist(),
            "escape_probabilities": escape_probs,
        },
        out_dir,
        "03_regime_transitions",
    )

    # ─── Step 6: PH on phase embeddings + phase-order nulls ───
    logger.info("=" * 60)
    logger.info("Phase 6 Step 6: PH on career phase space")
    logger.info("=" * 60)

    # Filter: all windows from individuals who ever visit disadvantaged regimes
    # + stratified sample of others (cap ~50k)
    pidps_disadvantaged = set()
    for pidp, seq in regime_sequences.items():
        if any(s["regime"] in DISADVANTAGED_REGIMES for s in seq):
            pidps_disadvantaged.add(pidp)

    disadv_mask = np.array([w["pidp"] in pidps_disadvantaged for w in windows])
    other_mask = ~disadv_mask

    n_disadv = disadv_mask.sum()
    max_other = max(0, 50000 - n_disadv)
    other_indices = np.where(other_mask)[0]
    rng = np.random.RandomState(42)
    if len(other_indices) > max_other:
        sampled_other = rng.choice(other_indices, size=max_other, replace=False)
    else:
        sampled_other = other_indices

    phase_indices = np.concatenate([np.where(disadv_mask)[0], sampled_other])
    phase_indices.sort()
    phase_embeddings = window_embeddings[phase_indices]

    logger.info(
        f"Phase embeddings: {phase_embeddings.shape} " f"({n_disadv} disadvantaged + {len(sampled_other)} other)"
    )
    np.save(out_dir / "04_phase_embeddings.npy", phase_embeddings)

    # Compute PH
    phase_ph = compute_trajectory_ph(
        phase_embeddings,
        max_dim=1,
        n_landmarks=min(args.ph_landmarks, phase_embeddings.shape[0]),
        method="maxmin_vr",
        validate=False,
    )
    results["phase_ph"] = {
        "n_landmarks": phase_ph["n_landmarks"],
        "elapsed": phase_ph["elapsed_seconds"],
        "summaries": phase_ph.get("summaries", {}),
    }
    _save(results["phase_ph"], out_dir, "05_phase_ph")

    # Save raw diagrams
    if "maxmin_vr" in phase_ph:
        ph_obj = phase_ph["maxmin_vr"]
        raw_dgms = {str(d): dgm.tolist() for d, dgm in ph_obj.dgms.items()}
        _save(raw_dgms, out_dir, "05_phase_ph_diagrams")
        if hasattr(ph_obj, "landmark_indices") and ph_obj.landmark_indices is not None:
            np.save(out_dir / "05_phase_landmark_indices.npy", ph_obj.landmark_indices)

    # Phase-order shuffle null test
    logger.info("Running phase-order shuffle null test...")
    phase_windows = [windows[i] for i in phase_indices]
    null_result = phase_order_shuffle_test(
        phase_embeddings,
        phase_windows,
        n_permutations=args.n_phase_perms,
        max_dim=1,
        n_landmarks=min(args.ph_landmarks, phase_embeddings.shape[0]),
        n_jobs=-1,
        seed=42,
    )
    results["phase_null_test"] = {k: v for k, v in null_result.items() if k != "null_distributions"}
    _save(null_result, out_dir, "06_phase_nulls")

    # Save null distributions as numpy for violin plots
    for dim_key, vals in null_result["null_distributions"].items():
        np.save(
            out_dir / f"06_phase_null_{dim_key}.npy",
            np.array(vals),
        )

    # ─── Step 7: Escape path archetypes ───
    logger.info("=" * 60)
    logger.info("Phase 6 Step 7: Escape path archetypes")
    logger.info("=" * 60)

    escapers = select_escapers(
        regime_sequences,
        disadvantaged_regimes=DISADVANTAGED_REGIMES,
        good_regimes=GOOD_REGIMES,
    )

    if len(escapers) >= 10:
        escape_features = compute_escape_features(escapers, regime_profiles)
        escape_features.to_csv(out_dir / "07_escape_features.csv", index=False)
        logger.info(f"Saved escape features: {len(escape_features)} paths")

        escape_clusters = cluster_escape_paths(escape_features)
        results["escape_clusters"] = {k: v for k, v in escape_clusters.items() if k != "labels"}
        _save(escape_clusters, out_dir, "08_escape_clusters")
    else:
        logger.warning(
            f"Only {len(escapers)} escapers found — too few for clustering. " "Saving raw escape records only."
        )
        results["escape_clusters"] = {"n_escapers": len(escapers), "skipped": True}
        _save({"escapers": escapers}, out_dir, "07_escape_raw")

    # ─── Summary ───
    elapsed = time.time() - t0
    results["elapsed_total"] = elapsed
    logger.info("=" * 60)
    logger.info(f"Phase 6 complete in {elapsed:.1f}s")
    logger.info(f"  Windows: {len(windows)}, " f"Individuals: {len(regime_sequences)}, " f"Escapers: {len(escapers)}")
    logger.info("=" * 60)

    _save(results, out_dir, "results_full")
    return results


def main():
    parser = argparse.ArgumentParser(description="Phase 6: Career-phase regime switching analysis")
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="results/trajectory_tda_integration",
        help="Phase 1–5 checkpoint directory",
    )
    parser.add_argument(
        "--phase6-dir",
        type=str,
        default="results/trajectory_tda_phase6",
        help="Phase 6 output directory",
    )
    parser.add_argument(
        "--window-years",
        type=int,
        default=10,
        help="Window width in years (default: 10)",
    )
    parser.add_argument(
        "--window-step",
        type=int,
        default=5,
        help="Step between windows in years (default: 5)",
    )
    parser.add_argument(
        "--ph-landmarks",
        type=int,
        default=3000,
        help="Landmarks for phase PH (default: 3000)",
    )
    parser.add_argument(
        "--n-phase-perms",
        type=int,
        default=200,
        help="Permutations for phase-order null (default: 200)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    run_phase6(args)


if __name__ == "__main__":
    main()
