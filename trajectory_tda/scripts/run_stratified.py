"""
Run stratified group comparisons from existing checkpoint data.

Extracts covariates (sex, cohort, parental NS-SEC) from raw BHPS/USoc,
links to trajectory embeddings via pidp, then runs group_comparison
for each stratification variable.

Each stratification can be run independently:
    python -m trajectory_tda.scripts.run_stratified --strat gender
    python -m trajectory_tda.scripts.run_stratified --strat cohort
    python -m trajectory_tda.scripts.run_stratified --strat nssec
    python -m trajectory_tda.scripts.run_stratified --strat all   # default
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

VALID_STRATS = ("gender", "cohort", "nssec", "all")


def _save_json(data: dict, path: Path) -> None:
    """Save dict to JSON with numpy conversion."""

    def convert(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, dict):
            return {str(k): convert(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [convert(v) for v in obj]
        return obj

    with open(path, "w") as f:
        json.dump(convert(data), f, indent=2)
    logger.info(f"Saved: {path}")


def _load_json(path: Path) -> dict:
    """Load JSON file."""
    with open(path) as f:
        return json.load(f)


def _load_shared_data(args: argparse.Namespace):
    """Load embeddings, trajectory metadata, and covariates.

    Returns (embeddings, pidp_array, cov_lookup, n).
    """
    from trajectory_tda.data.covariate_extractor import extract_covariates

    results_dir = Path(args.results_dir)

    logger.info("Loading checkpoint data...")
    embeddings = np.load(results_dir / "embeddings.npy")
    logger.info(f"Embeddings: {embeddings.shape}")

    with open(results_dir / "01_trajectories.json") as f:
        traj_data = json.load(f)
    metadata = traj_data["metadata"]
    pidps = metadata["pidp"]
    n = traj_data["n"]

    pidp_array = np.array([int(pidps[str(i)]) for i in range(n)])
    logger.info(f"Trajectories: {n}, unique pidps: {len(set(pidp_array))}")

    logger.info("Extracting covariates from raw BHPS/USoc data")
    covs = extract_covariates(data_dir=args.data_dir, pidps=pidp_array)
    covs_dedup = covs.drop_duplicates(subset="pidp", keep="first")
    cov_lookup = covs_dedup.set_index("pidp")

    return embeddings, pidp_array, cov_lookup, n


def _load_results(output_dir: Path) -> dict:
    """Load existing results checkpoint, or return empty dict."""
    path = output_dir / "06_stratified.json"
    if path.exists():
        results = _load_json(path)
        logger.info(f"Loaded existing results with keys: {list(results.keys())}")
        return results
    return {}


# ─────────────────────────────────────────────────────────────
# Individual stratification runners
# ─────────────────────────────────────────────────────────────


def run_gender(args: argparse.Namespace) -> dict:
    """Run gender stratification (Male vs Female)."""
    from trajectory_tda.analysis.group_comparison import compare_groups
    from trajectory_tda.topology.vectorisation import persistence_landscape

    t0 = time.time()
    embeddings, pidp_array, cov_lookup, n = _load_shared_data(args)
    output_dir = Path(args.results_dir)
    all_results = _load_results(output_dir)

    sex_labels = np.array(
        [cov_lookup.at[p, "sex"] if p in cov_lookup.index else None for p in pidp_array],
        dtype=object,
    )

    valid_sex = sex_labels != None  # noqa: E711
    sex_valid = int(valid_sex.sum())
    logger.info(f"Gender coverage: {sex_valid}/{n}")

    if sex_valid <= 100:
        logger.warning(f"Insufficient sex coverage ({sex_valid}) — skipping")
        return all_results

    logger.info("=" * 60)
    logger.info("Stratification: Gender (Male vs Female)")
    logger.info("=" * 60)

    gender_results = compare_groups(
        embeddings=embeddings[valid_sex],
        group_labels=sex_labels[valid_sex],
        n_permutations=args.n_perms,
        n_landmarks=args.landmarks,
    )
    all_results["gender"] = gender_results

    # Compute per-group landscapes for Figure 11
    gender_landscapes = {}
    for group_name in ["Male", "Female"]:
        mask = sex_labels == group_name
        if mask.sum() > 10:
            from poverty_tda.topology.multidim_ph import compute_rips_ph
            from trajectory_tda.topology.trajectory_ph import maxmin_landmarks

            g_emb = embeddings[mask]
            actual_lm = min(args.landmarks, len(g_emb))
            if actual_lm < len(g_emb):
                _, lm_pts = maxmin_landmarks(g_emb, actual_lm)
            else:
                lm_pts = g_emb
            ph = compute_rips_ph(lm_pts, max_dim=1)
            for dim in [0, 1]:
                t_vals, landscapes = persistence_landscape(ph, dim=dim, k_max=3)
                gender_landscapes[f"{group_name}_H{dim}"] = {
                    "t_values": t_vals.tolist(),
                    "landscapes": landscapes.tolist(),
                }
    all_results["gender_landscapes"] = gender_landscapes

    elapsed = time.time() - t0
    logger.info(f"Gender analysis complete in {elapsed:.1f}s")
    _save_json(all_results, output_dir / "06_stratified.json")
    return all_results


def run_cohort(args: argparse.Namespace) -> dict:
    """Run birth-cohort decade stratification."""
    from trajectory_tda.analysis.group_comparison import compare_groups

    t0 = time.time()
    embeddings, pidp_array, cov_lookup, n = _load_shared_data(args)
    output_dir = Path(args.results_dir)
    all_results = _load_results(output_dir)

    cohort_labels = np.array(
        [cov_lookup.at[p, "cohort_decade"] if p in cov_lookup.index else None for p in pidp_array],
        dtype=object,
    )

    valid_cohort = cohort_labels != None  # noqa: E711
    cohort_valid = int(valid_cohort.sum())
    logger.info(f"Cohort coverage: {cohort_valid}/{n}")

    if cohort_valid <= 100:
        logger.warning(f"Insufficient cohort coverage ({cohort_valid}) — skipping")
        return all_results

    # Filter to decades with enough data
    unique_decades = np.unique(cohort_labels[valid_cohort])
    decade_counts = {d: np.sum(cohort_labels == d) for d in unique_decades}
    logger.info(f"Cohort decades: {decade_counts}")

    keep_decades = {d for d, c in decade_counts.items() if c >= 500}
    if len(keep_decades) < 2:
        logger.warning(f"Only {len(keep_decades)} decades with >=500 trajectories")
        return all_results

    logger.info("=" * 60)
    logger.info("Stratification: Cohort decade")
    logger.info("=" * 60)

    decade_mask = np.array([c in keep_decades for c in cohort_labels])
    combined_mask = valid_cohort & decade_mask

    cohort_results = compare_groups(
        embeddings=embeddings[combined_mask],
        group_labels=cohort_labels[combined_mask],
        n_permutations=args.n_perms,
        n_landmarks=args.landmarks,
    )
    all_results["cohort"] = cohort_results

    elapsed = time.time() - t0
    logger.info(f"Cohort analysis complete in {elapsed:.1f}s")
    _save_json(all_results, output_dir / "06_stratified.json")
    return all_results


def run_nssec(args: argparse.Namespace) -> dict:
    """Run parental NS-SEC (3-class) stratification."""
    from trajectory_tda.analysis.group_comparison import compare_groups

    t0 = time.time()
    embeddings, pidp_array, cov_lookup, n = _load_shared_data(args)
    output_dir = Path(args.results_dir)
    all_results = _load_results(output_dir)

    nssec_labels = np.array(
        [cov_lookup.at[p, "parental_nssec3"] if p in cov_lookup.index else None for p in pidp_array],
        dtype=object,
    )

    valid_nssec = np.array([x is not None and not (isinstance(x, float) and np.isnan(x)) for x in nssec_labels])
    nssec_valid = int(valid_nssec.sum())
    logger.info(f"Parental NS-SEC coverage: {nssec_valid}/{n}")

    if nssec_valid <= 100:
        logger.warning(f"Insufficient NS-SEC coverage ({nssec_valid}) — skipping")
        return all_results

    logger.info("=" * 60)
    logger.info("Stratification: Parental NS-SEC (3-class)")
    logger.info("=" * 60)

    nssec_results = compare_groups(
        embeddings=embeddings[valid_nssec],
        group_labels=nssec_labels[valid_nssec],
        n_permutations=args.n_perms,
        n_landmarks=args.landmarks,
    )
    all_results["parental_nssec"] = nssec_results

    elapsed = time.time() - t0
    logger.info(f"Parental NS-SEC analysis complete in {elapsed:.1f}s")
    _save_json(all_results, output_dir / "06_stratified.json")
    return all_results


# ─────────────────────────────────────────────────────────────
# Orchestrator (runs selected or all)
# ─────────────────────────────────────────────────────────────

STRAT_RUNNERS = {
    "gender": run_gender,
    "cohort": run_cohort,
    "nssec": run_nssec,
}


def run_stratified(args: argparse.Namespace) -> dict:
    """Run one or all stratifications based on --strat flag."""
    strats = list(STRAT_RUNNERS.keys()) if args.strat == "all" else [args.strat]

    for name in strats:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Running stratification: {name}")
        logger.info(f"{'=' * 60}")
        STRAT_RUNNERS[name](args)

    # Final summary
    output_dir = Path(args.results_dir)
    all_results = _load_results(output_dir)
    logger.info("=" * 60)
    logger.info("Summary of all stratified results:")
    for strat_name in ["gender", "cohort", "parental_nssec"]:
        if strat_name in all_results:
            r = all_results[strat_name]
            n_sig = sum(
                1
                for v in r.get("pairwise_p_values", {}).values()
                if isinstance(v, dict) and v.get("significant_at_005")
            )
            n_tests = len(r.get("pairwise_p_values", {}))
            logger.info(f"  {strat_name}: {n_sig}/{n_tests} significant pairwise tests")
        else:
            logger.info(f"  {strat_name}: not yet run")
    logger.info("=" * 60)

    return all_results


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run stratified group comparisons from checkpoint data")
    parser.add_argument(
        "--strat",
        type=str,
        choices=VALID_STRATS,
        default="all",
        help="Which stratification to run: gender, cohort, nssec, or all (default: all)",
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="results/trajectory_tda_integration",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="trajectory_tda/data",
    )
    parser.add_argument(
        "--n-perms",
        type=int,
        default=100,
        help="Permutations per pairwise test (default: 100)",
    )
    parser.add_argument(
        "--landmarks",
        type=int,
        default=2000,
        help="Landmarks per stratum (default: 2000)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
    )

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    run_stratified(args)


if __name__ == "__main__":
    main()
