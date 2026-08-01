from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import errno
import json
import shutil
import subprocess
import sys
import threading

import pytest

from research_system.authority import (
    LedgerAuthorityGrantResolver,
    authority_bootstrap_sha256,
    initialize_authority_control_store,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.service import CommandService
from research_system.cli import main
from research_system.config import ControlBinding
from research_system.errors import (
    ArsError,
    ConfigurationError,
    ConflictError,
    IntegrityError,
    SchemaError,
)
from research_system.projection.replay import replay
from research_system.schema_registry import SchemaRegistry, runtime_schema_registry
from research_system.store.ledger import EventLedger
from research_system.store.identity import load_store_manifest
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore
from tests.research_system.factories import REPO_ROOT, create_task_command


PROJECT_ID = "prj_01978abc-1000-7000-8000-000000001000"
ACTOR_ID = "act_01978abc-1002-7000-8000-000000001002"
ROOT_ID = "agr_01978abc-1004-7000-8000-000000001004"
PUBLICATION_ID = "agr_01978abc-1001-7000-8000-000000001001"
DECISION_ID = "rgd_01978abc-1003-7000-8000-000000001003"
CMD_REVOKE = "cmd_01978abc-1005-7000-8000-000000001005"
CMD_RETRY = "cmd_01978abc-1006-7000-8000-000000001006"
CMD_EXACT_TASK = "cmd_01978abc-1016-7000-8000-000000001016"
SUBSTITUTE_ACTOR_ID = "act_01978abc-1010-7000-8000-000000001010"
SUBSTITUTE_DECISION_ID = "rgd_01978abc-1011-7000-8000-000000001011"
FOREIGN_PUBLICATION_ID = "agr_01978abc-1012-7000-8000-000000001012"
REUSED_TASK_ID = "tsk_01978abc-1013-7000-8000-000000001013"
SUBSTITUTE_BATCH_ID = "txb_01978abc-1014-7000-8000-000000001014"
SUBSTITUTE_EVENT_ID = "evt_01978abc-1015-7000-8000-000000001015"


SCHEMAS = SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")


def _code_root(tmp_path, name: str = "repo"):
    root = tmp_path / name
    shutil.copytree(
        REPO_ROOT / ".research-system" / "schemas",
        root / ".research-system" / "schemas",
    )
    return root


def _resolver(
    control_root,
    project_id,
    expected_store_identity,
):
    """Construct the production resolver with this module's trusted registry."""
    return LedgerAuthorityGrantResolver(
        control_root,
        project_id,
        expected_store_identity,
        SCHEMAS,
    )


def _grant(
    grant_id: str,
    command: str,
    subject_kind: str,
    subject_id: str,
    *,
    expires_at: str | None,
) -> dict[str, object]:
    return {
        "schema_id": "ars://core/authority-grant",
        "schema_version": "1.1.0",
        "authority_grant_id": grant_id,
        "actor_id": ACTOR_ID,
        "allowed_command_types": [command],
        "subject_scope": {
            "project_id": PROJECT_ID,
            "subject": {"kind": subject_kind, "id": subject_id},
        },
        "risk_ceiling": "R2",
        "effective_at": "2026-07-12T00:00:00Z",
        "expires_at": expires_at,
        "delegable": False,
        "revoked": False,
    }


def _bootstrap() -> dict[str, object]:
    root = _grant(
        ROOT_ID,
        "RevokeAuthorityGrant",
        "authority_grant",
        PUBLICATION_ID,
        expires_at=None,
    )
    publication = _grant(
        PUBLICATION_ID,
        "PublishReleaseGateDecision",
        "release_gate_decision",
        DECISION_ID,
        expires_at="2026-07-13T00:00:00Z",
    )
    return {
        "schema_id": "ars://core/authority-bootstrap-manifest",
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "owner_actor_id": ACTOR_ID,
        "root_grant": root,
        "root_grant_sha256": sha256_hex(canonical_bytes(root)),
        "publication_grant": publication,
        "publication_grant_sha256": sha256_hex(canonical_bytes(publication)),
        "publication_target_id": DECISION_ID,
    }


def _initialized(tmp_path):
    code_root = _code_root(tmp_path)
    control_root = tmp_path / "control"
    bootstrap = _bootstrap()
    approved = authority_bootstrap_sha256(bootstrap)
    identity = initialize_authority_control_store([code_root], control_root, PROJECT_ID, bootstrap, approved)
    return control_root, bootstrap, identity


def _replace_grant_object(control_root, grant_id, value) -> str:
    directory = control_root / "objects" / "authority_grant" / grant_id
    for path in directory.glob("*.json"):
        path.unlink()
    digest = sha256_hex(canonical_bytes(value))
    (directory / f"00000001-{digest}.json").write_bytes(canonical_bytes(value))
    return digest


def _rewrite_genesis(control_root, mutate) -> None:
    batch_path = next((control_root / "events" / PROJECT_ID).rglob("*.jsonl"))
    events = [json.loads(line) for line in batch_path.read_text(encoding="utf-8").splitlines() if line]
    mutate(events)
    previous_hash = "0" * 64
    for event in events:
        event["previous_event_hash"] = previous_hash
        event.pop("event_hash", None)
        event["event_hash"] = sha256_hex(canonical_bytes(event))
        previous_hash = event["event_hash"]
    batch_path.write_bytes(b"".join(canonical_bytes(event) + b"\n" for event in events))


def _hard_exit_initializer(tmp_path, failpoint: str):
    bootstrap_path = tmp_path / "bootstrap.json"
    bootstrap = _bootstrap()
    bootstrap_path.write_bytes(canonical_bytes(bootstrap))
    script = """
import json
import os
from pathlib import Path
import sys
import research_system.authority as authority

base = Path(sys.argv[1])
failpoint = sys.argv[2]
bootstrap = json.loads((base / "bootstrap.json").read_bytes())

def stop(point):
    if point == failpoint:
        os._exit(86)

authority._bootstrap_failpoint = stop
if failpoint == "at-rename":
    authority.os.rename = lambda *args: os._exit(86)
authority.initialize_authority_control_store(
    [base / "repo"],
    base / "control",
    sys.argv[3],
    bootstrap,
    authority.authority_bootstrap_sha256(bootstrap),
)
"""
    # Current interpreter, fixed argv shape, and synthetic test inputs only.
    return subprocess.run(  # nosemgrep: dangerous-subprocess-use-audit  # nosec B603
        [sys.executable, "-c", script, str(tmp_path), failpoint, PROJECT_ID],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_genesis_is_atomic_replay_derived_and_exact_retry_is_read_only(tmp_path) -> None:
    control_root, bootstrap, identity = _initialized(tmp_path)
    before = sorted(
        (path.relative_to(control_root).as_posix(), path.read_bytes())
        for path in control_root.rglob("*")
        if path.is_file()
    )
    assert (
        initialize_authority_control_store(
            [tmp_path / "repo"],
            control_root,
            PROJECT_ID,
            bootstrap,
            authority_bootstrap_sha256(bootstrap),
        )
        == identity
    )
    assert before == sorted(
        (path.relative_to(control_root).as_posix(), path.read_bytes())
        for path in control_root.rglob("*")
        if path.is_file()
    )
    events = tuple(EventLedger(control_root, PROJECT_ID).iter_events())
    assert [event["event_type"] for event in events] == [
        "AuthorityRootInitialized",
        "AuthorityGrantActivated",
    ]
    assert [event["transaction_index"] for event in events] == [1, 2]
    state = replay(events)
    assert state["authority_grants"][PUBLICATION_ID]["status"] == "active"


@pytest.mark.parametrize(
    "extra_full_version",
    [None, "9.9.9"],
    ids=["matching-version", "additional-arbitrary-version"],
)
def test_runtime_authority_payload_schema_cannot_be_shadowed_by_unbound_full_schema(
    tmp_path,
    extra_full_version,
) -> None:
    control_root, _, _ = _initialized(tmp_path)
    schema_root = tmp_path / "collision-schemas"
    shutil.copytree(REPO_ROOT / ".research-system" / "schemas", schema_root)
    event_schema_id = "ars://core/event/AuthorityRootInitialized"
    full_versions = ("1.0.0",) if extra_full_version is None else ("1.0.0", extra_full_version)
    for index, full_schema_version in enumerate(full_versions):
        (schema_root / f"authority-root-full-shadow-{index}.schema.json").write_bytes(
            canonical_bytes(
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "$id": event_schema_id,
                    "type": "object",
                    "properties": {
                        "schema_version": {"const": full_schema_version},
                    },
                    "required": ["schema_version"],
                    "additionalProperties": True,
                }
            )
        )
    schemas = runtime_schema_registry(schema_root)
    assert all(not schemas.is_active(event_schema_id, version) for version in full_versions)

    ledger = EventLedger(control_root, PROJECT_ID, schemas)
    root_event = next(ledger.iter_events())
    candidate = {
        field: root_event[field]
        for field in (
            "event_type",
            "stream_id",
            "schema_id",
            "command_id",
            "command_type",
            "command_schema_id",
            "command_schema_version",
            "command_schema_sha256",
            "actor_id",
            "authority_grant_id",
            "idempotency_key",
            "command_payload_hash",
            "correlation_id",
            "causation_id",
            "occurred_at",
        )
    }
    candidate.update(
        {
            "schema_version": root_event["schema_version"],
            "payload": {},
        }
    )
    before = tuple(ledger.iter_batches())

    with pytest.raises(SchemaError, match="bootstrap_manifest_sha256"):
        ledger.append([candidate])

    assert tuple(ledger.iter_batches()) == before

    recorded = deepcopy(root_event)
    recorded["payload"] = {}
    recorded.pop("event_hash")
    recorded["event_hash"] = sha256_hex(canonical_bytes(recorded))
    with pytest.raises(IntegrityError, match="event schema validation failed"):
        replay([recorded], schema_registry=schemas)


def test_authority_store_exact_retry_replays_activated_lifecycle_history(
    tmp_path,
) -> None:
    control_root, bootstrap, identity = _initialized(tmp_path)
    schemas = runtime_schema_registry(tmp_path / "repo" / ".research-system" / "schemas")
    command = create_task_command(
        CMD_EXACT_TASK,
        "authority-retry-exact-task",
        REUSED_TASK_ID,
        {"title": "Exact lifecycle authority retry"},
    )
    command_identity = schemas.resolve_identity(
        command["schema_id"],
        command["schema_version"],
    )
    event_identity = schemas.resolve_identity(
        "ars://core/event/TaskCreated",
        "1.0.0",
    )
    EventLedger(control_root, PROJECT_ID, schemas).append(
        [
            {
                "event_type": "TaskCreated",
                "stream_id": REUSED_TASK_ID,
                "command_id": command["command_id"],
                "command_type": command["command_type"],
                "command_schema_id": command_identity.schema_id,
                "command_schema_version": command_identity.schema_version,
                "command_schema_sha256": command_identity.sha256,
                "actor_id": command["actor_id"],
                "authority_grant_id": command["authority_grant_id"],
                "idempotency_key": command["idempotency_key"],
                "command_payload_hash": sha256_hex(canonical_bytes(command["payload"])),
                "correlation_id": command["correlation_id"],
                "causation_id": command["causation_id"],
                "schema_id": event_identity.schema_id,
                "schema_version": event_identity.schema_version,
                "occurred_at": None,
                "payload": command["payload"],
            }
        ]
    )

    assert (
        initialize_authority_control_store(
            [tmp_path / "repo"],
            control_root,
            PROJECT_ID,
            bootstrap,
            authority_bootstrap_sha256(bootstrap),
        )
        == identity
    )


def test_genesis_records_validated_generic_command_identity_and_replays_at_default_cutoff(
    tmp_path,
) -> None:
    control_root, _, _ = _initialized(tmp_path)
    events = tuple(EventLedger(control_root, PROJECT_ID).iter_events())
    command_identity = SCHEMAS.resolve_identity(
        "ars://core/command",
        "1.0.0",
    )

    assert len(events) == 2
    for event in events:
        assert event["command_schema_id"] == command_identity.schema_id
        assert event["command_schema_version"] == command_identity.schema_version
        assert event["command_schema_sha256"] == command_identity.sha256

    state = replay(events, schema_registry=SCHEMAS)
    assert state["authority_grants"][PUBLICATION_ID]["status"] == "active"


def test_replay_rejects_mismatched_genesis_envelope(tmp_path) -> None:
    control_root, _, _ = _initialized(tmp_path)
    events = list(EventLedger(control_root, PROJECT_ID).iter_events())
    events[1]["actor_id"] = SUBSTITUTE_ACTOR_ID
    events[1].pop("event_hash")
    events[1]["event_hash"] = sha256_hex(canonical_bytes(events[1]))

    with pytest.raises(IntegrityError, match="genesis envelope"):
        replay(events)


@pytest.mark.parametrize("mutation", ["wrong-event", "duplicate-activation"])
def test_replay_rejects_wrong_or_duplicate_genesis_activation(tmp_path, mutation) -> None:
    control_root, _, _ = _initialized(tmp_path)
    events = list(EventLedger(control_root, PROJECT_ID).iter_events())
    if mutation == "wrong-event":
        events[1]["event_type"] = "AuthorityRootInitialized"
        events[1]["schema_id"] = "ars://core/event/AuthorityRootInitialized"
        events[1].pop("event_hash")
        events[1]["event_hash"] = sha256_hex(canonical_bytes(events[1]))
    else:
        duplicate = deepcopy(events[1])
        duplicate.update(
            {
                "event_id": SUBSTITUTE_EVENT_ID,
                "global_position": 3,
                "previous_event_hash": events[1]["event_hash"],
                "stream_version": 2,
                "transaction_id": SUBSTITUTE_BATCH_ID,
                "transaction_index": 1,
                "transaction_count": 1,
            }
        )
        duplicate.pop("event_hash")
        duplicate["event_hash"] = sha256_hex(canonical_bytes(duplicate))
        events.append(duplicate)

    with pytest.raises(IntegrityError):
        replay(events)


def test_genesis_rejects_duplicate_resolved_code_roots(tmp_path) -> None:
    code_root = _code_root(tmp_path)
    control_root = tmp_path / "control"
    bootstrap = _bootstrap()

    with pytest.raises(ArsError, match="duplicate"):
        initialize_authority_control_store(
            [code_root, code_root / "."],
            control_root,
            PROJECT_ID,
            bootstrap,
            authority_bootstrap_sha256(bootstrap),
        )

    assert not control_root.exists()


def test_new_authority_store_requires_registered_schema_root_before_writes(
    tmp_path,
) -> None:
    code_root = tmp_path / "repo-without-schemas"
    code_root.mkdir()
    control_root = tmp_path / "control"
    bootstrap = _bootstrap()

    with pytest.raises(ArsError, match="requires a registered schema root"):
        initialize_authority_control_store(
            [code_root],
            control_root,
            PROJECT_ID,
            bootstrap,
            authority_bootstrap_sha256(bootstrap),
        )
    assert not control_root.exists()
    assert not list(tmp_path.glob(".control.authority-stage-*"))


def test_genesis_rejects_nonempty_target_without_mutation(tmp_path) -> None:
    code_root = _code_root(tmp_path)
    control_root = tmp_path / "control"
    control_root.mkdir()
    sentinel = control_root / "foreign.txt"
    sentinel.write_bytes(b"foreign-store")
    bootstrap = _bootstrap()

    with pytest.raises(IntegrityError, match="identity manifest"):
        initialize_authority_control_store(
            [code_root],
            control_root,
            PROJECT_ID,
            bootstrap,
            authority_bootstrap_sha256(bootstrap),
        )

    assert sentinel.read_bytes() == b"foreign-store"
    assert tuple(control_root.iterdir()) == (sentinel,)
    assert not list(tmp_path.glob(".control.authority-stage-*"))


def test_changed_retry_legacy_store_and_inert_object_fail_closed(tmp_path) -> None:
    control_root, bootstrap, _ = _initialized(tmp_path)
    changed = deepcopy(bootstrap)
    changed["publication_grant"]["expires_at"] = "2026-07-14T00:00:00Z"
    changed["publication_grant_sha256"] = sha256_hex(canonical_bytes(changed["publication_grant"]))
    with pytest.raises(ConflictError, match="bootstrap"):
        initialize_authority_control_store(
            [tmp_path / "repo"],
            control_root,
            PROJECT_ID,
            changed,
            authority_bootstrap_sha256(changed),
        )

    inert_root = tmp_path / "inert"
    inert_root.mkdir()
    ObjectStore(inert_root).write("authority_grant", PUBLICATION_ID, 1, bootstrap["publication_grant"])
    with pytest.raises(ArsError, match="authority_bootstrap_required"):
        _resolver(inert_root, PROJECT_ID, "0" * 64).resolve(
            PUBLICATION_ID,
            ACTOR_ID,
            "PublishReleaseGateDecision",
            PROJECT_ID,
            "release_gate_decision",
            DECISION_ID,
            datetime(2026, 7, 12, 12, tzinfo=UTC),
        )


@pytest.mark.parametrize("missing", ["bootstrap", "root_object", "publication_object"])
def test_exact_retry_rejects_missing_bound_authority_evidence(tmp_path, missing) -> None:
    control_root, bootstrap, _ = _initialized(tmp_path)
    paths = {
        "bootstrap": control_root / "manifests" / "authority-bootstrap.json",
        "root_object": next((control_root / "objects" / "authority_grant" / ROOT_ID).glob("*.json")),
        "publication_object": next((control_root / "objects" / "authority_grant" / PUBLICATION_ID).glob("*.json")),
    }
    paths[missing].unlink()

    with pytest.raises(IntegrityError):
        initialize_authority_control_store(
            [tmp_path / "repo"],
            control_root,
            PROJECT_ID,
            bootstrap,
            authority_bootstrap_sha256(bootstrap),
        )


def test_exact_retry_rejects_rehashed_code_root_store_swap(tmp_path) -> None:
    control_root, bootstrap, _ = _initialized(tmp_path)
    foreign_root = tmp_path / "foreign-repo"
    foreign_root.mkdir()
    manifest_path = control_root / "manifests" / "store-identity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["code_roots"] = [str(foreign_root.resolve())]
    manifest["manifest_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in manifest.items() if key != "manifest_hash"})
    )
    manifest_path.write_bytes(canonical_bytes(manifest))

    with pytest.raises(ConflictError, match="code root"):
        initialize_authority_control_store(
            [tmp_path / "repo"],
            control_root,
            PROJECT_ID,
            bootstrap,
            authority_bootstrap_sha256(bootstrap),
        )


def test_exact_retry_requires_implicit_new_writer_schema_binding_but_accepts_legacy(tmp_path) -> None:
    control_root, bootstrap, identity = _initialized(tmp_path)
    manifest_path = control_root / "manifests" / "store-identity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("schema_root")
    manifest["manifest_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in manifest.items() if key != "manifest_hash"})
    )
    manifest_path.write_bytes(canonical_bytes(manifest))

    with pytest.raises(IntegrityError, match="schema-root binding missing"):
        initialize_authority_control_store(
            [tmp_path / "repo"],
            control_root,
            PROJECT_ID,
            bootstrap,
            authority_bootstrap_sha256(bootstrap),
        )

    manifest.pop("schema_binding_version")
    manifest["manifest_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in manifest.items() if key != "manifest_hash"})
    )
    manifest_path.write_bytes(canonical_bytes(manifest))
    assert (
        initialize_authority_control_store(
            [tmp_path / "repo"],
            control_root,
            PROJECT_ID,
            bootstrap,
            authority_bootstrap_sha256(bootstrap),
        )
        == identity
    )


def test_exact_retry_rejects_foreign_two_grant_genesis(tmp_path) -> None:
    control_root, bootstrap, _ = _initialized(tmp_path)

    def substitute_publication_stream(events) -> None:
        events[1]["stream_id"] = FOREIGN_PUBLICATION_ID
        events[1]["payload"]["activated_grant_id"] = FOREIGN_PUBLICATION_ID

    _rewrite_genesis(control_root, substitute_publication_stream)

    with pytest.raises(IntegrityError, match="bootstrap"):
        initialize_authority_control_store(
            [tmp_path / "repo"],
            control_root,
            PROJECT_ID,
            bootstrap,
            authority_bootstrap_sha256(bootstrap),
        )


def test_resolver_enforces_hash_actor_command_project_target_time_and_tamper(tmp_path) -> None:
    control_root, bootstrap, identity = _initialized(tmp_path)
    resolver = _resolver(control_root, PROJECT_ID, identity)
    result = resolver.resolve(
        PUBLICATION_ID,
        ACTOR_ID,
        "PublishReleaseGateDecision",
        PROJECT_ID,
        "release_gate_decision",
        DECISION_ID,
        datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    assert result.authority_grant_sha256 == bootstrap["publication_grant_sha256"]
    assert (
        resolver.resolve(
            PUBLICATION_ID,
            ACTOR_ID,
            "PublishReleaseGateDecision",
            PROJECT_ID,
            "release_gate_decision",
            DECISION_ID,
            datetime(2026, 7, 12, tzinfo=UTC),
        ).status
        == "active"
    )
    assert (
        resolver.resolve(
            ROOT_ID,
            ACTOR_ID,
            "RevokeAuthorityGrant",
            PROJECT_ID,
            "authority_grant",
            PUBLICATION_ID,
            datetime(2036, 7, 12, tzinfo=UTC),
        ).expires_at
        is None
    )
    for changed in [
        (
            "act_01978abc-1008-7000-8000-000000001008",
            "PublishReleaseGateDecision",
            PROJECT_ID,
            "release_gate_decision",
            DECISION_ID,
        ),
        (ACTOR_ID, "RevokeAuthorityGrant", PROJECT_ID, "release_gate_decision", DECISION_ID),
        (
            ACTOR_ID,
            "PublishReleaseGateDecision",
            "prj_01978abc-1009-7000-8000-000000001009",
            "release_gate_decision",
            DECISION_ID,
        ),
        (
            ACTOR_ID,
            "PublishReleaseGateDecision",
            PROJECT_ID,
            "release_gate_decision",
            "rgd_01978abc-1007-7000-8000-000000001007",
        ),
    ]:
        with pytest.raises(ArsError):
            resolver.resolve(PUBLICATION_ID, *changed, datetime(2026, 7, 12, 12, tzinfo=UTC))
    with pytest.raises(ArsError, match="effective"):
        resolver.resolve(
            PUBLICATION_ID,
            ACTOR_ID,
            "PublishReleaseGateDecision",
            PROJECT_ID,
            "release_gate_decision",
            DECISION_ID,
            datetime(2026, 7, 11, tzinfo=UTC),
        )
    with pytest.raises(ArsError, match="expired"):
        resolver.resolve(
            PUBLICATION_ID,
            ACTOR_ID,
            "PublishReleaseGateDecision",
            PROJECT_ID,
            "release_gate_decision",
            DECISION_ID,
            datetime(2026, 7, 13, tzinfo=UTC),
        )
    with pytest.raises(ArsError, match="expired"):
        resolver.resolve(
            PUBLICATION_ID,
            ACTOR_ID,
            "PublishReleaseGateDecision",
            PROJECT_ID,
            "release_gate_decision",
            DECISION_ID,
            datetime(2026, 7, 14, tzinfo=UTC),
        )

    grant_path = next((control_root / "objects" / "authority_grant" / PUBLICATION_ID).glob("*.json"))
    grant_path.write_bytes(canonical_bytes({**bootstrap["publication_grant"], "risk_ceiling": "R3"}))
    with pytest.raises(IntegrityError, match="object"):
        resolver.resolve(
            PUBLICATION_ID,
            ACTOR_ID,
            "PublishReleaseGateDecision",
            PROJECT_ID,
            "release_gate_decision",
            DECISION_ID,
            datetime(2026, 7, 12, 12, tzinfo=UTC),
        )


def test_resolver_rejects_coordinated_genesis_and_grant_substitution(tmp_path) -> None:
    control_root, bootstrap, identity = _initialized(tmp_path)
    substituted_root = deepcopy(bootstrap["root_grant"])
    substituted_root["actor_id"] = SUBSTITUTE_ACTOR_ID
    substituted_publication = deepcopy(bootstrap["publication_grant"])
    substituted_publication["actor_id"] = SUBSTITUTE_ACTOR_ID
    substituted_publication["subject_scope"]["subject"]["id"] = SUBSTITUTE_DECISION_ID
    root_hash = _replace_grant_object(control_root, ROOT_ID, substituted_root)
    publication_hash = _replace_grant_object(control_root, PUBLICATION_ID, substituted_publication)

    def substitute(events) -> None:
        for event in events:
            event["actor_id"] = SUBSTITUTE_ACTOR_ID
        events[0]["payload"]["authorizing_grant_sha256"] = root_hash
        events[0]["payload"]["activated_grant_sha256"] = root_hash
        events[1]["payload"]["authorizing_grant_sha256"] = root_hash
        events[1]["payload"]["activated_grant_sha256"] = publication_hash

    _rewrite_genesis(control_root, substitute)

    with pytest.raises(IntegrityError, match="bootstrap"):
        _resolver(control_root, PROJECT_ID, identity).resolve(
            PUBLICATION_ID,
            SUBSTITUTE_ACTOR_ID,
            "PublishReleaseGateDecision",
            PROJECT_ID,
            "release_gate_decision",
            SUBSTITUTE_DECISION_ID,
            datetime(2026, 7, 12, 12, tzinfo=UTC),
        )


def _revoke_command(command_id: str) -> dict[str, object]:
    bootstrap = _bootstrap()
    return {
        "command_id": command_id,
        "command_type": "RevokeAuthorityGrant",
        "schema_id": "ars://core/command",
        "schema_version": "1.0.0",
        "submitted_at": "2026-07-12T12:00:00Z",
        "actor_id": ACTOR_ID,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": ROOT_ID,
        "target_stream_id": PUBLICATION_ID,
        "expected_stream_version": 1,
        "idempotency_key": "revoke-publication",
        "correlation_id": "synthetic-authority-test",
        "causation_id": None,
        "reason": "synthetic revocation",
        "evidence_refs": [],
        "payload": {
            "project_id": PROJECT_ID,
            "target_grant_id": PUBLICATION_ID,
            "target_grant_sha256": bootstrap["publication_grant_sha256"],
            "authority_grant_sha256": bootstrap["root_grant_sha256"],
            "reason": "synthetic revocation",
        },
    }


def test_revoke_payload_schema_rejects_extra_field_before_mutation(tmp_path) -> None:
    control_root, _, identity = _initialized(tmp_path)
    ledger = EventLedger(control_root, PROJECT_ID, SCHEMAS)
    service = CommandService(
        control_root,
        ledger,
        ObjectStore(control_root),
        ReceiptStore(control_root),
        SchemaRegistry(REPO_ROOT / ".research-system" / "schemas"),
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    command = _revoke_command(CMD_REVOKE)
    command["payload"]["unexpected"] = True
    before = tuple(ledger.iter_events())

    with pytest.raises(SchemaError, match="Additional properties"):
        service.submit(command)

    assert tuple(ledger.iter_events()) == before


def test_revoke_is_locked_monotonic_and_exact_retry_survives_restart(tmp_path) -> None:
    control_root, bootstrap, identity = _initialized(tmp_path)
    resolver = _resolver(control_root, PROJECT_ID, identity)
    schemas = SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=resolver,
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    original_bytes = next((control_root / "objects" / "authority_grant" / PUBLICATION_ID).glob("*.json")).read_bytes()
    original = service.submit(_revoke_command(CMD_REVOKE))
    assert original.status == "accepted"
    restarted = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    retry = restarted.submit(_revoke_command(CMD_RETRY))
    assert retry == original
    assert len(list((control_root / "receipts" / "idempotency").glob("*.json"))) == 1
    assert (
        next((control_root / "objects" / "authority_grant" / PUBLICATION_ID).glob("*.json")).read_bytes()
        == original_bytes
    )
    with pytest.raises(ArsError, match="revoked"):
        resolver.resolve(
            PUBLICATION_ID,
            ACTOR_ID,
            "PublishReleaseGateDecision",
            PROJECT_ID,
            "release_gate_decision",
            DECISION_ID,
            datetime(2026, 7, 12, 12, tzinfo=UTC),
        )
    assert replay(EventLedger(control_root, PROJECT_ID).iter_events())["authority_grants"][PUBLICATION_ID][
        "revocation_event_id"
    ]


def test_scoped_retry_rejects_changed_expected_stream_version(tmp_path) -> None:
    control_root, _, identity = _initialized(tmp_path)
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        SchemaRegistry(REPO_ROOT / ".research-system" / "schemas"),
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    assert service.submit(_revoke_command(CMD_REVOKE)).status == "accepted"
    changed_version = _revoke_command(CMD_RETRY)
    changed_version["expected_stream_version"] = 2

    with pytest.raises(ConflictError, match="expected stream version"):
        service.submit(changed_version)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reason", "changed revocation reason"),
        ("target_grant_sha256", "e" * 64),
        ("authority_grant_sha256", "f" * 64),
    ],
)
def test_scoped_retry_rejects_changed_payload_or_grant_hash(tmp_path, field, value) -> None:
    control_root, _, identity = _initialized(tmp_path)
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        SchemaRegistry(REPO_ROOT / ".research-system" / "schemas"),
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    assert service.submit(_revoke_command(CMD_REVOKE)).status == "accepted"
    changed = _revoke_command(CMD_RETRY)
    changed["payload"][field] = value

    with pytest.raises(ConflictError, match="idempotency key"):
        service.submit(changed)


def test_scoped_retry_rejects_reused_unrelated_command_id(tmp_path) -> None:
    control_root, _, identity = _initialized(tmp_path)
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, schemas),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    assert service.submit(_revoke_command(CMD_REVOKE)).status == "accepted"
    unrelated = create_task_command(
        CMD_RETRY,
        "unrelated-command-id-use",
        REUSED_TASK_ID,
        {"title": "unrelated"},
    )
    assert service.submit(unrelated).status == "accepted"

    with pytest.raises(ConflictError, match="command ID"):
        service.submit(_revoke_command(CMD_RETRY))


