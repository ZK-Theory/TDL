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


def _exact_document(
    value: object,
    fields: set[str],
    schema_id: str,
) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != fields
        or value.get("schema_id") != schema_id
        or value.get("schema_version") != "1.0.0"
    ):
        raise PublicationEvidenceError(f"invalid {schema_id} document")
    canonical_bytes(value)
    return value


def verify_release_publication(
    request: ReleasePublicationRequest,
    resolver: ReleasePublicationEvidenceResolver,
    schemas: SchemaRegistry,
) -> VerifiedReleasePublication:
    """Resolve, re-derive, and compare every publication evidence identity."""
    manifest = _exact_document(
        resolver.resolve_evaluation_runs(
            request.evaluation_runs_manifest_ref
        ),
        {
            "schema_id",
            "schema_version",
            "project_id",
            "release_decision",
        },
        "ars://evals/release-publication-evidence",
    )
    control = _exact_document(
        resolver.resolve_control_binding(request.control_binding_ref),
        {
            "schema_id",
            "schema_version",
            "project_id",
            "store_identity",
            "coverage_manifest_id",
        },
        "ars://evals/release-control-binding",
    )
    if (
        manifest["project_id"] != request.project_id
        or control["project_id"] != request.project_id
    ):
        raise PublicationEvidenceError("publication evidence project mismatch")
    source = manifest["release_decision"]
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
    if control["coverage_manifest_id"] != source.get("coverage_manifest_id"):
        raise PublicationEvidenceError("control binding coverage mismatch")
    store_identity = control.get("store_identity")
    if (
        not isinstance(store_identity, str)
        or len(store_identity) != 64
        or any(character not in "0123456789abcdef" for character in store_identity)
    ):
        raise PublicationEvidenceError("control binding store identity is invalid")
    derived, gate5_authorized = resolver.rederive_release_decision(
        manifest,
        control,
    )
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
        evaluation_runs_manifest_sha256=sha256_hex(canonical_bytes(manifest)),
        control_binding_ref=request.control_binding_ref,
        control_binding_sha256=sha256_hex(canonical_bytes(control)),
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
    source_decision: dict[str, Any],
    projection: dict[str, Any],
    project_id: str,
) -> dict[str, Any]:
    """Resolve and compare one canonical publication from replayed state."""
    decision_id = source_decision.get("release_gate_decision_id")
    if (
        source_decision.get("canonical_event_ref") != "unpublished:p0"
        or source_decision.get("decision") != "blocked"
        or not isinstance(decision_id, str)
    ):
        raise PublicationEvidenceError(
            "release verification requires the unpublished blocked source"
        )
    record = projection.get("release_decisions", {}).get(decision_id)
    if not isinstance(record, dict):
        raise PublicationEvidenceError("canonical release event is unavailable")
    event_id = record.get("event_id")
    published = dict(source_decision)
    published["canonical_event_ref"] = event_id
    if (
        record.get("project_id") != project_id
        or record.get("release_decision_id") != decision_id
        or record.get("release_decision") != published
        or record.get("source_decision_sha256")
        != sha256_hex(canonical_bytes(source_decision))
        or record.get("gate5_authorized") is not False
        or record.get("candidate_status") != "blocked"
        or not isinstance(event_id, str)
        or not event_id.startswith("evt_")
    ):
        raise PublicationEvidenceError("canonical release projection mismatch")
    return record
