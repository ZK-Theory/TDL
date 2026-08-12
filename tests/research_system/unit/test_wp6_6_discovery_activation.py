import json
from pathlib import Path

import research_system

from research_system.authority import (
    SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES,
    _SCOPED_COMMAND_SUBJECT_KINDS,
)
from research_system.discovery.runtime import (
    _DISCOVERY_COMMAND_TYPES,
    _DISCOVERY_DEFERRED_ROWS,
    _DISCOVERY_EXCLUDED_ROWS,
    _DISCOVERY_ROW_ROUTES,
    _validate_discovery_route_registry,
)
from research_system.schema_registry import runtime_schema_registry


REPOSITORY_ROOT = Path(research_system.__file__).resolve().parent.parent


def test_candidate_supersession_uses_candidate_compatible_scoped_authority():
    assert "SupersedeDiscoveryRecord" in SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES
    assert _SCOPED_COMMAND_SUBJECT_KINDS["SupersedeDiscoveryRecord"] == "scope_definition"
    assert (
        _SCOPED_COMMAND_SUBJECT_KINDS["SupersedeDiscoveryRecord"] == _SCOPED_COMMAND_SUBJECT_KINDS["RegisterCandidate"]
    )


def test_executable_route_registry_exactly_partitions_the_accepted_w11_catalogue():
    catalogue = json.loads(
        (REPOSITORY_ROOT / ".research-system/evals/expected/w11-portfolio-discovery-v1.json").read_bytes()
    )
    schemas = runtime_schema_registry(REPOSITORY_ROOT / ".research-system/schemas")

    _validate_discovery_route_registry(catalogue)
    assert len(_DISCOVERY_ROW_ROUTES) == 59
    assert len(_DISCOVERY_EXCLUDED_ROWS) == 21
    assert _DISCOVERY_DEFERRED_ROWS == {"OR-030": "WP6.7 annotation-epoch contract and initial authority activation"}
    assert set(_DISCOVERY_ROW_ROUTES).isdisjoint(_DISCOVERY_EXCLUDED_ROWS)
    assert {route.command_type for route in _DISCOVERY_ROW_ROUTES.values()} == _DISCOVERY_COMMAND_TYPES
    assert {route.family for route in _DISCOVERY_ROW_ROUTES.values()} == {
        "assay",
        "assay_authority",
        "authority",
        "candidate",
        "dossier",
        "genesis",
        "scout",
        "spike",
        "supersede",
    }
    for route in _DISCOVERY_ROW_ROUTES.values():
        assert schemas.command_binding(route.command_type) is not None
        assert _SCOPED_COMMAND_SUBJECT_KINDS[route.command_type] in {"decision", "review", "scope_definition"}
