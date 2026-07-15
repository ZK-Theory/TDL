"""Publication-only typed snapshot of the exact offline release derivation."""

from __future__ import annotations

import copy
from dataclasses import asdict
from types import MappingProxyType
from typing import Any

from research_system.adapters.parity import PolicyParityReport
from research_system.adapters.parity_evidence import FakeAdapterParityEvidence
from research_system.canonical import jsonable
from research_system.errors import ArsError
from research_system.evals.coverage import (
    DeferredCapability,
    DeferredCatalogueCase,
    P0Coverage,
)
from research_system.evals.harness import (
    EvaluationEvidence,
    ReleaseBindings,
    build_release_decision,
    decision_document,
)
from research_system.evals.models import GraderResult
from research_system.evals.scenarios import Gate3ScenarioResult
from research_system.evals.variants import (
    Gate5VariantRow,
    ObservedAssertionEvidence,
    VariantExecutionEvidence,
)
from research_system.policy.loader import (
    ACCEPTED_DG55_DECISION_PAYLOAD,
    OPERATIONS,
    canonical_policy_bundle_from_payload,
    policy_control_applicability_from_payload,
)
from research_system.policy.models import CanonicalPolicyBundle, PolicyControlApplicability

_DERIVATION_VERSION = "wp5.3-release-publication-v1"
_SCENARIO_CONTRACT = {
    "A": {
        "event_types": (
            "RouteSelected",
            "ResourceGrantRequested",
            "LeaseClaimed",
            "ProviderCommandIssued",
            "ProviderReceiptRecorded",
        ),
        "producer_actor_id": "actor-claude-producer",
        "verifier_actor_id": "actor-codex-verifier",
        "provider_command_count": 1,
    },
    "B": {
        "event_types": (
            "RouteSelectionFailed",
            "RerouteEvaluated",
            "RouteSelected",
        ),
        "original_requirement_id": "asr-preserved-r3",
        "reroute_requirement_id": "asr-preserved-r3",
    },
    "C": {
        "event_types": ("StopRequested", "StopConfirmed", "ExecutionResumed"),
        "initial_epoch": 2,
        "resume_epoch": 3,
    },
    "D": {
        "event_types": ("CommandRecovered", "ReceiptReconstructed"),
        "published_batch_count": 1,
        "replay_integrity": "pass",
    },
    "E": {
        "event_types": ("RestrictedDataRequested", "DispatchDenied"),
        "decision_reason": "restricted_data_denied",
    },
}


def _result_snapshot(result: GraderResult) -> dict[str, Any]:
    return jsonable(asdict(result))


def _binding_snapshots(bindings: ReleaseBindings) -> list[dict[str, Any]]:
    return [
        {
            "result_key": list(key),
            "subject_hash": bindings.expected_subject_hashes[key],
            "trace_hash": bindings.expected_trace_hashes[key],
            "oracle_hash": bindings.expected_oracle_hashes[key],
            "policy_hash": bindings.expected_policy_hashes[key],
            "threshold_policy_hash": bindings.expected_threshold_policy_hashes[key],
            "independence": bindings.required_independence[key],
            "critical": bindings.required_criticality[key],
        }
        for key in bindings.required_result_keys
    ]


def _bundle_source(bundle: CanonicalPolicyBundle) -> dict[str, Any]:
    controls = {item.control_id: item for item in bundle.controls}
    return {
        "schema_version": "1.0.0",
        "canonical_policy_bundle_id": bundle.canonical_policy_bundle_id,
        "revision": bundle.revision,
        "controls": {
            control_id: {
                "revision": controls[control_id].revision,
                "semantic_class": controls[control_id].semantic_class,
                "critical": controls[control_id].critical,
                "failure_mode": controls[control_id].failure_mode,
            }
            for control_id in OPERATIONS
        },
    }


