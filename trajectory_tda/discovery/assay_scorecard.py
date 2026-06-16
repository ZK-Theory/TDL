# Research context: docs/plans/strategy/Discovery-Harness-Plan-16-06-2026.md
# Purpose: Validate Discovery Harness assay scorecard blocks against the rubric contract.
"""Validation helpers for Discovery Harness assay scorecards."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import yaml

SCHEMA_VERSION = "discovery/assay-scorecard/v1"
VALID_DECISIONS = {"PROMOTE", "PARK", "KILL"}

ROOT_KEYS = {
    "schema_version",
    "candidate_id",
    "candidate_slug",
    "assayed_at",
    "source",
    "axis1_topology_gate",
    "axis2_data_feasibility",
    "axis3_novelty_publishability",
    "decision",
    "decision_rationale",
    "next",
}
AXIS1_KEYS = {
    "passes",
    "metric_space",
    "feature_claim_map",
    "reducible_to_baseline",
    "named_baseline",
    "adversarial_null",
}
SCORED_AXIS_KEYS = {"score", "rationale"}


def extract_scorecard_block(markdown: str) -> dict[str, Any]:
    """Return the YAML payload from a fenced ``assay_scorecard`` block."""
    lines = markdown.splitlines()
    in_block = False
    block: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not in_block and stripped in {"```yaml assay_scorecard", "```assay_scorecard"}:
            in_block = True
            continue
        if in_block and stripped == "```":
            parsed = yaml.safe_load("\n".join(block))
            if not isinstance(parsed, dict):
                raise AssertionError("assay_scorecard block must parse to a mapping")
            return parsed
        if in_block:
            block.append(line)
    raise AssertionError("missing fenced assay_scorecard block")


def validate_assay_scorecard(payload: Mapping[str, Any]) -> None:
    """Validate the Discovery Harness Assay scorecard rubric invariants."""
    _assert_exact_keys(payload, ROOT_KEYS, "scorecard")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise AssertionError(f"schema_version must equal {SCHEMA_VERSION!r}")

    for key in (
        "candidate_id",
        "candidate_slug",
        "assayed_at",
        "source",
        "decision_rationale",
        "next",
    ):
        _assert_nonempty_str(payload.get(key), key)

    if "programme_fit" in payload:
        raise AssertionError("programme_fit is deliberately excluded from Assay scoring")

    axis1 = _assert_mapping(payload.get("axis1_topology_gate"), "axis1_topology_gate")
    axis2 = _assert_mapping(payload.get("axis2_data_feasibility"), "axis2_data_feasibility")
    axis3 = _assert_mapping(
        payload.get("axis3_novelty_publishability"),
        "axis3_novelty_publishability",
    )
    _validate_axis1(axis1)
    axis2_score = _validate_scored_axis(axis2, "axis2_data_feasibility")
    axis3_score = _validate_scored_axis(axis3, "axis3_novelty_publishability")

    decision = payload.get("decision")
    if decision not in VALID_DECISIONS:
        raise AssertionError(f"decision must be one of {sorted(VALID_DECISIONS)}")

    gate_passes = axis1["passes"]
    if not gate_passes and decision != "KILL":
        raise AssertionError("Axis-1 gate failure must produce decision KILL")

    if decision == "PROMOTE":
        if not gate_passes:
            raise AssertionError("PROMOTE requires Axis-1 gate pass")
        if axis2_score == 0 or axis3_score == 0 or axis2_score + axis3_score < 4:
            raise AssertionError("PROMOTE requires Axis2 + Axis3 >= 4 and neither score at 0")
        if payload["next"] != "/spike":
            raise AssertionError("PROMOTE scorecards must set next to /spike")


def _validate_axis1(axis1: Mapping[str, Any]) -> None:
    _assert_exact_keys(axis1, AXIS1_KEYS, "axis1_topology_gate")
    if not isinstance(axis1["passes"], bool):
        raise AssertionError("axis1_topology_gate.passes must be bool")
    if not isinstance(axis1["reducible_to_baseline"], bool):
        raise AssertionError("axis1_topology_gate.reducible_to_baseline must be bool")
    for key in ("metric_space", "feature_claim_map", "named_baseline", "adversarial_null"):
        _assert_nonempty_str(axis1.get(key), f"axis1_topology_gate.{key}")
    if axis1["passes"] and axis1["reducible_to_baseline"]:
        raise AssertionError("Axis-1 cannot pass when the claim is reducible_to_baseline")


def _validate_scored_axis(axis: Mapping[str, Any], label: str) -> int:
    _assert_exact_keys(axis, SCORED_AXIS_KEYS, label)
    score = axis["score"]
    if isinstance(score, bool) or not isinstance(score, int):
        raise AssertionError(f"{label}.score must be an integer")
    if not 0 <= score <= 3:
        raise AssertionError(f"{label}.score must be in [0, 3]")
    _assert_nonempty_str(axis.get("rationale"), f"{label}.rationale")
    return score


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
