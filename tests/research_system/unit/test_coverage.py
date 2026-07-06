from pathlib import Path

from research_system.evals.coverage import P0_CASES, load_p0_coverage


ROOT = Path(__file__).resolve().parents[3]


def test_p0_coverage_selects_exact_merged_fixture_closure():
    coverage = load_p0_coverage(
        ROOT / ".research-system" / "evals" / "p0-coverage.yaml",
        fixture_root=ROOT / ".research-system" / "evals" / "fixtures",
        schema_root=ROOT / ".research-system" / "schemas",
    )
    assert len(P0_CASES) == 37
    assert dict(coverage.selected_fixture_revisions) == {
        fixture_id: "r1" for fixture_id in sorted(P0_CASES)
    }
    assert len(coverage.required_result_keys) == len(set(coverage.required_result_keys))
    assert coverage.transport == "fake"


def test_p0_coverage_keeps_judgment_and_gate5_capabilities_blocked():
    coverage = load_p0_coverage(
        ROOT / ".research-system" / "evals" / "p0-coverage.yaml",
        fixture_root=ROOT / ".research-system" / "evals" / "fixtures",
        schema_root=ROOT / ".research-system" / "schemas",
    )
    assert coverage.accepted_grader_classes == ("D", "O", "P", "R", "T")
    assert coverage.unavailable_grader_classes == ("H", "M")
    assert {item.fixture_id for item in coverage.omitted_gate5} == {
        "S-014",
        "S-015",
        "S-016",
    }
    assert all(item.status == "capability_disabled" for item in coverage.omitted_gate5)
    assert coverage.gate5_authorized is False
