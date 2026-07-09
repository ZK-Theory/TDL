import shutil
from pathlib import Path

import pytest
import yaml

from research_system.evals.coverage import P0_CASES, P0_DEFERRED, load_p0_coverage
from research_system.evals.errors import FixtureDefinitionError


ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / ".research-system" / "evals"
FIXTURES = EVALS / "fixtures"
SCHEMAS = ROOT / ".research-system" / "schemas"
COVERAGE = EVALS / "p0-coverage.yaml"


def test_p0_coverage_selects_exact_merged_fixture_closure():
    coverage = load_p0_coverage(
        ROOT / ".research-system" / "evals" / "p0-coverage.yaml",
        fixture_root=ROOT / ".research-system" / "evals" / "fixtures",
        schema_root=ROOT / ".research-system" / "schemas",
    )
    assert len(P0_CASES) == 37
    expected = {fixture_id: "r1" for fixture_id in sorted(P0_CASES)}
    expected["F-021"] = "r2"
    expected["F-036"] = "r2"
    assert dict(coverage.selected_fixture_revisions) == expected
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


def test_p0_coverage_explains_every_deferred_catalogue_case():
    coverage = load_p0_coverage(
        COVERAGE, fixture_root=FIXTURES, schema_root=SCHEMAS
    )
    assert {item.fixture_id for item in coverage.omitted_p0} == set(P0_DEFERRED)
    assert all(item.reason and item.plan_ref for item in coverage.omitted_p0)


def test_orphan_fixture_directory_absent_from_catalogue_is_rejected(tmp_path):
    fixtures = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, fixtures)
    shutil.copytree(fixtures / "F-001", fixtures / "F-999")
    with pytest.raises(FixtureDefinitionError, match="absent from the catalogue"):
        load_p0_coverage(COVERAGE, fixture_root=fixtures, schema_root=SCHEMAS)


def test_incomplete_omitted_p0_is_rejected(tmp_path):
    payload = yaml.safe_load(COVERAGE.read_text(encoding="utf-8"))
    payload["omitted_p0"] = payload["omitted_p0"][:-1]
    bad = tmp_path / "p0-coverage.yaml"
    bad.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(FixtureDefinitionError, match="omitted_p0"):
        load_p0_coverage(bad, fixture_root=FIXTURES, schema_root=SCHEMAS)


def test_coverage_missing_fixture_yaml_is_rejected(tmp_path):
    fixtures = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, fixtures)
    Path.unlink(fixtures / "F-001" / "fixture.yaml")
    with pytest.raises(FixtureDefinitionError, match="failed to load fixture.yaml for F-001"):
        load_p0_coverage(COVERAGE, fixture_root=fixtures, schema_root=SCHEMAS)


def test_coverage_malformed_fixture_yaml_is_rejected(tmp_path):
    fixtures = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, fixtures)
    (fixtures / "F-001" / "fixture.yaml").write_text("{invalid: json", encoding="utf-8")
    with pytest.raises(FixtureDefinitionError, match="failed to load fixture.yaml for F-001"):
        load_p0_coverage(COVERAGE, fixture_root=fixtures, schema_root=SCHEMAS)


def test_coverage_non_mapping_fixture_yaml_is_rejected(tmp_path):
    fixtures = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, fixtures)
    (fixtures / "F-001" / "fixture.yaml").write_text("- not a mapping\n", encoding="utf-8")
    with pytest.raises(FixtureDefinitionError, match="fixture.yaml for F-001 must be a mapping"):
        load_p0_coverage(COVERAGE, fixture_root=fixtures, schema_root=SCHEMAS)
