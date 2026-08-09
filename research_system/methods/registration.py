"""Durable candidate registration for owner-operated methods documents."""

from __future__ import annotations

import os
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConflictError
from research_system.ids import new_id
from research_system.store.durability import fsync_directory


class CommandSubmitter(Protocol):
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


class CandidateDocumentStore:
    """Write exact canonical bytes once beneath the configured control root."""

    def __init__(
        self,
        control_root: Path,
        *,
        root_id: str = "control",
        relative_directory: Path = Path("methods/documents"),
    ) -> None:
        self.control_root = control_root.resolve(strict=True)
        self.root_id = root_id
        if relative_directory.is_absolute() or ".." in relative_directory.parts:
            raise ValueError("candidate document directory must be control-relative")
        self.relative_directory = relative_directory

    def write(self, artefact_id: str, raw_bytes: bytes) -> str:
        relative = self.relative_directory / f"{artefact_id}.json"
        target = self.control_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if target.read_bytes() != raw_bytes:
                raise ConflictError("methods document identity already binds different bytes")
            return relative.as_posix()
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        fsync_directory(target.parent)
        return relative.as_posix()


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
    relative_path = document_store.write(registration.artefact_id, raw)
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
    command = {
        "command_id": new_id("command"),
        "command_type": "RegisterArtefact",
        "schema_id": "ars://core/command/RegisterArtefact",
        "schema_version": "1.0.0",
        "submitted_at": registration.submitted_at,
        "actor_id": registration.actor_id,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": registration.authority_grant_id,
        "target_stream_id": registration.artefact_id,
        "expected_stream_version": 0,
        "idempotency_key": f"methods-register:{registration.artefact_id}:{digest}",
        "correlation_id": registration.correlation_id,
        "causation_id": None,
        "reason": registration.reason,
        "evidence_refs": [],
        "payload": {"new_artefact_id": registration.artefact_id, "manifest": manifest},
        "project_id": registration.project_id,
    }
    receipt = command_service.submit(command)
    if getattr(receipt, "status", None) != "accepted":
        reason = getattr(receipt, "reason_code", None) or getattr(receipt, "status", "unknown")
        explanation = getattr(receipt, "explanation", None)
        detail = f": {explanation}" if explanation else ""
        raise ArsError(f"candidate artefact registration was not accepted ({reason}){detail}")
    return RegisteredCandidate(registration.artefact_id, digest, raw, relative_path, receipt)


__all__ = [
    "CandidateDocumentStore",
    "CandidateRegistration",
    "CommandSubmitter",
    "RegisteredCandidate",
    "register_candidate_document",
]
