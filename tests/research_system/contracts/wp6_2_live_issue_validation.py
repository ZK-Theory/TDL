from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


class LiveIssueContractError(ValueError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise LiveIssueContractError(code)


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _load_identity_bound_yaml(repo_root: Path, relative_path: str) -> Mapping[str, Any]:
    identity_path = repo_root / ".research-system/contracts/wp6-2-t3-t4-live-issue-schema-identities.yaml"
    identities = yaml.safe_load(identity_path.read_text(encoding="utf-8"))
    matches = [row for row in identities["contract_artifacts"] if row["path"] == relative_path]
    _require(len(matches) == 1, "registered_contract_identity_not_unique")
    raw = (repo_root / relative_path).read_bytes()
    _require(
        hashlib.sha256(raw).hexdigest() == matches[0]["raw_utf8_lf_sha256"],
        "registered_contract_byte_mismatch",
    )
    return yaml.safe_load(raw)


def load_trusted_resolver_authority(repo_root: Path, resolver_id: str) -> Mapping[str, Any]:
    path = repo_root / ".research-system/contracts/wp6-2-t3-t4-trusted-resolver-authorities.yaml"
    document = _load_identity_bound_yaml(repo_root, path.relative_to(repo_root).as_posix())
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


def validate_claim_command(claim: Mapping[str, Any], *, repo_root: Path) -> None:
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
    schema = json.loads(
        (
            repo_root / ".research-system/schemas/wp6-2-live-issue/commands/claim-live-provider-invocation.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(claim)
    _, intent_hash = compute_claim_intent(claim, preimage_fields=schema["x-intent-preimage-fields"])
    _require(claim.get("claim_intent_hash") == intent_hash, "claim_intent_hash_mismatch")
    final_fields = [field for field in schema["properties"] if field in claim and field != "payload_hash"]
    _, final_hash = compute_final_claim_payload(claim, preimage_fields=final_fields)
    _require(claim.get("payload_hash") == final_hash, "claim_payload_hash_mismatch")


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
    validate_reconciliation(
        command.get("reconciliation", {}),
        expected_reservation=command.get("reservation", {}),
    )


def _event_hash(event: Mapping[str, Any]) -> str:
    preimage = {key: value for key, value in event.items() if key != "event_hash"}
    return hashlib.sha256(b"ars:w2:event:v1\0" + canonical_json(preimage)).hexdigest()


def validate_event_batch(
    command: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    *,
    expected_event_types: Sequence[str],
    expected_global_tail: int,
    expected_previous_hash: str,
) -> None:
    validate_outcome_command(command)
    _require(len(events) == len(expected_event_types) == 3, "event_batch_count")
    _require([event.get("event_type") for event in events] == list(expected_event_types), "event_order")
    transaction_id = events[0].get("transaction_id")
    count = len(events)
    previous_hash = expected_previous_hash
    for index, event in enumerate(events):
        for field in (
            "command_id",
            "command_type",
            "correlation_id",
            "causation_id",
            "actor_id",
            "authority_grant_id",
            "authority_scope",
            "idempotency_key",
            "payload_hash",
        ):
            _require(event.get(field) == command.get(field), f"event_{field}_mismatch")
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
    invocation_stream = command["invocation_id"]
    cost_stream = command["cost_grant"]["id"]
    _require(
        [event["stream_id"] for event in events] == [invocation_stream, invocation_stream, cost_stream],
        "event_stream_roles",
    )
    _require(
        events[0]["prior_stream_version"] == command["expected_invocation_stream_version"], "event_invocation_prior"
    )
    _require(events[1]["prior_stream_version"] == events[0]["resulting_stream_version"], "event_invocation_sequence")
    _require(events[2]["prior_stream_version"] == command["expected_cost_grant_stream_version"], "event_cost_prior")
    for event in events:
        _require(event.get("stream_version") == event.get("resulting_stream_version"), "event_stream_version_alias")
    common_claim = command["claim"]
    common_evidence = command["invocation_evidence"]
    for event in events:
        payload = event["payload"]
        _require(payload.get("claim") == common_claim, "event_claim_join")
        _require(payload.get("invocation_evidence") == common_evidence, "event_evidence_join")
    _require(
        events[1]["payload"].get("live_provider_receipt") == command["live_provider_receipt"], "event_receipt_join"
    )
    _require(events[2]["payload"].get("reservation") == command["reservation"], "event_reservation_join")
    event_reconciliation = events[2]["payload"]
    _require(
        all(event_reconciliation.get(key) == value for key, value in command["reconciliation"].items()),
        "event_reconciliation_join",
    )
    validate_reconciliation(event_reconciliation, expected_reservation=command["reservation"])


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
    repo_root: Path,
    receipt: Mapping[str, Any],
) -> None:
    trusted_authority = load_trusted_resolver_authority(repo_root, receipt.get("resolver", {}).get("id", ""))
    records = [
        record
        for record in trusted_authority["resolver_store_records"]
        if record["identity"] == receipt.get("resolver_store_record")
    ]
    _require(len(records) == 1, "credential_receipt_store_record_not_registered")
    resolver_store_record = records[0]
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


def validate_reconciliation(
    record: Mapping[str, Any],
    *,
    expected_reservation: Mapping[str, Any],
) -> None:
    reserved = record.get("reserved_cost_microunits")
    consumed = record.get("consumed_cost_microunits")
    refund = record.get("refund_cost_microunits")
    _require(isinstance(reserved, int) and not isinstance(reserved, bool) and reserved >= 0, "cost_invalid")
    reservation = record.get("accepted_reservation", {})
    _require(reservation.get("reservation") == expected_reservation, "reservation_identity_mismatch")
    _require(reserved == reservation.get("reserved_cost_microunits"), "reservation_cost_mismatch")
    _require(record.get("currency") == reservation.get("currency"), "reservation_currency_mismatch")
    _require(record.get("rate_evidence") == reservation.get("rate_evidence"), "rate_evidence_mismatch")
    _require(
        record.get("cost_ceiling_microunits") == reservation.get("cost_ceiling_microunits"),
        "cost_ceiling_mismatch",
    )
    _require(reserved <= record.get("cost_ceiling_microunits"), "reservation_above_cost_ceiling")
    pre_reconciliation_available = reservation.get("pre_reconciliation_remaining_cost_microunits")
    _require(
        isinstance(pre_reconciliation_available, int)
        and not isinstance(pre_reconciliation_available, bool)
        and 0 <= pre_reconciliation_available <= record.get("cost_ceiling_microunits"),
        "pre_reconciliation_balance_invalid",
    )
    for field in (
        "reserved_input_tokens",
        "reserved_output_tokens",
        "total_token_ceiling",
        "input_rate",
        "output_rate",
    ):
        value = record.get(field)
        _require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"{field}_invalid")
        _require(value == reservation.get(field), f"reservation_{field}_mismatch")
    _require(
        record.get("total_token_ceiling") == record.get("reserved_input_tokens") + record.get("reserved_output_tokens"),
        "total_token_ceiling_invalid",
    )
    _require(
        record.get("zero_cost_authority") == reservation.get("zero_cost_authority"), "zero_cost_authority_mismatch"
    )
    mode = record.get("rate_mode")
    if mode == "uncertain":
        _require(record.get("actuals_proven") is False, "uncertain_actuals_proven")
        _require(
            record.get("input_tokens") is None
            and record.get("output_tokens") is None
            and record.get("total_tokens") is None,
            "uncertain_tokens_invented",
        )
        disposition = record.get("disposition")
        _require(disposition in {"reserved", "conservatively_consumed"}, "uncertain_disposition")
        if disposition == "reserved":
            _require(consumed is None and refund is None, "uncertain_cost_invented")
            _require(record.get("remaining_cost_microunits") is None, "uncertain_remaining_invented")
        else:
            _require(consumed == reserved and refund == 0, "uncertain_conservative_cost_invalid")
            _require(
                record.get("remaining_cost_microunits") == pre_reconciliation_available,
                "uncertain_conservative_remaining_invalid",
            )
        return
    _require(isinstance(consumed, int) and not isinstance(consumed, bool), "cost_invalid")
    _require(isinstance(refund, int) and not isinstance(refund, bool), "cost_invalid")
    _require(0 <= consumed <= reserved and refund == reserved - consumed, "cost_reconciliation_invalid")
    _require(record.get("actuals_proven") is True, "exact_actuals_unproven")
    _require(record.get("disposition") == "exact", "exact_disposition_invalid")
    _require(consumed <= record.get("cost_ceiling_microunits"), "consumed_above_cost_ceiling")
    _require(
        record.get("remaining_cost_microunits") == pre_reconciliation_available + refund,
        "remaining_cost_invalid",
    )
    _require(
        record.get("remaining_cost_microunits") <= record.get("cost_ceiling_microunits"), "remaining_above_cost_ceiling"
    )
    _require(mode == reservation.get("rate_mode"), "reservation_rate_mode_mismatch")
    if mode == "zero_cost_authorized":
        _require(reserved == consumed == refund == 0, "zero_cost_nonzero")
        _require(record.get("zero_cost_authority") is not None, "zero_cost_authority_missing")
        _require(record.get("input_rate") == record.get("output_rate") == 0, "zero_cost_rates_nonzero")
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
        _require(record.get("total_tokens") == input_tokens + output_tokens, "total_tokens_invalid")


def _content_hash(value: Mapping[str, Any]) -> str:
    preimage = {key: item for key, item in value.items() if key != "content_hash"}
    return hashlib.sha256(canonical_json(preimage)).hexdigest()


def validate_live_provider_receipt(
    receipt: Mapping[str, Any],
    *,
    evidence_store: Mapping[str, Mapping[str, Any]],
) -> None:
    reference = receipt["invocation_evidence"]
    evidence = evidence_store.get(reference["id"])
    _require(evidence is not None, "receipt_evidence_unresolved")
    _require(evidence.get("revision") == reference["revision"], "receipt_evidence_revision")
    _require(_content_hash(evidence) == evidence.get("content_hash") == reference["hash"], "receipt_evidence_content")
    validate_evidence_uniqueness(evidence)
    selection = evidence["actual_selection"]
    native = evidence["native_identity"]
    delivery = evidence["delivery"]
    accounting = evidence["accounting"]
    provider = selection["provider_family"]
    required_native = ("request_id", "response_id") if provider == "claude" else ("thread_id", "response_id")
    if receipt["research_eligibility"] == "eligible" or receipt["complete"] is True:
        _require(receipt["outcome"] == "terminal", "eligible_outcome")
        _require(evidence["terminal"]["lifecycle"] == "observed", "eligible_evidence_lifecycle")
        _require(
            all(isinstance(native[field], str) and native[field] for field in required_native),
            "eligible_native_identity",
        )
        _require(
            all(
                selection[field] is True
                for field in (
                    "provider_proven",
                    "model_proven",
                    "version_proven",
                    "profile_proven",
                    "credential_context_proven",
                )
            ),
            "eligible_selection_unproven",
        )
        _require(delivery["disposition"] == "proven" and bool(delivery["proof_fields"]), "eligible_delivery")
        _require(accounting["actuals_proven"] is True and accounting["rate_mode"] != "uncertain", "eligible_accounting")
        expected_selection = {
            "provider_family": selection["provider_family"],
            "model": selection["model"],
            "version": selection["version"],
            "profile": selection["profile"],
            "credential_context_id": selection["credential_context_id"],
            "all_proven": True,
        }
        _require(receipt["actual_selection"] == expected_selection, "receipt_selection_join")
        _require(receipt["delivery"] == delivery["disposition"], "receipt_delivery_join")
        for field in ("rate_mode", "actuals_proven", "input_tokens", "output_tokens", "cost_microunits"):
            receipt_field = "consumed_cost_microunits" if field == "cost_microunits" else field
            _require(receipt["accounting"][receipt_field] == accounting[field], f"receipt_accounting_{field}_join")


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
