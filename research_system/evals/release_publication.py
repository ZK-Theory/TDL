"""Canonical publication of an already-derived blocked release decision."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError
from research_system.ids import validate_id
from research_system.schema_registry import SchemaRegistry
from research_system.store.objects import ObjectStore


_REQUEST_FIELDS = frozenset(
    {
        "schema",
        "project_id",
        "release_decision_id",
        "evaluation_runs_manifest_ref",
        "control_binding_ref",
        "publication_authority_grant_id",
        "publication_authority_sha256",
        "idempotency_key",
    }
)


@dataclass(frozen=True, slots=True)
class ReleasePublicationRequest:
    """Strict non-secret reference request accepted by CommandService."""

    schema: str
    project_id: str
    release_decision_id: str
    evaluation_runs_manifest_ref: str
    control_binding_ref: str
    publication_authority_grant_id: str
    publication_authority_sha256: str
    idempotency_key: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ReleasePublicationRequest:
        if set(value) != _REQUEST_FIELDS:
            raise ValueError("release publication request fields must be exact")
        request = cls(**value)
        if request.schema != "ars://evals/release-publication-request":
            raise ValueError("release publication request schema mismatch")
        validate_id(request.project_id, "project")
        validate_id(request.release_decision_id, "release_gate_decision")
        validate_id(request.evaluation_runs_manifest_ref, "artefact")
        validate_id(request.control_binding_ref, "artefact")
        validate_id(request.publication_authority_grant_id, "authority_grant")
        if (
            len(request.publication_authority_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in request.publication_authority_sha256
            )
        ):
            raise ValueError("publication authority hash must be lowercase SHA-256")
        if not request.idempotency_key.startswith("release-publication:"):
            raise ValueError("release publication idempotency key is invalid")
        return request

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PublicationEvidenceError(ArsError):
    """A bounded publication-evidence failure suitable for a rejected receipt."""


class ReleasePublicationAuthorizer(Protocol):
    """Fail-closed authority seam; implementations resolve but never create grants."""

    def resolve(
        self,
        grant_id: str,
        actor_id: str,
        command_type: str,
        project_id: str,
        subject_kind: str,
        subject_id: str,
        now: Any,
    ) -> Any: ...


class ReleasePublicationEvidenceResolver(Protocol):
    """Resolve and independently re-derive publication evidence."""

    @property
    def expected_store_identity(self) -> str: ...

    def resolve_evaluation_runs(self, reference: str) -> dict[str, Any]: ...

    def resolve_control_binding(self, reference: str) -> dict[str, Any]: ...

    def rederive_release_decision(
        self,
        manifest: dict[str, Any],
        control_binding: dict[str, Any],
    ) -> tuple[dict[str, Any], object]: ...


@dataclass(frozen=True, slots=True)
class BoundReleasePublicationEvidence:
    """Narrow injected evidence binding used by the offline publication seam."""

    evaluation_runs_manifest_ref: str
    evaluation_runs_manifest: dict[str, Any]
    control_binding_ref: str
    control_binding: dict[str, Any]
    expected_store_identity: str
    rederive: Callable[
        [dict[str, Any], dict[str, Any]],
        tuple[dict[str, Any], object],
    ]
    _manifest_bytes: bytes = field(init=False, repr=False)
    _control_bytes: bytes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_manifest_bytes",
            canonical_bytes(self.evaluation_runs_manifest),
        )
        object.__setattr__(
            self,
            "_control_bytes",
            canonical_bytes(self.control_binding),
        )

    def resolve_evaluation_runs(self, reference: str) -> dict[str, Any]:
        if reference != self.evaluation_runs_manifest_ref:
            raise PublicationEvidenceError("evaluation runs reference is unknown")
        return json.loads(self._manifest_bytes)

    def resolve_control_binding(self, reference: str) -> dict[str, Any]:
        if reference != self.control_binding_ref:
            raise PublicationEvidenceError("control binding reference is unknown")
        return json.loads(self._control_bytes)

    def rederive_release_decision(
        self,
        manifest: dict[str, Any],
        control_binding: dict[str, Any],
    ) -> tuple[dict[str, Any], object]:
        return self.rederive(manifest, control_binding)


@dataclass(frozen=True, slots=True)
class StoredReleasePublicationEvidence:
    """Resolve immutable release evidence from the canonical object store."""

    objects: ObjectStore
    expected_store_identity: str
    rederive: Callable[
        [dict[str, Any], dict[str, Any]],
        tuple[dict[str, Any], object],
    ]

    def _resolve(self, reference: str) -> dict[str, Any]:
        value = self.objects.read("artefact", reference, 1)
        if not isinstance(value, dict) or content_artefact_id(value) != reference:
            raise PublicationEvidenceError("publication evidence identity mismatch")
        return value

    def resolve_evaluation_runs(self, reference: str) -> dict[str, Any]:
        return self._resolve(reference)

    def resolve_control_binding(self, reference: str) -> dict[str, Any]:
        return self._resolve(reference)

    def rederive_release_decision(
        self,
        manifest: dict[str, Any],
        control_binding: dict[str, Any],
    ) -> tuple[dict[str, Any], object]:
        return self.rederive(manifest, control_binding)


@dataclass(frozen=True, slots=True)
class VerifiedReleasePublication:
    """Canonical immutable inputs from which the ledger finalizes one event."""

    source_decision_bytes: bytes
    source_decision_sha256: str
    evaluation_runs_manifest_ref: str
    evaluation_runs_manifest_sha256: str
    control_binding_ref: str
    control_binding_sha256: str
    publication_authority_grant_id: str
    publication_authority_sha256: str

    def payload_for(self, event_id: str) -> dict[str, Any]:
        validate_id(event_id, "event")
        published = json.loads(self.source_decision_bytes)
        published["canonical_event_ref"] = event_id
        return {
            "release_decision": published,
            "source_decision_sha256": self.source_decision_sha256,
            "evaluation_runs_manifest_ref": self.evaluation_runs_manifest_ref,
            "evaluation_runs_manifest_sha256": (
                self.evaluation_runs_manifest_sha256
            ),
            "control_binding_ref": self.control_binding_ref,
            "control_binding_sha256": self.control_binding_sha256,
            "publication_authority_grant_id": (
                self.publication_authority_grant_id
            ),
            "publication_authority_sha256": self.publication_authority_sha256,
            "gate5_authorized": False,
            "candidate_status": "blocked",
        }


def _validated_document(
    value: object,
    schema_id: str,
    schemas: SchemaRegistry,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PublicationEvidenceError(f"invalid {schema_id} document")
    try:
        schemas.validate(schema_id, value)
        canonical_bytes(value)
    except (ArsError, TypeError, ValueError) as exc:
        raise PublicationEvidenceError(f"invalid {schema_id} document") from exc
    return value


def verify_release_publication(
    request: ReleasePublicationRequest,
    resolver: ReleasePublicationEvidenceResolver,
    schemas: SchemaRegistry,
) -> VerifiedReleasePublication:
    """Resolve, re-derive, and compare every publication evidence identity."""
    manifest = _validated_document(
        resolver.resolve_evaluation_runs(
            request.evaluation_runs_manifest_ref
        ),
        "ars://evals/release-publication-evidence",
        schemas,
    )
    control = _validated_document(
        resolver.resolve_control_binding(request.control_binding_ref),
        "ars://evals/release-control-binding",
        schemas,
    )
    if (
        manifest["project_id"] != request.project_id
        or control["project_id"] != request.project_id
    ):
        raise PublicationEvidenceError("publication evidence project mismatch")
    manifest_bytes = canonical_bytes(manifest)
    control_bytes = canonical_bytes(control)
    manifest_snapshot = json.loads(manifest_bytes)
    control_snapshot = json.loads(control_bytes)
    source = manifest_snapshot["release_decision"]
    if not isinstance(source, dict):
        raise PublicationEvidenceError("release decision document is missing")
    schemas.validate("ars://evals/release-gate-decision", source)
    if (
        source.get("release_gate_decision_id")
        != request.release_decision_id
        or source.get("canonical_event_ref") != "unpublished:p0"
        or source.get("decision") != "blocked"
    ):
        raise PublicationEvidenceError("unpublished blocked decision required")
    if control_snapshot["coverage_manifest_id"] != source.get("coverage_manifest_id"):
        raise PublicationEvidenceError("control binding coverage mismatch")
    store_identity = control_snapshot.get("store_identity")
    if store_identity != resolver.expected_store_identity:
        raise PublicationEvidenceError("control binding store identity mismatch")
    try:
        derived, gate5_authorized = resolver.rederive_release_decision(
            json.loads(manifest_bytes),
            json.loads(control_bytes),
        )
    except PublicationEvidenceError:
        raise
    except (ArsError, KeyError, TypeError, ValueError) as exc:
        raise PublicationEvidenceError(
            "typed release evidence re-derivation failed"
        ) from exc
    if gate5_authorized is not False:
        raise PublicationEvidenceError("Gate 5 must remain unauthorized")
    schemas.validate("ars://evals/release-gate-decision", derived)
    source_bytes = canonical_bytes(source)
    if canonical_bytes(derived) != source_bytes:
        raise PublicationEvidenceError("re-derived decision mismatch")
    return VerifiedReleasePublication(
        source_decision_bytes=source_bytes,
        source_decision_sha256=sha256_hex(source_bytes),
        evaluation_runs_manifest_ref=request.evaluation_runs_manifest_ref,
        evaluation_runs_manifest_sha256=sha256_hex(manifest_bytes),
        control_binding_ref=request.control_binding_ref,
        control_binding_sha256=sha256_hex(control_bytes),
        publication_authority_grant_id=(
            request.publication_authority_grant_id
        ),
        publication_authority_sha256=request.publication_authority_sha256,
    )


def content_artefact_id(value: Any) -> str:
    """Derive a stable UUIDv7-shaped artefact reference from canonical content."""
    raw = bytearray.fromhex(sha256_hex(canonical_bytes(value)))[:16]
    raw[6] = (raw[6] & 0x0F) | 0x70
    raw[8] = (raw[8] & 0x3F) | 0x80
    identifier = f"art_{uuid.UUID(bytes=bytes(raw))}"
    return validate_id(identifier, "artefact")


def verify_replayed_release(
    published_decision: dict[str, Any],
    rederived_source: dict[str, Any],
    projection: dict[str, Any],
    project_id: str,
    resolver: ReleasePublicationEvidenceResolver,
    schemas: SchemaRegistry,
) -> dict[str, Any]:
    """Resolve and compare one canonical publication from replayed state."""
    decision_id = published_decision.get("release_gate_decision_id")
    event_ref = published_decision.get("canonical_event_ref")
    if (
        event_ref == "unpublished:p0"
        or not isinstance(event_ref, str)
        or not event_ref.startswith("evt_")
        or published_decision.get("decision") != "blocked"
        or not isinstance(decision_id, str)
    ):
        raise PublicationEvidenceError(
            "release verification requires a published blocked decision"
        )
    record = projection.get("release_decisions", {}).get(decision_id)
    if not isinstance(record, dict):
        raise PublicationEvidenceError("canonical release event is unavailable")
    source = dict(published_decision)
    source["canonical_event_ref"] = "unpublished:p0"
    authority_id = record.get("publication_authority_grant_id")
    authority = projection.get("authority_grants", {}).get(authority_id)
    publication_position = record.get("event_position")
    revocation_position = (
        authority.get("revocation_position")
        if isinstance(authority, dict)
        else None
    )
    if (
        record.get("project_id") != project_id
        or record.get("release_decision_id") != decision_id
        or record.get("event_id") != event_ref
        or record.get("release_decision") != published_decision
        or record.get("source_decision_sha256")
        != sha256_hex(canonical_bytes(source))
        or canonical_bytes(rederived_source) != canonical_bytes(source)
        or record.get("gate5_authorized") is not False
        or record.get("candidate_status") != "blocked"
        or not isinstance(authority, dict)
        or authority.get("authority_grant_sha256")
        != record.get("publication_authority_sha256")
        or not isinstance(publication_position, int)
        or record.get("publication_authority_activation_position")
        != authority.get("activation_position")
        or not isinstance(authority.get("activation_position"), int)
        or authority["activation_position"] >= publication_position
        or (
            revocation_position is not None
            and (
                not isinstance(revocation_position, int)
                or revocation_position <= publication_position
            )
        )
    ):
        raise PublicationEvidenceError("canonical release projection mismatch")
    manifest = resolver.resolve_evaluation_runs(
        record["evaluation_runs_manifest_ref"]
    )
    control = resolver.resolve_control_binding(record["control_binding_ref"])
    manifest = _validated_document(
        manifest,
        "ars://evals/release-publication-evidence",
        schemas,
    )
    control = _validated_document(
        control,
        "ars://evals/release-control-binding",
        schemas,
    )
    try:
        resolved_source, resolved_gate = resolver.rederive_release_decision(
            json.loads(canonical_bytes(manifest)),
            json.loads(canonical_bytes(control)),
        )
    except PublicationEvidenceError:
        raise
    except (ArsError, KeyError, TypeError, ValueError) as exc:
        raise PublicationEvidenceError(
            "typed release evidence re-derivation failed"
        ) from exc
    if (
        sha256_hex(canonical_bytes(manifest))
        != record.get("evaluation_runs_manifest_sha256")
        or sha256_hex(canonical_bytes(control))
        != record.get("control_binding_sha256")
        or manifest.get("project_id") != project_id
        or manifest.get("release_decision") != source
        or canonical_bytes(resolved_source) != canonical_bytes(source)
        or resolved_gate is not False
        or control.get("project_id") != project_id
        or control.get("store_identity") != resolver.expected_store_identity
        or control.get("coverage_manifest_id")
        != source.get("coverage_manifest_id")
    ):
        raise PublicationEvidenceError("canonical release evidence mismatch")
    return record
