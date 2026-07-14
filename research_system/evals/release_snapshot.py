"""Publication-only typed snapshot of the exact offline release derivation."""

from __future__ import annotations

from dataclasses import asdict
from types import MappingProxyType
from typing import Any
import uuid

from research_system.adapters.parity import PolicyParityReport
from research_system.adapters.parity_evidence import FakeAdapterParityEvidence
from research_system.canonical import canonical_bytes, jsonable, sha256_hex
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
from research_system.ids import validate_id
from research_system.policy.models import (
    CanonicalPolicyBundle,
    Control,
    ControlApplicability,
    PolicyControlApplicability,
    ProviderEvidenceRequirement,
)

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


def _stable_id(kind: str, value: object) -> str:
    raw = bytearray.fromhex(sha256_hex(canonical_bytes(value)))[:16]
    raw[6] = (raw[6] & 0x0F) | 0x70
    raw[8] = (raw[8] & 0x3F) | 0x80
    prefixes = {
        "actor": "act",
        "evaluation_run": "run",
        "grader_result": "grr",
        "trace": "trc",
    }
    return validate_id(f"{prefixes[kind]}_{uuid.UUID(bytes=bytes(raw))}", kind)


def _result_snapshot(result: GraderResult) -> dict[str, Any]:
    return {
        "result_key": list(result.result_key),
        "verdict": result.verdict,
        "severity": result.severity,
        "critical": result.critical,
        "required": result.required,
        "subject_hash": result.subject_hash,
        "trace_hash": result.trace_hash,
        "oracle_hash": result.oracle_hash,
        "policy_hash": result.policy_hash,
        "threshold_policy_hash": result.threshold_policy_hash,
        "independently_recomputed": result.independently_recomputed,
        "producer_family": result.producer_family,
        "grader_family": result.grader_family,
        "context_relationship": result.context_relationship,
        "limitations": list(result.limitations),
        "redactions": list(result.redactions),
        "duration_ms": result.duration_ms,
        "cost_microunits": result.cost_microunits,
        "supersedes": result.supersedes,
    }


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


