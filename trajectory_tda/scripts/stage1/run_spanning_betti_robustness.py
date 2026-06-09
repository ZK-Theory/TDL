"""Spanning-vs-newcomer Betti-0 robustness check for T1.9.

Produces the date-suffixed detail and consolidated JSON artifacts for the
epsilon-star robustness check. The comparison uses a single full-checkpoint
PCA coordinate system, then filters rows into spanning and USoc-only newcomer
sub-populations. It never fits PCA separately by group or epsilon.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from trajectory_tda.scripts.stage1 import _battery_core as core


SCHEMA_VERSION = "stage1/spanning-betti-robustness/v1"
TASK_NAME = "T1.9 spanning Betti AUC + W2 + epsilon-star robustness"
PRE_REGISTRATION = "2026-05-13 M3 epsilon-star Robustness Check"
EPS_STARS = [0.54, 0.65, 0.7, 0.8]
EPS_STAR_LOCKED = 0.54
STATISTICS = ["single_eps_ratio", "auc_ratio", "w2_matched"]
DEFAULT_SEED = 42
DEFAULT_MATCHED_N = 8000
OUTPUT_REL_DIR = Path("results/trajectory_tda_spanning/knee_robustness")
FULL_CHECKPOINT_REL_DIR = Path("results/trajectory_tda_full")
KNEE_SOURCE = (
    "trajectory_tda.scripts.run_zigzag_sensitivity.detect_eps_star_knee; "
    "results/trajectory_tda_zigzag/sensitivity_2d/knee_analysis.json"
)

logger = logging.getLogger(__name__)


def _as_float_list(values: object) -> list[float] | None:
    if not isinstance(values, list):
        return None
    try:
        return [float(v) for v in values]
    except (TypeError, ValueError):
        return None


def _contains_forbidden_key(value: object, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_forbidden_key(v, key) for v in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_key(v, key) for v in value)
    return False


def validate_spanning_betti_robustness_payload(payload: dict[str, Any]) -> list[str]:
    """Return schema-contract validation errors for a consolidated payload."""
    errors: list[str] = []
    required = [
        "schema_version",
        "generated_at",
        "task",
        "pre_registration",
        "inputs",
        "params",
        "results",
        "decision",
    ]
    for key in required:
        if key not in payload:
            errors.append(f"missing required key: {key}")

    if _contains_forbidden_key(payload, "per_call_pca"):
        errors.append("forbidden key present: per_call_pca")

    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")
    if payload.get("task") != TASK_NAME:
        errors.append(f"task must be {TASK_NAME!r}")
    if "2026-05-13" not in str(payload.get("pre_registration", "")):
        errors.append("pre_registration must reference 2026-05-13")

    inputs = payload.get("inputs")
    if not isinstance(inputs, dict):
        errors.append("inputs must be a dict")
    else:
        for key in ("spanning_source", "newcomer_source", "knee_algorithm_source", "git_head"):
            if not inputs.get(key):
                errors.append(f"inputs.{key} is required")

    params = payload.get("params")
    if not isinstance(params, dict):
        errors.append("params must be a dict")
    else:
        eps_stars = _as_float_list(params.get("eps_stars"))
        if eps_stars != EPS_STARS:
            errors.append(f"params.eps_stars must equal {EPS_STARS}")
        if params.get("eps_star_locked") != EPS_STAR_LOCKED:
            errors.append(f"params.eps_star_locked must equal {EPS_STAR_LOCKED}")
        if params.get("seed") != DEFAULT_SEED:
            errors.append(f"params.seed must equal {DEFAULT_SEED}")
        if params.get("statistics") != STATISTICS:
            errors.append(f"params.statistics must equal {STATISTICS}")

    results = payload.get("results")
    if not isinstance(results, list):
        errors.append("results must be a list")
        results = []
    eps_seen: list[float] = []
    for idx, row in enumerate(results):
        if not isinstance(row, dict):
            errors.append(f"results[{idx}] must be a dict")
            continue
        try:
            eps = float(row["eps_star"])
            eps_seen.append(eps)
        except (KeyError, TypeError, ValueError):
            errors.append(f"results[{idx}].eps_star is required and must be numeric")
        for key in STATISTICS:
            if key not in row:
                errors.append(f"results[{idx}].{key} is required")
                continue
            if not isinstance(row[key], (int, float)) or not math.isfinite(float(row[key])):
                errors.append(f"results[{idx}].{key} must be a finite number")
        if isinstance(row.get("w2_matched"), (int, float)) and float(row["w2_matched"]) < 0:
            errors.append(f"results[{idx}].w2_matched must be non-negative")
        if not isinstance(row.get("newcomers_gt_spanning"), bool):
            errors.append(f"results[{idx}].newcomers_gt_spanning must be bool")

    if sorted(eps_seen) != sorted(EPS_STARS) or len(eps_seen) != len(set(eps_seen)):
        errors.append("results must contain exactly one entry per locked epsilon-star")

    decision = payload.get("decision")
    if not isinstance(decision, dict):
        errors.append("decision must be a dict")
    else:
        consistent = decision.get("consistent")
        outcome = decision.get("outcome")
        if not isinstance(consistent, bool):
            errors.append("decision.consistent must be bool")
        expected = "robust" if consistent is True else "divergent" if consistent is False else None
        if outcome not in {"robust", "divergent"}:
            errors.append("decision.outcome must be 'robust' or 'divergent'")
        elif expected is not None and outcome != expected:
            errors.append("decision.outcome must be 'robust' iff decision.consistent is true")

    return errors


def dispatches_spanning_betti_robustness_json(path: Path) -> bool:
    """Return True for consolidated T1.9 JSONs covered by the dispatch contract."""
    rel = path.as_posix()
    return rel.startswith(OUTPUT_REL_DIR.as_posix() + "/") and path.name.startswith("spanning_AUC_W2_") and path.suffix == ".json"


def _git_head(repo_root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def _sha256_ints(values: NDArray[np.integer[Any]]) -> str:
    arr = np.asarray(values, dtype=np.int64)
    return hashlib.sha256(arr.tobytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json_no_overwrite(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing result: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(core.convert_numpy(payload), f, indent=2)
        f.write("\n")


def _load_or_rebuild_full_embedding(
    worktree_checkpoint: Path,
    proj_checkpoint: Path,
) -> tuple[NDArray[np.float64], dict[str, Any]]:
    """Load full embeddings from PROJ_ROOT, rebuilding the gitignored cache if absent."""
    embedding_path = proj_checkpoint / "embeddings.npy"
    metadata_path = worktree_checkpoint / "01_trajectories.json"
    sequences_path = worktree_checkpoint / "01_trajectories_sequences.json"
    embedding_info_path = worktree_checkpoint / "02_embedding.json"

    expected = _load_json(embedding_info_path)
    expected_shape = tuple(expected["shape"])
    if embedding_path.exists():
        embeddings = np.load(embedding_path)
        if tuple(embeddings.shape) != expected_shape:
            raise ValueError(
                f"Full embedding cache shape {embeddings.shape} does not match {expected_shape}: {embedding_path}"
            )
        return embeddings, {
            "status": "reused_existing_proj_root_cache",
            "embedding_cache": str(embedding_path),
            "metadata_source": str(metadata_path),
            "regeneration_command": (
                "uv run python trajectory_tda/scripts/build_full_checkpoint.py "
                "--data-dir trajectory_tda/data --checkpoint results/trajectory_tda_full "
                "--min-years 10 --max-gap 2 --pca-dim 20"
            ),
        }

    from trajectory_tda.embedding.ngram_embed import ngram_embed
    from trajectory_tda.utils.model_io import save_model

    with sequences_path.open("r", encoding="utf-8") as f:
        trajectories = json.load(f)

    info = expected["info"]
    embeddings, embed_info = ngram_embed(
        trajectories,
        include_bigrams=info.get("n_bigram_dims", 0) > 0,
        include_trigrams=info.get("n_trigram_dims", 0) > 0,
        tfidf=bool(info.get("tfidf", False)),
        pca_dim=int(info.get("final_dims", 20)),
        umap_dim=None,
    )
    if tuple(embeddings.shape) != expected_shape:
        raise ValueError(f"Rebuilt full embeddings shape {embeddings.shape} does not match {expected_shape}")

    proj_checkpoint.mkdir(parents=True, exist_ok=True)
    np.save(embedding_path, embeddings)
    fitted_models = embed_info.get("fitted_models", {})
    if fitted_models.get("scaler") is not None:
        save_model(fitted_models["scaler"], proj_checkpoint / "02_scaler.joblib")
    if fitted_models.get("reducer") is not None:
        save_model(fitted_models["reducer"], proj_checkpoint / "02_pca.joblib")

    return embeddings, {
        "status": "rebuilt_proj_root_cache_from_committed_sequences",
        "embedding_cache": str(embedding_path),
        "metadata_source": str(metadata_path),
        "sequences_source": str(sequences_path),
        "model_cache_paths": {
            "scaler": str(proj_checkpoint / "02_scaler.joblib"),
            "pca": str(proj_checkpoint / "02_pca.joblib"),
        },
        "regeneration_command": (
            "uv run python trajectory_tda/scripts/build_full_checkpoint.py "
            "--data-dir trajectory_tda/data --checkpoint results/trajectory_tda_full "
            "--min-years 10 --max-gap 2 --pca-dim 20"
        ),
    }


def _group_indices(metadata: dict[str, Any], survey_era: str) -> NDArray[np.int64]:
    eras = metadata["survey_era"]
    return np.asarray([int(k) for k, value in eras.items() if value == survey_era], dtype=np.int64)


def _sample_indices(indices: NDArray[np.int64], matched_n: int, seed: int, offset: int) -> NDArray[np.int64]:
    if matched_n > len(indices):
        raise ValueError(f"Cannot sample {matched_n} rows from a group of size {len(indices)}")
    rng = np.random.default_rng(seed + offset)
    sampled = rng.choice(indices, size=matched_n, replace=False)
    return np.sort(sampled.astype(np.int64))


def _h0_diagram(points: NDArray[np.float64]) -> NDArray[np.float64]:
    import ripser

    result = ripser.ripser(points, maxdim=0)
    return np.asarray(result["dgms"][0], dtype=np.float64)


def _finite_deaths(dgm: NDArray[np.float64]) -> NDArray[np.float64]:
    if dgm.size == 0:
        return np.empty(0, dtype=np.float64)
    finite = dgm[np.isfinite(dgm).all(axis=1)]
    return np.asarray(finite[:, 1], dtype=np.float64)


def _betti0_at_eps(deaths: NDArray[np.float64], eps: float) -> int:
    return int(1 + np.sum(deaths > eps))


def _betti0_auc(deaths: NDArray[np.float64], eps_max: float) -> float:
    return float(eps_max + np.minimum(deaths, eps_max).sum())


def _w2_h0(dgm_a: NDArray[np.float64], dgm_b: NDArray[np.float64]) -> float:
    from gudhi.wasserstein import wasserstein_distance

    finite_a = dgm_a[np.isfinite(dgm_a).all(axis=1)] if dgm_a.size else np.empty((0, 2))
    finite_b = dgm_b[np.isfinite(dgm_b).all(axis=1)] if dgm_b.size else np.empty((0, 2))
    return float(wasserstein_distance(finite_a, finite_b, order=2, internal_p=2))


def _eps_tag(eps: float) -> str:
    return f"{int(round(eps * 100)):03d}"


def build_payload(
    *,
    repo_root: Path,
    matched_n: int,
    seed: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    metadata_path = repo_root / FULL_CHECKPOINT_REL_DIR / "01_trajectories.json"
    metadata_payload = _load_json(metadata_path)
    metadata = metadata_payload["metadata"]

    embeddings, cache_info = _load_or_rebuild_full_embedding(
        worktree_checkpoint=repo_root / FULL_CHECKPOINT_REL_DIR,
        proj_checkpoint=core.proj_root() / FULL_CHECKPOINT_REL_DIR,
    )

    spanning_all = _group_indices(metadata, "spanning")
    newcomer_all = _group_indices(metadata, "usoc_only")
    actual_n = min(matched_n, len(spanning_all), len(newcomer_all))
    spanning_idx = _sample_indices(spanning_all, actual_n, seed, offset=101)
    newcomer_idx = _sample_indices(newcomer_all, actual_n, seed, offset=202)

    logger.info("Matched sample size: %d", actual_n)
    logger.info("Computing H0 diagram for spanning sample")
    spanning_dgm = _h0_diagram(embeddings[spanning_idx])
    logger.info("Computing H0 diagram for newcomer sample")
    newcomer_dgm = _h0_diagram(embeddings[newcomer_idx])

    spanning_deaths = _finite_deaths(spanning_dgm)
    newcomer_deaths = _finite_deaths(newcomer_dgm)
    logger.info("Computing W2(D0 newcomer, D0 spanning)")
    w2 = _w2_h0(newcomer_dgm, spanning_dgm)

    rows: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    for eps in EPS_STARS:
        span_betti = _betti0_at_eps(spanning_deaths, eps)
        new_betti = _betti0_at_eps(newcomer_deaths, eps)
        span_auc = _betti0_auc(spanning_deaths, eps)
        new_auc = _betti0_auc(newcomer_deaths, eps)
        single_ratio = float(new_betti / span_betti)
        auc_ratio = float(new_auc / span_auc)
        supports = {
            "single_eps_ratio": bool(single_ratio > 1.0),
            "auc_ratio": bool(auc_ratio > 1.0),
            "w2_matched": bool(w2 > 0.0),
        }
        row = {
            "eps_star": eps,
            "single_eps_ratio": single_ratio,
            "auc_ratio": auc_ratio,
            "w2_matched": w2,
            "newcomers_gt_spanning": bool(single_ratio > 1.0),
            "all_statistics_support_headline": bool(all(supports.values())),
            "statistic_support": supports,
            "single_eps": {
                "spanning_beta0": span_betti,
                "newcomer_beta0": new_betti,
            },
            "auc": {
                "filtration_interval": [0.0, eps],
                "spanning_auc_beta0": span_auc,
                "newcomer_auc_beta0": new_auc,
            },
        }
        rows.append(row)
        details.append(
            {
                "schema_version": SCHEMA_VERSION,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "task": TASK_NAME,
                "eps_star": eps,
                "params": {
                    "seed": seed,
                    "matched_sample_size": actual_n,
                    "statistics": STATISTICS,
                    "homology_dimension": "H0",
                    "w2_order": 2,
                    "w2_internal_p": 2,
                },
                "sampling": {
                    "rule": (
                        "independent deterministic simple random samples without replacement "
                        "from spanning and USoc-only newcomer rows; sampled row ids sorted before PH"
                    ),
                    "seed": seed,
                    "spanning_population_n": int(len(spanning_all)),
                    "newcomer_population_n": int(len(newcomer_all)),
                    "spanning_sample_sha256": _sha256_ints(spanning_idx),
                    "newcomer_sample_sha256": _sha256_ints(newcomer_idx),
                },
                "result": row,
            }
        )

    decision_consistent = bool(all(row["all_statistics_support_headline"] for row in rows))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task": TASK_NAME,
        "pre_registration": PRE_REGISTRATION,
        "inputs": {
            "spanning_source": "results/trajectory_tda_full/01_trajectories.json::metadata.survey_era == 'spanning'",
            "newcomer_source": "results/trajectory_tda_full/01_trajectories.json::metadata.survey_era == 'usoc_only'",
            "knee_algorithm_source": KNEE_SOURCE,
            "git_head": _git_head(repo_root),
            "full_embedding_cache": cache_info,
        },
        "params": {
            "eps_stars": EPS_STARS,
            "eps_star_locked": EPS_STAR_LOCKED,
            "seed": seed,
            "statistics": STATISTICS,
            "homology_dimension": "H0",
            "matched_sample_size": actual_n,
            "requested_matched_sample_size": matched_n,
            "matching_rule": (
                "Use matched_n = min(requested_matched_n, n_spanning, n_usoc_only); "
                "draw independent simple random samples without replacement with seed offsets "
                "101 (spanning) and 202 (newcomers)."
            ),
            "frozen_loadings": True,
            "pca_scope": "single full-checkpoint PCA basis; no per-group or per-epsilon PCA refit",
            "w2_order": 2,
            "w2_internal_p": 2,
            "w2_ground_metric": "l2",
            "auc_filtration": "[0, eps_star]",
        },
        "results": rows,
        "decision": {
            "consistent": decision_consistent,
            "outcome": "robust" if decision_consistent else "divergent",
            "rule": (
                "consistent is true iff every epsilon-star has single_eps_ratio > 1, "
                "auc_ratio > 1, and W2(D0_newcomer, D0_spanning) > 0."
            ),
        },
    }
    errors = validate_spanning_betti_robustness_payload(payload)
    if errors:
        raise ValueError("Consolidated payload failed validation:\n  " + "\n  ".join(errors))
    return payload, details


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matched-n", type=int, default=DEFAULT_MATCHED_N)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    if args.seed != DEFAULT_SEED:
        raise ValueError(f"T1.9 seed is locked to {DEFAULT_SEED}")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    repo_root = Path.cwd()
    today = date.today().isoformat()
    output_dir = repo_root / OUTPUT_REL_DIR

    payload, details = build_payload(repo_root=repo_root, matched_n=args.matched_n, seed=args.seed)
    for detail in details:
        eps = float(detail["eps_star"])
        _write_json_no_overwrite(
            output_dir / f"spanning_betti_eps_{_eps_tag(eps)}_{today}.json",
            detail,
        )
    consolidated_path = output_dir / f"spanning_AUC_W2_{today}.json"
    _write_json_no_overwrite(consolidated_path, payload)
    print(f"Consolidated JSON: {consolidated_path}")


if __name__ == "__main__":
    main()
