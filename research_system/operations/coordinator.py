"""Selected-route revalidation and command-mediated provider issue."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from research_system.adapters.base import ProviderCommand, ProviderReceipt
from research_system.command.models import Receipt
from research_system.context.service import (
    ContextLifecycleCapability,
    LifecycleIssuedDispatch,
)
from research_system.errors import ArsError


class AdapterIssuePort(Protocol):
    def build_command_from_template(
        self,
        issued: LifecycleIssuedDispatch,
        grant: Mapping[str, Any],
        lease: Mapping[str, Any],
        capability: ContextLifecycleCapability,
    ) -> ProviderCommand: ...

    def record_issue_command(self, provider_command: ProviderCommand) -> dict[str, Any]: ...

    def issue(
        self,
        provider_command: ProviderCommand,
        issued_receipt: Receipt,
        issued: LifecycleIssuedDispatch,
        capability: ContextLifecycleCapability,
    ) -> ProviderReceipt: ...


class OperationsIssuePort(Protocol):
    def build_request(self, prepared: LifecycleIssuedDispatch, revalidated: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def request_grant_command(self, request: Mapping[str, Any]) -> dict[str, Any]: ...

    def load_grant(self, grant_receipt: Receipt) -> Mapping[str, Any]: ...

    def claim_lease_command(self, grant: Mapping[str, Any], attempt_id: str) -> dict[str, Any]: ...

    def load_lease(self, lease_receipt: Receipt) -> Mapping[str, Any]: ...

    def record_provider_receipt_command(
        self, lease: Mapping[str, Any], provider_receipt: ProviderReceipt
    ) -> dict[str, Any]: ...


class CommandServicePort(Protocol):
    def submit(self, command: dict[str, Any]) -> Receipt: ...


@dataclass(frozen=True, slots=True)
class CommandSubmission:
    """Observed result of the sole command-mediated canonical state path."""

    receipt: Receipt
    state_change_path: str
    direct_writer_used: bool


def submit_ars_command(
    command_service: CommandServicePort,
    command: dict[str, Any],
) -> CommandSubmission:
    """Submit one state change through CommandService and expose its route."""
    return CommandSubmission(
        receipt=command_service.submit(command),
        state_change_path="submit_ars_command",
        direct_writer_used=False,
    )


def _issue_bound_template(
    issued: LifecycleIssuedDispatch,
    capability: ContextLifecycleCapability,
    adapter: Any,
    operations: OperationsIssuePort,
    command_service: CommandServicePort,
) -> tuple[ProviderCommand, ProviderReceipt, Receipt]:
    request = operations.build_request(issued, {"template_sha256": issued.template.sha256})
    grant_receipt = submit_ars_command(command_service, operations.request_grant_command(request)).receipt
    grant = operations.load_grant(grant_receipt)
    lease_receipt = submit_ars_command(
        command_service, operations.claim_lease_command(grant, issued.attempt_id)
    ).receipt
    lease = operations.load_lease(lease_receipt)
    provider_command = adapter.build_command_from_template(
        issued,
        grant,
        lease,
        capability,
    )
    issued_receipt = submit_ars_command(command_service, adapter.record_issue_command(provider_command)).receipt
    provider_receipt = adapter.issue(
        provider_command,
        issued_receipt,
        issued,
        capability,
    )
    terminal_receipt = submit_ars_command(
        command_service, operations.record_provider_receipt_command(lease, provider_receipt)
    ).receipt
    return provider_command, provider_receipt, terminal_receipt


def issue_lifecycle_dispatch(
    dispatch: LifecycleIssuedDispatch,
    capability: ContextLifecycleCapability,
    adapter: AdapterIssuePort,
    operations: OperationsIssuePort,
    command_service: CommandServicePort,
) -> tuple[ProviderCommand, ProviderReceipt, Receipt]:
    """Issue only a service-sealed dispatch carrying its exact opaque capability."""
    if type(dispatch) is not LifecycleIssuedDispatch:
        raise ArsError("issued lifecycle dispatch is missing or forged")
    dispatch.verify_capability(capability)
    return _issue_bound_template(dispatch, capability, adapter, operations, command_service)
