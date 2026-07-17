"""Binding tests for the pre-authored T1.38 W2 gap-closure contracts."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

from scratch.w2_fallback_audit import audit_lib


CONTRACT_ROOT = Path("contracts")


def _contract(relative_path: str) -> dict[str, object]:
    return yaml.safe_load((CONTRACT_ROOT / relative_path).read_text(encoding="utf-8"))


def _valid_payload() -> dict[str, object]:
    return {
        "schema_version": "stage1/w2-gap-closure/v1",
        "generated_at": "2026-07-16T00:00:00+00:00",
        "task": "T1.38 test",
        "phase": "phase1",
        "pre_registration": "pre_registrations_w2_gap_closure_2026-07-15.json",
        "solver": {"name": "gudhi.wasserstein", "exact": True, "pot_available": True, "order": 2, "internal_p": 2},
        "params": {"seed": 42, "frozen_loadings": True, "p_value_formula": "(r+1)/(B+1)"},
        "inputs": {"git_head": "abc"},
        "convention_gate": {
            "reference_freshly_recomputed": True,
            "reference_source": "fresh recomputation",
            "artifact_under_test": "artifact.json",
            "absdiff": 0.0,
            "tol": 1e-9,
        },
        "diagonal_bound_screen": {"n_values_screened": 1, "n_violations": 0, "max_ratio_to_bound": 1.0, "tol": 1e-10},
        "cost_model": {
            "n_units_benchmarked": 8,
            "median_seconds_per_unit": 1.0,
            "min_seconds_per_unit": 0.5,
            "max_seconds_per_unit": 2.0,
            "projected_wall_hours": 1.0,
        },
    }


def _validate_payload(payload: dict[str, object]) -> None:
    solver = payload["solver"]
    params = payload["params"]
    gate = payload["convention_gate"]
    screen = payload["diagonal_bound_screen"]
    cost = payload["cost_model"]
    assert payload["phase"] in {"phase1", "phase2"}
    assert payload["inputs"]["git_head"]
    assert solver["exact"] is True and solver["pot_available"] is True
    assert solver["order"] == 2 and solver["internal_p"] == 2
    assert params == {"seed": 42, "frozen_loadings": True, "p_value_formula": "(r+1)/(B+1)"}
    assert gate["reference_freshly_recomputed"] is True
    assert gate["reference_source"] != gate["artifact_under_test"]
    assert gate["tol"] > 0 and gate["absdiff"] >= 0
    assert screen["n_violations"] == 0 and screen["max_ratio_to_bound"] <= 1.0 + screen["tol"]
    assert cost["n_units_benchmarked"] >= 8
    assert all(cost[key] > 0 for key in ("median_seconds_per_unit", "min_seconds_per_unit", "max_seconds_per_unit"))
    assert "greedy_fallback_used" not in payload and "per_call_pca" not in payload


def test_w2_gap_closure_output_schema() -> None:
    contract = _contract("tda-output-schemas/w2-gap-closure-output.yaml")
    assert contract["pending"] is False
    payload = _valid_payload()
    _validate_payload(payload)
    bad_exact = _valid_payload()
    bad_exact["solver"].update(exact=False)
    with pytest.raises(AssertionError):
        _validate_payload(bad_exact)
    bad_pot = _valid_payload()
    bad_pot["solver"].update(pot_available=False)
    with pytest.raises(AssertionError):
        _validate_payload(bad_pot)
    bad_order = _valid_payload()
    bad_order["solver"].update(order=1)
    with pytest.raises(AssertionError):
        _validate_payload(bad_order)
    bad_seed = _valid_payload()
    bad_seed["params"].update(seed=41)
    with pytest.raises(AssertionError):
        _validate_payload(bad_seed)
    stale_reference = _valid_payload()
    stale_reference["convention_gate"].update(reference_freshly_recomputed=False)
    with pytest.raises(AssertionError):
        _validate_payload(stale_reference)
    bound_violation = _valid_payload()
    bound_violation["diagonal_bound_screen"].update(n_violations=1)
    with pytest.raises(AssertionError):
        _validate_payload(bound_violation)
    too_few_benchmarks = _valid_payload()
    too_few_benchmarks["cost_model"].update(n_units_benchmarked=7)
    with pytest.raises(AssertionError):
        _validate_payload(too_few_benchmarks)
    forbidden_key = _valid_payload()
    forbidden_key["greedy_fallback_used"] = True
    with pytest.raises(AssertionError):
        _validate_payload(forbidden_key)


def test_w2_exact_diagonal_bound_invariant() -> None:
    contract = _contract("tda-formulas/w2-exact-diagonal-bound.yaml")
    assert contract["pending"] is False
    a = np.array([[0.0, 4.0]])
    b = np.array([[10.0, 14.0]])
    assert audit_lib.diagonal_bound(a, b) == pytest.approx(np.sqrt(16.0))
    rng = np.random.default_rng(42)
    for _ in range(20):
        left = np.column_stack((rng.uniform(0, 5, 4), rng.uniform(6, 12, 4)))
        right = np.column_stack((rng.uniform(0, 5, 4), rng.uniform(6, 12, 4)))
        assert audit_lib.exact_w2(left, right) <= audit_lib.diagonal_bound(left, right) + 1e-10
    greedy = audit_lib.greedy_w2(a, b)
    assert greedy > audit_lib.diagonal_bound(a, b)  # negative control: screen fires
    with pytest.raises(AssertionError):
        assert greedy <= audit_lib.diagonal_bound(a, b)
    with pytest.raises(AssertionError):
        assert greedy + 1.0 <= audit_lib.diagonal_bound(a, b)
    with pytest.raises(AssertionError):
        assert greedy + 2.0 <= audit_lib.diagonal_bound(a, b)
    with pytest.raises(AssertionError):
        assert greedy + 3.0 <= audit_lib.diagonal_bound(a, b)
    with pytest.raises(AssertionError):
        assert greedy + 4.0 <= audit_lib.diagonal_bound(a, b)
    assert audit_lib.diagonal_bound(np.empty((0, 2)), np.empty((0, 2))) == 0.0
    assert audit_lib.exact_w2(np.empty((0, 2)), np.empty((0, 2))) == 0.0


def test_w2_gap_closure_convention_gate_invariant() -> None:
    contract = _contract("tda-formulas/w2-gap-closure-convention-gate.yaml")
    assert contract["pending"] is False
    payload = _valid_payload()
    _validate_payload(payload)
    payload["convention_gate"]["reference_source"] = payload["convention_gate"]["artifact_under_test"]
    with pytest.raises(AssertionError):
        _validate_payload(payload)  # negative control: copied self-reference is rejected
    missing_absdiff = _valid_payload()
    del missing_absdiff["convention_gate"]["absdiff"]
    with pytest.raises(KeyError):
        _validate_payload(missing_absdiff)
    nonpositive_tolerance = _valid_payload()
    nonpositive_tolerance["convention_gate"]["tol"] = 0.0
    with pytest.raises(AssertionError):
        _validate_payload(nonpositive_tolerance)
    false_recompute = _valid_payload()
    false_recompute["convention_gate"]["reference_freshly_recomputed"] = False
    with pytest.raises(AssertionError):
        _validate_payload(false_recompute)
    scattered_births_a = np.array([[0.0, 4.0]])
    scattered_births_b = np.array([[10.0, 14.0]])
    assert audit_lib.exact_w2(scattered_births_a, scattered_births_b) != audit_lib.greedy_w2(
        scattered_births_a, scattered_births_b
    )
