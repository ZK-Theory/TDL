# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: T1.26 BHPS non-overlap sensitivity. Exclude BHPS individuals who
#   span into USoc, refit the k=8 GMM under full-BHPS frozen PCA loadings, and
#   rerun the canonical Stage-1 persistence headline on the BHPS-only remainder.
"""BHPS non-overlap sensitivity for the P01-A replication framing."""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from trajectory_tda.embedding.ngram_embed import _compute_bigrams, _compute_unigrams
from trajectory_tda.scripts.stage1 import _battery_core as core

LOGGER = logging.getLogger(__name__)

PROJ_ROOT = Path(os.environ.get("TDL_PROJ_ROOT", "C:/Users/steph/TDL"))
WORKTREE = Path(os.environ.get("TDL_WORKTREE", Path.cwd()))
BHPS_DIR_REL = Path("results/trajectory_tda_bhps")
SPANNING_DIR_REL = Path("results/trajectory_tda_spanning")
OUT_DIR_REL = Path("results/panel_methodology/bhps_nonoverlap")
BASELINE_HEADLINE_REL = Path("results/trajectory_tda_bhps/stage1/bhps_headline_frozen_2026-05-28.json")

SCHEMA_VERSION = "stage1/bhps-nonoverlap/v1"
TASK_NAME = "T1.26 BHPS non-overlap sensitivity"
PRE_REGISTRATION_REF = (
    "2026-06-08 T1.26 pre-registration: "
    "results/panel_methodology/bhps_nonoverlap/pre_registrations_2026-06-08.json"
)

GMM_K = 8
GMM_COVARIANCE_TYPE = "full"
GMM_N_INIT = 5
GMM_MAX_ITER = 200
SEED = 42
PCA_DIM = 20
PCA_SVD_SOLVER = "full"
ALPHA_LEVEL = 0.05
ARI_STABILITY_THRESHOLD = 0.9
P_VALUE_FORMULA = "(r+1)/(B+1)"


def _git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unavailable"


def _ordered_metadata_column(metadata: dict[str, Any], key: str) -> list[Any]:
    values = metadata[key]
    if not isinstance(values, dict):
        return list(values)
    return [values[str(i)] for i in range(len(values))]


def _load_checkpoint(checkpoint_dir: Path) -> tuple[list[list[str]], list[int]]:
    seq_path = checkpoint_dir / "01_trajectories_sequences.json"
    meta_path = checkpoint_dir / "01_trajectories.json"
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    sequences = json.loads(seq_path.read_text(encoding="utf-8"))
    pidps = [int(pidp) for pidp in _ordered_metadata_column(payload["metadata"], "pidp")]
    if len(sequences) != len(pidps):
        raise ValueError(f"Checkpoint length mismatch at {checkpoint_dir}")
    return sequences, pidps


def _load_baseline_labels(analysis_path: Path, expected_n: int) -> NDArray[np.int64]:
    payload = json.loads(analysis_path.read_text(encoding="utf-8"))
    labels = np.asarray(payload["gmm_labels"], dtype=np.int64)
    if len(labels) != expected_n:
        raise ValueError(
            f"Baseline GMM labels length {len(labels)} does not match BHPS checkpoint length {expected_n}"
        )
    return labels


def _build_raw_ngram_features(trajectories: list[list[str]]) -> NDArray[np.float64]:
    features = np.zeros((len(trajectories), 90), dtype=np.float64)
    for idx, trajectory in enumerate(trajectories):
        features[idx] = np.concatenate([_compute_unigrams(trajectory), _compute_bigrams(trajectory)])
    return features


def _fit_full_bhps_reference(
    trajectories: list[list[str]],
) -> tuple[NDArray[np.float64], dict[str, Any], dict[str, Any]]:
    raw = _build_raw_ngram_features(trajectories)
    scaler = StandardScaler(with_std=True)
    scaled = scaler.fit_transform(raw)
    pca = PCA(n_components=PCA_DIM, svd_solver=PCA_SVD_SOLVER, random_state=SEED)
    embedding = pca.fit_transform(scaled)
    models = {"scaler": scaler, "reducer": pca}
    info = {
        "reference": "full BHPS checkpoint",
        "reference_n": int(len(trajectories)),
        "raw_dims": int(raw.shape[1]),
        "pca_dim": PCA_DIM,
        "pca_svd_solver": PCA_SVD_SOLVER,
        "frozen_loadings": True,
        "pca_explained_variance": float(pca.explained_variance_ratio_.sum()),
    }
    return embedding, models, info


