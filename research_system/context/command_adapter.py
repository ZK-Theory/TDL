"""CommandService adapter for the W3 context lifecycle."""

from __future__ import annotations

import hashlib
import uuid
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from typing import Any, Callable, Iterable, Mapping

from research_system.command.service import CommandService
from research_system.store.lock import WriterLock


_SCHEMA_IDS = {
    "RequestContextPacket": "ars://core/command/RequestContextPacket",
    "BeginContextCompilation": "ars://core/command/BeginContextCompilation",
    "CompleteContextCompilation": "ars://core/command/CompleteContextCompilation",
    "ValidateContextPacket": "ars://core/command/ValidateContextPacket",
    "IssueContextPacket": "ars://core/command/IssueContextPacket",
    "RecordContextDelivery": "ars://core/command/RecordContextDelivery",
    "FailContextPacket": "ars://core/command/FailContextPacket",
    "ExpireContextPacket": "ars://core/command/ExpireContextPacket",
    "SupersedeContextPacket": "ars://core/command/SupersedeContextPacket",
}


def _stable_command_id(idempotency_key: str) -> str:
    value = int.from_bytes(hashlib.sha256(idempotency_key.encode("utf-8")).digest()[:16], "big")
    value = (value & ~(0xF << 76)) | (0x7 << 76)
    value = (value & ~(0b11 << 62)) | (0b10 << 62)
    return f"cmd_{uuid.UUID(int=value)}"


class CommandServiceContextWriter:
    """Submit every W3 transition through the canonical command service."""

    def __init__(
        self,
        service: CommandService,
        *,
        actor_id: str,
        authority_grant_id: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.service = service
        self.actor_id = actor_id
        self.authority_grant_id = authority_grant_id
        self.clock = clock or (lambda: datetime.now(UTC))

    def stream_version(self, context_id: str) -> int:
        return int(self.service.ledger.snapshot().stream_versions.get(context_id, 0))

    def lifecycle_lock(self, context_id: str) -> AbstractContextManager[None]:
        path = self.service.control_root / ".research-system" / "locks" / f"context-lifecycle-{context_id}.json"
        return WriterLock(
            path,
            {
                "lock_kind": "context_lifecycle",
                "context_id": context_id,
                "actor_id": self.actor_id,
            },
        )

    def iter_events(self, context_id: str) -> Iterable[Mapping[str, Any]]:
        return (event for event in self.service.ledger.iter_events() if event.get("stream_id") == context_id)

    def submit_context(
        self,
        *,
        command_type: str,
        context_id: str,
        expected_stream_version: int,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> Any:
        try:
            schema_id = _SCHEMA_IDS[command_type]
        except KeyError as exc:
            raise ValueError(f"unsupported context command: {command_type}") from exc
        submitted_at = self.clock().astimezone(UTC).isoformat().replace("+00:00", "Z")
        envelope = {
            "command_id": _stable_command_id(idempotency_key),
            "command_type": command_type,
            "schema_id": schema_id,
            "schema_version": "1.0.0",
            "submitted_at": submitted_at,
            "actor_id": self.actor_id,
            "on_behalf_of_actor_id": None,
            "authority_grant_id": self.authority_grant_id,
            "target_stream_id": context_id,
            "expected_stream_version": expected_stream_version,
            "idempotency_key": idempotency_key,
            "correlation_id": f"context:{context_id}",
            "causation_id": None,
            "reason": f"W3 context lifecycle transition {command_type}",
            "evidence_refs": [],
            "payload": dict(payload),
            "project_id": self.service.ledger.project_id,
            "context_lifecycle_submission_key": self.service._context_lifecycle_submission_key,
        }
        return self.service.submit(envelope)
