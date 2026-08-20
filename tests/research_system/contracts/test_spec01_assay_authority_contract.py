from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import shutil

import pytest
from jsonschema import Draft202012Validator

from research_system.canonical import canonical_bytes, sha256_hex
from tests.research_system.assay_authority_helpers import (
    SCOPE_HASH_FIELDS,
    bind_assay_fixture_to_current_spec_sources,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
RUBRIC_PATH = REPO_ROOT / ".research-system/contracts/wp6-6/assay-rubric-content-v1.json"
SCOPE_PATH = REPO_ROOT / ".research-system/contracts/wp6-6/assay-evidence-scope-content-v1.json"
RUBRIC_V2_PATH = REPO_ROOT / ".research-system/contracts/wp6-6/assay-rubric-content-v2.json"
SCOPE_V2_PATH = REPO_ROOT / ".research-system/contracts/wp6-6/assay-evidence-scope-content-v2.json"
RUBRIC_SCHEMA_PATH = REPO_ROOT / ".research-system/schemas/contracts/w11/assay-rubric-content.schema.json"
SCOPE_SCHEMA_PATH = REPO_ROOT / ".research-system/schemas/contracts/w11/assay-evidence-scope-content.schema.json"
SPEC_PATH = REPO_ROOT / ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-01-assay-brief-v1.1.0.md"
ROUTE_PATH = REPO_ROOT / ".research-system/contracts/wp6-6/spec-gate6-run-v1/route-package.json"
CATALOGUE_PATH = REPO_ROOT / ".research-system/evals/expected/w11-portfolio-discovery-v1.json"

SPEC_SHA256 = "d3b1eac020b5c94707461c0a475cc911e36ab78e2bc1243c0b28747748106972"
ROUTE_SHA256 = "4115f135c3459465ad492295366d1877a6ccc03549c7b53b893e00655567c14f"
ROUTE_SOURCE_COMMIT = "82f86d88e72d33ed9e39ccceac6e3bcdead0bb75"
ROUTE_SOURCE_BLOB = "23b6017625520c310202fd84ee45223ba6fecdf5"
CATALOGUE_SHA256 = "7e36b39a3a0aa0a01e262e9f8a8c0d8a35f111c76efa0054f2c326ee15860b80"
PRODUCER_ACTOR_ID = "act_e2651127-9ee1-7a64-a2ed-4e44008f1d4e"
SUCCESSOR_PRODUCER_ACTOR_ID = "act_9292d02f-7c6d-70ec-b188-6f1ef0ce36ee"

AXIS_IDS = ["topology_earns_its_keep", "data_feasibility", "novelty_publishability"]
PROMOTION_PREDICATES = [
    "PROMOTE requires topology_earns_its_keep == true",
    "PROMOTE requires data_feasibility + novelty_publishability >= 4",
    "PROMOTE requires data_feasibility > 0 and novelty_publishability > 0",
    "PROMOTE additionally requires one non-redundant primary claim",
    "PROMOTE additionally requires a planted noisy-circle benchmark with sphere control",
    "PROMOTE additionally requires a Euclidean PH baseline",
    "PROMOTE additionally requires a named future estimand and representation freeze",
    "PROMOTE additionally requires disconnected graphs treated as blocked",
    (
        "PROMOTE additionally requires a decision-complete SPEC-02 design within two hours, "
        "12 GB memory, 5 GB scratch, and four CPU slots"
    ),
    "PROMOTE additionally requires no unresolved primary-paper/code discrepancy",
]
HARD_GATE_PREDICATES = [
    "topology_earns_its_keep == true is evaluated before data_feasibility and novelty_publishability"
]
PARTIAL_PREDICATES = ["Partial requires blocked or incomplete required evidence and cannot be relabelled PROMOTE"]
PARK_PREDICATES = [
    (
        "PARK when topology_earns_its_keep == true, data_feasibility > 0, "
        "novelty_publishability > 0, and data_feasibility + novelty_publishability < 4, "
        "with named remediable gaps and revisit requirements"
    ),
    "PARK is required when any additional human-readable promotion gate is unmet or cannot be expressed by the machine scorecard",
]
KILL_PREDICATES = [
    "KILL when completed evidence has topology_earns_its_keep == false",
    "KILL when completed evidence has data_feasibility == 0",
    "KILL when completed evidence has novelty_publishability == 0",
    "KILL requires a directly verified decisive failure or redundancy",
]

RULE_HASH_FIELDS = (
    "evaluation_order",
    "recommendation_predicates",
    "hard_gate_predicates",
    "partial_predicates",
    "park_predicates",
    "kill_predicates",
    "rule_evaluation_algorithm_id",
    "rule_evaluation_algorithm_version",
)
EVIDENCE_ROW_HASH_FIELDS = (
    "evidence_key",
    "allowed_source_classes",
    "identity_requirement",
    "closure_requirement",
    "producer_requirement",
    "freshness_or_event_position",
    "validator_id",
    "validator_version",
    "independent_review_grade",
    "permitted_omissions",
    "unmet_reason_codes",
)


def _load() -> tuple[dict[str, object], dict[str, object]]:
    return json.loads(RUBRIC_PATH.read_bytes()), json.loads(SCOPE_PATH.read_bytes())


def _projection_hash(value: dict[str, object], fields: tuple[str, ...]) -> str:
    return sha256_hex(canonical_bytes({field: value[field] for field in fields}))


def _content_hash(value: dict[str, object]) -> str:
    preimage = dict(value)
    preimage.pop("content_hash", None)
    return sha256_hex(canonical_bytes(preimage))


def test_assay_fixture_rebinding_rejects_repository_root_and_allows_isolated_copy(tmp_path: Path) -> None:
    source_paths = (RUBRIC_PATH, SCOPE_PATH, ROUTE_PATH, SPEC_PATH)
    source_bytes = {path: path.read_bytes() for path in source_paths}

    with pytest.raises(ValueError, match="refusing to rewrite Assay authority fixture content"):
        bind_assay_fixture_to_current_spec_sources(REPO_ROOT)
    assert {path: path.read_bytes() for path in source_paths} == source_bytes

    fixture_root = tmp_path / "isolated-assay-fixture"
    for source_path in source_paths:
        target_path = fixture_root / source_path.relative_to(REPO_ROOT)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, target_path)
    bind_assay_fixture_to_current_spec_sources(fixture_root)

    rebound_rubric = json.loads((fixture_root / RUBRIC_PATH.relative_to(REPO_ROOT)).read_bytes())
    rebound_scope = json.loads((fixture_root / SCOPE_PATH.relative_to(REPO_ROOT)).read_bytes())
    route_sha256 = sha256_hex(source_bytes[ROUTE_PATH])
    spec_sha256 = sha256_hex(source_bytes[SPEC_PATH])
    assert {
        item["id"]: item["content_hash"]
        for item in rebound_rubric["source_refs"]
        if item.get("id") in {"SPEC-GATE6-RUN-V1", "SPEC-01"}
    } == {"SPEC-GATE6-RUN-V1": route_sha256, "SPEC-01": spec_sha256}
    assert rebound_rubric["content_hash"] == _content_hash(rebound_rubric)
    assert rebound_scope["rubric_ref"]["content_hash"] == rebound_rubric["content_hash"]
    assert rebound_scope["scope_closure_algorithm_hash"] == _projection_hash(
        rebound_scope,
        SCOPE_HASH_FIELDS,
    )
    assert rebound_scope["content_hash"] == _content_hash(rebound_scope)


