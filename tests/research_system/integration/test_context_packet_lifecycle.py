from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, tzinfo
import json
from types import SimpleNamespace

import pytest

from research_system.adapters.base import ProviderCommand, TransportResult
from research_system.adapters.fake import FakeTransport
from research_system.adapters.provider import ProviderAdapter
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.context.command_adapter import CommandServiceContextWriter
from research_system.context.models import ContextProfile, SourceFragment
from research_system.context.registry import (
    rebuild_context_lifecycle,
    rebuild_owner_operated_handoff,
    resolve_context_packet_for_consumer,
)
from research_system.context.service import ContextLifecycleService
from research_system.routing.engine import RouteCandidate
from research_system.context.tokenizers import ProviderCountEvidence, ReferenceRegexV1
from research_system.errors import ArsError
from research_system.ids import new_id
from research_system.operations.coordinator import issue_lifecycle_dispatch
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
    "PrepareOwnerOperatedContextHandoff": "OwnerOperatedContextHandoffPrepared",
    "ValidateOwnerOperatedContextHandoff": "OwnerOperatedContextHandoffValidated",
    "IssueOwnerOperatedContextHandoff": "OwnerOperatedContextHandoffIssued",
    "RecordOwnerOperatedContextDelivery": "OwnerOperatedContextDelivered",
}


class MissingOffsetTimezone(tzinfo):
    def utcoffset(self, _value):
        return None

    def dst(self, _value):
        return None


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
                "event_id": new_id("event"),
                "event_hash": sha256_hex(canonical_bytes(payload)),
                "event_type": EVENT_TYPES[command_type],
                "stream_id": context_id,
                "stream_version": expected_stream_version + 1,
                "idempotency_key": idempotency_key,
                "payload": dict(payload),
            }
        )
        return {"status": "accepted"}


class StaticSourceResolver:
    def __init__(self, *fragments: SourceFragment, before_resolve=None) -> None:
        self.fragments = fragments
        self.before_resolve = before_resolve
        self.calls: list[set[str]] = []

    def resolve(self, source_ids: set[str]) -> tuple[SourceFragment, ...]:
        if self.before_resolve is not None:
            self.before_resolve()
        self.calls.append(set(source_ids))
        return tuple(fragment for fragment in self.fragments if fragment.source_id in source_ids)


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
        source_resolver=StaticSourceResolver(fragment),
        profile=ContextProfile("bounded-r2", 100),
        reference_counter=ReferenceRegexV1(),
        required_source_ids={"method-source"},
    )


def test_owner_operated_profile_is_provider_free_and_replayable(tmp_path) -> None:
    objects = ObjectStore(tmp_path)
    writer = RecordingContextWriter()
    lifecycle = ContextLifecycleService(
        objects,
        writer,
        writer_id="spec-owner",
        clock=lambda: datetime(2026, 8, 14, 10, tzinfo=UTC),
    )
    context_id = new_id("context")
    compiled = compile_valid(lifecycle, context_id)

    validated = lifecycle.prevalidate_owner_operated(
        compiled,
        capability=compiled.capability,
        operator_id="stephen",
        operator_session_id="codex-desktop-session-1",
        recipient_id="spec-brief-consumer",
        purpose="methods_brief",
        scope="rm-03-export",
        accepted_artefacts=(
            {"artefact_id": new_id("artefact"), "content_sha256": "1" * 64},
            {"artefact_id": new_id("artefact"), "content_sha256": "2" * 64},
        ),
        application_version="1.0",
        valid_from="2026-08-14T10:00:00Z",
        expires_at="2026-08-14T12:00:00Z",
    )
    assert validated.profile.content["provider_launch"] is False
    assert "provider" not in validated.profile.content
    lifecycle.issue_owner_operated(validated)
    delivered = lifecycle.record_owner_operated_delivery(
        compiled,
        validated,
        recipient_id="spec-brief-consumer",
        recipient_session_id="codex-desktop-session-1",
    )

    assert delivered["status"] == "accepted"
    assert len([event for event in writer.events if event["event_type"] == "OwnerOperatedContextDelivered"]) == 1
    prepared = next(
        event["payload"] for event in writer.events if event["event_type"] == "OwnerOperatedContextHandoffPrepared"
    )
    assert prepared["owner_profile"]["provider_launch"] is False
    assert "provider_template" not in prepared

    with pytest.raises(ArsError, match="semantic identity|durable handoff"):
        lifecycle.record_owner_operated_delivery(
            compiled,
            validated,
            recipient_id="wrong-consumer",
            recipient_session_id="codex-desktop-session-1",
        )


def test_owner_operated_profile_rejects_duplicate_accepted_artefacts_before_publication(tmp_path) -> None:
    objects = ObjectStore(tmp_path)
    writer = RecordingContextWriter()
    lifecycle = ContextLifecycleService(
        objects,
        writer,
        writer_id="spec-owner",
        clock=lambda: datetime(2026, 8, 14, 11, tzinfo=UTC),
    )
    compiled = compile_valid(lifecycle, new_id("context"))
    artefact_id = new_id("artefact")
    before = tuple(writer.events)

    with pytest.raises(ArsError, match="artefact IDs must be unique"):
        lifecycle.prevalidate_owner_operated(
            compiled,
            capability=compiled.capability,
            operator_id="stephen",
            operator_session_id="codex-desktop-session-1",
            recipient_id="spec-brief-consumer",
            purpose="methods_brief",
            scope="rm-03-export",
            accepted_artefacts=(
                {"artefact_id": artefact_id, "content_sha256": "1" * 64},
                {"artefact_id": artefact_id, "content_sha256": "2" * 64},
            ),
            application_version="1.0",
            valid_from="2026-08-14T10:00:00Z",
            expires_at="2026-08-14T12:00:00Z",
        )

    assert tuple(writer.events) == before


@pytest.mark.parametrize(
    "now",
    (
        datetime(2026, 8, 14, 9, 59, 59, tzinfo=UTC),
        datetime(2026, 8, 14, 12, tzinfo=UTC),
    ),
)
def test_owner_operated_prevalidation_rejects_outside_half_open_window_without_publication(tmp_path, now) -> None:
    objects = ObjectStore(tmp_path)
    writer = RecordingContextWriter()
    lifecycle = ContextLifecycleService(objects, writer, writer_id="spec-owner", clock=lambda: now)
    compiled = compile_valid(lifecycle, new_id("context"))
    before = tuple(writer.events)

    with pytest.raises(ArsError, match="outside its finite window"):
        lifecycle.prevalidate_owner_operated(
            compiled,
            capability=compiled.capability,
            operator_id="stephen",
            operator_session_id="codex-desktop-session-1",
            recipient_id="spec-brief-consumer",
            purpose="methods_brief",
            scope="rm-03-export",
            accepted_artefacts=({"artefact_id": new_id("artefact"), "content_sha256": "1" * 64},),
            application_version="1.0",
            valid_from="2026-08-14T10:00:00Z",
            expires_at="2026-08-14T12:00:00Z",
        )

    assert tuple(writer.events) == before


