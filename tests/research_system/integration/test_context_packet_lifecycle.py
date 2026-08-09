from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest

from research_system.canonical import sha256_hex
from research_system.context.command_adapter import CommandServiceContextWriter
from research_system.context.models import ContextProfile, SourceFragment
from research_system.context.registry import (
    rebuild_context_lifecycle,
    resolve_context_packet_for_consumer,
)
from research_system.context.service import ContextLifecycleService
from research_system.context.tokenizers import ReferenceRegexV1
from research_system.errors import ArsError
from research_system.ids import new_id
from research_system.schema_registry import bundled_schema_registry
from research_system.store.objects import ObjectStore
from tests.research_system.factories import ACTORS, PROJECT_ID, activate_lifecycle_grant, control_plane


EVENT_TYPES = {
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


class RecordingContextWriter:
    def __init__(self) -> None:
        self.events: list[dict] = []
        self._lock_depth = 0

    def stream_version(self, context_id: str) -> int:
        return sum(event["stream_id"] == context_id for event in self.events)

    @contextmanager
    def lifecycle_lock(self, context_id: str):
        del context_id
        self._lock_depth += 1
        try:
            yield
        finally:
            self._lock_depth -= 1

    def iter_events(self, context_id: str):
        return (event for event in self.events if event["stream_id"] == context_id)

    def submit_context(
        self,
        *,
        command_type: str,
        context_id: str,
        expected_stream_version: int,
        idempotency_key: str,
        payload: dict,
    ) -> dict:
        assert expected_stream_version == self.stream_version(context_id)
        if command_type in {"ValidateContextPacket", "IssueContextPacket"}:
            assert self._lock_depth == 1
        self.events.append(
            {
                "event_type": EVENT_TYPES[command_type],
                "stream_id": context_id,
                "stream_version": expected_stream_version + 1,
                "idempotency_key": idempotency_key,
                "payload": dict(payload),
            }
        )
        return {"status": "accepted"}


def request_payload(context_id: str) -> dict:
    return {
        "request_id": "context-request-1",
        "context_id": context_id,
        "revision": 1,
        "project_id": new_id("project"),
        "task_id": new_id("task"),
        "task_revision": 1,
        "purpose": "methods_brief",
        "role": "implementer",
        "risk": "R2",
        "actor_id": new_id("actor"),
        "session_id": "session-1",
        "producing_attempt_id": None,
        "parent_context_id": None,
        "permitted_scopes": ["rm-03-export"],
        "control_store_identity": "store-1",
        "source_position": 7,
        "source_hash": "a" * 64,
        "compiler_version": "1.0.0",
        "policy_version": "1.0.0",
        "reference_profile": "bounded-r2",
        "reference_token_budget": 100,
        "provider_tokenizer_id": None,
        "provider_token_count": None,
        "provider_upper_bound_id": None,
        "provider_upper_bound_count": None,
        "provider_usable_capacity": None,
        "provider_reserve": None,
        "candidate_set_digest": "b" * 64,
        "retrieval_trace_refs": [],
        "confidence_summary": "all mandatory sources are direct and exact",
        "security_declaration": "no credentials, restricted data, transcripts, or hidden reasoning",
        "independence_evidence_refs": [],
        "delivery_receipt_refs": [],
        "currency_triggers": ["project-stream"],
        "retention_class": "project",
        "sensitivity_class": "internal",
        "supersession_lineage": [],
        "cumulative_addendum_bytes": 0,
        "expires_at": "2030-01-01T00:00:00Z",
    }


def compile_valid(service: ContextLifecycleService, context_id: str):
    content = "governing method and exact source"
    fragment = SourceFragment(
        source_id="method-source",
        revision="1",
        authority_rank=10,
        mandatory=True,
        content=content,
        content_hash=sha256_hex(content.encode("utf-8")),
    )
    return service.compile_packet(
        request=request_payload(context_id),
        fragments=[fragment],
        profile=ContextProfile("bounded-r2", 100),
        reference_counter=ReferenceRegexV1(),
        required_source_ids={"method-source"},
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "lost_after",
    ("RequestContextPacket", "BeginContextCompilation", "CompleteContextCompilation"),
)
def test_production_context_compilation_recovers_committed_response_loss(tmp_path, lost_after) -> None:
    harness = control_plane(tmp_path)
    context_id = new_id("context")
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="context",
        subject_id=context_id,
        command_types=(
            "RequestContextPacket",
            "BeginContextCompilation",
            "CompleteContextCompilation",
            "FailContextPacket",
        ),
    )

    def clock() -> datetime:
        return datetime(2026, 8, 9, tzinfo=UTC)

    base_writer = CommandServiceContextWriter(
        harness.service,
        actor_id=ACTORS["actor-a"],
        authority_grant_id=grant_id,
        clock=clock,
    )

    class LoseResponseOnce:
        lost = False

        def stream_version(self, selected_context_id):
            return base_writer.stream_version(selected_context_id)

        def lifecycle_lock(self, selected_context_id):
            return base_writer.lifecycle_lock(selected_context_id)

        def iter_events(self, selected_context_id):
            return base_writer.iter_events(selected_context_id)

        def submit_context(self, **kwargs):
            receipt = base_writer.submit_context(**kwargs)
            if kwargs["command_type"] == lost_after and not self.lost:
                self.lost = True
                raise ConnectionError("accepted context response was lost")
            return receipt

    writer = LoseResponseOnce()
    request = request_payload(context_id)
    request.update({"project_id": PROJECT_ID, "actor_id": ACTORS["actor-a"]})
    content = "governing method and exact source"
    fragments = [
        SourceFragment(
            source_id="method-source",
            revision="1",
            authority_rank=10,
            mandatory=True,
            content=content,
            content_hash=sha256_hex(content.encode("utf-8")),
        )
    ]

    def compile_with(service, selected_request):
        return service.compile_packet(
            request=selected_request,
            fragments=fragments,
            profile=ContextProfile("bounded-r2", 100),
            reference_counter=ReferenceRegexV1(),
            required_source_ids={"method-source"},
        )

    initial = ContextLifecycleService(harness.objects, writer, writer_id="writer-1", clock=clock)
    try:
        first = compile_with(initial, request)
    except ConnectionError:
        first = None
    restarted = ContextLifecycleService(harness.objects, writer, writer_id="writer-1", clock=clock)
    recovered = compile_with(restarted, request)
    exact_retry = compile_with(restarted, request)

    def compilation_identity(compiled):
        return (
            compiled.context_id,
            compiled.request_id,
            compiled.revision,
            compiled.packet_object_id,
            compiled.packet_sha256,
            compiled.manifest_object_id,
            compiled.manifest_sha256,
        )

    if first is not None:
        assert compilation_identity(first) == compilation_identity(recovered)
    assert compilation_identity(recovered) == compilation_identity(exact_retry)
    events = tuple(base_writer.iter_events(context_id))
    assert [event["event_type"] for event in events] == [
        "ContextPacketRequested",
        "ContextCompilationStarted",
        "ContextPacketCompiled",
    ]
    before_changed_retry = harness.ledger.snapshot()
    changed_request = deepcopy(request)
    changed_request["purpose"] = "changed-purpose"
    with pytest.raises(ArsError, match="changed the original request"):
        compile_with(restarted, changed_request)
    assert harness.ledger.snapshot() == before_changed_retry


