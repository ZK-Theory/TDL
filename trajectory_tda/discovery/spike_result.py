"""Validation helpers for Discovery Harness Spike result summaries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import yaml

SCHEMA_VERSION = "discovery/spike-result-summary/v1"
VALID_OUTCOMES = {"success", "partial", "failure"}
VALID_DECISIONS = {"dispatch", "park", "kill"}
ROOT_KEYS = {
    "schema_version",
    "candidate_slug",
    "source_preregistration",
    "completed_at",
    "outcome",
    "time_box_hours_used",
    "metric_space_confirmed",
    "toy_signal_status",
    "null_model_status",
    "baseline_comparison",
    "research_assurance_evidence",
    "artifacts",
    "decision",
    "next",
}
NULL_MODEL_STATUS_KEYS = {"defined", "perturbs_input", "evidence"}
BASELINE_COMPARISON_KEYS = {"baselines", "result"}
ASSURANCE_KEYS = {"topology", "null_model", "representation", "provenance"}


def extract_spike_result_block(markdown: str) -> dict[str, Any]:
    """Return the YAML payload from a fenced ``spike_result_summary`` block."""
    lines = markdown.splitlines()
    in_block = False
    block: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not in_block and stripped in {
            "```yaml spike_result_summary",
            "```spike_result_summary",
        }:
            in_block = True
            continue
        if in_block and stripped == "```":
            parsed = yaml.safe_load("\n".join(block))
            if not isinstance(parsed, dict):
                raise AssertionError("spike_result_summary block must parse to a mapping")
            return parsed
        if in_block:
            block.append(line)
    raise AssertionError("missing fenced spike_result_summary block")


def validate_spike_result(payload: Mapping[str, Any]) -> None:
    """Validate Spike result invariants before any APM handoff."""
    _assert_exact_keys(payload, ROOT_KEYS, "spike_result")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise AssertionError(f"schema_version must equal {SCHEMA_VERSION!r}")

    for key in (
        "candidate_slug",
        "source_preregistration",
        "completed_at",
        "toy_signal_status",
        "next",
    ):
        _assert_nonempty_str(payload.get(key), key)

    outcome = payload["outcome"]
    if outcome not in VALID_OUTCOMES:
        raise AssertionError(f"outcome must be one of {sorted(VALID_OUTCOMES)}")

    decision = payload["decision"]
    if decision not in VALID_DECISIONS:
        raise AssertionError(f"decision must be one of {sorted(VALID_DECISIONS)}")

    _validate_time_box_used(payload["time_box_hours_used"])
    if not isinstance(payload["metric_space_confirmed"], bool):
        raise AssertionError("metric_space_confirmed must be bool")

    _validate_null_model_status(_assert_mapping(payload["null_model_status"], "null_model_status"))
    _validate_baseline_comparison(
        _assert_mapping(payload["baseline_comparison"], "baseline_comparison")
    )
    _validate_assurance(
        _assert_mapping(payload["research_assurance_evidence"], "research_assurance_evidence")
    )
    _assert_nonempty_str_list(payload["artifacts"], "artifacts")

    if outcome == "success":
        if payload["metric_space_confirmed"] is not True:
            raise AssertionError("success requires metric_space_confirmed true")
        null_status = payload["null_model_status"]
        if null_status["defined"] is not True:
            raise AssertionError("success requires null_model_status.defined true")
        if null_status["perturbs_input"] is not True:
            raise AssertionError("success requires null_model_status.perturbs_input true")
        if decision != "dispatch":
            raise AssertionError("success requires decision dispatch")
        if payload["next"] != "/pre-reg-to-dispatch":
            raise AssertionError("success must hand off through /pre-reg-to-dispatch")
    elif decision == "dispatch":
        raise AssertionError(f"{outcome} Spike results must not dispatch")


def _validate_time_box_used(value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AssertionError("time_box_hours_used must be an integer")
    if not 0 <= value <= 4:
        raise AssertionError("time_box_hours_used must be between 0 and 4")


def _validate_null_model_status(status: Mapping[str, Any]) -> None:
    _assert_exact_keys(status, NULL_MODEL_STATUS_KEYS, "null_model_status")
    for key in ("defined", "perturbs_input"):
        if not isinstance(status[key], bool):
            raise AssertionError(f"null_model_status.{key} must be bool")
    _assert_nonempty_str(status["evidence"], "null_model_status.evidence")


def _validate_baseline_comparison(comparison: Mapping[str, Any]) -> None:
    _assert_exact_keys(comparison, BASELINE_COMPARISON_KEYS, "baseline_comparison")
    _assert_nonempty_str_list(comparison["baselines"], "baseline_comparison.baselines")
    _assert_nonempty_str(comparison["result"], "baseline_comparison.result")


def _validate_assurance(evidence: Mapping[str, Any]) -> None:
    _assert_exact_keys(evidence, ASSURANCE_KEYS, "research_assurance_evidence")
    for key in ASSURANCE_KEYS:
        _assert_nonempty_str(evidence[key], f"research_assurance_evidence.{key}")


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
