import importlib
import json
from pathlib import Path

import pytest

from research_system.evals.fixture_package import validate_fixture_package


REPO_ROOT = Path(__file__).resolve().parents[3]
ROOT = REPO_ROOT / ".research-system" / "evals" / "fixtures"
SCHEMAS = REPO_ROOT / ".research-system" / "schemas"
EXPECTED_CASES = {"S-014", "S-015", "S-016"}
EXPECTED_GRADERS = {
    "S-014": {"D", "T", "O", "P"},
    "S-015": {"D", "T"},
    "S-016": {"D", "T", "O", "H"},
}


def _materializer_module():
    return importlib.import_module("tools.ars.materialize_gate5_release_tranche")


def test_release_tranche_shard_has_exact_case_and_file_closure():
    materializer = _materializer_module()
    assert set(materializer.CASES) == EXPECTED_CASES
    for case_id in EXPECTED_CASES:
        package = ROOT / case_id
        assert {
            path.relative_to(package).as_posix()
            for path in package.rglob("*")
            if path.is_file()
        } == {
            "README.md",
            "fixture.yaml",
            "input/source-manifest.json",
            "input/stimulus.json",
            "expected/pre-control.json",
            "expected/post-control.json",
            "expected/trajectory.json",
            "graders/required.json",
        }
        validate_fixture_package(package, schema_root=SCHEMAS)


@pytest.mark.parametrize("case_id", sorted(EXPECTED_CASES))
def test_release_tranche_graders_are_exact_critical_required_sets(case_id):
    manifest = json.loads(
        (ROOT / case_id / "graders" / "required.json").read_text(encoding="utf-8")
    )
    rows = manifest["required_graders"]
    assert {row["grader_class"] for row in rows} == EXPECTED_GRADERS[case_id]
    assert all(row["critical"] is True and row["required"] is True for row in rows)


def test_release_tranche_materializer_check_is_cwd_independent(tmp_path, monkeypatch):
    materializer = _materializer_module()
    monkeypatch.chdir(tmp_path)
    materializer.materialize(ROOT, check=True)


def test_release_tranche_packages_are_synthetic_r0_without_credentials():
    for case_id in EXPECTED_CASES:
        fixture = (ROOT / case_id / "fixture.yaml").read_text(encoding="utf-8")
        source = json.loads(
            (ROOT / case_id / "input" / "source-manifest.json").read_text(
                encoding="utf-8"
            )
        )
        assert "input_fidelity: synthetic" in fixture
        assert "retention_class: R0" in fixture
        assert "credential" not in json.dumps(source).lower()
        assert ".env" not in json.dumps(source).lower()