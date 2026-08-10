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
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError as JsonSchemaSchemaError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from research_system.authority import GrantedPolicyActionIdentity, LedgerAuthorityGrantResolver
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.config import ControlBinding
from research_system.errors import ArsError, ConflictError, IntegrityError, SchemaError
from research_system.ids import validate_id
from research_system.schema_registry import SchemaRegistry, runtime_schema_registry
from research_system.store.identity import load_store_manifest, verify_store_identity
from research_system.store.schema_binding import verify_effective_store_schema_root
from research_system.store.layout import (
    require_control_root_disjoint_from_code_roots,
    require_existing_control_root,
)
from research_system.store.lock import WriterLock
from research_system.store.objects import ObjectStore


EXTERNAL_RECORD_KIND = "assurance_record"
_CONTRACT_NAME = "wp6-3-tdl-private-assurance-pack.yaml"
_SCHEMA_NAME = "wp6-3-tdl-private-assurance-pack.schema.json"
_PARENT_SCHEMA_BLOB = "5226d342d2a0d488eecee6f3f7c91b70930a41b3"
_PARENT_SCHEMA_SHA256 = "2dcceb9dd6c79af5140665a851e75712b0b6c4cf0c8ffed3e9c7445b06aeb2fb"
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

# The public semantic identity remains the exact class-specific typed id.  These
# are field-scoped ObjectStore kinds, not alternate public ids: two classes may
# share a prefix only because their storage fields are distinct.
_RECORD_STORAGE_KINDS: Mapping[str, str] = {record_class: record_class for record_class in _RECORD_CLASSES}

# The accepted contract makes supersession immutable and every lifecycle field
# in the twelve schemas is fixed to its active/completed value.  The only
# identities that have an initially revisable representation are the actor and
# producer-relationship records.  Their mutable fields are intentionally a
# closed allow-list; semantic identity, endpoints, lifecycle, and all evidence
# fields remain immutable.  Every other class requires a new semantic id.
_REVISABLE_RECORD_FIELDS: Mapping[str, frozenset[str]] = {
    "canonical_actor": frozenset({"canonical_name"}),
    "producer_relationship_evidence": frozenset({"relationship_context", "grade", "effective_at", "expires_at"}),
}

