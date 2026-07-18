"""Scale-coherence statistic and spatialised permutation null for IMD LADs.

The observed and null arms intentionally share :func:`scale_coherence_statistic`.
The null changes only the assignment of raw deprivation vectors to fixed spatial
nodes before any standardisation, neighbourhood averaging, or clustering.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.stats import spearmanr
from sklearn.cluster import KMeans

from trajectory_tda.topology.mcbif_nerve import hf_statistics, hilbert_grid_h0_h1

SEED = 42
KS = (3, 5, 7, 10, 15)
N_DOMAINS = 7
SCHEMA_VERSION = "deprivation-scale-coherence/v1"
ALPHA = 0.05
B_LOCKED = 999
LAD_FLOOR = 150
IMD_SHA256 = "b1b716aa2e476449f987b9de3e08255b4794eabfd270626de5de18b2f5eff3ef"
LSOA_SHA256 = "34d637634532b16824c576f0a297ee6ce07962b88d23aa0fd8e564c97a3d0f38"


def _validate_inputs(
    raw: NDArray[np.float64],
    closed_neighbours: Sequence[NDArray[np.intp]],
) -> None:
    if raw.ndim != 2 or raw.shape[1] != N_DOMAINS:
        raise ValueError(f"raw must have shape (n, {N_DOMAINS}); got {raw.shape}")
    if not np.isfinite(raw).all():
        raise ValueError("raw contains non-finite deprivation values")
    if len(closed_neighbours) != len(raw):
        raise ValueError("closed_neighbours must have one entry per raw row")
    for index, neighbours in enumerate(closed_neighbours):
        values = np.asarray(neighbours)
        if values.ndim != 1 or len(values) == 0:
            raise ValueError(f"closed_neighbours[{index}] must be a non-empty vector")
        if np.any(values < 0) or np.any(values >= len(raw)):
            raise ValueError(f"closed_neighbours[{index}] contains an out-of-range node")


def scale_coherence_statistic(
    raw: NDArray[np.float64],
    closed_neighbours: Sequence[NDArray[np.intp]],
) -> dict[str, Any]:
    """Run the locked z-score -> local mean -> k-means -> nerve pipeline."""
    values = np.asarray(raw, dtype=np.float64)
    _validate_inputs(values, closed_neighbours)

    means = values.mean(axis=0)
    standard_deviations = values.std(axis=0)
    standard_deviations[standard_deviations == 0.0] = 1.0
    standardised = (values - means) / standard_deviations
    local_features = np.vstack(
        [standardised[np.asarray(neighbours, dtype=np.intp)].mean(axis=0) for neighbours in closed_neighbours]
    )
    partitions = [
        KMeans(n_clusters=k, n_init=50, random_state=SEED).fit_predict(local_features).astype(np.int64) for k in KS
    ]
    grids = hilbert_grid_h0_h1(partitions)
    statistics = hf_statistics(grids["HF0"], grids["HF1"])
    return {
        **statistics,
        "partitions": partitions,
        "local_features": local_features,
        "hf0": grids["HF0"],
        "hf1": grids["HF1"],
    }


def spatialised_null_draw(
    raw: NDArray[np.float64],
    closed_neighbours: Sequence[NDArray[np.intp]],
    *,
    draw_index: int,
) -> dict[str, Any]:
    """Permute raw vectors with seed ``42 + draw_index`` and rerun the pipeline."""
    if type(draw_index) is not int or draw_index < 0:
        raise ValueError("draw_index must be a non-negative int")
    values = np.asarray(raw, dtype=np.float64)
    permutation = np.random.default_rng(SEED + draw_index).permutation(len(values))
    return scale_coherence_statistic(values[permutation], closed_neighbours)


def empirical_tail_pvalues(
    null_values: NDArray[np.float64],
    *,
    observed: float,
) -> tuple[float, float, float]:
    """Return locked inclusive lower/upper p-values and observed percentile."""
    values = np.asarray(null_values, dtype=np.float64)
    if values.ndim != 1 or len(values) == 0 or not np.isfinite(values).all():
        raise ValueError("null_values must be a non-empty finite vector")
    if not np.isfinite(observed):
        raise ValueError("observed must be finite")
    denominator = 1 + len(values)
    p_lower = float((1 + np.count_nonzero(values <= observed)) / denominator)
    p_upper = float((1 + np.count_nonzero(values >= observed)) / denominator)
    percentile = float(100.0 * np.mean(values <= observed))
    return p_lower, p_upper, percentile


def benjamini_hochberg(p_values: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return Benjamini-Hochberg adjusted p-values in original order."""
    values = np.asarray(p_values, dtype=np.float64)
    if values.ndim != 1 or len(values) == 0:
        raise ValueError("p_values must be a non-empty vector")
    if not np.isfinite(values).all() or np.any((values < 0.0) | (values > 1.0)):
        raise ValueError("p_values must all be finite and in [0, 1]")
    order = np.argsort(values, kind="stable")
    ranked = values[order]
    ranks = np.arange(1, len(values) + 1, dtype=np.float64)
    adjusted_ranked = np.minimum.accumulate((ranked * len(values) / ranks)[::-1])[::-1]
    adjusted = np.empty_like(adjusted_ranked)
    adjusted[order] = np.minimum(adjusted_ranked, 1.0)
    return adjusted


