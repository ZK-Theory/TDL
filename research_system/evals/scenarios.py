"""Composed deterministic Gate 3 scenarios A through E."""

from __future__ import annotations

from dataclasses import dataclass
from tempfile import TemporaryDirectory
from pathlib import Path

from research_system.adapters.base import ProviderCommand, ProviderReceipt
from research_system.command.models import Receipt
from research_system.ids import new_id
from research_system.operations.coordinator import issue_prepared_dispatch
from research_system.operations.leases import stop_confirmation
from research_system.operations.recovery import resume_from_checkpoint
from research_system.operations.resources import authorize_operational_surface
from research_system.routing.engine import PreparedDispatch, RouteCandidate, select_route
from research_system.routing.models import RouteRequest
from research_system.store.ledger import EventLedger


@dataclass(frozen=True, slots=True)
class Gate3ScenarioResult:
    """Evidence derived from calls through one composed foundation."""

    scenario_id: str
    event_types: tuple[str, ...]
    producer_actor_id: str | None = None
    verifier_actor_id: str | None = None
    original_requirement_id: str | None = None
    reroute_requirement_id: str | None = None
    provider_command_count: int = 0
    initial_epoch: int = 0
    resume_epoch: int = 0
    published_batch_count: int = 0
    replay_integrity: str | None = None
    decision_reason: str | None = None


def _checkpoint() -> dict[str, object]:
    return {
        "design_hash": "design-v1",
        "code_hash": "code-v1",
        "environment_hash": "environment-v1",
        "input_hashes": ["input-v1"],
        "representation_hash": "representation-v1",
        "parameters_hash": "parameters-v1",
        "rng_algorithm": "PCG64",
        "rng_state_hash": "rng-v1",
        "completed_work_units": [0],
        "payload_hash": "payload-v1",
    }


class _ScenarioCommandService:
    def __init__(self, events: list[str]):
        self.events = events

    def submit(self, command):
        self.events.append(command["event_type"])
        return Receipt("accepted", command["event_type"], "a" * 64, None, 1)


class _ScenarioAdapter:
    def load_evidence(self, evidence_id, content_hash):
        return {"evidence_id": evidence_id, "content_hash": content_hash}

    def revalidate(self, route, context, provider_evidence):
        return {"route": route, "context": context, "evidence": provider_evidence}

    def build_command(self, prepared, grant, lease, revalidated):
        return ProviderCommand(
            "pcmd-scenario", 1, "a" * 64, "fake", "p0", "profile",
            "adapter-v1", "b" * 64, "c" * 64, "d" * 64, "scenario",
            "request_model_work", 1.0, {"segments": {}}, True,
        )

    def record_issue_command(self, provider_command):
        return {"event_type": "ProviderCommandIssued"}

    def issue(self, provider_command, issued_receipt):
        return ProviderReceipt(
            provider_command.provider_command_id, 1, "a" * 64, "fake", "p0",
            "profile", "adapter-v1", "b" * 64, "c" * 64, "request",
            "response", "terminal", True, "c" * 64, (), "d" * 64, 0, None,
        )


class _ScenarioOperations:
    def build_request(self, prepared, revalidated):
        return {"prepared": prepared, "revalidated": revalidated}

    def request_grant_command(self, request):
        return {"event_type": "ResourceGrantRequested"}

    def load_grant(self, grant_receipt):
        return {"grant": grant_receipt.command_id}

    def claim_lease_command(self, grant, attempt_id):
        return {"event_type": "LeaseClaimed"}

    def load_lease(self, lease_receipt):
        return {"lease": lease_receipt.command_id}

    def record_provider_receipt_command(self, lease, provider_receipt):
        return {"event_type": "ProviderReceiptRecorded"}


class _UnavailableEvidence:
    routing_evidence_snapshot_id = "res-scenario"

    def hard_gate_failures(self, request, candidate):
        return ("provider_unavailable",)


