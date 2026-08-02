from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
import json
import threading

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Receipt
from research_system.command.service import MessageAdapterRegistration
from research_system.errors import ConflictError, IntegrityError, SchemaError
from research_system.projection.replay import rebuild_projection, replay
from tests.research_system.factories import (
    ACTORS,
    PROJECT_ID,
    activate_lifecycle_grant,
    control_plane,
    revoke_lifecycle_grant,
)


MESSAGE_ROWS = (
    ("message.publish_assignment", "PublishMessage", "MessagePublished"),
    ("message.publish_acknowledgement", "PublishMessage", "MessagePublished"),
    ("message.publish_progress", "PublishMessage", "MessagePublished"),
    ("message.publish_input_request", "PublishMessage", "MessagePublished"),
    ("message.publish_escalation", "PublishMessage", "MessagePublished"),
    ("message.publish_report", "PublishMessage", "MessagePublished"),
    ("message.publish_review_request", "PublishMessage", "MessagePublished"),
    ("message.publish_review_response", "PublishMessage", "MessagePublished"),
    ("message.publish_decision_request", "PublishMessage", "MessagePublished"),
    ("message.publish_handoff", "PublishMessage", "MessagePublished"),
    ("message.deliver", "RecordMessageDelivery", "MessageDelivered"),
    ("message.acknowledge", "AcknowledgeMessage", "MessageAcknowledged"),
    ("message.delivery_failure", "RecordMessageDeliveryFailure", "MessageDeliveryFailed"),
)

_MESSAGE_MATRIX_AXIS_NAMES = frozenset(
    {
        "authority",
        "retry_idempotency_key_command_id",
        "concurrency",
        "failed_mutation",
        "replay",
        "projection",
        "decisive_negative",
    }
)
_MESSAGE_ROW_CONCURRENCY = {
    "message.publish_assignment": "not-applicable: absent-stream publication has no competing terminal transition",
    "message.publish_acknowledgement": "not-applicable: absent-stream publication has no competing terminal transition",
    "message.publish_progress": "not-applicable: absent-stream publication has no competing terminal transition",
    "message.publish_input_request": "not-applicable: absent-stream publication has no competing terminal transition",
    "message.publish_escalation": "not-applicable: absent-stream publication has no competing terminal transition",
    "message.publish_report": "not-applicable: absent-stream publication has no competing terminal transition",
    "message.publish_review_request": "not-applicable: absent-stream publication has no competing terminal transition",
    "message.publish_review_response": "not-applicable: absent-stream publication has no competing terminal transition",
    "message.publish_decision_request": "not-applicable: absent-stream publication has no competing terminal transition",
    "message.publish_handoff": "not-applicable: absent-stream publication has no competing terminal transition",
    "message.deliver": "delivery-versus-failure-race",
    "message.acknowledge": "acknowledgement-race",
    "message.delivery_failure": "delivery-versus-failure-race",
}


@pytest.mark.parametrize(
    ("row_id", "command_type", "event_type"),
    MESSAGE_ROWS,
    ids=[row_id for row_id, _, _ in MESSAGE_ROWS],
)
def test_message_rows_have_exact_runtime_schema_bindings(
    tmp_path,
    row_id,
    command_type,
    event_type,
):
    """Each frozen Message row is an activated, exact command/event pair."""
    registry = control_plane(tmp_path).schemas

    command = registry.command_binding(command_type)
    event = registry.event_binding(event_type, command_type)

    assert command is not None, row_id
    assert event is not None, row_id
    assert command.schema_id == f"ars://core/command/{command_type}"
    assert event.schema_id == f"ars://core/event/{event_type}"
    assert command.schema_version == event.schema_version == "1.0.0"
    assert registry.resolve_identity(command.schema_id, command.schema_version).raw_bytes
    assert registry.resolve_identity(event.schema_id, event.schema_version).raw_bytes


def test_message_schema_bindings_preserve_all_eight_protected_raw_hashes(tmp_path):
    registry = control_plane(tmp_path).schemas
    expected = {
        "ars://core/command/PublishMessage": "14c0c66afc05dce4d4e90ff28c1828e68f8ca0471f740fdf5d4ed4cd818c9f3c",
        "ars://core/event/MessagePublished": "f9a4d7d685ee9cbb8c299791469078d45ad022989bcfcd8456e18ba6a6de5f3f",
        "ars://core/command/RecordMessageDelivery": "9f2acb3223b1a9098750364b4401dbfad91cd1de0a0e787123a19cfb2e67e828",
        "ars://core/event/MessageDelivered": "7c2fabe331a8745695345431e349637caf6eb79f8cab5938caa4caf53e329388",
        "ars://core/command/AcknowledgeMessage": "3b8218236c5d0afddff30c0e936362cfbdc916a192f9e449d5cfef914f2cb92d",
        "ars://core/event/MessageAcknowledged": "576f5d5369b11b355d06cc7faaaddd5ebcae1094d72cf03e5712cd96170886be",
        "ars://core/command/RecordMessageDeliveryFailure": "afe3393eefe58291b4e41b3b1d496f49e89dd73c19022ef6d94f1a62d4e44a89",
        "ars://core/event/MessageDeliveryFailed": "0632bd0bc4c4ecaeea753735d4094c472233cc582da590cd29c986ecec0db2e5",
    }
    for schema_id, expected_hash in expected.items():
        identity = registry.resolve_identity(schema_id, "1.0.0")
        assert identity.sha256 == expected_hash
        assert sha256(identity.raw_bytes).hexdigest() == expected_hash


@pytest.mark.parametrize(
    ("row_id", "command_type", "event_type"),
    MESSAGE_ROWS,
    ids=[row_id for row_id, _, _ in MESSAGE_ROWS],
)
def test_message_row_common_axis_matrix(tmp_path, row_id, command_type, event_type):
    """Exercise every frozen Message row through the common completion axes."""
    expected_rows = {item[0] for item in MESSAGE_ROWS}
    assert set(_MESSAGE_ROW_CONCURRENCY) == expected_rows
    assert len(_MESSAGE_ROW_CONCURRENCY) == len(MESSAGE_ROWS) == 13
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    base = 10_000 + (index for index, item in enumerate(MESSAGE_ROWS) if item[0] == row_id).__next__() * 10
    message_id, command, publication = _matrix_row_command(
        harness,
        row_id,
        command_type,
        base,
    )

    accepted = harness.service.submit(command)
    assert accepted.status == "accepted"
    event = tuple(harness.ledger.iter_events())[-1]
    assert event["event_type"] == event_type
    assert event["authority_grant_id"].startswith("agr_")

    before_retry = _no_domain_mutation_snapshot(harness)
    assert harness.service.submit(deepcopy(command)) == accepted
    assert _no_domain_mutation_snapshot(harness) == before_retry

    changed_command_id = deepcopy(command)
    changed_command_id["command_id"] = _command_id(base + 1_001)
    with pytest.raises(ConflictError, match="idempotency key"):
        harness.service.submit(changed_command_id)
    assert _no_domain_mutation_snapshot(harness) == before_retry

    changed_idempotency_key = deepcopy(command)
    changed_idempotency_key["idempotency_key"] = f"matrix-changed-key:{row_id}:{base}"
    with pytest.raises(ConflictError, match="command ID"):
        harness.service.submit(changed_idempotency_key)
    assert _no_domain_mutation_snapshot(harness) == before_retry

    authority_negative = _matrix_authority_negative(command, row_id, base)
    rejected_authority = harness.service.submit(authority_negative)
    assert rejected_authority.reason_code == "lifecycle_authority_unauthorized"
    assert _no_domain_mutation_snapshot(harness) == before_retry

    decisive_root = tmp_path / "matrix-decisive-negative"
    decisive_root.mkdir()
    decisive_harness = control_plane(
        decisive_root,
        message_adapter_registry=_adapter_registry(),
    )
    _, decisive_command, decisive_publication = _matrix_row_command(
        decisive_harness,
        row_id,
        command_type,
        base + 2_000,
    )
    decisive_negative = _matrix_decisive_negative(
        decisive_command,
        decisive_publication,
        base + 2_000,
    )
    before_decisive_negative = _no_domain_mutation_snapshot(decisive_harness)
    rejected = decisive_harness.service.submit(decisive_negative)
    assert rejected.status == "rejected"
    assert _no_domain_mutation_snapshot(decisive_harness) == before_decisive_negative

    events = tuple(harness.ledger.iter_events())
    replayed = replay(events, schema_registry=harness.schemas)
    projection_path = tmp_path / f"{row_id.replace('.', '-')}-projection.json"
    assert rebuild_projection(events, projection_path, schema_registry=harness.schemas) == replayed
    assert replayed["streams"][message_id] == harness.replay().stream_states[message_id]

    concurrency = _MESSAGE_ROW_CONCURRENCY[row_id]
    if concurrency.startswith("not-applicable"):
        assert command_type == "PublishMessage"
    elif concurrency == "acknowledgement-race":
        _assert_matrix_acknowledgement_race(tmp_path, base + 5_000)
    else:
        assert concurrency == "delivery-versus-failure-race"
        _assert_matrix_delivery_failure_race(tmp_path, base + 5_000)

    axes = {
        "authority": rejected_authority.reason_code,
        "retry_idempotency_key_command_id": accepted.command_id,
        "concurrency": concurrency,
        "failed_mutation": before_retry["tail"],
        "replay": replayed["streams"][message_id]["status"],
        "projection": projection_path.read_bytes(),
        "decisive_negative": rejected.reason_code,
    }
    assert set(axes) == _MESSAGE_MATRIX_AXIS_NAMES


def _message_id(number: int) -> str:
    return f"msg_01978abc-7100-7000-8000-{number:012d}"


def _command_id(number: int) -> str:
    return f"cmd_01978abc-7101-7000-8000-{number:012d}"


