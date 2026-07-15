# Research context: TDA-Research/00-Meta/Discovery/pl-time-resolved-transition-graphs-prereg-2026-07-10.md
# Purpose: Binding test for contracts/discovery-harness/pl-time-resolved-result.yaml.
#   Hermetic: operates on constructed payloads only, never on data files, so a
#   fresh worktree without the gitignored intermediates still validates the contract.
"""Binding tests for the LOCKED time-resolved persistent-Laplacian result contract."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "contracts/discovery-harness/pl-time-resolved-result.yaml"

SCHEMA_VERSION = "pl-time-resolved/v1"
B_EXPECTED = 1000
SEED_EXPECTED = 42
NULL_MODEL_EXPECTED = "markov-1-pooled"
WAVE_FLOOR_EXPECTED = 500
ALPHA = 0.05
REDUNDANCY_GATE = 0.95
VERDICTS = {"additive", "partial-signal", "redundant", "negative"}
SUBSTRATES = ("bhps", "integration")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _require_exact_type(value: object, expected: type, field: str) -> None:
    if type(value) is not expected:
        raise ValueError(f"{field} must have type {expected.__name__}")


def _require_finite_number(value: object, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    if not math.isfinite(float(value)):
        raise ValueError(f"{field} must be finite")


def _bh_adjust(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg adjusted p-values (step-up, monotonised, capped at 1).

    Re-derived independently of the battery so stored ``p_fdr`` values are checked
    rather than trusted: the verdict is a function of p_fdr, so an unchecked p_fdr
    would be an unenforced statistical claim.
    """
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running = 1.0
    for rank in range(m - 1, -1, -1):
        idx = order[rank]
        running = min(running, min(1.0, p_values[idx] * m / (rank + 1)))
        adjusted[idx] = running
    return adjusted


def _recompute_verdict(payload: dict[str, Any]) -> str:
    """Locked decision rule, recomputed from stored p_fdr and rho values."""
    nulls = payload["null_distribution"]
    redundancy = payload["redundancy"]
    ordered = [s for s in SUBSTRATES if s in nulls]
    rejects = [float(nulls[s]["p_fdr"]) <= ALPHA for s in ordered]
    gates = [
        abs(float(redundancy[s]["rho_gap_var"])) < REDUNDANCY_GATE
        and abs(float(redundancy[s]["rho_entropy_var"])) < REDUNDANCY_GATE
        for s in ordered
    ]
    if not any(rejects):
        return "negative"
    if all(rejects) and all(gates):
        return "additive"
    if sum(rejects) == 1 and gates[rejects.index(True)]:
        return "partial-signal"
    return "redundant"


