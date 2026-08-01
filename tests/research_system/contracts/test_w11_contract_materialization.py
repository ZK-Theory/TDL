"""Independent static controls for the bounded W11 contract foundation.

This test deliberately owns the expected family/path set.  It does not read a
catalogue, enumerate a registry, or generate an expected side from the files
under test.  The suite is for inert Stage-B materialization only: it does not
activate W11 runtime bindings or create the future expected catalogue.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from research_system.schema_registry import SchemaRegistry, _RUNTIME_BINDINGS


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
W11_PARENT = "c84eb2aaf0890d36d3735d08a14169f4c50935cd"
W11_SUBJECT = "04223674acdb82ee00d1410e960414d624c326b1"

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


def _schemas() -> list[tuple[Path, dict[str, Any]]]:
    return [(path, json.loads(path.read_text(encoding="utf-8"))) for path in sorted(SCHEMA_ROOT.glob("*.schema.json"))]


def _validate(schema: dict[str, Any], value: dict[str, Any]) -> None:
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        pytest.fail("; ".join(error.message for error in errors))
    if schema["$id"] in CONTENT_SCHEMA_IDS:
        _validate_w11_content_semantics(schema["$id"], value)


def _schema_by_id(schema_id: str) -> dict[str, Any]:
    return next(schema for _, schema in _schemas() if schema["$id"] == schema_id)


def _validate_w11_content_semantics(schema_id: str, value: dict[str, Any]) -> None:
    """Inert Stage-B semantic seam; no W11 runtime path imports this helper."""
    if schema_id not in CONTENT_SCHEMA_IDS:
        raise ValueError(f"not a W11 content schema: {schema_id}")

    revision = value.get("record_revision")
    predecessor = value.get("supersedes_revision")
    if revision == 1 and predecessor is not None:
        raise ValueError("revision 1 must have a null predecessor")
    if isinstance(revision, int) and not isinstance(revision, bool) and revision > 1:
        if predecessor != revision - 1:
            raise ValueError("later revisions must name the exact predecessor")

    for source_ref in value.get("source_refs", []):
        ref_kind = source_ref.get("ref_kind")
        fields = set(source_ref)
        if ref_kind in {"record", "artefact"}:
            expected = {"ref_kind", "id", "record_revision", "content_hash"}
            if fields != expected:
                raise ValueError("record and artefact references require id, record_revision, and content_hash only")
        elif ref_kind == "external":
            expected = {"ref_kind", "locator", "content_hash"}
            if fields != expected:
                raise ValueError("external references require locator and content_hash only")
        else:
            raise ValueError(f"unknown source reference kind: {ref_kind}")


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


def _owner_contract_row(owner_row_id: str) -> dict[str, Any]:
    return {
        "owner_row_id": owner_row_id,
        "logical_key": "owner-row",
        "schema_id": "ars://portfolio/test",
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
        "positive_test_identity": "W11-T01-OR-001",
        "negative_mutation_test_identity": "W11-T03-OR-001-owner-row-mutation",
        "retry_test_identity": "W11-T11-OR-001",
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


def test_representative_valid_examples_cover_content_relation_and_artifact() -> None:
    _validate(_schema_by_id("ars://portfolio/programme"), VALID_PROGRAMME)
    _validate(_schema_by_id("ars://portfolio/relation/discovery-promotion"), VALID_DISCOVERY_PROMOTION)
    _validate(_schema_by_id("ars://portfolio/assay-scorecard"), VALID_SCORECARD)


def test_owner_row_ids_are_exactly_the_two_w11_ranges() -> None:
    schema = _schema_by_id("ars://portfolio/w11-schema-catalogue-content")
    for owner_row_id in ("OR-001", "OR-040", "OR-041", "OR-101", "OR-140"):
        assert _fragment_is_valid(schema, "ownerContractRow", _owner_contract_row(owner_row_id))
    for owner_row_id in ("OR-000", "OR-042", "OR-100", "OR-141", "OR-01", "OR-1041"):
        assert not _fragment_is_valid(schema, "ownerContractRow", _owner_contract_row(owner_row_id))


def test_content_source_refs_use_only_their_ref_kind_identity() -> None:
    valid_refs = (
        {"ref_kind": "record", **_record_ref()},
        {"ref_kind": "artefact", "id": "art_1", "record_revision": 2, "content_hash": _HASH},
        {"ref_kind": "external", "locator": "https://example.invalid/source", "content_hash": _HASH},
    )
    invalid_refs = (
        {"ref_kind": "external", "locator": "https://example.invalid/source", "id": "obj_1", "content_hash": _HASH},
        {"ref_kind": "record", "locator": "https://example.invalid/source", "content_hash": _HASH},
        {"ref_kind": "artefact", "id": "art_1", "record_revision": 2, "locator": "foreign", "content_hash": _HASH},
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


def test_w11_timestamps_require_utc_rfc3339_z_with_format_checking() -> None:
    schema = _schema_by_id("ars://portfolio/programme")
    _validate(schema, VALID_PROGRAMME)
    offset_timestamp = deepcopy(VALID_PROGRAMME)
    offset_timestamp["created_at"] = "2026-01-01T01:00:00+01:00"
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    assert not validator.is_valid(offset_timestamp)


def test_w11_exact_subject_range_keeps_runtime_python_inert() -> None:
    changed_paths = subprocess.run(
        ["git", "diff", "--name-only", f"{W11_PARENT}..{W11_SUBJECT}", "--", "research_system"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.splitlines()
    assert not [path for path in changed_paths if path.endswith(".py")]


def test_w11_content_semantics_cover_every_content_schema() -> None:
    valid = {
        "record_revision": 1,
        "supersedes_revision": None,
        "source_refs": [_source_ref()],
    }
    for schema_id in sorted(CONTENT_SCHEMA_IDS):
        _validate_w11_content_semantics(schema_id, valid)

    wrong_predecessor = {**valid, "record_revision": 3, "supersedes_revision": 1}
    wrong_first_revision = {**valid, "supersedes_revision": 1}
    foreign_record_fields = {
        **valid,
        "source_refs": [
            {"ref_kind": "external", "locator": "https://example.invalid/source", "id": "obj_1", "content_hash": _HASH}
        ],
    }
    for schema_id in sorted(CONTENT_SCHEMA_IDS):
        with pytest.raises(ValueError, match="predecessor"):
            _validate_w11_content_semantics(schema_id, wrong_predecessor)
        with pytest.raises(ValueError, match="revision 1"):
            _validate_w11_content_semantics(schema_id, wrong_first_revision)
        with pytest.raises(ValueError, match="external"):
            _validate_w11_content_semantics(schema_id, foreign_record_fields)


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
        schema = _schema_by_id(schema_id)
        validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
        assert not validator.is_valid(mutated), f"mutation unexpectedly accepted: {schema_id}.{field}"


def _git_bytes(revision: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "cat-file", "-p", f"{revision}:{path}"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


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


def test_w11_schemas_load_through_the_registry_without_activation() -> None:
    registry = SchemaRegistry(SCHEMA_ROOT)
    assert registry.resolve_identity("ars://portfolio/programme", "1.0.0").schema_id == "ars://portfolio/programme"


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
    assert contract["acceptance_instance"] == "forbidden_in_pr1"
    assert set(contract["families"]["content"]) == set(CONTENT_KINDS)
    assert set(contract["families"]["relation"]) == set(RELATION_KINDS)
    assert set(contract["families"]["artefact"]) == set(ARTEFACT_KINDS)
    assert set(contract["families"]["bootstrap"]) == set(BOOTSTRAP_KINDS)
