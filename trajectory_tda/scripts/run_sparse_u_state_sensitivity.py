#!/usr/bin/env python3
# Research context: P01-A sparse unemployment-state reviewer sensitivity.
# Purpose: Collapse sparse U states two ways, re-embed, refit k=7 GMMs, and compare to locked regimes.
"""Run the sparse U-state six-state regime sensitivity.

Canonical USoc trajectories and locked 9-state labels are read from the main
project root. The date-suffixed result JSON is written under the worktree so it
can be committed with the producing script and contract bindings.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

PROJ_ROOT = Path(os.environ.get("TDL_PROJ_ROOT", r"C:\Users\steph\TDL"))
WORKTREE_ROOT = Path(__file__).resolve().parents[2]
SEQUENCES_REL = Path("results/trajectory_tda_integration/01_trajectories_sequences.json")
ANALYSIS_REL = Path("results/trajectory_tda_integration/05_analysis.json")
OUTPUT_REL_DIR = Path("results/panel_methodology/u_state_sensitivity")
PRE_REG_REL = Path("results/trajectory_tda_integration/stage1/pre_registrations_2026-06-06.json")
EXPECTED_N = 27280
SEED = 42
PCA_DIM = 20
ARI_THRESHOLD = 0.9
VARIANCE_THRESHOLD = 1e-12
STATE_ORDER_9 = ["EL", "EM", "EH", "UL", "UM", "UH", "IL", "IM", "IH"]
STATE_ORDER_6 = ["EL", "EM", "EH", "IL", "IM", "IH"]
COLLAPSE_MAPS = {
    "U_to_I": {"UL": "IL", "UM": "IM", "UH": "IH"},
    "U_to_E": {"UL": "EL", "UM": "EM", "UH": "EH"},
}
SCHEMA_VERSION = "stage1/sparse-u-state-six-state-sensitivity/v1"
TASK_NAME = "T1.25 sparse U-state 6-state sensitivity"
PRE_REGISTRATION = "2026-06-06 sparse U-state two-collapse pre-registration"


@dataclass(frozen=True)
class Inputs:
    trajectories: list[list[str]]
    locked_labels: NDArray[np.int_]
    sequences_path: Path
    analysis_path: Path


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_inputs(proj_root: Path = PROJ_ROOT) -> Inputs:
    sequences_path = proj_root / SEQUENCES_REL
    analysis_path = proj_root / ANALYSIS_REL
    if not sequences_path.exists():
        raise FileNotFoundError(f"canonical trajectories JSON not found: {sequences_path}")
    if not analysis_path.exists():
        raise FileNotFoundError(f"canonical analysis JSON not found: {analysis_path}")

    trajectories = _load_json(sequences_path)
    analysis = _load_json(analysis_path)
    if not isinstance(trajectories, list):
        raise TypeError("canonical trajectories JSON must be a list")
    labels = np.asarray(analysis.get("gmm_labels"), dtype=int)
    if len(trajectories) != EXPECTED_N or labels.shape != (EXPECTED_N,):
        raise ValueError(
            "canonical inputs must both cover exactly "
            f"N={EXPECTED_N}; got trajectories={len(trajectories)}, labels={labels.shape}"
        )
    return Inputs(
        trajectories=trajectories,
        locked_labels=labels,
        sequences_path=sequences_path,
        analysis_path=analysis_path,
    )


def collapse_trajectory(trajectory: list[str], recoding_map: dict[str, str]) -> list[str]:
    return [recoding_map.get(state, state) for state in trajectory]


def build_raw_ngram_features(
    trajectories: list[list[str]],
    state_order: list[str],
    recoding_map: dict[str, str] | None = None,
) -> NDArray[np.float64]:
    """Build normalized unigram+bigram frequencies for an arbitrary state order."""
    state_to_idx = {state: idx for idx, state in enumerate(state_order)}
    n_states = len(state_order)
    features = np.zeros((len(trajectories), n_states + n_states * n_states), dtype=np.float64)
    for row_idx, original in enumerate(trajectories):
        trajectory = collapse_trajectory(original, recoding_map or {})
        if not trajectory:
            continue
        unigram_counts = Counter(trajectory)
        for state, count in unigram_counts.items():
            idx = state_to_idx.get(state)
            if idx is not None:
                features[row_idx, idx] = count / len(trajectory)
        n_transitions = len(trajectory) - 1
        if n_transitions <= 0:
            continue
        bigram_counts = Counter(zip(trajectory, trajectory[1:], strict=False))
        offset = n_states
        for (src, dst), count in bigram_counts.items():
            src_idx = state_to_idx.get(src)
            dst_idx = state_to_idx.get(dst)
            if src_idx is not None and dst_idx is not None:
                features[row_idx, offset + src_idx * n_states + dst_idx] = count / n_transitions
    return features


def _effective_rank_from_eigenvalues(eigenvalues: NDArray[np.float64]) -> float:
    positive = eigenvalues[eigenvalues > 0]
    if positive.size == 0:
        return 0.0
    weights = positive / positive.sum()
    entropy = -float(np.sum(weights * np.log(weights)))
    return float(np.exp(entropy))


def dimensionality_diagnostics(raw_features: NDArray[np.float64], n_unigram_dims: int) -> dict[str, Any]:
    bigrams = raw_features[:, n_unigram_dims:]
    bigram_variances = np.var(bigrams, axis=0)
    scaled = StandardScaler().fit_transform(raw_features)
    cov = np.cov(scaled, rowvar=False)
    eigenvalues = np.linalg.eigvalsh(cov)
    eigenvalues = np.maximum(eigenvalues, 0.0)
    full_pca = PCA(n_components=min(raw_features.shape), svd_solver="full")
    full_pca.fit(scaled)
    cumulative = np.cumsum(full_pca.explained_variance_ratio_)
    return {
        "raw_dims": int(raw_features.shape[1]),
        "n_bigram_dims": int(bigrams.shape[1]),
        "variance_threshold": VARIANCE_THRESHOLD,
        "nontrivial_bigram_variance_dims": int(np.sum(bigram_variances > VARIANCE_THRESHOLD)),
        "effective_rank": _finite_float(_effective_rank_from_eigenvalues(eigenvalues)),
        "pca_explained_variance_20": _finite_float(cumulative[min(PCA_DIM, len(cumulative)) - 1]),
        "n_components_90pct": int(np.searchsorted(cumulative, 0.90) + 1),
        "n_components_95pct": int(np.searchsorted(cumulative, 0.95) + 1),
    }


def _finite_float(value: float | np.floating) -> float:
    out = float(value)
    if not np.isfinite(out):
        raise ValueError(f"non-finite metric encountered: {out}")
    return out


def _label_counts(labels: NDArray[np.int_]) -> dict[str, int]:
    return {str(int(label)): int(count) for label, count in sorted(Counter(labels.tolist()).items())}


def fit_variant(raw_features: NDArray[np.float64]) -> tuple[NDArray[np.int_], dict[str, Any]]:
    scaler = StandardScaler()
    scaled = scaler.fit_transform(raw_features)
    pca = PCA(n_components=PCA_DIM, svd_solver="full", random_state=SEED)
    embedding = pca.fit_transform(scaled)
    gmm = GaussianMixture(
        n_components=7,
        covariance_type="full",
        n_init=5,
        max_iter=200,
        random_state=SEED,
    )
    labels = gmm.fit_predict(embedding)
    info = {
        "pca_n_components": int(pca.n_components_),
        "pca_svd_solver": "full",
        "pca_random_state": SEED,
        "pca_explained_variance_20": _finite_float(np.sum(pca.explained_variance_ratio_)),
        "gmm_primary_k": int(gmm.n_components),
        "gmm_covariance_type": str(gmm.covariance_type),
        "gmm_n_init": int(gmm.n_init),
        "gmm_max_iter": int(gmm.max_iter),
        "gmm_random_state": SEED,
        "gmm_converged": bool(gmm.converged_),
        "gmm_n_iter": int(gmm.n_iter_),
        "gmm_lower_bound": _finite_float(gmm.lower_bound_),
        "gmm_bic": _finite_float(gmm.bic(embedding)),
        "gmm_label_counts": _label_counts(labels),
    }
    return labels, info


def git_head(worktree_root: Path = WORKTREE_ROOT) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=worktree_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def _decision_summary(variants: list[dict[str, Any]]) -> dict[str, Any]:
    all_ge = all(bool(v["ari_ge_0_9"]) for v in variants)
    any_below = any(not bool(v["ari_ge_0_9"]) for v in variants)
    if all_ge:
        direction = (
            "Both six-state collapse variants have ARI >= 0.9 against the locked 9-state labels; "
            "sparse U states do not appear to drive the locked regime structure. Retain U states "
            "on substantive grounds because unemployment remains conceptually distinct."
        )
        disclosure = "Report robustness to both U-state collapses and note that U states are retained substantively."
    else:
        direction = (
            "At least one six-state collapse variant has ARI below 0.9 against the locked 9-state labels; "
            "do not claim sparse U-state robustness without variant-specific disclosure."
        )
        disclosure = "Disclose the variant-specific sensitivity and avoid saying U-state sparsity is harmless."
    return {
        "all_variants_ari_ge_0_9": all_ge,
        "any_variant_ari_below_0_9": any_below,
        "paper_claim_direction": direction,
        "disclosure_required": disclosure,
    }


def build_result(inputs: Inputs, worktree_root: Path = WORKTREE_ROOT) -> dict[str, Any]:
    baseline_raw = build_raw_ngram_features(inputs.trajectories, STATE_ORDER_9)
    baseline = dimensionality_diagnostics(baseline_raw, len(STATE_ORDER_9))
    baseline["label_counts"] = _label_counts(inputs.locked_labels)

    variants: list[dict[str, Any]] = []
    for variant_name in ("U_to_I", "U_to_E"):
        recoding_map = COLLAPSE_MAPS[variant_name]
        raw_features = build_raw_ngram_features(inputs.trajectories, STATE_ORDER_6, recoding_map)
        diagnostics = dimensionality_diagnostics(raw_features, len(STATE_ORDER_6))
        labels, fit_info = fit_variant(raw_features)
        ari = _finite_float(adjusted_rand_score(inputs.locked_labels, labels))
        ari_ge = bool(ari >= ARI_THRESHOLD)
        variant = {
            "variant": variant_name,
            "recoding_map": recoding_map,
            **diagnostics,
            **fit_info,
            "ari_vs_9_state": ari,
            "ari_ge_0_9": ari_ge,
            "interpretation": (
                f"{variant_name} {'meets' if ari_ge else 'does not meet'} the pre-registered "
                f"ARI >= {ARI_THRESHOLD} stability threshold."
            ),
        }
        variants.append(variant)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "task": TASK_NAME,
        "pre_registration": PRE_REGISTRATION,
        "inputs": {
            "canonical_sequences_json": str(inputs.sequences_path),
            "canonical_analysis_json": str(inputs.analysis_path),
            "baseline_gmm_labels_source": f"{inputs.analysis_path}[gmm_labels]",
            "n_trajectories": EXPECTED_N,
            "row_order_basis": "Canonical checkpoint list index: 01_trajectories_sequences.json rows aligned to 05_analysis.json[gmm_labels].",
            "git_head": git_head(worktree_root),
        },
        "params": {
            "collapse_variants": ["U_to_I", "U_to_E"],
            "state_order_9": STATE_ORDER_9,
            "state_order_6": STATE_ORDER_6,
            "U_to_I_map": COLLAPSE_MAPS["U_to_I"],
            "U_to_E_map": COLLAPSE_MAPS["U_to_E"],
            "include_unigrams": True,
            "include_bigrams": True,
            "raw_dims_6": 42,
            "pca_dim": PCA_DIM,
            "pca_svd_solver": "full",
            "standardize": True,
            "gmm_primary_k": 7,
            "gmm_covariance_type": "full",
            "gmm_n_init": 5,
            "gmm_max_iter": 200,
            "seed": SEED,
            "ari_stability_threshold": ARI_THRESHOLD,
        },
        "baseline_9_state": baseline,
        "variants": variants,
        "decision_summary": _decision_summary(variants),
    }


def write_result(result: dict[str, Any], worktree_root: Path, run_date: str) -> Path:
    output_dir = worktree_root / OUTPUT_REL_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"six_state_gmm_{run_date}.json"
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing result JSON: {output_path}")
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run sparse U-state six-state GMM sensitivity.")
    parser.add_argument("--proj-root", type=Path, default=PROJ_ROOT)
    parser.add_argument("--worktree-root", type=Path, default=WORKTREE_ROOT)
    parser.add_argument("--run-date", default="2026-06-06")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    inputs = load_inputs(args.proj_root)
    result = build_result(inputs, args.worktree_root)
    output_path = write_result(result, args.worktree_root, args.run_date)
    print(output_path)


if __name__ == "__main__":
    main()
