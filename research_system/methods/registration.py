"""Durable candidate registration for owner-operated methods documents."""

from __future__ import annotations

import hashlib
import uuid
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command
from research_system.errors import ArsError, IntegrityError
from research_system.store.registered_content import (
    CandidateDocumentStore,
    committed_registration_event,
    recover_registered_content,
)


class CommandSubmitter(Protocol):
    ledger: Any

    def submit(self, envelope: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class CandidateRegistration:
    """Caller-authorized production metadata for one immutable document."""

    artefact_id: str
    project_id: str
    actor_id: str
    authority_grant_id: str
    submitted_at: str
    correlation_id: str
    reason: str
    manifest: dict[str, Any]


@dataclass(frozen=True)
class RegisteredCandidate:
    artefact_id: str
    content_sha256: str
    raw_bytes: bytes
    relative_path: str
    receipt: Any


def _stable_command_id(idempotency_key: str) -> str:
    """Derive one canonical UUIDv7 command identity for an exact registration."""

    value = int.from_bytes(hashlib.sha256(idempotency_key.encode("utf-8")).digest()[:16], "big")
    value = (value & ~(0xF << 76)) | (0x7 << 76)
    value = (value & ~(0b11 << 62)) | (0b10 << 62)
    return f"cmd_{uuid.UUID(int=value)}"


def register_candidate_document(
    *,
    value: dict[str, Any],
    registration: CandidateRegistration,
    document_store: CandidateDocumentStore,
    command_service: CommandSubmitter,
) -> RegisteredCandidate:
    """Persist and register exact bytes, always forcing initial candidate authority."""

    raw = canonical_bytes(value)
    digest = sha256_hex(raw)
    relative_path = document_store.relative_path(registration.artefact_id)
    manifest = deepcopy(registration.manifest)
    if manifest.get("artefact_id") != registration.artefact_id:
        raise ArsError("registration manifest does not bind the document artefact")
    manifest.update(
        {
            "root_id": document_store.root_id,
            "relative_path": relative_path,
            "size_bytes": len(raw),
            "media_type": "application/json",
            "content_sha256": digest,
        }
    )
    authority = manifest.get("authority")
    if not isinstance(authority, dict):
        raise ArsError("registration manifest authority is missing")
    authority["use_authority"] = "candidate"
    idempotency_key = f"methods-register:{registration.artefact_id}:{digest}"
    command = {
        "command_id": _stable_command_id(idempotency_key),
        "command_type": "RegisterArtefact",
        "schema_id": "ars://core/command/RegisterArtefact",
        "schema_version": "1.0.0",
        "submitted_at": registration.submitted_at,
        "actor_id": registration.actor_id,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": registration.authority_grant_id,
        "target_stream_id": registration.artefact_id,
        "expected_stream_version": 0,
        "idempotency_key": idempotency_key,
        "correlation_id": registration.correlation_id,
        "causation_id": None,
        "reason": registration.reason,
        "evidence_refs": [],
        "payload": {"new_artefact_id": registration.artefact_id, "manifest": manifest},
        "project_id": registration.project_id,
    }
    marker = document_store.stage_recovery_marker(command, relative_path, raw)
    receipt = command_service.submit(command)
    if getattr(receipt, "status", None) not in {"accepted", "replayed"}:
        document_store.remove_recovery_marker(marker)
        reason = getattr(receipt, "reason_code", None) or getattr(receipt, "status", "unknown")
        explanation = getattr(receipt, "explanation", None)
        detail = f": {explanation}" if explanation else ""
        raise ArsError(f"candidate artefact registration was not accepted ({reason}){detail}")
    event_batch_id = getattr(receipt, "event_batch_id", None)
    if (
        getattr(receipt, "command_id", None) != command["command_id"]
        or getattr(receipt, "payload_hash", None) != Command(command).payload_hash
        or not isinstance(event_batch_id, str)
        or not event_batch_id
    ):
        raise IntegrityError("candidate artefact registration receipt does not bind the exact command")
    ledger = getattr(command_service, "ledger", None)
    snapshot_method = getattr(ledger, "snapshot", None)
    if not callable(snapshot_method):
        raise IntegrityError("candidate artefact registration requires a readable committed ledger")
    snapshot = snapshot_method()
    events = getattr(snapshot, "events", None)
    if not isinstance(events, tuple):
        raise IntegrityError("candidate artefact registration ledger snapshot is invalid")
    committed_registration_event(events, command, event_batch_id=event_batch_id)
    recover_registered_content(document_store, events)
    if document_store.read_relative(relative_path) != raw or document_store.marker_exists(marker):
        raise IntegrityError("candidate artefact registration did not seal exact content")
    return RegisteredCandidate(registration.artefact_id, digest, raw, relative_path, receipt)


__all__ = [
    "CandidateDocumentStore",
    "CandidateRegistration",
    "CommandSubmitter",
    "RegisteredCandidate",
    "recover_registered_content",
    "register_candidate_document",
]
