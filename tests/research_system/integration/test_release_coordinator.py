from pathlib import Path

import pytest

from research_system.evals.harness import decide_p0_release, run_p0_coverage
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
    assert {result.result_key for result in evidence.results} == set(
        evidence.coverage.required_result_keys
    )
    assessment = decide_p0_release(evidence)
    assert assessment["decision"] == "blocked"
    assert assessment["missing"] == []
    assert assessment["unexpected"] == []
    assert assessment["duplicates"] == []


def test_forged_producer_document_cannot_enter_release_path():
    with pytest.raises(TypeError, match="EvaluationEvidence"):
        decide_p0_release({"candidate_status": "pass", "results": []})
