"""Non-runtime verifier for the inert W11 materialization surface.

This module is deliberately outside ``research_system``.  It validates the
W11 cross-field rules only when a caller supplies an explicit subject envelope,
and it has no runtime binding, handler, store, ledger, reducer, or projection
authority.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from functools import lru_cache
from math import isfinite
from pathlib import Path
from typing import Any, NoReturn

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import SchemaError
from research_system.schema_registry import SchemaRegistry


W11_MATERIALIZATION_BASE = "c84eb2aaf0890d36d3735d08a14169f4c50935cd"
_ENVELOPE_FIELDS = frozenset({"base_commit", "subject_commit", "subject_tree", "changed_paths"})
_PATH_ENTRY_FIELDS = frozenset({"path", "blob"})
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_OBJ_ID_RE = re.compile(r"^obj_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_ART_ID_RE = re.compile(r"^art_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")

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
    ("components", "component_count", "component_multiset_hash"),
    ("sources", "source_count", "source_multiset_hash"),
    ("objects", "object_count", "object_multiset_hash"),
    ("scope_definitions", "scope_count", "scope_multiset_hash"),
    ("dependency_edges", "edge_count", "edge_multiset_hash"),
    ("relationships", "relationship_count", "relationship_multiset_hash"),
)

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
    return _cached_registry_for_root(schema_root)


@lru_cache(maxsize=8)
def _cached_registry_for_root(schema_root: Path) -> SchemaRegistry:
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

    rows = value["owner_contract_rows"]
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
    for rows_key, count_key, hash_key in _DOSSIER_EXPECTED_SET_FAMILIES:
        rows = value[rows_key]
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

    axes: dict[str, Mapping[str, Any]] = {}
    for axis in rubric["axis_definitions"]:
        axis_id = axis["axis_id"]
        if axis_id in axes:
            _invalid(schema_id, f"frozen rubric contains duplicate axis {axis_id}")
        axes[axis_id] = axis
        expected_value_type = {
            "gate": "boolean",
            "integer_score": "integer",
            "registered_measure": "number",
        }[axis["axis_kind"]]
        if axis["value_type"] != expected_value_type:
            _invalid(schema_id, f"frozen rubric axis {axis_id} has an inconsistent value type")
        if "bounds" in axis and axis["bounds"]["minimum"] > axis["bounds"]["maximum"]:
            _invalid(schema_id, f"frozen rubric axis {axis_id} has descending bounds")

    required_axis_ids = set(rubric["required_axis_ids"])
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


def _is_ancestor(repo_root: Path, base_commit: str, subject_commit: str) -> bool:
    base_commit = _require_sha1(base_commit, "base_commit")
    subject_commit = _require_sha1(subject_commit, "subject_commit")
    try:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", base_commit, subject_commit],
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
        result = subprocess.run(
            ["git", *args],
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