def test_owner_operated_prevalidation_rechecks_window_before_validation(tmp_path) -> None:
    objects = ObjectStore(tmp_path)
    writer = RecordingContextWriter()
    lifecycle = ContextLifecycleService(
        objects,
        writer,
        writer_id="spec-owner",
        clock=lambda: datetime(2026, 8, 14, 11, tzinfo=UTC),
    )
    compiled = compile_valid(lifecycle, new_id("context"))

    class SaturatingClock:
        def __init__(self) -> None:
            self.calls = 0

        def __call__(self) -> datetime:
            self.calls += 1
            if self.calls == 1:
                return datetime(2026, 8, 14, 10, tzinfo=UTC)
            return datetime(2026, 8, 14, 12, tzinfo=UTC)

    clock = SaturatingClock()
    lifecycle.clock = clock

    with pytest.raises(ArsError, match="outside its finite window"):
        lifecycle.prevalidate_owner_operated(
            compiled,
            capability=compiled.capability,
            operator_id="stephen",
            operator_session_id="codex-desktop-session-1",
            recipient_id="spec-brief-consumer",
            purpose="methods_brief",
            scope="rm-03-export",
            accepted_artefacts=({"artefact_id": new_id("artefact"), "content_sha256": "1" * 64},),
            application_version="1.0",
            valid_from="2026-08-14T10:00:00Z",
            expires_at="2026-08-14T12:00:00Z",
        )

    owner_events = [event["event_type"] for event in writer.events if event["event_type"].startswith("Owner")]
    assert owner_events == ["OwnerOperatedContextHandoffPrepared"]
    assert clock.calls >= 2


def test_owner_operated_prevalidation_rejects_clock_with_non_utc_aware_timezone(tmp_path) -> None:
    objects = ObjectStore(tmp_path)
    writer = RecordingContextWriter()
    malformed = datetime(2026, 8, 14, 11, tzinfo=MissingOffsetTimezone())
    lifecycle = ContextLifecycleService(
        objects,
        writer,
        writer_id="spec-owner",
        clock=lambda: datetime(2026, 8, 14, 11, tzinfo=UTC),
    )
    compiled = compile_valid(lifecycle, new_id("context"))
    before = tuple(writer.events)
    lifecycle.clock = lambda: malformed

    with pytest.raises(ArsError, match="timezone-aware"):
        lifecycle.prevalidate_owner_operated(
            compiled,
            capability=compiled.capability,
            operator_id="stephen",
            operator_session_id="codex-desktop-session-1",
            recipient_id="spec-brief-consumer",
            purpose="methods_brief",
            scope="rm-03-export",
            accepted_artefacts=({"artefact_id": new_id("artefact"), "content_sha256": "1" * 64},),
            application_version="1.0",
            valid_from="2026-08-14T10:00:00Z",
            expires_at="2026-08-14T12:00:00Z",
        )

    assert tuple(writer.events) == before


def test_context_compilation_rejects_malformed_clock_before_publication(tmp_path) -> None:
    objects = ObjectStore(tmp_path)
    writer = RecordingContextWriter()
    malformed = datetime(2026, 8, 14, 11, tzinfo=MissingOffsetTimezone())
    lifecycle = ContextLifecycleService(objects, writer, writer_id="writer-1", clock=lambda: malformed)

    with pytest.raises(ArsError, match="timezone-aware"):
        compile_valid(lifecycle, new_id("context"))

    assert writer.events == []
    assert tuple((tmp_path / "objects" / "context").rglob("*.json")) == ()


def test_context_delivery_rejects_malformed_clock_before_receipt_or_event(tmp_path) -> None:
    objects = ObjectStore(tmp_path)
    writer = RecordingContextWriter()
    lifecycle = ContextLifecycleService(
        objects,
        writer,
        writer_id="writer-1",
        clock=lambda: datetime(2026, 8, 14, 11, tzinfo=UTC),
    )
    compiled = compile_valid(lifecycle, new_id("context"))
    before_events = deepcopy(writer.events)
    before_objects = tuple((tmp_path / "objects" / "context").rglob("*.json"))
    malformed = datetime(2026, 8, 14, 11, tzinfo=MissingOffsetTimezone())
    lifecycle.clock = lambda: malformed

    with pytest.raises(ArsError, match="timezone-aware"):
        lifecycle.record_delivery(
            compiled,
            recipient_id="consumer-1",
            recipient_session_id="session-1",
            adapter_id="adapter-1",
            delivered_sha256=compiled.packet_sha256,
        )

    assert writer.events == before_events
    assert tuple((tmp_path / "objects" / "context").rglob("*.json")) == before_objects


