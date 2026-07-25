from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any

DIGEST = "a" * 64
ALT_DIGEST = "b" * 64
UUID7 = "018f47a2-9b3c-7def-8abc-0123456789ab"


def triple(stem: str, *, digest: str = DIGEST) -> dict[str, Any]:
    return {"id": f"{stem}_{UUID7}", "revision": 1, "hash": digest}


def valid_credential_receipt() -> dict[str, Any]:
    receipt = {
        "schema_id": "ars://wp6-2/live-issue/CredentialUseReceipt",
        "schema_version": "1.0.0",
        "credential_use_receipt_id": f"cur_{UUID7}",
        "revision": 1,
        "content_hash": DIGEST,
        "owner": "named_credential_resolver",
        "resolver": {"id": "resolver.local", "version": "1.0.0"},
        "resolver_trust_root": triple("rtr"),
        "resolver_store": triple("rst"),
        "resolver_store_record": triple("rsr"),
        "secret_reference": triple("srf"),
        "credential_class": "api_token",
        "claim_command_id": f"cmd_{UUID7}",
        "invocation_id": f"pinv_{UUID7}",
        "claim_intent_hash": DIGEST,
        "provider_family": "claude",
        "requested_scope": "provider.invoke",
        "isolated_auth_context_id": "auth-context-1",
        "provider_process_context": "process-session-1",
        "checked_at": "2026-07-25T20:00:00Z",
        "expiry_state": "current",
        "revocation_state": "not_revoked",
        "contains_credential_bytes": False,
    }
    fields = trusted_resolver_authority()["attested_fields"]
    preimage = {field: receipt[field] for field in fields}
    signed_hash = hashlib.sha256(
        b"ars:wp6-2:credential-use-receipt:v1\0" + json.dumps(preimage, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    receipt["authority_attestation"] = {
        "trust_root": triple("rtr"),
        "signing_key_id": "resolver-signing-key-1",
        "algorithm": "resolver-store-attestation-v1",
        "signed_preimage_hash": signed_hash,
        "verification_evidence_hash": ALT_DIGEST,
    }
    return receipt


def trusted_resolver_authority() -> dict[str, Any]:
    return {
        "resolver": {"id": "resolver.local", "version": "1.0.0"},
        "resolver_trust_root": triple("rtr"),
        "resolver_store": triple("rst"),
        "allowed_signing_key_ids": ["resolver-signing-key-1"],
        "attested_fields": [
            "resolver",
            "resolver_trust_root",
            "resolver_store",
            "resolver_store_record",
            "secret_reference",
            "credential_class",
            "claim_command_id",
            "invocation_id",
            "claim_intent_hash",
            "provider_family",
            "requested_scope",
            "isolated_auth_context_id",
            "provider_process_context",
            "checked_at",
            "expiry_state",
            "revocation_state",
            "contains_credential_bytes",
        ],
    }


def resolver_store_record() -> dict[str, Any]:
    receipt = valid_credential_receipt()
    return {
        "identity": receipt["resolver_store_record"],
        **{
            field: receipt[field]
            for field in trusted_resolver_authority()["attested_fields"]
            if field not in {"resolver", "resolver_trust_root", "resolver_store", "resolver_store_record"}
        },
        "verification_evidence_hash": ALT_DIGEST,
    }


def valid_provider_invocation_evidence() -> dict[str, Any]:
    identity_preimage = {
        "claim": triple("clm"),
        "live_issue_binding": triple("lib"),
        "credential_use_receipt": triple("cur"),
        "invocation_observation_key": "process-session-1/request-1",
    }
    uniqueness = hashlib.sha256(
        b"ars:wp6-2:provider-invocation-evidence:v1\0"
        + json.dumps(identity_preimage, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    evidence = {
        "schema_id": "ars://wp6-2/live-issue/ProviderInvocationEvidence",
        "schema_version": "1.0.0",
        "provider_invocation_evidence_id": f"piev_{uniqueness}",
        "revision": 1,
        "content_hash": DIGEST,
        **identity_preimage,
        "evidence_uniqueness_key": uniqueness,
        "actual_argv_profile_hash": DIGEST,
        "cwd": "C:/worktree",
        "root": "C:/worktree",
        "redacted_environment_hash": DIGEST,
        "redacted_config_hash": DIGEST,
        "timestamps": {
            "attempted_at": "2026-07-25T20:00:00Z",
            "completed_at": "2026-07-25T20:00:01Z",
        },
        "native_identity": {
            "request_id": "request-1",
            "session_id": "session-1",
            "thread_id": None,
            "response_id": "response-1",
        },
        "actual_selection": {
            "provider_family": "claude",
            "provider_proven": True,
            "model": "claude-native-model",
            "model_proven": True,
            "version": "2026-07",
            "version_proven": True,
            "profile": "research",
            "profile_proven": True,
            "credential_context_id": "auth-context-1",
            "credential_context_proven": True,
        },
        "delivery": {
            "payload_hash": DIGEST,
            "context_hash": DIGEST,
            "disposition": "proven",
            "proof_fields": {
                "request_id": "request-1",
                "response_id": "response-1",
                "payload_acknowledgement": DIGEST,
            },
        },
        "terminal": {
            "lifecycle": "observed",
            "native_class": "success",
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
            "cost_microunits": 2,
        },
        "secret_scans": [{"seam": "argv", "status": "clear", "evidence_hash": DIGEST}],
        "source_declaration": "actual_process_and_provider_observations_not_command_assertions",
    }
    preimage = {key: value for key, value in evidence.items() if key != "content_hash"}
    evidence["content_hash"] = hashlib.sha256(
        json.dumps(preimage, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return evidence


def valid_live_provider_receipt() -> dict[str, Any]:
    evidence = valid_provider_invocation_evidence()
    return {
        "schema_id": "ars://adapters/provider-receipt/v3",
        "schema_version": "3.0.0",
        "provider_receipt_id": f"prcp_{UUID7}",
        "revision": 1,
        "content_hash": DIGEST,
        "claim": triple("clm"),
        "invocation_evidence": {
            "id": evidence["provider_invocation_evidence_id"],
            "revision": evidence["revision"],
            "hash": evidence["content_hash"],
        },
        "live_issue_binding": triple("lib"),
        "accepted_t2_receipt": triple("rcp"),
        "provider_command": triple("pcmd"),
        "reservation": triple("rsv"),
        "actual_selection": {
            "provider_family": "claude",
            "model": "claude-native-model",
            "version": "2026-07",
            "profile": "research",
            "credential_context_id": "auth-context-1",
            "all_proven": True,
        },
        "delivery": "proven",
        "outcome": "terminal",
        "accounting": {
            "rate_mode": "metered",
            "actuals_proven": True,
            "input_tokens": 1,
            "output_tokens": 1,
            "consumed_cost_microunits": 2,
            "disposition": "exact",
        },
        "research_eligibility": "eligible",
        "complete": True,
    }


def valid_reconciliation() -> dict[str, Any]:
    rate = triple("rate")
    return {
        "rate_mode": "metered",
        "accepted_reservation": {
            "reservation": triple("rsv"),
            "reserved_cost_microunits": 10,
            "cost_ceiling_microunits": 10,
            "pre_reconciliation_remaining_cost_microunits": 10,
            "currency": "USD_MICRO",
            "rate_evidence": rate,
        },
        "reserved_input_tokens": 10,
        "reserved_output_tokens": 10,
        "total_token_ceiling": 20,
        "input_tokens": 1,
        "output_tokens": 1,
        "total_tokens": 2,
        "input_rate": 1_000_000,
        "output_rate": 1_000_000,
        "currency": "USD_MICRO",
        "rate_evidence": rate,
        "zero_cost_authority": None,
        "cost_ceiling_microunits": 10,
        "reserved_cost_microunits": 10,
        "consumed_cost_microunits": 2,
        "refund_cost_microunits": 8,
        "remaining_cost_microunits": 8,
        "disposition": "exact",
        "actuals_proven": True,
    }


def valid_outcome_command() -> dict[str, Any]:
    evidence = valid_provider_invocation_evidence()
    return {
        "schema_id": "ars://wp6-2/live-issue/command/RecordLiveProviderInvocationOutcome",
        "schema_version": "1.0.0",
        "command_type": "RecordLiveProviderInvocationOutcome",
        "command_id": f"cmd_{UUID7}",
        "actor_id": f"act_{UUID7}",
        "on_behalf_of_actor_id": None,
        "authority_grant_id": f"agr_{UUID7}",
        "reason": "record one observed provider invocation",
        "evidence_refs": [triple("evi")],
        "authority_scope": "wp6.2.live-issue.outcome.record",
        "idempotency_key": "outcome-key-1",
        "correlation_id": "correlation-1",
        "causation_id": "causation-1",
        "payload_hash": DIGEST,
        "target_stream_id": f"pinv_{UUID7}",
        "invocation_id": f"pinv_{UUID7}",
        "expected_invocation_stream_version": 1,
        "expected_cost_grant_stream_version": 2,
        "expected_global_position": 42,
        "expected_ledger_tail_hash": DIGEST,
        "write_set": [
            {"stream_role": "provider_invocation", "stream_id": f"pinv_{UUID7}", "expected_version": 1},
            {"stream_role": "cost_grant", "stream_id": f"cgr_{UUID7}", "expected_version": 2},
        ],
        "claim": triple("clm"),
        "invocation_evidence": {
            "id": evidence["provider_invocation_evidence_id"],
            "revision": evidence["revision"],
            "hash": evidence["content_hash"],
        },
        "live_provider_receipt": triple("prcp"),
        "cost_grant": triple("cgr"),
        "reservation": triple("rsv"),
        "outcome": "terminal",
        "reconciliation": valid_reconciliation(),
        "submitted_at": "2026-07-25T20:00:02Z",
    }


def valid_outcome_events() -> list[dict[str, Any]]:
    command = valid_outcome_command()
    common = {
        "schema_version": "1.0.0",
        "project_id": "project-1",
        "transaction_id": f"txn_{UUID7}",
        "transaction_count": 3,
        "command_id": command["command_id"],
        "command_type": command["command_type"],
        "correlation_id": command["correlation_id"],
        "causation_id": command["causation_id"],
        "actor_id": command["actor_id"],
        "authority_grant_id": command["authority_grant_id"],
        "authority_scope": command["authority_scope"],
        "idempotency_key": command["idempotency_key"],
        "idempotency_key_hash": hashlib.sha256(command["idempotency_key"].encode()).hexdigest(),
        "payload_hash": command["payload_hash"],
        "occurred_at": "2026-07-25T20:00:03Z",
        "recorded_at": "2026-07-25T20:00:04Z",
    }
    events = [
        {
            **common,
            "schema_id": "ars://wp6-2/live-issue/event/ProviderInvocationOutcomeRecorded",
            "event_type": "ProviderInvocationOutcomeRecorded",
            "event_id": f"evt_{UUID7}",
            "stream_id": command["invocation_id"],
            "stream_version": 2,
            "prior_stream_version": 1,
            "resulting_stream_version": 2,
            "global_position": 43,
            "transaction_index": 0,
            "previous_event_hash": DIGEST,
            "payload": {
                "claim": command["claim"],
                "invocation_evidence": command["invocation_evidence"],
                "outcome": "terminal",
                "research_eligibility": "eligible",
            },
        },
        {
            **common,
            "schema_id": "ars://wp6-2/live-issue/event/LiveProviderReceiptRecorded",
            "event_type": "LiveProviderReceiptRecorded",
            "event_id": f"evt_{UUID7[:-1]}c",
            "stream_id": command["invocation_id"],
            "stream_version": 3,
            "prior_stream_version": 2,
            "resulting_stream_version": 3,
            "global_position": 44,
            "transaction_index": 1,
            "previous_event_hash": DIGEST,
            "payload": {
                "live_provider_receipt": command["live_provider_receipt"],
                "claim": command["claim"],
                "invocation_evidence": command["invocation_evidence"],
            },
        },
        {
            **common,
            "schema_id": "ars://wp6-2/live-issue/event/LiveCostGrantReconciled",
            "event_type": "LiveCostGrantReconciled",
            "event_id": f"evt_{UUID7[:-1]}d",
            "stream_id": command["cost_grant"]["id"],
            "stream_version": 3,
            "prior_stream_version": 2,
            "resulting_stream_version": 3,
            "global_position": 45,
            "transaction_index": 2,
            "previous_event_hash": DIGEST,
            "payload": {
                "claim": command["claim"],
                "invocation_evidence": command["invocation_evidence"],
                "reservation": command["reservation"],
                **valid_reconciliation(),
            },
        },
    ]
    previous = DIGEST
    for event in events:
        event["previous_event_hash"] = previous
        event["event_hash"] = hashlib.sha256(
            b"ars:w2:event:v1\0" + json.dumps(event, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        previous = event["event_hash"]
    return events


def valid_claim() -> dict[str, Any]:
    command = {
        "schema_id": "ars://wp6-2/live-issue/command/ClaimLiveProviderInvocation",
        "schema_version": "1.0.0",
        "command_type": "ClaimLiveProviderInvocation",
        "command_id": f"cmd_{UUID7}",
        "actor_id": f"act_{UUID7}",
        "on_behalf_of_actor_id": None,
        "authority_grant_id": f"agr_{UUID7}",
        "reason": "claim one authorized live provider invocation",
        "evidence_refs": [triple("evi")],
        "authority_scope": "wp6.2.live-issue.claim",
        "idempotency_key": "live-issue-key-1",
        "correlation_id": "correlation-1",
        "causation_id": "causation-1",
        "target_stream_id": f"pinv_{UUID7}",
        "expected_stream_version": 0,
        "write_set": [
            {
                "stream_role": "provider_invocation",
                "stream_id": f"pinv_{UUID7}",
                "expected_version": 0,
            }
        ],
        "expected_global_position": 42,
        "expected_ledger_tail_hash": DIGEST,
        "invocation_id": f"pinv_{UUID7}",
        "claim_intent_hash": DIGEST,
        "payload_hash": ALT_DIGEST,
        "accepted_t2_receipt": triple("rcp"),
        "accepted_t2_ledger_transaction": {
            **triple("txn"),
            "stream_version": 4,
        },
        "cost_grant_reserved_event": {
            **triple("evt"),
            "stream_version": 3,
        },
        "provider_command_issued_event": {
            **triple("evt"),
            "stream_version": 1,
        },
        "provider_command": triple("pcmd"),
        "cost_grant": triple("cgr"),
        "reservation": triple("rsv"),
        "secret_reference": triple("srf"),
        "task": triple("tsk"),
        "dispatch": triple("dsp"),
        "attempt": triple("att"),
        "resource_grant": triple("rgr"),
        "route": triple("rte"),
        "profile": triple("prf"),
        "context": triple("ctx"),
        "policy": triple("pol"),
        "adapter": triple("adp"),
        "live_issue_binding": triple("lib"),
        "resolver_trust_root": triple("rtr"),
        "resolver_requirement": {
            "resolver_id": "resolver.local",
            "resolver_version": "1.0.0",
            "credential_class": "api_token",
            "credential_scope": "provider.invoke",
            "isolated_auth_context_id": "auth-context-1",
        },
        "credential_use_receipt_id": f"cur_{UUID7}",
        "credential_use_receipt_revision": 1,
        "credential_use_receipt_hash": DIGEST,
        "provider_family": "claude",
        "normalized_operation": "messages.create",
        "preflight_hashes": {
            "policy_projection": DIGEST,
            "argv_profile": DIGEST,
            "payload": DIGEST,
            "context": DIGEST,
            "secret_scan": DIGEST,
            "resolver_receipt": DIGEST,
            "native_selector": DIGEST,
            "live_issue_binding": DIGEST,
        },
        "expected_object_versions": {
            name: 1
            for name in (
                "provider_command",
                "cost_grant",
                "reservation",
                "secret_reference",
                "task",
                "dispatch",
                "attempt",
                "resource_grant",
                "route",
                "profile",
                "context",
                "policy_bundle",
                "applicability_manifest",
                "adapter",
                "live_issue_binding",
                "resolver_trust_root",
                "ledger_transaction",
            )
        },
        "submitted_at": "2026-07-25T20:00:00Z",
    }
    excluded = {
        "credential_use_receipt_id",
        "credential_use_receipt_revision",
        "credential_use_receipt_hash",
        "payload_hash",
        "submitted_at",
        "recorded_at",
    }
    intent_fields = [key for key in command if key not in excluded and key != "claim_intent_hash"]
    intent_preimage = {field: command[field] for field in intent_fields}
    command["claim_intent_hash"] = hashlib.sha256(
        b"ars:wp6-2:live-claim-intent:v1\0"
        + json.dumps(intent_preimage, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    final_preimage = {key: value for key, value in command.items() if key != "payload_hash"}
    command["payload_hash"] = hashlib.sha256(
        b"ars:wp6-2:live-claim-payload:v1\0"
        + json.dumps(final_preimage, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return command


def valid_live_issue_binding() -> dict[str, Any]:
    return {
        "schema_id": "ars://wp6-2/live-issue/LiveIssueBinding",
        "schema_version": "1.0.0",
        "live_issue_binding_id": f"lib_{UUID7}",
        "revision": 1,
        "content_hash": DIGEST,
        "policy": {
            "bundle": triple("pol"),
            "applicability_manifest": triple("pam"),
            "compiler_id": "policy.compiler",
            "compiler_revision": "1",
            "generator_id": "policy.generator",
            "generator_revision": "1",
            "compiled_projection_hash": DIGEST,
            "ordered_control_ids": ["control-1", "control-2"],
        },
        "context": {
            "packet": triple("ctx"),
            "addenda": [triple("cxa")],
            "rendered_managed_content_hash": DIGEST,
            "input_token_gate": {"count": 100, "ceiling": 200, "passed": True},
            "reserved_output_token_gate": {"count": 50, "ceiling": 100, "passed": True},
        },
        "provider_selection": {
            "provider_family": "claude",
            "native_model_selector": "claude-native-model",
            "native_model_version": "2026-07",
            "route": triple("rte"),
            "profile": triple("prf"),
            "reasoning_setting": "standard",
        },
        "argv_profile": {
            "adapter_revision": "adapter-1",
            "executable": "claude",
            "ordered_flags": [
                "--model",
                "claude-native-model",
                "--profile",
                "research",
                "--reasoning",
                "standard",
            ],
            "profile_selector": "research",
            "model_flag": "--model=claude-native-model",
            "profile_flag": "--profile=research",
            "reasoning_flag": "--reasoning=standard",
            "sandbox": "workspace-write",
            "cwd": "C:/worktree",
            "root": "C:/worktree",
            "network": "provider_only",
            "tools": [],
            "permissions": ["workspace.read"],
            "environment_allowlist": ["PATH"],
            "prohibited_options": ["--dangerously-skip-permissions"],
        },
        "credential_requirement": {
            "secret_reference": triple("srf"),
            "resolver_id": "resolver.local",
            "resolver_version": "1.0.0",
            "resolver_trust_root": triple("rtr"),
            "credential_class": "api_token",
            "credential_scope": "provider.invoke",
            "isolated_auth_context_required": True,
            "expiry_revocation_rule": "current_and_not_revoked_at_claim",
        },
        "execution": {
            "timeout_ms": 60000,
            "cancellation": "terminate_process_group",
            "automatic_retry": False,
            "response_protocol": "provider_native_json",
        },
        "delivery_requirement": {
            "native_id_fields": ["request_id"],
            "native_status_fields": ["status"],
            "accounting_method": "provider_native",
            "max_input_tokens": 200,
            "max_output_tokens": 100,
            "max_cost_microunits": 1000,
            "expected_payload_hash": DIGEST,
            "expected_context_hash": DIGEST,
            "proven_predicate": "native request identity and payload acknowledgement both match",
        },
        "lifecycle": {
            "status": "proposed",
            "credential_material_prohibited": True,
            "unsupported_if_native_binding_inexact": True,
        },
    }


def clone(value: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(value)
