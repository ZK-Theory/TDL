"""
Priority 2 analyses: GMM bootstrap, H₀–GMM overlap, age-stratified
escape rates, and UMAP robustness re-run.

Loads Phase 1–6 artefacts and runs all Priority 2 items from the
Missing Elements Action Plan.

Usage:
    python -m trajectory_tda.scripts.run_priority2 \\
        --checkpoint-dir results/trajectory_tda_integration \\
        --phase6-dir results/trajectory_tda_phase6 \\
        --output-dir results/trajectory_tda_priority2
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

DISADVANTAGED_REGIMES = {2, 6}
GOOD_REGIMES = {1, 4}


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


def run_gmm_bootstrap(args: argparse.Namespace, out_dir: Path) -> dict:
    """P2-7: GMM Bootstrap Stability."""
    from trajectory_tda.analysis.gmm_bootstrap import gmm_bootstrap_stability
    from trajectory_tda.utils.model_io import load_model

    logger.info("=" * 60)
    logger.info("P2-7: GMM Bootstrap Stability")
    logger.info("=" * 60)

    cp_dir = Path(args.checkpoint_dir)

    # Load embeddings and GMM
    embeddings = np.load(cp_dir / "embeddings.npy")
    gmm = load_model(cp_dir / "05_gmm.joblib")
    full_labels = gmm.predict(embeddings)

    result = gmm_bootstrap_stability(
        embeddings=embeddings,
        full_labels=full_labels,
        k=gmm.n_components,
        n_bootstrap=args.n_bootstrap,
        random_state=42,
    )

    _save(result, out_dir, "p2_7_gmm_bootstrap")
    np.save(
        out_dir / "p2_7_ari_values.npy",
        np.array(result["ari_values"]),
    )

    return result


def run_h0_gmm_overlap(args: argparse.Namespace, out_dir: Path) -> dict:
    """P2-8: H₀ Component–GMM Regime Overlap."""
    from trajectory_tda.analysis.h0_gmm_overlap import compute_h0_gmm_overlap
    from trajectory_tda.utils.model_io import load_model

    logger.info("=" * 60)
    logger.info("P2-8: H₀ Component–GMM Regime Overlap")
    logger.info("=" * 60)

    cp_dir = Path(args.checkpoint_dir)

    embeddings = np.load(cp_dir / "embeddings.npy")
    gmm = load_model(cp_dir / "05_gmm.joblib")
    gmm_labels = gmm.predict(embeddings)

    # Load PH landmark indices
    lm_path = cp_dir / "03_ph_landmark_indices.npy"
    if not lm_path.exists():
        # Try phase 6 path
        lm_path = Path(args.phase6_dir) / "05_phase_landmark_indices.npy"
    if not lm_path.exists():
        # Recompute landmarks
        from trajectory_tda.topology.trajectory_ph import maxmin_landmarks

        logger.info("Landmark indices not found — recomputing with 5000 landmarks")
        lm_indices, _ = maxmin_landmarks(embeddings, n_landmarks=5000, seed=42)
    else:
        lm_indices = np.load(lm_path)

    result = compute_h0_gmm_overlap(
        embeddings=embeddings,
        gmm_labels=gmm_labels,
        landmark_indices=lm_indices,
        n_components=gmm.n_components,
    )

    # Remove non-serializable arrays for JSON, save separately
    h0_labels = result.pop("h0_labels")
    contingency = result.pop("contingency")

    np.save(out_dir / "p2_8_h0_labels.npy", h0_labels)
    np.save(out_dir / "p2_8_contingency.npy", contingency)
    result["contingency_table"] = contingency.tolist()

    _save(result, out_dir, "p2_8_h0_gmm_overlap")

    return result


def run_age_stratified(args: argparse.Namespace, out_dir: Path) -> dict:
    """P2-5: Age-Stratified Persistence/Escape Rates."""
    from trajectory_tda.analysis.age_stratified import (
        attach_age_to_windows,
        compute_age_stratified_escape_rates,
        escape_logistic_regression,
    )
    from trajectory_tda.data.covariate_extractor import extract_covariates
    from trajectory_tda.data.trajectory_builder import build_windows
    from trajectory_tda.utils.model_io import load_model

    logger.info("=" * 60)
    logger.info("P2-5: Age-Stratified Persistence/Escape Rates")
    logger.info("=" * 60)

    cp_dir = Path(args.checkpoint_dir)

    # Load trajectories and metadata
    with open(cp_dir / "01_trajectories_sequences.json") as f:
        trajectories = json.load(f)
    with open(cp_dir / "01_trajectories.json") as f:
        meta_raw = json.load(f)
    metadata = pd.DataFrame(meta_raw["metadata"])

    # Load models
    scaler = load_model(cp_dir / "02_scaler.joblib")
    pca = load_model(cp_dir / "02_pca.joblib")
    gmm = load_model(cp_dir / "05_gmm.joblib")

    # Extract covariates for birth_year and sex
    logger.info("Extracting covariates...")
    pidps = metadata["pidp"].values
    covs = extract_covariates(data_dir=args.data_dir, pidps=pidps)

    # Merge birth_year, sex, and parental NS-SEC into metadata
    if "birth_year" not in metadata.columns:
        cov_cols = ["pidp", "birth_year"]
        if "sex" in covs.columns:
            cov_cols.append("sex")
        if "parental_nssec3" in covs.columns:
            cov_cols.append("parental_nssec3")
        cov_dedup = covs[cov_cols].drop_duplicates(subset="pidp", keep="first")
        metadata = metadata.merge(cov_dedup, on="pidp", how="left")
        if "parental_nssec3" in metadata.columns:
            metadata.rename(columns={"parental_nssec3": "parental_nssec"}, inplace=True)

    # Add birth_cohort for logistic regression
    if "birth_year" in metadata.columns and "birth_cohort" not in metadata.columns:
        metadata["birth_cohort"] = pd.cut(
            metadata["birth_year"],
            bins=[0, 1950, 1960, 1970, 1980, 2010],
            labels=["pre-1950", "1950s", "1960s", "1970s", "post-1980"],
        )

    # Build windows
    windows = build_windows(trajectories, metadata, window_years=10, window_step=5)

    # Attach age
    windows = attach_age_to_windows(windows, metadata)

    # Embed and assign regimes (same as Phase 6)
    from trajectory_tda.embedding.ngram_embed import (
        _compute_bigrams,
        _compute_unigrams,
    )

    n_windows = len(windows)
    raw_features = np.zeros((n_windows, 90), dtype=np.float64)
    for i, w in enumerate(windows):
        uni = _compute_unigrams(w["states"])
        bi = _compute_bigrams(w["states"])
        raw_features[i] = np.concatenate([uni, bi])

    scaled = scaler.transform(raw_features)
    window_embeddings = pca.transform(scaled)
    window_regimes = gmm.predict(window_embeddings)

    # Age-stratified escape rates
    escape_results = compute_age_stratified_escape_rates(
        windows=windows,
        window_regimes=window_regimes,
        disadvantaged_regimes=DISADVANTAGED_REGIMES,
        good_regimes=GOOD_REGIMES,
    )

    # Logistic regression
    logit_results = escape_logistic_regression(
        windows=windows,
        window_regimes=window_regimes,
        metadata=metadata,
        disadvantaged_regimes=DISADVANTAGED_REGIMES,
        good_regimes=GOOD_REGIMES,
    )

    result = {
        "escape_rates": escape_results,
        "logistic_regression": logit_results,
    }

    _save(result, out_dir, "p2_5_age_stratified")

    return result


def _load_or_compute_umap(args, cp_dir: Path):
    """Load existing UMAP embeddings or compute from scratch."""
    from trajectory_tda.data.trajectory_builder import build_trajectories_from_raw
    from trajectory_tda.embedding.ngram_embed import ngram_embed

    umap_path = cp_dir / "embeddings_umap16.npy"
    if umap_path.exists():
        logger.info("Loading existing UMAP-16D embeddings...")
        umap_embeddings = np.load(umap_path)
        with open(cp_dir / "01_trajectories_sequences.json") as f:
            trajectories = json.load(f)
    else:
        logger.info("Computing UMAP-16D embedding from scratch...")
        trajectories, _ = build_trajectories_from_raw(
            data_dir=args.data_dir, min_years=10, max_gap=2
        )
        umap_embeddings, _ = ngram_embed(
            trajectories, include_bigrams=True, pca_dim=None, umap_dim=16
        )
        np.save(umap_path, umap_embeddings)

    return umap_embeddings, trajectories


def _run_umap_null_models(umap_embeddings, trajectories):
    """Run order-shuffle and Markov-1 null models on UMAP embedding.

    Null surrogates are re-embedded with UMAP-16D (same as observed) to ensure
    the test compares like with like.  Each permutation fits a fresh UMAP —
    expensive but methodologically correct.
    """
    from trajectory_tda.topology.permutation_nulls import permutation_test_trajectories

    n_lm = min(5000, umap_embeddings.shape[0])
    umap_kwargs = {"include_bigrams": True, "pca_dim": None, "umap_dim": 16}

    logger.info("Running order-shuffle null on UMAP-16D (n=100)...")
    null_order = permutation_test_trajectories(
        umap_embeddings,
        trajectories,
        null_type="order_shuffle",
        n_permutations=100,
        max_dim=1,
        n_landmarks=n_lm,
        n_jobs=-1,
        seed=42,
        embed_kwargs=umap_kwargs,
    )

    logger.info("Running Markov-1 null on UMAP-16D (n=100)...")
    null_markov = permutation_test_trajectories(
        umap_embeddings,
        trajectories,
        null_type="markov",
        markov_order=1,
        n_permutations=100,
        max_dim=1,
        n_landmarks=n_lm,
        n_jobs=-1,
        seed=42,
        embed_kwargs=umap_kwargs,
    )
    return null_order, null_markov


def _build_umap_escape_sequences(umap_labels, metadata):
    """Build per-person regime sequences from UMAP labels."""
    meta_indexed = metadata.set_index("pidp")
    umap_full_seqs = {}
    for i, label in enumerate(umap_labels):
        if i >= len(metadata):
            break
        pidp = metadata.iloc[i]["pidp"]
        if pidp in meta_indexed.index:
            row = meta_indexed.loc[pidp]
            s = row["start_year"]
            e = row["end_year"]
            start_yr = int(s) if np.isscalar(s) else int(s.iloc[0])
            end_yr = int(e) if np.isscalar(e) else int(e.iloc[0])
            umap_full_seqs[pidp] = [
                {
                    "regime": int(label),
                    "start_year": start_yr,
                    "end_year": end_yr,
                }
            ]
    return umap_full_seqs


def run_umap_robustness(args: argparse.Namespace, out_dir: Path) -> dict:
    """P2-6: UMAP Robustness — re-run key results under UMAP-16D.

    Runs: (a) GMM k=7 comparison with PCA regimes,
          (b) order-shuffle null (n=100),
          (c) Markov-1 null (n=100).
    Escape-rate replication is deferred because it requires windowed
    (Phase 6) analysis on the UMAP embedding, not trajectory-level labels.
    """
    from sklearn.metrics import adjusted_rand_score

    from trajectory_tda.analysis.regime_discovery import fit_gmm

    logger.info("=" * 60)
    logger.info("P2-6: UMAP Robustness Re-run")
    logger.info("=" * 60)

    cp_dir = Path(args.checkpoint_dir)

    with open(cp_dir / "05_analysis.json") as f:
        pca_labels = np.array(json.load(f)["gmm_labels"])

    umap_embeddings, trajectories = _load_or_compute_umap(args, cp_dir)

    # Fit GMM k=7 on UMAP
    logger.info("Fitting GMM k=7 on UMAP-16D...")
    _, umap_labels, gmm_info = fit_gmm(
        umap_embeddings, k_range=range(7, 8), random_state=42
    )

    ari_pca_umap = float(adjusted_rand_score(pca_labels, umap_labels))
    logger.info(f"ARI(PCA regimes, UMAP regimes) = {ari_pca_umap:.4f}")

    # Null models
    null_order, null_markov = _run_umap_null_models(umap_embeddings, trajectories)

    def strip(d):
        return {k: v for k, v in d.items() if k != "null_distributions"}

    result = {
        "ari_pca_umap": ari_pca_umap,
        "umap_k": int(gmm_info["k_optimal"]),
        "gmm_info": gmm_info,
        "order_shuffle_null": strip(null_order),
        "markov_1_null": strip(null_markov),
    }

    # Save null distributions
    for key, null_res in [("order_shuffle", null_order), ("markov_1", null_markov)]:
        if "null_distributions" in null_res:
            for dim_key, vals in null_res["null_distributions"].items():
                np.save(out_dir / f"p2_6_umap_{key}_{dim_key}.npy", np.array(vals))

    _save(result, out_dir, "p2_6_umap_robustness")
    return result


def run_priority2(args: argparse.Namespace) -> dict:
    """Run all Priority 2 analyses."""
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    results = {}

    # P2-7: GMM Bootstrap (lowest dependency, fastest)
    if not args.skip_bootstrap:
        results["gmm_bootstrap"] = run_gmm_bootstrap(args, out_dir)

    # P2-8: H₀–GMM Overlap
    if not args.skip_h0_overlap:
        results["h0_gmm_overlap"] = run_h0_gmm_overlap(args, out_dir)

    # P2-5: Age-Stratified Escape Rates
    if not args.skip_age_stratified:
        results["age_stratified"] = run_age_stratified(args, out_dir)

    # P2-6: UMAP Robustness
    if not args.skip_umap:
        results["umap_robustness"] = run_umap_robustness(args, out_dir)

    elapsed = time.time() - t0
    results["elapsed_total"] = elapsed
    logger.info(f"Priority 2 analyses complete in {elapsed:.1f}s")
    _save(results, out_dir, "priority2_results")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Priority 2: GMM bootstrap, H₀–GMM overlap, "
        "age-stratified escape, UMAP robustness"
    )
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
        "--output-dir",
        type=str,
        default="results/trajectory_tda_priority2",
        help="Priority 2 output directory",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="trajectory_tda/data",
        help="Raw BHPS/USoc data directory",
    )
    parser.add_argument(
        "--n-bootstrap",
        type=int,
        default=200,
        help="Number of GMM bootstrap iterations (default: 200)",
    )
    parser.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help="Skip GMM bootstrap stability",
    )
    parser.add_argument(
        "--skip-h0-overlap",
        action="store_true",
        help="Skip H₀–GMM overlap analysis",
    )
    parser.add_argument(
        "--skip-age-stratified",
        action="store_true",
        help="Skip age-stratified escape rates",
    )
    parser.add_argument(
        "--skip-umap",
        action="store_true",
        help="Skip UMAP robustness re-run",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    run_priority2(args)


if __name__ == "__main__":
    main()