def test_context_command_adapter_rejects_malformed_clock_without_submission() -> None:
    submissions = []
    service = SimpleNamespace(
        ledger=SimpleNamespace(project_id="prj_01978abc-1000-7000-8000-000000001000"),
        _context_lifecycle_submission_key=object(),
        submit=submissions.append,
    )
    malformed = datetime(2026, 8, 14, 11, tzinfo=MissingOffsetTimezone())
    writer = CommandServiceContextWriter(
        service,
        actor_id="act_01978abc-1000-7000-8000-000000001000",
        authority_grant_id="agr_01978abc-1000-7000-8000-000000001000",
        clock=lambda: malformed,
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        writer.submit_context(
            command_type="RequestContextPacket",
            context_id="ctx_01978abc-1000-7000-8000-000000001000",
            expected_stream_version=0,
            idempotency_key="context-clock-negative",
            payload={"context_id": "ctx_01978abc-1000-7000-8000-000000001000"},
        )

    assert submissions == []


def test_owner_operated_replay_rejects_delivery_session_outside_prepared_profile(tmp_path) -> None:
    objects = ObjectStore(tmp_path)
    writer = RecordingContextWriter()
    lifecycle = ContextLifecycleService(
        objects,
        writer,
        writer_id="spec-owner",
        clock=lambda: datetime(2026, 8, 14, 11, tzinfo=UTC),
    )
    compiled = compile_valid(lifecycle, new_id("context"))
    validated = lifecycle.prevalidate_owner_operated(
        compiled,
        capability=compiled.capability,
        operator_id="stephen",
        operator_session_id="codex-desktop-session-1",
        recipient_id="spec-brief-consumer",
        purpose="methods_brief",
        scope="rm-03-export",
        accepted_artefacts=({"artefact_id": new_id("artefact"), "content_sha256": "1" * 64},),
        application_version="1.0",
        valid_from="2026-08-14T10:00:00Z",
        expires_at="2026-08-14T12:00:00Z",
    )
    lifecycle.issue_owner_operated(validated)
    lifecycle.record_owner_operated_delivery(
        compiled,
        validated,
        recipient_id="spec-brief-consumer",
        recipient_session_id="codex-desktop-session-1",
    )
    tampered = deepcopy(writer.events)
    tampered[-1]["payload"]["recipient_session_id"] = "different-session"

    with pytest.raises(ArsError, match="operator session"):
        rebuild_owner_operated_handoff(tampered, compiled.context_id)


def test_owner_operated_exact_committed_retries_remain_available_after_expiry(tmp_path) -> None:
    class IdempotentWriter(RecordingContextWriter):
        def submit_context(self, **kwargs):
            prior = next(
                (event for event in self.events if event["idempotency_key"] == kwargs["idempotency_key"]),
                None,
            )
            if prior is not None:
                assert prior["payload"] == kwargs["payload"]
                return {"status": "accepted"}
            return super().submit_context(**kwargs)

    current = [datetime(2026, 8, 14, 11, tzinfo=UTC)]
    objects = ObjectStore(tmp_path)
    writer = IdempotentWriter()
    lifecycle = ContextLifecycleService(objects, writer, writer_id="spec-owner", clock=lambda: current[0])
    compiled = compile_valid(lifecycle, new_id("context"))
    kwargs = {
        "capability": compiled.capability,
        "operator_id": "stephen",
        "operator_session_id": "codex-desktop-session-1",
        "recipient_id": "spec-brief-consumer",
        "purpose": "methods_brief",
        "scope": "rm-03-export",
        "accepted_artefacts": ({"artefact_id": new_id("artefact"), "content_sha256": "1" * 64},),
        "application_version": "1.0",
        "valid_from": "2026-08-14T10:00:00Z",
        "expires_at": "2026-08-14T12:00:00Z",
    }
    validated = lifecycle.prevalidate_owner_operated(compiled, **kwargs)
    lifecycle.issue_owner_operated(validated)
    lifecycle.record_owner_operated_delivery(
        compiled,
        validated,
        recipient_id="spec-brief-consumer",
        recipient_session_id="codex-desktop-session-1",
    )
    before = deepcopy(writer.events)
    current[0] = datetime(2026, 8, 14, 12, tzinfo=UTC)

    assert lifecycle.prevalidate_owner_operated(compiled, **kwargs) == validated
    assert lifecycle.issue_owner_operated(validated)["status"] == "accepted"
    assert (
        lifecycle.record_owner_operated_delivery(
            compiled,
            validated,
            recipient_id="spec-brief-consumer",
            recipient_session_id="codex-desktop-session-1",
        )["status"]
        == "accepted"
    )
    assert writer.events == before


def test_owner_operated_exact_orphan_receipt_recovers_after_expiry(tmp_path) -> None:
    class InterruptBeforeDelivery(RecordingContextWriter):
        interrupted = False

        def submit_context(self, **kwargs):
            if kwargs["command_type"] == "RecordOwnerOperatedContextDelivery" and not self.interrupted:
                self.interrupted = True
                raise ConnectionError("delivery event response unavailable")
            return super().submit_context(**kwargs)

    current = [datetime(2026, 8, 14, 11, tzinfo=UTC)]
    objects = ObjectStore(tmp_path)
    writer = InterruptBeforeDelivery()
    lifecycle = ContextLifecycleService(objects, writer, writer_id="spec-owner", clock=lambda: current[0])
    compiled = compile_valid(lifecycle, new_id("context"))
    validated = lifecycle.prevalidate_owner_operated(
        compiled,
        capability=compiled.capability,
        operator_id="stephen",
        operator_session_id="codex-desktop-session-1",
        recipient_id="spec-brief-consumer",
        purpose="methods_brief",
        scope="rm-03-export",
        accepted_artefacts=({"artefact_id": new_id("artefact"), "content_sha256": "1" * 64},),
        application_version="1.0",
        valid_from="2026-08-14T10:00:00Z",
        expires_at="2026-08-14T12:00:00Z",
    )
    lifecycle.issue_owner_operated(validated)
    with pytest.raises(ConnectionError, match="response unavailable"):
        lifecycle.record_owner_operated_delivery(
            compiled,
            validated,
            recipient_id="spec-brief-consumer",
            recipient_session_id="codex-desktop-session-1",
        )
    receipt_paths = tuple((tmp_path / "objects" / "context").rglob("*.json"))
    receipt_bytes = {path: path.read_bytes() for path in receipt_paths}
    current[0] = datetime(2026, 8, 14, 12, tzinfo=UTC)

    recovered = lifecycle.record_owner_operated_delivery(
        compiled,
        validated,
        recipient_id="spec-brief-consumer",
        recipient_session_id="codex-desktop-session-1",
    )

    assert recovered["status"] == "accepted"
    assert len([event for event in writer.events if event["event_type"] == "OwnerOperatedContextDelivered"]) == 1
    assert {path: path.read_bytes() for path in receipt_paths} == receipt_bytes


def test_owner_operated_orphan_receipt_outside_original_window_remains_rejected(tmp_path) -> None:
    class InterruptBeforeDelivery(RecordingContextWriter):
        interrupted = False

        def submit_context(self, **kwargs):
            if kwargs["command_type"] == "RecordOwnerOperatedContextDelivery" and not self.interrupted:
                self.interrupted = True
                raise ConnectionError("delivery event response unavailable")
            return super().submit_context(**kwargs)

    current = [datetime(2026, 8, 14, 11, tzinfo=UTC)]
    objects = ObjectStore(tmp_path)
    writer = InterruptBeforeDelivery()
    lifecycle = ContextLifecycleService(objects, writer, writer_id="spec-owner", clock=lambda: current[0])
    compiled = compile_valid(lifecycle, new_id("context"))
    validated = lifecycle.prevalidate_owner_operated(
        compiled,
        capability=compiled.capability,
        operator_id="stephen",
        operator_session_id="codex-desktop-session-1",
        recipient_id="spec-brief-consumer",
        purpose="methods_brief",
        scope="rm-03-export",
        accepted_artefacts=({"artefact_id": new_id("artefact"), "content_sha256": "1" * 64},),
        application_version="1.0",
        valid_from="2026-08-14T10:00:00Z",
        expires_at="2026-08-14T12:00:00Z",
    )
    lifecycle.issue_owner_operated(validated)
    with pytest.raises(ConnectionError, match="response unavailable"):
        lifecycle.record_owner_operated_delivery(
            compiled,
            validated,
            recipient_id="spec-brief-consumer",
            recipient_session_id="codex-desktop-session-1",
        )
    receipt_path = next(
        path
        for path in (tmp_path / "objects" / "context").rglob("*.json")
        if json.loads(path.read_bytes()).get("schema_id") == "ars://wp6-6/owner-operated-context-delivery-receipt"
    )
    receipt = json.loads(receipt_path.read_bytes())
    receipt["delivered_at"] = "2026-08-14T12:00:00Z"
    changed_bytes = canonical_bytes(receipt)
    changed_path = receipt_path.with_name(f"00000001-{sha256_hex(changed_bytes)}.json")
    changed_path.write_bytes(changed_bytes)
    receipt_path.unlink()
    current[0] = datetime(2026, 8, 14, 12, tzinfo=UTC)
    before_events = deepcopy(writer.events)

    with pytest.raises(ArsError, match="outside its finite window"):
        lifecycle.record_owner_operated_delivery(
            compiled,
            validated,
            recipient_id="spec-brief-consumer",
            recipient_session_id="codex-desktop-session-1",
        )

    assert writer.events == before_events


def test_owner_operated_prevalidation_resumes_after_prepare_before_validate(tmp_path) -> None:
    objects = ObjectStore(tmp_path)

    class InterruptBeforeValidation(RecordingContextWriter):
        interrupted = False

        def submit_context(self, **kwargs):
            if any(event["idempotency_key"] == kwargs["idempotency_key"] for event in self.events):
                return {"status": "accepted"}
            if kwargs["command_type"] == "ValidateOwnerOperatedContextHandoff" and not self.interrupted:
                self.interrupted = True
                raise ConnectionError("validation response unavailable")
            return super().submit_context(**kwargs)

    writer = InterruptBeforeValidation()
    lifecycle = ContextLifecycleService(
        objects,
        writer,
        writer_id="spec-owner",
        clock=lambda: datetime(2026, 8, 14, 11, tzinfo=UTC),
    )
    compiled = compile_valid(lifecycle, new_id("context"))
    artefacts = (
        {"artefact_id": new_id("artefact"), "content_sha256": "1" * 64},
        {"artefact_id": new_id("artefact"), "content_sha256": "2" * 64},
    )

    def prevalidate() -> object:
        return lifecycle.prevalidate_owner_operated(
            compiled,
            capability=compiled.capability,
            operator_id="stephen",
            operator_session_id="codex-desktop-session-1",
            recipient_id="spec-brief-consumer",
            purpose="methods_brief",
            scope="rm-03-export",
            accepted_artefacts=artefacts,
            application_version="1.0",
            valid_from="2026-08-14T10:00:00Z",
            expires_at="2026-08-14T12:00:00Z",
        )

    with pytest.raises(ConnectionError, match="validation response unavailable"):
        prevalidate()
    assert [event["event_type"] for event in writer.events].count("OwnerOperatedContextHandoffPrepared") == 1

    validated = prevalidate()
    assert validated is not None
    assert [event["event_type"] for event in writer.events].count("OwnerOperatedContextHandoffPrepared") == 1
    assert [event["event_type"] for event in writer.events].count("OwnerOperatedContextHandoffValidated") == 1


@pytest.mark.integration
def test_owner_operated_lifecycle_uses_real_command_service_and_consumer_resolver(tmp_path) -> None:
    now = datetime(2026, 8, 14, 11, tzinfo=UTC)
    harness = control_plane(tmp_path, clock=lambda: now)
    context_id = new_id("context")
    commands = (
        "RequestContextPacket",
        "BeginContextCompilation",
        "CompleteContextCompilation",
        "FailContextPacket",
        "PrepareOwnerOperatedContextHandoff",
        "ValidateOwnerOperatedContextHandoff",
        "IssueOwnerOperatedContextHandoff",
        "RecordOwnerOperatedContextDelivery",
    )
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="context",
        subject_id=context_id,
        actor_id=ACTORS["actor-a"],
        command_types=commands,
    )
    writer = CommandServiceContextWriter(
        harness.service,
        actor_id=ACTORS["actor-a"],
        authority_grant_id=grant_id,
        clock=lambda: now,
    )
    lifecycle = ContextLifecycleService(harness.objects, writer, writer_id="spec-owner", clock=lambda: now)
    content = "governing method and exact source"
    fragment = SourceFragment(
        source_id="method-source",
        revision="1",
        authority_rank=10,
        mandatory=True,
        content=content,
        content_hash=sha256_hex(content.encode("utf-8")),
    )
    source_resolver = StaticSourceResolver(fragment)
    request = request_payload(context_id)
    request.update({"project_id": PROJECT_ID, "actor_id": ACTORS["actor-a"]})
    compiled = lifecycle.compile_packet(
        request=request,
        source_resolver=source_resolver,
        profile=ContextProfile("bounded-r2", 100),
        reference_counter=ReferenceRegexV1(),
        required_source_ids={"method-source"},
    )
    validated = lifecycle.prevalidate_owner_operated(
        compiled,
        capability=compiled.capability,
        operator_id=ACTORS["actor-a"],
        operator_session_id="codex-desktop-session-1",
        recipient_id="spec-brief-consumer",
        purpose="methods_brief",
        scope="rm-03-export",
        accepted_artefacts=(
            {"artefact_id": new_id("artefact"), "content_sha256": "1" * 64},
            {"artefact_id": new_id("artefact"), "content_sha256": "2" * 64},
        ),
        application_version="1.0",
        valid_from="2026-08-14T10:00:00Z",
        expires_at="2026-08-14T12:00:00Z",
    )
    lifecycle.issue_owner_operated(validated)
    first = lifecycle.record_owner_operated_delivery(
        compiled,
        validated,
        recipient_id="spec-brief-consumer",
        recipient_session_id="codex-desktop-session-1",
    )
    restarted = ContextLifecycleService(harness.objects, writer, writer_id="spec-owner", clock=lambda: now)
    recovered = restarted.record_owner_operated_delivery(
        compiled,
        validated,
        recipient_id="spec-brief-consumer",
        recipient_session_id="codex-desktop-session-1",
    )

    assert first.command_id == recovered.command_id
    events = tuple(writer.iter_events(context_id))
    assert [event["event_type"] for event in events][-4:] == list(EVENT_TYPES.values())[-4:]
    resolved = resolve_context_packet_for_consumer(
        events,
        harness.objects,
        context_id=context_id,
        revision=compiled.revision,
        packet_sha256=compiled.packet_sha256,
        consumer_id="spec-brief-consumer",
        purpose="methods_brief",
        scope="rm-03-export",
        evaluation_time=now,
        control_store_identity="store-1",
        source_position=7,
        source_hash="a" * 64,
        source_resolver=source_resolver,
    )
    assert resolved.delivery["provider_launch"] is False
    assert "adapter_id" not in resolved.delivery
    before = harness.ledger.snapshot()
    with pytest.raises(ArsError, match="profile does not authorize"):
        resolve_context_packet_for_consumer(
            events,
            harness.objects,
            context_id=context_id,
            revision=compiled.revision,
            packet_sha256=compiled.packet_sha256,
            consumer_id="foreign-consumer",
            purpose="methods_brief",
            scope="rm-03-export",
            evaluation_time=now,
            control_store_identity="store-1",
            source_position=7,
            source_hash="a" * 64,
            source_resolver=source_resolver,
        )
    with pytest.raises(ArsError, match="outside its finite window"):
        resolve_context_packet_for_consumer(
            events,
            harness.objects,
            context_id=context_id,
            revision=compiled.revision,
            packet_sha256=compiled.packet_sha256,
            consumer_id="spec-brief-consumer",
            purpose="methods_brief",
            scope="rm-03-export",
            evaluation_time=datetime(2026, 8, 14, 12, tzinfo=UTC),
            control_store_identity="store-1",
            source_position=7,
            source_hash="a" * 64,
            source_resolver=source_resolver,
        )
    assert harness.ledger.snapshot() == before