def _publish_payload(message_id: str, message_type: str) -> dict:
    common = {
        "new_message_id": message_id,
        "message_type": message_type,
        "sender_actor_id": ACTORS["actor-a"],
        "recipient_actor_ids": [ACTORS["actor-a"]],
        "audience": ["pilot"],
        "reply_to_message_id": _message_id(999),
        "thread_id": "thread:wp6.1",
        "typed_subject": "task:pilot",
        "sensitivity_class": "internal",
        "retention_class": "pilot",
        "body": f"Message payload for {message_type}.",
    }
    additions = {
        "assignment": {
            "task_id": "tsk_01978abc-7102-7000-8000-000000007102",
            "dispatch_id": "dsp_01978abc-7103-7000-8000-000000007103",
            "requested_action": "complete bounded pilot action",
            "deadline": "2026-08-02T12:00:00Z",
        },
        "acknowledgement": {
            "correlation_message_id": common["reply_to_message_id"],
            "acknowledged_subject_id": "task:pilot",
        },
        "progress": {
            "task_id": "tsk_01978abc-7102-7000-8000-000000007102",
            "attempt_id": "att_01978abc-7104-7000-8000-000000007104",
            "progress_evidence_refs": ["evidence:progress"],
        },
        "input_request": {
            "requested_action": "supply a bounded input",
            "deadline": "2026-08-02T12:00:00Z",
            "required_authority": "pilot-owner",
            "question": "Which input is authoritative?",
        },
        "escalation": {
            "escalation_kind": "blocked",
            "escalation_route": "pilot-owner",
            "escalation_evidence_refs": ["evidence:escalation"],
        },
        "report": {
            "task_id": "tsk_01978abc-7102-7000-8000-000000007102",
            "attempt_id": "att_01978abc-7104-7000-8000-000000007104",
            "artefact_ids": ["art_01978abc-7105-7000-8000-000000007105"],
        },
        "review_request": {
            "review_id": "rev_01978abc-7106-7000-8000-000000007106",
            "subject_ids": ["task:pilot"],
            "subject_hashes": ["a" * 64],
        },
        "review_response": {
            "review_id": "rev_01978abc-7106-7000-8000-000000007106",
            "verdict_record_id": "rev_01978abc-7109-7000-8000-000000007109",
        },
        "decision_request": {
            "decision_id": "dec_01978abc-7107-7000-8000-000000007107",
            "question": "Approve the bounded transition?",
            "required_authority": "pilot-owner",
        },
        "handoff": {"scope_refs": ["scope:pilot"]},
    }
    return {**common, **additions[message_type]}


def _message_command(
    *,
    command_id: str,
    command_type: str,
    message_id: str,
    expected_stream_version: int,
    payload: dict,
) -> dict:
    return {
        "command_id": command_id,
        "command_type": command_type,
        "schema_id": f"ars://core/command/{command_type}",
        "schema_version": "1.0.0",
        "submitted_at": "2026-08-02T09:00:00Z",
        "actor_id": ACTORS["actor-a"],
        "on_behalf_of_actor_id": None,
        "authority_grant_id": "agr_01978abc-7108-7000-8000-000000007108",
        "target_stream_id": message_id,
        "expected_stream_version": expected_stream_version,
        "idempotency_key": f"message:{command_type}:{command_id}",
        "correlation_id": f"message-correlation:{command_id}",
        "causation_id": None,
        "reason": "exercise the frozen Message lifecycle pilot",
        "evidence_refs": [],
        "project_id": PROJECT_ID,
        "payload": payload,
    }


def _adapter_registration(
    *,
    project_id: str = PROJECT_ID,
    status: str = "eligible",
    effective_at: datetime = datetime(2026, 1, 1, tzinfo=UTC),
    expires_at: datetime | None = datetime(2030, 1, 1, tzinfo=UTC),
    applicable_command_types: tuple[str, ...] = (
        "RecordMessageDelivery",
        "RecordMessageDeliveryFailure",
    ),
    allowed_actor_ids: tuple[str, ...] = (ACTORS["actor-a"],),
) -> MessageAdapterRegistration:
    content = {
        "delivery_adapter_id": "pilot-adapter",
        "project_id": project_id,
        "registry_revision": "pilot-r1",
        "status": status,
        "effective_at": effective_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "expires_at": None if expires_at is None else expires_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "applicable_command_types": list(applicable_command_types),
        "allowed_actor_ids": list(allowed_actor_ids),
    }
    return MessageAdapterRegistration(
        delivery_adapter_id="pilot-adapter",
        project_id=project_id,
        registry_revision="pilot-r1",
        registry_content_sha256=sha256_hex(canonical_bytes(content)),
        status=status,
        effective_at=effective_at,
        expires_at=expires_at,
        applicable_command_types=applicable_command_types,
        allowed_actor_ids=allowed_actor_ids,
    )


def _adapter_registry() -> tuple[MessageAdapterRegistration, ...]:
    return (_adapter_registration(),)


def _no_domain_mutation_snapshot(harness) -> dict:
    ledger_snapshot = harness.ledger.snapshot()
    view = harness.service._view_for(ledger_snapshot)
    receipts_root = harness.receipts.receipts_root
    receipt_bytes = {
        path.relative_to(receipts_root).as_posix(): path.read_bytes() for path in receipts_root.rglob("*.json")
    }
    return {
        "tail": (ledger_snapshot.global_position, ledger_snapshot.event_hash),
        "batches": tuple(harness.ledger.iter_batches()),
        "versions": dict(ledger_snapshot.stream_versions),
        "accepted_receipts": {
            path: value
            for path, value in receipt_bytes.items()
            if "/idempotency/" not in f"/{path}" and b'"status":"accepted"' in value
        },
        "idempotency_indexes": {
            path: value for path, value in receipt_bytes.items() if path.startswith("idempotency/")
        },
        "command_ids": dict(view.batches_by_command_id),
        "command_scopes": dict(view.batches_by_scope),
        "projection": replay(ledger_snapshot.events, schema_registry=harness.schemas),
        "history": harness.replay().stream_states,
    }


def _accepted_delivery(harness, number: int) -> tuple[str, dict, object]:
    message_id = _message_id(number)
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(number),
                command_type="PublishMessage",
                message_id=message_id,
                expected_stream_version=0,
                payload=_publish_payload(message_id, "handoff"),
            )
        ).status
        == "accepted"
    )
    publication = tuple(harness.ledger.iter_events())[-1]
    delivery = _message_command(
        command_id=_command_id(number + 1),
        command_type="RecordMessageDelivery",
        message_id=message_id,
        expected_stream_version=1,
        payload={
            "message_id": message_id,
            "content_sha256": sha256_hex(canonical_bytes(publication["payload"])),
            "recipient_actor_ids": [ACTORS["actor-a"]],
            "delivery_adapter_id": "pilot-adapter",
            "delivery_evidence_refs": ["evidence:delivery"],
        },
    )
    accepted = harness.service.submit(delivery)
    assert accepted.status == "accepted"
    return message_id, delivery, accepted


def _delivery_scoped_index_path(harness):
    return next(
        path
        for path in harness.receipts.index_root.glob("*.json")
        if json.loads(path.read_text(encoding="utf-8"))["scope"][2] == "RecordMessageDelivery"
    )


def _matrix_row_command(harness, row_id: str, command_type: str, base: int):
    message_id = _message_id(base)
    if command_type == "PublishMessage":
        return (
            message_id,
            _message_command(
                command_id=_command_id(base),
                command_type=command_type,
                message_id=message_id,
                expected_stream_version=0,
                payload=_publish_payload(
                    message_id,
                    row_id.removeprefix("message.publish_"),
                ),
            ),
            None,
        )

    published = _message_command(
        command_id=_command_id(base),
        command_type="PublishMessage",
        message_id=message_id,
        expected_stream_version=0,
        payload=_publish_payload(message_id, "handoff"),
    )
    assert harness.service.submit(published).status == "accepted"
    publication = tuple(harness.ledger.iter_events())[-1]
    content_sha256 = sha256_hex(canonical_bytes(publication["payload"]))
    if command_type == "RecordMessageDelivery":
        return (
            message_id,
            _message_command(
                command_id=_command_id(base + 1),
                command_type=command_type,
                message_id=message_id,
                expected_stream_version=1,
                payload={
                    "message_id": message_id,
                    "content_sha256": content_sha256,
                    "recipient_actor_ids": [ACTORS["actor-a"]],
                    "delivery_adapter_id": "pilot-adapter",
                    "delivery_evidence_refs": ["evidence:delivery"],
                },
            ),
            publication,
        )
    if command_type == "AcknowledgeMessage":
        delivered = _message_command(
            command_id=_command_id(base + 1),
            command_type="RecordMessageDelivery",
            message_id=message_id,
            expected_stream_version=1,
            payload={
                "message_id": message_id,
                "content_sha256": content_sha256,
                "recipient_actor_ids": [ACTORS["actor-a"]],
                "delivery_adapter_id": "pilot-adapter",
                "delivery_evidence_refs": ["evidence:delivery"],
            },
        )
        assert harness.service.submit(delivered).status == "accepted"
        return (
            message_id,
            _message_command(
                command_id=_command_id(base + 2),
                command_type=command_type,
                message_id=message_id,
                expected_stream_version=2,
                payload={
                    "message_id": message_id,
                    "content_sha256": content_sha256,
                    "recipient_actor_ids": [ACTORS["actor-a"]],
                    "source_position": publication["global_position"],
                },
            ),
            publication,
        )
    assert command_type == "RecordMessageDeliveryFailure"
    return (
        message_id,
        _message_command(
            command_id=_command_id(base + 1),
            command_type=command_type,
            message_id=message_id,
            expected_stream_version=1,
            payload={
                "message_id": message_id,
                "delivery_adapter_id": "pilot-adapter",
                "failure_kind": "unreachable",
                "failure_evidence_refs": ["evidence:failure"],
            },
        ),
        publication,
    )


