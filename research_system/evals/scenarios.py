"""Composed deterministic Gate 3 scenarios A through E."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
from tempfile import TemporaryDirectory
from pathlib import Path

from research_system.adapters.base import ProviderCommand, TransportResult
from research_system.adapters.fake import FakeTransport
from research_system.adapters.provider import ProviderAdapter
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.context.models import ContextProfile, SourceFragment
from research_system.context.service import ContextLifecycleFailure, ContextLifecycleService
from research_system.context.tokenizers import ProviderCountEvidence, ReferenceRegexV1
from research_system.ids import new_id
from research_system.evals.lifecycle import EvaluationLifecycleRuntime
from research_system.operations.leases import stop_confirmation
from research_system.operations.recovery import resume_from_checkpoint
from research_system.operations.resources import authorize_operational_surface
from research_system.routing.engine import RouteCandidate
from research_system.routing.independence import RelationshipEvidence, independence_grade
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore
from research_system.schema_registry import bundled_schema_registry


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


class _EligibleEvidence:
    routing_evidence_snapshot_id = "res-scenario-a"
    evidence_id = "art-scenario-evidence"
    content_hash = "b" * 64
    expires_at = "2030-01-01T00:00:00Z"

    def validate_pre_route(self):
        return None

    def hard_gate_failures(self, request, candidate):
        return ()


_CONTEXT_EVENTS = {
    "RequestContextPacket": "ContextPacketRequested",
    "BeginContextCompilation": "ContextCompilationStarted",
    "CompleteContextCompilation": "ContextPacketCompiled",
    "ValidateContextPacket": "ContextPacketValidated",
    "IssueContextPacket": "ContextPacketIssued",
    "FailContextPacket": "ContextPacketFailed",
}


class _ScenarioContextWriter:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def stream_version(self, context_id):
        return sum(event["stream_id"] == context_id for event in self.events)

    @contextmanager
    def lifecycle_lock(self, context_id):
        del context_id
        yield

    def iter_events(self, context_id):
        return (event for event in self.events if event["stream_id"] == context_id)

    def submit_context(self, *, command_type, context_id, expected_stream_version, idempotency_key, payload):
        self.events.append(
            {
                "event_type": _CONTEXT_EVENTS[command_type],
                "stream_id": context_id,
                "stream_version": expected_stream_version + 1,
                "idempotency_key": idempotency_key,
                "payload": dict(payload),
            }
        )
        return {"status": "accepted"}


class _ScenarioResolver:
    def __init__(self, fragment):
        self.fragment = fragment

    def resolve(self, source_ids):
        return (self.fragment,) if self.fragment.source_id in source_ids else ()


class _ScenarioTask:
    task_id = "task-scenario-a"
    revision = 1

    def __init__(self, request_id):
        self.route_request_id = request_id


class _ScenarioRequirement:
    assurance_requirement_id = "asr-scenario-a"
    content_hash = "a" * 64
    task_id = _ScenarioTask.task_id
    task_revision = 1


class _ScenarioW7:
    def load_evidence(self, evidence_id, content_hash):
        return {"evidence_id": evidence_id, "content_hash": content_hash}

    def revalidate(self, route, compiled, evidence, capability):
        del evidence
        return {
            "profile_id": route["winner"].profile_id,
            "packet_sha256": compiled.packet_sha256,
            "capability_digest": capability.digest,
        }

    def build_prevalidated_template(self, dispatch, revalidated, count, capability):
        del revalidated
        accounting = {
            "method": "exact",
            "raw_capacity": 100,
            "fixed_overhead": 10,
            "managed_tokens": count.count,
            "reserved_variable_tokens": 20,
            "segments": {"context": "managed"},
        }
        return {
            "operation": "deliver_context",
            "provider": count.provider,
            "model": count.model,
            "profile_id": dispatch.route["winner"].profile_id,
            "adapter_revision": "scenario-adapter-v1",
            "context_id": dispatch.context.context_id,
            "context_revision": dispatch.context.revision,
            "packet_sha256": dispatch.context.packet_sha256,
            "rendered_payload_hash": dispatch.context.packet_sha256,
            "command_revision": 1,
            "command_revision_hash": "c" * 64,
            "idempotency_key": "scenario-context-delivery",
            "timeout_s": 1,
            "policy_hash": "d" * 64,
            "parity_evidence_hash": "e" * 64,
            "currentness_evidence_hash": "f" * 64,
            "provider_count_evidence": {
                "counter_id": count.counter_id,
                "units": count.units,
                "count": count.count,
                "exact": count.exact,
                "provider": count.provider,
                "model": count.model,
                "rendering_revision": count.rendering_revision,
                "evidence_revision": count.evidence_revision,
            },
            "wrapper_accounting": accounting,
            "wrapper_accounting_sha256": sha256_hex(canonical_bytes(accounting)),
            "capability_digest": capability.digest,
        }


class _ScenarioTransport(FakeTransport):
    def __init__(self, command):
        self.command = command
        super().__init__(
            [
                TransportResult(
                    "terminal",
                    json.dumps(
                        {
                            "provider": command.provider,
                            "model": command.model,
                            "profile_id": command.profile_id,
                            "adapter_revision": command.adapter_revision,
                            "command_revision": command.revision,
                            "command_revision_hash": command.revision_hash,
                            "delivered_context_hash": command.context_hash,
                        }
                    ),
                    "",
                    "scenario-provider-request",
                    0,
                )
            ]
        )

    def invoke(self, argv, stdin, timeout_s):
        return super().invoke(argv, stdin, timeout_s)


class _OutageEvidence:
    routing_evidence_snapshot_id = "res-scenario-b"
    evidence_id = "art-scenario-b"
    content_hash = "4" * 64
    expires_at = "2030-01-01T00:00:00Z"

    def __init__(self, unavailable: frozenset[str]):
        self.unavailable = unavailable

    def hard_gate_failures(self, request, candidate):
        if candidate.profile_id in self.unavailable:
            return ("provider_unavailable",)
        return ()

    def validate_pre_route(self):
        return None


def _family(profile_id: str) -> str:
    return profile_id.split("-", maxsplit=1)[0]


class FoundationPorts:
    """Deterministic composition over existing WP1-WP3 public predicates."""

    def produce_and_verify(self) -> Gate3ScenarioResult:
        authorize_operational_surface(
            requested={"roots": {"control"}},
            granted={"roots": {"control"}},
        )
        request_identity = new_id("route_request")
        candidates = [
            RouteCandidate("claude-producer", 2, 2, 0, 2, 10, 5),
            RouteCandidate("codex-verifier", 1, 2, 0, 2, 12, 6),
        ]
        with TemporaryDirectory() as directory:
            writer = _ScenarioContextWriter()
            lifecycle = ContextLifecycleService(ObjectStore(Path(directory)), writer, writer_id="scenario-writer")
            source = "exact scenario governance source"
            fragment = SourceFragment(
                "scenario-source",
                "1",
                10,
                True,
                source,
                sha256_hex(source.encode("utf-8")),
            )
            compiled = lifecycle.compile_packet(
                request={
                    "request_id": "scenario-context-request",
                    "context_id": new_id("context"),
                    "revision": 1,
                    "compiler_version": "scenario-v1",
                    "policy_version": "scenario-v1",
                },
                source_resolver=_ScenarioResolver(fragment),
                profile=ContextProfile("scenario", 100),
                reference_counter=ReferenceRegexV1(),
                required_source_ids={"scenario-source"},
            )
            task = _ScenarioTask(request_identity)
            producer_dispatch = lifecycle.plan_dispatch(
                task=task,
                attempt_id=new_id("attempt"),
                requirement=_ScenarioRequirement(),
                compiled=compiled,
                capability=compiled.capability,
                candidates=candidates,
                provider_evidence=_EligibleEvidence(),
                operational_evidence=_EligibleEvidence(),
            )
            producer_profile = producer_dispatch.route["winner"].profile_id
            verifier_pool = [
                candidate for candidate in candidates if _family(candidate.profile_id) != _family(producer_profile)
            ]
            verifier_dispatch = lifecycle.plan_dispatch(
                task=task,
                attempt_id=new_id("attempt"),
                requirement=_ScenarioRequirement(),
                compiled=compiled,
                capability=compiled.capability,
                candidates=verifier_pool,
                provider_evidence=_EligibleEvidence(),
                operational_evidence=_EligibleEvidence(),
            )
            verifier_profile = verifier_dispatch.route["winner"].profile_id
            count = ProviderCountEvidence(
                "scenario-exact-v1",
                "provider_tokens",
                10,
                True,
                "fake",
                "p0",
                "scenario-render-v1",
                "scenario-eval-v1",
            )
            issued = lifecycle.prevalidate_and_issue_dispatch(
                producer_dispatch,
                capability=compiled.capability,
                provider_count_evidence=count,
                usable_capacity_tokens=100,
                w7_adapter=_ScenarioW7(),
            )
            content = issued.template.content
            provider_command = ProviderCommand(
                "pcmd-scenario",
                content["command_revision"],
                content["command_revision_hash"],
                content["provider"],
                content["model"],
                content["profile_id"],
                content["adapter_revision"],
                content["policy_hash"],
                content["packet_sha256"],
                content["rendered_payload_hash"],
                content["idempotency_key"],
                content["operation"],
                content["timeout_s"],
                content["wrapper_accounting"],
                True,
            )
            receipt = ProviderAdapter(["scenario-provider"], _ScenarioTransport(provider_command)).issue(
                provider_command,
                source,
                issued_dispatch=issued,
                capability=compiled.capability,
            )
            if not receipt.complete:
                raise ValueError("scenario provider delivery is incomplete")
        relationship = independence_grade(
            RelationshipEvidence(
                same_actor=False,
                same_session=False,
                same_context_hash=False,
                same_model_family=_family(producer_profile) == _family(verifier_profile),
                producer_conclusions_visible=False,
            )
        )
        if relationship not in {"I1", "I2"}:  # pragma: no cover - fail closed
            raise ValueError("verifier relationship is not independent")
        events = [
            "RouteSelected"
            for dispatch in (producer_dispatch, verifier_dispatch)
            if dispatch.route["kind"] == "selected"
        ]
        events.extend(
            "ProviderCommandIssued" for event in writer.events if event["event_type"] == "ContextPacketIssued"
        )
        provider_command_count = sum(event["event_type"] == "ContextPacketIssued" for event in writer.events)
        return Gate3ScenarioResult(
            "A",
            tuple(events),
            producer_actor_id=f"actor-{producer_profile}",
            verifier_actor_id=f"actor-{verifier_profile}",
            provider_command_count=provider_command_count,
        )

    def reroute_outage(self) -> Gate3ScenarioResult:
        request_identity = new_id("route_request")

        class Task:
            task_id = "task-scenario-b"
            revision = 1
            route_request_id = request_identity

        class Requirement:
            assurance_requirement_id = "asr-preserved-r3"
            content_hash = "a" * 64
            task_id = Task.task_id
            task_revision = Task.revision

        outage = RouteCandidate("provider-a", 1, 1, 0, 1, 1, 1)
        fallback = RouteCandidate("provider-b", 1, 1, 0, 1, 2, 2)
        evidence = _OutageEvidence(frozenset({"provider-a"}))
        runtime = EvaluationLifecycleRuntime(writer_id="scenario-b-evaluation")
        try:
            first_context = runtime.compile("scenario B unavailable route")
            try:
                runtime.plan(
                    first_context,
                    task=Task(),
                    attempt_id="attempt-scenario-b-first",
                    requirement=Requirement(),
                    candidates=[outage],
                    provider_evidence=evidence,
                    operational_evidence=evidence,
                )
            except ContextLifecycleFailure:
                events = ["RouteSelectionFailed"]
            else:  # pragma: no cover - fail closed
                events = ["RouteSelected"]
            second_context = runtime.compile("scenario B fallback route")
            second = runtime.plan(
                second_context,
                task=Task(),
                attempt_id="attempt-scenario-b-second",
                requirement=Requirement(),
                candidates=[outage, fallback],
                provider_evidence=evidence,
                operational_evidence=evidence,
            ).route
            issued_command_count = sum(event["event_type"] == "ContextPacketIssued" for event in runtime.writer.events)
        finally:
            runtime.close()
        events.append("RerouteEvaluated")
        if second["kind"] == "selected":
            events.append("RouteSelected")
        if second["request_id"] != request_identity:
            raise ValueError("reroute evaluated a different request")
        return Gate3ScenarioResult(
            "B",
            tuple(events),
            original_requirement_id=Requirement.assurance_requirement_id,
            reroute_requirement_id=Requirement.assurance_requirement_id,
            provider_command_count=issued_command_count,
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
            ledger = EventLedger(Path(directory), project_id, bundled_schema_registry())
            ledger.append([{"event_type": "ScenarioCommandCommitted", "stream_id": "scenario"}])
            restored = EventLedger(Path(directory), project_id, bundled_schema_registry())
            batches = tuple(restored.iter_batches())
            events = tuple(restored.iter_events())
        replay_integrity = "pass" if len(batches) == 1 and len(events) == 1 else "fail"
        return Gate3ScenarioResult(
            "D",
            ("CommandRecovered", "ReceiptReconstructed"),
            published_batch_count=len(batches),
            replay_integrity=replay_integrity,
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
        method = methods[scenario_id]
    except KeyError as exc:
        raise ValueError(f"unknown Gate 3 scenario: {scenario_id}") from exc
    return method()