def _applicability_source(
    applicability: PolicyControlApplicability,
    bundle: CanonicalPolicyBundle,
) -> dict[str, Any]:
    controls = {item.control_id: item for item in applicability.controls}
    return {
        "schema_id": "ars://adapters/policy-control-applicability",
        "schema_version": "1.0.0",
        "applicability_id": applicability.applicability_id,
        "applicability_hash": applicability.applicability_hash,
        "decision_ref": applicability.decision_ref,
        "decision_payload": copy.deepcopy(ACCEPTED_DG55_DECISION_PAYLOAD),
        "decision_record_hash": applicability.decision_record_hash,
        "bundle": {
            "id": bundle.canonical_policy_bundle_id,
            "revision": bundle.revision,
            "hash": bundle.content_hash,
        },
        "controls": [
            {
                "control_id": item.control_id,
                "control_revision": item.control_revision,
                "required_risk_tiers": list(item.required_risk_tiers),
                "required_operation_classes": list(item.required_operation_classes),
                "provider_requirements": [asdict(requirement) for requirement in item.provider_requirements],
            }
            for scope in ACCEPTED_DG55_DECISION_PAYLOAD["control_applicability"]
            for item in (controls[scope["control_id"]],)
        ],
    }


def build_release_snapshot_documents(
    evidence: EvaluationEvidence,
    scenarios: tuple[Gate3ScenarioResult, ...],
    source: dict[str, Any],
    *,
    project_id: str,
    store_identity: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Serialize the existing typed W6/W7/W8 release inputs deterministically.

    Args:
        evidence: Complete typed producer evidence from the offline fake run.
        scenarios: Exact ordered W8 operations scenario results.
        source: Already-derived unpublished release decision document.
        project_id: Project identity bound to the canonical control store.
        store_identity: Exact canonical control-store identity.

    Returns:
        Strict evidence-manifest and control-binding documents.

    Raises:
        ArsError: If complete policy applicability and parity evidence is absent.
    """
    if (
        evidence.canonical_policy_bundle is None
        or evidence.policy_applicability is None
        or evidence.parity_report is None
    ):
        raise ArsError("release publication requires complete parity evidence")
    manifest = jsonable(
        {
            "schema_id": "ars://evals/release-publication-evidence",
            "schema_version": "1.0.0",
            "project_id": project_id,
            "release_decision": source,
            "coverage": asdict(evidence.coverage),
            "release_bindings": _binding_snapshots(evidence.bindings),
            "release_results": [_result_snapshot(item) for item in evidence.results],
            "variant_rows": [asdict(item) for item in evidence.variant_rows],
            "variant_executions": [asdict(item) for item in evidence.variant_executions],
            "canonical_policy_bundle": {
                **asdict(evidence.canonical_policy_bundle),
                "source": _bundle_source(evidence.canonical_policy_bundle),
            },
            "policy_applicability": {
                **asdict(evidence.policy_applicability),
                "source": _applicability_source(
                    evidence.policy_applicability,
                    evidence.canonical_policy_bundle,
                ),
            },
            "parity_evidence": [asdict(item) for item in evidence.parity_evidence],
            "parity_report": asdict(evidence.parity_report),
            "operations_scenarios": [asdict(item) for item in scenarios],
        }
    )
    control = {
        "schema_id": "ars://evals/release-control-binding",
        "schema_version": "1.0.0",
        "project_id": project_id,
        "store_identity": store_identity,
        "coverage_manifest_id": evidence.coverage.coverage_revision,
        "transport": evidence.coverage.transport,
        "gate5_authorized": evidence.coverage.gate5_authorized,
        "operations_scenarios": list(evidence.coverage.scenarios),
        "derivation_contract_version": _DERIVATION_VERSION,
        "canonical_policy_bundle_id": (evidence.canonical_policy_bundle.canonical_policy_bundle_id),
        "canonical_policy_bundle_hash": evidence.canonical_policy_bundle.content_hash,
        "policy_control_applicability_id": (evidence.policy_applicability.applicability_id),
        "policy_control_applicability_hash": (evidence.policy_applicability.applicability_hash),
    }
    return manifest, control


def _coverage(value: dict[str, Any]) -> P0Coverage:
    return P0Coverage(
        coverage_revision=value["coverage_revision"],
        transport=value["transport"],
        selected_fixture_revisions=tuple(tuple(item) for item in value["selected_fixture_revisions"]),
        required_result_keys=tuple(tuple(item) for item in value["required_result_keys"]),
        accepted_grader_classes=tuple(value["accepted_grader_classes"]),
        unavailable_grader_classes=tuple(value["unavailable_grader_classes"]),
        omitted_gate5=tuple(DeferredCapability(**item) for item in value["omitted_gate5"]),
        omitted_p0=tuple(DeferredCatalogueCase(**item) for item in value["omitted_p0"]),
        scenarios=tuple(value["scenarios"]),
        gate5_authorized=value["gate5_authorized"],
    )


def _bindings(rows: list[dict[str, Any]]) -> ReleaseBindings:
    keys = tuple(tuple(row["result_key"]) for row in rows)

    def mapping(field: str) -> MappingProxyType:
        return MappingProxyType({tuple(row["result_key"]): row[field] for row in rows})

    return ReleaseBindings(
        required_result_keys=keys,
        expected_subject_hashes=mapping("subject_hash"),
        expected_trace_hashes=mapping("trace_hash"),
        expected_oracle_hashes=mapping("oracle_hash"),
        expected_policy_hashes=mapping("policy_hash"),
        expected_threshold_policy_hashes=mapping("threshold_policy_hash"),
        required_independence=mapping("independence"),
        required_criticality=mapping("critical"),
    )


def _result(value: dict[str, Any]) -> GraderResult:
    return GraderResult(
        grader_result_id=value["grader_result_id"],
        evaluation_run_id=value["evaluation_run_id"],
        fixture_id=value["fixture_id"],
        fixture_revision=value["fixture_revision"],
        variant_id=value["variant_id"],
        grader_id=value["grader_id"],
        grader_class=value["grader_class"],
        grader_version=value["grader_version"],
        verdict=value["verdict"],
        severity=value["severity"],
        critical=value["critical"],
        required=value["required"],
        subject_hash=value["subject_hash"],
        trace_hash=value["trace_hash"],
        oracle_hash=value["oracle_hash"],
        policy_hash=value["policy_hash"],
        threshold_policy_hash=value["threshold_policy_hash"],
        evidence_refs=tuple(value["evidence_refs"]),
        independently_recomputed=value["independently_recomputed"],
        producer_family=value["producer_family"],
        grader_family=value["grader_family"],
        context_relationship=value["context_relationship"],
        limitations=tuple(value["limitations"]),
        redactions=tuple(value["redactions"]),
        duration_ms=value["duration_ms"],
        cost_microunits=value["cost_microunits"],
        executed_by_actor_id=value["executed_by_actor_id"],
        supersedes=value["supersedes"],
    )


def _variant_execution(value: dict[str, Any]) -> VariantExecutionEvidence:
    return VariantExecutionEvidence(
        matrix_row=Gate5VariantRow(**value["matrix_row"]),
        first_normalized_decision_hash=value["first_normalized_decision_hash"],
        second_normalized_decision_hash=value["second_normalized_decision_hash"],
        decisions_equal=value["decisions_equal"],
        expected_evidence_hash=value["expected_evidence_hash"],
        first_observed_evidence_hash=value["first_observed_evidence_hash"],
        second_observed_evidence_hash=value["second_observed_evidence_hash"],
        oracle_match=value["oracle_match"],
        grader_result_keys=tuple(tuple(item) for item in value["grader_result_keys"]),
        grader_result_bindings=tuple((tuple(item[0]), *item[1:]) for item in value["grader_result_bindings"]),
        observed_assertions=tuple(ObservedAssertionEvidence(**item) for item in value["observed_assertions"]),
        execution_evidence_hash=value["execution_evidence_hash"],
    )


def _bundle(value: dict[str, Any]) -> CanonicalPolicyBundle:
    bundle = canonical_policy_bundle_from_payload(value["source"])
    if jsonable(asdict(bundle)) != {k: v for k, v in value.items() if k != "source"}:
        raise ValueError("canonical policy bundle snapshot mismatch")
    return bundle


def _applicability(
    value: dict[str, Any],
    bundle: CanonicalPolicyBundle,
) -> PolicyControlApplicability:
    applicability = policy_control_applicability_from_payload(
        value["source"],
        bundle=bundle,
    )
    if jsonable(asdict(applicability)) != {key: item for key, item in value.items() if key != "source"}:
        raise ValueError("policy applicability snapshot mismatch")
    return applicability


def _parity_evidence(value: dict[str, Any]) -> FakeAdapterParityEvidence:
    return FakeAdapterParityEvidence(
        **{
            **value,
            "matrix_tuple": tuple(value["matrix_tuple"]),
            "grader_result_keys": tuple(tuple(item) for item in value["grader_result_keys"]),
        }
    )


def _parity_report(value: dict[str, Any]) -> PolicyParityReport:
    return PolicyParityReport(
        **{
            **value,
            "rows": tuple(value["rows"]),
            "blocking_controls": tuple(value["blocking_controls"]),
        }
    )


def _scenarios(values: list[dict[str, Any]]) -> tuple[Gate3ScenarioResult, ...]:
    scenarios = tuple(Gate3ScenarioResult(**{**item, "event_types": tuple(item["event_types"])}) for item in values)
    if tuple(item.scenario_id for item in scenarios) != tuple("ABCDE"):
        raise ValueError("exact ordered operations scenarios A-E required")
    for scenario in scenarios:
        for field, expected in _SCENARIO_CONTRACT[scenario.scenario_id].items():
            if getattr(scenario, field) != expected:
                raise ValueError("operations scenario evidence mismatch")
    return scenarios


def rederive_release_from_snapshot(
    manifest: dict[str, Any],
    control: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Reconstruct frozen producer evidence and re-derive the source decision.

    Args:
        manifest: Strict stored producer-evidence manifest.
        control: Strict stored control-binding document.

    Returns:
        Re-derived decision document and the false Gate 5 disposition.

    Raises:
        ValueError: If any stored producer, policy, scenario, or control binding
            fails exact reconstruction and closure.
    """
    coverage = _coverage(manifest["coverage"])
    bindings = _bindings(manifest["release_bindings"])
    results = tuple(_result(item) for item in manifest["release_results"])
    bundle = _bundle(manifest["canonical_policy_bundle"])
    applicability = _applicability(manifest["policy_applicability"], bundle)
    evidence = EvaluationEvidence(
        coverage=coverage,
        bindings=bindings,
        results=results,
        variant_executions=tuple(_variant_execution(item) for item in manifest["variant_executions"]),
        variant_rows=tuple(Gate5VariantRow(**item) for item in manifest["variant_rows"]),
        canonical_policy_bundle=bundle,
        parity_report=_parity_report(manifest["parity_report"]),
        policy_applicability=applicability,
        parity_evidence=tuple(_parity_evidence(item) for item in manifest["parity_evidence"]),
    )
    scenarios = _scenarios(manifest["operations_scenarios"])
    source = manifest["release_decision"]
    if (
        control["project_id"] != manifest["project_id"]
        or control["coverage_manifest_id"] != coverage.coverage_revision
        or control["transport"] != coverage.transport
        or control["gate5_authorized"] is not coverage.gate5_authorized
        or control["operations_scenarios"] != list(coverage.scenarios)
        or control["derivation_contract_version"] != _DERIVATION_VERSION
        or control["canonical_policy_bundle_id"] != bundle.canonical_policy_bundle_id
        or control["canonical_policy_bundle_hash"] != bundle.content_hash
        or control["policy_control_applicability_id"] != applicability.applicability_id
        or control["policy_control_applicability_hash"] != applicability.applicability_hash
    ):
        raise ValueError("release snapshot control binding mismatch")
    record, outcome = build_release_decision(
        evidence,
        scenarios,
        decided_at=source["decided_at"],
        release_gate_decision_id=source["release_gate_decision_id"],
    )
    expected_incompatible = {item.result_key for item in results if item.verdict == "unable_to_grade"}
    observed_incompatible = {tuple(item[0]) for item in outcome["incompatible"]}
    blocking_fixtures = {
        item.fixture_id for item in results if item.verdict in {"fail", "unable_to_grade", "fixture_error"}
    }
    if (
        outcome["missing"]
        or outcome["unexpected"]
        or outcome["duplicates"]
        or observed_incompatible != expected_incompatible
        or len(outcome["blocking"]) != len(expected_incompatible)
        or len(blocking_fixtures) != 15
        or any(item.verdict == "fixture_error" for item in results)
        or len(results) != 302
        or len({item.result_key for item in results}) != 302
    ):
        raise ValueError("release snapshot result closure mismatch")
    return decision_document(record), coverage.gate5_authorized
