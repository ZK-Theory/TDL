"""Typed P0 execution evidence and strict release coordination."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType

import yaml

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.evals.calibration import calibrate_fixture
from research_system.evals.coverage import P0Coverage, load_p0_coverage
from research_system.evals.fixture_package import load_typed_definition
from research_system.evals.lifecycle import start_evaluation
from research_system.evals.models import GraderResult, ReleaseGateDecision, ResultKey, TraceEnvelope
from research_system.evals.release import decide_release
from research_system.evals.scenarios import Gate3ScenarioResult, run_gate3_scenario
from research_system.evals.trace import assert_trace_complete
from research_system.ids import new_id


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
    """
    coverage = load_p0_coverage(
        coverage_path,
        fixture_root=fixture_root,
        schema_root=schema_root,
    )
    root = Path(fixture_root)
    maps = {name: {} for name in ("subject", "trace", "oracle", "policy", "threshold", "independence", "criticality")}
    results = []
    for fixture_id, fixture_revision in coverage.selected_fixture_revisions:
        package_root = root / fixture_id
        definition = load_typed_definition(package_root)
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
        executed_by = new_id("actor")
        for grader in definition.required_graders:
            key = (fixture_id, fixture_revision, grader.grader_id, grader.grader_class, grader.grader_version)
            maps["subject"][key] = subject_hash
            maps["trace"][key] = trace_hash
            maps["oracle"][key] = oracle_hash
            maps["policy"][key] = policy_hash
            maps["threshold"][key] = threshold_hash
            maps["independence"][key] = grader.independence_requirement
            maps["criticality"][key] = grader.critical
            live = grader.grader_class in coverage.unavailable_grader_classes
            verdict = "unable_to_grade" if live else base_verdict
            results.append(
                GraderResult(
                    grader_result_id=new_id("grader_result"),
                    evaluation_run_id=run_id,
                    fixture_id=fixture_id,
                    fixture_revision=fixture_revision,
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
                    producer_family="reference-subject",
                    grader_family=("live-judgment-pending" if live else "deterministic-package-grader"),
                    context_relationship=grader.independence_requirement,
                    limitations=(("live judgment unavailable",) if live else ()),
                    redactions=(),
                    duration_ms=0,
                    cost_microunits=0,
                    executed_by_actor_id=executed_by,
                )
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
    return EvaluationEvidence(coverage, bindings, tuple(results))


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
    operations_status = (
        "pass"
        if {result.scenario_id for result in scenario_results} == set("ABCDE")
        else "blocked"
    )
    parity_status = "not_evaluated"  # Gate 5 dependency (obligation O11)
    decision = outcome["decision"]
    if decision == "pass" and not (
        operations_status == "pass" and parity_status == "pass"
    ):
        decision = "blocked"
    record = ReleaseGateDecision(
        release_gate_decision_id=new_id("release_gate_decision"),
        coverage_manifest_id=evidence.coverage.coverage_revision,
        baseline_identity="reference-pair-p0",
        candidate_identity="foundation-p0",
        evidence_snapshot_hash=sha256_hex(
            canonical_bytes(sorted(result.trace_hash for result in evidence.results))
        ),
        required_verdicts=tuple(
            (result.result_key, result.verdict) for result in evidence.results
        ),
        critical_failures=tuple(
            result.result_key
            for result in evidence.results
            if result.critical and result.verdict == "fail"
        ),
        parity_status=parity_status,
        operations_status=operations_status,
        decision=decision,
        decided_at=decided_at or datetime.now(timezone.utc).isoformat(),
        canonical_event_ref="unpublished:p0",  # obligation O12
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
    payload["required_verdicts"] = [
        [list(key), verdict] for key, verdict in record.required_verdicts
    ]
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