def _validate_semantics(rubric: dict[str, object], scope: dict[str, object]) -> None:
    axes = rubric["axis_definitions"]
    assert isinstance(axes, list)
    assert rubric["required_axis_ids"] == AXIS_IDS
    assert rubric["evaluation_order"] == AXIS_IDS
    assert [axis["axis_id"] for axis in axes] == AXIS_IDS
    assert axes[0]["axis_kind"] == "gate"
    assert axes[0]["value_type"] == "boolean"
    assert axes[0]["allowed_set"] == [False, True]
    for axis in axes[1:]:
        assert axis["axis_kind"] == "integer_score"
        assert axis["value_type"] == "integer"
        assert axis["bounds"] == {"minimum": 0, "maximum": 3}
    assert all(axis["required"] is True for axis in axes)

    assert rubric["rule_evaluation_algorithm_id"] == "spec-gate6-assay-score-v1"
    assert rubric["rule_evaluation_algorithm_version"] == "1.0.0"
    assert rubric["recommendation_predicates"] == PROMOTION_PREDICATES
    assert rubric["hard_gate_predicates"] == HARD_GATE_PREDICATES
    assert rubric["partial_predicates"] == PARTIAL_PREDICATES
    assert rubric["park_predicates"] == PARK_PREDICATES
    assert rubric["kill_predicates"] == KILL_PREDICATES

    evidence_rows = scope["evidence_rows"]
    assert isinstance(evidence_rows, list)
    assert [row["evidence_key"] for row in evidence_rows] == AXIS_IDS
    assert len(evidence_rows) == len(axes) == 3
    assert scope["required_assurance_lanes"] == ["Output", "Provenance", "independent_outcome_review"]
    assert scope["prohibited_producer_relationships"] == ["self-review"]
    assert scope["prohibited_source_classes"] == [
        "survey microdata",
        "numerical experiment result",
        "provider result",
    ]
    assert scope["partial_conditions"] == [
        "required evidence is blocked or incomplete",
        "Partial cannot be relabelled PROMOTE",
    ]
    assert all(row["independent_review_grade"] == "independent outcome review required" for row in evidence_rows)
    assert all(row["permitted_omissions"] == [] for row in evidence_rows)
    assert "self-review" in scope["stop_conditions"]
    assert "numerical outcome inspection" in scope["stop_conditions"]
    assert "provider API use" in scope["stop_conditions"]
    assert "SPEC-02 requires a later separate explicit live-run approval" in scope["stop_conditions"]


