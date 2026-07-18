import hashlib
import json
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from research_system.errors import SchemaError
from research_system.schema_registry import SchemaRegistry


ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / ".research-system" / "schemas"
CONTRACT_PATH = ROOT / ".research-system" / "contracts" / "wp6-3-tdl-private-assurance-pack.yaml"
PACK_PATH = ROOT / ".research-system" / "packs" / "tdl-private-assurance.yaml"
CONTRACT_SCHEMA_ID = "ars://contracts/wp6-3-tdl-private-assurance-pack"
PACK_SCHEMA_ID = "ars://assurance/assurance-pack"
LANES = {
    "topology",
    "stochastic_null",
    "statistical_panel",
    "representation",
    "output_provenance",
    "paper_claim",
}
AS_OF = datetime(2026, 7, 18, 12, tzinfo=timezone.utc)


class CandidatePackError(ValueError):
    """A semantic upstream-contract violation not expressible in JSON Schema."""


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _assert_all_object_schemas_are_closed(schema: dict) -> None:
    stack = [("<root>", schema)]
    seen_objects = 0
    while stack:
        location, node = stack.pop()
        if isinstance(node, dict):
            if node.get("type") == "object":
                seen_objects += 1
                assert node.get("additionalProperties") is False, location
            stack.extend((f"{location}/{key}", value) for key, value in node.items())
        elif isinstance(node, list):
            stack.extend((f"{location}/{index}", value) for index, value in enumerate(node))
    assert seen_objects > 10


def _versioned_reference(kind: str, reference_id: str, digit: str) -> dict:
    return {
        "reference_kind": kind,
        "reference_id": reference_id,
        "version_scheme": "git_blob",
        "version": digit * 40,
        "repository_path": f"reference/{reference_id}",
        "canonical_sha256": digit * 64,
        "reference_mode": "exact_versioned_reference",
        "inline_body": False,
    }


def _lane(lane_id: str, obligations: dict) -> dict:
    return {
        "lane_id": lane_id,
        "applicability": {
            "disposition": "required",
            "rationale": "Required by the accepted W5 and WP6.3 scope.",
            "author_actor_id": "act_requirement_author",
            "confirming_actor_id": "act_scope_reviewer",
            "independence_grade": "I2",
            "relationship_evidence_hash": "a" * 64,
            "confirmation_record_hash": "b" * 64,
            "producer_only_confirmation_permitted": False,
        },
        "governing_reference_ids": ["accepted-w5-v0.2"],
        "machine_checks": ["Validate exact identities and fail closed."],
        "human_review_questions": ["Does the obligation preserve its scientific boundary?"],
        "fixtures": [f"apf_{lane_id}_mutation"],
        "limitations": ["Prospective obligation; no result has been audited."],
        "failure_consequence": "blocked",
        "cross_lane_compensation": "prohibited",
        "obligations": obligations,
    }


