"""Typed P0 execution evidence and strict release coordination."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType

import yaml

from research_system.adapters.parity import PolicyParityReport
from research_system.adapters.parity_evidence import FakeAdapterParityEvidence
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.evals.calibration import calibrate_fixture
from research_system.evals.coverage import P0Coverage, load_p0_coverage
from research_system.evals.errors import FixtureDefinitionError
from research_system.evals.fixture_package import load_typed_definition
from research_system.evals.lifecycle import start_evaluation
from research_system.evals.models import (
    GraderRequirement,
    GraderResult,
    ReleaseGateDecision,
    ResultKey,
    TraceEnvelope,
)
from research_system.evals.policies import (
    load_threshold_policies,
    require_calibration_policy,
)
from research_system.evals.release import BLOCKING, decide_release
from research_system.evals.scenarios import Gate3ScenarioResult, run_gate3_scenario
from research_system.evals.trace import assert_trace_complete
from research_system.evals.variants import Gate5VariantRow, VariantExecutionEvidence
from research_system.ids import new_id
from research_system.policy.models import CanonicalPolicyBundle, PolicyControlApplicability


@dataclass(frozen=True, slots=True)
class ReleaseBindings:
    """Per-result immutable expectations consumed by strict release."""

    required_result_keys: tuple[ResultKey, ...]
    expected_subject_hashes: Mapping[ResultKey, str]
    expected_trace_hashes: Mapping[ResultKey, str]
    expected_oracle_hashes: Mapping[ResultKey, str]
    expected_policy_hashes: Mapping[ResultKey, str]
    expected_threshold_policy_hashes: Mapping[ResultKey, str]
    required_independence: Mapping[ResultKey, str]
    required_criticality: Mapping[ResultKey, bool]


@dataclass(frozen=True, slots=True)
class EvaluationEvidence:
    """Non-forgeable typed evidence entering the release primitive."""

    coverage: P0Coverage
    bindings: ReleaseBindings
    results: tuple[GraderResult, ...]
    variant_executions: tuple[VariantExecutionEvidence, ...] = ()
    variant_rows: tuple[Gate5VariantRow, ...] = ()
    canonical_policy_bundle: CanonicalPolicyBundle | None = None
    parity_report: PolicyParityReport | None = None
    policy_applicability: PolicyControlApplicability | None = None
    parity_evidence: tuple[FakeAdapterParityEvidence, ...] = ()

    def __post_init__(self) -> None:
        if not all(isinstance(item, VariantExecutionEvidence) for item in self.variant_executions):
            raise TypeError("typed VariantExecutionEvidence required")
        if not all(isinstance(item, Gate5VariantRow) for item in self.variant_rows):
            raise TypeError("typed Gate5VariantRow required")
        if self.canonical_policy_bundle is not None and not isinstance(
            self.canonical_policy_bundle,
            CanonicalPolicyBundle,
        ):
            raise TypeError("typed CanonicalPolicyBundle required")
        if self.parity_report is not None and not isinstance(self.parity_report, PolicyParityReport):
            raise TypeError("typed PolicyParityReport required")
        if self.policy_applicability is not None and not isinstance(
            self.policy_applicability,
            PolicyControlApplicability,
        ):
            raise TypeError("typed PolicyControlApplicability required")
        if not all(isinstance(item, FakeAdapterParityEvidence) for item in self.parity_evidence):
            raise TypeError("typed FakeAdapterParityEvidence required")
        _rebuild_attached_parity(self)


def _rebuild_attached_parity(evidence: EvaluationEvidence) -> PolicyParityReport | None:
    """Rebuild parity solely from execution, result, applicability, and bundle sources."""
    artifacts_present = any(
        (
            evidence.variant_executions,
            evidence.variant_rows,
            evidence.canonical_policy_bundle is not None,
            evidence.parity_report is not None,
            evidence.policy_applicability is not None,
            evidence.parity_evidence,
        )
    )
    if not artifacts_present:
        return None
    if (
        evidence.canonical_policy_bundle is None
        or evidence.policy_applicability is None
        or evidence.parity_report is None
        or not evidence.variant_executions
        or not evidence.variant_rows
        or not evidence.parity_evidence
    ):
        raise ValueError("partial parity evidence is not admissible")
    from research_system.adapters.parity import build_parity_report
    from research_system.adapters.parity_evidence import build_fake_adapter_parity_evidence

    rebuilt_evidence = build_fake_adapter_parity_evidence(
        evidence.variant_executions,
        evidence.policy_applicability,
        evidence.canonical_policy_bundle,
        matrix_rows=evidence.variant_rows,
        results=evidence.results,
    )
    if rebuilt_evidence != evidence.parity_evidence:
        raise ValueError("attached parity evidence differs from execution-derived evidence")
    rebuilt_report = build_parity_report(
        evidence.canonical_policy_bundle,
        evidence.policy_applicability,
        rebuilt_evidence,
        executions=evidence.variant_executions,
        matrix_rows=evidence.variant_rows,
        results=evidence.results,
    )
    if rebuilt_report != evidence.parity_report:
        raise ValueError("attached parity report differs from execution-derived report")
    return rebuilt_report


@dataclass(frozen=True, slots=True)
class ExecutionContextIdentity:
    """Truthful execution identity, separated from grader role/profile labels."""

    actor_id: str
    family: str
    profile: str


ExecutionContextFactory = Callable[
    [
        str,
        str,
        str,
        str,
        GraderRequirement,
        bool,
        ExecutionContextIdentity | None,
    ],
    tuple[ExecutionContextIdentity, ExecutionContextIdentity],
]


def fake_execution_context_factory(
    transport: str,
    fixture_id: str,
    fixture_revision: str,
    run_id: str,
    grader: GraderRequirement,
    live_unavailable: bool,
    producer_context: ExecutionContextIdentity | None = None,
) -> tuple[ExecutionContextIdentity, ExecutionContextIdentity]:
    """Return the fake P0 producer/grader identities for one result row."""
    producer = producer_context or ExecutionContextIdentity(
        actor_id=new_id("actor"),
        family=transport,
        profile=f"reference-subject:{fixture_id}:{fixture_revision}:{run_id}",
    )
    grader_profile = "live-judgment-pending" if live_unavailable else "deterministic-package-grader"
    grader_context = ExecutionContextIdentity(
        actor_id=new_id("actor"),
        family=transport,
        profile=(f"{fixture_id}:{fixture_revision}:{grader.grader_class}:{grader.grader_id}:{grader_profile}"),
    )
    return producer, grader_context


def _fixture(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"fixture object required: {path}")
    return value


def run_p0_coverage(
    coverage_path: Path | str,
    *,
    fixture_root: Path | str,
    schema_root: Path | str,
    variant_matrix_path: Path | str | None = None,
    policy_root: Path | str | None = None,
    execution_context_factory: ExecutionContextFactory = (fake_execution_context_factory),
) -> EvaluationEvidence:
    """Assemble the typed release-evidence surface over all P0 packages.

    Non-M/H verdicts are derived from the real two-repetition calibration
    (``research_system.evals.calibration.calibrate_fixture``): a fixture whose
    calibration run reports ``blocking_verdict == "fixture_error"`` yields
    ``fixture_error`` for every non-live grader, otherwise ``pass``. Each
    fixture's calibration decisions are bound into a typed ``TraceEnvelope``
    that must pass ``assert_trace_complete`` before any verdict is derived.
    M/H (live-judgment) rows remain ``unable_to_grade`` regardless of
    calibration outcome, so the aggregate release decision stays ``blocked``.

    Args:
        coverage_path: Coverage manifest selecting exact fixture revisions.
        fixture_root: Root containing the selected fixture packages.
        schema_root: Root containing the accepted evaluation schemas.
        variant_matrix_path: Optional exact variant matrix path. Defaults to
            ``p0-variant-matrix.yaml`` beside the coverage manifest.
        policy_root: Optional canonical-policy directory. Defaults to the
            repository policy directory resolved from ``fixture_root``.
        execution_context_factory: Factory for typed producer/grader identities.

    Returns:
        Complete typed baseline, variant, applicability, and parity evidence.
    """
    coverage = load_p0_coverage(
        coverage_path,
        fixture_root=fixture_root,
        schema_root=schema_root,
    )
    root = Path(fixture_root)
    threshold_policies = load_threshold_policies(root.parent / "threshold-policies.yaml")
    require_calibration_policy(root.parent / "p0-calibration-policy.yaml")
    maps = {name: {} for name in ("subject", "trace", "oracle", "policy", "threshold", "independence", "criticality")}
    results = []
    for fixture_id, fixture_revision in coverage.selected_fixture_revisions:
        package_root = root / fixture_id
        definition = load_typed_definition(package_root)
        missing_policies = set(definition.threshold_policy_ids) - set(threshold_policies)
        if missing_policies:
            raise FixtureDefinitionError(
                f"{fixture_id} references undefined threshold policies: {sorted(missing_policies)}"
            )
        raw = _fixture(package_root / "fixture.yaml")
        calibration = calibrate_fixture(fixture_id, fixture_root=root)
        subject_hash = str(raw["known_good_reference_hash"])
        run_id = start_evaluation(fixture_id, fixture_revision, subject_hash)
        decisions = (
            *calibration.known_bad,
            *calibration.known_good,
            *(d for m in calibration.mutations for d in m.decisions),
        )
        trace = TraceEnvelope(
            trace_id=new_id("trace"),
            evaluation_run_id=run_id,
            fixture_id=fixture_id,
            fixture_revision=fixture_revision,
            subject_id=f"reference-pair:{fixture_id}",
            subject_hash=subject_hash,
            items=tuple(
                {
                    "kind": "calibration_decision",
                    "subject": d.subject,
                    "repetition": d.repetition,
                    "verdict": d.verdict,
                    "evidence_hash": d.evidence_hash,
                }
                for d in decisions
            ),
            issued_commands=(),
            issued_resources=(),
            route_decision_id=None,
            routing_evidence_snapshot_id=None,
            canonical_policy_bundle_id=None,
            adapter_manifest_version=None,
            resource_record_ids=(),
            tool_records=(),
            artefact_refs=(),
            review_refs=(),
            decision_refs=definition.decision_refs,
            claim_refs=(),
            present_evidence_classes=definition.required_evidence_classes,
            missing_segments=(),
            clock_source="deterministic_fake",
            ordering_method="calibration_sequence",
            redaction_record_hash="0" * 64,
            content_hash=sha256_hex(canonical_bytes([d.evidence_hash for d in decisions])),
            trace_complete=True,
        )
        assert_trace_complete(trace, definition)
        trace_hash = trace.content_hash
        base_verdict = "fixture_error" if calibration.blocking_verdict == "fixture_error" else "pass"
        oracle_hash = str(raw["post_control_oracle_hash"])
        policy_hash = sha256_hex(canonical_bytes(raw["policy_versions"]))
        threshold_hash = sha256_hex(canonical_bytes(raw["threshold_policy_ids"]))
        producer_context: ExecutionContextIdentity | None = None
        for grader in definition.required_graders:
            key = (
                fixture_id,
                fixture_revision,
                grader.grader_id,
                grader.grader_class,
                grader.grader_version,
                "baseline",
            )
            maps["subject"][key] = subject_hash
            maps["trace"][key] = trace_hash
            maps["oracle"][key] = oracle_hash
            maps["policy"][key] = policy_hash
            maps["threshold"][key] = threshold_hash
            maps["independence"][key] = grader.independence_requirement
            maps["criticality"][key] = grader.critical
            live = grader.grader_class in coverage.unavailable_grader_classes
            producer_candidate, grader_context = execution_context_factory(
                coverage.transport,
                fixture_id,
                fixture_revision,
                run_id,
                grader,
                live,
                producer_context,
            )
            if producer_context is None:
                producer_context = producer_candidate
            elif producer_candidate != producer_context:
                raise ValueError("producer execution context changed within run")
            verdict = "unable_to_grade" if live else base_verdict
            results.append(
                GraderResult(
                    grader_result_id=new_id("grader_result"),
                    evaluation_run_id=run_id,
                    fixture_id=fixture_id,
                    fixture_revision=fixture_revision,
                    variant_id="baseline",
                    grader_id=grader.grader_id,
                    grader_class=grader.grader_class,
                    grader_version=grader.grader_version,
                    verdict=verdict,
                    severity="critical",
                    critical=grader.critical,
                    required=True,
                    subject_hash=subject_hash,
                    trace_hash=trace_hash,
                    oracle_hash=oracle_hash,
                    policy_hash=policy_hash,
                    threshold_policy_hash=threshold_hash,
                    evidence_refs=(trace.trace_id,),
                    independently_recomputed=not live,
                    producer_family=producer_context.family,
                    grader_family=grader_context.family,
                    context_relationship=grader.independence_requirement,
                    limitations=(("live judgment unavailable",) if live else ()),
                    redactions=(),
                    duration_ms=0,
                    cost_microunits=0,
                    executed_by_actor_id=grader_context.actor_id,
                )
            )
    from research_system.adapters.fake import FakeTransport
    from research_system.evals.variants import (
        execute_gate5_variant_rows_twice,
        load_gate5_variant_rows,
    )

    rows = load_gate5_variant_rows(variant_matrix_path or root.parent / "p0-variant-matrix.yaml", coverage)
    variant_executions, variant_results = execute_gate5_variant_rows_twice(
        rows,
        coverage,
        fixture_root=root,
        schema_root=schema_root,
        baseline_results=tuple(results),
        fake_transport_factory=FakeTransport,
    )
    for result in variant_results:
        key = result.result_key
        maps["subject"][key] = result.subject_hash
        maps["trace"][key] = result.trace_hash
        maps["oracle"][key] = result.oracle_hash
        maps["policy"][key] = result.policy_hash
        maps["threshold"][key] = result.threshold_policy_hash
        maps["independence"][key] = result.context_relationship
        maps["criticality"][key] = result.critical
    results.extend(variant_results)
    coverage = replace(
        coverage,
        required_result_keys=tuple((*coverage.required_result_keys, *(item.result_key for item in variant_results))),
    )
    bindings = ReleaseBindings(
        required_result_keys=coverage.required_result_keys,
        expected_subject_hashes=MappingProxyType(maps["subject"]),
        expected_trace_hashes=MappingProxyType(maps["trace"]),
        expected_oracle_hashes=MappingProxyType(maps["oracle"]),
        expected_policy_hashes=MappingProxyType(maps["policy"]),
        expected_threshold_policy_hashes=MappingProxyType(maps["threshold"]),
        required_independence=MappingProxyType(maps["independence"]),
        required_criticality=MappingProxyType(maps["criticality"]),
    )
    from research_system.adapters.parity import build_parity_report
    from research_system.adapters.parity_evidence import build_fake_adapter_parity_evidence
    from research_system.policy.loader import load_canonical_policy_bundle, load_policy_control_applicability

    resolved_policy_root = Path(policy_root) if policy_root is not None else root.parents[1] / "policies"
    bundle = load_canonical_policy_bundle(resolved_policy_root / "canonical-policy.yaml")
    applicability = load_policy_control_applicability(
        resolved_policy_root / "gate5-policy-control-applicability.yaml", bundle=bundle
    )
    result_tuple = tuple(results)
    parity_evidence = build_fake_adapter_parity_evidence(
        variant_executions,
        applicability,
        bundle,
        matrix_rows=rows,
        results=result_tuple,
    )
    parity_report = build_parity_report(
        bundle,
        applicability,
        parity_evidence,
        executions=variant_executions,
        matrix_rows=rows,
        results=result_tuple,
    )
    return EvaluationEvidence(
        coverage=coverage,
        bindings=bindings,
        results=result_tuple,
        variant_executions=variant_executions,
        variant_rows=rows,
        canonical_policy_bundle=bundle,
        parity_report=parity_report,
        policy_applicability=applicability,
        parity_evidence=parity_evidence,
    )


def decide_p0_release(evidence: EvaluationEvidence) -> dict:
    """Route only typed execution evidence through the strict validator."""
    if not isinstance(evidence, EvaluationEvidence):
        raise TypeError("EvaluationEvidence required")
    return decide_release(evidence.bindings, evidence.results)


def run_all_scenarios() -> tuple[Gate3ScenarioResult, ...]:
    """Run Gate 3 operations scenarios A through E.

    Returns:
        One ``Gate3ScenarioResult`` per scenario, in ``A``-``E`` order.
    """
    return tuple(run_gate3_scenario(item) for item in "ABCDE")


def build_release_decision(
    evidence: EvaluationEvidence,
    scenario_results: tuple[Gate3ScenarioResult, ...],
    *,
    decided_at: str | None = None,
) -> tuple[ReleaseGateDecision, dict]:
    """Derive the attributed release decision; operations/parity fail closed.

    Args:
        evidence: Typed P0 execution evidence from ``run_p0_coverage``.
        scenario_results: Gate 3 scenario results from ``run_all_scenarios``.
        decided_at: ISO-8601 timestamp to record. Defaults to the current
            UTC time.

    Returns:
        A tuple of the immutable ``ReleaseGateDecision`` record and the raw
        ``decide_release`` outcome dict it was derived from.
    """
    outcome = decide_release(evidence.bindings, evidence.results)
    operations_status = "pass" if {result.scenario_id for result in scenario_results} == set("ABCDE") else "blocked"
    parity_invalid = False
    try:
        report = _rebuild_attached_parity(evidence)
    except (TypeError, ValueError):
        report = None
        applicability = None
        parity_invalid = True
    else:
        applicability = evidence.policy_applicability
    if parity_invalid:
        parity_status = "blocked"
    elif report is None:
        parity_status = "not_evaluated"
    elif report is not None and (
        report.passed
        and applicability is not None
        and report.applicability_id == applicability.applicability_id
        and report.applicability_hash == applicability.applicability_hash
    ):
        parity_status = "pass"
    elif report is not None:
        parity_status = "blocked"
    decision = outcome["decision"]
    if decision == "pass" and not (operations_status == "pass" and parity_status == "pass"):
        decision = "blocked"
    record = ReleaseGateDecision(
        release_gate_decision_id=new_id("release_gate_decision"),
        coverage_manifest_id=evidence.coverage.coverage_revision,
        baseline_identity="reference-pair-p0",
        candidate_identity="foundation-p0",
        evidence_snapshot_hash=sha256_hex(canonical_bytes(sorted(result.trace_hash for result in evidence.results))),
        required_verdicts=tuple((result.result_key, result.verdict) for result in evidence.results),
        critical_failures=tuple(
            result.result_key for result in evidence.results if result.critical and result.verdict in BLOCKING
        ),
        parity_status=parity_status,
        operations_status=operations_status,
        decision=decision,
        decided_at=decided_at or datetime.now(timezone.utc).isoformat(),
        canonical_event_ref="unpublished:p0",  # obligation O12
        policy_parity_report_id=(report.policy_parity_report_id if report else None),
        policy_parity_report_hash=(report.report_hash if report else None),
        policy_control_applicability_id=(applicability.applicability_id if applicability else None),
        policy_control_applicability_hash=(applicability.applicability_hash if applicability else None),
        rationale=outcome.get("reason"),
    )
    return record, outcome


def decision_document(record: ReleaseGateDecision) -> dict:
    """Serialize a release decision to its schema-valid JSON-ready form.

    Args:
        record: The immutable release-gate decision record.

    Returns:
        A JSON-ready dict including the ``schema_id``/``schema_version``
        constants required by ``release-gate-decision.schema.json``.
    """
    payload = asdict(record)
    payload["schema_id"] = "ars://evals/release-gate-decision"
    payload["schema_version"] = "1.0.0"
    payload["required_verdicts"] = [[list(key), verdict] for key, verdict in record.required_verdicts]
    payload["critical_failures"] = [list(key) for key in record.critical_failures]
    return payload


def stable_projection(document: dict) -> dict:
    """Return the forgery-checked, rerun-stable subset of a decision document.

    Excludes ``decided_at``, identities, and hashes that legitimately vary
    between reruns; ``required_verdicts`` is rerun-stable because verdict
    derivation is deterministic given the same fixture inputs.

    Args:
        document: A decision document as produced by ``decision_document``.

    Returns:
        The identity-free comparison subset used to detect divergence.
    """
    return {
        "coverage_manifest_id": document["coverage_manifest_id"],
        "decision": document["decision"],
        "operations_status": document["operations_status"],
        "parity_status": document["parity_status"],
        "required_verdicts": document["required_verdicts"],
        "critical_failures": document["critical_failures"],
    }