def null_validity_record(
    observed_partitions: Sequence[NDArray[np.int64]],
    probe_partitions: Sequence[NDArray[np.int64]],
    null_values: NDArray[np.float64],
) -> dict[str, Any]:
    """Apply the promoted Spike-3 perturbation and non-degeneracy checks."""
    if len(observed_partitions) != len(probe_partitions) or not observed_partitions:
        raise ValueError("observed and probe partitions must have the same non-zero scale count")
    shapes_match = all(
        np.asarray(observed).shape == np.asarray(probe).shape
        for observed, probe in zip(observed_partitions, probe_partitions, strict=True)
    )
    partitions_perturbed = shapes_match and any(
        not np.array_equal(observed, probe)
        for observed, probe in zip(observed_partitions, probe_partitions, strict=True)
    )
    values = np.asarray(null_values, dtype=np.float64)
    if values.ndim != 1 or len(values) == 0 or not np.isfinite(values).all():
        raise ValueError("null_values must be a non-empty finite vector")
    null_standard_deviation = float(values.std())
    reasons: list[str] = []
    if not shapes_match:
        reasons.append("partition_shape_mismatch")
    elif not partitions_perturbed:
        reasons.append("partition_invariant")
    if null_standard_deviation == 0.0:
        reasons.append("zero_null_variance")
    return {
        "valid": not reasons,
        "criterion": "first draw perturbs >=1 full partition and null h1_total_area std > 0",
        "partition_shapes_match": shapes_match,
        "first_draw_partitions_perturbed": partitions_perturbed,
        "null_standard_deviation": null_standard_deviation,
        "null_unique_values": int(len(np.unique(values))),
        "reasons": reasons,
        "exclusion_is_independent_of_observed_statistic": True,
    }


def redundancy_record(
    h1_total_area: NDArray[np.float64],
    mean_ari_across_k: NDArray[np.float64],
    moran_i_pc1: NDArray[np.float64],
) -> dict[str, Any]:
    """Apply the locked two-baseline Spearman redundancy rule."""
    h1 = np.asarray(h1_total_area, dtype=np.float64)
    ari = np.asarray(mean_ari_across_k, dtype=np.float64)
    moran = np.asarray(moran_i_pc1, dtype=np.float64)
    if h1.ndim != 1 or len(h1) < 3 or ari.shape != h1.shape or moran.shape != h1.shape:
        raise ValueError("redundancy vectors must share a one-dimensional shape of length >= 3")
    if not np.isfinite(h1).all() or not np.isfinite(ari).all() or not np.isfinite(moran).all():
        raise ValueError("redundancy vectors must be finite")
    rho_ari = float(spearmanr(h1, ari).statistic)
    rho_moran = float(spearmanr(h1, moran).statistic)
    if not np.isfinite(rho_ari) or not np.isfinite(rho_moran):
        raise ValueError("redundancy correlation is undefined")
    ari_gate_passes = abs(rho_ari) < 0.95
    moran_gate_passes = abs(rho_moran) < 0.95
    return {
        "rho_h1_mean_ari_across_k": rho_ari,
        "rho_h1_moran_i_pc1": rho_moran,
        "ari_gate_passes": ari_gate_passes,
        "moran_gate_passes": moran_gate_passes,
        "redundant": not ari_gate_passes and not moran_gate_passes,
        "threshold_abs_lt": 0.95,
    }


def _require_close(actual: object, expected: float, field: str) -> None:
    if isinstance(actual, bool) or not isinstance(actual, (int, float)):
        raise ValueError(f"{field} must be numeric")
    if not np.isfinite(actual) or not np.isclose(float(actual), expected, rtol=0.0, atol=1e-12):
        raise ValueError(f"{field} is not recomputable from authoritative values")