def _fit_subset_gmm(embedding: NDArray[np.float64]) -> tuple[GaussianMixture, NDArray[np.int64]]:
    gmm = GaussianMixture(
        n_components=GMM_K,
        covariance_type=GMM_COVARIANCE_TYPE,
        n_init=GMM_N_INIT,
        max_iter=GMM_MAX_ITER,
        random_state=SEED,
    )
    gmm.fit(embedding)
    return gmm, gmm.predict(embedding).astype(np.int64)


def _label_counts(labels: NDArray[np.int64]) -> dict[str, int]:
    values, counts = np.unique(labels, return_counts=True)
    return {str(int(value)): int(count) for value, count in zip(values, counts, strict=True)}


def _direction(cell: dict[str, Any]) -> str:
    delta = float(cell["mean_obs_null"]) - float(cell["mean_null_null"])
    if delta > 0:
        return "obs_null_gt_null_null"
    if delta < 0:
        return "obs_null_lt_null_null"
    return "tie"


def _range_check_number(value: Any, lo: float, hi: float, name: str, errors: list[str]) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        errors.append(f"{name} must be numeric")
        return
    if not lo <= float(value) <= hi:
        errors.append(f"{name} must be in [{lo}, {hi}]")


def _positive_int(value: Any, name: str, errors: list[str], allow_zero: bool = False) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        errors.append(f"{name} must be an int")
        return
    if allow_zero:
        if value < 0:
            errors.append(f"{name} must be >= 0")
    elif value <= 0:
        errors.append(f"{name} must be > 0")


