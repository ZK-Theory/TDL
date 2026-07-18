import hashlib
import json
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from research_system.errors import SchemaError
from research_system.schema_registry import SchemaRegistry


ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / ".research-system" / "schemas"
CONTRACT_PATH = ROOT / ".research-system" / "contracts" / "wp6-3-tdl-private-assurance-pack.yaml"
PACK_PATH = ROOT / ".research-system" / "packs" / "tdl-private-assurance.yaml"
CONTRACT_SCHEMA_PATH = (
    ROOT / ".research-system" / "schemas" / "contracts" / "wp6-3-tdl-private-assurance-pack.schema.json"
)
CONTRACT_SCHEMA_ID = "ars://contracts/wp6-3-tdl-private-assurance-pack"
PACK_SCHEMA_ID = "ars://assurance/packs/tdl-private/1.0"
LEGACY_GENERIC_PACK_SCHEMA_ID = "ars://assurance/assurance-pack"
LANES = {
    "topology",
    "stochastic_null",
    "statistical_panel",
    "representation",
    "output_provenance",
    "paper_claim",
}
AS_OF = datetime(2026, 7, 18, 12, tzinfo=timezone.utc)

ACT_CONTRACT_AUTHOR = "act_00000000-0000-7000-8000-000000000001"
ACT_PRODUCER = "act_00000000-0000-7000-8000-000000000002"
ACT_REQUIREMENT_AUTHOR = "act_00000000-0000-7000-8000-000000000003"
ACT_SCOPE_REVIEWER = "act_00000000-0000-7000-8000-000000000004"
ACT_SCIENTIFIC_REVIEWER = "act_00000000-0000-7000-8000-000000000005"
ACT_OWNER = "act_00000000-0000-7000-8000-000000000006"
ASSURANCE_PACK_ID = "asp_00000000-0000-7000-8000-000000000007"
ASSURANCE_REQUIREMENT_ID = "asr_00000000-0000-7000-8000-000000000008"
REQUIREMENT_RECORD_ID = "ard_00000000-0000-7000-8000-000000000009"
REVIEW_RECORD_ID = "arv_00000000-0000-7000-8000-00000000000a"
OWNER_DECISION_ID = "apr_00000000-0000-7000-8000-00000000000b"
SCOPE_RELATIONSHIP_ID = "rel_00000000-0000-7000-8000-00000000000d"
REVIEW_RELATIONSHIP_ID = "rel_00000000-0000-7000-8000-00000000000e"
OWNER_GRANT_ID = "agr_00000000-0000-7000-8000-00000000000c"

EXPECTED_EXTERNAL_SCHEMA_IDS = {
    "canonical_actor": "ars://assurance/records/canonical-actor/1.0",
    "producer_relationship_evidence": "ars://assurance/records/producer-relationship-evidence/1.0",
    "accepted_assurance_requirement": "ars://assurance/records/accepted-assurance-requirement/1.0",
    "independent_pack_review": "ars://assurance/records/independent-pack-review/1.0",
    "stephen_owner_acceptance": "ars://assurance/records/stephen-owner-acceptance/1.0",
    "active_authority_grant": "ars://assurance/records/active-authority-grant/1.0",
    "registered_pack_object": "ars://assurance/records/registered-pack-object/1.0",
}

EXTERNAL_CONTRACT_REFERENCE = {
    "schema_id": CONTRACT_SCHEMA_ID,
    "schema_version": "1.0.0",
    "repository_path": ".research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml",
    "git_blob": "1" * 40,
    "canonical_sha256": "2" * 64,
}
EXTERNAL_SCHEMA_REFERENCE = {
    "schema_id": PACK_SCHEMA_ID,
    "schema_version": "1.0.0",
    "repository_path": ".research-system/schemas/assurance/assurance-pack.schema.json",
    "git_blob": "3" * 40,
    "canonical_sha256": "4" * 64,
}

EXPECTED_REFERENCE_IDS = frozenset(
    """
    contract/tda-formulas/w2-exact-diagonal-bound
    contract/topology-invariants/null-operation-changes-ph-input
    contract/topology-invariants/frozen-loadings-transform-only
    contract/stochastic-tests/markov-order-provenance
    contract/stochastic-tests/monte-carlo-permutation-p-value
    contract/stage1-output-schemas/stage1-output-json-validation
    skill/validate-topology
    skill/statistical-design-audit
    skill/representation-freeze-audit
    skill/result-provenance-review
    skill/paper-claim-trace
    skill/research-assurance-triage
    """.split()
)
EXPECTED_FIXTURE_IDS = frozenset(
    """
    apf_missing_lane apf_extra_lane apf_wrong_distribution_scope
    apf_missing_authority_separation apf_producer_only_not_applicable
    apf_unversioned_reference apf_inline_reference_copy
    apf_absent_permitted_consumers apf_absent_publication_restriction
    apf_absent_path_restriction apf_absent_data_restriction
    apf_stale_pack_identity apf_expired_currency apf_cross_lane_compensation
    apf_candidate_self_acceptance apf_actor_alias
    apf_requirement_author_is_producer apf_review_subject_mismatch
    apf_owner_subject_mismatch apf_content_hash_mismatch
    apf_coordinated_contract_pack_replacement apf_consumer_widening
    apf_contradictory_distribution apf_effective_expiry_inversion
    apf_duplicate_reference_id apf_aliased_reference_id
    apf_swapped_reference_kind apf_foreign_valid_reference
    apf_pending_reference apf_dangling_lane_reference
    apf_swapped_lane_reference apf_missing_fixture apf_extra_fixture
    apf_duplicate_fixture_id apf_swapped_fixture_attack_class
    apf_missing_obligation apf_extra_obligation apf_duplicate_obligation_id
    apf_swapped_obligation_lane apf_generic_obligation_prose
    apf_unable_to_grade_pass apf_partial_pass apf_failed_proof_pass
    apf_acceptance_before_review apf_accepted_candidate_state
    apf_schema_identity_swap apf_pack_object_id_alias
    apf_producer_change_stales_requirement
    apf_reference_activation_change_stales apf_tested_object_no_op
    apf_degenerate_fallback apf_claim_escalation
    """.split()
)
EXPECTED_OBLIGATION_IDS = {
    "topology": frozenset(
        """
        topology.persistence_construction_and_object topology.w2_convention
        topology.filtration_metric_order topology.threshold_truncation
        topology.landmark_rule topology.coefficient_field
        topology.homology_dimensions_and_essential_classes
        topology.benchmark_known_cases topology.scaling_and_direction
        topology.subject_topological_object_identity
        topology.interpretation_topology_geometry_association_causality
        """.split()
    ),
    "stochastic_null": frozenset(
        """
        stochastic_null.null_hypothesis_and_operation
        stochastic_null.exchangeability_conditioning
        stochastic_null.markov_order_and_strata stochastic_null.sampling_unit_and_b
        stochastic_null.rng_and_seed stochastic_null.denominator_and_p_value_formula
        stochastic_null.tested_object_mutation
        stochastic_null.independent_no_op_preflight
        stochastic_null.checkpoint_resume_equivalence
        stochastic_null.multiplicity_family
        stochastic_null.diagnostic_inferential_separation
        """.split()
    ),
    "statistical_panel": frozenset(
        """
        statistical_panel.estimand statistical_panel.target_population
        statistical_panel.eligibility_and_denominator
        statistical_panel.clustering_and_dependence
        statistical_panel.missingness_and_imputation
        statistical_panel.weights_and_trimming
        statistical_panel.variance_and_uncertainty statistical_panel.multiplicity
        statistical_panel.sensitivity statistical_panel.formula_and_software_procedure
        statistical_panel.boundary_sparse_separation_cases
        statistical_panel.descriptive_associational_predictive_causal_limits
        """.split()
    ),
    "representation": frozenset(
        """
        representation.fit_transform_authority
        representation.frozen_model_loadings_scaler_labels
        representation.training_population representation.state_recoding
        representation.windows_dimensions_and_vintage representation.fingerprint_hash
        representation.transform_only
        representation.comparability_across_waves_cohorts_subgroups
        representation.prohibited_refit_and_fallback
        representation.uncertainty_and_sensitivity
        """.split()
    ),
    "output_provenance": frozenset(
        """
        output_provenance.immutable_object_and_input_ids_hashes
        output_provenance.code_and_environment
        output_provenance.parameters_seeds_and_sample_restrictions
        output_provenance.roots_and_date_suffix output_provenance.no_overwrite
        output_provenance.schema_cache_lineage_and_regenerability
        output_provenance.consumer_required_comparison_fields
        output_provenance.scoped_supersession_and_retention
        output_provenance.exact_accepted_bytes_validation
        output_provenance.vault_and_claim_routing_authorization
        output_provenance.consumer_publication_path_data_boundaries
        """.split()
    ),
    "paper_claim": frozenset(
        """
        paper_claim.exact_accepted_result_and_evidence_ids_hashes
        paper_claim.governing_decision_rule_and_outcome paper_claim.proposed_wording
        paper_claim.claim_type_and_strength paper_claim.population_and_domain_scope
        paper_claim.uncertainty paper_claim.limitations_and_disclosure
        paper_claim.negative_and_partial_restrictions
        paper_claim.independent_claim_review
        paper_claim.stephen_attributed_promotion_decision
        paper_claim.no_causal_escalation paper_claim.no_novelty_escalation
        paper_claim.no_generality_escalation
        paper_claim.result_acceptance_and_claim_promotion_separation
        """.split()
    ),
}


