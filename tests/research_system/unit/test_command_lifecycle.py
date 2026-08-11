from __future__ import annotations

import pytest

from research_system.command.lifecycle import validate_exact_lifecycle_envelope


@pytest.mark.parametrize(
    ("event_type", "schema_id"),
    [
        ("PartialOutcomeRecorded", "ars://core/event/PartialOutcomeRecorded"),
        ("LeaseReleased", "ars://core/event/LeaseReleased"),
    ],
)
def test_cancel_discovery_evaluation_is_exact_operational_event_producer(event_type: str, schema_id: str) -> None:
    event = {
        "event_type": event_type,
        "schema_id": schema_id,
        "schema_version": "1.0.0",
        "command_type": "CancelDiscoveryEvaluation",
        "command_schema_id": "ars://core/command",
        "command_schema_version": "1.0.0",
        "command_payload_hash": "f" * 64,
        "payload": {},
    }

    assert validate_exact_lifecycle_envelope(event) == "CancelDiscoveryEvaluation"