def test_rejected_exact_retry_is_returned_before_current_authority_recheck(tmp_path) -> None:
    control_root, _, identity = _initialized(tmp_path)
    schemas = SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")
    resolver = _resolver(control_root, PROJECT_ID, identity)
    rejected_service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=resolver,
        clock=lambda: datetime(2026, 7, 11, tzinfo=UTC),
    )
    original = rejected_service.submit(_revoke_command(CMD_REVOKE))
    assert original.status == "rejected"
    assert original.reason_code == "authority_revocation_unauthorized"

    current_service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=resolver,
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    assert current_service.submit(_revoke_command(CMD_RETRY)) == original
    assert len(tuple(EventLedger(control_root, PROJECT_ID).iter_events())) == 2


def test_authority_integrity_failure_propagates_without_cached_rejection(tmp_path) -> None:
    control_root, bootstrap, identity = _initialized(tmp_path)
    root_path = next((control_root / "objects" / "authority_grant" / ROOT_ID).glob("*.json"))
    root_path.write_bytes(canonical_bytes({**bootstrap["root_grant"], "risk_ceiling": "R3"}))
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        SchemaRegistry(REPO_ROOT / ".research-system" / "schemas"),
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )

    with pytest.raises(IntegrityError, match="object"):
        service.submit(_revoke_command(CMD_REVOKE))

    assert not list((control_root / "receipts" / "idempotency").glob("*.json"))


