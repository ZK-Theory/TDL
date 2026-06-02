#!/usr/bin/env python3
# Research context: T1.33 family-of-origin topology signature.
# Purpose: Compute local persistence features, sibling-pair coherence,
#   comparator arms, and provenance-locked JSON outputs.
"""Run the family-of-origin topology signature analysis.

The pipeline uses the raw 90-D unigram+bigram trajectory embedding, computes
per-individual local Vietoris-Rips features on kNN sub-clouds, then evaluates
family-of-origin coherence against a cluster-size-preserving shuffle null.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import warnings
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from numpy.typing import NDArray
from ripser import ripser
from scipy.spatial.distance import pdist
from sklearn.neighbors import NearestNeighbors

from trajectory_tda.embedding.ngram_embed import (
    _compute_unigrams,
    ngram_embed,
)


LOGGER = logging.getLogger(__name__)

warnings.filterwarnings(
    "ignore",
    message="The input point cloud has more columns than rows; did you mean to transpose?",
    category=UserWarning,
    module="ripser.ripser",
)

PROJ_ROOT = Path(r"C:\Users\steph\TDL")
WORKTREE = Path(__file__).resolve().parents[2]
RESULTS_REL = Path("results/trajectory_tda_integration/foo_topology")
TRAJECTORIES_REL = Path("results/trajectory_tda_integration/01_trajectories_sequences.json")
METADATA_REL = Path("results/trajectory_tda_integration/01_trajectories.json")
FOO_REL = Path("data/derived/foo_clusters_2026-05-06.csv")

FEATURE_NAMES = [
    "max_h0_persistence",
    "total_h1_persistence",
    "landscape_integral_k1",
]
K_GRID = [10, 20, 50]
K_PRIMARY = 20
PRE_REGISTRATION_DATE = "2026-05-25"
SCHEMA_FEATURES = "foo-topology/per-individual-local-features/v1"
SCHEMA_SIBLING = "foo-topology/sibling-pair-permutation/v1"
SCHEMA_COMPARISON = "foo-topology/topology-distinctiveness-comparison/v1"


@dataclass(frozen=True)
class FooInputs:
    """Inputs aligned to the analytical sample row order."""

    trajectories: list[list[str]]
    pidps: NDArray[np.int64]
    foo_clusters: NDArray[np.int64]
    embeddings: NDArray[np.float64]
    c2_features: NDArray[np.float64]


@dataclass(frozen=True)
class SiblingAnalysis:
    """Sibling-pair permutation and ICC result for one feature space."""

    observed_mean: float
    n_sibling_pairs: int
    null_samples: NDArray[np.float64]
    null_mean: float
    null_std: float
    permutation_pvalue: float
    effect_size_ratio: float
    per_feature_icc: dict[str, dict[str, float | int]]


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest for a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_inputs(proj_root: Path = PROJ_ROOT) -> FooInputs:
    """Load trajectories, pidp metadata, FOO clusters, and raw features."""
    trajectories_path = proj_root / TRAJECTORIES_REL
    metadata_path = proj_root / METADATA_REL
    foo_path = proj_root / FOO_REL

    trajectories = json.loads(trajectories_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    n = int(metadata["n"])
    if len(trajectories) != n:
        raise ValueError(f"Trajectory count {len(trajectories)} does not match metadata n={n}")
    pidps = np.array([int(metadata["metadata"]["pidp"][str(i)]) for i in range(n)], dtype=np.int64)

    embeddings, info = ngram_embed(
        trajectories,
        include_bigrams=True,
        include_trigrams=False,
        tfidf=False,
        pca_dim=None,
        umap_dim=None,
        standardize=False,
        random_state=42,
    )
    embeddings = np.asarray(embeddings, dtype=np.float64)
    if embeddings.shape != (n, 90) or info["method"] != "raw":
        raise ValueError(f"Expected raw (N, 90) embedding, got {embeddings.shape}, {info['method']}")

    c2_features = build_summary_trajectory_features(trajectories)
    foo_clusters = load_foo_clusters(pidps, foo_path)
    return FooInputs(
        trajectories=trajectories,
        pidps=pidps,
        foo_clusters=foo_clusters,
        embeddings=embeddings,
        c2_features=c2_features,
    )


def load_foo_clusters(pidps: NDArray[np.int64], foo_path: Path) -> NDArray[np.int64]:
    """Join analytical-sample pidps to FOO cluster IDs.

    Missing pidps, if any, receive deterministic singleton cluster IDs outside
    the observed positive cluster range.
    """
    foo = pd.read_csv(foo_path, usecols=["pidp", "foo_cluster"])
    mapping = dict(zip(foo["pidp"].astype(np.int64), foo["foo_cluster"].astype(np.int64), strict=False))
    max_cluster = int(foo["foo_cluster"].max()) if not foo.empty else 0
    clusters = np.empty(len(pidps), dtype=np.int64)
    next_singleton = max_cluster + 1
    missing = 0
    for i, pidp in enumerate(pidps):
        cluster = mapping.get(int(pidp))
        if cluster is None:
            cluster = next_singleton
            next_singleton += 1
            missing += 1
        clusters[i] = int(cluster)
    if missing:
        LOGGER.warning("Assigned %d missing pidps to singleton FOO clusters", missing)
    return clusters


def build_summary_trajectory_features(trajectories: list[list[str]]) -> NDArray[np.float64]:
    """Build C2: nine occupancy proportions plus state-change count."""
    rows: list[NDArray[np.float64]] = []
    for traj in trajectories:
        unigram = _compute_unigrams(traj)
        transitions = float(sum(1 for a, b in zip(traj, traj[1:], strict=False) if a != b))
        rows.append(np.concatenate([unigram, np.array([transitions], dtype=np.float64)]))
    return np.vstack(rows).astype(np.float64)


def cluster_size_partition(clusters: NDArray[np.int64]) -> tuple[int, ...]:
    """Return the sorted cluster-size partition for a cluster assignment."""
    _, counts = np.unique(clusters, return_counts=True)
    return tuple(sorted(int(x) for x in counts))


def constrained_shuffle_clusters(
    observed_clusters: NDArray[np.int64], rng: np.random.Generator
) -> NDArray[np.int64]:
    """Shuffle cluster IDs across individuals while preserving cluster sizes."""
    return observed_clusters[rng.permutation(len(observed_clusters))]


def exact_knn_indices(
    embeddings: NDArray[np.float64], index: int, k: int
) -> NDArray[np.int64]:
    """Exact deterministic kNN for tests and small arrays."""
    deltas = embeddings - embeddings[index]
    distances = np.einsum("ij,ij->i", deltas, deltas)
    order = np.lexsort((np.arange(len(embeddings)), distances))
    order = order[order != index]
    return order[:k].astype(np.int64)


def _unique_embedding_groups(
    embeddings: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.int64], list[NDArray[np.int64]]]:
    unique_embeddings, inverse = np.unique(embeddings, axis=0, return_inverse=True)
    groups: list[list[int]] = [[] for _ in range(len(unique_embeddings))]
    for idx, group_id in enumerate(inverse):
        groups[int(group_id)].append(idx)
    arrays = [np.array(group, dtype=np.int64) for group in groups]
    return unique_embeddings.astype(np.float64), inverse.astype(np.int64), arrays


def _candidate_neighbour_rows(
    unique_embeddings: NDArray[np.float64],
    groups: list[NDArray[np.int64]],
    max_k: int,
    min_unique_candidates: int = 256,
) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
    n_unique = unique_embeddings.shape[0]
    n_query = min(n_unique, max(max_k + 1, min_unique_candidates))
    model = NearestNeighbors(metric="euclidean", algorithm="brute", n_jobs=-1)
    model.fit(unique_embeddings)

    while True:
        distances, neighbours = model.kneighbors(unique_embeddings, n_neighbors=n_query)
        insufficient = False
        for u in range(n_unique):
            available = sum(len(groups[int(v)]) for v in neighbours[u]) - 1
            if available < max_k:
                insufficient = True
                break
        if not insufficient or n_query == n_unique:
            return distances.astype(np.float64), neighbours.astype(np.int64)
        n_query = min(n_unique, n_query * 2)


def deterministic_neighbour_indices_by_group(
    embeddings: NDArray[np.float64], max_k: int
) -> tuple[NDArray[np.float64], NDArray[np.int64], list[NDArray[np.int64]], list[NDArray[np.int64]]]:
    """Build deterministic neighbour indices once per unique embedding row."""
    unique_embeddings, inverse, groups = _unique_embedding_groups(embeddings)
    distances, neighbours = _candidate_neighbour_rows(unique_embeddings, groups, max_k)
    all_neighbours: list[NDArray[np.int64]] = []
    for u in range(len(groups)):
        representative = int(groups[u][0])
        expanded: list[tuple[float, int]] = []
        for distance, unique_idx in zip(distances[u], neighbours[u], strict=True):
            for individual_idx in groups[int(unique_idx)]:
                if int(individual_idx) != representative:
                    expanded.append((float(distance), int(individual_idx)))
        expanded.sort(key=lambda item: (item[0], item[1]))
        if len(expanded) < max_k:
            raise ValueError(f"Only {len(expanded)} neighbours available for unique row {u}")
        all_neighbours.append(np.array([idx for _, idx in expanded[:max_k]], dtype=np.int64))
    return unique_embeddings, inverse, groups, all_neighbours


def _landscape_integral_first(
    h1_diagram: NDArray[np.float64], n_points: int
) -> float:
    finite = h1_diagram[np.isfinite(h1_diagram).all(axis=1)] if h1_diagram.size else h1_diagram
    finite = finite[finite[:, 1] > finite[:, 0]] if finite.size else finite
    if finite.size == 0:
        return 0.0
    x_min = float(np.min(finite[:, 0]))
    x_max = float(np.max(finite[:, 1]))
    if x_max <= x_min:
        return 0.0
    grid = np.linspace(x_min, x_max, n_points, dtype=np.float64)
    tents = np.minimum(grid[None, :] - finite[:, 0:1], finite[:, 1:2] - grid[None, :])
    landscape = np.maximum(np.max(tents, axis=0), 0.0)
    return float(np.trapezoid(landscape, grid))


def local_persistence_features(
    subcloud: NDArray[np.float64], landscape_n_points: int = 256
) -> NDArray[np.float64]:
    """Extract max H0, total H1, and first-landscape integral from a sub-cloud."""
    diagrams = ripser(subcloud, maxdim=1)["dgms"]
    h0 = diagrams[0]
    h0_finite = h0[np.isfinite(h0).all(axis=1)] if h0.size else h0
    h0_persistence = h0_finite[:, 1] - h0_finite[:, 0] if h0_finite.size else np.array([])
    max_h0 = float(np.max(h0_persistence)) if h0_persistence.size else 0.0

    h1 = diagrams[1] if len(diagrams) > 1 else np.empty((0, 2), dtype=np.float64)
    h1_finite = h1[np.isfinite(h1).all(axis=1)] if h1.size else h1
    h1_persistence = h1_finite[:, 1] - h1_finite[:, 0] if h1_finite.size else np.array([])
    h1_persistence = h1_persistence[h1_persistence > 0.0]
    total_h1 = float(np.sum(h1_persistence)) if h1_persistence.size else 0.0
    landscape = _landscape_integral_first(h1, landscape_n_points)
    return np.array([max_h0, total_h1, landscape], dtype=np.float64)


def _compute_unique_group_features(
    unique_idx: int,
    embeddings: NDArray[np.float64],
    groups: list[NDArray[np.int64]],
    neighbours_by_group: list[NDArray[np.int64]],
    k_grid: list[int],
    landscape_n_points: int,
) -> dict[int, NDArray[np.float64]]:
    representative = int(groups[unique_idx][0])
    neighbours = neighbours_by_group[unique_idx]
    result: dict[int, NDArray[np.float64]] = {}
    for k in k_grid:
        subcloud_idx = np.concatenate([[representative], neighbours[:k]])
        result[k] = local_persistence_features(embeddings[subcloud_idx], landscape_n_points)
    return result


def compute_per_individual_local_features(
    embeddings: NDArray[np.float64],
    k_grid: list[int] | None = None,
    landscape_n_points: int = 256,
    n_jobs: int = 1,
) -> dict[int, NDArray[np.float64]]:
    """Compute local PH features for every individual and every k."""
    if k_grid is None:
        k_grid = list(K_GRID)
    max_k = max(k_grid)
    _, inverse, groups, neighbours_by_group = deterministic_neighbour_indices_by_group(embeddings, max_k)
    LOGGER.info("Computing local PH for %d unique embedding rows", len(groups))
    unique_results = Parallel(n_jobs=n_jobs, verbose=10 if n_jobs != 1 else 0)(
        delayed(_compute_unique_group_features)(
            u, embeddings, groups, neighbours_by_group, k_grid, landscape_n_points
        )
        for u in range(len(groups))
    )
    features_by_k = {k: np.zeros((embeddings.shape[0], 3), dtype=np.float64) for k in k_grid}
    for u, per_k in enumerate(unique_results):
        members = np.flatnonzero(inverse == u)
        for k in k_grid:
            features_by_k[k][members] = per_k[k]
    for k, features in features_by_k.items():
        if np.any(features < -1e-12):
            raise ValueError(f"Negative local PH feature found for k={k}")
        features[features < 0] = 0.0
    return features_by_k


def _cluster_indices(clusters: NDArray[np.int64]) -> list[NDArray[np.int64]]:
    groups: dict[int, list[int]] = defaultdict(list)
    for idx, cluster in enumerate(clusters):
        groups[int(cluster)].append(idx)
    return [np.array(v, dtype=np.int64) for _, v in sorted(groups.items())]


def mean_within_pair_distance(
    features: NDArray[np.float64], clusters: NDArray[np.int64]
) -> tuple[float, int]:
    """Mean Euclidean distance over unordered pairs inside each cluster."""
    total = 0.0
    n_pairs = 0
    for idx in _cluster_indices(clusters):
        if len(idx) < 2:
            continue
        distances = pdist(features[idx], metric="euclidean")
        total += float(np.sum(distances))
        n_pairs += int(distances.size)
    if n_pairs == 0:
        raise ValueError("No within-cluster pairs available")
    return total / n_pairs, n_pairs


def _partition_position_blocks(clusters: NDArray[np.int64]) -> dict[int, NDArray[np.int64]]:
    sizes = [len(idx) for idx in _cluster_indices(clusters)]
    blocks: dict[int, list[NDArray[np.int64]]] = defaultdict(list)
    offset = 0
    for size in sizes:
        if size > 1:
            blocks[size].append(np.arange(offset, offset + size, dtype=np.int64))
        offset += size
    return {size: np.vstack(rows) for size, rows in blocks.items()}


def _partition_mean_distance(
    features: NDArray[np.float64],
    permuted_indices: NDArray[np.int64],
    position_blocks: dict[int, NDArray[np.int64]],
) -> float:
    total = 0.0
    n_pairs = 0
    for size, positions in position_blocks.items():
        block_indices = permuted_indices[positions]
        values = features[block_indices]
        for a, b in combinations(range(size), 2):
            diff = values[:, a, :] - values[:, b, :]
            total += float(np.sqrt(np.einsum("ij,ij->i", diff, diff)).sum())
            n_pairs += values.shape[0]
    return total / n_pairs


def constrained_shuffle_null_distribution(
    features: NDArray[np.float64],
    clusters: NDArray[np.int64],
    B: int,
    seed: int,
) -> NDArray[np.float64]:
    """Generate mean-distance samples under the constrained shuffle null."""
    rng = np.random.default_rng(seed)
    position_blocks = _partition_position_blocks(clusters)
    samples = np.empty(B, dtype=np.float64)
    n = features.shape[0]
    for b in range(B):
        permuted = rng.permutation(n)
        samples[b] = _partition_mean_distance(features, permuted, position_blocks)
    return samples


def _cluster_feature_stats(
    features: NDArray[np.float64], clusters: NDArray[np.int64]
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    indices = _cluster_indices(clusters)
    means = np.vstack([features[idx].mean(axis=0) for idx in indices])
    within_vars = np.full_like(means, np.nan, dtype=np.float64)
    for row, idx in enumerate(indices):
        if len(idx) > 1:
            within_vars[row] = np.var(features[idx], axis=0, ddof=1)
    return means, within_vars


def _icc_from_cluster_stats(
    means: NDArray[np.float64], within_vars: NDArray[np.float64]
) -> NDArray[np.float64]:
    between = np.var(means, axis=0, ddof=1)
    within = np.nanmean(within_vars, axis=0)
    within = np.where(np.isnan(within), 0.0, within)
    denom = between + within
    icc = np.divide(between, denom, out=np.zeros_like(between), where=denom > 0)
    return np.clip(icc, 0.0, 1.0)


def cluster_bootstrap_icc(
    features: NDArray[np.float64],
    clusters: NDArray[np.int64],
    feature_names: list[str],
    B_boot: int,
    seed: int,
) -> dict[str, dict[str, float | int]]:
    """Compute one-way ICC and cluster-bootstrap percentile CIs."""
    means, within_vars = _cluster_feature_stats(features, clusters)
    point = _icc_from_cluster_stats(means, within_vars)
    rng = np.random.default_rng(seed)
    boot = np.empty((B_boot, features.shape[1]), dtype=np.float64)
    n_clusters = means.shape[0]
    for b in range(B_boot):
        sampled = rng.integers(0, n_clusters, size=n_clusters)
        boot[b] = _icc_from_cluster_stats(means[sampled], within_vars[sampled])
    lower = np.percentile(boot, 2.5, axis=0)
    upper = np.percentile(boot, 97.5, axis=0)
    return {
        name: {
            "point_estimate": float(point[i]),
            "bootstrap_ci_lower": float(lower[i]),
            "bootstrap_ci_upper": float(upper[i]),
            "bootstrap_B": int(B_boot),
        }
        for i, name in enumerate(feature_names)
    }


def run_sibling_analysis(
    features: NDArray[np.float64],
    clusters: NDArray[np.int64],
    feature_names: list[str],
    B: int,
    seed: int,
    icc_bootstrap_B: int,
) -> SiblingAnalysis:
    """Run the sibling-pair coherence test and per-feature ICCs."""
    observed_mean, n_pairs = mean_within_pair_distance(features, clusters)
    null_samples = constrained_shuffle_null_distribution(features, clusters, B=B, seed=seed)
    r = int(np.sum(null_samples <= observed_mean))
    pvalue = (r + 1) / (B + 1)
    null_mean = float(np.mean(null_samples))
    effect_size_ratio = float(observed_mean / null_mean) if null_mean > 0 else float("inf")
    icc = cluster_bootstrap_icc(
        features=features,
        clusters=clusters,
        feature_names=feature_names,
        B_boot=icc_bootstrap_B,
        seed=seed,
    )
    return SiblingAnalysis(
        observed_mean=float(observed_mean),
        n_sibling_pairs=n_pairs,
        null_samples=null_samples,
        null_mean=null_mean,
        null_std=float(np.std(null_samples, ddof=1)),
        permutation_pvalue=float(pvalue),
        effect_size_ratio=effect_size_ratio,
        per_feature_icc=icc,
    )


def _icc_summary(analysis: SiblingAnalysis, feature_dim: int) -> dict[str, float | int | bool]:
    icc_values = [float(v["point_estimate"]) for v in analysis.per_feature_icc.values()]
    n_above_zero = sum(1 for v in analysis.per_feature_icc.values() if float(v["bootstrap_ci_lower"]) > 0.0)
    return {
        "feature_dim": int(feature_dim),
        "permutation_pvalue": analysis.permutation_pvalue,
        "effect_size_ratio": analysis.effect_size_ratio,
        "n_icc_features": int(feature_dim),
        "n_icc_ci_above_zero": int(n_above_zero),
        "max_icc": float(max(icc_values)) if icc_values else 0.0,
        "mean_icc": float(np.mean(icc_values)) if icc_values else 0.0,
        "rejects": bool(analysis.permutation_pvalue < 0.05),
    }


def distinctiveness_verdict(arms: dict[str, dict[str, float | int | bool]]) -> str:
    """Apply the pre-registered primary and distinctiveness rules."""
    topo = arms["topological"]
    support = bool(topo["rejects"]) and int(topo["n_icc_ci_above_zero"]) >= 1
    if not support:
        return "NO_FOO_SIGNAL"
    topo_closeness = abs(float(topo["effect_size_ratio"]) - 1.0)
    for key in ("c1_bigram_coordinate", "c2_summary_trajectory"):
        arm = arms[key]
        materially_weaker = (
            not bool(arm["rejects"])
            or int(arm["n_icc_ci_above_zero"]) == 0
            or abs(float(arm["effect_size_ratio"]) - 1.0) < topo_closeness
        )
        if materially_weaker:
            return "TOPOLOGY_DISTINCTIVE"
    return "SIGNAL_NOT_TOPOLOGY_SPECIFIC"


def _json_float(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def write_json_no_overwrite(path: Path, payload: dict[str, Any]) -> Path:
    """Write JSON, allowing only byte-identical idempotent reruns."""
    text = json.dumps(payload, indent=2, sort_keys=True, default=_json_float) + "\n"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == text:
            LOGGER.info("Existing output is byte-identical: %s", path)
            return path
        raise FileExistsError(f"Refusing to overwrite existing non-identical result: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_npy_no_overwrite(path: Path, array: NDArray[np.float64]) -> Path:
    """Write an array, allowing only numerically identical idempotent reruns."""
    if path.exists():
        existing = np.load(path)
        if existing.shape == array.shape and np.array_equal(existing, array):
            LOGGER.info("Existing array output is identical: %s", path)
            return path
        raise FileExistsError(f"Refusing to overwrite existing non-identical array: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, array)
    return path


def build_feature_payload(
    pidps: NDArray[np.int64],
    features_by_k: dict[int, NDArray[np.float64]],
    params: dict[str, Any],
    input_provenance: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    """Assemble the per-individual local-features JSON payload."""
    features_per_k: dict[str, list[dict[str, float | int]]] = {}
    for k in K_GRID:
        rows = []
        for pidp, row in zip(pidps, features_by_k[k], strict=True):
            rows.append(
                {
                    "individual_id": int(pidp),
                    "max_h0_persistence": float(row[0]),
                    "total_h1_persistence": float(row[1]),
                    "landscape_integral_k1": float(row[2]),
                }
            )
        features_per_k[f"k_{k}"] = rows
    return {
        "schema_version": SCHEMA_FEATURES,
        "generated_at": generated_at,
        "task": "T1.33 per-individual local PH features",
        "params": params,
        "features_per_k": features_per_k,
        "input_provenance": input_provenance,
    }


def build_sibling_payload(
    analysis: SiblingAnalysis,
    params: dict[str, Any],
    input_provenance: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    """Assemble the sibling-pair permutation JSON payload."""
    samples = analysis.null_samples
    return {
        "schema_version": SCHEMA_SIBLING,
        "generated_at": generated_at,
        "task": "T1.33 sibling-pair permutation test",
        "pre_registration": PRE_REGISTRATION_DATE,
        "params": params,
        "observed": {
            "mean_within_pair_distance": analysis.observed_mean,
            "n_sibling_pairs": analysis.n_sibling_pairs,
        },
        "null_distribution": {
            "mean_within_pair_distance_samples": samples.tolist(),
            "mean": analysis.null_mean,
            "std": analysis.null_std,
            "min": float(np.min(samples)),
            "max": float(np.max(samples)),
        },
        "permutation_pvalue": analysis.permutation_pvalue,
        "effect_size_ratio": analysis.effect_size_ratio,
        "per_feature_icc": analysis.per_feature_icc,
        "input_provenance": input_provenance,
    }


def build_comparison_payload(
    topological: SiblingAnalysis,
    c1: SiblingAnalysis,
    c2: SiblingAnalysis,
    params: dict[str, Any],
    input_provenance: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    """Assemble the topology-distinctiveness comparison JSON payload."""
    arms = {
        "topological": _icc_summary(topological, 3),
        "c1_bigram_coordinate": _icc_summary(c1, 90),
        "c2_summary_trajectory": _icc_summary(c2, 10),
    }
    return {
        "schema_version": SCHEMA_COMPARISON,
        "generated_at": generated_at,
        "task": "T1.33 topology-distinctiveness comparison",
        "pre_registration": PRE_REGISTRATION_DATE,
        "params": params,
        "arms": arms,
        "distinctiveness_verdict": distinctiveness_verdict(arms),
        "input_provenance": input_provenance,
    }


def _common_params(seed: int, B: int, icc_bootstrap_B: int, n: int) -> dict[str, Any]:
    return {
        "B": int(B),
        "seed": int(seed),
        "icc_bootstrap_B": int(icc_bootstrap_B),
        "k_primary": K_PRIMARY,
        "n_individuals": int(n),
        "pvalue_formula": "(r+1)/(B+1)",
        "null_type": "constrained-shuffle",
        "distance_in_feature_space": "euclidean",
    }


def run_pipeline(args: argparse.Namespace) -> dict[str, Path]:
    """Execute the full analysis and write the three result JSONs."""
    proj_root = Path(args.proj_root)
    worktree = Path(args.worktree)
    output_dir = worktree / RESULTS_REL
    proj_output_dir = proj_root / RESULTS_REL
    output_date = args.output_date or date.today().isoformat()
    generated_at = f"{output_date}T00:00:00"

    inputs = load_inputs(proj_root)
    n = len(inputs.pidps)
    trajectories_path = proj_root / TRAJECTORIES_REL
    metadata_path = proj_root / METADATA_REL
    foo_path = proj_root / FOO_REL
    raw_embedding_path = proj_output_dir / f"raw_bigram_embedding_{output_date}.npy"
    write_npy_no_overwrite(raw_embedding_path, inputs.embeddings)
    embedding_trace = sha256_file(raw_embedding_path)

    feature_path = output_dir / f"per_individual_local_features_{output_date}.json"
    sibling_path = output_dir / f"sibling_pair_permutation_{output_date}.json"
    comparison_path = output_dir / f"topology_distinctiveness_comparison_{output_date}.json"

    features_by_k = compute_per_individual_local_features(
        inputs.embeddings,
        k_grid=K_GRID,
        landscape_n_points=args.landscape_n_points,
        n_jobs=args.n_jobs,
    )

    feature_params = {
        "k_grid": K_GRID,
        "k_primary": K_PRIMARY,
        "seed": int(args.seed),
        "n_individuals": n,
        "landscape_n_points": int(args.landscape_n_points),
        "distance_metric": "euclidean",
        "filtration": "vietoris-rips",
        "max_dim": 1,
        "input_embeddings_path": str(raw_embedding_path),
        "input_trajectories_path": str(trajectories_path),
        "input_foo_clusters_path": str(foo_path),
        "embedding_dim": 90,
    }
    feature_payload = build_feature_payload(
        inputs.pidps,
        features_by_k,
        feature_params,
        {
            "embeddings_sha256": embedding_trace,
            "trajectories_sha256": sha256_file(trajectories_path),
            "metadata_sha256": sha256_file(metadata_path),
            "foo_clusters_sha256": sha256_file(foo_path),
            "embeddings_shape": [int(x) for x in inputs.embeddings.shape],
        },
        generated_at,
    )
    write_json_no_overwrite(feature_path, feature_payload)

    common_params = _common_params(args.seed, args.B, args.icc_bootstrap_B, n)
    sibling_params = {
        **common_params,
        "n_clusters_observed": int(len(np.unique(inputs.foo_clusters))),
        "pvalue_null_draws": int(args.B),
    }
    topo_features = features_by_k[K_PRIMARY]
    topological = run_sibling_analysis(
        topo_features,
        inputs.foo_clusters,
        FEATURE_NAMES,
        B=args.B,
        seed=args.seed,
        icc_bootstrap_B=args.icc_bootstrap_B,
    )
    sibling_payload = build_sibling_payload(
        topological,
        sibling_params,
        {
            "per_individual_features_path": str(feature_path),
            "per_individual_features_sha256": sha256_file(feature_path),
            "foo_clusters_path": str(foo_path),
            "foo_clusters_sha256": sha256_file(foo_path),
        },
        generated_at,
    )
    write_json_no_overwrite(sibling_path, sibling_payload)

    c1 = run_sibling_analysis(
        inputs.embeddings,
        inputs.foo_clusters,
        [f"bigram_coordinate_{i:02d}" for i in range(inputs.embeddings.shape[1])],
        B=args.B,
        seed=args.seed,
        icc_bootstrap_B=args.icc_bootstrap_B,
    )
    c2 = run_sibling_analysis(
        inputs.c2_features,
        inputs.foo_clusters,
        [f"state_occupancy_{i:02d}" for i in range(9)] + ["n_transitions"],
        B=args.B,
        seed=args.seed,
        icc_bootstrap_B=args.icc_bootstrap_B,
    )
    comparison_payload = build_comparison_payload(
        topological,
        c1,
        c2,
        common_params,
        {
            "sibling_pair_permutation_path": str(sibling_path),
            "sibling_pair_permutation_sha256": sha256_file(sibling_path),
            "foo_clusters_path": str(foo_path),
            "foo_clusters_sha256": sha256_file(foo_path),
        },
        generated_at,
    )
    write_json_no_overwrite(comparison_path, comparison_payload)

    LOGGER.info("Primary p=%.6g, ratio=%.6g", topological.permutation_pvalue, topological.effect_size_ratio)
    LOGGER.info("Distinctiveness verdict: %s", comparison_payload["distinctiveness_verdict"])
    return {
        "features": feature_path,
        "sibling": sibling_path,
        "comparison": comparison_path,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proj-root", default=str(PROJ_ROOT))
    parser.add_argument("--worktree", default=str(WORKTREE))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--B", type=int, default=5000)
    parser.add_argument("--icc-bootstrap-B", type=int, default=1000)
    parser.add_argument("--landscape-n-points", type=int, default=256)
    parser.add_argument("--n-jobs", type=int, default=1)
    parser.add_argument("--output-date", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args(argv)
    run_pipeline(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
