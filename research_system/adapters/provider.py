"""Normalized issue boundary and privacy-preserving receipt extraction."""

import json
from dataclasses import dataclass

from research_system.adapters.base import (
    ProviderCommand,
    ProviderReceipt,
    TransportResult,
)
from research_system.adapters.fake import FakeTransport
from research_system.canonical import sha256_hex
from research_system.errors import ArsError


_ALLOWED_SEGMENT_BUCKETS = frozenset({"managed", "reserved"})
_DECLARED_PROVIDER_OPERATIONS = frozenset(
    {
        "cancel_provider_work",
        "deliver_context",
        "deliver_message",
        "evaluate_gate5_fixture",
        "invoke_declared_tool",
        "query_provider_status",
        "request_model_work",
        "request_review",
    }
)
_LIVE_PROVIDER_OPERATIONS = frozenset(
    {
        "cancel_provider_work",
        "query_provider_status",
        "request_model_work",
        "request_review",
    }
)


@dataclass(frozen=True, slots=True)
class ProviderOperationPolicy:
    """Declared adapter operations and reviewed live-provider enablement."""

    declared_operations: frozenset[str]
    live_provider_operations: frozenset[str]
    live_provider_enabled: bool


def default_provider_operation_policy(*, live_provider_enabled: bool = False) -> ProviderOperationPolicy:
    """Return the fake-safe default policy shared by both provider builders."""
    return ProviderOperationPolicy(
        _DECLARED_PROVIDER_OPERATIONS,
        _LIVE_PROVIDER_OPERATIONS,
        live_provider_enabled,
    )


def enforce_provider_operation_policy(
    command: ProviderCommand,
    policy: ProviderOperationPolicy,
) -> None:
    """Reject undeclared or default-live operations before transport issue."""
    if command.operation not in policy.declared_operations:
        raise ArsError("undeclared_adapter_operation")
    if command.operation in policy.live_provider_operations and not policy.live_provider_enabled:
        raise ArsError("live_provider_disabled")


def validate_wrapper_accounting(accounting: dict) -> None:
    required = {
        "method",
        "raw_capacity",
        "fixed_overhead",
        "managed_tokens",
        "reserved_variable_tokens",
        "segments",
    }
    if set(accounting) != required:
        raise ArsError("wrapper_accounting_incomplete")
    segments = accounting["segments"]
    if not isinstance(segments, dict) or not segments or any(
        bucket not in _ALLOWED_SEGMENT_BUCKETS for bucket in segments.values()
    ):
        raise ArsError("wrapper_accounting_incomplete")
    numeric = (
        accounting["raw_capacity"],
        accounting["fixed_overhead"],
        accounting["managed_tokens"],
        accounting["reserved_variable_tokens"],
    )
    if any(not isinstance(value, int) or value < 0 for value in numeric):
        raise ArsError("wrapper_accounting_incomplete")
    if sum(numeric[1:]) > numeric[0]:
        raise ArsError("wrapper_capacity_exceeded")


def _payload(result: TransportResult) -> dict:
    if not result.stdout:
        return {}
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def normalize_receipt(
    command: ProviderCommand, result: TransportResult
) -> ProviderReceipt:
    """Extract registered semantics and discard raw transport content."""
    validate_wrapper_accounting(command.wrapper_accounting)
    payload = _payload(result)
    identity_matches = all(
        (
            payload.get("provider") == command.provider,
            payload.get("model") == command.model,
            payload.get("profile_id") == command.profile_id,
            payload.get("adapter_revision") == command.adapter_revision,
            payload.get("command_revision") == command.revision,
            payload.get("command_revision_hash") == command.revision_hash,
            payload.get("delivered_context_hash") == command.context_hash,
        )
    )
    status_map = {
        "timed_out": "uncertain",
        "uncertain": "uncertain",
        "cancelled": "cancelled",
        "duplicate": "duplicate",
    }
    outage = result.status == "provider_unavailable"
    status = "incomplete" if outage else status_map.get(result.status, result.status)
    terminal_like = status in {"terminal", "duplicate"} and result.exit_code == 0
    complete = terminal_like and identity_matches
    if terminal_like and not identity_matches:
        status = "incomplete"
    if result.status == "terminal" and result.exit_code not in {0, None}:
        status = "blocked"
        complete = False
    output_hash = sha256_hex(result.stdout.encode("utf-8")) if payload else None
    return ProviderReceipt(
        provider_command_id=command.provider_command_id,
        command_revision=command.revision,
        command_revision_hash=command.revision_hash,
        provider=command.provider,
        model=command.model,
        profile_id=command.profile_id,
        adapter_revision=command.adapter_revision,
        policy_hash=command.policy_hash,
        context_hash=command.context_hash,
        provider_request_id=result.provider_request_id,
        response_id=payload.get("response_id"),
        status=status,
        complete=complete,
        delivered_context_hash=payload.get("delivered_context_hash"),
        output_refs=tuple(payload.get("output_refs", ())),
        output_hash=output_hash,
        exit_code=result.exit_code,
        failure_code=(
            None
            if complete
            else "provider_unavailable"
            if outage
            else "provider_completion_unproven"
        ),
    )


def receipt_retention_mode(receipt: ProviderReceipt) -> str:
    """Derive the retention classification solely from normalized receipt data."""
    if receipt.redaction == "raw_transport_content_discarded":
        return "bounded_redacted"
    return "raw_retained"


class ProviderAdapter:
    def __init__(
        self,
        argv: list[str],
        transport,
        *,
        operation_policy: ProviderOperationPolicy | None = None,
    ):
        if not argv or not all(isinstance(value, str) and value for value in argv):
            raise ArsError("invalid provider argument array")
        self._argv = list(argv)
        self._transport = transport
        self._operation_policy = operation_policy or default_provider_operation_policy()
        if self._operation_policy.live_provider_enabled and not isinstance(
            transport,
            FakeTransport,
        ):
            raise ArsError("live_provider_capability_not_implemented")

    def issue(self, command: ProviderCommand, managed_content: str) -> ProviderReceipt:
        if not command.authorized:
            raise ArsError("unauthorized_adapter_command")
        enforce_provider_operation_policy(command, self._operation_policy)
        validate_wrapper_accounting(command.wrapper_accounting)
        result = self._transport.invoke(
            list(self._argv), managed_content, command.timeout_s
        )
        return normalize_receipt(command, result)