def _valid_pack() -> dict:
    contract_sources = _load_yaml(CONTRACT_PATH)["source_authority"]["governing_sources"]
    one = ["Explicit prospective obligation."]
    lanes = {
        "topology": _lane(
            "topology",
            {
                "persistence_construction": one,
                "filtration": one,
                "coefficient_field": one,
                "homology_dimensions": one,
                "benchmark_validation": one,
                "interpretation_boundaries": one,
            },
        ),
        "stochastic_null": _lane(
            "stochastic_null",
            {
                "markov_null_design": one,
                "tested_object_invariance": one,
                "rng_algorithm": one,
                "seed_recording": one,
                "inferential_denominator": one,
                "null_operation": one,
                "p_value_formula": one,
                "exchangeability": one,
            },
        ),
        "statistical_panel": _lane(
            "statistical_panel",
            {
                "estimand": one,
                "target_population": one,
                "eligibility": one,
                "denominator": one,
                "missingness": one,
                "clustering": one,
                "uncertainty": one,
                "multiplicity": one,
                "sensitivity": one,
            },
        ),
        "representation": _lane(
            "representation",
            {
                "frozen_fit_identity": one,
                "transform_identity": one,
                "recoding": one,
                "vintage": one,
                "comparability": one,
                "prohibited_refit": one,
            },
        ),
        "output_provenance": _lane(
            "output_provenance",
            {
                "immutable_ids_hashes": one,
                "schema_lineage": one,
                "currency": one,
                "retention": one,
                "consumers": one,
                "publication_boundaries": one,
                "path_boundaries": one,
                "data_boundaries": one,
                "no_overwrite": one,
            },
        ),
        "paper_claim": _lane(
            "paper_claim",
            {
                "topology_to_claim_limits": one,
                "result_decision_bindings": one,
                "required_reviews": one,
                "negative_partial_limitations": one,
                "prohibited_escalations": one,
            },
        ),
    }
    fixtures = [
        {
            "fixture_id": f"apf_contract_mutation_{index}",
            "lane_id": "cross_lane" if index == 9 else sorted(LANES)[index % 6],
            "attack_class": "cross_lane_compensation" if index == 9 else "missing",
            "mutations": [f"mutation-{index}"],
            "expected_outcome": "blocked",
            "cross_lane_compensation": "prohibited",
        }
        for index in range(10)
    ]
    return {
        "schema_id": PACK_SCHEMA_ID,
        "schema_version": "1.0.0",
        "pack_id": "TDL_private",
        "pack_revision": "1.0.0",
        "pack_content_sha256": "c" * 64,
        "canonical_repository_path": ".research-system/packs/tdl-private-assurance.yaml",
        "distribution_scope": "TDL_private",
        "upstream_contract": {
            "schema_id": CONTRACT_SCHEMA_ID,
            "schema_version": "1.0.0",
            "repository_path": ".research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml",
            "git_blob": "1" * 40,
            "canonical_sha256": "2" * 64,
            "acceptance_decision_hash": "3" * 64,
        },
        "lifecycle": {
            "state": "accepted",
            "effective_at": "2026-07-18T00:00:00Z",
            "expires_at": "2027-07-18T00:00:00Z",
            "supersedes_pack_hash": None,
            "stale_behavior": "block_consumption_and_require_new_review",
        },
        "governance": {
            "producer_actor_id": "act_future_pack_producer",
            "requirement_author_actor_id": "act_requirement_author",
            "scope_reviewer_actor_id": "act_scope_reviewer",
            "scientific_reviewer_actor_id": "act_scientific_reviewer",
            "acceptor_actor_id": "act_stephen_authority",
            "minimum_independence_grade": "I2",
            "relationship_evidence_hash": "4" * 64,
            "review_record_hash": "5" * 64,
            "acceptance_decision_hash": "6" * 64,
            "authorship_review_acceptance_separation": "required_and_resolved_from_authority_records",
        },
        "source_authority": {
            "accepted_plan_revision": "fe5f1d40bc8f05f061317c677b5891cea0711249",
            "governing_sources": deepcopy(contract_sources),
        },
        "references": {
            "contract_references": [_versioned_reference("contract", "null-operation-contract", "7")],
            "skill_references": [
                _versioned_reference("skill", skill, digit)
                for skill, digit in zip(
                    [
                        "validate-topology",
                        "statistical-design-audit",
                        "representation-freeze-audit",
                        "result-provenance-review",
                        "paper-claim-trace",
                    ],
                    "89abc",
                    strict=True,
                )
            ],
        },
        "distribution_controls": {
            "permitted_consumers": ["accepted_TDL_research_tasks"],
            "public_template_export": "prohibited",
            "publication_boundary": {
                "public_template_use": "prohibited",
                "manuscript_use": "requires_separately_accepted_result_and_claim_decision",
                "public_excerpt": "prohibited_without_template_safe_derivative_review",
                "claim_promotion": "requires_stephen_attributed_p005_decision",
            },
            "path_restrictions": ["No TDL-private path may enter a public template."],
            "data_restrictions": ["No raw restricted data may be embedded."],
            "restricted_data_material": "opaque_content_addressed_references_only",
            "secrets_env_transcripts": "prohibited",
        },
        "currency": {
            "currency_hash": "d" * 64,
            "verified_at": "2026-07-18T00:00:00Z",
            "expires_at": "2027-07-18T00:00:00Z",
            "currency_triggers": ["Referenced contract or skill identity changed."],
            "retention_class": "durable_governance_record",
            "stale_identity_behavior": "block_and_require_superseding_revision",
        },
        "lanes": lanes,
        "required_fixtures": fixtures,
        "limitations": ["The pack cannot establish any observed result or claim."],
        "core_boundary": {
            "may_modify_w1_w2_lifecycle": False,
            "may_modify_canonical_authority": False,
            "may_override_p005_p022": False,
            "may_lower_w3_w4_controls": False,
            "may_assert_observed_results": False,
            "may_accept_results": False,
            "may_promote_claims": False,
            "may_authorize_migration": False,
        },
    }