def test_replay_rejects_foreign_project_in_revocation_payload(tmp_path) -> None:
    control_root, _, identity = _initialized(tmp_path)
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        SchemaRegistry(REPO_ROOT / ".research-system" / "schemas"),
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    assert service.submit(_revoke_command(CMD_REVOKE)).status == "accepted"
    events = [deepcopy(event) for event in EventLedger(control_root, PROJECT_ID).iter_events()]
    changed = events[-1]
    changed["payload"]["project_id"] = "prj_01978abc-1099-7000-8000-000000001099"
    changed.pop("event_hash")
    changed["event_hash"] = sha256_hex(canonical_bytes(changed))

    with pytest.raises(IntegrityError, match="project"):
        replay(events)


def test_scoped_retry_replays_tampered_canonical_revocation_history(tmp_path) -> None:
    control_root, _, identity = _initialized(tmp_path)
    schemas = SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    original = service.submit(_revoke_command(CMD_REVOKE))
    assert original.status == "accepted"

    batch_path = next(
        path
        for path in (control_root / "events" / PROJECT_ID).rglob("*.jsonl")
        if '"AuthorityGrantRevoked"' in path.read_text(encoding="utf-8")
    )
    event = json.loads(batch_path.read_text(encoding="utf-8"))
    event["payload"]["project_id"] = "prj_01978abc-1099-7000-8000-000000001099"
    event.pop("event_hash")
    event["event_hash"] = sha256_hex(canonical_bytes(event))
    batch_path.write_bytes(canonical_bytes(event) + b"\n")

    restarted = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )

    with pytest.raises(IntegrityError, match="project"):
        restarted.submit(_revoke_command(CMD_RETRY))


