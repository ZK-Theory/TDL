from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


class LiveIssueContractError(ValueError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise LiveIssueContractError(code)


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


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
    expected: Mapping[str, Any],
) -> None:
    _require(receipt.get("owner") == "named_credential_resolver", "credential_receipt_wrong_owner")
    _require(receipt.get("contains_credential_bytes") is False, "credential_bytes_present")
    for field in (
        "resolver",
        "resolver_trust_root",
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
        _require(receipt.get(field) == expected.get(field), f"credential_receipt_{field}_mismatch")
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
