"""Binding tests for the pre-registered C1 persistent-Laplacian Fiedler null battery."""

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
CONTRACT_PATH = REPO_ROOT / "contracts/discovery-harness/c1-pl-fiedler-null-result.yaml"
RESULT_GLOB = "c1_pl_fiedler_null_*.json"
SEQUENCES_PATH = REPO_ROOT / "results/trajectory_tda_bhps/01_trajectories_sequences.json"
PRE_REGISTRATION = "results/trajectory_tda_bhps/pre_registrations_2026-07-07.json"
PINNED_SHA256 = "b5328c83edfb82bfd8e5e5b14e8df18fbc3d595f1e7dec4bd4f602f581d40490"
BACKENDS = {"petls", "petls-pytorch", "numpy-schur-scratch"}
VERDICTS = {"positive", "marginal", "negative"}
FORBIDDEN_KEYS = {"synthetic", "placeholder", "estimated"}
N_THRESHOLDS = 35
B_EXPECTED = 1000
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


def _std(values: list[float]) -> float:
    n = len(values)
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / n)


def validate_c1_pl_fiedler_null_result(payload: dict[str, Any]) -> None:
    """Validate the scientific and provenance interface of a C1 battery result."""
    required = {
        "schema_version",
        "generated_at",
        "task",
        "pre_registration",
        "substrate_sha256",
        "backend_used",
        "null_model_construction_verified",
        "params",
        "observed",
        "null_distribution",
        "pointwise",
        "decision",
    }
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"Missing required keys: {sorted(missing)}")
    forbidden = _find_forbidden_keys(payload)
    if forbidden:
        raise ValueError(f"Forbidden keys present: {sorted(forbidden)}")

    if payload["schema_version"] != "c1-pl-fiedler-null/v1":
        raise ValueError("schema_version must equal c1-pl-fiedler-null/v1")
    if payload["task"] != "T-C1-1":
        raise ValueError("task must equal T-C1-1")
    if payload["pre_registration"] != PRE_REGISTRATION:
        raise ValueError("pre_registration does not identify the locked design")

    sha = payload["substrate_sha256"]
    if not isinstance(sha, str) or SHA256_RE.fullmatch(sha) is None:
        raise ValueError("substrate_sha256 must be a 64-character SHA-256 hex digest")
    if sha.lower() != PINNED_SHA256:
        raise ValueError("substrate_sha256 does not match the pinned frozen substrate hash")
    if SEQUENCES_PATH.exists() and sha.lower() != _sha256(SEQUENCES_PATH):
        raise ValueError("substrate_sha256 does not match the on-disk sequences file")

    if payload["backend_used"] not in BACKENDS:
        raise ValueError("backend_used must be one of petls, petls-pytorch, numpy-schur-scratch")

    if payload["null_model_construction_verified"] is not True:
        raise ValueError("null_model_construction_verified must be true")

    params = payload["params"]
    if not isinstance(params, dict):
        raise ValueError("params must be a dictionary")
    for key in ("B", "seed", "null_model", "n_filtration_thresholds", "parallel_workers"):
        if key not in params:
            raise ValueError(f"params.{key} is required")
    _require_exact_type(params["B"], int, "params.B")
    if params["B"] < B_EXPECTED:
        raise ValueError("params.B must be at least 1000")
    _require_exact_type(params["seed"], int, "params.seed")
    if params["seed"] != 42:
        raise ValueError("params.seed must equal 42")
    if params["null_model"] != "markov-1":
        raise ValueError("params.null_model must equal markov-1")
    _require_exact_type(params["n_filtration_thresholds"], int, "params.n_filtration_thresholds")
    if params["n_filtration_thresholds"] != N_THRESHOLDS:
        raise ValueError("params.n_filtration_thresholds must equal 35")
    _require_exact_type(params["parallel_workers"], int, "params.parallel_workers")
    if params["parallel_workers"] < 4:
        raise ValueError("params.parallel_workers must be at least 4")

    observed = payload["observed"]
    if not isinstance(observed, dict):
        raise ValueError("observed must be a dictionary")
    _require_finite_number(observed.get("ifa"), "observed.ifa")
    curve = observed.get("lambda1_curve")
    if not isinstance(curve, list) or len(curve) != N_THRESHOLDS:
        raise ValueError("observed.lambda1_curve must be a list of exactly 35 floats")
    for v in curve:
        _require_finite_number(v, "observed.lambda1_curve[]")

    null_distribution = payload["null_distribution"]
    if not isinstance(null_distribution, dict):
        raise ValueError("null_distribution must be a dictionary")
    _require_exact_type(null_distribution.get("draws"), int, "null_distribution.draws")
    if null_distribution["draws"] < B_EXPECTED:
        raise ValueError("null_distribution.draws must be at least 1000")
    ifa_values = null_distribution.get("ifa_values")
    if not isinstance(ifa_values, list) or len(ifa_values) != B_EXPECTED:
        raise ValueError("null_distribution.ifa_values must be a list of exactly 1000 floats")
    for v in ifa_values:
        _require_finite_number(v, "null_distribution.ifa_values[]")
    if not _std([float(v) for v in ifa_values]) > 0.0:
        raise ValueError("null_distribution.ifa_values must be non-degenerate (std > 0)")
    _require_finite_number(null_distribution.get("percentile_95"), "null_distribution.percentile_95")

    pointwise = payload["pointwise"]
    if not isinstance(pointwise, dict):
        raise ValueError("pointwise must be a dictionary")
    p_values = pointwise.get("p_values")
    if not isinstance(p_values, list) or len(p_values) != N_THRESHOLDS:
        raise ValueError("pointwise.p_values must be a list of exactly 35 floats")
    for v in p_values:
        _require_finite_number(v, "pointwise.p_values[]")
        if not 0.0 <= float(v) <= 1.0:
            raise ValueError("pointwise.p_values entries must lie in [0, 1]")
    _require_exact_type(pointwise.get("bh_fdr_survivors"), int, "pointwise.bh_fdr_survivors")
    if not 0 <= pointwise["bh_fdr_survivors"] <= N_THRESHOLDS:
        raise ValueError("pointwise.bh_fdr_survivors must lie in [0, 35]")

    decision = payload["decision"]
    if not isinstance(decision, dict):
        raise ValueError("decision must be a dictionary")
    _require_finite_number(decision.get("ifa_p_value"), "decision.ifa_p_value")
    _require_exact_type(decision.get("pointwise_bh_survivors"), int, "decision.pointwise_bh_survivors")
    if decision.get("verdict") not in VERDICTS:
        raise ValueError("decision.verdict is invalid")


