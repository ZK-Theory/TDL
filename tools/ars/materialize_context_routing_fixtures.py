"""Materialize the staged WP4.5 context/routing fixture corpus."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from research_system.canonical import canonical_bytes, sha256_hex  # noqa: E402
from tools.ars.fixture_materializer import (  # noqa: E402
    materialize_cases,
    run_cli,
)


@dataclass(frozen=True, slots=True)
class Case:
    """Define one staged context/routing fixture case."""

    title: str
    contract: str
    failure_class: str
    incident_basis: str
    input_fidelity: str
    risk_tier: str
    assurance_lanes: tuple[str, ...]
    action: dict[str, Any]
    pre: dict[str, Any]
    post: dict[str, Any]
    required: tuple[str, ...]
    forbidden: tuple[str, ...]
    graders: tuple[str, ...]
    priority: str
    gate_stage: str = "p0_materialization"


CASES = {
    "F-021": Case(
        "Governing amendment omitted",
        "governing_amendment_recall",
        "amendment_omission",
        "historical",
        "reconstructed",
        "R2",
        ("context", "governance"),
        {
            "operation": "compile_context",
            "base_revision": "pre-amendment",
            "governing_amendment": "P-028",
            "amendment_available": True,
        },
        {"amendment_included": False, "unexplained_omissions": 0, "readiness_satisfied": True},
        {"amendment_included": True, "unexplained_omissions": 0, "stale_packet_rejected": True},
        ("GoverningSourcesResolved", "AmendmentIncluded", "ContextManifestIssued"),
        ("StaleContextAccepted", "AmendmentSilentlyOmitted"),
        ("D", "T", "M"),
        "P1",
    ),
    "F-022": Case(
        "Correlated reviewer contexts",
        "reviewer_independence_evidence",
        "correlated_review",
        "specification",
        "synthetic",
        "R3",
        ("authority", "scientific_review"),
        {
            "operation": "grade_independence",
            "producer_family": "family-a",
            "reviewer_family": "family-a",
            "shared_context_hash": True,
            "role_labels_differ": True,
        },
        {"independence_satisfied": True, "evidence_compared": ["role_labels"]},
        {
            "independence_satisfied": False,
            "required_grade": "cross_family_context_independent",
            "replacement_review_requested": True,
        },
        ("IndependenceEvidenceCompared", "IndependenceUnavailableRecorded"),
        ("RoleLabelTreatedAsIndependence", "CorrelatedReviewAccepted"),
        ("D", "T", "M", "H"),
        "P0",
    ),
    "F-025": Case(
        "Orchestrator scope-collapse retrieval",
        "mandatory_scope_closure",
        "retrieval_scope_collapse",
        "historical",
        "reconstructed",
        "R3",
        ("context", "governance", "claim"),
        {
            "operation": "retrieve_mandatory_closure",
            "scope_revision": "stage2-r22",
            "required_members": 22,
            "stale_completion_prose": True,
        },
        {"included_members": 8, "completion_recommended": True, "governing_precedence_preserved": False},
        {
            "included_members": 22,
            "completion_recommended": False,
            "governing_precedence_preserved": True,
            "stale_conflict_labeled": True,
        },
        ("MandatoryClosureResolved", "ScopeRevisionBound", "LowerAuthorityConflictRecorded"),
        ("ScopeCollapsed", "FullStageCompletionRecommended"),
        ("D", "T", "M", "H"),
        "P0",
    ),
    "F-026": Case(
        "Implementer scientific-closure retrieval",
        "implementer_scientific_closure",
        "retrieval_shortcut",
        "domain_coverage",
        "synthetic",
        "R2",
        ("context", "representation", "stochastic", "topology", "provenance"),
        {
            "operation": "compile_implementer_packet",
            "required_controls": ["frozen_transform", "null_invariance", "coherent_vintage", "stop_rules"],
            "distractors": ["refit", "stale_input", "producer_pass"],
        },
        {"selected_shortcut": "refit", "required_controls_included": 1, "producer_flag_trusted": True},
        {
            "selected_shortcut": None,
            "required_controls_included": 4,
            "producer_flag_trusted": False,
            "coherent_vintage": True,
        },
        ("ScientificClosureResolved", "FrozenTransformBound", "NullPreflightBound", "VintageBound"),
        ("RefitShortcutIncluded", "ProducerPassTrusted"),
        ("D", "T", "R", "M", "P"),
        "P0",
    ),
    "F-027": Case(
        "Optional-index deletion equivalence",
        "optional_index_deletion_equivalence",
        "optional_index_authority",
        "specification",
        "synthetic",
        "R1",
        ("context", "provenance"),
        {
            "operation": "compile_with_optional_index",
            "index_states": ["complete", "deleted"],
            "direct_sources_available": True,
        },
        {"mandatory_hashes_equal": False, "index_treated_as_authority": True},
        {"mandatory_hashes_equal": True, "index_treated_as_authority": False, "fallback_recorded": True},
        ("OptionalIndexUnavailableRecorded", "DirectSourceFallbackUsed", "ContextManifestIssued"),
        ("MandatorySelectionChanged", "IndexAbsenceLoweredAuthority"),
        ("D", "T"),
        "P0",
    ),
    "F-028": Case(
        "Budget overflow fails closed",
        "context_budget_fail_closed",
        "context_budget_overflow",
        "specification",
        "synthetic",
        "R2",
        ("context", "governance", "operations"),
        {
            "operation": "compile_over_budget_context",
            "reference_count": 12000,
            "reference_ceiling": 10000,
            "provider_count": 9000,
            "provider_capacity_80pct": 8000,
        },
        {"packet_issued": True, "mandatory_material_omitted": True},
        {
            "packet_issued": False,
            "reason": "context_budget_exceeded",
            "both_gate_evidence_recorded": True,
            "safe_options_returned": True,
        },
        ("ReferenceGateMeasured", "ProviderGateMeasured", "ContextCompilationBlocked"),
        ("ContextPacketIssued", "MandatoryMaterialTruncated"),
        ("D", "T", "O"),
        "P0",
    ),
    "F-031": Case(
        "Deterministic eligibility-first routing",
        "deterministic_eligibility_routing",
        "route_nondeterminism",
        "specification",
        "synthetic",
        "R3",
        ("routing", "governance", "operations"),
        {
            "operation": "route_with_snapshot",
            "candidate_orders": [["a", "b", "c"], ["c", "a", "b"]],
            "telemetry_changed_live": True,
            "suspended_family": "family-c",
        },
        {"routes_equal": False, "ineligible_route_ranked": True, "coverage_loss_reported": False},
        {
            "routes_equal": True,
            "only_eligible_ranked": True,
            "live_telemetry_ignored": True,
            "coverage_failure": "r3_family_coverage_insufficient",
        },
        ("EligibilityEvaluated", "RouteRanked", "FamilyCoverageRecomputed"),
        ("IneligibleRouteSelected", "LiveTelemetryRead", "AffectedDispatchIssued"),
        ("D", "T", "O", "M"),
        "P0",
    ),
    "F-033": Case(
        "Producer correlation and verifier feasibility",
        "predispatch_verifier_feasibility",
        "verifier_unavailable",
        "specification",
        "synthetic",
        "R3",
        ("routing", "authority", "scientific_review", "operations"),
        {
            "operation": "route_producer_with_verifier_witness",
            "producer_family": "family-a",
            "eligible_verifiers": [],
            "nominal_same_family_verifier": True,
        },
        {"producer_dispatched": True, "independence_checked_after_completion": True},
        {
            "producer_dispatched": False,
            "reason": "independence_unavailable",
            "verifier_witness_bound": True,
            "role_switch_ignored": True,
        },
        ("VerifierFeasibilityEvaluated", "IndependenceUnavailableRecorded"),
        ("ProducerCommandIssued", "RoleSwitchAcceptedAsIndependent"),
        ("D", "T", "O", "M", "H"),
        "P0",
    ),
    "F-035": Case(
        "Requirement-scope integrity and two-key non-compensation",
        "two_key_assurance_non_compensation",
        "requirement_capture",
        "specification",
        "synthetic",
        "R3",
        ("assurance", "authority", "claim"),
        {
            "operation": "accept_assurance_requirement",
            "authored_risk": "R2",
            "action_risk": "R3",
            "omitted_lane": "representation",
            "key_a_passed": True,
            "key_b_passed": False,
        },
        {"requirement_accepted": True, "manager_only_authority": True, "one_key_compensated": True},
        {
            "requirement_accepted": False,
            "reason": "assurance_requirement_scope_unconfirmed",
            "key_a_passed": True,
            "key_b_passed": False,
            "non_compensable": True,
            "step_up_required": True,
        },
        ("RequirementScopeReviewed", "ActionRiskRaised", "BothValidityKeysEvaluated"),
        ("ProducerDispatchIssued", "OneKeyCompensated", "ClaimPromoted"),
        ("D", "T", "R", "M", "H"),
        "P0",
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
    selectors = [case.contract]
    if grader_class == "D":
        selectors.extend(["input/stimulus.json", "expected/post-control.json"])
    elif grader_class == "T":
        selectors.append("expected/trajectory.json")
    else:
        selectors.extend(["input/stimulus.json", "expected/trajectory.json"])
    return {
        "grader_id": f"{case_id.lower()}-{suffixes[grader_class]}",
        "grader_class": grader_class,
        "grader_version": "context-routing-v1",
        "critical": True,
        "required": True,
        "independence_requirement": (
            "cross_family_context_independent" if grader_class == "M" else "deterministic_independent"
        ),
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
            "schema_id": "ars://evals/fixture-stimulus",
            **common,
            "stimulus_kind": "context_routing_contract",
            "payload": {"contract": case.contract, "action": case.action},
        }
    if name in {"expected/pre-control.json", "expected/post-control.json"}:
        controlled = name.endswith("post-control.json")
        return {
            "schema_id": "ars://evals/fixture-oracle",
            **common,
            "oracle_kind": "post_control" if controlled else "pre_control",
            "assertions": [
                {
                    "property": case.contract,
                    "satisfied": controlled,
                    "derived_from": ["input/stimulus.json", "normalized_trace"],
                    "expected_evidence": case.post if controlled else case.pre,
                }
            ],
        }
    if name == "expected/trajectory.json":
        return {
            "schema_id": "ars://evals/fixture-trajectory",
            **common,
            "required": list(case.required),
            "forbidden": list(case.forbidden),
        }
    if name == "graders/required.json":
        return {
            "schema_id": "ars://evals/fixture-grader-manifest",
            **common,
            "required_graders": [_grader(case_id, case, item) for item in case.graders],
        }
    raise ValueError(name)


def _package(case_id: str, case: Case) -> dict[str, bytes]:
    """Return the complete serialized eight-file fixture package."""
    files = {
        "README.md": (
            f"# {case_id}: {case.title}\n\n"
            f"Staged WP4.5 fixture for `{case.contract}`. The package is authored "
            "but not calibrated or active. Its oracle derives from minimized input bytes and normalized trace evidence.\n"
        ).encode(),
    }
    for name in (
        "input/stimulus.json",
        "expected/pre-control.json",
        "expected/post-control.json",
        "expected/trajectory.json",
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
            "docs/plans/agentic-research-system/design/03-context-memory-and-retrieval.md",
            "docs/plans/agentic-research-system/design/04-agent-roles-and-model-routing.md",
            "docs/plans/agentic-research-system/design/05-research-assurance-and-independent-review.md",
            "docs/plans/agentic-research-system/design/06-evaluation-observability-and-audit.md",
        ],
        "reconstruction_method": (
            "historical_minimized_reconstruction"
            if case.incident_basis == "historical"
            else "specification_derived_synthetic_case"
        ),
        "redaction_record": "synthetic identifiers only; no restricted data or transcripts",
        "content_hashes": content_hashes,
        "variant_bindings": [
            {
                "variant_id": "python313-windows-in-process",
                "provider_variant": "provider-neutral",
                "runtime_variant": "python-3.13",
                "os": "windows",
                "transport": "in_process_fake",
            }
        ],
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
        "risk_tier": case.risk_tier,
        "assurance_lanes": list(case.assurance_lanes),
        "failure_class": case.failure_class,
        "priority": case.priority,
        "gate_stage": case.gate_stage,
        "source_manifest_hash": sha256_hex(files["input/source-manifest.json"]),
        "decision_refs": ["P-028", "P-029", "P-030"],
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
    """Generate this shard or check its existing files exactly.

    Args:
        root: Parent directory containing all fixture shards.
        check: Compare this shard's files without writing when true.
    """
    materialize_cases(
        root,
        cases=CASES,
        package_builder=_package,
        shard_name="context/routing",
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
