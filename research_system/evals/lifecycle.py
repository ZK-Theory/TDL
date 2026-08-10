"""Real W3/W4/W7 lifecycle runtime for deterministic fake-provider evaluations."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from collections.abc import Callable
from typing import Any

from research_system.adapters.base import ProviderCommand, ProviderReceipt, TransportResult
from research_system.adapters.fake import FakeTransport
from research_system.adapters.provider import (
    ProviderAdapter,
    default_provider_operation_policy,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.context.models import ContextProfile, SourceFragment
from research_system.context.service import (
    CompiledContextPacket,
    ContextLifecycleService,
    LifecycleBoundDispatch,
    LifecycleIssuedDispatch,
)
from research_system.context.tokenizers import ProviderCountEvidence, ReferenceRegexV1
from research_system.ids import new_id
from research_system.routing.engine import RouteCandidate
from research_system.store.objects import ObjectStore


def start_evaluation(
    fixture_id: str,
    fixture_revision: str,
    subject_hash: str,
    *,
    retry_of: str | None = None,
) -> str:
    """Allocate a fresh run identity; content and lineage remain separate."""
    del fixture_id, fixture_revision, subject_hash, retry_of
    return new_id("evaluation_run")


_EVENT_TYPES = {
    "RequestContextPacket": "ContextPacketRequested",
    "BeginContextCompilation": "ContextCompilationStarted",
    "CompleteContextCompilation": "ContextPacketCompiled",
    "ValidateContextPacket": "ContextPacketValidated",
    "IssueContextPacket": "ContextPacketIssued",
    "RecordContextDelivery": "ContextPacketDelivered",
    "FailContextPacket": "ContextPacketFailed",
    "ExpireContextPacket": "ContextPacketExpired",
    "SupersedeContextPacket": "ContextPacketSuperseded",
}


class _EvaluationContextWriter:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def stream_version(self, context_id: str) -> int:
        return sum(event["stream_id"] == context_id for event in self.events)

    @contextmanager
    def lifecycle_lock(self, context_id: str):
        del context_id
        yield

    def iter_events(self, context_id: str):
        return (event for event in self.events if event["stream_id"] == context_id)

    def submit_context(
        self,
        *,
        command_type: str,
        context_id: str,
        expected_stream_version: int,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> dict[str, str]:
        self.events.append(
            {
                "event_type": _EVENT_TYPES[command_type],
                "stream_id": context_id,
                "stream_version": expected_stream_version + 1,
                "idempotency_key": idempotency_key,
                "payload": dict(payload),
            }
        )
        return {"status": "accepted"}


class _Resolver:
    def __init__(self, fragment: SourceFragment) -> None:
        self.fragment = fragment

    def resolve(self, source_ids: set[str]) -> tuple[SourceFragment, ...]:
        return (self.fragment,) if self.fragment.source_id in source_ids else ()


@dataclass(frozen=True, slots=True)
class EvaluationProviderBinding:
    provider: str
    model: str
    adapter_revision: str
    operation: str
    policy_hash: str
    parity_evidence_hash: str
    currentness_evidence_hash: str
    count: int = 10
    usable_capacity: int = 100


class _W7Adapter:
    def __init__(self, binding: EvaluationProviderBinding) -> None:
        self.binding = binding

    def load_evidence(self, evidence_id: str, content_hash: str) -> dict[str, str]:
        return {"evidence_id": evidence_id, "content_hash": content_hash}

    def revalidate(self, route, compiled, evidence, capability):
        return {
            "profile_id": route["winner"].profile_id,
            "packet_sha256": compiled.packet_sha256,
            "evidence_hash": evidence["content_hash"],
            "capability_digest": capability.digest,
        }

    def build_prevalidated_template(self, dispatch, revalidated, count, capability):
        if revalidated["profile_id"] != dispatch.route["winner"].profile_id:
            raise ValueError("selected evaluation route changed during revalidation")
        accounting = {
            "method": count.counter_id,
            "raw_capacity": self.binding.usable_capacity,
            "fixed_overhead": 10,
            "managed_tokens": count.count,
            "reserved_variable_tokens": 5,
            "segments": {"context": "managed", "system": "reserved"},
        }
        return {
            "operation": self.binding.operation,
            "provider": self.binding.provider,
            "model": self.binding.model,
            "profile_id": dispatch.route["winner"].profile_id,
            "adapter_revision": self.binding.adapter_revision,
            "context_id": dispatch.context.context_id,
            "context_revision": dispatch.context.revision,
            "packet_sha256": dispatch.context.packet_sha256,
            "rendered_payload_hash": dispatch.context.packet_sha256,
            "command_revision": 1,
            "command_revision_hash": sha256_hex(
                canonical_bytes(
                    {
                        "context_id": dispatch.context.context_id,
                        "packet_sha256": dispatch.context.packet_sha256,
                        "operation": self.binding.operation,
                    }
                )
            ),
            "idempotency_key": f"eval:{dispatch.context.request_id}:provider-issue",
            "timeout_s": 30,
            "policy_hash": self.binding.policy_hash,
            "parity_evidence_hash": self.binding.parity_evidence_hash,
            "currentness_evidence_hash": self.binding.currentness_evidence_hash,
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


class EvaluationLifecycleRuntime:
    """Own one durable temporary lifecycle store for a bounded evaluation run."""

    def __init__(self, *, writer_id: str = "evaluation-lifecycle") -> None:
        self._temporary = TemporaryDirectory()
        self.writer = _EvaluationContextWriter()
        self.service = ContextLifecycleService(
            ObjectStore(Path(self._temporary.name)),
            self.writer,
            writer_id=writer_id,
        )

    def close(self) -> None:
        self._temporary.cleanup()

    def compile(self, content: str, *, request_id: str | None = None) -> CompiledContextPacket:
        source_id = f"eval-source-{sha256_hex(content.encode('utf-8'))[:16]}"
        fragment = SourceFragment(
            source_id,
            "1",
            10,
            True,
            content,
            sha256_hex(content.encode("utf-8")),
        )
        return self.service.compile_packet(
            request={
                "request_id": request_id or f"evaluation-context-{new_id('context')}",
                "context_id": new_id("context"),
                "revision": 1,
                "compiler_version": "evaluation-lifecycle-v1",
                "policy_version": "evaluation-lifecycle-v1",
            },
            source_resolver=_Resolver(fragment),
            profile=ContextProfile("evaluation-lifecycle", 10_000),
            reference_counter=ReferenceRegexV1(),
            required_source_ids={source_id},
        )

    def plan(
        self,
        compiled: CompiledContextPacket,
        *,
        task: Any,
        attempt_id: str,
        requirement: Any,
        candidates: Any,
        provider_evidence: Any,
        operational_evidence: Any,
    ) -> LifecycleBoundDispatch:
        dispatch = self.service.plan_dispatch(
            task=task,
            attempt_id=attempt_id,
            requirement=requirement,
            compiled=compiled,
            capability=compiled.capability,
            candidates=candidates,
            provider_evidence=provider_evidence,
            operational_evidence=operational_evidence,
        )
        if type(dispatch) is not LifecycleBoundDispatch:
            raise ValueError("evaluation route did not produce a lifecycle dispatch")
        return dispatch

    def issue(
        self,
        dispatch: LifecycleBoundDispatch,
        *,
        binding: EvaluationProviderBinding,
        transport_result: TransportResult | Callable[[ProviderCommand], TransportResult],
        managed_content: str,
    ) -> tuple[LifecycleIssuedDispatch, ProviderCommand, ProviderReceipt]:
        count = ProviderCountEvidence(
            "evaluation-provider-count-v1",
            "provider_tokens",
            binding.count,
            True,
            binding.provider,
            binding.model,
            "evaluation-render-v1",
            "evaluation-evidence-v1",
        )
        issued = self.service.prevalidate_and_issue_dispatch(
            dispatch,
            capability=dispatch.context.capability,
            provider_count_evidence=count,
            usable_capacity_tokens=binding.usable_capacity,
            w7_adapter=_W7Adapter(binding),
        )
        content = issued.template.content
        command = ProviderCommand(
            provider_command_id=new_id("provider_command"),
            revision=content["command_revision"],
            revision_hash=content["command_revision_hash"],
            provider=content["provider"],
            model=content["model"],
            profile_id=content["profile_id"],
            adapter_revision=content["adapter_revision"],
            policy_hash=content["policy_hash"],
            context_hash=content["packet_sha256"],
            rendered_payload_hash=content["rendered_payload_hash"],
            idempotency_key=content["idempotency_key"],
            operation=content["operation"],
            timeout_s=content["timeout_s"],
            wrapper_accounting=content["wrapper_accounting"],
            authorized=True,
        )
        resolved_result = transport_result(command) if callable(transport_result) else transport_result
        receipt = ProviderAdapter(
            ["fake-evaluation-provider"],
            FakeTransport([resolved_result]),
            operation_policy=default_provider_operation_policy(live_provider_enabled=True),
        ).issue(
            command,
            managed_content,
            issued_dispatch=issued,
            capability=dispatch.context.capability,
        )
        return issued, command, receipt


def execute_lifecycle_fixture(
    registration: Any,
    subject: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Execute one protected fixture through W3/W4/W7 and fake transport."""

    class Task:
        task_id = f"task-calibration-{registration.fixture_id}"
        revision = 1
        route_request_id = f"route-calibration-{registration.fixture_id}-{new_id('context')}"

    class Requirement:
        assurance_requirement_id = f"requirement-calibration-{registration.fixture_id}"
        content_hash = "a" * 64
        task_id = Task.task_id
        task_revision = Task.revision

    class Evidence:
        routing_evidence_snapshot_id = f"snapshot-calibration-{registration.fixture_id}"
        evidence_id = f"evidence-calibration-{registration.fixture_id}"
        content_hash = "b" * 64
        expires_at = "2030-01-01T00:00:00Z"

        def validate_pre_route(self):
            return None

        def hard_gate_failures(self, request, candidate):
            del request, candidate
            return ()

    runtime = EvaluationLifecycleRuntime(writer_id=f"calibration-{registration.fixture_id}")
    try:
        managed_content = canonical_bytes(
            {"fixture_id": registration.fixture_id, "subject": subject, "payload": payload}
        ).decode("utf-8")
        compiled = runtime.compile(managed_content)
        dispatch = runtime.plan(
            compiled,
            task=Task(),
            attempt_id=f"attempt-calibration-{registration.fixture_id}",
            requirement=Requirement(),
            candidates=[RouteCandidate("calibration-fake", 1, 1, 0, 100, 1, 1)],
            provider_evidence=Evidence(),
            operational_evidence=Evidence(),
        )
        observed = registration.execute_raw(subject, dict(payload))
        observed_hash = sha256_hex(canonical_bytes(observed))

        def terminal(command: ProviderCommand) -> TransportResult:
            import json

            return TransportResult(
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
                        "output_refs": [f"decision:{observed_hash}"],
                    },
                    sort_keys=True,
                ),
                "",
                "calibration-provider-request",
                0,
            )

        _issued, _command, receipt = runtime.issue(
            dispatch,
            binding=EvaluationProviderBinding(
                provider="fake-codex",
                model="fake-model",
                adapter_revision="fake-codex-adapter-v1",
                operation="evaluate_gate5_fixture",
                policy_hash="c" * 64,
                parity_evidence_hash="d" * 64,
                currentness_evidence_hash="e" * 64,
            ),
            transport_result=terminal,
            managed_content=managed_content,
        )
        if not receipt.complete:
            raise ValueError("protected fixture provider execution is incomplete")
        return observed
    finally:
        runtime.close()
