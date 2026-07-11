"""Materialize the exact S-014/S-015/S-016 Gate 5 release tranche."""

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
    title: str
    contract: str
    failure_class: str
    lanes: tuple[str, ...]
    action: dict[str, Any]
    pre: dict[str, Any]
    post: dict[str, Any]
    required: tuple[str, ...]
    forbidden: tuple[str, ...]
    graders: tuple[str, ...]
    mutation_id: str


CASES = {
    "S-014": Case(
        "Backup restore and machine move",
        "restore_preflight_registered_topology",
        "restore_authority_before_verified_preflight",
        ("operations", "privacy", "provenance"),
        {
            "operation": "verify_restore_machine_move",
            "source_root": "synthetic://machine-a/control",
            "target_root": "synthetic://machine-b/control",
            "project_id": "project_synthetic_release",
            "store_id": "store_synthetic_release",
        },
        {
            "restore_preflight_status": "diagnostic_only",
            "failed_predicates": ["registered_topology_incomplete"],
            "writer_authority_attempted_before_verification": True,
            "registered_locations_complete": False,
        },
        {
            "restore_preflight_status": "verified",
            "failed_predicates": [],
            "writer_authority_attempted_before_verification": False,
            "registered_locations_complete": True,
        },
        ("RestorePreflightVerified", "RegisteredDeletionTopologyChecked"),
        ("WriterLeaseBeforeRestoreVerification", "EvidenceDeletionPending"),
        ("D", "T", "O", "P"),
        "remove_registered_backup_restore_closure",
    ),
    "S-015": Case(
        "Atomic supersession cycle rejection",
        "revision_qualified_supersession_cycle_rejection",
        "supersession_cycle_accepted_or_mutated",
        ("authority", "provenance"),
        {
            "operation": "supersede_task",
            "source": {"task_id": "task_c", "revision": 1},
            "replacement": {"task_id": "task_a", "revision": 1},
            "supersession_scope": ["research_authority"],
            "continuing_consumers": ["audit"],
        },
        {
            "cycle_accepted": True,
            "authority_unchanged": False,
            "rejection_reason": None,
            "rejected_receipt_count": 0,
        },
        {
            "cycle_accepted": False,
            "authority_unchanged": True,
            "rejection_reason": "supersession_cycle",
            "rejected_receipt_count": 1,
        },
        ("SupersessionCycleRejected", "RejectedReceiptRecorded"),
        ("TaskSuperseded", "LifecycleAuthorityChanged"),
        ("D", "T"),
        "allow_supersession_cycle",
    ),
    "S-016": Case(
        "R3 provider outage without fallback",
        "r3_provider_outage_preserves_requirements",
        "subthreshold_provider_fallback",
        ("routing", "operations", "authority"),
        {
            "operation": "route_r3_review",
            "required_risk": "R3",
            "required_independence": "I3",
            "required_family_count": 2,
            "provider_status": "unavailable",
        },
        {
            "pre_dispatch_failure": None,
            "candidate_rejection_codes": [],
            "prepared_dispatch_count": 1,
            "fallback_issued": True,
            "provider_receipt_status": "completed",
            "provider_failure_code": None,
            "provider_output_present": True,
            "bindings_unchanged": False,
            "canonical_dispatch_events": 1,
            "canonical_acceptance_events": 1,
            "task_accepted": True,
        },
        {
            "pre_dispatch_failure": "no_eligible_route",
            "candidate_rejection_codes": [
                "provider_unavailable",
                "capability_insufficient",
                "independence_unavailable",
            ],
            "prepared_dispatch_count": 0,
            "fallback_issued": False,
            "provider_receipt_status": "incomplete",
            "provider_failure_code": "provider_unavailable",
            "provider_output_present": False,
            "bindings_unchanged": True,
            "canonical_dispatch_events": 0,
            "canonical_acceptance_events": 0,
            "task_accepted": False,
        },
        ("ProviderOutageRecorded", "NoEligibleRoute"),
        ("FallbackDispatchIssued", "TaskAccepted"),
        ("D", "T", "O", "H"),
        "allow_subthreshold_outage_fallback",
    ),
}


def _json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def _grader(case_id: str, case: Case, grader_class: str) -> dict[str, Any]:
    suffix = {
        "D": "outcome",
        "T": "trajectory",
        "H": "human-authority",
        "O": "operational",
        "P": "privacy-security",
    }[grader_class]
    return {
        "grader_id": f"{case_id.lower()}-{suffix}",
        "grader_class": grader_class,
        "grader_version": "gate5-release-tranche-v1",
        "critical": True,
        "required": True,
        "independence_requirement": "deterministic_independent",
        "evidence_selectors": [case.contract, "input/stimulus.json", "normalized_trace"],
    }