def validate_bhps_nonoverlap_payload(payload: dict[str, Any]) -> None:
    """Validate a T1.26 BHPS non-overlap result payload.

    Args:
        payload: Candidate result payload.

    Raises:
        ValueError: If required fields, pinned literals, ranges, or coupled
            decision rules are violated.
    """
    errors: list[str] = []
    required = ["schema_version", "generated_at", "task", "pre_registration", "inputs", "params", "results", "decision"]
    for key in required:
        if key not in payload:
            errors.append(f"missing required key: {key}")
    if "per_call_pca" in payload:
        errors.append("forbidden key present: per_call_pca")
    if errors:
        raise ValueError("; ".join(errors))

    if payload["schema_version"] != SCHEMA_VERSION:
        errors.append(f"schema_version must equal {SCHEMA_VERSION!r}")
    if payload["task"] != TASK_NAME:
        errors.append(f"task must equal {TASK_NAME!r}")
    if "2026-06-08" not in str(payload["pre_registration"]):
        errors.append("pre_registration must reference the 2026-06-08 T1.26 pre-registration")

    inputs = payload["inputs"]
    for key in ("full_bhps_source", "spanning_ids_source", "baseline_bhps_gmm_labels_source", "git_head"):
        if key not in inputs:
            errors.append(f"inputs missing {key}")
    if "trajectory_tda_bhps" not in str(inputs.get("full_bhps_source", "")):
        errors.append("inputs.full_bhps_source must reference the BHPS checkpoint")
    if "trajectory_tda_spanning" not in str(inputs.get("spanning_ids_source", "")):
        errors.append("inputs.spanning_ids_source must reference the spanning checkpoint")
    if "05_analysis.json" not in str(inputs.get("baseline_bhps_gmm_labels_source", "")):
        errors.append("inputs.baseline_bhps_gmm_labels_source must reference 05_analysis.json")

    params = payload["params"]
    expected = {
        "gmm_k": GMM_K,
        "gmm_covariance_type": GMM_COVARIANCE_TYPE,
        "gmm_n_init": GMM_N_INIT,
        "gmm_max_iter": GMM_MAX_ITER,
        "seed": SEED,
        "pca_dim": PCA_DIM,
        "pca_svd_solver": PCA_SVD_SOLVER,
        "frozen_loadings": True,
        "p_value_formula": P_VALUE_FORMULA,
        "alpha_level": ALPHA_LEVEL,
        "ari_stability_threshold": ARI_STABILITY_THRESHOLD,
    }
    for key, value in expected.items():
        if params.get(key) != value:
            errors.append(f"params.{key} must equal {value!r}")
    _positive_int(params.get("L"), "params.L", errors)
    if params.get("L") != core.DEFAULT_L:
        errors.append(f"params.L must equal {core.DEFAULT_L}")
    _positive_int(params.get("B"), "params.B", errors)
    if isinstance(params.get("B"), int) and params["B"] < 1000:
        errors.append("params.B must be >= 1000")

    results = payload["results"]
    for key in ("n_bhps_full", "n_bhps_only"):
        _positive_int(results.get(key), f"results.{key}", errors)
    _positive_int(results.get("n_spanning_excluded"), "results.n_spanning_excluded", errors, allow_zero=True)
    if all(isinstance(results.get(key), int) for key in ("n_bhps_full", "n_spanning_excluded", "n_bhps_only")):
        if results["n_bhps_only"] != results["n_bhps_full"] - results["n_spanning_excluded"]:
            errors.append("results.n_bhps_only must equal n_bhps_full - n_spanning_excluded")
    _range_check_number(results.get("ari_vs_full"), -1.0, 1.0, "results.ari_vs_full", errors)
    if not isinstance(results.get("regime_stable"), bool):
        errors.append("results.regime_stable must be bool")
    elif isinstance(results.get("ari_vs_full"), (int, float)):
        if results["regime_stable"] != (float(results["ari_vs_full"]) >= ARI_STABILITY_THRESHOLD):
            errors.append("results.regime_stable must equal ari_vs_full >= 0.9")

    persistence = results.get("persistence", {})
    if not isinstance(persistence, dict):
        errors.append("results.persistence must be a dict")
        persistence = {}
    _range_check_number(persistence.get("h0_w2_p"), 0.0, 1.0, "results.persistence.h0_w2_p", errors)
    _range_check_number(persistence.get("h1_w2_p"), 0.0, 1.0, "results.persistence.h1_w2_p", errors)
    if not isinstance(persistence.get("h0_rejects"), bool):
        errors.append("results.persistence.h0_rejects must be bool")
    elif isinstance(persistence.get("h0_w2_p"), (int, float)):
        if persistence["h0_rejects"] != (float(persistence["h0_w2_p"]) < ALPHA_LEVEL):
            errors.append("results.persistence.h0_rejects must equal h0_w2_p < 0.05")
    if not isinstance(persistence.get("h1_asymmetry_preserved"), bool):
        errors.append("results.persistence.h1_asymmetry_preserved must be bool")

    decision = payload["decision"]
    if not isinstance(decision.get("primary_preserved"), bool):
        errors.append("decision.primary_preserved must be bool")
    else:
        expected_primary = bool(
            isinstance(persistence.get("h0_rejects"), bool)
            and persistence["h0_rejects"]
            and isinstance(persistence.get("h1_asymmetry_preserved"), bool)
            and persistence["h1_asymmetry_preserved"]
        )
        if decision["primary_preserved"] != expected_primary:
            errors.append("decision.primary_preserved must equal h0_rejects and h1_asymmetry_preserved")
    if decision.get("outcome") not in {"supported", "overlap_dependent"}:
        errors.append("decision.outcome must be 'supported' or 'overlap_dependent'")
    elif isinstance(decision.get("primary_preserved"), bool):
        expected_outcome = "supported" if decision["primary_preserved"] else "overlap_dependent"
        if decision["outcome"] != expected_outcome:
            errors.append("decision.outcome must be supported iff decision.primary_preserved is true")

    if errors:
        raise ValueError("; ".join(errors))


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Execute the non-overlap sensitivity and write the date-suffixed JSON."""
    started = time.perf_counter()
    worktree = Path(args.worktree)
    proj_root = Path(args.proj_root)
    output_dir = worktree / OUT_DIR_REL
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"bhps_only_gmm_ph_{args.date}.json"
    if output_path.exists():
        raise FileExistsError(f"Result already exists: {output_path}")

    cache_path = (
        proj_root
        / "results/trajectory_tda_integration/stage1/cache"
        / f"null_diagrams_bhps_nonoverlap_frozen_B{args.B}_L{args.L}_seed{args.seed}_{args.date}.npz"
    )
    if cache_path.exists():
        raise FileExistsError(f"Null-diagram cache already exists: {cache_path}")

    marker_path = core.write_launch_marker(
        "bhps_nonoverlap",
        {"L": args.L, "B": args.B, "seed": args.seed, "frozen_loadings": True},
    )

    bhps_dir = proj_root / BHPS_DIR_REL
    spanning_dir = proj_root / SPANNING_DIR_REL
    full_sequences, full_pidps = _load_checkpoint(bhps_dir)
    spanning_sequences, spanning_pidps = _load_checkpoint(spanning_dir)
    del spanning_sequences
    baseline_labels = _load_baseline_labels(bhps_dir / "05_analysis.json", len(full_pidps))

    full_embedding, frozen_models, representation_info = _fit_full_bhps_reference(full_sequences)
    spanning_pidp_set = set(spanning_pidps)
    keep_indices = [idx for idx, pidp in enumerate(full_pidps) if pidp not in spanning_pidp_set]
    excluded_indices = [idx for idx, pidp in enumerate(full_pidps) if pidp in spanning_pidp_set]
    if not keep_indices:
        raise ValueError("Spanning exclusion removed the full BHPS sample")

    subset_sequences = [full_sequences[idx] for idx in keep_indices]
    subset_embedding = full_embedding[keep_indices]
    baseline_subset_labels = baseline_labels[keep_indices]
    subset_pidps = [full_pidps[idx] for idx in keep_indices]

    gmm, subset_labels = _fit_subset_gmm(subset_embedding)
    ari = float(adjusted_rand_score(baseline_subset_labels, subset_labels))
    regime_stable = bool(ari >= ARI_STABILITY_THRESHOLD)

    embed_kwargs = {"include_bigrams": True, "tfidf": False, "pca_dim": PCA_DIM}
    out, null_results, ph_obs = core.run_headline_from_embeddings(
        embeddings=subset_embedding,
        trajectories=subset_sequences,
        embed_kwargs=embed_kwargs,
        n_permutations=args.B,
        n_landmarks=args.L,
        k_max=args.k_max,
        n_points=args.n_points,
        seed=args.seed,
        label="BHPS non-overlap",
        phase_tag="bhps_nonoverlap",
        n_jobs=args.n_jobs,
        n_null_pairs_cap=args.n_null_pairs,
        markov_order=core.DEFAULT_MARKOV_ORDER,
        frozen_models=frozen_models,
    )
    cache_written = core.write_null_diagram_cache(
        cache_path,
        null_results,
        ph_obs,
        {
            "B": args.B,
            "L": args.L,
            "actual_landmarks": min(args.L, len(subset_sequences)),
            "seed": args.seed,
            "dataset": "bhps_nonoverlap",
            "timestamp": args.date,
            "frozen_loadings": True,
            "n_bhps_only": len(subset_sequences),
        },
    )

    baseline_headline = json.loads((proj_root / BASELINE_HEADLINE_REL).read_text(encoding="utf-8"))
    baseline_h1_direction = _direction(baseline_headline["result"]["h1"])
    subset_h1_direction = _direction(out["h1"])
    h0_p = float(out["h0"]["w2_pvalue"])
    h1_p = float(out["h1"]["w2_pvalue"])
    h0_rejects = bool(h0_p < ALPHA_LEVEL)
    h1_asymmetry_preserved = bool(subset_h1_direction == baseline_h1_direction)
    primary_preserved = bool(h0_rejects and h1_asymmetry_preserved)
    decision_outcome = "supported" if primary_preserved else "overlap_dependent"

    runtime_seconds = float(time.perf_counter() - started)
    result = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "task": TASK_NAME,
        "pre_registration": PRE_REGISTRATION_REF,
        "inputs": {
            "full_bhps_source": str(BHPS_DIR_REL / "01_trajectories.json"),
            "full_bhps_sequences_source": str(BHPS_DIR_REL / "01_trajectories_sequences.json"),
            "spanning_ids_source": str(SPANNING_DIR_REL / "01_trajectories.json") + "[metadata.pidp]",
            "baseline_bhps_gmm_labels_source": str(BHPS_DIR_REL / "05_analysis.json") + "[gmm_labels]",
            "baseline_bhps_headline_source": str(BASELINE_HEADLINE_REL),
            "git_head": _git_head(),
        },
        "params": {
            "gmm_k": GMM_K,
            "gmm_covariance_type": GMM_COVARIANCE_TYPE,
            "gmm_n_init": GMM_N_INIT,
            "gmm_max_iter": GMM_MAX_ITER,
            "seed": args.seed,
            "pca_dim": PCA_DIM,
            "pca_svd_solver": PCA_SVD_SOLVER,
            "frozen_loadings": True,
            "L": args.L,
            "actual_landmarks": int(min(args.L, len(subset_sequences))),
            "B": args.B,
            "n_null_pairs_cap": args.n_null_pairs,
            "landscape_k_max": args.k_max,
            "landscape_n_points": args.n_points,
            "null_model": f"markov-{core.DEFAULT_MARKOV_ORDER}",
            "p_value_formula": P_VALUE_FORMULA,
            "alpha_level": ALPHA_LEVEL,
            "ari_stability_threshold": ARI_STABILITY_THRESHOLD,
            "n_jobs": args.n_jobs,
        },
        "results": {
            "n_bhps_full": int(len(full_pidps)),
            "n_spanning_excluded": int(len(excluded_indices)),
            "n_bhps_only": int(len(subset_sequences)),
            "n_spanning_source": int(len(spanning_pidps)),
            "ari_vs_full": ari,
            "regime_stable": regime_stable,
            "persistence": {
                "h0_w2_p": h0_p,
                "h1_w2_p": h1_p,
                "h0_rejects": h0_rejects,
                "h1_asymmetry_preserved": h1_asymmetry_preserved,
                "baseline_h1_direction": baseline_h1_direction,
                "bhps_only_h1_direction": subset_h1_direction,
                "h0_mean_obs_null": float(out["h0"]["mean_obs_null"]),
                "h0_mean_null_null": float(out["h0"]["mean_null_null"]),
                "h1_mean_obs_null": float(out["h1"]["mean_obs_null"]),
                "h1_mean_null_null": float(out["h1"]["mean_null_null"]),
            },
            "gmm": {
                "converged": bool(gmm.converged_),
                "n_iter": int(gmm.n_iter_),
                "lower_bound": float(gmm.lower_bound_),
                "label_counts": _label_counts(subset_labels),
                "baseline_label_counts_on_remainder": _label_counts(baseline_subset_labels),
                "n_common_pidps": int(len(subset_pidps)),
            },
            "runtime_seconds": runtime_seconds,
        },
        "decision": {
            "primary_preserved": primary_preserved,
            "outcome": decision_outcome,
            "rule": (
                "supported iff BHPS-only H0 W2 rejects at alpha=0.05 and the H1 asymmetry "
                "direction is unchanged versus full BHPS"
            ),
            "paper_section": "P01-A section 6.2",
            "ari_descriptor": "stable" if regime_stable else "unstable",
        },
        "representation_provenance": representation_info,
        "output_provenance": {
            "result_path": str(output_path.relative_to(worktree)),
            "null_diagram_cache": str(cache_written),
            "launch_marker": str(marker_path),
            "partial_json_glob": str(worktree / "results/trajectory_tda_integration/stage1/.partial/bhps_nonoverlap_*"),
            "regeneration_command": (
                ".\\.venv\\Scripts\\python.exe -m trajectory_tda.analysis.panel.t126_bhps_nonoverlap "
                f"--date {args.date} --L {args.L} --B {args.B} --seed {args.seed} --n-jobs {args.n_jobs}"
            ),
            "no_overwrite": True,
        },
        "headline_result": core.convert_numpy(out),
    }
    validate_bhps_nonoverlap_payload(result)
    output_path.write_text(json.dumps(core.convert_numpy(result), indent=2), encoding="utf-8")
    LOGGER.info("Saved result: %s", output_path)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=datetime.now(UTC).date().isoformat())
    parser.add_argument("--proj-root", default=str(PROJ_ROOT))
    parser.add_argument("--worktree", default=str(WORKTREE))
    parser.add_argument("--L", type=int, default=core.DEFAULT_L)
    parser.add_argument("--B", type=int, default=core.DEFAULT_B)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--k-max", type=int, default=core.DEFAULT_K_MAX)
    parser.add_argument("--n-points", type=int, default=core.DEFAULT_N_POINTS)
    parser.add_argument("--n-null-pairs", type=int, default=core.DEFAULT_N_NULL_PAIRS)
    parser.add_argument("--n-jobs", type=int, default=4)
    args = parser.parse_args()
    if args.seed != SEED:
        raise ValueError(f"--seed must remain locked to {SEED}")
    if args.L != core.DEFAULT_L:
        raise ValueError(f"--L must remain locked to {core.DEFAULT_L}")
    if args.B < 1000:
        raise ValueError("--B must be >= 1000")
    if args.n_jobs < 1:
        raise ValueError("--n-jobs must be >= 1")
    return args


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    run(parse_args())


if __name__ == "__main__":
    main()
