"""Independent source-fact checks for the proposed WP6.1 annex."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.research_system.contracts.wp6_1_schema_fact_oracle import (
    COMPLETE_SOURCE_GROUP_FIELDS,
    SOURCE_CLOSED_ENUMS,
    SOURCE_DOCUMENTS,
    SOURCE_REVISION,
    assert_all_binding_targets_resolve,
    assert_complete_source_groups,
    assert_conservative_identity_selections_are_explicit,
    assert_correction_and_recovery,
    assert_exact_roots,
    assert_generation_boundary,
    assert_high_risk_field_semantics,
    assert_owner_rows_and_bindings,
    assert_required_source_facts_bound,
    assert_shared_rules,
    assert_type_and_enum_authority,
    immutable_source_bytes,
    parse_owner_rows,
    resource_profile_branch_allowed,
    review_verdict_satisfies_gate,
    review_verdict_structurally_valid,
    writer_lease_allowed,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PROPOSAL_PATH = REPO_ROOT / ".research-system" / "contracts" / "wp6-1-schema-fact-annex-proposal.yaml"


@pytest.fixture(scope="module")
def proposal() -> dict[str, Any]:
    return yaml.safe_load(PROPOSAL_PATH.read_bytes())


@pytest.fixture(scope="module")
def owner_rows() -> tuple[Any, ...]:
    return parse_owner_rows(immutable_source_bytes(REPO_ROOT, "06d"))


def _object(subject: dict[str, Any], object_id: str) -> dict[str, Any]:
    return next(item for item in subject["reusable_objects"] if item["object_id"] == object_id)


def _enum(subject: dict[str, Any], enum_id: str) -> dict[str, Any]:
    return next(item for item in subject["source_closed_enums"] if item["enum_id"] == enum_id)


def _type(subject: dict[str, Any], type_id: str) -> dict[str, Any]:
    return next(item for item in subject["primitive_types"] if item["type_id"] == type_id)


def test_wp6_1_fact_annex_binds_the_exact_immutable_w2_w8_and_06d_bytes(proposal: dict[str, Any]) -> None:
    expected_documents = []
    for source_id, (path, git_blob_id, sha256) in SOURCE_DOCUMENTS.items():
        immutable_source_bytes(REPO_ROOT, source_id)
        expected_documents.append(
            {
                "source_id": source_id,
                "repository_path": path,
                "git_revision": SOURCE_REVISION,
                "git_blob_id": git_blob_id,
                "canonical_utf8_lf_sha256": sha256,
            }
        )
    assert proposal["source_documents"] == expected_documents


def test_wp6_1_fact_annex_independently_recovers_all_rows_and_ordered_events(
    proposal: dict[str, Any], owner_rows: tuple[Any, ...]
) -> None:
    assert len(owner_rows) == 104
    assert sum(len(row.event_types) for row in owner_rows) == 106
    assert len({row.command_type for row in owner_rows}) == 87
    assert len({event for row in owner_rows for event in row.event_types}) == 86
    assert_owner_rows_and_bindings(proposal, owner_rows)


def test_wp6_1_fact_annex_has_exact_closed_roots_including_command_project_id(proposal: dict[str, Any]) -> None:
    assert_exact_roots(proposal)


def test_wp6_1_fact_annex_closes_source_enums_id_grammars_and_p0_integer_bounds(proposal: dict[str, Any]) -> None:
    assert_type_and_enum_authority(proposal)


@pytest.mark.parametrize(
    ("enum_id", "invented"),
    [
        ("enum/review_verdict", "invented_verdict"),
        ("enum/availability", "invented_availability"),
        ("enum/operational_profile", "invented_profile"),
        ("enum/checkpoint_compatibility", "invented_compatibility"),
    ],
)
def test_wp6_1_public_closed_vocabulary_probe_rejects_invented_values(
    proposal: dict[str, Any], enum_id: str, invented: str
) -> None:
    assert invented not in _enum(proposal, enum_id)["values"]
    assert invented not in SOURCE_CLOSED_ENUMS[enum_id]


def test_wp6_1_fact_annex_contains_each_complete_high_risk_source_group(proposal: dict[str, Any]) -> None:
    assert_complete_source_groups(proposal)


def test_wp6_1_fact_annex_has_exact_profile_and_review_condition_semantics(proposal: dict[str, Any]) -> None:
    assert_high_risk_field_semantics(proposal)


def test_wp6_1_fact_annex_resolves_every_source_fact_binding_target(proposal: dict[str, Any]) -> None:
    assert_all_binding_targets_resolve(proposal)


def test_wp6_1_fact_annex_does_not_omit_a_required_source_fact_binding(proposal: dict[str, Any]) -> None:
    assert_required_source_facts_bound(proposal)


@pytest.mark.parametrize(
    "attack",
    ["resource_profile_type", "review_condition_owner_type", "resource_profile_revision_binding"],
)
def test_wp6_1_r4_wrong_but_resolving_semantic_attacks_are_rejected(proposal: dict[str, Any], attack: str) -> None:
    candidate = copy.deepcopy(proposal)
    if attack == "resource_profile_type":
        owner = _object(candidate, "object/resource_request")
        next(item for item in owner["fields"] if item["field_name"] == "operational_profile")["type_ref"] = (
            "type/nonempty_string"
        )
        assertion = assert_high_risk_field_semantics
    elif attack == "review_condition_owner_type":
        owner = _object(candidate, "object/review_gate_condition")
        next(item for item in owner["fields"] if item["field_name"] == "owner_actor_id")["type_ref"] = "type/any_id"
        assertion = assert_high_risk_field_semantics
    else:
        binding = next(
            item for item in candidate["source_fact_bindings"] if item["binding_id"] == "resource_profile_revision"
        )
        binding["target_path"] = "object/resource_request.operational_profile_policy_id"
        assertion = assert_required_source_facts_bound
    with pytest.raises(AssertionError):
        assertion(candidate)


_POLICY_ID = "pol_01989abc-1234-7abc-8def-0123456789ab"
_ACTOR_ID = "act_01989abc-1234-7abc-8def-0123456789ab"


def _applicability(disposition: str = "required") -> dict[str, Any]:
    return {
        "disposition": disposition,
        "policy_id": _POLICY_ID,
        "rationale": "selected by the profile policy",
        "applicability_evidence_refs": ["profile-evidence"],
    }


def _not_applicable() -> dict[str, Any]:
    return {
        "disposition": "not_applicable",
        "policy_id": _POLICY_ID,
        "rationale": "outside the trivial envelope",
        "applicability_evidence_refs": ["not-applicable-evidence"],
    }


def _valid_profile_record(profile: str) -> dict[str, Any]:
    record: dict[str, Any] = {
        "operational_profile": profile,
        "operational_profile_policy_id": _POLICY_ID,
        "operational_profile_revision": "1.0.0",
    }
    if profile == "trivial":
        record["trivial_profile_evidence"] = {
            "request_record_type": "resource_request",
            "grant_record_type": "resource_grant",
            "lease_scope": "command_scoped",
            "resource_ceilings_requirement": "explicit_resource_ceilings",
            "terminal_receipt_kind": "provider_receipt",
            "terminal_receipt_lease_release": "releases_lease",
            "terminal_receipt_evidence_refs": ["receipt-evidence"],
            "benchmark": _not_applicable(),
            "checkpoint": _not_applicable(),
            "periodic_heartbeat": _not_applicable(),
            "recovery": _not_applicable(),
            "provider_command_process": {
                "provider_command_id": "provider-command",
                "process_identity_disposition": "not_applicable",
                "process_identity_not_applicable_rationale": "provider-only command",
            },
        }
    elif profile == "bounded":
        record["bounded_profile_evidence"] = {
            "heartbeat": _applicability(),
            "output_tail": _applicability(),
            "stop": _applicability(),
            "checkpoint": _applicability("not_applicable"),
        }
    else:
        record["long_running_profile_evidence"] = {
            "benchmark": _applicability(),
            "heartbeat": _applicability(),
            "process": _applicability(),
            "checkpoint": _applicability(),
            "stop_recovery": _applicability(),
            "backup": _applicability(),
        }
    return record


@pytest.mark.parametrize("profile", ["trivial", "bounded", "long_running"])
def test_wp6_1_exact_resource_profile_branches_accept_complete_matching_evidence(profile: str) -> None:
    assert resource_profile_branch_allowed(_valid_profile_record(profile))


@pytest.mark.parametrize(
    "attack",
    [
        "null",
        "empty",
        "missing",
        "nested_null",
        "wrong_type",
        "wrong_disposition",
        "empty_evidence",
        "extra",
        "leakage",
        "fallback",
        "outer_null",
        "outer_missing",
        "outer_wrong_type",
    ],
)
def test_wp6_1_resource_profile_fixture_rejects_incomplete_or_leaking_nested_evidence(attack: str) -> None:
    record = _valid_profile_record("bounded")
    evidence = record["bounded_profile_evidence"]
    if attack == "null":
        record["bounded_profile_evidence"] = None
    elif attack == "empty":
        record["bounded_profile_evidence"] = {}
    elif attack == "missing":
        evidence.pop("checkpoint")
    elif attack == "nested_null":
        evidence["checkpoint"] = None
    elif attack == "wrong_type":
        evidence["heartbeat"] = "not-an-object"
    elif attack == "wrong_disposition":
        evidence["heartbeat"]["disposition"] = "invented"
    elif attack == "empty_evidence":
        evidence["heartbeat"]["applicability_evidence_refs"] = []
    elif attack == "extra":
        evidence["unexpected"] = _applicability()
    elif attack == "leakage":
        record["trivial_profile_evidence"] = _valid_profile_record("trivial")["trivial_profile_evidence"]
    elif attack == "fallback":
        record["operational_profile"] = "invented"
    elif attack == "outer_null":
        record["operational_profile_policy_id"] = None
    elif attack == "outer_missing":
        record.pop("operational_profile_revision")
    else:
        record["operational_profile_revision"] = 1
    assert not resource_profile_branch_allowed(record)


def _owned_non_blocking_condition() -> dict[str, Any]:
    return {
        "condition_text": "publish the stated limitation",
        "gate_disposition": "non_blocking",
        "owner_actor_id": _ACTOR_ID,
        "policy_id": _POLICY_ID,
        "evidence_refs": ["policy-evidence"],
    }


def test_wp6_1_review_gate_accepts_unconditional_or_fully_owned_non_blocking_approval() -> None:
    assert review_verdict_structurally_valid("approve", [])
    assert review_verdict_satisfies_gate("approve", [])
    assert review_verdict_satisfies_gate("approve_with_conditions", [_owned_non_blocking_condition()])


@pytest.mark.parametrize("verdict", ["changes_requested", "reject", "unable_to_verify", "withdrawn"])
def test_wp6_1_negative_review_verdicts_are_structurally_valid_but_gate_unsatisfied(verdict: str) -> None:
    assert review_verdict_structurally_valid(verdict, [])
    assert not review_verdict_satisfies_gate(verdict, [])


def test_wp6_1_empty_conditional_approval_is_structurally_valid_but_gate_unsatisfied() -> None:
    assert review_verdict_structurally_valid("approve_with_conditions", [])
    assert not review_verdict_satisfies_gate("approve_with_conditions", [])


@pytest.mark.parametrize(
    "missing_or_wrong",
    ["mixed", "blocking", "null_owner", "missing_owner", "wrong_owner_type", "policy", "evidence"],
)
def test_wp6_1_review_gate_rejects_unowned_blocking_or_unproved_conditional_approval(
    missing_or_wrong: str,
) -> None:
    condition = _owned_non_blocking_condition()
    conditions = [condition]
    if missing_or_wrong == "mixed":
        blocking = _owned_non_blocking_condition()
        blocking["gate_disposition"] = "blocking"
        conditions.append(blocking)
    elif missing_or_wrong == "blocking":
        condition["gate_disposition"] = "blocking"
    elif missing_or_wrong == "null_owner":
        condition["owner_actor_id"] = None
    elif missing_or_wrong == "missing_owner":
        condition.pop("owner_actor_id")
    elif missing_or_wrong == "wrong_owner_type":
        condition["owner_actor_id"] = "not-an-actor-id"
    elif missing_or_wrong == "policy":
        condition["policy_id"] = ""
    else:
        condition["evidence_refs"] = []
    assert not review_verdict_satisfies_gate("approve_with_conditions", conditions)


@pytest.mark.parametrize("attack", ["profile_fallback", "profile_branch", "review_gate_rule"])
def test_wp6_1_mutating_an_exact_profile_or_review_conditional_is_rejected(
    proposal: dict[str, Any], attack: str
) -> None:
    candidate = copy.deepcopy(proposal)
    if attack == "profile_fallback":
        candidate["object_variant_rules"][0]["no_fallback"] = False
    elif attack == "profile_branch":
        candidate["object_variant_rules"][0]["branches"][0]["forbidden_fields"] = []
    else:
        candidate["review_gate_condition_rule"]["gate_satisfaction_rule"] = "owner_optional"
    with pytest.raises(AssertionError):
        assert_high_risk_field_semantics(candidate)


@pytest.mark.parametrize(
    "attack",
    [
        "verdict_missing",
        "verdict_result",
        "verdict_extra",
        "condition_min_zero",
        "condition_min_two",
        "condition_min_absent",
        "global_list_min",
        "reusable_requiredness",
        "reusable_nullable_semantics",
        "nullable_outer_profile",
        "missing_nested_profile_field",
        "evidence_field_type",
        "evidence_minimum",
        "provenance_enum",
        "provenance_field",
        "provenance_binding",
    ],
)
def test_wp6_1_r5_authority_mutations_are_rejected(proposal: dict[str, Any], attack: str) -> None:
    candidate = copy.deepcopy(proposal)
    assertion = assert_high_risk_field_semantics
    if attack == "verdict_missing":
        candidate["review_gate_condition_rule"]["verdict_gate_results"].pop("withdrawn")
    elif attack == "verdict_result":
        candidate["review_gate_condition_rule"]["verdict_gate_results"]["reject"] = "satisfied"
    elif attack == "verdict_extra":
        candidate["review_gate_condition_rule"]["verdict_gate_results"]["invented"] = "satisfied"
    elif attack == "condition_min_zero":
        candidate["review_gate_condition_rule"]["approve_with_conditions_min_items"] = 0
    elif attack == "condition_min_two":
        candidate["review_gate_condition_rule"]["approve_with_conditions_min_items"] = 2
    elif attack == "condition_min_absent":
        candidate["review_gate_condition_rule"].pop("approve_with_conditions_min_items")
    elif attack == "global_list_min":
        _type(candidate, "type/review_gate_condition_list")["min_items"] = 1
    elif attack == "reusable_requiredness":
        candidate["reusable_object_field_rule"]["all_listed_reusable_object_fields_required"] = False
    elif attack == "reusable_nullable_semantics":
        candidate["reusable_object_field_rule"]["nullable_field_semantics"] = "listed_fields_optional"
    elif attack == "nullable_outer_profile":
        owner = _object(candidate, "object/resource_request")
        next(item for item in owner["fields"] if item["field_name"] == "bounded_profile_evidence")["nullable"] = True
    elif attack == "missing_nested_profile_field":
        owner = _object(candidate, "object/bounded_profile_evidence")
        owner["fields"] = [item for item in owner["fields"] if item["field_name"] != "checkpoint"]
    elif attack == "evidence_field_type":
        owner = _object(candidate, "object/profile_evidence_disposition")
        next(item for item in owner["fields"] if item["field_name"] == "applicability_evidence_refs")["type_ref"] = (
            "type/string_list"
        )
    elif attack == "evidence_minimum":
        _type(candidate, "type/nonempty_evidence_ref_list")["min_items"] = 0
    elif attack == "provenance_enum":
        _enum(candidate, "enum/review_condition_gate_disposition")["decision_basis"] = "source_literal"
    elif attack == "provenance_field":
        owner = _object(candidate, "object/review_gate_condition")
        next(item for item in owner["fields"] if item["field_name"] == "gate_disposition")["decision_basis"] = (
            "source_literal"
        )
    else:
        binding = next(
            item
            for item in candidate["source_fact_bindings"]
            if item["binding_id"] == "review_condition_gate_disposition"
        )
        binding["decision_basis"] = "source_literal"
        assertion = assert_required_source_facts_bound
    with pytest.raises(AssertionError):
        assertion(candidate)


def test_wp6_1_fact_annex_freezes_all_shared_command_and_event_normalizations(proposal: dict[str, Any]) -> None:
    assert_shared_rules(proposal)


def test_wp6_1_fact_annex_closes_all_correction_and_recovery_relations(proposal: dict[str, Any]) -> None:
    assert_correction_and_recovery(proposal)


def test_wp6_1_fact_annex_keeps_generation_deterministic_pending_and_non_runtime(proposal: dict[str, Any]) -> None:
    assert_generation_boundary(proposal)


def test_wp6_1_non_source_literal_identity_unions_are_separately_labelled_for_approval(
    proposal: dict[str, Any],
) -> None:
    assert_conservative_identity_selections_are_explicit(proposal)


@pytest.mark.parametrize(
    ("object_id", "field_name"),
    [(object_id, field) for object_id, fields in COMPLETE_SOURCE_GROUP_FIELDS.items() for field in sorted(fields)],
)
def test_wp6_1_omitting_any_high_risk_source_fact_is_rejected(
    proposal: dict[str, Any], object_id: str, field_name: str
) -> None:
    candidate = copy.deepcopy(proposal)
    owner = _object(candidate, object_id)
    owner["fields"] = [item for item in owner["fields"] if item["field_name"] != field_name]
    with pytest.raises(AssertionError):
        assert_complete_source_groups(candidate)


@pytest.mark.parametrize(
    ("kind", "identifier"),
    [
        ("enum", "enum/review_verdict"),
        ("enum", "enum/availability"),
        ("enum", "enum/operational_profile"),
        ("enum", "enum/checkpoint_compatibility"),
        ("id", "type/task_id"),
        ("id", "type/resource_request_id"),
        ("integer", "type/nonnegative_integer"),
        ("integer", "type/positive_integer"),
    ],
)
def test_wp6_1_widening_an_enum_id_or_integer_is_rejected(proposal: dict[str, Any], kind: str, identifier: str) -> None:
    candidate = copy.deepcopy(proposal)
    if kind == "enum":
        _enum(candidate, identifier)["values"].append("invented")
    elif kind == "id":
        _type(candidate, identifier)["pattern"] = ".+"
    else:
        _type(candidate, identifier)["maximum"] = 2**63
    with pytest.raises(AssertionError):
        assert_type_and_enum_authority(candidate)


def test_wp6_1_adding_a_generic_correction_fallback_is_rejected(proposal: dict[str, Any]) -> None:
    candidate = copy.deepcopy(proposal)
    candidate["correction_variant_mappings"].append(
        {
            "corrected_record_kind": "generic",
            "subject_id_type_ref": "type/any_id",
            "owner_projection": "governance",
            "governance_correction_index": "governance_correction_index",
            "subject_field": "erroneous_record_id",
            "projection_selector_rule": "fallback",
        }
    )
    with pytest.raises(AssertionError):
        assert_correction_and_recovery(candidate)


def test_wp6_1_changing_owner_row_order_is_rejected(proposal: dict[str, Any], owner_rows: tuple[Any, ...]) -> None:
    candidate = copy.deepcopy(proposal)
    candidate["command_payload_specs"][0], candidate["command_payload_specs"][1] = (
        candidate["command_payload_specs"][1],
        candidate["command_payload_specs"][0],
    )
    with pytest.raises(AssertionError):
        assert_owner_rows_and_bindings(candidate, owner_rows)


@pytest.mark.parametrize("stale_field", ["external_artefact_refs", "external_availability"])
def test_wp6_1_reintroducing_a_stale_parallel_recovery_field_is_rejected(
    proposal: dict[str, Any], stale_field: str
) -> None:
    candidate = copy.deepcopy(proposal)
    family = next(item for item in candidate["family_specs"] if item["family_id"] == "family/backup_recovery")
    family["fields"].append(
        {
            "field_name": stale_field,
            "type_ref": "type/nonempty_string",
            "nullable": False,
            "source_citation": "stale",
            "decision_basis": "conservative_proposal",
        }
    )
    with pytest.raises(AssertionError):
        assert_correction_and_recovery(candidate)


def test_wp6_1_recovery_writer_lease_requires_unique_complete_available_evidence() -> None:
    expected = {("art_a", "a" * 64), ("art_b", "b" * 64)}
    valid = [
        {
            "artefact_id": artefact_id,
            "content_sha256": digest,
            "availability": "available",
            "availability_evidence_refs": ["evidence"],
        }
        for artefact_id, digest in sorted(expected)
    ]
    assert writer_lease_allowed(valid, expected)
    for mutation in (
        valid[:1],
        [valid[0], valid[0]],
        [{**valid[0], "availability": "missing"}, valid[1]],
        [{**valid[0], "availability": "inaccessible"}, valid[1]],
        [{**valid[0], "availability": "quarantined"}, valid[1]],
        [{**valid[0], "availability_evidence_refs": []}, valid[1]],
    ):
        assert not writer_lease_allowed(mutation, expected)
