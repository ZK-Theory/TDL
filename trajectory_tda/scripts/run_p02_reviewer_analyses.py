"""Run all P02 reviewer-response analyses.

Orchestrates:
  1. UMAP embedding robustness (Mapper on UMAP-16D)
  2. Permutation null tests for sub-regime counts
  3. Multi-threshold sub-regime analysis with FDR correction
  4. Outcome--embedding correlation matrix
  5. R3/R5 churning transition decomposition

Usage:
    python -m trajectory_tda.scripts.run_p02_reviewer_analyses
    python -m trajectory_tda.scripts.run_p02_reviewer_analyses \
        --results-dir results/trajectory_tda_integration \
        --mapper-dir results/trajectory_tda_mapper \
        --output-dir results/trajectory_tda_mapper/reviewer_response \
        --n-perms 100
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from collections import Counter
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


def _save_json(data: dict | list, path: Path) -> None:
    """Save data to JSON with numpy type conversion."""

    def convert(obj: object) -> object:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, set):
            return sorted(obj)
        return obj

    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=convert)
    logger.info("Saved %s", path)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="P02 reviewer-response analyses.")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results/trajectory_tda_integration"),
        help="P01 integration results directory.",
    )
    parser.add_argument(
        "--mapper-dir",
        type=Path,
        default=Path("results/trajectory_tda_mapper"),
        help="P02 Mapper results directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/trajectory_tda_mapper/reviewer_response"),
        help="Output directory for reviewer analyses.",
    )
    parser.add_argument(
        "--outcomes-path",
        type=Path,
        default=Path("trajectory_tda/data/trajectory_outcomes.npz"),
        help="Path to trajectory_outcomes.npz.",
    )
    parser.add_argument(
        "--n-perms",
        type=int,
        default=100,
        help="Number of permutations for null tests.",
    )
    parser.add_argument(
        "--n-jobs",
        type=int,
        default=-1,
        help="Parallelism for joblib (-1 = all cores).",
    )
    parser.add_argument(
        "--skip-umap",
        action="store_true",
        help="Skip UMAP robustness analysis.",
    )
    parser.add_argument(
        "--skip-nulls",
        action="store_true",
        help="Skip permutation null tests.",
    )
    parser.add_argument(
        "--skip-correlations",
        action="store_true",
        help="Skip correlation matrix.",
    )
    parser.add_argument(
        "--skip-churning",
        action="store_true",
        help="Skip churning decomposition.",
    )
    return parser.parse_args()


# ────────────────────────────────────────────────────────────────────
# Analysis 1: UMAP Embedding Robustness
# ────────────────────────────────────────────────────────────────────


def run_umap_robustness(
    results_dir: Path,
    output_dir: Path,
    gmm_labels: NDArray[np.int64],
    n_regimes: int,
) -> dict:
    """Run Mapper on UMAP-16D embeddings and compare to PCA-20D baseline."""
    from trajectory_tda.mapper.mapper_pipeline import (
        build_mapper_graph,
        mapper_graph_summary,
    )
    from trajectory_tda.mapper.validation import (
        identify_subregime_structure,
        validate_against_regimes,
    )

    umap_path = results_dir / "embeddings_umap16.npy"
    if not umap_path.exists():
        logger.warning("UMAP embeddings not found at %s; skipping", umap_path)
        return {"error": "UMAP embeddings not found"}

    umap_emb = np.load(umap_path)
    logger.info("Loaded UMAP-16D embeddings: %s", umap_emb.shape)

    configs = [
        # DBSCAN with first-2D lens
        {
            "label": "umap16_pca2d_dbscan_eps0.5",
            "projection": "pca_2d",
            "clusterer": "dbscan",
            "clusterer_params": {"eps": 0.5, "min_samples": 5},
        },
        # DBSCAN with L2 norm lens
        {
            "label": "umap16_l2norm_dbscan_eps0.5",
            "projection": "l2norm",
            "clusterer": "dbscan",
            "clusterer_params": {"eps": 0.5, "min_samples": 5},
        },
        # Agglomerative with first-2D lens
        {
            "label": "umap16_pca2d_agglom_t1.5",
            "projection": "pca_2d",
            "clusterer": "agglomerative",
            "clusterer_params": {"threshold": 1.5},
        },
        # DBSCAN with UMAP first-2D as explicit lens (reviewer suggestion)
        {
            "label": "umap16_umap2d_dbscan_eps0.5",
            "projection": lambda emb: emb[:, :2],  # noqa: ARG005 — first 2 UMAP dims as lens
            "clusterer": "dbscan",
            "clusterer_params": {"eps": 0.5, "min_samples": 5},
        },
    ]

    all_results = []
    for cfg in configs:
        label = cfg["label"]
        logger.info("UMAP robustness: %s", label)

        proj = cfg["projection"]
        try:
            graph, _ = build_mapper_graph(
                umap_emb,
                projection=proj,
                n_cubes=30,
                overlap_frac=0.5,
                clusterer=cfg["clusterer"],
                clusterer_params=cfg["clusterer_params"],
                verbose=0,
            )
        except Exception as exc:
            logger.warning("Failed %s: %s", label, exc)
            all_results.append({"label": label, "error": str(exc)})
            continue

        summary = mapper_graph_summary(graph, n_points=len(umap_emb))
        validation = validate_against_regimes(graph, gmm_labels, n_regimes=n_regimes)

        # Sub-regime on first UMAP dimension (analogous to PC1)
        umap_dim1 = umap_emb[:, 0]
        l2_values = np.linalg.norm(umap_emb, axis=1)
        sub_dim1 = identify_subregime_structure(graph, gmm_labels, umap_dim1)
        sub_l2 = identify_subregime_structure(graph, gmm_labels, l2_values)

        entry = {
            "label": label,
            "summary": summary,
            "validation": {
                "nmi": validation["nmi"],
                "purity": validation["purity"],
                "n_bridge_nodes": validation["n_bridge_nodes"],
            },
            "subregime_dim1": {
                "n_total": sub_dim1["n_total"],
                "per_regime": sub_dim1["summary"],
            },
            "subregime_l2": {
                "n_total": sub_l2["n_total"],
                "per_regime": sub_l2["summary"],
            },
        }
        all_results.append(entry)

        logger.info(
            "  -> nodes=%d coverage=%.1f%% NMI=%.3f purity=%.3f sub_dim1=%d sub_l2=%d",
            summary["n_nodes"],
            summary["coverage"] * 100,
            validation["nmi"],
            validation["purity"],
            sub_dim1["n_total"],
            sub_l2["n_total"],
        )

    out_path = output_dir / "01_umap_robustness.json"
    _save_json({"configs_tested": len(configs), "results": all_results}, out_path)
    return {"configs_tested": len(configs), "results": all_results}


# ────────────────────────────────────────────────────────────────────
# Analysis 2: Permutation Null Tests
# ────────────────────────────────────────────────────────────────────


def run_permutation_nulls(
    embeddings: NDArray[np.float64],
    gmm_labels: NDArray[np.int64],
    n_regimes: int,
    n_perms: int,
    n_jobs: int,
    output_dir: Path,
) -> dict:
    """Run both permutation null tests on Mapper sub-regime counts."""
    from trajectory_tda.mapper.mapper_pipeline import build_mapper_graph
    from trajectory_tda.mapper.permutation_null import (
        regime_shuffle_null,
        within_node_shuffle_null,
    )

    pc1 = embeddings[:, 0]
    build_kwargs = {
        "projection": "pca_2d",
        "n_cubes": 30,
        "overlap_frac": 0.5,
        "clusterer": "dbscan",
        "clusterer_params": {"eps": 0.5, "min_samples": 5},
    }

    # Test 1: Regime-shuffle null
    logger.info("Running regime-shuffle null (%d perms)...", n_perms)
    regime_result = regime_shuffle_null(
        embeddings,
        gmm_labels,
        pc1,
        n_regimes=n_regimes,
        n_perms=n_perms,
        threshold_std=1.0,
        build_kwargs=build_kwargs,
        n_jobs=n_jobs,
    )

    # Test 2: Within-node-shuffle null (fix graph, shuffle outcomes)
    logger.info("Running within-node-shuffle null (%d perms)...", n_perms)
    graph, _ = build_mapper_graph(embeddings, verbose=0, **build_kwargs)
    within_result = within_node_shuffle_null(
        graph,
        gmm_labels,
        pc1,
        n_perms=n_perms,
        threshold_std=1.0,
        n_jobs=n_jobs,
    )

    results = {"regime_shuffle": regime_result, "within_node_shuffle": within_result}
    _save_json(results, output_dir / "02_permutation_nulls.json")
    return results


# ────────────────────────────────────────────────────────────────────
# Analysis 3: Multi-Threshold Sub-Regime + FDR Correction
# ────────────────────────────────────────────────────────────────────


def run_multi_threshold_analysis(
    embeddings: NDArray[np.float64],
    gmm_labels: NDArray[np.int64],
    n_regimes: int,
    output_dir: Path,
) -> dict:
    """Run sub-regime detection at multiple z-score thresholds with FDR."""
    from trajectory_tda.mapper.mapper_pipeline import build_mapper_graph
    from trajectory_tda.mapper.validation import identify_subregime_structure

    build_kwargs = {
        "projection": "pca_2d",
        "n_cubes": 30,
        "overlap_frac": 0.5,
        "clusterer": "dbscan",
        "clusterer_params": {"eps": 0.5, "min_samples": 5},
    }

    graph, _ = build_mapper_graph(embeddings, verbose=0, **build_kwargs)

    pc1 = embeddings[:, 0]
    l2 = np.linalg.norm(embeddings, axis=1)
    thresholds = [0.5, 1.0, 1.5, 2.0]

    results_by_threshold = {}
    for thresh in thresholds:
        pc1_result = identify_subregime_structure(graph, gmm_labels, pc1, threshold_std=thresh)
        l2_result = identify_subregime_structure(graph, gmm_labels, l2, threshold_std=thresh)
        results_by_threshold[str(thresh)] = {
            "pc1": {
                "n_total": pc1_result["n_total"],
                "per_regime": pc1_result["summary"],
            },
            "l2": {
                "n_total": l2_result["n_total"],
                "per_regime": l2_result["summary"],
            },
        }
        logger.info(
            "Threshold |z|>%.1f: PC1=%d sub-regime nodes, L2=%d",
            thresh,
            pc1_result["n_total"],
            l2_result["n_total"],
        )

    # FDR correction (Benjamini-Hochberg) across 7 regimes × 2 variables = 14 tests
    # For each regime-variable pair, compute a one-sided test:
    # fraction of nodes with |z| > threshold vs expected under normality
    n_nodes_total = len(graph.get("nodes", {}))
    fdr_results = _compute_fdr_correction(graph, gmm_labels, pc1, l2, n_regimes, n_nodes_total)

    output = {
        "thresholds": thresholds,
        "results_by_threshold": results_by_threshold,
        "fdr_correction": fdr_results,
    }
    _save_json(output, output_dir / "03_multi_threshold.json")
    return output


def _compute_fdr_correction(
    graph: dict,
    gmm_labels: NDArray[np.int64],
    pc1: NDArray[np.float64],
    l2: NDArray[np.float64],
    n_regimes: int,
    n_nodes_total: int,
) -> dict:
    """Compute FDR-corrected significance for sub-regime counts at |z|>1.0.

    For each regime × variable pair, tests whether the fraction of nodes
    with |z| > 1.0 exceeds the expected fraction under normality (31.7%).
    Uses a binomial test approximation, then applies Benjamini-Hochberg FDR.
    """
    from scipy.stats import binomtest, norm

    from trajectory_tda.mapper.validation import identify_subregime_structure

    threshold = 1.0
    expected_fraction = 2 * (1 - norm.cdf(threshold))  # ~0.3173

    p_values = []
    test_labels = []

    for var_name, outcome_values in [("PC1", pc1), ("L2", l2)]:
        result = identify_subregime_structure(graph, gmm_labels, outcome_values, threshold_std=threshold)
        for regime_idx in range(n_regimes):
            n_regime_nodes = result["summary"].get(regime_idx, 0)

            # Count total nodes dominated by this regime
            nodes = graph.get("nodes", {})
            regime_node_count = 0
            for _node_id, members in nodes.items():
                member_regimes = gmm_labels[members]
                counts = Counter(int(r) for r in member_regimes)
                if counts:
                    dominant = counts.most_common(1)[0][0]
                    if dominant == regime_idx and counts.most_common(1)[0][1] / len(members) >= 0.5:
                        regime_node_count += 1

            if regime_node_count == 0:
                continue

            # One-sided binomial test: observed >= expected?
            bt = binomtest(
                n_regime_nodes,
                regime_node_count,
                expected_fraction,
                alternative="greater",
            )
            p_values.append(bt.pvalue)
            test_labels.append(f"R{regime_idx}_{var_name}")

    # Benjamini-Hochberg FDR correction
    if p_values:
        sorted_indices = np.argsort(p_values)
        m = len(p_values)
        fdr_adjusted = np.zeros(m)
        for rank_idx, orig_idx in enumerate(sorted_indices):
            rank = rank_idx + 1
            fdr_adjusted[orig_idx] = min(p_values[orig_idx] * m / rank, 1.0)
        # Enforce monotonicity
        for i in range(m - 2, -1, -1):
            fdr_adjusted[sorted_indices[i]] = min(
                fdr_adjusted[sorted_indices[i]],
                fdr_adjusted[sorted_indices[i + 1]] if i + 1 < m else 1.0,
            )
    else:
        fdr_adjusted = np.array([])

    fdr_results = {}
    for i, label in enumerate(test_labels):
        fdr_results[label] = {
            "raw_p": float(p_values[i]),
            "fdr_adjusted_p": float(fdr_adjusted[i]),
            "significant_005": bool(fdr_adjusted[i] < 0.05),
        }

    n_sig = sum(1 for v in fdr_results.values() if v["significant_005"])
    logger.info(
        "FDR correction: %d/%d tests significant at q<0.05",
        n_sig,
        len(fdr_results),
    )

    return fdr_results


# ────────────────────────────────────────────────────────────────────
# Analysis 4: Outcome--Embedding Correlation Matrix
# ────────────────────────────────────────────────────────────────────


def run_correlation_analysis(
    embeddings: NDArray[np.float64],
    outcomes_path: Path,
    output_dir: Path,
) -> dict:
    """Compute and save correlation matrix between embedding and outcomes."""
    from trajectory_tda.mapper.correlation_analysis import (
        compute_outcome_correlation_matrix,
    )

    if not outcomes_path.exists():
        logger.warning("Outcomes file not found: %s", outcomes_path)
        return {"error": "outcomes file not found"}

    outcomes = np.load(outcomes_path)
    outcome_dict = {key: outcomes[key] for key in outcomes.files}

    result = compute_outcome_correlation_matrix(embeddings, outcome_dict)
    _save_json(result, output_dir / "04_correlation_matrix.json")
    return result


# ────────────────────────────────────────────────────────────────────
# Analysis 5: R3/R5 Churning Transition Decomposition
# ────────────────────────────────────────────────────────────────────


def run_churning_decomposition(
    results_dir: Path,
    gmm_labels: NDArray[np.int64],
    output_dir: Path,
) -> dict:
    """Decompose churning transitions in R3 and R5 by type.

    Classifies each year-to-year state change as one of:
      - E<->I: employment to inactivity or vice versa
      - E<->U: employment to unemployment or vice versa
      - U<->I: unemployment to inactivity or vice versa
      - within_E: between employment income bands
      - within_I: between inactivity income bands
      - within_U: between unemployment income bands
    """
    employed = {"EL", "EM", "EH"}
    unemployed = {"UL", "UM", "UH"}

    def classify_transition(s1: str, s2: str) -> str:
        """Classify a state transition by type."""
        if s1 == s2:
            return "no_change"
        cat1 = "E" if s1 in employed else ("U" if s1 in unemployed else "I")
        cat2 = "E" if s2 in employed else ("U" if s2 in unemployed else "I")
        if cat1 == cat2:
            return f"within_{cat1}"
        pair = tuple(sorted([cat1, cat2]))
        return f"{pair[0]}<->{pair[1]}"

    # Load trajectories
    seq_path = results_dir / "01_trajectories_sequences.json"
    with open(seq_path) as f:
        trajectories = json.load(f)

    target_regimes = {3: "R3_Emp-Inactive_Mix", 5: "R5_High-Income_Inactive"}
    results = {}

    for regime_idx, regime_name in target_regimes.items():
        mask = gmm_labels == regime_idx
        regime_indices = np.where(mask)[0]

        transition_counts: Counter = Counter()
        total_transitions = 0

        for idx in regime_indices:
            if idx >= len(trajectories):
                continue
            seq = trajectories[idx]
            for t in range(1, len(seq)):
                if seq[t] != seq[t - 1]:
                    trans_type = classify_transition(seq[t - 1], seq[t])
                    transition_counts[trans_type] += 1
                    total_transitions += 1

        # Convert to fractions
        fractions = {}
        if total_transitions > 0:
            for ttype, count in sorted(transition_counts.items()):
                fractions[ttype] = {
                    "count": count,
                    "fraction": round(count / total_transitions, 4),
                }

        results[regime_name] = {
            "n_trajectories": int(mask.sum()),
            "total_transitions": total_transitions,
            "transition_types": fractions,
        }

        logger.info(
            "%s: %d trajectories, %d transitions",
            regime_name,
            mask.sum(),
            total_transitions,
        )
        for ttype in ["E<->I", "E<->U", "I<->U", "within_E", "within_I", "within_U"]:
            fr = fractions.get(ttype, {}).get("fraction", 0.0)
            logger.info("  %s: %.1f%%", ttype, fr * 100)

    _save_json(results, output_dir / "05_churning_decomposition.json")
    return results


# ────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    args = _parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()

    # Load shared data
    logger.info("Loading data from %s", args.results_dir)
    embeddings = np.load(args.results_dir / "embeddings.npy")
    with open(args.results_dir / "05_analysis.json") as f:
        analysis = json.load(f)
    gmm_labels = np.array(analysis["gmm_labels"], dtype=np.int64)
    n_regimes = analysis["regimes"]["k_optimal"]
    logger.info(
        "Loaded: %d embeddings (%dD), %d regimes",
        len(embeddings),
        embeddings.shape[1],
        n_regimes,
    )

    all_results = {}

    # 1. UMAP robustness
    if not args.skip_umap:
        logger.info("=" * 60)
        logger.info("ANALYSIS 1: UMAP Embedding Robustness")
        logger.info("=" * 60)
        all_results["umap_robustness"] = run_umap_robustness(args.results_dir, output_dir, gmm_labels, n_regimes)

    # 2. Permutation nulls
    if not args.skip_nulls:
        logger.info("=" * 60)
        logger.info("ANALYSIS 2: Permutation Null Tests")
        logger.info("=" * 60)
        all_results["permutation_nulls"] = run_permutation_nulls(
            embeddings, gmm_labels, n_regimes, args.n_perms, args.n_jobs, output_dir
        )

    # 3. Multi-threshold analysis
    logger.info("=" * 60)
    logger.info("ANALYSIS 3: Multi-Threshold Sub-Regime + FDR")
    logger.info("=" * 60)
    all_results["multi_threshold"] = run_multi_threshold_analysis(embeddings, gmm_labels, n_regimes, output_dir)

    # 4. Correlation matrix
    if not args.skip_correlations:
        logger.info("=" * 60)
        logger.info("ANALYSIS 4: Outcome-Embedding Correlation Matrix")
        logger.info("=" * 60)
        all_results["correlation_matrix"] = run_correlation_analysis(embeddings, args.outcomes_path, output_dir)

    # 5. Churning decomposition
    if not args.skip_churning:
        logger.info("=" * 60)
        logger.info("ANALYSIS 5: R3/R5 Churning Decomposition")
        logger.info("=" * 60)
        all_results["churning_decomposition"] = run_churning_decomposition(args.results_dir, gmm_labels, output_dir)

    elapsed = time.time() - t0
    logger.info("=" * 60)
    logger.info("All analyses complete in %.1fs", elapsed)
    logger.info("Results saved to %s", output_dir)

    # Save combined summary
    _save_json(
        {"elapsed_seconds": elapsed, "analyses_run": list(all_results.keys())},
        output_dir / "00_summary.json",
    )


if __name__ == "__main__":
    main()
