from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.projection.replay import replay
from research_system.schema_registry import runtime_schema_registry
from tests.research_system.factories import activate_lifecycle_grant, control_plane


ROOT = Path(__file__).parents[3]
SCHEMAS = ROOT / ".research-system" / "schemas"
LEGACY_IDENTITIES = {
    "activate-authority-grant-command.schema.json": "904556b5f1a8c0fa45a39ab2245d3a4fe8c14a4c0387f3ddb7e3923a51549762",
    "scoped-authority-grant.schema.json": "03ac40ea2df4d100746b10d39ae1227a7d2835c18997f701a4f85ede992105bb",
    "scoped-authority-grant-activated-event.schema.json": "0d2d130b2b76e4d63fa6dcb92f821f7dcd3829ff817ec9f896fe7257c038e0d9",
    "owner-authority-administration-decision.schema.json": "971072c7b180b4c39125b012db323c167318db1656ba14f38839243a4f7615d3",
    "issued-authority-grant-revoked-event.schema.json": "a094787c5d8e4788e70b2462486622c3e26f4157932dc8ab4aa46a52c9bd14f5",
}


def test_legacy_bytes_are_preserved_and_successors_are_active() -> None:
    root = SCHEMAS / "wp6-3-authority"
    for name, expected in LEGACY_IDENTITIES.items():
        assert sha256((root / name).read_bytes()).hexdigest() == expected
    schemas = runtime_schema_registry(SCHEMAS)
    assert schemas.command_binding("ActivateAuthorityGrant").schema_version == "1.1.0"
    assert schemas.event_binding("AuthorityGrantActivated", "ActivateAuthorityGrant").schema_version == "1.1.0"
    assert schemas.event_binding("AuthorityGrantRevoked", "RevokeIssuedAuthorityGrant").schema_version == "1.1.0"
    assert schemas.is_active("ars://core/scoped-authority-grant", "2.1.0")
    assert schemas.is_active("ars://core/owner-authority-administration-decision", "1.1.0")
    assert (
        schemas.resolve_identity("ars://core/command/ActivateAuthorityGrant", "1.0.0").sha256
        == (LEGACY_IDENTITIES["activate-authority-grant-command.schema.json"])
    )


def test_replay_accepts_only_exact_legacy_and_successor_activation_pairs(tmp_path) -> None:
    harness = control_plane(tmp_path)
    artefact_id = "art_019fe47a-3000-7000-8000-000000003000"
    activate_lifecycle_grant(
        harness,
        subject_kind="artefact",
        subject_id=artefact_id,
        command_types=("RegisterArtefact",),
    )
    current_events = tuple(harness.authority_ledger.iter_events())
    current = replay(current_events, schema_registry=harness.schemas, authority_state_validator=lambda state: None)
    grant_id = f"agr_{artefact_id.split('_', 1)[1]}"
    assert current["authority_grants"][grant_id]["schema_version"] == "2.1.0"

    legacy = deepcopy(current_events[-1])
    legacy["schema_version"] = "1.0.0"
    legacy["command_schema_version"] = "1.0.0"
    legacy["command_schema_sha256"] = LEGACY_IDENTITIES["activate-authority-grant-command.schema.json"]
    legacy["payload"]["activated_grant_schema_version"] = "2.0.0"
    legacy["payload"]["activated_grant_schema_sha256"] = LEGACY_IDENTITIES["scoped-authority-grant.schema.json"]
    legacy.pop("event_hash")
    legacy["event_hash"] = sha256_hex(canonical_bytes(legacy))
    historical = replay(
        (*current_events[:-1], legacy),
        schema_registry=harness.schemas,
        authority_state_validator=lambda state: None,
    )
    assert historical["authority_grants"][grant_id]["schema_version"] == "2.0.0"

    mismatched = deepcopy(legacy)
    mismatched["schema_version"] = "1.1.0"
    mismatched.pop("event_hash")
    mismatched["event_hash"] = sha256_hex(canonical_bytes(mismatched))
    try:
        replay(
            (*current_events[:-1], mismatched),
            schema_registry=harness.schemas,
            authority_state_validator=lambda state: None,
        )
    except Exception as exc:  # exact rejection type is deliberately fail-closed
        assert "schema" in str(exc) or "binding" in str(exc)
    else:
        raise AssertionError("mixed authority schema versions must not replay")
