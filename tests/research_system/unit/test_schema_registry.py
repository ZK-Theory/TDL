import json
from dataclasses import FrozenInstanceError
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import shutil

import pytest

from jsonschema import Draft202012Validator, FormatChecker

from research_system.errors import SchemaError
from research_system.operations.resources import (
    RESOURCE_GRANT_V1_1_SCHEMA_ID,
    RESOURCE_GRANT_V1_1_SCHEMA_SHA256,
    RESOURCE_GRANT_V1_1_SCHEMA_VERSION,
)
from research_system.schema_registry import (
    RegisteredSchema,
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


def test_validation_and_resolution_share_one_frozen_registered_schema(tmp_path):
    root = tmp_path / "schemas"
    root.mkdir()
    source = root / "registered.schema.json"
    source.write_text(
        "{\n"
        '  "$schema": "https://json-schema.org/draft/2020-12/schema",\n'
        '  "$id": "ars://test/registered",\n'
        '  "type": "object",\n'
        '  "properties": {"schema_version": {"const": "1.0.0"}},\n'
        '  "required": ["schema_version"],\n'
        '  "additionalProperties": false\n'
        "}\n",
        encoding="utf-8",
        newline="\n",
    )
    registry = SchemaRegistry(root)

    validated = registry.validate(
        "ars://test/registered",
        {"schema_version": "1.0.0"},
        schema_version="1.0.0",
    )
    resolved = registry.resolve_identity("ars://test/registered", "1.0.0")

    assert isinstance(validated, RegisteredSchema)
    assert validated is resolved
    assert validated.raw_bytes_sha256 == sha256(source.read_bytes()).hexdigest()
    assert validated.parsed["$id"] == validated.schema_id
    with pytest.raises(FrozenInstanceError):
        validated.schema_id = "ars://test/changed"
    with pytest.raises(TypeError):
        validated.parsed["$id"] = "ars://test/changed"
    with pytest.raises(TypeError):
        validated.parsed["properties"]["schema_version"]["const"] = "2.0.0"
    with pytest.raises(TypeError):
        validated.parsed["required"].append("changed")

    source.write_text("{}\n", encoding="utf-8", newline="\n")
    validated_after_source_mutation = registry.validate(
        "ars://test/registered",
        {"schema_version": "1.0.0"},
        schema_version="1.0.0",
    )
    assert validated_after_source_mutation is validated
    assert validated_after_source_mutation.raw_bytes != source.read_bytes()


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda parsed: dict.__setitem__(parsed, "additionalProperties", True),
            id="dict-base-mutator",
        ),
        pytest.param(
            lambda parsed: list.append(parsed["required"], "unexpected"),
            id="list-base-mutator",
        ),
        pytest.param(
            lambda parsed: dict.__setitem__(
                parsed["properties"]["schema_version"],
                "const",
                "2.0.0",
            ),
            id="nested-base-mutator",
        ),
    ],
)
def test_registered_schema_semantics_cannot_diverge_from_raw_digest(tmp_path, mutate):
    root = tmp_path / "schemas"
    root.mkdir()
    source = root / "immutable.schema.json"
    source.write_text(
        "{\n"
        '  "$schema": "https://json-schema.org/draft/2020-12/schema",\n'
        '  "$id": "ars://test/deep-immutable",\n'
        '  "type": "object",\n'
        '  "properties": {"schema_version": {"const": "1.0.0"}},\n'
        '  "required": ["schema_version"],\n'
        '  "additionalProperties": false\n'
        "}\n",
        encoding="utf-8",
        newline="\n",
    )
    registry = SchemaRegistry(root)
    registered = registry.resolve_identity("ars://test/deep-immutable", "1.0.0")
    original_digest = registered.raw_bytes_sha256

    with pytest.raises(TypeError, match="immutable|descriptor"):
        mutate(registered.parsed)

    with pytest.raises(SchemaError):
        registry.validate(
            "ars://test/deep-immutable",
            {"schema_version": "wrong", "unexpected": True},
            schema_version="1.0.0",
        )
    assert registered.raw_bytes_sha256 == original_digest == sha256(registered.raw_bytes).hexdigest()