def _direction_vs_base_rate(fraction: float) -> str:
    if fraction > ALPHA:
        return "above"
    if fraction < ALPHA:
        return "below"
    return "equal"


def validate_result_payload(payload: dict[str, Any]) -> None:
    """Validate the locked result schema and recompute inference from draws."""
    required = {
        "schema_version",
        "input_sha256",
        "params",
        "lad_family",
        "lad_results",
        "sensitivity_excluding_spike_lads",
        "decision",
        "provenance",
    }
    if not isinstance(payload, dict):
        raise ValueError("result payload must be a dict")
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"missing required result keys: {sorted(missing)}")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"schema_version must equal {SCHEMA_VERSION}")
    if payload["input_sha256"] != {
        "imd2025_file7": IMD_SHA256,
        "lsoa_boundaries": LSOA_SHA256,
    }:
        raise ValueError("input_sha256 does not match the locked inputs")

    provenance = payload["provenance"]
    if not isinstance(provenance, dict):
        raise ValueError("provenance must be a dict")
    git_commit = provenance.get("git_commit")
    if (
        not isinstance(git_commit, str)
        or len(git_commit) != 40
        or any(char not in "0123456789abcdef" for char in git_commit)
    ):
        raise ValueError("provenance.git_commit must be a full lowercase Git SHA")
    if (
        provenance.get("pre_registration_sha256") != "4038ceb802d5a5185da1fde858d29e1147ac502e8c1178c1b4b366848c5f6bac"
        or provenance.get("pre_registration_json_sha256")
        != "fa1af694c4e740acd63ef591ec2b53e03e93b6bfc35ec1a79d9ce9ed45398a66"
    ):
        raise ValueError("provenance pre-registration hashes do not match the locked design")
    inputs = provenance.get("inputs")
    expected_inputs = {
        "imd2025_file7": {
            "path": "data/imd2025_file7.csv",
            "sha256": IMD_SHA256,
        },
        "lsoa_boundaries": {
            "path": "data/lsoa_dec_2021_bgc_v5.geojson",
            "sha256": LSOA_SHA256,
            "source": "ONS Open Geography Portal item 68515293204e43ca8ab56fa13ae8a547",
            "downloaded_at": "2026-07-10",
            "license": "OGL v3.0",
        },
    }
    if inputs != expected_inputs:
        raise ValueError("provenance.inputs must record the locked paths, hashes, and boundary source")

    params = payload["params"]
    expected_params = {
        "B": B_LOCKED,
        "seed": SEED,
        "per_draw_seeds": "42+b for b=0..998",
        "ks": list(KS),
        "lad_floor": LAD_FLOOR,
        "test": "one-sided-lower",
        "alpha": ALPHA,
        "fdr_method": "benjamini-hochberg",
    }
    if not isinstance(params, dict):
        raise ValueError("params must be a dict")
    for key, expected in expected_params.items():
        if type(params.get(key)) is not type(expected) or params.get(key) != expected:
            raise ValueError(f"params.{key} must equal {expected!r} with exact type")
    if type(params.get("workers")) is not int or params["workers"] < 8:
        raise ValueError("params.workers must be an int >= 8")

    family = payload["lad_family"]
    rows = payload["lad_results"]
    if not isinstance(family, dict) or not isinstance(rows, list) or not rows:
        raise ValueError("lad_family and non-empty lad_results are required")
    members = family.get("members")
    if type(family.get("eligible_count")) is not int or not isinstance(members, list):
        raise ValueError("lad_family count and members have invalid types")
    if family["eligible_count"] != len(members) or len(members) != len(rows):
        raise ValueError("BH family size must equal the recorded LAD list and results length")
    member_identity = [(m.get("lad_code"), m.get("lad_name"), m.get("n_lsoas")) for m in members]
    row_identity = [(r.get("lad_code"), r.get("lad_name"), r.get("n_lsoas")) for r in rows]
    if member_identity != row_identity or len({identity[0] for identity in member_identity}) != len(rows):
        raise ValueError("lad_results must match the frozen LAD family exactly and uniquely")

    execution = provenance.get("staged_execution")
    if not isinstance(execution, dict) or execution.get("all_batches_complete") is not True:
        raise ValueError("provenance.staged_execution must record complete execution")
    if execution.get("mode") == "staged":
        plan = execution.get("plan")
        artifacts = execution.get("batch_artifacts")
        if (
            not isinstance(plan, dict)
            or plan.get("family_sha256") != family.get("family_sha256")
            or not isinstance(plan.get("path"), str)
            or not isinstance(plan.get("sha256"), str)
            or len(plan["sha256"]) != 64
            or any(char not in "0123456789abcdef" for char in plan["sha256"])
            or plan.get("approval", {}).get("approved_by") != "User"
            or plan.get("approval", {}).get("instruction") != "Approve staged launch"
        ):
            raise ValueError("staged execution plan provenance is invalid")
        if not isinstance(artifacts, list) or [item.get("batch_index") for item in artifacts] != [1, 2, 3]:
            raise ValueError("staged execution must bind exactly batches 1, 2, and 3")
        if sum(item.get("member_count", -1) for item in artifacts) != len(rows):
            raise ValueError("staged batch member counts do not cover the result family")
        if any(
            not isinstance(item.get("path"), str)
            or not isinstance(item.get("sha256"), str)
            or len(item["sha256"]) != 64
            or any(char not in "0123456789abcdef" for char in item["sha256"])
            for item in artifacts
        ):
            raise ValueError("staged batch paths and hashes are invalid")
        if execution.get("inference_deferred_until_all_batches_complete") is not True:
            raise ValueError("staged inference deferral must be recorded")
    elif execution.get("mode") != "single-launch":
        raise ValueError("provenance.staged_execution.mode is invalid")

    p_lower_values: list[float] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or type(row.get("n_lsoas")) is not int or row["n_lsoas"] < LAD_FLOOR:
            raise ValueError(f"lad_results[{index}] has invalid LAD identity/count")
        observed = row.get("observed")
        null_values = np.asarray(row.get("null_h1_total_area"), dtype=np.float64)
        if not isinstance(observed, dict) or null_values.shape != (B_LOCKED,) or not np.isfinite(null_values).all():
            raise ValueError(f"lad_results[{index}] must store exactly {B_LOCKED} finite null values")
        observed_h1 = observed.get("h1_total_area")
        if isinstance(observed_h1, bool) or not isinstance(observed_h1, (int, float)) or not np.isfinite(observed_h1):
            raise ValueError(f"lad_results[{index}].observed.h1_total_area must be finite")
        p_lower, p_upper, percentile = empirical_tail_pvalues(null_values, observed=float(observed_h1))
        _require_close(row.get("p_lower"), p_lower, f"lad_results[{index}].p_lower")
        _require_close(row.get("p_upper"), p_upper, f"lad_results[{index}].p_upper")
        summary = row.get("null_summary")
        if not isinstance(summary, dict):
            raise ValueError(f"lad_results[{index}].null_summary must be a dict")
        _require_close(summary.get("mean"), float(null_values.mean()), f"lad_results[{index}].null_summary.mean")
        _require_close(
            summary.get("standard_deviation"),
            float(null_values.std()),
            f"lad_results[{index}].null_summary.standard_deviation",
        )
        _require_close(
            summary.get("observed_percentile"),
            percentile,
            f"lad_results[{index}].null_summary.observed_percentile",
        )
        validity = row.get("null_validity")
        if not isinstance(validity, dict) or validity.get("valid") is not True:
            raise ValueError(f"lad_results[{index}] lacks a passing null-validity record")
        rho_ari = row.get("rho_h1_mean_ari_across_k")
        rho_moran = row.get("rho_h1_moran_i_pc1")
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (rho_ari, rho_moran)):
            raise ValueError(f"lad_results[{index}] redundancy correlations must be numeric")
        redundant = abs(float(rho_ari)) >= 0.95 and abs(float(rho_moran)) >= 0.95
        if row.get("redundant") is not redundant:
            raise ValueError(f"lad_results[{index}].redundant conflicts with the locked two-gate rule")
        p_lower_values.append(p_lower)

    adjusted = benjamini_hochberg(np.asarray(p_lower_values, dtype=np.float64))
    rejects: list[bool] = []
    for index, (row, expected_q) in enumerate(zip(rows, adjusted, strict=True)):
        _require_close(row.get("p_fdr"), float(expected_q), f"lad_results[{index}].p_fdr")
        rejects_fdr = bool(expected_q <= ALPHA)
        if row.get("rejects_lower_fdr") is not rejects_fdr:
            raise ValueError(f"lad_results[{index}].rejects_lower_fdr is inconsistent")
        rejects.append(rejects_fdr)

    sensitivity = payload["sensitivity_excluding_spike_lads"]
    if not isinstance(sensitivity, dict) or sensitivity.get("bh_recomputed_on_reduced_family") is not True:
        raise ValueError("sensitivity must explicitly recompute BH on the reduced family")
    excluded_codes = sensitivity.get("excluded_lad_codes")
    if not isinstance(excluded_codes, list) or len(excluded_codes) != len(set(excluded_codes)):
        raise ValueError("sensitivity excluded_lad_codes must be a unique list")
    reduced_rows = [row for row in rows if row["lad_code"] not in set(excluded_codes)]
    if not reduced_rows:
        raise ValueError("sensitivity reduced family must be non-empty")
    reduced_q = benjamini_hochberg(np.asarray([row["p_lower"] for row in reduced_rows], dtype=np.float64))
    reduced_reject_count = int(np.count_nonzero(reduced_q <= ALPHA))
    reduced_fraction = reduced_reject_count / len(reduced_rows)
    primary_reject_count = int(sum(rejects))
    primary_fraction = primary_reject_count / len(rows)
    primary_direction = _direction_vs_base_rate(primary_fraction)
    reduced_direction = _direction_vs_base_rate(reduced_fraction)
    agrees = primary_direction == reduced_direction
    if sensitivity.get("family_size") != len(reduced_rows) or sensitivity.get("reject_count") != reduced_reject_count:
        raise ValueError("sensitivity counts are not recomputable")
    _require_close(sensitivity.get("coherent_fraction"), reduced_fraction, "sensitivity.coherent_fraction")
    sensitivity_rows = sensitivity.get("lad_results")
    if not isinstance(sensitivity_rows, list) or len(sensitivity_rows) != len(reduced_rows):
        raise ValueError("sensitivity.lad_results must cover the complete reduced family")
    for index, (sensitivity_row, primary_row, expected_q) in enumerate(
        zip(sensitivity_rows, reduced_rows, reduced_q, strict=True)
    ):
        if not isinstance(sensitivity_row, dict):
            raise ValueError(f"sensitivity.lad_results[{index}] must be a dict")
        expected_identity = (primary_row["lad_code"], primary_row["lad_name"], primary_row["n_lsoas"])
        actual_identity = (
            sensitivity_row.get("lad_code"),
            sensitivity_row.get("lad_name"),
            sensitivity_row.get("n_lsoas"),
        )
        if actual_identity != expected_identity:
            raise ValueError(f"sensitivity.lad_results[{index}] does not match the reduced family")
        _require_close(
            sensitivity_row.get("observed_h1_total_area"),
            float(primary_row["observed"]["h1_total_area"]),
            f"sensitivity.lad_results[{index}].observed_h1_total_area",
        )
        for field in ("p_lower", "p_upper"):
            _require_close(
                sensitivity_row.get(field),
                float(primary_row[field]),
                f"sensitivity.lad_results[{index}].{field}",
            )
        _require_close(
            sensitivity_row.get("primary_p_fdr"),
            float(primary_row["p_fdr"]),
            f"sensitivity.lad_results[{index}].primary_p_fdr",
        )
        _require_close(
            sensitivity_row.get("p_fdr"),
            float(expected_q),
            f"sensitivity.lad_results[{index}].p_fdr",
        )
        expected_reject = bool(expected_q <= ALPHA)
        if (
            sensitivity_row.get("primary_rejects_lower_fdr") is not primary_row["rejects_lower_fdr"]
            or sensitivity_row.get("rejects_lower_fdr") is not expected_reject
            or sensitivity_row.get("redundant") is not primary_row["redundant"]
        ):
            raise ValueError(f"sensitivity.lad_results[{index}] decision fields are inconsistent")
    if (
        sensitivity.get("direction_vs_null_base_rate") != reduced_direction
        or sensitivity.get("primary_direction_vs_null_base_rate") != primary_direction
        or sensitivity.get("direction_agrees") is not agrees
    ):
        raise ValueError("sensitivity direction fields are inconsistent")

    rejecting_redundant = any(reject and row["redundant"] for reject, row in zip(rejects, rows, strict=True))
    if primary_reject_count == 0:
        verdict = "negative"
    elif primary_fraction >= 0.20 and not rejecting_redundant and agrees:
        verdict = "coherence-confirmed"
    else:
        verdict = "partial-signal"
    decision = payload["decision"]
    if not isinstance(decision, dict):
        raise ValueError("decision must be a dict")
    if decision.get("verdict") != verdict:
        raise ValueError("decision.verdict conflicts with the locked rule")
    if decision.get("reject_count") != primary_reject_count or decision.get("eligible_count") != len(rows):
        raise ValueError("decision counts are inconsistent")
    _require_close(decision.get("reject_fraction"), primary_fraction, "decision.reject_fraction")
