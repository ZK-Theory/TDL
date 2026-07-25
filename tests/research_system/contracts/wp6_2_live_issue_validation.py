from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml


class LiveIssueContractError(ValueError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise LiveIssueContractError(code)


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_trusted_resolver_authority(repo_root: Path, resolver_id: str) -> Mapping[str, Any]:
    path = repo_root / ".research-system/contracts/wp6-2-t3-t4-trusted-resolver-authorities.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    _require(document.get("coordinator_authoritative") is False, "coordinator_marked_authoritative")
    matches = [authority for authority in document["authorities"] if authority["resolver"]["id"] == resolver_id]
    _require(len(matches) == 1, "trusted_resolver_authority_not_unique")
    return matches[0]


def compute_claim_intent(
    claim: Mapping[str, Any],
    *,
    preimage_fields: Sequence[str],
) -> tuple[dict[str, Any], str]:
    expected = set(preimage_fields)
    _require(expected <= set(claim), "intent_field_missing")
    preimage = {field: claim[field] for field in preimage_fields}
    domain = b"ars:wp6-2:live-claim-intent:v1\0"
    return preimage, hashlib.sha256(domain + canonical_json(preimage)).hexdigest()


def compute_final_claim_payload(
    claim: Mapping[str, Any],
    *,
    preimage_fields: Sequence[str],
) -> tuple[dict[str, Any], str]:
    _require("payload_hash" not in preimage_fields, "final_payload_hash_self_inclusion")
    _require(set(preimage_fields) == set(claim) - {"payload_hash"}, "final_payload_preimage_incomplete")
    preimage = {field: claim[field] for field in preimage_fields}
    domain = b"ars:wp6-2:live-claim-payload:v1\0"
    return preimage, hashlib.sha256(domain + canonical_json(preimage)).hexdigest()


def validate_claim_command(claim: Mapping[str, Any]) -> None:
    invocation_id = claim.get("invocation_id")
    _require(claim.get("target_stream_id") == invocation_id, "claim_target_mismatch")
    write_set = claim.get("write_set")
    _require(isinstance(write_set, list) and len(write_set) == 1, "claim_write_set_shape")
    _require(write_set[0].get("stream_role") == "provider_invocation", "claim_write_set_role")
    _require(write_set[0].get("stream_id") == invocation_id, "claim_write_set_stream_mismatch")
    _require(
        write_set[0].get("expected_version") == claim.get("expected_stream_version"),
        "claim_write_set_version_mismatch",
    )
    _require(
        claim.get("expected_global_position") >= 0
        and isinstance(claim.get("expected_ledger_tail_hash"), str)
        and len(claim["expected_ledger_tail_hash"]) == 64
        and set(claim["expected_ledger_tail_hash"]) <= set("0123456789abcdef"),
        "claim_global_tail_missing",
    )


def validate_outcome_command(command: Mapping[str, Any]) -> None:
    invocation_id = command.get("invocation_id")
    write_set = command.get("write_set")
    _require(command.get("target_stream_id") == invocation_id, "outcome_target_mismatch")
    _require(isinstance(write_set, list) and len(write_set) == 2, "outcome_write_set_shape")
    _require(
        [entry.get("stream_role") for entry in write_set] == ["provider_invocation", "cost_grant"],
        "outcome_write_set_order",
    )
    _require(write_set[0].get("stream_id") == invocation_id, "outcome_invocation_stream_mismatch")
    _require(
        write_set[0].get("expected_version") == command.get("expected_invocation_stream_version"),
        "outcome_invocation_version_mismatch",
    )
    _require(
        write_set[1].get("stream_id") == command.get("cost_grant", {}).get("id"),
        "outcome_cost_stream_mismatch",
    )
    _require(
        write_set[1].get("expected_version") == command.get("expected_cost_grant_stream_version"),
        "outcome_cost_version_mismatch",
    )


def _event_hash(event: Mapping[str, Any]) -> str:
    preimage = {key: value for key, value in event.items() if key != "event_hash"}
    return hashlib.sha256(b"ars:w2:event:v1\0" + canonical_json(preimage)).hexdigest()


def validate_event_batch(
    events: Sequence[Mapping[str, Any]],
    *,
    expected_global_tail: int,
    expected_previous_hash: str,
) -> None:
    _require(bool(events), "event_batch_empty")
    transaction_id = events[0].get("transaction_id")
    count = len(events)
    previous_hash = expected_previous_hash
    for index, event in enumerate(events):
        _require(event.get("transaction_id") == transaction_id, "event_transaction_mismatch")
        _require(event.get("transaction_index") == index, "event_transaction_index")
        _require(event.get("transaction_count") == count, "event_transaction_count")
        _require(event.get("global_position") == expected_global_tail + index + 1, "event_global_position")
        _require(
            event.get("resulting_stream_version") == event.get("prior_stream_version") + 1,
            "event_stream_version",
        )
        expected_key_hash = hashlib.sha256(event["idempotency_key"].encode("utf-8")).hexdigest()
        _require(event.get("idempotency_key_hash") == expected_key_hash, "event_idempotency_hash")
        _require(event.get("previous_event_hash") == previous_hash, "event_hash_chain")
        _require(event.get("event_hash") == _event_hash(event), "event_hash_invalid")
        previous_hash = event["event_hash"]


def validate_dependency_graph(
    actual_edges: Sequence[Sequence[str]],
    *,
    expected_edges: set[tuple[str, str]],
) -> None:
    edges = {tuple(edge) for edge in actual_edges}
    _require(edges == expected_edges, "dependency_graph_edge_mismatch")
    adjacency: dict[str, set[str]] = {}
    for source, target in edges:
        adjacency.setdefault(source, set()).add(target)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        _require(node not in visiting, "dependency_graph_cycle")
        if node in visited:
            return
        visiting.add(node)
        for child in adjacency.get(node, set()):
            visit(child)
        visiting.remove(node)
        visited.add(node)

    for node in set(adjacency):
        visit(node)
    _require(
        ("CredentialUseReceipt", "LiveIssueBinding") not in edges
        and ("CredentialUseReceipt", "claim_intent_hash") not in edges,
        "credential_receipt_back_edge",
    )


def validate_credential_receipt(
    receipt: Mapping[str, Any],
    *,
    trusted_authority: Mapping[str, Any],
    resolver_store_record: Mapping[str, Any],
) -> None:
    _require(receipt.get("owner") == "named_credential_resolver", "credential_receipt_wrong_owner")
    _require(receipt.get("contains_credential_bytes") is False, "credential_bytes_present")
    _require(
        receipt.get("resolver") == trusted_authority.get("resolver")
        and receipt.get("resolver_trust_root") == trusted_authority.get("resolver_trust_root")
        and receipt.get("resolver_store") == trusted_authority.get("resolver_store"),
        "credential_receipt_untrusted_authority",
    )
    _require(
        receipt.get("resolver_store_record") == resolver_store_record.get("identity"),
        "credential_receipt_wrong_store_record",
    )
    for field in (
        "secret_reference",
        "credential_class",
        "claim_command_id",
        "invocation_id",
        "claim_intent_hash",
        "provider_family",
        "requested_scope",
        "isolated_auth_context_id",
        "provider_process_context",
    ):
        _require(receipt.get(field) == resolver_store_record.get(field), f"credential_receipt_{field}_mismatch")
    attestation = receipt.get("authority_attestation", {})
    _require(attestation.get("trust_root") == trusted_authority.get("resolver_trust_root"), "attestation_trust_root")
    _require(
        attestation.get("signing_key_id") in trusted_authority.get("allowed_signing_key_ids", []), "attestation_key"
    )
    signed = {field: receipt[field] for field in trusted_authority["attested_fields"]}
    expected_hash = hashlib.sha256(b"ars:wp6-2:credential-use-receipt:v1\0" + canonical_json(signed)).hexdigest()
    _require(attestation.get("signed_preimage_hash") == expected_hash, "attestation_preimage_hash")
    _require(
        attestation.get("verification_evidence_hash") == resolver_store_record.get("verification_evidence_hash"),
        "attestation_evidence",
    )
    _require(receipt.get("expiry_state") == "current", "credential_receipt_stale")
    _require(receipt.get("revocation_state") == "not_revoked", "credential_receipt_revoked")


def validate_claim_arbitration(observation: Mapping[str, Any]) -> None:
    _require(observation.get("attempt_count") == 2, "claim_arbitration_requires_two_attempts")
    _require(observation.get("winner_count") == 1, "claim_arbitration_not_exactly_one_winner")
    _require(observation.get("loser_count") == 1, "claim_arbitration_not_exactly_one_loser")
    _require(observation.get("claim_event_count") == 1, "claim_arbitration_duplicate_event")
    _require(observation.get("invocation_count") == 1, "claim_arbitration_duplicate_invocation")
    _require(observation.get("automatic_retry_count") == 0, "claim_automatic_retry")


def validate_preflight_failure(observation: Mapping[str, Any]) -> None:
    _require(observation.get("status") == "rejected", "preflight_failure_not_rejected")
    for field in (
        "event_count",
        "invocation_count",
        "ledger_byte_delta",
        "canonical_object_byte_delta",
        "credential_receipt_project_publication_count",
    ):
        _require(observation.get(field) == 0, f"preflight_failure_effect_{field}")


def validate_outcome(observation: Mapping[str, Any]) -> None:
    state = observation.get("lifecycle")
    _require(state in {"not_invoked", "observed", "uncertain"}, "outcome_lifecycle_invalid")
    _require(observation.get("automatic_retry_count") == 0, "outcome_automatic_retry")
    if state in {"not_invoked", "uncertain"}:
        _require(observation.get("research_eligibility") == "ineligible", "unsafe_research_eligibility")
    if state == "uncertain":
        _require(observation.get("actual_input_tokens") is None, "uncertain_invented_input_tokens")
        _require(observation.get("actual_output_tokens") is None, "uncertain_invented_output_tokens")
        _require(
            observation.get("cost_disposition") in {"reserved", "conservatively_consumed"},
            "uncertain_cost_disposition_invalid",
        )
        _require(observation.get("refund_count") == 0, "uncertain_silent_refund")


def validate_reconciliation(record: Mapping[str, Any]) -> None:
    reserved = record.get("reserved_cost_microunits")
    consumed = record.get("consumed_cost_microunits")
    refund = record.get("refund_cost_microunits")
    _require(isinstance(reserved, int) and not isinstance(reserved, bool) and reserved >= 0, "cost_invalid")
    mode = record.get("rate_mode")
    if mode == "uncertain":
        _require(consumed is None and refund is None, "uncertain_cost_invented")
        _require(record.get("disposition") in {"reserved", "conservatively_consumed"}, "uncertain_disposition")
        return
    _require(isinstance(consumed, int) and not isinstance(consumed, bool), "cost_invalid")
    _require(isinstance(refund, int) and not isinstance(refund, bool), "cost_invalid")
    _require(0 <= consumed <= reserved and refund == reserved - consumed, "cost_reconciliation_invalid")
    if mode == "zero_cost_authorized":
        _require(reserved == consumed == refund == 0, "zero_cost_nonzero")
        _require(record.get("zero_cost_authority") is not None, "zero_cost_authority_missing")
    else:
        _require(mode == "metered", "rate_mode_invalid")
        input_tokens = record.get("input_tokens")
        output_tokens = record.get("output_tokens")
        input_rate = record.get("input_rate")
        output_rate = record.get("output_rate")
        _require(
            all(
                isinstance(v, int) and not isinstance(v, bool) and v >= 0
                for v in (input_tokens, output_tokens, input_rate, output_rate)
            ),
            "metered_values_invalid",
        )
        expected = (input_tokens * input_rate + 999_999) // 1_000_000
        expected += (output_tokens * output_rate + 999_999) // 1_000_000
        _require(consumed == expected, "metered_cost_formula_invalid")
        _require(input_tokens <= record.get("reserved_input_tokens"), "input_token_ceiling")
        _require(output_tokens <= record.get("reserved_output_tokens"), "output_token_ceiling")
        reservation = record.get("accepted_reservation", {})
        _require(reserved == reservation.get("reserved_cost_microunits"), "reservation_cost_mismatch")
        _require(record.get("currency") == reservation.get("currency"), "reservation_currency_mismatch")
        _require(record.get("rate_evidence") == reservation.get("rate_evidence"), "rate_evidence_mismatch")


def validate_live_issue_binding(binding: Mapping[str, Any]) -> None:
    selection = binding["provider_selection"]
    argv = binding["argv_profile"]
    provider = selection["provider_family"]
    expected = {
        "claude": [
            "--model",
            selection["native_model_selector"],
            "--profile",
            argv["profile_selector"],
            "--reasoning",
            selection["reasoning_setting"],
        ],
        "codex": [
            "--model",
            selection["native_model_selector"],
            "--profile",
            argv["profile_selector"],
            "--reasoning-effort",
            selection["reasoning_setting"],
        ],
    }[provider]
    _require(argv["executable"] == provider, "argv_executable_mismatch")
    _require(argv["ordered_flags"] == expected, "argv_profile_not_exact")
    for gate in ("input_token_gate", "reserved_output_token_gate"):
        item = binding["context"][gate]
        _require(item["passed"] is (item["count"] <= item["ceiling"]), f"{gate}_contradiction")
    _require(
        binding["context"]["input_token_gate"]["ceiling"] <= binding["delivery_requirement"]["max_input_tokens"],
        "input_gate_above_delivery_ceiling",
    )
    _require(
        binding["context"]["reserved_output_token_gate"]["ceiling"]
        <= binding["delivery_requirement"]["max_output_tokens"],
        "output_gate_above_delivery_ceiling",
    )


def validate_evidence_uniqueness(evidence: Mapping[str, Any]) -> str:
    preimage = {
        field: evidence[field]
        for field in (
            "claim",
            "live_issue_binding",
            "credential_use_receipt",
            "invocation_observation_key",
        )
    }
    digest = hashlib.sha256(b"ars:wp6-2:provider-invocation-evidence:v1\0" + canonical_json(preimage)).hexdigest()
    _require(evidence.get("evidence_uniqueness_key") == digest, "evidence_uniqueness_key")
    _require(evidence.get("provider_invocation_evidence_id") == f"piev_{digest}", "evidence_id_not_deterministic")
    return digest


def validate_evidence_store(existing: Mapping[str, Any] | None, candidate: Mapping[str, Any]) -> str:
    key = validate_evidence_uniqueness(candidate)
    if existing is None:
        return "insert"
    _require(validate_evidence_uniqueness(existing) == key, "evidence_store_key_mismatch")
    _require(existing == candidate, "evidence_store_conflict")
    return "duplicate"


def validate_evidence_orphan(observation: Mapping[str, Any]) -> None:
    _require(observation.get("object_publish_count") == 1, "orphan_publish_count_invalid")
    _require(observation.get("ledger_commit_count") == 0, "orphan_has_ledger_commit")
    for field in (
        "claim_authorization_count",
        "invocation_count",
        "receipt_count",
        "refund_count",
        "research_use_count",
    ):
        _require(observation.get(field) == 0, f"orphan_effect_{field}")


def validate_exact_replay(observation: Mapping[str, Any]) -> None:
    _require(observation.get("status") == "duplicate", "replay_not_duplicate")
    _require(observation.get("evidence_id") == observation.get("original_evidence_id"), "replay_evidence_changed")
    _require(observation.get("receipt_hash") == observation.get("original_receipt_hash"), "replay_receipt_changed")
    for field in (
        "new_invocation_count",
        "new_evidence_object_count",
        "new_receipt_count",
        "new_reconciliation_count",
        "new_refund_count",
    ):
        _require(observation.get(field) == 0, f"replay_effect_{field}")


def validate_native_binding(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> None:
    for field in (
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
    ):
        _require(actual.get(field) == expected.get(field), f"native_binding_{field}_mismatch")


def validate_no_secret_material(value: Any, *, sentinels: Sequence[str]) -> None:
    serialized = json.dumps(value, sort_keys=True)
    forbidden_names = ("raw_credential", "secret_bytes", "credential_value", "hidden_reasoning")
    _require(not any(name in serialized for name in forbidden_names), "secret_field_present")
    _require(not any(sentinel in serialized for sentinel in sentinels), "secret_sentinel_present")