@pytest.mark.integration
def test_owner_operated_delivery_recovers_receipt_written_before_event(tmp_path) -> None:
    objects = ObjectStore(tmp_path)

    class InterruptBeforeDelivery(RecordingContextWriter):
        interrupted = False

        def submit_context(self, **kwargs):
            if kwargs["command_type"] == "RecordOwnerOperatedContextDelivery" and not self.interrupted:
                self.interrupted = True
                raise ConnectionError("delivery event response unavailable")
            return super().submit_context(**kwargs)

    writer = InterruptBeforeDelivery()
    first_time = datetime(2026, 8, 14, 11, tzinfo=UTC)
    lifecycle = ContextLifecycleService(objects, writer, writer_id="spec-owner", clock=lambda: first_time)
    context_id = new_id("context")
    compiled = compile_valid(lifecycle, context_id)
    validated = lifecycle.prevalidate_owner_operated(
        compiled,
        capability=compiled.capability,
        operator_id="stephen",
        operator_session_id="codex-desktop-session-1",
        recipient_id="spec-brief-consumer",
        purpose="methods_brief",
        scope="rm-03-export",
        accepted_artefacts=(
            {"artefact_id": new_id("artefact"), "content_sha256": "1" * 64},
            {"artefact_id": new_id("artefact"), "content_sha256": "2" * 64},
        ),
        application_version="1.0",
        valid_from="2026-08-14T10:00:00Z",
        expires_at="2026-08-14T12:00:00Z",
    )
    lifecycle.issue_owner_operated(validated)
    with pytest.raises(ConnectionError, match="response unavailable"):
        lifecycle.record_owner_operated_delivery(
            compiled,
            validated,
            recipient_id="spec-brief-consumer",
            recipient_session_id="codex-desktop-session-1",
        )
    receipt_paths = tuple((tmp_path / "objects" / "context").rglob("*.json"))
    receipt_path = next(
        path
        for path in receipt_paths
        if json.loads(path.read_text(encoding="utf-8")).get("schema_id")
        == "ars://wp6-6/owner-operated-context-delivery-receipt"
    )
    receipt_bytes_before_retry = receipt_path.read_bytes()

    restarted = ContextLifecycleService(
        objects,
        writer,
        writer_id="spec-owner",
        clock=lambda: datetime(2026, 8, 14, 11, 30, tzinfo=UTC),
    )
    receipt = restarted.record_owner_operated_delivery(
        compiled,
        validated,
        recipient_id="spec-brief-consumer",
        recipient_session_id="codex-desktop-session-1",
    )

    assert receipt["status"] == "accepted"
    delivered = next(event for event in writer.events if event["event_type"] == "OwnerOperatedContextDelivered")
    stored = objects.read("context", delivered["payload"]["delivery_receipt_object_id"], 1)
    assert stored["delivered_at"] == "2026-08-14T11:00:00Z"
    assert receipt_path.read_bytes() == receipt_bytes_before_retry