def _matrix_authority_negative(command: dict, row_id: str, base: int) -> dict:
    negative = deepcopy(command)
    negative["command_id"] = _command_id(base + 3)
    negative["idempotency_key"] = f"matrix-authority:{row_id}:{base}"
    negative["actor_id"] = ACTORS["actor-b"]
    if negative["command_type"] == "PublishMessage":
        negative["payload"]["sender_actor_id"] = ACTORS["actor-b"]
    return negative


def _matrix_decisive_negative(command: dict, publication: dict | None, base: int) -> dict:
    negative = deepcopy(command)
    negative["command_id"] = _command_id(base + 4)
    negative["idempotency_key"] = f"matrix-negative:{command['command_type']}:{base}"
    if command["command_type"] == "PublishMessage":
        negative["payload"]["sender_actor_id"] = ACTORS["actor-b"]
    elif command["command_type"] == "RecordMessageDelivery":
        negative["payload"]["content_sha256"] = "b" * 64
    elif command["command_type"] == "AcknowledgeMessage":
        assert publication is not None
        negative["payload"]["source_position"] = publication["global_position"] + 1
    else:
        negative["payload"]["failure_evidence_refs"] = []
    return negative


def _matrix_concurrency_harness(tmp_path):
    root = tmp_path / "matrix-concurrency"
    root.mkdir()
    return control_plane(root, message_adapter_registry=_adapter_registry())


def _assert_matrix_acknowledgement_race(tmp_path, base: int) -> None:
    harness = _matrix_concurrency_harness(tmp_path)
    message_id, _, _ = _accepted_delivery(harness, base)
    publication = tuple(harness.ledger.iter_events())[0]
    content_sha256 = sha256_hex(canonical_bytes(publication["payload"]))
    commands = {
        label: _message_command(
            command_id=_command_id(number),
            command_type="AcknowledgeMessage",
            message_id=message_id,
            expected_stream_version=2,
            payload={
                "message_id": message_id,
                "content_sha256": content_sha256,
                "recipient_actor_ids": [ACTORS["actor-a"]],
                "source_position": publication["global_position"],
            },
        )
        for label, number in (("left", base + 2), ("right", base + 3))
    }
    barrier = threading.Barrier(3)
    outcomes: dict[str, object] = {}

    def submit(label: str) -> None:
        barrier.wait()
        try:
            outcomes[label] = harness.service.submit(commands[label])
        except Exception as exc:  # noqa: BLE001 - the race contract defines the outcome.
            outcomes[label] = exc

    threads = [threading.Thread(target=submit, args=(label,)) for label in commands]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()

    accepted = [outcome for outcome in outcomes.values() if getattr(outcome, "status", None) == "accepted"]
    losers = [
        outcome for outcome in outcomes.values() if getattr(outcome, "reason_code", None) == "stream_version_conflict"
    ]
    assert len(accepted) == len(losers) == 1
    loser_label = next(
        label
        for label, outcome in outcomes.items()
        if getattr(outcome, "reason_code", None) == "stream_version_conflict"
    )
    before = _no_domain_mutation_snapshot(harness)
    assert harness.service.submit(commands[loser_label]).reason_code == "stream_version_conflict"
    assert _no_domain_mutation_snapshot(harness) == before


def _assert_matrix_delivery_failure_race(tmp_path, base: int) -> None:
    harness = _matrix_concurrency_harness(tmp_path)
    message_id = _message_id(base)
    published = _message_command(
        command_id=_command_id(base),
        command_type="PublishMessage",
        message_id=message_id,
        expected_stream_version=0,
        payload=_publish_payload(message_id, "handoff"),
    )
    assert harness.service.submit(published).status == "accepted"
    publication = tuple(harness.ledger.iter_events())[-1]
    content_sha256 = sha256_hex(canonical_bytes(publication["payload"]))
    commands = {
        "delivery": _message_command(
            command_id=_command_id(base + 1),
            command_type="RecordMessageDelivery",
            message_id=message_id,
            expected_stream_version=1,
            payload={
                "message_id": message_id,
                "content_sha256": content_sha256,
                "recipient_actor_ids": [ACTORS["actor-a"]],
                "delivery_adapter_id": "pilot-adapter",
                "delivery_evidence_refs": ["evidence:delivery"],
            },
        ),
        "failure": _message_command(
            command_id=_command_id(base + 2),
            command_type="RecordMessageDeliveryFailure",
            message_id=message_id,
            expected_stream_version=1,
            payload={
                "message_id": message_id,
                "delivery_adapter_id": "pilot-adapter",
                "failure_kind": "unreachable",
                "failure_evidence_refs": ["evidence:failure"],
            },
        ),
    }
    barrier = threading.Barrier(3)
    outcomes: dict[str, object] = {}

    def submit(label: str) -> None:
        barrier.wait()
        try:
            outcomes[label] = harness.service.submit(commands[label])
        except Exception as exc:  # noqa: BLE001 - the race contract defines the outcome.
            outcomes[label] = exc

    threads = [threading.Thread(target=submit, args=(label,)) for label in commands]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()

    accepted = [outcome for outcome in outcomes.values() if getattr(outcome, "status", None) == "accepted"]
    losers = [
        outcome for outcome in outcomes.values() if getattr(outcome, "reason_code", None) == "stream_version_conflict"
    ]
    assert len(accepted) == len(losers) == 1
    loser_label = next(
        label
        for label, outcome in outcomes.items()
        if getattr(outcome, "reason_code", None) == "stream_version_conflict"
    )
    before = _no_domain_mutation_snapshot(harness)
    assert harness.service.submit(commands[loser_label]).reason_code == "stream_version_conflict"
    assert _no_domain_mutation_snapshot(harness) == before


def _rehash_event(event: dict) -> dict:
    unsigned = dict(event)
    unsigned.pop("event_hash")
    return {**event, "event_hash": sha256_hex(canonical_bytes(unsigned))}


@pytest.mark.parametrize(
    ("command_type", "payload"),
    [
        ("PublishMessage", _publish_payload(_message_id(11), "handoff")),
        (
            "RecordMessageDelivery",
            {
                "message_id": _message_id(12),
                "content_sha256": "a" * 64,
                "recipient_actor_ids": [ACTORS["actor-a"]],
                "delivery_adapter_id": "pilot-adapter",
                "delivery_evidence_refs": ["evidence:delivery"],
            },
        ),
        (
            "AcknowledgeMessage",
            {
                "message_id": _message_id(13),
                "content_sha256": "a" * 64,
                "recipient_actor_ids": [ACTORS["actor-a"]],
                "source_position": 1,
            },
        ),
        (
            "RecordMessageDeliveryFailure",
            {
                "message_id": _message_id(14),
                "delivery_adapter_id": "pilot-adapter",
                "failure_kind": "unreachable",
                "failure_evidence_refs": ["evidence:failure"],
            },
        ),
    ],
    ids=("publish", "deliver", "acknowledge", "delivery-failure"),
)
def test_each_message_command_rejects_missing_lifecycle_authority_without_domain_mutation(
    tmp_path,
    command_type,
    payload,
):
    harness = control_plane(
        tmp_path,
        auto_authority=False,
        message_adapter_registry=_adapter_registry(),
    )
    message_id = payload.get("new_message_id", payload.get("message_id"))
    before = _no_domain_mutation_snapshot(harness)
    receipt = harness.service.submit(
        _message_command(
            command_id=_command_id(10 + len(command_type)),
            command_type=command_type,
            message_id=message_id,
            expected_stream_version=0,
            payload=payload,
        )
    )

    assert receipt.status == "rejected"
    assert receipt.reason_code == "lifecycle_authority_unauthorized"
    assert _no_domain_mutation_snapshot(harness) == before


@pytest.mark.parametrize(
    ("case", "command_types", "subject_kind", "subject_id_mode", "effective_at", "expires_at"),
    [
        (
            "wrong-command-kind",
            ("AcknowledgeMessage",),
            "message",
            "submitted-message",
            "2026-01-01T00:00:00Z",
            "2030-01-01T00:00:00Z",
        ),
        # A valid scoped grant cannot carry PublishMessage for task: activation
        # rejects that malformed authority object.  This valid task grant is the
        # closest isolated wrong-kind authority input the schema admits.
        (
            "wrong-subject-kind",
            None,
            "task",
            "task",
            "2026-01-01T00:00:00Z",
            "2030-01-01T00:00:00Z",
        ),
        (
            "wrong-subject-id",
            None,
            "message",
            "different-message",
            "2026-01-01T00:00:00Z",
            "2030-01-01T00:00:00Z",
        ),
        (
            "not-yet-effective",
            None,
            "message",
            "submitted-message",
            "2027-01-01T00:00:00Z",
            "2030-01-01T00:00:00Z",
        ),
        (
            "expired",
            None,
            "message",
            "submitted-message",
            "2026-01-01T00:00:00Z",
            "2026-07-01T00:00:00Z",
        ),
    ],
)
def test_publish_rejects_wrong_or_noncurrent_scoped_authority_without_domain_mutation(
    tmp_path,
    case,
    command_types,
    subject_kind,
    subject_id_mode,
    effective_at,
    expires_at,
):
    activation_time = {
        "not-yet-effective": datetime(2027, 2, 1, tzinfo=UTC),
        "expired": datetime(2026, 2, 1, tzinfo=UTC),
    }.get(case, datetime(2026, 8, 1, tzinfo=UTC))
    harness = control_plane(
        tmp_path,
        auto_authority=False,
        clock=lambda: activation_time,
        message_adapter_registry=_adapter_registry(),
    )
    message_id = _message_id(24)
    subject_id = {
        "submitted-message": message_id,
        "different-message": _message_id(25),
        "task": "tsk_01978abc-7111-7000-8000-000000007111",
    }[subject_id_mode]
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind=subject_kind,
        subject_id=subject_id,
        command_types=command_types,
        effective_at=effective_at,
        expires_at=expires_at,
    )
    harness.service.clock = lambda: datetime(2026, 8, 1, tzinfo=UTC)
    command = _message_command(
        command_id=_command_id(24),
        command_type="PublishMessage",
        message_id=message_id,
        expected_stream_version=0,
        payload=_publish_payload(message_id, "handoff"),
    )
    command["authority_grant_id"] = grant_id
    before = _no_domain_mutation_snapshot(harness)
    receipt = harness.service.submit(command)

    assert receipt.status == "rejected", case
    assert receipt.reason_code == "lifecycle_authority_unauthorized"
    assert _no_domain_mutation_snapshot(harness) == before