def _valid_payload() -> dict[str, Any]:
    return {
        "schema_version": "c1-pl-fiedler-null/v1",
        "generated_at": "2026-07-07T12:00:00+00:00",
        "task": "T-C1-1",
        "pre_registration": PRE_REGISTRATION,
        "substrate_sha256": PINNED_SHA256,
        "backend_used": "petls",
        "null_model_construction_verified": True,
        "params": {
            "B": 1000,
            "seed": 42,
            "null_model": "markov-1",
            "n_filtration_thresholds": 35,
            "parallel_workers": 4,
            "wall_time_hours_budget": 2,
        },
        "observed": {
            "ifa": 0.131125,
            "lambda1_curve": [0.1] * 35,
        },
        "null_distribution": {
            "draws": 1000,
            "ifa_values": [0.1 + 0.0001 * i for i in range(1000)],
            "percentile_95": 0.2,
        },
        "pointwise": {
            "p_values": [0.5] * 35,
            "bh_fdr_survivors": 0,
        },
        "decision": {
            "ifa_p_value": 0.5,
            "pointwise_bh_survivors": 0,
            "verdict": "negative",
        },
    }


def _mutated(path: tuple[str, ...], value: object) -> dict[str, Any]:
    payload = copy.deepcopy(_valid_payload())
    target: dict[str, Any] = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return payload


