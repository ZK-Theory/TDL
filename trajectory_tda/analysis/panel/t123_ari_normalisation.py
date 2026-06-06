"""Normalised ARI uncertainty for H0 components versus GMM regimes.

Run from the task worktree root:

    uv run python trajectory_tda/analysis/panel/t123_ari_normalisation.py
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from joblib import Parallel, delayed
from scipy.sparse.csgraph import connected_components
from sklearn.metrics import adjusted_rand_score
from sklearn.neighbors import radius_neighbors_graph

PROJ_ROOT = Path("C:/Users/steph/TDL")
WORKTREE = Path.cwd()

DEFAULT_EMBEDDINGS_PATH = PROJ_ROOT / "results/trajectory_tda_integration/embeddings.npy"
DEFAULT_ANALYSIS_JSON = PROJ_ROOT / "results/trajectory_tda_integration/05_analysis.json"
DEFAULT_OUT_DIR = WORKTREE / "results/panel_methodology/ari"
DEFAULT_EPS_STAR = 0.54
DEFAULT_SEED = 42
DEFAULT_NULL_B = 5000
DEFAULT_BOOT_B = 1000
EXPECTED_N = 27_280


@dataclass(frozen=True)
class MaxAriResult:
    """Result of fixed-margin maximum ARI construction."""

    ari: float
    normalised_observed: float | None
    exact: bool
    method: str
    contingency: np.ndarray
    pair_overlap_sum: int
    unsplit_non_singleton_components: int
    split_non_singleton_components: int


def comb2(values: np.ndarray | int) -> np.ndarray | int:
    """Return n choose 2 for scalar or array-like counts."""

    arr = np.asarray(values, dtype=np.int64)
    out = arr * (arr - 1) // 2
    if np.isscalar(values):
        return int(out)
    return out


def git_head_sha() -> str:
    """Return current git HEAD SHA for provenance."""

    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except Exception:
        return "unknown"


def load_inputs(
    embeddings_path: Path = DEFAULT_EMBEDDINGS_PATH,
    analysis_json: Path = DEFAULT_ANALYSIS_JSON,
) -> tuple[np.ndarray, np.ndarray]:
    """Load canonical embeddings and GMM labels, failing fast on length mismatch."""

    embeddings = np.load(embeddings_path)
    with analysis_json.open("r", encoding="utf-8") as handle:
        analysis = json.load(handle)
    gmm_labels = np.asarray(analysis["gmm_labels"], dtype=np.int64)
    if embeddings.shape[0] != EXPECTED_N:
        raise ValueError(f"embedding row count {embeddings.shape[0]} != {EXPECTED_N}")
    if len(gmm_labels) != EXPECTED_N:
        raise ValueError(f"GMM label count {len(gmm_labels)} != {EXPECTED_N}")
    if embeddings.shape[0] != len(gmm_labels):
        raise ValueError("embedding row count and GMM label count differ")
    return embeddings, gmm_labels


def reconstruct_h0_labels(
    embeddings: np.ndarray,
    eps_star: float = DEFAULT_EPS_STAR,
    n_jobs: int = -1,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Reconstruct H0 labels as Euclidean radius-graph connected components."""

    graph = radius_neighbors_graph(
        embeddings,
        radius=eps_star,
        mode="connectivity",
        include_self=True,
        n_jobs=n_jobs,
    )
    n_components, labels = connected_components(graph, directed=False)
    labels = labels.astype(np.int64, copy=False)
    counts = np.bincount(labels, minlength=n_components)
    size_hist = Counter(int(x) for x in counts)
    diagnostics = {
        "n_components": int(n_components),
        "graph_nnz": int(graph.nnz),
        "largest_component_sizes": [int(x) for x in sorted(counts, reverse=True)[:20]],
        "component_size_histogram": {str(k): int(v) for k, v in sorted(size_hist.items())},
        "n_singleton_components": int(size_hist.get(1, 0)),
        "n_non_singleton_components": int(sum(v for k, v in size_hist.items() if k > 1)),
    }
    return labels, diagnostics


