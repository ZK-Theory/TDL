import json
from copy import deepcopy
from pathlib import Path
import shutil

import pytest

from jsonschema import Draft202012Validator, FormatChecker

from research_system.errors import SchemaError
from research_system.schema_registry import (
    SchemaRegistry,
    _is_rfc3339_date_time,
    authority_schema_registry,
)


SCHEMAS = Path(".research-system/schemas")
UUID7 = "01978abc-0001-7000-8000-000000000001"

# Instances chosen to separate "does not apply" from "applies and fails".
# ``format`` is defined to be ignored for instance types it does not target, so
# every non-string conforms vacuously; only malformed *strings* may be rejected.
_DATE_TIME_INSTANCES = (
    None,
    123,
    12.5,
    True,
    [],
    {},
    "2026-07-28T00:00:00Z",
    "2026-07-28T00:00:00z",
    "2026-07-28T00:00:00+01:00",
    "2026-07-28T00:00:00.123456Z",
    "nope",
    "",
    "2026-07-28",
    "2026-13-01T00:00:00Z",
)


def _command_payload():
    return {
        "command_id": f"cmd_{UUID7}",
        "command_type": "CreateTask",
        "schema_id": "ars://core/command",
        "schema_version": "1.0.0",
        "submitted_at": "2026-07-01T12:00:00Z",
        "actor_id": "act_01978abc-0002-7000-8000-000000000002",
        "on_behalf_of_actor_id": None,
        "authority_grant_id": "agr_01978abc-0003-7000-8000-000000000003",
        "target_stream_id": "tsk_01978abc-0004-7000-8000-000000000004",
        "expected_stream_version": 0,
        "idempotency_key": "create-task-1",
        "correlation_id": "synthetic-workflow-1",
        "causation_id": None,
        "reason": "synthetic P0 test",
        "evidence_refs": [],
        "payload": {},
    }


def _upstream_date_time_checker():
    """Return jsonschema's own ``date-time`` predicate, or None if unavailable.

    ``schema_registry`` registers its fallback on ``Draft202012Validator``'s
    shared checker *instance*, so that instance cannot distinguish the two
    implementations. A freshly constructed ``FormatChecker`` carries only the
    class-level registrations, which are upstream's.
    """
    entry = FormatChecker().checkers.get("date-time")
    return None if entry is None else entry[0]


def test_a_date_time_format_checker_is_registered():
    """Absence must be loud: without a checker, ``format`` silently no-ops.

    jsonschema does not fail when a format has no checker -- it ignores the
    keyword, so every malformed timestamp in the system would validate. That is
    the failure mode the fallback exists to prevent, so assert the outcome the
    fallback is meant to guarantee rather than trusting it fired.
    """
    assert "date-time" in Draft202012Validator.FORMAT_CHECKER.checkers


def test_fallback_date_time_checker_matches_upstream():
    """The fallback must agree with the checker it substitutes for.

    A substitute is correct only relative to what it replaces, not to its own
    intent. This previously returned False for non-strings while upstream
    returns True, making schema strictness depend on whether an optional
    package happened to be installed.
    """
    upstream = _upstream_date_time_checker()
    if upstream is None:
        pytest.skip("rfc3339-validator absent; no upstream checker to compare against")

    divergent = {
        instance: (_is_rfc3339_date_time(instance), upstream(instance))
        for instance in _DATE_TIME_INSTANCES
        if _is_rfc3339_date_time(instance) != upstream(instance)
    }
    assert not divergent, f"fallback diverges from upstream (fallback, upstream): {divergent}"


@pytest.mark.parametrize("instance", [None, 123, 12.5, True, [], {}])
def test_fallback_ignores_non_string_instances(instance):
    """Pins the specific regression: ``format`` does not apply to non-strings.

    Kept separate from the agreement test so this still fails loudly in an
    environment where the upstream comparison has to skip.
    """
    assert _is_rfc3339_date_time(instance) is True


@pytest.mark.parametrize("instance", ["nope", "", "2026-07-28", "2026-13-01T00:00:00Z"])
def test_fallback_still_rejects_malformed_timestamp_strings(instance):
    """Negative control: the relaxation above must not have made it vacuous."""
    assert _is_rfc3339_date_time(instance) is False


def test_registry_validates_command_envelope():
    SchemaRegistry(SCHEMAS).validate("ars://core/command", _command_payload())


def test_registry_rejects_malformed_command_submission_timestamp():
    registry = SchemaRegistry(SCHEMAS)
    payload = _command_payload()
    registry.validate("ars://core/command", payload)

    payload["submitted_at"] = "not-a-timestampZ"
    with pytest.raises(SchemaError, match="submitted_at"):
        registry.validate("ars://core/command", payload)


def test_registry_rejects_non_uuid7_command_identity():
    payload = _command_payload()
    payload["command_id"] = "cmd_" + "1" * 32
    with pytest.raises(SchemaError, match="command_id"):
        SchemaRegistry(SCHEMAS).validate("ars://core/command", payload)