class RecordingRoutingEvidence:
    routing_evidence_snapshot_id = "routing-snapshot-1"
    evidence_id = "provider-evidence-1"
    content_hash = "c" * 64
    expires_at = "2030-01-01T00:00:00Z"

    def __init__(self) -> None:
        self.gate_calls = 0

    def validate_pre_route(self) -> None:
        return None

    def hard_gate_failures(self, request, candidate) -> tuple[str, ...]:
        del request, candidate
        self.gate_calls += 1
        return ()


class RouteTask:
    task_id = "tsk_" + "1" * 32
    revision = 1
    route_request_id = "rrq_" + "2" * 32


class RouteRequirement:
    assurance_requirement_id = "asr_" + "3" * 32
    content_hash = "d" * 64
    task_id = RouteTask.task_id
    task_revision = RouteTask.revision


class RecordingW7Adapter:
    def __init__(self, compiled) -> None:
        self.compiled = compiled
        self.calls: list[str] = []

    def load_evidence(self, evidence_id, content_hash):
        self.calls.append("load_evidence")
        return {"evidence_id": evidence_id, "content_hash": content_hash}

    def revalidate(self, route, compiled, evidence, capability):
        self.calls.append("revalidate")
        assert compiled is self.compiled
        assert evidence["content_hash"] == "c" * 64
        return {"winner": route["winner"].profile_id, "capability": capability.digest}

    def build_prevalidated_template(self, dispatch, revalidated, count, capability):
        self.calls.append("build_prevalidated_template")
        assert revalidated == {
            "winner": dispatch.route["winner"].profile_id,
            "capability": capability.digest,
        }
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
            "adapter_revision": "adapter-v1",
            "context_id": dispatch.context.context_id,
            "context_revision": dispatch.context.revision,
            "packet_sha256": dispatch.context.packet_sha256,
            "rendered_payload_hash": dispatch.context.packet_sha256,
            "command_revision": 1,
            "command_revision_hash": "e" * 64,
            "idempotency_key": "issue-context-1",
            "timeout_s": 5,
            "policy_hash": "f" * 64,
            "parity_evidence_hash": "1" * 64,
            "currentness_evidence_hash": "2" * 64,
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


def provider_count(count: int = 10) -> ProviderCountEvidence:
    return ProviderCountEvidence(
        "fake-codex-exact-v1",
        "provider_tokens",
        count,
        True,
        "codex",
        "p0-fake",
        "render-v1",
        "eval-v1",
    )


def plan_valid(service: ContextLifecycleService, compiled):
    return service.plan_dispatch(
        task=RouteTask(),
        attempt_id="att_" + "4" * 32,
        requirement=RouteRequirement(),
        compiled=compiled,
        capability=compiled.capability,
        candidates=[RouteCandidate("codex", 1, 1, 0, 100, 1, 1)],
        provider_evidence=RecordingRoutingEvidence(),
        operational_evidence=RecordingRoutingEvidence(),
    )


def validate_valid(service: ContextLifecycleService, compiled):
    return service.prevalidate_dispatch(
        plan_valid(service, compiled),
        capability=compiled.capability,
        provider_count_evidence=provider_count(),
        usable_capacity_tokens=100,
        w7_adapter=RecordingW7Adapter(compiled),
    )


def issue_valid(service: ContextLifecycleService, compiled):
    return service.prevalidate_and_issue_dispatch(
        plan_valid(service, compiled),
        capability=compiled.capability,
        provider_count_evidence=provider_count(),
        usable_capacity_tokens=100,
        w7_adapter=RecordingW7Adapter(compiled),
    )


def test_cli_parser_exposes_exact_nine_context_lifecycle_operations() -> None:
    from research_system.cli import _parser

    expected = {
        "request",
        "begin-compilation",
        "complete-compilation",
        "validate",
        "issue",
        "deliver",
        "fail",
        "expire",
        "supersede",
    }
    observed = set()
    for action in sorted(expected):
        args = _parser().parse_args(
            [
                "context-packet",
                action,
                "--config",
                "config.json",
                "--input",
                "input.json",
                "--actor-id",
                "actor-1",
                "--authority-grant-id",
                "grant-1",
                "--writer-id",
                "writer-1",
            ]
        )
        observed.add(args.context_packet_action)
        assert args.handler.__name__ == "context_packet_transition"
    assert observed == expected


def test_cli_validate_rejects_caller_built_w4_w7_fields_before_any_access(monkeypatch, capsys) -> None:
    from research_system import cli

    effects: list[str] = []

    def bomb_runtime(_args):
        effects.append("runtime")
        raise AssertionError("CLI constructed the context lifecycle runtime")

    def bomb_read(_path):
        effects.append("input")
        raise AssertionError("CLI read caller-supplied validation input")

    monkeypatch.setattr(cli, "_context_packet_runtime", bomb_runtime)
    monkeypatch.setattr(cli, "_read_json", bomb_read)

    result = cli.main(
        [
            "context-packet",
            "validate",
            "--config",
            "unreachable-config.json",
            "--input",
            "unreachable-input.json",
            "--actor-id",
            "actor-1",
            "--authority-grant-id",
            "grant-1",
            "--writer-id",
            "writer-1",
        ]
    )

    assert result == 1
    assert effects == []
    assert "caller-supplied validation or provider-template fields are forbidden" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("action", "source", "invalid_field"),
    [
        ("request", {"payload": "not-an-object"}, "payload"),
        ("begin-compilation", {"payload": []}, "payload"),
        (
            "complete-compilation",
            {"payload": {}, "packet": "not-an-object", "manifest": {}},
            "packet",
        ),
        (
            "complete-compilation",
            {"payload": {}, "packet": {}, "manifest": None},
            "manifest",
        ),
    ],
)
def test_cli_rejects_non_object_lifecycle_inputs_before_service_call(
    monkeypatch,
    capsys,
    action,
    source,
    invalid_field,
) -> None:
    from research_system import cli

    calls = []

    class Lifecycle:
        def request(self, *_args, **_kwargs):
            calls.append("request")

        def begin_compilation(self, *_args, **_kwargs):
            calls.append("begin_compilation")

        def complete_compilation(self, *_args, **_kwargs):
            calls.append("complete_compilation")

    monkeypatch.setattr(cli, "_context_packet_runtime", lambda _args: Lifecycle())
    monkeypatch.setattr(cli, "_read_json", lambda _path: source)

    result = cli.main(
        [
            "context-packet",
            action,
            "--config",
            "config.json",
            "--input",
            "input.json",
            "--actor-id",
            "actor-1",
            "--authority-grant-id",
            "grant-1",
            "--writer-id",
            "writer-1",
        ]
    )

    assert result == 1
    assert calls == []
    assert f"context packet input field must be a JSON object: {invalid_field}" in capsys.readouterr().err


