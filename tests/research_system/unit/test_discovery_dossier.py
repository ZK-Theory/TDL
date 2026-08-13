from __future__ import annotations

import sys

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery import dossier as dossier_module
from research_system.discovery.dossier import DossierAdmissionRejected, canonical_dossier_hash


def test_dossier_semantic_hash_uses_the_replay_p0_canonical_encoder() -> None:
    value = {"axis_id": "identity", "value": 1}

    assert canonical_dossier_hash(value) == sha256_hex(canonical_bytes(value))


@pytest.mark.parametrize(
    "invalid_value",
    [
        {"axis_id": "identity", "value": 0.5},
        {"k\u00e9y": 1},
        {"value": 1 << 53},
    ],
    ids=["float", "non-ascii-key", "unsafe-integer"],
)
def test_dossier_semantic_hash_rejects_values_outside_p0(invalid_value: dict[str, object]) -> None:
    with pytest.raises((TypeError, ValueError), match="P0 canonical JSON"):
        canonical_dossier_hash(invalid_value)


def test_dependency_cycle_check_handles_a_chain_deeper_than_the_python_recursion_limit() -> None:
    depth = sys.getrecursionlimit() + 100
    adjacency = {f"node-{index}": {f"node-{index + 1}"} for index in range(depth)}
    adjacency[f"node-{depth}"] = set()

    dossier_module._validate_acyclic_dependencies(adjacency)

    adjacency[f"node-{depth}"].add(f"node-{depth // 2}")
    with pytest.raises(DossierAdmissionRejected, match="dependency_cycle"):
        dossier_module._validate_acyclic_dependencies(adjacency)