class CandidatePackError(ValueError):
    """A relational or external-authority violation outside JSON Schema."""


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _schema_registry() -> SchemaRegistry:
    return SchemaRegistry(SCHEMAS)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _git_blob_id(data: bytes) -> str:
    return subprocess.check_output(["git", "hash-object", "--stdin"], input=data).decode().strip()


def _git_blob_id_without_filters(data: bytes) -> str:
    return subprocess.check_output(["git", "hash-object", "--no-filters", "--stdin"], input=data).decode().strip()


def _raw_pack_bytes(pack: dict, *, leading_comment: str | None = None, reverse_top_level: bool = False) -> bytes:
    value = dict(reversed(list(pack.items()))) if reverse_top_level else pack
    rendered = yaml.safe_dump(value, sort_keys=False, allow_unicode=True, width=4096)
    if leading_comment is not None:
        rendered = f"# {leading_comment}\n{rendered}"
    raw = rendered.encode("utf-8")
    assert b"\r" not in raw
    assert raw.endswith(b"\n")
    return raw


def _parse_candidate_pack_bytes(raw_candidate_pack_bytes: bytes) -> dict:
    if b"\r" in raw_candidate_pack_bytes or not raw_candidate_pack_bytes.endswith(b"\n"):
        raise CandidatePackError("candidate bytes must be exact UTF-8/LF with terminal LF")
    try:
        decoded = raw_candidate_pack_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CandidatePackError("candidate bytes must be exact UTF-8/LF with terminal LF") from exc
    parsed = yaml.safe_load(decoded)
    if not isinstance(parsed, dict):
        raise CandidatePackError("candidate bytes must parse to one pack object")
    _schema_registry().validate(PACK_SCHEMA_ID, parsed)
    return parsed


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise CandidatePackError("timestamp must include timezone")
    return parsed


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
    assert seen_objects > 20


@lru_cache(maxsize=1)
def _external_schema_artifact() -> tuple[dict, str, str]:
    schema_document = _load_json(CONTRACT_SCHEMA_PATH)
    schema_bytes = CONTRACT_SCHEMA_PATH.read_bytes()
    Draft202012Validator.check_schema(schema_document)
    return schema_document, _git_blob_id(schema_bytes), hashlib.sha256(schema_bytes).hexdigest()


@lru_cache(maxsize=1)
def _external_root_validator() -> Draft202012Validator:
    return Draft202012Validator(_external_schema_artifact()[0], format_checker=Draft202012Validator.FORMAT_CHECKER)


def _external_schema_catalogue(contract: dict) -> tuple[dict, dict[str, dict]]:
    catalogue = contract["required_pack_contract"]["external_record_schema_catalogue"]
    schema_document, schema_blob, schema_sha256 = _external_schema_artifact()
    rows = _rows_by_id(catalogue["exact_schema_rows"], "record_class", "external schema")
    if set(rows) != set(EXPECTED_EXTERNAL_SCHEMA_IDS):
        raise CandidatePackError("external record schema class closure differs")
    if catalogue["exact_schema_count"] != len(rows):
        raise CandidatePackError("external record schema count differs")
    for record_class, row in rows.items():
        if row["record_type"] != record_class:
            raise CandidatePackError("external record class/type binding differs")
        if row["schema_id"] != EXPECTED_EXTERNAL_SCHEMA_IDS[record_class] or row["schema_version"] != "1.0.0":
            raise CandidatePackError("external record schema identity differs")
        if row["repository_path"] != catalogue["schema_document_repository_path"]:
            raise CandidatePackError("external record schema path differs")
        if row["schema_git_blob"] != schema_blob or row["schema_canonical_sha256"] != schema_sha256:
            raise CandidatePackError("external record schema content identity differs")
        definition_name = row["schema_json_pointer"].removeprefix("#/$defs/")
        external_schema = schema_document["$defs"].get(definition_name)
        if external_schema is None:
            raise CandidatePackError("external record schema pointer is unresolved")
        if (
            external_schema.get("$id") != row["schema_id"]
            or external_schema.get("x-schema-version") != row["schema_version"]
        ):
            raise CandidatePackError("external record schema pointer identity differs")
    return schema_document, rows


