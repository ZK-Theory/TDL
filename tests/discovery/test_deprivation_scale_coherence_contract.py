"""Binding test for the locked deprivation scale-coherence result contract."""

from __future__ import annotations

import copy
from typing import Any

import numpy as np
import pytest

from poverty_tda.topology.deprivation_scale_coherence import (
    benjamini_hochberg,
    validate_result_payload,
)


def _row(code: str, p_lower: float, *, redundant: bool = False) -> dict[str, Any]:
    count_lower = int(round(p_lower * 1000 - 1))
    null = [0.0] * count_lower + [1.0, 2.0] * ((999 - count_lower) // 2)
    if len(null) < 999:
        null.append(1.0)
    null = null[:999]
    observed = 0.0
    p_upper = (1 + sum(value >= observed for value in null)) / 1000
    return {
        "lad_code": code,
        "lad_name": code,
        "n_lsoas": 200,
        "observed": {
            "h1_total_area": observed,
            "h1_lag1_area": 0.0,
            "h1_max": 0.0,
            "mean_ari_across_k": 0.2,
            "moran_i_pc1": 0.3,
        },
        "null_h1_total_area": null,
        "null_summary": {
            "mean": float(np.mean(null)),
            "standard_deviation": float(np.std(null)),
            "observed_percentile": float(100 * np.mean(np.asarray(null) <= observed)),
        },
        "p_lower": p_lower,
        "p_upper": p_upper,
        "p_fdr": 0.0,
        "rho_h1_mean_ari_across_k": 0.2,
        "rho_h1_moran_i_pc1": 0.3,
        "redundant": redundant,
        "rejects_lower_fdr": False,
        "null_validity": {
            "valid": True,
            "criterion": "first draw perturbs >=1 full partition and null h1_total_area std > 0",
            "partition_shapes_match": True,
            "first_draw_partitions_perturbed": True,
            "null_standard_deviation": float(np.std(null)),
            "null_unique_values": len(set(null)),
            "reasons": [],
            "exclusion_is_independent_of_observed_statistic": True,
        },
    }


def _valid_payload() -> dict[str, Any]:
    rows = [
        _row("E08000025", 0.001),
        _row("E09000001", 0.001),
        _row("E09000002", 0.5),
        _row("E09000003", 0.5),
        _row("E09000004", 0.5),
    ]
    adjusted = benjamini_hochberg(np.array([row["p_lower"] for row in rows]))
    for row, value in zip(rows, adjusted, strict=True):
        row["p_fdr"] = float(value)
        row["rejects_lower_fdr"] = bool(value <= 0.05)
    reduced_rows = rows[1:]
    reduced_adjusted = benjamini_hochberg(np.array([row["p_lower"] for row in reduced_rows]))
    sensitivity_rows = [
        {
            "lad_code": row["lad_code"],
            "lad_name": row["lad_name"],
            "n_lsoas": row["n_lsoas"],
            "observed_h1_total_area": row["observed"]["h1_total_area"],
            "p_lower": row["p_lower"],
            "p_upper": row["p_upper"],
            "primary_p_fdr": row["p_fdr"],
            "primary_rejects_lower_fdr": row["rejects_lower_fdr"],
            "p_fdr": float(q_value),
            "rejects_lower_fdr": bool(q_value <= 0.05),
            "redundant": row["redundant"],
        }
        for row, q_value in zip(reduced_rows, reduced_adjusted, strict=True)
    ]
    return {
        "schema_version": "deprivation-scale-coherence/v1",
        "input_sha256": {
            "imd2025_file7": "b1b716aa2e476449f987b9de3e08255b4794eabfd270626de5de18b2f5eff3ef",
            "lsoa_boundaries": "34d637634532b16824c576f0a297ee6ce07962b88d23aa0fd8e564c97a3d0f38",
        },
        "params": {
            "B": 999,
            "seed": 42,
            "per_draw_seeds": "42+b for b=0..998",
            "ks": [3, 5, 7, 10, 15],
            "lad_floor": 150,
            "test": "one-sided-lower",
            "alpha": 0.05,
            "fdr_method": "benjamini-hochberg",
            "workers": 8,
        },
        "lad_family": {
            "eligible_count": len(rows),
            "members": [
                {"lad_code": row["lad_code"], "lad_name": row["lad_name"], "n_lsoas": row["n_lsoas"]} for row in rows
            ],
            "excluded": [],
        },
        "lad_results": rows,
        "sensitivity_excluding_spike_lads": {
            "excluded_lad_codes": ["E08000025"],
            "bh_recomputed_on_reduced_family": True,
            "family_size": 4,
            "reject_count": 1,
            "coherent_fraction": 0.25,
            "direction_vs_null_base_rate": "above",
            "primary_direction_vs_null_base_rate": "above",
            "direction_agrees": True,
            "lad_results": sensitivity_rows,
        },
        "decision": {
            "verdict": "coherence-confirmed",
            "reject_count": 2,
            "eligible_count": 5,
            "reject_fraction": 0.4,
        },
    }


def test_scale_coherence_rejects_invalid_payloads() -> None:
    payload = _valid_payload()
    validate_result_payload(payload)

    mutations = []
    wrong_schema = copy.deepcopy(payload)
    wrong_schema["schema_version"] = "wrong"
    mutations.append(wrong_schema)
    wrong_b = copy.deepcopy(payload)
    wrong_b["params"]["B"] = 99
    mutations.append(wrong_b)
    wrong_tail = copy.deepcopy(payload)
    wrong_tail["lad_results"][0]["p_lower"] = 0.2
    mutations.append(wrong_tail)
    wrong_fdr = copy.deepcopy(payload)
    wrong_fdr["lad_results"][0]["p_fdr"] = 0.9
    mutations.append(wrong_fdr)
    wrong_verdict = copy.deepcopy(payload)
    wrong_verdict["decision"]["verdict"] = "negative"
    mutations.append(wrong_verdict)
    missing_family_member = copy.deepcopy(payload)
    missing_family_member["lad_family"]["members"].pop()
    mutations.append(missing_family_member)
    missing_sensitivity_table = copy.deepcopy(payload)
    missing_sensitivity_table["sensitivity_excluding_spike_lads"].pop("lad_results")
    mutations.append(missing_sensitivity_table)
    wrong_sensitivity_fdr = copy.deepcopy(payload)
    wrong_sensitivity_fdr["sensitivity_excluding_spike_lads"]["lad_results"][0]["p_fdr"] = 0.9
    mutations.append(wrong_sensitivity_fdr)

    for invalid in mutations:
        with pytest.raises(ValueError):
            validate_result_payload(invalid)