def test_registry_rejects_duplicate_exact_schema_identity(tmp_path):
    root = tmp_path / "schemas"
    root.mkdir()
    schema = (
        "{\n"
        '  "$schema": "https://json-schema.org/draft/2020-12/schema",\n'
        '  "$id": "ars://test/duplicate",\n'
        '  "schema_version": "1.0.0",\n'
        '  "type": "object"\n'
        "}\n"
    )
    (root / "first.schema.json").write_text(schema, encoding="utf-8", newline="\n")
    (root / "second.schema.json").write_text(schema, encoding="utf-8", newline="\n")

    with pytest.raises(SchemaError, match="duplicate schema"):
        SchemaRegistry(root)


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
        "CreateBackup": ("ars://core/command/CreateBackup", "1.0.0"),
        "ActivateAuthorityGrant": (
            "ars://core/command/ActivateAuthorityGrant",
            "1.1.0",
        ),
        "RevokeIssuedAuthorityGrant": (
            "ars://core/command/RevokeIssuedAuthorityGrant",
            "1.0.0",
        ),
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
    assert registry.command_binding("ClaimDispatch") == SchemaBinding(
        "ars://core/command/ClaimDispatch",
        "1.0.0",
        command_type="ClaimDispatch",
    )
    assert registry.event_binding("DispatchClaimed", "ClaimDispatch") == SchemaBinding(
        "ars://core/event/DispatchClaimed",
        "1.0.0",
        event_type="DispatchClaimed",
        producer_command_type="ClaimDispatch",
    )
    assert registry.event_binding("TaskClaimStarted", "ClaimDispatch") == SchemaBinding(
        "ars://core/event/TaskClaimStarted",
        "1.0.0",
        event_type="TaskClaimStarted",
        producer_command_type="ClaimDispatch",
    )
    assert registry.event_binding("DispatchClaimed", "WrongProducer") is None
    assert registry.event_binding("DispatchClaimed", None) is None
    assert registry.has_producer_bindings("DispatchClaimed")
    assert registry.event_binding("TaskClaimStarted", "WrongProducer") is None
    assert registry.event_binding("TaskClaimStarted", None) is None
    assert registry.has_producer_bindings("TaskClaimStarted")
    assert registry.event_binding("BackupCreated", "CreateBackup") == SchemaBinding(
        "ars://core/event/BackupCreated",
        "1.0.0",
        event_type="BackupCreated",
        producer_command_type="CreateBackup",
    )
    assert registry.event_binding("BackupCreated", "WrongProducer") is None
    assert registry.event_binding("BackupCreated", None) is None
    assert registry.has_producer_bindings("BackupCreated")
    assert registry.event_binding(
        "ReviewRequested",
        "RequestDiscoveryOutcomeReview",
    ) == SchemaBinding(
        "ars://core/event/ReviewRequested",
        "1.0.0",
        event_type="ReviewRequested",
        producer_command_type="RequestDiscoveryOutcomeReview",
    )
    assert registry.event_binding(
        "ReviewVerdictRecorded",
        "ReviewDiscoveryOutcome",
    ) == SchemaBinding(
        "ars://core/event/ReviewVerdictRecorded",
        "1.0.0",
        event_type="ReviewVerdictRecorded",
        producer_command_type="ReviewDiscoveryOutcome",
    )
    assert registry.event_binding("ReviewRequested", "WrongProducer") is None
    assert registry.event_binding("ReviewRequested", None) is None
    assert registry.event_binding("ReviewVerdictRecorded", "WrongProducer") is None
    assert registry.event_binding("ReviewVerdictRecorded", None) is None
    assert (
        registry.resolve_identity("ars://core/command/CreateBackup", "1.0.0").sha256
        == "16fe11c88fbfce48185fa666be93978f02416013addf83a4c2c3634884292a24"
    )
    assert (
        registry.resolve_identity("ars://core/event/BackupCreated", "1.0.0").sha256
        == "78741041eaa8ec5de1dbadfb0a5d549b222ccf2873aa579c9f2a0db4f432fa40"
    )
    assert registry.event_binding(
        "AuthorityGrantActivated",
        "ActivateAuthorityGrant",
    ) == SchemaBinding(
        "ars://core/event/ScopedAuthorityGrantActivated",
        "1.1.0",
        event_type="AuthorityGrantActivated",
        producer_command_type="ActivateAuthorityGrant",
    )
    assert registry.event_binding(
        "AuthorityGrantRevoked",
        "RevokeIssuedAuthorityGrant",
    ) == SchemaBinding(
        "ars://core/event/IssuedAuthorityGrantRevoked",
        "1.1.0",
        event_type="AuthorityGrantRevoked",
        producer_command_type="RevokeIssuedAuthorityGrant",
    )
    assert registry.event_binding("AuthorityGrantActivated", "WrongProducer") is None
    assert registry.event_binding("AuthorityGrantActivated", None) is None
    assert registry.has_producer_bindings("AuthorityGrantActivated")
    assert registry.is_active("ars://core/scoped-authority-grant", "2.1.0")
    assert registry.is_active(
        "ars://core/policy-action/AcceptR3AssuranceRequirement",
        "1.0.0",
    )
    assert registry.policy_action_binding(
        "accept_r3_assurance_requirement",
    ) == SchemaBinding(
        "ars://core/policy-action/AcceptR3AssuranceRequirement",
        "1.0.0",
        policy_action_type="accept_r3_assurance_requirement",
    )
    assert registry.policy_action_binding("wrong_policy_action") is None


