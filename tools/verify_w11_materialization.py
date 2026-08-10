"""Non-runtime verifier for the inert W11 materialization surface.

This module is deliberately outside ``research_system``.  It validates the
W11 cross-field rules only when a caller supplies an explicit subject envelope,
and it has no runtime binding, handler, store, ledger, reducer, or projection
authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil

# Required for the narrow argv-only Git identity checks below; shell=False is explicit.
import subprocess  # nosec B404
from collections.abc import Callable, Iterable, Mapping, Sequence
from math import isfinite
from pathlib import Path
from typing import Any, NoReturn

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import SchemaError
from research_system.schema_registry import SchemaRegistry


W11_MATERIALIZATION_BASE = "c84eb2aaf0890d36d3735d08a14169f4c50935cd"
W11_FOUNDATION_COMMIT = "21fe265736834263e9c3094c89fc6a390670be7b"
W11_CONSTRUCTION_BASE = "516cc5320a2c09255414b94d5db7786dd12208df"
W11_SPECIFICATION_COMMIT = "892d1d1650cdcf71d2a886318e174a18e11d5de0"
W11_SPECIFICATION_PATH = "docs/plans/agentic-research-system/design/11-portfolio-and-discovery-lifecycle.md"
W11_SPECIFICATION_BLOB = "f90729d0c42a0de98d064fac0824d1969c871c82"
W11_SPECIFICATION_SHA256 = "65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70"
W11_SPECIFICATION_BYTES = 185214
W11_BOOTSTRAP_PATH = ".research-system/contracts/w11/w11-materialization-bootstrap-contract.yaml"
W11_BOOTSTRAP_SHA256 = "ebb7529a3bbf8faea9101b1556b3b71e6e0b3b9dbe0df163591466903d569d38"
W11_CATALOGUE_RECORD_ID = "obj_00000000-0000-7000-8000-000000000003"
W11_CATALOGUE_PROJECT_ID = "prj_00000000-0000-7000-8000-000000000001"
W11_EXPECTED_SOURCE_ACTOR_ID = "act_00000000-0000-7000-8000-000000000001"
_ENVELOPE_FIELDS = frozenset({"base_commit", "subject_commit", "subject_tree", "changed_paths"})
_PATH_ENTRY_FIELDS = frozenset({"path", "blob"})
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_OBJ_ID_RE = re.compile(r"^obj_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_ART_ID_RE = re.compile(r"^art_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_GIT_EXECUTABLE = shutil.which("git")
if _GIT_EXECUTABLE is not None:
    _GIT_EXECUTABLE = str(Path(_GIT_EXECUTABLE).resolve())

W11_CONTENT_SCHEMA_IDS = frozenset(
    {
        "ars://portfolio/programme",
        "ars://portfolio/paper",
        "ars://portfolio/hypothesis",
        "ars://portfolio/candidate",
        "ars://portfolio/method",
        "ars://portfolio/dataset",
        "ars://portfolio/claim",
        "ars://portfolio/dependency-edge",
        "ars://portfolio/assay-rubric-content",
        "ars://portfolio/assay-evidence-scope-content",
        "ars://portfolio/path-registration-content",
        "ars://portfolio/dossier-expected-set-content",
        "ars://portfolio/legacy-source-inventory-content",
        "ars://portfolio/legacy-transition-mapping-content",
        "ars://portfolio/legacy-cutover-closure-content",
        "ars://portfolio/w11-schema-catalogue-content",
    }
)
W11_SCHEMA_CATALOGUE_SCHEMA_ID = "ars://portfolio/w11-schema-catalogue-content"
W11_DOSSIER_EXPECTED_SET_SCHEMA_ID = "ars://portfolio/dossier-expected-set-content"
W11_ASSAY_RUBRIC_SCHEMA_ID = "ars://portfolio/assay-rubric-content"
W11_ASSAY_SCORECARD_SCHEMA_ID = "ars://portfolio/assay-scorecard"

_OWNER_ROW_IDS = frozenset(
    {*(f"OR-{number:03d}" for number in range(1, 42)), *(f"OR-{number:03d}" for number in range(101, 141))}
)
_DOSSIER_EXPECTED_SET_FAMILIES = (
    ("components", "component_count", "component_multiset_hash", "component_key"),
    ("sources", "source_count", "source_multiset_hash", "source_key"),
    ("objects", "object_count", "object_multiset_hash", "object_key"),
    ("scope_definitions", "scope_count", "scope_multiset_hash", "scope_key"),
    ("dependency_edges", "edge_count", "edge_multiset_hash", "edge_key"),
    ("relationships", "relationship_count", "relationship_multiset_hash", "relationship_key"),
)

_SCHEMA_SOURCE_ROOT = ".research-system/schemas/contracts/w11"
_SCHEMA_SOURCE_FAMILIES = (
    (
        "content",
        "ars://portfolio/",
        "",
        (
            "programme",
            "paper",
            "hypothesis",
            "candidate",
            "method",
            "dataset",
            "claim",
            "dependency-edge",
            "assay-rubric-content",
            "assay-evidence-scope-content",
            "path-registration-content",
            "dossier-expected-set-content",
            "legacy-source-inventory-content",
            "legacy-transition-mapping-content",
            "legacy-cutover-closure-content",
            "w11-schema-catalogue-content",
        ),
    ),
    (
        "relation",
        "ars://portfolio/relation/",
        "relation-",
        (
            "candidate",
            "assay",
            "spike",
            "assay-request",
            "assay-producer",
            "assay-bar-acceptance",
            "assay-outcome-review",
            "assay-cancellation-review",
            "spike-plan",
            "spike-attempt",
            "spike-outcome-review",
            "spike-cancellation-review",
            "discovery-promotion",
            "discovery-revisit",
            "authority-content-file-review-acceptance",
            "spike-execution-authority",
            "dossier-expected-set-acceptance",
            "path-registration-acceptance",
            "legacy-source-inventory-acceptance",
            "migration-authority",
            "legacy-path-cutover",
            "dossier-six-family-closure",
            "legacy-source-row-observation",
            "legacy-source-row-target",
            "inventory-mapping-transition-bijection",
            "path-physical-identity",
            "writer-revocation",
            "cutover-closure",
        ),
    ),
    (
        "artefact",
        "ars://portfolio/",
        "",
        (
            "assay-scorecard",
            "assay-partial",
            "spike-plan",
            "spike-verdict",
            "scout-observation-batch",
            "discovery-annotation",
            "research-dossier-manifest",
            "legacy-record-observed",
            "legacy-portfolio-path-observation",
            "authority-file-observation",
            "review-evidence",
            "collision-scan",
            "writer-revocation-snapshot",
            "projection-rebuild-proof",
        ),
    ),
    (
        "bootstrap",
        "ars://portfolio/",
        "",
        (
            "w11-catalogue-acceptance-envelope",
            "w11-materialization-bootstrap-contract",
            "import-accepted-w11-catalogue-genesis",
        ),
    ),
)
_EXPECTED_SCHEMA_SOURCE_CLOSURE = frozenset(
    (
        f"{family}:{kind}",
        f"{schema_prefix}{kind}",
        f"{_SCHEMA_SOURCE_ROOT}/{filename_prefix}{kind}.schema.json",
    )
    for family, schema_prefix, filename_prefix, kinds in _SCHEMA_SOURCE_FAMILIES
    for kind in kinds
)

_W11_CONTENT_SCHEMA_KEYS = (
    "programme",
    "paper",
    "hypothesis",
    "candidate",
    "method",
    "dataset",
    "claim",
    "dependency-edge",
    "assay-rubric-content",
    "assay-evidence-scope-content",
    "path-registration-content",
    "dossier-expected-set-content",
    "legacy-source-inventory-content",
    "legacy-transition-mapping-content",
    "legacy-cutover-closure-content",
    "w11-schema-catalogue-content",
)
_W11_RELATION_SCHEMA_KEYS = (
    "candidate",
    "assay",
    "spike",
    "assay-request",
    "assay-producer",
    "assay-bar-acceptance",
    "assay-outcome-review",
    "assay-cancellation-review",
    "spike-plan",
    "spike-attempt",
    "spike-outcome-review",
    "spike-cancellation-review",
    "discovery-promotion",
    "discovery-revisit",
    "authority-content-file-review-acceptance",
    "spike-execution-authority",
    "dossier-expected-set-acceptance",
    "path-registration-acceptance",
    "legacy-source-inventory-acceptance",
    "migration-authority",
    "legacy-path-cutover",
    "dossier-six-family-closure",
    "legacy-source-row-observation",
    "legacy-source-row-target",
    "inventory-mapping-transition-bijection",
    "path-physical-identity",
    "writer-revocation",
    "cutover-closure",
)
_W11_ARTEFACT_SCHEMA_KEYS = (
    "assay-scorecard",
    "assay-partial",
    "spike-plan",
    "spike-verdict",
    "scout-observation-batch",
    "discovery-annotation",
    "research-dossier-manifest",
    "legacy-record-observed",
    "legacy-portfolio-path-observation",
    "authority-file-observation",
    "review-evidence",
    "collision-scan",
    "writer-revocation-snapshot",
    "projection-rebuild-proof",
)
_W11_BOOTSTRAP_SCHEMA_KEYS = (
    "w11-catalogue-acceptance-envelope",
    "w11-materialization-bootstrap-contract",
    "import-accepted-w11-catalogue-genesis",
)
_W11_SCHEMA_PATHS = tuple(sorted(row[2] for row in _EXPECTED_SCHEMA_SOURCE_CLOSURE))
_W11_SCHEMA_LOGICAL_KEYS = {row[2]: row[0] for row in _EXPECTED_SCHEMA_SOURCE_CLOSURE}
_W11_SCHEMA_ROOT = ".research-system/schemas/contracts/w11"
_W11_EVENT_PATTERN = re.compile(r"W2\s+`([^`]+)`|E:[A-Za-z0-9_/-]+")
_W11_EVENT_CLEANUP_PATTERN = re.compile(r"W2\s+`[^`]+`|`?E:[A-Za-z0-9_/-]+`?")
_W11_COMMAND_PATTERN = re.compile(r"`([^`]+)`")
_W11_COMMAND_SCHEMA_PATTERN = re.compile(r"\(\s*`C:([^`]+)`\s*\)")

ReferenceValidator = Callable[[str, Mapping[str, Any]], None]


class MaterializationVerificationError(ValueError):
    """Raised when an external subject envelope is incomplete or inconsistent."""


def verify_subject_envelope(repo_root: Path, envelope: Mapping[str, Any]) -> None:
    """Verify one caller-supplied exact subject envelope against Git objects.

    The verifier does not infer a subject from the process environment, the
    working copy, or a symbolic ref.  The envelope must name the base commit,
    subject commit, subject tree, and the complete changed-path/blob manifest.
    """
    if not isinstance(envelope, Mapping) or set(envelope) != _ENVELOPE_FIELDS:
        _envelope_error("envelope fields must be exactly base_commit, subject_commit, subject_tree, changed_paths")

    base_commit = _require_sha1(envelope["base_commit"], "base_commit")
    subject_commit = _require_sha1(envelope["subject_commit"], "subject_commit")
    subject_tree = _require_sha1(envelope["subject_tree"], "subject_tree")
    if base_commit != W11_MATERIALIZATION_BASE:
        _envelope_error(f"base_commit must be {W11_MATERIALIZATION_BASE}")

    changed_paths = envelope["changed_paths"]
    if not isinstance(changed_paths, list) or not changed_paths:
        _envelope_error("changed_paths must be a non-empty list")

    manifest: dict[str, str] = {}
    for index, entry in enumerate(changed_paths):
        if not isinstance(entry, Mapping) or set(entry) != _PATH_ENTRY_FIELDS:
            _envelope_error(f"changed_paths[{index}] must contain exactly path and blob")
        path = entry["path"]
        blob = entry["blob"]
        if not isinstance(path, str) or not _is_repository_relative_path(path):
            _envelope_error(f"changed_paths[{index}] has an invalid repository path")
        if not isinstance(blob, str) or _SHA1_RE.fullmatch(blob) is None:
            _envelope_error(f"changed_paths[{index}] has an invalid blob ID")
        if path in manifest:
            _envelope_error(f"changed_paths contains duplicate path {path}")
        manifest[path] = blob

    if list(manifest) != sorted(manifest):
        _envelope_error("changed_paths must be sorted by path")

    actual_base = _git(repo_root, "rev-parse", "--verify", f"{base_commit}^{{commit}}")
    actual_subject = _git(repo_root, "rev-parse", "--verify", f"{subject_commit}^{{commit}}")
    actual_tree = _git(repo_root, "rev-parse", "--verify", f"{subject_commit}^{{tree}}")
    if actual_base != base_commit:
        _envelope_error("base_commit does not resolve to the named commit")
    if actual_subject != subject_commit:
        _envelope_error("subject_commit does not resolve to the named commit")
    if actual_tree != subject_tree:
        _envelope_error("subject_tree does not match subject_commit")
    if not _is_ancestor(repo_root, base_commit, subject_commit):
        _envelope_error("base_commit must be an ancestor of subject_commit")

    changed_output = _git(repo_root, "diff", "--name-only", "--no-renames", base_commit, subject_commit)
    actual_paths = {line for line in changed_output.splitlines() if line}
    observed_paths = set(manifest)
    if observed_paths != actual_paths:
        missing = sorted(actual_paths - observed_paths)
        extra = sorted(observed_paths - actual_paths)
        _envelope_error(f"changed path set mismatch; missing={missing}, extra={extra}")

    for path, expected_blob in manifest.items():
        actual_blob = _git(repo_root, "rev-parse", "--verify", f"{subject_commit}:{path}")
        object_type = _git(repo_root, "cat-file", "-t", actual_blob)
        if object_type != "blob":
            _envelope_error(f"changed path {path} does not resolve to a blob")
        if actual_blob != expected_blob:
            _envelope_error(f"blob mismatch for {path}: expected {expected_blob}, got {actual_blob}")


def verify_materialization_document(
    schema_root: Path,
    schema_id: str,
    value: Any,
    *,
    reference_documents: Iterable[Mapping[str, Any]] = (),
) -> None:
    """Validate one materialized document through the inert verifier seam."""
    registry = _registry_for_root(schema_root)

    def validate_reference(reference_schema_id: str, reference: Mapping[str, Any]) -> None:
        reference_version = reference.get("schema_version")
        registry.validate(
            reference_schema_id,
            reference,
            schema_version=reference_version if isinstance(reference_version, str) else None,
        )
        verify_w11_document(
            reference_schema_id,
            reference,
            reference_documents=(),
            validate_reference=None,
        )

    registry.validate(
        schema_id, value, schema_version=value.get("schema_version") if isinstance(value, Mapping) else None
    )
    verify_w11_document(
        schema_id,
        value,
        reference_documents=reference_documents,
        validate_reference=validate_reference,
    )


def verify_expected_catalogue(
    repo_root: Path,
    value: Mapping[str, Any],
    *,
    schema_root: Path | None = None,
) -> None:
    """Admit one static W11 catalogue against the accepted independent sources.

    The catalogue is the expected side of the W11 gate.  This function resolves
    the accepted specification and the exact foundation schema bytes through
    Git, compares complete records one-to-one, and never imports a runtime
    registry or implementation enumeration.
    """
    if not isinstance(value, Mapping):
        _invalid(W11_SCHEMA_CATALOGUE_SCHEMA_ID, "catalogue must be an object")

    resolved_schema_root = schema_root or (repo_root / _W11_SCHEMA_ROOT)
    verify_materialization_document(resolved_schema_root, W11_SCHEMA_CATALOGUE_SCHEMA_ID, value)

    expected_source_refs = _expected_source_refs(repo_root)
    _require_catalogue(
        value.get("created_by_actor_id") == W11_EXPECTED_SOURCE_ACTOR_ID, "producer actor identity mismatch"
    )
    _require_catalogue(value.get("record_id") == W11_CATALOGUE_RECORD_ID, "catalogue record identity mismatch")
    _require_catalogue(value.get("project_id") == W11_CATALOGUE_PROJECT_ID, "catalogue project identity mismatch")
    _require_catalogue(value.get("source_refs") == expected_source_refs, "catalogue source provenance mismatch")
    _require_catalogue(
        value.get("owner_spec_identity") == _expected_spec_identity(repo_root), "owner specification identity mismatch"
    )

    unsigned = {key: item for key, item in value.items() if key != "content_hash"}
    expected_content_hash = sha256_hex(canonical_bytes(unsigned))
    _require_catalogue(
        value.get("content_hash") == expected_content_hash, "content_hash must hash the P0 object excluding itself"
    )

    expected_schema_rows = _expected_schema_source_rows(repo_root, resolved_schema_root)
    actual_schema_rows = value.get("schema_source_rows")
    _require_catalogue(
        actual_schema_rows == expected_schema_rows,
        "schema_source_rows do not match the closed foundation byte manifest",
    )

    expected_owner_rows = _expected_owner_contract_rows(repo_root, expected_schema_rows)
    actual_owner_rows = value.get("owner_contract_rows")
    _require_catalogue(isinstance(actual_owner_rows, list), "owner_contract_rows must be an array")
    _require_catalogue(
        len(actual_owner_rows) == len(expected_owner_rows),
        "owner_contract_rows do not match the accepted W11 owner annex",
    )
    for actual_row, expected_row in zip(actual_owner_rows, expected_owner_rows, strict=True):
        verify_expected_owner_contract_row(actual_row, expected_row)
    _require_catalogue(value.get("owner_row_count") == len(_OWNER_ROW_IDS), "owner_row_count must be exactly 81")
    expected_range_hash = sha256_hex(canonical_bytes(sorted(_OWNER_ROW_IDS)))
    _require_catalogue(
        value.get("owner_row_range_hash") == expected_range_hash, "owner_row_range_hash is not deterministic"
    )


def _expected_source_refs(repo_root: Path) -> list[dict[str, str]]:
    bootstrap_raw = _git_raw(repo_root, "cat-file", "blob", f"{W11_FOUNDATION_COMMIT}:{W11_BOOTSTRAP_PATH}")
    bootstrap_sha256 = hashlib.sha256(bootstrap_raw).hexdigest()
    if bootstrap_sha256 != W11_BOOTSTRAP_SHA256:
        _require_catalogue(False, "bootstrap contract identity drifted at the foundation subject")
    return [
        {
            "ref_kind": "external",
            "locator": f"git:{W11_SPECIFICATION_COMMIT}:{W11_SPECIFICATION_PATH}",
            "content_hash": W11_SPECIFICATION_SHA256,
        },
        {
            "ref_kind": "external",
            "locator": f"git:{W11_FOUNDATION_COMMIT}:{W11_BOOTSTRAP_PATH}",
            "content_hash": W11_BOOTSTRAP_SHA256,
        },
    ]


def _expected_spec_identity(repo_root: Path) -> dict[str, Any]:
    raw = _git_raw(repo_root, "cat-file", "blob", f"{W11_SPECIFICATION_COMMIT}:{W11_SPECIFICATION_PATH}")
    _require_catalogue(len(raw) == W11_SPECIFICATION_BYTES, "accepted W11 specification byte length drifted")
    _require_catalogue(
        hashlib.sha256(raw).hexdigest() == W11_SPECIFICATION_SHA256, "accepted W11 specification SHA-256 drifted"
    )
    blob = _git(repo_root, "rev-parse", f"{W11_SPECIFICATION_COMMIT}:{W11_SPECIFICATION_PATH}")
    _require_catalogue(blob == W11_SPECIFICATION_BLOB, "accepted W11 specification Git blob drifted")
    return {
        "repository_path": W11_SPECIFICATION_PATH,
        "reviewed_commit": W11_SPECIFICATION_COMMIT,
        "git_blob": W11_SPECIFICATION_BLOB,
        "raw_sha256": W11_SPECIFICATION_SHA256,
        "raw_bytes": W11_SPECIFICATION_BYTES,
    }


def _expected_schema_source_rows(repo_root: Path, schema_root: Path) -> list[dict[str, Any]]:
    if not schema_root.is_dir():
        _require_catalogue(False, f"schema root does not exist: {schema_root}")

    actual_paths = sorted(path.relative_to(schema_root).as_posix() for path in schema_root.glob("*.schema.json"))
    expected_relative_paths = [path.removeprefix(f"{_W11_SCHEMA_ROOT}/") for path in _W11_SCHEMA_PATHS]
    expected_root_paths = sorted([*expected_relative_paths, "w11-common-definitions.schema.json"])
    _require_catalogue(actual_paths == expected_root_paths, "schema path manifest is not the closed 61-family set")

    rows: list[dict[str, Any]] = []
    for index, repository_path in enumerate(_W11_SCHEMA_PATHS, start=101):
        relative_path = repository_path.removeprefix(f"{_W11_SCHEMA_ROOT}/")
        raw = _git_raw(repo_root, "cat-file", "blob", f"{W11_FOUNDATION_COMMIT}:{repository_path}")
        current_path = schema_root / relative_path
        try:
            current_raw = current_path.read_bytes()
        except OSError as exc:
            _require_catalogue(False, f"cannot read schema {repository_path}: {exc}")
        _require_catalogue(
            current_raw == raw, f"schema bytes drifted from the exact foundation subject: {repository_path}"
        )
        try:
            schema = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            _require_catalogue(False, f"foundation schema is not UTF-8 JSON: {repository_path}: {exc}")
        schema_id = schema.get("$id")
        schema_version = schema.get("properties", {}).get("schema_version", {}).get("const", "1.0.0")
        blob = _git(repo_root, "rev-parse", f"{W11_FOUNDATION_COMMIT}:{repository_path}")
        source_row = {
            "logical_key": _W11_SCHEMA_LOGICAL_KEYS[repository_path],
            "schema_id": schema_id,
            "schema_version": schema_version,
            "repository_path": repository_path,
            "git_commit": W11_FOUNDATION_COMMIT,
            "git_blob": blob,
            "file_length": len(raw),
            "file_sha256": hashlib.sha256(raw).hexdigest(),
        }
        source_row["independent_observation_ref"] = _schema_observation_ref(index, source_row)
        rows.append(source_row)

    schema_ids = [row["schema_id"] for row in rows]
    _require_catalogue(len(schema_ids) == len(set(schema_ids)), "schema IDs are not collision-free")
    _require_catalogue(
        rows == sorted(rows, key=lambda row: row["repository_path"]), "schema_source_rows are not path-sorted"
    )
    return rows


def _schema_observation_ref(index: int, source_row: Mapping[str, Any]) -> dict[str, Any]:
    observation_identity = {
        "observation_kind": "w11-schema-source",
        "logical_key": source_row["logical_key"],
        "schema_id": source_row["schema_id"],
        "schema_version": source_row["schema_version"],
        "repository_path": source_row["repository_path"],
        "git_commit": source_row["git_commit"],
        "git_blob": source_row["git_blob"],
        "file_length": source_row["file_length"],
        "file_sha256": source_row["file_sha256"],
    }
    return {
        "id": f"obj_00000000-0000-7000-8000-{index:012d}",
        "record_revision": 1,
        "content_hash": sha256_hex(canonical_bytes(observation_identity)),
    }


def _expected_owner_contract_rows(repo_root: Path, schema_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    raw = _git_raw(repo_root, "cat-file", "blob", f"{W11_SPECIFICATION_COMMIT}:{W11_SPECIFICATION_PATH}")
    text = raw.decode("utf-8")
    observed_rows: list[dict[str, str]] = []
    for line in text.splitlines():
        if not re.match(r"^\| OR-\d{3} \|", line):
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) != 5:
            _require_catalogue(False, "accepted W11 owner row is not a five-cell binding")
        owner_row_id, command_cell, precondition_cell, effects_cell, implementation_cell = cells
        command_match = _W11_COMMAND_PATTERN.search(command_cell)
        schema_match = _W11_COMMAND_SCHEMA_PATTERN.search(command_cell)
        if command_match is None or schema_match is None:
            _require_catalogue(False, f"owner row {owner_row_id} has no exact command/schema token")
        command_with_discriminator = command_match.group(1)
        command_type, _, discriminator = command_with_discriminator.partition("/")
        command_schema_token = schema_match.group(1)
        command_parts = command_cell.split(";", 2)
        if len(command_parts) != 3:
            _require_catalogue(False, f"owner row {owner_row_id} has no complete authority subject")
        eligible_profile = command_parts[1].strip()
        authority_subject = command_parts[2].strip()
        reducer_tokens = re.findall(r"`(U:[^`]+)`", implementation_cell)
        projection_tokens = re.findall(r"`(P:[^`]+)`", implementation_cell)
        receipt_tokens = re.findall(r"`(R:[^`]+)`", implementation_cell)
        ordered_events = _ordered_event_tokens(effects_cell)
        affected_streams = _affected_stream_clauses(effects_cell)
        complete_write_set = [part.strip() for part in effects_cell.split(";") if part.strip()]
        if not reducer_tokens or not projection_tokens or len(receipt_tokens) != 1 or not ordered_events:
            _require_catalogue(False, f"owner row {owner_row_id} has an incomplete effect binding")
        observed_rows.append(
            {
                "owner_row_id": owner_row_id,
                "command_type": command_type,
                "command_schema_token": command_schema_token,
                "discriminator": discriminator,
                "eligible_profile": eligible_profile,
                "authority_subject": authority_subject,
                "preconditions": precondition_cell,
                "ordered_events": ordered_events,
                "affected_streams": affected_streams,
                "complete_write_set": complete_write_set,
                "reducer": ", ".join(reducer_tokens),
                "projection_targets": projection_tokens,
                "receipt_identity": receipt_tokens[0],
            }
        )

    observed_ids = [row["owner_row_id"] for row in observed_rows]
    _require_catalogue(
        observed_ids == sorted(_OWNER_ROW_IDS, key=_owner_sort_key),
        "accepted W11 owner rows are not the exact 81-row set",
    )
    schema_by_id = {row["schema_id"]: row for row in schema_rows}
    expected: list[dict[str, Any]] = []
    for source_row in observed_rows:
        owner_row_id = source_row["owner_row_id"]
        logical_key = source_row["command_schema_token"]
        if source_row["discriminator"]:
            logical_key = f"{logical_key}/{source_row['discriminator']}"
        schema_id = _owner_schema_id(owner_row_id, source_row["command_type"], source_row["discriminator"])
        if schema_id not in schema_by_id:
            _require_catalogue(False, f"owner row {owner_row_id} references a schema outside the closed manifest")
        row = {
            "owner_row_id": owner_row_id,
            "logical_key": logical_key,
            "schema_id": schema_id,
            "schema_version": "1.0.0",
            "file_observation_ref": dict(schema_by_id[schema_id]["independent_observation_ref"]),
            "command_type": source_row["command_type"],
            "payload_discriminant": logical_key,
            "eligible_profile": source_row["eligible_profile"],
            "authority_subject": source_row["authority_subject"],
            "preconditions": [source_row["preconditions"]],
            "ordered_events": source_row["ordered_events"],
            "affected_streams": source_row["affected_streams"],
            "complete_write_set": source_row["complete_write_set"],
            "reducer": source_row["reducer"],
            "projection_targets": source_row["projection_targets"],
            "receipt_identity": source_row["receipt_identity"],
            "positive_test_identity": f"W11-T01-{owner_row_id}",
            "negative_mutation_test_identity": f"W11-T03-{owner_row_id}-owner-row-mutation",
            "retry_test_identity": f"W11-T11-{owner_row_id}",
        }
        expected.append(row)
    return expected


def verify_expected_owner_contract_row(actual_row: Mapping[str, Any], expected_row: Mapping[str, Any]) -> None:
    """Compare one catalogue row with its independently derived owner binding."""
    _require_catalogue(
        actual_row == expected_row,
        "owner_contract_rows do not match the accepted W11 owner annex",
    )


def _owner_schema_id(owner_row_id: str, command_type: str, discriminator: str) -> str:
    if owner_row_id in {"OR-001", "OR-002"}:
        return "ars://portfolio/candidate"
    if command_type == "RequestAssay":
        return "ars://portfolio/relation/assay-request"
    if command_type == "RecordAssayScore":
        return "ars://portfolio/assay-scorecard"
    if command_type == "RecordAssayPartial":
        return "ars://portfolio/assay-partial"
    if command_type in {"ReviewDiscoveryOutcome", "RequestDiscoveryOutcomeReview"}:
        if discriminator.startswith("assay_cancelled"):
            return "ars://portfolio/relation/assay-cancellation-review"
        if discriminator.startswith("spike_cancelled"):
            return "ars://portfolio/relation/spike-cancellation-review"
        if discriminator.startswith("assay"):
            return "ars://portfolio/relation/assay-outcome-review"
        return "ars://portfolio/relation/spike-outcome-review"
    if command_type == "CancelDiscoveryEvaluation":
        return (
            "ars://portfolio/relation/assay-cancellation-review"
            if discriminator == "assay"
            else "ars://portfolio/relation/spike-cancellation-review"
        )
    if command_type in {"ProposeRevisitDecision"} or discriminator.startswith("discovery_revisit"):
        return "ars://portfolio/relation/discovery-revisit"
    if command_type == "ProposePromotionDecision" or discriminator.startswith("discovery_promotion"):
        return "ars://portfolio/relation/discovery-promotion"
    if command_type == "RegisterSpikePlan":
        return "ars://portfolio/relation/spike-plan"
    if command_type == "ProposeSpikeExecutionDecision" or discriminator == "spike_execution_authority":
        return "ars://portfolio/relation/spike-execution-authority"
    if command_type == "StartSpike":
        return "ars://portfolio/relation/spike-attempt"
    if command_type == "RecordSpikeVerdict":
        return "ars://portfolio/spike-verdict"
    if command_type == "AdmitResearchDossier":
        return "ars://portfolio/research-dossier-manifest"
    if command_type == "IngestScoutObservationBatch":
        return "ars://portfolio/scout-observation-batch"
    if command_type == "IngestDiscoveryAnnotation":
        return "ars://portfolio/discovery-annotation"
    if command_type == "RecordLegacyPortfolioObservation":
        return "ars://portfolio/legacy-portfolio-path-observation"
    if command_type == "TransitionPortfolioOwnership":
        return "ars://portfolio/relation/inventory-mapping-transition-bijection"
    if command_type == "CutOverDiscoveryPath":
        return "ars://portfolio/relation/legacy-path-cutover"
    if command_type == "RegisterAssayRubricContent":
        return "ars://portfolio/assay-rubric-content"
    if command_type == "RegisterAssayEvidenceScopeContent":
        return "ars://portfolio/assay-evidence-scope-content"
    if command_type == "ObserveW11AuthorityFile":
        return "ars://portfolio/authority-file-observation"
    if command_type in {"RequestW11AuthorityReview", "RecordW11AuthorityReview"}:
        return "ars://portfolio/relation/authority-content-file-review-acceptance"
    if command_type in {"ProposeW11AuthorityDecision", "ResolveDecision"}:
        decision_schemas = {
            "assay_bar_acceptance": "ars://portfolio/relation/assay-bar-acceptance",
            "dossier_expected_set_acceptance": "ars://portfolio/relation/dossier-expected-set-acceptance",
            "path_registration_acceptance": "ars://portfolio/relation/path-registration-acceptance",
            "legacy_source_inventory_acceptance": "ars://portfolio/relation/legacy-source-inventory-acceptance",
            "migration_authority": "ars://portfolio/relation/migration-authority",
            "legacy_path_cutover": "ars://portfolio/relation/legacy-path-cutover",
        }
        for suffix, schema_id in decision_schemas.items():
            if suffix in discriminator:
                return schema_id
    if command_type == "RecordAssayBarStaleness":
        return "ars://portfolio/relation/assay-bar-acceptance"
    if command_type == "RegisterDossierExpectedSetContent":
        return "ars://portfolio/dossier-expected-set-content"
    if command_type == "RegisterPathRegistrationContent":
        return "ars://portfolio/path-registration-content"
    if command_type == "RegisterLegacySourceInventoryContent":
        return "ars://portfolio/legacy-source-inventory-content"
    if command_type == "RegisterLegacyTransitionMappingContent":
        return "ars://portfolio/legacy-transition-mapping-content"
    if command_type == "RegisterLegacyCutoverClosureContent":
        return "ars://portfolio/legacy-cutover-closure-content"
    if command_type == "ImportAcceptedW11CatalogueGenesis":
        return "ars://portfolio/import-accepted-w11-catalogue-genesis"
    _require_catalogue(False, f"no independent schema mapping exists for {owner_row_id} {command_type}/{discriminator}")


def _ordered_event_tokens(effects: str) -> list[str]:
    tokens: list[str] = []
    for match in _W11_EVENT_PATTERN.finditer(effects):
        if match.group(1) is not None:
            tokens.append(f"W2:{match.group(1)}")
        else:
            tokens.append(match.group(0))
    return tokens


def _affected_stream_clauses(effects: str) -> list[str]:
    clauses: list[str] = []
    for segment in effects.split(";"):
        cleaned = _W11_EVENT_CLEANUP_PATTERN.sub("", segment)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")
        if not cleaned or cleaned in {"Always", "only if policy-satisfying"}:
            continue
        clauses.append(cleaned)
    return clauses or ["implicit W2 stream"]


def _owner_sort_key(owner_row_id: str) -> tuple[int, int]:
    return (0 if owner_row_id.startswith("OR-0") else 1, int(owner_row_id[3:]))


def _require_catalogue(condition: bool, message: str) -> None:
    if not condition:
        _invalid(W11_SCHEMA_CATALOGUE_SCHEMA_ID, message)


def verify_w11_document(
    schema_id: str,
    value: Any,
    *,
    reference_documents: Iterable[Mapping[str, Any]] = (),
    validate_reference: ReferenceValidator | None = None,
) -> None:
    """Apply W11 cross-field rules after the inert schema check has passed."""
    if not isinstance(value, Mapping):
        return

    if schema_id in W11_CONTENT_SCHEMA_IDS:
        _validate_content_envelope(schema_id, value)
    if schema_id == W11_SCHEMA_CATALOGUE_SCHEMA_ID:
        _validate_owner_contract_rows(schema_id, value)
    if schema_id == W11_DOSSIER_EXPECTED_SET_SCHEMA_ID:
        _validate_dossier_expected_set(schema_id, value)
    if schema_id == W11_ASSAY_SCORECARD_SCHEMA_ID:
        _validate_scorecard_against_rubric(
            schema_id,
            value,
            reference_documents=reference_documents,
            validate_reference=validate_reference,
        )


def _registry_for_root(schema_root: Path) -> SchemaRegistry:
    nested_schema_paths = sorted(path for path in schema_root.rglob("*.schema.json") if path.parent != schema_root)
    if nested_schema_paths:
        raise SchemaError(f"nested schema files are not permitted: {nested_schema_paths[0]}")
    return SchemaRegistry(schema_root)


def _validate_content_envelope(schema_id: str, value: Mapping[str, Any]) -> None:
    revision = value["record_revision"]
    predecessor = value["supersedes_revision"]
    if revision == 1 and predecessor is not None:
        _invalid(schema_id, "revision 1 must have null supersedes_revision")
    if type(revision) is int and revision > 1 and predecessor != revision - 1:
        _invalid(schema_id, "later revisions must name the exact predecessor")

    for index, source_ref in enumerate(value["source_refs"]):
        ref_kind = source_ref["ref_kind"]
        identifier = source_ref.get("id")
        if ref_kind == "record" and (not isinstance(identifier, str) or _OBJ_ID_RE.fullmatch(identifier) is None):
            _invalid(schema_id, f"source_refs[{index}] record identity must be a canonical obj_ UUID")
        if ref_kind == "artefact" and (not isinstance(identifier, str) or _ART_ID_RE.fullmatch(identifier) is None):
            _invalid(schema_id, f"source_refs[{index}] artefact identity must be a canonical art_ UUID")


def _validate_owner_contract_rows(schema_id: str, value: Mapping[str, Any]) -> None:
    schema_source_rows = value["schema_source_rows"]
    logical_keys = [row["logical_key"] for row in schema_source_rows]
    schema_ids = [row["schema_id"] for row in schema_source_rows]
    if len(set(logical_keys)) != len(logical_keys):
        _invalid(schema_id, "schema_source_rows logical_key values must be unique")
    if len(set(schema_ids)) != len(schema_ids):
        _invalid(schema_id, "schema_source_rows schema_id values must be unique")

    observed_schema_closure = {
        (row["logical_key"], row["schema_id"], row["repository_path"]) for row in schema_source_rows
    }
    if observed_schema_closure != _EXPECTED_SCHEMA_SOURCE_CLOSURE:
        missing = sorted(_EXPECTED_SCHEMA_SOURCE_CLOSURE - observed_schema_closure)
        unexpected = sorted(observed_schema_closure - _EXPECTED_SCHEMA_SOURCE_CLOSURE)
        _invalid(
            schema_id,
            "schema_source_rows must contain exact accepted 61-family schema closure; "
            f"missing={missing}, unexpected={unexpected}",
        )

    rows = value["owner_contract_rows"]
    owner_logical_keys = [row["logical_key"] for row in rows]
    if len(set(owner_logical_keys)) != len(owner_logical_keys):
        _invalid(schema_id, "owner_contract_rows logical_key values must be unique")

    observed_ids = [row["owner_row_id"] for row in rows]
    if len(set(observed_ids)) != len(observed_ids):
        _invalid(schema_id, "owner_contract_rows must contain each owner_row_id exactly once")
    if set(observed_ids) != _OWNER_ROW_IDS:
        missing = sorted(_OWNER_ROW_IDS - set(observed_ids))
        unexpected = sorted(set(observed_ids) - _OWNER_ROW_IDS)
        _invalid(schema_id, f"owner row set mismatch; missing={missing}, unexpected={unexpected}")

    for row in rows:
        owner_row_id = row["owner_row_id"]
        expected = {
            "positive_test_identity": f"W11-T01-{owner_row_id}",
            "negative_mutation_test_identity": f"W11-T03-{owner_row_id}-owner-row-mutation",
            "retry_test_identity": f"W11-T11-{owner_row_id}",
        }
        for field, expected_value in expected.items():
            if row[field] != expected_value:
                _invalid(schema_id, f"owner row {owner_row_id} {field} must be {expected_value}")


def _validate_dossier_expected_set(schema_id: str, value: Mapping[str, Any]) -> None:
    sorted_rows: dict[str, list[Mapping[str, Any]]] = {}
    for rows_key, count_key, hash_key, identity_key in _DOSSIER_EXPECTED_SET_FAMILIES:
        rows = value[rows_key]
        identities = [row[identity_key] for row in rows]
        if len(set(identities)) != len(identities):
            _invalid(schema_id, f"{rows_key} contains duplicate {identity_key} values")
        if value[count_key] != len(rows):
            _invalid(schema_id, f"{count_key} does not match row count")
        try:
            sorted_family = sorted(rows, key=canonical_bytes)
            computed_hash = sha256_hex(canonical_bytes(sorted_family))
        except (TypeError, ValueError) as exc:
            _invalid(schema_id, f"{hash_key} cannot be computed from P0-canonical rows: {exc}")
        sorted_rows[rows_key] = sorted_family
        if value[hash_key] != computed_hash:
            _invalid(schema_id, f"{hash_key} does not match the canonical row multiset")

    closure_payload = {
        "manifest_schema_id": value["schema_id"],
        "manifest_schema_version": value["schema_version"],
        "package_version": value["package_version"],
        "admission_profile_hash": value["admission_profile_ref"]["content_hash"],
        "components": sorted_rows["components"],
        "source_dependencies": sorted_rows["sources"],
        "objects": sorted_rows["objects"],
        "scope_definitions": sorted_rows["scope_definitions"],
        "dependency_edges": sorted_rows["dependency_edges"],
        "relationships": sorted_rows["relationships"],
    }
    try:
        computed_closure_hash = sha256_hex(canonical_bytes(closure_payload))
    except (TypeError, ValueError) as exc:
        _invalid(schema_id, f"expected_set_closure_hash cannot be computed from P0-canonical rows: {exc}")
    if value["expected_set_closure_hash"] != computed_closure_hash:
        _invalid(schema_id, "expected_set_closure_hash does not match the canonical closure")


def _validate_scorecard_against_rubric(
    schema_id: str,
    value: Mapping[str, Any],
    *,
    reference_documents: Iterable[Mapping[str, Any]],
    validate_reference: ReferenceValidator | None,
) -> None:
    rubric_ref = value["rubric_ref"]
    reference_documents = tuple(reference_documents)
    if reference_documents and validate_reference is None:
        _invalid(schema_id, "reference documents require validate_reference")
    matches: list[Mapping[str, Any]] = []
    for candidate in reference_documents:
        if not isinstance(candidate, Mapping):
            _invalid(schema_id, "reference documents must be mappings")
        if (
            candidate.get("schema_id") == W11_ASSAY_RUBRIC_SCHEMA_ID
            and candidate.get("schema_version") == "1.0.0"
            and candidate.get("record_id") == rubric_ref["id"]
            and candidate.get("record_revision") == rubric_ref["record_revision"]
            and candidate.get("content_hash") == rubric_ref["content_hash"]
        ):
            matches.append(candidate)

    if not matches:
        _invalid(schema_id, "rubric_ref could not be resolved to the frozen rubric")
    if len(matches) > 1:
        _invalid(schema_id, "rubric_ref resolved ambiguously")

    rubric = matches[0]
    if validate_reference is not None:
        validate_reference(W11_ASSAY_RUBRIC_SCHEMA_ID, rubric)
    if "axis_definitions" not in rubric:
        _invalid(schema_id, "frozen rubric is missing axis_definitions")
    axis_definitions = rubric["axis_definitions"]
    if not isinstance(axis_definitions, list):
        _invalid(schema_id, "frozen rubric axis_definitions must be a list")

    axes: dict[str, Mapping[str, Any]] = {}
    expected_value_types = {
        "gate": "boolean",
        "integer_score": "integer",
        "registered_measure": "number",
    }
    for index, axis in enumerate(axis_definitions):
        if not isinstance(axis, Mapping):
            _invalid(schema_id, f"frozen rubric axis_definitions[{index}] must be a mapping")
        axis_id = axis.get("axis_id")
        if not isinstance(axis_id, str) or not axis_id:
            _invalid(schema_id, f"frozen rubric axis_definitions[{index}] is missing axis_id")
        if axis_id in axes:
            _invalid(schema_id, f"frozen rubric contains duplicate axis {axis_id}")
        axes[axis_id] = axis
        axis_kind = axis.get("axis_kind")
        if not isinstance(axis_kind, str):
            _invalid(schema_id, f"frozen rubric axis {axis_id} is missing axis_kind")
        if axis_kind not in expected_value_types:
            _invalid(schema_id, f"frozen rubric axis {axis_id} has unknown axis_kind {axis_kind}")
        expected_value_type = expected_value_types[axis_kind]
        value_type = axis.get("value_type")
        if not isinstance(value_type, str):
            _invalid(schema_id, f"frozen rubric axis {axis_id} is missing value_type")
        if value_type != expected_value_type:
            _invalid(schema_id, f"frozen rubric axis {axis_id} has an inconsistent value type")
        _validate_frozen_axis_domain(schema_id, axis_id, axis_kind, axis)

    required_axis_ids_value = rubric.get("required_axis_ids")
    if (
        type(required_axis_ids_value) is not list
        or not required_axis_ids_value
        or not all(isinstance(axis_id, str) and axis_id for axis_id in required_axis_ids_value)
        or len(set(required_axis_ids_value)) != len(required_axis_ids_value)
    ):
        _invalid(schema_id, "frozen rubric required_axis_ids must be a non-empty list of unique strings")
    required_axis_ids = set(required_axis_ids_value)
    missing_rubric_axes = sorted(required_axis_ids - axes.keys())
    if missing_rubric_axes:
        _invalid(schema_id, f"frozen rubric required axes are undefined: {missing_rubric_axes}")

    observed_axis_ids: set[str] = set()
    for index, result in enumerate(value["axis_results"]):
        axis_id = result["axis_id"]
        if axis_id not in axes:
            _invalid(schema_id, f"axis_results[{index}] references unknown rubric axis {axis_id}")
        if axis_id in observed_axis_ids:
            _invalid(schema_id, f"axis_results contains duplicate rubric axis {axis_id}")
        observed_axis_ids.add(axis_id)
        axis = axes[axis_id]
        if result["axis_kind"] != axis["axis_kind"]:
            _invalid(
                schema_id,
                f"axis_results[{index}] axis kind mismatch for {axis_id}: expected {axis['axis_kind']}",
            )
        if not _value_is_in_frozen_domain(axis, result["value"]):
            _invalid(schema_id, f"axis_results[{index}] value is outside the frozen rubric domain for {axis_id}")

    missing_axis_ids = sorted(set(axes) - observed_axis_ids)
    unexpected_axis_ids = sorted(observed_axis_ids - set(axes))
    if missing_axis_ids or unexpected_axis_ids:
        _invalid(
            schema_id,
            f"axis_results axis set mismatch; missing={missing_axis_ids}, unexpected={unexpected_axis_ids}",
        )


def _validate_frozen_axis_domain(
    schema_id: str,
    axis_id: str,
    axis_kind: str,
    axis: Mapping[str, Any],
) -> None:
    has_allowed_set = "allowed_set" in axis
    has_bounds = "bounds" in axis
    if has_allowed_set == has_bounds:
        _invalid(schema_id, f"frozen rubric axis {axis_id} has an invalid domain shape")

    if has_allowed_set:
        allowed_set = axis["allowed_set"]
        if type(allowed_set) is not list or not allowed_set:
            _invalid(schema_id, f"frozen rubric axis {axis_id} allowed_set must be a non-empty JSON list")
        if axis_kind == "gate":
            if not all(type(value) is bool for value in allowed_set) or set(allowed_set) != {False, True}:
                _invalid(schema_id, f"frozen rubric axis {axis_id} allowed_set has invalid gate values")
        elif axis_kind == "integer_score":
            if not all(type(value) is int for value in allowed_set):
                _invalid(schema_id, f"frozen rubric axis {axis_id} allowed_set has invalid integer values")
        elif axis_kind == "registered_measure":
            if not all(
                type(value) in (int, float) and not isinstance(value, bool) and isfinite(value) for value in allowed_set
            ):
                _invalid(schema_id, f"frozen rubric axis {axis_id} allowed_set has invalid numeric values")
        return

    bounds = axis["bounds"]
    if not isinstance(bounds, Mapping) or set(bounds) != {"minimum", "maximum"}:
        _invalid(schema_id, f"frozen rubric axis {axis_id} has an invalid numeric domain")
    minimum = bounds["minimum"]
    maximum = bounds["maximum"]
    if axis_kind == "integer_score":
        valid_numbers = type(minimum) is int and type(maximum) is int
    elif axis_kind == "registered_measure":
        valid_numbers = all(
            type(bound) in (int, float) and not isinstance(bound, bool) and isfinite(bound)
            for bound in (minimum, maximum)
        )
    else:
        valid_numbers = False
    if not valid_numbers or minimum > maximum:
        _invalid(schema_id, f"frozen rubric axis {axis_id} has an invalid numeric domain")


def _value_is_in_frozen_domain(axis: Mapping[str, Any], value: Any) -> bool:
    axis_kind = axis["axis_kind"]
    if axis_kind == "gate" and type(value) is not bool:
        return False
    if axis_kind == "integer_score" and (type(value) is not int or isinstance(value, bool)):
        return False
    if axis_kind == "registered_measure" and (
        not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value)
    ):
        return False

    if "allowed_set" in axis:
        return any(_same_scalar(value, allowed) for allowed in axis["allowed_set"])

    bounds = axis.get("bounds")
    if bounds is None:
        return False
    return bounds["minimum"] <= value <= bounds["maximum"]


def _same_scalar(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    return type(left) is type(right) and left == right


def _is_repository_relative_path(path: str) -> bool:
    return bool(path) and path == path.replace("\\", "/") and not path.startswith("/") and ".." not in path.split("/")


def _require_sha1(value: Any, field: str) -> str:
    if not isinstance(value, str) or _SHA1_RE.fullmatch(value) is None:
        _envelope_error(f"{field} must be a lowercase 40-hex SHA")
    return value


def _git_executable() -> str:
    if _GIT_EXECUTABLE is None:
        _envelope_error("Git executable could not be resolved from PATH")
    return _GIT_EXECUTABLE


def _is_ancestor(repo_root: Path, base_commit: str, subject_commit: str) -> bool:
    base_commit = _require_sha1(base_commit, "base_commit")
    subject_commit = _require_sha1(subject_commit, "subject_commit")
    try:
        result = subprocess.run(  # nosec B603 - required argv-only Git ancestry check with validated SHAs.
            [_git_executable(), "merge-base", "--is-ancestor", base_commit, subject_commit],
            cwd=repo_root,
            check=False,
            shell=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        _envelope_error(f"Git ancestry lookup failed for {base_commit}..{subject_commit}: {exc}")
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    detail = result.stderr.strip() or f"exit status {result.returncode}"
    _envelope_error(f"Git ancestry lookup failed for {base_commit}..{subject_commit}: {detail}")


def _git(repo_root: Path, *args: str) -> str:
    try:
        result = subprocess.run(  # nosec B603 - required argv-only Git identity check with shell disabled.
            [_git_executable(), *args],
            cwd=repo_root,
            check=True,
            shell=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        _envelope_error(f"Git identity lookup failed for {' '.join(args)}: {detail}")
    return result.stdout.strip()


def _git_raw(repo_root: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = (
            exc.stderr.decode(errors="replace").strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        )
        _envelope_error(f"Git raw identity lookup failed for {' '.join(args)}: {detail}")
    return result.stdout


def _invalid(schema_id: str, message: str) -> NoReturn:
    raise SchemaError(f"{schema_id}: {message}")


def _envelope_error(message: str) -> NoReturn:
    raise MaterializationVerificationError(message)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--envelope", required=True, type=Path)
    args = parser.parse_args(argv)
    envelope = json.loads(args.envelope.read_text(encoding="utf-8"))
    verify_subject_envelope(args.repo_root, envelope)
    print("W11 materialization subject envelope verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
