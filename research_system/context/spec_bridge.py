"""Provider-free context production from one immutable Discovery replay."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.service import CommandService
from research_system.context.command_adapter import CommandServiceContextWriter
from research_system.context.models import ContextProfile, SourceFragment
from research_system.context.service import CompiledContextPacket, ContextLifecycleService
from research_system.context.tokenizers import ReferenceRegexV1
from research_system.discovery.operator import DiscoveryOperator
from research_system.discovery.replay.driver import replay_discovery
from research_system.errors import ArsError, IntegrityError
from research_system.store.objects import ObjectStore


def _stable_id(kind: str, seed: str) -> str:
    value = int.from_bytes(hashlib.sha256(seed.encode("utf-8")).digest()[:16], "big")
    value = (value & ~(0xF << 76)) | (0x7 << 76)
    value = (value & ~(0b11 << 62)) | (0b10 << 62)
    return f"{kind}_{uuid.UUID(int=value)}"


def derive_spec_owner_context_id(
    *,
    actor_id: str,
    operator_session_id: str,
    recipient_id: str,
    purpose: str,
    scope: str,
    application_version: str,
    valid_from: str,
    expires_at: str,
    retry_identity: str,
) -> str:
    """Derive the governed context target before its scoped grant exists."""

    semantic = [
        actor_id,
        operator_session_id,
        recipient_id,
        purpose,
        scope,
        application_version,
        valid_from,
        expires_at,
        retry_identity,
    ]
    if any(not value for value in semantic):
        raise ArsError("SPEC context semantic identities must be explicit")
    seed = sha256_hex(canonical_bytes({"semantic": semantic}))
    return _stable_id("ctx", f"{seed}:context")


@dataclass(frozen=True, slots=True)
class SpecContextSnapshot:
    source: SourceFragment
    source_position: int
    source_hash: str
    candidate_set_digest: str


class DiscoveryReplaySourceResolver:
    """Resolve one immutable, direct source derived from accepted replay state."""

    def __init__(self, snapshot: SpecContextSnapshot) -> None:
        self.snapshot = snapshot

    def resolve(self, source_ids: set[str]) -> tuple[SourceFragment, ...]:
        return (self.snapshot.source,) if source_ids == {self.snapshot.source.source_id} else ()


def build_spec_context_snapshot(
    events: Sequence[Mapping[str, Any]],
    *,
    schemas: Any,
    route_id: str,
    required_spec_source_sha256: str | None = None,
    authority_state_validator: Any = None,
) -> SpecContextSnapshot:
    """Freeze accepted Discovery identities without caller-authored hashes."""
    if not events:
        raise ArsError("SPEC context requires a durable Discovery replay")
    projection = replay_discovery(
        events,
        schemas=schemas,
        authority_state_validator=authority_state_validator,
    )
    accepted_inputs: list[dict[str, Any]] = []
    durable_approvals: list[dict[str, Any]] = []
    for artefact_id, state in sorted(projection.get("artefact_streams", {}).items()):
        if not isinstance(state, Mapping):
            continue
        manifest = state.get("manifest")
        if isinstance(manifest, Mapping) and manifest.get("artefact_type") == "spec_02_live_run_approval":
            durable_approvals.append(
                {
                    "artefact_id": artefact_id,
                    "content_sha256": state.get("content_sha256"),
                    "relative_path": manifest.get("relative_path"),
                }
            )
        if state.get("use_authority") != "accepted_for_scope":
            continue
        if isinstance(manifest, Mapping) and manifest.get("artefact_type") in {
            "spec_operator_source",
            "methods_asset",
        }:
            if (
                manifest.get("artefact_type") == "spec_operator_source"
                and required_spec_source_sha256 is not None
                and state.get("content_sha256") != required_spec_source_sha256
            ):
                continue
            accepted_inputs.append(
                {
                    "artefact_id": artefact_id,
                    "content_sha256": state.get("content_sha256"),
                    "artefact_type": manifest.get("artefact_type"),
                    "relative_path": manifest.get("relative_path"),
                }
            )
    if len(accepted_inputs) != 2 or sorted(item["artefact_type"] for item in accepted_inputs) != [
        "methods_asset",
        "spec_operator_source",
    ]:
        raise ArsError("SPEC context requires accepted brief source and Methods artefacts")
    candidates = [
        {"candidate_id": key, "state": value.get("status")}
        for key, value in sorted(projection.get("candidates", {}).items())
        if isinstance(value, Mapping)
    ]
    tail = events[-1]
    position = tail.get("global_position")
    tail_hash = tail.get("event_hash")
    if not isinstance(position, int) or not isinstance(tail_hash, str) or len(tail_hash) != 64:
        raise IntegrityError("Discovery replay tail identity is unavailable")
    content_value = {
        "schema_id": "ars://context/spec-discovery-source",
        "schema_version": "1.0.0",
        "route_id": route_id,
        "source_position": position,
        "source_hash": tail_hash,
        "accepted_inputs": accepted_inputs,
        "durable_spec_02_approvals": durable_approvals,
        "candidates": candidates,
    }
    raw = canonical_bytes(content_value)
    digest = sha256_hex(raw)
    return SpecContextSnapshot(
        source=SourceFragment(
            source_id=f"spec-discovery:{digest}",
            revision=tail_hash,
            authority_rank=100,
            mandatory=True,
            content=raw.decode("utf-8"),
            content_hash=digest,
        ),
        source_position=position,
        source_hash=tail_hash,
        candidate_set_digest=sha256_hex(canonical_bytes(candidates)),
    )


def deliver_spec_owner_context(
    *,
    operator: DiscoveryOperator,
    command_service: CommandService,
    actor_id: str,
    authority_grant_id: str,
    operator_session_id: str,
    recipient_id: str,
    purpose: str,
    scope: str,
    retry_identity: str,
    application_version: str,
    valid_from: str,
    expires_at: str,
    required_spec_source_sha256: str,
) -> tuple[CompiledContextPacket, DiscoveryReplaySourceResolver]:
    """Compile, validate, issue, and record an honest manual brief handoff."""
    if not authority_grant_id or not retry_identity:
        raise ArsError("SPEC context semantic identities and authority must be explicit")
    semantic = [
        actor_id,
        operator_session_id,
        recipient_id,
        purpose,
        scope,
        application_version,
        valid_from,
        expires_at,
        retry_identity,
    ]
    events = tuple(operator.ledger.iter_events())
    seed = sha256_hex(canonical_bytes({"semantic": semantic}))
    context_id = derive_spec_owner_context_id(
        actor_id=actor_id,
        operator_session_id=operator_session_id,
        recipient_id=recipient_id,
        purpose=purpose,
        scope=scope,
        application_version=application_version,
        valid_from=valid_from,
        expires_at=expires_at,
        retry_identity=retry_identity,
    )
    request_id = f"spec-context:{seed}"
    writer = CommandServiceContextWriter(
        command_service,
        actor_id=actor_id,
        authority_grant_id=authority_grant_id,
    )
    lifecycle = ContextLifecycleService(ObjectStore(operator.control_root), writer, writer_id="spec-owner-operated-v1")
    existing = tuple(writer.iter_events(context_id))
    if existing:
        compiled = lifecycle.recover_compiled(context_id)
        if compiled.request_id != request_id:
            raise IntegrityError("durable SPEC context retry identity differs")
        manifest = lifecycle.objects.read("context", compiled.manifest_object_id, 1)
        packet = lifecycle.objects.read("context", compiled.packet_object_id, compiled.revision)
        included = manifest.get("included") if isinstance(manifest, Mapping) else None
        if not isinstance(included, list) or len(included) != 1 or not isinstance(packet, Mapping):
            raise IntegrityError("durable SPEC context source identity is unavailable")
        row = included[0]
        rendered = packet.get("rendered_content")
        if not isinstance(row, Mapping) or not isinstance(rendered, str):
            raise IntegrityError("durable SPEC context source bytes are unavailable")
        durable_snapshot = SpecContextSnapshot(
            source=SourceFragment(
                source_id=str(row["source_id"]),
                revision=str(row["revision"]),
                authority_rank=100,
                mandatory=True,
                content=rendered,
                content_hash=str(row["content_hash"]),
            ),
            source_position=int(manifest["source_position"]),
            source_hash=str(manifest["source_hash"]),
            candidate_set_digest=str(manifest["candidate_set_digest"]),
        )
        try:
            source_value = json.loads(rendered)
            accepted_ids = {item["artefact_id"] for item in source_value["accepted_inputs"]}
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise IntegrityError("durable SPEC context source record is malformed") from exc
        source_position = durable_snapshot.source_position
        if source_position < 1 or source_position > len(events):
            raise IntegrityError("durable SPEC context source position is invalid")
        expected_snapshot = build_spec_context_snapshot(
            events[:source_position],
            schemas=operator.schemas,
            route_id="SPEC-GATE6-RUN-V1",
            required_spec_source_sha256=required_spec_source_sha256,
            authority_state_validator=operator.authority_resolver.validate_replayed_administration_state,
        )
        if durable_snapshot != expected_snapshot:
            raise IntegrityError("durable SPEC context source binding differs")
        snapshot = expected_snapshot
        for event in events[source_position:]:
            payload = event.get("payload")
            if (isinstance(payload, Mapping) and (payload.get("row_id") or payload.get("owner_row_id"))) or event.get(
                "stream_id"
            ) in accepted_ids:
                raise ArsError("Discovery replay or accepted source changed after SPEC context delivery")
    else:
        snapshot = build_spec_context_snapshot(
            events,
            schemas=operator.schemas,
            route_id="SPEC-GATE6-RUN-V1",
            required_spec_source_sha256=required_spec_source_sha256,
            authority_state_validator=operator.authority_resolver.validate_replayed_administration_state,
        )
        compiled = None
    source_resolver = DiscoveryReplaySourceResolver(snapshot)
    if compiled is None:
        compiled = lifecycle.compile_packet(
            request={
                "request_id": request_id,
                "context_id": context_id,
                "revision": 1,
                "project_id": operator.ledger.project_id,
                "task_id": _stable_id("tsk", f"{seed}:task"),
                "task_revision": 1,
                "purpose": purpose,
                "role": "operator",
                "risk": "R2",
                "actor_id": actor_id,
                "session_id": operator_session_id,
                "producing_attempt_id": None,
                "parent_context_id": None,
                "permitted_scopes": [scope],
                "control_store_identity": operator.ledger.store_identity,
                "source_position": snapshot.source_position,
                "source_hash": snapshot.source_hash,
                "compiler_version": "spec-owner-operated-v1",
                "policy_version": "spec-gate6-run-v1",
                "reference_profile": "spec-owner-operated",
                "reference_token_budget": 100000,
                "provider_tokenizer_id": None,
                "provider_token_count": None,
                "provider_upper_bound_id": None,
                "provider_upper_bound_count": None,
                "provider_usable_capacity": None,
                "provider_reserve": None,
                "candidate_set_digest": snapshot.candidate_set_digest,
                "retrieval_trace_refs": [],
                "confidence_summary": "exact accepted Discovery replay and brief inputs",
                "security_declaration": "no provider launch, credentials, transcript, or hidden reasoning",
                "independence_evidence_refs": [],
                "delivery_receipt_refs": [],
                "currency_triggers": ["discovery-ledger-tail"],
                "retention_class": "project",
                "sensitivity_class": "internal",
                "supersession_lineage": [],
                "cumulative_addendum_bytes": 0,
                "expires_at": None,
            },
            source_resolver=source_resolver,
            profile=ContextProfile("spec-owner-operated", 100000),
            reference_counter=ReferenceRegexV1(),
            required_source_ids={snapshot.source.source_id},
        )
    owner_types = {
        event.get("event_type")
        for event in writer.iter_events(compiled.context_id)
        if str(event.get("event_type", "")).startswith("OwnerOperatedContext")
    }
    if "OwnerOperatedContextHandoffValidated" not in owner_types:
        source_value = json.loads(snapshot.source.content)
        validated = lifecycle.prevalidate_owner_operated(
            compiled,
            capability=compiled.capability,
            operator_id=actor_id,
            operator_session_id=operator_session_id,
            recipient_id=recipient_id,
            purpose=purpose,
            scope=scope,
            accepted_artefacts=[
                {"artefact_id": item["artefact_id"], "content_sha256": item["content_sha256"]}
                for item in source_value["accepted_inputs"]
            ],
            application_version=application_version,
            valid_from=valid_from,
            expires_at=expires_at,
        )
    else:
        validated = lifecycle.recover_owner_operated_validated(compiled.context_id)
        profile = validated.profile.content
        expected = {
            "operator_id": actor_id,
            "operator_session_id": operator_session_id,
            "recipient_id": recipient_id,
            "purpose": purpose,
            "scope": scope,
            "context_id": compiled.context_id,
            "packet_sha256": compiled.packet_sha256,
        }
        if any(profile.get(key) != value for key, value in expected.items()):
            raise ArsError("owner-operated context retry changed the semantic handoff")
    owner_types = {event.get("event_type") for event in writer.iter_events(compiled.context_id)}
    if "OwnerOperatedContextHandoffIssued" not in owner_types:
        lifecycle.issue_owner_operated(validated)
    owner_types = {event.get("event_type") for event in writer.iter_events(compiled.context_id)}
    if "OwnerOperatedContextDelivered" not in owner_types:
        lifecycle.record_owner_operated_delivery(
            compiled,
            validated,
            recipient_id=recipient_id,
            recipient_session_id=operator_session_id,
        )
    return compiled, source_resolver


__all__ = [
    "DiscoveryReplaySourceResolver",
    "SpecContextSnapshot",
    "build_spec_context_snapshot",
    "deliver_spec_owner_context",
    "derive_spec_owner_context_id",
]
