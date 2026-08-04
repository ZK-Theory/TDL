"""Production semantic checks for the WP6.3 ``TDL_private`` assurance pack."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Literal

from research_system.assurance.pack_loader import PackAcceptanceSubject, PackUnconsumable
from research_system.canonical import canonical_bytes, sha256_hex


_EXPECTED_TOTAL_SOURCE_COUNT = 14
_EXPECTED_OBLIGATION_COUNT = 69
_EXPECTED_FIXTURE_COUNT = 53
_EXPECTED_BOUNDARY_FIXTURE_COUNT = 3


def validate_tdl_private_semantics(
    *,
    contract: Mapping[str, object],
    pack: Mapping[str, object],
    records: Mapping[str, object],
    subject: PackAcceptanceSubject,
    current_exact_reference_snapshot: Mapping[str, Mapping[str, object]],
    evaluation_time: datetime,
    phase: Literal["prepare", "acceptance"],
) -> None:
    """Promote the accepted WP6.3 semantic contract into the runner path."""

    if phase not in {"prepare", "acceptance"}:
        raise PackUnconsumable("assurance-pack semantic phase is not accepted")
    if evaluation_time.tzinfo is None or evaluation_time.utcoffset() is None:
        raise PackUnconsumable("semantic evaluation time must carry a timezone")
    evaluation_time = evaluation_time.astimezone(UTC)
    record_store, hash_manifest = _record_store(records)
    required = _required(contract)
    expected_applicability = _validate_candidate_projection(required, pack, current_exact_reference_snapshot)
    contract_review_provenance, schema_review_provenance = _validate_contract_schema_lifecycle(
        required,
        pack,
        record_store,
        hash_manifest,
    )
    requirement = _validate_requirement(
        contract,
        required,
        pack,
        record_store,
        hash_manifest,
        expected_applicability,
        evaluation_time,
    )
    if phase == "acceptance":
        _validate_external_acceptance(
            required,
            pack,
            record_store,
            hash_manifest,
            expected_applicability,
            subject,
            requirement,
            contract_review_provenance,
            schema_review_provenance,
            evaluation_time,
        )


def _record_store(records: Mapping[str, object]) -> tuple[dict[str, Mapping[str, object]], dict[str, str]]:
    store: dict[str, Mapping[str, object]] = {}
    hashes: dict[str, str] = {}
    for value in records.values():
        record = getattr(value, "record", None)
        record_id = getattr(value, "record_id", None)
        canonical_sha256 = getattr(value, "canonical_sha256", None)
        if not isinstance(record, Mapping) or not isinstance(record_id, str) or not isinstance(canonical_sha256, str):
            raise PackUnconsumable("semantic validator requires trusted external-record receipts")
        if record_id in store and store[record_id] != record:
            raise PackUnconsumable("semantic validator received conflicting external-record receipts")
        if sha256_hex(canonical_bytes(record)) != canonical_sha256:
            raise PackUnconsumable("external record receipt hash does not match canonical bytes")
        store[record_id] = record
        hashes[record_id] = canonical_sha256
    return store, hashes


def _required(contract: Mapping[str, object]) -> Mapping[str, object]:
    required = contract.get("required_pack_contract")
    if not isinstance(required, Mapping):
        raise PackUnconsumable("accepted contract does not declare required_pack_contract")
    return required


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PackUnconsumable(f"{label} is not a mapping")
    return value


def _sequence(value: object, label: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise PackUnconsumable(f"{label} is not a sequence")
    return value


def _parse_time(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise PackUnconsumable(f"{label} is not an RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PackUnconsumable(f"{label} is not an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PackUnconsumable(f"{label} must carry a timezone")
    return parsed.astimezone(UTC)


def _canonical_sha256(value: object) -> str:
    return sha256_hex(canonical_bytes(value))


def _rows_by_id(rows: object, id_field: str, label: str) -> dict[str, Mapping[str, object]]:
    result: dict[str, Mapping[str, object]] = {}
    for row_value in _sequence(rows, label):
        row = _mapping(row_value, label)
        row_id = row.get(id_field)
        if not isinstance(row_id, str) or not row_id:
            raise PackUnconsumable(f"{label} row lacks {id_field}")
        if row_id in result:
            raise PackUnconsumable(f"duplicate {label} row: {row_id}")
        result[row_id] = row
    return result


def _record(
    record_store: Mapping[str, Mapping[str, object]],
    hash_manifest: Mapping[str, str],
    record_id: object,
    record_type: str,
) -> Mapping[str, object]:
    if not isinstance(record_id, str) or record_id not in record_store or record_id not in hash_manifest:
        raise PackUnconsumable(f"missing external record: {record_id}")
    record = record_store[record_id]
    if record.get("record_type") != record_type:
        raise PackUnconsumable(f"external record has wrong type: {record_id}")
    if _canonical_sha256(record) != hash_manifest[record_id]:
        raise PackUnconsumable(f"external record hash mismatch: {record_id}")
    return record


def _validate_candidate_projection(
    required: Mapping[str, object],
    pack: Mapping[str, object],
    current_exact_reference_snapshot: Mapping[str, Mapping[str, object]],
) -> set[tuple[str, str]]:
    references = _mapping(required.get("references"), "accepted contract references")
    exact_reference_rows = list(_sequence(references.get("exact_reference_rows"), "exact reference rows"))
    pack_references = _mapping(pack.get("references"), "candidate references")
    candidate_reference_rows = [
        *_sequence(pack_references.get("contract_references"), "candidate contract references"),
        *_sequence(pack_references.get("skill_references"), "candidate skill references"),
    ]
    if candidate_reference_rows != exact_reference_rows:
        raise PackUnconsumable("candidate exact reference projection differs from accepted contract")
    reference_ids = {str(_mapping(row, "reference row").get("reference_id")) for row in exact_reference_rows}
    if (
        len(exact_reference_rows) + 2 != _EXPECTED_TOTAL_SOURCE_COUNT
        or len(reference_ids) != len(exact_reference_rows)
        or set(current_exact_reference_snapshot) != reference_ids
    ):
        raise PackUnconsumable("candidate source projection does not close exactly 14 sources")
    contract_count = sum(
        1 for row in exact_reference_rows if _mapping(row, "reference row").get("reference_kind") == "contract"
    )
    skill_count = sum(
        1 for row in exact_reference_rows if _mapping(row, "reference row").get("reference_kind") == "skill"
    )
    if references.get("required_contract_reference_count") != contract_count:
        raise PackUnconsumable("candidate contract source projection count differs")
    if references.get("required_skill_reference_count") != skill_count:
        raise PackUnconsumable("candidate skill source projection count differs")

    lanes = _mapping(required.get("lanes"), "accepted contract lanes")
    candidate_lanes = _mapping(pack.get("lanes"), "candidate lanes")
    if list(candidate_lanes) != list(required.get("six_lane_closure", ())) or set(candidate_lanes) != set(lanes):
        raise PackUnconsumable("candidate lane projection differs from exact six-lane closure")
    expected_applicability: set[tuple[str, str]] = set()
    expected_fixture_ids: set[str] = set()
    row_profile = _mapping(required.get("obligation_row_profile"), "obligation row profile")
    for lane_id, lane_value in lanes.items():
        lane = _mapping(lane_value, f"accepted lane {lane_id}")
        candidate_lane = _mapping(candidate_lanes.get(lane_id), f"candidate lane {lane_id}")
        if candidate_lane.get("lane_id") != lane.get("lane_id") or lane.get("lane_id") != lane_id:
            raise PackUnconsumable("candidate lane identity differs from accepted contract")
        if candidate_lane.get("governing_reference_ids") != lane.get("exact_governing_reference_ids"):
            raise PackUnconsumable("candidate lane governing references differ")
        if candidate_lane.get("fixture_ids") != lane.get("exact_fixture_ids"):
            raise PackUnconsumable("candidate lane fixture projection differs")
        expected_fixture_ids.update(str(item) for item in _sequence(lane.get("exact_fixture_ids"), "lane fixtures"))
        expected_rows = []
        for obligation_value in _sequence(lane.get("required_obligations"), "lane obligations"):
            obligation = _mapping(obligation_value, "lane obligation")
            expected_applicability.add((str(lane_id), str(obligation["obligation_id"])))
            expected_rows.append(
                {
                    "obligation_id": obligation["obligation_id"],
                    "row_profile_id": row_profile.get("row_profile_id"),
                    "source_authority_id": row_profile.get("source_authority_id"),
                    "source_sections": obligation["source_sections"],
                    "assertion_classes": obligation["assertion_classes"],
                    "enforcing_reference_ids": obligation["enforcing_reference_ids"],
                    "review_question_id": obligation["review_question_id"],
                    "evidence_output_id": obligation["evidence_output_id"],
                }
            )
        if candidate_lane.get("obligation_rows") != expected_rows:
            raise PackUnconsumable("candidate lane obligation projection differs")
    if len(expected_applicability) != _EXPECTED_OBLIGATION_COUNT:
        raise PackUnconsumable("candidate obligation projection does not close exactly 69 obligations")
    contract_fixture_rows = list(
        _sequence(
            _mapping(required.get("fixtures"), "contract fixtures").get("exact_fixture_rows"), "contract fixture rows"
        )
    )
    candidate_fixture_rows = list(_sequence(pack.get("required_fixtures"), "candidate required fixtures"))
    if candidate_fixture_rows != contract_fixture_rows or len(candidate_fixture_rows) != _EXPECTED_FIXTURE_COUNT:
        raise PackUnconsumable("candidate fixture projection does not close exactly 53 fixtures")
    observed_fixture_ids = set(_rows_by_id(candidate_fixture_rows, "fixture_id", "candidate fixture").keys())
    contract_fixture_ids = set(_rows_by_id(contract_fixture_rows, "fixture_id", "contract fixture").keys())
    if observed_fixture_ids != contract_fixture_ids or not expected_fixture_ids.issubset(observed_fixture_ids):
        raise PackUnconsumable("candidate fixture ids differ from accepted contract")
    boundary = _mapping(required.get("fixture_execution_boundary"), "fixture execution boundary")
    evidence = _mapping(required.get("external_acceptance_evidence"), "external acceptance evidence")
    boundary_sets = {
        tuple(_sequence(evidence.get("required_executed_boundary_fixture_ids"), "required boundary fixtures")),
        tuple(_sequence(boundary.get("upstream_executable_fixture_ids"), "upstream boundary fixtures")),
        tuple(_sequence(boundary.get("downstream_scientific_execution_fixture_ids"), "downstream boundary fixtures")),
    }
    if len(boundary_sets) != 1 or len(next(iter(boundary_sets))) != _EXPECTED_BOUNDARY_FIXTURE_COUNT:
        raise PackUnconsumable("boundary fixture declarations do not agree exactly")
    if set(next(iter(boundary_sets))) - observed_fixture_ids:
        raise PackUnconsumable("candidate fixture projection lacks exact boundary fixtures")
    return expected_applicability


def _validate_review_operator_provenance(
    required: Mapping[str, object],
    review: Mapping[str, object],
    *,
    producer_actor_id: str,
    reviewer_actor_id: str,
    label: str,
) -> Mapping[str, object]:
    evidence = _mapping(required.get("external_acceptance_evidence"), "external acceptance evidence")
    operator_model = _mapping(evidence.get("operator_model"), "operator model")
    allowed_session_families = set(
        _sequence(operator_model.get("allowed_session_families"), "allowed session families")
    )
    allowed_operator_types = set(_sequence(operator_model.get("allowed_agent_operator_types"), "allowed operators"))
    if operator_model.get("review_operator_must_be_agent_operator_type") is not True:
        allowed_operator_types.add("human_owner")
    if operator_model.get("human_owner_may_act_as_review_operator") is True:
        allowed_operator_types.add("human_owner")
    else:
        allowed_operator_types.discard("human_owner")
    provenance = _mapping(review.get("operator_provenance"), f"{label} operator provenance")
    producer = _mapping(provenance.get("producer_operator"), f"{label} producer operator")
    reviewer = _mapping(provenance.get("reviewer_operator"), f"{label} reviewer operator")
    if (
        producer.get("actor_id") != producer_actor_id
        or reviewer.get("actor_id") != reviewer_actor_id
        or producer.get("operator_type") not in allowed_operator_types
        or reviewer.get("operator_type") not in allowed_operator_types
        or provenance.get("session_family") not in allowed_session_families
        or provenance.get("producer_task_id") == provenance.get("review_task_id")
        or provenance.get("producer_session_id") == provenance.get("review_session_id")
        or provenance.get("context_mode") != "fresh_task_no_parent_history"
        or provenance.get("fork_turns") != "none"
    ):
        raise PackUnconsumable(f"{label} review task provenance does not prove a separate fresh context")
    return provenance


def _validate_contract_schema_lifecycle(
    required: Mapping[str, object],
    pack: Mapping[str, object],
    record_store: Mapping[str, Mapping[str, object]],
    hash_manifest: Mapping[str, str],
) -> tuple[Mapping[str, object], Mapping[str, object]]:
    authorships = [
        record for record in record_store.values() if record.get("record_type") == "contract_schema_authorship"
    ]
    contract_reviews = [
        record for record in record_store.values() if record.get("record_type") == "independent_contract_review"
    ]
    schema_reviews = [
        record for record in record_store.values() if record.get("record_type") == "independent_schema_review"
    ]
    acceptances = [
        record for record in record_store.values() if record.get("record_type") == "stephen_contract_schema_acceptance"
    ]
    if len(authorships) != 1 or len(contract_reviews) != 1 or len(schema_reviews) != 1 or len(acceptances) != 1:
        raise PackUnconsumable("contract/schema lifecycle records are not exact")
    authorship, contract_review, schema_review, acceptance = (
        authorships[0],
        contract_reviews[0],
        schema_reviews[0],
        acceptances[0],
    )
    accepted_contract_subject = pack.get("upstream_contract_reference")
    accepted_pack_schema_subject = pack.get("schema_reference")
    for record in (authorship, contract_review, schema_review, acceptance):
        if record.get("contract_subject") != accepted_contract_subject:
            raise PackUnconsumable("contract lifecycle does not bind the accepted contract subject")
        if record.get("pack_schema_subject") != accepted_pack_schema_subject:
            raise PackUnconsumable("contract lifecycle does not bind the accepted pack schema subject")
    authorship_id = authorship.get("authorship_record_id")
    contract_review_id = contract_review.get("review_record_id")
    schema_review_id = schema_review.get("review_record_id")
    if (
        contract_review.get("authorship_record_id") != authorship_id
        or contract_review.get("authorship_record_sha256") != hash_manifest.get(str(authorship_id))
        or schema_review.get("authorship_record_id") != authorship_id
        or schema_review.get("authorship_record_sha256") != hash_manifest.get(str(authorship_id))
    ):
        raise PackUnconsumable("contract/schema review does not bind exact authorship")
    contract_review_provenance = _validate_review_operator_provenance(
        required,
        contract_review,
        producer_actor_id=str(authorship.get("author_actor_id")),
        reviewer_actor_id=str(contract_review.get("reviewer_actor_id")),
        label="contract",
    )
    schema_review_provenance = _validate_review_operator_provenance(
        required,
        schema_review,
        producer_actor_id=str(authorship.get("author_actor_id")),
        reviewer_actor_id=str(schema_review.get("reviewer_actor_id")),
        label="schema",
    )
    if (
        acceptance.get("authorship_record_id") != authorship_id
        or acceptance.get("authorship_record_sha256") != hash_manifest.get(str(authorship_id))
        or acceptance.get("contract_review_record_id") != contract_review_id
        or acceptance.get("contract_review_record_sha256") != hash_manifest.get(str(contract_review_id))
        or acceptance.get("schema_review_record_id") != schema_review_id
        or acceptance.get("schema_review_record_sha256") != hash_manifest.get(str(schema_review_id))
    ):
        raise PackUnconsumable("Stephen contract/schema acceptance does not bind exact lifecycle records")
    if (
        authorship.get("author_actor_id") != contract_review.get("author_actor_id")
        or authorship.get("author_actor_id") != schema_review.get("author_actor_id")
        or len(
            {
                authorship.get("author_actor_id"),
                contract_review.get("reviewer_actor_id"),
                schema_review.get("reviewer_actor_id"),
                acceptance.get("acceptor_actor_id"),
                pack.get("producer_actor_id"),
            }
        )
        != 5
    ):
        raise PackUnconsumable("contract authorship, reviews, owner acceptance, and production must be distinct")
    return contract_review_provenance, schema_review_provenance


def _requirement_content_preimage(requirement: Mapping[str, object]) -> dict[str, object]:
    return {
        "assurance_requirement_id": requirement["assurance_requirement_id"],
        "revision": requirement["revision"],
        "subject_contract": requirement["subject_contract"],
        "canonical_requirement": requirement["canonical_requirement"],
        "prospective_producer_actor_id": requirement["prospective_producer_actor_id"],
        "obligation_applicability_rows": requirement["obligation_applicability_rows"],
    }


def _canonical_requirement_currency_hash(contract: Mapping[str, object], subject_contract: object) -> str:
    return _canonical_sha256(
        {
            "contract_subject": subject_contract,
            "governing_sources": _mapping(contract.get("source_authority"), "contract source authority").get(
                "governing_sources"
            ),
            "references": _mapping(_required(contract).get("references"), "contract references").get(
                "exact_reference_rows"
            ),
        }
    )


def _validate_requirement(
    contract: Mapping[str, object],
    required: Mapping[str, object],
    pack: Mapping[str, object],
    record_store: Mapping[str, Mapping[str, object]],
    hash_manifest: Mapping[str, str],
    expected_applicability: set[tuple[str, str]],
    evaluation_time: datetime,
) -> Mapping[str, object]:
    reference = _mapping(pack.get("assurance_requirement_reference"), "assurance requirement reference")
    requirement = _record(
        record_store, hash_manifest, reference.get("acceptance_record_id"), "accepted_assurance_requirement"
    )
    if hash_manifest[str(reference.get("acceptance_record_id"))] != reference.get("acceptance_record_sha256"):
        raise PackUnconsumable("candidate requirement reference does not match external record")
    if requirement.get("subject_contract") != pack.get("upstream_contract_reference"):
        raise PackUnconsumable("assurance requirement binds a different upstream contract")
    if (
        requirement.get("assurance_requirement_id") != reference.get("assurance_requirement_id")
        or requirement.get("revision") != reference.get("revision")
        or requirement.get("prospective_producer_actor_id") != pack.get("producer_actor_id")
    ):
        raise PackUnconsumable("assurance requirement identity mismatch")
    requirement_subject = _mapping(requirement.get("requirement_subject"), "requirement subject")
    canonical_requirement = _mapping(requirement.get("canonical_requirement"), "canonical requirement")
    canonical_preimage = {key: value for key, value in canonical_requirement.items() if key != "content_hash"}
    if (
        requirement_subject.get("assurance_requirement_id") != requirement.get("assurance_requirement_id")
        or requirement_subject.get("revision") != requirement.get("revision")
        or requirement_subject.get("canonical_sha256") != _canonical_sha256(_requirement_content_preimage(requirement))
        or requirement_subject.get("canonical_requirement_sha256") != _canonical_sha256(canonical_requirement)
        or canonical_requirement.get("content_hash") != _canonical_sha256(canonical_preimage)
        or canonical_requirement.get("assurance_requirement_id") != requirement.get("assurance_requirement_id")
        or canonical_requirement.get("revision") != requirement.get("revision")
        or canonical_requirement.get("requested_risk") != "R3"
        or canonical_requirement.get("w5_epistemic_risk_floor") != "R3"
        or canonical_requirement.get("action_semantic_risk") != "R3"
        or canonical_requirement.get("requirement_relationship_grade") != requirement.get("minimum_independence_grade")
        or canonical_requirement.get("lanes") != required.get("six_lane_closure")
        or canonical_requirement.get("currency_hash")
        != _canonical_requirement_currency_hash(contract, requirement.get("subject_contract"))
    ):
        raise PackUnconsumable("canonical AssuranceRequirement bytes or identity mismatch")
    applicability_rows = list(
        _sequence(requirement.get("obligation_applicability_rows"), "obligation applicability rows")
    )
    observed_applicability = {
        (_mapping(row, "applicability row").get("lane_id"), _mapping(row, "applicability row").get("obligation_id"))
        for row in applicability_rows
    }
    if len(applicability_rows) != _EXPECTED_OBLIGATION_COUNT or observed_applicability != expected_applicability:
        raise PackUnconsumable("accepted requirement applicability closure differs")
    scope_relationship = _record(
        record_store,
        hash_manifest,
        requirement.get("scope_relationship_record_id"),
        "producer_relationship_evidence",
    )
    requirement_accepted_at = _parse_time(requirement.get("accepted_at"), "accepted requirement accepted_at")
    relationship_effective_at = _parse_time(scope_relationship.get("effective_at"), "scope relationship effective_at")
    relationship_expires_at = _parse_time(scope_relationship.get("expires_at"), "scope relationship expires_at")
    for row_value in applicability_rows:
        row = _mapping(row_value, "applicability row")
        if (
            row.get("prospective_producer_actor_id") != pack.get("producer_actor_id")
            or row.get("decision_author_actor_id") != requirement.get("requirement_author_actor_id")
            or row.get("confirming_actor_id") != requirement.get("scope_reviewer_actor_id")
            or row.get("relationship_record_id") != requirement.get("scope_relationship_record_id")
            or row.get("minimum_independence_grade") != requirement.get("minimum_independence_grade")
        ):
            raise PackUnconsumable("accepted requirement applicability authority is unbound")
        decided_at = _parse_time(row.get("decided_at"), "applicability decided_at")
        if (
            not relationship_effective_at
            <= decided_at
            <= requirement_accepted_at
            <= evaluation_time
            < relationship_expires_at
        ):
            raise PackUnconsumable("applicability decision time is outside relationship or acceptance bounds")
    return requirement


def _pack_subject_dict(subject: PackAcceptanceSubject) -> dict[str, object]:
    return {
        "pack_git_blob": subject.pack_git_blob,
        "pack_raw_sha256": subject.pack_raw_sha256,
        "assurance_pack_id": subject.assurance_pack_id,
        "assurance_pack_revision": subject.assurance_pack_revision,
    }


def _two_key_closure_sha256(review: Mapping[str, object]) -> str:
    return _canonical_sha256(
        {
            "obligation_evidence_rows": review["obligation_evidence_rows"],
            "boundary_fixture_execution_rows": review["boundary_fixture_execution_rows"],
        }
    )


def _validate_external_acceptance(
    required: Mapping[str, object],
    pack: Mapping[str, object],
    record_store: Mapping[str, Mapping[str, object]],
    hash_manifest: Mapping[str, str],
    expected_applicability: set[tuple[str, str]],
    subject: PackAcceptanceSubject,
    requirement: Mapping[str, object],
    contract_review_provenance: Mapping[str, object],
    schema_review_provenance: Mapping[str, object],
    evaluation_time: datetime,
) -> None:
    pack_review = next(
        (record for record in record_store.values() if record.get("record_type") == "independent_pack_review"), None
    )
    owner = next(
        (record for record in record_store.values() if record.get("record_type") == "stephen_owner_acceptance"), None
    )
    if not isinstance(pack_review, Mapping) or not isinstance(owner, Mapping):
        raise PackUnconsumable("acceptance requires independent review and owner acceptance records")
    review_id = pack_review.get("review_record_id")
    owner_id = owner.get("owner_decision_id")
    review = _record(record_store, hash_manifest, review_id, "independent_pack_review")
    owner = _record(record_store, hash_manifest, owner_id, "stephen_owner_acceptance")
    review_relationship = _record(
        record_store,
        hash_manifest,
        review.get("relationship_record_id"),
        "producer_relationship_evidence",
    )
    owner_grant = _record(record_store, hash_manifest, owner.get("authority_grant_id"), "active_authority_grant")
    if review.get("subject") != _pack_subject_dict(subject):
        raise PackUnconsumable("independent review subject does not match loader-computed pack subject")
    if owner.get("subject") != _pack_subject_dict(subject):
        raise PackUnconsumable("owner decision subject does not match loader-computed pack subject")
    if owner.get("review_record_id") != review_id or owner.get("review_record_sha256") != hash_manifest.get(
        str(review_id)
    ):
        raise PackUnconsumable("owner decision does not bind the exact independent review")
    evidence_rows: dict[tuple[str, str], Mapping[str, object]] = {}
    for row_value in _sequence(review.get("obligation_evidence_rows"), "obligation evidence rows"):
        row = _mapping(row_value, "obligation evidence row")
        key = (str(row.get("lane_id")), str(row.get("obligation_id")))
        if key in evidence_rows:
            raise PackUnconsumable(f"duplicate two-key evidence row: {key}")
        evidence_rows[key] = row
    if set(evidence_rows) != expected_applicability or len(evidence_rows) != _EXPECTED_OBLIGATION_COUNT:
        raise PackUnconsumable("two-key evidence does not close every required obligation")
    declared_boundary_fixture_ids = _sequence(
        _mapping(required.get("external_acceptance_evidence"), "external acceptance evidence").get(
            "required_executed_boundary_fixture_ids"
        ),
        "required boundary fixtures",
    )
    fixture_rows = _rows_by_id(review.get("boundary_fixture_execution_rows"), "fixture_id", "boundary fixture evidence")
    if set(fixture_rows) != set(declared_boundary_fixture_ids):
        raise PackUnconsumable("two-key evidence lacks executed boundary fixtures")
    expected_two_key_root = _two_key_closure_sha256(review)
    if (
        review.get("two_key_closure_sha256") != expected_two_key_root
        or owner.get("two_key_closure_sha256") != expected_two_key_root
    ):
        raise PackUnconsumable("owner acceptance does not bind exact two-key evidence")
    provenance = _validate_review_operator_provenance(
        required,
        review,
        producer_actor_id=str(pack.get("producer_actor_id")),
        reviewer_actor_id=str(review.get("reviewer_actor_id")),
        label="pack",
    )
    canonical_requirement = _mapping(requirement.get("canonical_requirement"), "canonical requirement")
    if canonical_requirement.get("task_id") != provenance.get("producer_task_id"):
        raise PackUnconsumable("pack review task provenance does not prove a separate fresh context")
    if (
        len(
            {
                provenance.get("handoff_id"),
                contract_review_provenance.get("handoff_id"),
                schema_review_provenance.get("handoff_id"),
            }
        )
        != 1
    ):
        raise PackUnconsumable("review provenance records do not share one stable handoff identifier")
    evidence = _mapping(required.get("external_acceptance_evidence"), "external acceptance evidence")
    declared_review_types = set(
        _sequence(evidence.get("review_provenance_required_record_types"), "review record types")
    )
    checked_review_types = {"independent_contract_review", "independent_schema_review", "independent_pack_review"}
    if (
        evidence.get("review_provenance_partial_application") != "prohibited"
        or checked_review_types != declared_review_types
    ):
        raise PackUnconsumable("review provenance was not applied to every declared record type")
    if review.get("verdict") != "pass" or owner.get("outcome") != "accepted":
        raise PackUnconsumable("external review and owner acceptance are both required")
    if review.get("producer_actor_id") != pack.get("producer_actor_id"):
        raise PackUnconsumable("independent review names a different producer")
    if review_relationship.get("relationship_context") != "pack_scientific_review":
        raise PackUnconsumable("pack review relationship context is foreign")
    reviewed_at = _parse_time(review.get("reviewed_at"), "independent pack review reviewed_at")
    decided_at = _parse_time(owner.get("decided_at"), "owner acceptance decided_at")
    effective_at = _parse_time(review_relationship.get("effective_at"), "pack review relationship effective_at")
    expires_at = _parse_time(review_relationship.get("expires_at"), "pack review relationship expires_at")
    if not effective_at <= reviewed_at < decided_at <= evaluation_time < expires_at:
        raise PackUnconsumable("review, owner, and relationship times are out of order")
    if (
        owner_grant.get("actor_id") != owner.get("acceptor_actor_id")
        or owner_grant.get("subject_assurance_pack_id") != pack.get("assurance_pack_id")
        or owner_grant.get("grant_state") != "active"
        or owner_grant.get("revoked") is not False
    ):
        raise PackUnconsumable("owner acceptance authority grant identity is foreign")
