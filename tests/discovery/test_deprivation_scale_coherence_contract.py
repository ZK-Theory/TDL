"""Binding test for the locked deprivation scale-coherence result contract."""

from __future__ import annotations

import copy
from typing import Any

import numpy as np
import pytest

from poverty_tda.topology.deprivation_scale_coherence import (
    B_LOCKED,
    KS,
    SCHEMA_VERSION,
    SEED,
    SPIKE_LAD_CODES,
    benjamini_hochberg,
    canonical_family_sha256,
    execution_fingerprint_sha256,
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
        _row("E08000035", 0.5),
        _row("E06000065", 0.5),
        _row("E08000019", 0.5),
        _row("E06000066", 0.5),
        _row("E06000052", 0.5),
        _row("E09000001", 0.001),
    ]
    adjusted = benjamini_hochberg(np.array([row["p_lower"] for row in rows]))
    for row, value in zip(rows, adjusted, strict=True):
        row["p_fdr"] = float(value)
        row["rejects_lower_fdr"] = bool(value <= 0.05)
    reduced_rows = [row for row in rows if row["lad_code"] not in set(SPIKE_LAD_CODES)]
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
    members = [{"lad_code": row["lad_code"], "lad_name": row["lad_name"], "n_lsoas": row["n_lsoas"]} for row in rows]
    family_sha256 = canonical_family_sha256(members)
    fingerprint = {
        "schema_version": "deprivation-scale-coherence-execution/v1",
        "input_sha256": {
            "imd2025_file7": "b1b716aa2e476449f987b9de3e08255b4794eabfd270626de5de18b2f5eff3ef",
            "lsoa_boundaries": "34d637634532b16824c576f0a297ee6ce07962b88d23aa0fd8e564c97a3d0f38",
        },
        "statistic_schema_version": SCHEMA_VERSION,
        "family_sha256": family_sha256,
        "B": B_LOCKED,
        "seed": SEED,
        "per_draw_seeds": "42+b for b=0..998",
        "ks": list(KS),
        "workers": 8,
        "execution_commit": "9" * 40,
    }
    fingerprint["fingerprint_sha256"] = execution_fingerprint_sha256(fingerprint)
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
            "enumerated_count": len(rows),
            "enumerated_members": members,
            "eligible_count": len(rows),
            "family_sha256": family_sha256,
            "members": members,
            "excluded": [],
        },
        "lad_results": rows,
        "sensitivity_excluding_spike_lads": {
            "excluded_lad_codes": list(SPIKE_LAD_CODES),
            "bh_recomputed_on_reduced_family": True,
            "family_size": 1,
            "reject_count": 1,
            "coherent_fraction": 1.0,
            "direction_vs_null_base_rate": "above",
            "primary_direction_vs_null_base_rate": "above",
            "direction_agrees": True,
            "lad_results": sensitivity_rows,
        },
        "decision": {
            "verdict": "coherence-confirmed",
            "reject_count": 2,
            "eligible_count": 7,
            "reject_fraction": 2 / 7,
        },
        "provenance": {
            "git_commit": "a" * 40,
            "execution_fingerprint": fingerprint,
            "pre_registration_sha256": "4038ceb802d5a5185da1fde858d29e1147ac502e8c1178c1b4b366848c5f6bac",
            "pre_registration_json_sha256": "fa1af694c4e740acd63ef591ec2b53e03e93b6bfc35ec1a79d9ce9ed45398a66",
            "inputs": {
                "imd2025_file7": {
                    "path": "data/imd2025_file7.csv",
                    "sha256": "b1b716aa2e476449f987b9de3e08255b4794eabfd270626de5de18b2f5eff3ef",
                },
                "lsoa_boundaries": {
                    "path": "data/lsoa_dec_2021_bgc_v5.geojson",
                    "sha256": "34d637634532b16824c576f0a297ee6ce07962b88d23aa0fd8e564c97a3d0f38",
                    "source": "ONS Open Geography Portal item 68515293204e43ca8ab56fa13ae8a547",
                    "downloaded_at": "2026-07-10",
                    "license": "OGL v3.0",
                },
            },
            "staged_execution": {
                "mode": "staged",
                "plan": {
                    "path": "results/poverty_tda_mcbif/staged_launch_plan_deprivation_scale_coherence_2026-07-16.json",
                    "sha256": "b" * 64,
                    "family_sha256": family_sha256,
                    "approval": {"approved_by": "User", "instruction": "Approve staged launch"},
                    "execution_fingerprint_sha256": fingerprint["fingerprint_sha256"],
                },
                "batch_artifacts": [
                    {
                        "batch_index": index,
                        "path": f"results/poverty_tda_mcbif/.partial/deprivation_scale_coherence/staged_results/batch_{index}.json",
                        "sha256": hex_digit * 64,
                        "member_count": count,
                        "execution_fingerprint_sha256": fingerprint["fingerprint_sha256"],
                    }
                    for index, hex_digit, count in ((1, "c", 3), (2, "d", 2), (3, "e", 2))
                ],
                "all_batches_complete": True,
                "inference_deferred_until_all_batches_complete": True,
            },
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
    wrong_staged_family = copy.deepcopy(payload)
    wrong_staged_family["provenance"]["staged_execution"]["plan"]["family_sha256"] = "0" * 64
    mutations.append(wrong_staged_family)
    missing_input_path = copy.deepcopy(payload)
    missing_input_path["provenance"]["inputs"]["imd2025_file7"].pop("path")
    mutations.append(missing_input_path)
    wrong_family_hash = copy.deepcopy(payload)
    wrong_family_hash["lad_family"]["family_sha256"] = "0" * 64
    mutations.append(wrong_family_hash)
    wrong_null_validity = copy.deepcopy(payload)
    wrong_null_validity["lad_results"][0]["null_validity"]["null_unique_values"] += 1
    mutations.append(wrong_null_validity)
    non_finite_redundancy = copy.deepcopy(payload)
    non_finite_redundancy["lad_results"][0]["rho_h1_mean_ari_across_k"] = float("nan")
    mutations.append(non_finite_redundancy)
    arbitrary_sensitivity = copy.deepcopy(payload)
    arbitrary_sensitivity["sensitivity_excluding_spike_lads"]["excluded_lad_codes"] = ["E08000025"]
    mutations.append(arbitrary_sensitivity)
    wrong_execution_fingerprint = copy.deepcopy(payload)
    wrong_execution_fingerprint["provenance"]["execution_fingerprint"]["execution_commit"] = "8" * 40
    mutations.append(wrong_execution_fingerprint)

    for invalid in mutations:
        with pytest.raises(ValueError):
            validate_result_payload(invalid)