def test_c1_pl_fiedler_null_result_contract_rejects_invalid_payloads() -> None:
    """Accept a conforming result and reject every contracted violation."""
    validate_c1_pl_fiedler_null_result(_valid_payload())

    with pytest.raises(ValueError, match="Missing required keys"):
        bad = _valid_payload()
        del bad["observed"]
        validate_c1_pl_fiedler_null_result(bad)
    with pytest.raises(ValueError, match="Forbidden keys"):
        validate_c1_pl_fiedler_null_result(_mutated(("params", "synthetic"), True))
    with pytest.raises(ValueError, match="decision.verdict"):
        validate_c1_pl_fiedler_null_result(_mutated(("decision", "verdict"), "unknown"))
    with pytest.raises(ValueError, match="substrate_sha256"):
        validate_c1_pl_fiedler_null_result(_mutated(("substrate_sha256",), "0" * 64))
    with pytest.raises(ValueError, match="substrate_sha256 must be"):
        validate_c1_pl_fiedler_null_result(_mutated(("substrate_sha256",), "deadbeef"))
    with pytest.raises(ValueError, match="params.B"):
        validate_c1_pl_fiedler_null_result(_mutated(("params", "B"), 999))
    with pytest.raises(ValueError, match="params.seed must equal"):
        validate_c1_pl_fiedler_null_result(_mutated(("params", "seed"), 41))
    with pytest.raises(ValueError, match="params.null_model"):
        validate_c1_pl_fiedler_null_result(_mutated(("params", "null_model"), "markov-2"))
    with pytest.raises(ValueError, match="backend_used"):
        validate_c1_pl_fiedler_null_result(_mutated(("backend_used",), "scipy"))
    with pytest.raises(ValueError, match="observed.lambda1_curve"):
        validate_c1_pl_fiedler_null_result(_mutated(("observed", "lambda1_curve"), [0.1] * 34))
    with pytest.raises(ValueError, match="null_model_construction_verified"):
        validate_c1_pl_fiedler_null_result(_mutated(("null_model_construction_verified",), False))
    with pytest.raises(ValueError, match="non-degenerate"):
        validate_c1_pl_fiedler_null_result(_mutated(("null_distribution", "ifa_values"), [0.1] * 1000))
    with pytest.raises(ValueError, match="ifa_values must be a list of exactly 1000"):
        validate_c1_pl_fiedler_null_result(_mutated(("null_distribution", "ifa_values"), [0.1] * 999))
    with pytest.raises(ValueError, match="params.n_filtration_thresholds"):
        validate_c1_pl_fiedler_null_result(_mutated(("params", "n_filtration_thresholds"), 34))
    with pytest.raises(ValueError, match="params.parallel_workers"):
        validate_c1_pl_fiedler_null_result(_mutated(("params", "parallel_workers"), 3))
    with pytest.raises(ValueError, match="must have type int"):
        validate_c1_pl_fiedler_null_result(_mutated(("params", "seed"), True))


def test_c1_pl_fiedler_null_contract_metadata() -> None:
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["id"] == "c1-pl-fiedler-null-result"
    assert contract["kind"] == "schema"
    assert contract["pending"] is False
    assert contract["binding"]["test_file"] == ("tests/discovery/test_c1_pl_fiedler_null_contract.py")
    assert contract["binding"]["test_function"] == ("test_c1_pl_fiedler_null_result_contract_rejects_invalid_payloads")
    required = {entry["name"] for entry in contract["schema_def"]["required_keys"]}
    assert {"substrate_sha256", "backend_used", "params", "observed", "decision"} <= required


def test_c1_pl_fiedler_null_committed_results_validate() -> None:
    result_dir = REPO_ROOT / "results/trajectory_tda_bhps"
    result_files = sorted(result_dir.glob(RESULT_GLOB))
    if not result_files:
        pytest.skip("No C1 PL Fiedler null result exists before compute.")
    for result_file in result_files:
        payload = json.loads(result_file.read_text(encoding="utf-8"))
        validate_c1_pl_fiedler_null_result(payload)
