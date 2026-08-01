"""Validated external assurance-record catalogue and writer.

The upstream WP6.3 pack contract keeps the twelve record schemas as definitions
inside one accepted schema document.  This module turns that catalogue into the
single read/write seam used by the external control store.  It deliberately
does not create actors, grants, packs, acceptance decisions, or any other
record content: callers provide a JSON object and this seam validates and
persists that object exactly as supplied.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError as JsonSchemaSchemaError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.config import ControlBinding
from research_system.errors import ConflictError, IntegrityError, SchemaError
from research_system.store.identity import load_store_manifest, manifest_schema_root, verify_store_identity
from research_system.store.layout import require_control_root_disjoint_from_code_roots
from research_system.store.objects import ObjectStore


EXTERNAL_RECORD_KIND = "assurance_record"
_CONTRACT_NAME = "wp6-3-tdl-private-assurance-pack.yaml"
_SCHEMA_NAME = "wp6-3-tdl-private-assurance-pack.schema.json"
_PARENT_SCHEMA_BLOB = "acf622b4e7ae72ab9ac58d10aac14efed04560ac"
_PARENT_SCHEMA_SHA256 = "c6154c38bd8fa09589c2891d7771838e3561cd54df5964cd45bfc5cfce65cd8f"
_RECORD_CLASSES = (
    "canonical_actor",
    "producer_relationship_evidence",
    "contract_schema_authorship",
    "independent_contract_review",
    "independent_schema_review",
    "stephen_contract_schema_acceptance",
    "accepted_assurance_requirement",
    "obligation_applicability_confirmation",
    "independent_pack_review",
    "stephen_owner_acceptance",
    "active_authority_grant",
    "registered_pack_object",
)
_EXPECTED_ROWS: Mapping[str, tuple[str, str, str, str]] = {
    "canonical_actor": (
        "canonical_actor",
        "ars://assurance/records/canonical-actor/1.0",
        "1.0.0",
        "#/$defs/canonicalActorRecord",
    ),
    "producer_relationship_evidence": (
        "producer_relationship_evidence",
        "ars://assurance/records/producer-relationship-evidence/1.0",
        "1.0.0",
        "#/$defs/producerRelationshipEvidenceRecord",
    ),
    "contract_schema_authorship": (
        "contract_schema_authorship",
        "ars://assurance/records/contract-schema-authorship/1.0",
        "1.0.0",
        "#/$defs/contractSchemaAuthorshipRecord",
    ),
    "independent_contract_review": (
        "independent_contract_review",
        "ars://assurance/records/independent-contract-review/1.0",
        "1.0.0",
        "#/$defs/independentContractReviewRecord",
    ),
    "independent_schema_review": (
        "independent_schema_review",
        "ars://assurance/records/independent-schema-review/1.0",
        "1.0.0",
        "#/$defs/independentSchemaReviewRecord",
    ),
    "stephen_contract_schema_acceptance": (
        "stephen_contract_schema_acceptance",
        "ars://assurance/records/stephen-contract-schema-acceptance/1.0",
        "1.0.0",
        "#/$defs/stephenContractSchemaAcceptanceRecord",
    ),
    "accepted_assurance_requirement": (
        "accepted_assurance_requirement",
        "ars://assurance/records/accepted-assurance-requirement/1.0",
        "1.0.0",
        "#/$defs/acceptedAssuranceRequirementRecord",
    ),
    "obligation_applicability_confirmation": (
        "obligation_applicability_confirmation",
        "ars://assurance/records/obligation-applicability-confirmation/1.0",
        "1.0.0",
        "#/$defs/obligationApplicabilityConfirmationRecord",
    ),
    "independent_pack_review": (
        "independent_pack_review",
        "ars://assurance/records/independent-pack-review/1.0",
        "1.0.0",
        "#/$defs/independentPackReviewRecord",
    ),
    "stephen_owner_acceptance": (
        "stephen_owner_acceptance",
        "ars://assurance/records/stephen-owner-acceptance/1.0",
        "1.0.0",
        "#/$defs/stephenOwnerAcceptanceRecord",
    ),
    "active_authority_grant": (
        "active_authority_grant",
        "ars://assurance/records/active-authority-grant/1.0",
        "1.0.0",
        "#/$defs/activeAuthorityGrantRecord",
    ),
    "registered_pack_object": (
        "registered_pack_object",
        "ars://assurance/records/registered-pack-object/1.0",
        "1.0.0",
        "#/$defs/registeredPackObjectRecord",
    ),
}

# Identity field, lifecycle field, and active lifecycle value for each accepted
# record definition.  The map is deliberately kept beside the catalogue loader
# so a record class cannot be added without the schema-derived envelope check.
_RECORD_ENVELOPE: Mapping[str, tuple[str, str, str]] = {
    "canonical_actor": ("actor_id", "status", "active"),
    "producer_relationship_evidence": ("relationship_record_id", "status", "active"),
    "contract_schema_authorship": ("authorship_record_id", "authorship_state", "completed"),
    "independent_contract_review": ("review_record_id", "review_state", "completed"),
    "independent_schema_review": ("review_record_id", "review_state", "completed"),
    "stephen_contract_schema_acceptance": ("owner_decision_id", "decision_state", "active"),
    "accepted_assurance_requirement": ("acceptance_record_id", "acceptance_state", "active"),
    "obligation_applicability_confirmation": ("confirmation_record_id", "confirmation_state", "active"),
    "independent_pack_review": ("review_record_id", "review_state", "completed"),
    "stephen_owner_acceptance": ("owner_decision_id", "decision_state", "active"),
    "active_authority_grant": ("authority_grant_id", "grant_state", "active"),
    "registered_pack_object": ("assurance_pack_id", "registration_state", "active"),
}

_TYPED_ID = re.compile(r"^[a-z]{3,4}_(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$")


def git_blob_id(data: bytes) -> str:
    """Return the SHA-1 Git blob object id for exact bytes."""

    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


def storage_object_id(record_id: str) -> str:
    """Map a typed record identity to the registered ``assurance_record`` kind.

    The accepted record schemas intentionally retain their own identity prefixes
    (``act_``, ``rel_``, ``agr_``, and so on), while the object-store registry has
    one envelope kind with the ``arec_`` prefix.  The UUID suffix is preserved,
    making this a deterministic storage address rather than a generated alias.
    """

    if not isinstance(record_id, str):
        raise SchemaError("record identity must be a version-7 typed id")
    match = _TYPED_ID.fullmatch(record_id)
    if match is None:
        raise SchemaError("record identity must be a version-7 typed id")
    return f"arec_{match.group('uuid')}"


def load_complete_revision_history(
    objects: ObjectStore,
    kind: str,
    object_id: str,
) -> dict[int, Any]:
    """Load every immutable revision and require a single contiguous history."""

    directory = objects.control_root / "objects" / kind / object_id
    try:
        paths = sorted(directory.glob("*.json"))
    except OSError as exc:
        raise IntegrityError("external record revision history is unreadable") from exc
    history: dict[int, Any] = {}
    paths_by_revision: dict[int, Path] = {}
    for path in paths:
        match = re.fullmatch(r"(?P<revision>[0-9]{8})-[0-9a-f]{64}\.json", path.name)
        if match is None:
            raise IntegrityError(f"external record revision filename is malformed: {path.name}")
        revision = int(match.group("revision"))
        if revision in paths_by_revision:
            raise IntegrityError("external record revision history contains a duplicate or alternate revision")
        paths_by_revision[revision] = path
    for revision in sorted(paths_by_revision):
        history[revision] = objects.read(kind, object_id, revision)
    if history:
        latest = max(history)
        if set(history) != set(range(1, latest + 1)):
            raise IntegrityError("external record revision history must be complete and contiguous")
    return history


@dataclass(frozen=True)
class ExternalRecordSchemaRow:
    record_class: str
    record_type: str
    schema_id: str
    schema_version: str
    repository_path: str
    schema_json_pointer: str
    schema_git_blob: str
    schema_canonical_sha256: str
    identity_field: str
    state_field: str
    active_state: str
    schema: Mapping[str, Any]


class ExternalRecordSchemaCatalogue:
    """Load and validate the exact twelve-row external-record catalogue."""

    def __init__(self, schema_root: Path) -> None:
        try:
            self.schema_root = schema_root.resolve(strict=True)
            if not self.schema_root.is_dir():
                raise FileNotFoundError(self.schema_root)
        except OSError as exc:
            raise SchemaError("external record schema root is unavailable") from exc

        contract_path = self.schema_root.parent / "contracts" / _CONTRACT_NAME
        schema_path = self.schema_root / "contracts" / _SCHEMA_NAME
        try:
            contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
            raw_schema = schema_path.read_bytes()
            parent_schema = json.loads(raw_schema)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
            raise SchemaError("external record contract or schema is unreadable") from exc

        self._verify_parent_schema(schema_path, raw_schema, parent_schema)
        try:
            rows = contract["required_pack_contract"]["external_record_schema_catalogue"]["exact_schema_rows"]
        except (KeyError, TypeError) as exc:
            raise SchemaError("external record catalogue is missing") from exc
        if not isinstance(rows, list) or len(rows) != len(_RECORD_CLASSES):
            raise SchemaError("external record catalogue must contain exactly twelve rows")

        self._parent_schema = parent_schema
        self._format_checker = FormatChecker()
        registry = Registry().with_resource(parent_schema["$id"], Resource.from_contents(parent_schema))
        parsed: dict[str, ExternalRecordSchemaRow] = {}
        for row in rows:
            parsed_row = self._parse_row(row, parent_schema, schema_path)
            if parsed_row.record_class in parsed:
                raise SchemaError(f"duplicate external record class: {parsed_row.record_class}")
            parsed[parsed_row.record_class] = parsed_row
        if set(parsed) != set(_RECORD_CLASSES):
            raise SchemaError("external record catalogue class set is not exact")
        self._rows = parsed
        validation_schemas: dict[str, Mapping[str, Any]] = {}
        for row in parsed.values():
            # The accepted row is a fragment whose local references intentionally point
            # at the parent contract's definitions.  Add those definitions only to the
            # in-memory validation resource; the accepted schema bytes remain untouched.
            validation_schema = dict(row.schema)
            validation_schema["$defs"] = parent_schema["$defs"]
            registry = registry.with_resource(
                row.schema_id,
                Resource.from_contents(validation_schema, default_specification=DRAFT202012),
            )
            validation_schemas[row.record_class] = validation_schema
        self._registry = registry
        self._validation_schemas = validation_schemas

    @staticmethod
    def _verify_parent_schema(schema_path: Path, raw_schema: bytes, parent_schema: Mapping[str, Any]) -> None:
        if b"\r" in raw_schema or not raw_schema.endswith(b"\n"):
            raise SchemaError("external record schema is not UTF-8/LF")
        try:
            raw_schema.decode("utf-8", "strict")
            Draft202012Validator.check_schema(parent_schema)
        except (UnicodeDecodeError, TypeError, JsonSchemaSchemaError) as exc:
            raise SchemaError("external record parent schema is invalid") from exc
        if git_blob_id(raw_schema) != _PARENT_SCHEMA_BLOB:
            raise SchemaError("external record parent schema Git blob mismatch")
        if sha256_hex(raw_schema) != _PARENT_SCHEMA_SHA256:
            raise SchemaError("external record parent schema SHA-256 mismatch")
        if schema_path.name != _SCHEMA_NAME:
            raise SchemaError("external record parent schema path mismatch")

    @staticmethod
    def _resolve_pointer(document: Mapping[str, Any], pointer: str) -> Mapping[str, Any]:
        if not pointer.startswith("#/"):
            raise SchemaError("external record schema pointer must be a JSON pointer")
        current: Any = document
        for token in pointer[2:].split("/"):
            token = token.replace("~1", "/").replace("~0", "~")
            if not isinstance(current, Mapping) or token not in current:
                raise SchemaError(f"external record schema pointer does not resolve: {pointer}")
            current = current[token]
        if not isinstance(current, Mapping):
            raise SchemaError(f"external record schema pointer is not an object: {pointer}")
        return current

    def _parse_row(
        self,
        row: object,
        parent_schema: Mapping[str, Any],
        schema_path: Path,
    ) -> ExternalRecordSchemaRow:
        if not isinstance(row, Mapping):
            raise SchemaError("external record catalogue row must be an object")
        required = {
            "record_class",
            "record_type",
            "schema_id",
            "schema_version",
            "repository_path",
            "schema_json_pointer",
            "schema_git_blob",
            "schema_canonical_sha256",
        }
        if set(row) != required:
            raise SchemaError("external record catalogue row fields are not exact")
        record_class = row["record_class"]
        record_type = row["record_type"]
        pointer = row["schema_json_pointer"]
        if not all(isinstance(row[key], str) for key in required):
            raise SchemaError("external record catalogue row values must be strings")
        repo_root = self.schema_root.parents[1]
        try:
            repository_path = schema_path.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError as exc:
            raise SchemaError("external record schema path is outside the repository root") from exc
        if row["repository_path"] != repository_path:
            raise SchemaError("external record catalogue repository path mismatch")
        expected = _EXPECTED_ROWS.get(str(record_class))
        if (
            expected is None
            or (str(record_type), str(row["schema_id"]), str(row["schema_version"]), str(pointer)) != expected
        ):
            raise SchemaError(f"external record catalogue identity is not accepted: {record_class}")
        if row["schema_git_blob"] != _PARENT_SCHEMA_BLOB or row["schema_canonical_sha256"] != _PARENT_SCHEMA_SHA256:
            raise SchemaError(f"external record catalogue parent identity is not accepted: {record_class}")
        fragment = self._resolve_pointer(parent_schema, pointer)
        if fragment.get("$id") != row["schema_id"] or fragment.get("x-schema-version") != row["schema_version"]:
            raise SchemaError(f"external record schema identity mismatch: {record_class}")
        if fragment.get("properties", {}).get("record_type", {}).get("const") != record_type:
            raise SchemaError(f"external record type mismatch: {record_class}")
        identity_field, state_field, active_state = _RECORD_ENVELOPE.get(str(record_class), ("", "", ""))
        if not identity_field or identity_field not in fragment.get("required", ()):
            raise SchemaError(f"external record identity field is not required: {record_class}")
        state_schema = fragment.get("properties", {}).get(state_field, {})
        if state_field not in fragment.get("required", ()) or state_schema.get("const") != active_state:
            raise SchemaError(f"external record lifecycle field is not exact: {record_class}")
        return ExternalRecordSchemaRow(
            record_class=str(record_class),
            record_type=str(record_type),
            schema_id=str(row["schema_id"]),
            schema_version=str(row["schema_version"]),
            repository_path=repository_path,
            schema_json_pointer=str(pointer),
            schema_git_blob=str(row["schema_git_blob"]),
            schema_canonical_sha256=str(row["schema_canonical_sha256"]),
            identity_field=identity_field,
            state_field=state_field,
            active_state=active_state,
            schema=fragment,
        )

    @property
    def rows(self) -> Mapping[str, ExternalRecordSchemaRow]:
        return self._rows

    @property
    def registry(self) -> Registry:
        return self._registry

    def row(self, record_class: str) -> ExternalRecordSchemaRow:
        try:
            return self._rows[record_class]
        except KeyError as exc:
            raise SchemaError(f"unknown external record class: {record_class}") from exc

    def validate(self, record_class: str, record_id: str, record: object) -> ExternalRecordSchemaRow:
        row = self.row(record_class)
        if not isinstance(record, Mapping):
            raise SchemaError("external record must be a JSON object")
        if record.get("record_type") != row.record_type:
            raise SchemaError(f"external record class/type mismatch: {record_class}")
        if record.get(row.identity_field) != record_id:
            raise SchemaError(f"external record identity field does not match record identity: {record_class}")
        validator = Draft202012Validator(
            self._validation_schemas[record_class],
            registry=self._registry,
            format_checker=self._format_checker,
        )
        errors = sorted(validator.iter_errors(record), key=lambda error: list(error.absolute_path))
        if errors:
            message = "; ".join(
                f"{'.'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}" for error in errors
            )
            raise SchemaError(f"{row.schema_id}: {message}")
        return row


@dataclass(frozen=True)
class ExternalAssuranceRecordReceipt:
    record_class: str
    record_id: str
    revision: int
    canonical_sha256: str
    schema_id: str
    schema_version: str
    schema_git_blob: str
    schema_canonical_sha256: str


class ExternalAssuranceRecordStore:
    """Write schema-valid, externally bound assurance records with CAS."""

    def __init__(self, binding: ControlBinding) -> None:
        if not isinstance(binding, ControlBinding):
            raise TypeError("external assurance records require a validated ControlBinding")
        try:
            control_root = binding.control_root.resolve(strict=True)
            code_roots = [root.resolve(strict=True) for root in binding.code_roots]
            verify_store_identity(control_root, binding.project_id, binding.store_identity, code_roots)
            require_control_root_disjoint_from_code_roots(code_roots, control_root)
            manifest_schema = manifest_schema_root(load_store_manifest(control_root))
            if manifest_schema is not None and manifest_schema.resolve(strict=True) != binding.schema_root.resolve(
                strict=True
            ):
                raise IntegrityError("binding schema root differs from store manifest")
        except (OSError, KeyError, ValueError) as exc:
            raise IntegrityError("control binding is not valid for external assurance records") from exc
        self.binding = binding
        self.catalogue = ExternalRecordSchemaCatalogue(binding.schema_root)
        self.objects = ObjectStore(control_root)

    def _receipt(
        self, row: ExternalRecordSchemaRow, record_id: str, revision: int, record: Mapping[str, Any]
    ) -> ExternalAssuranceRecordReceipt:
        return ExternalAssuranceRecordReceipt(
            record_class=row.record_class,
            record_id=record_id,
            revision=revision,
            canonical_sha256=sha256_hex(canonical_bytes(record)),
            schema_id=row.schema_id,
            schema_version=row.schema_version,
            schema_git_blob=row.schema_git_blob,
            schema_canonical_sha256=row.schema_canonical_sha256,
        )

    def _validated_history(
        self,
        *,
        record_class: str,
        record_id: str,
        object_id: str,
    ) -> dict[int, Any]:
        row = self.catalogue.row(record_class)
        history = load_complete_revision_history(self.objects, EXTERNAL_RECORD_KIND, object_id)
        for existing in history.values():
            if (
                not isinstance(existing, Mapping)
                or existing.get("record_type") != row.record_type
                or existing.get(row.identity_field) != record_id
            ):
                raise IntegrityError("external record revision history contains a foreign or mismatched identity")
            self.catalogue.validate(record_class, record_id, existing)
        return history

    def write(
        self,
        *,
        record_class: str,
        record_id: str,
        revision: int,
        expected_previous_revision: int,
        record: Mapping[str, Any],
    ) -> ExternalAssuranceRecordReceipt:
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise ConflictError("record revision must be positive")
        if (
            isinstance(expected_previous_revision, bool)
            or not isinstance(expected_previous_revision, int)
            or expected_previous_revision < 0
        ):
            raise ConflictError("expected previous revision must be non-negative")
        if revision != expected_previous_revision + 1:
            raise ConflictError("record revision must be the expected previous revision plus one")
        row = self.catalogue.validate(record_class, record_id, record)
        object_id = storage_object_id(record_id)
        history = self._validated_history(record_class=record_class, record_id=record_id, object_id=object_id)
        latest = max(history) if history else None
        observed = 0 if latest is None else latest
        if latest == revision:
            existing = history[revision]
            if existing == dict(record):
                return self._receipt(row, record_id, revision, record)
            raise ConflictError("object revision already exists with different content")
        if observed != expected_previous_revision:
            raise ConflictError(f"expected previous revision {expected_previous_revision}, observed {observed}")
        self.objects.write(EXTERNAL_RECORD_KIND, object_id, revision, dict(record))
        return self._receipt(row, record_id, revision, record)