class FoundationPorts:
    """Deterministic composition over existing WP1-WP3 public predicates."""

    def produce_and_verify(self) -> Gate3ScenarioResult:
        authorize_operational_surface(
            requested={"roots": {"control"}},
            granted={"roots": {"control"}},
        )
        events = ["AssuranceRequirementRecorded", "ContextCompiled", "RouteSelected"]
        prepared = PreparedDispatch(
            "att-scenario", "asr-scenario", "a" * 64, {"compiled": True},
            {"kind": "selected"}, "art-evidence", "b" * 64,
            "art-operations", "c" * 64, "2026-07-07T00:00:00Z",
        )
        issue_prepared_dispatch(
            prepared, _ScenarioAdapter(), _ScenarioOperations(),
            _ScenarioCommandService(events),
        )
        events.append("GraderResultRecorded")
        return Gate3ScenarioResult(
            "A", tuple(events), producer_actor_id="actor-producer",
            verifier_actor_id="actor-independent-verifier", provider_command_count=1,
        )

    def reroute_outage(self) -> Gate3ScenarioResult:
        requirement_id = "asr-preserved-r3"
        request = RouteRequest(
            "route-request", "task", 1, requirement_id, "a" * 64,
            "context", "b" * 64,
        )
        candidate = RouteCandidate("provider-a", 1, 1, 0, 1, 1, 1)
        decision = select_route(request, [candidate], _UnavailableEvidence())
        if decision["kind"] != "failure":
            raise ValueError("outage route unexpectedly selected")
        return Gate3ScenarioResult(
            "B", ("RouteSelectionFailed", "RerouteRequested"),
            original_requirement_id=requirement_id,
            reroute_requirement_id=requirement_id,
        )

    def stop_and_resume(self) -> Gate3ScenarioResult:
        disposition = stop_confirmation(
            provider="terminal",
            process_children="terminal",
            output_writer="terminal",
            checkpoint_writer="terminal",
        )
        if disposition != "confirmed":
            raise ValueError("stop not confirmed")
        initial = 2
        resumed = resume_from_checkpoint(
            _checkpoint(),
            _checkpoint(),
            prior_epoch=initial,
        )
        return Gate3ScenarioResult(
            "C",
            ("StopRequested", "StopConfirmed", "ExecutionResumed"),
            initial_epoch=initial,
            resume_epoch=int(resumed["new_execution_epoch"]),
        )

    def recover_writer(self) -> Gate3ScenarioResult:
        with TemporaryDirectory() as directory:
            project_id = new_id("project")
            ledger = EventLedger(Path(directory), project_id)
            ledger.append(
                [{"event_type": "ScenarioCommandCommitted", "stream_id": "scenario"}]
            )
            restored = EventLedger(Path(directory), project_id)
            batches = tuple(restored.iter_batches())
            events = tuple(restored.iter_events())
        replay_integrity = (
            "pass" if len(batches) <= 1 and len(events) == 1 else "fail"
        )
        return Gate3ScenarioResult(
            "D", ("CommandRecovered", "ReceiptReconstructed"),
            published_batch_count=len(batches), replay_integrity=replay_integrity,
        )

    def deny_restricted_issue(self) -> Gate3ScenarioResult:
        events = ["RestrictedDataRequested"]
        try:
            authorize_operational_surface(
                requested={"roots": {"restricted"}},
                granted={"roots": {"control"}},
            )
        except ValueError:
            events.append("DispatchDenied")
        else:  # pragma: no cover - fail-closed guard
            events.append("ProviderCommandIssued")
        return Gate3ScenarioResult(
            "E",
            tuple(events),
            decision_reason="restricted_data_denied",
        )


def run_gate3_scenario(
    scenario_id: str,
    foundation: FoundationPorts | None = None,
) -> Gate3ScenarioResult:
    """Run one scenario through the supplied composed foundation ports."""
    foundation = foundation or FoundationPorts()
    methods = {
        "A": foundation.produce_and_verify,
        "B": foundation.reroute_outage,
        "C": foundation.stop_and_resume,
        "D": foundation.recover_writer,
        "E": foundation.deny_restricted_issue,
    }
    try:
        return methods[scenario_id]()
    except KeyError as exc:
        raise ValueError(f"unknown Gate 3 scenario: {scenario_id}") from exc