def test_publish_rejects_prohibited_actor_on_current_exact_message_grant_without_domain_mutation(
    tmp_path,
):
    harness = control_plane(
        tmp_path,
        auto_authority=False,
        message_adapter_registry=_adapter_registry(),
    )
    message_id = _message_id(26)
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="message",
        subject_id=message_id,
    )
    payload = _publish_payload(message_id, "handoff")
    payload["sender_actor_id"] = ACTORS["actor-b"]
    command = _message_command(
        command_id=_command_id(26),
        command_type="PublishMessage",
        message_id=message_id,
        expected_stream_version=0,
        payload=payload,
    )
    command["actor_id"] = ACTORS["actor-b"]
    command["authority_grant_id"] = grant_id
    before = _no_domain_mutation_snapshot(harness)
    receipt = harness.service.submit(command)

    assert receipt.status == "rejected"
    assert receipt.reason_code == "lifecycle_authority_unauthorized"
    assert _no_domain_mutation_snapshot(harness) == before


def test_publish_rejects_wrong_project_scope_authority_without_domain_mutation(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(27)
    command = _message_command(
        command_id=_command_id(27),
        command_type="PublishMessage",
        message_id=message_id,
        expected_stream_version=0,
        payload=_publish_payload(message_id, "handoff"),
    )
    command["project_id"] = "prj_01978abc-7112-7000-8000-000000007112"
    before = _no_domain_mutation_snapshot(harness)
    receipt = harness.service.submit(command)

    assert receipt.status == "rejected"
    assert receipt.reason_code == "lifecycle_authority_unauthorized"
    assert _no_domain_mutation_snapshot(harness) == before


@pytest.mark.parametrize(
    "message_type",
    [
        "assignment",
        "acknowledgement",
        "progress",
        "input_request",
        "escalation",
        "report",
        "review_request",
        "review_response",
        "decision_request",
        "handoff",
    ],
    ids=lambda value: f"message.publish_{value}",
)
def test_each_publish_discriminant_builds_its_closed_message_payload(tmp_path, message_type):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(
        100
        + list(
            "assignment acknowledgement progress input_request escalation report review_request review_response decision_request handoff".split()
        ).index(message_type)
    )
    payload = _publish_payload(message_id, message_type)
    command = _message_command(
        command_id=_command_id(100 + len(message_type)),
        command_type="PublishMessage",
        message_id=message_id,
        expected_stream_version=0,
        payload=payload,
    )

    receipt = harness.service.submit(command)
    event = tuple(harness.ledger.iter_events())[-1]

    assert receipt.status == "accepted"
    assert event["event_type"] == "MessagePublished"
    assert event["payload"] == payload
    assert event["command_payload_hash"] == sha256_hex(canonical_bytes(payload))


@pytest.mark.parametrize(
    ("case", "mutate"),
    [
        ("unsupported", lambda payload: payload.__setitem__("message_type", "notice")),
        ("missing", lambda payload: payload.pop("scope_refs")),
        ("aliased", lambda payload: payload.__setitem__("message_type", "input-request")),
        (
            "payload-inconsistent",
            lambda payload: payload.__setitem__("task_id", "tsk_01978abc-7102-7000-8000-000000007102"),
        ),
    ],
)
def test_publish_discriminants_fail_closed_before_mutating_domain_state(tmp_path, case, mutate):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(190)
    payload = _publish_payload(message_id, "handoff")
    mutate(payload)
    before = _no_domain_mutation_snapshot(harness)

    with pytest.raises(SchemaError):
        harness.service.submit(
            _message_command(
                command_id=_command_id(190),
                command_type="PublishMessage",
                message_id=message_id,
                expected_stream_version=0,
                payload=payload,
            )
        )
    assert _no_domain_mutation_snapshot(harness) == before, case


def test_delivery_acknowledgement_and_failure_follow_only_the_frozen_paths(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(200)
    published = _message_command(
        command_id=_command_id(200),
        command_type="PublishMessage",
        message_id=message_id,
        expected_stream_version=0,
        payload=_publish_payload(message_id, "handoff"),
    )
    assert harness.service.submit(published).status == "accepted"
    publication = tuple(harness.ledger.iter_events())[-1]
    content_sha256 = sha256_hex(canonical_bytes(publication["payload"]))
    delivery = _message_command(
        command_id=_command_id(201),
        command_type="RecordMessageDelivery",
        message_id=message_id,
        expected_stream_version=1,
        payload={
            "message_id": message_id,
            "content_sha256": content_sha256,
            "recipient_actor_ids": [ACTORS["actor-a"]],
            "delivery_adapter_id": "pilot-adapter",
            "delivery_evidence_refs": ["evidence:delivery"],
        },
    )
    assert harness.service.submit(delivery).status == "accepted"
    acknowledgement = _message_command(
        command_id=_command_id(202),
        command_type="AcknowledgeMessage",
        message_id=message_id,
        expected_stream_version=2,
        payload={
            "message_id": message_id,
            "content_sha256": content_sha256,
            "recipient_actor_ids": [ACTORS["actor-a"]],
            "source_position": publication["global_position"],
        },
    )
    assert harness.service.submit(acknowledgement).status == "accepted"
    state = replay(harness.ledger.iter_events(), schema_registry=harness.schemas)
    assert state["streams"][message_id]["status"] == "acknowledged"


@pytest.mark.parametrize(
    ("registry", "reason"),
    [
        (None, "missing-default"),
        ((), "missing"),
        ((_adapter_registration(), _adapter_registration()), "ambiguous"),
        ((_adapter_registration(status="suspended"),), "status"),
        (
            (_adapter_registration(project_id="prj_01978abc-7110-7000-8000-000000007110"),),
            "project",
        ),
        ((_adapter_registration(applicable_command_types=("RecordMessageDeliveryFailure",)),), "capability"),
        ((_adapter_registration(allowed_actor_ids=(ACTORS["actor-b"],)),), "actor"),
        ((_adapter_registration(effective_at=datetime(2027, 1, 1, tzinfo=UTC)),), "not-effective"),
        ((_adapter_registration(expires_at=datetime(2026, 7, 1, tzinfo=UTC)),), "expired"),
    ],
)
def test_delivery_rejects_invalid_service_local_adapter_snapshot_without_ledger_mutation(
    tmp_path,
    registry,
    reason,
):
    harness = control_plane(tmp_path, message_adapter_registry=registry)
    message_id = _message_id(300)
    published = _message_command(
        command_id=_command_id(300),
        command_type="PublishMessage",
        message_id=message_id,
        expected_stream_version=0,
        payload=_publish_payload(message_id, "handoff"),
    )
    assert harness.service.submit(published).status == "accepted"
    publication = tuple(harness.ledger.iter_events())[-1]
    before = _no_domain_mutation_snapshot(harness)
    rejected = harness.service.submit(
        _message_command(
            command_id=_command_id(301),
            command_type="RecordMessageDelivery",
            message_id=message_id,
            expected_stream_version=1,
            payload={
                "message_id": message_id,
                "content_sha256": sha256_hex(canonical_bytes(publication["payload"])),
                "recipient_actor_ids": [ACTORS["actor-a"]],
                "delivery_adapter_id": "pilot-adapter",
                "delivery_evidence_refs": ["evidence:delivery"],
            },
        )
    )

    assert rejected.status == "rejected", reason
    assert rejected.reason_code == "message_adapter_unauthorized"
    assert _no_domain_mutation_snapshot(harness) == before


@pytest.mark.parametrize(
    ("field", "value"),
    [("status", "retired"), ("registry_revision", "pilot-r2")],
    ids=("status", "revision"),
)
def test_adapter_snapshot_content_hash_cannot_self_attest_mutated_entry_content(field, value):
    entry = _adapter_registration()
    changed = {
        "delivery_adapter_id": entry.delivery_adapter_id,
        "project_id": entry.project_id,
        "registry_revision": entry.registry_revision,
        "registry_content_sha256": entry.registry_content_sha256,
        "status": entry.status,
        "effective_at": entry.effective_at,
        "expires_at": entry.expires_at,
        "applicable_command_types": entry.applicable_command_types,
        "allowed_actor_ids": entry.allowed_actor_ids,
    }
    changed[field] = value
    with pytest.raises(ValueError, match="content hash"):
        MessageAdapterRegistration(**changed)


def test_delivery_failure_requires_its_own_adapter_capability_and_frozen_snapshot(tmp_path):
    registrations = [_adapter_registration(applicable_command_types=("RecordMessageDelivery",))]
    harness = control_plane(tmp_path, message_adapter_registry=registrations)
    registrations.clear()
    copied_message_id = _message_id(349)
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(349),
                command_type="PublishMessage",
                message_id=copied_message_id,
                expected_stream_version=0,
                payload=_publish_payload(copied_message_id, "handoff"),
            )
        ).status
        == "accepted"
    )
    copied_publication = tuple(harness.ledger.iter_events())[-1]
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(348),
                command_type="RecordMessageDelivery",
                message_id=copied_message_id,
                expected_stream_version=1,
                payload={
                    "message_id": copied_message_id,
                    "content_sha256": sha256_hex(canonical_bytes(copied_publication["payload"])),
                    "recipient_actor_ids": [ACTORS["actor-a"]],
                    "delivery_adapter_id": "pilot-adapter",
                    "delivery_evidence_refs": ["evidence:delivery"],
                },
            )
        ).status
        == "accepted"
    )
    message_id = _message_id(350)
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(350),
                command_type="PublishMessage",
                message_id=message_id,
                expected_stream_version=0,
                payload=_publish_payload(message_id, "handoff"),
            )
        ).status
        == "accepted"
    )
    before = _no_domain_mutation_snapshot(harness)
    rejected = harness.service.submit(
        _message_command(
            command_id=_command_id(351),
            command_type="RecordMessageDeliveryFailure",
            message_id=message_id,
            expected_stream_version=1,
            payload={
                "message_id": message_id,
                "delivery_adapter_id": "pilot-adapter",
                "failure_kind": "unreachable",
                "failure_evidence_refs": ["evidence:failure"],
            },
        )
    )

    assert rejected.reason_code == "message_adapter_unauthorized"
    assert _no_domain_mutation_snapshot(harness) == before