def test_runtime_binding_inventory_is_public_and_stably_ordered():
    bindings = runtime_schema_registry(SCHEMAS).active_bindings()

    assert len(bindings) == 261
    assert bindings == tuple(
        sorted(
            bindings,
            key=lambda binding: (
                binding.schema_id,
                binding.schema_version,
                binding.command_type or "",
                binding.event_type or "",
                binding.producer_command_type or "",
                binding.policy_action_type or "",
            ),
        )
    )
    assert len(set(bindings)) == len(bindings)


@pytest.mark.parametrize(
    ("command_type", "event_type"),
    [
        ("SupersedeDiscoveryRecord", "CandidateSuperseded"),
    ],
)
def test_wp6_6_supersession_has_sealed_generic_envelope_bindings(command_type, event_type):
    """OR-002 has accepted content but no dedicated command/event envelope."""
    registry = runtime_schema_registry(SCHEMAS)

    assert registry.command_binding(command_type) == SchemaBinding(
        "ars://core/command",
        "1.0.0",
        command_type=command_type,
    )
    assert registry.event_binding(event_type, command_type) == SchemaBinding(
        "ars://core/event",
        "1.0.0",
        event_type=event_type,
        producer_command_type=command_type,
    )
    assert registry.event_binding(event_type, "WrongProducer") is None
    assert registry.event_binding(event_type, None) is None
    assert registry.has_producer_bindings(event_type)


def test_wp6_6_annotation_route_remains_inactive_without_epoch_authority():
    registry = runtime_schema_registry(SCHEMAS)

    assert registry.command_binding("IngestDiscoveryAnnotation") is None
    assert registry.event_binding("DiscoveryAnnotationIngested", "IngestDiscoveryAnnotation") is None
    assert not registry.has_producer_bindings("DiscoveryAnnotationIngested")


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


def test_registry_binds_bytes_to_the_canonical_path_read_under_symlink_swap(tmp_path, monkeypatch):
    root = tmp_path / "schemas"
    targets = tmp_path / "targets"
    root.mkdir()
    targets.mkdir()
    first = targets / "first.schema.json"
    second = targets / "second.schema.json"
    first.write_text(
        json.dumps(
            {
                "$id": "ars://test/path-race",
                "title": "first",
                "type": "object",
                "properties": {"schema_version": {"const": "1.0.0"}},
            }
        ),
        encoding="utf-8",
    )
    second.write_text(
        json.dumps(
            {
                "$id": "ars://test/path-race",
                "title": "second",
                "type": "object",
                "properties": {"schema_version": {"const": "1.0.0"}},
            }
        ),
        encoding="utf-8",
    )
    alias = root / "active.schema.json"
    try:
        alias.symlink_to(first)
    except OSError as exc:
        pytest.skip(f"file symlink unavailable: {exc}")

    real_read_bytes = Path.read_bytes
    swapped = False

    def swap_after_alias_read(path: Path) -> bytes:
        nonlocal swapped
        raw = real_read_bytes(path)
        if path == first.resolve() and not swapped:
            alias.unlink()
            alias.symlink_to(second)
            swapped = True
        return raw

    monkeypatch.setattr(Path, "read_bytes", swap_after_alias_read)

    identity = SchemaRegistry(root).resolve_identity("ars://test/path-race", "1.0.0")

    assert swapped
    assert alias.resolve() == second
    assert identity.raw_bytes == real_read_bytes(identity.source_path)
    assert identity.raw_bytes_sha256 == sha256(identity.raw_bytes).hexdigest()


def test_resource_grant_versions_coexist_and_require_explicit_version():
    registry = SchemaRegistry(SCHEMAS)
    schema_id = RESOURCE_GRANT_V1_1_SCHEMA_ID

    legacy = registry.resolve_identity(schema_id, "1.0.0")
    current = registry.resolve_identity(schema_id, RESOURCE_GRANT_V1_1_SCHEMA_VERSION)
    source = SCHEMAS / "operations" / "resource-grant.v1-1.schema.json"

    assert legacy.source_path.name == "resource-grant.schema.json"
    assert current.source_path == source.resolve()
    assert current.raw_bytes == source.read_bytes()
    assert legacy.schema_id == current.schema_id == schema_id
    assert legacy.schema_version == "1.0.0"
    assert current.schema_version == RESOURCE_GRANT_V1_1_SCHEMA_VERSION
    assert RESOURCE_GRANT_V1_1_SCHEMA_SHA256 == "3cf8e8b48e90c63d06eb7f807d02ef15fdc0507416ac3a014dd326ae10e8da39"
    assert current.sha256 == RESOURCE_GRANT_V1_1_SCHEMA_SHA256
    assert sha256(source.read_bytes()).hexdigest() == RESOURCE_GRANT_V1_1_SCHEMA_SHA256
    with pytest.raises(SchemaError, match="schema version required"):
        registry.validate(schema_id, {})


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
    assert paths, "core schema catalogue is empty"
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
    assert paths, "command schema catalogue is empty"
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


