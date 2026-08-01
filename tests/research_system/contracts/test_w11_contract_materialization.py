"""Independent static controls for the bounded W11 contract foundation.

This test deliberately owns the expected family/path set.  It does not read a
catalogue, enumerate a registry, or generate an expected side from the files
under test.  The suite is for inert Stage-B materialization only: it does not
activate W11 runtime bindings or create the future expected catalogue.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from research_system.errors import SchemaError
from research_system.schema_registry import _RUNTIME_BINDINGS, bundled_runtime_schema_registry
import tools.verify_w11_materialization as w11_verifier
from tools.verify_w11_materialization import (
    MaterializationVerificationError,
    verify_materialization_document,
    verify_subject_envelope,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPO_ROOT / ".research-system" / "schemas" / "contracts" / "w11"
BOOTSTRAP_CONTRACT = (
    REPO_ROOT / ".research-system" / "contracts" / "w11" / "w11-materialization-bootstrap-contract.yaml"
)
W11_PATH = "docs/plans/agentic-research-system/design/11-portfolio-and-discovery-lifecycle.md"
W11_COMMIT = "892d1d1650cdcf71d2a886318e174a18e11d5de0"
W11_BLOB = "f90729d0c42a0de98d064fac0824d1969c871c82"
W11_SHA256 = "65a7bc6a69c29d9bf7c4bde805aa8103b60738a0c9c63399661c60d37ea40f70"
W11_BYTES = 185214

CONTENT_KINDS = (
    "programme",
    "paper",
    "hypothesis",
    "candidate",
    "method",
    "dataset",
    "claim",
    "dependency-edge",
    "assay-rubric-content",
    "assay-evidence-scope-content",
    "path-registration-content",
    "dossier-expected-set-content",
    "legacy-source-inventory-content",
    "legacy-transition-mapping-content",
    "legacy-cutover-closure-content",
    "w11-schema-catalogue-content",
)
RELATION_KINDS = (
    "candidate",
    "assay",
    "spike",
    "assay-request",
    "assay-producer",
    "assay-bar-acceptance",
    "assay-outcome-review",
    "assay-cancellation-review",
    "spike-plan",
    "spike-attempt",
    "spike-outcome-review",
    "spike-cancellation-review",
    "discovery-promotion",
    "discovery-revisit",
    "authority-content-file-review-acceptance",
    "spike-execution-authority",
    "dossier-expected-set-acceptance",
    "path-registration-acceptance",
    "legacy-source-inventory-acceptance",
    "migration-authority",
    "legacy-path-cutover",
    "dossier-six-family-closure",
    "legacy-source-row-observation",
    "legacy-source-row-target",
    "inventory-mapping-transition-bijection",
    "path-physical-identity",
    "writer-revocation",
    "cutover-closure",
)
ARTEFACT_KINDS = (
    "assay-scorecard",
    "assay-partial",
    "spike-plan",
    "spike-verdict",
    "scout-observation-batch",
    "discovery-annotation",
    "research-dossier-manifest",
    "legacy-record-observed",
    "legacy-portfolio-path-observation",
    "authority-file-observation",
    "review-evidence",
    "collision-scan",
    "writer-revocation-snapshot",
    "projection-rebuild-proof",
)
BOOTSTRAP_KINDS = (
    "w11-catalogue-acceptance-envelope",
    "w11-materialization-bootstrap-contract",
    "import-accepted-w11-catalogue-genesis",
)

EXPECTED_IDS = {
    "ars://portfolio/w11-common-definitions",
    *(f"ars://portfolio/{kind}" for kind in CONTENT_KINDS),
    *(f"ars://portfolio/relation/{kind}" for kind in RELATION_KINDS),
    *(f"ars://portfolio/{kind}" for kind in ARTEFACT_KINDS),
    *(f"ars://portfolio/{kind}" for kind in BOOTSTRAP_KINDS),
}

CONTENT_SCHEMA_IDS = {f"ars://portfolio/{kind}" for kind in CONTENT_KINDS}

_HASH = "0" * 64


def _record_ref(identifier: str = "obj_00000000-0000-7000-8000-000000000001") -> dict[str, Any]:
    return {"id": identifier, "record_revision": 1, "content_hash": _HASH}


def _source_ref() -> dict[str, Any]:
    return {"ref_kind": "record", **_record_ref()}


VALID_PROGRAMME = {
    "schema_id": "ars://portfolio/programme",
    "schema_version": "1.0.0",
    "record_id": "obj_00000000-0000-7000-8000-000000000001",
    "record_revision": 1,
    "supersedes_revision": None,
    "project_id": "prj_00000000-0000-7000-8000-000000000001",
    "portfolio_kind": "programme",
    "aliases": [],
    "created_at": "2026-01-01T00:00:00Z",
    "created_by_actor_id": "act_00000000-0000-7000-8000-000000000001",
    "source_refs": [_source_ref()],
    "content_hash": _HASH,
    "title": "A bounded programme",
    "research_questions": ["Does the claim hold?"],
    "intended_contributions": ["A reproducible answer"],
    "falsification_value": "A failed test is informative",
    "negative_result_value": "The null result is retained",
    "resource_envelope_ref": _record_ref(),
    "promotion_policy_ref": _record_ref(),
    "dependency_edge_refs": [_record_ref("obj_00000000-0000-7000-8000-000000000002")],
}

VALID_DISCOVERY_PROMOTION = {
    "schema_id": "ars://portfolio/relation/discovery-promotion",
    "schema_version": "1.0.0",
    "relation_kind": "discovery_promotion",
    "decision_id": "dec_00000000-0000-7000-8000-000000000001",
    "candidate_ref": _record_ref(),
    "gate": "assay_to_spike",
    "aggregate_ref": _record_ref(),
    "aggregate_relation_hash": _HASH,
    "evidence_ref": _record_ref(),
    "selected_option": "PROMOTE",
    "next_candidate_state": "spike_planned",
    "rationale": "The predeclared gate is met.",
    "considered_evidence_refs": [_record_ref()],
    "conditions": [],
    "effective_scope": "project",
    "revisit_triggers": [],
    "actor_id": "act_00000000-0000-7000-8000-000000000001",
}

VALID_SCORECARD = {
    "schema_id": "ars://portfolio/assay-scorecard",
    "schema_version": "1.0.0",
    "candidate_ref": _record_ref(),
    "assay_id": "asy_00000000-0000-7000-8000-000000000001",
    "assay_requested_event_ref": _record_ref(),
    "assay_relation_hash": _HASH,
    "rubric_ref": _record_ref(),
    "scope_ref": _record_ref(),
    "assay_bar_acceptance_ref": _record_ref(),
    "file_observation_refs": [_record_ref(), _record_ref()],
    "producer_relation_ref": _record_ref(),
    "axis_results": [
        {
            "axis_id": "design",
            "axis_kind": "gate",
            "value": True,
            "rationale": "The design is pre-specified.",
            "evidence_refs": [_record_ref()],
            "unmet_condition_codes": [],
            "validator_id": "validator.design",
            "validator_hash": _HASH,
        }
    ],
    "required_axis_set_hash": _HASH,
    "observed_axis_set_hash": _HASH,
    "mechanical_recommendation": "PROMOTE",
    "rule_evaluation_ref": _record_ref(),
    "limitations": [],
    "prohibited_inferences": ["This score is not causal evidence."],
    "producer_actor_id": "act_00000000-0000-7000-8000-000000000001",
    "producer_profile_ref": _record_ref(),
    "producer_context_ref": _record_ref(),
    "review_requirements": [],
}

VALID_DISCOVERY_REVISIT = {
    "schema_id": "ars://portfolio/relation/discovery-revisit",
    "schema_version": "1.0.0",
    "relation_kind": "discovery_revisit",
    "decision_id": "dec_00000000-0000-7000-8000-000000000001",
    "candidate_ref": _record_ref(),
    "prior_aggregate_ref": _record_ref(),
    "prior_outcome_review_ref": _record_ref(),
    "satisfied_revisit_predicate_ref": _record_ref(),
    "selected_option": "RETRY",
    "actor_id": "act_00000000-0000-7000-8000-000000000001",
}

VALID_SPIKE_VERDICT = {
    "schema_id": "ars://portfolio/spike-verdict",
    "schema_version": "1.0.0",
    "spike_id": "spk_00000000-0000-7000-8000-000000000001",
    "candidate_ref": _record_ref(),
    "originating_assay_ref": _record_ref(),
    "spike_plan_ref": _record_ref(),
    "attempt_ref": _record_ref(),
    "verdict": "PASS",
    "success_predicates": [{"predicate": "success", "status": "passed", "evidence_refs": [_record_ref()]}],
    "failure_predicates": [],
    "kill_conditions": [],
    "artefact_refs": [],
    "validation_refs": [],
    "completed_scope": "The declared scope completed.",
    "unmet_scope": "None.",
    "limitations": [],
    "mechanical_recommendation": "NONE",
    "prohibited_inferences": ["This verdict does not authorize dispatch."],
}

VALID_REVIEW_EVIDENCE = {
    "schema_id": "ars://portfolio/review-evidence",
    "schema_version": "1.0.0",
    "subject_ref": _record_ref(),
    "file_observation_ref": _record_ref(),
    "reviewer_actor_id": "act_00000000-0000-7000-8000-000000000001",
    "reviewer_relationship_ref": _record_ref(),
    "verdict": "accept_exact_subject",
    "severity_findings": [],
    "reviewed_at": "2026-01-01T00:00:00Z",
    "evidence_refs": [_record_ref()],
}

VALID_SPIKE_PLAN = {
    "schema_id": "ars://portfolio/spike-plan",
    "schema_version": "1.0.0",
    "spike_id": "spk_00000000-0000-7000-8000-000000000001",
    "candidate_ref": _record_ref(),
    "originating_assay_ref": _record_ref(),
    "source_scorecard_refs": [_record_ref()],
    "assay_promotion_decision_ref": _record_ref(),
    "required_approving_authority": "Stephen",
    "time_resource_box": {
        "time_limit_seconds": 3600,
        "worker_limit": 1,
        "memory_limit_mb": 1024,
        "storage_limit_mb": 4096,
        "network_access": False,
    },
    "question": "Does the bounded spike predicate hold?",
    "scope": "Synthetic validation only.",
    "inputs": ["input-a"],
    "method_or_object": "bounded method",
    "baselines": [],
    "null_or_comparator": None,
    "success_predicates": ["success"],
    "failure_predicates": [],
    "kill_conditions": [],
    "partial_rules": [],
    "planned_contracts": ["contract-a"],
    "outputs": ["output-a"],
    "prohibited_work": [],
    "outcome_to_next_step": {"PASS": "stop"},
}


def _test_canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _test_hash(value: Any) -> str:
    return hashlib.sha256(_test_canonical_bytes(value)).hexdigest()


def _test_multiset_hash(rows: list[dict[str, Any]]) -> str:
    return _test_hash(sorted(rows, key=_test_canonical_bytes))


@lru_cache(maxsize=1)
def _schemas() -> tuple[tuple[Path, dict[str, Any]], ...]:
    paths = sorted(SCHEMA_ROOT.rglob("*.schema.json"))
    nested_paths = [path for path in paths if path.parent != SCHEMA_ROOT]
    if nested_paths:
        pytest.fail(f"W11 schema catalogue must be flat; unexpected nested schema {nested_paths[0]}")
    return tuple((path, json.loads(path.read_text(encoding="utf-8"))) for path in paths)


def _validate(schema: dict[str, Any], value: dict[str, Any]) -> None:
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        pytest.fail("; ".join(error.message for error in errors))


def _schema_by_id(schema_id: str) -> dict[str, Any]:
    return next(schema for _, schema in _schemas() if schema["$id"] == schema_id)


def _fragment_is_valid(schema: dict[str, Any], definition: str, value: dict[str, Any]) -> bool:
    fragment = {
        "$schema": schema["$schema"],
        "$ref": f"#/$defs/{definition}",
        "$defs": schema["$defs"],
    }
    return Draft202012Validator(
        fragment,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    ).is_valid(value)


def _owner_contract_row(owner_row_id: str, *, test_owner_row_id: str | None = None) -> dict[str, Any]:
    bound_test_owner_row_id = test_owner_row_id or owner_row_id
    return {
        "owner_row_id": owner_row_id,
        "logical_key": f"owner:{owner_row_id}",
        "schema_id": f"ars://portfolio/owner/{owner_row_id.lower()}",
        "schema_version": "1.0.0",
        "file_observation_ref": _record_ref(),
        "command_type": "C:test",
        "payload_discriminant": "test",
        "eligible_profile": "profile:test",
        "authority_subject": "subject:test",
        "preconditions": ["precondition"],
        "ordered_events": ["event"],
        "affected_streams": ["stream"],
        "complete_write_set": ["write"],
        "reducer": "U:test",
        "projection_targets": ["P:test"],
        "receipt_identity": "R:test",
        "positive_test_identity": f"W11-T01-{bound_test_owner_row_id}",
        "negative_mutation_test_identity": f"W11-T03-{bound_test_owner_row_id}-owner-row-mutation",
        "retry_test_identity": f"W11-T11-{bound_test_owner_row_id}",
    }


def _schema_source_row(logical_key: str, schema_id: str, filename: str) -> dict[str, Any]:
    return {
        "logical_key": logical_key,
        "schema_id": schema_id,
        "schema_version": "1.0.0",
        "repository_path": f".research-system/schemas/contracts/w11/{filename}",
        "git_commit": "0" * 40,
        "git_blob": "0" * 40,
        "file_length": 1,
        "file_sha256": _HASH,
        "independent_observation_ref": _record_ref(),
    }


def _valid_catalogue() -> dict[str, Any]:
    owner_row_ids = [
        *(f"OR-{number:03d}" for number in range(1, 42)),
        *(f"OR-{number:03d}" for number in range(101, 141)),
    ]
    return {
        "schema_id": "ars://portfolio/w11-schema-catalogue-content",
        "schema_version": "1.0.0",
        "record_id": "obj_00000000-0000-7000-8000-000000000003",
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": "prj_00000000-0000-7000-8000-000000000001",
        "portfolio_kind": "w11_schema_catalogue_content",
        "aliases": [],
        "created_at": "2026-01-01T00:00:00Z",
        "created_by_actor_id": "act_00000000-0000-7000-8000-000000000001",
        "source_refs": [_source_ref()],
        "content_hash": _HASH,
        "owner_spec_identity": {
            "repository_path": W11_PATH,
            "reviewed_commit": W11_COMMIT,
            "git_blob": W11_BLOB,
            "raw_sha256": W11_SHA256,
            "raw_bytes": W11_BYTES,
        },
        "owner_row_count": 81,
        "owner_row_range_hash": _HASH,
        "schema_source_rows": [
            *(
                _schema_source_row(
                    f"content:{kind}",
                    f"ars://portfolio/{kind}",
                    f"{kind}.schema.json",
                )
                for kind in CONTENT_KINDS
            ),
            *(
                _schema_source_row(
                    f"relation:{kind}",
                    f"ars://portfolio/relation/{kind}",
                    f"relation-{kind}.schema.json",
                )
                for kind in RELATION_KINDS
            ),
            *(
                _schema_source_row(
                    f"artefact:{kind}",
                    f"ars://portfolio/{kind}",
                    f"{kind}.schema.json",
                )
                for kind in ARTEFACT_KINDS
            ),
            *(
                _schema_source_row(
                    f"bootstrap:{kind}",
                    f"ars://portfolio/{kind}",
                    f"{kind}.schema.json",
                )
                for kind in BOOTSTRAP_KINDS
            ),
        ],
        "owner_contract_rows": [_owner_contract_row(owner_row_id) for owner_row_id in owner_row_ids],
    }


def _axis_definition(axis_kind: str, value_type: str, domain: str) -> dict[str, Any]:
    axis = {
        "axis_id": f"{axis_kind}-axis",
        "axis_kind": axis_kind,
        "value_schema": value_type,
        "value_type": value_type,
        "required": True,
        "evidence_type_allowlist": ["ars://portfolio/review-evidence"],
        "validator_schema_id": f"ars://portfolio/validator/{axis_kind}",
        "validator_schema_version": "1.0.0",
        "failure_codes": ["not_met"],
    }
    if domain == "allowed_set":
        axis["allowed_set"] = [False, True] if axis_kind == "gate" else [0, 1]
    else:
        axis["bounds"] = {"minimum": 0, "maximum": 1 if axis_kind == "registered_measure" else 3}
    return axis


def _valid_rubric() -> dict[str, Any]:
    return {
        "schema_id": "ars://portfolio/assay-rubric-content",
        "schema_version": "1.0.0",
        "record_id": "obj_00000000-0000-7000-8000-000000000001",
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": "prj_00000000-0000-7000-8000-000000000001",
        "portfolio_kind": "assay_rubric_content",
        "aliases": [],
        "created_at": "2026-01-01T00:00:00Z",
        "created_by_actor_id": "act_00000000-0000-7000-8000-000000000001",
        "source_refs": [_source_ref()],
        "content_hash": _HASH,
        "rubric_id": "rubric.initial",
        "accepted_owner_requirement_refs": [_record_ref()],
        "domain_pack_refs": [_record_ref("obj_00000000-0000-7000-8000-000000000002")],
        "axis_definitions": [
            {
                "axis_id": "design",
                "axis_kind": "gate",
                "value_schema": "boolean",
                "value_type": "boolean",
                "allowed_set": [False, True],
                "required": True,
                "evidence_type_allowlist": ["ars://portfolio/review-evidence"],
                "validator_schema_id": "ars://portfolio/validator/design",
                "validator_schema_version": "1.0.0",
                "failure_codes": ["not_met"],
            }
        ],
        "required_axis_ids": ["design"],
        "forbidden_axis_ids": [],
        "required_axis_set_hash": _HASH,
        "evaluation_order": ["design"],
        "recommendation_predicates": ["all required axes pass"],
        "hard_gate_predicates": ["design"],
        "partial_predicates": ["incomplete"],
        "park_predicates": ["uncertain"],
        "kill_predicates": ["unsafe"],
        "rule_evaluation_algorithm_id": "test-rule-evaluator",
        "rule_evaluation_algorithm_version": "1.0.0",
        "rule_evaluation_algorithm_hash": _HASH,
        "source_authority_refs": [_record_ref()],
        "limitations": ["Fixture only."],
        "prohibited_inferences": ["This rubric is not a result."],
        "effective_candidate_kinds": ["method"],
        "effective_project_scope_ref": _record_ref(),
    }


VALID_RUBRIC = _valid_rubric()


def _valid_dossier_expected_set() -> dict[str, Any]:
    rows = {
        "components": [
            {
                "component_key": "component-a",
                "component_kind": "schema",
                "schema_id": "ars://portfolio/component-a",
                "schema_version": "1.0.0",
                "root_id": "root-a",
                "relative_path_or_object_ref": "component-a.json",
                "size_bytes": 1,
                "sha256": _HASH,
                "required": True,
                "dependency_keys": [],
                "permitted_consumers": ["dossier-admission"],
                "confidentiality_class": "public",
            }
        ],
        "sources": [
            {
                "source_key": "source-a",
                "source_kind": "file",
                "schema_or_media_type": "application/json",
                "root_id": "root-a",
                "relative_path_or_locator": "source-a.json",
                "size_bytes": 1,
                "sha256": _HASH,
                "source_authority_class": "independent",
                "required": True,
                "permitted_consumers": ["dossier-admission"],
                "confidentiality_class": "public",
                "independent_resolution_policy_id": "policy-a",
                "independent_resolution_policy_hash": _HASH,
            }
        ],
        "objects": [
            {
                "object_key": "object-a",
                "portfolio_kind": "candidate",
                "schema_id": "ars://portfolio/candidate",
                "schema_version": "1.0.0",
                "proposed_record_id": "obj_00000000-0000-7000-8000-000000000004",
                "proposed_revision": 1,
                "blueprint_hash": _HASH,
                "expected_content_hash": _HASH,
                "source_keys": ["source-a"],
                "permitted_consumers": ["dossier-admission"],
            }
        ],
        "scope_definitions": [
            {
                "scope_key": "scope-a",
                "scope_schema_id": "ars://portfolio/scope",
                "scope_schema_version": "1.0.0",
                "proposed_scope_id": "scope-a-id",
                "proposed_revision": 1,
                "blueprint_hash": _HASH,
                "expected_content_hash": _HASH,
                "governing_object_keys": ["object-a"],
                "permitted_consumers": ["dossier-admission"],
            }
        ],
        "dependency_edges": [
            {
                "edge_key": "edge-a",
                "edge_type": "requires",
                "proposed_edge_id": "obj_00000000-0000-7000-8000-000000000005",
                "proposed_revision": 1,
                "from_key": "object-a",
                "from_revision": 1,
                "from_hash": _HASH,
                "to_key": "object-a",
                "to_revision": 1,
                "to_hash": _HASH,
                "required": True,
                "satisfaction_predicate_ref_or_null": None,
                "effective_scope_key": "scope-a",
                "expected_content_hash": _HASH,
            }
        ],
        "relationships": [
            {
                "relationship_key": "relationship-a",
                "relationship_kind": "candidate",
                "ordered_member_keys_with_revisions_hashes": [f"object-a:1:{_HASH}"],
                "relation_schema_id": "ars://portfolio/relation/candidate",
                "relation_schema_version": "1.0.0",
                "relation_hash": _HASH,
            }
        ],
    }
    value: dict[str, Any] = {
        "schema_id": "ars://portfolio/dossier-expected-set-content",
        "schema_version": "1.0.0",
        "record_id": "obj_00000000-0000-7000-8000-000000000003",
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": "prj_00000000-0000-7000-8000-000000000001",
        "portfolio_kind": "dossier_expected_set_content",
        "aliases": [],
        "created_at": "2026-01-01T00:00:00Z",
        "created_by_actor_id": "act_00000000-0000-7000-8000-000000000001",
        "source_refs": [_source_ref()],
        "content_hash": _HASH,
        "expected_set_id": "expected-set-a",
        "dossier_ref": _record_ref(),
        "package_version": "1.0.0",
        "admission_profile_ref": _record_ref("obj_00000000-0000-7000-8000-000000000002"),
        "effective_from": "2026-01-01T00:00:00Z",
        "effective_until": None,
        "accepted_owner_requirement_refs": [_record_ref()],
        "source_authority_refs": [_record_ref()],
        "author_actor_id": "act_00000000-0000-7000-8000-000000000001",
        "producing_context_ref": _record_ref(),
        **rows,
    }
    for row_key, count_key, hash_key in (
        ("components", "component_count", "component_multiset_hash"),
        ("sources", "source_count", "source_multiset_hash"),
        ("objects", "object_count", "object_multiset_hash"),
        ("scope_definitions", "scope_count", "scope_multiset_hash"),
        ("dependency_edges", "edge_count", "edge_multiset_hash"),
        ("relationships", "relationship_count", "relationship_multiset_hash"),
    ):
        value[count_key] = len(rows[row_key])
        value[hash_key] = _test_multiset_hash(rows[row_key])
    value["expected_set_closure_hash"] = _test_hash(
        {
            "manifest_schema_id": value["schema_id"],
            "manifest_schema_version": value["schema_version"],
            "package_version": value["package_version"],
            "admission_profile_hash": value["admission_profile_ref"]["content_hash"],
            "components": sorted(rows["components"], key=_test_canonical_bytes),
            "source_dependencies": sorted(rows["sources"], key=_test_canonical_bytes),
            "objects": sorted(rows["objects"], key=_test_canonical_bytes),
            "scope_definitions": sorted(rows["scope_definitions"], key=_test_canonical_bytes),
            "dependency_edges": sorted(rows["dependency_edges"], key=_test_canonical_bytes),
            "relationships": sorted(rows["relationships"], key=_test_canonical_bytes),
        }
    )
    return value


VALID_DOSSIER_EXPECTED_SET = _valid_dossier_expected_set()


def test_representative_valid_examples_cover_content_relation_and_artifact() -> None:
    _validate(_schema_by_id("ars://portfolio/programme"), VALID_PROGRAMME)
    _validate(_schema_by_id("ars://portfolio/relation/discovery-promotion"), VALID_DISCOVERY_PROMOTION)
    _validate(_schema_by_id("ars://portfolio/relation/discovery-revisit"), VALID_DISCOVERY_REVISIT)
    _validate(_schema_by_id("ars://portfolio/assay-scorecard"), VALID_SCORECARD)
    _validate(_schema_by_id("ars://portfolio/spike-verdict"), VALID_SPIKE_VERDICT)
    _validate(_schema_by_id("ars://portfolio/review-evidence"), VALID_REVIEW_EVIDENCE)
    _validate(_schema_by_id("ars://portfolio/spike-plan"), VALID_SPIKE_PLAN)


def test_owner_row_ids_are_exactly_the_two_w11_ranges() -> None:
    schema = _schema_by_id("ars://portfolio/w11-schema-catalogue-content")
    for owner_row_id in ("OR-001", "OR-040", "OR-041", "OR-101", "OR-140"):
        assert _fragment_is_valid(schema, "ownerContractRow", _owner_contract_row(owner_row_id))
    for owner_row_id in ("OR-000", "OR-042", "OR-100", "OR-141", "OR-01", "OR-1041"):
        assert not _fragment_is_valid(schema, "ownerContractRow", _owner_contract_row(owner_row_id))


def test_content_source_refs_use_only_their_ref_kind_identity() -> None:
    valid_refs = (
        {"ref_kind": "record", **_record_ref()},
        {
            "ref_kind": "artefact",
            "id": "art_00000000-0000-7000-8000-000000000001",
            "record_revision": 2,
            "content_hash": _HASH,
        },
        {"ref_kind": "external", "locator": "https://example.invalid/source", "content_hash": _HASH},
    )
    invalid_refs = (
        {"ref_kind": "external", "locator": "https://example.invalid/source", "id": "obj_1", "content_hash": _HASH},
        {"ref_kind": "record", "locator": "https://example.invalid/source", "content_hash": _HASH},
        {
            "ref_kind": "artefact",
            "id": "art_00000000-0000-7000-8000-000000000001",
            "record_revision": 2,
            "locator": "foreign",
            "content_hash": _HASH,
        },
    )
    for schema_id in sorted(CONTENT_SCHEMA_IDS):
        schema = _schema_by_id(schema_id)
        for source_ref in valid_refs:
            assert _fragment_is_valid(schema, "sourceRef", source_ref), schema_id
        for source_ref in invalid_refs:
            assert not _fragment_is_valid(schema, "sourceRef", source_ref), schema_id


def test_assay_axis_domains_and_scorecard_values_are_typed_and_closed() -> None:
    rubric_schema = _schema_by_id("ars://portfolio/assay-rubric-content")
    for axis_kind, value_type, domain in (
        ("gate", "boolean", "allowed_set"),
        ("integer_score", "integer", "bounds"),
        ("registered_measure", "number", "bounds"),
    ):
        assert _fragment_is_valid(
            rubric_schema,
            "axisDefinition",
            _axis_definition(axis_kind, value_type, domain),
        )

    missing_type = _axis_definition("gate", "boolean", "allowed_set")
    missing_type.pop("value_type")
    assert not _fragment_is_valid(rubric_schema, "axisDefinition", missing_type)
    missing_domain = _axis_definition("integer_score", "integer", "bounds")
    missing_domain.pop("bounds")
    assert not _fragment_is_valid(rubric_schema, "axisDefinition", missing_domain)
    wrong_domain = _axis_definition("gate", "integer", "bounds")
    assert not _fragment_is_valid(rubric_schema, "axisDefinition", wrong_domain)

    scorecard_schema = _schema_by_id("ars://portfolio/assay-scorecard")
    for axis_kind, value in (("gate", True), ("integer_score", 2), ("registered_measure", 0.5)):
        axis_result = deepcopy(VALID_SCORECARD["axis_results"][0])
        axis_result["axis_kind"] = axis_kind
        axis_result["value"] = value
        assert _fragment_is_valid(scorecard_schema, "axisResult", axis_result)
    for value in (None, {}, [], "not-a-score"):
        axis_result = deepcopy(VALID_SCORECARD["axis_results"][0])
        axis_result["value"] = value
        assert not _fragment_is_valid(scorecard_schema, "axisResult", axis_result)
    wrong_gate_domain = deepcopy(VALID_SCORECARD["axis_results"][0])
    wrong_gate_domain["value"] = 1
    assert not _fragment_is_valid(scorecard_schema, "axisResult", wrong_gate_domain)
    wrong_integer_domain = deepcopy(VALID_SCORECARD["axis_results"][0])
    wrong_integer_domain["axis_kind"] = "integer_score"
    wrong_integer_domain["value"] = True
    assert not _fragment_is_valid(scorecard_schema, "axisResult", wrong_integer_domain)
    empty_evidence = deepcopy(VALID_SCORECARD["axis_results"][0])
    empty_evidence["evidence_refs"] = []
    assert not _fragment_is_valid(scorecard_schema, "axisResult", empty_evidence)


def test_spike_verdict_requires_evidence_and_an_applicable_predicate() -> None:
    schema = _schema_by_id("ars://portfolio/spike-verdict")
    assert Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).is_valid(
        VALID_SPIKE_VERDICT
    )

    empty_evidence = deepcopy(VALID_SPIKE_VERDICT)
    empty_evidence["success_predicates"][0]["evidence_refs"] = []
    assert not Draft202012Validator(schema).is_valid(empty_evidence)

    no_success_predicate = deepcopy(VALID_SPIKE_VERDICT)
    no_success_predicate["success_predicates"] = []
    assert not Draft202012Validator(schema).is_valid(no_success_predicate)

    failure_with_evidence = deepcopy(VALID_SPIKE_VERDICT)
    failure_with_evidence["verdict"] = "FAIL"
    failure_with_evidence["success_predicates"] = []
    failure_with_evidence["failure_predicates"] = [
        {"predicate": "failure", "status": "failed", "evidence_refs": [_record_ref()]}
    ]
    assert Draft202012Validator(schema).is_valid(failure_with_evidence)


def test_review_evidence_cannot_accept_blocking_findings() -> None:
    schema = _schema_by_id("ars://portfolio/review-evidence")
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    assert validator.is_valid(VALID_REVIEW_EVIDENCE)

    for severity in ("Critical", "Major"):
        blocking = deepcopy(VALID_REVIEW_EVIDENCE)
        blocking["severity_findings"] = [{"severity": severity, "finding_id": "finding-1", "disposition": "open"}]
        assert not validator.is_valid(blocking)

    non_blocking = deepcopy(VALID_REVIEW_EVIDENCE)
    non_blocking["severity_findings"] = [{"severity": "Minor", "finding_id": "finding-1", "disposition": "open"}]
    assert validator.is_valid(non_blocking)


def test_spike_plan_time_resource_box_is_bounded_and_non_empty() -> None:
    schema = _schema_by_id("ars://portfolio/spike-plan")
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    assert validator.is_valid(VALID_SPIKE_PLAN)

    empty = deepcopy(VALID_SPIKE_PLAN)
    empty["time_resource_box"] = {}
    assert not validator.is_valid(empty)

    unknown_constraint = deepcopy(VALID_SPIKE_PLAN)
    unknown_constraint["time_resource_box"]["unbounded_constraint"] = True
    assert not validator.is_valid(unknown_constraint)


def test_w11_timestamps_require_utc_rfc3339_z_with_format_checking() -> None:
    schema = _schema_by_id("ars://portfolio/programme")
    _validate(schema, VALID_PROGRAMME)
    offset_timestamp = deepcopy(VALID_PROGRAMME)
    offset_timestamp["created_at"] = "2026-01-01T01:00:00+01:00"
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    assert not validator.is_valid(offset_timestamp)


def test_physical_identity_contracts_share_one_canonical_shape() -> None:
    expected = {
        "type": "object",
        "required": [
            "canonical_target",
            "reparse_chain",
            "volume_serial_number",
            "stable_file_id",
            "link_count",
            "case_aliases",
            "unicode_aliases",
            "short_name_aliases",
        ],
        "properties": {
            "canonical_target": {"type": "string", "minLength": 1},
            "reparse_chain": {"type": "array", "items": {"type": "string", "minLength": 1}},
            "volume_serial_number": {"type": "string", "minLength": 1},
            "stable_file_id": {"type": "string", "minLength": 1},
            "link_count": {"type": "integer", "minimum": 1},
            "case_aliases": {"type": "array", "items": {"type": "string", "minLength": 1}},
            "unicode_aliases": {"type": "array", "items": {"type": "string", "minLength": 1}},
            "short_name_aliases": {"type": "array", "items": {"type": "string", "minLength": 1}},
        },
        "additionalProperties": False,
    }
    definitions = (
        ("ars://portfolio/path-registration-content", "resolved_physical_identity"),
        ("ars://portfolio/legacy-source-inventory-content", "opened_physical_identity"),
        ("ars://portfolio/legacy-cutover-closure-content", "physical_identity"),
        ("ars://portfolio/legacy-portfolio-path-observation", "physical_identity"),
        ("ars://portfolio/legacy-record-observed", "physical_source_identity"),
    )
    for schema_id, property_name in definitions:
        schema = _schema_by_id(schema_id)
        assert schema["properties"][property_name]["$ref"] == "#/$defs/physicalIdentity"
        assert schema["$defs"]["physicalIdentity"] == expected

    relation_schema = _schema_by_id("ars://portfolio/relation/path-physical-identity")
    relation_shape = {key: relation_schema[key] for key in ("type", "required", "properties", "additionalProperties")}
    assert relation_shape == {
        "type": expected["type"],
        "required": ["schema_id", "schema_version", "relation_kind", *expected["required"]],
        "properties": {
            "schema_id": {"const": "ars://portfolio/relation/path-physical-identity"},
            "schema_version": {"const": "1.0.0"},
            "relation_kind": {"const": "path-physical-identity"},
            **expected["properties"],
        },
        "additionalProperties": False,
    }


def test_path_physical_identity_rejects_empty_alias_entries() -> None:
    schema = _schema_by_id("ars://portfolio/relation/path-physical-identity")
    value = {
        "schema_id": "ars://portfolio/relation/path-physical-identity",
        "schema_version": "1.0.0",
        "relation_kind": "path-physical-identity",
        "canonical_target": "C:/vault",
        "reparse_chain": ["C:/vault"],
        "volume_serial_number": "volume-1",
        "stable_file_id": "file-1",
        "link_count": 1,
        "case_aliases": ["C:/VAULT"],
        "unicode_aliases": ["C:/vault"],
        "short_name_aliases": ["C:/VAULT~1"],
    }
    validator = Draft202012Validator(schema)
    assert validator.is_valid(value)
    for field in ("reparse_chain", "case_aliases", "unicode_aliases", "short_name_aliases"):
        invalid = deepcopy(value)
        invalid[field] = [""]
        assert not validator.is_valid(invalid), field


def test_relation_discriminators_match_bootstrap_slugs() -> None:
    for kind in ("assay", "candidate", "spike-plan", "spike", "spike-attempt"):
        schema = _schema_by_id(f"ars://portfolio/relation/{kind}")
        assert schema["properties"]["relation_kind"]["const"] == kind


def test_discovery_revisit_requires_actor_attribution() -> None:
    schema = _schema_by_id("ars://portfolio/relation/discovery-revisit")
    validator = Draft202012Validator(schema)
    assert validator.is_valid(VALID_DISCOVERY_REVISIT)
    missing_actor = deepcopy(VALID_DISCOVERY_REVISIT)
    missing_actor.pop("actor_id")
    assert not validator.is_valid(missing_actor)


def test_research_dossier_prohibited_adoption_claims_reject_empty_strings() -> None:
    schema = _schema_by_id("ars://portfolio/research-dossier-manifest")
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    manifest = {
        "schema_id": "ars://portfolio/research-dossier-manifest",
        "schema_version": "1.0.0",
        "dossier_logical_id": "dossier-a",
        "dossier_revision": 1,
        "package_version": "1.0.0",
        "purpose": "Fixture",
        "author": "actor-a",
        "created_at": "2026-01-01T00:00:00Z",
        "governing_decisions": [],
        "component_count": 0,
        "components": [],
        "source_dependency_count": 0,
        "source_dependencies": [],
        "object_blueprints": [],
        "scope_definition_blueprints": [],
        "dependency_edges": [],
        "relationships": [],
        "object_count": 0,
        "scope_count": 0,
        "edge_count": 0,
        "relationship_count": 0,
        "admission_profile_ref": _record_ref(),
        "ownership_declarations": ["successor-owned only"],
        "prohibited_adoption_claims": ["legacy prose is not authority"],
        "closure_hash": _HASH,
    }
    assert validator.is_valid(manifest)
    invalid = deepcopy(manifest)
    invalid["prohibited_adoption_claims"] = [""]
    assert not validator.is_valid(invalid)


def test_production_w11_materialization_base_is_stable() -> None:
    assert w11_verifier.W11_MATERIALIZATION_BASE == "c84eb2aaf0890d36d3735d08a14169f4c50935cd"


def test_w11_exact_subject_range_keeps_runtime_activation_bounded(
    monkeypatch: pytest.MonkeyPatch, synthetic_w11_dag: dict[str, Any]
) -> None:
    monkeypatch.setattr(w11_verifier, "W11_MATERIALIZATION_BASE", synthetic_w11_dag["base"])
    envelope = _subject_envelope(synthetic_w11_dag["repo"], synthetic_w11_dag["base"], synthetic_w11_dag["subject"])
    verify_subject_envelope(synthetic_w11_dag["repo"], envelope)


@pytest.mark.parametrize(
    "mutation", ["missing", "extra", "swapped", "wrong_commit", "wrong_tree", "wrong_path", "wrong_blob"]
)
def test_w11_subject_envelope_rejects_incomplete_or_substituted_identity(
    mutation: str, monkeypatch: pytest.MonkeyPatch, synthetic_w11_dag: dict[str, Any]
) -> None:
    monkeypatch.setattr(w11_verifier, "W11_MATERIALIZATION_BASE", synthetic_w11_dag["base"])
    envelope = _subject_envelope(synthetic_w11_dag["repo"], synthetic_w11_dag["base"], synthetic_w11_dag["subject"])
    if mutation == "missing":
        envelope["changed_paths"] = envelope["changed_paths"][1:]
    elif mutation == "extra":
        envelope["changed_paths"].append({"path": "tools/not-a-change.py", "blob": "0" * 40})
    elif mutation == "swapped":
        first, second = envelope["changed_paths"][:2]
        first["blob"], second["blob"] = second["blob"], first["blob"]
    elif mutation == "wrong_commit":
        envelope["subject_commit"] = synthetic_w11_dag["base"]
    elif mutation == "wrong_tree":
        envelope["subject_tree"] = "0" * 40
    elif mutation == "wrong_path":
        envelope["changed_paths"][0]["path"] = "tools/not-a-change.py"
    elif mutation == "wrong_blob":
        envelope["changed_paths"][0]["blob"] = "0" * 40
    with pytest.raises(MaterializationVerificationError):
        verify_subject_envelope(synthetic_w11_dag["repo"], envelope)


def test_w11_subject_envelope_rejects_complete_non_ancestor_before_range_comparison(
    monkeypatch: pytest.MonkeyPatch, synthetic_w11_dag: dict[str, Any]
) -> None:
    monkeypatch.setattr(w11_verifier, "W11_MATERIALIZATION_BASE", synthetic_w11_dag["base"])
    envelope = _subject_envelope(synthetic_w11_dag["repo"], synthetic_w11_dag["base"], synthetic_w11_dag["unrelated"])
    with pytest.raises(MaterializationVerificationError, match="base_commit must be an ancestor of subject_commit"):
        verify_subject_envelope(synthetic_w11_dag["repo"], envelope)


def test_w11_content_semantics_are_enforced_at_inert_verifier_admission() -> None:
    verify_materialization_document(SCHEMA_ROOT, "ars://portfolio/programme", VALID_PROGRAMME)

    wrong_predecessor = deepcopy(VALID_PROGRAMME)
    wrong_predecessor["record_revision"] = 3
    wrong_predecessor["supersedes_revision"] = 1
    with pytest.raises(SchemaError, match="exact predecessor"):
        verify_materialization_document(SCHEMA_ROOT, "ars://portfolio/programme", wrong_predecessor)

    wrong_first_revision = deepcopy(VALID_PROGRAMME)
    wrong_first_revision["supersedes_revision"] = 1
    with pytest.raises(SchemaError, match="revision 1 must have null"):
        verify_materialization_document(SCHEMA_ROOT, "ars://portfolio/programme", wrong_first_revision)

    valid_artefact_source = deepcopy(VALID_PROGRAMME)
    valid_artefact_source["source_refs"] = [
        {
            "ref_kind": "artefact",
            "id": "art_00000000-0000-7000-8000-000000000001",
            "record_revision": 2,
            "content_hash": _HASH,
        }
    ]
    verify_materialization_document(SCHEMA_ROOT, "ars://portfolio/programme", valid_artefact_source)

    cross_kind_source = deepcopy(VALID_PROGRAMME)
    cross_kind_source["source_refs"] = [
        {"ref_kind": "artefact", "id": VALID_PROGRAMME["record_id"], "record_revision": 1, "content_hash": _HASH}
    ]
    with pytest.raises(SchemaError, match="canonical art_ UUID"):
        verify_materialization_document(SCHEMA_ROOT, "ars://portfolio/programme", cross_kind_source)

    malformed_identity = deepcopy(VALID_PROGRAMME)
    malformed_identity["source_refs"] = [
        {"ref_kind": "record", "id": "obj_not-a-uuid", "record_revision": 1, "content_hash": _HASH}
    ]
    with pytest.raises(SchemaError, match="canonical obj_ UUID"):
        verify_materialization_document(SCHEMA_ROOT, "ars://portfolio/programme", malformed_identity)


def test_w11_catalogue_binds_each_owner_row_to_its_literal_tests() -> None:
    catalogue = _valid_catalogue()
    verify_materialization_document(SCHEMA_ROOT, "ars://portfolio/w11-schema-catalogue-content", catalogue)

    swapped = deepcopy(catalogue)
    swapped["owner_contract_rows"][-1] = _owner_contract_row("OR-140", test_owner_row_id="OR-001")
    with pytest.raises(SchemaError, match="owner row OR-140 positive_test_identity"):
        verify_materialization_document(SCHEMA_ROOT, "ars://portfolio/w11-schema-catalogue-content", swapped)

    duplicate_logical_key = deepcopy(catalogue)
    duplicate_logical_key["schema_source_rows"][1]["logical_key"] = duplicate_logical_key["schema_source_rows"][0][
        "logical_key"
    ]
    with pytest.raises(SchemaError, match="schema_source_rows logical_key values must be unique"):
        verify_materialization_document(
            SCHEMA_ROOT,
            "ars://portfolio/w11-schema-catalogue-content",
            duplicate_logical_key,
        )

    duplicate_schema_id = deepcopy(catalogue)
    duplicate_schema_id["schema_source_rows"][1]["schema_id"] = duplicate_schema_id["schema_source_rows"][0][
        "schema_id"
    ]
    duplicate_schema_id["schema_source_rows"][1]["logical_key"] = "content:programme-copy"
    with pytest.raises(SchemaError, match="schema_source_rows schema_id values must be unique"):
        verify_materialization_document(
            SCHEMA_ROOT,
            "ars://portfolio/w11-schema-catalogue-content",
            duplicate_schema_id,
        )


def test_w11_catalogue_requires_exact_schema_family_closure_and_owner_identity_uniqueness() -> None:
    catalogue = _valid_catalogue()
    incomplete = deepcopy(catalogue)
    incomplete["schema_source_rows"][-1]["logical_key"] = "bootstrap:unexpected"
    incomplete["schema_source_rows"][-1]["schema_id"] = "ars://portfolio/unexpected"
    incomplete["schema_source_rows"][-1]["repository_path"] = (
        ".research-system/schemas/contracts/w11/unexpected.schema.json"
    )
    with pytest.raises(SchemaError, match="exact accepted 61-family schema closure"):
        verify_materialization_document(SCHEMA_ROOT, "ars://portfolio/w11-schema-catalogue-content", incomplete)

    duplicate_owner_logical = deepcopy(catalogue)
    duplicate_owner_logical["owner_contract_rows"][1]["logical_key"] = duplicate_owner_logical["owner_contract_rows"][
        0
    ]["logical_key"]
    with pytest.raises(SchemaError, match="owner_contract_rows logical_key values must be unique"):
        verify_materialization_document(
            SCHEMA_ROOT,
            "ars://portfolio/w11-schema-catalogue-content",
            duplicate_owner_logical,
        )

    duplicate_owner_schema = deepcopy(catalogue)
    duplicate_owner_schema["owner_contract_rows"][1]["schema_id"] = duplicate_owner_schema["owner_contract_rows"][0][
        "schema_id"
    ]
    with pytest.raises(SchemaError, match="owner_contract_rows schema_id values must be unique"):
        verify_materialization_document(
            SCHEMA_ROOT,
            "ars://portfolio/w11-schema-catalogue-content",
            duplicate_owner_schema,
        )


def test_w11_scorecard_resolves_the_frozen_rubric_at_inert_verifier_admission() -> None:
    verify_materialization_document(
        SCHEMA_ROOT,
        "ars://portfolio/assay-scorecard",
        VALID_SCORECARD,
        reference_documents=[VALID_RUBRIC],
    )

    unresolved = deepcopy(VALID_SCORECARD)
    with pytest.raises(SchemaError, match="rubric_ref could not be resolved"):
        verify_materialization_document(SCHEMA_ROOT, "ars://portfolio/assay-scorecard", unresolved)

    malformed_rubric = deepcopy(VALID_RUBRIC)
    malformed_rubric.pop("axis_definitions")
    with pytest.raises(SchemaError, match="reference documents require validate_reference"):
        w11_verifier.verify_w11_document(
            "ars://portfolio/assay-scorecard",
            VALID_SCORECARD,
            reference_documents=[malformed_rubric],
            validate_reference=None,
        )

    unknown_axis = deepcopy(VALID_SCORECARD)
    unknown_axis["axis_results"][0]["axis_id"] = "unknown"
    with pytest.raises(SchemaError, match="unknown rubric axis"):
        verify_materialization_document(
            SCHEMA_ROOT,
            "ars://portfolio/assay-scorecard",
            unknown_axis,
            reference_documents=[VALID_RUBRIC],
        )

    kind_mismatch = deepcopy(VALID_SCORECARD)
    kind_mismatch["axis_results"][0]["axis_kind"] = "integer_score"
    kind_mismatch["axis_results"][0]["value"] = 1
    with pytest.raises(SchemaError, match="axis kind mismatch"):
        verify_materialization_document(
            SCHEMA_ROOT,
            "ars://portfolio/assay-scorecard",
            kind_mismatch,
            reference_documents=[VALID_RUBRIC],
        )

    integer_rubric = deepcopy(VALID_RUBRIC)
    integer_axis = integer_rubric["axis_definitions"][0]
    integer_axis["axis_kind"] = "integer_score"
    integer_axis["value_schema"] = "integer"
    integer_axis["value_type"] = "integer"
    integer_axis.pop("allowed_set")
    integer_axis["bounds"] = {"minimum": 0, "maximum": 3}
    integer_scorecard = deepcopy(VALID_SCORECARD)
    integer_scorecard["axis_results"][0]["axis_kind"] = "integer_score"
    integer_scorecard["axis_results"][0]["value"] = 2
    verify_materialization_document(
        SCHEMA_ROOT,
        "ars://portfolio/assay-scorecard",
        integer_scorecard,
        reference_documents=[integer_rubric],
    )

    out_of_domain = deepcopy(integer_scorecard)
    out_of_domain["axis_results"][0]["value"] = 99
    with pytest.raises(SchemaError, match="outside the frozen rubric domain"):
        verify_materialization_document(
            SCHEMA_ROOT,
            "ars://portfolio/assay-scorecard",
            out_of_domain,
            reference_documents=[integer_rubric],
        )

    optional_rubric = deepcopy(VALID_RUBRIC)
    optional_rubric["axis_definitions"].append(_axis_definition("integer_score", "integer", "bounds"))
    optional_rubric["axis_definitions"][-1]["axis_id"] = "sensitivity"
    with pytest.raises(SchemaError, match="axis set mismatch"):
        verify_materialization_document(
            SCHEMA_ROOT,
            "ars://portfolio/assay-scorecard",
            VALID_SCORECARD,
            reference_documents=[optional_rubric],
        )


def test_w11_scorecard_matching_malformed_rubric_with_noop_callback_is_controlled() -> None:
    malformed_rubric = deepcopy(VALID_RUBRIC)
    malformed_rubric.pop("axis_definitions")
    with pytest.raises(SchemaError, match="axis_definitions"):
        w11_verifier.verify_w11_document(
            "ars://portfolio/assay-scorecard",
            VALID_SCORECARD,
            reference_documents=[malformed_rubric],
            validate_reference=lambda _schema_id, _reference: None,
        )


def test_w11_dossier_expected_set_recomputes_all_cross_field_identity() -> None:
    dossier = deepcopy(VALID_DOSSIER_EXPECTED_SET)
    verify_materialization_document(SCHEMA_ROOT, "ars://portfolio/dossier-expected-set-content", dossier)

    for field in (
        "component_count",
        "source_count",
        "object_count",
        "scope_count",
        "edge_count",
        "relationship_count",
    ):
        mutated = deepcopy(dossier)
        mutated[field] += 1
        with pytest.raises(SchemaError, match=f"{field} does not match"):
            verify_materialization_document(SCHEMA_ROOT, "ars://portfolio/dossier-expected-set-content", mutated)

    for field in (
        "component_multiset_hash",
        "source_multiset_hash",
        "object_multiset_hash",
        "scope_multiset_hash",
        "edge_multiset_hash",
        "relationship_multiset_hash",
        "expected_set_closure_hash",
    ):
        mutated = deepcopy(dossier)
        mutated[field] = "f" * 64
        with pytest.raises(SchemaError, match=f"{field} does not match"):
            verify_materialization_document(SCHEMA_ROOT, "ars://portfolio/dossier-expected-set-content", mutated)

    row_mutation = deepcopy(dossier)
    row_mutation["components"][0]["component_kind"] = "different-kind"
    with pytest.raises(SchemaError, match="component_multiset_hash does not match"):
        verify_materialization_document(SCHEMA_ROOT, "ars://portfolio/dossier-expected-set-content", row_mutation)


def test_w11_dossier_rejects_a_coordinated_duplicate_after_recomputing_all_hashes() -> None:
    duplicated = deepcopy(VALID_DOSSIER_EXPECTED_SET)
    duplicated["components"].append(deepcopy(duplicated["components"][0]))
    duplicated["component_count"] = len(duplicated["components"])
    duplicated["component_multiset_hash"] = _test_multiset_hash(duplicated["components"])
    duplicated["expected_set_closure_hash"] = _test_hash(
        {
            "manifest_schema_id": duplicated["schema_id"],
            "manifest_schema_version": duplicated["schema_version"],
            "package_version": duplicated["package_version"],
            "admission_profile_hash": duplicated["admission_profile_ref"]["content_hash"],
            "components": sorted(duplicated["components"], key=_test_canonical_bytes),
            "source_dependencies": sorted(duplicated["sources"], key=_test_canonical_bytes),
            "objects": sorted(duplicated["objects"], key=_test_canonical_bytes),
            "scope_definitions": sorted(duplicated["scope_definitions"], key=_test_canonical_bytes),
            "dependency_edges": sorted(duplicated["dependency_edges"], key=_test_canonical_bytes),
            "relationships": sorted(duplicated["relationships"], key=_test_canonical_bytes),
        }
    )

    with pytest.raises(SchemaError, match="components contains duplicate component_key"):
        verify_materialization_document(SCHEMA_ROOT, "ars://portfolio/dossier-expected-set-content", duplicated)


def test_w11_representative_mutations_are_rejected() -> None:
    mutations = [
        ("ars://portfolio/programme", VALID_PROGRAMME, "title", 7),
        ("ars://portfolio/programme", VALID_PROGRAMME, "unexpected", True),
        ("ars://portfolio/relation/discovery-promotion", VALID_DISCOVERY_PROMOTION, "selected_option", "MAYBE"),
        ("ars://portfolio/relation/discovery-promotion", VALID_DISCOVERY_PROMOTION, "relation_kind", "other_decision"),
    ]
    for schema_id, original, field, value in mutations:
        mutated = deepcopy(original)
        mutated[field] = value
        with pytest.raises(SchemaError):
            verify_materialization_document(SCHEMA_ROOT, schema_id, mutated)


def _git_bytes(revision: str, path: str) -> bytes:
    try:
        return subprocess.run(
            ["git", "cat-file", "-p", f"{revision}:{path}"],
            cwd=REPO_ROOT,
            check=True,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="replace").strip()
        pytest.fail(f"full-history W11 identity lookup failed for {revision}:{path}: {detail}")


def _git_blob(repo_root: Path, revision: str, path: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", f"{revision}:{path}"],
        cwd=repo_root,
        check=True,
        shell=False,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


def _git_tree(repo_root: Path, revision: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", f"{revision}^{{tree}}"],
        cwd=repo_root,
        check=True,
        shell=False,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


@pytest.fixture
def synthetic_w11_dag(tmp_path: Path) -> dict[str, Any]:
    repo_root = tmp_path / "synthetic-w11-repo"
    repo_root.mkdir()
    _git_test(repo_root, "init", "--quiet")
    _git_test(repo_root, "config", "user.email", "w11-tests@example.invalid")
    _git_test(repo_root, "config", "user.name", "W11 tests")

    (repo_root / "base.txt").write_text("base\n", encoding="utf-8")
    _git_test(repo_root, "add", "base.txt")
    _git_test(repo_root, "commit", "--quiet", "--no-gpg-sign", "-m", "synthetic base")
    base = _git_test(repo_root, "rev-parse", "HEAD")

    (repo_root / "subject.txt").write_text("descendant\n", encoding="utf-8")
    (repo_root / "subject-meta.txt").write_text("descendant metadata\n", encoding="utf-8")
    _git_test(repo_root, "add", "subject.txt", "subject-meta.txt")
    _git_test(repo_root, "commit", "--quiet", "--no-gpg-sign", "-m", "synthetic descendant")
    subject = _git_test(repo_root, "rev-parse", "HEAD")

    unrelated_blob = _git_test(repo_root, "hash-object", "-w", "--stdin", input_text="unrelated\n")
    index_env = os.environ.copy()
    index_env["GIT_INDEX_FILE"] = str(tmp_path / "synthetic-unrelated-index")
    _git_test(repo_root, "read-tree", f"{base}^{{tree}}", env=index_env)
    _git_test(
        repo_root, "update-index", "--add", "--cacheinfo", f"100644,{unrelated_blob},unrelated.txt", env=index_env
    )
    unrelated_tree = _git_test(repo_root, "write-tree", env=index_env)
    unrelated = _git_test(repo_root, "commit-tree", unrelated_tree, "-m", "synthetic unrelated root", env=index_env)
    return {"repo": repo_root, "base": base, "subject": subject, "unrelated": unrelated}


def _git_test(repo_root: Path, *args: str, input_text: str | None = None, env: dict[str, str] | None = None) -> str:
    isolated_env = os.environ.copy()
    if env is not None:
        isolated_env.update(env)
    for key in tuple(isolated_env):
        if key == "GIT_CONFIG_COUNT" or key.startswith("GIT_CONFIG_KEY_") or key.startswith("GIT_CONFIG_VALUE_"):
            isolated_env.pop(key, None)
    isolated_env["GIT_CONFIG_GLOBAL"] = str(repo_root / ".missing-global-config")
    isolated_env["GIT_CONFIG_SYSTEM"] = str(repo_root / ".missing-system-config")
    isolated_env["GIT_CONFIG_NOSYSTEM"] = "1"
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        env=isolated_env,
        shell=False,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def _subject_envelope(repo_root: Path, base_commit: str, subject_commit: str) -> dict[str, Any]:
    paths = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", base_commit, subject_commit],
        cwd=repo_root,
        check=True,
        shell=False,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.splitlines()
    return {
        "base_commit": base_commit,
        "subject_commit": subject_commit,
        "subject_tree": _git_tree(repo_root, subject_commit),
        "changed_paths": [{"path": path, "blob": _git_blob(repo_root, subject_commit, path)} for path in paths],
    }


def test_w11_foundation_has_the_independent_closed_family_set() -> None:
    schemas = _schemas()
    assert {schema["$id"] for _, schema in schemas} == EXPECTED_IDS
    assert len({path.as_posix() for path, _ in schemas}) == len(schemas)
    assert len({schema["$id"] for _, schema in schemas}) == len(schemas)
    assert not (REPO_ROOT / ".research-system" / "evals" / "expected" / "w11-portfolio-discovery-v1.json").exists()


def test_every_w11_schema_is_strict_and_versioned() -> None:
    def assert_no_open_object(node: Any, location: str) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is not True, location
            for key, value in node.items():
                assert_no_open_object(value, f"{location}/{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                assert_no_open_object(value, f"{location}[{index}]")

    for path, schema in _schemas():
        Draft202012Validator.check_schema(schema)
        assert_no_open_object(schema, path.as_posix())
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"].startswith("ars://portfolio/")
        if schema["$id"] != "ars://portfolio/w11-common-definitions":
            assert schema["properties"]["schema_id"]["const"] == schema["$id"]
            assert schema["properties"]["schema_version"]["const"] == "1.0.0"
            assert schema["additionalProperties"] is False or schema.get("unevaluatedProperties") is False
        assert path.suffixes[-2:] == [".schema", ".json"]


def test_w11_content_schemas_forbid_self_attestation_and_runtime_state() -> None:
    forbidden = {
        "repository_path",
        "git_commit",
        "git_blob",
        "file_length",
        "file_sha256",
        "serialized_byte_length",
        "serialized_sha256",
        "file_observation_id",
        "review_id",
        "review_verdict",
        "acceptance_id",
        "accepted_by",
        "accepted_at",
        "acceptance_event_id",
        "runtime_registry_id",
        "genesis_import_id",
        "lifecycle_state",
        "status",
        "current",
        "reviewed",
        "accepted",
    }
    for path, schema in _schemas():
        if schema["$id"] not in CONTENT_SCHEMA_IDS:
            continue
        properties = set(schema.get("properties", {}))
        assert not (properties & forbidden), f"{path}: {properties & forbidden}"
        assert "content_hash" in properties
        assert "catalogue_content_hash" not in properties


@pytest.mark.integration
def test_raw_w11_identity_uses_the_explicit_git_namespace() -> None:
    raw = _git_bytes(W11_COMMIT, W11_PATH)
    assert hashlib.sha256(raw).hexdigest() == W11_SHA256
    assert len(raw) == W11_BYTES
    assert b"\r" not in raw
    assert raw.decode("utf-8")
    assert (
        subprocess.run(
            ["git", "rev-parse", f"{W11_COMMIT}:{W11_PATH}"],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        == W11_BLOB
    )


def test_w11_ids_are_not_runtime_activated() -> None:
    active_ids = {binding.schema_id for binding in _RUNTIME_BINDINGS}
    assert not (EXPECTED_IDS & active_ids)
    assert not any(schema_id.startswith("ars://portfolio/") for schema_id in active_ids)

    runtime = bundled_runtime_schema_registry()
    assert not runtime.is_active("ars://portfolio/programme", "1.0.0")
    with pytest.raises(SchemaError, match="inactive schema"):
        runtime.validate_active(
            "ars://portfolio/programme",
            VALID_PROGRAMME,
            schema_version="1.0.0",
        )

    core_command = {
        "command_id": "cmd_01978abc-0001-7000-8000-000000000001",
        "command_type": "CreateTask",
        "schema_id": "ars://core/command",
        "schema_version": "1.0.0",
        "submitted_at": "2026-07-01T12:00:00Z",
        "actor_id": "act_01978abc-0002-7000-8000-000000000002",
        "on_behalf_of_actor_id": None,
        "authority_grant_id": "agr_01978abc-0003-7000-8000-000000000003",
        "target_stream_id": "tsk_01978abc-0004-7000-8000-000000000004",
        "expected_stream_version": 0,
        "idempotency_key": "create-task-1",
        "correlation_id": "synthetic-workflow-1",
        "causation_id": None,
        "reason": "synthetic P0 test",
        "evidence_refs": [],
        "payload": {},
    }
    runtime.validate("ars://core/command", core_command)
    core_command["command_id"] = "cmd_not-a-uuid"
    with pytest.raises(SchemaError, match="command_id"):
        runtime.validate("ars://core/command", core_command)


def test_w11_schemas_load_through_the_registry_without_activation() -> None:
    runtime = bundled_runtime_schema_registry()
    assert runtime.resolve_identity("ars://portfolio/programme", "1.0.0").schema_id == "ars://portfolio/programme"


def test_w11_verifier_rejects_nested_late_schema_files(tmp_path: Path) -> None:
    schema_root = tmp_path / "schemas"
    schema_root.mkdir()
    (schema_root / "programme.schema.json").write_bytes((SCHEMA_ROOT / "programme.schema.json").read_bytes())
    nested = schema_root / "nested"
    nested.mkdir()
    (nested / "late.schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "ars://portfolio/nested-late",
                "type": "object",
                "additionalProperties": False,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SchemaError, match="nested schema files are not permitted"):
        verify_materialization_document(schema_root, "ars://portfolio/programme", VALID_PROGRAMME)


def test_w11_verifier_observes_a_same_root_late_schema(tmp_path: Path) -> None:
    schema_root = tmp_path / "schemas"
    schema_root.mkdir()
    (schema_root / "programme.schema.json").write_bytes((SCHEMA_ROOT / "programme.schema.json").read_bytes())
    verify_materialization_document(schema_root, "ars://portfolio/programme", VALID_PROGRAMME)

    (schema_root / "late.schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "ars://portfolio/late",
                "type": "object",
                "required": ["schema_id", "schema_version"],
                "properties": {
                    "schema_id": {"const": "ars://portfolio/late"},
                    "schema_version": {"const": "1.0.0"},
                },
                "additionalProperties": False,
            }
        ),
        encoding="utf-8",
    )
    verify_materialization_document(
        schema_root,
        "ars://portfolio/late",
        {"schema_id": "ars://portfolio/late", "schema_version": "1.0.0"},
    )


def test_w11_verifier_observes_a_same_root_schema_replacement(tmp_path: Path) -> None:
    schema_root = tmp_path / "schemas"
    schema_root.mkdir()
    programme_schema_path = schema_root / "programme.schema.json"
    programme_schema_path.write_bytes((SCHEMA_ROOT / "programme.schema.json").read_bytes())
    verify_materialization_document(schema_root, "ars://portfolio/programme", VALID_PROGRAMME)

    replacement = json.loads(programme_schema_path.read_text(encoding="utf-8"))
    replacement["required"].append("late_marker")
    programme_schema_path.write_text(json.dumps(replacement), encoding="utf-8")
    with pytest.raises(SchemaError, match="late_marker"):
        verify_materialization_document(schema_root, "ars://portfolio/programme", VALID_PROGRAMME)


def test_bootstrap_contract_is_inert_and_binds_the_accepted_w11_tuple() -> None:
    contract = yaml.safe_load(BOOTSTRAP_CONTRACT.read_text(encoding="utf-8"))
    _validate(_schema_by_id("ars://portfolio/w11-materialization-bootstrap-contract"), contract)
    assert contract["schema_id"] == "ars://portfolio/w11-materialization-bootstrap-contract"
    assert contract["schema_version"] == "1.0.0"
    assert contract["source_spec"] == {
        "repository_path": W11_PATH,
        "reviewed_commit": W11_COMMIT,
        "git_blob": W11_BLOB,
        "raw_sha256": W11_SHA256,
        "raw_bytes": W11_BYTES,
    }
    assert contract["materialization_status"] == "inert_foundation_only"
    assert contract["runtime_activation"] == "forbidden"
    assert contract["expected_catalogue"] == "forbidden_in_pr1"
    assert contract["bootstrap_verifier"]["interface"] == "tools.verify_w11_materialization:verify_subject_envelope"
    assert contract["bootstrap_verifier"]["subject_envelope"] == {
        "authority": "caller_supplied_external",
        "required_fields": ["base_commit", "subject_commit", "subject_tree", "changed_paths"],
        "path_entry_fields": ["path", "blob"],
        "exact_path_set": "git_diff_base_to_subject",
        "no_implicit_working_copy_or_symbolic_ref": True,
    }
    assert contract["acceptance_instance"] == "forbidden_in_pr1"
    assert contract["verification_rules"] == [
        "accepted W11 raw-byte tuple is independently observed",
        "every materialized schema is Draft 2020-12 valid and closed",
        "W11 IDs remain absent from runtime bindings",
        "no expected catalogue or acceptance instance is materialized",
        "no runtime production Python is changed",
        "the non-runtime verifier requires the caller-supplied external subject envelope",
        "the envelope names the exact base, subject commit, subject tree, changed paths, and per-path blobs",
    ]
    for family, expected in (
        ("content", CONTENT_KINDS),
        ("relation", RELATION_KINDS),
        ("artefact", ARTEFACT_KINDS),
        ("bootstrap", BOOTSTRAP_KINDS),
    ):
        assert len(contract["families"][family]) == len(expected)
        assert len(contract["families"][family]) == len(set(contract["families"][family]))
        assert set(contract["families"][family]) == set(expected)

    schema = _schema_by_id("ars://portfolio/w11-materialization-bootstrap-contract")
    duplicate_family = deepcopy(contract)
    duplicate_family["families"]["content"].append(duplicate_family["families"]["content"][0])
    assert not Draft202012Validator(schema).is_valid(duplicate_family)
    duplicate_rule = deepcopy(contract)
    duplicate_rule["verification_rules"].append(duplicate_rule["verification_rules"][0])
    assert not Draft202012Validator(schema).is_valid(duplicate_rule)