def test_plain_control_plane_uses_explicit_adapter_snapshot_with_manually_activated_authority(tmp_path):
    harness = control_plane(
        tmp_path,
        auto_authority=False,
        message_adapter_registry=_adapter_registry(),
    )
    message_id = _message_id(375)
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="message",
        subject_id=message_id,
    )
    published = _message_command(
        command_id=_command_id(375),
        command_type="PublishMessage",
        message_id=message_id,
        expected_stream_version=0,
        payload=_publish_payload(message_id, "handoff"),
    )
    published["authority_grant_id"] = grant_id
    assert harness.service.submit(published).status == "accepted"
    publication = tuple(harness.ledger.iter_events())[-1]
    delivery = _message_command(
        command_id=_command_id(376),
        command_type="RecordMessageDelivery",
        message_id=message_id,
        expected_stream_version=1,
        payload={
            "message_id": message_id,
            "content_sha256": sha256_hex(canonical_bytes(publication["payload"])),
            "recipient_actor_ids": [ACTORS["actor-a"]],
            "delivery_adapter_id": "pilot-adapter",
            "delivery_evidence_refs": ["evidence:delivery"],
        },
    )
    delivery["authority_grant_id"] = grant_id

    assert harness.service.submit(delivery).status == "accepted"


@pytest.mark.parametrize(
    ("command_type", "payload"),
    [
        (
            "RecordMessageDelivery",
            {
                "delivery_adapter_id": "pilot-adapter",
                "delivery_evidence_refs": [],
            },
        ),
        (
            "RecordMessageDeliveryFailure",
            {
                "delivery_adapter_id": "pilot-adapter",
                "failure_kind": "unreachable",
                "failure_evidence_refs": [],
            },
        ),
    ],
    ids=("message.deliver", "message.delivery_failure"),
)
def test_adapter_transitions_require_evidence_before_any_ledger_mutation(
    tmp_path,
    command_type,
    payload,
):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(400)
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(400),
                command_type="PublishMessage",
                message_id=message_id,
                expected_stream_version=0,
                payload=_publish_payload(message_id, "handoff"),
            )
        ).status
        == "accepted"
    )
    publication = tuple(harness.ledger.iter_events())[-1]
    before = _no_domain_mutation_snapshot(harness)
    transition_payload = {"message_id": message_id, **payload}
    if command_type == "RecordMessageDelivery":
        transition_payload.update(
            {
                "content_sha256": sha256_hex(canonical_bytes(publication["payload"])),
                "recipient_actor_ids": [ACTORS["actor-a"]],
            }
        )
    rejected = harness.service.submit(
        _message_command(
            command_id=_command_id(401),
            command_type=command_type,
            message_id=message_id,
            expected_stream_version=1,
            payload=transition_payload,
        )
    )

    assert rejected.status == "rejected"
    assert rejected.reason_code == "message_evidence_required"
    assert _no_domain_mutation_snapshot(harness) == before


def test_external_reply_lineage_is_preserved_while_self_and_bad_acknowledgement_links_fail_closed(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(500)
    published = _message_command(
        command_id=_command_id(500),
        command_type="PublishMessage",
        message_id=message_id,
        expected_stream_version=0,
        payload=_publish_payload(message_id, "handoff"),
    )
    assert harness.service.submit(published).status == "accepted"
    event = tuple(harness.ledger.iter_events())[-1]
    assert event["payload"]["reply_to_message_id"] == _message_id(999)

    before = tuple(harness.ledger.iter_events())
    self_link = _publish_payload(_message_id(501), "handoff")
    self_link["reply_to_message_id"] = _message_id(501)
    self_rejected = harness.service.submit(
        _message_command(
            command_id=_command_id(501),
            command_type="PublishMessage",
            message_id=_message_id(501),
            expected_stream_version=0,
            payload=self_link,
        )
    )
    assert self_rejected.reason_code == "message_self_reference"
    assert tuple(harness.ledger.iter_events()) == before

    bad_ack = _publish_payload(_message_id(502), "acknowledgement")
    bad_ack["correlation_message_id"] = _message_id(998)
    correlation_rejected = harness.service.submit(
        _message_command(
            command_id=_command_id(502),
            command_type="PublishMessage",
            message_id=_message_id(502),
            expected_stream_version=0,
            payload=bad_ack,
        )
    )
    assert correlation_rejected.reason_code == "message_correlation_mismatch"
    assert tuple(harness.ledger.iter_events()) == before


@pytest.mark.parametrize(
    ("message_type", "mutate", "reason"),
    [
        (
            "handoff",
            lambda payload, message_id: payload.__setitem__("reply_to_message_id", message_id),
            "self reference",
        ),
        (
            "acknowledgement",
            lambda payload, _ignored: payload.__setitem__("correlation_message_id", _message_id(996)),
            "correlation",
        ),
    ],
    ids=("self-link", "acknowledgement-correlation"),
)
def test_replay_rejects_message_lineage_divergence_even_when_event_hash_is_recomputed(
    tmp_path,
    message_type,
    mutate,
    reason,
):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(550)
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(550),
                command_type="PublishMessage",
                message_id=message_id,
                expected_stream_version=0,
                payload=_publish_payload(message_id, message_type),
            )
        ).status
        == "accepted"
    )
    forged = deepcopy(list(harness.ledger.iter_events()))
    mutate(forged[0]["payload"], message_id)
    forged[0]["command_payload_hash"] = sha256_hex(canonical_bytes(forged[0]["payload"]))
    forged[0] = _rehash_event(forged[0])

    with pytest.raises(IntegrityError, match=reason):
        replay(forged, schema_registry=harness.schemas)


def test_unknown_major_message_event_fails_before_projection_publication(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(560)
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(560),
                command_type="PublishMessage",
                message_id=message_id,
                expected_stream_version=0,
                payload=_publish_payload(message_id, "handoff"),
            )
        ).status
        == "accepted"
    )
    unknown_major = deepcopy(list(harness.ledger.iter_events()))
    unknown_major[0]["schema_version"] = "2.0.0"
    unknown_major[0] = _rehash_event(unknown_major[0])
    projection_path = tmp_path / "existing-message-projection.json"
    projection_path.write_bytes(b"previous-projection\n")
    before = _no_domain_mutation_snapshot(harness)

    with pytest.raises(IntegrityError, match="unsupported major at 1"):
        rebuild_projection(unknown_major, projection_path, schema_registry=harness.schemas)
    assert projection_path.read_bytes() == b"previous-projection\n"
    assert _no_domain_mutation_snapshot(harness) == before


def test_recognized_message_event_under_generic_schema_fails_before_projection_publication(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(565)
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(565),
                command_type="PublishMessage",
                message_id=message_id,
                expected_stream_version=0,
                payload=_publish_payload(message_id, "handoff"),
            )
        ).status
        == "accepted"
    )
    forged = deepcopy(list(harness.ledger.iter_events()))
    forged[0]["schema_id"] = "ars://core/event"
    forged[0] = _rehash_event(forged[0])
    projection_path = tmp_path / "generic-message-projection.json"
    projection_path.write_bytes(b"previous-projection\n")
    before = _no_domain_mutation_snapshot(harness)

    with pytest.raises(IntegrityError, match="exact lifecycle event provenance mismatch"):
        rebuild_projection(forged, projection_path, schema_registry=harness.schemas)

    assert projection_path.read_bytes() == b"previous-projection\n"
    assert _no_domain_mutation_snapshot(harness) == before


@pytest.mark.parametrize(
    ("case", "mutate", "reason"),
    [
        (
            "sender",
            lambda payload: payload.__setitem__("sender_actor_id", ACTORS["actor-b"]),
            "message_sender_mismatch",
        ),
        (
            "new-message-id",
            lambda payload: payload.__setitem__("new_message_id", _message_id(572)),
            "invalid_message_subject_identity",
        ),
    ],
)
def test_publish_identity_rejections_preserve_full_domain_state(tmp_path, case, mutate, reason):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(570)
    payload = _publish_payload(message_id, "handoff")
    mutate(payload)
    before = _no_domain_mutation_snapshot(harness)
    rejected = harness.service.submit(
        _message_command(
            command_id=_command_id(570),
            command_type="PublishMessage",
            message_id=message_id,
            expected_stream_version=0,
            payload=payload,
        )
    )

    assert rejected.status == "rejected", case
    assert rejected.reason_code == reason
    assert _no_domain_mutation_snapshot(harness) == before


