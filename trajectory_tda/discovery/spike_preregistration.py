# Research context: docs/plans/strategy/Discovery-Harness-Plan-16-06-2026.md
# Purpose: Validate Discovery Harness Spike pre-registration blocks against the contract.
"""Validation helpers for Discovery Harness Spike pre-registrations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA_VERSION = "discovery/spike-pre-registration/v1"
ROOT_KEYS = {
    "schema_version",
    "candidate_slug",
    "source_scorecard",
    "registered_at",
    "approval",
    "time_box_hours",
    "research_question",
    "metric_space",
    "toy_scope",
    "topology_gate",
    "null_model",
    "baselines",
    "decision_rule",
    "outcome_to_prose",
    "planned_contracts",
    "next_on_success",
    "next_on_failure",
}
APPROVAL_KEYS = {"approved", "approved_by", "approved_at"}
TOY_SCOPE_KEYS = {"dataset", "max_units", "compute_budget"}
TOPOLOGY_GATE_KEYS = {"assay_gate_passed", "feature_claim_map", "named_baseline"}
NULL_MODEL_KEYS = {"operation", "invariance_risk"}
DECISION_RULE_KEYS = {"success_criteria", "failure_criteria"}
OUTCOME_TO_PROSE_KEYS = {"success", "partial", "failure"}


def validate_spike_preregistration(payload: Mapping[str, Any]) -> None:
    """Validate the front-of-funnel Spike pre-registration seam."""
    _assert_exact_keys(payload, ROOT_KEYS, "spike_pre_registration")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise AssertionError(f"schema_version must equal {SCHEMA_VERSION!r}")

    for key in (
        "candidate_slug",
        "source_scorecard",
        "registered_at",
        "research_question",
        "metric_space",
        "next_on_failure",
    ):
        _assert_nonempty_str(payload.get(key), key)

    _validate_approval(_assert_mapping(payload["approval"], "approval"))
    _validate_time_box(payload["time_box_hours"])
    _validate_toy_scope(_assert_mapping(payload["toy_scope"], "toy_scope"))
    _validate_topology_gate(_assert_mapping(payload["topology_gate"], "topology_gate"))
    _validate_null_model(_assert_mapping(payload["null_model"], "null_model"))
    _assert_nonempty_str_list(payload["baselines"], "baselines")
    _validate_decision_rule(_assert_mapping(payload["decision_rule"], "decision_rule"))
    _validate_outcome_to_prose(_assert_mapping(payload["outcome_to_prose"], "outcome_to_prose"))
    _assert_nonempty_str_list(payload["planned_contracts"], "planned_contracts")
    if payload["next_on_success"] != "/pre-reg-to-dispatch":
        raise AssertionError("next_on_success must be /pre-reg-to-dispatch")


def _validate_approval(approval: Mapping[str, Any]) -> None:
    _assert_exact_keys(approval, APPROVAL_KEYS, "approval")
    if approval["approved"] is not True:
        raise AssertionError("approval.approved must be true before Spike execution")
    _assert_nonempty_str(approval["approved_by"], "approval.approved_by")
    _assert_nonempty_str(approval["approved_at"], "approval.approved_at")


def _validate_time_box(value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AssertionError("time_box_hours must be an integer")
    if not 1 <= value <= 4:
        raise AssertionError("time_box_hours must be between 1 and 4")


def _validate_toy_scope(scope: Mapping[str, Any]) -> None:
    _assert_exact_keys(scope, TOY_SCOPE_KEYS, "toy_scope")
    _assert_nonempty_str(scope["dataset"], "toy_scope.dataset")
    _assert_nonempty_str(scope["compute_budget"], "toy_scope.compute_budget")
    max_units = scope["max_units"]
    if isinstance(max_units, bool) or not isinstance(max_units, int) or max_units <= 0:
        raise AssertionError("toy_scope.max_units must be a positive integer")


def _validate_topology_gate(gate: Mapping[str, Any]) -> None:
    _assert_exact_keys(gate, TOPOLOGY_GATE_KEYS, "topology_gate")
    if gate["assay_gate_passed"] is not True:
        raise AssertionError("Spike requires the Assay topology gate to have passed")
    _assert_nonempty_str(gate["feature_claim_map"], "topology_gate.feature_claim_map")
    _assert_nonempty_str(gate["named_baseline"], "topology_gate.named_baseline")


def _validate_null_model(null_model: Mapping[str, Any]) -> None:
    _assert_exact_keys(null_model, NULL_MODEL_KEYS, "null_model")
    _assert_nonempty_str(null_model["operation"], "null_model.operation")
    _assert_nonempty_str(null_model["invariance_risk"], "null_model.invariance_risk")


def _validate_decision_rule(rule: Mapping[str, Any]) -> None:
    _assert_exact_keys(rule, DECISION_RULE_KEYS, "decision_rule")
    _assert_nonempty_str_list(rule["success_criteria"], "decision_rule.success_criteria")
    _assert_nonempty_str_list(rule["failure_criteria"], "decision_rule.failure_criteria")


def _validate_outcome_to_prose(mapping: Mapping[str, Any]) -> None:
    _assert_exact_keys(mapping, OUTCOME_TO_PROSE_KEYS, "outcome_to_prose")
    for key in OUTCOME_TO_PROSE_KEYS:
        _assert_nonempty_str(mapping[key], f"outcome_to_prose.{key}")


def _assert_exact_keys(payload: Mapping[str, Any], expected: set[str], label: str) -> None:
    missing = sorted(expected - set(payload))
    extra = sorted(set(payload) - expected)
    if missing:
        raise AssertionError(f"{label} missing required keys: {missing}")
    if extra:
        raise AssertionError(f"{label} has unexpected keys: {extra}")


def _assert_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AssertionError(f"{label} must be a mapping")
    return value


def _assert_nonempty_str(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise AssertionError(f"{label} must be a non-empty string")


def _assert_nonempty_str_list(value: Any, label: str) -> None:
    if isinstance(value, str) or not isinstance(value, Sequence) or not value:
        raise AssertionError(f"{label} must be a non-empty list")
    for i, item in enumerate(value):
        _assert_nonempty_str(item, f"{label}[{i}]")
