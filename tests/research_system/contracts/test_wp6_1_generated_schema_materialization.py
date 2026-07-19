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


_TOY_PAYLOAD_FIELDS = {
    "command_key",
    "event_key",
    "subject_reference",
    "evidence_reference",
    "source_model_citation",
}
_COMMAND_ROOT_REQUIRED = {
    "command_id",
    "command_type",
    "schema_id",
    "schema_version",
    "submitted_at",
    "actor_id",
    "on_behalf_of_actor_id",
    "authority_grant_id",
    "target_stream_id",
    "expected_stream_version",
    "idempotency_key",
    "correlation_id",
    "causation_id",
    "reason",
    "evidence_refs",
    "payload",
}
_EVENT_ROOT_REQUIRED = {
    "event_id",
    "event_type",
    "schema_id",
    "schema_version",
    "project_id",
    "stream_id",
    "stream_version",
    "global_position",
    "transaction_id",
    "transaction_index",
    "transaction_count",
    "command_id",
    "command_schema_id",
    "command_schema_version",
    "command_schema_sha256",
    "correlation_id",
    "causation_id",
    "actor_id",
    "authority_grant_id",
    "occurred_at",
    "recorded_at",
    "payload",
    "previous_event_hash",
    "event_hash",
    "event_schema_id",
    "event_schema_version",
    "event_schema_sha256",
    "reducer_id",
    "projection_targets",
}


def _walk_objects(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        found = [value] if value.get("type") == "object" else []
        return found + [item for child in value.values() for item in _walk_objects(child)]
    if isinstance(value, list):
        return [item for child in value for item in _walk_objects(child)]
    return []


def _all_catalogue_schemas() -> list[tuple[dict[str, Any], dict[str, Any], str]]:
    catalogue, _ = _documents()
    result: list[tuple[dict[str, Any], dict[str, Any], str]] = []
    seen: set[str] = set()
    for row in catalogue["rows"]:
        bindings = [
            (row["command_schema_identity"], "command"),
            *[(item, "event") for item in row["event_schema_bindings"]],
        ]
        for identity, kind in bindings:
            path = identity[f"{kind}_schema_path"]
            if path not in seen:
                result.append((identity, _schema(path), kind))
                seen.add(path)
    return result


def test_wp6_1_generated_schemas_reject_toy_shell_fields_and_close_every_object() -> None:
    for _identity, schema, _kind in _all_catalogue_schemas():
        payload_text = json.dumps(schema)
        assert not any(f'"{field}"' in payload_text for field in _TOY_PAYLOAD_FIELDS)
        objects = _walk_objects(schema)
        assert objects
        assert all(node.get("additionalProperties") is False for node in objects)


def test_wp6_1_generated_roots_materialize_the_approved_command_and_event_envelopes() -> None:
    for _identity, schema, kind in _all_catalogue_schemas():
        expected = _COMMAND_ROOT_REQUIRED if kind == "command" else _EVENT_ROOT_REQUIRED
        assert set(schema["required"]) == expected
        assert "envelope" not in schema["properties"]


def test_wp6_1_catalogue_authority_sources_are_real_required_domain_fields() -> None:
    catalogue, _ = _documents()
    for row in catalogue["rows"]:
        schema = _schema(row["command_schema_identity"]["command_schema_path"])
        source = row["authority"]["authority_subject_id_source"]
        if source.startswith("payload."):
            field = source.split(".", 1)[1]
            variants = schema["$defs"]["payload"]["oneOf"]
            assert any(field in variant["required"] for variant in variants), row["key"]
        elif source == "envelope.target_stream_id":
            assert "target_stream_id" in schema["required"]
            assert "x-source-citation" in schema["properties"]["target_stream_id"]


@pytest.mark.parametrize(
    "key",
    [
        "scope.create",
        "task.create",
        "dispatch.issue",
        "task.claim_start",
        "attempt.create",
        "checkpoint.record",
        "message.publish_assignment",
        "artefact.register",
        "review.request",
        "decision.propose",
        "rule.evaluate",
        "correction.record",
        "operator.request_resource_grant",
        "operator.record_heartbeat",
        "operator.request_pause",
        "operator.request_stop",
        "operator.request_resume",
        "operator.quarantine_orphan",
        "operator.create_backup",
    ],
)
def test_wp6_1_representative_command_variants_require_domain_facts_not_metadata(key: str) -> None:
    catalogue, _ = _documents()
    row = next(item for item in catalogue["rows"] if item["key"] == key)
    schema = _schema(row["command_schema_identity"]["command_schema_path"])
    variants = schema["$defs"]["payload"]["oneOf"]
    metadata = {"schema_id", "schema_version", "command_type", "command_id", "project_id", "target_stream_id"}
    assert all(len(set(variant["required"]) - metadata) >= 2 for variant in variants), key


def test_wp6_1_shared_command_families_preserve_atomic_and_discriminated_domain_variants() -> None:
    catalogue, _ = _documents()
    claim = next(row for row in catalogue["rows"] if row["key"] == "task.claim_start")
    claim_schema = _schema(claim["command_schema_identity"]["command_schema_path"])
    claim_payload = claim_schema["$defs"]["payload"]["oneOf"]
    assert len(claim_payload) == 1
    assert set(claim_payload[0]["required"]) >= {"dispatch_id", "task_id", "task_revision", "lease_id"}

    message = next(row for row in catalogue["rows"] if row["key"] == "message.publish_assignment")
    variants = _schema(message["command_schema_identity"]["command_schema_path"])["$defs"]["payload"]["oneOf"]
    assert len(variants) == 10
    assert {item["properties"]["message_type"]["const"] for item in variants} == {
        "assignment",
        "acknowledgement",
        "progress",
        "input_request",
        "escalation",
        "report",
        "review_request",
        "review_response",
        "decision_request",
        "handoff",
    }
    assert all(len(set(item["required"]) - {"message_type"}) >= 2 for item in variants)


def test_wp6_1_public_registry_rejects_domain_omission_wrong_type_nested_extra_and_hybrid() -> None:
    catalogue, _ = _documents()
    message = next(row for row in catalogue["rows"] if row["key"] == "message.publish_assignment")
    schema = _schema(message["command_schema_identity"]["command_schema_path"])
    registry = SchemaRegistry(SCHEMA_ROOT)
    instance = _valid_instance(schema)
    registry.validate(schema["$id"], instance)
    for mutator in (
        lambda value: value["payload"].pop("assignee_id", None),
        lambda value: value["payload"].__setitem__("message_type", 7),
        lambda value: value["payload"].__setitem__("nested_escape", {"unexpected": True}),
        lambda value: value["payload"].update({"message_type": "assignment", "review_id": "rev-1"}),
    ):
        candidate = json.loads(json.dumps(instance))
        mutator(candidate)
        with pytest.raises(SchemaError):
            registry.validate(schema["$id"], candidate)