def _validate_external_record(contract: dict, record: dict, record_class: str) -> None:
    schema_document, rows = _external_schema_catalogue(contract)
    row = rows[record_class]
    definition_name = row["schema_json_pointer"].removeprefix("#/$defs/")
    root_validator = _external_root_validator()
    errors = sorted(
        root_validator.evolve(schema=schema_document["$defs"][definition_name]).iter_errors(record),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        message = "; ".join(
            f"{'.'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}" for error in errors
        )
        raise CandidatePackError(f"invalid {record_class} record: {message}")


def _rows_by_id(rows: list[dict], id_field: str, label: str) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for row in rows:
        row_id = row[id_field]
        if row_id in indexed:
            raise CandidatePackError(f"duplicate {label} id: {row_id}")
        indexed[row_id] = row
    return indexed


def _derived_pending_reference_ids(contract: dict) -> set[str]:
    references = contract["required_pack_contract"]["references"]
    rows = references["exact_reference_rows"]
    acceptance_active_states = set(references["acceptance_active_states"])
    return {
        row["reference_id"]
        for row in rows
        if row["activation_state"] not in acceptance_active_states or not row["pack_acceptance_eligible"]
    }


def _validate_pending_reference_relation(contract: dict) -> None:
    observed = contract["required_pack_contract"]["references"]["current_pending_reference_ids"]
    expected = _derived_pending_reference_ids(contract)
    if len(observed) != len(set(observed)) or set(observed) != expected:
        raise CandidatePackError("current pending reference relation differs from derived exact set")


def _validate_lane_enforcer_relation(pack: dict, observed_references: dict[str, dict]) -> None:
    for lane_id, lane in pack["lanes"].items():
        governing = set(lane["governing_reference_ids"])
        for obligation in lane["obligation_rows"]:
            for reference_id in obligation["enforcing_reference_ids"]:
                if reference_id not in governing:
                    raise CandidatePackError("obligation enforcer is omitted from lane governing relation")
                reference = observed_references.get(reference_id)
                if reference is None or lane_id not in reference["allowed_lane_ids"]:
                    raise CandidatePackError("obligation enforcer is foreign or not permitted for lane")


def _expanded_obligation(row: dict, profile: dict) -> dict:
    return {
        "obligation_id": row["obligation_id"],
        "row_profile_id": profile["row_profile_id"],
        "source_authority_id": profile["source_authority_id"],
        "source_sections": deepcopy(row["source_sections"]),
        "assertion_classes": deepcopy(row["assertion_classes"]),
        "enforcing_reference_ids": deepcopy(row["enforcing_reference_ids"]),
        "review_question_id": row["review_question_id"],
        "evidence_output_id": row["evidence_output_id"],
    }


def _proposed_pack(contract: dict | None = None) -> dict:
    contract = deepcopy(contract or _load_yaml(CONTRACT_PATH))
    required = contract["required_pack_contract"]
    reference_rows = required["references"]["exact_reference_rows"]
    contract_references = [deepcopy(row) for row in reference_rows if row["reference_kind"] == "contract"]
    skill_references = [deepcopy(row) for row in reference_rows if row["reference_kind"] == "skill"]
    profile = required["obligation_row_profile"]
    lanes = {}
    for lane_id, lane_contract in required["lanes"].items():
        lanes[lane_id] = {
            "lane_id": lane_id,
            "governing_reference_ids": deepcopy(lane_contract["exact_governing_reference_ids"]),
            "obligation_rows": [_expanded_obligation(row, profile) for row in lane_contract["required_obligations"]],
            "fixture_ids": deepcopy(lane_contract["exact_fixture_ids"]),
            "prospective_schema_only": True,
            "scientific_review_status": "not_performed_by_pack_schema",
            "failure_consequence": "blocked_no_cross_lane_compensation",
            "cross_lane_compensation": "prohibited",
        }
    return {
        "schema_id": PACK_SCHEMA_ID,
        "schema_version": "1.0.0",
        "pack_id": "TDL_private",
        "assurance_pack_id": ASSURANCE_PACK_ID,
        "assurance_pack_revision": 1,
        "canonical_repository_path": ".research-system/packs/tdl-private-assurance.yaml",
        "distribution_scope": "TDL_private",
        "candidate_state": "proposed",
        "producer_actor_id": ACT_PRODUCER,
        "upstream_contract_reference": deepcopy(EXTERNAL_CONTRACT_REFERENCE),
        "schema_reference": deepcopy(EXTERNAL_SCHEMA_REFERENCE),
        "assurance_requirement_reference": {
            "assurance_requirement_id": ASSURANCE_REQUIREMENT_ID,
            "revision": 1,
            "canonical_sha256": "5" * 64,
            "acceptance_record_id": REQUIREMENT_RECORD_ID,
            "acceptance_record_sha256": "6" * 64,
            "prospective_producer_actor_id": ACT_PRODUCER,
        },
        "source_authority": {
            "accepted_plan_revision": contract["source_authority"]["accepted_plan_revision"],
            "governing_sources": deepcopy(contract["source_authority"]["governing_sources"]),
        },
        "references": {
            "contract_references": contract_references,
            "skill_references": skill_references,
        },
        "task_applicability_policy": {
            "pack_obligations": "all_required",
            "task_not_applicable_location": "external_accepted_assurance_requirement",
            "producer_only_confirmation": "prohibited",
            "minimum_independence_grade": "I2",
            "unable_to_grade_may_pass": False,
            "partial_may_pass": False,
            "failed_proof_may_pass": False,
        },
        "distribution_controls": {
            "permitted_consumers": deepcopy(required["distribution"]["exact_permitted_consumers"]),
            "public_template_export": "prohibited",
            "publication_boundary": {
                "public_template_use": "prohibited",
                "manuscript_use": "requires_separately_accepted_result_and_claim_decision",
                "public_excerpt": "prohibited_without_template_safe_derivative_review",
                "claim_promotion": "requires_stephen_attributed_p005_decision",
            },
            "path_restrictions": {
                "repository_namespace": "tdl_private_only",
                "public_repository_paths": "prohibited",
                "public_template_paths": "prohibited",
                "private_path_disclosure": "opaque_content_addressed_references_only",
            },
            "data_restrictions": {
                "raw_restricted_data": "prohibited",
                "minimized_excerpts": "separately_authorized_only",
                "restricted_references": "opaque_content_addressed_only",
                "secrets_env_transcripts_hidden_reasoning": "prohibited",
            },
        },
        "currency": {
            "authored_at": "2026-07-18T09:00:00Z",
            "effective_at": "2026-07-18T09:15:00Z",
            "expires_at": "2027-07-18T09:00:00Z",
            "currency_triggers": [
                "upstream_contract_identity_changed",
                "schema_identity_changed",
                "reference_identity_or_activation_changed",
                "assurance_requirement_or_producer_relationship_changed",
                "distribution_or_consumer_policy_changed",
            ],
            "retention_class": "durable_governance_record",
            "stale_identity_behavior": "block_consumption_and_require_superseding_revision",
        },
        "lanes": lanes,
        "required_fixtures": deepcopy(required["fixtures"]["exact_fixture_rows"]),
        "limitations": [
            "prospective_pack_no_result_or_claim_review",
            "schema_shape_does_not_establish_scientific_validity",
            "candidate_cannot_assert_review_or_owner_acceptance",
            "pending_reference_blocks_owner_acceptance",
        ],
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


def _eligible_contract() -> dict:
    contract = _load_yaml(CONTRACT_PATH)
    replacement_digits = iter("789a")
    for row in contract["required_pack_contract"]["references"]["exact_reference_rows"]:
        if row["reference_kind"] == "contract" and not row["pack_acceptance_eligible"]:
            digit = next(replacement_digits)
            row["activation_state"] = "active"
            row["pack_acceptance_eligible"] = True
            row["git_blob"] = digit * 40
            row["canonical_sha256"] = digit * 64
    contract["required_pack_contract"]["references"]["current_pending_reference_ids"] = []
    return contract


def _validate_proposed_pack(
    pack: dict,
    *,
    contract: dict | None = None,
    accepted_contract_oracle_sha256: str | None = None,
    require_active_references: bool = False,
    registered_pack_ids: frozenset[str] = frozenset({ASSURANCE_PACK_ID}),
    as_of: datetime = AS_OF,
) -> None:
    contract = contract or _load_yaml(CONTRACT_PATH)
    accepted_contract_oracle_sha256 = accepted_contract_oracle_sha256 or _canonical_sha256(_load_yaml(CONTRACT_PATH))
    _schema_registry().validate(PACK_SCHEMA_ID, pack)
    _validate_pending_reference_relation(contract)
    _external_schema_catalogue(contract)
    if _canonical_sha256(contract) != accepted_contract_oracle_sha256:
        raise CandidatePackError("upstream contract oracle identity mismatch")
    if pack["upstream_contract_reference"] != EXTERNAL_CONTRACT_REFERENCE:
        raise CandidatePackError("stale upstream contract subject")
    if pack["schema_reference"] != EXTERNAL_SCHEMA_REFERENCE:
        raise CandidatePackError("stale pack schema subject")
    if pack["assurance_pack_id"] not in registered_pack_ids:
        raise CandidatePackError("assurance_pack_id is not registered by W1 authority")
    if pack["assurance_requirement_reference"]["prospective_producer_actor_id"] != pack["producer_actor_id"]:
        raise CandidatePackError("prospective producer relationship is stale")
    expected_source_authority = {
        "accepted_plan_revision": contract["source_authority"]["accepted_plan_revision"],
        "governing_sources": contract["source_authority"]["governing_sources"],
    }
    if pack["source_authority"] != expected_source_authority:
        raise CandidatePackError("stale or incomplete source authority")

    required = contract["required_pack_contract"]
    expected_references = _rows_by_id(required["references"]["exact_reference_rows"], "reference_id", "reference")
    observed_reference_rows = pack["references"]["contract_references"] + pack["references"]["skill_references"]
    observed_references = _rows_by_id(observed_reference_rows, "reference_id", "reference")
    if observed_references != expected_references:
        raise CandidatePackError("reference rows must equal the exact upstream set")
    if set(observed_references) != EXPECTED_REFERENCE_IDS:
        raise CandidatePackError("reference ID closure differs from the independent fixture")
    if require_active_references and _derived_pending_reference_ids(contract):
        raise CandidatePackError("pending reference blocks pack acceptance")

    if set(pack["lanes"]) != LANES:
        raise CandidatePackError("exact six-lane closure required")
    expected_fixtures = _rows_by_id(required["fixtures"]["exact_fixture_rows"], "fixture_id", "fixture")
    observed_fixtures = _rows_by_id(pack["required_fixtures"], "fixture_id", "fixture")
    if observed_fixtures != expected_fixtures:
        raise CandidatePackError("fixture rows must equal the exact upstream set")
    if set(observed_fixtures) != EXPECTED_FIXTURE_IDS:
        raise CandidatePackError("fixture ID closure differs from the independent fixture")

    profile = required["obligation_row_profile"]
    for lane_id, lane_contract in required["lanes"].items():
        lane = pack["lanes"][lane_id]
        if lane["lane_id"] != lane_id:
            raise CandidatePackError("lane key and lane_id must match")
        if set(lane["governing_reference_ids"]) != set(lane_contract["exact_governing_reference_ids"]) or len(
            lane["governing_reference_ids"]
        ) != len(lane_contract["exact_governing_reference_ids"]):
            raise CandidatePackError("lane reference relation differs from the exact upstream row")
        for reference_id in lane["governing_reference_ids"]:
            reference = observed_references.get(reference_id)
            if reference is None:
                raise CandidatePackError("dangling lane reference")
            if lane_id not in reference["allowed_lane_ids"]:
                raise CandidatePackError("foreign-valid reference is not allowed for lane")
        expected_obligations = _rows_by_id(
            [_expanded_obligation(row, profile) for row in lane_contract["required_obligations"]],
            "obligation_id",
            "obligation",
        )
        observed_obligations = _rows_by_id(lane["obligation_rows"], "obligation_id", "obligation")
        if observed_obligations != expected_obligations:
            raise CandidatePackError("obligation rows must equal the exact upstream lane set")
        if set(observed_obligations) != EXPECTED_OBLIGATION_IDS[lane_id]:
            raise CandidatePackError("obligation closure differs from the independent W5 fixture")
        if set(lane["fixture_ids"]) != set(lane_contract["exact_fixture_ids"]) or len(lane["fixture_ids"]) != len(
            lane_contract["exact_fixture_ids"]
        ):
            raise CandidatePackError("lane fixture relation differs from the exact upstream row")
        if not set(lane["fixture_ids"]) <= set(observed_fixtures):
            raise CandidatePackError("dangling lane fixture")
    _validate_lane_enforcer_relation(pack, observed_references)

    authored_at = _parse_datetime(pack["currency"]["authored_at"])
    effective_at = _parse_datetime(pack["currency"]["effective_at"])
    expires_at = _parse_datetime(pack["currency"]["expires_at"])
    if not authored_at <= effective_at < expires_at:
        raise CandidatePackError("candidate currency time order is invalid")
    if expires_at <= as_of:
        raise CandidatePackError("candidate currency expired")


def _pack_subject(raw_candidate_pack_bytes: bytes, *, expected_pack: dict | None = None) -> dict:
    pack = _parse_candidate_pack_bytes(raw_candidate_pack_bytes)
    if expected_pack is not None and pack != expected_pack:
        raise CandidatePackError("raw candidate bytes do not parse to the supplied candidate")
    return {
        "pack_id": pack["pack_id"],
        "assurance_pack_id": pack["assurance_pack_id"],
        "assurance_pack_revision": pack["assurance_pack_revision"],
        "canonical_repository_path": pack["canonical_repository_path"],
        "pack_git_blob": _git_blob_id(raw_candidate_pack_bytes),
        "pack_raw_sha256": hashlib.sha256(raw_candidate_pack_bytes).hexdigest(),
        "schema_id": pack["schema_reference"]["schema_id"],
        "schema_version": pack["schema_reference"]["schema_version"],
        "schema_repository_path": pack["schema_reference"]["repository_path"],
        "schema_git_blob": pack["schema_reference"]["git_blob"],
        "schema_canonical_sha256": pack["schema_reference"]["canonical_sha256"],
    }


def _rehash_record(record_store: dict[str, dict], hash_manifest: dict[str, str], record_id: str) -> None:
    hash_manifest[record_id] = _canonical_sha256(record_store[record_id])


def _actor_record(actor_id: str, canonical_name: str, *, actor_kind: str = "agent") -> dict:
    return {
        "record_type": "canonical_actor",
        "actor_id": actor_id,
        "actor_kind": actor_kind,
        "canonical_name": canonical_name,
        "status": "active",
    }


def _external_records(pack: dict) -> tuple[dict, bytes, dict[str, dict], dict[str, str]]:
    requirement_record = {
        "record_type": "accepted_assurance_requirement",
        "acceptance_record_id": REQUIREMENT_RECORD_ID,
        "assurance_requirement_id": ASSURANCE_REQUIREMENT_ID,
        "revision": 1,
        "subject_contract": deepcopy(EXTERNAL_CONTRACT_REFERENCE),
        "requirement_author_actor_id": ACT_REQUIREMENT_AUTHOR,
        "scope_reviewer_actor_id": ACT_SCOPE_REVIEWER,
        "acceptor_actor_id": ACT_OWNER,
        "prospective_producer_actor_id": ACT_PRODUCER,
        "minimum_independence_grade": "I2",
        "scope_relationship_record_id": SCOPE_RELATIONSHIP_ID,
        "outcome": "accepted",
        "acceptance_state": "active",
        "accepted_at": "2026-07-18T08:30:00Z",
    }
    requirement_hash = _canonical_sha256(requirement_record)
    pack["assurance_requirement_reference"]["acceptance_record_sha256"] = requirement_hash
    raw_candidate_pack_bytes = _raw_pack_bytes(pack)
    subject = _pack_subject(raw_candidate_pack_bytes, expected_pack=pack)
    scope_relationship = {
        "record_type": "producer_relationship_evidence",
        "relationship_record_id": SCOPE_RELATIONSHIP_ID,
        "relationship_context": "requirement_scope_review",
        "subject_actor_id": ACT_SCOPE_REVIEWER,
        "object_actor_id": ACT_PRODUCER,
        "grade": "I2",
        "status": "active",
        "effective_at": "2026-07-18T08:15:00Z",
        "expires_at": "2027-07-18T08:15:00Z",
    }
    review_relationship = {
        "record_type": "producer_relationship_evidence",
        "relationship_record_id": REVIEW_RELATIONSHIP_ID,
        "relationship_context": "pack_scientific_review",
        "subject_actor_id": ACT_SCIENTIFIC_REVIEWER,
        "object_actor_id": ACT_PRODUCER,
        "grade": "I2",
        "status": "active",
        "effective_at": "2026-07-18T09:20:00Z",
        "expires_at": "2027-07-18T09:30:00Z",
    }
    review_record = {
        "record_type": "independent_pack_review",
        "review_record_id": REVIEW_RECORD_ID,
        "subject": deepcopy(subject),
        "reviewer_actor_id": ACT_SCIENTIFIC_REVIEWER,
        "producer_actor_id": ACT_PRODUCER,
        "relationship_record_id": REVIEW_RELATIONSHIP_ID,
        "minimum_independence_grade": "I2",
        "verdict": "pass",
        "review_state": "completed",
        "reviewed_at": "2026-07-18T10:00:00Z",
    }
    review_hash = _canonical_sha256(review_record)
    owner_grant = {
        "record_type": "active_authority_grant",
        "authority_grant_id": OWNER_GRANT_ID,
        "actor_id": ACT_OWNER,
        "authority_class": "stephen_reserved_owner_acceptance",
        "subject_assurance_pack_id": ASSURANCE_PACK_ID,
        "grant_state": "active",
        "effective_at": "2026-07-18T07:00:00Z",
        "expires_at": "2027-07-18T07:00:00Z",
        "revoked": False,
    }
    owner_decision = {
        "record_type": "stephen_owner_acceptance",
        "owner_decision_id": OWNER_DECISION_ID,
        "subject": deepcopy(subject),
        "review_record_id": REVIEW_RECORD_ID,
        "review_record_sha256": review_hash,
        "acceptor_actor_id": ACT_OWNER,
        "authority_grant_id": OWNER_GRANT_ID,
        "outcome": "accepted",
        "decision_state": "active",
        "decided_at": "2026-07-18T11:00:00Z",
    }
    pack_registry = {
        "record_type": "registered_pack_object",
        "assurance_pack_id": ASSURANCE_PACK_ID,
        "id_kind": "assurance_pack",
        "revision": 1,
        "canonical_repository_path": ".research-system/packs/tdl-private-assurance.yaml",
        "registration_state": "active",
        "registered_at": "2026-07-18T08:45:00Z",
    }
    record_store = {
        ACT_CONTRACT_AUTHOR: _actor_record(ACT_CONTRACT_AUTHOR, "contract-author-agent"),
        ACT_PRODUCER: _actor_record(ACT_PRODUCER, "future-pack-producer-agent"),
        ACT_REQUIREMENT_AUTHOR: _actor_record(ACT_REQUIREMENT_AUTHOR, "requirement-author-agent"),
        ACT_SCOPE_REVIEWER: _actor_record(ACT_SCOPE_REVIEWER, "requirement-scope-reviewer-agent"),
        ACT_SCIENTIFIC_REVIEWER: _actor_record(ACT_SCIENTIFIC_REVIEWER, "pack-scientific-reviewer-agent"),
        ACT_OWNER: _actor_record(ACT_OWNER, "Stephen", actor_kind="human"),
        REQUIREMENT_RECORD_ID: requirement_record,
        SCOPE_RELATIONSHIP_ID: scope_relationship,
        REVIEW_RELATIONSHIP_ID: review_relationship,
        REVIEW_RECORD_ID: review_record,
        OWNER_GRANT_ID: owner_grant,
        OWNER_DECISION_ID: owner_decision,
        ASSURANCE_PACK_ID: pack_registry,
    }
    hash_manifest = {record_id: _canonical_sha256(record) for record_id, record in record_store.items()}
    return pack, raw_candidate_pack_bytes, record_store, hash_manifest


def _refresh_acceptance_chain(pack: dict, record_store: dict[str, dict], hash_manifest: dict[str, str]) -> bytes:
    _rehash_record(record_store, hash_manifest, REQUIREMENT_RECORD_ID)
    pack["assurance_requirement_reference"]["acceptance_record_sha256"] = hash_manifest[REQUIREMENT_RECORD_ID]
    raw_candidate_pack_bytes = _raw_pack_bytes(pack)
    subject = _pack_subject(raw_candidate_pack_bytes, expected_pack=pack)
    record_store[REVIEW_RECORD_ID]["subject"] = deepcopy(subject)
    _rehash_record(record_store, hash_manifest, REVIEW_RECORD_ID)
    record_store[OWNER_DECISION_ID]["subject"] = deepcopy(subject)
    record_store[OWNER_DECISION_ID]["review_record_sha256"] = hash_manifest[REVIEW_RECORD_ID]
    _rehash_record(record_store, hash_manifest, OWNER_DECISION_ID)
    return raw_candidate_pack_bytes


def _coordinate_all_external_hashes(pack: dict, record_store: dict[str, dict]) -> tuple[bytes, dict[str, str]]:
    hash_manifest = {record_id: _canonical_sha256(record) for record_id, record in record_store.items()}
    raw_candidate_pack_bytes = _refresh_acceptance_chain(pack, record_store, hash_manifest)
    return raw_candidate_pack_bytes, hash_manifest


def _eligible_acceptance_fixture() -> tuple[dict, str, dict, bytes, dict[str, dict], dict[str, str]]:
    contract = _eligible_contract()
    _schema_registry().validate(CONTRACT_SCHEMA_ID, contract)
    _validate_pending_reference_relation(contract)
    oracle_sha = _canonical_sha256(contract)
    pack, raw_candidate_pack_bytes, record_store, hash_manifest = _external_records(_proposed_pack(contract))
    return contract, oracle_sha, pack, raw_candidate_pack_bytes, record_store, hash_manifest


def _resolved_record(
    contract: dict,
    record_store: dict[str, dict],
    hash_manifest: dict[str, str],
    record_id: str,
    record_class: str,
) -> dict:
    if record_id not in record_store or record_id not in hash_manifest:
        raise CandidatePackError(f"missing external record: {record_id}")
    record = record_store[record_id]
    if _canonical_sha256(record) != hash_manifest[record_id]:
        raise CandidatePackError(f"external record hash mismatch: {record_id}")
    _validate_external_record(contract, record, record_class)
    identity_fields = {
        "canonical_actor": "actor_id",
        "producer_relationship_evidence": "relationship_record_id",
        "accepted_assurance_requirement": "acceptance_record_id",
        "independent_pack_review": "review_record_id",
        "stephen_owner_acceptance": "owner_decision_id",
        "active_authority_grant": "authority_grant_id",
        "registered_pack_object": "assurance_pack_id",
    }
    if record[identity_fields[record_class]] != record_id:
        raise CandidatePackError(f"external record key/body identity mismatch: {record_id}")
    return record


def _validate_external_acceptance(
    pack: dict,
    *,
    raw_candidate_pack_bytes: bytes,
    contract: dict,
    accepted_contract_oracle_sha256: str,
    record_store: dict[str, dict],
    hash_manifest: dict[str, str],
    review_record_id: str = REVIEW_RECORD_ID,
    owner_decision_id: str = OWNER_DECISION_ID,
    contract_author_actor_id: str = ACT_CONTRACT_AUTHOR,
    as_of: datetime = AS_OF,
) -> None:
    parsed_pack = _parse_candidate_pack_bytes(raw_candidate_pack_bytes)
    if parsed_pack != pack:
        raise CandidatePackError("raw candidate bytes do not parse to the supplied candidate")
    _validate_proposed_pack(
        parsed_pack,
        contract=contract,
        accepted_contract_oracle_sha256=accepted_contract_oracle_sha256,
        require_active_references=True,
        as_of=as_of,
    )
    requirement_id = pack["assurance_requirement_reference"]["acceptance_record_id"]
    requirement = _resolved_record(
        contract, record_store, hash_manifest, requirement_id, "accepted_assurance_requirement"
    )
    if hash_manifest[requirement_id] != pack["assurance_requirement_reference"]["acceptance_record_sha256"]:
        raise CandidatePackError("candidate requirement reference does not match external record")
    if requirement["subject_contract"] != EXTERNAL_CONTRACT_REFERENCE:
        raise CandidatePackError("assurance requirement binds a different upstream contract")
    if (
        requirement["assurance_requirement_id"] != pack["assurance_requirement_reference"]["assurance_requirement_id"]
        or requirement["revision"] != pack["assurance_requirement_reference"]["revision"]
    ):
        raise CandidatePackError("assurance requirement identity mismatch")
    if requirement["prospective_producer_actor_id"] != pack["producer_actor_id"]:
        raise CandidatePackError("accepted requirement names a different producer")
    scope_relationship = _resolved_record(
        contract,
        record_store,
        hash_manifest,
        requirement["scope_relationship_record_id"],
        "producer_relationship_evidence",
    )
    review = _resolved_record(contract, record_store, hash_manifest, review_record_id, "independent_pack_review")
    review_relationship = _resolved_record(
        contract,
        record_store,
        hash_manifest,
        review["relationship_record_id"],
        "producer_relationship_evidence",
    )
    owner = _resolved_record(contract, record_store, hash_manifest, owner_decision_id, "stephen_owner_acceptance")
    grant = _resolved_record(
        contract, record_store, hash_manifest, owner["authority_grant_id"], "active_authority_grant"
    )
    registered_object = _resolved_record(
        contract, record_store, hash_manifest, pack["assurance_pack_id"], "registered_pack_object"
    )
    subject = _pack_subject(raw_candidate_pack_bytes, expected_pack=pack)
    if review["subject"] != subject:
        raise CandidatePackError("independent review subject does not match loader-computed pack subject")
    if owner["subject"] != subject:
        raise CandidatePackError("owner decision subject does not match loader-computed pack subject")
    if (
        owner["review_record_id"] != review_record_id
        or owner["review_record_sha256"] != hash_manifest[review_record_id]
    ):
        raise CandidatePackError("owner decision does not bind the exact independent review")
    if review["verdict"] != "pass" or owner["outcome"] != "accepted":
        raise CandidatePackError("external review and owner acceptance are both required")
    if review["producer_actor_id"] != pack["producer_actor_id"]:
        raise CandidatePackError("independent review names a different producer")
    if requirement["minimum_independence_grade"] not in {"I2", "I3"}:
        raise CandidatePackError("requirement scope review is below I2")
    if review["minimum_independence_grade"] not in {"I2", "I3"}:
        raise CandidatePackError("pack review is below I2")
    if (
        scope_relationship["relationship_context"] != "requirement_scope_review"
        or scope_relationship["subject_actor_id"] != requirement["scope_reviewer_actor_id"]
        or scope_relationship["object_actor_id"] != pack["producer_actor_id"]
        or scope_relationship["grade"] != requirement["minimum_independence_grade"]
    ):
        raise CandidatePackError("scope relationship does not bind reviewer and producer")
    if (
        review_relationship["relationship_context"] != "pack_scientific_review"
        or review_relationship["subject_actor_id"] != review["reviewer_actor_id"]
        or review_relationship["object_actor_id"] != pack["producer_actor_id"]
    ):
        raise CandidatePackError("review relationship does not bind reviewer and producer")
    if review_relationship["grade"] != review["minimum_independence_grade"]:
        raise CandidatePackError("review relationship grade mismatch")
    actor_ids = {
        contract_author_actor_id,
        requirement["requirement_author_actor_id"],
        requirement["scope_reviewer_actor_id"],
        pack["producer_actor_id"],
        review["reviewer_actor_id"],
        owner["acceptor_actor_id"],
    }
    if len(actor_ids) != 6:
        raise CandidatePackError("authorship, production, review, and acceptance must be distinct")
    if requirement["acceptor_actor_id"] != owner["acceptor_actor_id"]:
        raise CandidatePackError("accepted requirement lacks the canonical Stephen acceptor")
    if requirement["acceptor_actor_id"] == pack["producer_actor_id"]:
        raise CandidatePackError("requirement acceptor must be independent of producer")
    for actor_id in actor_ids:
        _resolved_record(contract, record_store, hash_manifest, actor_id, "canonical_actor")
    owner_actor = _resolved_record(contract, record_store, hash_manifest, owner["acceptor_actor_id"], "canonical_actor")
    if owner_actor["actor_kind"] != "human" or owner_actor["canonical_name"] != "Stephen":
        raise CandidatePackError("owner acceptance lacks the canonical Stephen actor")
    if (
        grant["actor_id"] != owner["acceptor_actor_id"]
        or grant["subject_assurance_pack_id"] != pack["assurance_pack_id"]
    ):
        raise CandidatePackError("owner acceptance lacks the canonical Stephen authority grant")
    if (
        registered_object["assurance_pack_id"] != pack["assurance_pack_id"]
        or registered_object["revision"] != pack["assurance_pack_revision"]
        or registered_object["canonical_repository_path"] != pack["canonical_repository_path"]
    ):
        raise CandidatePackError("assurance pack object registration mismatch")
    requirement_accepted_at = _parse_datetime(requirement["accepted_at"])
    registered_at = _parse_datetime(registered_object["registered_at"])
    authored_at = _parse_datetime(pack["currency"]["authored_at"])
    effective_at = _parse_datetime(pack["currency"]["effective_at"])
    reviewed_at = _parse_datetime(review["reviewed_at"])
    decided_at = _parse_datetime(owner["decided_at"])
    if not requirement_accepted_at < authored_at < reviewed_at < decided_at <= as_of:
        raise CandidatePackError(
            "temporal order must be requirement accepted, candidate authored, independently reviewed, owner accepted"
        )
    if not requirement_accepted_at < registered_at <= authored_at <= effective_at < reviewed_at:
        raise CandidatePackError("pack registration and candidate effective-time order is invalid")
    for relationship, action_time in (
        (scope_relationship, requirement_accepted_at),
        (review_relationship, reviewed_at),
    ):
        if (
            not _parse_datetime(relationship["effective_at"])
            <= action_time
            <= as_of
            < _parse_datetime(relationship["expires_at"])
        ):
            raise CandidatePackError("relationship evidence is not current")
    if not _parse_datetime(grant["effective_at"]) <= decided_at <= as_of < _parse_datetime(grant["expires_at"]):
        raise CandidatePackError("owner authority grant is not current")


def test_upstream_contract_is_strict_pending_and_identity_separated():
    registry = _schema_registry()
    contract = _load_yaml(CONTRACT_PATH)
    registry.validate(CONTRACT_SCHEMA_ID, contract)
    assert registry.contains(PACK_SCHEMA_ID)
    assert registry.contains(CONTRACT_SCHEMA_ID)
    assert not registry.contains(LEGACY_GENERIC_PACK_SCHEMA_ID)
    assert contract["status"] == "pending_independent_re_review"
    assert contract["contract_revision"] == 3
    assert contract["review_gate"]["current_disposition"] == (
        "stop_for_fresh_independent_re_review_and_stephen_acceptance"
    )
    assert contract["remediation_review"]["verdict"] == "rework_required"
    assert contract["remediation_review"]["subject_commit"] == "d722664f54a55c59466a9923ac5706c7db010081"
    assert contract["remediation_review"]["report_git_blob"] == "9347c80afeb375d68e6c7e161d65c8ec3afea8fb"
    assert contract["proposed_pack_identity"]["pack_id"] == "TDL_private"
    assert contract["proposed_pack_identity"]["pack_id_semantics"] == ("accepted_domain_pack_family_name")
    assert contract["proposed_pack_identity"]["assurance_pack_object"]["id_prefix"] == "asp"
    assert contract["proposed_pack_identity"]["schema_profile"] == {
        "schema_id": PACK_SCHEMA_ID,
        "schema_version": "1.0.0",
        "repository_path": ".research-system/schemas/assurance/assurance-pack.schema.json",
        "content_identity_location": "external_contract_review_and_owner_acceptance_records",
    }
    semantic_interface = contract["required_pack_contract"]["public_semantic_interface"]
    assert semantic_interface["required_callable"] == (
        "research_system.assurance.validate_tdl_private_pack_for_acceptance"
    )
    assert semantic_interface["implementation_status"].startswith("blocking_future_dependency")
    assert (
        contract["required_pack_contract"]["external_lifecycle"]["candidate_may_assert_review_or_acceptance"] is False
    )
    assert (
        contract["required_pack_contract"]["external_acceptance_evidence"]["candidate_may_supply_record_bodies"]
        is False
    )
    pending = {
        row["reference_id"]
        for row in contract["required_pack_contract"]["references"]["exact_reference_rows"]
        if not row["pack_acceptance_eligible"]
    }
    assert pending == {
        "contract/topology-invariants/null-operation-changes-ph-input",
        "contract/stochastic-tests/markov-order-provenance",
    }
    assert set(contract["required_pack_contract"]["references"]["current_pending_reference_ids"]) == pending
    _validate_pending_reference_relation(contract)
    _external_schema_catalogue(contract)
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
    for reference in contract["required_pack_contract"]["references"]["exact_reference_rows"]:
        blob = subprocess.check_output(
            ["git", "rev-parse", f"HEAD:{reference['repository_path']}"], cwd=ROOT, text=True
        ).strip()
        assert blob == reference["git_blob"]
        blob_bytes = subprocess.check_output(["git", "cat-file", "blob", blob], cwd=ROOT)
        assert hashlib.sha256(blob_bytes).hexdigest() == reference["canonical_sha256"]
    bound_names = set(contract["validation_bindings"]["durable_test_functions"])
    assert bound_names <= set(globals())
    assert set(contract["validation_bindings"]["task_local_unbound_test_functions"]) <= set(globals())
    assert not bound_names & set(contract["validation_bindings"]["task_local_unbound_test_functions"])
    _assert_all_object_schemas_are_closed(_load_json(SCHEMAS / "assurance" / "assurance-pack.schema.json"))
    _assert_all_object_schemas_are_closed(
        _load_json(SCHEMAS / "contracts" / "wp6-3-tdl-private-assurance-pack.schema.json")
    )


def test_scope_stop_future_pack_is_absent_in_remediation_task():
    assert not PACK_PATH.exists(), "the future pack remains prohibited in this remediation task"
    tracked = subprocess.run(
        ["git", "cat-file", "-e", "HEAD:.research-system/packs/tdl-private-assurance.yaml"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    assert tracked.returncode != 0


def test_external_record_schema_catalogue_rejects_missing_alias_swap_and_stale_content():
    missing = _load_yaml(CONTRACT_PATH)
    missing["required_pack_contract"]["external_record_schema_catalogue"]["exact_schema_rows"].pop()
    with pytest.raises(CandidatePackError, match="schema class closure"):
        _external_schema_catalogue(missing)

    aliased = _load_yaml(CONTRACT_PATH)
    aliased["required_pack_contract"]["external_record_schema_catalogue"]["exact_schema_rows"][0]["schema_id"] = (
        "ars://assurance/records/actor-alias/1.0"
    )
    with pytest.raises(CandidatePackError, match="schema identity"):
        _external_schema_catalogue(aliased)

    swapped = _load_yaml(CONTRACT_PATH)
    rows = swapped["required_pack_contract"]["external_record_schema_catalogue"]["exact_schema_rows"]
    rows[0]["schema_json_pointer"], rows[1]["schema_json_pointer"] = (
        rows[1]["schema_json_pointer"],
        rows[0]["schema_json_pointer"],
    )
    with pytest.raises(CandidatePackError, match="pointer identity"):
        _external_schema_catalogue(swapped)

    stale_content = _load_yaml(CONTRACT_PATH)
    stale_content["required_pack_contract"]["external_record_schema_catalogue"]["exact_schema_rows"][0][
        "schema_git_blob"
    ] = "f" * 40
    with pytest.raises(CandidatePackError, match="content identity"):
        _external_schema_catalogue(stale_content)


def test_candidate_schema_is_proposed_only_and_has_no_acceptance_surface():
    pack = _proposed_pack()
    _validate_proposed_pack(pack)
    assert pack["candidate_state"] == "proposed"
    forbidden = {
        "accepted",
        "review_record_hash",
        "acceptance_decision_hash",
        "acceptor_actor_id",
        "scientific_reviewer_actor_id",
        "pack_content_sha256",
    }
    assert not forbidden & set(pack)

    self_accepted = deepcopy(pack)
    self_accepted["candidate_state"] = "accepted"
    with pytest.raises(SchemaError, match="candidate_state"):
        _validate_proposed_pack(self_accepted)

    self_review = deepcopy(pack)
    self_review["review_record_hash"] = "f" * 64
    with pytest.raises(SchemaError, match="review_record_hash"):
        _validate_proposed_pack(self_review)

    producer_only_na = deepcopy(pack)
    producer_only_na["lanes"]["topology"]["not_applicable"] = {
        "author_actor_id": ACT_PRODUCER,
        "confirming_actor_id": ACT_PRODUCER,
    }
    with pytest.raises(SchemaError, match="not_applicable"):
        _validate_proposed_pack(producer_only_na)


def test_external_acceptance_requires_independent_exact_subject_records():
    contract, oracle_sha, pack, raw_candidate_pack_bytes, record_store, hash_manifest = _eligible_acceptance_fixture()
    _validate_external_acceptance(
        pack,
        raw_candidate_pack_bytes=raw_candidate_pack_bytes,
        contract=contract,
        accepted_contract_oracle_sha256=oracle_sha,
        record_store=record_store,
        hash_manifest=hash_manifest,
    )

    same_author_pack = deepcopy(pack)
    same_author = deepcopy(record_store)
    same_author[REQUIREMENT_RECORD_ID]["requirement_author_actor_id"] = ACT_PRODUCER
    same_author_raw, same_author_hashes = _coordinate_all_external_hashes(same_author_pack, same_author)
    with pytest.raises(CandidatePackError, match="must be distinct"):
        _validate_external_acceptance(
            same_author_pack,
            raw_candidate_pack_bytes=same_author_raw,
            contract=contract,
            accepted_contract_oracle_sha256=oracle_sha,
            record_store=same_author,
            hash_manifest=same_author_hashes,
        )

    wrong_review_subject = deepcopy(record_store)
    wrong_review_hashes = deepcopy(hash_manifest)
    wrong_review_subject[REVIEW_RECORD_ID]["subject"]["pack_raw_sha256"] = "f" * 64
    _rehash_record(wrong_review_subject, wrong_review_hashes, REVIEW_RECORD_ID)
    wrong_review_subject[OWNER_DECISION_ID]["review_record_sha256"] = wrong_review_hashes[REVIEW_RECORD_ID]
    _rehash_record(wrong_review_subject, wrong_review_hashes, OWNER_DECISION_ID)
    with pytest.raises(CandidatePackError, match="review subject"):
        _validate_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            accepted_contract_oracle_sha256=oracle_sha,
            record_store=wrong_review_subject,
            hash_manifest=wrong_review_hashes,
        )

    wrong_owner_subject = deepcopy(record_store)
    wrong_owner_hashes = deepcopy(hash_manifest)
    wrong_owner_subject[OWNER_DECISION_ID]["subject"]["pack_git_blob"] = "f" * 40
    _rehash_record(wrong_owner_subject, wrong_owner_hashes, OWNER_DECISION_ID)
    with pytest.raises(CandidatePackError, match="owner decision subject"):
        _validate_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            accepted_contract_oracle_sha256=oracle_sha,
            record_store=wrong_owner_subject,
            hash_manifest=wrong_owner_hashes,
        )

    no_owner_grant = deepcopy(record_store)
    no_owner_grant.pop(OWNER_GRANT_ID)
    with pytest.raises(CandidatePackError, match="missing external record"):
        _validate_external_acceptance(
            pack,
            raw_candidate_pack_bytes=raw_candidate_pack_bytes,
            contract=contract,
            accepted_contract_oracle_sha256=oracle_sha,
            record_store=no_owner_grant,
            hash_manifest=hash_manifest,
        )

    actor_alias = deepcopy(pack)
    actor_alias["producer_actor_id"] = "act_future_pack_producer"
    actor_alias["assurance_requirement_reference"]["prospective_producer_actor_id"] = "act_future_pack_producer"
    with pytest.raises(SchemaError, match="producer_actor_id"):
        _validate_external_acceptance(
            actor_alias,
            raw_candidate_pack_bytes=_raw_pack_bytes(actor_alias),
            contract=contract,
            accepted_contract_oracle_sha256=oracle_sha,
            record_store=record_store,
            hash_manifest=hash_manifest,
        )


def test_hash_valid_external_record_semantic_mutations_are_rejected():
    mutations = {
        "rejected requirement": lambda records: records[REQUIREMENT_RECORD_ID].update(outcome="rejected"),
        "producer accepts requirement": lambda records: records[REQUIREMENT_RECORD_ID].update(
            acceptor_actor_id=ACT_PRODUCER
        ),
        "requirement accepted after owner": lambda records: records[REQUIREMENT_RECORD_ID].update(
            accepted_at="2026-07-18T11:30:00Z"
        ),
        "foreign requirement record type": lambda records: records[REQUIREMENT_RECORD_ID].update(
            record_type="foreign_requirement"
        ),
        "foreign owner record type": lambda records: records[OWNER_DECISION_ID].update(
            record_type="foreign_owner_decision"
        ),
        "wrong review producer": lambda records: records[REVIEW_RECORD_ID].update(
            producer_actor_id=ACT_REQUIREMENT_AUTHOR
        ),
        "role-like reviewer alias": lambda records: records[REVIEW_RECORD_ID].update(
            reviewer_actor_id="pack_scientific_reviewer"
        ),
        "inactive canonical actor": lambda records: records[ACT_SCIENTIFIC_REVIEWER].update(status="inactive"),
        "foreign authority class": lambda records: records[OWNER_GRANT_ID].update(
            authority_class="foreign_owner_authority"
        ),
        "relationship substitution": lambda records: records[REVIEW_RECORD_ID].update(
            relationship_record_id=SCOPE_RELATIONSHIP_ID
        ),
        "review before candidate": lambda records: records[REVIEW_RECORD_ID].update(reviewed_at="2026-07-18T08:50:00Z"),
    }
    for _label, mutate in mutations.items():
        contract, oracle_sha, pack, _, record_store, _ = _eligible_acceptance_fixture()
        mutate(record_store)
        raw_candidate_pack_bytes, hash_manifest = _coordinate_all_external_hashes(pack, record_store)
        with pytest.raises(CandidatePackError):
            _validate_external_acceptance(
                pack,
                raw_candidate_pack_bytes=raw_candidate_pack_bytes,
                contract=contract,
                accepted_contract_oracle_sha256=oracle_sha,
                record_store=record_store,
                hash_manifest=hash_manifest,
            )


def test_raw_candidate_bytes_define_portable_review_subject():
    contract, oracle_sha, pack, raw_candidate_pack_bytes, record_store, hash_manifest = _eligible_acceptance_fixture()
    baseline_subject = _pack_subject(raw_candidate_pack_bytes, expected_pack=pack)
    assert baseline_subject["pack_git_blob"] == _git_blob_id_without_filters(raw_candidate_pack_bytes)
    assert baseline_subject["pack_raw_sha256"] == hashlib.sha256(raw_candidate_pack_bytes).hexdigest()

    equivalent_bytes = [
        _raw_pack_bytes(pack, leading_comment="semantically equivalent but byte-distinct"),
        _raw_pack_bytes(pack, reverse_top_level=True),
        raw_candidate_pack_bytes.replace(b"schema_version:", b"\nschema_version:", 1),
    ]
    for candidate_bytes in equivalent_bytes:
        assert _parse_candidate_pack_bytes(candidate_bytes) == pack
        subject = _pack_subject(candidate_bytes, expected_pack=pack)
        assert subject != baseline_subject
        assert subject["pack_git_blob"] == _git_blob_id_without_filters(candidate_bytes)
        with pytest.raises(CandidatePackError, match="review subject"):
            _validate_external_acceptance(
                pack,
                raw_candidate_pack_bytes=candidate_bytes,
                contract=contract,
                accepted_contract_oracle_sha256=oracle_sha,
                record_store=record_store,
                hash_manifest=hash_manifest,
            )


def test_exact_reference_set_rejects_missing_extra_duplicate_alias_swap_and_foreign_rows():
    base = _proposed_pack()

    missing = deepcopy(base)
    missing["references"]["contract_references"].pop()
    with pytest.raises((SchemaError, CandidatePackError)):
        _validate_proposed_pack(missing)

    foreign = deepcopy(base)
    foreign_row = deepcopy(foreign["references"]["contract_references"][0])
    foreign_row["reference_id"] = "contract/foreign/shape-valid"
    foreign_row["repository_path"] = "contracts/foreign/shape-valid.yaml"
    foreign["references"]["contract_references"][0] = foreign_row
    with pytest.raises(CandidatePackError, match="exact upstream set"):
        _validate_proposed_pack(foreign)

    duplicate = deepcopy(base)
    duplicate_row = deepcopy(duplicate["references"]["contract_references"][0])
    duplicate_row["canonical_sha256"] = "f" * 64
    duplicate["references"]["contract_references"][1] = duplicate_row
    with pytest.raises(CandidatePackError, match="duplicate reference id"):
        _validate_proposed_pack(duplicate)

    alias = deepcopy(base)
    alias["references"]["skill_references"][0]["reference_id"] = "skill/validate_topology"
    with pytest.raises(CandidatePackError, match="exact upstream set"):
        _validate_proposed_pack(alias)

    kind_swap = deepcopy(base)
    contract_row = kind_swap["references"]["contract_references"].pop()
    skill_row = kind_swap["references"]["skill_references"].pop()
    kind_swap["references"]["contract_references"].append(skill_row)
    kind_swap["references"]["skill_references"].append(contract_row)
    with pytest.raises(SchemaError):
        _validate_proposed_pack(kind_swap)

    copied = deepcopy(base)
    copied["references"]["skill_references"][0]["inline_body"] = True
    with pytest.raises(SchemaError, match="inline_body"):
        _validate_proposed_pack(copied)


def test_lane_reference_relations_reject_dangling_swapped_and_pending_rows():
    contract = _load_yaml(CONTRACT_PATH)
    for lane_id in ("topology", "statistical_panel", "output_provenance"):
        assert (
            "skill/paper-claim-trace"
            in contract["required_pack_contract"]["lanes"][lane_id]["exact_governing_reference_ids"]
        )

    dangling = _proposed_pack()
    dangling["lanes"]["topology"]["governing_reference_ids"][0] = "skill/foreign-valid"
    with pytest.raises(CandidatePackError, match="lane reference relation"):
        _validate_proposed_pack(dangling)

    swapped = _proposed_pack()
    swapped["lanes"]["representation"]["governing_reference_ids"] = deepcopy(
        swapped["lanes"]["topology"]["governing_reference_ids"]
    )
    with pytest.raises(CandidatePackError, match="lane reference relation"):
        _validate_proposed_pack(swapped)

    current_pending = _proposed_pack()
    with pytest.raises(CandidatePackError, match="pending reference blocks"):
        _validate_proposed_pack(current_pending, require_active_references=True)

    eligible_contract = _eligible_contract()
    _schema_registry().validate(CONTRACT_SCHEMA_ID, eligible_contract)
    assert eligible_contract["required_pack_contract"]["references"]["current_pending_reference_ids"] == []
    _validate_pending_reference_relation(eligible_contract)
    eligible = _proposed_pack(eligible_contract)
    _validate_proposed_pack(
        eligible,
        contract=eligible_contract,
        accepted_contract_oracle_sha256=_canonical_sha256(eligible_contract),
        require_active_references=True,
    )

    missing_pending = _load_yaml(CONTRACT_PATH)
    missing_pending["required_pack_contract"]["references"]["current_pending_reference_ids"].pop()
    with pytest.raises(CandidatePackError, match="pending reference relation"):
        _validate_proposed_pack(
            _proposed_pack(missing_pending),
            contract=missing_pending,
            accepted_contract_oracle_sha256=_canonical_sha256(missing_pending),
        )

    stale_pending = _eligible_contract()
    stale_pending["required_pack_contract"]["references"]["current_pending_reference_ids"].append(
        "contract/topology-invariants/null-operation-changes-ph-input"
    )
    _schema_registry().validate(CONTRACT_SCHEMA_ID, stale_pending)
    with pytest.raises(CandidatePackError, match="pending reference relation"):
        _validate_proposed_pack(
            _proposed_pack(stale_pending),
            contract=stale_pending,
            accepted_contract_oracle_sha256=_canonical_sha256(stale_pending),
        )

    omitted_contract = _load_yaml(CONTRACT_PATH)
    omitted_contract["required_pack_contract"]["lanes"]["topology"]["exact_governing_reference_ids"].remove(
        "skill/paper-claim-trace"
    )
    omitted_pack = _proposed_pack(omitted_contract)
    with pytest.raises(CandidatePackError, match="enforcer is omitted"):
        _validate_proposed_pack(
            omitted_pack,
            contract=omitted_contract,
            accepted_contract_oracle_sha256=_canonical_sha256(omitted_contract),
        )

    foreign_valid = _proposed_pack()
    interpretation = next(
        row
        for row in foreign_valid["lanes"]["topology"]["obligation_rows"]
        if row["obligation_id"] == "topology.interpretation_topology_geometry_association_causality"
    )
    interpretation["enforcing_reference_ids"][-1] = "skill/research-assurance-triage"
    with pytest.raises(CandidatePackError, match="obligation rows"):
        _validate_proposed_pack(foreign_valid)


def test_exact_fixture_set_rejects_missing_extra_duplicate_and_attack_swaps():
    missing = _proposed_pack()
    missing["required_fixtures"].pop()
    with pytest.raises(CandidatePackError, match="fixture rows"):
        _validate_proposed_pack(missing)

    extra = _proposed_pack()
    extra_row = deepcopy(extra["required_fixtures"][0])
    extra_row["fixture_id"] = "apf_foreign_shape_valid"
    extra["required_fixtures"].append(extra_row)
    with pytest.raises(CandidatePackError, match="fixture rows"):
        _validate_proposed_pack(extra)

    duplicate = _proposed_pack()
    duplicate_row = deepcopy(duplicate["required_fixtures"][0])
    duplicate_row["attack_class"] = "extra"
    duplicate["required_fixtures"][1] = duplicate_row
    with pytest.raises(CandidatePackError, match="duplicate fixture id"):
        _validate_proposed_pack(duplicate)

    attack_swap = _proposed_pack()
    attack_swap["required_fixtures"][0]["attack_class"] = "authority"
    with pytest.raises(CandidatePackError, match="fixture rows"):
        _validate_proposed_pack(attack_swap)


def test_no_op_degenerate_and_claim_escalation_rows_have_upstream_negatives_and_downstream_stop():
    contract = _load_yaml(CONTRACT_PATH)
    boundary = contract["required_pack_contract"]["fixture_execution_boundary"]
    assert boundary["upstream_executable_fixture_ids"] == [
        "apf_tested_object_no_op",
        "apf_degenerate_fallback",
        "apf_claim_escalation",
    ]
    assert boundary["downstream_enforcement_status"].startswith("hard_stop_requires_distinct_future_producer")
    assert boundary["upstream_may_claim_downstream_execution"] is False

    no_op = _proposed_pack()
    no_op["required_fixtures"] = [
        row for row in no_op["required_fixtures"] if row["fixture_id"] != "apf_tested_object_no_op"
    ]
    with pytest.raises((SchemaError, CandidatePackError)):
        _validate_proposed_pack(no_op)

    degenerate = _proposed_pack()
    next(row for row in degenerate["required_fixtures"] if row["fixture_id"] == "apf_degenerate_fallback")[
        "expected_outcome"
    ] = "accepted"
    with pytest.raises(SchemaError, match="expected_outcome"):
        _validate_proposed_pack(degenerate)

    claim_escalation = _proposed_pack()
    claim_escalation["core_boundary"]["may_promote_claims"] = True
    with pytest.raises(SchemaError, match="may_promote_claims"):
        _validate_proposed_pack(claim_escalation)


def test_complete_w5_obligation_rows_reject_missing_duplicate_swap_and_free_text():
    pack = _proposed_pack()
    for lane_id, expected_ids in EXPECTED_OBLIGATION_IDS.items():
        assert {row["obligation_id"] for row in pack["lanes"][lane_id]["obligation_rows"]} == (expected_ids)

    missing = _proposed_pack()
    missing["lanes"]["topology"]["obligation_rows"].pop()
    with pytest.raises((SchemaError, CandidatePackError)):
        _validate_proposed_pack(missing)

    duplicate = _proposed_pack()
    duplicate_row = deepcopy(duplicate["lanes"]["topology"]["obligation_rows"][0])
    duplicate_row["review_question_id"] = "review.topology.duplicate_alias"
    duplicate["lanes"]["topology"]["obligation_rows"][1] = duplicate_row
    with pytest.raises(CandidatePackError, match="duplicate obligation id"):
        _validate_proposed_pack(duplicate)

    swapped = _proposed_pack()
    swapped["lanes"]["topology"]["obligation_rows"][0], swapped["lanes"]["representation"]["obligation_rows"][0] = (
        swapped["lanes"]["representation"]["obligation_rows"][0],
        swapped["lanes"]["topology"]["obligation_rows"][0],
    )
    with pytest.raises(CandidatePackError, match="obligation rows"):
        _validate_proposed_pack(swapped)

    free_text = _proposed_pack()
    free_text["lanes"]["topology"]["obligation_rows"][0]["obligation_text"] = "Explicit prospective obligation."
    with pytest.raises(SchemaError, match="obligation_text"):
        _validate_proposed_pack(free_text)


def test_distribution_currency_and_identity_mutations_fail_closed():
    wrong_scope = _proposed_pack()
    wrong_scope["distribution_scope"] = "template_safe"
    with pytest.raises(SchemaError, match="distribution_scope"):
        _validate_proposed_pack(wrong_scope)

    widened = _proposed_pack()
    widened["distribution_controls"]["permitted_consumers"].append("public_template_exporter")
    with pytest.raises(SchemaError, match="permitted_consumers"):
        _validate_proposed_pack(widened)

    for missing_field in ("permitted_consumers", "publication_boundary", "path_restrictions", "data_restrictions"):
        missing = _proposed_pack()
        del missing["distribution_controls"][missing_field]
        with pytest.raises(SchemaError, match=missing_field):
            _validate_proposed_pack(missing)

    contradictory = _proposed_pack()
    contradictory["distribution_controls"]["path_restrictions"]["public_template_paths"] = "allowed"
    with pytest.raises(SchemaError, match="public_template_paths"):
        _validate_proposed_pack(contradictory)

    inverted = _proposed_pack()
    inverted["currency"]["effective_at"] = "2028-01-01T00:00:00Z"
    with pytest.raises(CandidatePackError, match="time order"):
        _validate_proposed_pack(inverted)

    expired = _proposed_pack()
    expired["currency"]["authored_at"] = "2026-07-15T00:00:00Z"
    expired["currency"]["effective_at"] = "2026-07-16T00:00:00Z"
    expired["currency"]["expires_at"] = "2026-07-17T00:00:00Z"
    with pytest.raises(CandidatePackError, match="expired"):
        _validate_proposed_pack(expired)

    stale_contract = _proposed_pack()
    stale_contract["upstream_contract_reference"]["canonical_sha256"] = "f" * 64
    with pytest.raises(CandidatePackError, match="stale upstream contract subject"):
        _validate_proposed_pack(stale_contract)

    schema_swap = _proposed_pack()
    schema_swap["schema_reference"]["git_blob"] = "f" * 40
    with pytest.raises(CandidatePackError, match="stale pack schema subject"):
        _validate_proposed_pack(schema_swap)

    object_alias = _proposed_pack()
    object_alias["assurance_pack_id"] = "TDL_private"
    with pytest.raises(SchemaError, match="assurance_pack_id"):
        _validate_proposed_pack(object_alias)

    producer_change = _proposed_pack()
    producer_change["producer_actor_id"] = ACT_SCIENTIFIC_REVIEWER
    with pytest.raises(CandidatePackError, match="prospective producer relationship is stale"):
        _validate_proposed_pack(producer_change)


def test_coordinated_candidate_and_oracle_replacement_does_not_change_external_authority():
    accepted_contract = _load_yaml(CONTRACT_PATH)
    frozen_oracle_sha = _canonical_sha256(accepted_contract)
    candidate = _proposed_pack(accepted_contract)
    expected_row = accepted_contract["required_pack_contract"]["references"]["exact_reference_rows"][0]
    expected_row["canonical_sha256"] = "f" * 64
    candidate_row = candidate["references"]["contract_references"][0]
    candidate_row["canonical_sha256"] = "f" * 64
    with pytest.raises(CandidatePackError, match="oracle identity mismatch"):
        _validate_proposed_pack(
            candidate,
            contract=accepted_contract,
            accepted_contract_oracle_sha256=frozen_oracle_sha,
        )

    eligible_contract = _eligible_contract()
    pack, _, record_store, hash_manifest = _external_records(_proposed_pack(eligible_contract))
    tampered_pack = deepcopy(pack)
    tampered_pack["currency"]["expires_at"] = "2028-07-18T09:00:00Z"
    tampered_review = deepcopy(record_store)
    tampered_raw, _ = _coordinate_all_external_hashes(tampered_pack, tampered_review)
    frozen_external_manifest = deepcopy(hash_manifest)
    with pytest.raises(CandidatePackError, match="external record hash mismatch"):
        _validate_external_acceptance(
            tampered_pack,
            raw_candidate_pack_bytes=tampered_raw,
            contract=eligible_contract,
            accepted_contract_oracle_sha256=_canonical_sha256(eligible_contract),
            record_store=tampered_review,
            hash_manifest=frozen_external_manifest,
        )
