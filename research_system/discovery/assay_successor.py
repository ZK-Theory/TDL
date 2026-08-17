"""Govern one immutable Assay authority-successor document."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConfigurationError
from research_system.git_execution import run_git
from research_system.schema_registry import SchemaRegistry

if TYPE_CHECKING:
    from research_system.methods.registration import (
        CandidateDocumentStore,
        CandidateRegistration,
        CommandSubmitter,
        RegisteredCandidate,
    )


SCHEMA_ID = "ars://portfolio/assay-authority-successor"
DOCUMENT_TYPE = "assay_authority_successor"
ROUTE_PATH = ".research-system/contracts/wp6-6/spec-gate6-run-v1/route-package.json"
SPEC_01_PATH = ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-01-assay-brief-v1.1.0.md"
RUBRIC_V2_PATH = ".research-system/contracts/wp6-6/assay-rubric-content-v2.json"
SCOPE_V2_PATH = ".research-system/contracts/wp6-6/assay-evidence-scope-content-v2.json"
RUBRIC_V1_PATH = ".research-system/contracts/wp6-6/assay-rubric-content-v1.json"
SCOPE_V1_PATH = ".research-system/contracts/wp6-6/assay-evidence-scope-content-v1.json"
CORRECTION_SCHEMA_ID = "ars://portfolio/spec-01-source-correction"
_ACTOR_ID = re.compile(r"^act_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_SUCCESSOR_ID = re.compile(r"^assay-authority-successor:[a-z0-9._:-]+$")
_RULE_HASH_FIELDS = (
    "evaluation_order",
    "recommendation_predicates",
    "hard_gate_predicates",
    "partial_predicates",
    "park_predicates",
    "kill_predicates",
    "rule_evaluation_algorithm_id",
    "rule_evaluation_algorithm_version",
)
_EVIDENCE_ROW_HASH_FIELDS = (
    "evidence_key",
    "allowed_source_classes",
    "identity_requirement",
    "closure_requirement",
    "producer_requirement",
    "freshness_or_event_position",
    "validator_id",
    "validator_version",
    "independent_review_grade",
    "permitted_omissions",
    "unmet_reason_codes",
)
_SCOPE_HASH_FIELDS = (
    "scope_id",
    "rubric_ref",
    "required_assurance_lanes",
    "evidence_rows",
    "prohibited_source_classes",
    "prohibited_producer_relationships",
    "no_compensation_pairs",
    "confidentiality_rules",
    "stop_conditions",
    "partial_conditions",
    "evidence_order_constraints",
    "scope_closure_algorithm_id",
    "scope_closure_algorithm_version",
    "effective_candidate_kinds",
    "effective_project_scope_ref",
)


def _git(root: Path, *arguments: str, text: bool = True) -> str | bytes:
    result = run_git(
        root,
        *arguments,
        text=text,
        unavailable_message="Assay authority successor Git binding is unavailable",
    )
    if result.returncode != 0:
        raise ConfigurationError("Assay authority successor Git binding is unavailable")
    if text:
        return result.stdout.strip()
    return bytes(result.stdout)


def _canonical_relative_path(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"{label} path is invalid")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ConfigurationError(f"{label} path is invalid")
    return value


def _committed_bytes(root: Path, commit: str, relative_path: str, label: str) -> bytes:
    path = _canonical_relative_path(relative_path, label)
    raw = _git(root, "show", f"{commit}:{path}", text=False)
    if not isinstance(raw, bytes):
        raise ConfigurationError(f"{label} Git bytes are invalid")
    return raw


def _record_ref(content: Mapping[str, Any], *, repository_path: str | None = None) -> dict[str, Any]:
    value = {
        "id": content.get("record_id"),
        "record_revision": content.get("record_revision"),
        "content_hash": content.get("content_hash"),
    }
    if repository_path is not None:
        value["repository_path"] = repository_path
    return value


def _validate_self_and_derived_hashes(kind: str, content: Mapping[str, Any]) -> None:
    preimage = dict(content)
    declared_hash = preimage.pop("content_hash", None)
    if declared_hash != sha256_hex(canonical_bytes(preimage)):
        raise ValueError(f"successor {kind} self-hash differs")
    if kind == "rubric":
        if content.get("required_axis_set_hash") != sha256_hex(
            canonical_bytes(sorted(content.get("required_axis_ids", [])))
        ) or content.get("rule_evaluation_algorithm_hash") != _projection_hash(content, _RULE_HASH_FIELDS):
            raise ValueError("successor rubric derived hash differs")
        return
    evidence_rows = content.get("evidence_rows")
    if (
        not isinstance(evidence_rows, list)
        or any(not isinstance(row, Mapping) for row in evidence_rows)
        or any(row.get("validator_hash") != _projection_hash(row, _EVIDENCE_ROW_HASH_FIELDS) for row in evidence_rows)
    ):
        raise ValueError("successor scope evidence-row hash differs")
    if content.get("scope_closure_algorithm_hash") != _projection_hash(content, _SCOPE_HASH_FIELDS):
        raise ValueError("successor scope closure hash differs")


def _validate_ref_sequence(
    predecessor: object,
    successor: object,
    *,
    governed_hashes: Mapping[str, str],
    label: str,
) -> None:
    if not isinstance(predecessor, list) or not isinstance(successor, list) or len(predecessor) != len(successor):
        raise ValueError(f"successor {label} changes protected semantics")
    for old, new in zip(predecessor, successor, strict=True):
        if not isinstance(old, Mapping) or not isinstance(new, Mapping) or set(old) != set(new):
            raise ValueError(f"successor {label} changes protected semantics")
        old_core = {key: value for key, value in old.items() if key != "content_hash"}
        new_core = {key: value for key, value in new.items() if key != "content_hash"}
        if old_core != new_core:
            raise ValueError(f"successor {label} changes protected semantics")
        record_id = old.get("id")
        if record_id in governed_hashes:
            if new.get("content_hash") != governed_hashes[record_id]:
                raise ValueError(f"successor {label} governed source binding differs")
        elif new != old:
            raise ValueError(f"successor {label} changes protected semantics")


def validate_successor_authority_semantics(
    *,
    predecessor_rubric: Mapping[str, Any],
    predecessor_scope: Mapping[str, Any],
    successor_rubric: Mapping[str, Any],
    successor_scope: Mapping[str, Any],
    governed_hashes: Mapping[str, str],
) -> None:
    """Prove revision two is a field-level identity-preserving source refresh."""

    for kind, predecessor, successor in (
        ("rubric", predecessor_rubric, successor_rubric),
        ("scope", predecessor_scope, successor_scope),
    ):
        _validate_self_and_derived_hashes(kind, successor)
        if (
            successor.get("record_id") != predecessor.get("record_id")
            or successor.get("record_revision") != predecessor.get("record_revision", 0) + 1
            or successor.get("supersedes_revision") != predecessor.get("record_revision")
            or successor.get("content_hash") == predecessor.get("content_hash")
        ):
            raise ValueError(f"successor {kind} lineage differs")
        project_old = predecessor.get("effective_project_scope_ref")
        project_new = successor.get("effective_project_scope_ref")
        if not isinstance(project_old, Mapping) or not isinstance(project_new, Mapping):
            raise ValueError(f"successor {kind} changes protected semantics")
        if {key: value for key, value in project_old.items() if key != "content_hash"} != {
            key: value for key, value in project_new.items() if key != "content_hash"
        } or project_new.get("content_hash") != governed_hashes.get("SPEC-GATE6-RUN-V1"):
            raise ValueError(f"successor {kind} project-scope binding differs")
        _validate_ref_sequence(
            predecessor.get("source_refs"),
            successor.get("source_refs"),
            governed_hashes=governed_hashes,
            label=f"{kind} source refs",
        )
    _validate_ref_sequence(
        predecessor_rubric.get("source_authority_refs"),
        successor_rubric.get("source_authority_refs"),
        governed_hashes=governed_hashes,
        label="rubric source-authority refs",
    )
    if successor_scope.get("rubric_ref") != _record_ref(successor_rubric):
        raise ValueError("successor scope does not bind the successor rubric")

    common_allowed = {
        "content_hash",
        "created_at",
        "created_by_actor_id",
        "effective_project_scope_ref",
        "record_revision",
        "source_refs",
        "supersedes_revision",
    }
    rubric_allowed = common_allowed | {"source_authority_refs"}
    scope_allowed = common_allowed | {"rubric_ref", "scope_closure_algorithm_hash"}
    for kind, predecessor, successor, allowed in (
        ("rubric", predecessor_rubric, successor_rubric, rubric_allowed),
        ("scope", predecessor_scope, successor_scope, scope_allowed),
    ):
        if {key: value for key, value in predecessor.items() if key not in allowed} != {
            key: value for key, value in successor.items() if key not in allowed
        }:
            raise ValueError(f"successor {kind} changes protected semantics")


def validate_assay_authority_successor_document(
    value: Mapping[str, Any],
    *,
    registration: CandidateRegistration,
    repository_root: Path,
    schemas: SchemaRegistry,
) -> dict[str, Any]:
    """Validate one successor document against exact committed authority bytes."""

    document = dict(value)
    schemas.validate(SCHEMA_ID, document, schema_version="1.0.0")
    schemas.validate(CORRECTION_SCHEMA_ID, document["source_correction_document"], schema_version="1.0.0")
    if (
        sha256_hex(canonical_bytes(document["source_correction_document"]))
        != document["source_correction_ref"]["content_hash"]
    ):
        raise ConfigurationError("Assay authority successor correction binding differs")
    manifest = registration.manifest
    if (
        document.get("producer_actor_id") != registration.actor_id
        or manifest.get("artefact_id") != registration.artefact_id
        or manifest.get("artefact_type") != DOCUMENT_TYPE
        or manifest.get("artefact_schema_id") != SCHEMA_ID
        or manifest.get("artefact_schema_version") != "1.0.0"
        or manifest.get("producer_actor_id") != registration.actor_id
    ):
        raise ConfigurationError("Assay authority successor registration binding differs")

    root = repository_root.resolve(strict=True)
    top = _git(root, "rev-parse", "--show-toplevel")
    head = _git(root, "rev-parse", "HEAD")
    if Path(str(top)).resolve(strict=True) != root or document.get("git_commit") != head:
        raise ConfigurationError("Assay authority successor Git subject differs")
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none"):
        raise ConfigurationError("Assay authority successor repository is not clean")

    governed_sources = document["governed_sources"]
    expected_source_paths = {"route": ROUTE_PATH, "spec_01": SPEC_01_PATH}
    for kind, expected_path in expected_source_paths.items():
        source_ref = governed_sources[kind]
        if source_ref.get("repository_path") != expected_path:
            raise ConfigurationError("Assay authority successor source path differs")
        raw = _committed_bytes(root, str(head), expected_path, f"{kind} source")
        if source_ref.get("content_sha256") != sha256_hex(raw):
            raise ConfigurationError("Assay authority successor source hash differs")

    accepted = document["accepted_authority"]
    successor = document["successor_authority"]
    decoded: dict[str, dict[str, Any]] = {}
    predecessors: dict[str, dict[str, Any]] = {}
    for kind in ("rubric", "scope"):
        successor_ref = successor[f"{kind}_ref"]
        raw = _committed_bytes(root, str(head), successor_ref["repository_path"], f"successor {kind}")
        try:
            content = json.loads(raw)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ConfigurationError(f"successor {kind} content is invalid") from exc
        if raw not in {canonical_bytes(content), canonical_bytes(content) + b"\n"}:
            raise ConfigurationError(f"successor {kind} content is not canonical JSON")
        schemas.validate(
            "ars://portfolio/assay-rubric-content"
            if kind == "rubric"
            else "ars://portfolio/assay-evidence-scope-content",
            content,
            schema_version="1.0.0",
        )
        if _record_ref(content, repository_path=successor_ref["repository_path"]) != successor_ref:
            raise ConfigurationError(f"successor {kind} content binding differs")
        if successor.get(f"{kind}_content") != content:
            raise ConfigurationError(f"successor {kind} embedded content differs")
        predecessor_ref = accepted[f"{kind}_ref"]
        if (
            content.get("record_revision") != predecessor_ref.get("record_revision") + 1
            or content.get("supersedes_revision") != predecessor_ref.get("record_revision")
            or content.get("record_id") != predecessor_ref.get("id")
            or content.get("content_hash") == predecessor_ref.get("content_hash")
        ):
            raise ConfigurationError(f"successor {kind} lineage differs")
        predecessor_path = RUBRIC_V1_PATH if kind == "rubric" else SCOPE_V1_PATH
        try:
            predecessor = json.loads(_committed_bytes(root, str(head), predecessor_path, f"predecessor {kind}"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ConfigurationError(f"predecessor {kind} content is invalid") from exc
        schemas.validate(
            "ars://portfolio/assay-rubric-content"
            if kind == "rubric"
            else "ars://portfolio/assay-evidence-scope-content",
            predecessor,
            schema_version="1.0.0",
        )
        if _record_ref(predecessor) != predecessor_ref:
            raise ConfigurationError(f"accepted {kind} binding differs")
        decoded[kind] = content
        predecessors[kind] = predecessor
    if (
        decoded["rubric"].get("created_by_actor_id") != document["producer_actor_id"]
        or decoded["scope"].get("created_by_actor_id") != document["producer_actor_id"]
    ):
        raise ConfigurationError("successor authority producer differs")
    source_hashes = {
        "SPEC-GATE6-RUN-V1": governed_sources["route"]["content_sha256"],
        "SPEC-01": governed_sources["spec_01"]["content_sha256"],
    }
    try:
        validate_successor_authority_semantics(
            predecessor_rubric=predecessors["rubric"],
            predecessor_scope=predecessors["scope"],
            successor_rubric=decoded["rubric"],
            successor_scope=decoded["scope"],
            governed_hashes=source_hashes,
        )
    except ValueError as exc:
        raise ConfigurationError(str(exc)) from exc
    return document


def register_assay_authority_successor_document(
    *,
    value: dict[str, Any],
    registration: CandidateRegistration,
    document_store: CandidateDocumentStore,
    command_service: CommandSubmitter,
    repository_root: Path,
    schemas: SchemaRegistry,
) -> RegisteredCandidate:
    """Validate, register, and immutably publish one authority-successor document."""

    from research_system.methods.registration import register_candidate_document

    document = validate_assay_authority_successor_document(
        value,
        registration=registration,
        repository_root=repository_root,
        schemas=schemas,
    )
    return register_candidate_document(
        value=document,
        registration=registration,
        document_store=document_store,
        command_service=command_service,
    )


def successor_document_hashes(value: object) -> dict[str, str]:
    """Return the two successor hashes from an exact closed document shape."""

    if not isinstance(value, Mapping) or set(value) != {
        "schema_id",
        "schema_version",
        "document_type",
        "successor_id",
        "route_id",
        "created_at",
        "producer_actor_id",
        "source_correction_ref",
        "source_correction_document",
        "accepted_authority",
        "successor_authority",
        "governed_sources",
        "git_commit",
    }:
        raise ValueError("invalid Assay authority successor document")
    if (
        value.get("schema_id") != SCHEMA_ID
        or value.get("schema_version") != "1.0.0"
        or value.get("document_type") != DOCUMENT_TYPE
        or value.get("route_id") != "SPEC-GATE6-RUN-V1"
        or not isinstance(value.get("successor_id"), str)
        or _SUCCESSOR_ID.fullmatch(value["successor_id"]) is None
        or not _utc_timestamp(value.get("created_at"))
        or not isinstance(value.get("producer_actor_id"), str)
        or _ACTOR_ID.fullmatch(value["producer_actor_id"]) is None
        or not _lowercase_hex(value.get("git_commit"), 40)
        or not _valid_record_ref(value.get("source_correction_ref"))
        or not isinstance(value.get("source_correction_document"), Mapping)
        or sha256_hex(canonical_bytes(value["source_correction_document"]))
        != value["source_correction_ref"]["content_hash"]
    ):
        raise ValueError("invalid Assay authority successor document")
    accepted = value.get("accepted_authority")
    successor = value.get("successor_authority")
    governed_sources = value.get("governed_sources")
    if (
        not isinstance(accepted, Mapping)
        or set(accepted) != {"rubric_ref", "scope_ref"}
        or not isinstance(successor, Mapping)
        or set(successor) != {"rubric_ref", "rubric_content", "scope_ref", "scope_content"}
        or not isinstance(governed_sources, Mapping)
        or set(governed_sources) != {"route", "spec_01"}
        or not _valid_file_ref(governed_sources.get("route"), ROUTE_PATH)
        or not _valid_file_ref(governed_sources.get("spec_01"), SPEC_01_PATH)
    ):
        raise ValueError("invalid Assay authority successor document")
    hashes: dict[str, str] = {}
    successor_paths = {"rubric": RUBRIC_V2_PATH, "scope": SCOPE_V2_PATH}
    for kind in ("rubric", "scope"):
        old_ref = accepted.get(f"{kind}_ref")
        new_ref = successor.get(f"{kind}_ref")
        embedded = successor.get(f"{kind}_content")
        if (
            not _valid_record_ref(old_ref)
            or not isinstance(new_ref, Mapping)
            or set(new_ref) != {"id", "record_revision", "content_hash", "repository_path"}
            or new_ref.get("repository_path") != successor_paths[kind]
            or old_ref.get("id") != new_ref.get("id")
            or type(old_ref.get("record_revision")) is not int
            or new_ref.get("record_revision") != old_ref.get("record_revision") + 1
            or not _lowercase_hex(new_ref.get("content_hash"), 64)
            or new_ref.get("content_hash") == old_ref.get("content_hash")
            or not isinstance(embedded, Mapping)
            or _record_ref(embedded, repository_path=successor_paths[kind]) != new_ref
        ):
            raise ValueError("invalid Assay authority successor document")
        hashes[kind] = str(new_ref["content_hash"])
    return hashes


def _lowercase_hex(value: object, length: int) -> bool:
    return (
        isinstance(value, str) and len(value) == length and all(character in "0123456789abcdef" for character in value)
    )


def _projection_hash(value: Mapping[str, Any], fields: tuple[str, ...]) -> str:
    try:
        projection = {field: value[field] for field in fields}
    except KeyError as exc:
        raise ConfigurationError("successor authority derived-hash input is missing") from exc
    return sha256_hex(canonical_bytes(projection))


def _utc_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError:
        return False
    return parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0


def _valid_record_ref(value: object) -> bool:
    return bool(
        isinstance(value, Mapping)
        and set(value) == {"id", "record_revision", "content_hash"}
        and isinstance(value.get("id"), str)
        and value["id"]
        and type(value.get("record_revision")) is int
        and value["record_revision"] >= 1
        and _lowercase_hex(value.get("content_hash"), 64)
    )


def _valid_file_ref(value: object, expected_path: str) -> bool:
    return bool(
        isinstance(value, Mapping)
        and set(value) == {"repository_path", "content_sha256"}
        and value.get("repository_path") == expected_path
        and _lowercase_hex(value.get("content_sha256"), 64)
    )


__all__ = [
    "DOCUMENT_TYPE",
    "ROUTE_PATH",
    "RUBRIC_V2_PATH",
    "SCHEMA_ID",
    "SCOPE_V2_PATH",
    "SPEC_01_PATH",
    "register_assay_authority_successor_document",
    "successor_document_hashes",
    "validate_successor_authority_semantics",
    "validate_assay_authority_successor_document",
]
