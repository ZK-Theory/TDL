#!/usr/bin/env python3
# Research context: Stage-1 auxiliary diagnostics for trajectory TDA reviewer checks.
# Purpose: Generate Mapper threshold and KDE sub-level H0 outputs, and provide
#   a resumable Markov-2 alpha-sweep runner with explicit frozen-loadings provenance.
"""Stage-1 auxiliary diagnostic runners.

Canonical inputs are read from the main project tree while committed
result JSONs are written under the active worktree. The functions here are
kept importable so contract binding tests can validate output payloads without
re-running the long stochastic computations.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from sklearn.metrics import adjusted_rand_score
from sklearn.neighbors import KernelDensity, NearestNeighbors
from sklearn.preprocessing import StandardScaler

PROJ_ROOT = Path(os.environ.get("TDL_PROJ_ROOT", r"C:\Users\steph\TDL"))
WORKTREE_ROOT = Path(__file__).resolve().parents[2]
USOC_REL = Path("results/trajectory_tda_integration")
BHPS_REL = Path("results/trajectory_tda_bhps")
PREREG_REL = Path("results/trajectory_tda_integration/stage1/pre_registrations_2026-06-07.json")
MAPPER_GRAPH_REL = Path("results/trajectory_tda_mapper/06_mapper_graph.json")
MAPPER_OUTPUT_REL = Path("results/trajectory_tda_integration/mapper_threshold")
KDE_OUTPUT_REL = Path("results/trajectory_tda_integration/density_topology")
MARKOV_OUTPUT_REL = Path("results/trajectory_tda_integration/post_audit")
SEED = 42
USOC_N = 27280
MAPPER_THRESHOLDS = [1.0, 1.5, 2.0]
MARKOV_ALPHAS = [0, 0.5, 1, 5]
MARKOV_DATASETS = ["usoc", "bhps"]
PRE_REGISTRATION = "2026-06-07 Stage-1 auxiliary-diagnostics pre-registration"


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def git_head(worktree_root: Path = WORKTREE_ROOT) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=worktree_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_no_overwrite(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing result JSON: {path}")
    path.write_text(json.dumps(_jsonable(payload), indent=2) + "\n", encoding="utf-8")
    return path


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


@dataclass(frozen=True)
class CanonicalData:
    embeddings: NDArray[np.float64]
    gmm_labels: NDArray[np.int64]
    trajectories: list[list[str]]
    root: Path


def load_canonical_dataset(dataset: str, proj_root: Path = PROJ_ROOT) -> CanonicalData:
    if dataset == "usoc":
        root = proj_root / USOC_REL
    elif dataset == "bhps":
        root = proj_root / BHPS_REL
    else:
        raise ValueError(f"unknown dataset: {dataset}")
    embeddings = np.load(root / "embeddings.npy")
    trajectories = _read_json(root / "01_trajectories_sequences.json")
    analysis = _read_json(root / "05_analysis.json")
    labels = np.asarray(analysis["gmm_labels"], dtype=np.int64)
    if len(embeddings) != len(trajectories):
        raise ValueError(f"{dataset}: embeddings and trajectories are not row-aligned")
    if len(labels) != len(embeddings):
        raise ValueError(f"{dataset}: GMM labels are not row-aligned with embeddings")
    return CanonicalData(embeddings=embeddings, gmm_labels=labels, trajectories=trajectories, root=root)


def benjamini_hochberg(p_values: NDArray[np.float64]) -> tuple[NDArray[np.float64], NDArray[np.bool_]]:
    p = np.asarray(p_values, dtype=np.float64)
    if p.ndim != 1:
        raise ValueError("p_values must be one-dimensional")
    if p.size == 0:
        return np.array([], dtype=np.float64), np.array([], dtype=bool)
    if np.any((p < 0) | (p > 1) | ~np.isfinite(p)):
        raise ValueError("p_values must be finite values in [0, 1]")
    order = np.argsort(p)
    ranked = p[order]
    m = p.size
    adjusted_sorted = ranked * m / np.arange(1, m + 1)
    adjusted_sorted = np.minimum.accumulate(adjusted_sorted[::-1])[::-1]
    adjusted_sorted = np.clip(adjusted_sorted, 0.0, 1.0)
    adjusted = np.empty_like(adjusted_sorted)
    adjusted[order] = adjusted_sorted
    return adjusted, adjusted <= 0.05


def _dominant_node_rows(
    graph: dict[str, Any],
    labels: NDArray[np.int64],
    outcome: NDArray[np.float64],
) -> list[dict[str, Any]]:
    nodes = graph.get("nodes", {})
    regime_stats: dict[int, dict[str, float]] = {}
    for regime in sorted(int(r) for r in np.unique(labels)):
        vals = outcome[labels == regime]
        regime_stats[regime] = {
            "mean": float(np.mean(vals)),
            "std": float(np.std(vals)) if len(vals) > 1 else 0.0,
        }

    rows: list[dict[str, Any]] = []
    for node_id in sorted(nodes):
        members = np.asarray(nodes[node_id], dtype=np.int64)
        if members.size == 0:
            continue
        counts = Counter(int(r) for r in labels[members])
        regime, regime_n = counts.most_common(1)[0]
        purity = regime_n / members.size
        if purity < 0.5:
            continue
        node_mean = float(np.mean(outcome[members]))
        r_stats = regime_stats[regime]
        z_score = 0.0 if r_stats["std"] <= 0 else abs(node_mean - r_stats["mean"]) / r_stats["std"]
        rows.append(
            {
                "node_id": str(node_id),
                "members": members,
                "dominant_regime": int(regime),
                "dominant_regime_purity": float(purity),
                "node_size": int(members.size),
                "node_mean": node_mean,
                "regime_mean": r_stats["mean"],
                "z_score": float(z_score),
            }
        )
    return rows


def _mapper_empirical_pvalues(
    rows: list[dict[str, Any]],
    labels: NDArray[np.int64],
    outcome: NDArray[np.float64],
    b_permutations: int,
    seed: int,
) -> NDArray[np.float64]:
    rng = np.random.default_rng(seed)
    exceed = np.ones(len(rows), dtype=np.int64)
    by_regime = {int(r): np.where(labels == r)[0] for r in np.unique(labels)}
    observed = np.asarray([row["z_score"] for row in rows], dtype=np.float64)

    for _ in range(b_permutations):
        shuffled = outcome.copy()
        for idx in by_regime.values():
            shuffled[idx] = shuffled[idx][rng.permutation(len(idx))]
        for i, row in enumerate(rows):
            members = row["members"]
            regime = int(row["dominant_regime"])
            vals = shuffled[labels == regime]
            regime_std = float(np.std(vals)) if len(vals) > 1 else 0.0
            if regime_std <= 0:
                z_perm = 0.0
            else:
                node_mean = float(np.mean(shuffled[members]))
                z_perm = abs(node_mean - float(np.mean(vals))) / regime_std
            if z_perm >= observed[i]:
                exceed[i] += 1
    return exceed / (b_permutations + 1)


def build_mapper_threshold_payload(
    proj_root: Path = PROJ_ROOT,
    worktree_root: Path = WORKTREE_ROOT,
    b_permutations: int = 1000,
    seed: int = SEED,
) -> dict[str, Any]:
    data = load_canonical_dataset("usoc", proj_root)
    graph_path = worktree_root / MAPPER_GRAPH_REL
    graph = _read_json(graph_path)
    pc1 = data.embeddings[:, 0].astype(np.float64)
    rows = _dominant_node_rows(graph, data.gmm_labels, pc1)
    p_values = _mapper_empirical_pvalues(rows, data.gmm_labels, pc1, b_permutations, seed)
    q_values, bh_flags = benjamini_hochberg(p_values)

    node_records = []
    for row, raw_p, q, flag in zip(rows, p_values, q_values, bh_flags, strict=True):
        node_records.append(
            {
                "node_id": row["node_id"],
                "dominant_regime": row["dominant_regime"],
                "dominant_regime_purity": row["dominant_regime_purity"],
                "node_size": row["node_size"],
                "node_mean": row["node_mean"],
                "regime_mean": row["regime_mean"],
                "z_score": row["z_score"],
                "empirical_p_value": float(raw_p),
                "bh_q_value": float(q),
                "bh_significant": bool(flag),
            }
        )

    results = []
    high_sets = []
    for threshold in MAPPER_THRESHOLDS:
        selected = [node for node in node_records if abs(float(node["z_score"])) > threshold]
        selected_bh = [node for node in selected if bool(node["bh_significant"])]
        high_sets.append({node["node_id"] for node in selected_bh})
        results.append(
            {
                "z_threshold": float(threshold),
                "n_subregime_nodes": len(selected),
                "B": int(b_permutations),
                "n_bh_significant_nodes": len(selected_bh),
                "node_ids": [node["node_id"] for node in selected],
                "bh_significant_node_ids": [node["node_id"] for node in selected_bh],
            }
        )

    high_confidence = sorted(set.intersection(*high_sets)) if high_sets else []
    return {
        "schema_version": "stage1/mapper-threshold-sweep/v1",
        "generated_at": _now_iso(),
        "task": "T1.10 Mapper threshold sensitivity sweep",
        "pre_registration": PRE_REGISTRATION,
        "inputs": {
            "mapper_graph_source": str(graph_path),
            "canonical_embedding_source": str(data.root / "embeddings.npy"),
            "baseline_gmm_labels_source": str(data.root / "05_analysis.json[gmm_labels]"),
            "n_trajectories": int(len(data.embeddings)),
            "git_head": git_head(worktree_root),
        },
        "params": {
            "z_thresholds": MAPPER_THRESHOLDS,
            "B": int(b_permutations),
            "seed": int(seed),
            "fdr_method": "benjamini-hochberg",
            "outcome": "embedding_pc1",
            "null": "within-regime PC1 shuffle on fixed Mapper graph",
        },
        "results": results,
        "high_confidence_nodes": high_confidence,
        "per_node_z_scores": node_records,
    }


def _silverman_bandwidth(x: NDArray[np.float64]) -> float:
    n, d = x.shape
    scale = float(np.mean(np.std(x, axis=0, ddof=1)))
    factor = (n * (d + 2) / 4.0) ** (-1.0 / (d + 4))
    return float(max(scale * factor, 1e-6))


def _density_gradient_partition(
    x: NDArray[np.float64],
    log_density: NDArray[np.float64],
    k: int,
    seed: int,
) -> tuple[NDArray[np.int64], dict[str, Any]]:
    nn = NearestNeighbors(n_neighbors=min(31, len(x)), algorithm="auto")
    nn.fit(x)
    _, neigh = nn.kneighbors(x, return_distance=True)
    parent = np.arange(len(x), dtype=np.int64)
    for i in range(len(x)):
        candidates = neigh[i][log_density[neigh[i]] > log_density[i]]
        if len(candidates) > 0:
            parent[i] = int(candidates[np.argmax(log_density[candidates])])

    def find_root(i: int) -> int:
        path = []
        while parent[i] != i:
            path.append(i)
            i = int(parent[i])
        for j in path:
            parent[j] = i
        return i

    roots = np.array([find_root(i) for i in range(len(x))], dtype=np.int64)
    unique_roots, counts = np.unique(roots, return_counts=True)
    if len(unique_roots) <= k:
        root_to_label = {int(root): idx for idx, root in enumerate(unique_roots)}
        labels = np.array([root_to_label[int(root)] for root in roots], dtype=np.int64)
        return labels, {"initial_modes": int(len(unique_roots)), "merge_method": "none_needed"}

    root_density = np.array([log_density[root] for root in unique_roots])
    candidate_order = np.lexsort((-counts, -root_density))[::-1]
    top_roots = unique_roots[candidate_order[:k]]
    centers = x[top_roots]
    root_points = x[unique_roots]
    nearest = NearestNeighbors(n_neighbors=1).fit(centers)
    _, root_label = nearest.kneighbors(root_points, return_distance=True)
    merged_root_label = {int(root): int(lbl[0]) for root, lbl in zip(unique_roots, root_label, strict=True)}
    labels = np.array([merged_root_label[int(root)] for root in roots], dtype=np.int64)
    return labels, {
        "initial_modes": int(len(unique_roots)),
        "tree_cut_k": int(k),
        "merge_method": "merge density-gradient basins to nearest of top-k density peaks",
        "top_peak_indices": [int(v) for v in top_roots],
    }


def _cubical_h0_summary(
    kde: KernelDensity,
    x_scaled: NDArray[np.float64],
    grid_resolution: int,
) -> dict[str, Any]:
    import gudhi as gd

    x0 = x_scaled[:, 0]
    x1 = x_scaled[:, 1]
    q0 = np.quantile(x0, [0.01, 0.99])
    q1 = np.quantile(x1, [0.01, 0.99])
    gx = np.linspace(float(q0[0]), float(q0[1]), grid_resolution)
    gy = np.linspace(float(q1[0]), float(q1[1]), grid_resolution)
    rest = np.median(x_scaled[:, 2:], axis=0) if x_scaled.shape[1] > 2 else np.empty(0)
    grid = np.zeros((grid_resolution * grid_resolution, x_scaled.shape[1]), dtype=np.float64)
    cursor = 0
    for a in gx:
        for b in gy:
            if x_scaled.shape[1] > 2:
                grid[cursor] = np.concatenate(([a, b], rest))
            else:
                grid[cursor] = [a, b]
            cursor += 1
    neg_log_density = -kde.score_samples(grid).reshape(grid_resolution, grid_resolution)
    complex_ = gd.CubicalComplex(top_dimensional_cells=neg_log_density)
    complex_.persistence()
    intervals = np.asarray(complex_.persistence_intervals_in_dimension(0), dtype=np.float64)
    finite = intervals[np.isfinite(intervals).all(axis=1)] if intervals.size else np.empty((0, 2))
    persistence = finite[:, 1] - finite[:, 0] if finite.size else np.array([], dtype=np.float64)
    return {
        "grid_projection": "first_two_standardized_pca_axes_with_remaining_axes_at_median",
        "grid_resolution": int(grid_resolution),
        "n_h0_features": int(len(intervals)),
        "n_finite_h0_features": int(len(finite)),
        "max_finite_persistence": float(np.max(persistence)) if len(persistence) else 0.0,
        "median_finite_persistence": float(np.median(persistence)) if len(persistence) else 0.0,
    }


def build_kde_sublevel_payload(
    proj_root: Path = PROJ_ROOT,
    worktree_root: Path = WORKTREE_ROOT,
    grid_resolution: int = 50,
    kde_sample_size: int = 5000,
    seed: int = SEED,
) -> dict[str, Any]:
    data = load_canonical_dataset("usoc", proj_root)
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(data.embeddings.astype(np.float64))
    rng = np.random.default_rng(seed)
    sample_size = min(kde_sample_size, len(x_scaled))
    sample_idx = np.sort(rng.choice(len(x_scaled), size=sample_size, replace=False))
    x_fit = x_scaled[sample_idx]
    bandwidth = _silverman_bandwidth(x_fit)
    kde = KernelDensity(kernel="gaussian", bandwidth=bandwidth, algorithm="ball_tree")
    kde.fit(x_fit)
    log_density = kde.score_samples(x_scaled)
    partition, tree_info = _density_gradient_partition(x_scaled, log_density, k=7, seed=seed)
    ari = float(adjusted_rand_score(data.gmm_labels, partition))
    h0_summary = _cubical_h0_summary(kde, x_scaled, grid_resolution)
    label_counts = {str(int(k)): int(v) for k, v in sorted(Counter(partition.tolist()).items())}
    return {
        "schema_version": "stage1/kde-sublevel-h0/v1",
        "generated_at": _now_iso(),
        "task": "T1.11 KDE sub-level-set H0",
        "pre_registration": PRE_REGISTRATION,
        "inputs": {
            "canonical_embedding_source": str(data.root / "embeddings.npy"),
            "baseline_gmm_labels_source": str(data.root / "05_analysis.json[gmm_labels]"),
            "n_trajectories": int(len(data.embeddings)),
            "git_head": git_head(worktree_root),
        },
        "params": {
            "bandwidth_rule": "silverman-on-standardized-pca20-kde-fit-sample",
            "bandwidth": float(bandwidth),
            "grid_resolution": int(grid_resolution),
            "k_prominence": 7,
            "seed": int(seed),
            "frozen_loadings": True,
            "kde_fit_sample_size": int(sample_size),
            "tree_cut_method": tree_info["merge_method"],
        },
        "results": {
            "n_h0_features": int(h0_summary["n_h0_features"]),
            "n_finite_h0_features": int(h0_summary["n_finite_h0_features"]),
            "tree_cut_k": 7,
            "ari_vs_gmm": ari,
            "substantial_recovery": bool(ari > 0.3),
            "partition_label_counts": label_counts,
            "density_tree_initial_modes": int(tree_info["initial_modes"]),
            "h0_persistence_summary": h0_summary,
        },
    }


def validate_markov2_alpha_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ["schema_version", "generated_at", "task", "pre_registration", "inputs", "params", "results", "stability"]
    errors.extend(f"missing required key: {key}" for key in required if key not in payload)
    if "per_call_pca" in payload:
        errors.append("forbidden key present: per_call_pca")
    if errors:
        return errors
    params = payload["params"]
    if params.get("alphas") != MARKOV_ALPHAS or params.get("L") != 5000 or params.get("seed") != 42:
        errors.append("params must pin alphas, L=5000, and seed=42")
    if params.get("B", 0) < 1000:
        errors.append("params.B must be >= 1000")
    if params.get("datasets") != MARKOV_DATASETS:
        errors.append("params.datasets must be exactly ['usoc', 'bhps']")
    if params.get("frozen_loadings") is not True:
        errors.append("params.frozen_loadings must be true")
    if params.get("p_value_formula") != "(r+1)/(B+1)":
        errors.append("params.p_value_formula mismatch")
    cells = {(row.get("alpha"), row.get("dataset")) for row in payload.get("results", [])}
    expected = {(alpha, dataset) for alpha in MARKOV_ALPHAS for dataset in MARKOV_DATASETS}
    if cells != expected or len(payload.get("results", [])) != 8:
        errors.append("results must contain all 8 alpha x dataset cells")
    for row in payload.get("results", []):
        if row.get("alpha") not in MARKOV_ALPHAS or row.get("dataset") not in MARKOV_DATASETS:
            errors.append("result cell has invalid alpha or dataset")
        p_value = row.get("p_value")
        w2 = row.get("w2_obs_null")
        if not isinstance(p_value, (int, float)) or not 0 <= p_value <= 1:
            errors.append("result p_value must be in [0, 1]")
        if not isinstance(w2, (int, float)) or w2 < 0:
            errors.append("result w2_obs_null must be non-negative")
    stability = payload["stability"]
    if stability.get("conclusion_stable") is True and stability.get("canonical_alpha") != 1:
        errors.append("stable conclusion must keep canonical_alpha == 1")
    return errors


def validate_mapper_threshold_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ["schema_version", "generated_at", "task", "pre_registration", "inputs", "params", "results", "high_confidence_nodes"]
    errors.extend(f"missing required key: {key}" for key in required if key not in payload)
    if "uncorrected_only" in payload:
        errors.append("forbidden key present: uncorrected_only")
    if errors:
        return errors
    params = payload["params"]
    if params.get("z_thresholds") != MAPPER_THRESHOLDS or params.get("fdr_method") != "benjamini-hochberg":
        errors.append("params must pin thresholds and BH FDR method")
    if params.get("B", 0) < 1000 or params.get("seed") != 42:
        errors.append("params must pin B>=1000 and seed=42")
    rows = payload.get("results", [])
    if len(rows) != 3 or {row.get("z_threshold") for row in rows} != set(MAPPER_THRESHOLDS):
        errors.append("results must contain one entry per threshold")
    for row in rows:
        n_sub = row.get("n_subregime_nodes")
        n_bh = row.get("n_bh_significant_nodes")
        if not isinstance(n_sub, int) or n_sub < 0:
            errors.append("n_subregime_nodes must be a non-negative int")
        if not isinstance(n_bh, int) or n_bh < 0:
            errors.append("n_bh_significant_nodes must be a non-negative int")
        if isinstance(n_sub, int) and isinstance(n_bh, int) and n_bh > n_sub:
            errors.append("n_bh_significant_nodes cannot exceed n_subregime_nodes")
        if row.get("B", 0) < 1000:
            errors.append("each result B must be >= 1000")
    return errors


def validate_kde_sublevel_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ["schema_version", "generated_at", "task", "pre_registration", "inputs", "params", "results"]
    errors.extend(f"missing required key: {key}" for key in required if key not in payload)
    if "per_call_pca" in payload:
        errors.append("forbidden key present: per_call_pca")
    if errors:
        return errors
    params = payload["params"]
    results = payload["results"]
    if params.get("k_prominence") != 7 or params.get("seed") != 42 or params.get("frozen_loadings") is not True:
        errors.append("params must pin k_prominence=7, seed=42, frozen_loadings=true")
    if not isinstance(params.get("bandwidth_rule"), str) or not params.get("bandwidth_rule"):
        errors.append("params.bandwidth_rule must be a non-empty string")
    if "grid_resolution" not in params:
        errors.append("params.grid_resolution is required")
    if results.get("tree_cut_k") != 7:
        errors.append("results.tree_cut_k must equal 7")
    n_features = results.get("n_h0_features")
    if not isinstance(n_features, int) or n_features < 0:
        errors.append("results.n_h0_features must be a non-negative int")
    ari = results.get("ari_vs_gmm")
    if not isinstance(ari, (int, float)) or not -1 <= ari <= 1:
        errors.append("results.ari_vs_gmm must be in [-1, 1]")
    elif results.get("substantial_recovery") != (ari > 0.3):
        errors.append("results.substantial_recovery disagrees with ari_vs_gmm > 0.3")
    return errors


def write_mapper_threshold(run_date: str, proj_root: Path, worktree_root: Path) -> Path:
    payload = build_mapper_threshold_payload(proj_root, worktree_root)
    errors = validate_mapper_threshold_payload(payload)
    if errors:
        raise ValueError("mapper payload invalid: " + "; ".join(errors))
    return _write_json_no_overwrite(
        worktree_root / MAPPER_OUTPUT_REL / f"sub_regime_thresh_sweep_{run_date}.json",
        payload,
    )


def write_kde_sublevel(run_date: str, proj_root: Path, worktree_root: Path) -> Path:
    payload = build_kde_sublevel_payload(proj_root, worktree_root)
    errors = validate_kde_sublevel_payload(payload)
    if errors:
        raise ValueError("kde payload invalid: " + "; ".join(errors))
    return _write_json_no_overwrite(
        worktree_root / KDE_OUTPUT_REL / f"sublevel_kde_h0_{run_date}.json",
        payload,
    )


def markov2_walltime_estimate() -> dict[str, Any]:
    historical_seconds = 5139.5
    historical_b = 100
    target_b = 1000
    cells = len(MARKOV_ALPHAS) * len(MARKOV_DATASETS)
    single_cell_hours = historical_seconds * target_b / historical_b / 3600
    return {
        "basis": "historical USoc Markov-2 W2 L5000 B100 run took 5139.5 seconds",
        "estimated_single_cell_hours": single_cell_hours,
        "estimated_8_cell_serial_hours": single_cell_hours * cells,
        "parallelism_required": ">=4 workers with per-cell checkpoints before full launch",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage-1 auxiliary diagnostics.")
    parser.add_argument("command", choices=["mapper", "kde", "estimate-markov2"])
    parser.add_argument("--proj-root", type=Path, default=PROJ_ROOT)
    parser.add_argument("--worktree-root", type=Path, default=WORKTREE_ROOT)
    parser.add_argument("--run-date", default=datetime.now(UTC).date().isoformat())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start = time.time()
    if args.command == "mapper":
        print(write_mapper_threshold(args.run_date, args.proj_root, args.worktree_root))
    elif args.command == "kde":
        print(write_kde_sublevel(args.run_date, args.proj_root, args.worktree_root))
    elif args.command == "estimate-markov2":
        print(json.dumps(markov2_walltime_estimate(), indent=2))
    print(f"elapsed_seconds={time.time() - start:.3f}")


if __name__ == "__main__":
    main()