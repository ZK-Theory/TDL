"""Contract bindings for T1.9 spanning Betti robustness outputs."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

from trajectory_tda.scripts.stage1.run_spanning_betti_robustness import (
    EPS_STARS,
    PRE_REGISTRATION,
    SCHEMA_VERSION,
    STATISTICS,
    TASK_NAME,
    dispatches_spanning_betti_robustness_json,
    validate_spanning_betti_robustness_payload,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"


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


def _representative_payload() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": "2026-06-08T00:00:00+00:00",
        "task": TASK_NAME,
        "pre_registration": PRE_REGISTRATION,
        "inputs": {
            "spanning_source": "results/trajectory_tda_full/01_trajectories.json::metadata.survey_era == 'spanning'",
            "newcomer_source": "results/trajectory_tda_full/01_trajectories.json::metadata.survey_era == 'usoc_only'",
            "knee_algorithm_source": "trajectory_tda.scripts.run_zigzag_sensitivity.detect_eps_star_knee",
            "git_head": "abc123",
        },
        "params": {
            "eps_stars": EPS_STARS,
            "eps_star_locked": 0.54,
            "seed": 42,
            "statistics": STATISTICS,
        },
        "results": [
            {
                "eps_star": eps,
                "single_eps_ratio": 1.4,
                "auc_ratio": 1.2,
                "w2_matched": 0.3,
                "newcomers_gt_spanning": True,
            }
            for eps in EPS_STARS
        ],
        "decision": {
            "consistent": True,
            "outcome": "robust",
        },
    }


def _assert_error_message(payload: dict, expected: str) -> list[str]:
    errors = validate_spanning_betti_robustness_payload(payload)
    assert any(expected in err for err in errors), errors
    return errors


def test_spanning_betti_robustness_output_schema() -> None:
    """Representative output satisfies the schema and must-assert rejection clauses."""
    payload = _representative_payload()
    assert validate_spanning_betti_robustness_payload(payload) == []

    bad = copy.deepcopy(payload)
    bad["params"]["eps_stars"] = [0.54, 0.65]
    errors = _assert_error_message(bad, "params.eps_stars")
    assert errors != []

    bad = copy.deepcopy(payload)
    bad["params"]["seed"] = 7
    errors = _assert_error_message(bad, "params.seed")
    assert errors != []

    bad = copy.deepcopy(payload)
    bad["params"]["statistics"] = ["single_eps_ratio", "auc_ratio"]
    errors = _assert_error_message(bad, "params.statistics")
    assert errors != []

    bad = copy.deepcopy(payload)
    bad["results"] = bad["results"][:-1]
    errors = _assert_error_message(bad, "one entry per locked epsilon-star")
    assert errors != []

    bad = copy.deepcopy(payload)
    bad["results"][0]["eps_star"] = bad["results"][1]["eps_star"]
    errors = _assert_error_message(bad, "one entry per locked epsilon-star")
    assert errors != []

    bad = copy.deepcopy(payload)
    bad["results"][0]["w2_matched"] = -0.1
    errors = _assert_error_message(bad, "w2_matched must be non-negative")
    assert errors != []

    bad = copy.deepcopy(payload)
    bad["decision"]["outcome"] = "divergent"
    errors = _assert_error_message(bad, "robust")
    assert errors != []

    bad = copy.deepcopy(payload)
    bad["per_call_pca"] = True
    errors = _assert_error_message(bad, "forbidden key")
    assert errors != []


def test_spanning_betti_robustness_json_validation_dispatch() -> None:
    """Dispatch only consolidated T1.9 JSONs and validate matched on-disk payloads."""
    output_validation = _load_contract(
        "stage1-output-schemas/spanning-betti-robustness-output-json-validation.yaml"
    )
    ov = output_validation["output_validation"]
    glob_pattern = ov["applies_to_glob"]
    assert ov["schema_contracts"] == ["spanning-betti-robustness-output"]

    assert Path("results/trajectory_tda_spanning/knee_robustness/spanning_AUC_W2_2026-06-08.json").full_match(
        glob_pattern
    )
    assert not Path(
        "results/trajectory_tda_spanning/knee_robustness/spanning_betti_eps_054_2026-06-08.json"
    ).full_match(glob_pattern)
    assert dispatches_spanning_betti_robustness_json(
        Path("results/trajectory_tda_spanning/knee_robustness/spanning_AUC_W2_2026-06-08.json")
    )
    assert not dispatches_spanning_betti_robustness_json(
        Path("results/trajectory_tda_spanning/knee_robustness/spanning_betti_eps_054_2026-06-08.json")
    )

    for json_path in _matched_jsons(glob_pattern):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        errors = validate_spanning_betti_robustness_payload(data)
        assert not errors, f"{json_path} failed spanning robustness schema:\n  " + "\n  ".join(errors)
