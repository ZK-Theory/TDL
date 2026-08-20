"""Production W3 context-packet lifecycle over immutable objects and command writes."""

from __future__ import annotations

import secrets
import json
import hashlib
import uuid
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.context.compiler import _validate_provider_gate, compile_candidate
from research_system.context.models import ContextProfile
from research_system.context.sources import SourceResolver, resolve_sources
from research_system.errors import ArsError
from research_system.ids import new_id


class ContextObjectWriter(Protocol):
    def read(self, kind: str, object_id: str, revision: int) -> Any: ...

    def revision_exists(self, kind: str, object_id: str, revision: int) -> bool: ...

    def write(self, kind: str, object_id: str, revision: int, value: Any) -> Any: ...


class ContextCommandWriter(Protocol):
    """Adapter boundary implemented by the canonical command service."""

    def stream_version(self, context_id: str) -> int: ...

    def lifecycle_lock(self, context_id: str) -> AbstractContextManager[None]: ...

    def iter_events(self, context_id: str) -> Iterable[Mapping[str, Any]]: ...

    def submit_context(
        self,
        *,
        command_type: str,
        context_id: str,
        expected_stream_version: int,
        idempotency_key: str,
        payload: Mapping[str, Any],
    ) -> Any: ...


class ContextLifecycleFailure(ArsError):
    """A terminal lifecycle failure carrying its original durable receipt."""

    def __init__(self, message: str, receipt: Any, detail: Any = None) -> None:
        super().__init__(message)
        self.receipt = receipt
        self.detail = detail


@dataclass(frozen=True, slots=True)
class CompiledContextPacket:
    context_id: str
    request_id: str
    revision: int
    packet_object_id: str
    packet_sha256: str
    manifest_object_id: str
    manifest_sha256: str
    capability: "ContextLifecycleCapability"
    transition_receipts: Mapping[str, Any]

    @property
    def state(self) -> str:
        return "compiled"

    @property
    def context_candidate_id(self) -> str:
        return self.context_id

    @property
    def content_hash(self) -> str:
        return self.packet_sha256


@dataclass(frozen=True, slots=True, init=False)
class ContextLifecycleCapability:
    context_id: str
    request_id: str
    revision: int
    packet_sha256: str
    writer_id: str
    lifecycle_version: str
    digest: str
    _issuer_nonce: str

    def __init__(
        self,
        *,
        context_id: str,
        request_id: str,
        revision: int,
        packet_sha256: str,
        writer_id: str,
        lifecycle_version: str,
        issuer_nonce: str,
        mint_key: object,
    ) -> None:
        if mint_key is not _CAPABILITY_MINT_KEY:
            raise TypeError("context lifecycle capabilities are service-minted")
        content = {
            "context_id": context_id,
            "request_id": request_id,
            "revision": revision,
            "packet_sha256": packet_sha256,
            "writer_id": writer_id,
            "lifecycle_version": lifecycle_version,
            "issuer_nonce": issuer_nonce,
        }
        object.__setattr__(self, "context_id", context_id)
        object.__setattr__(self, "request_id", request_id)
        object.__setattr__(self, "revision", revision)
        object.__setattr__(self, "packet_sha256", packet_sha256)
        object.__setattr__(self, "writer_id", writer_id)
        object.__setattr__(self, "lifecycle_version", lifecycle_version)
        object.__setattr__(self, "digest", sha256_hex(canonical_bytes(content)))
        object.__setattr__(self, "_issuer_nonce", issuer_nonce)


@dataclass(frozen=True, slots=True, init=False)
class LifecycleBoundDispatch:
    """Service-sealed W4 result accepted by downstream issue boundaries."""

    attempt_id: str
    assurance_requirement_id: str
    assurance_requirement_hash: str
    context: CompiledContextPacket
    route: object
    provider_evidence_id: str
    provider_evidence_hash: str
    operational_evidence_id: str
    operational_evidence_hash: str
    expires_at: str
    capability_digest: str
    state: str
    _capability: ContextLifecycleCapability

    def __init__(
        self,
        *,
        attempt_id: str,
        assurance_requirement_id: str,
        assurance_requirement_hash: str,
        context: CompiledContextPacket,
        route: object,
        provider_evidence_id: str,
        provider_evidence_hash: str,
        operational_evidence_id: str,
        operational_evidence_hash: str,
        expires_at: str,
        capability: ContextLifecycleCapability,
        mint_key: object,
    ) -> None:
        if mint_key is not _DISPATCH_MINT_KEY:
            raise TypeError("lifecycle dispatches are service-sealed")
        values = {
            "attempt_id": attempt_id,
            "assurance_requirement_id": assurance_requirement_id,
            "assurance_requirement_hash": assurance_requirement_hash,
            "context": context,
            "route": route,
            "provider_evidence_id": provider_evidence_id,
            "provider_evidence_hash": provider_evidence_hash,
            "operational_evidence_id": operational_evidence_id,
            "operational_evidence_hash": operational_evidence_hash,
            "expires_at": expires_at,
            "capability_digest": capability.digest,
            "state": "unissued",
            "_capability": capability,
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)

    def verify_capability(self, capability: ContextLifecycleCapability) -> None:
        if capability is not self._capability or capability.digest != self.capability_digest:
            raise ArsError("context lifecycle capability is missing or forged")


@dataclass(frozen=True, slots=True, init=False)
class LifecycleIssuedDispatch:
    """Issued W3 packet plus the unchanged W7 template handed to W8."""

    dispatch: LifecycleBoundDispatch
    template: "PrevalidatedProviderCommandTemplate"
    capability_digest: str
    state: str
    _capability: ContextLifecycleCapability

    def __init__(
        self,
        *,
        dispatch: LifecycleBoundDispatch,
        template: "PrevalidatedProviderCommandTemplate",
        capability: ContextLifecycleCapability,
        mint_key: object,
    ) -> None:
        if mint_key is not _DISPATCH_MINT_KEY:
            raise TypeError("issued lifecycle dispatches are service-sealed")
        dispatch.verify_capability(capability)
        object.__setattr__(self, "dispatch", dispatch)
        object.__setattr__(self, "template", template)
        object.__setattr__(self, "capability_digest", capability.digest)
        object.__setattr__(self, "state", "issued")
        object.__setattr__(self, "_capability", capability)

    @property
    def context(self) -> CompiledContextPacket:
        return self.dispatch.context

    @property
    def attempt_id(self) -> str:
        return self.dispatch.attempt_id

    @property
    def route(self) -> object:
        return self.dispatch.route

    def verify_capability(self, capability: ContextLifecycleCapability) -> None:
        self.dispatch.verify_capability(capability)
        if capability is not self._capability:
            raise ArsError("context lifecycle capability is missing or forged")