def test_registry_rejects_unknown_schema():
    with pytest.raises(SchemaError, match="unknown schema"):
        SchemaRegistry(SCHEMAS).validate("ars://missing", {})


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("extra",), "forbidden"),
        (("project_id",), "prj_not-a-uuid7"),
        (("target_grant_id",), "agr_not-a-uuid7"),
        (("target_grant_sha256",), "0" * 63),
        (("authority_grant_sha256",), "not-a-hash"),
        (("reason",), ""),
    ],
)
def test_revoke_authority_grant_payload_schema_is_strict(path, value):
    payload = {
        "project_id": "prj_01978abc-1000-7000-8000-000000001000",
        "target_grant_id": "agr_01978abc-1001-7000-8000-000000001001",
        "target_grant_sha256": "1" * 64,
        "authority_grant_sha256": "2" * 64,
        "reason": "synthetic revocation",
    }
    invalid = deepcopy(payload)
    invalid[path[0]] = value
    registry = SchemaRegistry(SCHEMAS)
    registry.validate("ars://core/command/RevokeAuthorityGrant/payload", payload)
    with pytest.raises(SchemaError):
        registry.validate("ars://core/command/RevokeAuthorityGrant/payload", invalid)


def test_every_core_schema_declares_closed_object_contract():
    paths = sorted((SCHEMAS / "core").glob("*.schema.json"))
    assert {path.name for path in paths} == {
        "authority-bootstrap-input.schema.json",
        "authority-bootstrap-manifest.schema.json",
        "authority-grant-activated.schema.json",
        "authority-grant-revoked.schema.json",
        "authority-grant.schema.json",
        "authority-root-initialized.schema.json",
        "command.schema.json",
        "event.schema.json",
        "receipt.schema.json",
        "release-gate-decision-published.schema.json",
        "revoke-authority-grant.schema.json",
        "store-identity-1.1.schema.json",
        "task.schema.json",
    }
    for path in paths:
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"].startswith("ars://core/")
        assert schema["type"] == "object"
        assert schema["required"]
        assert schema["properties"]
        assert schema["additionalProperties"] is False


def test_every_command_schema_declares_closed_object_contract():
    paths = sorted((SCHEMAS / "core" / "commands").glob("*.schema.json"))
    assert len(paths) == 87
    for path in paths:
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"].startswith("ars://core/command/")
        assert schema["type"] == "object"
        assert schema["required"]
        assert schema["properties"]
        assert schema["additionalProperties"] is False


def test_task_schema_uses_w2_status_vocabulary():
    task = {
        "schema_id": "ars://core/task",
        "schema_version": "1.0.0",
        "task_id": "tsk_01978abc-0004-7000-8000-000000000004",
        "record_revision": 1,
        "status": "draft",
        "content_hash": "0" * 64,
    }
    registry = SchemaRegistry(SCHEMAS)
    registry.validate("ars://core/task", task)
    task["status"] = "proposed"
    with pytest.raises(SchemaError, match="status"):
        registry.validate("ars://core/task", task)


def test_authority_event_and_store_schemas_require_complete_registered_ids():
    registry = SchemaRegistry(SCHEMAS)
    root_payload = {
        "bootstrap_manifest_sha256": "0" * 64,
        "authorizing_grant_id": "agr_not-a-uuid7",
        "authorizing_grant_sha256": "1" * 64,
        "activated_grant_id": "agr_not-a-uuid7",
        "activated_grant_sha256": "1" * 64,
    }
    with pytest.raises(SchemaError, match="authorizing_grant_id"):
        registry.validate("ars://core/event/AuthorityRootInitialized/payload", root_payload)

    store_identity = {
        "schema_id": "ars://core/store-identity",
        "schema_version": "1.1.0",
        "store_nonce": "0" * 32,
        "project_id": "prj_not-a-uuid7",
        "bootstrap_manifest_sha256": "1" * 64,
        "store_identity": "2" * 64,
        "control_root": "C:/synthetic-control",
        "code_roots": ["C:/synthetic-code"],
        "endpoint_scheme": "local-cli",
        "manifest_hash": "3" * 64,
    }
    with pytest.raises(SchemaError, match="project_id"):
        registry.validate("ars://core/store-identity/1.1", store_identity)


def test_store_identity_1_1_schema_accepts_optional_physical_schema_binding():
    registry = SchemaRegistry(SCHEMAS)
    manifest = {
        "schema_id": "ars://core/store-identity",
        "schema_version": "1.1.0",
        "store_nonce": "0" * 32,
        "project_id": "prj_01978abc-0001-7000-8000-000000000001",
        "bootstrap_manifest_sha256": "1" * 64,
        "store_identity": "2" * 64,
        "control_root": "C:/synthetic-control",
        "code_roots": ["C:/synthetic-code"],
        "endpoint_scheme": "local-cli",
        "manifest_hash": "3" * 64,
    }

    registry.validate("ars://core/store-identity/1.1", manifest)
    manifest["schema_root"] = "C:/synthetic-code/.research-system/schemas"
    registry.validate("ars://core/store-identity/1.1", manifest)
    manifest["schema_binding_version"] = "1.0.0"
    registry.validate("ars://core/store-identity/1.1", manifest)

    manifest.pop("schema_root")
    with pytest.raises(SchemaError, match="schema_root"):
        registry.validate("ars://core/store-identity/1.1", manifest)


def test_authority_registry_rejects_missing_revocation_payload_schema(tmp_path):
    schema_root = tmp_path / "schemas"
    shutil.copytree(SCHEMAS, schema_root)
    (schema_root / "core" / "authority-grant-revoked.schema.json").unlink()

    with pytest.raises(
        SchemaError,
        match="ars://core/event/AuthorityGrantRevoked/payload",
    ):
        authority_schema_registry(schema_root)