def test_scoped_receipt_rejects_tampered_embedded_payload_hash(tmp_path) -> None:
    control_root, _, identity = _initialized(tmp_path)
    schemas = SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    assert service.submit(_revoke_command(CMD_REVOKE)).status == "accepted"
    index_path = next((control_root / "receipts" / "idempotency").glob("*.json"))
    record = json.loads(index_path.read_text(encoding="utf-8"))
    record["receipt"]["payload_hash"] = "f" * 64
    index_path.write_bytes(canonical_bytes(record))
    restarted = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )

    with pytest.raises(ConflictError, match="payload"):
        restarted.submit(_revoke_command(CMD_RETRY))


@pytest.mark.parametrize("tamper", ["event_batch_id", "status"])
def test_scoped_receipt_reconciles_accepted_outcome_with_ledger(tmp_path, tamper) -> None:
    control_root, _, identity = _initialized(tmp_path)
    schemas = SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    assert service.submit(_revoke_command(CMD_REVOKE)).status == "accepted"
    index_path = next((control_root / "receipts" / "idempotency").glob("*.json"))
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if tamper == "event_batch_id":
        index["receipt"]["outcome"]["event_batch_id"] = SUBSTITUTE_BATCH_ID
    else:
        index["receipt"]["status"] = "conflict"
        index["receipt"]["outcome"]["event_batch_id"] = None
        index["receipt"]["outcome"]["reason_code"] = "stream_version_conflict"
    index_path.write_bytes(canonical_bytes(index))
    (control_root / "receipts" / f"{CMD_REVOKE}.json").write_bytes(canonical_bytes(index["receipt"]))
    restarted = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )

    with pytest.raises(IntegrityError, match="ledger"):
        restarted.submit(_revoke_command(CMD_RETRY))