@pytest.mark.parametrize(
    ("case", "mutate", "reason"),
    [
        (
            "message-id",
            lambda payload: payload.__setitem__("message_id", _message_id(582)),
            "invalid_message_subject_identity",
        ),
        (
            "content-sha256",
            lambda payload: payload.__setitem__("content_sha256", "0" * 64),
            "message_content_mismatch",
        ),
        (
            "recipient-set",
            lambda payload: payload.__setitem__("recipient_actor_ids", [ACTORS["actor-b"]]),
            "message_content_mismatch",
        ),
        (
            "adapter-id",
            lambda payload: payload.__setitem__("delivery_adapter_id", "unknown-pilot-adapter"),
            "message_adapter_unauthorized",
        ),
    ],
)
def test_delivery_identity_content_and_adapter_rejections_preserve_full_domain_state(
    tmp_path,
    case,
    mutate,
    reason,
):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(580)
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(580),
                command_type="PublishMessage",
                message_id=message_id,
                expected_stream_version=0,
                payload=_publish_payload(message_id, "handoff"),
            )
        ).status
        == "accepted"
    )
    publication = tuple(harness.ledger.iter_events())[-1]
    payload = {
        "message_id": message_id,
        "content_sha256": sha256_hex(canonical_bytes(publication["payload"])),
        "recipient_actor_ids": [ACTORS["actor-a"]],
        "delivery_adapter_id": "pilot-adapter",
        "delivery_evidence_refs": ["evidence:delivery"],
    }
    mutate(payload)
    before = _no_domain_mutation_snapshot(harness)
    rejected = harness.service.submit(
        _message_command(
            command_id=_command_id(581),
            command_type="RecordMessageDelivery",
            message_id=message_id,
            expected_stream_version=1,
            payload=payload,
        )
    )

    assert rejected.status == "rejected", case
    assert rejected.reason_code == reason
    assert _no_domain_mutation_snapshot(harness) == before


def test_acknowledgement_requires_delivery_and_a_published_recipient_without_domain_mutation(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(590)
    published_payload = _publish_payload(message_id, "handoff")
    published_payload["recipient_actor_ids"] = [ACTORS["actor-b"]]
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(590),
                command_type="PublishMessage",
                message_id=message_id,
                expected_stream_version=0,
                payload=published_payload,
            )
        ).status
        == "accepted"
    )
    publication = tuple(harness.ledger.iter_events())[-1]
    content_sha256 = sha256_hex(canonical_bytes(publication["payload"]))
    acknowledgement_payload = {
        "message_id": message_id,
        "content_sha256": content_sha256,
        "recipient_actor_ids": [ACTORS["actor-b"]],
        "source_position": publication["global_position"],
    }
    before = _no_domain_mutation_snapshot(harness)
    before_delivery = harness.service.submit(
        _message_command(
            command_id=_command_id(591),
            command_type="AcknowledgeMessage",
            message_id=message_id,
            expected_stream_version=1,
            payload=acknowledgement_payload,
        )
    )
    assert before_delivery.reason_code == "invalid_message_transition"
    assert _no_domain_mutation_snapshot(harness) == before

    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(592),
                command_type="RecordMessageDelivery",
                message_id=message_id,
                expected_stream_version=1,
                payload={
                    "message_id": message_id,
                    "content_sha256": content_sha256,
                    "recipient_actor_ids": [ACTORS["actor-b"]],
                    "delivery_adapter_id": "pilot-adapter",
                    "delivery_evidence_refs": ["evidence:delivery"],
                },
            )
        ).status
        == "accepted"
    )
    before = _no_domain_mutation_snapshot(harness)
    nonrecipient = harness.service.submit(
        _message_command(
            command_id=_command_id(593),
            command_type="AcknowledgeMessage",
            message_id=message_id,
            expected_stream_version=2,
            payload=acknowledgement_payload,
        )
    )
    assert nonrecipient.reason_code == "message_recipient_mismatch"
    assert _no_domain_mutation_snapshot(harness) == before


def test_delivery_retry_and_changed_idempotency_or_command_identity_are_atomic(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(600)
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(600),
                command_type="PublishMessage",
                message_id=message_id,
                expected_stream_version=0,
                payload=_publish_payload(message_id, "handoff"),
            )
        ).status
        == "accepted"
    )
    publication = tuple(harness.ledger.iter_events())[-1]
    delivery = _message_command(
        command_id=_command_id(601),
        command_type="RecordMessageDelivery",
        message_id=message_id,
        expected_stream_version=1,
        payload={
            "message_id": message_id,
            "content_sha256": sha256_hex(canonical_bytes(publication["payload"])),
            "recipient_actor_ids": [ACTORS["actor-a"]],
            "delivery_adapter_id": "pilot-adapter",
            "delivery_evidence_refs": ["evidence:delivery"],
        },
    )
    first = harness.service.submit(delivery)
    before = _no_domain_mutation_snapshot(harness)
    harness.service._message_adapter_registry = (_adapter_registration(status="retired"),)
    assert harness.service.submit(delivery) == first
    assert _no_domain_mutation_snapshot(harness) == before

    changed_command_id = dict(delivery)
    changed_command_id["command_id"] = _command_id(602)
    with pytest.raises(ConflictError, match="idempotency key"):
        harness.service.submit(changed_command_id)
    changed_idempotency = dict(delivery)
    changed_idempotency["idempotency_key"] = "message:changed-idempotency"
    with pytest.raises(ConflictError, match="command ID"):
        harness.service.submit(changed_idempotency)
    assert _no_domain_mutation_snapshot(harness) == before


def test_published_message_payload_is_detached_from_caller_and_remains_deliverable(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(603)
    submitted = _message_command(
        command_id=_command_id(603),
        command_type="PublishMessage",
        message_id=message_id,
        expected_stream_version=0,
        payload=_publish_payload(message_id, "handoff"),
    )
    expected_payload = deepcopy(submitted["payload"])
    assert harness.service.submit(submitted).status == "accepted"

    submitted["payload"]["body"] = "caller-mutated-after-acceptance"

    cached_publication = harness.ledger.snapshot().events[-1]
    durable_publication = tuple(harness.ledger.iter_events())[-1]
    assert cached_publication["payload"] == expected_payload
    assert durable_publication["payload"] == expected_payload
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(604),
                command_type="RecordMessageDelivery",
                message_id=message_id,
                expected_stream_version=1,
                payload={
                    "message_id": message_id,
                    "content_sha256": sha256_hex(canonical_bytes(expected_payload)),
                    "recipient_actor_ids": [ACTORS["actor-a"]],
                    "delivery_adapter_id": "pilot-adapter",
                    "delivery_evidence_refs": ["evidence:delivery"],
                },
            )
        ).status
        == "accepted"
    )


@pytest.mark.parametrize("axis", ("project", "current-authority"))
def test_adapter_retry_rechecks_project_and_current_authority_before_returning_receipt(tmp_path, axis):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id, delivery, accepted = _accepted_delivery(harness, 605)
    retry = deepcopy(delivery)
    if axis == "project":
        retry["project_id"] = "prj_01978abc-7112-7000-8000-000000007112"
    else:
        revoke_lifecycle_grant(harness, subject_id=message_id)
    before = _no_domain_mutation_snapshot(harness)

    rejected = harness.service.submit(retry)

    assert rejected.status == "rejected", axis
    assert rejected != accepted
    assert rejected.reason_code == "lifecycle_authority_unauthorized"
    assert _no_domain_mutation_snapshot(harness) == before


