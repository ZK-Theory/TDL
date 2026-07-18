from __future__ import annotations

import base64
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Callable

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
FUTURE_RESULT_SCHEMA_PATH = SCHEMA_ROOT / "contracts" / "wp6-2-live-grader-calibration-future-result.schema.json"
APPROVED_PLAN_REVISION = "fe5f1d40bc8f05f061317c677b5891cea0711249"
BASE_REVISION = "4e6fd0cb26c04ff9707c3183f663461d752b53b9"
REVIEW_COMMIT = "e7c30ef75750ddbddbe7761e858f1cda68d9247f"
ANNEX_PATH = "docs/plans/agentic-research-system/implementation/06e-wp6-2-live-replacement-map.md"
REVIEW_PATH = "docs/plans/agentic-research-system/reviews/adversarial-wp6-2-t1a-protocol-review-2026-07-18.md"
FIXTURE_IDS = [
    "F-005",
    "F-009",
    "F-012",
    "F-014",
    "F-020",
    "F-021",
    "F-022",
    "F-025",
    "F-026",
    "F-031",
    "F-032",
    "F-033",
    "F-035",
    "F-036",
    "S-016",
]


def _canonical_json_bytes(value: object, *, final_lf: bool = False) -> bytes:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return payload + (b"\n" if final_lf else b"")


def _canonical_json_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _git_output(*args: str, text: bool = True) -> str | bytes:
    return subprocess.check_output(["git", *args], text=text)


def _revision_bytes(revision: str, path: str) -> bytes:
    return _git_output("show", f"{revision}:{path}", text=False)


def _revision_blob(revision: str, path: str) -> str:
    return str(_git_output("rev-parse", f"{revision}:{path}")).strip()


def _revision_json(path: str) -> Any:
    return json.loads(_revision_bytes(BASE_REVISION, path))


def _revision_yaml(path: str) -> Any:
    return yaml.safe_load(_revision_bytes(BASE_REVISION, path))


def _normalize_utf8_lf(raw: bytes) -> bytes:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise AssertionError("canonical UTF-8 must not contain a BOM")
    text = raw.decode("utf-8", errors="strict")
    normalized = text.replace("\r\n", "\n")
    if "\r" in normalized:
        raise AssertionError("lone CR is not a supported checkout representation")
    return normalized.encode("utf-8")


def _canonical_file_bytes(path: Path) -> bytes:
    return _normalize_utf8_lf(path.read_bytes())


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(_canonical_file_bytes(path))


def _without(value: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key not in keys}


def _protocol() -> dict[str, Any]:
    return _load_yaml(PROTOCOL_PATH)


