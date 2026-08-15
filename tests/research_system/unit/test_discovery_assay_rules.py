from copy import deepcopy
import json
from pathlib import Path

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.rules import _mechanical_assay_recommendation


REPO_ROOT = Path(__file__).resolve().parents[3]


def _rubric() -> dict[str, object]:
    rubric: dict[str, object] = {
        "rule_evaluation_algorithm_id": "spec-gate6-assay-score-v1",
        "rule_evaluation_algorithm_version": "1.0.0",
        "required_axis_ids": [
            "topology_earns_its_keep",
            "data_feasibility",
            "novelty_publishability",
        ],
        "evaluation_order": [
            "topology_earns_its_keep",
            "data_feasibility",
            "novelty_publishability",
        ],
        "recommendation_predicates": [
            "PROMOTE requires topology_earns_its_keep == true",
            "PROMOTE requires data_feasibility + novelty_publishability >= 4",
            "PROMOTE requires data_feasibility > 0 and novelty_publishability > 0",
        ],
        "hard_gate_predicates": ["topology first"],
        "partial_predicates": [
            "Partial requires blocked or incomplete required evidence and cannot be relabelled PROMOTE"
        ],
        "park_predicates": [
            "PARK when topology_earns_its_keep == true, data_feasibility > 0, novelty_publishability > 0, and "
            "data_feasibility + novelty_publishability < 4, with named remediable gaps and revisit requirements",
            "PARK is required when any additional human-readable promotion gate is unmet or cannot be expressed "
            "by the machine scorecard",
        ],
        "kill_predicates": [
            "KILL when completed evidence has topology_earns_its_keep == false",
            "KILL when completed evidence has data_feasibility == 0",
            "KILL when completed evidence has novelty_publishability == 0",
            "KILL requires a directly verified decisive failure or redundancy",
        ],
    }
    preimage_fields = (
        "evaluation_order",
        "recommendation_predicates",
        "hard_gate_predicates",
        "partial_predicates",
        "park_predicates",
        "kill_predicates",
        "rule_evaluation_algorithm_id",
        "rule_evaluation_algorithm_version",
    )
    rubric["rule_evaluation_algorithm_hash"] = sha256_hex(
        canonical_bytes({field: rubric[field] for field in preimage_fields})
    )
    return rubric


def _definitions() -> list[dict[str, object]]:
    return [
        {
            "axis_id": "topology_earns_its_keep",
            "axis_kind": "gate",
            "value_type": "boolean",
            "allowed_set": [False, True],
            "required": True,
        },
        {
            "axis_id": "data_feasibility",
            "axis_kind": "integer_score",
            "value_type": "integer",
            "bounds": {"minimum": 0, "maximum": 3},
            "required": True,
        },
        {
            "axis_id": "novelty_publishability",
            "axis_kind": "integer_score",
            "value_type": "integer",
            "bounds": {"minimum": 0, "maximum": 3},
            "required": True,
        },
    ]


def _results(
    topology: bool,
    data_score: int,
    novelty_score: int,
    definitions: list[dict[str, object]] | None = None,
) -> dict[str, tuple[dict[str, object], dict[str, object]]]:
    definitions = definitions or _definitions()
    values = (topology, data_score, novelty_score)
    return {
        definition["axis_id"]: (definition, {"value": value})
        for definition, value in zip(definitions, values, strict=True)
    }


@pytest.mark.parametrize(
    ("topology", "data_score", "novelty_score", "expected"),
    [
        (True, 2, 2, "PROMOTE"),
        (True, 1, 2, "PARK"),
        (False, 3, 3, "KILL"),
        (True, 0, 3, "KILL"),
        (True, 3, 0, "KILL"),
    ],
)
def test_spec_gate6_mechanical_recommendation(
    topology: bool,
    data_score: int,
    novelty_score: int,
    expected: str,
) -> None:
    definitions = _definitions()

    assert (
        _mechanical_assay_recommendation(_rubric(), definitions, _results(topology, data_score, novelty_score))
        == expected
    )


@pytest.mark.parametrize("mutation", ["axis_id", "bounds", "algorithm", "predicate"])
def test_spec_gate6_mechanical_recommendation_rejects_rule_substitution(mutation: str) -> None:
    rubric = _rubric()
    definitions = _definitions()
    if mutation == "axis_id":
        definitions[0]["axis_id"] = "topology_optional"
    elif mutation == "bounds":
        definitions[1]["bounds"] = {"minimum": 0, "maximum": 4}
    elif mutation == "algorithm":
        rubric["rule_evaluation_algorithm_version"] = "2.0.0"
    else:
        rubric["recommendation_predicates"][0] = "PROMOTE always"
        preimage_fields = (
            "evaluation_order",
            "recommendation_predicates",
            "hard_gate_predicates",
            "partial_predicates",
            "park_predicates",
            "kill_predicates",
            "rule_evaluation_algorithm_id",
            "rule_evaluation_algorithm_version",
        )
        rubric["rule_evaluation_algorithm_hash"] = sha256_hex(
            canonical_bytes({field: rubric[field] for field in preimage_fields})
        )

    results = _results(True, 2, 2, definitions)
    assert _mechanical_assay_recommendation(rubric, definitions, results) is None


def test_spec_gate6_mechanical_recommendation_rejects_optional_required_axis() -> None:
    definitions = deepcopy(_definitions())
    definitions[2]["required"] = False

    assert _mechanical_assay_recommendation(_rubric(), definitions, _results(True, 2, 2, definitions)) is None


def test_committed_spec_gate6_rubric_uses_the_executable_rule() -> None:
    rubric = json.loads((REPO_ROOT / ".research-system/contracts/wp6-6/assay-rubric-content-v1.json").read_bytes())
    definitions = rubric["axis_definitions"]
    results = {
        definition["axis_id"]: (definition, {"value": value})
        for definition, value in zip(definitions, (True, 2, 2), strict=True)
    }

    assert _mechanical_assay_recommendation(rubric, definitions, results) == "PROMOTE"