def test_adapter_retry_rejects_unsupported_major_history_without_mutation(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    _, delivery, _ = _accepted_delivery(harness, 610)
    event_path = max(harness.ledger.events_root.rglob("*.jsonl"))
    forged = json.loads(event_path.read_text(encoding="utf-8"))
    forged["schema_version"] = "2.0.0"
    event_path.write_bytes(canonical_bytes(_rehash_event(forged)) + b"\n")
    before = {
        "events": {
            path.relative_to(harness.ledger.events_root).as_posix(): path.read_bytes()
            for path in harness.ledger.events_root.rglob("*.jsonl")
        },
        "receipts": {
            path.relative_to(harness.receipts.receipts_root).as_posix(): path.read_bytes()
            for path in harness.receipts.receipts_root.rglob("*.json")
        },
    }

    with pytest.raises(IntegrityError, match="unsupported major at 2"):
        harness.service.submit(delivery)

    after = {
        "events": {
            path.relative_to(harness.ledger.events_root).as_posix(): path.read_bytes()
            for path in harness.ledger.events_root.rglob("*.jsonl")
        },
        "receipts": {
            path.relative_to(harness.receipts.receipts_root).as_posix(): path.read_bytes()
            for path in harness.receipts.receipts_root.rglob("*.json")
        },
    }
    assert after == before


def test_adapter_retry_reconciles_missing_scoped_index_without_new_message_event(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    _, delivery, accepted = _accepted_delivery(harness, 615)
    index_path = _delivery_scoped_index_path(harness)
    expected_index = index_path.read_bytes()
    index_path.unlink()
    before = _no_domain_mutation_snapshot(harness)

    retried = harness.service.submit(delivery)

    after = _no_domain_mutation_snapshot(harness)
    assert retried == accepted
    assert index_path.read_bytes() == expected_index
    for axis in (
        "tail",
        "batches",
        "versions",
        "accepted_receipts",
        "command_ids",
        "command_scopes",
        "projection",
        "history",
    ):
        assert after[axis] == before[axis]


def test_orphan_message_receipt_is_rejected_before_append_without_mutation(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(616)
    command = _message_command(
        command_id=_command_id(616),
        command_type="PublishMessage",
        message_id=message_id,
        expected_stream_version=0,
        payload=_publish_payload(message_id, "handoff"),
    )
    orphan = Receipt(
        status="accepted",
        command_id=command["command_id"],
        payload_hash=sha256_hex(canonical_bytes(command["payload"])),
        event_batch_id="orphan-batch",
        observed_stream_version=1,
    )
    harness.receipts.write(orphan)
    receipt_bytes_before = {
        path.relative_to(harness.receipts.receipts_root).as_posix(): path.read_bytes()
        for path in harness.receipts.receipts_root.rglob("*.json")
    }
    index_bytes_before = {
        path.relative_to(harness.receipts.index_root).as_posix(): path.read_bytes()
        for path in harness.receipts.index_root.rglob("*.json")
    }
    before = _no_domain_mutation_snapshot(harness)
    event_count_before = len(tuple(harness.ledger.iter_events()))

    with pytest.raises(
        ConflictError,
        match=f"^receipt already exists: {command['command_id']}$",
    ):
        harness.service.submit(command)

    after = _no_domain_mutation_snapshot(harness)
    receipt_bytes_after = {
        path.relative_to(harness.receipts.receipts_root).as_posix(): path.read_bytes()
        for path in harness.receipts.receipts_root.rglob("*.json")
    }
    index_bytes_after = {
        path.relative_to(harness.receipts.index_root).as_posix(): path.read_bytes()
        for path in harness.receipts.index_root.rglob("*.json")
    }
    assert event_count_before == 0
    assert len(tuple(harness.ledger.iter_events())) == event_count_before
    assert after["tail"] == before["tail"]
    assert after["batches"] == before["batches"]
    assert after["versions"] == before["versions"]
    assert receipt_bytes_after == receipt_bytes_before
    assert after["accepted_receipts"] == before["accepted_receipts"]
    assert index_bytes_after == index_bytes_before
    assert after["idempotency_indexes"] == before["idempotency_indexes"]
    assert after["command_ids"] == before["command_ids"]
    assert after["command_scopes"] == before["command_scopes"]
    assert after["history"] == before["history"]
    assert after["projection"] == before["projection"]


def test_adapter_retry_rejects_foreign_scoped_index_without_mutation(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    _, delivery, _ = _accepted_delivery(harness, 620)
    index_path = _delivery_scoped_index_path(harness)
    foreign = json.loads(index_path.read_text(encoding="utf-8"))
    foreign["project_id"] = "prj_01978abc-7113-7000-8000-000000007113"
    index_path.write_bytes(canonical_bytes(foreign))
    before = _no_domain_mutation_snapshot(harness)

    with pytest.raises(ConflictError, match="idempotency index target mismatch"):
        harness.service.submit(delivery)

    assert _no_domain_mutation_snapshot(harness) == before


def test_invalid_message_schema_rejection_preserves_full_domain_state(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(610)
    payload = _publish_payload(message_id, "handoff")
    payload["body"] = None
    before = _no_domain_mutation_snapshot(harness)

    with pytest.raises(SchemaError):
        harness.service.submit(
            _message_command(
                command_id=_command_id(610),
                command_type="PublishMessage",
                message_id=message_id,
                expected_stream_version=0,
                payload=payload,
            )
        )
    assert _no_domain_mutation_snapshot(harness) == before


def test_acknowledgement_race_has_one_stable_conflict_loser_without_extra_mutation(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(620)
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(620),
                command_type="PublishMessage",
                message_id=message_id,
                expected_stream_version=0,
                payload=_publish_payload(message_id, "handoff"),
            )
        ).status
        == "accepted"
    )
    publication = tuple(harness.ledger.iter_events())[-1]
    content_sha256 = sha256_hex(canonical_bytes(publication["payload"]))
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(621),
                command_type="RecordMessageDelivery",
                message_id=message_id,
                expected_stream_version=1,
                payload={
                    "message_id": message_id,
                    "content_sha256": content_sha256,
                    "recipient_actor_ids": [ACTORS["actor-a"]],
                    "delivery_adapter_id": "pilot-adapter",
                    "delivery_evidence_refs": ["evidence:delivery"],
                },
            )
        ).status
        == "accepted"
    )
    acknowledgement_payload = {
        "message_id": message_id,
        "content_sha256": content_sha256,
        "recipient_actor_ids": [ACTORS["actor-a"]],
        "source_position": publication["global_position"],
    }
    commands = {
        label: _message_command(
            command_id=_command_id(number),
            command_type="AcknowledgeMessage",
            message_id=message_id,
            expected_stream_version=2,
            payload=acknowledgement_payload,
        )
        for label, number in (("left", 622), ("right", 623))
    }
    barrier = threading.Barrier(3)
    outcomes: dict[str, object] = {}

    def submit(label: str) -> None:
        barrier.wait()
        outcomes[label] = harness.service.submit(commands[label])

    left = threading.Thread(target=submit, args=("left",))
    right = threading.Thread(target=submit, args=("right",))
    left.start()
    right.start()
    barrier.wait()
    left.join()
    right.join()

    accepted = [outcome for outcome in outcomes.values() if getattr(outcome, "status", None) == "accepted"]
    conflicts = [
        outcome for outcome in outcomes.values() if getattr(outcome, "reason_code", None) == "stream_version_conflict"
    ]
    assert len(accepted) == len(conflicts) == 1
    assert len(tuple(harness.ledger.iter_events())) == 3
    loser_label = next(
        label
        for label, outcome in outcomes.items()
        if getattr(outcome, "reason_code", None) == "stream_version_conflict"
    )
    before = _no_domain_mutation_snapshot(harness)
    repeated_loser = harness.service.submit(commands[loser_label])
    assert repeated_loser.reason_code == "stream_version_conflict"
    assert _no_domain_mutation_snapshot(harness) == before


def test_delivery_failure_race_has_one_terminal_winner_and_one_unchanged_loser(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(700)
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(700),
                command_type="PublishMessage",
                message_id=message_id,
                expected_stream_version=0,
                payload=_publish_payload(message_id, "handoff"),
            )
        ).status
        == "accepted"
    )
    publication = tuple(harness.ledger.iter_events())[-1]
    content_sha256 = sha256_hex(canonical_bytes(publication["payload"]))
    delivery = _message_command(
        command_id=_command_id(701),
        command_type="RecordMessageDelivery",
        message_id=message_id,
        expected_stream_version=1,
        payload={
            "message_id": message_id,
            "content_sha256": content_sha256,
            "recipient_actor_ids": [ACTORS["actor-a"]],
            "delivery_adapter_id": "pilot-adapter",
            "delivery_evidence_refs": ["evidence:delivery"],
        },
    )
    failure = _message_command(
        command_id=_command_id(702),
        command_type="RecordMessageDeliveryFailure",
        message_id=message_id,
        expected_stream_version=1,
        payload={
            "message_id": message_id,
            "delivery_adapter_id": "pilot-adapter",
            "failure_kind": "unreachable",
            "failure_evidence_refs": ["evidence:failure"],
        },
    )
    barrier = threading.Barrier(3)
    outcomes: list[object] = []

    def submit(command: dict) -> None:
        barrier.wait()
        try:
            outcomes.append(harness.service.submit(command))
        except Exception as exc:  # noqa: BLE001 - the loser is contract-defined below.
            outcomes.append(exc)

    left = threading.Thread(target=submit, args=(delivery,))
    right = threading.Thread(target=submit, args=(failure,))
    left.start()
    right.start()
    barrier.wait()
    left.join()
    right.join()

    accepted = [outcome for outcome in outcomes if getattr(outcome, "status", None) == "accepted"]
    conflicts = [outcome for outcome in outcomes if getattr(outcome, "reason_code", None) == "stream_version_conflict"]
    assert len(accepted) == len(conflicts) == 1
    events = tuple(harness.ledger.iter_events())
    assert len(events) == 2
    terminal = replay(events, schema_registry=harness.schemas)["streams"][message_id]
    assert terminal["status"] in {"delivered", "delivery_failed"}


def test_delivery_and_failure_reject_after_each_terminal_message_state_without_mutation(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    acknowledged_id = _message_id(750)
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(750),
                command_type="PublishMessage",
                message_id=acknowledged_id,
                expected_stream_version=0,
                payload=_publish_payload(acknowledged_id, "handoff"),
            )
        ).status
        == "accepted"
    )
    acknowledged_publication = tuple(harness.ledger.iter_events())[-1]
    acknowledged_hash = sha256_hex(canonical_bytes(acknowledged_publication["payload"]))
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(751),
                command_type="RecordMessageDelivery",
                message_id=acknowledged_id,
                expected_stream_version=1,
                payload={
                    "message_id": acknowledged_id,
                    "content_sha256": acknowledged_hash,
                    "recipient_actor_ids": [ACTORS["actor-a"]],
                    "delivery_adapter_id": "pilot-adapter",
                    "delivery_evidence_refs": ["evidence:delivery"],
                },
            )
        ).status
        == "accepted"
    )
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(752),
                command_type="AcknowledgeMessage",
                message_id=acknowledged_id,
                expected_stream_version=2,
                payload={
                    "message_id": acknowledged_id,
                    "content_sha256": acknowledged_hash,
                    "recipient_actor_ids": [ACTORS["actor-a"]],
                    "source_position": acknowledged_publication["global_position"],
                },
            )
        ).status
        == "accepted"
    )
    before = _no_domain_mutation_snapshot(harness)
    for command_type, payload in (
        (
            "RecordMessageDelivery",
            {
                "message_id": acknowledged_id,
                "content_sha256": acknowledged_hash,
                "recipient_actor_ids": [ACTORS["actor-a"]],
                "delivery_adapter_id": "pilot-adapter",
                "delivery_evidence_refs": ["evidence:delivery"],
            },
        ),
        (
            "RecordMessageDeliveryFailure",
            {
                "message_id": acknowledged_id,
                "delivery_adapter_id": "pilot-adapter",
                "failure_kind": "unreachable",
                "failure_evidence_refs": ["evidence:failure"],
            },
        ),
    ):
        rejected = harness.service.submit(
            _message_command(
                command_id=_command_id(753 + len(command_type)),
                command_type=command_type,
                message_id=acknowledged_id,
                expected_stream_version=3,
                payload=payload,
            )
        )
        assert rejected.reason_code == "invalid_message_transition"
        assert _no_domain_mutation_snapshot(harness) == before

    failed_id = _message_id(760)
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(760),
                command_type="PublishMessage",
                message_id=failed_id,
                expected_stream_version=0,
                payload=_publish_payload(failed_id, "handoff"),
            )
        ).status
        == "accepted"
    )
    failed_publication = tuple(harness.ledger.iter_events())[-1]
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(761),
                command_type="RecordMessageDeliveryFailure",
                message_id=failed_id,
                expected_stream_version=1,
                payload={
                    "message_id": failed_id,
                    "delivery_adapter_id": "pilot-adapter",
                    "failure_kind": "unreachable",
                    "failure_evidence_refs": ["evidence:failure"],
                },
            )
        ).status
        == "accepted"
    )
    before = _no_domain_mutation_snapshot(harness)
    rejected = harness.service.submit(
        _message_command(
            command_id=_command_id(762),
            command_type="RecordMessageDelivery",
            message_id=failed_id,
            expected_stream_version=2,
            payload={
                "message_id": failed_id,
                "content_sha256": sha256_hex(canonical_bytes(failed_publication["payload"])),
                "recipient_actor_ids": [ACTORS["actor-a"]],
                "delivery_adapter_id": "pilot-adapter",
                "delivery_evidence_refs": ["evidence:delivery"],
            },
        )
    )
    assert rejected.reason_code == "invalid_message_transition"
    assert _no_domain_mutation_snapshot(harness) == before


