"""Independent source-fact oracle for the proposed WP6.1 fact annex.

The constants in this module are authored from the immutable W2, W8, and 06d
documents.  The module deliberately has no dependency on the WP6.1 resolver,
materializer, validator, generated schemas, or proposal companion schema.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SOURCE_REVISION = "fe5f1d40bc8f05f061317c677b5891cea0711249"
SOURCE_DOCUMENTS = {
    "W2": (
        "docs/plans/agentic-research-system/design/02-task-event-and-artifact-schema.md",
        "7e09a9c49605663bb50163840fff3ae4c8212748",
        "dd5f45ec91cb4c10f0e8d1d99341ad16745bec21f58400b6643285224870f9c6",
    ),
    "W8": (
        "docs/plans/agentic-research-system/design/08-resource-checkpoint-and-operations.md",
        "d26f24b9a6670b095d307fe531a7bb9b31c55311",
        "84c80a8b499394fed65ed0d4e7fe1f4f9a85a8ccc23b299c85198e5d60e79a58",
    ),
    "06d": (
        "docs/plans/agentic-research-system/implementation/06d-wp6-1-owner-source-catalogue.md",
        "5e2eb60ca4419d1529506de6859fb027cff518af",
        "96932fd752362eddb6da2da77bc0b56ccb8e83ced58e93c3b139e3248acb08f7",
    ),
}

P0_MAXIMUM = 9_007_199_254_740_991
EXPECTED_CARDINALITIES = {
    "owner_rows": 104,
    "command_bindings": 104,
    "event_bindings": 106,
    "unique_command_types": 87,
    "unique_event_types": 86,
    "generated_schema_identities": 173,
    "command_root_fields": 17,
    "event_root_fields": 27,
    "families": 14,
}

COMMAND_ROOT = (
    ("command_id", "type/command_id", False),
    ("command_type", "type/nonempty_string", False),
    ("schema_id", "type/nonempty_string", False),
    ("schema_version", "type/semver", False),
    ("project_id", "type/project_id", False),
    ("submitted_at", "type/utc_z", False),
    ("actor_id", "type/actor_id", False),
    ("on_behalf_of_actor_id", "type/actor_id", True),
    ("authority_grant_id", "type/authority_grant_id", False),
    ("target_stream_id", "type/any_id", False),
    ("expected_stream_version", "type/nonnegative_integer", False),
    ("idempotency_key", "type/nonempty_string", False),
    ("correlation_id", "type/nonempty_string", False),
    ("causation_id", "type/any_id", True),
    ("reason", "type/nonempty_string", False),
    ("evidence_refs", "type/string_list", False),
    ("payload", "type/payload_object", False),
)

EVENT_ROOT = (
    ("event_id", "type/event_id", False),
    ("event_type", "type/nonempty_string", False),
    ("schema_id", "type/nonempty_string", False),
    ("schema_version", "type/semver", False),
    ("project_id", "type/project_id", False),
    ("stream_id", "type/any_id", False),
    ("stream_version", "type/positive_integer", False),
    ("global_position", "type/positive_integer", False),
    ("transaction_id", "type/transaction_id", False),
    ("transaction_index", "type/positive_integer", False),
    ("transaction_count", "type/positive_integer", False),
    ("command_id", "type/command_id", False),
    ("command_type", "type/nonempty_string", False),
    ("command_schema_id", "type/nonempty_string", False),
    ("command_schema_version", "type/semver", False),
    ("command_schema_sha256", "type/sha256", False),
    ("idempotency_key", "type/nonempty_string", False),
    ("command_payload_hash", "type/sha256", False),
    ("correlation_id", "type/nonempty_string", False),
    ("causation_id", "type/any_id", True),
    ("actor_id", "type/actor_id", False),
    ("authority_grant_id", "type/authority_grant_id", False),
    ("occurred_at", "type/utc_z", True),
    ("recorded_at", "type/utc_z", False),
    ("payload", "type/payload_object", False),
    ("previous_event_hash", "type/sha256", False),
    ("event_hash", "type/sha256", False),
)

FAMILY_IDS = (
    "family/scope",
    "family/task",
    "family/dispatch",
    "family/lease",
    "family/attempt_checkpoint",
    "family/message",
    "family/blocker",
    "family/artefact",
    "family/review",
    "family/decision",
    "family/rule_evaluation",
    "family/correction",
    "family/resource_operation",
    "family/backup_recovery",
)

SHARED_RULES = {
    ("command", "ClaimDispatch"): ("single_normalized_fact", None, ("task_claim_start", "dispatch_claim"), ()),
    ("command", "ReopenTask"): (
        "one_of_discriminator",
        "prior_terminal_status",
        ("task_reopen_partial", "task_reopen_rejected", "task_reopen_cancelled"),
        (
            ("task_reopen_partial", "partial"),
            ("task_reopen_rejected", "rejected"),
            ("task_reopen_cancelled", "cancelled"),
        ),
    ),
    ("command", "ExpireDispatch"): (
        "one_of_discriminator",
        "observed_prior_state",
        ("dispatch_expire_issued", "dispatch_expire_delivered", "dispatch_expire_acknowledged"),
        (
            ("dispatch_expire_issued", "issued"),
            ("dispatch_expire_delivered", "delivered"),
            ("dispatch_expire_acknowledged", "acknowledged"),
        ),
    ),
    ("command", "WithdrawDispatch"): (
        "one_of_discriminator",
        "observed_prior_state",
        ("dispatch_withdraw_issued", "dispatch_withdraw_claimed"),
        (("dispatch_withdraw_issued", "issued"), ("dispatch_withdraw_claimed", "claimed")),
    ),
    ("command", "ClaimExecutionLease"): (
        "single_normalized_fact",
        None,
        ("lease_activate", "operator_claim_execution_lease"),
        (),
    ),
    ("command", "PublishMessage"): (
        "one_of_discriminator",
        "message_type",
        (
            "message_publish_assignment",
            "message_publish_acknowledgement",
            "message_publish_progress",
            "message_publish_input_request",
            "message_publish_escalation",
            "message_publish_report",
            "message_publish_review_request",
            "message_publish_review_response",
            "message_publish_decision_request",
            "message_publish_handoff",
        ),
        (
            ("message_publish_assignment", "assignment"),
            ("message_publish_acknowledgement", "acknowledgement"),
            ("message_publish_progress", "progress"),
            ("message_publish_input_request", "input_request"),
            ("message_publish_escalation", "escalation"),
            ("message_publish_report", "report"),
            ("message_publish_review_request", "review_request"),
            ("message_publish_review_response", "review_response"),
            ("message_publish_decision_request", "decision_request"),
            ("message_publish_handoff", "handoff"),
        ),
    ),
    ("command", "SatisfyReview"): (
        "one_of_discriminator",
        "prior_review_state",
        ("review_satisfy", "review_satisfy_after_changes"),
        (("review_satisfy", "verdict_recorded"), ("review_satisfy_after_changes", "changes_requested")),
    ),
    ("event", "DispatchClaimed"): ("single_normalized_fact", None, ("task_claim_start", "dispatch_claim"), ()),
    ("event", "TaskClaimStarted"): ("single_normalized_fact", None, ("task_claim_start", "dispatch_claim"), ()),
    ("event", "PartialOutcomeRecorded"): (
        "one_of_discriminator",
        "subject_kind",
        ("task_close_partial", "attempt_partial"),
        (("task_close_partial", "task"), ("attempt_partial", "attempt")),
    ),
    ("event", "TaskReopened"): (
        "one_of_discriminator",
        "prior_terminal_status",
        ("task_reopen_partial", "task_reopen_rejected", "task_reopen_cancelled"),
        (
            ("task_reopen_partial", "partial"),
            ("task_reopen_rejected", "rejected"),
            ("task_reopen_cancelled", "cancelled"),
        ),
    ),
    ("event", "DispatchExpired"): (
        "one_of_discriminator",
        "observed_prior_state",
        ("dispatch_expire_issued", "dispatch_expire_delivered", "dispatch_expire_acknowledged"),
        (
            ("dispatch_expire_issued", "issued"),
            ("dispatch_expire_delivered", "delivered"),
            ("dispatch_expire_acknowledged", "acknowledged"),
        ),
    ),
    ("event", "DispatchWithdrawn"): (
        "one_of_discriminator",
        "observed_prior_state",
        ("dispatch_withdraw_issued", "dispatch_withdraw_claimed"),
        (("dispatch_withdraw_issued", "issued"), ("dispatch_withdraw_claimed", "claimed")),
    ),
    ("event", "LeaseGranted"): (
        "single_normalized_fact",
        None,
        ("lease_activate", "operator_claim_execution_lease"),
        (),
    ),
    ("event", "AttemptCreated"): (
        "one_of_discriminator",
        "creation_kind",
        ("attempt_create", "attempt_retry"),
        (("attempt_create", "initial"), ("attempt_retry", "retry")),
    ),
    ("event", "MessagePublished"): (
        "one_of_discriminator",
        "message_type",
        (
            "message_publish_assignment",
            "message_publish_acknowledgement",
            "message_publish_progress",
            "message_publish_input_request",
            "message_publish_escalation",
            "message_publish_report",
            "message_publish_review_request",
            "message_publish_review_response",
            "message_publish_decision_request",
            "message_publish_handoff",
        ),
        (
            ("message_publish_assignment", "assignment"),
            ("message_publish_acknowledgement", "acknowledgement"),
            ("message_publish_progress", "progress"),
            ("message_publish_input_request", "input_request"),
            ("message_publish_escalation", "escalation"),
            ("message_publish_report", "report"),
            ("message_publish_review_request", "review_request"),
            ("message_publish_review_response", "review_response"),
            ("message_publish_decision_request", "decision_request"),
            ("message_publish_handoff", "handoff"),
        ),
    ),
    ("event", "ReviewSatisfied"): (
        "one_of_discriminator",
        "prior_review_state",
        ("review_satisfy", "review_satisfy_after_changes"),
        (("review_satisfy", "verdict_recorded"), ("review_satisfy_after_changes", "changes_requested")),
    ),
}

SOURCE_CLOSED_ENUMS = {
    "enum/task_status": (
        "draft",
        "readiness_pending",
        "ready",
        "in_progress",
        "review_pending",
        "blocked",
        "input_required",
        "paused",
        "accepted",
        "rejected",
        "partial",
        "cancelled",
        "superseded",
    ),
    "enum/member_disposition": (
        "accepted",
        "partial_accepted",
        "deferred",
        "superseded",
        "removed_by_amendment",
        "cancelled",
        "rejected",
    ),
    "enum/concurrency_mode": ("exclusive", "comparative", "redundant"),
    "enum/message_type": (
        "assignment",
        "acknowledgement",
        "progress",
        "input_request",
        "escalation",
        "report",
        "review_request",
        "review_response",
        "decision_request",
        "handoff",
    ),
    "enum/review_type": (
        "software",
        "provenance",
        "mathematical",
        "statistical",
        "topological",
        "representation",
        "claim",
        "operations",
        "adapter_parity",
        "migration",
    ),
    "enum/review_verdict": (
        "approve",
        "approve_with_conditions",
        "changes_requested",
        "reject",
        "unable_to_verify",
        "withdrawn",
    ),
    "enum/review_condition_gate_disposition": ("non_blocking", "blocking"),
    "enum/decision_kind": (
        "design_lock",
        "preregistration_amendment",
        "methodological_exception",
        "runtime_guardrail_override",
        "result_interpretation",
        "claim_promotion",
        "scope_amendment",
        "migration_authority",
        "policy_exception",
        "task_reopen",
    ),
    "enum/availability": ("available", "missing", "inaccessible", "quarantined"),
    "enum/regenerability": ("not_declared", "regenerable_verified", "non_regenerable", "unknown"),
    "enum/integrity": ("unverified", "verified", "failed"),
    "enum/structural_validation": ("not_run", "passed", "failed", "partial", "not_applicable"),
    "enum/scientific_review": ("not_required", "pending", "approved", "rejected", "unable_to_verify"),
    "enum/use_authority": ("candidate", "accepted_for_scope", "rejected", "superseded", "restricted"),
    "enum/profile_evidence_disposition": ("required", "not_applicable"),
    "enum/trivial_terminal_receipt_kind": ("provider_receipt", "operator_receipt"),
    "enum/lease_scope": ("command_scoped",),
    "enum/not_applicable_profile_evidence": ("not_applicable",),
    "enum/trivial_request_record_type": ("resource_request",),
    "enum/trivial_grant_record_type": ("resource_grant",),
    "enum/trivial_ceilings_requirement": ("explicit_resource_ceilings",),
    "enum/trivial_lease_release": ("releases_lease",),
    "enum/operational_profile": ("trivial", "bounded", "long_running"),
    "enum/checkpoint_compatibility": ("compatible", "incompatible", "unable_to_determine"),
    "enum/profile_applicability": ("required", "not_applicable"),
    "enum/corrected_record_kind": (
        "scope_definition",
        "task",
        "dispatch",
        "lease",
        "attempt",
        "checkpoint",
        "message",
        "blocker",
        "artefact",
        "review",
        "decision",
        "rule_evaluation",
        "resource",
        "operation",
        "backup",
    ),
}

UUID7_TAIL = r"[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
SOURCE_LITERAL_ID_PREFIXES = {
    "type/project_id": "prj",
    "type/task_id": "tsk",
    "type/dispatch_id": "dsp",
    "type/attempt_id": "att",
    "type/artefact_id": "art",
    "type/actor_id": "act",
    "type/authority_grant_id": "agr",
    "type/command_id": "cmd",
    "type/event_id": "evt",
    "type/transaction_id": "txb",
    "type/object_id": "obj",
    "type/lease_id": "els",
    "type/message_id": "msg",
    "type/blocker_id": "blk",
    "type/validation_id": "val",
    "type/review_id": "rev",
    "type/decision_id": "dec",
    "type/context_id": "ctx",
    "type/policy_version_id": "pol",
    "type/resource_request_id": "rsq",
    "type/resource_grant_id": "rgr",
    "type/resource_conflict_id": "rcf",
    "type/heartbeat_id": "hbt",
    "type/process_identity_id": "pid",
    "type/checkpoint_manifest_id": "cpm",
    "type/stop_record_id": "stp",
    "type/resume_decision_id": "rsd",
    "type/recovery_evidence_id": "rcv",
    "type/backup_receipt_id": "bkr",
    "type/operator_command_id": "opc",
    "type/operator_receipt_id": "opr",
}

COMPLETE_SOURCE_GROUP_FIELDS = {
    "object/task_definition": frozenset(
        {
            "task_id",
            "revision",
            "aliases",
            "project_id",
            "portfolio_refs",
            "scope_refs",
            "title",
            "objective",
            "bounded_scope",
            "non_goals",
            "dependencies",
            "governing_design_refs",
            "risk_tier_request",
            "assurance_lanes",
            "machine_checks",
            "human_questions",
            "independent_review_requirements",
            "expected_artefact_types",
            "acceptance_criteria",
            "partial_criteria",
            "prohibited_shortcuts",
            "root_binding_requirements",
            "concurrency_mode",
            "resource_policy_ref",
            "checkpoint_expectation",
            "dispatch_authority",
            "amend_authority",
            "cancel_authority",
            "review_authority",
            "accept_authority",
            "reopen_authority",
            "supersede_authority",
            "creator_actor_id",
            "created_at",
            "source_import_refs",
            "content_sha256",
        }
    ),
    "object/dispatch_definition": frozenset(
        {
            "dispatch_id",
            "task_id",
            "task_revision",
            "target_role",
            "target_profile",
            "target_actor_id",
            "model_eval_profile_ref",
            "context_packet_id",
            "policy_version",
            "assurance_plan_version",
            "root_bindings",
            "branch_identity",
            "worktree_identity",
            "expected_commit",
            "capabilities",
            "permissions",
            "resource_request_id",
            "output_namespace",
            "delivery_deadline",
            "claim_deadline",
            "concurrency_mode",
            "stop_rules",
            "partial_rules",
            "escalation_rules",
        }
    ),
    "object/root_binding": frozenset(
        {
            "root_kind",
            "canonical_uri",
            "workspace_identity",
            "access_mode",
            "expected_branch",
            "expected_commit",
            "provenance_authority",
        }
    ),
    "object/artefact_manifest": frozenset(
        {
            "artefact_id",
            "aliases",
            "artefact_type",
            "artefact_schema_id",
            "artefact_schema_version",
            "task_id",
            "dispatch_id",
            "attempt_id",
            "producer_actor_id",
            "producer_profile",
            "context_packet_id",
            "created_at",
            "code_commit",
            "branch_identity",
            "worktree_identity",
            "environment_fingerprint",
            "root_id",
            "relative_path",
            "size_bytes",
            "media_type",
            "content_sha256",
            "observed_at",
            "availability_check_evidence_refs",
            "input_dependencies",
            "research_provenance",
            "validation",
            "authority",
            "operations",
        }
    ),
    "object/resource_request": frozenset(
        {
            "resource_request_id",
            "task_id",
            "dispatch_id",
            "attempt_id",
            "route_id",
            "operation_class",
            "provider_requirements",
            "runtime_requirements",
            "operational_profile",
            "operational_profile_policy_id",
            "operational_profile_revision",
            "requesting_actor_id",
            "requesting_profile",
            "requesting_authority_grant_id",
            "expected_control_store_position",
            "requested_host_pool",
            "root_bindings",
            "resource_ceilings",
            "network_constraints",
            "external_write_constraints",
            "sensitivity_constraints",
            "exclusive_resource_keys",
            "shared_resource_keys",
            "compatibility_keys",
            "runtime_distribution",
            "deadline",
            "checkpoint_interval_seconds",
            "benchmark_evidence_refs",
            "projection_evidence_refs",
            "stop_rules",
            "pause_rules",
            "partial_rules",
            "escalation_rules",
            "release_obligations",
            "cleanup_obligations",
            "trivial_profile_evidence",
            "bounded_profile_evidence",
            "long_running_profile_evidence",
        }
    ),
}

RESOURCE_REQUEST_PROFILE_FIELD_FACTS = {
    "object/resource_request": (
        (
            "operational_profile",
            "enum/operational_profile",
            False,
            "discriminator:object_variant_rule/resource_request_operational_profile",
        ),
        ("operational_profile_policy_id", "type/policy_version_id", False, None),
        ("operational_profile_revision", "type/semver", False, None),
        (
            "trivial_profile_evidence",
            "object/trivial_profile_evidence",
            False,
            "required_iff:operational_profile=trivial;forbidden_otherwise",
        ),
        (
            "bounded_profile_evidence",
            "object/bounded_profile_evidence",
            False,
            "required_iff:operational_profile=bounded;forbidden_otherwise",
        ),
        (
            "long_running_profile_evidence",
            "object/long_running_profile_evidence",
            False,
            "required_iff:operational_profile=long_running;forbidden_otherwise",
        ),
    ),
    "object/profile_evidence_disposition": (
        ("disposition", "enum/profile_evidence_disposition", False, "policy_selects:required_or_not_applicable"),
        ("policy_id", "type/policy_version_id", False, "required_for:profile_evidence_disposition"),
        ("rationale", "type/nonempty_string", False, "required_for:profile_evidence_disposition"),
        (
            "applicability_evidence_refs",
            "type/nonempty_evidence_ref_list",
            False,
            "required_for:profile_evidence_disposition",
        ),
    ),
    "object/trivial_not_applicable_evidence": (
        ("disposition", "enum/not_applicable_profile_evidence", False, "const:not_applicable"),
        ("policy_id", "type/policy_version_id", False, "required_for:not_applicable"),
        ("rationale", "type/nonempty_string", False, "required_for:not_applicable"),
        ("applicability_evidence_refs", "type/nonempty_evidence_ref_list", False, "required_for:not_applicable"),
    ),
    "object/trivial_provider_command_process": (
        ("provider_command_id", "type/any_id", False, "allowed_only:operational_profile=trivial"),
        (
            "process_identity_disposition",
            "enum/not_applicable_profile_evidence",
            False,
            "const:not_applicable;allowed_only:operational_profile=trivial",
        ),
        (
            "process_identity_not_applicable_rationale",
            "type/nonempty_string",
            False,
            "required_for:trivial_provider_command_process",
        ),
    ),
    "object/trivial_profile_evidence": (
        ("request_record_type", "enum/trivial_request_record_type", False, "required_if:operational_profile=trivial"),
        ("grant_record_type", "enum/trivial_grant_record_type", False, "required_if:operational_profile=trivial"),
        ("lease_scope", "enum/lease_scope", False, "required_if:operational_profile=trivial"),
        (
            "resource_ceilings_requirement",
            "enum/trivial_ceilings_requirement",
            False,
            "required_if:operational_profile=trivial",
        ),
        (
            "terminal_receipt_kind",
            "enum/trivial_terminal_receipt_kind",
            False,
            "required_if:operational_profile=trivial",
        ),
        (
            "terminal_receipt_lease_release",
            "enum/trivial_lease_release",
            False,
            "required_if:operational_profile=trivial",
        ),
        (
            "terminal_receipt_evidence_refs",
            "type/nonempty_evidence_ref_list",
            False,
            "required_if:operational_profile=trivial",
        ),
        ("benchmark", "object/trivial_not_applicable_evidence", False, "not_applicable_if:operational_profile=trivial"),
        (
            "checkpoint",
            "object/trivial_not_applicable_evidence",
            False,
            "not_applicable_if:operational_profile=trivial",
        ),
        (
            "periodic_heartbeat",
            "object/trivial_not_applicable_evidence",
            False,
            "not_applicable_if:operational_profile=trivial",
        ),
        ("recovery", "object/trivial_not_applicable_evidence", False, "not_applicable_if:operational_profile=trivial"),
        (
            "provider_command_process",
            "object/trivial_provider_command_process",
            False,
            "allowed_only:operational_profile=trivial",
        ),
    ),
    "object/bounded_profile_evidence": (
        ("heartbeat", "object/profile_evidence_disposition", False, "policy_selected_if:operational_profile=bounded"),
        ("output_tail", "object/profile_evidence_disposition", False, "policy_selected_if:operational_profile=bounded"),
        ("stop", "object/profile_evidence_disposition", False, "policy_selected_if:operational_profile=bounded"),
        ("checkpoint", "object/profile_evidence_disposition", False, "policy_selected_if:operational_profile=bounded"),
    ),
    "object/long_running_profile_evidence": (
        ("benchmark", "object/profile_evidence_disposition", False, "applicable_if:operational_profile=long_running"),
        ("heartbeat", "object/profile_evidence_disposition", False, "applicable_if:operational_profile=long_running"),
        ("process", "object/profile_evidence_disposition", False, "applicable_if:operational_profile=long_running"),
        ("checkpoint", "object/profile_evidence_disposition", False, "applicable_if:operational_profile=long_running"),
        (
            "stop_recovery",
            "object/profile_evidence_disposition",
            False,
            "applicable_if:operational_profile=long_running",
        ),
        ("backup", "object/profile_evidence_disposition", False, "applicable_if:operational_profile=long_running"),
    ),
}

RESOURCE_PROFILE_VARIANT_RULE = {
    "rule_id": "object_variant_rule/resource_request_operational_profile",
    "object_id": "object/resource_request",
    "discriminator_field": "operational_profile",
    "no_fallback": True,
    "source_semantics": "source_literal",
    "representation_choice": "conservative_proposal",
    "source_citation": "W8 §11.1",
    "branches": [
        {
            "discriminator_const": "trivial",
            "required_fields": ["trivial_profile_evidence"],
            "forbidden_fields": ["bounded_profile_evidence", "long_running_profile_evidence"],
        },
        {
            "discriminator_const": "bounded",
            "required_fields": ["bounded_profile_evidence"],
            "forbidden_fields": ["trivial_profile_evidence", "long_running_profile_evidence"],
        },
        {
            "discriminator_const": "long_running",
            "required_fields": ["long_running_profile_evidence"],
            "forbidden_fields": ["trivial_profile_evidence", "bounded_profile_evidence"],
        },
    ],
}

REVIEW_CONDITION_FIELD_FACTS = {
    "family/review": (
        ("verdict", "enum/review_verdict", False, "controls:review_gate_condition_rule/approve_with_conditions"),
        (
            "conditions",
            "type/review_gate_condition_list",
            False,
            "all_items:non_blocking_with_non_null_owner_policy_and_evidence_when_gate_satisfied",
        ),
        (
            "satisfaction_gate",
            "type/nonempty_string",
            False,
            "satisfied_iff:every_condition_non_blocking_with_non_null_owner_policy_and_evidence",
        ),
    ),
    "object/review_gate_condition": (
        ("condition_text", "type/nonempty_string", False, "required_for:approve_with_conditions"),
        (
            "gate_disposition",
            "enum/review_condition_gate_disposition",
            False,
            "must_equal:non_blocking_when_gate_satisfied",
        ),
        (
            "owner_actor_id",
            "type/actor_id",
            True,
            "non_null_when:approve_with_conditions_satisfies_gate",
        ),
        ("policy_id", "type/policy_version_id", False, "required_when:approve_with_conditions_satisfies_gate"),
        (
            "evidence_refs",
            "type/nonempty_evidence_ref_list",
            False,
            "required_when:approve_with_conditions_satisfies_gate",
        ),
    ),
}

VERDICT_GATE_RESULTS = {
    "approve": "satisfied",
    "approve_with_conditions": (
        "satisfied_if_nonempty_all_conditions_non_blocking_with_non_null_typed_actor_owner_policy_and_nonempty_evidence"
    ),
    "changes_requested": "unsatisfied",
    "reject": "unsatisfied",
    "unable_to_verify": "unsatisfied",
    "withdrawn": "unsatisfied",
}

REVIEW_GATE_CONDITION_RULE = {
    "rule_id": "review_gate_condition_rule/total_verdict_gate_relation",
    "family_id": "family/review",
    "verdict_field": "verdict",
    "condition_field": "conditions",
    "gate_field": "satisfaction_gate",
    "gate_satisfaction_rule": "closed_total_verdict_map",
    "verdict_gate_results": VERDICT_GATE_RESULTS,
    "approve_with_conditions_min_items": 1,
    "condition_item_rule": "every_condition_non_blocking_with_non_null_typed_actor_owner_policy_and_nonempty_evidence",
    "task_state_effect": "no_direct_task_state_change",
    "source_semantics": "source_literal",
    "representation_choice": "conservative_proposal",
    "source_citation": "W2 §§17.3-17.4",
}

REUSABLE_OBJECT_FIELD_RULE = {
    "all_listed_reusable_object_fields_required": True,
    "variant_controlled_field_exception": (
        "fields_controlled_by_same_object_variant_rule_are_exempt_from_global_requiredness"
    ),
    "variant_controlled_field_derivation": "union_of_all_branch_required_fields_and_forbidden_fields",
    "requiredness_precedence": (
        "variant_branch_presence_rules_override_global_requiredness_for_controlled_fields_only"
    ),
    "non_variant_listed_fields_required": True,
    "selected_variant_required_fields_non_null": True,
    "selected_variant_forbidden_fields_absent": True,
    "selected_nested_object_fields_required": True,
    "nullable_field_semantics": "required_key_value_may_be_null_only_when_nullable_true",
    "nonempty_evidence_type_ref": "type/nonempty_evidence_ref_list",
    "decision_basis": "conservative_proposal",
    "source_citation": "W2/W8 listed typed facts and R6 same-object variant requiredness composition",
}

# Independently transcribed from immutable W2/W8/06d facts and the reviewed
# conservative target selections.  This ledger must never be generated from
# the proposal, resolver, materializer, generated schemas, or companion schema.
SOURCE_FACT_BINDING_TSV = """\
task_identity_task_id	W2	10.1	Identity: task_id	object/task_definition.task_id	source_literal
task_identity_revision	W2	10.1	Identity: revision	object/task_definition.revision	conservative_proposal
task_identity_aliases	W2	10.1	Identity: aliases	object/task_definition.aliases	conservative_proposal
task_identity_project	W2	10.1	Identity: project	object/task_definition.project_id	source_literal
task_identity_portfolio_refs	W2	10.1	Identity: portfolio references	object/task_definition.portfolio_refs	conservative_proposal
task_identity_scope_refs	W2	10.1	Identity: scope references	object/task_definition.scope_refs	conservative_proposal
task_purpose_title	W2	10.1	Purpose: title	object/task_definition.title	conservative_proposal
task_purpose_objective	W2	10.1	Purpose: objective	object/task_definition.objective	source_literal
task_purpose_bounded_scope	W2	10.1	Purpose: bounded scope	object/task_definition.bounded_scope	conservative_proposal
task_purpose_non_goals	W2	10.1	Purpose: non-goals	object/task_definition.non_goals	conservative_proposal
task_dependency_task_ids	W2	10.1	Dependency: required Task IDs	object/dependency.subject_id{subject_kind=task}	conservative_proposal
task_dependency_decision_ids	W2	10.1	Dependency: required decision IDs	object/dependency.subject_id{subject_kind=decision}	conservative_proposal
task_dependency_artefact_ids	W2	10.1	Dependency: required artefact IDs	object/dependency.subject_id{subject_kind=artefact}	conservative_proposal
task_dependency_predicates	W2	10.1	Dependency: satisfaction predicates	object/dependency.satisfaction_predicate	conservative_proposal
task_design_governing_refs	W2	10.1	Research design: governing preregistration/design/contract refs	object/task_definition.governing_design_refs	conservative_proposal
task_design_risk_tier	W2	10.1	Research design: risk tier request	object/task_definition.risk_tier_request	conservative_proposal
task_assurance_lanes	W2	10.1	Assurance: touched lanes	object/task_definition.assurance_lanes	conservative_proposal
task_assurance_machine_checks	W2	10.1	Assurance: machine checks	object/task_definition.machine_checks	conservative_proposal
task_assurance_human_questions	W2	10.1	Assurance: human questions	object/task_definition.human_questions	conservative_proposal
task_assurance_independent_review	W2	10.1	Assurance: independent-review requirements	object/task_definition.independent_review_requirements	conservative_proposal
task_delivery_artefacts	W2	10.1	Delivery: expected artefact types	object/task_definition.expected_artefact_types	conservative_proposal
task_delivery_acceptance	W2	10.1	Delivery: acceptance criteria	object/task_definition.acceptance_criteria	conservative_proposal
task_delivery_partial	W2	10.1	Delivery: Partial criteria	object/task_definition.partial_criteria	conservative_proposal
task_delivery_shortcuts	W2	10.1	Delivery: prohibited shortcuts	object/task_definition.prohibited_shortcuts	conservative_proposal
task_execution_roots	W2	10.1	Execution: root-binding requirements	object/task_definition.root_binding_requirements	conservative_proposal
task_execution_concurrency	W2	10.1	Execution: concurrency policy	object/task_definition.concurrency_mode	source_literal
task_execution_resource_policy	W2	10.1	Execution: resource-policy reference	object/task_definition.resource_policy_ref	conservative_proposal
task_execution_checkpoint	W2	10.1	Execution: checkpoint expectation	object/task_definition.checkpoint_expectation	conservative_proposal
task_authority_actions	W2	10.1	Authority: dispatch/amend/cancel/review/accept/reopen/supersede	object/task_definition.{dispatch_authority,amend_authority,cancel_authority,review_authority,accept_authority,reopen_authority,supersede_authority}	conservative_proposal
task_provenance_creator	W2	10.1	Provenance: creator	object/task_definition.creator_actor_id	conservative_proposal
task_provenance_time	W2	10.1	Provenance: creation time	object/task_definition.created_at	conservative_proposal
task_provenance_imports	W2	10.1	Provenance: source/import refs	object/task_definition.source_import_refs	conservative_proposal
task_provenance_hash	W2	10.1	Provenance: content hash	object/task_definition.content_sha256	source_literal
dispatch_task_revision	W2	12.1	Task revision	object/dispatch_definition.task_revision	source_literal
dispatch_target_role	W2	12.1	target role	object/dispatch_definition.target_role	conservative_proposal
dispatch_target_profile	W2	12.1	target profile	object/dispatch_definition.target_profile	conservative_proposal
dispatch_target_actor	W2	12.1	optional target actor	object/dispatch_definition.target_actor_id	conservative_proposal
dispatch_model_eval	W2	12.1	required model/eval profile reference	object/dispatch_definition.model_eval_profile_ref	conservative_proposal
dispatch_context	W2	12.1	context packet ID	object/dispatch_definition.context_packet_id	source_literal
dispatch_policy	W2	12.1	policy version	object/dispatch_definition.policy_version	source_literal
dispatch_assurance	W2	12.1	assurance-plan version	object/dispatch_definition.assurance_plan_version	conservative_proposal
dispatch_roots	W2	12.1	explicit roots	object/dispatch_definition.root_bindings	conservative_proposal
dispatch_branch	W2	12.1	branch identity	object/dispatch_definition.branch_identity	conservative_proposal
dispatch_worktree	W2	12.1	worktree identity	object/dispatch_definition.worktree_identity	conservative_proposal
dispatch_commit	W2	12.1	expected commit	object/dispatch_definition.expected_commit	conservative_proposal
dispatch_capabilities	W2	12.1	capability set	object/dispatch_definition.capabilities	conservative_proposal
dispatch_permissions	W2	12.1	permission set	object/dispatch_definition.permissions	conservative_proposal
dispatch_resource_request	W2	12.1	ResourceRequest reference	object/dispatch_definition.resource_request_id	source_literal
dispatch_namespace	W2	12.1	output namespace	object/dispatch_definition.output_namespace	conservative_proposal
dispatch_delivery_deadline	W2	12.1	delivery deadline	object/dispatch_definition.delivery_deadline	source_literal
dispatch_claim_deadline	W2	12.1	claim deadline	object/dispatch_definition.claim_deadline	source_literal
dispatch_concurrency	W2	12.1	concurrency mode	object/dispatch_definition.concurrency_mode	source_literal
dispatch_stop_partial_escalation	W2	12.1	stop/Partial/escalation rules	object/dispatch_definition.{stop_rules,partial_rules,escalation_rules}	conservative_proposal
root_kind	W2	12.1	root kind	object/root_binding.root_kind	conservative_proposal
root_canonical_uri	W2	12.1	canonical URI/path	object/root_binding.canonical_uri	conservative_proposal
root_workspace	W2	12.1	workspace identity	object/root_binding.workspace_identity	conservative_proposal
root_access	W2	12.1	access mode	object/root_binding.access_mode	conservative_proposal
root_expected_branch_commit	W2	12.1	applicable expected branch/commit	object/root_binding.{expected_branch,expected_commit}	conservative_proposal
root_provenance_authority	W2	12.1	provenance authority	object/root_binding.provenance_authority	conservative_proposal
review_verdict	W2	17.3	verdict	family/review.verdict	source_literal
review_findings	W2	17.3	findings	family/review.findings	conservative_proposal
review_evidence	W2	17.3	evidence	family/review.required_evidence_refs	conservative_proposal
review_limitations	W2	17.3	limitations	family/review.limitations	conservative_proposal
review_conditions	W2	17.3	conditions	family/review.conditions	source_literal
review_condition_text	W2	17.3	condition text	object/review_gate_condition.condition_text	source_literal
review_condition_gate_disposition	W2	17.3	closed non_blocking/blocking JSON representation of acceptance-policy condition classification	object/review_gate_condition.gate_disposition	conservative_proposal
review_condition_owner_actor	W2	17.3	condition owner recorded for gate-satisfying conditional approval	object/review_gate_condition.owner_actor_id	conservative_proposal
review_condition_policy	W2	17.3	acceptance policy identity	object/review_gate_condition.policy_id	conservative_proposal
review_condition_evidence	W2	17.3	condition evidence	object/review_gate_condition.evidence_refs	conservative_proposal
review_condition_gate_rule	W2	17.3	approve_with_conditions satisfies a gate only for all non-blocking owned conditions	family/review.conditions	source_literal
review_verdict_no_direct_task_state	W2	17.4	review verdict never directly changes Task state	family/review.verdict	source_literal
review_reviewer_metadata	W2	17.3	reviewer actor/profile/session/model metadata	family/review.{reviewer_actor_id,reviewer_profile,reviewer_session,reviewer_model_metadata}	conservative_proposal
review_context_manifest	W2	17.3	context-manifest ID/hash	family/review.{context_manifest_id,context_manifest_sha256}	conservative_proposal
review_subject_hash	W2	17.3	subject_hash	family/review.unchanged_subject_sha256	source_literal
review_producing_attempt	W2	17.3	producing_attempt_relationship	family/review.producing_attempt_id	conservative_proposal
review_trace_visibility	W2	17.3	trace_visibility_evidence	family/review.trace_visibility_evidence_refs	conservative_proposal
review_independence_grade	W2	17.3	independence_grade	family/review.computed_independence_grade	conservative_proposal
artefact_identity_id	W2	16.1	Identity: artefact ID	object/artefact_manifest.artefact_id	source_literal
artefact_identity_aliases	W2	16.1	Identity: aliases	object/artefact_manifest.aliases	conservative_proposal
artefact_identity_type	W2	16.1	Identity: type	object/artefact_manifest.artefact_type	conservative_proposal
artefact_identity_schema_id	W2	16.1	Identity: schema ID	object/artefact_manifest.artefact_schema_id	conservative_proposal
artefact_identity_version	W2	16.1	Identity: version	object/artefact_manifest.artefact_schema_version	conservative_proposal
artefact_production_task	W2	16.1	Production: Task	object/artefact_manifest.task_id	source_literal
artefact_production_dispatch	W2	16.1	Production: dispatch	object/artefact_manifest.dispatch_id	source_literal
artefact_production_attempt	W2	16.1	Production: attempt	object/artefact_manifest.attempt_id	source_literal
artefact_production_actor	W2	16.1	Production: producer actor	object/artefact_manifest.producer_actor_id	conservative_proposal
artefact_production_profile	W2	16.1	Production: producer profile	object/artefact_manifest.producer_profile	conservative_proposal
artefact_production_context	W2	16.1	Production: context packet	object/artefact_manifest.context_packet_id	source_literal
artefact_production_created	W2	16.1	Production: creation time	object/artefact_manifest.created_at	conservative_proposal
artefact_code_commit	W2	16.1	Code/environment: commit	object/artefact_manifest.code_commit	conservative_proposal
artefact_code_branch	W2	16.1	Code/environment: branch identity	object/artefact_manifest.branch_identity	conservative_proposal
artefact_code_worktree	W2	16.1	Code/environment: worktree identity	object/artefact_manifest.worktree_identity	conservative_proposal
artefact_code_environment	W2	16.1	Code/environment: environment/toolchain fingerprint	object/artefact_manifest.environment_fingerprint	conservative_proposal
artefact_location_root	W2	16.1	Location: declared root ID	object/artefact_manifest.root_id	conservative_proposal
artefact_location_path	W2	16.1	Location: relative path/URI	object/artefact_manifest.relative_path	conservative_proposal
artefact_location_size	W2	16.1	Location: size	object/artefact_manifest.size_bytes	conservative_proposal
artefact_location_media_type	W2	16.1	Location: media type	object/artefact_manifest.media_type	conservative_proposal
artefact_integrity_hash	W2	16.1	Integrity: SHA-256	object/artefact_manifest.content_sha256	source_literal
artefact_integrity_observation	W2	16.1	Integrity: observation time	object/artefact_manifest.observed_at	conservative_proposal
artefact_integrity_availability_check	W2	16.1	Integrity: availability check	object/artefact_manifest.availability_check_evidence_refs	conservative_proposal
artefact_inputs_id	W2	16.1	Inputs: input artefact IDs	object/artefact_manifest.input_dependencies.input_artefact_id	source_literal
artefact_inputs_hash	W2	16.1	Inputs: input artefact hashes	object/artefact_manifest.input_dependencies.input_content_sha256	source_literal
artefact_inputs_role	W2	16.1	Inputs: dependency roles	object/artefact_manifest.input_dependencies.dependency_role	conservative_proposal
artefact_provenance_dataset_ids	W2	16.1	Research provenance: dataset IDs	object/artefact_manifest.research_provenance.dataset_ids	conservative_proposal
artefact_provenance_vintages	W2	16.1	Research provenance: dataset vintages	object/artefact_manifest.research_provenance.dataset_vintages	conservative_proposal
artefact_provenance_representations	W2	16.1	Research provenance: representation IDs	object/artefact_manifest.research_provenance.representation_ids	conservative_proposal
artefact_provenance_parameters	W2	16.1	Research provenance: parameter IDs	object/artefact_manifest.research_provenance.parameter_ids	conservative_proposal
artefact_provenance_seeds	W2	16.1	Research provenance: seed IDs	object/artefact_manifest.research_provenance.seed_ids	conservative_proposal
artefact_provenance_restrictions	W2	16.1	Research provenance: sample restriction IDs	object/artefact_manifest.research_provenance.sample_restriction_ids	conservative_proposal
artefact_validation_records	W2	16.1	Validation: validation-record refs	object/artefact_manifest.validation.validation_record_refs	conservative_proposal
artefact_validation_contracts	W2	16.1	Validation: expected contract IDs	object/artefact_manifest.validation.expected_contract_ids	conservative_proposal
artefact_validation_schemas	W2	16.1	Validation: expected schema IDs	object/artefact_manifest.validation.expected_schema_ids	conservative_proposal
artefact_authority_availability	W2	16.2	Authority dimension: availability	object/artefact_manifest.authority.availability	source_literal
artefact_authority_regenerability	W2	16.2	Authority dimension: regenerability	object/artefact_manifest.authority.regenerability	source_literal
artefact_authority_integrity	W2	16.2	Authority dimension: integrity	object/artefact_manifest.authority.integrity	source_literal
artefact_authority_structural	W2	16.2	Authority dimension: structural validation	object/artefact_manifest.authority.structural_validation	source_literal
artefact_authority_scientific	W2	16.2	Authority dimension: scientific review	object/artefact_manifest.authority.scientific_review	source_literal
artefact_authority_use	W2	16.2	Authority dimension: use authority	object/artefact_manifest.authority.use_authority	source_literal
artefact_authority_scope	W2	16.1	Authority: accepted scope	object/artefact_manifest.authority.accepted_scope	conservative_proposal
artefact_authority_consumers	W2	16.1	Authority: consumer restrictions	object/artefact_manifest.authority.consumer_restrictions	conservative_proposal
artefact_operations_no_overwrite	W2	16.1	Operations: no-overwrite evidence	object/artefact_manifest.operations.no_overwrite_evidence_refs	conservative_proposal
artefact_operations_retention	W2	16.1	Operations: retention	object/artefact_manifest.operations.retention_class	conservative_proposal
artefact_operations_confidentiality	W2	16.1	Operations: confidentiality	object/artefact_manifest.operations.confidentiality_class	conservative_proposal
artefact_operations_external_data	W2	16.1	Operations: external-data constraints	object/artefact_manifest.operations.external_data_constraints	conservative_proposal
resource_identity_request_id	W8	7	ResourceRequest identity	object/resource_request.resource_request_id	source_literal
resource_identity_task	W8	7	Task identity	object/resource_request.task_id	source_literal
resource_identity_dispatch	W8	7	Dispatch identity	object/resource_request.dispatch_id	source_literal
resource_identity_attempt	W8	7	Attempt identity	object/resource_request.attempt_id	source_literal
resource_identity_route	W8	7	Route identity	object/resource_request.route_id	conservative_proposal
resource_operation_class	W8	7	Normalized operation class	object/resource_request.operation_class	conservative_proposal
resource_provider	W8	7	Provider requirements	object/resource_request.provider_requirements	conservative_proposal
resource_runtime	W8	7	Runtime requirements	object/resource_request.runtime_requirements	conservative_proposal
resource_profile	W8	7	Operational profile	object/resource_request.operational_profile	source_literal
resource_profile_policy	W8	7	Operational-profile policy ID	object/resource_request.operational_profile_policy_id	conservative_proposal
resource_profile_revision	W8	7	Operational-profile revision	object/resource_request.operational_profile_revision	conservative_proposal
resource_requester_actor	W8	7	Requesting actor	object/resource_request.requesting_actor_id	conservative_proposal
resource_requester_profile	W8	7	Requesting profile	object/resource_request.requesting_profile	conservative_proposal
resource_requester_authority	W8	7	Requesting authority	object/resource_request.requesting_authority_grant_id	conservative_proposal
resource_expected_position	W8	7	Expected control-store position	object/resource_request.expected_control_store_position	conservative_proposal
resource_host_pool	W8	7	Requested host pool	object/resource_request.requested_host_pool	conservative_proposal
resource_roots	W8	7	Typed control/code/result/cache/data roots	object/resource_request.root_bindings	conservative_proposal
resource_cpu_processes	W8	7	CPU process limits	object/resource_request.resource_ceilings.cpu_processes	conservative_proposal
resource_cpu_threads	W8	7	CPU thread limits	object/resource_request.resource_ceilings.cpu_threads	conservative_proposal
resource_ram_working	W8	7	RAM working estimate	object/resource_request.resource_ceilings.ram_working_bytes	conservative_proposal
resource_ram_peak	W8	7	RAM peak estimate	object/resource_request.resource_ceilings.ram_peak_bytes	conservative_proposal
resource_gpu	W8	7	GPU/device requirements	object/resource_request.resource_ceilings.gpu_devices	conservative_proposal
resource_storage	W8	7	Storage estimate	object/resource_request.resource_ceilings.storage_bytes	conservative_proposal
resource_io	W8	7	IO estimate	object/resource_request.resource_ceilings.io_bytes	conservative_proposal
resource_network	W8	7	Network constraints	object/resource_request.network_constraints	conservative_proposal
resource_external_write	W8	7	External-write constraints	object/resource_request.external_write_constraints	conservative_proposal
resource_sensitivity	W8	7	Sensitivity constraints	object/resource_request.sensitivity_constraints	conservative_proposal
resource_exclusive	W8	7	Exclusive resources	object/resource_request.exclusive_resource_keys	conservative_proposal
resource_shared	W8	7	Shared resources	object/resource_request.shared_resource_keys	conservative_proposal
resource_compatibility	W8	7	Compatibility keys	object/resource_request.compatibility_keys	conservative_proposal
resource_runtime_minimum	W8	7	Runtime minimum	object/resource_request.runtime_distribution.minimum_seconds	conservative_proposal
resource_runtime_expected	W8	7	Runtime expected	object/resource_request.runtime_distribution.expected_seconds	conservative_proposal
resource_runtime_maximum	W8	7	Runtime maximum	object/resource_request.runtime_distribution.maximum_seconds	conservative_proposal
resource_deadline	W8	7	Deadline	object/resource_request.deadline	source_literal
resource_checkpoint_interval	W8	7	Checkpoint interval	object/resource_request.checkpoint_interval_seconds	conservative_proposal
resource_benchmark	W8	7	Benchmark evidence	object/resource_request.benchmark_evidence_refs	conservative_proposal
resource_projection	W8	7	Projection evidence	object/resource_request.projection_evidence_refs	conservative_proposal
resource_uncertainty	W8	7	Uncertainty basis	object/resource_request.runtime_distribution.uncertainty_basis	conservative_proposal
resource_stop	W8	7	Stop rules	object/resource_request.stop_rules	conservative_proposal
resource_pause	W8	7	Pause rules	object/resource_request.pause_rules	conservative_proposal
resource_partial	W8	7	Partial rules	object/resource_request.partial_rules	conservative_proposal
resource_escalation	W8	7	Escalation rules	object/resource_request.escalation_rules	conservative_proposal
resource_release	W8	7	Resource-release obligations	object/resource_request.release_obligations	conservative_proposal
resource_cleanup	W8	7	Cleanup obligations	object/resource_request.cleanup_obligations	conservative_proposal
trivial_typed_request	W8	11.1	Trivial typed request	object/resource_request.trivial_profile_evidence.request_record_type	source_literal
trivial_typed_grant	W8	11.1	Trivial typed grant	object/resource_request.trivial_profile_evidence.grant_record_type	source_literal
trivial_command_lease	W8	11.1	Trivial command-scoped lease	object/resource_request.trivial_profile_evidence.lease_scope	source_literal
trivial_explicit_ceilings	W8	11.1	Trivial explicit resource ceilings	object/resource_request.trivial_profile_evidence.resource_ceilings_requirement	source_literal
trivial_terminal_receipt_kind	W8	11.1	Trivial terminal ProviderReceipt or OperatorReceipt	object/resource_request.trivial_profile_evidence.terminal_receipt_kind	source_literal
trivial_terminal_release	W8	11.1	Trivial terminal receipt releases lease	object/resource_request.trivial_profile_evidence.terminal_receipt_lease_release	source_literal
trivial_terminal_evidence	W8	11.1	Trivial terminal receipt closure evidence	object/resource_request.trivial_profile_evidence.terminal_receipt_evidence_refs	conservative_proposal
trivial_benchmark_disposition	W8	11.1	Trivial benchmark required or not_applicable disposition	object/resource_request.trivial_profile_evidence.benchmark.disposition	source_literal
trivial_checkpoint_disposition	W8	11.1	Trivial checkpoint required or not_applicable disposition	object/resource_request.trivial_profile_evidence.checkpoint.disposition	source_literal
trivial_heartbeat_disposition	W8	11.1	Trivial periodic-heartbeat required or not_applicable disposition	object/resource_request.trivial_profile_evidence.periodic_heartbeat.disposition	source_literal
trivial_recovery_disposition	W8	11.1	Trivial recovery required or not_applicable disposition	object/resource_request.trivial_profile_evidence.recovery.disposition	source_literal
trivial_benchmark_policy	W8	11.1	Trivial benchmark disposition policy ID	object/resource_request.trivial_profile_evidence.benchmark.policy_id	conservative_proposal
trivial_benchmark_rationale	W8	11.1	Trivial benchmark disposition rationale	object/resource_request.trivial_profile_evidence.benchmark.rationale	conservative_proposal
trivial_benchmark_applicability	W8	11.1	Trivial benchmark applicability evidence	object/resource_request.trivial_profile_evidence.benchmark.applicability_evidence_refs	conservative_proposal
trivial_checkpoint_policy	W8	11.1	Trivial checkpoint disposition policy ID	object/resource_request.trivial_profile_evidence.checkpoint.policy_id	conservative_proposal
trivial_checkpoint_rationale	W8	11.1	Trivial checkpoint disposition rationale	object/resource_request.trivial_profile_evidence.checkpoint.rationale	conservative_proposal
trivial_checkpoint_applicability	W8	11.1	Trivial checkpoint applicability evidence	object/resource_request.trivial_profile_evidence.checkpoint.applicability_evidence_refs	conservative_proposal
trivial_heartbeat_policy	W8	11.1	Trivial periodic-heartbeat disposition policy ID	object/resource_request.trivial_profile_evidence.periodic_heartbeat.policy_id	conservative_proposal
trivial_heartbeat_rationale	W8	11.1	Trivial periodic-heartbeat disposition rationale	object/resource_request.trivial_profile_evidence.periodic_heartbeat.rationale	conservative_proposal
trivial_heartbeat_applicability	W8	11.1	Trivial periodic-heartbeat applicability evidence	object/resource_request.trivial_profile_evidence.periodic_heartbeat.applicability_evidence_refs	conservative_proposal
trivial_recovery_policy	W8	11.1	Trivial recovery disposition policy ID	object/resource_request.trivial_profile_evidence.recovery.policy_id	conservative_proposal
trivial_recovery_rationale	W8	11.1	Trivial recovery disposition rationale	object/resource_request.trivial_profile_evidence.recovery.rationale	conservative_proposal
trivial_recovery_applicability	W8	11.1	Trivial recovery applicability evidence	object/resource_request.trivial_profile_evidence.recovery.applicability_evidence_refs	conservative_proposal
trivial_provider_command	W8	12	Trivial provider command identity	object/resource_request.trivial_profile_evidence.provider_command_process.provider_command_id	conservative_proposal
trivial_process_na	W8	12	Trivial process identity not_applicable disposition	object/resource_request.trivial_profile_evidence.provider_command_process.process_identity_disposition	source_literal
trivial_process_na_rationale	W8	12	Trivial process identity not_applicable rationale	object/resource_request.trivial_profile_evidence.provider_command_process.process_identity_not_applicable_rationale	conservative_proposal
correction_selector_scope_definition	06d	1.4	scope_definition selects scope and governance correction index	correction_variant_mappings{corrected_record_kind=scope_definition}.projection_selector_rule	source_literal
correction_selector_task	06d	1.4	task selects task and governance correction index	correction_variant_mappings{corrected_record_kind=task}.projection_selector_rule	source_literal
correction_selector_dispatch	06d	1.4	dispatch selects dispatch and governance correction index	correction_variant_mappings{corrected_record_kind=dispatch}.projection_selector_rule	source_literal
correction_selector_lease	06d	1.4	lease selects lease and governance correction index	correction_variant_mappings{corrected_record_kind=lease}.projection_selector_rule	source_literal
correction_selector_attempt	06d	1.4	attempt selects attempt and governance correction index	correction_variant_mappings{corrected_record_kind=attempt}.projection_selector_rule	source_literal
correction_selector_checkpoint	06d	1.4	checkpoint selects checkpoint and governance correction index	correction_variant_mappings{corrected_record_kind=checkpoint}.projection_selector_rule	source_literal
correction_selector_message	06d	1.4	message selects message and governance correction index	correction_variant_mappings{corrected_record_kind=message}.projection_selector_rule	source_literal
correction_selector_blocker	06d	1.4	blocker selects blocker and governance correction index	correction_variant_mappings{corrected_record_kind=blocker}.projection_selector_rule	source_literal
correction_selector_artefact	06d	1.4	artefact selects artefact and governance correction index	correction_variant_mappings{corrected_record_kind=artefact}.projection_selector_rule	source_literal
correction_selector_review	06d	1.4	review selects review and governance correction index	correction_variant_mappings{corrected_record_kind=review}.projection_selector_rule	source_literal
correction_selector_decision	06d	1.4	decision selects decision and governance correction index	correction_variant_mappings{corrected_record_kind=decision}.projection_selector_rule	source_literal
correction_selector_rule_evaluation	06d	1.4	rule_evaluation selects rule_evaluation and governance correction index	correction_variant_mappings{corrected_record_kind=rule_evaluation}.projection_selector_rule	source_literal
correction_selector_resource	06d	1.4	resource selects resource and governance correction index	correction_variant_mappings{corrected_record_kind=resource}.projection_selector_rule	source_literal
correction_selector_operation	06d	1.4	operation selects operations and governance correction index	correction_variant_mappings{corrected_record_kind=operation}.projection_selector_rule	source_literal
correction_selector_backup	06d	1.4	backup selects backup and governance correction index	correction_variant_mappings{corrected_record_kind=backup}.projection_selector_rule	source_literal
correction_selector_exactly_one_owner	06d	1.4	Each correction selects exactly one owner projection	family/correction.affected_projections	source_literal
correction_governance_correction_index	06d	1.4	Each correction also requires the governance correction index	family/correction.governance_correction_index	source_literal
recovery_external_manifest	W8	19	BackupReceipt binds external artefact manifest	recovery_external_artefact_rules.entry_object_ref	conservative_proposal
recovery_external_availability	W8	19	BackupReceipt binds external artefact availability status	object/external_artefact_availability.availability	source_literal
recovery_external_availability_evidence	W8	19	Restore availability proof is retained per external artefact	object/external_artefact_availability.availability_evidence_refs	conservative_proposal
recovery_restore_writer_lease	W8	19-21	Availability must verify before writer lease; failed or partial restore is diagnostic only with no writer lease	recovery_external_artefact_rules.writer_lease_rule	source_literal
resource_profile_variant_discriminator	W8	11.1	one unified ResourceRequest with required operational_profile	object/resource_request.operational_profile	source_literal
resource_profile_trivial_branch	W8	11.1	trivial explicit not_applicable evidence branch	object/resource_request.trivial_profile_evidence	source_literal
resource_profile_bounded_branch	W8	11.1	bounded policy-selected heartbeat output-tail stop checkpoint branch	object/resource_request.bounded_profile_evidence	source_literal
resource_profile_long_running_branch	W8	11.1	long_running full applicable benchmark heartbeat process checkpoint stop-recovery backup branch	object/resource_request.long_running_profile_evidence	source_literal
bounded_profile_heartbeat	W8	11.1	bounded heartbeat group selected by policy	object/bounded_profile_evidence.heartbeat	source_literal
bounded_profile_output_tail	W8	11.1	bounded output-tail group selected by policy	object/bounded_profile_evidence.output_tail	source_literal
bounded_profile_stop	W8	11.1	bounded stop group selected by policy	object/bounded_profile_evidence.stop	source_literal
bounded_profile_checkpoint	W8	11.1	bounded checkpoint group selected by policy	object/bounded_profile_evidence.checkpoint	source_literal
long_running_profile_benchmark	W8	11.1	long_running applicable benchmark obligation	object/long_running_profile_evidence.benchmark	source_literal
long_running_profile_heartbeat	W8	11.1	long_running applicable heartbeat obligation	object/long_running_profile_evidence.heartbeat	source_literal
long_running_profile_process	W8	11.1-12	long_running applicable process obligation	object/long_running_profile_evidence.process	source_literal
long_running_profile_checkpoint	W8	11.1	long_running applicable checkpoint obligation	object/long_running_profile_evidence.checkpoint	source_literal
long_running_profile_stop_recovery	W8	11.1	long_running applicable stop/recovery obligation	object/long_running_profile_evidence.stop_recovery	source_literal
long_running_profile_backup	W8	11.1	long_running applicable backup obligation	object/long_running_profile_evidence.backup	source_literal
"""
SOURCE_FACT_BINDINGS = tuple(tuple(value for value in row.split("\t")) for row in SOURCE_FACT_BINDING_TSV.splitlines())

REVIEW_VERDICT_FACTS = frozenset(
    {
        "verdict",
        "findings",
        "required_evidence_refs",
        "limitations",
        "conditions",
        "reviewer_actor_id",
        "reviewer_profile",
        "reviewer_session",
        "reviewer_model_metadata",
        "context_manifest_id",
        "context_manifest_sha256",
        "unchanged_subject_sha256",
        "producing_attempt_id",
        "trace_visibility_evidence_refs",
        "computed_independence_grade",
    }
)

CORRECTION_PROJECTIONS = {
    "scope_definition": "scope",
    "task": "task",
    "dispatch": "dispatch",
    "lease": "lease",
    "attempt": "attempt",
    "checkpoint": "checkpoint",
    "message": "message",
    "blocker": "blocker",
    "artefact": "artefact",
    "review": "review",
    "decision": "decision",
    "rule_evaluation": "rule_evaluation",
    "resource": "resource",
    "operation": "operations",
    "backup": "backup",
}
CORRECTION_SUBJECT_SELECTION = {
    "scope_definition": "type/object_id",
    "task": "type/task_id",
    "dispatch": "type/dispatch_id",
    "lease": "type/lease_id",
    "attempt": "type/attempt_id",
    "checkpoint": "type/checkpoint_manifest_id",
    "message": "type/message_id",
    "blocker": "type/blocker_id",
    "artefact": "type/artefact_id",
    "review": "type/review_id",
    "decision": "type/decision_id",
    "rule_evaluation": "type/validation_id",
    "resource": "type/resource_id",
    "operation": "type/operation_id",
    "backup": "type/backup_receipt_id",
}

RECOVERY_RULES = {
    "external_artefact_field": "external_artefacts",
    "entry_object_ref": "object/external_artefact_availability",
    "entry_identity_fields": ["artefact_id", "content_sha256"],
    "availability_evidence_field": "availability_evidence_refs",
    "uniqueness_rule": "unique_by_artefact_id_and_content_sha256",
    "manifest_coverage_rule": "every_external_manifest_reference_exactly_once",
    "writer_lease_rule": "every_entry_available_with_nonempty_evidence_before_writer_lease",
    "diagnostic_only_conditions": [
        "missing",
        "inaccessible",
        "quarantined",
        "missing_availability_evidence",
        "incomplete_manifest_coverage",
        "partial_restore",
    ],
}
STALE_RECOVERY_FIELDS = {"external_artefact_refs", "external_availability"}

REQUIRED_READINESS_BLOCKERS = ["independent_source_fact_oracle", "fresh_exact_byte_review", "explicit_owner_approval"]


@dataclass(frozen=True)
class OwnerRow:
    key: str
    command_type: str
    event_types: tuple[str, ...]


def immutable_source_bytes(repo_root: Path, source_id: str) -> bytes:
    path, expected_blob, expected_sha256 = SOURCE_DOCUMENTS[source_id]
    raw = subprocess.run(
        ["git", "show", f"{SOURCE_REVISION}:{path}"], cwd=repo_root, stdout=subprocess.PIPE, check=True
    ).stdout
    assert not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw
    assert hashlib.sha256(raw).hexdigest() == expected_sha256
    blob = (
        subprocess.run(
            ["git", "hash-object", "--no-filters", "--stdin"],
            cwd=repo_root,
            input=raw,
            stdout=subprocess.PIPE,
            check=True,
        )
        .stdout.decode("ascii")
        .strip()
    )
    assert blob == expected_blob
    return raw


def parse_owner_rows(annex_bytes: bytes) -> tuple[OwnerRow, ...]:
    rows: list[OwnerRow] = []
    for line in annex_bytes.decode("utf-8").splitlines():
        cells = line.split("|")
        if len(cells) < 7:
            continue
        key = cells[1].strip().strip("`")
        if not re.fullmatch(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", key):
            continue
        semantic_types = re.findall(r"\b[A-Z][A-Za-z0-9]+\b", cells[3])
        assert len(semantic_types) in {2, 3}, key
        rows.append(OwnerRow(key, semantic_types[0], tuple(semantic_types[1:])))
    return tuple(rows)


def field_map(owner: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fields = owner["fields"]
    assert len({item["field_name"] for item in fields}) == len(fields)
    return {item["field_name"]: item for item in fields}


def assert_exact_roots(subject: dict[str, Any]) -> None:
    for key, expected in (("command_root", COMMAND_ROOT), ("event_root", EVENT_ROOT)):
        observed = tuple(
            (field["field_name"], field["type_ref"], field["nullable"]) for field in subject[key]["fields"]
        )
        assert observed == expected
        assert subject[key]["additional_properties"] is False


def assert_type_and_enum_authority(subject: dict[str, Any]) -> None:
    types = {item["type_id"]: item for item in subject["primitive_types"]}
    enums = {item["enum_id"]: item for item in subject["source_closed_enums"]}
    assert types["type/nonnegative_integer"]["maximum"] == P0_MAXIMUM
    assert types["type/positive_integer"]["maximum"] == P0_MAXIMUM
    assert types["type/nonnegative_integer"]["minimum"] == 0
    assert types["type/positive_integer"]["minimum"] == 1
    for type_id, prefix in SOURCE_LITERAL_ID_PREFIXES.items():
        assert types[type_id]["pattern"] == f"^{prefix}_{UUID7_TAIL}$"
    for enum_id, values in SOURCE_CLOSED_ENUMS.items():
        assert tuple(enums[enum_id]["values"]) == values
    assert set(enums["enum/checkpoint_compatibility"]["values"]).isdisjoint({"not_applicable"})
    assert "not_applicable" in enums["enum/profile_applicability"]["values"]


def assert_complete_source_groups(subject: dict[str, Any]) -> None:
    objects = {item["object_id"]: item for item in subject["reusable_objects"]}
    for object_id, expected_fields in COMPLETE_SOURCE_GROUP_FIELDS.items():
        assert frozenset(field_map(objects[object_id])) == expected_fields
        assert objects[object_id]["additional_properties"] is False
    review = next(item for item in subject["family_specs"] if item["family_id"] == "family/review")
    assert REVIEW_VERDICT_FACTS <= frozenset(field_map(review))


def assert_high_risk_field_semantics(subject: dict[str, Any]) -> None:
    """Compare exact source-derived types, nullability, and conditional relations."""
    objects = {item["object_id"]: item for item in subject["reusable_objects"]}
    families = {item["family_id"]: item for item in subject["family_specs"]}
    types = {item["type_id"]: item for item in subject["primitive_types"]}
    enums = {item["enum_id"]: item for item in subject["source_closed_enums"]}

    assert subject["object_variant_rules"] == [RESOURCE_PROFILE_VARIANT_RULE]
    assert subject["review_gate_condition_rule"] == REVIEW_GATE_CONDITION_RULE
    assert subject["reusable_object_field_rule"] == REUSABLE_OBJECT_FIELD_RULE
    review_condition_list = types["type/review_gate_condition_list"]
    assert (
        review_condition_list["json_type"],
        review_condition_list["nullable"],
        review_condition_list["item_type_ref"],
    ) == ("array", False, "object/review_gate_condition")
    assert "min_items" not in review_condition_list
    nonempty_evidence = types["type/nonempty_evidence_ref_list"]
    assert (
        nonempty_evidence["json_type"],
        nonempty_evidence["nullable"],
        nonempty_evidence["min_items"],
        nonempty_evidence["item_type_ref"],
    ) == ("array", False, 1, "type/nonempty_string")
    assert enums["enum/review_condition_gate_disposition"]["decision_basis"] == "conservative_proposal"

    for object_id, expected in RESOURCE_REQUEST_PROFILE_FIELD_FACTS.items():
        fields = field_map(objects[object_id])
        if object_id != "object/resource_request":
            assert tuple(fields) == tuple(item[0] for item in expected)
        observed = tuple(
            (field_name, fields[field_name]["type_ref"], fields[field_name]["nullable"], conditional_relation)
            for field_name, _type_ref, _nullable, conditional_relation in expected
        )
        assert observed == expected

    for owner_id, expected in REVIEW_CONDITION_FIELD_FACTS.items():
        fields = field_map(objects.get(owner_id, families.get(owner_id)))
        if owner_id == "object/review_gate_condition":
            assert tuple(fields) == tuple(item[0] for item in expected)
        observed = tuple(
            (field_name, fields[field_name]["type_ref"], fields[field_name]["nullable"], conditional_relation)
            for field_name, _type_ref, _nullable, conditional_relation in expected
        )
        assert observed == expected
    assert field_map(objects["object/review_gate_condition"])["gate_disposition"]["decision_basis"] == (
        "conservative_proposal"
    )


def _resolve_target(subject: dict[str, Any], target: str) -> bool:
    if target.startswith("correction_variant_mappings{"):
        match = re.fullmatch(r"correction_variant_mappings\{corrected_record_kind=([a-z_]+)\}\.([a-z_]+)", target)
        if not match:
            return False
        kind, field = match.groups()
        row = next(
            (item for item in subject["correction_variant_mappings"] if item["corrected_record_kind"] == kind), None
        )
        return row is not None and field in row
    if target.startswith("recovery_external_artefact_rules."):
        return target.split(".", 1)[1] in subject["recovery_external_artefact_rules"]
    owner_id, tail = target.split(".", 1)
    owners = {
        **{item["object_id"]: item for item in subject["reusable_objects"]},
        **{item["family_id"]: item for item in subject["family_specs"]},
    }
    fields = field_map(owners[owner_id])
    brace = re.fullmatch(r"\{([a-z0-9_,]+)\}", tail)
    if brace:
        return set(brace.group(1).split(",")) <= set(fields)
    selected_field = re.fullmatch(r"([a-z0-9_]+)\{([a-z0-9_]+)=([a-z0-9_]+)\}", tail)
    if selected_field:
        target_field, discriminator, _value = selected_field.groups()
        return target_field in fields and discriminator in fields
    parts = tail.split(".")
    objects = {item["object_id"]: item for item in subject["reusable_objects"]}
    types = {item["type_id"]: item for item in subject["primitive_types"]}
    for index, part in enumerate(parts):
        if part not in fields:
            return False
        if index == len(parts) - 1:
            return True
        ref = fields[part]["type_ref"]
        if ref in objects:
            fields = field_map(objects[ref])
        elif ref in types and types[ref].get("item_type_ref") in objects:
            fields = field_map(objects[types[ref]["item_type_ref"]])
        else:
            return False
    return False


def assert_all_binding_targets_resolve(subject: dict[str, Any]) -> None:
    bindings = subject["source_fact_bindings"]
    assert len({item["binding_id"] for item in bindings}) == len(bindings)
    assert all(_resolve_target(subject, item["target_path"]) for item in bindings)


def assert_exact_source_fact_bindings(subject: dict[str, Any]) -> None:
    keys = ("binding_id", "source_id", "source_section", "source_fact", "target_path", "decision_basis")
    observed = tuple(tuple(str(item[key]) for key in keys) for item in subject["source_fact_bindings"])
    assert len(SOURCE_FACT_BINDINGS) == 229
    assert observed == SOURCE_FACT_BINDINGS


def assert_required_source_facts_bound(subject: dict[str, Any]) -> None:
    """Compatibility entry point retained for the intentional RED mutation suite."""
    assert_exact_source_fact_bindings(subject)


def assert_owner_rows_and_bindings(subject: dict[str, Any], rows: tuple[OwnerRow, ...]) -> None:
    assert subject["cardinalities"] == EXPECTED_CARDINALITIES
    commands = subject["command_payload_specs"]
    events = subject["event_fact_specs"]
    bindings = subject["row_bindings"]
    assert [item["row_key"] for item in commands] == [row.key for row in rows]
    assert [item["command_type"] for item in commands] == [row.command_type for row in rows]
    assert [item["row_key"] for item in bindings] == [row.key for row in rows]
    expected_events = [(row.key, ordinal, event) for row in rows for ordinal, event in enumerate(row.event_types, 1)]
    observed_events = [(item["row_key"], item["event_ordinal"], item["event_type"]) for item in events]
    assert observed_events == expected_events
    assert len({item["command_type"] for item in commands}) == 87
    assert len({item["event_type"] for item in events}) == 86
    event_by_id = {item["spec_id"]: item for item in events}
    for row, binding in zip(rows, bindings, strict=True):
        assert binding["command_payload_spec_ref"] == "command_payload/" + row.key.replace(".", "_")
        assert [event_by_id[ref]["event_type"] for ref in binding["ordered_event_fact_spec_refs"]] == list(
            row.event_types
        )
    family_fields = {item["family_id"]: set(field_map(item)) for item in subject["family_specs"]}
    for spec in [*commands, *events]:
        assert spec["family_ref"] in family_fields
        assert set(spec["required_field_names"]) <= family_fields[spec["family_ref"]]
        assert spec["additional_properties"] is False


def assert_correction_and_recovery(subject: dict[str, Any]) -> None:
    rows = subject["correction_variant_mappings"]
    assert [item["corrected_record_kind"] for item in rows] == list(CORRECTION_PROJECTIONS)
    assert {item["corrected_record_kind"]: item["owner_projection"] for item in rows} == CORRECTION_PROJECTIONS
    assert {item["corrected_record_kind"]: item["subject_id_type_ref"] for item in rows} == CORRECTION_SUBJECT_SELECTION
    assert all(item["subject_field"] == "erroneous_record_id" for item in rows)
    assert all(item["governance_correction_index"] == "governance_correction_index" for item in rows)
    assert all(
        item["projection_selector_rule"] == "exactly_one_owner_projection_plus_governance_correction_index"
        for item in rows
    )
    assert subject["recovery_external_artefact_rules"] == RECOVERY_RULES
    backup = next(item for item in subject["family_specs"] if item["family_id"] == "family/backup_recovery")
    assert STALE_RECOVERY_FIELDS.isdisjoint(field_map(backup))
    external = next(
        item for item in subject["reusable_objects"] if item["object_id"] == "object/external_artefact_availability"
    )
    assert set(field_map(external)) == {"artefact_id", "content_sha256", "availability", "availability_evidence_refs"}
    evidence_type = next(
        item for item in subject["primitive_types"] if item["type_id"] == "type/nonempty_evidence_ref_list"
    )
    assert evidence_type["min_items"] == 1


def assert_generation_boundary(subject: dict[str, Any]) -> None:
    assert tuple(item["family_id"] for item in subject["family_specs"]) == FAMILY_IDS
    assert len(subject["shared_schema_rules"]) == 17
    assert subject["generation_contract"] == {
        "mode": "deterministic_total_function",
        "byte_changing_choices_remaining": 0,
        "generator_runtime_authority": False,
        "generated_schema_identity_count": 173,
        "open_policy_vocabularies": "versioned_runtime_policy_gate_only",
        "institutional_classifications": "versioned_runtime_policy_gate_only",
        "stage_1_ready": False,
        "pending_r3_remediation": [],
        "readiness_blockers": REQUIRED_READINESS_BLOCKERS,
    }
    assert subject["schema_identity_rule"] == {
        "identity_key": ["schema_kind", "semantic_type"],
        "unique_command_identities": 87,
        "unique_event_identities": 86,
        "total_identities": 173,
        "repeated_rows_share_identity": True,
        "variants_are_closed_within_shared_identity": True,
    }
    assert len(subject["decision_register"]) == 14
    assert all(item["generator_byte_change_allowed"] is False for item in subject["decision_register"])


def assert_shared_rules(subject: dict[str, Any]) -> None:
    observed = {}
    for item in subject["shared_schema_rules"]:
        observed[(item["schema_kind"], item["semantic_type"])] = (
            item["variant_rule"],
            item.get("discriminator_field"),
            tuple(item["variant_ids"]),
            tuple((entry["variant_id"], entry["const_value"]) for entry in item.get("variant_const_values", [])),
        )
    assert observed == SHARED_RULES


def assert_conservative_identity_selections_are_explicit(subject: dict[str, Any]) -> None:
    decisions = {item["decision_id"]: item for item in subject["decision_register"]}
    # W2 assigns val_ to ValidationRecord, not RuleEvaluation.  W8 lists the
    # primitive IDs but does not source-literally define resource/operation unions.
    assert "proposal_decision/rule_evaluation_subject_id_grammar" in decisions
    assert "proposal_decision/resource_operation_id_unions" in decisions
    assert "type/validation_id" in decisions["proposal_decision/rule_evaluation_subject_id_grammar"]["selected_rule"]
    assert "type/resource_id" in decisions["proposal_decision/resource_operation_id_unions"]["selected_rule"]
    assert "type/operation_id" in decisions["proposal_decision/resource_operation_id_unions"]["selected_rule"]
    types = {item["type_id"]: item for item in subject["primitive_types"]}
    assert types["type/resource_id"]["decision_basis"] == "conservative_proposal"
    assert types["type/operation_id"]["decision_basis"] == "conservative_proposal"


def _valid_typed_value(value: Any, type_ref: str) -> bool:
    if type_ref in SOURCE_CLOSED_ENUMS:
        return value in SOURCE_CLOSED_ENUMS[type_ref]
    if type_ref in {"type/nonempty_string", "type/any_id"}:
        return isinstance(value, str) and bool(value)
    if type_ref == "type/semver":
        return isinstance(value, str) and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value) is not None
    if type_ref in {"type/policy_version_id", "type/actor_id"}:
        prefix = SOURCE_LITERAL_ID_PREFIXES[type_ref]
        return isinstance(value, str) and re.fullmatch(f"{prefix}_{UUID7_TAIL}", value) is not None
    if type_ref == "type/nonempty_evidence_ref_list":
        return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item for item in value)
    if type_ref.startswith("object/"):
        return _profile_object_valid(value, type_ref)
    return False


def _profile_object_valid(value: Any, object_id: str) -> bool:
    expected = RESOURCE_REQUEST_PROFILE_FIELD_FACTS.get(object_id)
    if expected is None or not isinstance(value, dict):
        return False
    if set(value) != {item[0] for item in expected}:
        return False
    for field_name, type_ref, nullable, _relation in expected:
        field_value = value[field_name]
        if field_value is None:
            if not nullable:
                return False
        elif not _valid_typed_value(field_value, type_ref):
            return False
    return True


def resource_request_composed_field_sets(
    profile: str,
    variant_rule: dict[str, Any] | None = None,
    field_rule: dict[str, Any] | None = None,
) -> dict[str, frozenset[str]] | None:
    variant_rule = RESOURCE_PROFILE_VARIANT_RULE if variant_rule is None else variant_rule
    field_rule = REUSABLE_OBJECT_FIELD_RULE if field_rule is None else field_rule
    branches = variant_rule.get("branches", [])
    selected = [item for item in branches if item.get("discriminator_const") == profile]
    if len(selected) != 1:
        return None
    controlled = frozenset(
        field for branch in branches for key in ("required_fields", "forbidden_fields") for field in branch.get(key, [])
    )
    all_fields = COMPLETE_SOURCE_GROUP_FIELDS["object/resource_request"]
    exception_is_exact = all(
        (
            variant_rule.get("object_id") == "object/resource_request",
            variant_rule.get("no_fallback") is True,
            field_rule.get("all_listed_reusable_object_fields_required") is True,
            field_rule.get("variant_controlled_field_exception")
            == "fields_controlled_by_same_object_variant_rule_are_exempt_from_global_requiredness",
            field_rule.get("variant_controlled_field_derivation")
            == "union_of_all_branch_required_fields_and_forbidden_fields",
            field_rule.get("requiredness_precedence")
            == "variant_branch_presence_rules_override_global_requiredness_for_controlled_fields_only",
            field_rule.get("non_variant_listed_fields_required") is True,
            field_rule.get("selected_variant_required_fields_non_null") is True,
            field_rule.get("selected_variant_forbidden_fields_absent") is True,
            field_rule.get("selected_nested_object_fields_required") is True,
        )
    )
    common = frozenset(all_fields - controlled) if exception_is_exact else frozenset(all_fields)
    required = common | frozenset(selected[0].get("required_fields", []))
    forbidden = frozenset(selected[0].get("forbidden_fields", []))
    return {
        "controlled": controlled,
        "common": common,
        "required": required,
        "forbidden": forbidden,
    }


def composed_resource_request_satisfiable(
    record: dict[str, Any],
    variant_rule: dict[str, Any] | None = None,
    field_rule: dict[str, Any] | None = None,
) -> bool:
    field_sets = resource_request_composed_field_sets(
        record.get("operational_profile"), variant_rule=variant_rule, field_rule=field_rule
    )
    if field_sets is None:
        return False
    if field_sets["controlled"] != frozenset(
        {"trivial_profile_evidence", "bounded_profile_evidence", "long_running_profile_evidence"}
    ):
        return False
    if len(field_sets["common"]) != 35 or field_sets["required"] & field_sets["forbidden"]:
        return False
    if set(record) != field_sets["required"]:
        return False
    selected_fields = field_sets["required"] & field_sets["controlled"]
    if len(selected_fields) != 1 or any(record[field] is None for field in selected_fields):
        return False
    profile_slice = {
        key: value
        for key, value in record.items()
        if key
        in {
            "operational_profile",
            "operational_profile_policy_id",
            "operational_profile_revision",
            *field_sets["controlled"],
        }
    }
    return resource_profile_branch_allowed(profile_slice)


def resource_profile_branch_allowed(record: dict[str, Any]) -> bool:
    profile = record.get("operational_profile")
    branch = next(
        (item for item in RESOURCE_PROFILE_VARIANT_RULE["branches"] if item["discriminator_const"] == profile),
        None,
    )
    if branch is None:
        return False
    required = {
        "operational_profile",
        "operational_profile_policy_id",
        "operational_profile_revision",
        *branch["required_fields"],
    }
    if set(record) != required:
        return False
    fields = {item[0]: item for item in RESOURCE_REQUEST_PROFILE_FIELD_FACTS["object/resource_request"]}
    return all(
        record[field_name] is not None and _valid_typed_value(record[field_name], fields[field_name][1])
        for field_name in required
    )


def review_verdict_structurally_valid(verdict: str, conditions: Any) -> bool:
    if verdict not in VERDICT_GATE_RESULTS or not isinstance(conditions, list):
        return False
    expected = REVIEW_CONDITION_FIELD_FACTS["object/review_gate_condition"]
    for condition in conditions:
        if not isinstance(condition, dict) or set(condition) != {item[0] for item in expected}:
            return False
        for field_name, type_ref, nullable, _relation in expected:
            value = condition[field_name]
            if value is None:
                if not nullable:
                    return False
            elif not _valid_typed_value(value, type_ref):
                return False
    return True


def review_verdict_satisfies_gate(verdict: str, conditions: list[dict[str, Any]]) -> bool:
    if not review_verdict_structurally_valid(verdict, conditions):
        return False
    if VERDICT_GATE_RESULTS[verdict] == "satisfied":
        return True
    if verdict != "approve_with_conditions" or len(conditions) < 1:
        return False
    return all(item["gate_disposition"] == "non_blocking" and item["owner_actor_id"] is not None for item in conditions)


def writer_lease_allowed(entries: list[dict[str, Any]], expected_manifest: set[tuple[str, str]]) -> bool:
    identities = [(item.get("artefact_id"), item.get("content_sha256")) for item in entries]
    if len(set(identities)) != len(identities) or set(identities) != expected_manifest:
        return False
    return all(item.get("availability") == "available" and item.get("availability_evidence_refs") for item in entries)
