"""Binding tests for the pre-registered MCbiF employment battery result."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "contracts/discovery-harness/mcbif-employment-result.yaml"
RESULT_GLOB = "mcbif_employment_battery_*.json"
EMBEDDINGS_PATH = REPO_ROOT / "results/trajectory_tda_integration/embeddings.npy"
SEQUENCES_PATH = REPO_ROOT / "results/trajectory_tda_integration/01_trajectories_sequences.json"
PRE_REGISTRATION = "results/trajectory_tda_mcbif/pre_registrations_2026-07-03.json"
FORBIDDEN_KEYS = {"synthetic", "placeholder", "estimated", "refit_pca"}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_exact_type(value: object, expected: type, field: str) -> None:
    if type(value) is not expected:
        raise ValueError(f"{field} must have type {expected.__name__}")


def _require_finite_number(value: object, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    if not math.isfinite(float(value)):
        raise ValueError(f"{field} must be finite")


def _find_forbidden_keys(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        found.update(FORBIDDEN_KEYS.intersection(value))
        for child in value.values():
            found.update(_find_forbidden_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_find_forbidden_keys(child))
    return found


def validate_mcbif_employment_result(payload: dict[str, Any]) -> None:
    """Validate the scientific and provenance interface of a battery result."""
    required = {
        "schema_version",
        "generated_at",
        "task",
        "pre_registration",
        "embeddings_sha256",
        "sequences_sha256",
        "null_model_construction_verified",
        "params",
        "observed",
        "null_distribution",
        "baselines",
        "decision",
    }
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"Missing required keys: {sorted(missing)}")
    forbidden = _find_forbidden_keys(payload)
    if forbidden:
        raise ValueError(f"Forbidden keys present: {sorted(forbidden)}")

    if payload["schema_version"] != "mcbif-employment/v1":
        raise ValueError("schema_version must equal mcbif-employment/v1")
    if payload["task"] != "T-MCBIF-2":
        raise ValueError("task must equal T-MCBIF-2")
    if payload["pre_registration"] != PRE_REGISTRATION:
        raise ValueError("pre_registration does not identify the locked design")
    if payload["null_model_construction_verified"] is not True:
        raise ValueError("null_model_construction_verified must be true")

    for key, path in (
        ("embeddings_sha256", EMBEDDINGS_PATH),
        ("sequences_sha256", SEQUENCES_PATH),
    ):
        value = payload[key]
        if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
            raise ValueError(f"{key} must be a 64-character SHA-256 hex digest")
        if value.lower() != _sha256(path):
            raise ValueError(f"{key} does not match the frozen file")

    params = payload["params"]
    if not isinstance(params, dict):
        raise ValueError("params must be a dictionary")
    for key in (
        "n_trajectories_eligible",
        "n_wave_positions",
        "n_valid",
        "valid_waves",
        "B",
        "seed",
        "null_model",
        "partition_method",
        "parallel_workers",
        "wall_time_hours_budget",
    ):
        if key not in params:
            raise ValueError(f"params.{key} is required")
    for key in ("n_trajectories_eligible", "n_wave_positions"):
        _require_exact_type(params[key], int, f"params.{key}")
        if params[key] <= 0:
            raise ValueError(f"params.{key} must be positive")
    _require_exact_type(params["B"], int, "params.B")
    if params["B"] < 1000:
        raise ValueError("params.B must be at least 1000")
    _require_exact_type(params["seed"], int, "params.seed")
    if params["seed"] != 42:
        raise ValueError("params.seed must equal 42")
    if params["null_model"] != "wave-label-permutation":
        raise ValueError("params.null_model must equal wave-label-permutation")
    if params["partition_method"] != "categorical":
        raise ValueError("params.partition_method must equal categorical")
    _require_exact_type(params["parallel_workers"], int, "params.parallel_workers")
    if params["parallel_workers"] < 4:
        raise ValueError("params.parallel_workers must be at least 4")
    if params["wall_time_hours_budget"] != 8:
        raise ValueError("params.wall_time_hours_budget must equal 8")
    if not isinstance(params["valid_waves"], list) or not all(
        type(wave) is int for wave in params["valid_waves"]
    ):
        raise ValueError("params.valid_waves must be a list of integers")
    if len(params["valid_waves"]) != params["n_wave_positions"]:
        raise ValueError("params.n_wave_positions must equal len(valid_waves)")
    n_valid = params["n_valid"]
    if not isinstance(n_valid, dict) or not n_valid:
        raise ValueError("params.n_valid must be a non-empty dictionary")
    if not all(isinstance(k, str) and type(v) is int and v >= 0 for k, v in n_valid.items()):
        raise ValueError("params.n_valid must map wave-index strings to non-negative integers")

    observed = payload["observed"]
    for key in ("h1_rank", "h0_rank"):
        if key not in observed:
            raise ValueError(f"observed.{key} is required")
        _require_exact_type(observed[key], int, f"observed.{key}")
        if observed[key] < 0:
            raise ValueError(f"observed.{key} must be non-negative")

    null_distribution = payload["null_distribution"]
    _require_exact_type(null_distribution.get("draws"), int, "null_distribution.draws")
    if null_distribution["draws"] < 1000:
        raise ValueError("null_distribution.draws must be at least 1000")
    for key in ("percentile_95", "percentile_99", "mean", "std"):
        _require_finite_number(null_distribution.get(key), f"null_distribution.{key}")

    baselines = payload["baselines"]
    for key in ("ari_across_waves", "conditional_entropy", "consensus_clustering"):
        if not isinstance(baselines.get(key), dict):
            raise ValueError(f"baselines.{key} must be a dictionary")

    decision = payload["decision"]
    if decision.get("verdict") not in {"additive", "redundant", "infeasible"}:
        raise ValueError("decision.verdict is invalid")
    if not isinstance(decision.get("rationale"), str) or not decision["rationale"].strip():
        raise ValueError("decision.rationale must be a non-empty string")


def _valid_payload() -> dict[str, Any]:
    return {
        "schema_version": "mcbif-employment/v1",
        "generated_at": "2026-07-04T12:00:00+00:00",
        "task": "T-MCBIF-2",
        "pre_registration": PRE_REGISTRATION,
        "embeddings_sha256": _sha256(EMBEDDINGS_PATH),
        "sequences_sha256": _sha256(SEQUENCES_PATH),
        "null_model_construction_verified": True,
        "params": {
            "n_trajectories_eligible": 13640,
            "n_wave_positions": 2,
            "n_valid": {"0": 27280, "1": 20000},
            "valid_waves": [0, 1],
            "B": 1000,
            "seed": 42,
            "null_model": "wave-label-permutation",
            "partition_method": "categorical",
            "parallel_workers": 4,
            "wall_time_hours_budget": 8,
        },
        "observed": {"h1_rank": 10, "h0_rank": 3},
        "null_distribution": {
            "draws": 1000,
            "percentile_95": 8.0,
            "percentile_99": 9.0,
            "mean": 4.0,
            "std": 1.0,
        },
        "baselines": {
            "ari_across_waves": {"mean": 0.1, "max": 0.2, "per_pair": {}},
            "conditional_entropy": {"mean": 0.5, "per_pair": {}},
            "consensus_clustering": {"mean_coassignment": 0.2, "var_coassignment": 0.1},
        },
        "decision": {"verdict": "additive", "rationale": "Contract fixture."},
    }


def _mutated(path: tuple[str, ...], value: object) -> dict[str, Any]:
    payload = copy.deepcopy(_valid_payload())
    target: dict[str, Any] = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return payload


def test_mcbif_employment_result_contract_rejects_invalid_payloads() -> None:
    """Accept a conforming result and reject every contracted violation."""
    validate_mcbif_employment_result(_valid_payload())

    with pytest.raises(ValueError, match="Missing required keys"):
        bad = _valid_payload()
        del bad["observed"]
        validate_mcbif_employment_result(bad)
    with pytest.raises(ValueError, match="Forbidden keys"):
        validate_mcbif_employment_result(_mutated(("params", "refit_pca"), True))
    with pytest.raises(ValueError, match="params.B"):
        validate_mcbif_employment_result(_mutated(("params", "B"), 999))
    with pytest.raises(ValueError, match="params.seed"):
        validate_mcbif_employment_result(_mutated(("params", "seed"), 41))
    with pytest.raises(ValueError, match="null_model"):
        validate_mcbif_employment_result(_mutated(("params", "null_model"), "row-shuffle"))
    with pytest.raises(ValueError, match="partition_method"):
        validate_mcbif_employment_result(_mutated(("params", "partition_method"), "k-means"))
    with pytest.raises(ValueError, match="parallel_workers"):
        validate_mcbif_employment_result(_mutated(("params", "parallel_workers"), 3))
    with pytest.raises(ValueError, match="null_model_construction_verified"):
        validate_mcbif_employment_result(
            _mutated(("null_model_construction_verified",), False)
        )
    with pytest.raises(ValueError, match="embeddings_sha256"):
        validate_mcbif_employment_result(_mutated(("embeddings_sha256",), "0" * 64))
    with pytest.raises(ValueError, match="sequences_sha256"):
        validate_mcbif_employment_result(_mutated(("sequences_sha256",), "0" * 64))
    with pytest.raises(ValueError, match="decision.verdict"):
        validate_mcbif_employment_result(_mutated(("decision", "verdict"), "unknown"))
    with pytest.raises(ValueError, match="must have type int"):
        validate_mcbif_employment_result(_mutated(("params", "seed"), True))


def test_mcbif_employment_contract_metadata() -> None:
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["id"] == "mcbif-employment-result"
    assert contract["kind"] == "schema"
    assert contract["pending"] is False
    assert contract["binding"]["test_file"] == (
        "tests/discovery/test_mcbif_employment_contract.py"
    )
    assert contract["binding"]["test_function"] == (
        "test_mcbif_employment_result_contract_rejects_invalid_payloads"
    )
    required = {entry["name"] for entry in contract["schema_def"]["required_keys"]}
    assert {"embeddings_sha256", "sequences_sha256", "params", "decision"} <= required


def test_mcbif_employment_committed_results_validate() -> None:
    result_dir = REPO_ROOT / "results/trajectory_tda_mcbif"
    result_files = sorted(result_dir.glob(RESULT_GLOB))
    if not result_files:
        pytest.skip("No MCbiF employment battery result exists before compute.")
    for result_file in result_files:
        payload = json.loads(result_file.read_text(encoding="utf-8"))
        validate_mcbif_employment_result(payload)