def test_scoped_receipt_rejects_malformed_index_and_embedded_receipt(tmp_path) -> None:
    control_root, bootstrap, identity = _initialized(tmp_path)
    receipts = ReceiptStore(control_root)
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        receipts,
        SchemaRegistry(REPO_ROOT / ".research-system" / "schemas"),
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    assert service.submit(_revoke_command(CMD_REVOKE)).status == "accepted"
    index_path = next((control_root / "receipts" / "idempotency").glob("*.json"))
    original = json.loads(index_path.read_text(encoding="utf-8"))
    scope = (ACTOR_ID, ROOT_ID, "RevokeAuthorityGrant", "revoke-publication")

    malformed_records = []
    wrong_schema = deepcopy(original)
    wrong_schema["schema_version"] = "9.9.9"
    malformed_records.append(wrong_schema)
    missing_outcome = deepcopy(original)
    missing_outcome["receipt"].pop("outcome")
    malformed_records.append(missing_outcome)
    invalid_command = deepcopy(original)
    invalid_command["receipt"]["command_id"] = [CMD_REVOKE]
    malformed_records.append(invalid_command)

    for malformed in malformed_records:
        index_path.write_bytes(canonical_bytes(malformed))
        with pytest.raises(ConflictError, match="invalid"):
            receipts.load_scoped(
                scope,
                original["payload_hash"],
                bootstrap["root_grant_sha256"],
                1,
            )


def test_scoped_receipt_exact_retry_recovers_stale_matching_temp(tmp_path, monkeypatch) -> None:
    control_root, _, identity = _initialized(tmp_path)
    receipts = ReceiptStore(control_root)
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        receipts,
        SchemaRegistry(REPO_ROOT / ".research-system" / "schemas"),
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 11, tzinfo=UTC),
    )
    publish = receipts._publish

    def fail_index_publish(source, target):
        if source.name.endswith(".idempotency.tmp"):
            raise OSError("idempotency publication crash")
        publish(source, target)

    monkeypatch.setattr(receipts, "_publish", fail_index_publish)
    with pytest.raises(OSError, match="publication crash"):
        service.submit(_revoke_command(CMD_REVOKE))
    assert list((control_root / "runtime").glob("*.idempotency.tmp"))
    monkeypatch.setattr(receipts, "_publish", publish)

    retry = service.submit(_revoke_command(CMD_REVOKE))

    assert retry.status == "rejected"
    assert len(list((control_root / "receipts" / "idempotency").glob("*.json"))) == 1
    assert not list((control_root / "runtime").glob("*.idempotency.tmp"))


def test_restart_rebuilds_missing_scoped_index_from_canonical_batch(tmp_path) -> None:
    control_root, _, identity = _initialized(tmp_path)
    schemas = SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    original = service.submit(_revoke_command(CMD_REVOKE))
    index_path = next((control_root / "receipts" / "idempotency").glob("*.json"))
    index_path.unlink()
    restarted = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )

    assert restarted.submit(_revoke_command(CMD_RETRY)) == original
    assert len(list((control_root / "receipts" / "idempotency").glob("*.json"))) == 1