def _validate_candidate_pack(
    pack: dict,
    *,
    expected_contract_blob: str = "1" * 40,
    expected_contract_sha256: str = "2" * 64,
    as_of: datetime = AS_OF,
) -> None:
    SchemaRegistry(SCHEMAS).validate(PACK_SCHEMA_ID, pack)
    if set(pack["lanes"]) != LANES:
        raise CandidatePackError("exact six-lane closure required")
    expected_sources = _load_yaml(CONTRACT_PATH)["source_authority"]["governing_sources"]
    if pack["source_authority"]["governing_sources"] != expected_sources:
        raise CandidatePackError("stale or incomplete source authority")
    governance = pack["governance"]
    separated = {
        governance["producer_actor_id"],
        governance["scope_reviewer_actor_id"],
        governance["scientific_reviewer_actor_id"],
        governance["acceptor_actor_id"],
    }
    if len(separated) != 4:
        raise CandidatePackError("producer, reviewers, and acceptor must be distinct")
    if pack["lifecycle"]["state"] == "accepted" and (
        governance["review_record_hash"] is None or governance["acceptance_decision_hash"] is None
    ):
        raise CandidatePackError("accepted pack requires review and acceptance hashes")
    for lane in pack["lanes"].values():
        applicability = lane["applicability"]
        if (
            applicability["disposition"] == "not_applicable"
            and applicability["confirming_actor_id"] == governance["producer_actor_id"]
        ):
            raise CandidatePackError("producer-only not_applicable is prohibited")
    upstream = pack["upstream_contract"]
    if upstream["git_blob"] != expected_contract_blob or upstream["canonical_sha256"] != expected_contract_sha256:
        raise CandidatePackError("stale upstream contract identity")
    if _parse_datetime(pack["lifecycle"]["expires_at"]) <= as_of:
        raise CandidatePackError("pack lifecycle expired")
    if _parse_datetime(pack["currency"]["verified_at"]) > as_of:
        raise CandidatePackError("pack currency verification is in the future")
    if _parse_datetime(pack["currency"]["expires_at"]) <= as_of:
        raise CandidatePackError("pack currency expired")


def test_upstream_contract_is_strict_pending_and_content_addressed():
    registry = SchemaRegistry(SCHEMAS)
    contract = _load_yaml(CONTRACT_PATH)
    registry.validate(CONTRACT_SCHEMA_ID, contract)
    assert registry.contains(PACK_SCHEMA_ID)
    assert registry.contains(CONTRACT_SCHEMA_ID)
    assert contract["status"] == "pending_independent_review"
    assert contract["review_gate"]["current_disposition"] == "stop_for_independent_review"
    assert contract["task_assurance_posture"] == {
        "primary_lane": "output_provenance",
        "other_lane_treatment": "prospective_schema_requirements_only",
        "result_audits_performed": False,
        "claim_review_performed": False,
    }
    assert contract["proposed_pack_identity"] == {
        "pack_id": "TDL_private",
        "repository_path": ".research-system/packs/tdl-private-assurance.yaml",
        "schema_id": PACK_SCHEMA_ID,
        "schema_version": "1.0.0",
        "distribution_scope": "TDL_private",
        "decision_state": "proposed_pending_independent_review_and_owner_acceptance",
    }
    assert not PACK_PATH.exists(), "the future TDL_private pack must not be authored in this task"
    for source in contract["source_authority"]["governing_sources"]:
        blob = subprocess.check_output(
            ["git", "rev-parse", f"{source['git_commit']}:{source['repository_path']}"],
            cwd=ROOT,
            text=True,
        ).strip()
        assert blob == source["git_blob"]
        blob_bytes = subprocess.check_output(["git", "cat-file", "blob", blob], cwd=ROOT)
        assert hashlib.sha256(blob_bytes).hexdigest() == source["canonical_sha256"]
        assert b"\r" not in blob_bytes
    bound_names = set(contract["validation_bindings"]["test_functions"])
    assert bound_names <= set(globals())
    _assert_all_object_schemas_are_closed(_load_json(SCHEMAS / "assurance" / "assurance-pack.schema.json"))
    _assert_all_object_schemas_are_closed(
        _load_json(SCHEMAS / "contracts" / "wp6-3-tdl-private-assurance-pack.schema.json")
    )