def test_context_packet_runs_requested_through_delivered_and_resolves(tmp_path) -> None:
    writer = RecordingContextWriter()
    objects = ObjectStore(tmp_path)
    service = ContextLifecycleService(objects, writer, writer_id="writer-1")
    compiled = compile_valid(service, new_id("context"))
    schemas = bundled_schema_registry()
    schemas.validate(
        "ars://context/context-packet",
        objects.read("context", compiled.packet_object_id, compiled.revision),
        schema_version="1.0.0",
    )
    schemas.validate(
        "ars://context/context-manifest",
        objects.read("context", compiled.manifest_object_id, 1),
        schema_version="1.0.0",
    )

    service.validate_and_issue(
        compiled,
        capability=compiled.capability,
        validation_evidence={
            "route_decision_id": "route-1",
            "route_witness_sha256": "c" * 64,
            "selected_route_evidence_sha256": "d" * 64,
        },
        provider_template={
            "operation": "compile_brief",
            "provider": "provider-1",
            "model": "model-1",
            "rendered_sha256": "e" * 64,
        },
    )
    service.record_delivery(
        compiled,
        recipient_id="consumer-1",
        recipient_session_id="consumer-session-1",
        adapter_id="adapter-1",
        delivered_sha256=compiled.packet_sha256,
    )
    delivery_event = writer.events[-1]["payload"]
    schemas.validate(
        "ars://context/context-delivery-receipt",
        objects.read("context", delivery_event["delivery_receipt_object_id"], 1),
        schema_version="1.0.0",
    )

    state = rebuild_context_lifecycle(writer.events, compiled.context_id)
    assert state.state == "delivered"
    resolved = resolve_context_packet_for_consumer(
        writer.events,
        objects,
        context_id=compiled.context_id,
        revision=1,
        packet_sha256=compiled.packet_sha256,
        consumer_id="consumer-1",
        purpose="methods_brief",
        scope="rm-03-export",
        evaluation_time=datetime(2029, 1, 1, tzinfo=UTC),
        control_store_identity="store-1",
        source_position=7,
        source_hash="a" * 64,
    )
    assert resolved.packet["rendered_content"] == "governing method and exact source"