def build_release_snapshot_documents(
    evidence: EvaluationEvidence,
    scenarios: tuple[Gate3ScenarioResult, ...],
    source: dict[str, Any],
    *,
    project_id: str,
    store_identity: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Serialize the existing typed W6/W7/W8 release inputs deterministically."""
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
            "release_results": [
                _result_snapshot(item)
                for item in evidence.results
            ],
            "variant_rows": [asdict(item) for item in evidence.variant_rows],
            "variant_executions": [
                asdict(item) for item in evidence.variant_executions
            ],
            "canonical_policy_bundle": asdict(evidence.canonical_policy_bundle),
            "policy_applicability": asdict(evidence.policy_applicability),
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
        "canonical_policy_bundle_id": (
            evidence.canonical_policy_bundle.canonical_policy_bundle_id
        ),
        "canonical_policy_bundle_hash": evidence.canonical_policy_bundle.content_hash,
        "policy_control_applicability_id": (
            evidence.policy_applicability.applicability_id
        ),
        "policy_control_applicability_hash": (
            evidence.policy_applicability.applicability_hash
        ),
    }
    return manifest, control


def _coverage(value: dict[str, Any]) -> P0Coverage:
    return P0Coverage(
        coverage_revision=value["coverage_revision"],
        transport=value["transport"],
        selected_fixture_revisions=tuple(
            tuple(item) for item in value["selected_fixture_revisions"]
        ),
        required_result_keys=tuple(
            tuple(item) for item in value["required_result_keys"]
        ),
        accepted_grader_classes=tuple(value["accepted_grader_classes"]),
        unavailable_grader_classes=tuple(value["unavailable_grader_classes"]),
        omitted_gate5=tuple(
            DeferredCapability(**item) for item in value["omitted_gate5"]
        ),
        omitted_p0=tuple(
            DeferredCatalogueCase(**item) for item in value["omitted_p0"]
        ),
        scenarios=tuple(value["scenarios"]),
        gate5_authorized=value["gate5_authorized"],
    )


def _bindings(rows: list[dict[str, Any]]) -> ReleaseBindings:
    keys = tuple(tuple(row["result_key"]) for row in rows)

    def mapping(field: str) -> MappingProxyType:
        return MappingProxyType(
            {tuple(row["result_key"]): row[field] for row in rows}
        )

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
    key = tuple(value["result_key"])
    seed = ["release-result", list(key)]
    return GraderResult(
        grader_result_id=_stable_id("grader_result", seed),
        evaluation_run_id=_stable_id("evaluation_run", seed),
        fixture_id=key[0],
        fixture_revision=key[1],
        grader_id=key[2],
        grader_class=key[3],
        grader_version=key[4],
        variant_id=key[5],
        verdict=value["verdict"],
        severity=value["severity"],
        critical=value["critical"],
        required=value["required"],
        subject_hash=value["subject_hash"],
        trace_hash=value["trace_hash"],
        oracle_hash=value["oracle_hash"],
        policy_hash=value["policy_hash"],
        threshold_policy_hash=value["threshold_policy_hash"],
        evidence_refs=(_stable_id("trace", seed),),
        independently_recomputed=value["independently_recomputed"],
        producer_family=value["producer_family"],
        grader_family=value["grader_family"],
        context_relationship=value["context_relationship"],
        limitations=tuple(value["limitations"]),
        redactions=tuple(value["redactions"]),
        duration_ms=value["duration_ms"],
        cost_microunits=value["cost_microunits"],
        executed_by_actor_id=_stable_id("actor", seed),
        supersedes=value["supersedes"],
    )


def _variant_execution(value: dict[str, Any]) -> VariantExecutionEvidence:
    return VariantExecutionEvidence(
        matrix_row=Gate5VariantRow(**value["matrix_row"]),
        first_normalized_decision_hash=value["first_normalized_decision_hash"],
        second_normalized_decision_hash=value["second_normalized_decision_hash"],
        decisions_equal=value["decisions_equal"],
        grader_result_keys=tuple(
            tuple(item) for item in value["grader_result_keys"]
        ),
        grader_result_bindings=tuple(
            (tuple(item[0]), *item[1:])
            for item in value["grader_result_bindings"]
        ),
        observed_assertions=tuple(
            ObservedAssertionEvidence(**item)
            for item in value["observed_assertions"]
        ),
        execution_evidence_hash=value["execution_evidence_hash"],
    )


def _bundle(value: dict[str, Any]) -> CanonicalPolicyBundle:
    return CanonicalPolicyBundle(
        value["canonical_policy_bundle_id"],
        value["revision"],
        value["content_hash"],
        tuple(Control(**item) for item in value["controls"]),
    )


def _applicability(value: dict[str, Any]) -> PolicyControlApplicability:
    controls = tuple(
        ControlApplicability(
            control_id=item["control_id"],
            control_revision=item["control_revision"],
            required_risk_tiers=tuple(item["required_risk_tiers"]),
            required_operation_classes=tuple(item["required_operation_classes"]),
            provider_requirements=tuple(
                ProviderEvidenceRequirement(**requirement)
                for requirement in item["provider_requirements"]
            ),
        )
        for item in value["controls"]
    )
    return PolicyControlApplicability(
        applicability_id=value["applicability_id"],
        applicability_hash=value["applicability_hash"],
        decision_ref=value["decision_ref"],
        decision_record_hash=value["decision_record_hash"],
        bundle_id=value["bundle_id"],
        bundle_revision=value["bundle_revision"],
        bundle_hash=value["bundle_hash"],
        controls=controls,
    )


def _parity_evidence(value: dict[str, Any]) -> FakeAdapterParityEvidence:
    return FakeAdapterParityEvidence(
        **{
            **value,
            "matrix_tuple": tuple(value["matrix_tuple"]),
            "grader_result_keys": tuple(
                tuple(item) for item in value["grader_result_keys"]
            ),
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
    scenarios = tuple(
        Gate3ScenarioResult(**{**item, "event_types": tuple(item["event_types"])})
        for item in values
    )
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
    """Reconstruct frozen producer evidence and re-derive the source decision."""
    coverage = _coverage(manifest["coverage"])
    bindings = _bindings(manifest["release_bindings"])
    results = tuple(_result(item) for item in manifest["release_results"])
    bundle = _bundle(manifest["canonical_policy_bundle"])
    applicability = _applicability(manifest["policy_applicability"])
    evidence = EvaluationEvidence(
        coverage=coverage,
        bindings=bindings,
        results=results,
        variant_executions=tuple(
            _variant_execution(item) for item in manifest["variant_executions"]
        ),
        variant_rows=tuple(
            Gate5VariantRow(**item) for item in manifest["variant_rows"]
        ),
        canonical_policy_bundle=bundle,
        parity_report=_parity_report(manifest["parity_report"]),
        policy_applicability=applicability,
        parity_evidence=tuple(
            _parity_evidence(item) for item in manifest["parity_evidence"]
        ),
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
        or control["canonical_policy_bundle_id"]
        != bundle.canonical_policy_bundle_id
        or control["canonical_policy_bundle_hash"] != bundle.content_hash
        or control["policy_control_applicability_id"]
        != applicability.applicability_id
        or control["policy_control_applicability_hash"]
        != applicability.applicability_hash
    ):
        raise ValueError("release snapshot control binding mismatch")
    record, outcome = build_release_decision(
        evidence,
        scenarios,
        decided_at=source["decided_at"],
        release_gate_decision_id=source["release_gate_decision_id"],
    )
    expected_incompatible = {
        item.result_key
        for item in results
        if item.verdict == "unable_to_grade"
    }
    observed_incompatible = {tuple(item[0]) for item in outcome["incompatible"]}
    blocking_fixtures = {
        item.fixture_id
        for item in results
        if item.verdict in {"fail", "unable_to_grade", "fixture_error"}
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
