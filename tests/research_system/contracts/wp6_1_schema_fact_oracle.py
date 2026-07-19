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
        }
    ),
}

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
        "conditional_approval_owner",
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


def assert_required_source_facts_bound(subject: dict[str, Any]) -> None:
    bindings = {item["binding_id"]: item for item in subject["source_fact_bindings"]}
    # W2 section 10.1 names Task/Decision/Artefact dependencies and their
    # satisfaction predicates as a non-compensating Task group.
    required_dependencies = {
        "task_dependency_task_ids",
        "task_dependency_decision_ids",
        "task_dependency_artefact_ids",
        "task_dependency_predicates",
    }
    assert required_dependencies <= set(bindings)
    required_recovery = {
        "recovery_external_manifest",
        "recovery_external_availability",
        "recovery_external_availability_evidence",
        "recovery_restore_writer_lease",
    }
    assert required_recovery <= set(bindings)


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
    assert len(subject["decision_register"]) == 12
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


def writer_lease_allowed(entries: list[dict[str, Any]], expected_manifest: set[tuple[str, str]]) -> bool:
    identities = [(item.get("artefact_id"), item.get("content_sha256")) for item in entries]
    if len(set(identities)) != len(identities) or set(identities) != expected_manifest:
        return False
    return all(item.get("availability") == "available" and item.get("availability_evidence_refs") for item in entries)
