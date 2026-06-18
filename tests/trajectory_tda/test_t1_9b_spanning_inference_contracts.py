"""Contract bindings for T1.9b spanning Betti inference outputs."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

from trajectory_tda.scripts.stage1.run_spanning_betti_inference import (
    DEFAULT_B,
    DEFAULT_MATCHED_N,
    DEFAULT_SEED,
    EPS_STAR_LOCKED,
    EPS_STARS,
    P_VALUE_FORMULA,
    P_VALUE_METHOD,
    PRE_REGISTRATION,
    SCHEMA_VERSION,
    STATISTICS,
    TASK_NAME,
    dispatches_spanning_betti_inference_json,
    summarize_inference,
    validate_spanning_betti_inference_payload,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"
EPS_KEYS = [f"{eps:.2f}" for eps in EPS_STARS]


def _load_contract(rel_path: str) -> dict:
    path = CONTRACTS_DIR / rel_path
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _matched_jsons(glob_pattern: str) -> list[Path]:
    matched: list[Path] = []
    for path in REPO_ROOT.rglob("*.json"):
        rel = path.relative_to(REPO_ROOT)
        if rel.full_match(glob_pattern):
            matched.append(path)
    return matched


def _draw(lane: str, draw_index: int, spawn_index: int) -> dict:
    return {
        "lane": lane,
        "draw_index": draw_index,
        "seed_entropy": DEFAULT_SEED,
        "seed_spawn_key": [spawn_index],
        "single_eps_ratio_by_eps": {key: 1.01 for key in EPS_KEYS},
        "auc_ratio_windowed_by_eps": {key: 1.02 for key in EPS_KEYS},
        "w2_matched": 0.5,
        "elapsed_s": 1.0,
    }


def _representative_payload() -> dict:
    observed = {
        "eps_lo": 0.12,
        "single_eps_ratio_by_eps": {key: 1.20 for key in EPS_KEYS},
        "auc_ratio_windowed_by_eps": {key: 1.25 for key in EPS_KEYS},
        "w2_matched": 2.0,
        "counts_by_eps": {
            key: {"spanning_beta0": 10, "newcomer_beta0": 12} for key in EPS_KEYS
        },
    }
    permutation = [
        _draw("permutation", idx, idx) for idx in range(DEFAULT_B)
    ]
    bootstrap = [
        {
            **_draw("bootstrap", idx, DEFAULT_B + idx),
            "single_eps_ratio_by_eps": {key: 1.18 for key in EPS_KEYS},
            "auc_ratio_windowed_by_eps": {key: 1.22 for key in EPS_KEYS},
        }
        for idx in range(DEFAULT_B)
    ]
    results, decision = summarize_inference(
        observed=observed,
        permutation_draws=permutation,
        bootstrap_draws=bootstrap,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": "2026-06-18T00:00:00+00:00",
        "task": TASK_NAME,
        "pre_registration": PRE_REGISTRATION,
        "inputs": {
            "spanning_source": "results/trajectory_tda_full/01_trajectories.json::spanning",
            "newcomer_source": "results/trajectory_tda_full/01_trajectories.json::usoc_only",
            "t19_result_source": (
                "results/trajectory_tda_spanning/knee_robustness/"
                "spanning_AUC_W2_2026-06-09.json"
            ),
            "pre_registration_source": (
                "results/trajectory_tda_spanning/knee_robustness/"
                "pre_registrations_2026-06-09.json"
            ),
            "git_head": "abc123",
        },
        "params": {
            "matched_sample_size": DEFAULT_MATCHED_N,
            "eps_stars": EPS_STARS,
            "eps_star_locked": EPS_STAR_LOCKED,
            "B_permutation": DEFAULT_B,
            "B_bootstrap": DEFAULT_B,
            "seed": DEFAULT_SEED,
            "statistics": STATISTICS,
            "p_value_formula": P_VALUE_FORMULA,
            "p_value_method": P_VALUE_METHOD,
            "dual_metric": True,
            "eps_lo": 0.12,
        },
        "observed": observed,
        "results": results,
        "per_draw": {
            "permutation": permutation,
            "bootstrap": bootstrap,
        },
        "decision": decision,
    }


def _assert_error_message(payload: dict, expected: str) -> list[str]:
    errors = validate_spanning_betti_inference_payload(payload)
    assert any(expected in err for err in errors), errors
    return errors


def test_spanning_betti_inference_output_schema() -> None:
    """Representative output satisfies the schema and must-assert clauses."""
    contract = _load_contract("stage1-output-schemas/spanning-betti-inference-output.yaml")
    assert "pending" not in contract

    payload = _representative_payload()
    assert validate_spanning_betti_inference_payload(payload) == []

    bad = copy.deepcopy(payload)
    bad["params"]["B_permutation"] = 999
    assert _assert_error_message(bad, "B_permutation") != []

    bad = copy.deepcopy(payload)
    bad["params"]["B_bootstrap"] = 999
    assert _assert_error_message(bad, "B_bootstrap") != []

    bad = copy.deepcopy(payload)
    bad["params"]["seed"] = 7
    assert _assert_error_message(bad, "params.seed") != []

    bad = copy.deepcopy(payload)
    bad["params"]["dual_metric"] = False
    assert _assert_error_message(bad, "dual_metric") != []

    bad = copy.deepcopy(payload)
    bad["params"]["eps_stars"] = [0.54, 0.65]
    assert _assert_error_message(bad, "params.eps_stars") != []

    bad = copy.deepcopy(payload)
    bad["per_draw"]["permutation"] = bad["per_draw"]["permutation"][:-1]
    assert _assert_error_message(bad, "per_draw.permutation length") != []

    bad = copy.deepcopy(payload)
    bad["results"] = bad["results"][:-1]
    assert _assert_error_message(bad, "one entry per epsilon-star") != []

    bad = copy.deepcopy(payload)
    bad["results"][0]["auc_perm_p"] = 2.0
    assert _assert_error_message(bad, "auc_perm_p must be in [0, 1]") != []

    bad = copy.deepcopy(payload)
    bad["results"][0]["auc_boot_ci"] = [1.3, 1.1]
    assert _assert_error_message(bad, "lower bound") != []

    bad = copy.deepcopy(payload)
    bad["results"][0]["w2_matched"] = -0.1
    assert _assert_error_message(bad, "w2_matched must be non-negative") != []

    bad = copy.deepcopy(payload)
    bad["decision"]["outcome"] = "unsupported"
    assert _assert_error_message(bad, "allowed outcomes") != []

    bad = copy.deepcopy(payload)
    bad["decision"]["outcome"] = "no_robust_difference"
    assert _assert_error_message(bad, "contradicts satisfied directional gates") != []

    bad = copy.deepcopy(payload)
    bad["results"][0]["single_eps_perm_p"] = 0.5
    assert _assert_error_message(bad, "does not match per_draw recomputation") != []

    bad = copy.deepcopy(payload)
    bad["per_call_pca"] = True
    assert _assert_error_message(bad, "forbidden key") != []


def test_spanning_betti_inference_json_validation_dispatch() -> None:
    """Dispatch only T1.9b inference JSONs and validate matched payloads."""
    output_validation = _load_contract(
        "stage1-output-schemas/spanning-betti-inference-output-json-validation.yaml"
    )
    assert "pending" not in output_validation
    ov = output_validation["output_validation"]
    glob_pattern = ov["applies_to_glob"]
    assert ov["schema_contracts"] == ["spanning-betti-inference-output"]

    assert Path(
        "results/trajectory_tda_spanning/knee_robustness/"
        "spanning_betti_inference_2026-06-18.json"
    ).full_match(glob_pattern)
    assert not Path(
        "results/trajectory_tda_spanning/knee_robustness/"
        "spanning_AUC_W2_2026-06-09.json"
    ).full_match(glob_pattern)
    assert not Path(
        "results/trajectory_tda_spanning/knee_robustness/"
        "spanning_betti_eps_054_2026-06-09.json"
    ).full_match(glob_pattern)
    assert dispatches_spanning_betti_inference_json(
        Path(
            "results/trajectory_tda_spanning/knee_robustness/"
            "spanning_betti_inference_2026-06-18.json"
        )
    )
    assert not dispatches_spanning_betti_inference_json(
        Path(
            "results/trajectory_tda_spanning/knee_robustness/"
            "spanning_AUC_W2_2026-06-09.json"
        )
    )

    for json_path in _matched_jsons(glob_pattern):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        errors = validate_spanning_betti_inference_payload(data)
        assert not errors, f"{json_path} failed spanning inference schema:\n  " + "\n  ".join(errors)
