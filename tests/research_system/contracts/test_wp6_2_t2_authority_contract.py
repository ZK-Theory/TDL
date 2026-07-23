from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from tests.research_system.contracts.wp6_2_t2_authority_validation import (
    validate_event_observation,
    validate_t2_authority_contract,
)
from tests.research_system.contracts.wp6_2_t2_expectations import (
    ADDENDUM_PATH,
    CATALOGUE_PATH,
    CATALOGUE_SCHEMA_PATH,
    CROSSWALK_AUTHORITIES,
    CROSSWALK_PATH,
    CROSSWALK_SCHEMA_PATH,
    EVENT_HASH_FIELDS,
    EXPECTED_ROWS,
    IDENTITY_MANIFEST_PATH,
    IDENTITY_MANIFEST_SCHEMA_PATH,
    PROTECTED_MEMBERSHIP_PATH,
    PROTECTED_MEMBERSHIP_SCHEMA_PATH,
    PROVIDER_COMMAND_W7_FIELDS,
    PROVIDER_RECEIPT_W7_FIELDS,
    R1_FINDING_IDS,
    SCHEMA_IDENTITIES,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_json(relative_path: str) -> dict[str, object]:
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def _load_yaml(relative_path: str) -> dict[str, object]:
    return yaml.safe_load((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def test_required_t2_contract_artifacts_exist() -> None:
    required_paths = {
        ADDENDUM_PATH,
        CATALOGUE_PATH,
        CATALOGUE_SCHEMA_PATH,
        IDENTITY_MANIFEST_PATH,
        IDENTITY_MANIFEST_SCHEMA_PATH,
        CROSSWALK_PATH,
        CROSSWALK_SCHEMA_PATH,
        PROTECTED_MEMBERSHIP_PATH,
        PROTECTED_MEMBERSHIP_SCHEMA_PATH,
        *(identity["path"] for identity in SCHEMA_IDENTITIES.values()),
    }
    missing = sorted(path for path in required_paths if not (REPO_ROOT / path).is_file())
    assert not missing, f"missing T2 contract artifacts: {missing}"


def test_catalogue_has_exact_independent_three_row_set() -> None:
    catalogue = _load_yaml(CATALOGUE_PATH)
    assert catalogue["writer"] == "research_system.command.service.CommandService"
    assert catalogue["transition_family_closed"] is True
    assert len(catalogue["rows"]) == 3
    for actual, expected in zip(catalogue["rows"], EXPECTED_ROWS, strict=True):
        for key, value in expected.items():
            assert actual[key] == value


@pytest.mark.parametrize("schema_identity", SCHEMA_IDENTITIES.values(), ids=SCHEMA_IDENTITIES.keys())
def test_each_t2_schema_is_strict_draft_2020_12(schema_identity: dict[str, str]) -> None:
    schema = _load_json(schema_identity["path"])
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == schema_identity["schema_id"]
    assert schema["properties"]["schema_version"]["const"] == schema_identity["schema_version"]
    assert schema["additionalProperties"] is False


def test_catalogue_and_manifest_pass_strict_schemas_with_format_checking() -> None:
    for document_path, schema_path in (
        (CATALOGUE_PATH, CATALOGUE_SCHEMA_PATH),
        (IDENTITY_MANIFEST_PATH, IDENTITY_MANIFEST_SCHEMA_PATH),
        (CROSSWALK_PATH, CROSSWALK_SCHEMA_PATH),
        (PROTECTED_MEMBERSHIP_PATH, PROTECTED_MEMBERSHIP_SCHEMA_PATH),
    ):
        document = _load_yaml(document_path)
        schema = _load_json(schema_path)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(
            schema,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        ).validate(document)


def _valid_secret_reference() -> dict[str, object]:
    digest = "a" * 64
    suffix = "018f47a2-9b3c-7def-8abc-0123456789ab"
    return {
        "schema_id": "ars://wp6-2/t2/secret-reference",
        "schema_version": "1.0.0",
        "secret_reference_id": f"srf_{suffix}",
        "revision": 1,
        "content_hash": digest,
        "provider": "claude",
        "credential_class": "api_token",
        "resolver_id": {
            "registry_type": "secret_resolver",
            "canonical_uri": "ars://registry/secret-resolver/local-opaque-resolver",
            "revision": 1,
            "content_hash": digest,
        },
        "resolver_version": "1.0.0",
        "allowed_scope": {
            "task_id": f"tsk_{suffix}",
            "dispatch_id": f"dsp_{suffix}",
            "attempt_id": f"att_{suffix}",
            "route_id": f"rte_{suffix}",
            "profile_id": f"prf_{suffix}",
            "adapter_revision": "adapter-1",
            "provider_command_id": f"pcmd_{suffix}",
            "provider_command_revision": 1,
            "provider_command_hash": digest,
        },
        "expires_at": "2026-07-23T00:00:00Z",
        "revocation_binding": {
            "authority_grant_id": f"agr_{suffix}",
            "resource_grant_id": f"rgr_{suffix}",
            "new_issue_rule": "require_both_current_projections_active",
            "reconciliation_rule": "reconcile_every_previously_accepted_reservation",
        },
        "redaction_proof": {
            "policy_id": "wp6-2-t2-opaque-secret-reference-policy",
            "policy_version": "1.0.0",
            "evidence_sha256": digest,
            "status": "opaque_metadata_only_no_raw_credential_or_resolution",
        },
    }


def test_format_checker_rejects_invalid_secret_reference_expiry() -> None:
    schema = _load_json(SCHEMA_IDENTITIES["secret_reference"]["path"])
    validator = Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    value = _valid_secret_reference()
    assert not list(validator.iter_errors(value))
    value["expires_at"] = "not-a-date-time"
    assert any(error.validator == "format" for error in validator.iter_errors(value))


def test_secret_reference_schema_has_no_secret_byte_escape_field() -> None:
    schema = _load_json(SCHEMA_IDENTITIES["secret_reference"]["path"])
    value = _valid_secret_reference()
    value["secret_bytes"] = "forbidden"
    errors = list(Draft202012Validator(schema).iter_errors(value))
    assert any(error.validator == "additionalProperties" for error in errors)


def test_pos_issue_cost_grant() -> None:
    validate_event_observation("IssueCostGrant", ["CostGrantIssued"])


def test_pos_authorize_provider_issue_atomic() -> None:
    validate_event_observation(
        "AuthorizeProviderIssue",
        ["CostGrantReserved", "ProviderCommandIssued"],
    )


def test_pos_record_provider_receipt_atomic() -> None:
    validate_event_observation(
        "RecordProviderReceipt",
        ["ProviderReceiptRecorded", "CostGrantReconciled"],
    )


def test_complete_t2_semantic_and_content_address_binding() -> None:
    validate_t2_authority_contract(REPO_ROOT)


def test_r3_receipt_v2_enforces_complete_ordered_proof() -> None:
    schema = _load_json(SCHEMA_IDENTITIES["receipt_v2"]["path"])
    required = set(schema["required"])
    assert {
        "command_id",
        "idempotency_key_hash",
        "payload_hash",
        "event_batch_id",
        "events",
        "outcome",
    } <= required
    assert schema["x-major-version-dispatch"] == "exact_major_version_required"


def test_all_event_envelopes_carry_complete_logical_idempotency_tuple() -> None:
    for event_type in (
        "CostGrantIssued",
        "CostGrantReserved",
        "ProviderCommandIssued",
        "ProviderReceiptRecorded",
        "CostGrantReconciled",
    ):
        schema = _load_json(SCHEMA_IDENTITIES[event_type]["path"])
        assert EVENT_HASH_FIELDS <= set(schema["required"]), event_type


def test_secret_reference_remains_strict_opaque_metadata() -> None:
    secret_schema = _load_json(SCHEMA_IDENTITIES["secret_reference"]["path"])
    assert secret_schema["properties"]["resolver_id"]["type"] == "object"
    serialized = json.dumps(secret_schema, sort_keys=True)
    assert "credential_value" not in serialized
    assert "secret_bytes" not in serialized
    redaction_properties = secret_schema["properties"]["redaction_proof"]["properties"]
    assert set(redaction_properties) == {"policy_id", "policy_version", "evidence_sha256", "status"}


def test_r1_red_c4_relational_invariants_are_normative() -> None:
    expected = {
        "target_write_set_payload_identity",
        "issue_expected_version_zero",
        "deterministic_reservation_identity",
        "authority_subject_identity_revision_hash",
        "receipt_grant_and_reservation_identity_revision_hash",
        "ordered_events_and_resulting_versions",
    }
    for command_type in ("IssueCostGrant", "AuthorizeProviderIssue", "RecordProviderReceipt"):
        schema = _load_json(SCHEMA_IDENTITIES[command_type]["path"])
        assert expected <= set(schema["x-semantic-validation"]), command_type


def test_r1_red_m1_cost_modes_and_integer_formula_are_bound() -> None:
    schema = _load_json(SCHEMA_IDENTITIES["cost_grant"]["path"])
    rate_evidence = schema["properties"]["rate_evidence"]
    assert rate_evidence["oneOf"][0]["properties"]["mode"]["const"] == "metered"
    assert rate_evidence["oneOf"][1]["properties"]["mode"]["const"] == "zero_cost_authorized"
    authorize_schema = _load_json(SCHEMA_IDENTITIES["AuthorizeProviderIssue"]["path"])
    assert authorize_schema["properties"]["payload"]["properties"]["reserved_cost_microunits"] == {
        "type": "integer",
        "minimum": 0,
    }
    assert schema["x-cost-formula"] == (
        "ceil_div(actual_input_tokens*input_microunits_per_million_tokens,1000000)"
        "+ceil_div(actual_output_tokens*output_microunits_per_million_tokens,1000000)"
    )


def test_provider_successors_cover_exact_t2_authority_cost_subset() -> None:
    command = _load_json(SCHEMA_IDENTITIES["provider_command_v2"]["path"])
    receipt = _load_json(SCHEMA_IDENTITIES["provider_receipt_v2"]["path"])
    for schema, expected in (
        (command, PROVIDER_COMMAND_W7_FIELDS),
        (receipt, PROVIDER_RECEIPT_W7_FIELDS),
    ):
        assert schema["x-t2-validation-scope"] == "t2_authority_cost_subset"
        assert set(schema["required"]) == expected
        assert schema["x-deferred-qualification"] == "remaining_W7_sections_9_and_10_require_T3_T4_runtime_evidence"


def test_receipt_v2_permitted_stream_prefixes() -> None:
    schema = _load_json(SCHEMA_IDENTITIES["secret_reference"]["path"])
    validator = Draft202012Validator(schema)
    valid = _valid_secret_reference()
    valid["secret_reference_id"] = "srf_018f47a2-9b3c-7def-8abc-0123456789ab"
    assert not list(validator.iter_errors(valid))
    valid["secret_reference_id"] = "srf_abc"
    assert list(validator.iter_errors(valid))
    expected_prefixes = {
        "cost_grant": ("cost_grant_id", "cgr_"),
        "provider_command_v2": ("provider_command_id", "pcmd_"),
        "provider_receipt_v2": ("provider_receipt_id", "prcp_"),
    }
    for schema_name, (field, prefix) in expected_prefixes.items():
        candidate = _load_json(SCHEMA_IDENTITIES[schema_name]["path"])
        pattern = candidate["properties"][field]["pattern"]
        assert pattern.startswith(f"^{prefix}") and "-7[0-9a-f]{3}-[89ab]" in pattern
    receipt = _load_json(SCHEMA_IDENTITIES["receipt_v2"]["path"])
    stream_id = receipt["properties"]["events"]["items"]["properties"]["stream_id"]
    assert {item["pattern"][:5] for item in stream_id["oneOf"]} == {"^cgr_", "^pcmd"}


def test_r1_red_machine_crosswalk_has_independent_complete_oracle() -> None:
    crosswalk = _load_yaml(CROSSWALK_PATH)
    schema = _load_json(CROSSWALK_SCHEMA_PATH)
    Draft202012Validator(schema).validate(crosswalk)
    assert set(crosswalk["authorities"]) == CROSSWALK_AUTHORITIES
    assert {row["finding_id"] for row in crosswalk["rows"]} == R1_FINDING_IDS
