"""Materialize the staged WP4.4 control/store fixture corpus."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from research_system.canonical import canonical_bytes, sha256_hex

from tools.ars.fixture_materializer import materialize_cases, run_cli

_REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class Case:
    """Define one staged control/store fixture case."""

    title: str
    contract: str
    failure_class: str
    incident_basis: str
    input_fidelity: str
    assurance_lanes: tuple[str, ...]
    action: dict[str, Any]
    pre: dict[str, Any]
    post: dict[str, Any]
    required: tuple[str, ...]
    forbidden: tuple[str, ...]
    graders: tuple[str, ...]
    priority: str
    gate_stage: str


CASES = {
    "F-001": Case(
        "Single-slot overwrite", "immutable_message_ownership",
        "authority_overwrite", "historical", "reconstructed",
        ("coordination", "provenance"),
        {"operation": "publish_message", "slot": "task.md", "incoming_owner": "T0.12"},
        {"existing_owner": "T0.3", "destructive_overwrite": True, "surviving_ids": ["T0.12"]},
        {"destructive_overwrite": False, "surviving_ids": ["T0.3", "T0.12"], "collision_visible": True},
        ("MessagePublished:T0.3", "MessagePublished:T0.12", "OwnershipConflictRecorded"),
        ("MessageOverwritten", "TaskInferredComplete"), ("D", "T", "O"),
        "P0", "p0_materialization",
    ),
    "F-002": Case(
        "Task and report collision", "message_kind_separation",
        "task_report_collision", "historical", "reconstructed", ("coordination",),
        {"operation": "publish_assignment", "task_id": "T1.28", "occupied_slot_kind": "report", "occupied_task_id": "T1.6"},
        {"shared_slot": True, "report_erased": True},
        {"shared_slot": False, "message_kinds": ["assignment", "report", "acknowledgement", "review"], "report_preserved": True},
        ("AssignmentPublished", "ReportPreserved", "MessageAcknowledged:T1.6"),
        ("ReportClearedByAssignment", "DispatchStateErased"), ("D", "T"),
        "P0", "p0_materialization",
    ),
    "F-003": Case(
        "Wrong control root", "explicit_root_binding",
        "wrong_control_root", "historical", "minimized", ("provenance", "operations"),
        {"operation": "resolve_dispatch_roots", "cwd": "worktree", "control_root": "main", "code_root": "worktree", "result_root": "worktree/results", "cache_root": "main/cache"},
        {"resolution_source": "cwd", "write_target": "worktree/.apm/bus"},
        {"resolution_source": "dispatch_bindings", "wrong_root_rejected": True, "attempt_manifest_bound": True},
        ("RootBindingsValidated", "AttemptManifestRecorded"),
        ("WrongRootWrite", "CwdDerivedAuthority"), ("D", "T", "O"),
        "P0", "p0_materialization",
    ),
    "F-004": Case(
        "Stale completion log", "canonical_projection_precedence",
        "stale_completion_log", "historical", "minimized", ("provenance",),
        {"operation": "rebuild_task_projection", "manual_frontmatter": "Complete", "manual_body": "verdict pending", "accepted_event_state": "accepted"},
        {"current_sources": ["frontmatter", "body"], "states": ["Complete", "pending"]},
        {"current_source": "accepted_events", "current_state": "accepted", "manual_log_retained": True, "drift_diagnostic": True},
        ("ProjectionRebuilt", "ProjectionDriftDiagnosed"),
        ("ManualLogPromotedToAuthority", "AcceptedStateRewritten"), ("D", "T"),
        "P0", "p0_materialization",
    ),
    "F-005": Case(
        "Narrowed stage collapse", "exact_scope_revision_closure",
        "narrowed_stage_completion", "historical", "minimized", ("governance", "claim"),
        {"operation": "complete_scope", "scope_revision": "stage2-r22", "required_member_count": 22, "submitted_member_count": 8},
        {"completion_accepted": True, "missing_member_count": 14},
        {"completion_accepted": False, "missing_member_count": 14, "missing_dispositions_reported": True},
        ("CompleteScopeRejected", "MissingScopeMembersReported"),
        ("ScopeCompleted", "OmittedMemberInferredComplete"), ("D", "T", "H"),
        "P0", "p0_materialization",
    ),
    "S-001": Case(
        "Idempotent lost receipt", "idempotent_receipt_recovery",
        "lost_response_retry", "specification", "synthetic", ("coordination", "operations"),
        {"operation": "retry_command", "command_id": "cmd-fixed", "first_response": "lost", "retry_payload": "identical"},
        {"event_batch_count": 2, "receipt_reconstructed": False},
        {"event_batch_count": 1, "receipt_reconstructed": True, "changed_payload_conflicts": True},
        ("CommandCommitted", "ReceiptReconstructed"),
        ("DuplicateBatchCommitted", "ChangedPayloadAccepted"), ("D", "T", "O"),
        "P1", "interface_review",
    ),
    "S-002": Case(
        "Exclusive competing claims", "exclusive_claim_serialization",
        "competing_exclusive_claims", "specification", "synthetic", ("coordination",),
        {"operation": "claim_dispatch", "dispatch_id": "dsp-fixed", "expected_version": 0, "actors": ["actor-a", "actor-b"]},
        {"accepted_claims": 2, "active_attempts": 2},
        {"accepted_claims": 1, "conflict_receipts": 1, "active_attempts": 1},
        ("DispatchClaimed", "ClaimConflictRecorded"),
        ("SecondClaimAccepted", "DualActiveAttempt"), ("D", "T"),
        "P1", "interface_review",
    ),
    "S-006": Case(
        "Compatibility ownership collision", "compatibility_path_ownership",
        "compatibility_ownership_collision", "specification", "synthetic", ("coordination", "provenance"),
        {"operation": "register_compatibility_path", "path": "legacy/task.md", "legacy_writable": True, "incoming_owner": "other-task"},
        {"registration_accepted": True, "canonical_messages_preserved": False},
        {"registration_accepted": False, "canonical_messages_preserved": True, "collision_reported": True},
        ("CompatibilityRegistrationRejected", "OwnershipCollisionRecorded"),
        ("SharedLegacyPathRegistered", "CanonicalMessageDeleted"), ("D", "T"),
        "P1", "interface_review",
    ),
    "S-008": Case(
        "Incomplete scope completion", "complete_scope_member_closure",
        "incomplete_scope_completion", "specification", "synthetic", ("governance",),
        {"operation": "complete_scope", "scope_revision": "scope-22", "required_members": 22, "submitted_members": 8},
        {"completion_event_count": 1, "missing_dispositions": 14},
        {"completion_event_count": 0, "missing_dispositions": 14, "rejection_reason": "scope_incomplete"},
        ("CommandRejected:scope_incomplete", "MissingScopeMembersReported"),
        ("ScopeCompleted", "CompletionProjectionPublished"), ("D", "T"),
        "P1", "interface_review",
    ),
    "S-009": Case(
        "Projection rebuild", "projection_replay_equivalence",
        "projection_rebuild", "specification", "synthetic", ("provenance", "operations"),
        {"operation": "rebuild_projection", "delete_generated_views": True, "replay_modes": ["genesis", "verified_snapshot_tail"]},
        {"checksum_match": False, "database_treated_as_authority": True},
        {"checksum_match": True, "database_treated_as_authority": False, "rebuilds": 2},
        ("ProjectionDeleted", "ProjectionRebuiltFromGenesis", "ProjectionRebuiltFromSnapshot"),
        ("DatabaseReadAsAuthority", "ProjectionChecksumDiverged"), ("D", "T", "O"),
        "P1", "interface_review",
    ),
    "S-010": Case(
        "Unknown event major version", "unknown_event_version_fail_closed",
        "unknown_event_version", "specification", "synthetic", ("provenance", "operations"),
        {"operation": "replay_ledger", "unknown_schema_id": "ars://events/task/99.0.0", "unknown_position": 4},
        {"partial_projection_published": True, "failed_position": None},
        {"partial_projection_published": False, "failed_position": 4, "prior_projection_state": "stale"},
        ("ReplayStoppedAt:4", "PriorProjectionMarkedStale"),
        ("PartialProjectionPublished", "UnknownEventSkipped"), ("D", "T", "O"),
        "P1", "interface_review",
    ),
    "S-011": Case(
        "Writer crash window", "atomic_writer_crash_recovery",
        "writer_crash_window", "specification", "synthetic", ("coordination", "operations"),
        {"operation": "inject_writer_crash", "windows": ["before_rename", "after_rename", "before_receipt"]},
        {"possible_batch_counts": [0, 1, 2], "receipt_matches_committed_batch": False},
        {"possible_batch_counts": [0, 1], "receipt_matches_committed_batch": True, "half_command_visible": False},
        ("WriterCrashInjected", "CommittedBatchRecovered", "ReceiptReconstructed"),
        ("HalfCommandPublished", "DuplicateBatchCommitted"), ("D", "T", "O"),
        "P0", "p0_materialization",
    ),
    "S-012": Case(
        "Divergent task branches", "single_writer_branch_serialization",
        "divergent_branch_allocation", "specification", "synthetic", ("coordination", "provenance"),
        {"operation": "submit_from_worktrees", "tail_position": 9, "worktrees": ["branch-a", "branch-b"], "registered_service": "project-writer"},
        {"allocated_positions": [10, 10], "divergent_store_accepted": True},
        {"allocated_positions": [10, 11], "divergent_store_accepted": False, "single_writer_enforced": True},
        ("WriterLeaseChecked", "CommandsSerialized"),
        ("OverlappingPositionAllocated", "DivergentStoreAccepted"), ("D", "T", "O"),
        "P0", "p0_materialization",
    ),
}


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def _grader(case_id: str, case: Case, grader_class: str) -> dict[str, Any]:
    """Return one explicit grader requirement for a fixture case."""
    suffixes = {
        "D": "outcome",
        "T": "trajectory",
        "R": "research-quality",
        "M": "independent-model",
        "H": "human-authority",
        "O": "operational",
        "P": "privacy-security",
    }
    suffix = suffixes[grader_class]
    selectors = [case.contract]
    if grader_class == "D":
        selectors.extend(["input/stimulus.json", "expected/post-control.json"])
    elif grader_class == "T":
        selectors.append("expected/trajectory.json")
    else:
        selectors.extend(["input/stimulus.json", "expected/trajectory.json"])
    return {
        "grader_id": f"{case_id.lower()}-{suffix}",
        "grader_class": grader_class,
        "grader_version": "control-store-v1",
        "critical": True,
        "required": True,
        "independence_requirement": "deterministic_independent",
        "evidence_selectors": selectors,
    }


def _document(case_id: str, name: str, case: Case) -> dict[str, Any]:
    """Return one schema-bound JSON document for a fixture package."""
    common = {
        "schema_version": "1.0.0",
        "fixture_id": case_id,
        "fixture_revision": "r1",
    }
    if name == "input/stimulus.json":
        return {
            "schema_id": "ars://evals/fixture-stimulus", **common,
            "stimulus_kind": "control_store_contract",
            "payload": {"contract": case.contract, "action": case.action},
        }
    if name in {"expected/pre-control.json", "expected/post-control.json"}:
        controlled = name.endswith("post-control.json")
        evidence = case.post if controlled else case.pre
        return {
            "schema_id": "ars://evals/fixture-oracle", **common,
            "oracle_kind": "post_control" if controlled else "pre_control",
            "assertions": [{
                "property": case.contract,
                "satisfied": controlled,
                "derived_from": ["input/stimulus.json", "normalized_trace"],
                "expected_evidence": evidence,
            }],
        }
    if name == "expected/trajectory.json":
        return {
            "schema_id": "ars://evals/fixture-trajectory", **common,
            "required": list(case.required), "forbidden": list(case.forbidden),
        }
    if name == "graders/required.json":
        return {
            "schema_id": "ars://evals/fixture-grader-manifest", **common,
            "required_graders": [_grader(case_id, case, item) for item in case.graders],
        }
    raise ValueError(name)


def _package(case_id: str, case: Case) -> dict[str, bytes]:
    """Return the complete serialized eight-file fixture package."""
    files = {
        "README.md": (
            f"# {case_id}: {case.title}\n\n"
            f"Staged WP4.4 fixture for `{case.contract}`. The package is authored but "
            "not calibrated or active. Its oracle derives from the minimized stimulus and normalized trace.\n"
        ).encode(),
    }
    for name in (
        "input/stimulus.json", "expected/pre-control.json",
        "expected/post-control.json", "expected/trajectory.json",
        "graders/required.json",
    ):
        files[name] = _json_bytes(_document(case_id, name, case))
    content_hashes = {name: sha256_hex(data) for name, data in files.items()}
    source = {
        "schema_id": "ars://evals/fixture-source-manifest",
        "schema_version": "1.0.0",
        "fixture_id": case_id,
        "fixture_revision": "r1",
        "source_snapshot_date": "2026-07-01",
        "authoritative_refs": [
            "docs/plans/agentic-research-system/design/02-task-event-and-artifact-schema.md",
            "docs/plans/agentic-research-system/design/06-evaluation-observability-and-audit.md",
        ],
        "reconstruction_method": (
            "historical_minimized_reconstruction" if case.incident_basis == "historical"
            else "specification_derived_synthetic_case"
        ),
        "redaction_record": "synthetic identifiers only; no restricted data or transcripts",
        "content_hashes": content_hashes,
        "variant_bindings": [{
            "variant_id": "python313-windows-in-process",
            "provider_variant": "provider-neutral",
            "runtime_variant": "python-3.13",
            "os": "windows",
            "transport": "in_process_fake",
        }],
    }
    files["input/source-manifest.json"] = _json_bytes(source)
    graders = json.loads(files["graders/required.json"])["required_graders"]
    definition = {
        "schema_id": "ars://evals/fixture-definition",
        "schema_version": "1.0.0",
        "fixture_id": case_id,
        "fixture_revision": "r1",
        "title": case.title,
        "owner": "evaluation_owner",
        "status": "authored",
        "incident_basis": case.incident_basis,
        "input_fidelity": case.input_fidelity,
        "risk_tier": "R2",
        "assurance_lanes": list(case.assurance_lanes),
        "failure_class": case.failure_class,
        "priority": case.priority,
        "gate_stage": case.gate_stage,
        "source_manifest_hash": sha256_hex(files["input/source-manifest.json"]),
        "decision_refs": ["P-030"],
        "policy_versions": ["canonical-policy-v1"],
        "schema_versions": ["fixture-definition-v1"],
        "confidentiality": "internal",
        "permitted_consumers": ["eval"],
        "setup_hash": sha256_hex(canonical_bytes(case.action)),
        "stimulus_hash": content_hashes["input/stimulus.json"],
        "pre_control_oracle_hash": content_hashes["expected/pre-control.json"],
        "post_control_oracle_hash": content_hashes["expected/post-control.json"],
        "required_trajectory": list(case.required),
        "forbidden_trajectory": list(case.forbidden),
        "allowed_terminal_states": ["decided"],
        "expected_stop_semantics": "fail_closed",
        "required_graders": graders,
        "threshold_policy_ids": ["exact-property-v1"],
        "required_evidence_classes": [case.contract, "normalized_trace"],
        "known_bad_reference_hash": content_hashes["expected/pre-control.json"],
        "known_good_reference_hash": content_hashes["expected/post-control.json"],
        "mutation_ids": [f"{case.contract}-violation"],
        "safe_variation_ids": ["identifier-renaming"],
        "calibration_record_id": None,
        "retention_class": "R0",
        "retention_rule_id": "R0:synthetic_fixture_package",
        "redaction_policy_id": "redaction-v1",
    }
    files["fixture.yaml"] = yaml.safe_dump(definition, sort_keys=False).encode()
    return files


def materialize(root: Path, *, check: bool = False) -> None:
    """Generate fixtures or check that existing files match exactly.

    Args:
        root: Destination containing the control/store fixture directories.
        check: Compare existing files without writing when true.
    """
    materialize_cases(
        root,
        cases=CASES,
        package_builder=_package,
        shard_name="control/store",
        check=check,
    )


def main() -> None:
    """Run the CLI in deterministic generation or check-only mode."""
    run_cli(
        materialize,
        default_root=_REPO_ROOT / ".research-system" / "evals" / "fixtures",
    )


if __name__ == "__main__":
    main()
