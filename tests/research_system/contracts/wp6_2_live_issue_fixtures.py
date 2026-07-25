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
