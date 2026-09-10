"""Binding tests for the role-driven independence guard.

Observation 2026-08-12-wp61-lane-lacks-t2-independence-guard: the WP6.2 T2 lane machine-checked
producer/oracle independence; the WP6.1 lane held the same property by convention. These tests
cover every discovered lane from its declared roles, and the negative controls prove each part of
the assertion can actually fire — a guard nobody has watched fail is indistinguishable from one
that cannot.
"""

from __future__ import annotations

import copy
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from tests.research_system.contracts import artifact_role_independence as guard


REPO_ROOT = Path(__file__).resolve().parents[3]


def _wp6_1() -> Mapping[str, Any]:
    return guard.covered_manifests()[guard.WP6_1_ROLES_PATH]


def _paths_for(manifest: Mapping[str, Any], role: str) -> list[str]:
    """Select artifact paths by role from the manifest, rather than restating them here."""
    paths = [row.repository_path for row in guard.declarations(manifest) if row.role == role]
    assert paths, f"manifest declares no {role!r} artifact"
    return paths


def _mutated_copy(tmp_path: Path, repository_path: str, *, prepend: str = "", append: str = "") -> Path:
    """Copy a declared artifact to `tmp_path` with injected source, leaving the real tree untouched."""
    target = tmp_path / Path(repository_path).name
    shutil.copyfile(REPO_ROOT / repository_path, target)
    target.write_text(prepend + target.read_text(encoding="utf-8") + append, encoding="utf-8", newline="\n")
    return target


def test_wp6_1_lane_is_independent_apart_from_its_pinned_breach() -> None:
    """The lane the observation was raised against, now checked rather than assumed."""
    assert guard.violations(_wp6_1()) == []


def test_wp6_2_t2_lane_is_independent_under_the_same_rule() -> None:
    """One rule covers both lanes; T2 needed no contract change to be included."""
    assert guard.violations(guard.covered_manifests()[guard.WP6_2_T2_IDENTITIES_PATH]) == []


def test_assert_independent_sweeps_every_discovered_lane() -> None:
    """Both known lanes are discovered, and the entry point passes across all of them."""
    discovered = set(guard.covered_manifests())
    assert {guard.WP6_1_ROLES_PATH, guard.WP6_2_T2_IDENTITIES_PATH} <= discovered
    guard.assert_independent()


def test_a_newly_declared_lane_is_enforced_without_code_changes(tmp_path: Path) -> None:
    """Regression: PR #281 review. Lanes were a hard-coded pair, so a new role contract went unchecked.

    Builds a throwaway lane whose oracle imports its materializer, and requires discovery to find it
    and the guard to fail — with no edit to the guard module.
    """
    package = tmp_path / "lanepkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "producer.py").write_text("VALUE = 1\n", encoding="utf-8")
    (package / "oracle.py").write_text("from lanepkg import producer\n", encoding="utf-8")
    contracts = tmp_path / guard.CONTRACTS_DIR
    contracts.mkdir(parents=True)
    (contracts / "new-lane-roles.yaml").write_text(
        "artifacts:\n"
        "- artifact_role: schema_materializer\n"
        "  repository_path: lanepkg/producer.py\n"
        "- artifact_role: independent_oracle\n"
        "  repository_path: lanepkg/oracle.py\n",
        encoding="utf-8",
    )

    assert f"{guard.CONTRACTS_DIR}/new-lane-roles.yaml" in guard.covered_manifests(tmp_path)
    with pytest.raises(AssertionError, match="lanepkg.producer"):
        guard.assert_independent(repo_root=tmp_path)


def test_negative_control_forbidden_import_is_detected(tmp_path: Path) -> None:
    """THE WATCHED FAILURE.

    Copy a WP6.1 expected-side artifact, add an import the contract forbids, and require the guard to
    fire and name the edge. Without this, "the lane is independent" is unfalsifiable.
    """
    manifest = _wp6_1()
    oracle = _paths_for(manifest, "independent_oracle")[0]
    mutated = _mutated_copy(
        tmp_path,
        oracle,
        append="\nfrom tests.research_system.contracts.wp6_1_schema_materializer import schemas  # injected\n",
    )

    found = guard.violations(manifest, source_override={oracle: mutated})

    assert any("wp6_1_schema_materializer" in line and "forbidden by contract" in line for line in found)


