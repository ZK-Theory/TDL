"""Normalized issue boundary and privacy-preserving receipt extraction."""

import json
from dataclasses import dataclass
from typing import Any

from research_system.adapters.base import (
    ProviderCommand,
    ProviderReceipt,
    TransportResult,
)
from research_system.adapters.fake import FakeTransport
from research_system.canonical import sha256_hex
from research_system.context.template import validate_wrapper_accounting
from research_system.errors import ArsError


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


def _payload(result: TransportResult) -> dict:
    if not result.stdout:
        return {}
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def normalize_receipt(command: ProviderCommand, result: TransportResult) -> ProviderReceipt:
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
        failure_code=(None if complete else "provider_unavailable" if outage else "provider_completion_unproven"),
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

    def issue(
        self,
        command: ProviderCommand,
        managed_content: str,
        *,
        issued_dispatch: Any | None = None,
        capability: Any | None = None,
    ) -> ProviderReceipt:
        if command.operation == "deliver_context" or issued_dispatch is not None or capability is not None:
            self._verify_context_delivery_seal(
                command,
                issued_dispatch=issued_dispatch,
                capability=capability,
            )
        return self._issue_command(command, managed_content)

    def issue_adapter_scientific_probe(
        self,
        command: ProviderCommand,
        managed_content: str,
    ) -> ProviderReceipt:
        """Run an exact fake-transport adapter probe with no lifecycle inputs."""
        if not isinstance(self._transport, FakeTransport):
            raise ArsError("adapter scientific probes require FakeTransport")
        return self._issue_command(command, managed_content)

    def _issue_command(
        self,
        command: ProviderCommand,
        managed_content: str,
    ) -> ProviderReceipt:
        if not command.authorized:
            raise ArsError("unauthorized_adapter_command")
        enforce_provider_operation_policy(command, self._operation_policy)
        validate_wrapper_accounting(command.wrapper_accounting)
        result = self._transport.invoke(list(self._argv), managed_content, command.timeout_s)
        return normalize_receipt(command, result)

    @staticmethod
    def _verify_context_delivery_seal(
        command: ProviderCommand,
        *,
        issued_dispatch: Any | None,
        capability: Any | None,
    ) -> None:
        from research_system.context.service import LifecycleIssuedDispatch

        if type(issued_dispatch) is not LifecycleIssuedDispatch or capability is None:
            raise ArsError("issued context lifecycle dispatch is missing or forged")
        issued_dispatch.verify_capability(capability)
        content = issued_dispatch.template.content
        expected = {
            "revision": content["command_revision"],
            "revision_hash": content["command_revision_hash"],
            "provider": content["provider"],
            "model": content["model"],
            "profile_id": content["profile_id"],
            "adapter_revision": content["adapter_revision"],
            "policy_hash": content["policy_hash"],
            "context_hash": content["packet_sha256"],
            "rendered_payload_hash": content["rendered_payload_hash"],
            "idempotency_key": content["idempotency_key"],
            "operation": content["operation"],
            "timeout_s": content["timeout_s"],
            "wrapper_accounting": content["wrapper_accounting"],
        }
        observed = {name: getattr(command, name) for name in expected}
        if observed != expected:
            raise ArsError("provider command changed the prevalidated context template")
