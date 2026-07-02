"""Selected-route revalidation and command-mediated provider issue."""

from typing import Protocol

from research_system.errors import ArsError


class AdapterIssuePort(Protocol):
    def load_evidence(self, evidence_id: str, content_hash: str): ...

    def revalidate(self, route, context, provider_evidence): ...

    def build_command(self, prepared, grant, lease, revalidated): ...

    def record_issue_command(self, provider_command): ...

    def issue(self, provider_command, issued_receipt): ...


class OperationsIssuePort(Protocol):
    def build_request(self, prepared, revalidated): ...

    def request_grant_command(self, request): ...

    def load_grant(self, grant_receipt): ...

    def claim_lease_command(self, grant, attempt_id: str): ...

    def load_lease(self, lease_receipt): ...

    def record_provider_receipt_command(self, lease, provider_receipt): ...


class CommandServicePort(Protocol):
    def submit(self, command): ...


def issue_prepared_dispatch(
    prepared,
    adapter: AdapterIssuePort,
    operations: OperationsIssuePort,
    command_service: CommandServicePort,
):
    """Issue only through revalidation and typed WP1 command transitions."""
    if prepared.state != "unissued":
        raise ArsError("prepared dispatch is not unissued")
    provider_evidence = adapter.load_evidence(
        prepared.provider_evidence_id, prepared.provider_evidence_hash
    )
    revalidated = adapter.revalidate(
        prepared.route, prepared.context, provider_evidence
    )
    request = operations.build_request(prepared, revalidated)
    grant_receipt = command_service.submit(
        operations.request_grant_command(request)
    )
    grant = operations.load_grant(grant_receipt)
    lease_receipt = command_service.submit(
        operations.claim_lease_command(grant, prepared.attempt_id)
    )
    lease = operations.load_lease(lease_receipt)
    provider_command = adapter.build_command(prepared, grant, lease, revalidated)
    issued_receipt = command_service.submit(
        adapter.record_issue_command(provider_command)
    )
    provider_receipt = adapter.issue(provider_command, issued_receipt)
    terminal_receipt = command_service.submit(
        operations.record_provider_receipt_command(lease, provider_receipt)
    )
    return provider_command, provider_receipt, terminal_receipt