def _package(case_id: str, case: Case) -> dict[str, bytes]:
    common = {
        "schema_version": "1.0.0",
        "fixture_id": case_id,
        "fixture_revision": "r1",
    }
    docs = {
        "input/stimulus.json": {
            "schema_id": "ars://evals/fixture-stimulus",
            **common,
            "stimulus_kind": "gate5_release_tranche_contract",
            "payload": {"contract": case.contract, "action": case.action},
        },
        "expected/pre-control.json": {
            "schema_id": "ars://evals/fixture-oracle",
            **common,
            "oracle_kind": "pre_control",
            "assertions": [{
                "property": case.contract,
                "satisfied": False,
                "derived_from": ["input/stimulus.json", "normalized_trace"],
                "expected_evidence": case.pre,
            }],
        },
        "expected/post-control.json": {
            "schema_id": "ars://evals/fixture-oracle",
            **common,
            "oracle_kind": "post_control",
            "assertions": [{
                "property": case.contract,
                "satisfied": True,
                "derived_from": ["input/stimulus.json", "normalized_trace"],
                "expected_evidence": case.post,
            }],
        },
        "expected/trajectory.json": {
            "schema_id": "ars://evals/fixture-trajectory",
            **common,
            "required": list(case.required),
            "forbidden": list(case.forbidden),
        },
        "graders/required.json": {
            "schema_id": "ars://evals/fixture-grader-manifest",
            **common,
            "required_graders": [_grader(case_id, case, item) for item in case.graders],
        },
    }
    files = {name: _json(doc) for name, doc in docs.items()}
    files["README.md"] = (
        f"# {case_id}: {case.title}\n\nSynthetic Gate 5 release-tranche fixture. "
        "No live provider, restricted data, transcripts, or secrets.\n"
    ).encode()
    hashes = {name: sha256_hex(data) for name, data in files.items()}
    source = {
        "schema_id": "ars://evals/fixture-source-manifest",
        **common,
        "source_snapshot_date": "2026-07-10",
        "authoritative_refs": [
            "docs/plans/agentic-research-system/implementation/05b-wp5-4-release-tranche-plan.md",
            "docs/plans/agentic-research-system/design/06-evaluation-observability-and-audit.md",
        ],
        "reconstruction_method": "specification_derived_synthetic_case",
        "redaction_record": "synthetic identifiers only; no secrets or transcripts",
        "content_hashes": hashes,
        "variant_bindings": [{
            "variant_id": "python313-windows-in-process",
            "provider_variant": "provider-neutral",
            "runtime_variant": "python-3.13",
            "os": "windows",
            "transport": "in_process_fake",
        }],
    }
    files["input/source-manifest.json"] = _json(source)
    graders = docs["graders/required.json"]["required_graders"]
    definition = {
        "schema_id": "ars://evals/fixture-definition",
        **common,
        "title": case.title,
        "owner": "evaluation_owner",
        "status": "authored",
        "incident_basis": "specification",
        "input_fidelity": "synthetic",
        "risk_tier": "R3",
        "assurance_lanes": list(case.lanes),
        "failure_class": case.failure_class,
        "priority": "P1",
        "gate_stage": "foundation_release",
        "source_manifest_hash": sha256_hex(files["input/source-manifest.json"]),
        "decision_refs": ["D-G5-1(a)", "D-G5-2", "D-G5-3"],
        "policy_versions": ["canonical-policy-v1"],
        "schema_versions": ["fixture-definition-v1"],
        "confidentiality": "internal",
        "permitted_consumers": ["eval"],
        "setup_hash": sha256_hex(canonical_bytes(case.action)),
        "stimulus_hash": hashes["input/stimulus.json"],
        "pre_control_oracle_hash": hashes["expected/pre-control.json"],
        "post_control_oracle_hash": hashes["expected/post-control.json"],
        "required_trajectory": list(case.required),
        "forbidden_trajectory": list(case.forbidden),
        "allowed_terminal_states": ["decided"],
        "expected_stop_semantics": "fail_closed",
        "required_graders": graders,
        "threshold_policy_ids": ["exact-property-v1"],
        "required_evidence_classes": [case.contract, "normalized_trace"],
        "known_bad_reference_hash": hashes["expected/pre-control.json"],
        "known_good_reference_hash": hashes["expected/post-control.json"],
        "mutation_ids": [case.mutation_id],
        "safe_variation_ids": ["identifier-renaming"],
        "calibration_record_id": None,
        "retention_class": "R0",
        "retention_rule_id": "R0:synthetic_fixture_package",
        "redaction_policy_id": "redaction-v1",
    }
    files["fixture.yaml"] = yaml.safe_dump(definition, sort_keys=False).encode()
    return files


def materialize(root: Path, *, check: bool = False) -> None:
    """Materialize or check the Gate 5 release-tranche fixture corpus.

    Args:
        root: Directory containing the S-014/S-015/S-016 fixture packages.
        check: Verify existing files byte-for-byte instead of writing when true.
    """
    materialize_cases(
        root,
        cases=CASES,
        package_builder=_package,
        shard_name="Gate 5 release tranche",
        check=check,
    )


def main() -> None:
    """Run the release-tranche materializer command-line entry point."""
    run_cli(materialize, default_root=_REPO_ROOT / ".research-system" / "evals" / "fixtures")


if __name__ == "__main__":
    main()