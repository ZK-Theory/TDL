from __future__ import annotations

import hashlib
import json
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from tests.research_system.contracts.wp6_2_live_issue_fixtures import (
    ALT_DIGEST,
    DIGEST,
    clone,
    valid_claim,
    valid_credential_receipt,
    valid_live_issue_binding,
)
from tests.research_system.contracts.wp6_2_live_issue_expectations import (
    ADDENDUM_PATH,
    CATALOGUE_PATH,
    CATALOGUE_SCHEMA_PATH,
    EXPECTED_DIRECT_DEPENDENCY_EDGES,
    EXPECTED_SCHEMA_IDENTITIES,
    EXPECTED_TRANSITIONS,
    IDENTITY_MANIFEST_PATH,
    IDENTITY_MANIFEST_SCHEMA_PATH,
    INTENT_EXCLUDED_FIELDS,
)
from tests.research_system.contracts.wp6_2_live_issue_validation import (
    LiveIssueContractError,
    compute_claim_intent,
    validate_claim_arbitration,
    validate_credential_receipt,
    validate_dependency_graph,
    validate_evidence_orphan,
    validate_exact_replay,
    validate_native_binding,
    validate_no_secret_material,
    validate_outcome,
    validate_preflight_failure,
    validate_reconciliation,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_required_live_issue_contract_artifacts_exist() -> None:
    required = {
        ADDENDUM_PATH,
        CATALOGUE_PATH,
        CATALOGUE_SCHEMA_PATH,
        IDENTITY_MANIFEST_PATH,
        IDENTITY_MANIFEST_SCHEMA_PATH,
        *(identity[0] for identity in EXPECTED_SCHEMA_IDENTITIES.values()),
    }
    missing = sorted(path for path in required if not (REPO_ROOT / path).is_file())
    assert not missing, f"missing live-issue contract artifacts: {missing}"


def _load_json(path: str) -> dict[str, object]:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def _load_yaml(path: str) -> dict[str, object]:
    return yaml.safe_load((REPO_ROOT / path).read_text(encoding="utf-8"))


def _schema(name: str) -> dict[str, object]:
    return _load_json(EXPECTED_SCHEMA_IDENTITIES[name][0])


def test_catalogue_and_identity_manifest_are_strict_draft_2020_12() -> None:
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


@pytest.mark.parametrize(
    ("name", "identity"),
    EXPECTED_SCHEMA_IDENTITIES.items(),
    ids=EXPECTED_SCHEMA_IDENTITIES.keys(),
)
def test_each_live_issue_schema_has_exact_identity_and_closed_shape(
    name: str,
    identity: tuple[str, str, str],
) -> None:
    del name
    path, schema_id, version = identity
    schema = _load_json(path)
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == schema_id
    assert schema["properties"]["schema_version"]["const"] == version
    assert schema["additionalProperties"] is False


def test_catalogue_has_exact_independent_transition_membership() -> None:
    catalogue = _load_yaml(CATALOGUE_PATH)
    actual = {row["key"]: row for row in catalogue["transitions"]}
    assert set(actual) == set(EXPECTED_TRANSITIONS)
    for key, expected in EXPECTED_TRANSITIONS.items():
        for field, value in expected.items():
            assert actual[key][field] == value
    assert catalogue["provider_call_authorized"] is False
    assert catalogue["automatic_retry"] is False
    assert catalogue["accepted_t2_predecessor_immutable"] is True


def test_identity_manifest_has_exact_independent_schema_membership() -> None:
    manifest = _load_yaml(IDENTITY_MANIFEST_PATH)
    actual = {
        row["role"] + ":" + row["schema_id"]: (
            row["path"],
            row["schema_id"],
            row["schema_version"],
        )
        for row in manifest["artifacts"]
    }
    assert set(actual.values()) == set(EXPECTED_SCHEMA_IDENTITIES.values())
    assert manifest["candidate_identity_binding"] == ("external_exact_state_review_and_owner_acceptance_only")


def test_live_issue_binding_is_strict_precredential() -> None:
    schema = _schema("live_issue_binding")
    valid = valid_live_issue_binding()
    validator = Draft202012Validator(schema)
    assert not list(validator.iter_errors(valid))
    for forbidden in schema["x-prohibited-fields"]:
        mutated = clone(valid)
        mutated[forbidden] = DIGEST
        assert any(error.validator == "additionalProperties" for error in validator.iter_errors(mutated))


def test_credential_receipt_schema_and_semantics_reject_fabrication_and_drift() -> None:
    schema = _schema("credential_use_receipt")
    valid = valid_credential_receipt()
    validator = Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    assert not list(validator.iter_errors(valid))
    validate_credential_receipt(valid, expected=valid)
    mutations = {
        "owner": "coordinator",
        "resolver_trust_root": {"id": "wrong", "revision": 1, "hash": DIGEST},
        "requested_scope": "wrong.scope",
        "provider_family": "codex",
        "isolated_auth_context_id": "wrong-context",
        "claim_command_id": "cmd_018f47a2-9b3c-7def-8abc-0123456789ac",
        "claim_intent_hash": ALT_DIGEST,
        "expiry_state": "expired",
        "revocation_state": "revoked",
        "contains_credential_bytes": True,
    }
    for field, replacement in mutations.items():
        mutated = clone(valid)
        mutated[field] = replacement
        with pytest.raises(LiveIssueContractError):
            validate_credential_receipt(mutated, expected=valid)


def test_intent_preimage_is_literal_complete_and_excludes_exact_six_fields() -> None:
    schema = _schema("claim_command")
    claim = valid_claim()
    Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    ).validate(claim)
    fields = schema["x-intent-preimage-fields"]
    assert set(schema["x-intent-excluded-fields"]) == INTENT_EXCLUDED_FIELDS
    assert not (set(fields) & INTENT_EXCLUDED_FIELDS)
    required_intent_fields = set(schema["required"]) - INTENT_EXCLUDED_FIELDS - {"claim_intent_hash"}
    assert set(fields) == required_intent_fields
    preimage, digest = compute_claim_intent(claim, preimage_fields=fields)
    assert set(preimage) == set(fields)
    assert len(digest) == 64