def test_restart_rebuilds_missing_operational_receipt_from_scoped_index(
    tmp_path,
) -> None:
    control_root, _, identity = _initialized(tmp_path)
    schemas = SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    original = service.submit(_revoke_command(CMD_REVOKE))
    receipt_path = control_root / "receipts" / f"{CMD_REVOKE}.json"
    receipt_path.unlink()
    restarted = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )

    assert restarted.submit(_revoke_command(CMD_RETRY)) == original
    assert receipt_path.is_file()


def test_restart_rejects_changed_expected_version_without_scoped_index(
    tmp_path,
) -> None:
    control_root, _, identity = _initialized(tmp_path)
    schemas = SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    assert service.submit(_revoke_command(CMD_REVOKE)).status == "accepted"
    next((control_root / "receipts" / "idempotency").glob("*.json")).unlink()
    changed_version = _revoke_command(CMD_RETRY)
    changed_version["expected_stream_version"] = 2
    restarted = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=_resolver(control_root, PROJECT_ID, identity),
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )

    with pytest.raises(ConflictError, match="idempotency key"):
        restarted.submit(changed_version)


def test_cli_store_init_requires_and_publishes_approved_authority_bootstrap(tmp_path, monkeypatch, capsys) -> None:
    code_root = tmp_path / "repo"
    shutil.copytree(
        REPO_ROOT / ".research-system" / "schemas",
        code_root / ".research-system" / "schemas",
    )
    bootstrap = _bootstrap()
    bootstrap_path = tmp_path / "authority-bootstrap.json"
    bootstrap_path.write_bytes(
        canonical_bytes(
            {
                "schema_id": "ars://core/authority-bootstrap-input",
                "schema_version": "1.0.0",
                "approved_bootstrap_sha256": authority_bootstrap_sha256(bootstrap),
                "manifest": bootstrap,
            }
        )
    )
    monkeypatch.setattr(
        "research_system.cli.subprocess.run",
        lambda *args, **kwargs: type(
            "Result", (), {"returncode": 0, "stdout": f"worktree {code_root.resolve()}\n", "stderr": ""}
        )(),
    )
    control_root = tmp_path / "control"
    assert (
        main(
            [
                "store",
                "init",
                "--code-root",
                str(code_root),
                "--control-root",
                str(control_root),
                "--project-id",
                PROJECT_ID,
                "--authority-bootstrap",
                str(bootstrap_path),
            ]
        )
        == 0
    )
    output = __import__("json").loads(capsys.readouterr().out)
    assert output["bootstrap_manifest_sha256"] == authority_bootstrap_sha256(bootstrap)
    assert output["store_identity"]


def test_cli_store_init_binds_explicit_schema_authority_across_worktrees(tmp_path, monkeypatch, capsys) -> None:
    explicit_root = tmp_path / "explicit"
    linked_root = tmp_path / "linked"
    for root in (explicit_root, linked_root):
        shutil.copytree(
            REPO_ROOT / ".research-system" / "schemas",
            root / ".research-system" / "schemas",
        )
    (linked_root / ".research-system" / "schemas" / "linked-only.schema.json").write_bytes(
        canonical_bytes(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "ars://test/linked-only",
                "type": "object",
            }
        )
    )
    bootstrap = _bootstrap()
    bootstrap_path = tmp_path / "authority-bootstrap.json"
    bootstrap_path.write_bytes(
        canonical_bytes(
            {
                "schema_id": "ars://core/authority-bootstrap-input",
                "schema_version": "1.0.0",
                "approved_bootstrap_sha256": authority_bootstrap_sha256(bootstrap),
                "manifest": bootstrap,
            }
        )
    )
    worktree_output = "".join(f"worktree {root.resolve()}\n" for root in (explicit_root, linked_root))
    monkeypatch.setattr(
        "research_system.cli.subprocess.run",
        lambda *args, **kwargs: type("Result", (), {"returncode": 0, "stdout": worktree_output, "stderr": ""})(),
    )
    control_root = tmp_path / "control"
    init_args = [
        "store",
        "init",
        "--code-root",
        str(explicit_root),
        "--control-root",
        str(control_root),
        "--project-id",
        PROJECT_ID,
        "--authority-bootstrap",
        str(bootstrap_path),
    ]

    assert main(init_args) == 0
    first_identity = json.loads(capsys.readouterr().out)["store_identity"]
    manifest = load_store_manifest(control_root)
    assert manifest["schema_root"] == str((explicit_root / ".research-system" / "schemas").resolve())
    assert manifest["code_roots"] == sorted([str(explicit_root.resolve()), str(linked_root.resolve())])
    stable = {
        "schema_id": manifest["schema_id"],
        "schema_version": manifest["schema_version"],
        "store_nonce": manifest["store_nonce"],
        "project_id": manifest["project_id"],
        "bootstrap_manifest_sha256": manifest["bootstrap_manifest_sha256"],
    }
    assert first_identity == sha256_hex(canonical_bytes(stable))

    assert main(init_args) == 0
    assert json.loads(capsys.readouterr().out)["store_identity"] == first_identity
    assert main(["replay", "verify", "--control-root", str(control_root)]) == 0
    capsys.readouterr()
    projection = explicit_root / ".research-system" / "projections" / "state.json"
    assert (
        main(
            [
                "projection",
                "rebuild",
                "--control-root",
                str(control_root),
                "--output",
                str(projection),
            ]
        )
        == 0
    )
    assert json.loads(projection.read_text(encoding="utf-8"))["last_position"] == 2


@pytest.mark.parametrize(
    "authority_kind, message",
    [
        ("changed", "schema root binding mismatch"),
        ("unregistered", "registered code root"),
        ("wrong_suffix", "registered code root"),
        ("missing", "existing directory"),
        ("malformed", "usable SchemaRegistry"),
    ],
)
def test_exact_retry_rejects_changed_or_malformed_schema_authority(tmp_path, authority_kind, message) -> None:
    explicit_root = tmp_path / "explicit"
    linked_root = tmp_path / "linked"
    unregistered_root = tmp_path / "unregistered"
    for root in (explicit_root, linked_root, unregistered_root):
        shutil.copytree(
            REPO_ROOT / ".research-system" / "schemas",
            root / ".research-system" / "schemas",
        )
    code_roots = [explicit_root, linked_root]
    explicit_schema_root = explicit_root / ".research-system" / "schemas"
    bootstrap = _bootstrap()
    approved = authority_bootstrap_sha256(bootstrap)
    control_root = tmp_path / "control"
    initialize_authority_control_store(
        code_roots,
        control_root,
        PROJECT_ID,
        bootstrap,
        approved,
        canonical_schema_root=explicit_schema_root,
    )
    before = sorted(
        (path.relative_to(control_root).as_posix(), path.read_bytes())
        for path in control_root.rglob("*")
        if path.is_file()
    )
    candidates = {
        "changed": linked_root / ".research-system" / "schemas",
        "unregistered": unregistered_root / ".research-system" / "schemas",
        "wrong_suffix": explicit_root / ".research-system" / "schemas-wrong",
        "missing": explicit_root / ".research-system" / "schemas",
        "malformed": explicit_root / ".research-system" / "schemas",
    }
    if authority_kind == "wrong_suffix":
        shutil.copytree(explicit_schema_root, candidates[authority_kind])
    elif authority_kind == "missing":
        shutil.rmtree(explicit_schema_root)
    elif authority_kind == "malformed":
        (explicit_schema_root / "core" / "event.schema.json").unlink()

    with pytest.raises(ArsError, match=message):
        initialize_authority_control_store(
            code_roots,
            control_root,
            PROJECT_ID,
            bootstrap,
            approved,
            canonical_schema_root=candidates[authority_kind],
        )
    assert before == sorted(
        (path.relative_to(control_root).as_posix(), path.read_bytes())
        for path in control_root.rglob("*")
        if path.is_file()
    )