def test_w4_route_rejects_missing_or_foreign_capability_before_evidence(tmp_path) -> None:
    first = ContextLifecycleService(ObjectStore(tmp_path / "first"), RecordingContextWriter(), writer_id="writer-1")
    second = ContextLifecycleService(ObjectStore(tmp_path / "second"), RecordingContextWriter(), writer_id="writer-2")
    compiled = compile_valid(first, new_id("context"))
    foreign = compile_valid(second, new_id("context")).capability
    provider = RecordingRoutingEvidence()
    operational = RecordingRoutingEvidence()
    candidates = [RouteCandidate("codex", 1, 1, 0, 100, 1, 1)]

    with pytest.raises(TypeError):
        first.plan_dispatch(
            task=RouteTask(),
            attempt_id="att_" + "4" * 32,
            requirement=RouteRequirement(),
            compiled=compiled,
            candidates=candidates,
            provider_evidence=provider,
            operational_evidence=operational,
        )
    with pytest.raises(ArsError, match="missing or forged"):
        first.plan_dispatch(
            task=RouteTask(),
            attempt_id="att_" + "4" * 32,
            requirement=RouteRequirement(),
            compiled=compiled,
            capability=foreign,
            candidates=candidates,
            provider_evidence=provider,
            operational_evidence=operational,
        )

    assert provider.gate_calls == 0
    assert operational.gate_calls == 0


def test_w4_route_returns_service_sealed_lifecycle_dispatch(tmp_path) -> None:
    service = ContextLifecycleService(ObjectStore(tmp_path), RecordingContextWriter(), writer_id="writer-1")
    compiled = compile_valid(service, new_id("context"))
    provider = RecordingRoutingEvidence()
    operational = RecordingRoutingEvidence()

    dispatch = service.plan_dispatch(
        task=RouteTask(),
        attempt_id="att_" + "4" * 32,
        requirement=RouteRequirement(),
        compiled=compiled,
        capability=compiled.capability,
        candidates=[RouteCandidate("codex", 1, 1, 0, 100, 1, 1)],
        provider_evidence=provider,
        operational_evidence=operational,
    )

    assert dispatch.context is compiled
    assert dispatch.capability_digest == compiled.capability.digest
    assert dispatch.state == "unissued"
    dispatch.verify_capability(compiled.capability)


def test_coordinator_rejects_foreign_capability_before_any_issue_side_effect(tmp_path) -> None:
    first = ContextLifecycleService(ObjectStore(tmp_path / "first"), RecordingContextWriter(), writer_id="writer-1")
    second = ContextLifecycleService(ObjectStore(tmp_path / "second"), RecordingContextWriter(), writer_id="writer-2")
    compiled = compile_valid(first, new_id("context"))
    foreign = compile_valid(second, new_id("context")).capability
    provider = RecordingRoutingEvidence()
    operational = RecordingRoutingEvidence()
    dispatch = first.plan_dispatch(
        task=RouteTask(),
        attempt_id="att_" + "4" * 32,
        requirement=RouteRequirement(),
        compiled=compiled,
        capability=compiled.capability,
        candidates=[RouteCandidate("codex", 1, 1, 0, 100, 1, 1)],
        provider_evidence=provider,
        operational_evidence=operational,
    )

    class BombPort:
        calls = 0

        def load_evidence(self, *args):
            self.calls += 1
            raise AssertionError("issue side effect reached")

    bomb = BombPort()
    with pytest.raises(ArsError, match="missing or forged"):
        issue_lifecycle_dispatch(dispatch, foreign, bomb, bomb, bomb)
    assert bomb.calls == 0


def test_provider_receipt_replay_skips_provider_reinvocation() -> None:
    from research_system.adapters.base import ProviderCommand, ProviderReceipt
    from research_system.command.models import Receipt
    from research_system.operations.coordinator import _issue_bound_template

    command = ProviderCommand(
        "pcmd-replayed",
        1,
        "a" * 64,
        "fake",
        "model",
        "profile",
        "adapter-v1",
        "b" * 64,
        "c" * 64,
        "d" * 64,
        "replay-key",
        "deliver_context",
        30,
        {},
        True,
    )
    provider_receipt = ProviderReceipt(
        command.provider_command_id,
        command.revision,
        command.revision_hash,
        command.provider,
        command.model,
        command.profile_id,
        command.adapter_revision,
        command.policy_hash,
        command.context_hash,
        "provider-request",
        "response",
        "complete",
        True,
        command.context_hash,
        (),
        None,
        0,
        None,
    )
    terminal_receipt = Receipt("replayed", "terminal", "2" * 64, "batch-4", 4)

    class Commands:
        def __init__(self):
            self.receipts = iter(
                [
                    Receipt("accepted", "grant", "e" * 64, "batch-1", 1),
                    Receipt("accepted", "lease", "f" * 64, "batch-2", 2),
                    Receipt("replayed", "issued", "1" * 64, "batch-3", 3),
                ]
            )

        def submit(self, _command):
            return next(self.receipts)

    class Operations:
        def __init__(self, recovered):
            self.recovered = recovered

        def build_request(self, _issued, binding):
            return binding

        def request_grant_command(self, request):
            return dict(request)

        def load_grant(self, _receipt):
            return {"grant": "recorded"}

        def claim_lease_command(self, grant, attempt_id):
            return {**grant, "attempt_id": attempt_id}

        def load_lease(self, _receipt):
            return {"lease": "recorded"}

        def load_provider_receipt(self, lease, observed_command):
            assert lease == {"lease": "recorded"}
            assert observed_command == command
            return self.recovered, terminal_receipt

        def record_provider_receipt_command(self, _lease, _provider_receipt):
            raise AssertionError("replayed provider receipt was recorded again")

    class Adapter:
        def build_command_from_template(self, *_args):
            return command

        def record_issue_command(self, _command):
            return {"command": "issued"}

        def issue(self, *_args):
            raise AssertionError("provider was reinvoked during replay")

    issued = SimpleNamespace(template=SimpleNamespace(sha256="3" * 64), attempt_id="attempt-1")
    assert _issue_bound_template(issued, object(), Adapter(), Operations(provider_receipt), Commands()) == (
        command,
        provider_receipt,
        terminal_receipt,
    )

    mismatches = {
        "provider_command_id": "pcmd-foreign",
        "command_revision": 2,
        "command_revision_hash": "9" * 64,
        "provider": "foreign-provider",
        "model": "foreign-model",
        "profile_id": "foreign-profile",
        "adapter_revision": "foreign-adapter",
        "policy_hash": "8" * 64,
        "context_hash": "7" * 64,
        "delivered_context_hash": "6" * 64,
    }
    for field, value in mismatches.items():
        with pytest.raises(ArsError, match="recovered provider receipt does not match issued command"):
            _issue_bound_template(
                issued,
                object(),
                Adapter(),
                Operations(replace(provider_receipt, **{field: value})),
                Commands(),
            )