def test_spec01_assay_authorities_are_schema_valid_canonical_current_content() -> None:
    rubric, scope = _load()
    for schema_path, value in ((RUBRIC_SCHEMA_PATH, rubric), (SCOPE_SCHEMA_PATH, scope)):
        schema = json.loads(schema_path.read_bytes())
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(value)

    assert RUBRIC_PATH.read_bytes() == canonical_bytes(rubric) + b"\n"
    assert SCOPE_PATH.read_bytes() == canonical_bytes(scope) + b"\n"
    assert rubric["content_hash"] == _content_hash(rubric)
    assert scope["content_hash"] == _content_hash(scope)
    assert rubric["created_by_actor_id"] == PRODUCER_ACTOR_ID
    assert scope["created_by_actor_id"] == PRODUCER_ACTOR_ID
    assert scope["rubric_ref"] == {
        "id": rubric["record_id"],
        "record_revision": rubric["record_revision"],
        "content_hash": rubric["content_hash"],
    }
    _validate_semantics(rubric, scope)


def test_spec01_assay_authority_revision_1_binds_its_historical_route_source_and_derived_hashes() -> None:
    rubric, scope = _load()
    assert hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest() == SPEC_SHA256
    git = shutil.which("git")
    assert git is not None, "a full Git checkout is required to verify historical Assay authority"
    historical_commit = subprocess.run(
        [git, "-C", str(REPO_ROOT), "rev-parse", "--verify", f"{ROUTE_SOURCE_COMMIT}^{{commit}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert (
        historical_commit.returncode == 0
    ), "a full Git checkout containing the historical Assay route commit is required"
    historical_route = subprocess.check_output(
        [git, "-C", str(REPO_ROOT), "show", f"{ROUTE_SOURCE_COMMIT}:{ROUTE_PATH.relative_to(REPO_ROOT).as_posix()}"],
    )
    historical_blob = subprocess.check_output(
        [
            git,
            "-C",
            str(REPO_ROOT),
            "rev-parse",
            f"{ROUTE_SOURCE_COMMIT}:{ROUTE_PATH.relative_to(REPO_ROOT).as_posix()}",
        ],
        text=True,
    ).strip()
    assert historical_blob == ROUTE_SOURCE_BLOB
    assert hashlib.sha256(historical_route).hexdigest() == ROUTE_SHA256
    assert hashlib.sha256(CATALOGUE_PATH.read_bytes()).hexdigest() == CATALOGUE_SHA256

    expected_sources = [SPEC_SHA256, ROUTE_SHA256, CATALOGUE_SHA256]
    assert [ref["content_hash"] for ref in rubric["source_refs"]] == expected_sources
    assert [ref["content_hash"] for ref in scope["source_refs"]] == expected_sources
    assert rubric["accepted_owner_requirement_refs"] == [
        {"id": "W11:OR-101", "record_revision": 1, "content_hash": CATALOGUE_SHA256}
    ]
    assert scope["accepted_owner_requirement_refs"] == [
        {"id": "W11:OR-102", "record_revision": 1, "content_hash": CATALOGUE_SHA256}
    ]

    assert rubric["required_axis_set_hash"] == sha256_hex(canonical_bytes(sorted(AXIS_IDS)))
    assert rubric["rule_evaluation_algorithm_hash"] == _projection_hash(rubric, RULE_HASH_FIELDS)
    for row in scope["evidence_rows"]:
        assert row["validator_hash"] == _projection_hash(row, EVIDENCE_ROW_HASH_FIELDS)
    assert scope["scope_closure_algorithm_hash"] == _projection_hash(scope, SCOPE_HASH_FIELDS)

    combined_text = (RUBRIC_PATH.read_text(encoding="utf-8") + SCOPE_PATH.read_text(encoding="utf-8")).lower()
    assert "1" * 64 not in combined_text
    assert "fixture" not in combined_text
    assert "provider-free" not in combined_text


def test_spec01_assay_authority_revision_2_is_an_exact_current_route_successor() -> None:
    old_rubric, old_scope = _load()
    rubric = json.loads(RUBRIC_V2_PATH.read_bytes())
    scope = json.loads(SCOPE_V2_PATH.read_bytes())
    for path, schema_path, value in (
        (RUBRIC_V2_PATH, RUBRIC_SCHEMA_PATH, rubric),
        (SCOPE_V2_PATH, SCOPE_SCHEMA_PATH, scope),
    ):
        Draft202012Validator(
            json.loads(schema_path.read_bytes()),
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        ).validate(value)
        assert path.read_bytes() == canonical_bytes(value) + b"\n"
        assert value["content_hash"] == _content_hash(value)

    current_route_sha256 = hashlib.sha256(ROUTE_PATH.read_bytes()).hexdigest()
    assert current_route_sha256 != ROUTE_SHA256
    for value, old_value in ((rubric, old_rubric), (scope, old_scope)):
        assert value["record_id"] == old_value["record_id"]
        assert value["record_revision"] == 2
        assert value["supersedes_revision"] == 1
        assert value["created_by_actor_id"] == SUCCESSOR_PRODUCER_ACTOR_ID
        assert value["effective_project_scope_ref"]["content_hash"] == current_route_sha256
        source_hashes = {ref.get("id"): ref.get("content_hash") for ref in value["source_refs"]}
        assert source_hashes["SPEC-01"] == SPEC_SHA256
        assert source_hashes["SPEC-GATE6-RUN-V1"] == current_route_sha256

    authority_hashes = {ref["id"]: ref["content_hash"] for ref in rubric["source_authority_refs"]}
    assert authority_hashes == {"SPEC-01": SPEC_SHA256, "SPEC-GATE6-RUN-V1": current_route_sha256}
    assert scope["rubric_ref"] == {
        "id": rubric["record_id"],
        "record_revision": 2,
        "content_hash": rubric["content_hash"],
    }
    assert scope["scope_closure_algorithm_hash"] == _projection_hash(scope, SCOPE_HASH_FIELDS)

    revision_fields = {
        "content_hash",
        "created_at",
        "created_by_actor_id",
        "effective_project_scope_ref",
        "record_revision",
        "source_authority_refs",
        "source_refs",
        "supersedes_revision",
    }
    assert {key: value for key, value in rubric.items() if key not in revision_fields} == {
        key: value for key, value in old_rubric.items() if key not in revision_fields
    }
    scope_revision_fields = revision_fields | {"rubric_ref", "scope_closure_algorithm_hash"}
    assert {key: value for key, value in scope.items() if key not in scope_revision_fields} == {
        key: value for key, value in old_scope.items() if key not in scope_revision_fields
    }
    _validate_semantics(rubric, scope)


@pytest.mark.parametrize(
    ("complete", "topology", "data", "novelty", "expected"),
    [
        (True, True, 1, 3, "PROMOTE"),
        (True, True, 2, 2, "PROMOTE"),
        (True, True, 3, 1, "PROMOTE"),
        (True, False, 3, 3, "KILL"),
        (True, True, 0, 3, "KILL"),
        (True, True, 3, 0, "KILL"),
        (True, True, 1, 2, "PARK"),
        (False, True, 3, 3, "PARTIAL"),
    ],
)
def test_spec01_mechanical_recommendation_truth_table(
    complete: bool,
    topology: bool,
    data: int,
    novelty: int,
    expected: str,
) -> None:
    rubric, _ = _load()
    _validate_semantics(rubric, json.loads(SCOPE_PATH.read_bytes()))
    observed = (
        "PARTIAL"
        if not complete
        else "KILL"
        if topology is False or data == 0 or novelty == 0
        else "PROMOTE"
        if data + novelty >= 4
        else "PARK"
    )
    assert observed == expected


@pytest.mark.parametrize("mutation", ["axis", "rule"])
def test_semantic_drift_is_rejected_even_when_mutation_hashes_are_recomputed(mutation: str) -> None:
    rubric, scope = map(deepcopy, _load())
    if mutation == "axis":
        rubric["evaluation_order"][1:] = reversed(rubric["evaluation_order"][1:])
    else:
        rubric["recommendation_predicates"][1] = "PROMOTE requires data_feasibility + novelty_publishability >= 3"
    rubric["rule_evaluation_algorithm_hash"] = _projection_hash(rubric, RULE_HASH_FIELDS)
    rubric["content_hash"] = _content_hash(rubric)
    scope["rubric_ref"]["content_hash"] = rubric["content_hash"]
    scope["scope_closure_algorithm_hash"] = _projection_hash(scope, SCOPE_HASH_FIELDS)
    scope["content_hash"] = _content_hash(scope)
    with pytest.raises(AssertionError):
        _validate_semantics(rubric, scope)