def test_manifest_replay_rejects_tampered_or_missing_schema_authority(tmp_path, monkeypatch) -> None:
    explicit_root = tmp_path / "explicit"
    linked_root = tmp_path / "linked"
    for root in (explicit_root, linked_root):
        shutil.copytree(
            REPO_ROOT / ".research-system" / "schemas",
            root / ".research-system" / "schemas",
        )
    bootstrap = _bootstrap()
    bootstrap_path = tmp_path / "authority-bootstrap.json"
    bootstrap_path.write_bytes(
        canonical_bytes(
            {
                "schema_id": "ars://core/authority-bootstrap-input",
                "schema_version": "1.0.0",
                "approved_bootstrap_sha256": authority_bootstrap_sha256(bootstrap),
                "manifest": bootstrap,
            }
        )
    )
    monkeypatch.setattr(
        "research_system.cli.subprocess.run",
        lambda *args, **kwargs: type(
            "Result",
            (),
            {
                "returncode": 0,
                "stdout": "".join(f"worktree {root.resolve()}\n" for root in (explicit_root, linked_root)),
                "stderr": "",
            },
        )(),
    )
    control_root = tmp_path / "control"
    assert (
        main(
            [
                "store",
                "init",
                "--code-root",
                str(explicit_root),
                "--control-root",
                str(control_root),
                "--project-id",
                PROJECT_ID,
                "--authority-bootstrap",
                str(bootstrap_path),
            ]
        )
        == 0
    )
    manifest_path = control_root / "manifests" / "store-identity.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_root"] = str((linked_root / ".research-system" / "schemas").resolve())
    manifest_path.write_bytes(canonical_bytes(manifest))
    with pytest.raises(IntegrityError, match="manifest hash mismatch"):
        main(["replay", "verify", "--control-root", str(control_root)])

    manifest["manifest_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in manifest.items() if key != "manifest_hash"})
    )
    manifest_path.write_bytes(canonical_bytes(manifest))
    with pytest.raises(ConflictError, match="schema root binding mismatch"):
        initialize_authority_control_store(
            [explicit_root, linked_root],
            control_root,
            PROJECT_ID,
            bootstrap,
            authority_bootstrap_sha256(bootstrap),
            canonical_schema_root=explicit_root / ".research-system" / "schemas",
        )
    shutil.rmtree(linked_root / ".research-system" / "schemas")
    with pytest.raises(ConfigurationError, match="schema root is missing"):
        main(["replay", "verify", "--control-root", str(control_root)])