def _encoded_bytes(payload: bytes) -> dict[str, Any]:
    return {
        "encoding": "base64_of_utf8_canonical_json_with_single_terminal_lf",
        "bytes_base64": base64.b64encode(payload).decode("ascii"),
        "byte_length": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


@lru_cache(maxsize=1)
def _parse_approved_bindings() -> dict[str, list[dict[str, Any]]]:
    raw = str(_git_output("show", f"{APPROVED_PLAN_REVISION}:{ANNEX_PATH}"))
    row_pattern = re.compile(
        r"^\|\s*(\d+)\s*\|\s*\x60\((.*?)\)\x60\s*\|\s*\x60\((.*?)\)\x60\s*\|",
        re.MULTILINE,
    )
    expected: dict[str, list[dict[str, Any]]] = {"model": [], "human": []}
    for match in row_pattern.finditer(raw):
        row_number = int(match.group(1))
        predecessor = tuple(part.strip() for part in match.group(2).split(","))
        successor = tuple(part.strip() for part in match.group(3).split(","))
        assert len(predecessor) == len(successor) == 6
        fixture_id, revision, grader_id, grader_class, grader_version, source_variant = predecessor
        class_name = "model" if grader_class == "M" else "human" if grader_class == "H" else None
        if class_name is None:
            continue
        binding = {
            "fixture_id": fixture_id,
            "fixture_revision": revision,
            "grader_id": grader_id,
            "grader_class": grader_class,
            "grader_version": grader_version,
            "source_variant_id": source_variant,
            "prospective_live_variant_id": successor[5],
            "obligation_id": f"{grader_class}-{row_number:03d}",
        }
        binding["binding_sha256"] = _canonical_json_sha256(binding)
        expected[class_name].append(binding)
    assert len(expected["model"]) == 31
    assert len(expected["human"]) == 20
    return expected


def _case_id(class_token: str, kind_token: str, fixture_id: str, transformation_id: str) -> str:
    suffix = transformation_id.replace("_", "-").upper()
    return f"{class_token}-{kind_token}-{fixture_id}-{suffix}"


@lru_cache(maxsize=2)
def _expected_case_sources(class_name: str) -> list[dict[str, Any]]:
    class_token = "M" if class_name == "model" else "H"
    bindings = _parse_approved_bindings()[class_name]
    fixture_order = list(dict.fromkeys(binding["fixture_id"] for binding in bindings))
    cases: list[tuple[str, str, str, str]] = []
    for fixture_id in fixture_order:
        fixture = _revision_yaml(f".research-system/evals/fixtures/{fixture_id}/fixture.yaml")
        cases.extend(
            ("negative", "NEG", fixture_id, transformation_id) for transformation_id in fixture["mutation_ids"]
        )
    cases.extend(("positive", "POS", fixture_id, "known-good-post-control") for fixture_id in fixture_order)
    for fixture_id in fixture_order:
        fixture = _revision_yaml(f".research-system/evals/fixtures/{fixture_id}/fixture.yaml")
        cases.extend(
            ("safe_variation", "SAF", fixture_id, transformation_id)
            for transformation_id in fixture["safe_variation_ids"]
        )
    if "F-022" in fixture_order:
        cases.append(
            (
                "ambiguous",
                "AMB",
                "F-022",
                "withhold-reviewer-relationship-and-authority-attribution",
            )
        )
    cases.extend(
        (
            "producer_correlated",
            "PRO",
            fixture_id,
            "substitute-same-family-or-same-context-nominal-reviewer",
        )
        for fixture_id in ("F-022", "F-033", "F-035")
        if fixture_id in fixture_order
    )
    expected: list[dict[str, Any]] = []
    for case_kind, kind_token, fixture_id, transformation_id in cases:
        fixture_path = f".research-system/evals/fixtures/{fixture_id}"
        fixture = _revision_yaml(f"{fixture_path}/fixture.yaml")
        if case_kind in {"negative", "producer_correlated"}:
            role = "known_bad_pre_control"
            leaf = "expected/pre-control.json"
            decision = "reject"
        elif case_kind in {"positive", "safe_variation"}:
            role = "known_good_post_control"
            leaf = "expected/post-control.json"
            decision = "accept"
        else:
            role = "fixture_stimulus_for_ambiguous_view"
            leaf = "input/stimulus.json"
            decision = "adjudication_required"
        source_path = f"{fixture_path}/{leaf}"
        expected.append(
            {
                "case_id": _case_id(class_token, kind_token, fixture_id, transformation_id),
                "case_kind": case_kind,
                "fixture_id": fixture_id,
                "fixture_revision": fixture["fixture_revision"],
                "source_fixture_tree_git_sha1": _revision_blob(BASE_REVISION, fixture_path),
                "source_reference_sha256": hashlib.sha256(_revision_bytes(BASE_REVISION, source_path)).hexdigest(),
                "transformation_id": transformation_id,
                "expected_decision": decision,
                "blinding_rule": (
                    "initial_exact_subject_excludes_case_kind_expected_decision_oracle_and_concrete_producer_allocation"
                ),
                "grader_class": class_token,
                "source_reference_role": role,
                "source_reference_path": source_path,
                "source_reference_git_blob_sha1": _revision_blob(BASE_REVISION, source_path),
            }
        )
    return expected


def _transformation_algorithm(transformation_id: str) -> tuple[str, dict[str, Any]]:
    if transformation_id == "identifier-renaming":
        return (
            "fixture_oracle_projection_then_recursive_exact_identifier_value_substitution_v1",
            {
                "fixture_id_replacement": "CALIBRATION-FIXTURE",
                "fixture_revision_replacement": "calibration-revision",
                "key_names_changed": False,
                "ordered_steps": [
                    "project_candidate_without_oracle_labels",
                    "replace_all_exact_string_values_equal_to_fixture_id",
                    "replace_all_exact_string_values_equal_to_fixture_revision",
                    "serialize_canonical_json_utf8_with_single_terminal_lf",
                ],
            },
        )
    if transformation_id == "withhold-reviewer-relationship-and-authority-attribution":
        return (
            "stimulus_projection_with_exact_relationship_key_omission_v1",
            {
                "omitted_keys_recursively": [
                    "producer_family",
                    "reviewer_family",
                    "role_labels_differ",
                ],
                "ordered_steps": [
                    "remove_exact_omitted_keys_from_stimulus",
                    "create_withheld_relationship_candidate_output",
                    "serialize_canonical_json_utf8_with_single_terminal_lf",
                ],
            },
        )
    if transformation_id == "substitute-same-family-or-same-context-nominal-reviewer":
        return (
            "fixture_oracle_projection_with_original_relationship_evidence_v1",
            {
                "ordered_steps": [
                    "preserve_fixture_stimulus_relationship_evidence",
                    "project_candidate_without_oracle_labels",
                    "serialize_canonical_json_utf8_with_single_terminal_lf",
                ],
                "relationship_evidence_visibility": ("visible_without_expected_decision_or_oracle"),
            },
        )
    return (
        "fixture_oracle_projection_v1",
        {
            "ordered_steps": [
                "preserve_fixture_stimulus",
                "project_candidate_without_oracle_labels",
                "serialize_canonical_json_utf8_with_single_terminal_lf",
            ],
            "removed_oracle_fields": ["expected_evidence", "oracle_kind", "satisfied"],
        },
    )


@lru_cache(maxsize=1)
def _expected_transformation_specs() -> list[dict[str, Any]]:
    transformation_ids = sorted(
        {case["transformation_id"] for class_name in ("model", "human") for case in _expected_case_sources(class_name)}
    )
    specs = []
    for transformation_id in transformation_ids:
        algorithm_id, parameters = _transformation_algorithm(transformation_id)
        spec = {
            "transformation_id": transformation_id,
            "transformation_version": "1.0.0",
            "algorithm_id": algorithm_id,
            "parameters": parameters,
            "implementation_rule": (
                "language_independent_ordered_steps_are_normative_and_test_recomputed_from_immutable_fixture_json"
            ),
        }
        spec["transformation_spec_sha256"] = _canonical_json_sha256(spec)
        specs.append(spec)
    return specs


def _replace_identifier_values(value: Any, fixture_id: str, revision: str) -> Any:
    if isinstance(value, dict):
        return {key: _replace_identifier_values(item, fixture_id, revision) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_identifier_values(item, fixture_id, revision) for item in value]
    if value == fixture_id:
        return "CALIBRATION-FIXTURE"
    if value == revision:
        return "calibration-revision"
    return value


def _remove_relationship_attribution(value: Any) -> Any:
    omitted = {"producer_family", "reviewer_family", "role_labels_differ"}
    if isinstance(value, dict):
        return {key: _remove_relationship_attribution(item) for key, item in value.items() if key not in omitted}
    if isinstance(value, list):
        return [_remove_relationship_attribution(item) for item in value]
    return value


def _candidate_projection(reference: dict[str, Any]) -> dict[str, Any]:
    return {
        "assertions": [
            {
                "derived_from": assertion["derived_from"],
                "evidence": assertion["expected_evidence"],
                "property": assertion["property"],
            }
            for assertion in reference["assertions"]
        ],
        "fixture_id": reference["fixture_id"],
        "fixture_revision": reference["fixture_revision"],
        "schema_id": "ars://contracts/wp6-2-live-grader-calibration-candidate",
        "schema_version": "1.0.0",
    }


def _expected_subject(case: dict[str, Any]) -> bytes:
    fixture_path = f".research-system/evals/fixtures/{case['fixture_id']}"
    stimulus = _revision_json(f"{fixture_path}/input/stimulus.json")
    reference = _revision_json(case["source_reference_path"])
    transformation_id = case["transformation_id"]
    if transformation_id == "withhold-reviewer-relationship-and-authority-attribution":
        visible_stimulus = _remove_relationship_attribution(stimulus)
        candidate = {
            "authority_attribution": "withheld",
            "relationship_evidence": visible_stimulus["payload"]["action"],
        }
    else:
        visible_stimulus = deepcopy(stimulus)
        candidate = _candidate_projection(reference)
    if transformation_id == "identifier-renaming":
        visible_stimulus = _replace_identifier_values(
            visible_stimulus,
            case["fixture_id"],
            case["fixture_revision"],
        )
        candidate = _replace_identifier_values(
            candidate,
            case["fixture_id"],
            case["fixture_revision"],
        )
    return _canonical_json_bytes(
        {
            "candidate_output": candidate,
            "schema_id": "ars://contracts/wp6-2-live-grader-calibration-subject",
            "schema_version": "1.0.0",
            "stimulus": visible_stimulus,
        },
        final_lf=True,
    )


def _expected_fixture_oracle(fixture_id: str) -> dict[str, Any]:
    fixture_path = f".research-system/evals/fixtures/{fixture_id}"
    fixture = _revision_yaml(f"{fixture_path}/fixture.yaml")
    paths = {
        "stimulus": f"{fixture_path}/input/stimulus.json",
        "pre_control": f"{fixture_path}/expected/pre-control.json",
        "post_control": f"{fixture_path}/expected/post-control.json",
        "trajectory": f"{fixture_path}/expected/trajectory.json",
    }
    packet = {name: _revision_json(path) for name, path in paths.items()}
    payload = _canonical_json_bytes(packet, final_lf=True)
    oracle = {
        "oracle_id": f"wp6-2-independent-oracle-{fixture_id.lower()}",
        "fixture_id": fixture_id,
        "fixture_revision": fixture["fixture_revision"],
        "source_paths": paths,
        "source_git_blob_sha1s": {name: _revision_blob(BASE_REVISION, path) for name, path in paths.items()},
        "source_byte_sha256s": {
            name: hashlib.sha256(_revision_bytes(BASE_REVISION, path)).hexdigest() for name, path in paths.items()
        },
        **_encoded_bytes(payload),
        "authority_rule": (
            "adjudicator_only_oracle_derived_from_accepted_gate5_fixture_bytes_and_never_present_in_initial_subject"
        ),
    }
    oracle["oracle_manifest_sha256"] = _canonical_json_sha256(oracle)
    return oracle


@lru_cache(maxsize=1)
def _expected_components() -> dict[str, Any]:
    bindings = _parse_approved_bindings()
    target_sets = {
        "model": {
            "grader_class": "M",
            "obligation_count": 31,
            "bindings": bindings["model"],
            "expected_set_sha256": _canonical_json_sha256(bindings["model"]),
        },
        "human": {
            "grader_class": "H",
            "obligation_count": 20,
            "bindings": bindings["human"],
            "expected_set_sha256": _canonical_json_sha256(bindings["human"]),
        },
        "non_compensation_rule": (
            "model_and_human_expected_sets_are_disjoint_and_neither_class_may_supply_repair_or_replace_the_other"
        ),
    }
    specs = _expected_transformation_specs()
    specs_by_id = {spec["transformation_id"]: spec for spec in specs}
    oracles = [_expected_fixture_oracle(fixture_id) for fixture_id in FIXTURE_IDS]
    oracle_by_fixture = {oracle["fixture_id"]: oracle for oracle in oracles}
    calibration_sets: dict[str, Any] = {}
    records_by_class: dict[str, list[dict[str, Any]]] = {}
    for class_name, class_token in (("model", "M"), ("human", "H")):
        bindings_by_fixture: dict[str, list[dict[str, Any]]] = {}
        for binding in bindings[class_name]:
            bindings_by_fixture.setdefault(binding["fixture_id"], []).append(binding)
        fixture_case_index: dict[str, int] = {}
        records = []
        cases = []
        for base_case in _expected_case_sources(class_name):
            case = deepcopy(base_case)
            fixture_id = case["fixture_id"]
            index = fixture_case_index.get(fixture_id, 0)
            fixture_case_index[fixture_id] = index + 1
            binding = bindings_by_fixture[fixture_id][index % len(bindings_by_fixture[fixture_id])]
            variant = binding["source_variant_id"]
            if "claude" in variant:
                producer_family = "claude"
            elif "codex" in variant:
                producer_family = "codex"
            else:
                producer_family = "claude" if index % 2 == 0 else "codex"
            if producer_family == "claude":
                producer_role = "t3-claude-protected-producer"
                producer_context = "wp6-2-t3-claude-protected-canary-context-v1"
            else:
                producer_role = "t4-codex-protected-producer"
                producer_context = "wp6-2-t4-codex-protected-canary-context-v1"
            grader_family = (
                "independent-model-assurance-family"
                if class_name == "model"
                else "independent-human-assurance-authority"
            )
            grader_context = f"wp6-2-t1b-{class_name}-{binding['grader_id']}-independent-context-v1"
            subject = _encoded_bytes(_expected_subject(case))
            relationship_rule = (
                "same_family_or_context_relationship_evidence_visible_concrete_producer_allocation_hidden"
                if case["case_kind"] == "producer_correlated"
                else "fixture_relationship_evidence_visible_only_when_present_in_exact_subject_bytes"
            )
            initial_view = {
                "view_id": f"initial-blinded-{case['case_id'].lower()}",
                "visible_fields": [
                    "exact_expected_subject_bytes",
                    "common_decision_rubric_criteria",
                    "relationship_evidence_embedded_in_subject_when_present",
                ],
                "hidden_fields": [
                    "case_id",
                    "case_kind",
                    "expected_decision",
                    "independent_oracle_bytes",
                    "producer_actor_role_id",
                    "producer_family",
                    "producer_context_id",
                    "target_obligation_id",
                ],
                "relationship_evidence_rule": relationship_rule,
                "expected_decision_present": False,
                "independent_oracle_present": False,
                "subject_sha256": subject["sha256"],
            }
            initial_view["view_manifest_sha256"] = _canonical_json_sha256(initial_view)
            if class_name == "human":
                adjudication = {
                    "rule": (
                        "required_only_after_two_blinded_initial_decisions_are_immutably_recorded_and_disagree_or_request_adjudication"
                    ),
                    "required_input_fields": [
                        "case_execution_record_sha256",
                        "exact_subject_sha256",
                        "independent_oracle_sha256",
                        "human_rubric_sha256",
                        "initial_grader_01_actor_and_context_sha256",
                        "initial_grader_01_decision_and_rationale_sha256",
                        "initial_grader_02_actor_and_context_sha256",
                        "initial_grader_02_decision_and_rationale_sha256",
                        "disagreement_code",
                        "relationship_evidence_sha256",
                        "adjudicator_actor_authority_and_independence_sha256",
                    ],
                    "adjudicator_role_id": "human-adjudicator-distinct-role",
                    "expected_decision_field_permitted": False,
                }
                initial_roles = ["human-initial-grader-01", "human-initial-grader-02"]
                adjudicator_role: str | None = "human-adjudicator-distinct-role"
            else:
                adjudication = {
                    "rule": ("no_model_adjudication_nonagreement_or_nondeterminism_blocks_the_model_class"),
                    "required_input_fields": [],
                    "adjudicator_role_id": None,
                    "expected_decision_field_permitted": False,
                }
                initial_roles = [binding["grader_id"]]
                adjudicator_role = None
            adjudication["adjudication_input_manifest_sha256"] = _canonical_json_sha256(adjudication)
            oracle = oracle_by_fixture[fixture_id]
            spec = specs_by_id[case["transformation_id"]]
            stimulus_path = f".research-system/evals/fixtures/{fixture_id}/input/stimulus.json"
            record = {
                "execution_id": f"EXEC-{case['case_id']}",
                "case_id": case["case_id"],
                "grader_class": class_token,
                "case_kind": case["case_kind"],
                "fixture_id": fixture_id,
                "fixture_revision": case["fixture_revision"],
                "source_fixture_tree_git_sha1": case["source_fixture_tree_git_sha1"],
                "source_reference_role": case["source_reference_role"],
                "source_reference_path": case["source_reference_path"],
                "source_reference_git_blob_sha1": case["source_reference_git_blob_sha1"],
                "source_reference_sha256": case["source_reference_sha256"],
                "stimulus_path": stimulus_path,
                "stimulus_git_blob_sha1": _revision_blob(BASE_REVISION, stimulus_path),
                "stimulus_sha256": hashlib.sha256(_revision_bytes(BASE_REVISION, stimulus_path)).hexdigest(),
                "transformation_id": case["transformation_id"],
                "transformation_version": "1.0.0",
                "transformation_spec_sha256": spec["transformation_spec_sha256"],
                "expected_subject": subject,
                "independent_oracle_id": oracle["oracle_id"],
                "independent_oracle_sha256": oracle["sha256"],
                "independent_oracle_manifest_sha256": oracle["oracle_manifest_sha256"],
                "target_obligation_id": binding["obligation_id"],
                "target_binding_sha256": binding["binding_sha256"],
                "producer_actor_role_id": producer_role,
                "producer_family": producer_family,
                "producer_context_id": producer_context,
                "grader_actor_role_id": binding["grader_id"],
                "grader_family": grader_family,
                "grader_context_id": grader_context,
                "producer_grader_family_relation": "different_families_required",
                "producer_grader_context_relation": "different_contexts_required",
                "repetition_ids": ["rep-01", "rep-02"],
                "initial_grader_role_ids": initial_roles,
                "human_adjudicator_role_id": adjudicator_role,
                "initial_blinded_view": initial_view,
                "adjudication_inputs": adjudication,
                "expected_decision": case["expected_decision"],
                "expected_decision_authority_rule": (
                    "governance_only_never_serialized_into_initial_subject_or_initial_grader_request"
                ),
                "expiry_and_amendment_identity": (
                    "wp6-2-live-grader-calibration-protocol@1.1.0/90-days/"
                    "new-hash-review-and-stephen-acceptance-on-any-change"
                ),
            }
            record["execution_record_sha256"] = _canonical_json_sha256(record)
            case["transformation_spec_sha256"] = spec["transformation_spec_sha256"]
            case["expected_subject_sha256"] = subject["sha256"]
            case["target_obligation_id"] = binding["obligation_id"]
            case["target_binding_sha256"] = binding["binding_sha256"]
            case["initial_blinded_view_sha256"] = initial_view["view_manifest_sha256"]
            case["adjudication_input_manifest_sha256"] = adjudication["adjudication_input_manifest_sha256"]
            case["execution_record_sha256"] = record["execution_record_sha256"]
            case["case_sha256"] = _canonical_json_sha256(_without(case, "case_sha256"))
            records.append(record)
            cases.append(case)
        block = {
            "case_count": len(cases),
            "cases": cases,
            "expected_set_sha256": _canonical_json_sha256(cases),
            "manifest_id": f"wp6-2-live-grader-{class_name}-execution-cases",
            "manifest_version": "1.1.0",
        }
        block["manifest_sha256"] = _canonical_json_sha256(block)
        calibration_sets[class_name] = block
        records_by_class[class_name] = records
    model_manifest = {
        "manifest_id": "wp6-2-live-grader-model-execution-case-manifest",
        "manifest_version": "1.1.0",
        "case_count": 39,
        "records": records_by_class["model"],
    }
    model_manifest["manifest_sha256"] = _canonical_json_sha256(model_manifest)
    human_manifest = {
        "manifest_id": "wp6-2-live-grader-human-execution-case-manifest",
        "manifest_version": "1.1.0",
        "case_count": 28,
        "records": records_by_class["human"],
    }
    human_manifest["manifest_sha256"] = _canonical_json_sha256(human_manifest)
    execution = {
        "execution_freeze_id": "wp6-2-live-grader-calibration-execution-freeze",
        "execution_freeze_version": "1.1.0",
        "subject_packet_schema_id": ("ars://contracts/wp6-2-live-grader-calibration-subject"),
        "subject_packet_schema_version": "1.0.0",
        "canonical_byte_rule": (
            "UTF-8_without_BOM_canonical_JSON_sorted_keys_compact_separators_and_exactly_one_terminal_LF"
        ),
        "transformation_specs": specs,
        "transformation_specs_sha256": _canonical_json_sha256(specs),
        "fixture_oracles": oracles,
        "fixture_oracles_sha256": _canonical_json_sha256(oracles),
        "allocation_rule": (
            "within_each_grader_class_and_fixture_in_declared_case_order_assign_declared_target_bindings_cyclically_in_declared_binding_order_then_bind_exact_producer_and_grader_roles_in_each_record"
        ),
        "model_manifest": model_manifest,
        "human_manifest": human_manifest,
        "expected_observation_separation_rule": (
            "initial_subject_bytes_are_exact_and_exclude_case_id_case_kind_expected_decision_oracle_and_concrete_producer_allocation_observed_decisions_must_come_from_grader_outputs"
        ),
    }
    execution["execution_freeze_sha256"] = _canonical_json_sha256(execution)
    return {
        "target_expected_sets": target_sets,
        "calibration_expected_sets": calibration_sets,
        "execution_case_manifests": execution,
    }


def _assert_semantic_oracles(value: dict[str, Any]) -> None:
    expected = _expected_components()
    for key in (
        "target_expected_sets",
        "calibration_expected_sets",
        "execution_case_manifests",
    ):
        assert value[key] == expected[key], f"independent exact oracle mismatch: {key}"
    rubric = value["human_rubric"]
    assert rubric["rubric_sha256"] == _canonical_json_sha256(_without(rubric, "rubric_sha256"))


def _validate_protocol(value: dict[str, Any]) -> None:
    SchemaRegistry(SCHEMA_ROOT).validate(
        "ars://contracts/wp6-2-live-grader-calibration-protocol",
        value,
    )
    try:
        _assert_semantic_oracles(value)
    except AssertionError as exc:
        raise SchemaError(str(exc)) from exc


def test_portable_canonical_identity_and_scoped_manifest_bind_every_schema() -> None:
    registry = SchemaRegistry(SCHEMA_ROOT)
    protocol = _protocol()
    manifest = _load_yaml(IDENTITY_MANIFEST_PATH)
    registry.validate(
        "ars://contracts/wp6-2-live-grader-calibration-protocol-identity-manifest",
        manifest,
    )
    _validate_protocol(protocol)
    assert manifest["scope"] == "wp6-2-t1a-live-grader-calibration-protocol-only"
    protocol_identity = manifest["protocol_identity"]
    protocol_bytes = _canonical_file_bytes(PROTOCOL_PATH)
    schema_bytes = _canonical_file_bytes(PROTOCOL_SCHEMA_PATH)
    assert hashlib.sha256(protocol_bytes).hexdigest() == protocol_identity["canonical_sha256"]
    assert _git_blob_sha1(protocol_bytes) == protocol_identity["git_blob_sha1"]
    assert hashlib.sha256(schema_bytes).hexdigest() == protocol_identity["schema_canonical_sha256"]
    assert _git_blob_sha1(schema_bytes) == protocol_identity["schema_git_blob_sha1"]
    result_identity = manifest["future_result_schema_identity"]
    result_schema_bytes = _canonical_file_bytes(FUTURE_RESULT_SCHEMA_PATH)
    assert hashlib.sha256(result_schema_bytes).hexdigest() == result_identity["schema_canonical_sha256"]
    assert _git_blob_sha1(result_schema_bytes) == result_identity["schema_git_blob_sha1"]
    review_identity = manifest["review_identity"]
    assert _revision_blob(REVIEW_COMMIT, REVIEW_PATH) == review_identity["review_report_git_blob_sha1"]
    sample_lf = b"alpha\nbeta\n"
    assert _normalize_utf8_lf(sample_lf.replace(b"\n", b"\r\n")) == sample_lf


@pytest.mark.parametrize(
    "schema_path",
    [
        PROTOCOL_SCHEMA_PATH,
        IDENTITY_MANIFEST_SCHEMA_PATH,
        FUTURE_RESULT_SCHEMA_PATH,
    ],
)
def test_contract_schemas_have_no_defaults_and_close_every_typed_object(
    schema_path: Path,
) -> None:
    schema = json.loads(_canonical_file_bytes(schema_path))

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


def test_independent_exact_oracles_include_obligation_ids_and_all_relations() -> None:
    protocol = _protocol()
    expected = _expected_components()
    assert protocol["target_expected_sets"] == expected["target_expected_sets"]
    assert protocol["calibration_expected_sets"] == expected["calibration_expected_sets"]
    assert protocol["execution_case_manifests"] == expected["execution_case_manifests"]
    assert [binding["obligation_id"] for binding in expected["target_expected_sets"]["model"]["bindings"]][0] == "M-005"
    assert [binding["obligation_id"] for binding in expected["target_expected_sets"]["human"]["bindings"]][0] == "H-001"


def test_exact_subject_bytes_are_blinded_and_oracles_are_adjudicator_only() -> None:
    execution = _protocol()["execution_case_manifests"]
    records = execution["model_manifest"]["records"] + execution["human_manifest"]["records"]
    assert len(records) == 67
    for record in records:
        payload = base64.b64decode(record["expected_subject"]["bytes_base64"], validate=True)
        assert payload.endswith(b"\n")
        assert b"\r" not in payload
        assert len(payload) == record["expected_subject"]["byte_length"]
        assert hashlib.sha256(payload).hexdigest() == record["expected_subject"]["sha256"]
        decoded = payload.decode("utf-8")
        for forbidden in (
            '"expected_decision"',
            '"expected_evidence"',
            '"oracle_kind"',
            '"satisfied"',
            record["case_id"],
            record["producer_actor_role_id"],
        ):
            assert forbidden not in decoded
        assert record["initial_blinded_view"]["expected_decision_present"] is False
        assert record["initial_blinded_view"]["independent_oracle_present"] is False
        assert record["producer_family"] != record["grader_family"]
        assert record["producer_context_id"] != record["grader_context_id"]


def test_finite_census_estimand_acceptance_and_seed_are_coherent() -> None:
    protocol = _protocol()
    estimand = protocol["estimands_and_uncertainty"]
    assert estimand["target_population_type"] == (
        "complete_purposive_finite_census_with_no_superpopulation_or_future_fixture_inference"
    )
    assert estimand["model_fixture_cluster_denominator"] == 11
    assert estimand["human_fixture_cluster_denominator"] == 8
    assert "no_confidence_probability_or_sampling_error_interpretation" in estimand["uncertainty_method"]
    assert "prohibited" in estimand["resampling_rule"]
    criteria = protocol["prospective_acceptance_criteria"]
    for class_name in ("model", "human"):
        assert criteria[class_name]["false_pass_count_max"] == 0
        assert criteria[class_name]["false_pass_proportion_max"] == 0.0
        assert criteria[class_name]["false_block_count_max"] == 0
        assert criteria[class_name]["false_block_proportion_max"] == 0.0
        assert criteria[class_name]["bound_label"] == ("prospective_preregistered_finite_census_descriptive_bound")
    assert "confidence_level" not in criteria
    randomness = protocol["repetition_and_randomness"]
    digest = hashlib.sha256(randomness["seed_derivation_material"].encode("utf-8")).digest()
    assert digest.hex() == randomness["seed_derivation_sha256"]
    assert int.from_bytes(digest[:4], "big") & 0x7FFFFFFF == randomness["deterministic_seed"]
    assert randomness["seed_extraction_algorithm"] == (
        "uint32_be(sha256_utf8(seed_derivation_material)[0:4])_bitwise_and_0x7fffffff"
    )


def test_future_result_schema_binds_case_relations_and_forbids_expected_decision() -> None:
    schema = json.loads(_canonical_file_bytes(FUTURE_RESULT_SCHEMA_PATH))
    record = schema["$defs"]["initial_record"]
    assert record["additionalProperties"] is False
    assert "expected_decision" not in record["properties"]
    assert record["properties"]["expected_decision_available_to_initial_grader"] == {"const": False}
    model_branches = schema["properties"]["model_records"]["items"]["allOf"][1]["oneOf"]
    human_branches = schema["properties"]["human_initial_records"]["items"]["allOf"][1]["oneOf"]
    assert len(model_branches) == 39
    assert len(human_branches) == 28
    branch_ids = {branch["properties"]["case_id"]["const"] for branch in model_branches + human_branches}
    expected_ids = {
        case["case_id"]
        for class_name in ("model", "human")
        for case in _expected_components()["calibration_expected_sets"][class_name]["cases"]
    }
    assert branch_ids == expected_ids


def test_review_remediation_remains_pending_fresh_independent_rereview() -> None:
    protocol = _protocol()
    review = protocol["review_remediation"]
    report_bytes = _revision_bytes(REVIEW_COMMIT, REVIEW_PATH)
    assert review["exact_reviewed_subject"] == ("fe2962fa9e10eb290dec0b9e53c3b81bd3ac6491")
    assert review["review_verdict"] == "rework_required"
    assert hashlib.sha256(report_bytes).hexdigest() == review["review_report_canonical_sha256"]
    assert review["independent_rereview_required"] is True
    assert review["self_acceptance_permitted"] is False
    assert protocol["dependency_graph"] == ("T1a -> T2 -> T3/T4 -> T1b -> T5 -> T6 -> T7 -> T8")
    assert protocol["claim_status"] == "no_observed_calibration_claim"


def _refresh_candidate_hashes(value: dict[str, Any]) -> None:
    for class_name in ("model", "human"):
        target = value["target_expected_sets"][class_name]
        for binding in target["bindings"]:
            binding["binding_sha256"] = _canonical_json_sha256(_without(binding, "binding_sha256"))
        target["expected_set_sha256"] = _canonical_json_sha256(target["bindings"])
    freeze = value["execution_case_manifests"]
    for spec in freeze["transformation_specs"]:
        spec["transformation_spec_sha256"] = _canonical_json_sha256(_without(spec, "transformation_spec_sha256"))
    freeze["transformation_specs_sha256"] = _canonical_json_sha256(freeze["transformation_specs"])
    for oracle in freeze["fixture_oracles"]:
        oracle["oracle_manifest_sha256"] = _canonical_json_sha256(_without(oracle, "oracle_manifest_sha256"))
    freeze["fixture_oracles_sha256"] = _canonical_json_sha256(freeze["fixture_oracles"])
    records_by_id: dict[str, dict[str, Any]] = {}
    for class_name in ("model", "human"):
        manifest = freeze[f"{class_name}_manifest"]
        for record in manifest["records"]:
            view = record["initial_blinded_view"]
            view["view_manifest_sha256"] = _canonical_json_sha256(_without(view, "view_manifest_sha256"))
            adjudication = record["adjudication_inputs"]
            adjudication["adjudication_input_manifest_sha256"] = _canonical_json_sha256(
                _without(adjudication, "adjudication_input_manifest_sha256")
            )
            record["execution_record_sha256"] = _canonical_json_sha256(_without(record, "execution_record_sha256"))
            records_by_id[record["case_id"]] = record
        manifest["manifest_sha256"] = _canonical_json_sha256(_without(manifest, "manifest_sha256"))
        block = value["calibration_expected_sets"][class_name]
        for case in block["cases"]:
            record = records_by_id[case["case_id"]]
            case["transformation_spec_sha256"] = record["transformation_spec_sha256"]
            case["expected_subject_sha256"] = record["expected_subject"]["sha256"]
            case["target_obligation_id"] = record["target_obligation_id"]
            case["target_binding_sha256"] = record["target_binding_sha256"]
            case["initial_blinded_view_sha256"] = record["initial_blinded_view"]["view_manifest_sha256"]
            case["adjudication_input_manifest_sha256"] = record["adjudication_inputs"][
                "adjudication_input_manifest_sha256"
            ]
            case["execution_record_sha256"] = record["execution_record_sha256"]
            case["case_sha256"] = _canonical_json_sha256(_without(case, "case_sha256"))
        block["expected_set_sha256"] = _canonical_json_sha256(block["cases"])
        block["manifest_sha256"] = _canonical_json_sha256(_without(block, "manifest_sha256"))
    freeze["execution_freeze_sha256"] = _canonical_json_sha256(_without(freeze, "execution_freeze_sha256"))


def _missing_required(value: dict[str, Any]) -> None:
    value.pop("protocol_version")


def _wrong_type(value: dict[str, Any]) -> None:
    value["repetition_and_randomness"]["repeat_count"] = "2"


def _extra_field(value: dict[str, Any]) -> None:
    value["execution_case_manifests"]["unregistered_default"] = "forbidden"


def _coordinated_obligation_id_swap(value: dict[str, Any]) -> None:
    bindings = value["target_expected_sets"]["model"]["bindings"]
    first, second = bindings[:2]
    old_first, old_second = first["obligation_id"], second["obligation_id"]
    first["obligation_id"], second["obligation_id"] = old_second, old_first
    first["binding_sha256"] = _canonical_json_sha256(_without(first, "binding_sha256"))
    second["binding_sha256"] = _canonical_json_sha256(_without(second, "binding_sha256"))
    mapping = {
        old_first: (first["obligation_id"], first["binding_sha256"]),
        old_second: (second["obligation_id"], second["binding_sha256"]),
    }
    for record in value["execution_case_manifests"]["model_manifest"]["records"]:
        if record["target_obligation_id"] in mapping:
            record["target_obligation_id"], record["target_binding_sha256"] = mapping[record["target_obligation_id"]]
    _refresh_candidate_hashes(value)


def _coordinated_case_id_swap(value: dict[str, Any]) -> None:
    cases = value["calibration_expected_sets"]["model"]["cases"]
    records = value["execution_case_manifests"]["model_manifest"]["records"]
    first_id, second_id = cases[0]["case_id"], cases[1]["case_id"]
    cases[0]["case_id"], cases[1]["case_id"] = second_id, first_id
    first_record = next(record for record in records if record["case_id"] == first_id)
    second_record = next(record for record in records if record["case_id"] == second_id)
    first_record["case_id"], second_record["case_id"] = second_id, first_id
    first_record["execution_id"] = f"EXEC-{second_id}"
    second_record["execution_id"] = f"EXEC-{first_id}"
    _refresh_candidate_hashes(value)


def _coordinated_cross_fixture_reference(value: dict[str, Any]) -> None:
    records = value["execution_case_manifests"]["model_manifest"]["records"]
    target = records[0]
    donor = next(record for record in records if record["fixture_id"] != target["fixture_id"])
    for key in (
        "source_reference_role",
        "source_reference_path",
        "source_reference_git_blob_sha1",
        "source_reference_sha256",
        "stimulus_path",
        "stimulus_git_blob_sha1",
        "stimulus_sha256",
        "expected_subject",
    ):
        target[key] = deepcopy(donor[key])
    target["initial_blinded_view"]["subject_sha256"] = target["expected_subject"]["sha256"]
    case = next(
        item for item in value["calibration_expected_sets"]["model"]["cases"] if item["case_id"] == target["case_id"]
    )
    for key in (
        "source_reference_role",
        "source_reference_path",
        "source_reference_git_blob_sha1",
        "source_reference_sha256",
    ):
        case[key] = target[key]
    _refresh_candidate_hashes(value)


def _coordinated_transformation_alias(value: dict[str, Any]) -> None:
    freeze = value["execution_case_manifests"]
    record = freeze["model_manifest"]["records"][0]
    old_id = record["transformation_id"]
    alias = f"alias-{old_id}"
    spec = next(item for item in freeze["transformation_specs"] if item["transformation_id"] == old_id)
    spec["transformation_id"] = alias
    record["transformation_id"] = alias
    case = next(
        item for item in value["calibration_expected_sets"]["model"]["cases"] if item["case_id"] == record["case_id"]
    )
    case["transformation_id"] = alias
    _refresh_candidate_hashes(value)


def _expected_bytes_changed_and_rehashed(value: dict[str, Any]) -> None:
    record = value["execution_case_manifests"]["model_manifest"]["records"][0]
    payload = base64.b64decode(record["expected_subject"]["bytes_base64"])
    mutated = payload[:-2] + b" \n"
    record["expected_subject"] = _encoded_bytes(mutated)
    record["initial_blinded_view"]["subject_sha256"] = record["expected_subject"]["sha256"]
    _refresh_candidate_hashes(value)


def _adjudication_input_omitted_and_rehashed(value: dict[str, Any]) -> None:
    record = value["execution_case_manifests"]["human_manifest"]["records"][0]
    record["adjudication_inputs"]["required_input_fields"].pop()
    _refresh_candidate_hashes(value)


def _model_human_cross_compensation(value: dict[str, Any]) -> None:
    value["target_expected_sets"]["model"]["bindings"][0] = deepcopy(
        value["target_expected_sets"]["human"]["bindings"][0]
    )


def _correlated_producer_reviewer(value: dict[str, Any]) -> None:
    value["execution_case_manifests"]["model_manifest"]["records"][0]["grader_family"] = "claude"


def _stale_corpus(value: dict[str, Any]) -> None:
    value["corpus"]["vintage"]["accepted_gate5_fixture_tree_git_sha1"] = "0" * 40


def _stale_rubric(value: dict[str, Any]) -> None:
    value["human_rubric"]["rubric_version"] = "0.9.0"


def _omitted_case(value: dict[str, Any]) -> None:
    value["calibration_expected_sets"]["model"]["cases"].pop()


def _omitted_repeat(value: dict[str, Any]) -> None:
    value["repetition_and_randomness"]["repetition_ids"].pop()


def _altered_denominator(value: dict[str, Any]) -> None:
    value["estimands_and_uncertainty"]["human_fixture_cluster_denominator"] = 20


def _altered_estimand(value: dict[str, Any]) -> None:
    value["estimands_and_uncertainty"]["estimand"] = "per_repetition_unclustered_error_rate"


def _altered_bound(value: dict[str, Any]) -> None:
    value["prospective_acceptance_criteria"]["human"]["false_pass_proportion_max"] = 0.5


def _self_attested_evidence(value: dict[str, Any]) -> None:
    value["independence"]["self_attested_evidence_permitted"] = True


Mutation = Callable[[dict[str, Any]], None]


@pytest.mark.parametrize(
    "mutation",
    [
        _missing_required,
        _wrong_type,
        _extra_field,
        _coordinated_obligation_id_swap,
        _coordinated_case_id_swap,
        _coordinated_cross_fixture_reference,
        _coordinated_transformation_alias,
        _expected_bytes_changed_and_rehashed,
        _adjudication_input_omitted_and_rehashed,
        _model_human_cross_compensation,
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
def test_public_contract_seam_rejects_adversarial_bypasses(mutation: Mutation) -> None:
    candidate = deepcopy(_protocol())
    mutation(candidate)
    with pytest.raises(SchemaError):
        _validate_protocol(candidate)