def test_candidate_pack_accepts_complete_six_lane_shape():
    pack = _valid_pack()
    _validate_candidate_pack(pack)
    assert set(pack["lanes"]) == LANES
    assert all(lane["cross_lane_compensation"] == "prohibited" for lane in pack["lanes"].values())


def test_candidate_pack_rejects_lane_closure_and_distribution_mutations():
    missing = _valid_pack()
    del missing["lanes"]["topology"]
    with pytest.raises(SchemaError, match="topology"):
        _validate_candidate_pack(missing)

    extra = _valid_pack()
    extra["lanes"]["qualitative"] = deepcopy(extra["lanes"]["topology"])
    with pytest.raises(SchemaError, match="qualitative"):
        _validate_candidate_pack(extra)

    wrong_scope = _valid_pack()
    wrong_scope["distribution_scope"] = "template_safe"
    with pytest.raises(SchemaError, match="distribution_scope"):
        _validate_candidate_pack(wrong_scope)


def test_candidate_pack_rejects_authority_and_not_applicable_bypasses():
    missing_role = _valid_pack()
    del missing_role["governance"]["scientific_reviewer_actor_id"]
    with pytest.raises(SchemaError, match="scientific_reviewer_actor_id"):
        _validate_candidate_pack(missing_role)

    same_authority = _valid_pack()
    same_authority["governance"]["scientific_reviewer_actor_id"] = same_authority["governance"]["producer_actor_id"]
    with pytest.raises(CandidatePackError, match="must be distinct"):
        _validate_candidate_pack(same_authority)

    producer_only = _valid_pack()
    producer_only["lanes"]["topology"]["applicability"].update(
        {
            "disposition": "not_applicable",
            "confirming_actor_id": producer_only["governance"]["producer_actor_id"],
        }
    )
    with pytest.raises(CandidatePackError, match="producer-only not_applicable"):
        _validate_candidate_pack(producer_only)


def test_candidate_pack_rejects_reference_and_boundary_bypasses():
    unversioned = _valid_pack()
    del unversioned["references"]["contract_references"][0]["version"]
    with pytest.raises(SchemaError, match="version"):
        _validate_candidate_pack(unversioned)

    copied_body = _valid_pack()
    copied_body["references"]["skill_references"][0]["inline_body"] = True
    with pytest.raises(SchemaError, match="inline_body"):
        _validate_candidate_pack(copied_body)

    for missing_field in (
        "permitted_consumers",
        "publication_boundary",
        "path_restrictions",
        "data_restrictions",
    ):
        missing_boundary = _valid_pack()
        del missing_boundary["distribution_controls"][missing_field]
        with pytest.raises(SchemaError, match=missing_field):
            _validate_candidate_pack(missing_boundary)


def test_candidate_pack_rejects_stale_identity_currency_and_cross_lane_compensation():
    stale_identity = _valid_pack()
    stale_identity["upstream_contract"]["canonical_sha256"] = "f" * 64
    with pytest.raises(CandidatePackError, match="stale upstream contract identity"):
        _validate_candidate_pack(stale_identity)

    stale_source = _valid_pack()
    stale_source["source_authority"]["governing_sources"][0]["git_blob"] = "f" * 40
    with pytest.raises(CandidatePackError, match="stale or incomplete source authority"):
        _validate_candidate_pack(stale_source)

    stale_currency = _valid_pack()
    stale_currency["currency"]["expires_at"] = "2026-07-17T00:00:00Z"
    with pytest.raises(CandidatePackError, match="currency expired"):
        _validate_candidate_pack(stale_currency)

    compensated = _valid_pack()
    compensated["lanes"]["paper_claim"]["cross_lane_compensation"] = "allowed"
    with pytest.raises(SchemaError, match="cross_lane_compensation"):
        _validate_candidate_pack(compensated)