def test_s016_evidence_identity_check_is_explicit(monkeypatch) -> None:
    from research_system.evals import lifecycle as lifecycle_module
    from research_system.evals.executors.release_tranche import execute_s016

    def probe_plan(self, _compiled, **kwargs):
        wrong_request = SimpleNamespace(task_id="unexpected-task")
        kwargs["provider_evidence"].hard_gate_failures(wrong_request, kwargs["candidates"][0])
        raise AssertionError("evidence identity check did not fail closed")

    monkeypatch.setattr(lifecycle_module.EvaluationLifecycleRuntime, "plan", probe_plan)
    with pytest.raises(ValueError, match="unexpected route request"):
        execute_s016("known_good", {"contract": "x", "action": {"required_risk": "R3", "required_independence": "I3"}})


def test_w4_no_route_is_one_compiled_phase_lifecycle_failure(tmp_path) -> None:
    writer = RecordingContextWriter()
    service = ContextLifecycleService(ObjectStore(tmp_path), writer, writer_id="writer-1")
    compiled = compile_valid(service, new_id("context"))
    provider = RecordingRoutingEvidence()
    operational = RecordingRoutingEvidence()
    provider.hard_gate_failures = lambda request, candidate: ("provider_unavailable",)

    with pytest.raises(ArsError, match="no eligible route") as caught:
        service.plan_dispatch(
            task=RouteTask(),
            attempt_id="att_" + "4" * 32,
            requirement=RouteRequirement(),
            compiled=compiled,
            capability=compiled.capability,
            candidates=[RouteCandidate("codex", 1, 1, 0, 100, 1, 1)],
            provider_evidence=provider,
            operational_evidence=operational,
        )

    assert caught.value.receipt == {"status": "accepted"}
    failures = [event for event in writer.events if event["event_type"] == "ContextPacketFailed"]
    assert len(failures) == 1
    assert failures[0]["payload"] == {
        "context_id": compiled.context_id,
        "request_id": compiled.request_id,
        "lifecycle_phase": "compiled",
        "failure_code": "no_eligible_route",
        "packet_evidence_status": "present",
        "packet_revision": compiled.revision,
        "packet_sha256": compiled.packet_sha256,
    }


def test_w7_prevalidation_freezes_template_then_issues_under_lifecycle_lock(tmp_path) -> None:
    writer = RecordingContextWriter()
    service = ContextLifecycleService(ObjectStore(tmp_path), writer, writer_id="writer-1")
    compiled = compile_valid(service, new_id("context"))
    dispatch = service.plan_dispatch(
        task=RouteTask(),
        attempt_id="att_" + "4" * 32,
        requirement=RouteRequirement(),
        compiled=compiled,
        capability=compiled.capability,
        candidates=[RouteCandidate("codex", 1, 1, 0, 100, 1, 1)],
        provider_evidence=RecordingRoutingEvidence(),
        operational_evidence=RecordingRoutingEvidence(),
    )
    adapter = RecordingW7Adapter(compiled)

    issued = service.prevalidate_and_issue_dispatch(
        dispatch,
        capability=compiled.capability,
        provider_count_evidence=provider_count(),
        usable_capacity_tokens=100,
        w7_adapter=adapter,
    )

    assert issued.state == "issued"
    assert issued.template.content["packet_sha256"] == compiled.packet_sha256
    assert adapter.calls == ["load_evidence", "revalidate", "build_prevalidated_template"]
    assert [event["event_type"] for event in writer.events[-2:]] == [
        "ContextPacketValidated",
        "ContextPacketIssued",
    ]


def test_w7_capacity_failure_writes_once_before_adapter_side_effect(tmp_path) -> None:
    writer = RecordingContextWriter()
    service = ContextLifecycleService(ObjectStore(tmp_path), writer, writer_id="writer-1")
    compiled = compile_valid(service, new_id("context"))
    dispatch = service.plan_dispatch(
        task=RouteTask(),
        attempt_id="att_" + "4" * 32,
        requirement=RouteRequirement(),
        compiled=compiled,
        capability=compiled.capability,
        candidates=[RouteCandidate("codex", 1, 1, 0, 100, 1, 1)],
        provider_evidence=RecordingRoutingEvidence(),
        operational_evidence=RecordingRoutingEvidence(),
    )
    adapter = RecordingW7Adapter(compiled)

    with pytest.raises(ArsError, match="bound_provider_capacity_gate"):
        service.prevalidate_and_issue_dispatch(
            dispatch,
            capability=compiled.capability,
            provider_count_evidence=provider_count(81),
            usable_capacity_tokens=100,
            w7_adapter=adapter,
        )

    assert adapter.calls == []
    assert [event["event_type"] for event in writer.events].count("ContextPacketFailed") == 1


