from pathlib import Path

import pytest

from research_system.evals.harness import (
    build_release_decision,
    decide_p0_release,
    run_all_scenarios,
    run_p0_coverage,
)
from research_system.evals.lifecycle import start_evaluation


ROOT = Path(__file__).resolve().parents[3]
COVERAGE = ROOT / ".research-system" / "evals" / "p0-coverage.yaml"
FIXTURES = ROOT / ".research-system" / "evals" / "fixtures"
SCHEMAS = ROOT / ".research-system" / "schemas"


def test_evaluation_execution_identity_is_unique_with_lineage_separate():
    first = start_evaluation("F-001", "r1", "a" * 64)
    second = start_evaluation("F-001", "r1", "a" * 64, retry_of=first)
    assert first != second


def test_strict_release_consumes_exact_typed_results_and_blocks_missing_mh():
    evidence = run_p0_coverage(COVERAGE, fixture_root=FIXTURES, schema_root=SCHEMAS)
    assert len(evidence.results) == len(evidence.coverage.required_result_keys)
    assert len(evidence.results) == 302
    assert {result.result_key for result in evidence.results} == set(evidence.coverage.required_result_keys)
    assessment = decide_p0_release(evidence)
    assert assessment["decision"] == "blocked"
    assert assessment["missing"] == []
    assert assessment["unexpected"] == []
    assert assessment["duplicates"] == []
    s016 = {
        result.grader_class: result.verdict
        for result in evidence.results
        if result.fixture_id == "S-016"
    }
    assert s016 == {"D": "pass", "T": "pass", "O": "pass", "H": "unable_to_grade"}
    decision, raw = build_release_decision(
        evidence,
        run_all_scenarios(),
        decided_at="2026-07-11T00:00:00Z",
    )
    assert raw["decision"] == "blocked"
    assert decision.decision == "blocked"
    assert decision.parity_status == "pass"
    assert decision.policy_parity_report_id.startswith("ppr_")
    assert decision.policy_control_applicability_id.startswith("pca_")


def test_fake_p0_family_identity_reaches_cross_family_rejection():
    evidence = run_p0_coverage(COVERAGE, fixture_root=FIXTURES, schema_root=SCHEMAS)
    assert len(evidence.results) == len(evidence.coverage.required_result_keys)
    assert {result.result_key for result in evidence.results} == set(
        evidence.coverage.required_result_keys
    )
    retired_literals = {
        "reference-subject",
        "live-judgment-pending",
        "deterministic-package-grader",
    }
    observed_families = {
        family
        for result in evidence.results
        for family in (result.producer_family, result.grader_family)
    }
    assert observed_families == {"fake"}
    assert observed_families.isdisjoint(retired_literals)

    cross_family_keys = {
        key
        for key, requirement in evidence.bindings.required_independence.items()
        if requirement.startswith("cross_family")
    }
    assert cross_family_keys

    assessment = decide_p0_release(evidence)
    incompatible = dict(assessment["incompatible"])
    assert {
        key
        for key, reason in incompatible.items()
        if reason == "cross-family independence unavailable"
    } == cross_family_keys
    assert assessment["decision"] == "blocked"
    assert assessment["missing"] == []
    assert assessment["unexpected"] == []
    assert assessment["duplicates"] == []


def test_forged_producer_document_cannot_enter_release_path():
    with pytest.raises(TypeError, match="EvaluationEvidence"):
        decide_p0_release({"candidate_status": "pass", "results": []})


def test_verdicts_derive_from_calibration_not_constants():
    evidence = run_p0_coverage(COVERAGE, fixture_root=FIXTURES, schema_root=SCHEMAS)
    by_fixture = {}
    for result in evidence.results:
        by_fixture.setdefault(result.fixture_id, set()).add(result.verdict)
    assert "fixture_error" not in by_fixture["F-036"]
    assert "unable_to_grade" in by_fixture["F-036"]
    assert by_fixture["F-001"] <= {"pass", "unable_to_grade"}
    assert all(r.verdict == "unable_to_grade" for r in evidence.results if r.grader_class in {"M", "H"})