def test_control_binding_rejects_schema_root_that_disagrees_with_store(tmp_path) -> None:
    explicit_root = tmp_path / "explicit"
    linked_root = tmp_path / "linked"
    for root in (explicit_root, linked_root):
        shutil.copytree(
            REPO_ROOT / ".research-system" / "schemas",
            root / ".research-system" / "schemas",
        )
    bootstrap = _bootstrap()
    control_root = tmp_path / "control"
    identity = initialize_authority_control_store(
        [explicit_root, linked_root],
        control_root,
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
        canonical_schema_root=explicit_root / ".research-system" / "schemas",
    )
    binding_path = tmp_path / "binding.yaml"
    binding_path.write_text(
        json.dumps(
            {
                "code_roots": [
                    str(explicit_root.resolve()),
                    str(linked_root.resolve()),
                ],
                "control_root": str(control_root.resolve()),
                "project_id": PROJECT_ID,
                "schema_root": str((linked_root / ".research-system" / "schemas").resolve()),
                "store_identity": identity,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="conflicts with store manifest"):
        ControlBinding.load(binding_path)


def test_control_binding_reports_unavailable_configured_schema_root(tmp_path) -> None:
    control_root, _, identity = _initialized(tmp_path)
    binding_path = tmp_path / "binding.yaml"
    binding_path.write_text(
        json.dumps(
            {
                "code_roots": [str((tmp_path / "repo").resolve())],
                "control_root": str(control_root.resolve()),
                "project_id": PROJECT_ID,
                "schema_root": str((tmp_path / "missing" / ".research-system" / "schemas").resolve()),
                "store_identity": identity,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="configured schema root is unavailable"):
        ControlBinding.load(binding_path)


def test_control_binding_reports_missing_manifest_schema_root(tmp_path) -> None:
    explicit_root = _code_root(tmp_path, "explicit")
    linked_root = _code_root(tmp_path, "linked")
    control_root = tmp_path / "control"
    bootstrap = _bootstrap()
    identity = initialize_authority_control_store(
        [explicit_root, linked_root],
        control_root,
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
        canonical_schema_root=explicit_root / ".research-system" / "schemas",
    )
    shutil.rmtree(explicit_root / ".research-system" / "schemas")
    binding_path = tmp_path / "binding.yaml"
    binding_path.write_text(
        json.dumps(
            {
                "code_roots": [str(explicit_root.resolve()), str(linked_root.resolve())],
                "control_root": str(control_root.resolve()),
                "project_id": PROJECT_ID,
                "schema_root": str((linked_root / ".research-system" / "schemas").resolve()),
                "store_identity": identity,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="store manifest schema root is missing"):
        ControlBinding.load(binding_path)


def test_cli_command_submit_wires_validated_authority_resolver(tmp_path, capsys, monkeypatch) -> None:
    control_root, _, identity = _initialized(tmp_path)
    config_path = tmp_path / "binding.json"
    config_path.write_text(
        json.dumps(
            {
                "code_roots": [str((tmp_path / "repo").resolve())],
                "control_root": str(control_root.resolve()),
                "project_id": PROJECT_ID,
                "schema_root": str((tmp_path / "repo" / ".research-system" / "schemas").resolve()),
                "store_identity": identity,
            }
        ),
        encoding="utf-8",
    )
    command_path = tmp_path / "revoke.json"
    command_path.write_bytes(canonical_bytes(_revoke_command(CMD_REVOKE)))
    monkeypatch.setattr(
        "research_system.cli._authority_clock",
        lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
        raising=False,
    )

    assert (
        main(
            [
                "command",
                "submit",
                "--config",
                str(config_path),
                "--command",
                str(command_path),
            ]
        )
        == 0
    )

    assert json.loads(capsys.readouterr().out)["status"] == "accepted"


def test_pre_rename_crash_leaves_no_visible_store_and_exact_retry_recovers(tmp_path, monkeypatch) -> None:
    code_root = _code_root(tmp_path)
    control_root = tmp_path / "control"
    bootstrap = _bootstrap()
    approved = authority_bootstrap_sha256(bootstrap)
    real_rename = __import__("os").rename
    monkeypatch.setattr(
        "research_system.authority.os.rename",
        lambda *args: (_ for _ in ()).throw(OSError("pre-rename crash")),
    )
    with pytest.raises(OSError, match="pre-rename crash"):
        initialize_authority_control_store([code_root], control_root, PROJECT_ID, bootstrap, approved)
    assert not control_root.exists()
    assert not list(tmp_path.glob(".control.authority-stage-*"))
    monkeypatch.setattr("research_system.authority.os.rename", real_rename)
    identity = initialize_authority_control_store([code_root], control_root, PROJECT_ID, bootstrap, approved)
    assert _resolver(control_root, PROJECT_ID, identity)


def test_hard_exit_complete_stage_resumes_byte_for_byte(tmp_path) -> None:
    code_root = _code_root(tmp_path)
    bootstrap = _bootstrap()

    crashed = _hard_exit_initializer(tmp_path, "after-staged-replay")

    assert crashed.returncode == 86, crashed.stderr
    assert not (tmp_path / "control").exists()
    stage = next(tmp_path.glob(".control.authority-stage-*"))
    staged_files = {
        path.relative_to(stage).as_posix(): path.read_bytes()
        for path in stage.rglob("*")
        if path.is_file() and path.name != "authority-bootstrap-stage.json"
    }
    staged_identity = json.loads((stage / "manifests" / "store-identity.json").read_text(encoding="utf-8"))[
        "store_identity"
    ]

    identity = initialize_authority_control_store(
        [code_root],
        tmp_path / "control",
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
    )

    final_root = tmp_path / "control"
    final_files = {
        path.relative_to(final_root).as_posix(): path.read_bytes() for path in final_root.rglob("*") if path.is_file()
    }
    assert identity == staged_identity
    assert final_files == staged_files


def test_hard_exit_at_atomic_rename_resumes_without_orphan(tmp_path) -> None:
    code_root = _code_root(tmp_path)
    bootstrap = _bootstrap()

    crashed = _hard_exit_initializer(tmp_path, "at-rename")

    assert crashed.returncode == 86, crashed.stderr
    assert not (tmp_path / "control").exists()
    stage = next(tmp_path.glob(".control.authority-stage-*"))
    marker = stage / "runtime" / "authority-bootstrap-stage.json"
    assert marker.is_file()
    staged_files = {
        path.relative_to(stage).as_posix(): path.read_bytes()
        for path in stage.rglob("*")
        if path.is_file() and path != marker
    }
    staged_identity = json.loads((stage / "manifests" / "store-identity.json").read_text(encoding="utf-8"))[
        "store_identity"
    ]

    identity = initialize_authority_control_store(
        [code_root],
        tmp_path / "control",
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
    )

    final_root = tmp_path / "control"
    final_files = {
        path.relative_to(final_root).as_posix(): path.read_bytes() for path in final_root.rglob("*") if path.is_file()
    }
    assert identity == staged_identity
    assert final_files == staged_files
    assert not list(tmp_path.glob(".control.authority-stage-*"))


@pytest.mark.parametrize(
    "failpoint",
    [
        "after-stage-marker",
        "after-identity",
        "after-bootstrap",
        "after-root-object",
        "after-publication-object",
        "after-event-batch",
        "after-staged-replay",
        "after-rename",
    ],
)
def test_hard_exit_boundaries_recover_only_one_complete_store(tmp_path, failpoint) -> None:
    code_root = _code_root(tmp_path)
    bootstrap = _bootstrap()

    crashed = _hard_exit_initializer(tmp_path, failpoint)

    assert crashed.returncode == 86, crashed.stderr
    control_root = tmp_path / "control"
    if control_root.exists():
        assert failpoint == "after-rename"
    else:
        assert list(tmp_path.glob(".control.authority-stage-*"))
    identity = initialize_authority_control_store(
        [code_root],
        control_root,
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
    )
    resolved = _resolver(control_root, PROJECT_ID, identity).resolve(
        PUBLICATION_ID,
        ACTOR_ID,
        "PublishReleaseGateDecision",
        PROJECT_ID,
        "release_gate_decision",
        DECISION_ID,
        datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    assert resolved.authority_grant_sha256 == bootstrap["publication_grant_sha256"]


def test_partial_and_foreign_hash_stages_remain_inert(tmp_path) -> None:
    code_root = _code_root(tmp_path)
    bootstrap = _bootstrap()
    crashed = _hard_exit_initializer(tmp_path, "after-identity")
    assert crashed.returncode == 86, crashed.stderr
    partial_stage = next(tmp_path.glob(".control.authority-stage-*"))
    partial_identity = json.loads((partial_stage / "manifests" / "store-identity.json").read_text(encoding="utf-8"))[
        "store_identity"
    ]
    foreign_stage = tmp_path / ".control.authority-stage-foreign"
    (foreign_stage / "runtime").mkdir(parents=True)
    (foreign_stage / "runtime" / "authority-bootstrap-stage.json").write_bytes(
        canonical_bytes(
            {
                "schema_id": "ars://core/authority-bootstrap-stage",
                "schema_version": "1.0.0",
                "bootstrap_manifest_sha256": "f" * 64,
                "status": "complete",
            }
        )
    )

    identity = initialize_authority_control_store(
        [code_root],
        tmp_path / "control",
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
    )

    assert identity != partial_identity
    assert partial_stage.exists()
    assert foreign_stage.exists()


def test_portable_publication_collision_verifies_winner_and_cleans_loser(tmp_path, monkeypatch) -> None:
    code_root = _code_root(tmp_path)
    control_root = tmp_path / "control"
    bootstrap = _bootstrap()

    def publish_competing_store(source, target):
        shutil.copytree(source, target)
        raise OSError(errno.ENOTEMPTY, "target directory is not empty")

    monkeypatch.setattr("research_system.authority.os.rename", publish_competing_store)
    identity = initialize_authority_control_store(
        [code_root],
        control_root,
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
    )

    assert _resolver(control_root, PROJECT_ID, identity)
    assert not list(tmp_path.glob(".control.authority-stage-*"))


def test_competing_initializers_converge_on_one_complete_identity(tmp_path) -> None:
    code_root = _code_root(tmp_path)
    control_root = tmp_path / "control"
    bootstrap = _bootstrap()
    approved = authority_bootstrap_sha256(bootstrap)
    barrier = threading.Barrier(2)
    identities: list[str] = []
    errors: list[BaseException] = []

    def initialize() -> None:
        try:
            barrier.wait()
            identities.append(
                initialize_authority_control_store([code_root], control_root, PROJECT_ID, bootstrap, approved)
            )
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    workers = [threading.Thread(target=initialize) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    assert errors == []
    assert len(identities) == 2
    assert identities[0] == identities[1]
    assert len(tuple(EventLedger(control_root, PROJECT_ID).iter_events())) == 2


def test_governed_authority_hook_rechecks_under_same_writer_lock_as_revoke(tmp_path) -> None:
    control_root, _, identity = _initialized(tmp_path)
    resolver = _resolver(control_root, PROJECT_ID, identity)
    schemas = SchemaRegistry(REPO_ROOT / ".research-system" / "schemas")
    service = CommandService(
        control_root,
        EventLedger(control_root, PROJECT_ID, SCHEMAS),
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
        authority_resolver=resolver,
        clock=lambda: datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    entered = threading.Event()
    release = threading.Event()

    def governed_operation() -> None:
        service.with_locked_authority(
            authority_grant_id=PUBLICATION_ID,
            actor_id=ACTOR_ID,
            command_type="PublishReleaseGateDecision",
            project_id=PROJECT_ID,
            subject_kind="release_gate_decision",
            subject_id=DECISION_ID,
            callback=lambda result: (
                entered.set(),
                release.wait(2),
                result.authority_grant_sha256,
            )[-1],
        )

    worker = threading.Thread(target=governed_operation)
    worker.start()
    assert entered.wait(1)
    with pytest.raises(ConflictError, match="writer lock exists"):
        service.submit(_revoke_command(CMD_REVOKE))
    release.set()
    worker.join()
    assert service.submit(_revoke_command(CMD_REVOKE)).status == "accepted"
    with pytest.raises(ArsError, match="revoked"):
        service.with_locked_authority(
            authority_grant_id=PUBLICATION_ID,
            actor_id=ACTOR_ID,
            command_type="PublishReleaseGateDecision",
            project_id=PROJECT_ID,
            subject_kind="release_gate_decision",
            subject_id=DECISION_ID,
            callback=lambda result: result,
        )