def contingency_table(
    row_labels: np.ndarray,
    col_labels: np.ndarray,
    n_rows: int | None = None,
    n_cols: int | None = None,
) -> np.ndarray:
    """Build a dense contingency table for non-negative integer labels."""

    if len(row_labels) != len(col_labels):
        raise ValueError("label vectors must have equal length")
    if n_rows is None:
        n_rows = int(row_labels.max()) + 1
    if n_cols is None:
        n_cols = int(col_labels.max()) + 1
    encoded = row_labels.astype(np.int64) * n_cols + col_labels.astype(np.int64)
    return np.bincount(encoded, minlength=n_rows * n_cols).reshape(n_rows, n_cols)


def adjusted_rand_from_contingency(table: np.ndarray) -> float:
    """Compute adjusted Rand index from a contingency table."""

    table = np.asarray(table, dtype=np.int64)
    n = int(table.sum())
    if n < 2:
        return 1.0
    sum_cells = int(comb2(table).sum())
    row_pairs = int(comb2(table.sum(axis=1)).sum())
    col_pairs = int(comb2(table.sum(axis=0)).sum())
    total_pairs = int(comb2(n))
    expected = row_pairs * col_pairs / total_pairs
    max_index = 0.5 * (row_pairs + col_pairs)
    denominator = max_index - expected
    if denominator == 0:
        return 1.0 if sum_cells == max_index else 0.0
    return float((sum_cells - expected) / denominator)


def adjusted_rand_fast(
    row_labels: np.ndarray,
    col_labels: np.ndarray,
    n_rows: int | None = None,
    n_cols: int | None = None,
) -> float:
    """Compute ARI directly from integer labels via bincount."""

    return adjusted_rand_from_contingency(
        contingency_table(row_labels, col_labels, n_rows=n_rows, n_cols=n_cols)
    )


def construct_exact_max_contingency(
    row_counts: np.ndarray,
    col_counts: np.ndarray,
) -> tuple[np.ndarray, bool, int, int]:
    """Construct a fixed-margin contingency table that maximizes ARI when certifiable.

    ARI's fixed-margin denominator is constant, so maximizing ARI is equivalent
    to maximizing sum_ij choose(n_ij, 2). For each row i, this contribution is
    bounded above by choose(row_count_i, 2). If every non-singleton row can be
    assigned whole to a column without exceeding column capacities, the table
    attains the global upper bound and is therefore exact. Singleton rows then
    fill the remaining margins without changing pair overlap.
    """

    row_counts = np.asarray(row_counts, dtype=np.int64)
    col_counts = np.asarray(col_counts, dtype=np.int64)
    table = np.zeros((len(row_counts), len(col_counts)), dtype=np.int64)
    remaining = col_counts.copy()
    non_singletons = [
        (int(size), int(row_id))
        for row_id, size in enumerate(row_counts)
        if int(size) > 1
    ]
    non_singletons.sort(reverse=True)

    split_count = 0
    for size, row_id in non_singletons:
        candidates = np.flatnonzero(remaining >= size)
        if len(candidates) == 0:
            split_count += 1
            break
        best = int(candidates[np.argmin(remaining[candidates] - size)])
        table[row_id, best] = size
        remaining[best] -= size

    if split_count:
        return table, False, len(non_singletons) - split_count, split_count

    for row_id, size in enumerate(row_counts):
        if size != 1:
            continue
        candidates = np.flatnonzero(remaining > 0)
        if len(candidates) == 0:
            return table, False, len(non_singletons), split_count
        col = int(candidates[np.argmax(remaining[candidates])])
        table[row_id, col] = 1
        remaining[col] -= 1

    exact = bool(np.all(remaining == 0))
    return table, exact, len(non_singletons), split_count