@pytest.mark.parametrize(
    "field",
    [
        "command_type",
        "write_set",
        "expected_ledger_tail_hash",
        "accepted_t2_receipt",
        "live_issue_binding",
        "resolver_trust_root",
        "resolver_requirement",
        "provider_family",
        "preflight_hashes",
        "expected_object_versions",
    ],
)
def test_changing_any_representative_intent_field_invalidates_resolver_proof(
    field: str,
) -> None:
    schema = _schema("claim_command")
    fields = schema["x-intent-preimage-fields"]
    claim = valid_claim()
    _, original = compute_claim_intent(claim, preimage_fields=fields)
    mutated = deepcopy(claim)
    mutated[field] = "changed" if isinstance(mutated[field], str) else {"changed": 1}
    _, changed = compute_claim_intent(mutated, preimage_fields=fields)
    assert changed != original


def test_credential_receipt_triple_does_not_change_intent_but_changes_full_payload() -> None:
    schema = _schema("claim_command")
    fields = schema["x-intent-preimage-fields"]
    claim = valid_claim()
    _, original_intent = compute_claim_intent(claim, preimage_fields=fields)
    original_full = hashlib.sha256(json.dumps(claim, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    mutated = clone(claim)
    mutated["credential_use_receipt_hash"] = ALT_DIGEST
    _, changed_intent = compute_claim_intent(mutated, preimage_fields=fields)
    changed_full = hashlib.sha256(json.dumps(mutated, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert changed_intent == original_intent
    assert changed_full != original_full


def test_dependency_graph_has_exact_five_direct_edges_and_is_acyclic() -> None:
    catalogue = _load_yaml(CATALOGUE_PATH)
    edges = catalogue["dependency_graph"]["direct_edges"]
    validate_dependency_graph(edges, expected_edges=EXPECTED_DIRECT_DEPENDENCY_EDGES)
    for extra in (
        ["CredentialUseReceipt", "claim_intent_hash"],
        ["completed_claim_payload_hash", "LiveIssueBinding"],
    ):
        with pytest.raises(LiveIssueContractError):
            validate_dependency_graph(
                [*edges, extra],
                expected_edges=EXPECTED_DIRECT_DEPENDENCY_EDGES,
            )


def test_concurrent_claim_has_exactly_one_winner_and_no_retry() -> None:
    validate_claim_arbitration(
        {
            "attempt_count": 2,
            "winner_count": 1,
            "loser_count": 1,
            "claim_event_count": 1,
            "invocation_count": 1,
            "automatic_retry_count": 0,
        }
    )
    for field in ("winner_count", "claim_event_count", "invocation_count", "automatic_retry_count"):
        invalid = {
            "attempt_count": 2,
            "winner_count": 1,
            "loser_count": 1,
            "claim_event_count": 1,
            "invocation_count": 1,
            "automatic_retry_count": 0,
        }
        invalid[field] += 1
        with pytest.raises(LiveIssueContractError):
            validate_claim_arbitration(invalid)


@pytest.mark.parametrize(
    "reason",
    [
        "accepted_t2_issue_missing",
        "accepted_t2_issue_duplicate",
        "accepted_t2_batch_mismatch",
        "canonical_object_mismatch",
        "policy_derivation_mismatch",
        "native_selector_mismatch",
        "argv_profile_mismatch",
        "preflight_hash_mismatch",
        "credential_receipt_untrusted",
        "credential_receipt_stale",
        "credential_scope_mismatch",
        "credential_context_mismatch",
        "expiry_or_revocation_failed",
        "secret_scan_failed",
    ],
)
def test_every_precall_rejection_is_byte_identical_and_has_zero_effects(reason: str) -> None:
    validate_preflight_failure(
        {
            "status": "rejected",
            "reason": reason,
            "event_count": 0,
            "invocation_count": 0,
            "ledger_byte_delta": 0,
            "canonical_object_byte_delta": 0,
            "credential_receipt_project_publication_count": 0,
        }
    )


@pytest.mark.parametrize("lifecycle", ["not_invoked", "observed", "uncertain"])
def test_crash_and_outcome_lifecycle_is_conservative(lifecycle: str) -> None:
    observation = {
        "lifecycle": lifecycle,
        "automatic_retry_count": 0,
        "research_eligibility": "eligible" if lifecycle == "observed" else "ineligible",
        "actual_input_tokens": 10 if lifecycle == "observed" else None,
        "actual_output_tokens": 5 if lifecycle == "observed" else None,
        "cost_disposition": "exact" if lifecycle == "observed" else "reserved",
        "refund_count": 0,
    }
    validate_outcome(observation)


def test_inert_orphan_and_exact_replay_have_no_second_effects() -> None:
    validate_evidence_orphan(
        {
            "object_publish_count": 1,
            "ledger_commit_count": 0,
            "claim_authorization_count": 0,
            "invocation_count": 0,
            "receipt_count": 0,
            "refund_count": 0,
            "research_use_count": 0,
        }
    )
    validate_exact_replay(
        {
            "status": "duplicate",
            "evidence_id": "piev-1",
            "original_evidence_id": "piev-1",
            "receipt_hash": DIGEST,
            "original_receipt_hash": DIGEST,
            "new_invocation_count": 0,
            "new_evidence_object_count": 0,
            "new_receipt_count": 0,
            "new_reconciliation_count": 0,
            "new_refund_count": 0,
        }
    )


def test_metered_zero_cost_and_uncertain_reconciliation() -> None:
    validate_reconciliation(
        {
            "rate_mode": "metered",
            "reserved_cost_microunits": 5,
            "consumed_cost_microunits": 3,
            "refund_cost_microunits": 2,
            "disposition": "exact",
            "input_tokens": 1_000_000,
            "output_tokens": 1_000_000,
            "input_rate": 1,
            "output_rate": 2,
        }
    )
    validate_reconciliation(
        {
            "rate_mode": "zero_cost_authorized",
            "reserved_cost_microunits": 0,
            "consumed_cost_microunits": 0,
            "refund_cost_microunits": 0,
            "disposition": "exact",
            "zero_cost_authority": {"id": "authority-1", "revision": 1, "hash": DIGEST},
        }
    )
    validate_reconciliation(
        {
            "rate_mode": "uncertain",
            "reserved_cost_microunits": 5,
            "consumed_cost_microunits": None,
            "refund_cost_microunits": None,
            "disposition": "reserved",
        }
    )


@pytest.mark.parametrize(
    "field",
    [
        "provider_family",
        "native_model_selector",
        "native_model_version",
        "profile_id",
        "credential_context_id",
        "argv_profile_hash",
        "payload_hash",
        "context_hash",
        "policy_bundle_hash",
        "applicability_manifest_hash",
        "compiler_revision",
        "generator_revision",
        "ordered_control_ids",
        "policy_projection_hash",
        "route_hash",
        "reasoning_setting",
        "response_protocol",
    ],
)
def test_actual_native_and_derivation_mismatch_fails_closed(field: str) -> None:
    expected = {
        "provider_family": "claude",
        "native_model_selector": "native-model",
        "native_model_version": "v1",
        "profile_id": "profile-1",
        "credential_context_id": "auth-1",
        "argv_profile_hash": DIGEST,
        "payload_hash": DIGEST,
        "context_hash": DIGEST,
        "policy_bundle_hash": DIGEST,
        "applicability_manifest_hash": DIGEST,
        "compiler_revision": "compiler-v1",
        "generator_revision": "generator-v1",
        "ordered_control_ids": ["control-1", "control-2"],
        "policy_projection_hash": DIGEST,
        "route_hash": DIGEST,
        "reasoning_setting": "standard",
        "response_protocol": "provider_native_json",
    }
    validate_native_binding(expected, expected)
    actual = dict(expected)
    actual[field] = ALT_DIGEST if field.endswith("hash") else "wrong"
    with pytest.raises(LiveIssueContractError):
        validate_native_binding(actual, expected)


def test_secret_material_and_sentinels_are_rejected_across_evidence() -> None:
    clean = {
        "argv": ["--model", "native-model"],
        "environment": {"PATH": "redacted"},
        "payload_hash": DIGEST,
        "events": [],
        "objects": [],
        "receipts": [],
        "outputs": [],
    }
    validate_no_secret_material(clean, sentinels=["SENTINEL_SECRET_VALUE"])
    for mutation in (
        {"raw_credential": "value"},
        {"argv": ["SENTINEL_SECRET_VALUE"]},
        {"hidden_reasoning": "forbidden"},
    ):
        with pytest.raises(LiveIssueContractError):
            validate_no_secret_material({**clean, **mutation}, sentinels=["SENTINEL_SECRET_VALUE"])


def _git_blob_bytes(revision: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    ).stdout


def test_accepted_t2_wp6_1_t1a_bytes_remain_exact() -> None:
    protected = _load_yaml(".research-system/contracts/wp6-2-t2-protected-membership.yaml")
    assert len(protected["members"]) == protected["protected_path_count"] == 220
    for member in protected["members"]:
        path = member["repository_path"]
        blob = subprocess.run(
            ["git", "rev-parse", f"HEAD:{path}"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        raw = _git_blob_bytes("HEAD", path)
        assert blob == member["git_blob_id"], path
        assert hashlib.sha256(raw).hexdigest() == member["raw_git_blob_sha256"], path

    identities = _load_yaml(".research-system/contracts/wp6-2-t2-schema-identities.yaml")
    for artifact in identities["artifacts"]:
        path = artifact["repository_path"]
        raw = _git_blob_bytes("HEAD", path)
        blob = subprocess.run(
            ["git", "rev-parse", f"HEAD:{path}"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert blob == artifact["git_blob_id"], path
        assert hashlib.sha256(raw).hexdigest() == artifact["raw_utf8_lf_sha256"], path
