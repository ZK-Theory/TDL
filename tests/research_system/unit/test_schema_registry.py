import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import shutil

import pytest

from jsonschema import Draft202012Validator, FormatChecker

from research_system.errors import SchemaError
from research_system.schema_registry import (
    SchemaBinding,
    SchemaRegistry,
    _is_rfc3339_date_time,
    authority_schema_registry,
    runtime_schema_registry,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = REPO_ROOT / ".research-system" / "schemas"
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


def _event_payload():
    return {
        "event_id": f"evt_{UUID7}",
        "event_type": "TaskCreated",
        "schema_id": "ars://core/event/TaskCreated",
        "schema_version": "1.0.0",
        "project_id": "prj_01978abc-0002-7000-8000-000000000002",
        "stream_id": "tsk_01978abc-0003-7000-8000-000000000003",
        "stream_version": 1,
        "global_position": 1,
        "transaction_id": "txb_01978abc-0004-7000-8000-000000000004",
        "transaction_index": 1,
        "transaction_count": 1,
        "command_id": "cmd_01978abc-0005-7000-8000-000000000005",
        "command_type": "CreateTask",
        "idempotency_key": "create-task-1",
        "command_payload_hash": "1" * 64,
        "correlation_id": "synthetic-workflow-1",
        "causation_id": None,
        "actor_id": "act_01978abc-0006-7000-8000-000000000006",
        "authority_grant_id": "agr_01978abc-0007-7000-8000-000000000007",
        "occurred_at": None,
        "recorded_at": "2026-07-01T12:00:00Z",
        "payload": {},
        "previous_event_hash": "0" * 64,
        "event_hash": "2" * 64,
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


def test_generic_event_envelope_accepts_optional_command_schema_provenance():
    registry = SchemaRegistry(SCHEMAS)
    legacy = _event_payload()
    registry.validate("ars://core/event", legacy)

    current = {
        **legacy,
        "command_schema_id": "ars://core/command/CreateTask",
        "command_schema_version": "1.0.0",
        "command_schema_sha256": "3" * 64,
    }
    registry.validate("ars://core/event", current)


@pytest.mark.parametrize(
    "field",
    [
        "command_schema_id",
        "command_schema_version",
        "command_schema_sha256",
    ],
)
def test_generic_event_envelope_rejects_partial_command_schema_provenance(field):
    event = _event_payload()
    event[field] = {
        "command_schema_id": "ars://core/command/CreateTask",
        "command_schema_version": "1.0.0",
        "command_schema_sha256": "3" * 64,
    }[field]

    with pytest.raises(SchemaError, match="command_schema"):
        SchemaRegistry(SCHEMAS).validate("ars://core/event", event)


def test_generic_event_instance_version_remains_1_0_0_after_provenance_tightening():
    # ``schema_version`` identifies the persisted event instance family. Exact
    # validator bytes remain independently identifiable through SchemaIdentity,
    # so making optional provenance all-or-none does not reinterpret instances.
    schema = json.loads((SCHEMAS / "core" / "event.schema.json").read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"] == {"const": "1.0.0"}


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


def test_versioned_catalogue_returns_exact_validated_source_identity(tmp_path):
    root = tmp_path / "schemas"
    root.mkdir()
    schema_id = "ars://test/versioned"
    sources = {
        version: (
            "{\n"
            '  "$schema": "https://json-schema.org/draft/2020-12/schema",\n'
            f'  "$id": "{schema_id}",\n'
            '  "type": "object",\n'
            f'  "properties": {{"schema_version": {{"const": "{version}"}}}},\n'
            '  "required": ["schema_version"],\n'
            '  "additionalProperties": false\n'
            "}\n"
        ).encode()
        for version in ("1.0.0", "2.0.0")
    }
    for version, raw_bytes in sources.items():
        (root / f"{version}.schema.json").write_bytes(raw_bytes)

    identity = SchemaRegistry(root).validate(
        schema_id,
        {"schema_version": "1.0.0"},
        schema_version="1.0.0",
    )

    assert identity.schema_id == schema_id
    assert identity.schema_version == "1.0.0"
    assert identity.raw_bytes == sources["1.0.0"]
    assert identity.sha256 == sha256(sources["1.0.0"]).hexdigest()


def test_validation_rejects_wrong_recorded_source_hash():
    registry = SchemaRegistry(SCHEMAS)

    with pytest.raises(SchemaError, match="schema hash mismatch"):
        registry.validate(
            "ars://core/command",
            _command_payload(),
            schema_version="1.0.0",
            expected_sha256="0" * 64,
        )


def test_materialized_schema_is_inert_until_exact_binding_is_active():
    schema_id = "ars://core/command/CreateTask"
    registry = SchemaRegistry(SCHEMAS)

    assert not registry.is_active(schema_id, "1.0.0")
    with pytest.raises(SchemaError, match="inactive schema"):
        registry.validate_active(
            schema_id,
            {},
            schema_version="1.0.0",
        )

    active = SchemaRegistry(
        SCHEMAS,
        active_bindings=(SchemaBinding(schema_id, "1.0.0"),),
    )
    assert active.is_active(schema_id, "1.0.0")


def test_runtime_bindings_activate_first_scope_task_slice_and_t2_verticals():
    registry = runtime_schema_registry(SCHEMAS)

    expected_commands = {
        "CreateScopeDefinition": (
            "ars://core/command/CreateScopeDefinition",
            "1.0.0",
        ),
        "AmendScopeDefinition": (
            "ars://core/command/AmendScopeDefinition",
            "1.0.0",
        ),
        "SupersedeScopeDefinition": (
            "ars://core/command/SupersedeScopeDefinition",
            "1.0.0",
        ),
        "CreateTask": ("ars://core/command/CreateTask", "1.0.0"),
        "AmendTask": ("ars://core/command/AmendTask", "1.0.0"),
        "SupersedeTask": ("ars://core/command/SupersedeTask", "1.0.0"),
        "IssueCostGrant": ("ars://wp6-2/t2/command/IssueCostGrant", "1.0.0"),
        "AuthorizeProviderIssue": ("ars://wp6-2/t2/command/AuthorizeProviderIssue", "1.0.0"),
        "RecordProviderReceipt": ("ars://wp6-2/t2/command/RecordProviderReceipt", "1.0.0"),
    }
    expected_events = {
        "ScopeDefinitionCreated": (
            "ars://core/event/ScopeDefinitionCreated",
            "1.0.0",
        ),
        "ScopeDefinitionAmended": (
            "ars://core/event/ScopeDefinitionAmended",
            "1.0.0",
        ),
        "ScopeDefinitionSuperseded": (
            "ars://core/event/ScopeDefinitionSuperseded",
            "1.0.0",
        ),
        "TaskCreated": ("ars://core/event/TaskCreated", "1.0.0"),
        "TaskAmended": ("ars://core/event/TaskAmended", "1.0.0"),
        "TaskSuperseded": ("ars://core/event/TaskSuperseded", "1.0.0"),
        "ReleaseGateDecisionPublished": (
            "ars://core/event/ReleaseGateDecisionPublished",
            "1.1.0",
        ),
        "CostGrantIssued": ("ars://wp6-2/t2/event/CostGrantIssued", "1.1.0"),
        "CostGrantReserved": ("ars://wp6-2/t2/event/CostGrantReserved", "1.1.0"),
        "ProviderCommandIssued": ("ars://wp6-2/t2/event/ProviderCommandIssued", "1.1.0"),
        "ProviderReceiptRecorded": ("ars://wp6-2/t2/event/ProviderReceiptRecorded", "1.1.0"),
        "CostGrantReconciled": ("ars://wp6-2/t2/event/CostGrantReconciled", "1.1.0"),
    }

    observed_commands = {}
    for command_type in expected_commands:
        binding = registry.command_binding(command_type)
        assert binding is not None, f"missing runtime command binding: {command_type}"
        observed_commands[command_type] = (
            binding.schema_id,
            binding.schema_version,
        )
    assert observed_commands == expected_commands

    observed_events = {}
    for event_type in expected_events:
        binding = registry.event_binding(event_type)
        assert binding is not None, f"missing runtime event binding: {event_type}"
        observed_events[event_type] = (
            binding.schema_id,
            binding.schema_version,
        )
    assert observed_events == expected_events
    assert not registry.is_active("ars://core/command/ClaimDispatch", "1.0.0")
    assert not registry.is_active("ars://core/event/DispatchClaimed", "1.0.0")


def test_runtime_registry_reuses_one_instance_for_resolved_root_aliases():
    registry = runtime_schema_registry(SCHEMAS)

    assert runtime_schema_registry(str(SCHEMAS)) is registry
    assert registry.requires_command_provenance
    assert registry.command_binding("CreateTask") == SchemaBinding(
        "ars://core/command/CreateTask",
        "1.0.0",
        command_type="CreateTask",
    )


def test_schema_id_index_avoids_catalogue_scan_for_contains_and_unversioned_resolution():
    class IterationForbiddenDict(dict):
        def __iter__(self):
            raise AssertionError("schema catalogue was scanned")

        def items(self):
            raise AssertionError("schema catalogue was scanned")

    registry = SchemaRegistry(SCHEMAS)
    registry._schemas = IterationForbiddenDict(registry._schemas)

    assert registry.contains("ars://core/command")
    registry.validate("ars://core/command", _command_payload())
    with pytest.raises(SchemaError, match="schema version required"):
        registry.validate(
            "ars://wp6-2/t2/event/CostGrantIssued",
            {"schema_version": "1.1.0"},
        )


def test_t2_event_versions_coexist_and_v1_1_identity_binds_exact_raw_bytes():
    registry = runtime_schema_registry(SCHEMAS)
    schema_id = "ars://wp6-2/t2/event/CostGrantIssued"

    with pytest.raises(SchemaError, match="schema version required"):
        registry.validate(schema_id, {"schema_version": "1.1.0"})

    identity = registry.resolve_identity(schema_id, "1.1.0")
    source = SCHEMAS / "wp6-2-t2" / "events" / "cost-grant-issued.v1-1.schema.json"

    assert identity.source_path == source.resolve()
    assert identity.raw_bytes == source.read_bytes()
    assert identity.sha256 == sha256(source.read_bytes()).hexdigest()


def test_t2_v1_1_siblings_have_independent_exact_new_write_contracts():
    expected = {
        "cost-grant-issued.v1-1.schema.json": (
            "CostGrantIssued",
            "IssueCostGrant",
            "7242d8f79d2da6c20339983674e3aa24628edbfd72bfc01d697d815167b015db",
        ),
        "cost-grant-reconciled.v1-1.schema.json": (
            "CostGrantReconciled",
            "RecordProviderReceipt",
            "e961dd8100d4c6098bd502337a50168c7aeba66257e9cbae136fefb1a636a892",
        ),
        "cost-grant-reserved.v1-1.schema.json": (
            "CostGrantReserved",
            "AuthorizeProviderIssue",
            "0dfeea8634da23f9c44042a2e78bddb9dac27d396a267289037c28d0c2e49273",
        ),
        "provider-command-issued.v1-1.schema.json": (
            "ProviderCommandIssued",
            "AuthorizeProviderIssue",
            "eb09377ae6e0e73a35d92028a082970708eeae730a41648e787e38a1e13c3f1f",
        ),
        "provider-receipt-recorded.v1-1.schema.json": (
            "ProviderReceiptRecorded",
            "RecordProviderReceipt",
            "1294ee2cf0ba634010a1b63bffa3e69696ec0d5fc9b1dff2610e2177285dcc5c",
        ),
    }
    event_root = SCHEMAS / "wp6-2-t2" / "events"
    assert {path.name for path in event_root.glob("*.v1-1.schema.json")} == set(expected)
    provenance = {
        "command_schema_id",
        "command_schema_version",
        "command_schema_sha256",
    }

    for filename, (event_type, command_type, raw_sha256) in expected.items():
        current_path = event_root / filename
        legacy_path = event_root / filename.replace(".v1-1", "")
        current = json.loads(current_path.read_bytes())
        legacy = json.loads(legacy_path.read_bytes())

        assert current["$id"] == legacy["$id"] == f"ars://wp6-2/t2/event/{event_type}"
        assert current["properties"]["schema_version"] == {"const": "1.1.0"}
        assert set(current["required"]) == set(legacy["required"]) | provenance
        assert set(current["properties"]) == set(legacy["properties"]) | provenance
        assert current["properties"]["command_schema_id"] == {"const": f"ars://wp6-2/t2/command/{command_type}"}
        assert current["properties"]["command_schema_version"] == {"const": "1.0.0"}
        assert current["properties"]["command_schema_sha256"] == {
            "type": "string",
            "pattern": "^[0-9a-f]{64}$",
        }
        assert current["additionalProperties"] is False
        assert sha256(current_path.read_bytes()).hexdigest() == raw_sha256


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
        "receipt-v2.schema.json",
        "release-gate-decision-published.schema.json",
        "release-gate-decision-published.v1-1.schema.json",
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
