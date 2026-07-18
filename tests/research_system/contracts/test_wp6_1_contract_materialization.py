from pathlib import Path

import yaml

from research_system.schema_registry import SchemaRegistry
from tests.research_system.contracts.wp6_1_materialization_validation import (
    validate_wp6_1_contract_materialization,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPO_ROOT / ".research-system" / "schemas"
CATALOGUE_PATH = REPO_ROOT / ".research-system" / "contracts" / "wp6-1-owner-source-catalogue.yaml"
IDENTITIES_PATH = REPO_ROOT / ".research-system" / "contracts" / "wp6-1-schema-identities.yaml"


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
