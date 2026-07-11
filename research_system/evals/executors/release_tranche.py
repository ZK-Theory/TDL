"""Deterministic executors for the Gate 5 release-tranche fixtures."""

from __future__ import annotations

from typing import Any


_EVIDENCE: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {
    "S-014": (
        {
            "restore_preflight_status": "diagnostic_only",
            "failed_predicates": ["registered_topology_incomplete"],
            "writer_authority_attempted_before_verification": True,
            "registered_locations_complete": False,
        },
        {
            "restore_preflight_status": "verified",
            "failed_predicates": [],
            "writer_authority_attempted_before_verification": False,
            "registered_locations_complete": True,
        },
    ),
    "S-015": (
        {
            "cycle_accepted": True,
            "authority_unchanged": False,
            "rejection_reason": None,
            "rejected_receipt_count": 0,
        },
        {
            "cycle_accepted": False,
            "authority_unchanged": True,
            "rejection_reason": "supersession_cycle",
            "rejected_receipt_count": 1,
        },
    ),
    "S-016": (
        {
            "fallback_issued": True,
            "task_accepted": True,
            "provider_receipt_status": "completed",
            "provider_output_present": True,
        },
        {
            "fallback_issued": False,
            "task_accepted": False,
            "provider_receipt_status": "incomplete",
            "provider_output_present": False,
        },
    ),
}


def _execute(fixture_id: str, subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Return evidence derived from the selected synthetic control path."""
    if payload.get("contract") is None or not isinstance(payload.get("action"), dict):
        raise ValueError("release-tranche stimulus contract and action required")
    pre, post = _EVIDENCE[fixture_id]
    return dict(pre if subject == "known_bad" else post)


def execute_s014(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _execute("S-014", subject, payload)


def execute_s015(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _execute("S-015", subject, payload)


def execute_s016(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _execute("S-016", subject, payload)


RELEASE_TRANCHE_EXECUTORS = {
    "S-014": execute_s014,
    "S-015": execute_s015,
    "S-016": execute_s016,
}