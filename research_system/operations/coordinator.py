"""Selected-route revalidation and command-mediated provider issue."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from research_system.adapters.base import ProviderCommand, ProviderReceipt
from research_system.command.models import Receipt
from research_system.errors import ArsError
from research_system.routing.engine import PreparedDispatch


class AdapterIssuePort(Protocol):
    def load_evidence(
        self, evidence_id: str, content_hash: str
    ) -> Mapping[str, Any]: ...

    def revalidate(
        self,
        route: object,
        context: object,
        provider_evidence: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...

    def build_command(
        self,
        prepared: PreparedDispatch,
        grant: Mapping[str, Any],
        lease: Mapping[str, Any],
        revalidated: Mapping[str, Any],
    ) -> ProviderCommand: ...

    def record_issue_command(
        self, provider_command: ProviderCommand
    ) -> dict[str, Any]: ...

    def issue(
        self, provider_command: ProviderCommand, issued_receipt: Receipt
    ) -> ProviderReceipt: ...


class OperationsIssuePort(Protocol):
    def build_request(
        self, prepared: PreparedDispatch, revalidated: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...

    def request_grant_command(
        self, request: Mapping[str, Any]
    ) -> dict[str, Any]: ...

    def load_grant(self, grant_receipt: Receipt) -> Mapping[str, Any]: ...

    def claim_lease_command(
        self, grant: Mapping[str, Any], attempt_id: str
    ) -> dict[str, Any]: ...

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


def issue_prepared_dispatch(
    prepared: PreparedDispatch,
    adapter: AdapterIssuePort,
    operations: OperationsIssuePort,
    command_service: CommandServicePort,
) -> tuple[ProviderCommand, ProviderReceipt, Receipt]:
    """Revalidate and issue a prepared dispatch through command transitions.

    Args:
        prepared: Immutable unissued dispatch prepared by the routing layer.
        adapter: Provider-neutral evidence, command, and issue port.
        operations: Resource-grant, lease, and terminal-record port.
        command_service: Typed WP1 command submission boundary.

    Returns:
        Provider command, normalized provider receipt, and terminal receipt.

    Raises:
        ArsError: If the prepared dispatch is no longer unissued.
    """
    if prepared.state != "unissued":
        raise ArsError("prepared dispatch is not unissued")
    provider_evidence = adapter.load_evidence(
        prepared.provider_evidence_id, prepared.provider_evidence_hash
    )
    revalidated = adapter.revalidate(
        prepared.route, prepared.context, provider_evidence
    )
    request = operations.build_request(prepared, revalidated)
    grant_receipt = submit_ars_command(command_service,
        operations.request_grant_command(request)
    ).receipt
    grant = operations.load_grant(grant_receipt)
    lease_receipt = submit_ars_command(command_service,
        operations.claim_lease_command(grant, prepared.attempt_id)
    ).receipt
    lease = operations.load_lease(lease_receipt)
    provider_command = adapter.build_command(prepared, grant, lease, revalidated)
    issued_receipt = submit_ars_command(command_service,
        adapter.record_issue_command(provider_command)
    ).receipt
    provider_receipt = adapter.issue(provider_command, issued_receipt)
    terminal_receipt = submit_ars_command(command_service,
        operations.record_provider_receipt_command(lease, provider_receipt)
    ).receipt
    return provider_command, provider_receipt, terminal_receipt
