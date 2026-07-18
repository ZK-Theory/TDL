from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Callable

import pytest
import yaml

from research_system.errors import SchemaError
from research_system.schema_registry import SchemaRegistry


SCHEMA_ROOT = Path(".research-system/schemas")
CONTRACT_ROOT = Path(".research-system/contracts")
PROTOCOL_PATH = CONTRACT_ROOT / "wp6-2-live-grader-calibration-protocol.yaml"
IDENTITY_MANIFEST_PATH = CONTRACT_ROOT / "wp6-2-live-grader-calibration-protocol-identity-manifest.yaml"
PROTOCOL_SCHEMA_PATH = SCHEMA_ROOT / "contracts" / "wp6-2-live-grader-calibration-protocol.schema.json"
IDENTITY_MANIFEST_SCHEMA_PATH = (
    SCHEMA_ROOT / "contracts" / "wp6-2-live-grader-calibration-protocol-identity-manifest.schema.json"
)
APPROVED_PLAN_REVISION = "fe5f1d40bc8f05f061317c677b5891cea0711249"
BASE_REVISION = "4e6fd0cb26c04ff9707c3183f663461d752b53b9"
ANNEX_PATH = "docs/plans/agentic-research-system/implementation/" "06e-wp6-2-live-replacement-map.md"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _canonical_json_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _git_output(*args: str, text: bool = True) -> str | bytes:
    return subprocess.check_output(["git", *args], text=text)


def _protocol() -> dict:
    return _load_yaml(PROTOCOL_PATH)


def _validate_protocol(value: dict) -> None:
    SchemaRegistry(SCHEMA_ROOT).validate(
        "ars://contracts/wp6-2-live-grader-calibration-protocol",
        value,
    )


def _without(value: dict, *keys: str) -> dict:
    return {key: item for key, item in value.items() if key not in keys}


def _parse_approved_06e_rows() -> list[tuple[str, ...]]:
    raw = _git_output("show", f"{APPROVED_PLAN_REVISION}:{ANNEX_PATH}")
    row_pattern = re.compile(
        r"^\|\s*(\d+)\s*\|\s*\x60\((.*?)\)\x60\s*\|\s*\x60\((.*?)\)\x60\s*\|",
        re.MULTILINE,
    )
    rows: list[tuple[str, ...]] = []
    for match in row_pattern.finditer(raw):
        predecessor = tuple(part.strip() for part in match.group(2).split(","))
        successor = tuple(part.strip() for part in match.group(3).split(","))
        assert len(predecessor) == 6
        assert len(successor) == 6
        rows.append((*predecessor, successor[5]))
    assert len(rows) == 51
    return rows


def _binding_tuple(binding: dict) -> tuple[str, ...]:
    return (
        binding["fixture_id"],
        binding["fixture_revision"],
        binding["grader_id"],
        binding["grader_class"],
        binding["grader_version"],
        binding["source_variant_id"],
        binding["prospective_live_variant_id"],
    )


def test_protocol_and_scoped_identity_manifest_are_strict_content_addressed_contracts() -> None:
    registry = SchemaRegistry(SCHEMA_ROOT)
    protocol = _protocol()
    manifest = _load_yaml(IDENTITY_MANIFEST_PATH)
    registry.validate(
        "ars://contracts/wp6-2-live-grader-calibration-protocol-identity-manifest",
        manifest,
    )
    _validate_protocol(protocol)

    assert manifest["scope"] == "wp6-2-t1a-live-grader-calibration-protocol-only"
    assert set(manifest) == {
        "schema_id",
        "schema_version",
        "manifest_id",
        "manifest_version",
        "scope",
        "protocol_identity",
    }
    entry = manifest["protocol_identity"]
    protocol_bytes = PROTOCOL_PATH.read_bytes()
    schema_bytes = PROTOCOL_SCHEMA_PATH.read_bytes()
    assert b"\r" not in protocol_bytes
    assert b"\r" not in schema_bytes
    assert hashlib.sha256(protocol_bytes).hexdigest() == entry["canonical_sha256"]
    assert _git_blob_sha1(protocol_bytes) == entry["git_blob_sha1"]
    assert hashlib.sha256(schema_bytes).hexdigest() == entry["schema_canonical_sha256"]
    assert _git_blob_sha1(schema_bytes) == entry["schema_git_blob_sha1"]
    assert entry["status"] == "preregistered_pending_independent_review_and_stephen_acceptance"


