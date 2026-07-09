"""Provider-neutral transport and normalized command contracts."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TransportResult:
    status: str
    stdout: str
    stderr: str
    provider_request_id: str | None
    exit_code: int | None


class Transport(Protocol):
    def invoke(
        self, argv: list[str], stdin: str, timeout_s: float
    ) -> TransportResult: ...


@dataclass(frozen=True)
class ProviderCommand:
    provider_command_id: str
    revision: int
    revision_hash: str
    provider: str
    model: str
    profile_id: str
    adapter_revision: str
    policy_hash: str
    context_hash: str
    rendered_payload_hash: str
    idempotency_key: str
    operation: str
    timeout_s: float
    wrapper_accounting: dict
    authorized: bool


@dataclass(frozen=True)
class ProviderReceipt:
    provider_command_id: str
    command_revision: int
    command_revision_hash: str
    provider: str
    model: str
    profile_id: str
    adapter_revision: str
    policy_hash: str
    context_hash: str
    provider_request_id: str | None
    response_id: str | None
    status: str
    complete: bool
    delivered_context_hash: str | None
    output_refs: tuple[str, ...]
    output_hash: str | None
    exit_code: int | None
    failure_code: str | None
    redaction: str = "raw_transport_content_discarded"
