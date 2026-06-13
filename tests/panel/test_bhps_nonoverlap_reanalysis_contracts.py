# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Contract bindings for the T1.26b BHPS non-overlap re-analysis
#   result schema and JSON-validation dispatch.
"""Contract bindings for BHPS non-overlap re-analysis results."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from trajectory_tda.analysis.panel.t126b_bhps_nonoverlap_reanalysis import (
    SCHEMA_VERSION,
    TASK_NAME,
    validate_bhps_nonoverlap_reanalysis_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"
SCHEMA_REL = "panel-output-schemas/bhps-nonoverlap-reanalysis-output.yaml"
OUTPUT_VALIDATION_REL = "panel-output-schemas/bhps-nonoverlap-reanalysis-output-json-validation.yaml"
OUTPUT_GLOB = "results/panel_methodology/bhps_nonoverlap/bhps_nonoverlap_reanalysis_*.json"


def _load_contract(rel_path: str) -> dict[str, Any]:
    with (CONTRACTS_DIR / rel_path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _matched_jsons(glob_pattern: str) -> list[Path]:
    return [path for path in REPO_ROOT.rglob("*.json") if path.relative_to(REPO_ROOT).full_match(glob_pattern)]


def _sample(index: int, seed: int, d_perm: float, rejects: bool) -> dict[str, Any]:
    return {
        "subsample_index": index,
        "draw_seed": seed,
        "permutation_seed": seed,
        "n": 3202,
        "L": 5000,
        "actual_landmarks": 3202,
        "selected_index_sha256": "0" * 64,
        "h1_w2_p": 0.01 if rejects else 0.4,
        "h1_w2_rejects": rejects,
        "h1_w2_d_perm": d_perm,
        "h1_landscape_l2_p": 0.001,
        "h1_landscape_l2_rejects": True,
        "h1_landscape_l2_d_perm": 4.2,
        "h0_w2_p": 0.001,
        "h0_landscape_l2_p": 0.001,
        "metrics": {
            "h0": {"w2_p": 0.001, "w2_rejects": True, "landscape_l2_p": 0.001, "landscape_l2_rejects": True},
            "h1": {"w2_p": 0.01 if rejects else 0.4, "w2_rejects": rejects, "landscape_l2_p": 0.001, "landscape_l2_rejects": True},
        },
        "runtime_seconds": 1.0,
        "null_diagram_cache": f"cache_{index}.npz",
        "checkpoint": f"checkpoint_{index}.json",
    }


def _valid_payload() -> dict[str, Any]:
    samples = [_sample(index, 100 + index, -3.0 + index * 0.1, index < 3) for index in range(20)]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": "2026-06-09T00:00:00+00:00",
        "task": TASK_NAME,
        "pre_registration": "2026-06-09 T1.26b pre-registration amendment",
        "inputs": {
            "full_bhps_source": "results/trajectory_tda_bhps/01_trajectories.json",
            "spanning_ids_source": "results/trajectory_tda_spanning/01_trajectories.json[metadata.pidp]",
            "t126_result_source": "results/panel_methodology/bhps_nonoverlap/bhps_only_gmm_ph_2026-06-09.json",
            "baseline_bhps_headline_source": "results/trajectory_tda_bhps/stage1/bhps_headline_frozen_2026-05-28.json",
            "git_head": "abc123",
        },
        "params": {
            "matched_landmark_fraction": 0.588,
            "matched_landmark_fraction_exact": 0.5876,
            "K_subsamples": 20,
            "subsample_n": 3202,
            "B": 1000,
            "seed": 42,
            "frozen_loadings": True,
            "dual_metric": True,
            "pca_dim": 20,
            "pca_svd_solver": "full",
            "arm_a_L": 1882,
            "arm_b_L": 5000,
            "null_model": "markov-1",
            "p_value_formula": "(r+1)/(B+1)",
            "alpha_level": 0.05,
        },
        "arm_a": {
            "L": 1882,
            "actual_landmarks": 1882,
            "h1_w2_p": 0.04,
            "h1_w2_rejects": True,
            "h1_w2_d_perm": 2.1,
            "h1_landscape_l2_p": 0.001,
            "h1_landscape_l2_rejects": True,
            "h1_landscape_l2_d_perm": 5.0,
            "h0_w2_p": 0.001,
            "h0_w2_rejects": True,
            "h0_w2_d_perm": 11.0,
            "h0_landscape_l2_p": 0.001,
            "h0_landscape_l2_rejects": True,
            "h0_landscape_l2_d_perm": 4.8,
        },
        "arm_b": {
            "K": 20,
            "subsample_n": 3202,
            "L": 5000,
            "actual_landmarks": 3202,
            "per_subsample_seeds": [100 + index for index in range(20)],
            "remainder_h1_w2_d_perm": -2.85,
            "remainder_h1_w2_p": 0.995,
            "remainder_h1_landscape_l2_p": 0.001,
            "null_band": {
                "d_perm_mean": -2.05,
                "d_perm_sd": 0.61,
                "d_perm_q025": -3.1,
                "d_perm_q975": -1.0,
            },
            "remainder_within_band": True,
            "n_subsamples_h1_w2_reject": 3,
            "subsamples": samples,
        },
        "decision": {
            "overlap_specific": False,
            "outcome": "size_or_fraction_artefact",
        },
    }


def _assert_valid(payload: dict[str, Any]) -> None:
    try:
        validate_bhps_nonoverlap_reanalysis_payload(payload)
    except ValueError as exc:
        raise AssertionError(str(exc)) from exc


def test_bhps_nonoverlap_reanalysis_output_schema() -> None:
    """Representative payload passes; contract-listed violations reject."""
    _assert_valid(_valid_payload())

    bad = _valid_payload()
    bad["params"]["K_subsamples"] = 19
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    bad = _valid_payload()
    bad["params"]["subsample_n"] = 3203
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    bad = _valid_payload()
    bad["params"]["seed"] = 99
    bad["params"]["dual_metric"] = False
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    bad = _valid_payload()
    bad["arm_a"]["h1_w2_p"] = 0.20
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    bad = _valid_payload()
    bad["arm_b"]["remainder_h1_w2_d_perm"] = -4.0
    bad["arm_b"]["remainder_within_band"] = True
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    bad = _valid_payload()
    bad["arm_b"]["n_subsamples_h1_w2_reject"] = 21
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    bad = _valid_payload()
    bad["decision"]["outcome"] = "overlap_dependent"
    bad["decision"]["overlap_specific"] = True
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    bad = _valid_payload()
    bad["arm_a"]["h1_landscape_l2_p"] = 1.2
    with pytest.raises(AssertionError):
        _assert_valid(bad)

    bad = _valid_payload()
    bad["per_call_pca"] = True
    with pytest.raises(AssertionError):
        _assert_valid(bad)


def test_bhps_nonoverlap_reanalysis_json_validation_dispatch() -> None:
    """Dispatch contract targets the reanalysis glob and validates matched JSONs."""
    output_validation = _load_contract(OUTPUT_VALIDATION_REL)
    ov = output_validation["output_validation"]
    assert ov["applies_to_glob"] == OUTPUT_GLOB
    assert ov["schema_contracts"] == ["bhps-nonoverlap-reanalysis-output"]
    assert Path("results/panel_methodology/bhps_nonoverlap/bhps_nonoverlap_reanalysis_2026-06-09.json").full_match(
        ov["applies_to_glob"]
    )
    assert not Path("results/panel_methodology/bhps_nonoverlap/bhps_only_gmm_ph_2026-06-09.json").full_match(
        ov["applies_to_glob"]
    )
    assert _load_contract(SCHEMA_REL)["binding"]["test_function"] == "test_bhps_nonoverlap_reanalysis_output_schema"

    matched = _matched_jsons(ov["applies_to_glob"])
    for json_path in matched:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        validate_bhps_nonoverlap_reanalysis_payload(payload)


def test_bhps_nonoverlap_reanalysis_validator_is_pure_for_valid_payload() -> None:
    """Validator does not mutate a valid payload."""
    payload = _valid_payload()
    before = copy.deepcopy(payload)
    _assert_valid(payload)
    assert payload == before
