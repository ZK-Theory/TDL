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
from tests.research_system.contracts.wp6_1_schema_expectations import PAYLOAD_EXPECTATIONS, PayloadExpectation
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


def _resolve_local_reference(definition: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    """Resolve a local definition without consulting generator implementation."""
    while "$ref" in definition:
        token = definition["$ref"].removeprefix("#/$defs/")
        definition = root["$defs"][token]
    return definition


def _payload_variants(schema: dict[str, Any]) -> list[dict[str, Any]]:
    payload = _resolve_local_reference(schema["$defs"]["payload"], schema)
    return [_resolve_local_reference(item, schema) for item in payload.get("oneOf", [payload])]


def _applicable_payload_variants(schema: dict[str, Any], expectation: PayloadExpectation) -> list[dict[str, Any]]:
    variants = _payload_variants(schema)
    matches: list[dict[str, Any]] = []
    for variant in variants:
        properties = variant.get("properties", {})
        if all(
            field in properties and _resolve_local_reference(properties[field], schema).get("const") == value
            for field, value in expectation.selectors
        ):
            matches.append(variant)
    return matches


def _valid_instance(schema: dict[str, Any]) -> dict[str, Any]:
    return _schema_value(schema, schema)


def _schema_value(definition: dict[str, Any], root: dict[str, Any]) -> Any:
    if "$ref" in definition:
        token = definition["$ref"].removeprefix("#/$defs/")
        return _schema_value(root["$defs"][token], root)
    if "const" in definition:
        return definition["const"]
    if "oneOf" in definition:
        return _schema_value(definition["oneOf"][0], root)
    if definition.get("type") == "object":
        return {name: _schema_value(definition["properties"][name], root) for name in definition.get("required", [])}
    if definition.get("type") == "array":
        return [_schema_value(definition.get("items", {}), root)]
    if definition.get("type") == "integer":
        return max(1, definition.get("minimum", 1))
    if definition.get("type") == "boolean":
        return True
    if definition.get("type") == ["string", "null"]:
        return "value"
    pattern = definition.get("pattern", "")
    if "[0-9a-f]{64}" in pattern:
        return "a" * 64
    if "date-time" == definition.get("format"):
        return "2026-07-19T00:00:00Z"
    if "uuid" in pattern:
        return "tsk_01979c31-6710-7a2d-8d4b-6d2c62e07f51"
    return "value"


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


def test_wp6_1_payload_oracle_covers_the_exact_owner_catalogue_key_set() -> None:
    catalogue, _ = _documents()
    assert set(PAYLOAD_EXPECTATIONS) == {row["key"] for row in catalogue["rows"]}
    assert len(PAYLOAD_EXPECTATIONS) == 104


def test_wp6_1_each_owner_row_payload_variant_carries_its_independent_minimum_facts() -> None:
    catalogue, _ = _documents()
    for row in catalogue["rows"]:
        expectation = PAYLOAD_EXPECTATIONS[row["key"]]
        schema = _schema(row["command_schema_identity"]["command_schema_path"])
        variants = _applicable_payload_variants(schema, expectation)

        assert variants, (
            f"{row['key']}: no payload variant matches independently specified "
            f"discriminants {dict(expectation.selectors)!r}"
        )
        for variant in variants:
            required = set(variant.get("required", []))
            assert expectation.required_fields <= required, (
                f"{row['key']}: applicable payload variant omits {sorted(expectation.required_fields - required)!r}"
            )


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
    "command_type",
    "command_schema_id",
    "command_schema_version",
    "command_schema_sha256",
    "idempotency_key",
    "command_payload_hash",
    "correlation_id",
    "causation_id",
    "actor_id",
    "authority_grant_id",
    "occurred_at",
    "recorded_at",
    "payload",
    "previous_event_hash",
    "event_hash",
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


def test_wp6_1_scope_variants_bind_closed_member_and_disposition_facts() -> None:
    catalogue, _ = _documents()
    rows = {row["key"]: row for row in catalogue["rows"]}
    create = _schema(rows["scope.create"]["command_schema_identity"]["command_schema_path"])
    member = create["$defs"]["scope_member"]
    assert member["additionalProperties"] is False
    assert set(member["required"]) == {"member_id", "member_kind", "required_disposition"}
    create_required = set(create["$defs"]["payload"]["oneOf"][0]["required"])
    assert create_required >= {
        "new_scope_definition_id",
        "members",
        "dependencies",
        "ordering_rules",
        "completion_rule",
        "authority_rule",
        "effective_at",
        "supersession_rule",
    }
    for key in ("scope.amend_revision", "scope.complete"):
        schema = _schema(rows[key]["command_schema_identity"]["command_schema_path"])
        disposition = schema["$defs"]["member_disposition"]
        assert disposition["additionalProperties"] is False
        assert set(disposition["required"]) == {"member_id", "member_kind", "disposition"}


_MESSAGE_UNIVERSAL = {
    "new_message_id",
    "message_type",
    "sender_actor_id",
    "recipient_actor_ids",
    "audience",
    "thread_id",
    "reply_to_message_id",
    "typed_subject",
    "sensitivity_class",
    "retention_class",
}


def test_wp6_1_message_command_and_event_variants_bind_universal_facts_and_body_exclusivity() -> None:
    catalogue, _ = _documents()
    row = next(item for item in catalogue["rows"] if item["key"] == "message.publish_assignment")
    identities = [row["command_schema_identity"], row["event_schema_bindings"][0]]
    registry = SchemaRegistry(SCHEMA_ROOT)
    for identity in identities:
        kind = "command" if "command_schema_path" in identity else "event"
        schema = _schema(identity[f"{kind}_schema_path"])
        variants = schema["$defs"]["payload"]["oneOf"]
        assert len(variants) == 10
        for index, variant in enumerate(variants):
            assert set(variant["required"]) >= _MESSAGE_UNIVERSAL
            assert {"required": ["body"]} in variant["oneOf"]
            assert {"required": ["body_artefact_ref"]} in variant["oneOf"]
            instance = _schema_value(schema, schema)
            instance["payload"] = _schema_value(variant, schema)
            registry.validate(schema["$id"], instance)
            missing = json.loads(json.dumps(instance))
            missing["payload"].pop("typed_subject")
            with pytest.raises(SchemaError):
                registry.validate(schema["$id"], missing)
            assert index < 10
