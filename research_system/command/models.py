from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex


@dataclass(frozen=True)
class Command:
    envelope: dict[str, Any]

    @property
    def command_id(self) -> str:
        return str(self.envelope['command_id'])

    @property
    def idempotency_key(self) -> str:
        return str(self.envelope['idempotency_key'])

    @property
    def actor_id(self) -> str:
        return str(self.envelope['actor_id'])

    @property
    def target_stream_id(self) -> str:
        return str(self.envelope['target_stream_id'])

    @property
    def expected_stream_version(self) -> int:
        return int(self.envelope['expected_stream_version'])

    @property
    def payload_hash(self) -> str:
        return sha256_hex(canonical_bytes(self.envelope['payload']))


@dataclass(frozen=True)
class Receipt:
    status: str
    command_id: str
    payload_hash: str
    event_batch_id: str | None
    observed_stream_version: int
    reason_code: str | None = None
