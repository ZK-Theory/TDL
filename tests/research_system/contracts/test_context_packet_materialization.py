from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
CANDIDATE = ROOT / ".research-system/contracts/candidates/06j-w3-context-packet-v1"
CANONICAL_CONTRACT = ROOT / ".research-system/contracts/context-packet-v1"
SCHEMAS = ROOT / ".research-system/schemas"


COMMANDS = {
    "RequestContextPacket": "request_context_packet.schema.json",
    "BeginContextCompilation": "begin_context_compilation.schema.json",
    "CompleteContextCompilation": "complete_context_compilation.schema.json",
    "ValidateContextPacket": "validate_context_packet.schema.json",
    "IssueContextPacket": "issue_context_packet.schema.json",
    "RecordContextDelivery": "record_context_delivery.schema.json",
    "FailContextPacket": "fail_context_packet.schema.json",
    "ExpireContextPacket": "expire_context_packet.schema.json",
    "SupersedeContextPacket": "supersede_context_packet.schema.json",
}
EVENTS = {
    "ContextPacketRequested": "context_packet_requested.schema.json",
    "ContextCompilationStarted": "context_compilation_started.schema.json",
    "ContextPacketCompiled": "context_packet_compiled.schema.json",
    "ContextPacketValidated": "context_packet_validated.schema.json",
    "ContextPacketIssued": "context_packet_issued.schema.json",
    "ContextPacketDelivered": "context_packet_delivered.schema.json",
    "ContextPacketFailed": "context_packet_failed.schema.json",
    "ContextPacketExpired": "context_packet_expired.schema.json",
    "ContextPacketSuperseded": "context_packet_superseded.schema.json",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob(path: Path) -> str:
    result = subprocess.run(
        ["git", "hash-object", "--no-filters", "--", str(path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_context_packet_candidate_is_exactly_materialized_and_identity_bound() -> None:
    for name in (
        "catalogue-addendum.yaml",
        "transition-table.yaml",
        "authority-scopes.yaml",
        "identity-manifest.yaml",
    ):
        assert (CANDIDATE / name).read_bytes() == (CANONICAL_CONTRACT / name).read_bytes()
    for filename in COMMANDS.values():
        assert (CANDIDATE / "commands" / filename).read_bytes() == (SCHEMAS / "core/commands" / filename).read_bytes()
    for filename in EVENTS.values():
        assert (CANDIDATE / "events" / filename).read_bytes() == (SCHEMAS / "core/events" / filename).read_bytes()
    for filename in (
        "context-packet.schema.json",
        "context-manifest.schema.json",
        "context-delivery-receipt.schema.json",
    ):
        assert (CANDIDATE / "objects" / filename).read_bytes() == (SCHEMAS / "context" / filename).read_bytes()

    manifest = yaml.safe_load((CANDIDATE / "identity-manifest.yaml").read_text(encoding="utf-8"))
    bound_paths = set()
    for leaf in manifest["leaves"]:
        path = CANDIDATE / leaf["path"]
        bound_paths.add(leaf["path"])
        assert _sha256(path) == leaf["sha256"]
        assert _git_blob(path) == leaf["git_blob"]
    actual = {
        path.relative_to(CANDIDATE).as_posix()
        for path in CANDIDATE.rglob("*")
        if path.is_file() and path.name != "identity-manifest.yaml"
    }
    assert bound_paths == actual


def test_context_packet_catalogue_and_transition_family_are_complete() -> None:
    catalogue = yaml.safe_load((CANONICAL_CONTRACT / "catalogue-addendum.yaml").read_text(encoding="utf-8"))
    transitions = yaml.safe_load((CANONICAL_CONTRACT / "transition-table.yaml").read_text(encoding="utf-8"))
    assert set(catalogue["commands"]) == set(COMMANDS)
    assert set(catalogue["events"]) == set(EVENTS)
    assert {row["command"] for row in transitions["transitions"]} == set(COMMANDS)
    assert {row["event"] for row in transitions["transitions"]} == set(EVENTS)
    assert catalogue["reservations"] == {"F-029": "p1-design-only", "F-030": "p1-design-only"}

    for command, filename in COMMANDS.items():
        schema = json.loads((SCHEMAS / "core/commands" / filename).read_text(encoding="utf-8"))
        assert schema["$id"] == f"ars://core/command/{command}"
        assert schema["additionalProperties"] is False
        assert schema["properties"]["payload"]["additionalProperties"] is False
    for event, filename in EVENTS.items():
        schema = json.loads((SCHEMAS / "core/events" / filename).read_text(encoding="utf-8"))
        assert schema["$id"] == f"ars://core/event/{event}"
        assert schema["additionalProperties"] is False
        assert schema["properties"]["payload"]["additionalProperties"] is False


def test_context_command_schema_rejects_unknown_top_level_field() -> None:
    schema = json.loads((SCHEMAS / "core/commands/begin_context_compilation.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    envelope = {
        "command_id": "cmd_01978abc-1000-7000-8000-000000001000",
        "command_type": "BeginContextCompilation",
        "schema_id": "ars://core/command/BeginContextCompilation",
        "schema_version": "1.0.0",
        "submitted_at": "2026-08-08T12:00:00Z",
        "actor_id": "act_01978abc-1001-7000-8000-000000001001",
        "on_behalf_of_actor_id": None,
        "authority_grant_id": "agr_01978abc-1002-7000-8000-000000001002",
        "target_stream_id": "ctx_01978abc-1003-7000-8000-000000001003",
        "expected_stream_version": 1,
        "idempotency_key": "context:compile",
        "correlation_id": "context:ctx_01978abc-1003-7000-8000-000000001003",
        "causation_id": None,
        "reason": "W3 context lifecycle transition BeginContextCompilation",
        "evidence_refs": [],
        "payload": {
            "context_id": "ctx_01978abc-1003-7000-8000-000000001003",
            "request_id": "request-one",
            "revision": 1,
            "compiler_version": "1.0.0",
            "policy_version": "1.0.0",
        },
        "project_id": "prj_01978abc-1004-7000-8000-000000001004",
    }
    assert not list(validator.iter_errors(envelope))
    envelope["unknown_top_level_field"] = "rejected"
    assert any(error.validator == "additionalProperties" for error in validator.iter_errors(envelope))


def test_context_event_schema_rejects_unknown_top_level_field() -> None:
    schema = json.loads((SCHEMAS / "core/events/context_compilation_started.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    envelope = {
        "event_id": "evt_01978abc-1000-7000-8000-000000001000",
        "event_type": "ContextCompilationStarted",
        "schema_id": "ars://core/event/ContextCompilationStarted",
        "schema_version": "1.0.0",
        "project_id": "prj_01978abc-1001-7000-8000-000000001001",
        "stream_id": "ctx_01978abc-1002-7000-8000-000000001002",
        "stream_version": 2,
        "global_position": 2,
        "transaction_id": "txb_01978abc-1003-7000-8000-000000001003",
        "transaction_index": 1,
        "transaction_count": 1,
        "command_id": "cmd_01978abc-1004-7000-8000-000000001004",
        "command_type": "BeginContextCompilation",
        "command_schema_id": "ars://core/command/BeginContextCompilation",
        "command_schema_version": "1.0.0",
        "command_schema_sha256": "5384a2b46a98dd4a534e9103d7cb313ac12109fb54712cff608e2277d86e65f9",
        "idempotency_key": "context:compile",
        "command_payload_hash": "b" * 64,
        "correlation_id": "context:ctx_01978abc-1002-7000-8000-000000001002",
        "causation_id": None,
        "actor_id": "act_01978abc-1005-7000-8000-000000001005",
        "authority_grant_id": "agr_01978abc-1006-7000-8000-000000001006",
        "occurred_at": None,
        "recorded_at": "2026-08-08T12:00:00Z",
        "payload": {
            "context_id": "ctx_01978abc-1002-7000-8000-000000001002",
            "request_id": "request-one",
            "revision": 1,
            "compiler_version": "1.0.0",
            "policy_version": "1.0.0",
        },
        "previous_event_hash": "c" * 64,
        "event_hash": "d" * 64,
    }
    assert not list(validator.iter_errors(envelope))
    envelope["unknown_top_level_field"] = "rejected"
    assert any(error.validator == "additionalProperties" for error in validator.iter_errors(envelope))


def test_failed_packet_schema_rejects_phase_evidence_contradictions() -> None:
    schema = json.loads((SCHEMAS / "core/commands/fail_context_packet.schema.json").read_text(encoding="utf-8"))[
        "properties"
    ]["payload"]
    validator = Draft202012Validator(schema)
    base = {
        "context_id": "ctx_01978abc-1000-7000-8000-000000001000",
        "request_id": "req-1",
        "failure_code": "context_compilation_failed",
    }
    assert not list(
        validator.iter_errors(
            {
                **base,
                "lifecycle_phase": "compiling",
                "packet_evidence_status": "absent_before_immutable_bytes",
                "packet_revision": None,
                "packet_sha256": None,
            }
        )
    )
    contradictory = {
        **base,
        "lifecycle_phase": "compiled",
        "packet_evidence_status": "absent_before_immutable_bytes",
        "packet_revision": None,
        "packet_sha256": None,
    }
    assert list(validator.iter_errors(contradictory))