def test_delivery_failure_is_a_replayable_terminal_path_and_message_provenance_divergence_fails_closed(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(800)
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(800),
                command_type="PublishMessage",
                message_id=message_id,
                expected_stream_version=0,
                payload=_publish_payload(message_id, "handoff"),
            )
        ).status
        == "accepted"
    )
    failed = harness.service.submit(
        _message_command(
            command_id=_command_id(801),
            command_type="RecordMessageDeliveryFailure",
            message_id=message_id,
            expected_stream_version=1,
            payload={
                "message_id": message_id,
                "delivery_adapter_id": "pilot-adapter",
                "failure_kind": "unreachable",
                "failure_evidence_refs": ["evidence:failure"],
            },
        )
    )
    assert failed.status == "accepted"
    events = list(harness.ledger.iter_events())
    state = replay(events, schema_registry=harness.schemas)
    assert state["streams"][message_id]["status"] == "delivery_failed"
    projection_path = tmp_path / "message-projection.json"
    assert rebuild_projection(events, projection_path, schema_registry=harness.schemas) == state
    assert harness.replay().stream_states[message_id]["status"] == "delivery_failed"

    divergent = deepcopy(events)
    divergent[0]["payload"]["reply_to_message_id"] = _message_id(997)
    unsigned = dict(divergent[0])
    unsigned.pop("event_hash")
    divergent[0]["event_hash"] = sha256_hex(canonical_bytes(unsigned))
    with pytest.raises(IntegrityError, match="provenance"):
        replay(divergent, schema_registry=harness.schemas)


def test_replay_rejects_missing_message_reducer_route_and_divergent_terminal_history(tmp_path):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(820)
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(820),
                command_type="PublishMessage",
                message_id=message_id,
                expected_stream_version=0,
                payload=_publish_payload(message_id, "handoff"),
            )
        ).status
        == "accepted"
    )
    publication = tuple(harness.ledger.iter_events())[-1]
    content_sha256 = sha256_hex(canonical_bytes(publication["payload"]))
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(821),
                command_type="RecordMessageDelivery",
                message_id=message_id,
                expected_stream_version=1,
                payload={
                    "message_id": message_id,
                    "content_sha256": content_sha256,
                    "recipient_actor_ids": [ACTORS["actor-a"]],
                    "delivery_adapter_id": "pilot-adapter",
                    "delivery_evidence_refs": ["evidence:delivery"],
                },
            )
        ).status
        == "accepted"
    )
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(822),
                command_type="AcknowledgeMessage",
                message_id=message_id,
                expected_stream_version=2,
                payload={
                    "message_id": message_id,
                    "content_sha256": content_sha256,
                    "recipient_actor_ids": [ACTORS["actor-a"]],
                    "source_position": publication["global_position"],
                },
            )
        ).status
        == "accepted"
    )
    events = list(harness.ledger.iter_events())
    before = _no_domain_mutation_snapshot(harness)

    missing_route = deepcopy(events[:1])
    missing_route[0]["schema_id"] = "ars://core/event"
    missing_route[0]["event_type"] = "MessageReducerRouteMissing"
    missing_route[0] = _rehash_event(missing_route[0])
    with pytest.raises(IntegrityError, match="unsupported event type"):
        replay(missing_route, schema_registry=harness.schemas)

    divergent_terminal = deepcopy(events)
    failure_binding = harness.schemas.command_binding("RecordMessageDeliveryFailure")
    assert failure_binding is not None
    divergent_terminal[-1].update(
        {
            "event_type": "MessageDeliveryFailed",
            "command_type": "RecordMessageDeliveryFailure",
            "command_schema_id": failure_binding.schema_id,
            "command_schema_version": failure_binding.schema_version,
            "command_schema_sha256": harness.schemas.resolve_identity(
                failure_binding.schema_id,
                failure_binding.schema_version,
            ).sha256,
            "schema_id": "ars://core/event/MessageDeliveryFailed",
            "schema_version": "1.0.0",
            "payload": {
                "message_id": message_id,
                "delivery_adapter_id": "pilot-adapter",
                "failure_kind": "unreachable",
                "failure_evidence_refs": ["evidence:failure"],
            },
        }
    )
    divergent_terminal[-1]["command_payload_hash"] = sha256_hex(canonical_bytes(divergent_terminal[-1]["payload"]))
    divergent_terminal[-1] = _rehash_event(divergent_terminal[-1])
    with pytest.raises(IntegrityError, match="requires published Message state"):
        replay(divergent_terminal, schema_registry=harness.schemas)
    assert _no_domain_mutation_snapshot(harness) == before


@pytest.mark.parametrize(
    ("case", "event_index", "field", "value", "reason"),
    [
        ("published-sender", 0, "actor_id", ACTORS["actor-b"], "sender binding"),
        ("acknowledgement-recipient", 2, "actor_id", ACTORS["actor-b"], "recipient binding"),
    ],
)
def test_replay_rejects_message_actor_binding_divergence(
    tmp_path,
    case,
    event_index,
    field,
    value,
    reason,
):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(830)
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(830),
                command_type="PublishMessage",
                message_id=message_id,
                expected_stream_version=0,
                payload=_publish_payload(message_id, "handoff"),
            )
        ).status
        == "accepted"
    )
    publication = tuple(harness.ledger.iter_events())[-1]
    content_sha256 = sha256_hex(canonical_bytes(publication["payload"]))
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(831),
                command_type="RecordMessageDelivery",
                message_id=message_id,
                expected_stream_version=1,
                payload={
                    "message_id": message_id,
                    "content_sha256": content_sha256,
                    "recipient_actor_ids": [ACTORS["actor-a"]],
                    "delivery_adapter_id": "pilot-adapter",
                    "delivery_evidence_refs": ["evidence:delivery"],
                },
            )
        ).status
        == "accepted"
    )
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(832),
                command_type="AcknowledgeMessage",
                message_id=message_id,
                expected_stream_version=2,
                payload={
                    "message_id": message_id,
                    "content_sha256": content_sha256,
                    "recipient_actor_ids": [ACTORS["actor-a"]],
                    "source_position": publication["global_position"],
                },
            )
        ).status
        == "accepted"
    )
    forged = deepcopy(list(harness.ledger.iter_events()))
    forged[event_index][field] = value
    forged[event_index] = _rehash_event(forged[event_index])
    before = _no_domain_mutation_snapshot(harness)

    with pytest.raises(IntegrityError, match=reason):
        replay(forged[: event_index + 1] if event_index == 0 else forged, schema_registry=harness.schemas)
    assert _no_domain_mutation_snapshot(harness) == before, case


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("content_sha256", "0" * 64, "message_content_mismatch"),
        ("recipient_actor_ids", [ACTORS["actor-b"]], "message_content_mismatch"),
        ("source_position", 999, "message_content_mismatch"),
    ],
    ids=("content-hash", "recipient-set", "publication-source-position"),
)
def test_acknowledgement_binds_publication_content_and_position_before_mutation(
    tmp_path,
    field,
    value,
    reason,
):
    harness = control_plane(tmp_path, message_adapter_registry=_adapter_registry())
    message_id = _message_id(900)
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(900),
                command_type="PublishMessage",
                message_id=message_id,
                expected_stream_version=0,
                payload=_publish_payload(message_id, "handoff"),
            )
        ).status
        == "accepted"
    )
    publication = tuple(harness.ledger.iter_events())[-1]
    content_sha256 = sha256_hex(canonical_bytes(publication["payload"]))
    assert (
        harness.service.submit(
            _message_command(
                command_id=_command_id(901),
                command_type="RecordMessageDelivery",
                message_id=message_id,
                expected_stream_version=1,
                payload={
                    "message_id": message_id,
                    "content_sha256": content_sha256,
                    "recipient_actor_ids": [ACTORS["actor-a"]],
                    "delivery_adapter_id": "pilot-adapter",
                    "delivery_evidence_refs": ["evidence:delivery"],
                },
            )
        ).status
        == "accepted"
    )
    before = _no_domain_mutation_snapshot(harness)
    acknowledgement = {
        "message_id": message_id,
        "content_sha256": content_sha256,
        "recipient_actor_ids": [ACTORS["actor-a"]],
        "source_position": publication["global_position"],
    }
    acknowledgement[field] = value
    rejected = harness.service.submit(
        _message_command(
            command_id=_command_id(902),
            command_type="AcknowledgeMessage",
            message_id=message_id,
            expected_stream_version=2,
            payload=acknowledgement,
        )
    )
    assert rejected.reason_code == reason
    assert _no_domain_mutation_snapshot(harness) == before
