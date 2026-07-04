"""Fail-closed validation for staged eight-file evaluation packages."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import SchemaError
from research_system.evals.errors import FixtureDefinitionError
from research_system.schema_registry import SchemaRegistry

PACKAGE_PATHS = frozenset(
    {
        "fixture.yaml",
        "README.md",
        "input/source-manifest.json",
        "input/stimulus.json",
        "expected/pre-control.json",
        "expected/post-control.json",
        "expected/trajectory.json",
        "graders/required.json",
    }
)
_BOUND_CONTENT_PATHS = PACKAGE_PATHS - {
    "fixture.yaml",
    "input/source-manifest.json",
}
_JSON_SCHEMAS = {
    "input/source-manifest.json": "ars://evals/fixture-source-manifest",
    "input/stimulus.json": "ars://evals/fixture-stimulus",
    "expected/pre-control.json": "ars://evals/fixture-oracle",
    "expected/post-control.json": "ars://evals/fixture-oracle",
    "expected/trajectory.json": "ars://evals/fixture-trajectory",
    "graders/required.json": "ars://evals/fixture-grader-manifest",
}


@dataclass(frozen=True, slots=True)
class ValidatedFixturePackage:
    """Content-bound result for a staged, not activated, fixture package."""

    fixture_id: str
    fixture_revision: str
    content_hashes: dict[str, str]
    package_hash: str
    variant_ids: tuple[str, ...]
    activation_status: str = "staged"


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FixtureDefinitionError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _parse_json(data: bytes, relative: str) -> dict[str, Any]:
    try:
        payload = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_object_pairs,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise FixtureDefinitionError(f"invalid JSON: {relative}") from exc
    if not isinstance(payload, dict):
        raise FixtureDefinitionError(f"JSON object required: {relative}")
    return payload


def _read_fixture(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise FixtureDefinitionError(f"invalid fixture YAML: {path}") from exc
    if not isinstance(payload, dict):
        raise FixtureDefinitionError("fixture YAML object required")
    return payload


def _validate_instance(
    registry: SchemaRegistry,
    schema_id: str,
    payload: dict[str, Any],
) -> None:
    try:
        registry.validate(schema_id, payload)
    except SchemaError as exc:
        raise FixtureDefinitionError(str(exc)) from exc


def _require_identity(
    payload: dict[str, Any],
    fixture_id: str,
    fixture_revision: str,
    relative: str,
) -> None:
    if (
        payload.get("fixture_id") != fixture_id
        or payload.get("fixture_revision") != fixture_revision
    ):
        raise FixtureDefinitionError(f"package identity mismatch: {relative}")


def validate_fixture_package(
    root: Path | str,
    *,
    schema_root: Path | str,
) -> ValidatedFixturePackage:
    """Validate one staged package without activating catalogue coverage."""
    root = Path(root)
    observed = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    if observed != PACKAGE_PATHS:
        missing = sorted(PACKAGE_PATHS - observed)
        extra = sorted(observed - PACKAGE_PATHS)
        raise FixtureDefinitionError(
            "fixture package file closure mismatch: "
            f"missing={missing}, extra={extra}"
        )

    files = {relative: (root / relative).read_bytes() for relative in PACKAGE_PATHS}
    try:
        files["README.md"].decode("utf-8")
    except UnicodeError as exc:
        raise FixtureDefinitionError("README.md must be UTF-8") from exc
    if not files["README.md"].strip():
        raise FixtureDefinitionError("README.md must not be empty")

    registry = SchemaRegistry(Path(schema_root))
    fixture = _read_fixture(root / "fixture.yaml")
    _validate_instance(registry, "ars://evals/fixture-definition", fixture)
    fixture_id = str(fixture["fixture_id"])
    fixture_revision = str(fixture["fixture_revision"])

    documents: dict[str, dict[str, Any]] = {}
    for relative, schema_id in _JSON_SCHEMAS.items():
        payload = _parse_json(files[relative], relative)
        _validate_instance(registry, schema_id, payload)
        _require_identity(payload, fixture_id, fixture_revision, relative)
        documents[relative] = payload

    content_hashes = {
        relative: sha256_hex(data) for relative, data in sorted(files.items())
    }
    source = documents["input/source-manifest.json"]
    if fixture["source_manifest_hash"] != content_hashes["input/source-manifest.json"]:
        raise FixtureDefinitionError("source manifest hash mismatch")
    declared_hashes = source["content_hashes"]
    if set(declared_hashes) != _BOUND_CONTENT_PATHS:
        raise FixtureDefinitionError("source manifest content hash closure mismatch")
    for relative in sorted(_BOUND_CONTENT_PATHS):
        if declared_hashes[relative] != content_hashes[relative]:
            raise FixtureDefinitionError(f"content hash mismatch: {relative}")

    direct_bindings = {
        "stimulus_hash": "input/stimulus.json",
        "pre_control_oracle_hash": "expected/pre-control.json",
        "post_control_oracle_hash": "expected/post-control.json",
        "known_bad_reference_hash": "expected/pre-control.json",
        "known_good_reference_hash": "expected/post-control.json",
    }
    for field, relative in direct_bindings.items():
        if fixture[field] != content_hashes[relative]:
            raise FixtureDefinitionError(f"content hash mismatch: {relative}")

    trajectory = documents["expected/trajectory.json"]
    if (
        trajectory["required"] != fixture["required_trajectory"]
        or trajectory["forbidden"] != fixture["forbidden_trajectory"]
    ):
        raise FixtureDefinitionError("trajectory binding mismatch")
    graders = documents["graders/required.json"]
    if graders["required_graders"] != fixture["required_graders"]:
        raise FixtureDefinitionError("grader manifest binding mismatch")

    variant_ids = tuple(row["variant_id"] for row in source["variant_bindings"])
    if len(set(variant_ids)) != len(variant_ids):
        raise FixtureDefinitionError("duplicate variant binding")
    wildcard_fields = (
        "variant_id",
        "provider_variant",
        "runtime_variant",
        "os",
        "transport",
    )
    for row in source["variant_bindings"]:
        for field in wildcard_fields:
            value = str(row.get(field, "")).strip().lower()
            if value == "any" or "*" in value:
                raise FixtureDefinitionError("wildcard variant binding prohibited")

    package_hash = sha256_hex(canonical_bytes(content_hashes))
    return ValidatedFixturePackage(
        fixture_id=fixture_id,
        fixture_revision=fixture_revision,
        content_hashes=content_hashes,
        package_hash=package_hash,
        variant_ids=variant_ids,
    )