@dataclass(frozen=True, slots=True)
class PrevalidatedProviderCommandTemplate:
    canonical_json: str
    sha256: str

    @classmethod
    def freeze(cls, content: Mapping[str, Any]) -> "PrevalidatedProviderCommandTemplate":
        frozen = canonical_bytes(dict(content))
        return cls(canonical_json=frozen.decode("utf-8"), sha256=sha256_hex(frozen))

    @property
    def content(self) -> Mapping[str, Any]:
        """Return a new mapping so callers cannot mutate the frozen preimage."""
        value = json.loads(self.canonical_json)
        assert isinstance(value, dict)
        return value


@dataclass(frozen=True, slots=True)
class ValidatedContextPacket:
    """Replay-recoverable authority needed to issue one validated packet."""

    context_id: str
    request_id: str
    revision: int
    packet_sha256: str
    manifest_sha256: str
    capability_digest: str
    template: PrevalidatedProviderCommandTemplate


@dataclass(frozen=True, slots=True)
class ValidatedOwnerOperatedContextPacket:
    """Replay-recoverable authority for a manual, provider-free handoff."""

    context_id: str
    request_id: str
    revision: int
    packet_sha256: str
    manifest_sha256: str
    capability_digest: str
    profile: PrevalidatedProviderCommandTemplate


_CAPABILITY_MINT_KEY = object()
_DISPATCH_MINT_KEY = object()
_LIFECYCLE_VERSION = "context-packet-v1"


def _receipt_status(receipt: Any) -> str | None:
    if isinstance(receipt, Mapping):
        value = receipt.get("status")
    else:
        value = getattr(receipt, "status", None)
    return value if isinstance(value, str) else None


def _require_accepted(receipt: Any, command_type: str) -> Any:
    if _receipt_status(receipt) not in {"accepted", "replayed"}:
        raise ArsError(f"{command_type} was not accepted")
    return receipt


def _stable_key(request_id: str, command_type: str) -> str:
    return f"context:{request_id}:{command_type}"


def _stable_context_id(seed: str) -> str:
    value = int.from_bytes(hashlib.sha256(seed.encode("utf-8")).digest()[:16], "big")
    value = (value & ~(0xF << 76)) | (0x7 << 76)
    value = (value & ~(0b11 << 62)) | (0b10 << 62)
    return f"ctx_{uuid.UUID(int=value)}"


def _compilation_failure_code(exc: Exception) -> str:
    message = str(exc)
    if "mandatory source omitted" in message:
        return "mandatory_source_missing"
    if "source hash mismatch" in message:
        return "source_hash_mismatch"
    if "unsafe" in message or "restricted" in message:
        return "unsafe_source"
    return "context_compilation_failed"


def _compilation_failure_message(code: object) -> str:
    return {
        "mandatory_source_missing": "mandatory source omitted",
        "source_hash_mismatch": "source hash mismatch",
        "unsafe_source": "unsafe or restricted source",
    }.get(str(code), "context compilation failed")


