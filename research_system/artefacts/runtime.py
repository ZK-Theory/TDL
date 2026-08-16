"""Production adapters for replay-authorized artefact consumption."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from research_system.authority import LedgerAuthorityGrantResolver
from research_system.artefacts.authority import (
    AcceptedContractSubject,
    ArtefactAuthorityContractLoader,
    GoverningEvidenceResolution,
)
from research_system.artefacts.use_resolver import ArtefactUseResolver
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.config import ControlBinding
from research_system.discovery.runtime import build_spec_execution_authority_validator
from research_system.errors import ArsError
from research_system.evidence.consumers import ArtefactEvidenceConsumers
from research_system.ids import validate_id
from research_system.schema_registry import SchemaRegistry, runtime_schema_registry
from research_system.store.ledger import EventLedger
from research_system.store.lock import WriterLock
from research_system.store.objects import ObjectStore


ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT = AcceptedContractSubject(
    manifest_git_blob="9d415f9af23caa963c36dbbb8103c2bf55101a95",
    manifest_sha256="365ee6643dc626f361f00bb06901718386dba319549d7079f5182fa672d1cb05",
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

    @staticmethod
    def _validate_reference_id(reference_id: object) -> str:
        if not isinstance(reference_id, str):
            raise ArsError("governing review reference identity is invalid")
        try:
            return validate_id(reference_id, "assurance_record")
        except (TypeError, ValueError) as exc:
            raise ArsError("governing review reference identity is invalid") from exc

    @staticmethod
    def _validate_evaluation_time(evaluation_time: object) -> datetime:
        if (
            not isinstance(evaluation_time, datetime)
            or evaluation_time.tzinfo is None
            or evaluation_time.utcoffset() != UTC.utcoffset(evaluation_time)
        ):
            raise ArsError("governing review evaluation time must be UTC")
        return evaluation_time

    def _validated_publications(
        self,
        publications: object,
    ) -> tuple[tuple[str, dict[str, object]], ...]:
        if not isinstance(publications, list):
            raise ArsError("governing review publications must be a list")
        references: set[str] = set()
        validated: list[tuple[str, dict[str, object]]] = []
        for publication in publications:
            if not isinstance(publication, Mapping):
                raise ArsError("governing review publication must be a mapping")
            if set(publication) != {"reference_id", "record"}:
                raise ArsError("governing review publication fields are invalid")
            reference_id = self._validate_reference_id(publication.get("reference_id"))
            record = publication.get("record")
            if reference_id in references or not isinstance(record, Mapping):
                raise ArsError("governing review publication identities are invalid")
            references.add(reference_id)
            value = dict(record)
            self.schemas.validate("ars://evidence/governing-scientific-review", value)
            validated.append((reference_id, value))
        return tuple(validated)

    def _prevalidate_values(self, values: tuple[tuple[str, dict[str, object]], ...]) -> None:
        for reference_id, value in values:
            if self.objects.revision_exists("assurance_record", reference_id, 1):
                if self.objects.read("assurance_record", reference_id, 1) != value:
                    raise ArsError("governing review publication identity conflicts")

    def publish(self, reference_id: str, record: Mapping[str, object]) -> GoverningEvidenceResolution:
        reference_id = self._validate_reference_id(reference_id)
        if not isinstance(record, Mapping):
            raise ArsError("governing review record must be a mapping")
        value = dict(record)
        self.schemas.validate("ars://evidence/governing-scientific-review", value)
        self.objects.write("assurance_record", reference_id, 1, value)
        return self.resolve(
            reference_id,
            project_id=str(value["project_id"]),
            evaluation_time=datetime.now(UTC),
        )

    def prevalidate_publications(self, publications: list[Mapping[str, object]]) -> None:
        """Validate one exact write-once publication set without creating objects."""

        self._prevalidate_values(self._validated_publications(publications))

    def publish_batch(
        self,
        publications: list[Mapping[str, object]],
        *,
        project_id: str,
        evaluation_time: datetime,
    ) -> tuple[GoverningEvidenceResolution, ...]:
        """Publish one project-bound set after locked, whole-set prevalidation.

        Exact retries are idempotent. A synchronous member failure rolls back
        only revisions first created by this call while the writer lock remains
        held; pre-existing matching revisions are never removed.
        """

        evaluation_time = self._validate_evaluation_time(evaluation_time)
        values = self._validated_publications(publications)
        if not isinstance(project_id, str) or any(value.get("project_id") != project_id for _, value in values):
            raise ArsError("governing review publication belongs to a different project")
        batch_sha256 = sha256_hex(
            canonical_bytes([{"reference_id": reference_id, "record": value} for reference_id, value in values])
        )
        lock_identity = {
            "writer_id": f"governing-review-batch:{batch_sha256}",
            "command_type": "PublishGoverningScientificReviews",
        }
        with WriterLock(self.objects.control_root / "runtime" / "writer.lock", lock_identity):
            self._prevalidate_values(values)
            existed_before = {
                reference_id: self.objects.revision_exists("assurance_record", reference_id, 1)
                for reference_id, _value in values
            }
            written: list[tuple[str, dict[str, object]]] = []
            try:
                for reference_id, value in values:
                    self.objects.write("assurance_record", reference_id, 1, value)
                    written.append((reference_id, value))
            except Exception:
                for reference_id, value in reversed(written):
                    self.objects.rollback_new_revision(
                        "assurance_record",
                        reference_id,
                        1,
                        value,
                        existed_before=existed_before[reference_id],
                    )
                raise
            return tuple(
                self.resolve(
                    reference_id,
                    project_id=project_id,
                    evaluation_time=evaluation_time,
                )
                for reference_id, _value in values
            )

    def resolve(
        self,
        reference_id: str,
        *,
        project_id: str,
        evaluation_time: datetime,
    ) -> GoverningEvidenceResolution:
        reference_id = self._validate_reference_id(reference_id)
        self._validate_evaluation_time(evaluation_time)
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
    ledger = EventLedger(binding.control_root, binding.project_id, schemas, store_identity=binding.store_identity)
    authority = LedgerAuthorityGrantResolver(
        binding.control_root,
        binding.project_id,
        binding.store_identity,
        schemas,
        approved_witness=binding.origin_witness,
        approved_witness_path=binding.origin_witness_path,
    )
    resolver = ArtefactUseResolver(
        ledger=ledger,
        objects=objects,
        schemas=schemas,
        contract_loader=ArtefactAuthorityContractLoader(ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT),
        governing_evidence=GoverningScientificReviewStore(objects, schemas),
        content_reader=ControlRootArtefactContentReader(binding.control_root),
        authority_state_validator=authority.validate_replayed_administration_state,
        spec_execution_authority_validator_factory=lambda events: build_spec_execution_authority_validator(
            control_root=binding.control_root,
            schemas=schemas,
            authority_resolver=authority,
            events=events,
        ),
    )
    return ArtefactEvidenceConsumers(resolver)


__all__ = [
    "ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT",
    "ControlRootArtefactContentReader",
    "GoverningScientificReviewStore",
    "build_artefact_consumers",
]
