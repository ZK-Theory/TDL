# Research context: Stage-1 T1.5 H2/positive-control/doubled-n diagnostics.
# Purpose: Binding tests for the consolidated diagnostics summary schema and
#   frozen-loadings positive-control runner.
"""Contract bindings for the T1.5 auxiliary diagnostics outputs."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

import trajectory_tda.scripts.run_positive_control as positive_control
import trajectory_tda.scripts.run_stage1_aux_diagnostics as aux_diagnostics

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"
SUMMARY_OUTPUT_GLOB = "results/trajectory_tda_integration/h2_check/diagnostics_summary_*.json"


def _validate_h2_payload(payload: dict[str, Any]) -> list[str]:
    assert hasattr(aux_diagnostics, "validate_h2_positive_control_diagnostics_payload")
    return aux_diagnostics.validate_h2_positive_control_diagnostics_payload(payload)


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


def _diagnostics_payload() -> dict[str, Any]:
    obs_h0 = [1.0 + i / 1000 for i in range(200)]
    obs_h1 = [2.0 + i / 1000 for i in range(200)]
    null_h0 = [0.5 + i / 10000 for i in range(2000)]
    null_h1 = [0.75 + i / 10000 for i in range(2000)]
    null_ph_wall_times = [60.0 + i / 100 for i in range(50)]
    pair_indices = [[i % 200, (i + 1) % 200] for i in range(2000)]
    return {
        "schema_version": "stage1/h2-positive-control-diagnostics/v1",
        "generated_at": "2026-06-08T12:00:00+00:00",
        "task": "T1.5 H2 + positive control + doubled-n W2",
        "pre_registration": "2026-05-13 H2-Check pre-registration",
        "inputs": {
            "canonical_embedding_source": "C:/Users/steph/TDL/results/trajectory_tda_integration/embeddings.npy",
            "fitted_markov1_source": "C:/Users/steph/TDL/results/trajectory_tda_integration/01_trajectories_sequences.json",
            "git_head": "abc123",
        },
        "h2_check": {
            "maxdim": 2,
            "L": 1000,
            "fallback_reason": "L=2000 exceeded the max-hours/RAM guard; used documented fallback L=1000.",
            "seed": 42,
            "B": 50,
            "markov_order": 1,
            "null": "markov-1",
            "wasserstein_order": 2,
            "wasserstein_internal_p": 2,
            "ph_method": "collapse",
            "do_cocycles": False,
            "threshold_rule": "random-500-pairwise-pdist-p75-seed42",
            "threshold_value": 19.765,
            "edge_prop_at_thresh": 0.7525,
            "candidate_tetrahedra_burden": 7.52e9,
            "observed_ph_wall_time_seconds": 61.4,
            "null_ph_wall_times_seconds": null_ph_wall_times,
            "backend_versions": {"gudhi": "3.11.0", "ripser": "0.6.14"},
            "n_h2_features": 9,
            "total_persistence_h2": 12.5,
            "markov1_null_p": 0.69,
        },
        "positive_control": {
            "null": "markov-1",
            "seed": 42,
            "frozen_loadings": True,
            "p_h0": 0.44,
            "p_h1": 0.61,
            "tolerance_band": [0.3, 0.7],
            "calibrated": True,
        },
        "doubled_n_w2": {
            "n_perms": 200,
            "n_nullnull": 2000,
            "L": 5000,
            "seed": 42,
            "markov_order": 1,
            "wasserstein_order": 2,
            "wasserstein_internal_p": 2,
            "p_value": 0.004975124378109453,
            "stable_vs_t1_2": True,
            "per_pair_w2": {
                "obs_null": {"H0": obs_h0, "H1": obs_h1},
                "null_null": {
                    "pair_draw_seed": 42,
                    "pair_indices": pair_indices,
                    "H0": null_h0,
                    "H1": null_h1,
                },
            },
        },
    }


def _assert_no_errors(errors: list[str]) -> None:
    assert not errors, "; ".join(errors)


def test_h2_positive_control_diagnostics_output_schema() -> None:
    """Representative payload passes; contract-listed violations reject."""
    _assert_no_errors(_validate_h2_payload(_diagnostics_payload()))

    bad = _diagnostics_payload()
    bad["h2_check"]["maxdim"] = 1
    with pytest.raises(AssertionError):
        _assert_no_errors(_validate_h2_payload(bad))

    bad = _diagnostics_payload()
    bad["positive_control"]["seed"] = 99
    with pytest.raises(AssertionError):
        _assert_no_errors(_validate_h2_payload(bad))

    bad = _diagnostics_payload()
    bad["positive_control"]["tolerance_band"] = [0.25, 0.75]
    with pytest.raises(AssertionError):
        _assert_no_errors(_validate_h2_payload(bad))

    bad = _diagnostics_payload()
    bad["positive_control"]["p_h1"] = 0.9
    bad["positive_control"]["calibrated"] = True
    with pytest.raises(AssertionError):
        _assert_no_errors(_validate_h2_payload(bad))

    bad = _diagnostics_payload()
    bad["doubled_n_w2"]["n_perms"] = 100
    bad["doubled_n_w2"]["n_nullnull"] = 500
    with pytest.raises(AssertionError):
        _assert_no_errors(_validate_h2_payload(bad))

    bad = _diagnostics_payload()
    bad["h2_check"]["markov1_null_p"] = 1.1
    with pytest.raises(AssertionError):
        _assert_no_errors(_validate_h2_payload(bad))

    bad = _diagnostics_payload()
    bad["doubled_n_w2"]["per_pair_w2"]["obs_null"]["H0"] = bad["doubled_n_w2"]["per_pair_w2"]["obs_null"]["H0"][:-1]
    with pytest.raises(AssertionError):
        _assert_no_errors(_validate_h2_payload(bad))

    bad = _diagnostics_payload()
    bad["doubled_n_w2"]["per_pair_w2"]["null_null"]["H1"][10] = float("nan")
    with pytest.raises(AssertionError):
        _assert_no_errors(_validate_h2_payload(bad))

    bad = _diagnostics_payload()
    bad["doubled_n_w2"]["per_pair_w2"]["null_null"]["pair_indices"][0] = [0, 0]
    with pytest.raises(AssertionError):
        _assert_no_errors(_validate_h2_payload(bad))

    bad = _diagnostics_payload()
    bad["h2_check"]["total_persistence_h2"] = -0.1
    with pytest.raises(AssertionError):
        _assert_no_errors(_validate_h2_payload(bad))

    bad = _diagnostics_payload()
    bad["h2_check"]["ph_method"] = "approximate"
    with pytest.raises(AssertionError):
        _assert_no_errors(_validate_h2_payload(bad))

    bad = _diagnostics_payload()
    bad["per_call_pca"] = True
    with pytest.raises(AssertionError):
        _assert_no_errors(_validate_h2_payload(bad))


def test_h2_positive_control_diagnostics_json_validation_dispatch() -> None:
    output_validation = _load_contract(
        "stage1-output-schemas/h2-positive-control-diagnostics-output-json-validation.yaml"
    )
    ov = output_validation["output_validation"]
    assert ov["applies_to_glob"] == SUMMARY_OUTPUT_GLOB
    assert ov["schema_contracts"] == ["h2-positive-control-diagnostics-output"]
    assert Path("results/trajectory_tda_integration/h2_check/diagnostics_summary_2026-06-08.json").full_match(
        ov["applies_to_glob"]
    )
    assert not Path("results/trajectory_tda_integration/h2_check/ph_H2_L1000_2026-06-08.json").full_match(
        ov["applies_to_glob"]
    )
    assert not Path(
        "results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_L5000_doublen_2026-06-08.json"
    ).full_match(ov["applies_to_glob"])

    for json_path in _matched_jsons(ov["applies_to_glob"]):
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        _assert_no_errors(_validate_h2_payload(payload))


def test_h2_diagnostics_payload_validator_is_pure() -> None:
    payload = _diagnostics_payload()
    before = copy.deepcopy(payload)
    _validate_h2_payload(payload)
    assert payload == before


def test_positive_control_threads_frozen_loadings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    trajectories = [["EL", "EM", "EH"], ["UL", "UM", "UH"], ["IL", "IM", "IH"]]
    model_bundle = {"scaler": object(), "reducer": object()}
    seen: dict[str, Any] = {}

    monkeypatch.setattr(
        positive_control,
        "load_checkpoint",
        lambda checkpoint_dir: (np.zeros((3, 2)), trajectories, {"pca_dim": 2, "include_bigrams": True}),
    )
    monkeypatch.setattr(
        positive_control,
        "ngram_embed",
        lambda trajs, **kwargs: (np.ones((len(trajs), 2)), {"fitted_models": model_bundle}),
    )

    def fake_markov_shuffle(trajectories, rng, markov_order=1, embed_kwargs=None, alpha=1.0, frozen_models=None):
        seen["synthetic_frozen_models"] = frozen_models
        return np.ones((len(trajectories), 2))

    def fake_permutation_test_trajectories(**kwargs):
        seen["null_frozen_models"] = kwargs.get("frozen_models")
        return {"H0": {"p_value": 0.5}, "H1": {"p_value": 0.6}}

    monkeypatch.setattr(positive_control, "_markov_shuffle", fake_markov_shuffle)
    monkeypatch.setattr(positive_control, "permutation_test_trajectories", fake_permutation_test_trajectories)

    result = positive_control.run_positive_control(
        checkpoint_dir=tmp_path,
        n_permutations=2,
        n_landmarks=3,
        seed=42,
        frozen_loadings=True,
    )

    assert seen["synthetic_frozen_models"] is model_bundle
    assert seen["null_frozen_models"] is model_bundle
    assert result["frozen_loadings"] is True
