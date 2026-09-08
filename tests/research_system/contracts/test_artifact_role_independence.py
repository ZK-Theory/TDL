"""Binding tests for the role-driven independence guard.

Observation 2026-08-12-wp61-lane-lacks-t2-independence-guard: the WP6.2 T2 lane machine-checked
producer/oracle independence; the WP6.1 lane held the same property by convention. These tests
cover both lanes from their declared roles, and the negative control proves the assertion can
actually fire — a guard nobody has watched fail is indistinguishable from one that cannot.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests.research_system.contracts import artifact_role_independence as guard


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_wp6_1_lane_is_independent() -> None:
    """The lane the observation was raised against, now checked rather than assumed."""
    manifest = guard.covered_manifests()[guard.WP6_1_ROLES_PATH]
    assert guard.violations(manifest) == []


def test_wp6_2_t2_lane_is_independent_under_the_same_rule() -> None:
    """One rule covers both lanes; T2 needed no contract change to be included."""
    manifest = guard.covered_manifests()[guard.WP6_2_T2_IDENTITIES_PATH]
    assert guard.violations(manifest) == []


def test_assert_independent_covers_every_declared_lane() -> None:
    """The entry point the suite calls must sweep all covered manifests, not a subset."""
    guard.assert_independent()
    assert set(guard.covered_manifests()) == {guard.WP6_1_ROLES_PATH, guard.WP6_2_T2_IDENTITIES_PATH}


def test_negative_control_forbidden_import_is_detected(tmp_path: Path) -> None:
    """THE WATCHED FAILURE.

    Copy the WP6.1 expected side, add the exact import the contract forbids, and require the guard
    to fire and name the edge. Without this, "the lane is independent" is unfalsifiable.
    """
    manifest = guard.covered_manifests()[guard.WP6_1_ROLES_PATH]
    oracle_path = "tests/research_system/contracts/wp6_1_schema_expectations.py"
    mutated = tmp_path / "wp6_1_schema_expectations_mutated.py"
    shutil.copyfile(REPO_ROOT / oracle_path, mutated)
    mutated.write_text(
        mutated.read_text(encoding="utf-8")
        + "\nfrom tests.research_system.contracts.wp6_1_schema_materializer import schemas  # injected\n",
        encoding="utf-8",
        newline="\n",
    )

    found = guard.violations(manifest, source_override={oracle_path: mutated})

    assert found, "the guard did not fire on an injected oracle → materializer import"
    assert any("wp6_1_schema_materializer" in line for line in found)
    assert any("forbidden by contract" in line for line in found)


def test_negative_control_plain_import_form_is_also_detected(tmp_path: Path) -> None:
    """`import a.b.c` reaches the same module as `from a.b import c` and must not slip past."""
    manifest = guard.covered_manifests()[guard.WP6_1_ROLES_PATH]
    oracle_path = "tests/research_system/contracts/wp6_1_schema_fact_oracle.py"
    mutated = tmp_path / "wp6_1_schema_fact_oracle_mutated.py"
    shutil.copyfile(REPO_ROOT / oracle_path, mutated)
    mutated.write_text(
        "import tests.research_system.contracts.wp6_1_schema_materializer  # injected\n"
        + mutated.read_text(encoding="utf-8"),
        encoding="utf-8",
        newline="\n",
    )

    found = guard.violations(manifest, source_override={oracle_path: mutated})

    assert found, "plain `import x.y.z` form escaped the guard"


def test_non_python_artifacts_are_skipped_not_treated_as_empty() -> None:
    """A schema or catalogue has no import graph; counting it as clean would be vacuous coverage."""
    manifest = guard.covered_manifests()[guard.WP6_2_T2_IDENTITIES_PATH]
    declared_paths = {row.repository_path for row in guard.declarations(manifest)}
    assert declared_paths, "T2 must contribute Python artifacts to the guard"
    assert all(path.endswith(".py") for path in declared_paths)
    assert ".gitattributes" not in declared_paths


def test_contract_names_its_own_enforcement_artifacts() -> None:
    """A contract that declares a guard must name it, or the binding rots unnoticed."""
    manifest = guard.covered_manifests()[guard.WP6_1_ROLES_PATH]
    enforcement = manifest["enforcement"]
    assert (REPO_ROOT / enforcement["guard_module"]).is_file()
    assert (REPO_ROOT / enforcement["binding_test"]).is_file()
    assert enforcement["negative_control"] in Path(__file__).read_text(encoding="utf-8")


def test_declared_roles_match_the_files_that_exist() -> None:
    """Every declared path must exist, or the lane is guarded in name only."""
    for path, manifest in guard.covered_manifests().items():
        for row in guard.declarations(manifest):
            assert (REPO_ROOT / row.repository_path).is_file(), f"{path} declares a missing artifact: {row}"


@pytest.mark.parametrize("edge", guard.DEFAULT_INDEPENDENCE_EDGES)
def test_default_edges_are_symmetric(edge: tuple[str, str]) -> None:
    """Both directions are disqualifying; a one-way default would leave half the property open."""
    importer, imported = edge
    assert (imported, importer) in guard.DEFAULT_INDEPENDENCE_EDGES
