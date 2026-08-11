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

    def load_provider_receipt(
        self,
        lease: Mapping[str, Any],
        provider_command: ProviderCommand,
    ) -> tuple[ProviderReceipt, Receipt] | None:
        """Load a receipt only for the exact active lease and provider command.

        Implementations must validate that ``lease`` is current and authorized for
        the issued attempt, then match every field of ``provider_command`` against
        the stored command before returning its provider and terminal receipts.

        Args:
            lease: Revalidated execution lease governing provider issue.
            provider_command: Exact command whose durable result may be replayed.

        Returns:
            The command-bound provider and terminal receipts, or ``None`` when no
            receipt has been recorded for that exact lease and command.

        Raises:
            ArsError: If a stored receipt exists but its lease or command binding
                is not exact.
        """
        ...

    def record_provider_receipt_command(
        self, lease: Mapping[str, Any], provider_receipt: ProviderReceipt
    ) -> dict[str, Any]: ...


class CommandServicePort(Protocol):
    def submit(self, command: dict[str, Any]) -> Receipt: ...


def _validate_recovered_provider_receipt(
    provider_command: ProviderCommand,
    provider_receipt: ProviderReceipt,
) -> None:
    command_binding_matches = all(
        (
            provider_receipt.provider_command_id == provider_command.provider_command_id,
            provider_receipt.command_revision == provider_command.revision,
            provider_receipt.command_revision_hash == provider_command.revision_hash,
            provider_receipt.provider == provider_command.provider,
            provider_receipt.model == provider_command.model,
            provider_receipt.profile_id == provider_command.profile_id,
            provider_receipt.adapter_revision == provider_command.adapter_revision,
            provider_receipt.policy_hash == provider_command.policy_hash,
            provider_receipt.context_hash == provider_command.context_hash,
            not provider_receipt.complete or provider_receipt.delivered_context_hash == provider_command.context_hash,
        )
    )
    if not command_binding_matches:
        raise ArsError("recovered provider receipt does not match issued command")


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
    recovered = operations.load_provider_receipt(lease, provider_command)
    if recovered is None:
        provider_receipt = adapter.issue(
            provider_command,
            issued_receipt,
            issued,
            capability,
        )
        terminal_receipt = submit_ars_command(
            command_service, operations.record_provider_receipt_command(lease, provider_receipt)
        ).receipt
    else:
        provider_receipt, terminal_receipt = recovered
        _validate_recovered_provider_receipt(provider_command, provider_receipt)
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