_CALLER_ACTOR_CLASSES = frozenset({"human", "agent", "service"})
_RFC3339_UTC = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$")
_RELATIONSHIP_FIELD_BY_CLASS: Mapping[str, str] = {
    "producer_relationship_evidence": "relationship_record_id",
    "independent_contract_review": "relationship_record_id",
    "independent_schema_review": "relationship_record_id",
    "obligation_applicability_confirmation": "relationship_record_id",
    "accepted_assurance_requirement": "scope_relationship_record_id",
    "independent_pack_review": "relationship_record_id",
}
_PUBLICATION_POLICY_ACTION = "publish_external_assurance_record"
_PUBLICATION_POLICY_ACTION_SCHEMA_ID = "ars://core/policy-action/PublishExternalAssuranceRecord"
_PUBLICATION_POLICY_ACTION_SCHEMA_VERSION = "1.0.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_TYPED_ID = re.compile(r"^[a-z]{3,4}_(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$")


def git_blob_id(data: bytes) -> str:
    """Return the SHA-1 Git blob object id for exact bytes."""

    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


def storage_object_kind(record_class: str) -> str:
    """Return the field-scoped ObjectStore kind for one exact record class."""

    try:
        return _RECORD_STORAGE_KINDS[record_class]
    except KeyError as exc:
        raise SchemaError(f"unknown external record class: {record_class}") from exc


def storage_object_id(record_id: str, record_class: str | None = None) -> str:
    """Validate and return the full semantic id without a lossy alias rewrite.

    ``record_class`` is required at production seams so the id prefix is checked
    against the class-specific kind.  The optional form is retained only for
    low-level callers that need generic typed-id validation.
    """

    if not isinstance(record_id, str):
        raise SchemaError("record identity must be a version-7 typed id")
    match = _TYPED_ID.fullmatch(record_id)
    if match is None:
        raise SchemaError("record identity must be a version-7 typed id")
    if record_class is not None:
        storage_object_kind(record_class)
        try:
            validate_id(record_id, record_class)
        except (AttributeError, TypeError, ValueError) as exc:
            raise SchemaError(f"record identity prefix does not match class: {record_class}") from exc
    return record_id


def storage_object_key(record_class: str, record_id: str) -> tuple[str, str]:
    """Return the exact class-kind and full semantic-id storage key."""

    return storage_object_kind(record_class), storage_object_id(record_id, record_class)


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
    caller_actor_id: str | None = None
    authority_grant_id: str | None = None
    record_action: str | None = None
    publication_context_sha256: str | None = None


@dataclass(frozen=True)
class ExternalRecordPublicationContext:
    """Attributed caller/session context required at the governed write seam.

    This is an attribution and authority-binding value, not provider or OAuth
    authentication.  Its exact fields are carried into the writer lock and are
    compared with the record request before any authority resolution or CAS.
    """

    caller_actor_id: str
    caller_actor_class: str
    authority_grant_id: str
    record_action: str
    record_class: str
    record_id: str
    revision: int
    expected_previous_revision: int
    project_id: str
    store_identity: str
    authority_root: str
    canonical_sha256: str
    task_id: str
    session_id: str
    relationship_record_id: str | None
    required_risk: str
    occurred_at: str


@dataclass(frozen=True)
class ExternalRecordResolution(Mapping[str, object]):
    """A persisted record body plus trusted storage revision and digest."""

    record_class: str
    record_id: str
    revision: int
    canonical_sha256: str
    record: Mapping[str, object]

    @property
    def body(self) -> Mapping[str, object]:
        return self.record

    def __getitem__(self, key: str) -> object:
        return self.record[key]

    def __iter__(self):
        return iter(self.record)

    def __len__(self) -> int:
        return len(self.record)


class ExternalAssuranceRecordStore:
    """Write schema-valid external records through an authority-bound CAS seam."""

    def _build_catalogue(self, schema_root: Path) -> ExternalRecordSchemaCatalogue:
        """Build this store's closed schema profile after binding validation."""

        return ExternalRecordSchemaCatalogue(schema_root)

    def __init__(self, binding: ControlBinding, *, clock: Callable[[], datetime] | None = None) -> None:
        if not isinstance(binding, ControlBinding):
            raise TypeError("external assurance records require a validated ControlBinding")
        try:
            if binding.origin_witness is None:
                raise IntegrityError("control binding has no approved origin witness")
            code_roots = [root.resolve(strict=False) for root in binding.code_roots]
            control_root = require_existing_control_root(code_roots, binding.control_root)
            verify_store_identity(
                control_root,
                binding.project_id,
                binding.store_identity,
                code_roots,
                approved_witness=binding.origin_witness,
                approved_witness_path=binding.origin_witness_path,
            )
            require_control_root_disjoint_from_code_roots(code_roots, control_root)
            manifest = load_store_manifest(
                control_root,
                approved_witness=binding.origin_witness,
                approved_witness_path=binding.origin_witness_path,
            )
            verify_effective_store_schema_root(
                control_root,
                manifest,
                binding.schema_root,
                activation_sha256=binding.schema_binding_activation_sha256,
            )
        except (OSError, KeyError, ValueError) as exc:
            raise IntegrityError("control binding is not valid for external assurance records") from exc
        self.binding = binding
        self.catalogue = self._build_catalogue(binding.schema_root)
        self.objects = ObjectStore(control_root)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._authority_schemas: SchemaRegistry | None = None
        self._authority_resolver: LedgerAuthorityGrantResolver | None = None

    def _storage_object_key(
        self,
        record_class: str,
        record_id: str,
        *,
        record: Mapping[str, Any] | None = None,
    ) -> tuple[str, str]:
        """Resolve the storage key for this store's record profile.

        The accepted WP6.3 profile keeps its exact class-specific key mapping.
        A separately governed profile may override this hook while reusing the
        binding, history, locking, CAS, receipt, and resolution substrate.  The
        body is supplied on write paths and omitted when resolving by identity.
        """

        del record
        return storage_object_key(record_class, record_id)

    def _receipt(
        self,
        row: ExternalRecordSchemaRow,
        record_id: str,
        revision: int,
        record: Mapping[str, Any],
        publication_context: ExternalRecordPublicationContext | None = None,
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
            caller_actor_id=None if publication_context is None else publication_context.caller_actor_id,
            authority_grant_id=None if publication_context is None else publication_context.authority_grant_id,
            record_action=None if publication_context is None else publication_context.record_action,
            publication_context_sha256=(
                None if publication_context is None else sha256_hex(canonical_bytes(asdict(publication_context)))
            ),
        )

    @staticmethod
    def _validate_revision_numbers(revision: int, expected_previous_revision: int) -> None:
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

    @staticmethod
    def _validate_context_id(value: object, kind: str, label: str) -> str:
        try:
            return validate_id(str(value), kind)
        except (AttributeError, TypeError, ValueError) as exc:
            raise SchemaError(f"publication context {label} is not a valid {kind} id") from exc

    def _validate_publication_context(
        self,
        *,
        context: ExternalRecordPublicationContext,
        record_class: str,
        record_id: str,
        revision: int,
        expected_previous_revision: int,
        record: Mapping[str, Any],
    ) -> None:
        if not isinstance(context, ExternalRecordPublicationContext):
            raise SchemaError("external record publication context is required")
        if context.record_class != record_class:
            raise SchemaError("publication context record class does not match the request")
        if context.record_id != record_id:
            raise SchemaError("publication context record id does not match the request")
        if context.revision != revision:
            raise SchemaError("publication context revision does not match the request")
        if context.expected_previous_revision != expected_previous_revision:
            raise SchemaError("publication context expected previous revision does not match the request")
        expected_action = "create" if revision == 1 and expected_previous_revision == 0 else "revise"
        if context.record_action != expected_action:
            raise SchemaError("publication context record action does not match revision")
        if context.project_id != self.binding.project_id:
            raise SchemaError("publication context project does not match the bound project")
        if context.store_identity != self.binding.store_identity:
            raise SchemaError("publication context store identity does not match the bound store")
        if not _SHA256.fullmatch(context.canonical_sha256):
            raise SchemaError("publication context canonical body hash is not a lowercase SHA-256")
        if context.canonical_sha256 != sha256_hex(canonical_bytes(record)):
            raise SchemaError("publication context canonical body hash does not match the record")
        self._validate_context_id(context.caller_actor_id, "actor", "caller actor")
        if context.caller_actor_class not in _CALLER_ACTOR_CLASSES:
            raise SchemaError("publication context caller actor class is not accepted")
        self._validate_context_id(context.authority_grant_id, "authority_grant", "authority grant")
        self._validate_context_id(context.authority_root, "authority_grant", "authority root")
        self._validate_context_id(context.task_id, "task", "task")
        self._validate_context_id(context.session_id, "context", "session")
        if context.relationship_record_id is not None:
            self._validate_context_id(
                context.relationship_record_id,
                "producer_relationship_evidence",
                "relationship",
            )
        if context.required_risk not in {"R0", "R1", "R2", "R3"}:
            raise SchemaError("publication context risk must be R0 through R3")
        if _RFC3339_UTC.fullmatch(context.occurred_at) is None:
            raise SchemaError("publication context occurred_at must be strict RFC3339 UTC")
        try:
            occurred_at = datetime.fromisoformat(context.occurred_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SchemaError("publication context occurred_at is not a valid timestamp") from exc
        if occurred_at.tzinfo != timezone.utc:
            raise SchemaError("publication context occurred_at must be UTC")
        self._storage_object_key(record_class, record_id, record=record)

        relationship_field = _RELATIONSHIP_FIELD_BY_CLASS.get(record_class)
        if relationship_field is None:
            if context.relationship_record_id is not None:
                raise SchemaError("publication context relationship is not valid for this record class")
        elif context.relationship_record_id != record.get(relationship_field):
            raise SchemaError("publication context relationship does not match the record")

        caller_id = context.caller_actor_id
        if record_class == "canonical_actor":
            if record.get("actor_id") != caller_id:
                raise SchemaError("caller/body actor identity mismatch")
        elif record_class == "producer_relationship_evidence":
            subject = record.get("subject_actor_id")
            object_actor = record.get("object_actor_id")
            if subject == object_actor == caller_id:
                raise SchemaError("relationship self-attestation is prohibited")
            if caller_id not in {subject, object_actor}:
                raise SchemaError("caller/body relationship actor mismatch")
        elif record_class == "contract_schema_authorship":
            if record.get("author_actor_id") != caller_id:
                raise SchemaError("caller/body author identity mismatch")
        elif record_class in {"independent_contract_review", "independent_schema_review"}:
            if record.get("reviewer_actor_id") != caller_id:
                raise SchemaError("caller/body reviewer identity mismatch")
            if record.get("reviewer_actor_id") == record.get("author_actor_id"):
                raise SchemaError("review self-attestation is prohibited")
        elif record_class == "stephen_contract_schema_acceptance":
            if record.get("acceptor_actor_id") != caller_id:
                raise SchemaError("caller/body owner identity mismatch")
        elif record_class == "obligation_applicability_confirmation":
            if record.get("confirming_actor_id") != caller_id:
                raise SchemaError("caller/body confirmer identity mismatch")
            if caller_id in {
                record.get("decision_author_actor_id"),
                record.get("prospective_producer_actor_id"),
            }:
                raise SchemaError("applicability self-attestation is prohibited")
        elif record_class == "accepted_assurance_requirement":
            if record.get("acceptor_actor_id") != caller_id:
                raise SchemaError("caller/body acceptor identity mismatch")
            if caller_id in {
                record.get("requirement_author_actor_id"),
                record.get("scope_reviewer_actor_id"),
                record.get("prospective_producer_actor_id"),
            }:
                raise SchemaError("requirement self-attestation is prohibited")
        elif record_class == "independent_pack_review":
            if record.get("reviewer_actor_id") != caller_id:
                raise SchemaError("caller/body reviewer identity mismatch")
            if caller_id == record.get("producer_actor_id"):
                raise SchemaError("pack review self-attestation is prohibited")
        elif record_class == "stephen_owner_acceptance":
            if record.get("acceptor_actor_id") != caller_id:
                raise SchemaError("caller/body owner identity mismatch")
        elif record_class == "active_authority_grant":
            if record.get("actor_id") != caller_id:
                raise SchemaError("caller/body authority-grant actor identity mismatch")

    @staticmethod
    def _publication_action_payload(context: ExternalRecordPublicationContext) -> dict[str, Any]:
        return {
            "schema_id": _PUBLICATION_POLICY_ACTION_SCHEMA_ID,
            "schema_version": _PUBLICATION_POLICY_ACTION_SCHEMA_VERSION,
            "policy_action_type": _PUBLICATION_POLICY_ACTION,
            "project_id": context.project_id,
            "actor_id": context.caller_actor_id,
            "actor_class": context.caller_actor_class,
            "authority_grant_id": context.authority_grant_id,
            "subject_scope": {
                "kind": "external_assurance_record",
                "id": context.record_id,
            },
            "record_class": context.record_class,
            "record_id": context.record_id,
            "record_action": context.record_action,
            "revision": context.revision,
            "expected_previous_revision": context.expected_previous_revision,
            "store_identity": context.store_identity,
            "authority_root": context.authority_root,
            "task_id": context.task_id,
            "session_id": context.session_id,
            "relationship_record_id": context.relationship_record_id,
            "required_risk": context.required_risk,
            "canonical_sha256": context.canonical_sha256,
            "occurred_at": context.occurred_at,
        }

    def _validated_history(
        self,
        *,
        record_class: str,
        record_id: str,
        record: Mapping[str, Any] | None = None,
        resolution_errors: bool = False,
    ) -> tuple[str, str, dict[int, Any]]:
        row = self.catalogue.row(record_class)
        kind, object_id = self._storage_object_key(record_class, record_id, record=record)
        history = load_complete_revision_history(self.objects, kind, object_id)
        for existing in history.values():
            if not isinstance(existing, Mapping):
                if resolution_errors:
                    raise IntegrityError(f"external record is not a record body: {record_id}")
                raise IntegrityError("external record revision history contains a foreign or mismatched identity")
            if existing.get("record_type") != row.record_type or (
                not resolution_errors and existing.get(row.identity_field) != record_id
            ):
                raise IntegrityError("external record revision history contains a foreign or mismatched identity")
            self.catalogue.validate(record_class, record_id, existing)
        return kind, object_id, history

    def resolve_from_storage(
        self,
        *,
        record_class: str,
        record_id: str,
    ) -> ExternalRecordResolution:
        """Resolve the latest schema-valid body using storage-derived metadata."""

        _kind, _object_id, history = self._validated_history(
            record_class=record_class,
            record_id=record_id,
            resolution_errors=True,
        )
        if not history:
            raise ArsError(f"external record has no persisted revision: {record_id}")
        revision = max(history)
        selected_record = history[revision]
        return ExternalRecordResolution(
            record_class=record_class,
            record_id=record_id,
            revision=revision,
            canonical_sha256=sha256_hex(canonical_bytes(selected_record)),
            record=dict(selected_record),
        )

    def _check_revision_policy(
        self,
        *,
        record_class: str,
        record: Mapping[str, Any],
        history: Mapping[int, Any],
        revision: int,
        expected_previous_revision: int,
    ) -> None:
        if revision <= 1:
            return
        allowed = _REVISABLE_RECORD_FIELDS.get(record_class)
        if allowed is None:
            raise ConflictError(
                f"record class {record_class} is immutable after revision 1; create a new semantic identity"
            )
        previous = history.get(expected_previous_revision)
        if not isinstance(previous, Mapping):
            return
        immutable_fields = set(previous) | set(record)
        immutable_fields.difference_update(allowed)
        changed = sorted(field for field in immutable_fields if previous.get(field) != record.get(field))
        if changed:
            raise ConflictError(
                f"record revision changes closed immutable fields for {record_class}: {', '.join(changed)}"
            )

    def _write_storage(
        self,
        *,
        record_class: str,
        record_id: str,
        revision: int,
        expected_previous_revision: int,
        record: Mapping[str, Any],
        publication_context: ExternalRecordPublicationContext | None = None,
    ) -> ExternalAssuranceRecordReceipt:
        """Apply the schema/CAS substrate after governance has been resolved.

        This deliberately private seam is used by resolver/storage contract tests
        and by the future accepted authority resolver.  The public ``write``
        method never reaches it until current publication authority is resolved.
        """

        self._validate_revision_numbers(revision, expected_previous_revision)
        row = self.catalogue.validate(record_class, record_id, record)
        kind, object_id, history = self._validated_history(
            record_class=record_class,
            record_id=record_id,
            record=record,
        )
        latest = max(history) if history else None
        observed = 0 if latest is None else latest
        self._check_revision_policy(
            record_class=record_class,
            record=record,
            history=history,
            revision=revision,
            expected_previous_revision=expected_previous_revision,
        )
        if latest == revision:
            existing = history[revision]
            if existing == dict(record):
                return self._receipt(row, record_id, revision, record, publication_context)
            raise ConflictError("object revision already exists with different content")
        if observed != expected_previous_revision:
            raise ConflictError(f"expected previous revision {expected_previous_revision}, observed {observed}")
        self.objects.write(kind, object_id, revision, dict(record))
        return self._receipt(row, record_id, revision, record, publication_context)

    def _resolve_current_publication_authority(
        self,
        context: ExternalRecordPublicationContext,
        *,
        record: Mapping[str, Any],
    ) -> None:
        """Resolve the exact publication action from replayed authority in-lock."""

        del record

        if self._authority_schemas is None or self._authority_resolver is None:
            self._authority_schemas = runtime_schema_registry(self.binding.schema_root)
            self._authority_resolver = LedgerAuthorityGrantResolver(
                self.binding.control_root,
                self.binding.project_id,
                self.binding.store_identity,
                self._authority_schemas,
                approved_witness=self.binding.origin_witness,
                approved_witness_path=self.binding.origin_witness_path,
            )
        action = self._publication_action_payload(context)
        self._authority_schemas.validate_active(
            _PUBLICATION_POLICY_ACTION_SCHEMA_ID,
            action,
            schema_version=_PUBLICATION_POLICY_ACTION_SCHEMA_VERSION,
        )
        administration = self._authority_resolver.administration_context()
        if (
            administration.project_id != self.binding.project_id
            or administration.store_identity != self.binding.store_identity
            or context.authority_root != administration.root_grant_id
        ):
            raise ArsError("publication authority root or store binding mismatch")
        policy = self._authority_schemas.resolve_identity(
            _PUBLICATION_POLICY_ACTION_SCHEMA_ID,
            _PUBLICATION_POLICY_ACTION_SCHEMA_VERSION,
        )
        try:
            authority_time = self._clock()
        except Exception as exc:  # noqa: BLE001 - a failed trusted clock must fail closed
            raise IntegrityError("trusted publication clock failed") from exc
        if (
            not isinstance(authority_time, datetime)
            or authority_time.tzinfo is None
            or authority_time.utcoffset() is None
        ):
            raise IntegrityError("trusted publication clock must return a timezone-aware datetime")
        self._authority_resolver.resolve_policy_action(
            context.authority_grant_id,
            context.caller_actor_id,
            context.caller_actor_class,
            GrantedPolicyActionIdentity(
                _PUBLICATION_POLICY_ACTION,
                policy.schema_id,
                policy.schema_version,
                policy.sha256,
            ),
            context.required_risk,
            context.project_id,
            "external_assurance_record",
            context.record_id,
            authority_time.astimezone(timezone.utc),
        )

    def write(
        self,
        *,
        record_class: str,
        record_id: str,
        revision: int,
        expected_previous_revision: int,
        record: Mapping[str, Any],
        publication_context: ExternalRecordPublicationContext | None = None,
    ) -> ExternalAssuranceRecordReceipt:
        """Validate attribution, lock, re-resolve authority, then publish by CAS."""

        if publication_context is None:
            raise SchemaError("external record publication context is required")
        self._validate_revision_numbers(revision, expected_previous_revision)
        self.catalogue.validate(record_class, record_id, record)
        self._validate_publication_context(
            context=publication_context,
            record_class=record_class,
            record_id=record_id,
            revision=revision,
            expected_previous_revision=expected_previous_revision,
            record=record,
        )
        with WriterLock(
            self.binding.control_root / "runtime" / "writer.lock",
            {
                "operation": "external_record_publication",
                "record_class": record_class,
                "record_id": record_id,
                "revision": str(revision),
                "session_id": publication_context.session_id,
                "record_action": publication_context.record_action,
                "authority_grant_id": publication_context.authority_grant_id,
                "canonical_sha256": publication_context.canonical_sha256,
            },
        ):
            self._resolve_current_publication_authority(publication_context, record=record)
            return self._write_storage(
                record_class=record_class,
                record_id=record_id,
                revision=revision,
                expected_previous_revision=expected_previous_revision,
                record=record,
                publication_context=publication_context,
            )