class ContextLifecycleService:
    """Own the linear W3 lifecycle; persistence is delegated to canonical stores."""

    def __init__(
        self,
        objects: ContextObjectWriter,
        commands: ContextCommandWriter,
        *,
        writer_id: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not writer_id:
            raise ValueError("writer_id must be non-empty")
        self.objects = objects
        self.commands = commands
        self.writer_id = writer_id
        self.clock = clock or (lambda: datetime.now(UTC))
        self._issuer_nonce = secrets.token_hex(32)

    def _submit(self, command_type: str, context_id: str, request_id: str, payload: Mapping[str, Any]) -> Any:
        idempotency_key = _stable_key(request_id, command_type)
        committed = tuple(
            event for event in self.commands.iter_events(context_id) if event.get("idempotency_key") == idempotency_key
        )
        if len(committed) > 1:
            raise ArsError("context transition idempotency key is not unique")
        if committed:
            stream_version = committed[0].get("stream_version")
            if not isinstance(stream_version, int) or isinstance(stream_version, bool) or stream_version < 1:
                raise ArsError("committed context transition stream version is invalid")
            expected = stream_version - 1
        else:
            expected = self.commands.stream_version(context_id)
        return _require_accepted(
            self.commands.submit_context(
                command_type=command_type,
                context_id=context_id,
                expected_stream_version=expected,
                idempotency_key=idempotency_key,
                payload=dict(payload),
            ),
            command_type,
        )

    def _clock_utc(self, boundary: str) -> datetime:
        observed_at = self.clock()
        if not isinstance(observed_at, datetime) or observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ArsError(f"{boundary} clock must be timezone-aware")
        return observed_at.astimezone(UTC)

    def _mint(self, context_id: str, request_id: str, revision: int, packet_sha256: str) -> ContextLifecycleCapability:
        return ContextLifecycleCapability(
            context_id=context_id,
            request_id=request_id,
            revision=revision,
            packet_sha256=packet_sha256,
            writer_id=self.writer_id,
            lifecycle_version=_LIFECYCLE_VERSION,
            issuer_nonce=self._issuer_nonce,
            mint_key=_CAPABILITY_MINT_KEY,
        )

    def verify_capability(
        self,
        capability: ContextLifecycleCapability,
        *,
        context_id: str,
        packet_sha256: str,
    ) -> None:
        if type(capability) is not ContextLifecycleCapability:
            raise ArsError("context lifecycle capability is missing or forged")
        expected = self._mint(
            capability.context_id,
            capability.request_id,
            capability.revision,
            capability.packet_sha256,
        )
        if (
            capability._issuer_nonce != self._issuer_nonce
            or capability.digest != expected.digest
            or capability.writer_id != self.writer_id
            or capability.context_id != context_id
            or capability.packet_sha256 != packet_sha256
        ):
            raise ArsError("context lifecycle capability is missing or forged")

    def plan_dispatch(
        self,
        *,
        task: Any,
        attempt_id: str,
        requirement: Any,
        compiled: CompiledContextPacket,
        capability: ContextLifecycleCapability,
        candidates: Any,
        provider_evidence: Any,
        operational_evidence: Any,
    ) -> LifecycleBoundDispatch | dict[str, Any]:
        """Run W4 only for a packet carrying this service's exact capability."""
        self.verify_capability(
            capability,
            context_id=compiled.context_id,
            packet_sha256=compiled.packet_sha256,
        )
        if compiled.capability is not capability:
            raise ArsError("context lifecycle capability is missing or forged")
        from research_system.routing.orchestrator import _plan_dispatch

        planned = _plan_dispatch(
            task,
            attempt_id,
            requirement,
            compiled,
            candidates,
            provider_evidence,
            operational_evidence,
        )
        if isinstance(planned, dict):
            receipt = self.fail(
                context_id=compiled.context_id,
                request_id=compiled.request_id,
                lifecycle_phase="compiled",
                failure_code="no_eligible_route",
                packet_revision=compiled.revision,
                packet_sha256=compiled.packet_sha256,
            )
            raise ContextLifecycleFailure("no eligible route", receipt, planned)
        return LifecycleBoundDispatch(
            attempt_id=planned.attempt_id,
            assurance_requirement_id=planned.assurance_requirement_id,
            assurance_requirement_hash=planned.assurance_requirement_hash,
            context=compiled,
            route=planned.route,
            provider_evidence_id=planned.provider_evidence_id,
            provider_evidence_hash=planned.provider_evidence_hash,
            operational_evidence_id=planned.operational_evidence_id,
            operational_evidence_hash=planned.operational_evidence_hash,
            expires_at=planned.expires_at,
            capability=capability,
            mint_key=_DISPATCH_MINT_KEY,
        )

    def validate_provider_capacity(
        self,
        compiled: CompiledContextPacket,
        *,
        capability: ContextLifecycleCapability,
        evidence: Any,
        usable_capacity_tokens: int,
    ) -> Any:
        """Apply the selected-route W7 capacity gate behind lifecycle authority."""
        self.verify_capability(
            capability,
            context_id=compiled.context_id,
            packet_sha256=compiled.packet_sha256,
        )
        if compiled.capability is not capability:
            raise ArsError("context lifecycle capability is missing or forged")
        return _validate_provider_gate(compiled, evidence, usable_capacity_tokens)

    def request(self, payload: Mapping[str, Any]) -> Any:
        """Submit the bounded request transition without performing source access."""
        value = dict(payload)
        return self._submit(
            "RequestContextPacket",
            str(value["context_id"]),
            str(value["request_id"]),
            value,
        )

    def begin_compilation(self, payload: Mapping[str, Any]) -> Any:
        """Submit the bounded compilation-start transition."""
        value = dict(payload)
        return self._submit(
            "BeginContextCompilation",
            str(value["context_id"]),
            str(value["request_id"]),
            value,
        )

    def complete_compilation(
        self,
        payload: Mapping[str, Any],
        *,
        packet: Mapping[str, Any],
        manifest: Mapping[str, Any],
    ) -> Any:
        """Write exact immutable objects, then submit the bounded completion."""
        value = dict(payload)
        packet_value = dict(packet)
        manifest_value = dict(manifest)
        context_id = str(value["context_id"])
        request_id = str(value["request_id"])
        packet_id = str(value["packet_object_id"])
        packet_revision = int(value["packet_revision"])
        manifest_id = str(value["manifest_object_id"])
        manifest_revision = int(value["manifest_revision"])
        try:
            packet_sha256 = sha256_hex(canonical_bytes(packet_value))
            manifest_sha256 = sha256_hex(canonical_bytes(manifest_value))
        except (TypeError, ValueError) as exc:
            raise ArsError("context completion objects are not canonical") from exc
        if (
            packet_value.get("context_id") != context_id
            or packet_value.get("request_id") != request_id
            or packet_value.get("revision") != packet_revision
            or packet_value.get("manifest_id") != manifest_id
            or manifest_value.get("context_id") != context_id
            or manifest_value.get("request_id") != request_id
            or manifest_value.get("packet_object_id") != packet_id
            or manifest_value.get("packet_revision") != packet_revision
            or packet_sha256 != value.get("packet_sha256")
            or manifest_sha256 != value.get("manifest_sha256")
        ):
            raise ArsError("context completion objects do not match the transition evidence")
        self.objects.write("context", packet_id, packet_revision, packet_value)
        self.objects.write("context", manifest_id, manifest_revision, manifest_value)
        return self._submit(
            "CompleteContextCompilation",
            context_id,
            request_id,
            value,
        )

    def prevalidate_and_issue_dispatch(
        self,
        dispatch: LifecycleBoundDispatch,
        *,
        capability: ContextLifecycleCapability,
        provider_count_evidence: Any,
        usable_capacity_tokens: int,
        w7_adapter: Any,
    ) -> LifecycleIssuedDispatch:
        """Bind selected-route W7 evidence and issue one immutable packet template."""
        validated = self.prevalidate_dispatch(
            dispatch,
            capability=capability,
            provider_count_evidence=provider_count_evidence,
            usable_capacity_tokens=usable_capacity_tokens,
            w7_adapter=w7_adapter,
        )
        self.issue(validated)
        return LifecycleIssuedDispatch(
            dispatch=dispatch,
            template=validated.template,
            capability=capability,
            mint_key=_DISPATCH_MINT_KEY,
        )

    def prevalidate_dispatch(
        self,
        dispatch: LifecycleBoundDispatch,
        *,
        capability: ContextLifecycleCapability,
        provider_count_evidence: Any,
        usable_capacity_tokens: int,
        w7_adapter: Any,
    ) -> ValidatedContextPacket:
        """Validate only a service-sealed W4 dispatch through selected-route W7."""
        if type(dispatch) is not LifecycleBoundDispatch:
            raise ArsError("lifecycle-bound dispatch is missing or forged")
        dispatch.verify_capability(capability)
        compiled = dispatch.context
        self.verify_capability(
            capability,
            context_id=compiled.context_id,
            packet_sha256=compiled.packet_sha256,
        )
        try:
            self.validate_provider_capacity(
                compiled,
                capability=capability,
                evidence=provider_count_evidence,
                usable_capacity_tokens=usable_capacity_tokens,
            )
            provider_evidence = w7_adapter.load_evidence(
                dispatch.provider_evidence_id,
                dispatch.provider_evidence_hash,
            )
            revalidated = w7_adapter.revalidate(
                dispatch.route,
                compiled,
                provider_evidence,
                capability,
            )
            provider_template = w7_adapter.build_prevalidated_template(
                dispatch,
                revalidated,
                provider_count_evidence,
                capability,
            )
            self._validate_prevalidated_template(
                compiled,
                dispatch,
                capability,
                provider_count_evidence,
                provider_template,
            )
        except Exception as exc:
            receipt = self.fail(
                context_id=compiled.context_id,
                request_id=compiled.request_id,
                lifecycle_phase="compiled",
                failure_code="selected_route_prevalidation_failed",
                packet_revision=compiled.revision,
                packet_sha256=compiled.packet_sha256,
            )
            raise ContextLifecycleFailure(str(exc), receipt) from exc
        validated = self._validated_packet(compiled, capability, provider_template)
        with self.commands.lifecycle_lock(compiled.context_id):
            self._submit_validation(
                validated,
                {
                    "route_decision_id": str(dispatch.route.get("request_id")),
                    "route_witness_sha256": dispatch.provider_evidence_hash,
                    "selected_route_evidence_sha256": dispatch.operational_evidence_hash,
                },
            )
        return validated

    def _validate_prevalidated_template(
        self,
        compiled: CompiledContextPacket,
        dispatch: LifecycleBoundDispatch,
        capability: ContextLifecycleCapability,
        provider_count_evidence: Any,
        value: Mapping[str, Any],
    ) -> None:
        from research_system.context.template import validate_wrapper_accounting

        required = {
            "operation",
            "provider",
            "model",
            "profile_id",
            "adapter_revision",
            "context_id",
            "context_revision",
            "packet_sha256",
            "rendered_payload_hash",
            "command_revision",
            "command_revision_hash",
            "idempotency_key",
            "timeout_s",
            "policy_hash",
            "parity_evidence_hash",
            "currentness_evidence_hash",
            "provider_count_evidence",
            "wrapper_accounting",
            "wrapper_accounting_sha256",
            "capability_digest",
        }
        if set(value) != required:
            raise ArsError("prevalidated provider template fields are incomplete")
        winner = dispatch.route.get("winner")
        if (
            value["context_id"] != compiled.context_id
            or value["context_revision"] != compiled.revision
            or value["packet_sha256"] != compiled.packet_sha256
            or value["capability_digest"] != capability.digest
            or winner is None
            or value["profile_id"] != winner.profile_id
        ):
            raise ArsError("prevalidated provider template identity mismatch")
        count_content = {
            "counter_id": provider_count_evidence.counter_id,
            "units": provider_count_evidence.units,
            "count": provider_count_evidence.count,
            "exact": provider_count_evidence.exact,
            "provider": provider_count_evidence.provider,
            "model": provider_count_evidence.model,
            "rendering_revision": provider_count_evidence.rendering_revision,
            "evidence_revision": provider_count_evidence.evidence_revision,
        }
        if value["provider_count_evidence"] != count_content:
            raise ArsError("provider count evidence changed during template construction")
        if value["provider"] != count_content["provider"] or value["model"] != count_content["model"]:
            raise ArsError("selected provider identity changed during template construction")
        accounting = value["wrapper_accounting"]
        validate_wrapper_accounting(accounting)
        if value["wrapper_accounting_sha256"] != sha256_hex(canonical_bytes(accounting)):
            raise ArsError("wrapper accounting bytes changed during template construction")
        canonical_bytes(dict(value))

    def compile_packet(
        self,
        *,
        request: Mapping[str, Any],
        source_resolver: SourceResolver,
        profile: ContextProfile,
        reference_counter: Any,
        required_source_ids: set[str],
        optional_source_ids: set[str] | None = None,
        omissions: Mapping[str, str] | None = None,
    ) -> CompiledContextPacket:
        """Write requested/compiling, immutable packet objects, then compiled."""
        request_payload = dict(request)
        request_id = str(request_payload["request_id"])
        context_id = str(request_payload.get("context_id") or new_id("context"))
        revision = int(request_payload.get("revision", 1))
        if revision < 1:
            raise ValueError("context revision must be positive")
        request_payload.update(
            {
                "context_id": context_id,
                "revision": revision,
                "required_source_ids": sorted(required_source_ids),
            }
        )
        prior_events = tuple(self.commands.iter_events(context_id))
        if prior_events:
            from research_system.context.registry import rebuild_context_lifecycle

            prior = rebuild_context_lifecycle(prior_events, context_id)
            if dict(prior.request) != request_payload:
                raise ArsError("context compilation retry changed the original request")
            if prior.state == "failed":
                if not isinstance(prior.terminal, Mapping):
                    raise ArsError("failed context lifecycle is missing terminal evidence")
                receipt = self._submit(
                    "FailContextPacket",
                    context_id,
                    request_id,
                    prior.terminal,
                )
                raise ContextLifecycleFailure(
                    _compilation_failure_message(prior.terminal.get("failure_code")),
                    receipt,
                )
            if prior.compilation is not None:
                if prior.state not in {"compiled", "validated", "issued", "delivered"}:
                    raise ArsError(f"context compilation is terminal in state {prior.state}")
                return self.recover_compiled(context_id)
        created_at = self._clock_utc("context compilation")
        request_receipt = self._submit("RequestContextPacket", context_id, request_id, request_payload)
        begin_receipt = self._submit(
            "BeginContextCompilation",
            context_id,
            request_id,
            {
                "context_id": context_id,
                "request_id": request_id,
                "revision": revision,
                "compiler_version": request_payload["compiler_version"],
                "policy_version": request_payload["policy_version"],
            },
        )
        try:
            fragments = resolve_sources(
                source_resolver,
                required_source_ids,
                optional_source_ids,
            )
            candidate = compile_candidate(
                fragments,
                profile,
                reference_counter,
                required_source_ids,
                optional_source_ids,
                omissions,
            )
            packet_object_id = new_id("context")
            manifest_object_id = new_id("context")
            packet = {
                "schema_id": "ars://context/context-packet",
                "schema_version": "1.0.0",
                "context_id": context_id,
                "request_id": request_id,
                "revision": revision,
                "manifest_id": manifest_object_id,
                "manifest_revision": 1,
                "rendered_content": candidate.rendered_content,
                "rendered_sha256": candidate.content_hash,
            }
            manifest = {
                **request_payload,
                "schema_id": "ars://context/context-manifest",
                "schema_version": "1.0.0",
                "manifest_id": manifest_object_id,
                "manifest_revision": 1,
                "packet_object_id": packet_object_id,
                "packet_revision": revision,
                "rendered_packet_sha256": candidate.content_hash,
                "utf8_bytes": candidate.utf8_bytes,
                "reference_token_count": candidate.reference_count,
                "reference_tokenizer_id": candidate.reference_counter_id,
                "included": list(candidate.source_manifest),
                "omissions": [
                    {"source_id": key, "reason": value} for key, value in sorted(candidate.omissions.items())
                ],
                "conflicts": list(candidate.conflicts),
                "freshness_verdict": "current",
                "created_at": created_at.isoformat().replace("+00:00", "Z"),
            }
            packet_sha256 = sha256_hex(canonical_bytes(packet))
            manifest_sha256 = sha256_hex(canonical_bytes(manifest))
            self.objects.write("context", packet_object_id, revision, packet)
            self.objects.write("context", manifest_object_id, 1, manifest)
            complete_receipt = self._submit(
                "CompleteContextCompilation",
                context_id,
                request_id,
                {
                    "context_id": context_id,
                    "request_id": request_id,
                    "packet_object_id": packet_object_id,
                    "packet_revision": revision,
                    "packet_sha256": packet_sha256,
                    "manifest_object_id": manifest_object_id,
                    "manifest_revision": 1,
                    "manifest_sha256": manifest_sha256,
                    "rendered_sha256": candidate.content_hash,
                },
            )
        except Exception as exc:
            try:
                return self.recover_compiled(context_id)
            except ArsError:
                pass
            failure_receipt = self._submit(
                "FailContextPacket",
                context_id,
                request_id,
                {
                    "context_id": context_id,
                    "request_id": request_id,
                    "lifecycle_phase": "compiling",
                    "failure_code": _compilation_failure_code(exc),
                    "packet_evidence_status": "absent_before_immutable_bytes",
                    "packet_revision": None,
                    "packet_sha256": None,
                },
            )
            raise ContextLifecycleFailure(str(exc), failure_receipt) from exc
        capability = self._mint(context_id, request_id, revision, packet_sha256)
        return CompiledContextPacket(
            context_id=context_id,
            request_id=request_id,
            revision=revision,
            packet_object_id=packet_object_id,
            packet_sha256=packet_sha256,
            manifest_object_id=manifest_object_id,
            manifest_sha256=manifest_sha256,
            capability=capability,
            transition_receipts=MappingProxyType(
                {
                    "RequestContextPacket": request_receipt,
                    "BeginContextCompilation": begin_receipt,
                    "CompleteContextCompilation": complete_receipt,
                }
            ),
        )

    def recover_compiled(self, context_id: str) -> CompiledContextPacket:
        """Rebuild exact compilation authority after a lost accepted response."""
        from research_system.context.registry import rebuild_context_lifecycle

        events = tuple(self.commands.iter_events(context_id))
        state = rebuild_context_lifecycle(events, context_id)
        if state.compilation is None or state.state not in {"compiled", "validated", "issued", "delivered"}:
            raise ArsError("context packet is not recoverable from compiled state")
        compilation = state.compilation
        packet_object_id = str(compilation["packet_object_id"])
        packet_revision = int(compilation["packet_revision"])
        packet_sha256 = str(compilation["packet_sha256"])
        manifest_object_id = str(compilation["manifest_object_id"])
        manifest_revision = int(compilation["manifest_revision"])
        manifest_sha256 = str(compilation["manifest_sha256"])
        packet = self.objects.read("context", packet_object_id, packet_revision)
        manifest = self.objects.read("context", manifest_object_id, manifest_revision)
        if not isinstance(packet, Mapping) or not isinstance(manifest, Mapping):
            raise ArsError("compiled context packet objects are unavailable")
        if (
            sha256_hex(canonical_bytes(dict(packet))) != packet_sha256
            or sha256_hex(canonical_bytes(dict(manifest))) != manifest_sha256
        ):
            raise ArsError("compiled context packet object bytes changed")
        request_id = str(state.request["request_id"])
        if (
            packet.get("context_id") != context_id
            or packet.get("request_id") != request_id
            or packet.get("revision") != packet_revision
            or packet.get("manifest_id") != manifest_object_id
            or manifest.get("context_id") != context_id
            or manifest.get("request_id") != request_id
            or manifest.get("packet_object_id") != packet_object_id
            or manifest.get("packet_revision") != packet_revision
            or manifest.get("rendered_packet_sha256") != packet.get("rendered_sha256")
        ):
            raise ArsError("compiled context packet object identities changed")
        capability = self._mint(context_id, request_id, packet_revision, packet_sha256)
        started = next(
            (event.get("payload") for event in events if event.get("event_type") == "ContextCompilationStarted"),
            None,
        )
        if not isinstance(started, Mapping):
            raise ArsError("context compilation start evidence is unavailable")
        transition_receipts = MappingProxyType(
            {
                "RequestContextPacket": self._submit("RequestContextPacket", context_id, request_id, state.request),
                "BeginContextCompilation": self._submit("BeginContextCompilation", context_id, request_id, started),
                "CompleteContextCompilation": self._submit(
                    "CompleteContextCompilation", context_id, request_id, compilation
                ),
            }
        )
        return CompiledContextPacket(
            context_id=context_id,
            request_id=request_id,
            revision=packet_revision,
            packet_object_id=packet_object_id,
            packet_sha256=packet_sha256,
            manifest_object_id=manifest_object_id,
            manifest_sha256=manifest_sha256,
            capability=capability,
            transition_receipts=transition_receipts,
        )

    def _validated_packet(
        self,
        compiled: CompiledContextPacket,
        capability: ContextLifecycleCapability,
        provider_template: Mapping[str, Any],
    ) -> ValidatedContextPacket:
        return ValidatedContextPacket(
            context_id=compiled.context_id,
            request_id=compiled.request_id,
            revision=compiled.revision,
            packet_sha256=compiled.packet_sha256,
            manifest_sha256=compiled.manifest_sha256,
            capability_digest=capability.digest,
            template=PrevalidatedProviderCommandTemplate.freeze(provider_template),
        )

    def _submit_validation(
        self,
        validated: ValidatedContextPacket,
        evidence: Mapping[str, Any],
    ) -> Any:
        return self._submit(
            "ValidateContextPacket",
            validated.context_id,
            validated.request_id,
            {
                "context_id": validated.context_id,
                "request_id": validated.request_id,
                "packet_revision": validated.revision,
                "packet_sha256": validated.packet_sha256,
                "capability_digest": validated.capability_digest,
                "provider_template": dict(validated.template.content),
                "provider_template_sha256": validated.template.sha256,
                **dict(evidence),
            },
        )

    def _submit_issue(self, validated: ValidatedContextPacket) -> Any:
        return self._submit(
            "IssueContextPacket",
            validated.context_id,
            validated.request_id,
            {
                "context_id": validated.context_id,
                "request_id": validated.request_id,
                "packet_revision": validated.revision,
                "packet_sha256": validated.packet_sha256,
                "manifest_sha256": validated.manifest_sha256,
                "capability_digest": validated.capability_digest,
                "provider_template_sha256": validated.template.sha256,
            },
        )

    @staticmethod
    def _owner_window(profile: Mapping[str, Any]) -> tuple[datetime, datetime]:
        valid_from = profile.get("valid_from")
        expires_at = profile.get("expires_at")
        if not isinstance(valid_from, str) or not isinstance(expires_at, str):
            raise ArsError("owner-operated handoff window is invalid")
        try:
            starts = datetime.fromisoformat(valid_from.replace("Z", "+00:00"))
            expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ArsError("owner-operated handoff window is invalid") from exc
        if not valid_from.endswith("Z") or not expires_at.endswith("Z") or starts >= expires:
            raise ArsError("owner-operated handoff window must be finite and increasing")
        return starts.astimezone(UTC), expires.astimezone(UTC)

    def _require_current_owner_window(self, profile: Mapping[str, Any]) -> datetime:
        observed_at = self._clock_utc("owner-operated handoff")
        starts, expires = self._owner_window(profile)
        if not starts <= observed_at < expires:
            raise ArsError("owner-operated delivery is outside its finite window")
        return observed_at

    @classmethod
    def _owner_receipt_time(cls, receipt: Mapping[str, Any], profile: Mapping[str, Any]) -> datetime:
        delivered_at = receipt.get("delivered_at")
        if not isinstance(delivered_at, str) or not delivered_at.endswith("Z"):
            raise ArsError("owner-operated delivery receipt time is invalid")
        try:
            observed_at = datetime.fromisoformat(delivered_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ArsError("owner-operated delivery receipt time is invalid") from exc
        starts, expires = cls._owner_window(profile)
        if observed_at.tzinfo != UTC or not starts <= observed_at < expires:
            raise ArsError("owner-operated delivery receipt is outside its finite window")
        return observed_at

    def prevalidate_owner_operated(
        self,
        compiled: CompiledContextPacket,
        *,
        capability: ContextLifecycleCapability,
        operator_id: str,
        operator_session_id: str,
        recipient_id: str,
        purpose: str,
        scope: str,
        accepted_artefacts: Sequence[Mapping[str, str]],
        application_version: str,
        valid_from: str,
        expires_at: str,
    ) -> ValidatedOwnerOperatedContextPacket:
        """Validate one explicit manual Codex Desktop handoff without W4/W7 claims."""
        self.verify_capability(capability, context_id=compiled.context_id, packet_sha256=compiled.packet_sha256)
        if compiled.capability is not capability:
            raise ArsError("context lifecycle capability is missing or forged")
        if not all(
            (
                operator_id,
                operator_session_id,
                recipient_id,
                purpose,
                scope,
                application_version,
                valid_from,
                expires_at,
            )
        ):
            raise ArsError("owner-operated handoff identities must be explicit")
        self._owner_window({"valid_from": valid_from, "expires_at": expires_at})
        artefact_ids: set[str] = set()
        for accepted in accepted_artefacts:
            artefact_id = accepted.get("artefact_id")
            content_sha256 = accepted.get("content_sha256")
            if not isinstance(artefact_id, str) or not isinstance(content_sha256, str):
                raise ArsError("accepted owner-operated artefact identity is invalid")
            if artefact_id in artefact_ids:
                raise ArsError("accepted owner-operated artefact IDs must be unique")
            artefact_ids.add(artefact_id)
        profile_value = {
            "schema_id": "ars://context/owner-operated-delivery-profile",
            "schema_version": "1.0.0",
            "delivery_mode": "manual_codex_desktop",
            "application": "Codex Desktop",
            "application_version": application_version,
            "provider_launch": False,
            "operator_id": operator_id,
            "operator_session_id": operator_session_id,
            "recipient_id": recipient_id,
            "purpose": purpose,
            "scope": scope,
            "context_id": compiled.context_id,
            "packet_revision": compiled.revision,
            "packet_sha256": compiled.packet_sha256,
            "capability_digest": capability.digest,
            "valid_from": valid_from,
            "expires_at": expires_at,
        }
        profile = PrevalidatedProviderCommandTemplate.freeze(profile_value)
        validated = ValidatedOwnerOperatedContextPacket(
            context_id=compiled.context_id,
            request_id=compiled.request_id,
            revision=compiled.revision,
            packet_sha256=compiled.packet_sha256,
            manifest_sha256=compiled.manifest_sha256,
            capability_digest=capability.digest,
            profile=profile,
        )
        binding = {
            "context_id": compiled.context_id,
            "request_id": compiled.request_id,
            "packet_revision": compiled.revision,
            "packet_sha256": compiled.packet_sha256,
            "manifest_sha256": compiled.manifest_sha256,
            "owner_profile_sha256": profile.sha256,
        }
        with self.commands.lifecycle_lock(compiled.context_id):
            prepare_payload = {
                **binding,
                "owner_profile": dict(profile.content),
                "accepted_artefacts": [dict(item) for item in accepted_artefacts],
            }
            existing_types = {event.get("event_type") for event in self.commands.iter_events(compiled.context_id)}
            if "OwnerOperatedContextHandoffPrepared" not in existing_types:
                self._require_current_owner_window(profile.content)
                self._submit(
                    "PrepareOwnerOperatedContextHandoff",
                    compiled.context_id,
                    compiled.request_id,
                    prepare_payload,
                )
            prepared = self._owner_event(compiled.context_id, "OwnerOperatedContextHandoffPrepared")
            if prepared.get("payload") != prepare_payload:
                raise ArsError("owner-operated handoff retry changed the prepared profile")
            if "OwnerOperatedContextHandoffValidated" not in existing_types:
                self._require_current_owner_window(profile.content)
                self._submit(
                    "ValidateOwnerOperatedContextHandoff",
                    compiled.context_id,
                    compiled.request_id,
                    {
                        **binding,
                        "prepared_event_id": prepared["event_id"],
                        "prepared_event_sha256": prepared["event_hash"],
                    },
                )
            if self.recover_owner_operated_validated(compiled.context_id) != validated:
                raise ArsError("validated owner-operated context recovery identity changed")
        return validated

    def issue_owner_operated(self, validated: ValidatedOwnerOperatedContextPacket) -> Any:
        """Issue only an exact replayed manual-handoff profile; never launch a provider."""
        with self.commands.lifecycle_lock(validated.context_id):
            state = self.recover_owner_operated_validated(validated.context_id)
            if state != validated:
                raise ArsError("validated owner-operated context recovery identity changed")
            validation = self._owner_event(validated.context_id, "OwnerOperatedContextHandoffValidated")
            issued = tuple(
                event
                for event in self.commands.iter_events(validated.context_id)
                if event.get("event_type") == "OwnerOperatedContextHandoffIssued"
            )
            if len(issued) > 1:
                raise ArsError("owner-operated issuance event is not unique")
            if not issued:
                self._require_current_owner_window(validated.profile.content)
            return self._submit(
                "IssueOwnerOperatedContextHandoff",
                validated.context_id,
                validated.request_id,
                {
                    "context_id": validated.context_id,
                    "request_id": validated.request_id,
                    "packet_revision": validated.revision,
                    "packet_sha256": validated.packet_sha256,
                    "manifest_sha256": validated.manifest_sha256,
                    "owner_profile_sha256": validated.profile.sha256,
                    "validation_event_id": validation["event_id"],
                    "validation_event_sha256": validation["event_hash"],
                },
            )

    def recover_owner_operated_validated(self, context_id: str) -> ValidatedOwnerOperatedContextPacket:
        from research_system.context.registry import rebuild_context_lifecycle

        state = rebuild_context_lifecycle(self.commands.iter_events(context_id), context_id)
        if state.state != "compiled" or state.compilation is None:
            raise ArsError("owner-operated context packet is not recoverable from validated state")
        prepared = self._owner_event(context_id, "OwnerOperatedContextHandoffPrepared")
        self._owner_event(context_id, "OwnerOperatedContextHandoffValidated")
        value = prepared.get("payload", {}).get("owner_profile")
        if not isinstance(value, Mapping):
            raise ArsError("owner-operated delivery profile is missing")
        profile = PrevalidatedProviderCommandTemplate.freeze(value)
        if (
            profile.sha256 != prepared.get("payload", {}).get("owner_profile_sha256")
            or value.get("provider_launch") is not False
        ):
            raise ArsError("owner-operated delivery profile bytes changed")
        compilation = state.compilation
        packet = self.objects.read("context", str(compilation["packet_object_id"]), int(compilation["packet_revision"]))
        manifest = self.objects.read(
            "context", str(compilation["manifest_object_id"]), int(compilation["manifest_revision"])
        )
        if sha256_hex(canonical_bytes(packet)) != compilation.get("packet_sha256") or sha256_hex(
            canonical_bytes(manifest)
        ) != compilation.get("manifest_sha256"):
            raise ArsError("owner-operated context packet object bytes changed")
        return ValidatedOwnerOperatedContextPacket(
            context_id=context_id,
            request_id=str(state.request["request_id"]),
            revision=int(compilation["packet_revision"]),
            packet_sha256=str(compilation["packet_sha256"]),
            manifest_sha256=str(compilation["manifest_sha256"]),
            capability_digest=str(value["capability_digest"]),
            profile=profile,
        )

    def _owner_event(self, context_id: str, event_type: str) -> Mapping[str, Any]:
        matches = [event for event in self.commands.iter_events(context_id) if event.get("event_type") == event_type]
        if len(matches) != 1:
            raise ArsError(f"owner-operated lifecycle event is unavailable: {event_type}")
        return matches[0]

    def recover_validated(self, context_id: str) -> ValidatedContextPacket:
        """Rebuild exact issue authority from verified lifecycle and object bytes."""
        from research_system.context.registry import rebuild_context_lifecycle

        state = rebuild_context_lifecycle(self.commands.iter_events(context_id), context_id)
        if state.state != "validated" or state.compilation is None or state.validation is None:
            raise ArsError("context packet is not recoverable from validated state")
        compilation = state.compilation
        validation = state.validation
        packet = self.objects.read(
            "context",
            str(compilation["packet_object_id"]),
            int(compilation["packet_revision"]),
        )
        manifest = self.objects.read(
            "context",
            str(compilation["manifest_object_id"]),
            int(compilation["manifest_revision"]),
        )
        if sha256_hex(canonical_bytes(packet)) != compilation.get("packet_sha256") or sha256_hex(
            canonical_bytes(manifest)
        ) != compilation.get("manifest_sha256"):
            raise ArsError("validated context packet object bytes changed")
        template_value = validation.get("provider_template")
        if not isinstance(template_value, Mapping):
            raise ArsError("validated provider template is missing")
        template = PrevalidatedProviderCommandTemplate.freeze(template_value)
        if template.sha256 != validation.get("provider_template_sha256"):
            raise ArsError("validated provider template bytes changed")
        return ValidatedContextPacket(
            context_id=context_id,
            request_id=str(state.request["request_id"]),
            revision=int(compilation["packet_revision"]),
            packet_sha256=str(compilation["packet_sha256"]),
            manifest_sha256=str(compilation["manifest_sha256"]),
            capability_digest=str(validation["capability_digest"]),
            template=template,
        )

    def issue(self, validated: ValidatedContextPacket) -> PrevalidatedProviderCommandTemplate:
        """Issue only the exact replay-recovered validated packet."""
        with self.commands.lifecycle_lock(validated.context_id):
            if self.recover_validated(validated.context_id) != validated:
                raise ArsError("validated context recovery identity changed")
            self._submit_issue(validated)
        return validated.template

    def record_delivery(
        self,
        compiled: CompiledContextPacket,
        *,
        recipient_id: str,
        recipient_session_id: str,
        adapter_id: str,
        delivered_sha256: str,
    ) -> Any:
        if delivered_sha256 != compiled.packet_sha256:
            raise ArsError("delivery hash does not match issued packet bytes")
        delivered_at = self._clock_utc("context delivery")
        delivery_receipt_id = new_id("context")
        delivery_receipt = {
            "schema_id": "ars://context/context-delivery-receipt",
            "schema_version": "1.0.0",
            "delivery_receipt_id": delivery_receipt_id,
            "context_id": compiled.context_id,
            "packet_revision": compiled.revision,
            "packet_sha256": compiled.packet_sha256,
            "recipient_id": recipient_id,
            "recipient_session_id": recipient_session_id,
            "adapter_id": adapter_id,
            "delivered_at": delivered_at.isoformat().replace("+00:00", "Z"),
        }
        delivery_receipt_sha256 = sha256_hex(canonical_bytes(delivery_receipt))
        self.objects.write("context", delivery_receipt_id, 1, delivery_receipt)
        return self._submit(
            "RecordContextDelivery",
            compiled.context_id,
            compiled.request_id,
            {
                "context_id": compiled.context_id,
                "request_id": compiled.request_id,
                "packet_revision": compiled.revision,
                "packet_sha256": compiled.packet_sha256,
                "recipient_id": recipient_id,
                "recipient_session_id": recipient_session_id,
                "adapter_id": adapter_id,
                "delivery_receipt_object_id": delivery_receipt_id,
                "delivery_receipt_revision": 1,
                "delivery_receipt_sha256": delivery_receipt_sha256,
            },
        )

    def record_owner_operated_delivery(
        self,
        compiled: CompiledContextPacket,
        validated: ValidatedOwnerOperatedContextPacket,
        *,
        recipient_id: str,
        recipient_session_id: str,
    ) -> Any:
        """Record manual receipt evidence without an adapter, transport, or provider claim."""
        with self.commands.lifecycle_lock(compiled.context_id):
            delivered = [
                event
                for event in self.commands.iter_events(compiled.context_id)
                if event.get("event_type") == "OwnerOperatedContextDelivered"
            ]
            if delivered:
                if len(delivered) != 1:
                    raise ArsError("owner-operated delivery event is not unique")
                prior = delivered[0].get("payload")
                if (
                    not isinstance(prior, Mapping)
                    or prior.get("recipient_id") != recipient_id
                    or prior.get("recipient_session_id") != recipient_session_id
                    or prior.get("packet_sha256") != compiled.packet_sha256
                    or prior.get("owner_profile_sha256") != validated.profile.sha256
                ):
                    raise ArsError("owner-operated delivery retry changed the durable handoff")
                receipt_object_id = prior.get("delivery_receipt_object_id")
                receipt_revision = prior.get("delivery_receipt_revision")
                if not isinstance(receipt_object_id, str) or type(receipt_revision) is not int:
                    raise ArsError("owner-operated delivery receipt identity is invalid")
                receipt = self.objects.read(
                    "context",
                    receipt_object_id,
                    receipt_revision,
                )
                if (
                    not isinstance(receipt, Mapping)
                    or sha256_hex(canonical_bytes(receipt)) != prior.get("delivery_receipt_sha256")
                    or receipt.get("owner_profile_sha256") != validated.profile.sha256
                    or receipt.get("recipient_id") != recipient_id
                    or receipt.get("recipient_session_id") != recipient_session_id
                ):
                    raise ArsError("owner-operated delivery receipt changed after commitment")
                self._owner_receipt_time(receipt, validated.profile.content)
                return self._submit(
                    "RecordOwnerOperatedContextDelivery", compiled.context_id, compiled.request_id, prior
                )
            if self.recover_owner_operated_validated(compiled.context_id) != validated:
                raise ArsError("validated owner-operated context recovery identity changed")
            issuance = self._owner_event(compiled.context_id, "OwnerOperatedContextHandoffIssued")
            if validated.packet_sha256 != compiled.packet_sha256:
                raise ArsError("owner-operated delivery packet identity differs")
            profile = validated.profile.content
            if (
                profile.get("provider_launch") is not False
                or profile.get("recipient_id") != recipient_id
                or profile.get("operator_session_id") != recipient_session_id
            ):
                raise ArsError("owner-operated delivery semantic identity differs")
            receipt_id = _stable_context_id(
                f"{compiled.request_id}:{compiled.packet_sha256}:{recipient_id}:{recipient_session_id}:owner-operated"
            )
            receipt_identity = {
                "schema_id": "ars://wp6-6/owner-operated-context-delivery-receipt",
                "schema_version": "1.0.0",
                "delivery_receipt_id": receipt_id,
                "context_id": compiled.context_id,
                "packet_revision": compiled.revision,
                "packet_sha256": compiled.packet_sha256,
                "owner_profile_sha256": validated.profile.sha256,
                "recipient_id": recipient_id,
                "recipient_session_id": recipient_session_id,
                "provider_launch": False,
            }
            if self.objects.revision_exists("context", receipt_id, 1):
                receipt = self.objects.read("context", receipt_id, 1)
                if not isinstance(receipt, Mapping) or any(
                    receipt.get(field) != expected for field, expected in receipt_identity.items()
                ):
                    raise ArsError("owner-operated delivery receipt conflicts with the durable handoff")
                self._owner_receipt_time(receipt, profile)
            else:
                delivered_at = self._require_current_owner_window(profile)
                receipt = {
                    **receipt_identity,
                    "delivered_at": delivered_at.isoformat().replace("+00:00", "Z"),
                }
            receipt_sha256 = sha256_hex(canonical_bytes(receipt))
            if not self.objects.revision_exists("context", receipt_id, 1):
                self.objects.write("context", receipt_id, 1, receipt)
            return self._submit(
                "RecordOwnerOperatedContextDelivery",
                compiled.context_id,
                compiled.request_id,
                {
                    "context_id": compiled.context_id,
                    "request_id": compiled.request_id,
                    "packet_revision": compiled.revision,
                    "packet_sha256": compiled.packet_sha256,
                    "manifest_sha256": compiled.manifest_sha256,
                    "owner_profile_sha256": validated.profile.sha256,
                    "issuance_event_id": issuance["event_id"],
                    "issuance_event_sha256": issuance["event_hash"],
                    "recipient_id": recipient_id,
                    "recipient_session_id": recipient_session_id,
                    "delivery_receipt_object_id": receipt_id,
                    "delivery_receipt_revision": 1,
                    "delivery_receipt_sha256": receipt_sha256,
                },
            )

    def fail(
        self,
        *,
        context_id: str,
        request_id: str,
        lifecycle_phase: str,
        failure_code: str,
        packet_revision: int | None = None,
        packet_sha256: str | None = None,
    ) -> Any:
        if lifecycle_phase not in {"requested", "compiling", "compiled"}:
            raise ValueError("failure phase must be requested, compiling, or compiled")
        present = lifecycle_phase == "compiled"
        if present != (packet_revision is not None and packet_sha256 is not None):
            raise ValueError("failure packet evidence does not match the lifecycle phase")
        return self._submit(
            "FailContextPacket",
            context_id,
            request_id,
            {
                "context_id": context_id,
                "request_id": request_id,
                "lifecycle_phase": lifecycle_phase,
                "failure_code": failure_code,
                "packet_evidence_status": ("present" if present else "absent_before_immutable_bytes"),
                "packet_revision": packet_revision,
                "packet_sha256": packet_sha256,
            },
        )

    def expire(self, compiled: CompiledContextPacket, reason: str) -> Any:
        return self._submit(
            "ExpireContextPacket",
            compiled.context_id,
            compiled.request_id,
            {
                "context_id": compiled.context_id,
                "request_id": compiled.request_id,
                "packet_revision": compiled.revision,
                "packet_sha256": compiled.packet_sha256,
                "reason": reason,
            },
        )

    def supersede(
        self,
        compiled: CompiledContextPacket,
        *,
        replacement_context_id: str,
        replacement_packet_sha256: str,
        reason: str,
    ) -> Any:
        return self._submit(
            "SupersedeContextPacket",
            compiled.context_id,
            compiled.request_id,
            {
                "context_id": compiled.context_id,
                "request_id": compiled.request_id,
                "packet_revision": compiled.revision,
                "packet_sha256": compiled.packet_sha256,
                "replacement_context_id": replacement_context_id,
                "replacement_packet_sha256": replacement_packet_sha256,
                "reason": reason,
            },
        )