def compute_max_ari(
    row_counts: np.ndarray,
    col_counts: np.ndarray,
    observed_ari: float,
) -> MaxAriResult:
    """Compute the exact fixed-margin maximum ARI when the certificate holds."""

    table, exact, unsplit, split = construct_exact_max_contingency(row_counts, col_counts)
    max_ari = adjusted_rand_from_contingency(table)
    normalised = observed_ari / max_ari if max_ari > 0 else None
    method = (
        "Exact fixed-margin maximum: all non-singleton H0 components are packed "
        "whole into the seven GMM column margins, attaining the row-wise upper "
        "bound sum_i choose(a_i, 2); singleton components fill residual margins."
        if exact
        else "Uncertified greedy fixed-margin construction; treat as an upper bound only."
    )
    return MaxAriResult(
        ari=float(max_ari),
        normalised_observed=float(normalised) if normalised is not None else None,
        exact=exact,
        method=method,
        contingency=table,
        pair_overlap_sum=int(comb2(table).sum()),
        unsplit_non_singleton_components=int(unsplit),
        split_non_singleton_components=int(split),
    )


def _null_batch(
    h0_labels: np.ndarray,
    gmm_labels: np.ndarray,
    n_h0: int,
    n_gmm: int,
    seed: int,
    draws: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = np.empty(draws, dtype=np.float64)
    for i in range(draws):
        permuted = rng.permutation(gmm_labels)
        out[i] = adjusted_rand_fast(h0_labels, permuted, n_rows=n_h0, n_cols=n_gmm)
    return out


def _bootstrap_batch(
    h0_labels: np.ndarray,
    gmm_labels: np.ndarray,
    n_h0: int,
    n_gmm: int,
    seed: int,
    draws: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = len(h0_labels)
    out = np.empty(draws, dtype=np.float64)
    for i in range(draws):
        idx = rng.integers(0, n, size=n)
        out[i] = adjusted_rand_fast(
            h0_labels[idx],
            gmm_labels[idx],
            n_rows=n_h0,
            n_cols=n_gmm,
        )
    return out


def _batch_sizes(total: int, n_batches: int) -> list[int]:
    base, extra = divmod(total, n_batches)
    return [base + (1 if i < extra else 0) for i in range(n_batches) if base + (1 if i < extra else 0) > 0]


def parallel_draws(
    worker,
    total: int,
    seed: int,
    n_jobs: int,
    *worker_args,
) -> np.ndarray:
    """Run independent Monte Carlo batches with deterministic per-batch seeds."""

    if total <= 0:
        return np.empty(0, dtype=np.float64)
    n_batches = min(max(1, n_jobs * 4), total)
    sizes = _batch_sizes(total, n_batches)
    seed_seq = np.random.SeedSequence(seed)
    child_seeds = [int(s.generate_state(1, dtype=np.uint32)[0]) for s in seed_seq.spawn(len(sizes))]
    chunks = Parallel(n_jobs=n_jobs, prefer="processes")(
        delayed(worker)(*worker_args, child_seed, draws)
        for child_seed, draws in zip(child_seeds, sizes)
    )
    return np.concatenate(chunks)


def finite_summary(values: np.ndarray) -> tuple[np.ndarray, int]:
    """Return finite values and count of non-finite failures."""

    finite_mask = np.isfinite(values)
    return values[finite_mask], int((~finite_mask).sum())


def validate_payload(payload: dict[str, Any]) -> None:
    """Machine-check output JSON invariants required by the task."""

    required_top = {
        "schema_version",
        "created_at",
        "git_head",
        "input_paths",
        "representation",
        "parameters",
        "label_counts",
        "observed_ari",
        "null_distribution",
        "max_achievable_ari",
        "bootstrap_ci",
        "interpretation",
        "runtime",
    }
    for forbidden in ("pickle_labels_path", "joblib_labels_path", "causal_interpretation"):
        assert forbidden not in payload, f"forbidden key present: {forbidden}"

    missing_top = required_top - set(payload)
    assert not missing_top, f"missing required top-level keys: {sorted(missing_top)}"
    assert payload["schema_version"] == "ari-normalisation-v1"

    input_paths = payload["input_paths"]
    for key in ("embeddings", "analysis_json", "gmm_labels_key"):
        assert key in input_paths, f"missing input path field: {key}"
    assert input_paths["gmm_labels_key"] == "gmm_labels"
    assert input_paths["embeddings"].endswith("results\\trajectory_tda_integration\\embeddings.npy") or input_paths[
        "embeddings"
    ].endswith("results/trajectory_tda_integration/embeddings.npy")
    assert input_paths["analysis_json"].endswith("results\\trajectory_tda_integration\\05_analysis.json") or input_paths[
        "analysis_json"
    ].endswith("results/trajectory_tda_integration/05_analysis.json")

    representation = payload["representation"]
    assert representation["embedding_source"] == "canonical embeddings.npy"
    assert representation["gmm_label_source"] == "canonical 05_analysis.json['gmm_labels']"
    assert representation["row_alignment"] == "same checkpoint directory and row order"
    assert representation["uses_pickle_or_joblib_labels"] is False

    parameters = payload["parameters"]
    assert parameters["eps_star"] == DEFAULT_EPS_STAR
    assert parameters["seed"] == DEFAULT_SEED
    assert parameters["null_B_requested"] > 0
    assert parameters["bootstrap_B_requested"] > 0
    assert parameters["n_jobs"] >= 1

    observed = float(payload["observed_ari"])
    assert -1.0 <= observed <= 1.0
    assert payload["label_counts"]["n"] == EXPECTED_N
    assert payload["label_counts"]["h0_label_length"] == EXPECTED_N
    assert payload["label_counts"]["gmm_label_length"] == EXPECTED_N
    assert payload["label_counts"]["h0_components"]["n_components"] >= 1
    assert "h0_component_counts" in payload["label_counts"]
    assert payload["label_counts"]["gmm_regime_count"] >= 1

    assert payload["null_distribution"]["se"] >= 0.0
    assert payload["null_distribution"]["B"] > 0
    assert payload["null_distribution"]["seed"] == DEFAULT_SEED
    assert payload["null_distribution"]["finite_count"] > 0
    assert payload["null_distribution"]["procedure"]

    lo, hi = payload["bootstrap_ci"]["percentile_95"]
    assert lo <= hi
    assert payload["bootstrap_ci"]["B"] > 0
    assert payload["bootstrap_ci"]["seed"] == DEFAULT_SEED
    assert payload["bootstrap_ci"]["resampling_unit"] == "individual"

    max_block = payload["max_achievable_ari"]
    assert isinstance(max_block["exact"], bool)
    assert max_block["status"] in {"exact", "upper_bound"}
    assert max_block["method"]
    if max_block["exact"]:
        assert max_block["status"] == "exact"
        assert "normalised_observed_ari" in max_block
        assert "normalised_ari_upper_bound_scale" not in max_block
    else:
        assert max_block["status"] == "upper_bound"
        assert "normalised_ari_upper_bound_scale" in max_block
        assert "normalised_observed_ari" not in max_block

    interpretation = payload["interpretation"]
    assert isinstance(interpretation, Mapping)
    assert interpretation["statistic_role"] == "descriptive agreement statistic"
    assert interpretation["causal_claim"] == "none"
    assert interpretation["topological_distinctiveness_claim"] == "none"
    assert interpretation["normalisation_basis"] in {"exact", "upper_bound"}

    numeric_paths = [
        ("observed_ari", payload["observed_ari"]),
        ("null_mean", payload["null_distribution"]["mean"]),
        ("null_se", payload["null_distribution"]["se"]),
        ("max_ari", max_block["value"]),
        ("bootstrap_lo", lo),
        ("bootstrap_hi", hi),
    ]
    normalised_key = (
        "normalised_observed_ari"
        if max_block["exact"]
        else "normalised_ari_upper_bound_scale"
    )
    if max_block[normalised_key] is not None:
        numeric_paths.append(
            (
                normalised_key,
                max_block[normalised_key],
            )
        )
    for name, value in numeric_paths:
        assert math.isfinite(float(value)), f"{name} is not finite"


def write_json_no_overwrite(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON result, refusing to overwrite an existing file."""

    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing result: {path}")
    assert path.name == f"ari_normalised_{payload['created_at']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    validate_payload(payload)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def validate_ari_normalisation_output(payload: Mapping[str, Any]) -> None:
    """Validate an ARI-normalisation output payload against the local contract."""

    validate_payload(dict(payload))


def dispatch_t123_json(path: Path, payload: Mapping[str, Any]) -> bool:
    """Validate T1.23 ARI JSONs and leave unrelated panel JSONs untouched."""

    rel = path.as_posix()
    if path.name.startswith("ari_normalised_") and path.suffix == ".json" and "results/panel_methodology/ari/" in rel:
        validate_ari_normalisation_output(payload)
        return True
    return False


def build_result(
    eps_star: float,
    seed: int,
    null_b: int,
    boot_b: int,
    n_jobs: int,
) -> dict[str, Any]:
    """Run the full ARI calculation and return a serialisable result payload."""

    started = time.perf_counter()
    embeddings, gmm_labels = load_inputs()
    h0_labels, h0_diagnostics = reconstruct_h0_labels(embeddings, eps_star=eps_star)
    if len(h0_labels) != len(gmm_labels) or len(h0_labels) != EXPECTED_N:
        raise ValueError("H0, GMM, and embedding lengths do not all equal 27,280")

    n_h0 = int(h0_labels.max()) + 1
    n_gmm = int(gmm_labels.max()) + 1
    observed = float(adjusted_rand_score(h0_labels, gmm_labels))
    observed_fast = adjusted_rand_fast(h0_labels, gmm_labels, n_rows=n_h0, n_cols=n_gmm)
    if not np.isclose(observed, observed_fast, atol=1e-12):
        raise ValueError("fast ARI implementation disagrees with sklearn")

    row_counts = np.bincount(h0_labels, minlength=n_h0)
    col_counts = np.bincount(gmm_labels, minlength=n_gmm)
    max_ari = compute_max_ari(row_counts, col_counts, observed)

    null_values = parallel_draws(
        _null_batch,
        null_b,
        seed,
        n_jobs,
        h0_labels,
        gmm_labels,
        n_h0,
        n_gmm,
    )
    null_finite, null_failures = finite_summary(null_values)
    if len(null_finite) == 0:
        raise ValueError("all null ARI draws failed")
    exceed = int(np.sum(null_finite >= observed))
    p_upper = float((exceed + 1) / (len(null_finite) + 1))

    boot_values = parallel_draws(
        _bootstrap_batch,
        boot_b,
        seed + 1,
        n_jobs,
        h0_labels,
        gmm_labels,
        n_h0,
        n_gmm,
    )
    boot_finite, boot_failures = finite_summary(boot_values)
    if len(boot_finite) == 0:
        raise ValueError("all bootstrap ARI draws failed")

    elapsed = time.perf_counter() - started
    payload: dict[str, Any] = {
        "schema_version": "ari-normalisation-v1",
        "created_at": date.today().isoformat(),
        "git_head": git_head_sha(),
        "input_paths": {
            "embeddings": str(DEFAULT_EMBEDDINGS_PATH),
            "analysis_json": str(DEFAULT_ANALYSIS_JSON),
            "gmm_labels_key": "gmm_labels",
        },
        "representation": {
            "embedding_source": "canonical embeddings.npy",
            "gmm_label_source": "canonical 05_analysis.json['gmm_labels']",
            "checkpoint_directory": str(PROJ_ROOT / "results/trajectory_tda_integration"),
            "row_alignment": "same checkpoint directory and row order",
            "row_alignment_justification": (
                "H0 labels are reconstructed directly from embeddings.npy rows; "
                "GMM labels are read from the same checkpoint directory's "
                "05_analysis.json['gmm_labels']; both vectors are asserted length 27,280."
            ),
            "uses_pickle_or_joblib_labels": False,
        },
        "parameters": {
            "eps_star": eps_star,
            "h0_label_method": (
                "Connected components of the Euclidean radius-neighbors graph "
                "with edge distance <= eps_star and include_self=True."
            ),
            "seed": seed,
            "null_B_requested": null_b,
            "bootstrap_B_requested": boot_b,
            "n_jobs": n_jobs,
        },
        "label_counts": {
            "n": int(len(h0_labels)),
            "h0_label_length": int(len(h0_labels)),
            "gmm_label_length": int(len(gmm_labels)),
            "h0_components": h0_diagnostics,
            "h0_component_counts": {str(i): int(v) for i, v in enumerate(row_counts)},
            "gmm_regime_count": int(n_gmm),
            "gmm_regime_counts": {str(i): int(v) for i, v in enumerate(col_counts)},
        },
        "observed_ari": observed,
        "null_distribution": {
            "procedure": (
                "Permute GMM labels relative to fixed H0 labels, preserving both "
                "cluster-size distributions under independence."
            ),
            "B": int(len(null_finite)),
            "seed": seed,
            "finite_count": int(len(null_finite)),
            "failures_non_finite": null_failures,
            "mean": float(np.mean(null_finite)),
            "se": float(np.std(null_finite, ddof=1)) if len(null_finite) > 1 else 0.0,
            "pvalue_upper_tail_bias_corrected": p_upper,
            "exceedances_observed_or_larger": exceed,
            "quantiles": {
                "0.025": float(np.quantile(null_finite, 0.025)),
                "0.5": float(np.quantile(null_finite, 0.5)),
                "0.975": float(np.quantile(null_finite, 0.975)),
            },
        },
        "max_achievable_ari": {
            "value": max_ari.ari,
            "exact": max_ari.exact,
            "status": "exact" if max_ari.exact else "upper_bound",
            "method": max_ari.method,
            "pair_overlap_sum": max_ari.pair_overlap_sum,
            "unsplit_non_singleton_components": max_ari.unsplit_non_singleton_components,
            "split_non_singleton_components": max_ari.split_non_singleton_components,
        },
        "bootstrap_ci": {
            "procedure": "Resample paired individual rows (H0 label, GMM label) with replacement.",
            "resampling_unit": "individual",
            "B": int(len(boot_finite)),
            "seed": seed,
            "finite_count": int(len(boot_finite)),
            "failures_non_finite": boot_failures,
            "mean": float(np.mean(boot_finite)),
            "se": float(np.std(boot_finite, ddof=1)) if len(boot_finite) > 1 else 0.0,
            "percentile_95": [
                float(np.quantile(boot_finite, 0.025)),
                float(np.quantile(boot_finite, 0.975)),
            ],
        },
        "interpretation": {
            "statistic_role": "descriptive agreement statistic",
            "causal_claim": "none",
            "topological_distinctiveness_claim": "none",
            "normalisation_basis": "exact" if max_ari.exact else "upper_bound",
            "paper_claim_guardrail": (
                "Report as exact normalised ARI only if max_achievable_ari.exact is true; "
                "otherwise report as upper-bound scaled agreement pending Manager review."
            ),
        },
        "runtime": {
            "wall_seconds": float(elapsed),
        },
    }
    if max_ari.exact:
        payload["max_achievable_ari"]["normalised_observed_ari"] = max_ari.normalised_observed
    else:
        payload["max_achievable_ari"]["normalised_ari_upper_bound_scale"] = max_ari.normalised_observed
    validate_payload(payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eps-star", type=float, default=DEFAULT_EPS_STAR)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--null-B", type=int, default=DEFAULT_NULL_B)
    parser.add_argument("--boot-B", type=int, default=DEFAULT_BOOT_B)
    parser.add_argument("--n-jobs", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_path = args.out_dir / f"ari_normalised_{args.date}.json"
    print("=== ARI normalisation: H0 eps*=0.54 versus GMM regimes ===")
    print(f"Output: {out_path}")
    payload = build_result(
        eps_star=args.eps_star,
        seed=args.seed,
        null_b=args.null_B,
        boot_b=args.boot_B,
        n_jobs=args.n_jobs,
    )
    write_json_no_overwrite(out_path, payload)
    max_block = payload["max_achievable_ari"]
    normalised_value = max_block.get(
        "normalised_observed_ari",
        max_block.get("normalised_ari_upper_bound_scale"),
    )
    print(json.dumps({
        "observed_ari": payload["observed_ari"],
        "null_se": payload["null_distribution"]["se"],
        "max_ari": max_block["value"],
        "normalised_ari": normalised_value,
        "bootstrap_ci": payload["bootstrap_ci"]["percentile_95"],
        "wall_seconds": payload["runtime"]["wall_seconds"],
    }, indent=2))
    print("=== complete ===")


if __name__ == "__main__":
    main()
