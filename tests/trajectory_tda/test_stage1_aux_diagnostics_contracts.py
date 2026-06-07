# Research context: Stage-1 auxiliary-diagnostics contract bindings.
# Purpose: Verify Mapper threshold and KDE sub-level H0 output schemas and dispatch.
"""Contract bindings for Stage-1 auxiliary diagnostic outputs."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from trajectory_tda.scripts.run_stage1_aux_diagnostics import (
    MAPPER_THRESHOLDS,
    validate_kde_sublevel_payload,
    validate_mapper_threshold_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"
MAPPER_OUTPUT_GLOB = "results/trajectory_tda_integration/mapper_threshold/sub_regime_thresh_sweep_*.json"
KDE_OUTPUT_GLOB = "results/trajectory_tda_integration/density_topology/sublevel_kde_h0_*.json"


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


def _markov_payload() -> dict[str, Any]:
    results = []
    for alpha in [0, 0.5, 1, 5]:
        for dataset in ["usoc", "bhps"]:
            results.append(
                {
                    "alpha": alpha,
                    "dataset": dataset,
                    "total_persistence": 1.0,
                    "w2_obs_null": 0.5,
                    "p_value": 0.01,
                }
            )
    return {
        "schema_version": "stage1/markov2-alpha-sweep/v1",
        "generated_at": "2026-06-07T00:00:00+00:00",
        "task": "T1.8 Markov-2 alpha sensitivity sweep",
        "pre_registration": "2026-06-07 Stage-1 auxiliary-diagnostics pre-registration",
        "inputs": {
            "canonical_embedding_source": "results/trajectory_tda_integration/embeddings.npy",
            "baseline_gmm_labels_source": "results/trajectory_tda_integration/05_analysis.json[gmm_labels]",
            "n_trajectories": 27280,
            "git_head": "abc123",
        },
        "params": {
            "alphas": [0, 0.5, 1, 5],
            "L": 5000,
            "B": 1000,
            "seed": 42,
            "datasets": ["usoc", "bhps"],
            "frozen_loadings": True,
            "p_value_formula": "(r+1)/(B+1)",
        },
        "results": results,
        "stability": {"conclusion_stable": True, "canonical_alpha": 1},
    }


def _mapper_payload() -> dict[str, Any]:
    return {
        "schema_version": "stage1/mapper-threshold-sweep/v1",
        "generated_at": "2026-06-07T00:00:00+00:00",
        "task": "T1.10 Mapper threshold sensitivity sweep",
        "pre_registration": "2026-06-07 Stage-1 auxiliary-diagnostics pre-registration",
        "inputs": {
            "mapper_graph_source": "results/trajectory_tda_mapper/06_mapper_graph.json",
            "baseline_gmm_labels_source": "results/trajectory_tda_integration/05_analysis.json[gmm_labels]",
            "git_head": "abc123",
        },
        "params": {
            "z_thresholds": [1.0, 1.5, 2.0],
            "B": 1000,
            "seed": 42,
            "fdr_method": "benjamini-hochberg",
        },
        "results": [
            {"z_threshold": 1.0, "n_subregime_nodes": 3, "B": 1000, "n_bh_significant_nodes": 2},
            {"z_threshold": 1.5, "n_subregime_nodes": 2, "B": 1000, "n_bh_significant_nodes": 1},
            {"z_threshold": 2.0, "n_subregime_nodes": 1, "B": 1000, "n_bh_significant_nodes": 1},
        ],
        "high_confidence_nodes": ["node-a"],
    }


def _kde_payload(ari: float = 0.31) -> dict[str, Any]:
    return {
        "schema_version": "stage1/kde-sublevel-h0/v1",
        "generated_at": "2026-06-07T00:00:00+00:00",
        "task": "T1.11 KDE sub-level-set H0",
        "pre_registration": "2026-06-07 Stage-1 auxiliary-diagnostics pre-registration",
        "inputs": {
            "canonical_embedding_source": "results/trajectory_tda_integration/embeddings.npy",
            "baseline_gmm_labels_source": "results/trajectory_tda_integration/05_analysis.json[gmm_labels]",
            "n_trajectories": 27280,
            "git_head": "abc123",
        },
        "params": {
            "bandwidth_rule": "silverman-on-standardized-pca20-kde-fit-sample",
            "grid_resolution": 50,
            "k_prominence": 7,
            "seed": 42,
            "frozen_loadings": True,
        },
        "results": {
            "n_h0_features": 10,
            "tree_cut_k": 7,
            "ari_vs_gmm": ari,
            "substantial_recovery": ari > 0.3,
        },
    }


def _assert_no_errors(errors: list[str]) -> None:
    assert not errors, "; ".join(errors)


def test_mapper_threshold_sweep_output_schema() -> None:
    """Representative payload passes; contract-listed violations reject."""
    _assert_no_errors(validate_mapper_threshold_payload(_mapper_payload()))

    # (a) params.z_thresholds != [1.0, 1.5, 2.0] or fdr_method is not BH
    bad = _mapper_payload()
    bad["params"]["z_thresholds"] = [1.0]
    bad["params"]["fdr_method"] = "none"
    with pytest.raises(AssertionError):
        _assert_no_errors(validate_mapper_threshold_payload(bad))

    # (b) results does not have one entry per threshold
    bad = _mapper_payload()
    bad["results"] = bad["results"][:2]
    with pytest.raises(AssertionError):
        _assert_no_errors(validate_mapper_threshold_payload(bad))

    # (c) n_bh_significant_nodes greater than n_subregime_nodes or negative count
    bad = _mapper_payload()
    bad["results"][0]["n_bh_significant_nodes"] = 4
    bad["results"][1]["n_subregime_nodes"] = -1
    with pytest.raises(AssertionError):
        _assert_no_errors(validate_mapper_threshold_payload(bad))

    # (d) a forbidden key is present
    bad = _mapper_payload()
    bad["uncorrected_only"] = True
    with pytest.raises(AssertionError):
        _assert_no_errors(validate_mapper_threshold_payload(bad))


def test_mapper_threshold_sweep_json_validation_dispatch() -> None:
    output_validation = _load_contract("stage1-output-schemas/mapper-threshold-sweep-output-json-validation.yaml")
    ov = output_validation["output_validation"]
    assert ov["applies_to_glob"] == MAPPER_OUTPUT_GLOB
    assert ov["schema_contracts"] == ["mapper-threshold-sweep-output"]
    assert Path("results/trajectory_tda_integration/mapper_threshold/sub_regime_thresh_sweep_2026-06-07.json").full_match(
        ov["applies_to_glob"]
    )
    assert not Path("results/trajectory_tda_integration/mapper_threshold/sub_regime_thresh_notes_2026-06-07.json").full_match(
        ov["applies_to_glob"]
    )
    matched = _matched_jsons(ov["applies_to_glob"])
    assert matched, f"no result JSON matched dispatch glob {ov['applies_to_glob']}"
    for json_path in matched:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        _assert_no_errors(validate_mapper_threshold_payload(payload))


def test_kde_sublevel_h0_output_schema() -> None:
    """Representative payload passes; contract-listed violations reject."""
    _assert_no_errors(validate_kde_sublevel_payload(_kde_payload()))

    # (a) params.k_prominence != 7 or params.seed != 42
    bad = _kde_payload()
    bad["params"]["k_prominence"] = 6
    bad["params"]["seed"] = 99
    with pytest.raises(AssertionError):
        _assert_no_errors(validate_kde_sublevel_payload(bad))

    # (b) results.tree_cut_k != 7
    bad = _kde_payload()
    bad["results"]["tree_cut_k"] = 6
    with pytest.raises(AssertionError):
        _assert_no_errors(validate_kde_sublevel_payload(bad))

    # (c) results.ari_vs_gmm is outside [-1, 1]
    bad = _kde_payload()
    bad["results"]["ari_vs_gmm"] = 1.5
    with pytest.raises(AssertionError):
        _assert_no_errors(validate_kde_sublevel_payload(bad))

    # (d) substantial_recovery disagrees with ari_vs_gmm > 0.3
    bad = _kde_payload(ari=0.1)
    bad["results"]["substantial_recovery"] = True
    with pytest.raises(AssertionError):
        _assert_no_errors(validate_kde_sublevel_payload(bad))

    # (e) a forbidden key is present
    bad = _kde_payload()
    bad["per_call_pca"] = True
    with pytest.raises(AssertionError):
        _assert_no_errors(validate_kde_sublevel_payload(bad))


def test_kde_sublevel_h0_json_validation_dispatch() -> None:
    output_validation = _load_contract("stage1-output-schemas/kde-sublevel-h0-output-json-validation.yaml")
    ov = output_validation["output_validation"]
    assert ov["applies_to_glob"] == KDE_OUTPUT_GLOB
    assert ov["schema_contracts"] == ["kde-sublevel-h0-output"]
    assert Path("results/trajectory_tda_integration/density_topology/sublevel_kde_h0_2026-06-07.json").full_match(
        ov["applies_to_glob"]
    )
    assert not Path("results/trajectory_tda_integration/density_topology/sublevel_kde_notes_2026-06-07.json").full_match(
        ov["applies_to_glob"]
    )
    matched = _matched_jsons(ov["applies_to_glob"])
    assert matched, f"no result JSON matched dispatch glob {ov['applies_to_glob']}"
    for json_path in matched:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        _assert_no_errors(validate_kde_sublevel_payload(payload))


def test_auxiliary_payload_validators_are_pure() -> None:
    payloads = [_mapper_payload(), _kde_payload()]
    validators = [validate_mapper_threshold_payload, validate_kde_sublevel_payload]
    for payload, validator in zip(payloads, validators, strict=True):
        before = copy.deepcopy(payload)
        validator(payload)
        assert payload == before
    assert MAPPER_THRESHOLDS == [1.0, 1.5, 2.0]