"""SPEC-01's Assay rule in W11 admission and SPEC-01's own Assay bar (P-058, 2026-10-07, P5-8 and P5-9)."""

from __future__ import annotations

import json

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery import spec_assay
from research_system.discovery.assay_authority import content_sha256
from research_system.discovery.rules import (
    SPEC_01_ASSAY_RULE,
    SPEC_01_ASSAY_RULE_SHA256,
    _axis_set_hash,
    _spec_01_recommendation,
    evaluates_spec_01_rule,
)
from research_system.schema_registry import runtime_schema_registry
from tests.research_system.factories import PROJECT_ID, REPO_ROOT

PACKAGE = ".research-system/contracts/wp6-6/spec-gate6-run-v1"


def _content(relative: str) -> dict:
    raw = (REPO_ROOT / relative).read_bytes()
    value = json.loads(raw)
    assert raw == canonical_bytes(value) + b"\n"
    return value


RUBRIC = _content(spec_assay.ASSAY_RUBRIC_PATH)
SCOPE = _content(spec_assay.ASSAY_SCOPE_PATH)
FURTHER_GATES = [axis["axis_id"] for axis in RUBRIC["axis_definitions"][3:]]


def _results(*, topology=True, data=2, novelty=2, failed_gate=None):
    values = {"topology_earns_its_keep": topology, "data_feasibility": data, "novelty_publishability": novelty}
    return [
        (axis, {"axis_id": axis["axis_id"], "value": values.get(axis["axis_id"], axis["axis_id"] != failed_gate)})
        for axis in RUBRIC["axis_definitions"]
    ]


@pytest.mark.parametrize(
    ("case", "expected"),
    (
        ({"topology": False}, "KILL"),
        ({"topology": False, "data": 3, "novelty": 3}, "KILL"),
        ({"data": 2, "novelty": 2}, "PROMOTE"),
        ({"data": 3, "novelty": 1}, "PROMOTE"),
        ({"data": 3, "novelty": 3}, "PROMOTE"),
        ({"data": 2, "novelty": 1}, "PARK"),
        ({"data": 3, "novelty": 0}, "PARK"),
        ({"data": 0, "novelty": 3}, "PARK"),
        ({"data": 0, "novelty": 0}, "PARK"),
        *(({"data": 3, "novelty": 3, "failed_gate": gate}, "PARK") for gate in FURTHER_GATES),
    ),
)
def test_spec_01_rule_truth_table(case, expected):
    assert _spec_01_recommendation(_results(**case)) == expected


def test_a_bar_that_cannot_carry_the_rule_is_inadmissible():
    without_scores = [(axis, result) for axis, result in _results() if axis["axis_kind"] == "gate"]
    assert _spec_01_recommendation(without_scores) is None


def test_only_the_registered_descriptor_selects_the_rule():
    assert evaluates_spec_01_rule(RUBRIC)
    assert SPEC_01_ASSAY_RULE_SHA256 == sha256_hex(canonical_bytes(SPEC_01_ASSAY_RULE))
    for field, value in (
        ("rule_evaluation_algorithm_hash", "1" * 64),
        ("rule_evaluation_algorithm_version", "2.0.0"),
        ("rule_evaluation_algorithm_id", "exact-axis-closure"),
    ):
        assert not evaluates_spec_01_rule({**RUBRIC, field: value})
    fixture = _content(spec_assay.W11_FIXTURE_RUBRIC_PATH)
    assert not evaluates_spec_01_rule(fixture)


def test_spec_01_bar_is_exact_and_bound_to_its_sources():
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    schemas.validate("ars://portfolio/assay-rubric-content", RUBRIC, schema_version="1.0.0")
    schemas.validate("ars://portfolio/assay-evidence-scope-content", SCOPE, schema_version="1.0.0")
    for content in (RUBRIC, SCOPE):
        assert content["content_hash"] == content_sha256(content)
        assert content["project_id"] == PROJECT_ID
        assert content["created_by_actor_id"] == "act_01a1169f-019f-7fbb-b9f6-0246970f1d9a"
    axis_ids = [axis["axis_id"] for axis in RUBRIC["axis_definitions"]]
    assert axis_ids[:3] == [SPEC_01_ASSAY_RULE["decisive_gate_axis_id"], *SPEC_01_ASSAY_RULE["score_axis_ids"]]
    assert RUBRIC["required_axis_ids"] == RUBRIC["evaluation_order"] == axis_ids
    assert RUBRIC["required_axis_set_hash"] == _axis_set_hash(axis_ids)
    assert [row["evidence_key"] for row in SCOPE["evidence_rows"]] == axis_ids
    assert SCOPE["rubric_ref"] == {
        "id": RUBRIC["record_id"],
        "record_revision": 1,
        "content_hash": RUBRIC["content_hash"],
    }
    brief = sha256_hex((REPO_ROOT / PACKAGE / "spec-01-assay-brief-v1.1.0.md").read_bytes())
    route = sha256_hex((REPO_ROOT / PACKAGE / "route-package.json").read_bytes())
    for content in (RUBRIC, SCOPE):
        assert content["accepted_owner_requirement_refs"] == [
            {"id": "SPEC-01", "record_revision": 1, "content_hash": brief}
        ]
        assert content["effective_project_scope_ref"]["content_hash"] == route
    assert RUBRIC["source_authority_refs"][0]["content_hash"] == route
    assert {row["validator_hash"] for row in SCOPE["evidence_rows"]} == {brief}
