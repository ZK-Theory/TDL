"""Independent minimum payload facts required by the approved WP6.1 design.

This oracle is intentionally literal: it is derived from W2, W8, and the
06d owner catalogue, rather than from the materializer or generated schemas.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from tests.research_system.contracts.wp6_1_schema_source import approved_fact_annex_bytes


@dataclass(frozen=True)
class PayloadExpectation:
    """Minimum facts and literal discriminator(s) for one owner-catalogue row."""

    required_fields: frozenset[str]
    selectors: tuple[tuple[str, Any], ...] = ()


def _payload(*fields: str, **selectors: Any) -> PayloadExpectation:
    # 06d's owner-row labels identify the command, but W2/W8 do not make them
    # payload facts.  They therefore do not select a schema variant.  A shared
    # payload-specific discriminant (for example ``message_type``) does.
    payload_selectors = {
        name: value for name, value in selectors.items() if name not in {"command_key", "owner_command"}
    }
    return PayloadExpectation(frozenset(fields), tuple(payload_selectors.items()))


# W2 \u00a710--19, W8 \u00a77--20, and 06d \u00a71.2--1.4.  Each catalogue key is
# deliberately listed here, even where a command schema is shared.
PAYLOAD_EXPECTATIONS: dict[str, PayloadExpectation] = {
    "scope.create": _payload(
        "new_scope_definition_id", "members", "completion_rule", "effective_at", command_key="scope.create"
    ),
    "scope.amend_revision": _payload(
        "new_scope_definition_id", "amendment_reason", "effective_at", command_key="scope.amend_revision"
    ),
    "scope.supersede": _payload(
        "replacement_scope_definition_id", "supersession_reason", command_key="scope.supersede"
    ),
    "scope.complete": _payload("scope_definition_revision", "member_dispositions", command_key="scope.complete"),
    "task.create": _payload(
        "new_task_id", "task_revision", "title", "objective", "acceptance_criteria", command_key="task.create"
    ),
    "task.amend_revision": _payload(
        "new_task_revision", "amendment_reason", "effective_at", command_key="task.amend_revision"
    ),
    "task.request_readiness": _payload("readiness_evidence_refs", command_key="task.request_readiness"),
    "task.approve_readiness": _payload(
        "readiness_evidence_refs", "approval_basis", command_key="task.approve_readiness"
    ),
    "task.block": _payload("blocker_id", "resume_condition", command_key="task.block"),
    "task.request_input": _payload("input_request_id", "requested_decision", command_key="task.request_input"),
    "task.pause": _payload("pause_reason", "resume_condition", command_key="task.pause"),
    "task.claim_start": _payload("dispatch_id", "task_id", "task_revision", "lease_id", command_key="task.claim_start"),
    "task.submit_review": _payload(
        "attempt_id", "candidate_artefact_ids", "review_ids", command_key="task.submit_review"
    ),
    "task.resume": _payload("resumption_basis", "prior_active_status", command_key="task.resume"),
    "task.accept": _payload("satisfied_review_ids", "accepted_artefact_ids", command_key="task.accept"),
    "task.reject": _payload("review_id", "rejection_reason", command_key="task.reject"),
    "task.close_partial": _payload(
        "accepted_output_ids", "unmet_obligations", "claim_restrictions", command_key="task.close_partial"
    ),
    "task.cancel": _payload("cancellation_reason", "attempt_dispositions", command_key="task.cancel"),
    "task.supersede": _payload("replacement_task_id", "replacement_task_revision", command_key="task.supersede"),
    "task.reopen_partial": _payload("reopen_reason", "new_execution_epoch", command_key="task.reopen_partial"),
    "task.reopen_rejected": _payload("reopen_reason", "new_execution_epoch", command_key="task.reopen_rejected"),
    "task.reopen_cancelled": _payload("reopen_reason", "new_execution_epoch", command_key="task.reopen_cancelled"),
    "dispatch.issue": _payload(
        "dispatch_id", "task_id", "task_revision", "target_role", "context_packet_id", command_key="dispatch.issue"
    ),
    "dispatch.deliver": _payload("dispatch_id", "delivery_channel", "delivered_at", command_key="dispatch.deliver"),
    "dispatch.acknowledge": _payload("dispatch_id", "acknowledged_at", command_key="dispatch.acknowledge"),
    "dispatch.claim": _payload("dispatch_id", "task_id", "task_revision", "lease_id", command_key="dispatch.claim"),
    "dispatch.fulfil": _payload("dispatch_id", "attempt_id", "outcome_ref", command_key="dispatch.fulfil"),
    "dispatch.expire_issued": _payload("dispatch_id", "observed_at", command_key="dispatch.expire_issued"),
    "dispatch.expire_delivered": _payload("dispatch_id", "observed_at", command_key="dispatch.expire_delivered"),
    "dispatch.expire_acknowledged": _payload("dispatch_id", "observed_at", command_key="dispatch.expire_acknowledged"),
    "dispatch.withdraw_issued": _payload("dispatch_id", "withdrawal_reason", command_key="dispatch.withdraw_issued"),
    "dispatch.withdraw_claimed": _payload("dispatch_id", "withdrawal_reason", command_key="dispatch.withdraw_claimed"),
    "lease.activate": _payload(
        "new_lease_id", "dispatch_id", "holder_actor_id", "expires_at", command_key="lease.activate"
    ),
    "lease.renew": _payload("new_expiry_at", "heartbeat_event_id", command_key="lease.renew"),
    "lease.release": _payload("release_reason", "released_at", command_key="lease.release"),
    "lease.expire": _payload("observed_at", "expiry_reason", command_key="lease.expire"),
    "lease.revoke": _payload("revocation_reason", "revoked_at", command_key="lease.revoke"),
    "attempt.create": _payload(
        "new_attempt_id", "dispatch_id", "attempt_ordinal", "execution_epoch", command_key="attempt.create"
    ),
    "attempt.claim": _payload("lease_id", "claimed_at", command_key="attempt.claim"),
    "attempt.start": _payload("process_identity_id", "started_at", command_key="attempt.start"),
    "attempt.complete": _payload(
        "completed_at", "candidate_artefact_ids", "outcome_evidence_refs", command_key="attempt.complete"
    ),
    "attempt.fail": _payload("failed_at", "failure_reason", "evidence_refs", command_key="attempt.fail"),
    "attempt.partial": _payload(
        "completed_obligations", "unmet_obligations", "claim_restrictions", command_key="attempt.partial"
    ),
    "attempt.pause": _payload("checkpoint_id", "pause_reason", command_key="attempt.pause"),
    "attempt.resume": _payload("checkpoint_id", "compatibility_verdict", command_key="attempt.resume"),
    "attempt.request_stop": _payload("stop_reason", "stop_deadline", command_key="attempt.request_stop"),
    "attempt.abandon": _payload("stop_record_id", "checkpoint_disposition", command_key="attempt.abandon"),
    "attempt.supersede": _payload("replacement_attempt_id", "supersession_reason", command_key="attempt.supersede"),
    "attempt.retry": _payload("new_attempt_id", "prior_attempt_id", "reuse_declaration", command_key="attempt.retry"),
    "checkpoint.record": _payload(
        "attempt_id",
        "task_revision",
        "compatibility_fingerprint",
        "completed_work_units",
        command_key="checkpoint.record",
    ),
    "message.publish_assignment": _payload(
        "new_message_id",
        "recipient_actor_ids",
        "typed_subject",
        command_key="message.publish_assignment",
        message_type="assignment",
    ),
    "message.publish_acknowledgement": _payload(
        "new_message_id",
        "recipient_actor_ids",
        "typed_subject",
        command_key="message.publish_acknowledgement",
        message_type="acknowledgement",
    ),
    "message.publish_progress": _payload(
        "new_message_id",
        "recipient_actor_ids",
        "typed_subject",
        command_key="message.publish_progress",
        message_type="progress",
    ),
    "message.publish_input_request": _payload(
        "new_message_id",
        "recipient_actor_ids",
        "typed_subject",
        command_key="message.publish_input_request",
        message_type="input_request",
    ),
    "message.publish_escalation": _payload(
        "new_message_id",
        "recipient_actor_ids",
        "typed_subject",
        command_key="message.publish_escalation",
        message_type="escalation",
    ),
    "message.publish_report": _payload(
        "new_message_id",
        "recipient_actor_ids",
        "typed_subject",
        command_key="message.publish_report",
        message_type="report",
    ),
    "message.publish_review_request": _payload(
        "new_message_id",
        "recipient_actor_ids",
        "typed_subject",
        command_key="message.publish_review_request",
        message_type="review_request",
    ),
    "message.publish_review_response": _payload(
        "new_message_id",
        "recipient_actor_ids",
        "typed_subject",
        command_key="message.publish_review_response",
        message_type="review_response",
    ),
    "message.publish_decision_request": _payload(
        "new_message_id",
        "recipient_actor_ids",
        "typed_subject",
        command_key="message.publish_decision_request",
        message_type="decision_request",
    ),
    "message.publish_handoff": _payload(
        "new_message_id",
        "recipient_actor_ids",
        "typed_subject",
        command_key="message.publish_handoff",
        message_type="handoff",
    ),
    "message.deliver": _payload("delivery_channel", "delivered_at", command_key="message.deliver"),
    "message.acknowledge": _payload("acknowledged_at", "acknowledgement_evidence", command_key="message.acknowledge"),
    "message.delivery_failure": _payload("failure_reason", "failed_at", command_key="message.delivery_failure"),
    "blocker.record": _payload(
        "new_blocker_id", "blocker_type", "resume_condition", "responsible_owner", command_key="blocker.record"
    ),
    "blocker.resolve": _payload("resolution_evidence", "resolved_at", command_key="blocker.resolve"),
    "artefact.register": _payload(
        "new_artefact_id", "artefact_type", "content_sha256", "attempt_id", command_key="artefact.register"
    ),
    "artefact.availability": _payload("availability", "availability_evidence", command_key="artefact.availability"),
    "artefact.regenerability": _payload(
        "regenerability", "regeneration_evidence", command_key="artefact.regenerability"
    ),
    "artefact.integrity": _payload("integrity", "integrity_evidence", command_key="artefact.integrity"),
    "artefact.structural_validation": _payload(
        "validation_record_id", "validator_identity", "verdict", command_key="artefact.structural_validation"
    ),
    "artefact.scientific_review": _payload(
        "review_id", "scientific_review_status", command_key="artefact.scientific_review"
    ),
    "artefact.use_authority": _payload("use_authority", "consumer_restrictions", command_key="artefact.use_authority"),
    "artefact.supersede": _payload(
        "replacement_artefact_id", "supersession_scope", "continuing_consumers", command_key="artefact.supersede"
    ),
    "review.request": _payload(
        "new_review_id", "subject_ids", "subject_hashes", "review_type", command_key="review.request"
    ),
    "review.assign": _payload("reviewer_actor_id", "independence_grade", command_key="review.assign"),
    "review.start": _payload("started_at", "reviewer_session_id", command_key="review.start"),
    "review.record_verdict": _payload(
        "verdict", "findings", "subject_hash", "reviewer_actor_id", command_key="review.record_verdict"
    ),
    "review.request_changes": _payload("change_requests", "review_id", command_key="review.request_changes"),
    "review.satisfy": _payload("satisfied_gate_id", "satisfaction_basis", command_key="review.satisfy"),
    "review.satisfy_after_changes": _payload(
        "satisfied_gate_id", "satisfaction_basis", command_key="review.satisfy_after_changes"
    ),
    "review.withdraw": _payload("withdrawal_reason", "withdrawn_at", command_key="review.withdraw"),
    "review.supersede": _payload("replacement_review_id", "supersession_reason", command_key="review.supersede"),
    "decision.propose": _payload(
        "new_decision_id", "question", "options", "recommendation", command_key="decision.propose"
    ),
    "decision.request_review": _payload("review_id", "review_questions", command_key="decision.request_review"),
    "decision.resolve": _payload(
        "selected_option", "decision_evidence_refs", "effective_at", command_key="decision.resolve"
    ),
    "decision.reject": _payload("rejection_reason", "rejected_at", command_key="decision.reject"),
    "decision.expire": _payload("observed_at", "expiry_reason", command_key="decision.expire"),
    "decision.supersede": _payload("replacement_decision_id", "supersession_reason", command_key="decision.supersede"),
    "rule.evaluate": _payload(
        "new_rule_evaluation_id", "rule_version", "input_hashes", "output", command_key="rule.evaluate"
    ),
    "decision.amend": _payload(
        "new_decision_revision", "amended_fields", "amendment_reason", command_key="decision.amend"
    ),
    "correction.record": _payload(
        "erroneous_record_id", "corrected_record_kind", "corrected_evidence", command_key="correction.record"
    ),
    "operator.request_resource_grant": _payload(
        "resource_id", "operational_profile", "resource_request", owner_command="request_resource_grant"
    ),
    "operator.claim_execution_lease": _payload(
        "new_lease_id", "resource_grant_id", "attempt_id", owner_command="claim_execution_lease"
    ),
    "operator.record_heartbeat": _payload(
        "lease_id", "sequence", "observed_at", "work_unit_progress", owner_command="record_heartbeat"
    ),
    "operator.request_pause": _payload("attempt_id", "pause_reason", owner_command="request_pause"),
    "operator.confirm_pause": _payload("checkpoint_id", "pause_disposition", owner_command="confirm_pause"),
    "operator.request_stop": _payload("attempt_id", "stop_reason", "stop_deadline", owner_command="request_stop"),
    "operator.confirm_stop": _payload(
        "stop_record_id", "process_disposition", "checkpoint_disposition", owner_command="confirm_stop"
    ),
    "operator.request_resume": _payload(
        "checkpoint_id", "compatibility_verdict", "new_execution_epoch", owner_command="request_resume"
    ),
    "operator.release_resources": _payload("resource_id", "release_reason", owner_command="release_resources"),
    "operator.quarantine_orphan": _payload(
        "recovery_evidence", "quarantine_reason", "consumer_restrictions", owner_command="quarantine_orphan"
    ),
    "operator.adopt_late_artefact": _payload(
        "artefact_id", "attempt_id", "review_id", owner_command="adopt_late_artefact"
    ),
    "operator.create_backup": _payload(
        "project_id", "snapshot_id", "canonical_tail_hash", owner_command="create_backup"
    ),
    "operator.verify_restore": _payload(
        "project_id", "backup_receipt_id", "restore_verdict", owner_command="verify_restore"
    ),
}


def _accepted_fact_expectations() -> dict[str, PayloadExpectation]:
    """Derive the independent minimum-fact oracle from the accepted annex."""
    repo_root = Path(__file__).resolve().parents[3]
    proposal = yaml.safe_load(approved_fact_annex_bytes(repo_root))
    rules = {
        rule["semantic_type"]: rule for rule in proposal["shared_schema_rules"] if rule["schema_kind"] == "command"
    }
    result: dict[str, PayloadExpectation] = {}
    for spec in proposal["command_payload_specs"]:
        selectors: dict[str, Any] = {}
        rule = rules.get(spec["command_type"])
        if rule and rule["variant_rule"] == "one_of_discriminator":
            candidates = [
                item
                for item in rule["variant_const_values"]
                if spec["variant_id"] == item["variant_id"] or spec["variant_id"].startswith(item["variant_id"] + "_")
            ]
            if candidates:
                chosen = max(candidates, key=lambda item: len(item["variant_id"]))
                selectors[rule["discriminator_field"]] = chosen["const_value"]
        result[spec["row_key"]] = PayloadExpectation(frozenset(spec["required_field_names"]), tuple(selectors.items()))
    return result


PAYLOAD_EXPECTATIONS = _accepted_fact_expectations()
