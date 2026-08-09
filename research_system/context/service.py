"""Production W3 context-packet lifecycle over immutable objects and command writes."""

from __future__ import annotations

import secrets
import json
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Iterable, Mapping, Protocol

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.context.compiler import compile_candidate
from research_system.context.models import ContextProfile, SourceFragment
from research_system.errors import ArsError
from research_system.ids import new_id


class ContextObjectWriter(Protocol):
    def read(self, kind: str, object_id: str, revision: int) -> Any: ...

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


_CAPABILITY_MINT_KEY = object()
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

    def compile_packet(
        self,
        *,
        request: Mapping[str, Any],
        fragments: Iterable[SourceFragment],
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
            if prior.compilation is not None:
                if prior.state not in {"compiled", "validated", "issued", "delivered"}:
                    raise ArsError(f"context compilation is terminal in state {prior.state}")
                return self.recover_compiled(context_id)
        self._submit("RequestContextPacket", context_id, request_id, request_payload)
        self._submit(
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
                "created_at": self.clock().astimezone(UTC).isoformat().replace("+00:00", "Z"),
            }
            packet_sha256 = sha256_hex(canonical_bytes(packet))
            manifest_sha256 = sha256_hex(canonical_bytes(manifest))
            self.objects.write("context", packet_object_id, revision, packet)
            self.objects.write("context", manifest_object_id, 1, manifest)
            self._submit(
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
        except Exception:
            try:
                return self.recover_compiled(context_id)
            except ArsError:
                pass
            self._submit(
                "FailContextPacket",
                context_id,
                request_id,
                {
                    "context_id": context_id,
                    "request_id": request_id,
                    "lifecycle_phase": "compiling",
                    "failure_code": "context_compilation_failed",
                    "packet_evidence_status": "absent_before_immutable_bytes",
                    "packet_revision": None,
                    "packet_sha256": None,
                },
            )
            raise
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
        )

    def recover_compiled(self, context_id: str) -> CompiledContextPacket:
        """Rebuild exact compilation authority after a lost accepted response."""
        from research_system.context.registry import rebuild_context_lifecycle

        state = rebuild_context_lifecycle(self.commands.iter_events(context_id), context_id)
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
        return CompiledContextPacket(
            context_id=context_id,
            request_id=request_id,
            revision=packet_revision,
            packet_object_id=packet_object_id,
            packet_sha256=packet_sha256,
            manifest_object_id=manifest_object_id,
            manifest_sha256=manifest_sha256,
            capability=capability,
        )

    def validate_and_issue(
        self,
        compiled: CompiledContextPacket,
        *,
        capability: ContextLifecycleCapability,
        validation_evidence: Mapping[str, Any],
        provider_template: Mapping[str, Any],
    ) -> PrevalidatedProviderCommandTemplate:
        """Freeze validation evidence and issue without releasing the writer lock."""
        self.verify_capability(
            capability,
            context_id=compiled.context_id,
            packet_sha256=compiled.packet_sha256,
        )
        validated = self._validated_packet(compiled, capability, provider_template)
        with self.commands.lifecycle_lock(compiled.context_id):
            self._submit_validation(validated, validation_evidence)
            self._submit_issue(validated)
        return validated.template

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

    def validate(
        self,
        compiled: CompiledContextPacket,
        *,
        capability: ContextLifecycleCapability,
        validation_evidence: Mapping[str, Any],
        provider_template: Mapping[str, Any],
    ) -> ValidatedContextPacket:
        """Persist validation separately so issue can recover after restart."""
        self.verify_capability(
            capability,
            context_id=compiled.context_id,
            packet_sha256=compiled.packet_sha256,
        )
        validated = self._validated_packet(compiled, capability, provider_template)
        with self.commands.lifecycle_lock(compiled.context_id):
            self._submit_validation(validated, validation_evidence)
        return validated

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
            "delivered_at": self.clock().astimezone(UTC).isoformat().replace("+00:00", "Z"),
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
