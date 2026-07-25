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
    UUID7,
    clone,
    resolver_store_record,
    triple,
    trusted_resolver_authority,
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
    TRUSTED_RESOLVER_PATH,
    TRUSTED_RESOLVER_SCHEMA_PATH,
)
from tests.research_system.contracts.wp6_2_live_issue_validation import (
    LiveIssueContractError,
    compute_claim_intent,
    compute_final_claim_payload,
    load_trusted_resolver_authority,
    validate_claim_command,
    validate_claim_arbitration,
    validate_credential_receipt,
    validate_dependency_graph,
    validate_evidence_orphan,
    validate_exact_replay,
    validate_evidence_store,
    validate_evidence_uniqueness,
    validate_event_batch,
    validate_live_issue_binding,
    validate_native_binding,
    validate_no_secret_material,
    validate_outcome,
    validate_outcome_command,
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
        TRUSTED_RESOLVER_PATH,
        TRUSTED_RESOLVER_SCHEMA_PATH,
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
        (TRUSTED_RESOLVER_PATH, TRUSTED_RESOLVER_SCHEMA_PATH),
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
    for row in manifest["artifacts"]:
        path = REPO_ROOT / row["path"]
        raw = path.read_bytes()
        blob = subprocess.run(
            ["git", "hash-object", f"--path={row['path']}", row["path"]],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert blob == row["git_blob_id"], row["path"]
        assert hashlib.sha256(raw).hexdigest() == row["raw_utf8_lf_sha256"], row["path"]
    for row in manifest["contract_artifacts"]:
        path = REPO_ROOT / row["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["raw_utf8_lf_sha256"]
        blob = subprocess.run(
            ["git", "hash-object", f"--path={row['path']}", row["path"]],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert blob == row["git_blob_id"]


def test_every_catalogue_reference_binds_actual_schema_identity_and_bytes() -> None:
    catalogue = _load_yaml(CATALOGUE_PATH)
    bindings = {(row["reference_kind"], row["reference"]): row for row in catalogue["reference_bindings"]}
    expected: set[tuple[str, str]] = set()
    for transition in catalogue["transitions"]:
        expected.add(("command", transition["command_type"]))
        expected.update(("event", name) for name in transition["ordered_events"])
        expected.update(("reducer", name) for name in transition["reducers"])
        expected.update(("projection", name) for name in transition["projections"])
    assert set(bindings) == expected
    for row in bindings.values():
        path = REPO_ROOT / row["path"]
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["$id"] == row["schema_id"]
        assert schema["properties"]["schema_version"]["const"] == row["schema_version"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["raw_utf8_lf_sha256"]
        blob = subprocess.run(
            ["git", "hash-object", f"--path={row['path']}", row["path"]],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert blob == row["git_blob_id"]


def test_live_issue_binding_is_strict_precredential() -> None:
    schema = _schema("live_issue_binding")
    valid = valid_live_issue_binding()
    validator = Draft202012Validator(schema)
    assert not list(validator.iter_errors(valid))
    for forbidden in schema["x-prohibited-fields"]:
        mutated = clone(valid)
        mutated[forbidden] = DIGEST
        assert any(error.validator == "additionalProperties" for error in validator.iter_errors(mutated))


def test_reviewed_six_adversarial_escapes_are_rejected() -> None:
    claim_schema = _schema("claim_command")
    claim = valid_claim()

    distinct_ids = clone(claim)
    distinct_ids["target_stream_id"] = f"pinv_{UUID7[:-1]}c"
    with pytest.raises(LiveIssueContractError):
        validate_claim_command(distinct_ids)

    malformed_uuid = clone(claim)
    malformed_uuid["command_id"] = "cmd_not-a-uuid"
    assert list(Draft202012Validator(claim_schema).iter_errors(malformed_uuid))

    outcome_schema = _schema("record_outcome_command")
    duplicated_roles = {
        "schema_id": "ars://wp6-2/live-issue/command/RecordLiveProviderInvocationOutcome",
        "schema_version": "1.0.0",
        "command_type": "RecordLiveProviderInvocationOutcome",
        "command_id": f"cmd_{UUID7}",
        "actor_id": f"act_{UUID7}",
        "authority_scope": "wp6.2.live-issue.outcome.record",
        "idempotency_key": "outcome-1",
        "payload_hash": DIGEST,
        "invocation_id": f"pinv_{UUID7}",
        "expected_invocation_stream_version": 1,
        "expected_cost_grant_stream_version": 2,
        "write_set": [
            {"stream_role": "provider_invocation", "stream_id": f"pinv_{UUID7}", "expected_version": 1},
            {"stream_role": "provider_invocation", "stream_id": f"pinv_{UUID7}", "expected_version": 1},
        ],
        "claim": triple("clm"),
        "invocation_evidence": triple("piev"),
        "live_provider_receipt": triple("prcp"),
        "cost_grant": triple("cgr"),
        "reservation": triple("crs"),
        "outcome": "terminal",
        "reconciliation": {
            "rate_mode": "metered",
            "reserved_cost_microunits": 10,
            "consumed_cost_microunits": 10,
            "refund_cost_microunits": 0,
            "disposition": "exact",
            "actuals_proven": True,
        },
        "submitted_at": "2026-07-25T20:00:00Z",
    }
    assert list(Draft202012Validator(outcome_schema).iter_errors(duplicated_roles))

    event_schema = _schema("claimed_event")
    missing_w2_envelope = {
        "schema_id": "ars://wp6-2/live-issue/event/LiveProviderInvocationClaimed",
        "schema_version": "1.0.0",
        "event_type": "LiveProviderInvocationClaimed",
        "event_id": f"evt_{UUID7}",
        "stream_id": f"pinv_{UUID7}",
        "prior_stream_version": 0,
        "resulting_stream_version": 1,
        "transaction_position": 0,
        "command_id": f"cmd_{UUID7}",
        "payload": {
            "invocation_id": f"pinv_{UUID7}",
            "claim_intent_hash": DIGEST,
            "live_issue_binding": triple("lib"),
            "credential_use_receipt": triple("cur"),
            "accepted_t2_receipt": triple("rcp"),
        },
    }
    assert list(Draft202012Validator(event_schema).iter_errors(missing_w2_envelope))

    evidence_schema = _schema("provider_invocation_evidence")
    proofless_evidence = {
        "schema_id": "ars://wp6-2/live-issue/ProviderInvocationEvidence",
        "schema_version": "1.0.0",
        "provider_invocation_evidence_id": f"piev_{UUID7}",
        "revision": 1,
        "content_hash": DIGEST,
        "claim": triple("clm"),
        "live_issue_binding": triple("lib"),
        "actual_argv_profile_hash": DIGEST,
        "cwd": "C:/worktree",
        "root": "C:/worktree",
        "redacted_environment_hash": DIGEST,
        "redacted_config_hash": DIGEST,
        "credential_use_receipt": triple("cur"),
        "timestamps": {"attempted_at": "2026-07-25T20:00:00Z", "completed_at": None},
        "native_identity": {"request_id": None, "session_id": None, "thread_id": None, "response_id": None},
        "actual_selection": {
            "provider_family": "claude",
            "provider_proven": True,
            "model": None,
            "model_proven": True,
            "version": None,
            "version_proven": True,
            "profile": None,
            "profile_proven": True,
        },
        "delivery": {
            "payload_hash": DIGEST,
            "context_hash": DIGEST,
            "disposition": "proven",
            "proof_fields": {},
        },
        "terminal": {
            "lifecycle": "observed",
            "native_class": None,
            "exit_code": 0,
            "cancelled": False,
            "timed_out": False,
            "error_class": None,
        },
        "actions": {"attempted": [], "allowed": [], "denied": []},
        "outputs": [],
        "accounting": {
            "method": "provider_native",
            "input_tokens": 1,
            "output_tokens": 1,
            "actuals_proven": True,
            "omissions": [],
            "rate_mode": "metered",
            "cost_microunits": 1,
        },
        "secret_scans": [{"seam": "argv", "status": "clear", "evidence_hash": DIGEST}],
        "source_declaration": "actual_process_and_provider_observations_not_command_assertions",
    }
    assert list(Draft202012Validator(evidence_schema).iter_errors(proofless_evidence))

    receipt_schema = _schema("live_provider_receipt_v3")
    contradictory_receipt = {
        "schema_id": "ars://adapters/provider-receipt/v3",
        "schema_version": "3.0.0",
        "provider_receipt_id": f"prcp_{UUID7}",
        "revision": 1,
        "content_hash": DIGEST,
        "claim": triple("clm"),
        "invocation_evidence": triple("piev"),
        "live_issue_binding": triple("lib"),
        "accepted_t2_receipt": triple("rcp"),
        "provider_command": triple("pcmd"),
        "reservation": triple("crs"),
        "actual_selection": {
            "provider_family": "claude",
            "model": None,
            "version": None,
            "profile": None,
            "credential_context_id": None,
            "all_proven": False,
        },
        "delivery": "unproven",
        "outcome": "uncertain",
        "accounting": {
            "rate_mode": "uncertain",
            "actuals_proven": False,
            "input_tokens": None,
            "output_tokens": None,
            "consumed_cost_microunits": None,
            "disposition": "reserved",
        },
        "research_eligibility": "eligible",
        "complete": True,
    }
    assert list(Draft202012Validator(receipt_schema).iter_errors(contradictory_receipt))


def test_credential_receipt_schema_and_semantics_reject_fabrication_and_drift() -> None:
    schema = _schema("credential_use_receipt")
    valid = valid_credential_receipt()
    validator = Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    assert not list(validator.iter_errors(valid))
    trusted = load_trusted_resolver_authority(REPO_ROOT, "resolver.local")
    assert trusted == trusted_resolver_authority()
    store_record = resolver_store_record()
    validate_credential_receipt(
        valid,
        trusted_authority=trusted,
        resolver_store_record=store_record,
    )
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
            validate_credential_receipt(
                mutated,
                trusted_authority=trusted,
                resolver_store_record=store_record,
            )

    fabricated = clone(valid)
    fabricated["claim_intent_hash"] = ALT_DIGEST
    with pytest.raises(LiveIssueContractError):
        validate_credential_receipt(
            fabricated,
            trusted_authority=trusted,
            resolver_store_record=store_record,
        )
    wrong_store = clone(store_record)
    wrong_store["identity"] = triple("rsr", digest=ALT_DIGEST)
    with pytest.raises(LiveIssueContractError):
        validate_credential_receipt(
            valid,
            trusted_authority=trusted,
            resolver_store_record=wrong_store,
        )


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


def test_final_payload_hash_is_domain_separated_complete_and_non_recursive() -> None:
    schema = _schema("claim_command")
    claim = valid_claim()
    fields = [field for field in schema["properties"] if field in claim and field != "payload_hash"]
    preimage, digest = compute_final_claim_payload(claim, preimage_fields=fields)
    assert digest == claim["payload_hash"]
    assert "payload_hash" not in preimage
    for invalid_fields in (fields[:-1], [*fields, "payload_hash"]):
        with pytest.raises(LiveIssueContractError):
            compute_final_claim_payload(claim, preimage_fields=invalid_fields)
    substituted = clone(claim)
    substituted["provider_family"] = "codex"
    _, changed = compute_final_claim_payload(substituted, preimage_fields=fields)
    assert changed != digest


def test_command_identity_joins_and_global_tail_are_independent_semantics() -> None:
    claim = valid_claim()
    validate_claim_command(claim)
    for field in ("target_stream_id", "expected_ledger_tail_hash"):
        mutated = clone(claim)
        mutated[field] = "wrong"
        with pytest.raises(LiveIssueContractError):
            validate_claim_command(mutated)

    outcome = {
        "target_stream_id": f"pinv_{UUID7}",
        "invocation_id": f"pinv_{UUID7}",
        "expected_invocation_stream_version": 1,
        "expected_cost_grant_stream_version": 2,
        "cost_grant": triple("cgr"),
        "write_set": [
            {"stream_role": "provider_invocation", "stream_id": f"pinv_{UUID7}", "expected_version": 1},
            {"stream_role": "cost_grant", "stream_id": f"cgr_{UUID7}", "expected_version": 2},
        ],
    }
    validate_outcome_command(outcome)
    duplicated = clone(outcome)
    duplicated["write_set"][1]["stream_role"] = "provider_invocation"
    with pytest.raises(LiveIssueContractError):
        validate_outcome_command(duplicated)


def test_event_batch_replay_global_tail_and_hash_chain_are_reconstructible() -> None:
    key = "outcome-key-1"
    event = {
        "schema_id": "ars://wp6-2/live-issue/event/ProviderInvocationOutcomeRecorded",
        "schema_version": "1.0.0",
        "event_type": "ProviderInvocationOutcomeRecorded",
        "event_id": f"evt_{UUID7}",
        "project_id": "project-1",
        "stream_id": f"pinv_{UUID7}",
        "stream_version": 2,
        "prior_stream_version": 1,
        "resulting_stream_version": 2,
        "global_position": 43,
        "transaction_id": f"txn_{UUID7}",
        "transaction_index": 0,
        "transaction_count": 1,
        "command_id": f"cmd_{UUID7}",
        "command_type": "RecordLiveProviderInvocationOutcome",
        "correlation_id": "correlation-1",
        "causation_id": "causation-1",
        "actor_id": f"act_{UUID7}",
        "authority_grant_id": f"agr_{UUID7}",
        "authority_scope": "wp6.2.live-issue.outcome.record",
        "idempotency_key": key,
        "idempotency_key_hash": hashlib.sha256(key.encode()).hexdigest(),
        "payload_hash": DIGEST,
        "occurred_at": "2026-07-25T20:00:00Z",
        "recorded_at": "2026-07-25T20:00:01Z",
        "previous_event_hash": DIGEST,
        "payload": {"outcome": "terminal"},
    }
    event["event_hash"] = hashlib.sha256(
        b"ars:w2:event:v1\0" + json.dumps(event, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    validate_event_batch([event], expected_global_tail=42, expected_previous_hash=DIGEST)
    for field in ("global_position", "idempotency_key_hash", "previous_event_hash", "event_hash"):
        invalid = clone(event)
        invalid[field] = ALT_DIGEST if field.endswith("hash") else 44
        with pytest.raises(LiveIssueContractError):
            validate_event_batch([invalid], expected_global_tail=42, expected_previous_hash=DIGEST)


def test_binding_argv_and_token_gates_are_exact_and_relational() -> None:
    binding = valid_live_issue_binding()
    validate_live_issue_binding(binding)
    for mutation in ("empty_argv", "contradictory_gate", "above_ceiling"):
        invalid = clone(binding)
        if mutation == "empty_argv":
            invalid["argv_profile"]["ordered_flags"] = []
        elif mutation == "contradictory_gate":
            invalid["context"]["input_token_gate"]["passed"] = False
        else:
            invalid["context"]["input_token_gate"]["count"] = 201
        with pytest.raises(LiveIssueContractError):
            validate_live_issue_binding(invalid)


def test_evidence_identity_is_deterministic_and_store_conflicts_fail() -> None:
    evidence = {
        "claim": triple("clm"),
        "live_issue_binding": triple("lib"),
        "credential_use_receipt": triple("cur"),
        "invocation_observation_key": "process-session-1/request-1",
    }
    preimage = dict(evidence)
    digest = hashlib.sha256(
        b"ars:wp6-2:provider-invocation-evidence:v1\0"
        + json.dumps(preimage, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    evidence["evidence_uniqueness_key"] = digest
    evidence["provider_invocation_evidence_id"] = f"piev_{digest}"
    assert validate_evidence_uniqueness(evidence) == digest
    assert validate_evidence_store(None, evidence) == "insert"
    assert validate_evidence_store(evidence, clone(evidence)) == "duplicate"
    conflict = clone(evidence)
    conflict["extra"] = "different-content"
    with pytest.raises(LiveIssueContractError):
        validate_evidence_store(evidence, conflict)


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
            "reserved_input_tokens": 1_000_000,
            "reserved_output_tokens": 1_000_000,
            "currency": "USD_MICRO",
            "rate_evidence": triple("rate"),
            "accepted_reservation": {
                "reserved_cost_microunits": 5,
                "currency": "USD_MICRO",
                "rate_evidence": triple("rate"),
            },
        }
    )
    invalid = {
        "rate_mode": "metered",
        "reserved_cost_microunits": 10,
        "consumed_cost_microunits": 10,
        "refund_cost_microunits": 10,
        "disposition": "exact",
        "input_tokens": 1,
        "output_tokens": 1,
        "input_rate": 5_000_000,
        "output_rate": 5_000_000,
        "reserved_input_tokens": 1,
        "reserved_output_tokens": 1,
        "currency": "USD_MICRO",
        "rate_evidence": triple("rate"),
        "accepted_reservation": {
            "reserved_cost_microunits": 10,
            "currency": "USD_MICRO",
            "rate_evidence": triple("rate"),
        },
    }
    with pytest.raises(LiveIssueContractError):
        validate_reconciliation(invalid)
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