def test_schema_identity_history_resolves_exact_superseded_bytes(tmp_path: Path) -> None:
    schema_id = "ars://test/collided-version"
    current = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": schema_id,
        "type": "object",
        "properties": {"schema_version": {"const": "1.0.0"}},
        "required": ["schema_version"],
        "additionalProperties": False,
    }
    superseded = deepcopy(current)
    superseded["properties"]["temporary_field"] = {"type": "string"}
    current_raw = json.dumps(current, sort_keys=True, separators=(",", ":")).encode("utf-8")
    superseded_raw = json.dumps(superseded, sort_keys=True, separators=(",", ":")).encode("utf-8")
    superseded_sha256 = sha256(superseded_raw).hexdigest()
    (tmp_path / "current.schema.json").write_bytes(current_raw)
    (tmp_path / "history").mkdir()
    archive_ref = f"history/sha256-{superseded_sha256}.json"
    (tmp_path / archive_ref).write_bytes(superseded_raw)
    manifest = {
        "schema_id": "ars://core/schema-identity-history",
        "schema_version": "1.0.0",
        "aliases": [
            {
                "schema_id": schema_id,
                "schema_version": "1.0.0",
                "raw_bytes_sha256": superseded_sha256,
                "archive_ref": archive_ref,
            }
        ],
    }
    (tmp_path / "schema-identity-history.json").write_bytes(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )

    registry = SchemaRegistry(tmp_path)

    assert registry.resolve_identity(schema_id, "1.0.0").raw_bytes == current_raw
    assert (
        registry.resolve_identity(
            schema_id,
            "1.0.0",
            expected_sha256=superseded_sha256,
        ).raw_bytes
        == superseded_raw
    )
    assert (
        registry.validate(
            schema_id,
            {"schema_version": "1.0.0"},
            expected_sha256=superseded_sha256,
        ).raw_bytes
        == superseded_raw
    )
    with pytest.raises(SchemaError, match="schema hash mismatch"):
        registry.resolve_identity(schema_id, "1.0.0", expected_sha256="0" * 64)

    active_registry = SchemaRegistry(
        tmp_path,
        active_bindings=(SchemaBinding(schema_id, "1.0.0", command_type="TestCommand"),),
    )
    with pytest.raises(SchemaError, match="active schema hash mismatch"):
        active_registry.validate_active(
            schema_id,
            {"schema_version": "1.0.0"},
            schema_version="1.0.0",
            expected_sha256=superseded_sha256,
        )


def test_advance_store_binding_history_is_replayable_but_v1_2_is_active() -> None:
    registry = runtime_schema_registry(SCHEMAS)
    schema_id = "ars://wp6-6/gate6/binding-repair/command/AdvanceStoreBinding"

    assert registry.resolve_identity(schema_id, "1.0.0").sha256 == (
        "cbbe5b6b3a9cd6d97c8c648cfe7c49e16b3b813b800e28ffa94c1d7ebe4f8157"
    )
    superseded_sha256 = "5f15223aeec3cbe0825a49b5395467a62cda255378496a04fc83941557dbc3cb"
    assert (
        registry.resolve_identity(
            schema_id,
            "1.0.0",
            expected_sha256=superseded_sha256,
        ).sha256
        == superseded_sha256
    )
    v1_1 = registry.resolve_identity(schema_id, "1.1.0")
    assert (
        v1_1.raw_bytes
        == (SCHEMAS / "wp6-6" / "gate6-binding-repair" / "advance-store-binding-command.v1-1.schema.json").read_bytes()
    )
    assert registry.command_binding("AdvanceStoreBinding") == SchemaBinding(
        schema_id,
        "1.2.0",
        command_type="AdvanceStoreBinding",
    )


def test_schema_registry_reports_a_missing_root_through_its_public_error_contract(tmp_path: Path) -> None:
    with pytest.raises(SchemaError, match="schema root"):
        SchemaRegistry(tmp_path / "missing")


def test_runtime_schema_registry_cache_is_scoped_to_the_verified_catalogue_generation() -> None:
    first = runtime_schema_registry(SCHEMAS, generation="head-a:catalogue")
    same = runtime_schema_registry(SCHEMAS, generation="head-a:catalogue")
    successor = runtime_schema_registry(SCHEMAS, generation="head-b:catalogue")

    assert same is first
    assert successor is not first
