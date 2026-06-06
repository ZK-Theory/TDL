# Research context: sparse U-state six-state sensitivity contract bindings.
# Purpose: Verify the T1.25 output schema and output-validation dispatch.
"""Contract bindings for sparse U-state six-state sensitivity results."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from trajectory_tda.scripts.run_sparse_u_state_sensitivity import build_raw_ngram_features

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"
OUTPUT_GLOB = "results/panel_methodology/u_state_sensitivity/six_state_gmm_*.json"
SCHEMA_REL = "stage1-output-schemas/sparse-u-state-six-state-sensitivity-output.yaml"
OUTPUT_VALIDATION_REL = "stage1-output-schemas/sparse-u-state-six-state-sensitivity-output-json-validation.yaml"
REQUIRED_ROOT_KEYS = [
    "schema_version",
    "generated_at",
    "task",
    "pre_registration",
    "inputs",
    "params",
    "baseline_9_state",
    "variants",
    "decision_summary",
]
FORBIDDEN_ROOT_KEYS = ["single_collapse_only", "stale_pickle_labels"]
VARIANTS = ["U_to_I", "U_to_E"]
STATE_ORDER_6 = ["EL", "EM", "EH", "IL", "IM", "IH"]
RECODING_MAPS = {
    "U_to_I": {"UL": "IL", "UM": "IM", "UH": "IH"},
    "U_to_E": {"UL": "EL", "UM": "EM", "UH": "EH"},
}


def _load_contract(rel_path: str) -> dict[str, Any]:
    path = CONTRACTS_DIR / rel_path
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _matched_jsons(glob_pattern: str) -> list[Path]:
    matched: list[Path] = []
    for path in REPO_ROOT.rglob("*.json"):
        rel = path.relative_to(REPO_ROOT)
        if rel.full_match(glob_pattern):
            matched.append(path)
    return matched


def _valid_payload() -> dict[str, Any]:
    variants = []
    for name, ari in (("U_to_I", 0.91), ("U_to_E", 0.92)):
        variants.append(
            {
                "variant": name,
                "recoding_map": dict(RECODING_MAPS[name]),
                "raw_dims": 42,
                "n_bigram_dims": 36,
                "nontrivial_bigram_variance_dims": 30,
                "pca_explained_variance_20": 0.99,
                "n_components_90pct": 12,
                "n_components_95pct": 16,
                "effective_rank": 10.0,
                "gmm_primary_k": 7,
                "gmm_label_counts": {"0": 10, "1": 20},
                "ari_vs_9_state": ari,
                "ari_ge_0_9": ari >= 0.9,
                "interpretation": "Representative interpretation text.",
            }
        )
    return {
        "schema_version": "stage1/sparse-u-state-six-state-sensitivity/v1",
        "generated_at": "2026-06-06T00:00:00+00:00",
        "task": "T1.25 sparse U-state 6-state sensitivity",
        "pre_registration": "2026-06-06 sparse U-state two-collapse pre-registration",
        "inputs": {
            "canonical_sequences_json": "results/trajectory_tda_integration/01_trajectories_sequences.json",
            "canonical_analysis_json": "results/trajectory_tda_integration/05_analysis.json",
            "baseline_gmm_labels_source": "results/trajectory_tda_integration/05_analysis.json[gmm_labels]",
            "n_trajectories": 27280,
            "git_head": "abc123",
        },
        "params": {
            "collapse_variants": VARIANTS,
            "state_order_6": STATE_ORDER_6,
            "include_unigrams": True,
            "include_bigrams": True,
            "raw_dims_6": 42,
            "pca_dim": 20,
            "pca_svd_solver": "full",
            "standardize": True,
            "gmm_primary_k": 7,
            "gmm_covariance_type": "full",
            "gmm_n_init": 5,
            "gmm_max_iter": 200,
            "seed": 42,
            "ari_stability_threshold": 0.9,
        },
        "baseline_9_state": {
            "raw_dims": 90,
            "n_bigram_dims": 81,
            "label_counts": {"0": 100},
            "nontrivial_bigram_variance_dims": 70,
            "pca_explained_variance_20": 0.98,
            "n_components_90pct": 14,
            "n_components_95pct": 18,
            "effective_rank": 12.0,
        },
        "variants": variants,
        "decision_summary": {
            "all_variants_ari_ge_0_9": True,
            "any_variant_ari_below_0_9": False,
            "paper_claim_direction": "Sparse U states do not appear to drive the locked 9-state regime structure.",
            "disclosure_required": "Report robustness to both U-state collapses.",
        },
    }


def _validate_sparse_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = [key for key in REQUIRED_ROOT_KEYS if key not in payload]
    errors.extend(f"missing required key: {key}" for key in missing)
    errors.extend(f"forbidden key present: {key}" for key in FORBIDDEN_ROOT_KEYS if key in payload)
    if missing:
        return errors

    inputs = payload["inputs"]
    params = payload["params"]
    variants = payload["variants"]
    summary = payload["decision_summary"]

    if inputs.get("n_trajectories") != 27280:
        errors.append("inputs.n_trajectories must equal 27280")
    if params.get("collapse_variants") != VARIANTS:
        errors.append("params.collapse_variants must be exactly ['U_to_I', 'U_to_E']")
    if params.get("state_order_6") != STATE_ORDER_6:
        errors.append("params.state_order_6 mismatch")
    if params.get("pca_svd_solver") != "full":
        errors.append("params.pca_svd_solver must equal 'full'")
    if params.get("gmm_primary_k") != 7:
        errors.append("params.gmm_primary_k must equal 7")
    if params.get("seed") != 42:
        errors.append("params.seed must equal 42")
    if params.get("raw_dims_6") != 42:
        errors.append("params.raw_dims_6 must equal 42")

    if not isinstance(variants, list) or {row.get("variant") for row in variants} != set(VARIANTS):
        errors.append("variants must contain exactly U_to_I and U_to_E")
        return errors
    for row in variants:
        name = row["variant"]
        recoding = row.get("recoding_map", {})
        for state in ("UL", "UM", "UH"):
            if recoding.get(state) != RECODING_MAPS[name][state]:
                errors.append(f"{name}.recoding_map missing or wrong for {state}")
        if row.get("raw_dims") != 42:
            errors.append(f"{name}.raw_dims must equal 42")
        if row.get("n_bigram_dims") != 36:
            errors.append(f"{name}.n_bigram_dims must equal 36")
        if row.get("gmm_primary_k") != 7:
            errors.append(f"{name}.gmm_primary_k must equal 7")
        ari = row.get("ari_vs_9_state")
        if not isinstance(ari, (int, float)) or not -1 <= ari <= 1:
            errors.append(f"{name}.ari_vs_9_state must be in [-1, 1]")
            continue
        if row.get("ari_ge_0_9") != (ari >= 0.9):
            errors.append(f"{name}.ari_ge_0_9 disagrees with ari_vs_9_state >= 0.9")

    variant_bools = [bool(row["ari_ge_0_9"]) for row in variants]
    if summary.get("all_variants_ari_ge_0_9") != all(variant_bools):
        errors.append("decision_summary.all_variants_ari_ge_0_9 disagrees with variants")
    if summary.get("any_variant_ari_below_0_9") != any(not flag for flag in variant_bools):
        errors.append("decision_summary.any_variant_ari_below_0_9 disagrees with variants")
    direction = str(summary.get("paper_claim_direction", "")).lower()
    if "superior" in direction:
        errors.append("paper_claim_direction must not claim the 6-state model is superior")
    return errors


def _assert_valid_sparse_payload(payload: dict[str, Any]) -> None:
    errors = _validate_sparse_payload(payload)
    assert not errors, "sparse U-state schema violations: " + "; ".join(errors)


def test_sparse_u_state_feature_builder_collapses_without_mutating_global_states() -> None:
    trajectories = [["UL", "UM", "EH"], ["UH", "IL"]]
    raw = build_raw_ngram_features(trajectories, STATE_ORDER_6, RECODING_MAPS["U_to_I"])
    assert raw.shape == (2, 42)
    assert raw[0, STATE_ORDER_6.index("IL")] == pytest.approx(1 / 3)
    assert raw[0, STATE_ORDER_6.index("IM")] == pytest.approx(1 / 3)
    assert raw[0, STATE_ORDER_6.index("EH")] == pytest.approx(1 / 3)


def test_sparse_u_state_sensitivity_output_schema() -> None:
    """Representative payload passes; contract-listed violations reject."""
    _assert_valid_sparse_payload(_valid_payload())

    # (a) variants missing either U_to_I or U_to_E
    bad = _valid_payload()
    bad["variants"] = bad["variants"][:1]
    with pytest.raises(AssertionError):
        _assert_valid_sparse_payload(bad)

    # (b) inputs.n_trajectories != 27280
    bad = _valid_payload()
    bad["inputs"]["n_trajectories"] = 27279
    with pytest.raises(AssertionError):
        _assert_valid_sparse_payload(bad)

    # (c) params.pca_svd_solver != 'full' or gmm_primary_k != 7 or seed != 42
    bad = _valid_payload()
    bad["params"]["pca_svd_solver"] = "randomized"
    bad["params"]["gmm_primary_k"] = 6
    bad["params"]["seed"] = 99
    with pytest.raises(AssertionError):
        _assert_valid_sparse_payload(bad)

    # (d) variant raw_dims != 42, n_bigram_dims != 36, or missing UL/UM/UH recoding
    bad = _valid_payload()
    bad["variants"][0]["raw_dims"] = 41
    bad["variants"][0]["n_bigram_dims"] = 35
    bad["variants"][0]["recoding_map"].pop("UL")
    with pytest.raises(AssertionError):
        _assert_valid_sparse_payload(bad)

    # (e) ari_vs_9_state outside [-1, 1] or ari_ge_0_9 disagreement
    bad = _valid_payload()
    bad["variants"][0]["ari_vs_9_state"] = 1.5
    bad["variants"][1]["ari_ge_0_9"] = False
    with pytest.raises(AssertionError):
        _assert_valid_sparse_payload(bad)

    # (f) decision_summary.all_variants_ari_ge_0_9 disagrees with variant booleans
    bad = _valid_payload()
    bad["decision_summary"]["all_variants_ari_ge_0_9"] = False
    with pytest.raises(AssertionError):
        _assert_valid_sparse_payload(bad)

    # (g) a forbidden key is present
    bad = _valid_payload()
    bad["single_collapse_only"] = True
    with pytest.raises(AssertionError):
        _assert_valid_sparse_payload(bad)


def test_sparse_u_state_sensitivity_json_validation_dispatch() -> None:
    output_validation = _load_contract(OUTPUT_VALIDATION_REL)
    ov = output_validation["output_validation"]
    assert ov["applies_to_glob"] == OUTPUT_GLOB
    assert ov["schema_contracts"] == ["sparse-u-state-six-state-sensitivity-output"]
    assert Path("results/panel_methodology/u_state_sensitivity/six_state_gmm_2026-06-06.json").full_match(
        ov["applies_to_glob"]
    )
    assert not Path("results/panel_methodology/u_state_sensitivity/not_six_state_2026-06-06.json").full_match(
        ov["applies_to_glob"]
    )
    assert _load_contract(SCHEMA_REL)["binding"]["test_function"] == "test_sparse_u_state_sensitivity_output_schema"

    for json_path in _matched_jsons(ov["applies_to_glob"]):
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        _assert_valid_sparse_payload(payload)


def test_sparse_payload_validator_is_pure_for_valid_payload() -> None:
    payload = _valid_payload()
    before = copy.deepcopy(payload)
    _assert_valid_sparse_payload(payload)
    assert payload == before