def test_compilation_failure_writes_one_terminal_failure_and_no_packet(tmp_path) -> None:
    writer = RecordingContextWriter()
    service = ContextLifecycleService(ObjectStore(tmp_path), writer, writer_id="writer-1")
    context_id = new_id("context")
    with pytest.raises(ArsError, match="mandatory source omitted"):
        service.compile_packet(
            request=request_payload(context_id),
            fragments=[],
            profile=ContextProfile("bounded-r2", 100),
            reference_counter=ReferenceRegexV1(),
            required_source_ids={"missing"},
        )
    state = rebuild_context_lifecycle(writer.events, context_id)
    assert state.state == "failed"
    assert [event["event_type"] for event in writer.events] == [
        "ContextPacketRequested",
        "ContextCompilationStarted",
        "ContextPacketFailed",
    ]


def test_delivery_hash_mismatch_has_no_delivery_write(tmp_path) -> None:
    writer = RecordingContextWriter()
    service = ContextLifecycleService(ObjectStore(tmp_path), writer, writer_id="writer-1")
    compiled = compile_valid(service, new_id("context"))
    service.validate_and_issue(
        compiled,
        capability=compiled.capability,
        validation_evidence={"route_decision_id": "route-1"},
        provider_template={"operation": "compile_brief"},
    )
    before = list(writer.events)
    with pytest.raises(ArsError, match="delivery hash"):
        service.record_delivery(
            compiled,
            recipient_id="consumer-1",
            recipient_session_id="consumer-session-1",
            adapter_id="adapter-1",
            delivered_sha256="0" * 64,
        )
    assert writer.events == before


def test_validation_to_issue_recovers_after_process_restart(tmp_path) -> None:
    writer = RecordingContextWriter()
    objects = ObjectStore(tmp_path)
    initial = ContextLifecycleService(objects, writer, writer_id="writer-1")
    compiled = compile_valid(initial, new_id("context"))
    template = {
        "operation": "compile_brief",
        "provider": "provider-1",
        "model": "model-1",
        "rendered_sha256": "e" * 64,
    }
    validation = {
        "route_decision_id": "route-1",
        "route_witness_sha256": "c" * 64,
        "selected_route_evidence_sha256": "d" * 64,
    }
    validated = initial.validate(
        compiled,
        capability=compiled.capability,
        validation_evidence=validation,
        provider_template=template,
    )

    restarted = ContextLifecycleService(objects, writer, writer_id="writer-1")
    recovered = restarted.recover_validated(compiled.context_id)
    assert restarted.issue(recovered) == validated.template
    assert rebuild_context_lifecycle(writer.events, compiled.context_id).state == "issued"


def test_validated_recovery_rejects_template_substitution(tmp_path) -> None:
    writer = RecordingContextWriter()
    objects = ObjectStore(tmp_path)
    service = ContextLifecycleService(objects, writer, writer_id="writer-1")
    compiled = compile_valid(service, new_id("context"))
    service.validate(
        compiled,
        capability=compiled.capability,
        validation_evidence={"route_decision_id": "route-1"},
        provider_template={"operation": "compile_brief"},
    )
    writer.events[-1]["payload"]["provider_template"] = {"operation": "substituted"}

    restarted = ContextLifecycleService(objects, writer, writer_id="writer-1")
    with pytest.raises(ArsError, match="template bytes changed"):
        restarted.recover_validated(compiled.context_id)