def test_deliver_context_transport_requires_unchanged_issued_template_and_capability(tmp_path) -> None:
    writer = RecordingContextWriter()
    service = ContextLifecycleService(ObjectStore(tmp_path), writer, writer_id="writer-1")
    compiled = compile_valid(service, new_id("context"))
    dispatch = service.plan_dispatch(
        task=RouteTask(),
        attempt_id="att_" + "4" * 32,
        requirement=RouteRequirement(),
        compiled=compiled,
        capability=compiled.capability,
        candidates=[RouteCandidate("codex", 1, 1, 0, 100, 1, 1)],
        provider_evidence=RecordingRoutingEvidence(),
        operational_evidence=RecordingRoutingEvidence(),
    )
    issued = service.prevalidate_and_issue_dispatch(
        dispatch,
        capability=compiled.capability,
        provider_count_evidence=provider_count(),
        usable_capacity_tokens=100,
        w7_adapter=RecordingW7Adapter(compiled),
    )
    content = issued.template.content
    command = ProviderCommand(
        provider_command_id="pcmd_" + "5" * 32,
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

    class NonFakeTransport:
        calls = 0

        def invoke(self, argv, stdin, timeout_s):
            del argv, stdin, timeout_s
            self.calls += 1
            raise AssertionError("non-fake transport reached")

    non_fake = NonFakeTransport()
    with pytest.raises(ArsError, match="requires FakeTransport"):
        ProviderAdapter(["provider"], non_fake).issue(
            command,
            "managed context",
            issued_dispatch=issued,
            capability=compiled.capability,
        )
    assert non_fake.calls == 0

    class CountingTransport(FakeTransport):
        def __init__(self):
            self.calls = 0

        def invoke(self, argv, stdin, timeout_s):
            del argv, stdin, timeout_s
            self.calls += 1
            return TransportResult(
                status="terminal",
                stdout=json.dumps(
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
                stderr="",
                provider_request_id="provider-request-1",
                exit_code=0,
            )

    transport = CountingTransport()
    adapter = ProviderAdapter(["fake-provider"], transport)
    with pytest.raises(ArsError, match="missing or forged"):
        adapter.issue(command, "managed context")
    assert transport.calls == 0

    receipt = adapter.issue(
        command,
        "managed context",
        issued_dispatch=issued,
        capability=compiled.capability,
    )
    assert receipt.complete is True
    assert transport.calls == 1


def test_context_compilation_begins_before_source_access_and_returns_receipts(tmp_path) -> None:
    writer = RecordingContextWriter()
    service = ContextLifecycleService(ObjectStore(tmp_path), writer, writer_id="writer-1")
    context_id = new_id("context")
    content = "governing method and exact source"
    fragment = SourceFragment(
        source_id="method-source",
        revision="1",
        authority_rank=10,
        mandatory=True,
        content=content,
        content_hash=sha256_hex(content.encode("utf-8")),
    )
    resolver = StaticSourceResolver(
        fragment,
        before_resolve=lambda: (
            writer.events[-1]["event_type"] == "ContextCompilationStarted"
            or pytest.fail("source access occurred before BeginContextCompilation")
        ),
    )

    compiled = service.compile_packet(
        request=request_payload(context_id),
        source_resolver=resolver,
        profile=ContextProfile("bounded-r2", 100),
        reference_counter=ReferenceRegexV1(),
        required_source_ids={"method-source"},
    )

    assert resolver.calls == [{"method-source"}]
    assert set(compiled.transition_receipts) == {
        "RequestContextPacket",
        "BeginContextCompilation",
        "CompleteContextCompilation",
    }


def test_raw_command_service_cannot_bypass_context_lifecycle(tmp_path) -> None:
    harness = control_plane(tmp_path)
    context_id = new_id("context")
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="context",
        subject_id=context_id,
        command_types=("RequestContextPacket",),
    )
    payload = request_payload(context_id)
    payload.update(
        {
            "project_id": PROJECT_ID,
            "actor_id": ACTORS["actor-a"],
            "required_source_ids": ["method-source"],
        }
    )
    envelope = {
        "command_id": new_id("command"),
        "command_type": "RequestContextPacket",
        "schema_id": "ars://core/command/RequestContextPacket",
        "schema_version": "1.0.0",
        "submitted_at": "2026-08-10T12:00:00Z",
        "actor_id": ACTORS["actor-a"],
        "on_behalf_of_actor_id": None,
        "authority_grant_id": grant_id,
        "target_stream_id": context_id,
        "expected_stream_version": 0,
        "idempotency_key": "raw-context-lifecycle-bypass",
        "correlation_id": f"context:{context_id}",
        "causation_id": None,
        "reason": "attempt raw context lifecycle submission",
        "evidence_refs": [],
        "payload": payload,
        "project_id": PROJECT_ID,
    }
    before = harness.ledger.snapshot()

    with pytest.raises(ArsError, match="ContextLifecycleService"):
        harness.service.submit(envelope)

    assert harness.ledger.snapshot() == before


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
            source_resolver=StaticSourceResolver(*fragments),
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

    issue_valid(service, compiled)
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
        source_resolver=StaticSourceResolver(
            SourceFragment(
                source_id="method-source",
                revision="1",
                authority_rank=10,
                mandatory=True,
                content="governing method and exact source",
                content_hash=sha256_hex(b"governing method and exact source"),
            )
        ),
    )
    assert resolved.packet["rendered_content"] == "governing method and exact source"

    with pytest.raises(ArsError, match="stale or superseded"):
        resolve_context_packet_for_consumer(
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
            source_resolver=StaticSourceResolver(
                SourceFragment(
                    source_id="method-source",
                    revision="1",
                    authority_rank=10,
                    mandatory=True,
                    content="governing method and exact source",
                    content_hash=sha256_hex(b"governing method and exact source"),
                    current=False,
                )
            ),
        )


def test_compilation_failure_writes_one_terminal_failure_and_no_packet(tmp_path) -> None:
    writer = RecordingContextWriter()
    service = ContextLifecycleService(ObjectStore(tmp_path), writer, writer_id="writer-1")
    context_id = new_id("context")
    with pytest.raises(ArsError, match="mandatory source omitted"):
        service.compile_packet(
            request=request_payload(context_id),
            source_resolver=StaticSourceResolver(),
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


def test_restricted_source_fails_before_packet_persistence(tmp_path) -> None:
    writer = RecordingContextWriter()
    objects = ObjectStore(tmp_path)
    service = ContextLifecycleService(objects, writer, writer_id="writer-1")
    context_id = new_id("context")
    content = "restricted source"
    fragment = SourceFragment(
        source_id="restricted-source",
        revision="1",
        authority_rank=10,
        mandatory=True,
        content=content,
        content_hash=sha256_hex(content.encode("utf-8")),
        sensitivity_class="restricted",
    )

    with pytest.raises(ArsError, match="unsafe or restricted"):
        service.compile_packet(
            request=request_payload(context_id),
            source_resolver=StaticSourceResolver(fragment),
            profile=ContextProfile("bounded-r2", 100),
            reference_counter=ReferenceRegexV1(),
            required_source_ids={"restricted-source"},
        )

    assert [event["event_type"] for event in writer.events] == [
        "ContextPacketRequested",
        "ContextCompilationStarted",
        "ContextPacketFailed",
    ]
    assert not list(tmp_path.rglob("*.json"))


def test_production_source_failure_retries_original_receipt_without_reresolving(tmp_path) -> None:
    harness = control_plane(tmp_path)
    context_id = new_id("context")
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="context",
        subject_id=context_id,
        command_types=(
            "RequestContextPacket",
            "BeginContextCompilation",
            "FailContextPacket",
        ),
    )
    writer = CommandServiceContextWriter(
        harness.service,
        actor_id=ACTORS["actor-a"],
        authority_grant_id=grant_id,
        clock=lambda: datetime(2026, 8, 10, tzinfo=UTC),
    )
    service = ContextLifecycleService(harness.objects, writer, writer_id="writer-1")
    resolver = StaticSourceResolver()
    request = request_payload(context_id)
    request.update({"project_id": PROJECT_ID, "actor_id": ACTORS["actor-a"]})

    def compile_missing_source():
        return service.compile_packet(
            request=request,
            source_resolver=resolver,
            profile=ContextProfile("bounded-r2", 100),
            reference_counter=ReferenceRegexV1(),
            required_source_ids={"missing"},
        )

    with pytest.raises(ArsError, match="mandatory source omitted") as first:
        compile_missing_source()
    with pytest.raises(ArsError, match="mandatory source omitted") as retry:
        compile_missing_source()

    assert first.value.receipt == retry.value.receipt
    assert resolver.calls == [{"missing"}]
    assert [event["event_type"] for event in writer.iter_events(context_id)] == [
        "ContextPacketRequested",
        "ContextCompilationStarted",
        "ContextPacketFailed",
    ]


def test_delivery_hash_mismatch_has_no_delivery_write(tmp_path) -> None:
    writer = RecordingContextWriter()
    service = ContextLifecycleService(ObjectStore(tmp_path), writer, writer_id="writer-1")
    compiled = compile_valid(service, new_id("context"))
    issue_valid(service, compiled)
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
    validated = validate_valid(initial, compiled)

    restarted = ContextLifecycleService(objects, writer, writer_id="writer-1")
    recovered = restarted.recover_validated(compiled.context_id)
    assert restarted.issue(recovered) == validated.template
    assert rebuild_context_lifecycle(writer.events, compiled.context_id).state == "issued"


def test_validated_recovery_rejects_template_substitution(tmp_path) -> None:
    writer = RecordingContextWriter()
    objects = ObjectStore(tmp_path)
    service = ContextLifecycleService(objects, writer, writer_id="writer-1")
    compiled = compile_valid(service, new_id("context"))
    validate_valid(service, compiled)
    writer.events[-1]["payload"]["provider_template"] = {"operation": "substituted"}

    restarted = ContextLifecycleService(objects, writer, writer_id="writer-1")
    with pytest.raises(ArsError, match="template bytes changed"):
        restarted.recover_validated(compiled.context_id)