def validate_pl_time_resolved_result(payload: dict[str, Any]) -> None:
    """Validate a time-resolved PL battery result against the LOCKED pre-registration.

    Raises:
        ValueError: On any contract violation.
    """
    required = {
        "schema_version",
        "substrate_sha256",
        "params",
        "eligible_waves",
        "observed",
        "null_distribution",
        "redundancy",
        "decision",
    }
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"missing required top-level keys: {sorted(missing)}")

    # (b) schema_version
    _require_exact_type(payload["schema_version"], str, "schema_version")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"schema_version must equal {SCHEMA_VERSION!r}")

    # (k) substrate provenance
    sha_map = payload["substrate_sha256"]
    _require_exact_type(sha_map, dict, "substrate_sha256")
    for substrate in SUBSTRATES:
        if substrate not in sha_map:
            raise ValueError(f"substrate_sha256 missing the {substrate!r} entry")
        if not SHA256_RE.match(str(sha_map[substrate])):
            raise ValueError(f"substrate_sha256[{substrate!r}] must be a 64-hex sha256")

    # (c)(d)(e)(f) locked params
    params = payload["params"]
    _require_exact_type(params, dict, "params")
    _require_exact_type(params.get("B"), int, "params.B")
    if params["B"] != B_EXPECTED:
        raise ValueError(f"params.B must equal the pre-registered {B_EXPECTED}")
    _require_exact_type(params.get("seed"), int, "params.seed")
    if params["seed"] != SEED_EXPECTED:
        raise ValueError(f"params.seed must equal the pre-registered {SEED_EXPECTED}")
    _require_exact_type(params.get("null_model"), str, "params.null_model")
    if params["null_model"] != NULL_MODEL_EXPECTED:
        raise ValueError(f"params.null_model must equal {NULL_MODEL_EXPECTED!r}")
    _require_exact_type(params.get("wave_floor"), int, "params.wave_floor")
    if params["wave_floor"] != WAVE_FLOOR_EXPECTED:
        raise ValueError(f"params.wave_floor must equal the pre-registered {WAVE_FLOOR_EXPECTED}")

    eligible = payload["eligible_waves"]
    observed = payload["observed"]
    nulls = payload["null_distribution"]
    redundancy = payload["redundancy"]
    for name, block in (
        ("eligible_waves", eligible),
        ("observed", observed),
        ("null_distribution", nulls),
        ("redundancy", redundancy),
    ):
        _require_exact_type(block, dict, name)
        if not block:
            raise ValueError(f"{name} must not be empty")

    p_floor = 1.0 / (B_EXPECTED + 1)
    for substrate in nulls:
        obs_block = observed.get(substrate)
        if obs_block is None:
            raise ValueError(f"observed missing the {substrate!r} entry")
        null_block = nulls[substrate]

        # (g) fixed threshold grid identity across observed and null
        obs_grid = obs_block.get("grid_sha256")
        null_grid = null_block.get("grid_sha256")
        if obs_grid is None or null_grid is None:
            raise ValueError(f"{substrate}: grid_sha256 must be recorded for both observed and null")
        if obs_grid != null_grid:
            raise ValueError(
                f"{substrate}: observed grid_sha256 {obs_grid!r} differs from the null draws' grid {null_grid!r} — "
                "the locked design requires one identical grid for observed and every null draw"
            )

        # (h) two-sided p formula
        for key in ("p_lower", "p_upper", "p_two", "p_fdr"):
            _require_finite_number(null_block.get(key), f"null_distribution[{substrate}].{key}")
            value = float(null_block[key])
            if not (p_floor <= value <= 1.0):
                raise ValueError(f"null_distribution[{substrate}].{key}={value} outside [1/(B+1), 1]")
        expected_two = min(1.0, 2.0 * min(float(null_block["p_lower"]), float(null_block["p_upper"])))
        if not math.isclose(float(null_block["p_two"]), expected_two, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError(
                f"{substrate}: p_two={null_block['p_two']} does not equal min(1, 2*min(p_lower, p_upper))={expected_two}"
            )

        red_block = redundancy.get(substrate)
        if red_block is None:
            raise ValueError(f"redundancy missing the {substrate!r} entry")
        for key in ("rho_gap_var", "rho_entropy_var"):
            _require_finite_number(red_block.get(key), f"redundancy[{substrate}].{key}")
            if abs(float(red_block[key])) > 1.0:
                raise ValueError(f"redundancy[{substrate}].{key} must satisfy abs(rho) <= 1")

    # Every branch of the locked rule quantifies over BOTH substrates ("on BOTH", "on
    # exactly one"), so a partial substrate set has no defined verdict — and on a
    # single entry `all(rejects)` would vacuously return ADDITIVE off one substrate.
    if sorted(nulls) != sorted(SUBSTRATES):
        raise ValueError(
            f"null_distribution must cover exactly the locked substrates {sorted(SUBSTRATES)}, got {sorted(nulls)}"
        )

    # BH-FDR recomputed from the stored p_two values rather than trusted.
    ordered = [s for s in SUBSTRATES if s in nulls]
    recomputed_fdr = _bh_adjust([float(nulls[s]["p_two"]) for s in ordered])
    for substrate, expected in zip(ordered, recomputed_fdr):
        if not math.isclose(float(nulls[substrate]["p_fdr"]), expected, rel_tol=1e-9, abs_tol=1e-12):
            raise ValueError(
                f"null_distribution[{substrate}].p_fdr={nulls[substrate]['p_fdr']} does not match BH-FDR "
                f"recomputed from the stored p_two values ({expected})"
            )

    # (i)(j) decision
    decision = payload["decision"]
    _require_exact_type(decision, dict, "decision")
    verdict = decision.get("verdict")
    if verdict not in VERDICTS:
        raise ValueError(f"decision.verdict must be one of {sorted(VERDICTS)}")
    recomputed = _recompute_verdict(payload)
    if verdict != recomputed:
        raise ValueError(
            f"decision.verdict {verdict!r} is inconsistent with the locked rule (recomputed {recomputed!r})"
        )


def _valid_payload() -> dict[str, Any]:
    """A conforming payload: both substrates reject, gates pass -> additive."""
    grid_sha = "a" * 64
    return {
        "schema_version": SCHEMA_VERSION,
        "substrate_sha256": {
            "bhps": "b5328c83edfb82bfd8e5e5b14e8df18fbc3d595f1e7dec4bd4f602f581d40490",
            "integration": "7a4869170bb8c0f096c407a636ec09ee1926946372b27c18762734d96059e3b8",
        },
        "params": {"B": 1000, "seed": 42, "null_model": "markov-1-pooled", "wave_floor": 500},
        "eligible_waves": {
            "bhps": {"0": 5200, "1": 5000, "2": 4800, "3": 4600, "4": 4400},
            "integration": {"0": 9000, "1": 8800, "2": 8600, "3": 8400, "4": 8200},
        },
        "observed": {
            "bhps": {"ifa_t": [0.1, 0.2, 0.3, 0.4, 0.5], "var_ifa": 0.02, "grid_length": 120, "grid_sha256": grid_sha},
            "integration": {
                "ifa_t": [0.2, 0.3, 0.4, 0.5, 0.6],
                "var_ifa": 0.03,
                "grid_length": 140,
                "grid_sha256": grid_sha,
            },
        },
        "null_distribution": {
            "bhps": {
                "var_ifa_draws": [0.001, 0.002],
                "grid_sha256": grid_sha,
                "null_mean": 0.0015,
                "null_std": 0.0005,
                "p_lower": 1.0,
                "p_upper": 0.000999000999000999,
                "p_two": 0.001998001998001998,
                "p_fdr": 0.001998001998001998,
            },
            "integration": {
                "var_ifa_draws": [0.001, 0.002],
                "grid_sha256": grid_sha,
                "null_mean": 0.0015,
                "null_std": 0.0005,
                "p_lower": 1.0,
                "p_upper": 0.000999000999000999,
                "p_two": 0.001998001998001998,
                "p_fdr": 0.001998001998001998,
            },
        },
        "redundancy": {
            "bhps": {"rho_gap_var": 0.09, "rho_entropy_var": 0.25},
            "integration": {"rho_gap_var": 0.11, "rho_entropy_var": 0.30},
        },
        "decision": {"verdict": "additive", "rationale": "both substrates reject with gates passing"},
    }


def test_contract_file_matches_the_binding() -> None:
    """The contract on disk must point at this test function and pin these values."""
    contract = yaml.safe_load(CONTRACT_PATH.read_text())

    assert contract["id"] == "pl-time-resolved-result"
    assert contract["kind"] == "schema"
    assert contract["binding"]["test_file"] == "tests/discovery/test_pl_time_resolved_contract.py"
    assert contract["binding"]["test_function"] == "test_pl_time_resolved_rejects_invalid_payloads"
    assert contract["schema_def"]["applies_to"] == "results/trajectory_tda_bhps/pl_time_resolved_*.json"
    declared = {key["name"] for key in contract["schema_def"]["required_keys"]}
    assert declared == {
        "schema_version",
        "substrate_sha256",
        "params",
        "eligible_waves",
        "observed",
        "null_distribution",
        "redundancy",
        "decision",
    }


def test_pl_time_resolved_rejects_invalid_payloads() -> None:
    """Bound test for pl-time-resolved-result.

    Accepts a conforming payload and rejects each pre-registered violation.
    """
    validate_pl_time_resolved_result(_valid_payload())

    # (a) required top-level evidence is missing
    for key in (
        "schema_version",
        "substrate_sha256",
        "params",
        "eligible_waves",
        "observed",
        "null_distribution",
        "redundancy",
        "decision",
    ):
        payload = _valid_payload()
        del payload[key]
        with pytest.raises(ValueError, match="missing required top-level keys"):
            validate_pl_time_resolved_result(payload)

    # (b) schema_version differs
    payload = _valid_payload()
    payload["schema_version"] = "pl-time-resolved/v2"
    with pytest.raises(ValueError, match="schema_version must equal"):
        validate_pl_time_resolved_result(payload)

    # (c) params.B differs from 1000
    payload = _valid_payload()
    payload["params"]["B"] = 99
    with pytest.raises(ValueError, match="params.B must equal"):
        validate_pl_time_resolved_result(payload)

    # (d) params.seed differs from 42, or has the wrong type
    payload = _valid_payload()
    payload["params"]["seed"] = 1
    with pytest.raises(ValueError, match="params.seed must equal"):
        validate_pl_time_resolved_result(payload)

    payload = _valid_payload()
    payload["params"]["seed"] = "42"
    with pytest.raises(ValueError, match="params.seed must have type int"):
        validate_pl_time_resolved_result(payload)

    # (e) params.null_model differs
    payload = _valid_payload()
    payload["params"]["null_model"] = "stratified-label-permutation"
    with pytest.raises(ValueError, match="params.null_model must equal"):
        validate_pl_time_resolved_result(payload)

    # (f) params.wave_floor differs from 500
    payload = _valid_payload()
    payload["params"]["wave_floor"] = 250
    with pytest.raises(ValueError, match="params.wave_floor must equal"):
        validate_pl_time_resolved_result(payload)

    # (g) the grid recorded for observed differs from the grid recorded for the null draws
    payload = _valid_payload()
    payload["null_distribution"]["bhps"]["grid_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="differs from the null draws' grid"):
        validate_pl_time_resolved_result(payload)

    payload = _valid_payload()
    del payload["observed"]["bhps"]["grid_sha256"]
    with pytest.raises(ValueError, match="grid_sha256 must be recorded"):
        validate_pl_time_resolved_result(payload)

    # (h) p_two does not equal min(1, 2*min(p_lower, p_upper))
    payload = _valid_payload()
    payload["null_distribution"]["bhps"]["p_two"] = 0.5
    with pytest.raises(ValueError, match="does not equal min\\(1, 2\\*min"):
        validate_pl_time_resolved_result(payload)

    # p out of range
    payload = _valid_payload()
    payload["null_distribution"]["bhps"]["p_upper"] = 0.0
    with pytest.raises(ValueError, match="outside"):
        validate_pl_time_resolved_result(payload)

    # (i) verdict outside the locked vocabulary
    payload = _valid_payload()
    payload["decision"]["verdict"] = "positive"
    with pytest.raises(ValueError, match="decision.verdict must be one of"):
        validate_pl_time_resolved_result(payload)

    # (j) verdict inconsistent with the locked rule recomputed from stored values.
    # No rejections -> negative, not additive. p_two and p_fdr move together so the
    # payload stays BH-consistent and the verdict check is what fires.
    payload = _valid_payload()
    for substrate in SUBSTRATES:
        payload["null_distribution"][substrate]["p_lower"] = 0.3
        payload["null_distribution"][substrate]["p_upper"] = 0.7
        payload["null_distribution"][substrate]["p_two"] = 0.6
        payload["null_distribution"][substrate]["p_fdr"] = 0.6
    with pytest.raises(ValueError, match="inconsistent with the locked rule"):
        validate_pl_time_resolved_result(payload)

    # Rejections everywhere but a gate fails -> redundant, not additive.
    payload = _valid_payload()
    payload["redundancy"]["bhps"]["rho_gap_var"] = 0.97
    with pytest.raises(ValueError, match="inconsistent with the locked rule"):
        validate_pl_time_resolved_result(payload)

    # Exactly one substrate rejects with gates passing there -> partial-signal.
    # This mirrors the real 2026-07-15 outcome (bhps rejects, integration does not).
    payload = _valid_payload()
    payload["null_distribution"]["integration"]["p_lower"] = 0.3
    payload["null_distribution"]["integration"]["p_upper"] = 0.7
    payload["null_distribution"]["integration"]["p_two"] = 0.6
    payload["null_distribution"]["integration"]["p_fdr"] = 0.6
    payload["null_distribution"]["bhps"]["p_fdr"] = 0.003996003996003996  # BH over [0.001998, 0.6]
    with pytest.raises(ValueError, match="inconsistent with the locked rule"):
        validate_pl_time_resolved_result(payload)
    payload["decision"]["verdict"] = "partial-signal"
    validate_pl_time_resolved_result(payload)

    # A p_fdr that does not follow from the stored p_two values is rejected on its own.
    payload = _valid_payload()
    payload["null_distribution"]["bhps"]["p_fdr"] = 0.9
    with pytest.raises(ValueError, match="does not match BH-FDR"):
        validate_pl_time_resolved_result(payload)

    # A partial substrate set has no defined verdict under the locked rule.
    payload = _valid_payload()
    del payload["null_distribution"]["integration"]
    with pytest.raises(ValueError, match="must cover exactly the locked substrates"):
        validate_pl_time_resolved_result(payload)

    # (k) substrate_sha256 missing an entry
    for substrate in SUBSTRATES:
        payload = _valid_payload()
        del payload["substrate_sha256"][substrate]
        with pytest.raises(ValueError, match=f"missing the '{substrate}' entry"):
            validate_pl_time_resolved_result(payload)

    # (l) contract-pinned values supplied with the wrong type
    payload = _valid_payload()
    payload["params"]["B"] = "1000"
    with pytest.raises(ValueError, match="params.B must have type int"):
        validate_pl_time_resolved_result(payload)

    payload = _valid_payload()
    payload["params"]["wave_floor"] = 500.0
    with pytest.raises(ValueError, match="params.wave_floor must have type int"):
        validate_pl_time_resolved_result(payload)

    payload = _valid_payload()
    payload["redundancy"] = []
    with pytest.raises(ValueError, match="redundancy must have type dict"):
        validate_pl_time_resolved_result(payload)
