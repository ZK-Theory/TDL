import subprocess
from pathlib import Path

import pytest
import yaml

from research_system.schema_registry import SchemaRegistry
from tests.research_system.contracts import wp6_1_materialization_validation as validation
from tests.research_system.contracts.wp6_1_materialization_validation import (
    validate_wp6_1_contract_materialization,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPO_ROOT / ".research-system" / "schemas"
CATALOGUE_PATH = REPO_ROOT / ".research-system" / "contracts" / "wp6-1-owner-source-catalogue.yaml"
IDENTITIES_PATH = REPO_ROOT / ".research-system" / "contracts" / "wp6-1-schema-identities.yaml"


def _git_bytes(revision: str, repository_path: Path) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{revision}:{repository_path.as_posix()}"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


@pytest.mark.parametrize("artifact_path", [CATALOGUE_PATH, IDENTITIES_PATH])
def test_wp6_1_contract_artifacts_are_exact_committed_lf_bytes(artifact_path: Path) -> None:
    """Checkout filters must not make the two accepted candidates byte-distinct."""
    checkout_bytes = artifact_path.read_bytes()
    committed_bytes = _git_bytes("HEAD", artifact_path.relative_to(REPO_ROOT))

    assert checkout_bytes == committed_bytes
    assert not checkout_bytes.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in checkout_bytes


def test_wp6_1_validator_parses_the_verified_approved_annex_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The mutable checkout annex must never be reopened after Git provenance passes."""

    def mutable_checkout_parse_forbidden(_: Path) -> object:
        raise AssertionError("validator reopened mutable approved-annex checkout bytes")

    monkeypatch.setattr(validation, "_parse_annex", mutable_checkout_parse_forbidden)
    summary = validate_wp6_1_contract_materialization(
        catalogue_path=CATALOGUE_PATH,
        identities_path=IDENTITIES_PATH,
        schema_root=SCHEMA_ROOT,
    )

    assert summary.normalized_row_count == 104


def test_wp6_1_materialization_strict_schemas_are_registered() -> None:
    registry = SchemaRegistry(SCHEMA_ROOT)

    assert registry.contains("ars://contracts/wp6-1-owner-source-catalogue")
    assert registry.contains("ars://contracts/wp6-1-schema-identities")


def test_wp6_1_materialization_artifacts_validate_through_public_schema_seam() -> None:
    registry = SchemaRegistry(SCHEMA_ROOT)
    catalogue = yaml.safe_load(CATALOGUE_PATH.read_text(encoding="utf-8"))
    identities = yaml.safe_load(IDENTITIES_PATH.read_text(encoding="utf-8"))

    registry.validate("ars://contracts/wp6-1-owner-source-catalogue", catalogue)
    registry.validate("ars://contracts/wp6-1-schema-identities", identities)


def test_wp6_1_materialization_binds_exact_104_row_multiset_and_182_expanded_edges() -> None:
    summary = validate_wp6_1_contract_materialization(
        catalogue_path=CATALOGUE_PATH,
        identities_path=IDENTITIES_PATH,
        schema_root=SCHEMA_ROOT,
    )

    assert summary.normalized_row_count == 104
    assert summary.expanded_edge_count == 182
