"""Production adapters for replay-authorized artefact consumption."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from research_system.artefacts.authority import (
    AcceptedContractSubject,
    ArtefactAuthorityContractLoader,
    GoverningEvidenceResolution,
)
from research_system.artefacts.use_resolver import ArtefactUseResolver
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.config import ControlBinding
from research_system.errors import ArsError
from research_system.evidence.consumers import ArtefactEvidenceConsumers
from research_system.ids import validate_id
from research_system.schema_registry import SchemaRegistry, runtime_schema_registry
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore


ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT = AcceptedContractSubject(
    manifest_git_blob="0cd9581ca4427a8515aefd99a7a045d52452ddd3",
    manifest_sha256="0b1f5499d631bfd113dcec0453247d68468a91a2c2bf997b295f6088ff418e6b",
)


class ControlRootArtefactContentReader:
    """Read registered bytes only from the selected canonical control root."""

    def __init__(self, control_root: Path) -> None:
        self.control_root = control_root.resolve(strict=True)

    def read(self, *, root_id: str, relative_path: str) -> bytes:
        if root_id != "control":
            raise ArsError("artefact content root is not the selected control store")
        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ArsError("artefact content path is not a safe control-relative path")
        candidate = (self.control_root / relative).resolve(strict=True)
        try:
            candidate.relative_to(self.control_root)
        except ValueError as exc:
            raise ArsError("artefact content path escapes the selected control store") from exc
        if not candidate.is_file():
            raise ArsError("artefact content path is not a regular file")
        return candidate.read_bytes()


class GoverningScientificReviewStore:
    """Write-once authority channel for independently attributed review facts."""

    def __init__(self, objects: ObjectStore, schemas: SchemaRegistry) -> None:
        self.objects = objects
        self.schemas = schemas

    def publish(self, reference_id: str, record: Mapping[str, object]) -> GoverningEvidenceResolution:
        validate_id(reference_id, "assurance_record")
        value = dict(record)
        self.schemas.validate("ars://evidence/governing-scientific-review", value)
        self.objects.write("assurance_record", reference_id, 1, value)
        return self.resolve(
            reference_id,
            project_id=str(value["project_id"]),
            evaluation_time=datetime.now(UTC),
        )

    def resolve(
        self,
        reference_id: str,
        *,
        project_id: str,
        evaluation_time: datetime,
    ) -> GoverningEvidenceResolution:
        validate_id(reference_id, "assurance_record")
        if evaluation_time.tzinfo is None or evaluation_time.utcoffset() != UTC.utcoffset(evaluation_time):
            raise ArsError("governing review evaluation time must be UTC")
        value = self.objects.read("assurance_record", reference_id, 1)
        if not isinstance(value, dict):
            raise ArsError("governing review evidence is unavailable")
        self.schemas.validate("ars://evidence/governing-scientific-review", value)
        if value.get("project_id") != project_id:
            raise ArsError("governing review evidence belongs to a different project")
        return GoverningEvidenceResolution(
            reference_id=reference_id,
            canonical_sha256=sha256_hex(canonical_bytes(value)),
            record=value,
        )


def build_artefact_consumers(binding: ControlBinding) -> ArtefactEvidenceConsumers:
    """Construct the accepted 06i consumer port from one verified binding."""
    schemas = runtime_schema_registry(binding.schema_root)
    objects = ObjectStore(binding.control_root)
    resolver = ArtefactUseResolver(
        ledger=EventLedger(binding.control_root, binding.project_id, schemas),
        objects=objects,
        schemas=schemas,
        contract_loader=ArtefactAuthorityContractLoader(ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT),
        governing_evidence=GoverningScientificReviewStore(objects, schemas),
        content_reader=ControlRootArtefactContentReader(binding.control_root),
    )
    return ArtefactEvidenceConsumers(resolver)


__all__ = [
    "ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT",
    "ControlRootArtefactContentReader",
    "GoverningScientificReviewStore",
    "build_artefact_consumers",
]
