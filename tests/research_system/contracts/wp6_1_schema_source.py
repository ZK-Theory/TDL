"""Verified design sources and typed payload model for WP6.1 schemas.

The generated contract is deliberately derived from the reviewed Git objects,
not from the mutable checkout or the runtime registry.  Every owner row has one
explicit resolver; an unknown or missing row is an error rather than an
invitation to manufacture a generic payload.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ANNEX_REVISION = "fe5f1d40bc8f05f061317c677b5891cea0711249"
ANNEX_PATH = "docs/plans/agentic-research-system/implementation/06d-wp6-1-owner-source-catalogue.md"
ANNEX_BLOB = "5e2eb60ca4419d1529506de6859fb027cff518af"
ANNEX_SHA256 = "96932fd752362eddb6da2da77bc0b56ccb8e83ced58e93c3b139e3248acb08f7"
W2_PATH = "docs/plans/agentic-research-system/design/02-task-event-and-artifact-schema.md"
W2_BLOB = "7e09a9c49605663bb50163840fff3ae4c8212748"
W2_SHA256 = "dd5f45ec91cb4c10f0e8d1d99341ad16745bec21f58400b6643285224870f9c6"
W8_PATH = "docs/plans/agentic-research-system/design/08-resource-checkpoint-and-operations.md"
W8_BLOB = "d26f24b9a6670b095d307fe531a7bb9b31c55311"
W8_SHA256 = "84c80a8b499394fed65ed0d4e7fe1f4f9a85a8ccc23b299c85198e5d60e79a58"
TICK = chr(96)


@dataclass(frozen=True)
class ApprovedSource:
    name: str
    path: str
    revision: str
    blob: str
    sha256: str


ANNEX_SOURCE = ApprovedSource("06d", ANNEX_PATH, ANNEX_REVISION, ANNEX_BLOB, ANNEX_SHA256)
W2_SOURCE = ApprovedSource("W2", W2_PATH, ANNEX_REVISION, W2_BLOB, W2_SHA256)
W8_SOURCE = ApprovedSource("W8", W8_PATH, ANNEX_REVISION, W8_BLOB, W8_SHA256)


@dataclass(frozen=True)
class SourceCitation:
    source: ApprovedSource
    section: str
    row_key: str | None = None

    def text(self) -> str:
        row = f", owner row `{self.row_key}`" if self.row_key else ""
        return f"{self.source.name} {self.section}{row} at {self.source.revision}:{self.source.path}"


@dataclass(frozen=True)
class FieldSpec:
    name: str
    json_type: str
    citations: tuple[SourceCitation, ...]
    const: str | None = None
    nullable: bool = False
    item_type: str | None = None
    object_spec: ObjectSpec | None = None
    minimum: int | None = None
    format: str | None = None


@dataclass(frozen=True)
class ObjectSpec:
    fields: tuple[FieldSpec, ...]
    citations: tuple[SourceCitation, ...]


@dataclass(frozen=True)
class OperationSpec:
    row_key: str
    command_payload: ObjectSpec
    event_payloads: tuple[tuple[str, ObjectSpec], ...]


@dataclass(frozen=True)
class SourceRow:
    source_table: str
    key: str
    owner_transition: str
    command_event_identity: str
    command_token: str
    command_type: str
    events: tuple[tuple[str, str], ...]
    reducer_projection: str
    authority: str
    receipt_tests: str


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def canonical_yaml_bytes(value: Any) -> bytes:
    import yaml

    text = yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=4096)
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def git_blob_id(repo_root: Path, data: bytes) -> str:
    """Ask Git for the raw, no-filter blob identity; never use SHA-1 directly."""
    result = subprocess.run(
        ["git", "hash-object", "--no-filters", "--stdin"],
        cwd=repo_root,
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout.decode("ascii").strip()


def approved_source_bytes(repo_root: Path, source: ApprovedSource) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{source.revision}:{source.path}"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"approved WP6.1 {source.name} object is unavailable")
    data = result.stdout
    if git_blob_id(repo_root, data) != source.blob:
        raise RuntimeError(f"approved WP6.1 {source.name} Git blob mismatch")
    if hashlib.sha256(data).hexdigest() != source.sha256:
        raise RuntimeError(f"approved WP6.1 {source.name} SHA-256 mismatch")
    if data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise RuntimeError(f"approved WP6.1 {source.name} bytes are not UTF-8/LF canonical")
    return data


def approved_annex_bytes(repo_root: Path) -> bytes:
    return approved_source_bytes(repo_root, ANNEX_SOURCE)


def _plain(value: str) -> str:
    return value.replace(TICK, "")


def _parse_rows(data: bytes) -> list[SourceRow]:
    section: str | None = None
    rows: list[SourceRow] = []
    for line in data.decode("utf-8").splitlines():
        if line.startswith("## 2. "):
            section = "w2_lifecycle"
        elif line.startswith("## 3. "):
            section = "w2_messages_governance"
        elif line.startswith("## 4. "):
            section = "w8_operator"
        elif line.startswith("## 5. "):
            section = None
        if section is None or not line.startswith(f"| {TICK}"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6:
            continue
        parts = [_plain(item.strip()) for item in cells[2].split(";")]
        if len(parts) != 3:
            raise RuntimeError(f"malformed command/event cell for {cells[0]}")
        command_token, command_type = (item.strip() for item in parts[0].split(" / ", 1))
        events = [item.strip() for item in parts[1].strip("[]").split(",")]
        event_tokens = [item.strip() for item in parts[2].strip("[]").split(",")]
        if len(events) != len(event_tokens):
            raise RuntimeError(f"event/token mismatch for {cells[0]}")
        rows.append(
            SourceRow(
                source_table=section,
                key=_plain(cells[0]),
                owner_transition=cells[1],
                command_event_identity=cells[2],
                command_token=command_token,
                command_type=command_type,
                events=tuple(zip(events, event_tokens, strict=True)),
                reducer_projection=cells[3],
                authority=cells[4],
                receipt_tests=cells[5],
            )
        )
    if len(rows) != 104 or len({row.key for row in rows}) != 104:
        raise RuntimeError("approved WP6.1 06d row cardinality is not exactly 104")
    return rows


def source_rows(repo_root: Path) -> list[SourceRow]:
    return _parse_rows(approved_annex_bytes(repo_root))


def source_citation(row: SourceRow) -> str:
    return _row_citation(row).text()


def snake(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()


def schema_identity(token: str, semantic_type: str, kind: str) -> dict[str, str]:
    suffix = token.split("/", 1)[1]
    if kind == "command":
        return {
            "schema_token": token,
            "command_schema_path": f".research-system/schemas/core/commands/{suffix}.schema.json",
            "command_schema_id": f"ars://core/command/{semantic_type}",
            "command_schema_version": "1.0.0",
        }
    return {
        "event_type": semantic_type,
        "schema_token": token,
        "event_schema_path": f".research-system/schemas/core/events/{suffix}.schema.json",
        "event_schema_id": f"ars://core/event/{semantic_type}",
        "event_schema_version": "1.0.0",
    }


def grouped_rows(rows: Iterable[SourceRow], *, kind: str) -> dict[str, list[tuple[SourceRow, str, str]]]:
    grouped: dict[str, list[tuple[SourceRow, str, str]]] = {}
    for row in rows:
        values = (
            [(row.command_token, row.command_type)]
            if kind == "command"
            else [(event_token, event_type) for event_type, event_token in row.events]
        )
        for token, semantic_type in values:
            path = schema_identity(token, semantic_type, kind)[f"{kind}_schema_path"]
            grouped.setdefault(path, []).append((row, token, semantic_type))
    return grouped


COMMAND_ROOT_NAMES = (
    "command_id",
    "command_type",
    "schema_id",
    "schema_version",
    "submitted_at",
    "actor_id",
    "on_behalf_of_actor_id",
    "authority_grant_id",
    "target_stream_id",
    "expected_stream_version",
    "idempotency_key",
    "correlation_id",
    "causation_id",
    "reason",
    "evidence_refs",
    "payload",
)
EVENT_ROOT_NAMES = (
    "event_id",
    "event_type",
    "schema_id",
    "schema_version",
    "project_id",
    "stream_id",
    "stream_version",
    "global_position",
    "transaction_id",
    "transaction_index",
    "transaction_count",
    "command_id",
    "command_type",
    "command_schema_id",
    "command_schema_version",
    "command_schema_sha256",
    "idempotency_key",
    "command_payload_hash",
    "correlation_id",
    "causation_id",
    "actor_id",
    "authority_grant_id",
    "occurred_at",
    "recorded_at",
    "payload",
    "previous_event_hash",
    "event_hash",
)


_INTEGER_FIELDS = {
    "revision",
    "task_revision",
    "scope_revision",
    "attempt_ordinal",
    "execution_epoch",
    "heartbeat_sequence",
    "expected_dispatch_stream_version",
    "expected_task_stream_version",
    "completed_units",
    "remaining_units",
    "resource_request_revision",
    "stream_version",
    "global_position",
    "transaction_index",
    "transaction_count",
    "expected_stream_version",
}
_BOOLEAN_FIELDS = {"must_stop", "available", "regenerable", "integrity_valid", "restore_valid", "writers_closed"}
_ARRAY_FIELDS = {
    "member_ids",
    "member_dispositions",
    "evidence_refs",
    "recipient_actor_ids",
    "audience_actor_ids",
    "valid_artefact_ids",
    "artefact_ids",
    "checkpoint_ids",
    "finding_ids",
    "condition_ids",
    "input_ids",
    "affected_projection_ids",
    "affected_consumer_ids",
    "allowed_consumer_ids",
    "required_evidence_ids",
    "root_binding_ids",
    "capability_ids",
    "resource_ids",
    "process_ids",
    "child_process_ids",
}


def _domain_source(row: SourceRow) -> ApprovedSource:
    return W8_SOURCE if row.source_table == "w8_operator" else W2_SOURCE


def _domain_section(row: SourceRow) -> str:
    family = row.key.split(".", 1)[0]
    if row.source_table == "w8_operator":
        return {
            "operator.request_resource_grant": "§§7-8, §20",
            "operator.claim_execution_lease": "§12, §20",
            "operator.record_heartbeat": "§12, §20",
            "operator.request_pause": "§17.2, §20",
            "operator.confirm_pause": "§17.2, §20",
            "operator.request_stop": "§17.1, §20",
            "operator.confirm_stop": "§17.1, §20",
            "operator.request_resume": "§17.3, §20",
            "operator.release_resources": "§§7-8, §20",
            "operator.quarantine_orphan": "§18, §20",
            "operator.adopt_late_artefact": "§18, §20",
            "operator.create_backup": "§19, §20",
            "operator.verify_restore": "§19, §20",
        }[row.key]
    return {
        "scope": "§10.2",
        "task": "§§10-11",
        "dispatch": "§12.1",
        "lease": "§12.3",
        "attempt": "§12.4",
        "checkpoint": "§12.5",
        "message": "§14.1",
        "blocker": "§15.1",
        "artefact": "§16",
        "review": "§17",
        "decision": "§18",
        "rule": "§18.4",
        "correction": "§19.1",
    }[family]


def _row_citation(row: SourceRow) -> SourceCitation:
    section = {"w2_lifecycle": "§2", "w2_messages_governance": "§3", "w8_operator": "§4"}[row.source_table]
    return SourceCitation(ANNEX_SOURCE, section, row.key)


def _citations(row: SourceRow) -> tuple[SourceCitation, ...]:
    return (SourceCitation(_domain_source(row), _domain_section(row)), _row_citation(row))


def _field(name: str, citations: tuple[SourceCitation, ...], *, const: str | None = None) -> FieldSpec:
    if name == "declared_write_set":
        member = ObjectSpec(
            fields=(
                FieldSpec("stream_kind", "string", citations),
                FieldSpec("stream_id", "string", citations),
                FieldSpec("expected_version", "integer", citations),
            ),
            citations=citations,
        )
        return FieldSpec(name, "array", citations, object_spec=member)
    if name in _INTEGER_FIELDS or name.endswith("_version") or name.endswith("_ordinal"):
        return FieldSpec(name, "integer", citations, const=const)
    if name in _BOOLEAN_FIELDS:
        return FieldSpec(name, "boolean", citations, const=const)
    if name in _ARRAY_FIELDS or name.endswith("_ids") or name.endswith("_refs"):
        return FieldSpec(name, "array", citations, const=const, item_type="string")
    return FieldSpec(name, "string", citations, const=const)


def _object(row: SourceRow, names: tuple[str, ...], consts: Mapping[str, str] | None = None) -> ObjectSpec:
    citations = _citations(row)
    consts = consts or {}
    return ObjectSpec(tuple(_field(name, citations, const=consts.get(name)) for name in names), citations)


# Each tuple is (command fields, event fact field sets, command constants, event constants).
# The map is intentionally exhaustive and has no family/default resolver.
_OperationData = tuple[tuple[str, ...], tuple[tuple[str, ...], ...], Mapping[str, str], tuple[Mapping[str, str], ...]]


def _d(
    command: tuple[str, ...],
    *events: tuple[str, ...],
    command_consts: Mapping[str, str] | None = None,
    event_consts: tuple[Mapping[str, str], ...] | None = None,
) -> _OperationData:
    return command, events, command_consts or {}, event_consts or tuple({} for _ in events)


_OPERATION_DATA: dict[str, _OperationData] = {
    "scope.create": _d(
        ("new_scope_definition_id", "revision", "member_ids", "completion_predicate"),
        ("scope_definition_id", "revision", "member_ids", "completion_predicate"),
    ),
    "scope.amend_revision": _d(
        ("scope_definition_id", "revision", "member_dispositions", "amendment_reason"),
        ("scope_definition_id", "revision", "member_dispositions", "amended_at"),
    ),
    "scope.supersede": _d(
        ("scope_definition_id", "superseding_scope_definition_id", "supersession_reason"),
        ("scope_definition_id", "superseding_scope_definition_id", "superseded_at"),
    ),
    "scope.complete": _d(
        ("scope_definition_id", "scope_revision", "member_dispositions", "completion_evidence_ref"),
        ("scope_definition_id", "scope_revision", "member_dispositions", "completed_at"),
    ),
    "task.create": _d(
        ("new_task_id", "revision", "objective", "scope_definition_id", "acceptance_criteria_ref"),
        ("task_id", "revision", "objective", "scope_definition_id"),
    ),
    "task.amend_revision": _d(
        ("task_id", "revision", "objective", "amendment_reason"), ("task_id", "revision", "objective", "amended_at")
    ),
    "task.request_readiness": _d(
        ("task_id", "task_revision", "readiness_evidence_ref"),
        ("task_id", "task_revision", "readiness_evidence_ref", "requested_at"),
    ),
    "task.approve_readiness": _d(
        ("task_id", "task_revision", "readiness_review_id"),
        ("task_id", "task_revision", "readiness_review_id", "approved_at"),
    ),
    "task.block": _d(("task_id", "blocker_id", "block_reason"), ("task_id", "blocker_id", "blocked_at")),
    "task.request_input": _d(
        ("task_id", "input_requirement_id", "requested_from_actor_id"),
        ("task_id", "input_requirement_id", "requested_from_actor_id", "requested_at"),
    ),
    "task.pause": _d(("task_id", "attempt_id", "pause_reason"), ("task_id", "attempt_id", "paused_at")),
    "task.claim_start": _d(
        (
            "dispatch_id",
            "task_id",
            "task_revision",
            "lease_id",
            "expected_dispatch_stream_version",
            "expected_task_stream_version",
            "declared_write_set",
        ),
        ("dispatch_id", "task_id", "task_revision", "lease_id", "claimed_at"),
        ("task_id", "task_revision", "dispatch_id", "lease_id", "started_at"),
    ),
    "task.submit_review": _d(
        ("task_id", "task_revision", "review_id"), ("task_id", "task_revision", "review_id", "submitted_at")
    ),
    "task.resume": _d(
        ("task_id", "attempt_id", "resume_evidence_ref"), ("task_id", "attempt_id", "resume_evidence_ref", "resumed_at")
    ),
    "task.accept": _d(
        ("task_id", "task_revision", "review_id", "acceptance_evidence_ref"),
        ("task_id", "task_revision", "review_id", "accepted_at"),
    ),
    "task.reject": _d(
        ("task_id", "task_revision", "review_id", "rejection_reason"),
        ("task_id", "task_revision", "review_id", "rejected_at"),
    ),
    "task.close_partial": _d(
        ("task_id", "partial_reason", "valid_artefact_ids"),
        ("task_id", "partial_reason", "valid_artefact_ids", "recorded_at"),
    ),
    "task.cancel": _d(
        ("task_id", "cancel_reason", "cancellation_evidence_ref"), ("task_id", "cancel_reason", "cancelled_at")
    ),
    "task.supersede": _d(
        ("task_id", "superseding_task_id", "supersession_reason"), ("task_id", "superseding_task_id", "superseded_at")
    ),
    "task.reopen_partial": _d(
        ("task_id", "reopen_reason", "review_id"), ("task_id", "prior_status", "reopen_reason", "reopened_at")
    ),
    "task.reopen_rejected": _d(
        ("task_id", "reopen_reason", "review_id"), ("task_id", "prior_status", "reopen_reason", "reopened_at")
    ),
    "task.reopen_cancelled": _d(
        ("task_id", "reopen_reason", "review_id"), ("task_id", "prior_status", "reopen_reason", "reopened_at")
    ),
    "dispatch.issue": _d(
        ("dispatch_id", "task_id", "task_revision", "target_profile_id", "context_packet_id", "root_binding_ids"),
        ("dispatch_id", "task_id", "task_revision", "target_profile_id", "issued_at"),
    ),
    "dispatch.deliver": _d(
        ("dispatch_id", "delivery_message_id", "delivery_evidence_ref"),
        ("dispatch_id", "delivery_message_id", "delivered_at"),
    ),
    "dispatch.acknowledge": _d(
        ("dispatch_id", "acknowledgement_message_id", "acknowledging_actor_id"),
        ("dispatch_id", "acknowledgement_message_id", "acknowledged_at"),
    ),
    "dispatch.claim": _d(
        (
            "dispatch_id",
            "task_id",
            "task_revision",
            "lease_id",
            "expected_dispatch_stream_version",
            "expected_task_stream_version",
            "declared_write_set",
        ),
        ("dispatch_id", "task_id", "task_revision", "lease_id", "claimed_at"),
        ("task_id", "task_revision", "dispatch_id", "lease_id", "started_at"),
    ),
    "dispatch.fulfil": _d(
        ("dispatch_id", "attempt_id", "artefact_ids"), ("dispatch_id", "attempt_id", "artefact_ids", "fulfilled_at")
    ),
    "dispatch.expire_issued": _d(
        ("dispatch_id", "observed_at", "expiry_reason"), ("dispatch_id", "prior_status", "observed_at", "expiry_reason")
    ),
    "dispatch.expire_delivered": _d(
        ("dispatch_id", "observed_at", "expiry_reason"), ("dispatch_id", "prior_status", "observed_at", "expiry_reason")
    ),
    "dispatch.expire_acknowledged": _d(
        ("dispatch_id", "observed_at", "expiry_reason"), ("dispatch_id", "prior_status", "observed_at", "expiry_reason")
    ),
    "dispatch.withdraw_issued": _d(
        ("dispatch_id", "withdrawal_reason", "replacement_dispatch_id"),
        ("dispatch_id", "withdrawal_reason", "withdrawn_at"),
    ),
    "dispatch.withdraw_claimed": _d(
        ("dispatch_id", "withdrawal_reason", "replacement_dispatch_id"),
        ("dispatch_id", "withdrawal_reason", "withdrawn_at"),
    ),
    "lease.activate": _d(
        ("new_lease_id", "task_id", "task_revision", "dispatch_id", "attempt_id", "expires_at"),
        ("lease_id", "task_id", "task_revision", "dispatch_id", "attempt_id", "granted_at", "expires_at"),
    ),
    "lease.renew": _d(
        ("lease_id", "expires_at", "heartbeat_event_id"), ("lease_id", "prior_expiry_at", "expires_at", "renewed_at")
    ),
    "lease.release": _d(
        ("lease_id", "release_reason", "release_evidence_ref"), ("lease_id", "release_reason", "released_at")
    ),
    "lease.expire": _d(("lease_id", "observed_at", "expiry_reason"), ("lease_id", "observed_at", "expiry_reason")),
    "lease.revoke": _d(
        ("lease_id", "revocation_reason", "revocation_evidence_ref"), ("lease_id", "revocation_reason", "revoked_at")
    ),
    "attempt.create": _d(
        ("new_attempt_id", "task_id", "task_revision", "dispatch_id", "lease_id", "attempt_ordinal", "execution_epoch"),
        ("attempt_id", "task_id", "task_revision", "attempt_ordinal", "execution_epoch"),
    ),
    "attempt.claim": _d(
        ("attempt_id", "lease_id", "holder_actor_id"), ("attempt_id", "lease_id", "holder_actor_id", "claimed_at")
    ),
    "attempt.start": _d(
        ("attempt_id", "process_identity_id", "start_evidence_ref"), ("attempt_id", "process_identity_id", "started_at")
    ),
    "attempt.complete": _d(
        ("attempt_id", "artefact_ids", "completion_evidence_ref"), ("attempt_id", "artefact_ids", "completed_at")
    ),
    "attempt.fail": _d(
        ("attempt_id", "failure_reason", "failure_evidence_ref"), ("attempt_id", "failure_reason", "failed_at")
    ),
    "attempt.partial": _d(
        ("attempt_id", "partial_reason", "valid_artefact_ids"),
        ("attempt_id", "partial_reason", "valid_artefact_ids", "recorded_at"),
    ),
    "attempt.pause": _d(("attempt_id", "checkpoint_id", "pause_reason"), ("attempt_id", "checkpoint_id", "paused_at")),
    "attempt.resume": _d(
        ("attempt_id", "checkpoint_id", "compatibility_fingerprint"),
        ("attempt_id", "checkpoint_id", "execution_epoch", "resumed_at"),
    ),
    "attempt.request_stop": _d(
        ("attempt_id", "lease_id", "stop_reason"), ("attempt_id", "lease_id", "stop_reason", "requested_at")
    ),
    "attempt.abandon": _d(
        ("attempt_id", "stop_record_id", "terminal_evidence_ref"), ("attempt_id", "stop_record_id", "abandoned_at")
    ),
    "attempt.supersede": _d(
        ("attempt_id", "superseding_attempt_id", "supersession_reason"),
        ("attempt_id", "superseding_attempt_id", "superseded_at"),
    ),
    "attempt.retry": _d(
        (
            "new_attempt_id",
            "task_id",
            "task_revision",
            "previous_attempt_id",
            "retry_reason",
            "attempt_ordinal",
            "execution_epoch",
        ),
        ("attempt_id", "task_id", "task_revision", "previous_attempt_id", "attempt_ordinal", "execution_epoch"),
    ),
    "checkpoint.record": _d(
        (
            "attempt_id",
            "task_id",
            "task_revision",
            "checkpoint_manifest_id",
            "compatibility_fingerprint",
            "completed_units",
            "remaining_units",
        ),
        (
            "checkpoint_id",
            "attempt_id",
            "task_id",
            "task_revision",
            "checkpoint_manifest_id",
            "compatibility_fingerprint",
            "recorded_at",
        ),
    ),
    "message.publish_assignment": _d(
        (
            "new_message_id",
            "message_type",
            "sender_actor_id",
            "recipient_actor_ids",
            "thread_id",
            "task_id",
            "dispatch_id",
            "assignee_id",
        ),
        ("message_id", "message_type", "task_id", "dispatch_id", "assignee_id", "published_at"),
        command_consts={"message_type": "assignment"},
        event_consts=({"message_type": "assignment"},),
    ),
    "message.publish_acknowledgement": _d(
        (
            "new_message_id",
            "message_type",
            "sender_actor_id",
            "recipient_actor_ids",
            "thread_id",
            "acknowledged_message_id",
            "acknowledgement_body",
        ),
        ("message_id", "message_type", "acknowledged_message_id", "published_at"),
        command_consts={"message_type": "acknowledgement"},
        event_consts=({"message_type": "acknowledgement"},),
    ),
    "message.publish_progress": _d(
        (
            "new_message_id",
            "message_type",
            "sender_actor_id",
            "recipient_actor_ids",
            "thread_id",
            "attempt_id",
            "progress_evidence_ref",
        ),
        ("message_id", "message_type", "attempt_id", "progress_evidence_ref", "published_at"),
        command_consts={"message_type": "progress"},
        event_consts=({"message_type": "progress"},),
    ),
    "message.publish_input_request": _d(
        (
            "new_message_id",
            "message_type",
            "sender_actor_id",
            "recipient_actor_ids",
            "thread_id",
            "task_id",
            "input_requirement_id",
        ),
        ("message_id", "message_type", "task_id", "input_requirement_id", "published_at"),
        command_consts={"message_type": "input_request"},
        event_consts=({"message_type": "input_request"},),
    ),
    "message.publish_escalation": _d(
        (
            "new_message_id",
            "message_type",
            "sender_actor_id",
            "recipient_actor_ids",
            "thread_id",
            "blocker_id",
            "escalation_reason",
        ),
        ("message_id", "message_type", "blocker_id", "escalation_reason", "published_at"),
        command_consts={"message_type": "escalation"},
        event_consts=({"message_type": "escalation"},),
    ),
    "message.publish_report": _d(
        (
            "new_message_id",
            "message_type",
            "sender_actor_id",
            "recipient_actor_ids",
            "thread_id",
            "attempt_id",
            "report_artefact_id",
        ),
        ("message_id", "message_type", "attempt_id", "report_artefact_id", "published_at"),
        command_consts={"message_type": "report"},
        event_consts=({"message_type": "report"},),
    ),
    "message.publish_review_request": _d(
        (
            "new_message_id",
            "message_type",
            "sender_actor_id",
            "recipient_actor_ids",
            "thread_id",
            "review_id",
            "subject_artefact_id",
        ),
        ("message_id", "message_type", "review_id", "subject_artefact_id", "published_at"),
        command_consts={"message_type": "review_request"},
        event_consts=({"message_type": "review_request"},),
    ),
    "message.publish_review_response": _d(
        (
            "new_message_id",
            "message_type",
            "sender_actor_id",
            "recipient_actor_ids",
            "thread_id",
            "review_id",
            "verdict_id",
        ),
        ("message_id", "message_type", "review_id", "verdict_id", "published_at"),
        command_consts={"message_type": "review_response"},
        event_consts=({"message_type": "review_response"},),
    ),
    "message.publish_decision_request": _d(
        (
            "new_message_id",
            "message_type",
            "sender_actor_id",
            "recipient_actor_ids",
            "thread_id",
            "decision_id",
            "question",
        ),
        ("message_id", "message_type", "decision_id", "question", "published_at"),
        command_consts={"message_type": "decision_request"},
        event_consts=({"message_type": "decision_request"},),
    ),
    "message.publish_handoff": _d(
        (
            "new_message_id",
            "message_type",
            "sender_actor_id",
            "recipient_actor_ids",
            "thread_id",
            "task_id",
            "handoff_manifest_id",
        ),
        ("message_id", "message_type", "task_id", "handoff_manifest_id", "published_at"),
        command_consts={"message_type": "handoff"},
        event_consts=({"message_type": "handoff"},),
    ),
    "message.deliver": _d(
        ("message_id", "recipient_actor_id", "delivery_evidence_ref"),
        ("message_id", "recipient_actor_id", "delivered_at"),
    ),
    "message.acknowledge": _d(
        ("message_id", "acknowledging_actor_id", "acknowledgement_evidence_ref"),
        ("message_id", "acknowledging_actor_id", "acknowledged_at"),
    ),
    "message.delivery_failure": _d(
        ("message_id", "recipient_actor_id", "failure_reason"),
        ("message_id", "recipient_actor_id", "failure_reason", "failed_at"),
    ),
    "blocker.record": _d(
        ("new_blocker_id", "blocker_type", "affected_task_id", "resume_condition", "must_stop"),
        ("blocker_id", "blocker_type", "affected_task_id", "resume_condition", "must_stop", "recorded_at"),
    ),
    "blocker.resolve": _d(
        ("blocker_id", "resolution_evidence_ref", "resume_condition_satisfied_by"),
        ("blocker_id", "resolution_evidence_ref", "resolved_at"),
    ),
    "artefact.register": _d(
        ("new_artefact_id", "artefact_type", "task_id", "attempt_id", "content_sha256", "location_uri"),
        ("artefact_id", "artefact_type", "task_id", "attempt_id", "content_sha256", "registered_at"),
    ),
    "artefact.availability": _d(
        ("artefact_id", "available", "availability_evidence_ref"),
        ("artefact_id", "available", "availability_evidence_ref", "observed_at"),
    ),
    "artefact.regenerability": _d(
        ("artefact_id", "regenerable", "regeneration_evidence_ref"),
        ("artefact_id", "regenerable", "regeneration_evidence_ref", "observed_at"),
    ),
    "artefact.integrity": _d(
        ("artefact_id", "integrity_valid", "observed_sha256"),
        ("artefact_id", "integrity_valid", "observed_sha256", "observed_at"),
    ),
    "artefact.structural_validation": _d(
        ("artefact_id", "validation_record_id", "structural_verdict"),
        ("artefact_id", "validation_record_id", "structural_verdict", "recorded_at"),
    ),
    "artefact.scientific_review": _d(
        ("artefact_id", "review_id", "scientific_verdict"),
        ("artefact_id", "review_id", "scientific_verdict", "recorded_at"),
    ),
    "artefact.use_authority": _d(
        ("artefact_id", "use_authority", "allowed_consumer_ids"),
        ("artefact_id", "use_authority", "allowed_consumer_ids", "set_at"),
    ),
    "artefact.supersede": _d(
        ("artefact_id", "superseding_artefact_id", "supersession_reason"),
        ("artefact_id", "superseding_artefact_id", "superseded_at"),
    ),
    "review.request": _d(
        ("new_review_id", "review_type", "subject_id", "subject_sha256", "required_evidence_ids", "independence_grade"),
        ("review_id", "review_type", "subject_id", "subject_sha256", "requested_at"),
    ),
    "review.assign": _d(
        ("review_id", "reviewer_actor_id", "reviewer_profile_id"),
        ("review_id", "reviewer_actor_id", "reviewer_profile_id", "assigned_at"),
    ),
    "review.start": _d(
        ("review_id", "reviewer_actor_id", "context_manifest_id"),
        ("review_id", "reviewer_actor_id", "context_manifest_id", "started_at"),
    ),
    "review.record_verdict": _d(
        ("review_id", "verdict", "finding_ids", "evidence_ref"),
        ("review_id", "verdict", "finding_ids", "evidence_ref", "recorded_at"),
    ),
    "review.request_changes": _d(
        ("review_id", "finding_ids", "change_request_ref"),
        ("review_id", "finding_ids", "change_request_ref", "requested_at"),
    ),
    "review.satisfy": _d(
        ("review_id", "verdict_id", "satisfaction_evidence_ref"), ("review_id", "verdict_id", "satisfied_at")
    ),
    "review.satisfy_after_changes": _d(
        ("review_id", "verdict_id", "satisfaction_evidence_ref"), ("review_id", "verdict_id", "satisfied_at")
    ),
    "review.withdraw": _d(
        ("review_id", "withdrawal_reason", "withdrawal_evidence_ref"),
        ("review_id", "withdrawal_reason", "withdrawn_at"),
    ),
    "review.supersede": _d(
        ("review_id", "superseding_review_id", "supersession_reason"),
        ("review_id", "superseding_review_id", "superseded_at"),
    ),
    "decision.propose": _d(
        ("new_decision_id", "question", "options_ref", "recommendation", "governing_evidence_ref"),
        ("decision_id", "question", "options_ref", "recommendation", "proposed_at"),
    ),
    "decision.request_review": _d(
        ("decision_id", "review_id", "review_questions_ref"), ("decision_id", "review_id", "requested_at")
    ),
    "decision.resolve": _d(
        ("decision_id", "selected_option", "evidence_ref", "effective_scope"),
        ("decision_id", "selected_option", "evidence_ref", "effective_scope", "resolved_at"),
    ),
    "decision.reject": _d(
        ("decision_id", "rejection_reason", "evidence_ref"), ("decision_id", "rejection_reason", "rejected_at")
    ),
    "decision.expire": _d(
        ("decision_id", "observed_at", "expiry_reason"), ("decision_id", "observed_at", "expiry_reason")
    ),
    "decision.supersede": _d(
        ("decision_id", "superseding_decision_id", "supersession_reason"),
        ("decision_id", "superseding_decision_id", "superseded_at"),
    ),
    "rule.evaluate": _d(
        ("new_rule_evaluation_id", "rule_version", "referent_id", "input_ids", "calculation_ref"),
        ("rule_evaluation_id", "rule_version", "referent_id", "input_ids", "output", "evidence_hash"),
    ),
    "decision.amend": _d(
        ("decision_id", "amended_subject_version", "changed_fields_ref", "amendment_reason"),
        ("decision_id", "amended_subject_version", "changed_fields_ref", "amendment_reason", "proposed_at"),
    ),
    "correction.record": _d(
        (
            "erroneous_record_id",
            "incorrect_assertion",
            "corrected_evidence_ref",
            "affected_projection_ids",
            "affected_consumer_ids",
        ),
        (
            "erroneous_record_id",
            "incorrect_assertion",
            "corrected_evidence_ref",
            "affected_projection_ids",
            "recorded_at",
        ),
    ),
    "operator.request_resource_grant": _d(
        (
            "resource_id",
            "task_id",
            "dispatch_id",
            "attempt_id",
            "operational_profile_id",
            "root_binding_ids",
            "resource_estimate_ref",
        ),
        ("resource_request_id", "task_id", "dispatch_id", "attempt_id", "operational_profile_id", "requested_at"),
    ),
    "operator.claim_execution_lease": _d(
        (
            "new_lease_id",
            "resource_grant_id",
            "task_id",
            "task_revision",
            "dispatch_id",
            "attempt_id",
            "process_identity_id",
            "expires_at",
        ),
        (
            "lease_id",
            "resource_grant_id",
            "task_id",
            "task_revision",
            "dispatch_id",
            "attempt_id",
            "granted_at",
            "expires_at",
        ),
    ),
    "operator.record_heartbeat": _d(
        ("lease_id", "heartbeat_sequence", "process_identity_id", "progress_evidence_ref", "checkpoint_id"),
        ("lease_id", "heartbeat_sequence", "process_identity_id", "progress_evidence_ref", "recorded_at"),
    ),
    "operator.request_pause": _d(
        ("attempt_id", "lease_id", "checkpoint_id", "pause_reason"),
        ("attempt_id", "lease_id", "checkpoint_id", "requested_at"),
    ),
    "operator.confirm_pause": _d(
        ("attempt_id", "lease_id", "checkpoint_id", "process_identity_id"),
        ("attempt_id", "lease_id", "checkpoint_id", "confirmed_at"),
    ),
    "operator.request_stop": _d(
        ("attempt_id", "lease_id", "process_identity_id", "stop_reason"),
        ("attempt_id", "lease_id", "process_identity_id", "requested_at"),
    ),
    "operator.confirm_stop": _d(
        ("attempt_id", "lease_id", "stop_record_id", "writers_closed"),
        ("attempt_id", "lease_id", "stop_record_id", "writers_closed", "confirmed_at"),
    ),
    "operator.request_resume": _d(
        ("attempt_id", "checkpoint_id", "compatibility_verdict", "new_execution_epoch"),
        ("attempt_id", "checkpoint_id", "compatibility_verdict", "new_execution_epoch", "requested_at"),
    ),
    "operator.release_resources": _d(
        ("resource_id", "resource_grant_id", "release_evidence_ref"),
        ("resource_id", "resource_grant_id", "released_at"),
    ),
    "operator.quarantine_orphan": _d(
        ("attempt_id", "recovery_evidence_id", "process_ids", "artefact_ids"),
        ("attempt_id", "recovery_evidence_id", "process_ids", "artefact_ids", "quarantined_at"),
    ),
    "operator.adopt_late_artefact": _d(
        ("artefact_id", "attempt_id", "review_id", "recovery_evidence_id"),
        ("artefact_id", "attempt_id", "review_id", "recovery_evidence_id", "adopted_at"),
    ),
    "operator.create_backup": _d(
        ("project_id", "control_store_id", "tail_hash", "destination_class"),
        ("backup_receipt_id", "project_id", "control_store_id", "tail_hash", "created_at"),
    ),
    "operator.verify_restore": _d(
        ("project_id", "backup_receipt_id", "restore_evidence_ref", "restore_valid"),
        ("project_id", "backup_receipt_id", "restore_evidence_ref", "restore_valid", "verified_at"),
    ),
}


def _resolver_for(key: str) -> Callable[[SourceRow], OperationSpec]:
    data = _OPERATION_DATA[key]

    def resolve(row: SourceRow) -> OperationSpec:
        if row.key != key:
            raise RuntimeError(f"WP6.1 resolver {key} received {row.key}")
        command_names, event_names, command_consts, event_consts = data
        if len(event_names) != len(row.events) or len(event_consts) != len(row.events):
            raise RuntimeError(f"WP6.1 event fact cardinality mismatch for {key}")
        return OperationSpec(
            row_key=key,
            command_payload=_object(row, command_names, command_consts),
            event_payloads=tuple(
                (event_type, _object(row, names, consts))
                for (event_type, _), names, consts in zip(row.events, event_names, event_consts, strict=True)
            ),
        )

    return resolve


ROW_RESOLVERS: dict[str, Callable[[SourceRow], OperationSpec]] = {key: _resolver_for(key) for key in _OPERATION_DATA}


def resolve_operation_specs(repo_root: Path, rows: Iterable[SourceRow]) -> dict[str, OperationSpec]:
    """Resolve the exact 104-row semantic model after verifying all sources."""
    approved_source_bytes(repo_root, W2_SOURCE)
    approved_source_bytes(repo_root, W8_SOURCE)
    row_list = list(rows)
    row_keys = [row.key for row in row_list]
    if len(row_keys) != 104 or len(set(row_keys)) != 104:
        raise RuntimeError("WP6.1 operation source is not exactly 104 unique rows")
    if set(row_keys) != set(ROW_RESOLVERS):
        missing = sorted(set(row_keys) - set(ROW_RESOLVERS))
        extra = sorted(set(ROW_RESOLVERS) - set(row_keys))
        raise RuntimeError(f"WP6.1 exact resolver mismatch; missing={missing}, extra={extra}")
    resolved = {row.key: ROW_RESOLVERS[row.key](row) for row in row_list}
    if any(not spec.command_payload.fields or not spec.event_payloads for spec in resolved.values()):
        raise RuntimeError("WP6.1 operation model contains an empty payload")
    return resolved


def command_root_spec() -> ObjectSpec:
    citation = (SourceCitation(W2_SOURCE, "§8.1"),)
    fields = []
    for name in COMMAND_ROOT_NAMES:
        if name == "payload":
            continue
        if name in {"expected_stream_version"}:
            fields.append(FieldSpec(name, "integer", citation, minimum=0))
        elif name == "evidence_refs":
            fields.append(FieldSpec(name, "array", citation, item_type="string"))
        elif name in {"on_behalf_of_actor_id", "causation_id"}:
            fields.append(FieldSpec(name, "string", citation, nullable=True))
        elif name == "submitted_at":
            fields.append(FieldSpec(name, "string", citation, format="date-time"))
        else:
            fields.append(FieldSpec(name, "string", citation))
    return ObjectSpec(tuple(fields), citation)


def event_root_spec() -> ObjectSpec:
    w2 = SourceCitation(W2_SOURCE, "§9.2")
    annex = SourceCitation(ANNEX_SOURCE, "§1.1")
    fields = []
    for name in EVENT_ROOT_NAMES:
        if name == "payload":
            continue
        citations = (annex,) if name.startswith("command_schema_") else (w2,)
        if name in {"stream_version", "global_position", "transaction_index", "transaction_count"}:
            fields.append(FieldSpec(name, "integer", citations, minimum=1))
        elif name == "occurred_at":
            fields.append(FieldSpec(name, "string", citations, nullable=True, format="date-time"))
        elif name == "causation_id":
            fields.append(FieldSpec(name, "string", citations, nullable=True))
        elif name in {"recorded_at"}:
            fields.append(FieldSpec(name, "string", citations, format="date-time"))
        else:
            fields.append(FieldSpec(name, "string", citations))
    return ObjectSpec(tuple(fields), (w2, annex))
