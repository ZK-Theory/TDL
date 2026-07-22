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
    EXPECTED_ROWS,
    IDENTITY_MANIFEST_PATH,
    IDENTITY_MANIFEST_SCHEMA_PATH,
    PRE_ISSUE_SENTINEL_SEAMS,
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
    return {
        "schema_id": "ars://wp6-2/t2/secret-reference",
        "schema_version": "1.0.0",
        "secret_reference_id": "sref_abc",
        "revision": 1,
        "content_hash": digest,
        "provider": "claude",
        "credential_class": "api_token",
        "resolver_id": "local-opaque-resolver",
        "resolver_version": "1.0.0",
        "allowed_scope": {
            "task_id": "tsk_abc",
            "dispatch_id": "dsp_abc",
            "attempt_id": "att_abc",
            "route_id": "route-1",
            "profile_id": "profile-1",
            "adapter_revision": "adapter-1",
            "provider_command_id": "pcmd_abc",
            "provider_command_revision": 1,
            "provider_command_hash": digest,
        },
        "expires_at": "2026-07-23T00:00:00Z",
        "revocation_binding": {
            "authority_grant_id": "agr_abc",
            "resource_grant_id": "rgr_abc",
            "new_issue_rule": "require_both_current_projections_active",
            "reconciliation_rule": "reconcile_every_previously_accepted_reservation",
        },
        "redaction_proof": {
            "policy_id": "wp6-2-t2-secret-sentinel-policy",
            "policy_version": "1.0.0",
            "evidence_sha256": digest,
            "status": "no_secret_material_observed",
            "checked_seams": PRE_ISSUE_SENTINEL_SEAMS,
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
