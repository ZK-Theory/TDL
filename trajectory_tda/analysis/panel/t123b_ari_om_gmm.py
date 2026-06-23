# Research context: TDA-Research/03-Papers/P01-A-JRSSA/_project.md
# Purpose: Normalised ARI (observed vs exact fixed-margin maximum) with
#          permutation-null SE and bootstrap CI for optimal-matching (dynamic
#          Hamming, Lesnard 2010) k=7 clusters versus GMM k=7 regimes — the
#          object reviewer B9 names (v1 section 4.6, ARI = 0.26).
"""Normalised ARI uncertainty for OM (dynamic Hamming) k=7 versus GMM regimes.

This mirrors the T1.23 H0-vs-GMM machinery but swaps the label source: instead
of H0 tree-cut connected components, the row clustering is the optimal-matching
(dynamic Hamming distance, Lesnard 2010) Ward-linkage clustering cut at k=7.
The observed ARI must reproduce the canonical OM-vs-GMM agreement
(``comparison_at_gmm_k.ari`` from ``05_om_baseline_results.json`` = 0.2611807),
which closes reviewer concern B9.

Run from the task worktree root::

    uv run --env-file .env python -m trajectory_tda.analysis.panel.t123b_ari_om_gmm
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from datetime import date
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from numpy.typing import NDArray
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.metrics import adjusted_rand_score

from trajectory_tda.analysis.panel.fixed_margin_max_ari import (
    CertifiedMaxAri,
    certify_max_ari,
)
from trajectory_tda.analysis.panel.t123_ari_normalisation import (
    adjusted_rand_fast,
    finite_summary,
    git_head_sha,
    parallel_draws,
)
from trajectory_tda.scripts.run_om_baseline import compute_pairwise_dhd

PROJ_ROOT = Path(os.environ.get("TDL_PROJ_ROOT", "C:/Users/steph/TDL"))
WORKTREE = Path.cwd()

DEFAULT_SEQUENCES_PATH = PROJ_ROOT / "results/trajectory_tda_integration/01_trajectories_sequences.json"
DEFAULT_ANALYSIS_JSON = PROJ_ROOT / "results/trajectory_tda_integration/05_analysis.json"
DEFAULT_OM_DIR = PROJ_ROOT / "results/trajectory_tda_robustness/om_baseline"
DEFAULT_OUT_DIR = WORKTREE / "results/panel_methodology/ari"

DEFAULT_SEED = 42
DEFAULT_NULL_B = 5000
DEFAULT_BOOT_B = 1000
EXPECTED_N = 27_280
OM_K = 7
GMM_K = 7
# comparison_at_gmm_k.ari in results/.../om_baseline/05_om_baseline_results.json
CANARY_OBSERVED_ARI = 0.2611807
CANARY_TOL = 1e-4

SCHEMA_VERSION = "ari-om-gmm-normalisation-v1"
REFERENT = "optimal-matching (dynamic Hamming, Lesnard 2010) k=7 vs GMM k=7"


def _null_batch_om(
    om_labels: NDArray[np.int64],
    gmm_labels: NDArray[np.int64],
    n_om: int,
    n_gmm: int,
    seed: int,
    draws: int,
) -> NDArray[np.float64]:
    """Cluster-size-preserving independence null: permute GMM labels."""

    rng = np.random.default_rng(seed)
    out = np.empty(draws, dtype=np.float64)
    for i in range(draws):
        permuted = rng.permutation(gmm_labels)
        out[i] = adjusted_rand_fast(om_labels, permuted, n_rows=n_om, n_cols=n_gmm)
    return out


def _bootstrap_batch_om(
    om_labels: NDArray[np.int64],
    gmm_labels: NDArray[np.int64],
    n_om: int,
    n_gmm: int,
    seed: int,
    draws: int,
) -> NDArray[np.float64]:
    """Paired-individual bootstrap: resample (OM, GMM) label pairs."""

    rng = np.random.default_rng(seed)
    n = len(om_labels)
    out = np.empty(draws, dtype=np.float64)
    for i in range(draws):
        idx = rng.integers(0, n, size=n)
        out[i] = adjusted_rand_fast(om_labels[idx], gmm_labels[idx], n_rows=n_om, n_cols=n_gmm)
    return out


def load_gmm_labels(analysis_json: Path = DEFAULT_ANALYSIS_JSON) -> NDArray[np.int64]:
    """Load the canonical locked GMM labels from 05_analysis.json."""

    with analysis_json.open("r", encoding="utf-8") as handle:
        analysis = json.load(handle)
    gmm_labels = np.asarray(analysis["gmm_labels"], dtype=np.int64)
    if len(gmm_labels) != EXPECTED_N:
        raise ValueError(f"GMM label count {len(gmm_labels)} != {EXPECTED_N}")
    return gmm_labels


def load_om_k7_labels(
    sequences_path: Path = DEFAULT_SEQUENCES_PATH,
    om_dir: Path = DEFAULT_OM_DIR,
    om_k: int = OM_K,
) -> tuple[NDArray[np.int64], dict[str, Any]]:
    """Return OM k=7 cluster labels, regenerating the Ward linkage if absent.

    Consumes the gitignored OM intermediates at ``om_dir`` per the two-path
    rule. If neither a cached k=7 label array nor the Ward linkage is present,
    the canonical dynamic-Hamming distance matrix is recomputed from the
    trajectory sequences (the non-trivial step) and the linkage + k=7 labels
    are persisted for downstream reuse.

    Args:
        sequences_path: Canonical ``01_trajectories_sequences.json``.
        om_dir: OM baseline output directory (gitignored intermediates).
        om_k: Number of clusters to cut the Ward dendrogram at.

    Returns:
        Tuple of the 0-indexed OM label array and a provenance dict.
    """

    labels_path = om_dir / f"04_om_labels_k{om_k}.npy"
    linkage_path = om_dir / "02_ward_linkage.npy"
    om_dir.mkdir(parents=True, exist_ok=True)

    if labels_path.exists():
        labels = np.load(labels_path).astype(np.int64, copy=False)
        source = f"cached {labels_path.name} (fcluster of Ward linkage at k={om_k})"
        regenerated = False
    else:
        if linkage_path.exists():
            linkage_matrix = np.load(linkage_path)
            source = (
                f"fcluster(k={om_k}) of cached Ward linkage {linkage_path.name} "
                "(dynamic Hamming distance, Lesnard 2010)"
            )
        else:
            with sequences_path.open("r", encoding="utf-8") as handle:
                trajectories = json.load(handle)
            if len(trajectories) != EXPECTED_N:
                raise ValueError(f"trajectory count {len(trajectories)} != {EXPECTED_N}")
            condensed = compute_pairwise_dhd(trajectories)
            linkage_matrix = linkage(condensed, method="ward")
            np.save(linkage_path, linkage_matrix)
            source = f"fcluster(k={om_k}) of recomputed Ward linkage (dynamic Hamming distance, Lesnard 2010)"
        labels = fcluster(linkage_matrix, t=om_k, criterion="maxclust").astype(np.int64) - 1
        np.save(labels_path, labels)
        regenerated = True

    if len(labels) != EXPECTED_N:
        raise ValueError(f"OM label count {len(labels)} != {EXPECTED_N}")
    counts = np.bincount(labels, minlength=int(labels.max()) + 1)
    diagnostics = {
        "om_label_source": source,
        "regenerated": regenerated,
        "om_cluster_count": int(len(counts)),
        "om_cluster_counts": {str(i): int(v) for i, v in enumerate(counts)},
    }
    return labels, diagnostics


def build_max_achievable_block(
    cert: CertifiedMaxAri,
    bootstrap_ci_95: list[float],
) -> dict[str, Any]:
    """Assemble the ``max_achievable_ari`` block from a certified-maximum result.

    The headline ``value`` is the achievable maximum ARI (a concrete feasible table,
    so a rigorous lower bound on the true fixed-margin maximum); the rigorous upper
    bound and the resulting normalised-ARI bracket are recorded alongside. The
    bootstrap CI is rescaled by the achievable maximum (the point normaliser).
    """

    ach = cert.ari_max_achievable
    boot_lo, boot_hi = float(bootstrap_ci_95[0]), float(bootstrap_ci_95[1])
    return {
        "value": ach,
        "exact": cert.status == "exact",
        "status": cert.status,
        "method": cert.achievable_method,
        "achievable_lower_bound": {
            "ari": ach,
            "pair_overlap_sum": cert.achievable_pair_overlap,
            "method": cert.achievable_method,
        },
        "rigorous_upper_bound": {
            "ari": cert.ari_max_upper_bound,
            "pair_overlap_sum": cert.upper_bound_pair_overlap,
            "method": cert.upper_bound_method,
        },
        "achieving_table": cert.achieving_table.tolist(),
        "normalised_observed_ari": cert.normalised_observed_ari,
        "normalised_ari_bracket": [
            cert.normalised_lower_bound,
            cert.normalised_observed_ari,
        ],
        "normalised_ci_percentile_95": [boot_lo / ach, boot_hi / ach],
    }


def validate_payload(payload: dict[str, Any]) -> None:
    """Machine-check OM-vs-GMM ARI output invariants required by the contract."""

    required_top = {
        "schema_version",
        "created_at",
        "git_head",
        "referent",
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
    # Object-confusion guard versus the T1.23 H0-tree-cut schema/payload.
    for forbidden in (
        "eps_star",
        "h0_components",
        "pickle_labels_path",
        "joblib_labels_path",
        "causal_interpretation",
    ):
        assert forbidden not in payload, f"forbidden key present: {forbidden}"
    assert "eps_star" not in payload["parameters"], "eps_star leaked into parameters"
    assert "h0_components" not in payload["label_counts"], "h0_components leaked"

    missing_top = required_top - set(payload)
    assert not missing_top, f"missing required top-level keys: {sorted(missing_top)}"
    assert payload["schema_version"] == SCHEMA_VERSION

    referent = payload["referent"]
    assert "optimal-matching" in referent.lower()
    assert "k=7" in referent and "gmm" in referent.lower()

    input_paths = payload["input_paths"]
    for key in ("trajectories", "analysis_json", "gmm_labels_key"):
        assert key in input_paths, f"missing input path field: {key}"
    assert input_paths["gmm_labels_key"] == "gmm_labels"
    assert (
        input_paths["trajectories"]
        .replace("\\", "/")
        .endswith("results/trajectory_tda_integration/01_trajectories_sequences.json")
    )
    assert (
        input_paths["analysis_json"].replace("\\", "/").endswith("results/trajectory_tda_integration/05_analysis.json")
    )

    representation = payload["representation"]
    assert "k=7" in representation["om_label_source"]
    assert representation["gmm_label_source"] == "canonical 05_analysis.json['gmm_labels']"
    assert representation["uses_pickle_or_joblib_labels"] is False

    parameters = payload["parameters"]
    assert parameters["om_k"] == OM_K
    assert parameters["gmm_k"] == GMM_K
    assert parameters["seed"] == DEFAULT_SEED
    assert parameters["null_B_requested"] > 0
    assert parameters["bootstrap_B_requested"] > 0

    counts = payload["label_counts"]
    assert counts["n"] == EXPECTED_N
    assert counts["om_label_length"] == EXPECTED_N
    assert counts["gmm_label_length"] == EXPECTED_N
    assert counts["om_cluster_count"] == OM_K
    assert counts["gmm_regime_count"] >= 1
    assert "om_cluster_counts" in counts
    assert "gmm_regime_counts" in counts

    observed = float(payload["observed_ari"])
    assert -1.0 <= observed <= 1.0
    assert abs(observed - CANARY_OBSERVED_ARI) <= CANARY_TOL, (
        f"observed_ari {observed} does not reproduce {CANARY_OBSERVED_ARI} within {CANARY_TOL}"
    )

    null_block = payload["null_distribution"]
    assert null_block["se"] >= 0.0
    assert math.isfinite(float(null_block["se"]))
    assert null_block["B"] > 0
    assert null_block["seed"] == DEFAULT_SEED
    assert null_block["finite_count"] > 0
    assert null_block["procedure"]
    assert 0.0 < float(null_block["pvalue"]) <= 1.0

    max_block = payload["max_achievable_ari"]
    value = float(max_block["value"])
    assert -1.0 <= value <= 1.0
    assert math.isfinite(value), "max_ari value not finite"
    # (j) The certified maximum must be a real constrained maximum, never the
    # vacuous 1.0 the trivial whole-cluster-packing fallback produced.
    assert value < 1.0, "max_achievable_ari.value must be a real fixed-margin maximum < 1.0"
    assert isinstance(max_block["exact"], bool)
    assert max_block["status"] in {"exact", "bracket"}
    assert max_block["exact"] == (max_block["status"] == "exact")
    assert max_block["method"]

    ub_block = max_block["rigorous_upper_bound"]
    ub_ari = float(ub_block["ari"])
    assert -1.0 <= ub_ari <= 1.0 and math.isfinite(ub_ari)
    assert ub_ari + 1e-12 >= value, "rigorous upper bound is below the achievable value"
    assert ub_block["method"]

    # (k) The normalisation must actually rescale: a real maximum < 1 forces the
    # normalised ARI strictly above the observed ARI.
    norm = float(max_block["normalised_observed_ari"])
    assert math.isfinite(norm)
    assert abs(norm - observed) > 1e-9, "normalised ARI must differ from observed ARI"
    nlo, nhi = max_block["normalised_ari_bracket"]
    assert float(nlo) <= float(nhi)
    if max_block["status"] == "exact":
        assert abs(float(nlo) - float(nhi)) <= 1e-9, "exact status requires a degenerate bracket"
    cilo, cihi = max_block["normalised_ci_percentile_95"]
    assert float(cilo) <= float(cihi)
    assert math.isfinite(float(cilo)) and math.isfinite(float(cihi))

    boot_block = payload["bootstrap_ci"]
    lo, hi = boot_block["percentile_95"]
    assert lo <= hi
    assert math.isfinite(float(lo)) and math.isfinite(float(hi))
    assert boot_block["B"] > 0
    assert boot_block["seed"] == DEFAULT_SEED
    assert boot_block["resampling_unit"] == "individual"

    interpretation = payload["interpretation"]
    assert isinstance(interpretation, Mapping)
    assert interpretation["closes_b9"] is True
    assert interpretation["causal_claim"] == "none"
    assert interpretation["topological_distinctiveness_claim"] == "none"

    assert float(payload["runtime"]["wall_seconds"]) >= 0.0


def validate_ari_om_gmm_output(payload: Mapping[str, Any]) -> None:
    """Validate an OM-vs-GMM ARI output payload against the local contract."""

    validate_payload(dict(payload))


def dispatch_t123b_json(path: Path, payload: Mapping[str, Any]) -> bool:
    """Route OM-vs-GMM ARI JSONs; leave unrelated panel JSONs untouched.

    Returns True only for ``ari_om_gmm_normalised_*.json`` files under
    ``results/panel_methodology/ari/``. The H0-tree-cut ``ari_normalised_*.json``
    files and other panel JSONs are not captured.
    """

    rel = path.as_posix()
    if (
        path.name.startswith("ari_om_gmm_normalised_")
        and path.suffix == ".json"
        and "results/panel_methodology/ari/" in rel
    ):
        validate_ari_om_gmm_output(payload)
        return True
    return False


def write_json_no_overwrite(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON result, refusing to overwrite an existing file."""

    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing result: {path}")
    assert path.name == f"ari_om_gmm_normalised_{payload['created_at']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    validate_payload(payload)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def build_result(
    seed: int,
    null_b: int,
    boot_b: int,
    n_jobs: int,
) -> dict[str, Any]:
    """Run the full OM-vs-GMM ARI calculation and return a result payload."""

    started = time.perf_counter()
    gmm_labels = load_gmm_labels()
    om_labels, om_diagnostics = load_om_k7_labels()
    if len(om_labels) != len(gmm_labels) or len(om_labels) != EXPECTED_N:
        raise ValueError("OM, GMM, and expected lengths do not all equal 27,280")

    n_om = int(om_labels.max()) + 1
    n_gmm = int(gmm_labels.max()) + 1
    if n_om != OM_K:
        raise ValueError(f"OM cut produced {n_om} clusters, expected {OM_K}")

    observed = float(adjusted_rand_score(om_labels, gmm_labels))
    observed_fast = adjusted_rand_fast(om_labels, gmm_labels, n_rows=n_om, n_cols=n_gmm)
    if not np.isclose(observed, observed_fast, atol=1e-12):
        raise ValueError("fast ARI implementation disagrees with sklearn")
    if abs(observed - CANARY_OBSERVED_ARI) > CANARY_TOL:
        raise ValueError(
            f"canary failed: observed ARI {observed} != {CANARY_OBSERVED_ARI} "
            f"(tol {CANARY_TOL}); OM k=7 labels do not match the baseline"
        )

    row_counts = np.bincount(om_labels, minlength=n_om)
    col_counts = np.bincount(gmm_labels, minlength=n_gmm)
    max_cert = certify_max_ari(row_counts, col_counts, observed)

    null_values = parallel_draws(_null_batch_om, null_b, seed, n_jobs, om_labels, gmm_labels, n_om, n_gmm)
    null_finite, null_failures = finite_summary(null_values)
    if len(null_finite) == 0:
        raise ValueError("all null ARI draws failed")
    exceed = int(np.sum(null_finite >= observed))
    p_upper = float((exceed + 1) / (len(null_finite) + 1))

    boot_values = parallel_draws(_bootstrap_batch_om, boot_b, seed + 1, n_jobs, om_labels, gmm_labels, n_om, n_gmm)
    boot_finite, boot_failures = finite_summary(boot_values)
    if len(boot_finite) == 0:
        raise ValueError("all bootstrap ARI draws failed")

    boot_ci_95 = [
        float(np.quantile(boot_finite, 0.025)),
        float(np.quantile(boot_finite, 0.975)),
    ]
    max_block = build_max_achievable_block(max_cert, boot_ci_95)
    elapsed = time.perf_counter() - started
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "created_at": date.today().isoformat(),
        "git_head": git_head_sha(),
        "referent": REFERENT,
        "input_paths": {
            "trajectories": str(DEFAULT_SEQUENCES_PATH),
            "analysis_json": str(DEFAULT_ANALYSIS_JSON),
            "gmm_labels_key": "gmm_labels",
        },
        "representation": {
            "om_label_source": om_diagnostics["om_label_source"],
            "gmm_label_source": "canonical 05_analysis.json['gmm_labels']",
            "om_baseline_directory": str(DEFAULT_OM_DIR),
            "row_alignment": "same trajectory/GMM row order, both length 27,280",
            "uses_pickle_or_joblib_labels": False,
            "regenerated_linkage": om_diagnostics["regenerated"],
        },
        "parameters": {
            "om_k": OM_K,
            "gmm_k": GMM_K,
            "om_distance": "dynamic Hamming distance (Lesnard 2010), Ward linkage",
            "seed": seed,
            "null_B_requested": null_b,
            "bootstrap_B_requested": boot_b,
            "n_jobs": n_jobs,
        },
        "label_counts": {
            "n": int(len(om_labels)),
            "om_label_length": int(len(om_labels)),
            "gmm_label_length": int(len(gmm_labels)),
            "om_cluster_count": int(n_om),
            "om_cluster_counts": om_diagnostics["om_cluster_counts"],
            "gmm_regime_count": int(n_gmm),
            "gmm_regime_counts": {str(i): int(v) for i, v in enumerate(col_counts)},
        },
        "observed_ari": observed,
        "null_distribution": {
            "procedure": (
                "Permute GMM labels relative to fixed OM k=7 labels, preserving "
                "both cluster-size distributions under independence."
            ),
            "B": int(len(null_finite)),
            "seed": seed,
            "finite_count": int(len(null_finite)),
            "failures_non_finite": null_failures,
            "mean": float(np.mean(null_finite)),
            "se": float(np.std(null_finite, ddof=1)) if len(null_finite) > 1 else 0.0,
            "pvalue": p_upper,
            "pvalue_definition": "(r + 1) / (B + 1), r = draws >= observed, B = finite draws",
            "exceedances_observed_or_larger": exceed,
            "quantiles": {
                "0.025": float(np.quantile(null_finite, 0.025)),
                "0.5": float(np.quantile(null_finite, 0.5)),
                "0.975": float(np.quantile(null_finite, 0.975)),
            },
        },
        "max_achievable_ari": max_block,
        "bootstrap_ci": {
            "procedure": ("Resample paired individual rows (OM label, GMM label) with replacement."),
            "resampling_unit": "individual",
            "B": int(len(boot_finite)),
            "seed": seed,
            "finite_count": int(len(boot_finite)),
            "failures_non_finite": boot_failures,
            "mean": float(np.mean(boot_finite)),
            "se": float(np.std(boot_finite, ddof=1)) if len(boot_finite) > 1 else 0.0,
            "percentile_95": boot_ci_95,
        },
        "interpretation": {
            "statistic_role": "descriptive clustering-agreement statistic",
            "closes_b9": True,
            "claim": (
                "Optimal-matching (dynamic Hamming) k=7 clusters and GMM k=7 "
                "regimes agree at ARI = 0.26 (closes reviewer B9)."
            ),
            "causal_claim": "none",
            "topological_distinctiveness_claim": "none",
            "normalisation_basis": max_cert.status,
            "paper_claim_guardrail": (
                "Report as the OM-vs-GMM agreement only; do not imply causal mediation or topological distinctiveness."
            ),
        },
        "runtime": {"wall_seconds": float(elapsed)},
    }
    validate_payload(payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--null-B", type=int, default=DEFAULT_NULL_B)
    parser.add_argument("--boot-B", type=int, default=DEFAULT_BOOT_B)
    parser.add_argument("--n-jobs", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_path = args.out_dir / f"ari_om_gmm_normalised_{args.date}.json"
    print("=== OM (dynamic Hamming) k=7 versus GMM k=7 normalised ARI ===")
    print(f"Output: {out_path}")
    payload = build_result(
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
    print(
        json.dumps(
            {
                "observed_ari": payload["observed_ari"],
                "null_se": payload["null_distribution"]["se"],
                "pvalue": payload["null_distribution"]["pvalue"],
                "max_ari": max_block["value"],
                "max_ari_exact": max_block["exact"],
                "normalised_ari": normalised_value,
                "bootstrap_ci": payload["bootstrap_ci"]["percentile_95"],
                "wall_seconds": payload["runtime"]["wall_seconds"],
            },
            indent=2,
        )
    )
    print("=== complete ===")


if __name__ == "__main__":
    main()