@pytest.mark.parametrize(
    "schema_path",
    [PROTOCOL_SCHEMA_PATH, IDENTITY_MANIFEST_SCHEMA_PATH],
)
def test_contract_schemas_have_no_defaults_and_close_every_object(schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    def walk(value: object) -> None:
        if isinstance(value, dict):
            assert "default" not in value
            if value.get("type") == "object":
                assert value.get("additionalProperties") is False
                assert set(value["required"]) == set(value["properties"])
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(schema)


def test_expected_sets_bind_exact_approved_06e_model_and_human_rows() -> None:
    protocol = _protocol()
    approved = _parse_approved_06e_rows()
    expected_model = {row for row in approved if row[3] == "M"}
    expected_human = {row for row in approved if row[3] == "H"}
    actual_model = {_binding_tuple(binding) for binding in protocol["target_expected_sets"]["model"]["bindings"]}
    actual_human = {_binding_tuple(binding) for binding in protocol["target_expected_sets"]["human"]["bindings"]}

    assert len(expected_model) == len(actual_model) == 31
    assert len(expected_human) == len(actual_human) == 20
    assert actual_model == expected_model
    assert actual_human == expected_human
    assert actual_model.isdisjoint(actual_human)

    for class_name in ("model", "human"):
        expected_set = protocol["target_expected_sets"][class_name]
        assert _canonical_json_sha256(expected_set["bindings"]) == expected_set["expected_set_sha256"]
        for binding in expected_set["bindings"]:
            descriptor = _without(binding, "binding_sha256", "obligation_id")
            assert _canonical_json_sha256(descriptor) == binding["binding_sha256"]


def test_corpus_and_case_hashes_bind_the_accepted_immutable_fixture_tree() -> None:
    protocol = _protocol()
    corpus = protocol["corpus"]
    assert (
        _git_output(
            "rev-parse",
            f"{BASE_REVISION}:.research-system/evals/fixtures",
        ).strip()
        == corpus["vintage"]["accepted_gate5_fixture_tree_git_sha1"]
    )
    assert _canonical_json_sha256(corpus["fixture_packages"]) == corpus["corpus_manifest_sha256"]

    package_ids: set[str] = set()
    for package in corpus["fixture_packages"]:
        package_ids.add(package["fixture_id"])
        assert (
            _git_output(
                "rev-parse",
                f"{BASE_REVISION}:{package['package_path']}",
            ).strip()
            == package["package_tree_git_sha1"]
        )
        fixture_path = f"{package['package_path']}/fixture.yaml"
        assert (
            _git_output(
                "rev-parse",
                f"{BASE_REVISION}:{fixture_path}",
            ).strip()
            == package["fixture_yaml_git_blob_sha1"]
        )
        fixture = yaml.safe_load(_git_output("show", f"{BASE_REVISION}:{fixture_path}"))
        assert fixture["fixture_revision"] == package["fixture_revision"]
        assert fixture["source_manifest_hash"] == package["source_manifest_sha256"]
        assert fixture["stimulus_hash"] == package["stimulus_sha256"]
        assert fixture["known_bad_reference_hash"] == package["known_bad_reference_sha256"]
        assert fixture["known_good_reference_hash"] == package["known_good_reference_sha256"]
        assert fixture["mutation_ids"] == package["mutation_ids"]
        assert fixture["safe_variation_ids"] == package["safe_variation_ids"]

    for class_name, expected_count in (("model", 39), ("human", 28)):
        expected_set = protocol["calibration_expected_sets"][class_name]
        assert len(expected_set["cases"]) == expected_count
        assert _canonical_json_sha256(expected_set["cases"]) == expected_set["expected_set_sha256"]
        for case in expected_set["cases"]:
            assert case["fixture_id"] in package_ids
            assert _canonical_json_sha256(_without(case, "case_sha256")) == case["case_sha256"]
            if case["case_kind"] in {"negative", "producer_correlated"}:
                assert case["expected_decision"] == "reject"
            elif case["case_kind"] in {"positive", "safe_variation"}:
                assert case["expected_decision"] == "accept"
            else:
                assert case["case_kind"] == "ambiguous"
                assert case["expected_decision"] == "adjudication_required"


def test_human_rubric_and_prospective_bounds_are_internally_bound() -> None:
    protocol = _protocol()
    rubric = protocol["human_rubric"]
    assert _canonical_json_sha256(_without(rubric, "rubric_sha256")) == rubric["rubric_sha256"]
    assert rubric["minimum_blinded_graders"] == 2
    assert rubric["permitted_human_authority_class"] == (
        "stephen_attributed_or_explicitly_delegated_i2_human_assurance_authority"
    )

    criteria = protocol["prospective_acceptance_criteria"]
    assert criteria["criterion_label"] == ("prospective_preregistered_acceptance_criteria_not_observed_calibration")
    for class_name, denominator in (("model", 11), ("human", 8)):
        upper_at_zero = 1 - (0.05 ** (1 / denominator))
        class_criteria = criteria[class_name]
        assert class_criteria["false_pass_count_max"] == 0
        assert class_criteria["false_block_count_max"] == 0
        assert upper_at_zero <= class_criteria["false_pass_upper_bound_max"]
        assert upper_at_zero <= class_criteria["false_block_upper_bound_max"]
        assert class_criteria["bound_label"] == "prospective_preregistered_bound"


def test_future_evidence_and_assurance_dispositions_are_complete() -> None:
    protocol = _protocol()
    future = protocol["future_result_and_evidence_fields"]
    assert {
        "protocol_sha256",
        "corpus_manifest_sha256",
        "case_sha256",
        "repetition_id",
        "producer_family",
        "grader_family",
        "independent_review_sha256",
        "currentness_status",
        "suspension_status",
    } <= set(future["common_required"])
    assert {
        "provider_command_sha256",
        "provider_receipt_sha256",
        "cost_grant_sha256",
        "execution_lease_sha256",
        "false_pass_summary",
        "false_block_summary",
        "uncertainty_result",
    } <= set(future["model_required"])
    assert {
        "rubric_sha256",
        "human_authority_class",
        "blinding_record_sha256",
        "disagreement_record_sha256",
        "adjudication_record_sha256",
        "rubric_revision_status",
    } <= set(future["human_required"])

    lanes = protocol["research_assurance_requirements"]["assurance_lanes_touched"]
    assert lanes == {
        "stochastic_null": "required",
        "statistical_panel": "required",
        "output_provenance": "required_primary",
        "topology": "not_applicable_no_topological_object_or_claim",
        "representation": "not_applicable_no_representation_fit_transform_or_claim",
        "paper_claim": "not_applicable_no_research_claim",
    }
    assert protocol["claim_status"] == "no_observed_calibration_claim"
    assert protocol["independence"]["self_attested_evidence_permitted"] is False
    assert protocol["independence"]["observed_side_may_define_or_amend_expected_sets"] is False


Mutation = Callable[[dict], None]


def _missing_required(value: dict) -> None:
    value.pop("protocol_version")


def _wrong_type(value: dict) -> None:
    value["repetition_and_randomness"]["repeat_count"] = "2"


def _extra_field(value: dict) -> None:
    value["corpus"]["unregistered_default"] = "forbidden"


def _model_human_target_cross_compensation(value: dict) -> None:
    value["target_expected_sets"]["model"]["bindings"][0] = deepcopy(
        value["target_expected_sets"]["human"]["bindings"][0]
    )


def _model_human_case_cross_compensation(value: dict) -> None:
    value["calibration_expected_sets"]["model"]["cases"][0] = deepcopy(
        value["calibration_expected_sets"]["human"]["cases"][0]
    )


def _correlated_producer_reviewer(value: dict) -> None:
    value["independence"]["model"]["producer_grader_family_relation"] = "same_family"


def _stale_corpus(value: dict) -> None:
    value["corpus"]["vintage"]["accepted_gate5_fixture_tree_git_sha1"] = "0" * 40


def _stale_rubric(value: dict) -> None:
    value["human_rubric"]["rubric_version"] = "0.9.0"


def _omitted_case(value: dict) -> None:
    value["calibration_expected_sets"]["model"]["cases"].pop()


def _omitted_repeat(value: dict) -> None:
    value["repetition_and_randomness"]["repetition_ids"].pop()


def _altered_denominator(value: dict) -> None:
    value["estimands_and_uncertainty"]["human_fixture_cluster_denominator"] = 20


def _altered_estimand(value: dict) -> None:
    value["estimands_and_uncertainty"]["estimand"] = "per_repetition_unclustered_error_rate"


def _altered_bound(value: dict) -> None:
    value["prospective_acceptance_criteria"]["human"]["false_pass_upper_bound_max"] = 0.5


def _self_attested_evidence(value: dict) -> None:
    value["independence"]["self_attested_evidence_permitted"] = True


@pytest.mark.parametrize(
    "mutation",
    [
        _missing_required,
        _wrong_type,
        _extra_field,
        _model_human_target_cross_compensation,
        _model_human_case_cross_compensation,
        _correlated_producer_reviewer,
        _stale_corpus,
        _stale_rubric,
        _omitted_case,
        _omitted_repeat,
        _altered_denominator,
        _altered_estimand,
        _altered_bound,
        _self_attested_evidence,
    ],
    ids=lambda mutation: mutation.__name__.removeprefix("_"),
)
def test_public_schema_seam_rejects_protocol_bypasses(mutation: Mutation) -> None:
    candidate = deepcopy(_protocol())
    mutation(candidate)
    with pytest.raises(SchemaError):
        _validate_protocol(candidate)
