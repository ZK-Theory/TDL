"""Regression tests for the WP6.1 proposed generated schema surface."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from research_system.errors import SchemaError
from research_system.schema_registry import SchemaRegistry
from tests.research_system.contracts.wp6_1_schema_materializer import generate_artifacts, materialize
from tests.research_system.contracts.wp6_1_schema_source import git_blob_id


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPO_ROOT / ".research-system" / "schemas"
CONTRACT_ROOT = REPO_ROOT / ".research-system" / "contracts"


def _documents() -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        yaml.safe_load((CONTRACT_ROOT / "wp6-1-owner-source-catalogue.yaml").read_bytes()),
        yaml.safe_load((CONTRACT_ROOT / "wp6-1-schema-identities.yaml").read_bytes()),
    )


def _schema(path: str) -> dict[str, Any]:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def _valid_instance(schema: dict[str, Any]) -> dict[str, Any]:
    payload = schema["$defs"]["payload"]["oneOf"][0]
    payload_values: dict[str, Any] = {}
    for name, definition in payload["properties"].items():
        payload_values[name] = definition.get("const", f"{name}-value")
    return {
        "schema_id": schema["$id"],
        "schema_version": "1.0.0",
        "command_type" if "/command/" in schema["$id"] else "event_type": schema["$id"].rsplit("/", 1)[1],
        "envelope": {
            "project_id": "project-1",
            "stream_id": "stream-1",
            "authority_grant_id": "grant-1",
            "idempotency_key": "idem-1",
        },
        "payload": payload_values,
    }


def test_wp6_1_generator_is_idempotent_and_matches_all_committed_raw_bytes() -> None:
    generated = generate_artifacts(REPO_ROOT)

    assert len([path for path in generated if "/commands/" in path]) == 87
    assert len([path for path in generated if "/events/" in path]) == 86
    assert len(generated) == 175
    assert materialize(REPO_ROOT, write=False) == []
    for path, expected in generated.items():
        assert (REPO_ROOT / path).read_bytes() == expected
        assert not expected.startswith(b"\xef\xbb\xbf")
        assert b"\r" not in expected


def test_wp6_1_identity_manifest_binds_raw_schema_bytes_paths_ids_versions_and_git_blobs() -> None:
    catalogue, identities = _documents()
    assert len(identities["rows"]) == len(catalogue["rows"]) == 104
    observations = 0
    for row in identities["rows"]:
        for identity in [row["command_schema_identity"], *row["event_schema_bindings"]]:
            kind = "command" if "command_schema_path" in identity else "event"
            path = identity[f"{kind}_schema_path"]
            data = (REPO_ROOT / path).read_bytes()
            schema = _schema(path)
            assert identity[f"{kind}_schema_sha256"] == hashlib.sha256(data).hexdigest()
            assert schema["$id"] == identity[f"{kind}_schema_id"]
            assert schema["properties"]["schema_version"]["const"] == identity[f"{kind}_schema_version"]
            assert identity["materialization_status"] == "proposed_materialized"
            assert identity["review_status"] == "pending_independent_review"
            assert identity["acceptance_status"] == "pending_d_g6_3_owner_acceptance"
            assert (
                git_blob_id(REPO_ROOT, data)
                == subprocess.run(
                    ["git", "hash-object", "--no-filters", "--stdin"],
                    cwd=REPO_ROOT,
                    input=data,
                    stdout=subprocess.PIPE,
                    check=True,
                )
                .stdout.decode("ascii")
                .strip()
            )
            observations += 1
    assert observations == 210


def test_wp6_1_generated_schemas_are_closed_domain_specific_and_cover_shared_unions() -> None:
    catalogue, _ = _documents()
    message = next(row for row in catalogue["rows"] if row["key"] == "message.publish_assignment")
    schema = _schema(message["command_schema_identity"]["command_schema_path"])
    variants = schema["$defs"]["payload"]["oneOf"]

    assert len(variants) == 10
    assert all(variant["type"] == "object" and variant["additionalProperties"] is False for variant in variants)
    assert all(len(variant["required"]) >= 4 for variant in variants)
    assert all("x-source-citation" in field for variant in variants for field in variant["properties"].values())
    references = [value for value in _walk_values(schema) if isinstance(value, str) and value.startswith("#/$defs/")]
    assert references
    assert "http" not in json.dumps(schema).replace("https://json-schema.org/draft/2020-12/schema", "")

    registry = SchemaRegistry(SCHEMA_ROOT)
    assert registry.contains(message["command_schema_identity"]["command_schema_id"])
    instance = _valid_instance(schema)
    registry.validate(schema["$id"], instance)
    instance["payload"]["unexpected"] = "toy-shell escape"
    with pytest.raises(SchemaError):
        registry.validate(schema["$id"], instance)


def _walk_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return [item for child in value.values() for item in _walk_values(child)]
    if isinstance(value, list):
        return [item for child in value for item in _walk_values(child)]
    return [value]


@pytest.mark.parametrize(
    ("key", "field", "replacement"),
    [
        ("task.create", "command_key", "task.create_alias"),
        ("message.publish_assignment", "command_key", "message.publish_report"),
        ("operator.request_stop", "subject_reference", ""),
    ],
)
def test_wp6_1_field_family_negatives_reject_wrong_discriminator_or_empty_domain_values(
    key: str, field: str, replacement: str
) -> None:
    catalogue, _ = _documents()
    row = next(item for item in catalogue["rows"] if item["key"] == key)
    schema = _schema(row["command_schema_identity"]["command_schema_path"])
    registry = SchemaRegistry(SCHEMA_ROOT)
    instance = _valid_instance(schema)
    instance["payload"][field] = replacement

    with pytest.raises(SchemaError):
        registry.validate(schema["$id"], instance)
