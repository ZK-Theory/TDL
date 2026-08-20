from copy import deepcopy

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.decision_identity import decision_semantic_sha256


def _resolved_decision() -> dict[str, object]:
    return {
        "status": "resolved",
        "kind": "assay",
        "decision_kind": "promotion",
        "recommendation": "PARK",
        "options": ["PROMOTE", "PARK", "KILL"],
        "selected_option": "PARK",
        "proposal_event_hash": "a" * 64,
        "proposal_version": 1,
        "version": 2,
    }


def test_decision_semantic_hash_is_stable_when_terminal_replay_provenance_is_attached() -> None:
    before_terminal_projection = _resolved_decision()
    after_terminal_projection = {
        **before_terminal_projection,
        "terminal_event_id": "evt_019fe47a-1080-7000-8000-000000001080",
        "terminal_event_hash": "b" * 64,
    }

    assert sha256_hex(canonical_bytes(before_terminal_projection)) != sha256_hex(
        canonical_bytes(after_terminal_projection)
    )
    assert decision_semantic_sha256(before_terminal_projection) == decision_semantic_sha256(after_terminal_projection)


@pytest.mark.parametrize(
    ("field", "changed_value"),
    (
        ("status", "proposed"),
        ("kind", "spike"),
        ("decision_kind", "design_lock"),
        ("recommendation", "KILL"),
        ("options", ["PARK", "KILL"]),
        ("selected_option", "KILL"),
        ("proposal_event_hash", "c" * 64),
        ("proposal_version", 2),
        ("version", 3),
    ),
)
def test_decision_semantic_hash_rejects_changed_decision_meaning(
    field: str,
    changed_value: object,
) -> None:
    decision = _resolved_decision()
    changed = deepcopy(decision)
    changed[field] = changed_value

    assert decision_semantic_sha256(decision) != decision_semantic_sha256(changed)
