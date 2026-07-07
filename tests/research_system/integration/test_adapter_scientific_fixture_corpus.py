import json
from pathlib import Path

import pytest

from research_system.evals.fixture_package import validate_fixture_package
from tools.ars.materialize_adapter_scientific_fixtures import CASES, materialize


REPO_ROOT = Path(__file__).resolve().parents[3]
ROOT = REPO_ROOT / ".research-system" / "evals" / "fixtures"
SCHEMAS = REPO_ROOT / ".research-system" / "schemas"
EXPECTED_CASES = {
    "F-007",
    "F-008",
    "F-009",
    "F-010",
    "F-011",
    "F-012",
    "F-013",
    "F-014",
    "F-020",
    "F-032",
    "F-034",
    "F-036",
    "S-003",
    "S-004",
    "S-013",
}


def _document(case_id: str, relative: str) -> dict:
    return json.loads((ROOT / case_id / relative).read_text(encoding="utf-8"))


def test_adapter_scientific_shard_has_exact_case_contract():
    assert set(CASES) == EXPECTED_CASES
    missing = EXPECTED_CASES - {path.name for path in ROOT.iterdir() if path.is_dir()}
    assert not missing


@pytest.mark.parametrize("case_id", sorted(EXPECTED_CASES))
def test_adapter_scientific_packages_are_hash_bound_and_behavior_specific(case_id):
    validate_fixture_package(ROOT / case_id, schema_root=SCHEMAS)
    stimulus = _document(case_id, "input/stimulus.json")
    pre = _document(case_id, "expected/pre-control.json")
    post = _document(case_id, "expected/post-control.json")

    assert stimulus["payload"]["contract"] == CASES[case_id].contract
    assert pre["assertions"][0]["property"] == CASES[case_id].contract
    assert post["assertions"][0]["property"] == CASES[case_id].contract
    assert pre["assertions"][0]["expected_evidence"] == CASES[case_id].pre
    assert post["assertions"][0]["expected_evidence"] == CASES[case_id].post
    assert CASES[case_id].pre != CASES[case_id].post


def test_scientific_oracle_literals_encode_expected_invariants():
    # Asserts the authored expected-evidence literals in CASES; nothing is
    # recomputed here. Real oracle recomputation lands in WP4.8.
    assert CASES["F-011"].post["fit_calls"] == 0
    assert CASES["F-012"].pre["tested_object_changed"] is False
    assert CASES["F-012"].post["tested_object_changed"] is True
    assert CASES["F-013"].post["manifest_vintages_coherent"] is True
    assert CASES["F-014"].post["independent_authority"] is True
    assert CASES["F-036"].post["mutation_detected"] is True


def test_adapter_scientific_materializer_check_is_cwd_independent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    materialize(ROOT, check=True)
