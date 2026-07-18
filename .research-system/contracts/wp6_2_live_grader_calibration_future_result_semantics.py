"""Pure semantic validation for prospective WP6.2 T1b evidence.

This module is part of the T1a contract surface.  It performs no provider,
credential, runtime, ledger, or result I/O.  Callers must first validate the
candidate and the scoped identity manifest with their closed JSON Schemas,
supply the protocol's canonical authenticated bytes, and resolve authority
records from an independent trusted store.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

import yaml


class FutureResultSemanticError(ValueError):
    """Raised when prospective evidence violates the frozen T1a relations."""


@dataclass(frozen=True)
class FutureResultSemanticDisposition:
    """Derived, non-authoritative result of semantic validation."""

    model_slot_count: int
    human_initial_slot_count: int
    human_adjudication_slot_count: int
    class_summaries: tuple[Mapping[str, Any], Mapping[str, Any]]
    authority_record_ids: tuple[str, str, str, str]


def canonical_record_sha256(record: Mapping[str, Any]) -> str:
    """Return the contract's canonical SHA-256 for an external record body."""

    payload = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _fail(message: str) -> None:
    raise FutureResultSemanticError(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        _fail(message)


def _require_exact_keys(record: Mapping[str, Any], keys: set[str], label: str) -> None:
    actual = set(record)
    _require(actual == keys, f"{label} keys differ: expected {sorted(keys)}, got {sorted(actual)}")


def _require_exact_value(actual: Any, expected: Any, label: str) -> None:
    _require(actual == expected, f"{label} differs from frozen authority")


def _authenticate_protocol(
    *,
    protocol: Mapping[str, Any],
    protocol_canonical_bytes: bytes,
    identity_manifest: Mapping[str, Any],
) -> Mapping[str, Any]:
    _require(isinstance(protocol_canonical_bytes, bytes), "protocol canonical bytes must be bytes")
    _require(not protocol_canonical_bytes.startswith(b"\xef\xbb\xbf"), "protocol canonical bytes contain a BOM")
    _require(b"\r" not in protocol_canonical_bytes, "protocol canonical bytes are not UTF-8/LF canonical bytes")
    try:
        text = protocol_canonical_bytes.decode("utf-8", errors="strict")
        parsed = yaml.safe_load(text)
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        _fail(f"protocol canonical bytes cannot be parsed: {exc}")
    _require(isinstance(parsed, Mapping), "protocol canonical bytes do not contain a mapping")

    protocol_identity = identity_manifest["protocol_identity"]
    _require_exact_value(
        hashlib.sha256(protocol_canonical_bytes).hexdigest(),
        protocol_identity["canonical_sha256"],
        "protocol canonical byte SHA-256",
    )
    _require_exact_value(
        _git_blob_sha1(protocol_canonical_bytes),
        protocol_identity["git_blob_sha1"],
        "protocol canonical byte Git blob SHA-1",
    )
    _require_exact_value(protocol, parsed, "protocol mapping differs from authenticated canonical bytes")
    _require_exact_value(parsed["protocol_id"], protocol_identity["contract_id"], "protocol contract_id")
    _require_exact_value(parsed["protocol_version"], protocol_identity["contract_version"], "protocol contract_version")

    execution_freeze = parsed["execution_case_manifests"]
    derived_execution_freeze_sha256 = canonical_record_sha256(
        {key: value for key, value in execution_freeze.items() if key != "execution_freeze_sha256"}
    )
    _require_exact_value(
        execution_freeze["execution_freeze_sha256"],
        derived_execution_freeze_sha256,
        "protocol execution freeze SHA-256",
    )

    required_slots = parsed["required_execution_slot_projection"]
    derived_required_slot_set_sha256 = canonical_record_sha256(
        {key: value for key, value in required_slots.items() if key != "required_slot_set_sha256"}
    )
    _require_exact_value(
        required_slots["required_slot_set_sha256"],
        derived_required_slot_set_sha256,
        "protocol required slot-set SHA-256",
    )

    slot_identity = identity_manifest["required_slot_set_identity"]
    _require_exact_value(
        derived_execution_freeze_sha256,
        slot_identity["execution_freeze_sha256"],
        "identity manifest execution freeze SHA-256",
    )
    _require_exact_value(
        derived_required_slot_set_sha256,
        slot_identity["canonical_sha256"],
        "identity manifest required slot-set SHA-256",
    )
    for field, records_field in (
        ("model_initial_slot_count", "model_initial_slots"),
        ("human_initial_slot_count", "human_initial_slots"),
        ("human_adjudication_slot_count", "human_adjudication_slots"),
    ):
        _require_exact_value(required_slots[field], len(required_slots[records_field]), f"protocol {field}")
        _require_exact_value(required_slots[field], slot_identity[field], f"identity manifest {field}")
    return parsed


def _case_indexes(protocol: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    model = {case["case_id"]: case for case in protocol["calibration_expected_sets"]["model"]["cases"]}
    human = {case["case_id"]: case for case in protocol["calibration_expected_sets"]["human"]["cases"]}
    return model, human


def _execution_indexes(
    protocol: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    freeze = protocol["execution_case_manifests"]
    model = {record["case_id"]: record for record in freeze["model_manifest"]["records"]}
    human = {record["case_id"]: record for record in freeze["human_manifest"]["records"]}
    return model, human


_INITIAL_RELATION_FIELDS = (
    "case_id",
    "execution_record_sha256",
    "grader_class",
    "target_obligation_id",
    "target_binding_sha256",
    "expected_subject_sha256",
    "independent_oracle_sha256",
    "producer_actor_role_id",
    "producer_family",
    "producer_context_id",
    "grader_actor_role_id",
    "grader_family",
    "grader_context_id",
)


def _validate_initial_records(
    *,
    label: str,
    actual_records: Sequence[Mapping[str, Any]],
    expected_slots: Sequence[Mapping[str, Any]],
    cases: Mapping[str, Mapping[str, Any]],
    executions: Mapping[str, Mapping[str, Any]],
    grader_class: str,
    evidence_authority_class: str,
) -> dict[str, Mapping[str, Any]]:
    _require(
        len(actual_records) == len(expected_slots),
        f"{label} record count does not equal the frozen slot count",
    )
    actual_projection = [
        {
            "execution_slot_id": record["execution_slot_id"],
            "case_id": record["case_id"],
            "execution_record_sha256": record["execution_record_sha256"],
            "repetition_id": record["repetition_id"],
            "initial_grader_role_id": record["initial_grader_role_id"],
        }
        for record in actual_records
    ]
    _require_exact_value(actual_projection, list(expected_slots), f"{label} ordered slot projection")
    slot_ids = [slot["execution_slot_id"] for slot in actual_projection]
    _require(len(slot_ids) == len(set(slot_ids)), f"{label} contains a duplicate execution slot")

    by_slot: dict[str, Mapping[str, Any]] = {}
    for index, (actual, slot) in enumerate(zip(actual_records, expected_slots, strict=True)):
        case_id = slot["case_id"]
        case = cases.get(case_id)
        execution = executions.get(case_id)
        _require(case is not None and execution is not None, f"{label}[{index}] has a foreign case")
        expected_relations = {
            "case_id": case_id,
            "execution_record_sha256": execution["execution_record_sha256"],
            "grader_class": grader_class,
            "target_obligation_id": execution["target_obligation_id"],
            "target_binding_sha256": execution["target_binding_sha256"],
            "expected_subject_sha256": execution["expected_subject"]["sha256"],
            "independent_oracle_sha256": execution["independent_oracle_sha256"],
            "producer_actor_role_id": execution["producer_actor_role_id"],
            "producer_family": execution["producer_family"],
            "producer_context_id": execution["producer_context_id"],
            "grader_actor_role_id": execution["grader_actor_role_id"],
            "grader_family": execution["grader_family"],
            "grader_context_id": execution["grader_context_id"],
        }
        for field in _INITIAL_RELATION_FIELDS:
            _require_exact_value(actual[field], expected_relations[field], f"{label}[{index}].{field}")
        _require_exact_value(actual["case_sha256"], case["case_sha256"], f"{label}[{index}].case_sha256")
        _require_exact_value(
            actual["evidence_authority_class"],
            evidence_authority_class,
            f"{label}[{index}].evidence_authority_class",
        )
        _require(
            actual["producer_family"] != actual["grader_family"],
            f"{label}[{index}] producer and grader families are correlated",
        )
        _require(
            actual["producer_context_id"] != actual["grader_context_id"],
            f"{label}[{index}] producer and grader contexts are correlated",
        )
        _require(
            actual["expected_decision_available_to_initial_grader"] is False,
            f"{label}[{index}] exposes the expected decision",
        )
        _require_exact_value(
            actual["observed_decision_source"],
            "grader_output_without_expected_decision_access",
            f"{label}[{index}].observed_decision_source",
        )
        by_slot[slot["execution_slot_id"]] = actual
    return by_slot


def _validate_adjudications(
    *,
    actual_records: Sequence[Mapping[str, Any]],
    expected_slots: Sequence[Mapping[str, Any]],
    human_initial_by_slot: Mapping[str, Mapping[str, Any]],
    human_executions: Mapping[str, Mapping[str, Any]],
) -> dict[str, str]:
    _require(
        len(actual_records) == len(expected_slots),
        "human adjudication count does not equal the frozen case count",
    )
    projection_fields = (
        "adjudication_slot_id",
        "case_id",
        "execution_record_sha256",
        "adjudication_input_manifest_sha256",
    )
    actual_projection = [{field: record[field] for field in projection_fields} for record in actual_records]
    expected_projection = [{field: slot[field] for field in projection_fields} for slot in expected_slots]
    _require_exact_value(
        actual_projection,
        expected_projection,
        "human ordered adjudication-slot projection",
    )
    case_ids = [record["case_id"] for record in actual_records]
    _require(len(case_ids) == len(set(case_ids)), "human adjudications repeat a case")

    final_decisions: dict[str, str] = {}
    for index, (actual, slot) in enumerate(zip(actual_records, expected_slots, strict=True)):
        case_id = slot["case_id"]
        execution = human_executions[case_id]
        expected_initial = []
        for execution_slot_id in slot["initial_execution_slot_ids"]:
            initial = human_initial_by_slot.get(execution_slot_id)
            _require(initial is not None, f"adjudication[{index}] references a missing initial slot")
            expected_initial.append(
                {
                    "execution_slot_id": execution_slot_id,
                    "grader_output_sha256": initial["grader_output_sha256"],
                    "observed_decision": initial["observed_decision"],
                }
            )
        _require_exact_value(
            actual["initial_decisions"],
            expected_initial,
            f"adjudication[{index}].initial_decisions",
        )
        decisions = [item["observed_decision"] for item in expected_initial]
        if "adjudication_required" in decisions:
            disagreement_code = "adjudication_requested"
        elif len(set(decisions)) > 1:
            disagreement_code = "decision_disagreement"
        else:
            disagreement_code = "none"
        required = disagreement_code != "none"
        _require_exact_value(
            actual["disagreement_code"],
            disagreement_code,
            f"adjudication[{index}].disagreement_code",
        )
        _require_exact_value(
            actual["adjudication_required"],
            required,
            f"adjudication[{index}].adjudication_required",
        )
        _require_exact_value(
            actual["adjudicator_role_id"],
            execution["human_adjudicator_role_id"],
            f"adjudication[{index}].adjudicator_role_id",
        )
        _require(
            actual["adjudicator_role_id"] not in execution["initial_grader_role_ids"],
            f"adjudication[{index}] reuses an initial grader role",
        )
        _require(
            actual["expected_decision_available_to_adjudicator"] is False,
            f"adjudication[{index}] exposes the expected decision",
        )
        if required:
            _require(
                actual["adjudicated_decision"] in {"accept", "reject", "adjudication_required"},
                f"adjudication[{index}] lacks a required adjudicated decision",
            )
            authority_sha = actual["adjudicator_actor_authority_and_independence_sha256"]
            _require(
                isinstance(authority_sha, str) and authority_sha != "0" * 64,
                f"adjudication[{index}] lacks independently addressable authority evidence",
            )
            final_decisions[case_id] = actual["adjudicated_decision"]
        else:
            _require_exact_value(
                actual["adjudicated_decision"],
                "not_required",
                f"adjudication[{index}].adjudicated_decision",
            )
            _require(
                actual["adjudicator_actor_authority_and_independence_sha256"] is None,
                f"adjudication[{index}] self-attests unused adjudicator authority",
            )
            final_decisions[case_id] = decisions[0]
    return final_decisions


def _model_final_decisions(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, str | None]:
    by_case: dict[str, list[str]] = {}
    for record in records:
        by_case.setdefault(record["case_id"], []).append(record["observed_decision"])
    return {case_id: decisions[0] if len(set(decisions)) == 1 else None for case_id, decisions in by_case.items()}


def _derive_summary(
    *,
    grader_class: str,
    cases: Mapping[str, Mapping[str, Any]],
    final_decisions: Mapping[str, str | None],
    denominator: int,
) -> dict[str, Any]:
    by_fixture: dict[str, list[Mapping[str, Any]]] = {}
    for case in cases.values():
        by_fixture.setdefault(case["fixture_id"], []).append(case)
    _require(len(by_fixture) == denominator, f"{grader_class} fixture denominator drift")
    false_pass = 0
    false_block = 0
    decision_error = 0
    for fixture_cases in by_fixture.values():
        observed_pairs = [(case["expected_decision"], final_decisions.get(case["case_id"])) for case in fixture_cases]
        false_pass += int(any(expected == "reject" and observed == "accept" for expected, observed in observed_pairs))
        false_block += int(any(expected == "accept" and observed != "accept" for expected, observed in observed_pairs))
        decision_error += int(any(expected != observed for expected, observed in observed_pairs))
    return {
        "grader_class": grader_class,
        "fixture_cluster_denominator": denominator,
        "false_pass_count": false_pass,
        "false_pass_proportion": false_pass / denominator,
        "false_block_count": false_block,
        "false_block_proportion": false_block / denominator,
        "decision_error_count": decision_error,
        "sampling_uncertainty_interpretation": "none_exact_finite_census_descriptive_closure",
        "zero_error_rule": "accepted_if_and_only_if_all_three_derived_error_counts_equal_zero",
        "accepted": false_pass == 0 and false_block == 0 and decision_error == 0,
    }


def _resolve_authority_record(
    *,
    candidate: Mapping[str, Any],
    records: Mapping[str, Mapping[str, Any]],
    id_field: str,
    sha_field: str,
    exact_keys: set[str],
    label: str,
) -> Mapping[str, Any]:
    record_id = candidate[id_field]
    record = records.get(record_id)
    _require(record is not None, f"{label} is absent from the trusted external authority set")
    _require_exact_keys(record, exact_keys, label)
    _require_exact_value(record["record_id"], record_id, f"{label}.record_id")
    _require_exact_value(
        canonical_record_sha256(record),
        candidate[sha_field],
        f"{label} canonical SHA-256",
    )
    return record


def _validate_external_authority(
    *,
    candidate: Mapping[str, Any],
    protocol: Mapping[str, Any],
    identity_manifest: Mapping[str, Any],
    records: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str, str, str]:
    protocol_record = _resolve_authority_record(
        candidate=candidate,
        records=records,
        id_field="protocol_identity_record_id",
        sha_field="protocol_identity_record_sha256",
        exact_keys={
            "record_id",
            "record_type",
            "subject_type",
            "subject_id",
            "subject_version",
            "subject_canonical_sha256",
            "subject_git_blob_sha1",
            "outcome",
            "authority_class",
            "sequence_position",
        },
        label="protocol identity record",
    )
    protocol_identity = identity_manifest["protocol_identity"]
    expected_protocol = {
        "record_type": "wp6_2_t1a_protocol_identity_acceptance",
        "subject_type": "wp6_2_t1a_live_grader_calibration_protocol",
        "subject_id": protocol["protocol_id"],
        "subject_version": protocol["protocol_version"],
        "subject_canonical_sha256": protocol_identity["canonical_sha256"],
        "subject_git_blob_sha1": protocol_identity["git_blob_sha1"],
        "outcome": "accepted_identity",
        "authority_class": "independent_protocol_identity_registry",
    }
    for field, expected in expected_protocol.items():
        _require_exact_value(protocol_record[field], expected, f"protocol identity record.{field}")

    slot_record = _resolve_authority_record(
        candidate=candidate,
        records=records,
        id_field="required_slot_set_identity_record_id",
        sha_field="required_slot_set_identity_record_sha256",
        exact_keys={
            "record_id",
            "record_type",
            "subject_type",
            "subject_id",
            "subject_version",
            "subject_canonical_sha256",
            "execution_freeze_sha256",
            "outcome",
            "authority_class",
            "sequence_position",
        },
        label="required slot-set identity record",
    )
    slot_identity = identity_manifest["required_slot_set_identity"]
    expected_slot = {
        "record_type": "wp6_2_t1a_required_slot_set_acceptance",
        "subject_type": "wp6_2_t1a_required_execution_slot_set",
        "subject_id": slot_identity["required_slot_set_id"],
        "subject_version": slot_identity["required_slot_set_version"],
        "subject_canonical_sha256": slot_identity["canonical_sha256"],
        "execution_freeze_sha256": slot_identity["execution_freeze_sha256"],
        "outcome": "accepted_exact_set",
        "authority_class": "independent_expected_set_registry",
    }
    for field, expected in expected_slot.items():
        _require_exact_value(slot_record[field], expected, f"required slot-set record.{field}")

    review_record = _resolve_authority_record(
        candidate=candidate,
        records=records,
        id_field="t1a_independent_review_record_id",
        sha_field="t1a_independent_review_record_sha256",
        exact_keys={
            "record_id",
            "record_type",
            "subject_type",
            "subject_id",
            "subject_version",
            "protocol_canonical_sha256",
            "required_slot_set_sha256",
            "protocol_identity_record_id",
            "protocol_identity_record_sha256",
            "required_slot_set_identity_record_id",
            "required_slot_set_identity_record_sha256",
            "outcome",
            "authority_class",
            "reviewer_distinct_from_protocol_author",
            "sequence_position",
        },
        label="T1a independent review record",
    )
    expected_review = {
        "record_type": "wp6_2_t1a_independent_review",
        "subject_type": "wp6_2_t1a_protocol_and_required_slot_set",
        "subject_id": protocol["protocol_id"],
        "subject_version": protocol["protocol_version"],
        "protocol_canonical_sha256": protocol_identity["canonical_sha256"],
        "required_slot_set_sha256": slot_identity["canonical_sha256"],
        "protocol_identity_record_id": protocol_record["record_id"],
        "protocol_identity_record_sha256": canonical_record_sha256(protocol_record),
        "required_slot_set_identity_record_id": slot_record["record_id"],
        "required_slot_set_identity_record_sha256": canonical_record_sha256(slot_record),
        "outcome": "accept",
        "authority_class": "distinct_independent_reviewer",
        "reviewer_distinct_from_protocol_author": True,
    }
    for field, expected in expected_review.items():
        _require_exact_value(review_record[field], expected, f"T1a independent review record.{field}")

    owner_record = _resolve_authority_record(
        candidate=candidate,
        records=records,
        id_field="t1a_stephen_acceptance_record_id",
        sha_field="t1a_stephen_acceptance_record_sha256",
        exact_keys={
            "record_id",
            "record_type",
            "subject_type",
            "subject_id",
            "subject_version",
            "protocol_canonical_sha256",
            "required_slot_set_sha256",
            "independent_review_record_id",
            "independent_review_record_sha256",
            "outcome",
            "authority_id",
            "authority_class",
            "sequence_position",
        },
        label="T1a Stephen acceptance record",
    )
    expected_owner = {
        "record_type": "wp6_2_t1a_owner_acceptance",
        "subject_type": "wp6_2_t1a_protocol_and_required_slot_set",
        "subject_id": protocol["protocol_id"],
        "subject_version": protocol["protocol_version"],
        "protocol_canonical_sha256": protocol_identity["canonical_sha256"],
        "required_slot_set_sha256": slot_identity["canonical_sha256"],
        "independent_review_record_id": review_record["record_id"],
        "independent_review_record_sha256": canonical_record_sha256(review_record),
        "outcome": "accepted",
        "authority_id": "stephen",
        "authority_class": "named_owner",
    }
    for field, expected in expected_owner.items():
        _require_exact_value(owner_record[field], expected, f"T1a Stephen acceptance record.{field}")

    positions = [
        protocol_record["sequence_position"],
        slot_record["sequence_position"],
        review_record["sequence_position"],
        owner_record["sequence_position"],
    ]
    _require(
        all(isinstance(position, int) and not isinstance(position, bool) and position >= 0 for position in positions),
        "external authority sequence positions must be non-negative integers",
    )
    _require(
        positions[0] < positions[1] < positions[2] < positions[3],
        "external authority records are not in protocol -> slot set -> review -> owner order",
    )
    return tuple(record["record_id"] for record in (protocol_record, slot_record, review_record, owner_record))


def validate_future_result_semantics(
    candidate: Mapping[str, Any],
    *,
    protocol: Mapping[str, Any],
    protocol_canonical_bytes: bytes,
    identity_manifest: Mapping[str, Any],
    accepted_authority_records: Mapping[str, Mapping[str, Any]],
) -> FutureResultSemanticDisposition:
    """Validate prospective evidence against frozen slots and external authority.

    Args:
        candidate: Prospective result already validated by the closed result schema.
        protocol: Parsed protocol mapping. It must equal the mapping parsed from
            ``protocol_canonical_bytes`` exactly.
        protocol_canonical_bytes: Authenticated UTF-8/LF protocol bytes whose SHA-256
            and Git blob SHA-1 match the scoped identity manifest.
        identity_manifest: Closed, schema-validated T1a identity manifest.
        accepted_authority_records: Trusted caller-supplied records resolved from an
            independent store, never from the candidate.

    Returns:
        A derived, non-authoritative semantic disposition.

    Raises:
        FutureResultSemanticError: If protocol byte identity, derived execution or
            slot hashes, external authority, or candidate relations differ from the
            frozen T1a contract.

    This function never writes or accepts a result; it only derives whether a
    prospective candidate is semantically coherent with the T1a contract.
    """

    _require_exact_value(
        identity_manifest["scope"],
        "wp6-2-t1a-live-grader-calibration-protocol-only",
        "identity manifest scope",
    )
    protocol = _authenticate_protocol(
        protocol=protocol,
        protocol_canonical_bytes=protocol_canonical_bytes,
        identity_manifest=identity_manifest,
    )
    protocol_identity = identity_manifest["protocol_identity"]
    slot_identity = identity_manifest["required_slot_set_identity"]
    _require_exact_value(candidate["protocol_id"], protocol["protocol_id"], "candidate protocol_id")
    _require_exact_value(candidate["protocol_version"], protocol["protocol_version"], "candidate protocol_version")
    _require_exact_value(
        candidate["protocol_canonical_sha256"],
        protocol_identity["canonical_sha256"],
        "candidate protocol_canonical_sha256",
    )
    _require_exact_value(
        candidate["protocol_git_blob_sha1"],
        protocol_identity["git_blob_sha1"],
        "candidate protocol_git_blob_sha1",
    )
    _require_exact_value(
        candidate["required_slot_set_id"],
        slot_identity["required_slot_set_id"],
        "candidate required_slot_set_id",
    )
    _require_exact_value(
        candidate["required_slot_set_version"],
        slot_identity["required_slot_set_version"],
        "candidate required_slot_set_version",
    )
    _require_exact_value(
        candidate["required_slot_set_sha256"],
        slot_identity["canonical_sha256"],
        "candidate required_slot_set_sha256",
    )
    _require_exact_value(
        candidate["execution_freeze_sha256"],
        protocol["execution_case_manifests"]["execution_freeze_sha256"],
        "candidate execution_freeze_sha256",
    )
    _require_exact_value(
        candidate["corpus_manifest_sha256"],
        protocol["corpus"]["corpus_manifest_sha256"],
        "candidate corpus_manifest_sha256",
    )

    authority_ids = _validate_external_authority(
        candidate=candidate,
        protocol=protocol,
        identity_manifest=identity_manifest,
        records=accepted_authority_records,
    )

    model_cases, human_cases = _case_indexes(protocol)
    model_executions, human_executions = _execution_indexes(protocol)
    required_slots = protocol["required_execution_slot_projection"]
    _validate_initial_records(
        label="model",
        actual_records=candidate["model_records"],
        expected_slots=required_slots["model_initial_slots"],
        cases=model_cases,
        executions=model_executions,
        grader_class="M",
        evidence_authority_class="independent_model_grader_evidence",
    )
    human_by_slot = _validate_initial_records(
        label="human initial",
        actual_records=candidate["human_initial_records"],
        expected_slots=required_slots["human_initial_slots"],
        cases=human_cases,
        executions=human_executions,
        grader_class="H",
        evidence_authority_class="permitted_human_assurance_authority_evidence",
    )
    human_final = _validate_adjudications(
        actual_records=candidate["human_adjudication_records"],
        expected_slots=required_slots["human_adjudication_slots"],
        human_initial_by_slot=human_by_slot,
        human_executions=human_executions,
    )
    model_final = _model_final_decisions(candidate["model_records"])
    derived_summaries = (
        _derive_summary(
            grader_class="M",
            cases=model_cases,
            final_decisions=model_final,
            denominator=protocol["estimands_and_uncertainty"]["model_fixture_cluster_denominator"],
        ),
        _derive_summary(
            grader_class="H",
            cases=human_cases,
            final_decisions=human_final,
            denominator=protocol["estimands_and_uncertainty"]["human_fixture_cluster_denominator"],
        ),
    )
    _require_exact_value(
        candidate["class_summaries"],
        list(derived_summaries),
        "candidate class summaries",
    )
    return FutureResultSemanticDisposition(
        model_slot_count=len(candidate["model_records"]),
        human_initial_slot_count=len(candidate["human_initial_records"]),
        human_adjudication_slot_count=len(candidate["human_adjudication_records"]),
        class_summaries=derived_summaries,
        authority_record_ids=authority_ids,
    )


__all__ = [
    "FutureResultSemanticDisposition",
    "FutureResultSemanticError",
    "canonical_record_sha256",
    "validate_future_result_semantics",
]
