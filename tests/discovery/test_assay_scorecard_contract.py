"""Contract bindings for Discovery Harness assay scorecards."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from trajectory_tda.discovery.assay_scorecard import (
    extract_scorecard_block,
    validate_assay_scorecard,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"
DISCOVERY_CONTRACT = "discovery-harness/assay-scorecard.yaml"


def _load_contract(rel_path: str) -> dict[str, Any]:
    path = CONTRACTS_DIR / rel_path
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _valid_scorecard() -> dict[str, Any]:
    return {
        "schema_version": "discovery/assay-scorecard/v1",
        "candidate_id": "arxiv-2606-11911",
        "candidate_slug": "from-persistence-to-survival",
        "assayed_at": "2026-06-16",
        "source": "_inbox/2026-W25.md",
        "axis1_topology_gate": {
            "passes": True,
            "metric_space": "Persistence diagrams with a named diagram metric.",
            "feature_claim_map": "H1 persistence shift maps to a falsifiable survival contrast.",
            "reducible_to_baseline": False,
            "named_baseline": "Cox model on non-topological summary features.",
            "adversarial_null": "A standard survival baseline could explain the claim without PH.",
        },
        "axis2_data_feasibility": {
            "score": 2,
            "rationale": "Existing outputs can provide diagrams; panel transfer needs a toy probe.",
        },
        "axis3_novelty_publishability": {
            "score": 2,
            "rationale": "Clear methods gap with identifiable statistical-methods venues.",
        },
        "decision": "PROMOTE",
        "decision_rationale": "Gate passes and scored axes sum to 4 with neither score at 0.",
        "next": "/spike",
    }


def _mutated(path: tuple[str, ...], value: object) -> dict[str, Any]:
    payload = copy.deepcopy(_valid_scorecard())
    target = payload
    for key in path[:-1]:
        target = target[key]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    return payload


def test_assay_scorecard_schema_rejects_invalid_decision_logic() -> None:
    """Representative scorecard passes; rubric-listed violations reject."""
    validate_assay_scorecard(_valid_scorecard())

    # (a) Axis-1 gate failure cannot PROMOTE.
    bad = _mutated(("axis1_topology_gate", "passes"), False)
    with pytest.raises(AssertionError, match="Axis-1"):
        validate_assay_scorecard(bad)

    # (b) Axis 2/3 scores must be integers in [0, 3].
    bad = _mutated(("axis2_data_feasibility", "score"), 4)
    with pytest.raises(AssertionError, match="axis2_data_feasibility.score"):
        validate_assay_scorecard(bad)

    bad = _mutated(("axis3_novelty_publishability", "score"), 1.5)
    with pytest.raises(AssertionError, match="axis3_novelty_publishability.score"):
        validate_assay_scorecard(bad)

    # (c) PROMOTE requires Axis2 + Axis3 >= 4 and neither score equals 0.
    bad = _mutated(("axis2_data_feasibility", "score"), 1)
    with pytest.raises(AssertionError, match="PROMOTE"):
        validate_assay_scorecard(bad)

    bad = _mutated(("axis3_novelty_publishability", "score"), 0)
    with pytest.raises(AssertionError, match="PROMOTE"):
        validate_assay_scorecard(bad)

    # (d) Axis-1 must name a metric, falsifiable feature claim, and baseline.
    for field in ("metric_space", "feature_claim_map", "named_baseline", "adversarial_null"):
        bad = _mutated(("axis1_topology_gate", field), "")
        with pytest.raises(AssertionError, match=field):
            validate_assay_scorecard(bad)

    # (e) Programme fit is deliberately excluded from the scorecard.
    bad = _valid_scorecard()
    bad["programme_fit"] = 3
    with pytest.raises(AssertionError, match="programme_fit"):
        validate_assay_scorecard(bad)


def test_assay_scorecard_markdown_block_extraction() -> None:
    note = """# Candidate

```yaml assay_scorecard
schema_version: discovery/assay-scorecard/v1
candidate_id: arxiv-2606-11911
candidate_slug: from-persistence-to-survival
assayed_at: "2026-06-16"
source: _inbox/2026-W25.md
axis1_topology_gate:
  passes: true
  metric_space: Persistence diagrams with a named diagram metric.
  feature_claim_map: H1 persistence shift maps to a falsifiable survival contrast.
  reducible_to_baseline: false
  named_baseline: Cox model on non-topological summary features.
  adversarial_null: A standard survival baseline could explain the claim without PH.
axis2_data_feasibility:
  score: 2
  rationale: Existing outputs can provide diagrams; panel transfer needs a toy probe.
axis3_novelty_publishability:
  score: 2
  rationale: Clear methods gap with identifiable statistical-methods venues.
decision: PROMOTE
decision_rationale: Gate passes and scored axes sum to 4 with neither score at 0.
next: /spike
```
"""
    extracted = extract_scorecard_block(note)
    assert extracted["schema_version"] == "discovery/assay-scorecard/v1"
    validate_assay_scorecard(extracted)


def test_assay_scorecard_contract_binding() -> None:
    contract = _load_contract(DISCOVERY_CONTRACT)
    assert contract["id"] == "assay-scorecard"
    assert contract["kind"] == "schema"
    assert contract["binding"]["test_file"] == "tests/discovery/test_assay_scorecard_contract.py"
    assert contract["binding"]["test_function"] == "test_assay_scorecard_schema_rejects_invalid_decision_logic"

    required = [entry["name"] for entry in contract["schema_def"]["required_keys"]]
    assert required == [
        "schema_version",
        "candidate_id",
        "candidate_slug",
        "assayed_at",
        "source",
        "axis1_topology_gate",
        "axis2_data_feasibility",
        "axis3_novelty_publishability",
        "decision",
        "decision_rationale",
        "next",
    ]

    forbidden = [entry["name"] for entry in contract["schema_def"]["forbidden_keys"]]
    assert forbidden == ["programme_fit"]