@pytest.mark.parametrize(
    "injected",
    [
        pytest.param("import tests.research_system.contracts.wp6_1_schema_materializer\n", id="plain-import"),
        pytest.param(
            "from tests.research_system.contracts import wp6_1_schema_materializer\n",
            id="from-package-import-submodule",
        ),
        pytest.param(
            "from tests.research_system.contracts import wp6_1_schema_materializer as producer\n",
            id="from-package-import-aliased",
        ),
        pytest.param("from . import wp6_1_schema_materializer\n", id="relative-import"),
    ],
)
def test_negative_control_every_import_form_is_detected(tmp_path: Path, injected: str) -> None:
    """Regression: PR #281 review. Only ``ImportFrom.module`` was compared.

    ``from pkg import submodule`` records just ``pkg`` there, so the package-import idiom this very
    package uses — and the relative form — escaped the guard entirely.
    """
    manifest = _wp6_1()
    for oracle in _paths_for(manifest, "independent_oracle"):
        mutated = _mutated_copy(tmp_path, oracle, prepend=injected)
        found = guard.violations(manifest, source_override={oracle: mutated})
        assert any("wp6_1_schema_materializer" in line for line in found), f"{injected!r} escaped via {oracle}"


def test_pinned_breach_fails_when_the_shared_surface_grows(tmp_path: Path) -> None:
    """Regression: PR #281 review, P1. The pin must bound the breach, not waive it."""
    manifest = _wp6_1()
    materializer = _paths_for(manifest, "schema_materializer")[0]
    mutated = _mutated_copy(tmp_path, materializer, append="\n_UNPINNED = validation._require  # injected\n")

    found = guard.violations(manifest, source_override={materializer: mutated})

    assert any("_require" in line and "beyond the pinned known breach" in line for line in found)


def test_pinned_breach_fails_when_an_entry_goes_stale() -> None:
    """A pin the materializer no longer needs must be removed, so the entry cannot outlive the fix."""
    manifest = copy.deepcopy(dict(_wp6_1()))
    edge = next(e for e in manifest["independence_edges"] if "known_breach" in e)
    edge["known_breach"]["attributes"] = [*edge["known_breach"]["attributes"], "_never_used_helper"]

    found = guard.violations(manifest)

    assert any("_never_used_helper" in line and "still pins it" in line for line in found)


def test_unpinned_breach_would_fail_the_lane() -> None:
    """The breach is real: without its pin the WP6.1 lane goes red, so the pin is load-bearing."""
    manifest = copy.deepcopy(dict(_wp6_1()))
    for edge in manifest["independence_edges"]:
        edge.pop("known_breach", None)

    found = guard.violations(manifest)

    assert any("wp6_1_materialization_validation" in line for line in found)


def test_edge_naming_an_undeclared_role_fails_closed() -> None:
    """Regression: PR #281 review. A misspelled or deleted role silently skipped its edge."""
    manifest = copy.deepcopy(dict(_wp6_1()))
    manifest["artifacts"] = [row for row in manifest["artifacts"] if row["artifact_role"] != "independent_oracle"]

    with pytest.raises(guard.RoleContractError, match="independent_oracle"):
        guard.violations(manifest)


def test_explicit_module_must_match_its_path() -> None:
    """Regression: PR #281 review. A stale ``module`` value made the real module's imports unmatchable."""
    manifest = copy.deepcopy(dict(_wp6_1()))
    manifest["artifacts"][0]["module"] = "tests.research_system.contracts.renamed_elsewhere"

    with pytest.raises(guard.RoleContractError, match="does not match its path"):
        guard.declarations(manifest)


def test_non_python_artifacts_are_skipped_not_treated_as_empty() -> None:
    """A schema or catalogue has no import graph; counting it as clean would be vacuous coverage."""
    manifest = guard.covered_manifests()[guard.WP6_2_T2_IDENTITIES_PATH]
    declared_paths = {row.repository_path for row in guard.declarations(manifest)}
    assert declared_paths, "T2 must contribute Python artifacts to the guard"
    assert all(path.endswith(".py") for path in declared_paths)


def test_contract_names_its_own_enforcement_artifacts() -> None:
    """A contract that declares a guard must name it, or the binding rots unnoticed."""
    enforcement = _wp6_1()["enforcement"]
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
