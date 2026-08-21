"""Shared Discovery lifecycle rules.

Every predicate here is the single source of truth for one accepted-W11
lifecycle relation.  Preparation calls it before publishing an event and replay
calls it while accepting one, so the two sides cannot drift: there is exactly one
copy of each rule and both paths reach it.

This is a leaf module.  It is pure -- it reads mappings and returns booleans (or
raises :class:`IntegrityError`) and holds no projection state, no ledger handle
and no schema registry.  It must never import replay, preparation, or the
runtime facade.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Iterable, Mapping

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.reducers import replay_control_plane
from research_system.discovery.assay_successor import DOCUMENT_TYPE as ASSAY_SUCCESSOR_DOCUMENT_TYPE
from research_system.discovery.assay_successor import SCHEMA_ID as ASSAY_SUCCESSOR_SCHEMA_ID
from research_system.discovery.assay_successor import (
    successor_document_hashes,
    validate_successor_authority_semantics,
)
from research_system.discovery.dossier import (
    AcceptedExpectedSet,
    DossierMember,
    accepted_expected_set_hash,
    admission_profile_hash,
    canonical_dossier_hash,
)
from research_system.errors import ConfigurationError, IntegrityError, SchemaError


_ASSAY_PARTIAL_FIELDS = frozenset(
    {
        "schema_id",
        "schema_version",
        "assay_id",
        "candidate_ref",
        "rubric_ref",
        "scope_ref",
        "assay_bar_acceptance_ref",
        "assay_relation_hash",
        "completed_axes",
        "completed_evidence",
        "unmet_axes",
        "unmet_evidence",
        "reason_codes",
        "limitations",
        "revisit_requirements",
        "mechanical_recommendation",
    }
)

_LEGACY_SPEC_CANDIDATE_ID = "obj_01a00620-0f74-7613-a7b0-dffbb50d9663"
_LEGACY_SPEC_ASSAY_ID = "asy_01a00620-0f74-74e6-b440-f760f4eb6731"


def _is_spec_route_candidate(state: Mapping[str, Any], candidate: Mapping[str, Any] | None) -> bool:
    """Return whether the candidate is bound to the Gate 6 SPEC route.

    New candidates carry the exact route source query.  The persisted 2026-08
    Gate 6 run predates that query token.  Its exact immutable candidate and
    Assay identities may therefore use the accepted-bar relation as a replay
    compatibility proof; that relation is not a reusable route classifier.
    """

    if not isinstance(candidate, Mapping):
        return False
    observations = state.get("source_observations", {})
    if any(
        isinstance(observation, Mapping)
        and observation.get("batch", {}).get("source_query") == "exact:SPEC-GATE6-RUN-V1"
        for observation_id in candidate.get("source_observation_refs", ())
        for observation in (observations.get(observation_id),)
    ):
        return True
    assays = state.get("assays", {})
    bar = state.get("assay_bar_authority")
    assay = assays.get(candidate.get("assay_id")) if isinstance(assays, Mapping) else None
    return bool(
        candidate.get("candidate_id") == _LEGACY_SPEC_CANDIDATE_ID
        and candidate.get("assay_id") == _LEGACY_SPEC_ASSAY_ID
        and isinstance(bar, Mapping)
        and bar.get("status") == "accepted"
        and isinstance(assay, Mapping)
        and assay.get("candidate_id") == _LEGACY_SPEC_CANDIDATE_ID
        and assay.get("assay_bar_acceptance_sha256") == bar.get("acceptance_sha256")
        and assay.get("producer_relation_sha256") == bar.get("producer_relation_sha256")
    )


def _valid_assay_partial_shape(artifact: Mapping[str, Any]) -> bool:
    """Validate the closed non-reference shape of an Assay Partial artifact."""
    list_fields = (
        "completed_axes",
        "completed_evidence",
        "unmet_axes",
        "unmet_evidence",
        "reason_codes",
        "limitations",
        "revisit_requirements",
    )
    return bool(
        set(artifact) == _ASSAY_PARTIAL_FIELDS
        and artifact.get("schema_id") == "ars://portfolio/assay-partial"
        and artifact.get("schema_version") == "1.0.0"
        and all(
            isinstance(artifact.get(field), list) and all(isinstance(value, str) for value in artifact[field])
            for field in list_fields
        )
        and all(artifact.get(field) for field in ("unmet_axes", "reason_codes", "revisit_requirements"))
        and artifact.get("mechanical_recommendation") in {"PARK", "KILL", "UNABLE_TO_SCORE"}
    )


def _valid_promotion_options(value: Any) -> bool:
    """Return whether a proposal carries the exact PromotionDecision option set."""
    return bool(
        isinstance(value, list)
        and len(value) == 3
        and all(isinstance(option, str) for option in value)
        and set(value) == {"PROMOTE", "PARK", "KILL"}
    )


def _valid_spike_execution_proposal(value: Any) -> bool:
    """Return whether a Spike execution proposal carries the closed option set."""

    return bool(
        isinstance(value, Mapping)
        and value.get("recommendation") in {"approve", "reject"}
        and isinstance(value.get("options"), list)
        and len(value["options"]) == 2
        and set(value["options"]) == {"approve", "reject"}
    )


def _valid_revisit_proposal(value: Any, review_id: Any) -> bool:
    """Return whether a revisit proposal carries the closed option set."""

    return bool(
        isinstance(value, Mapping)
        and isinstance(review_id, str)
        and value.get("recommendation") in {"RETRY", "PARK", "KILL"}
        and isinstance(value.get("options"), list)
        and len(value["options"]) == 3
        and all(isinstance(option, str) for option in value["options"])
        and set(value["options"]) == {"RETRY", "PARK", "KILL"}
        and isinstance(value.get("governing_evidence_refs"), list)
        and review_id in value["governing_evidence_refs"]
    )


def _record_ref(record_id: Any, revision: Any, content_hash: Any) -> dict[str, Any]:
    """Build the exact immutable record reference used by W11 relations."""

    return {"id": record_id, "record_revision": revision, "content_hash": content_hash}


def _candidate_ref(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Build the immutable content reference for one Candidate."""

    return _record_ref(candidate.get("candidate_id"), candidate.get("revision"), candidate.get("content_sha256"))


def _candidate_supersession_lineage(
    candidates: Mapping[str, Any],
    predecessor: Mapping[str, Any],
    replacement: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Derive the acyclic immutable Candidate lineage ending in a replacement."""

    reverse_lineage: list[dict[str, Any]] = []
    seen: set[Any] = set()
    current: Mapping[str, Any] | None = predecessor
    while current is not None:
        candidate_id = current.get("candidate_id")
        if not isinstance(candidate_id, str) or candidate_id in seen:
            raise IntegrityError("Candidate supersession lineage is cyclic")
        seen.add(candidate_id)
        reverse_lineage.append(_candidate_ref(current))
        prior = [
            value
            for value in candidates.values()
            if isinstance(value, Mapping) and value.get("superseded_by") == candidate_id
        ]
        if not prior:
            break
        if len(prior) != 1:
            raise IntegrityError("Candidate supersession lineage is incomplete")
        current = prior[0]
    replacement_id = replacement.get("candidate_id")
    if replacement_id in seen:
        raise IntegrityError("Candidate supersession lineage is cyclic")
    return [*reversed(reverse_lineage), _candidate_ref(replacement)]


def _candidate_replacement_is_used(candidates: Mapping[str, Any], replacement_id: Any) -> bool:
    """Return whether an authorized predecessor relation already names the replacement."""

    return any(
        isinstance(candidate, Mapping) and candidate.get("superseded_by") == replacement_id
        for candidate in candidates.values()
    )


def _review_ref(review: Mapping[str, Any]) -> dict[str, Any]:
    """Build the immutable reference to a satisfied review verdict."""

    return _record_ref(review.get("review_id"), review.get("version"), review.get("verdict_event_hash"))


def _aggregate_content_hash(aggregate: Mapping[str, Any]) -> Any:
    """Return the exact terminal evidence hash for an Assay or Spike."""

    return aggregate.get("scorecard_sha256", aggregate.get("verdict_sha256", aggregate.get("outcome_sha256")))


def _promotion_relation_matches(
    relation: Any,
    *,
    decision_id: Any,
    candidate: Mapping[str, Any],
    aggregate_id: Any,
    aggregate: Mapping[str, Any],
    review: Mapping[str, Any],
    gate: str,
    recommendation: Any,
    actor_id: Any,
) -> bool:
    """Validate the strict W11 discovery-promotion companion relation."""

    next_state = {
        "PROMOTE": {
            "assay_to_spike": "spike_planning_authorized",
            "spike_to_preregistration": "preregistration_authorized",
        }.get(gate),
        "PARK": "parked",
        "KILL": "killed",
    }.get(recommendation)
    evidence_hash = _aggregate_content_hash(aggregate)
    expected_aggregate_ref = _record_ref(aggregate_id, aggregate.get("version"), evidence_hash)
    expected_review_ref = _review_ref(review)
    return bool(
        isinstance(relation, Mapping)
        and set(relation)
        == {
            "schema_id",
            "schema_version",
            "relation_kind",
            "decision_id",
            "candidate_ref",
            "gate",
            "aggregate_ref",
            "aggregate_relation_hash",
            "evidence_ref",
            "selected_option",
            "next_candidate_state",
            "rationale",
            "considered_evidence_refs",
            "conditions",
            "effective_scope",
            "revisit_triggers",
            "actor_id",
        }
        and relation.get("schema_id") == "ars://portfolio/relation/discovery-promotion"
        and relation.get("schema_version") == "1.0.0"
        and relation.get("relation_kind") == "discovery_promotion"
        and relation.get("decision_id") == decision_id
        and relation.get("candidate_ref")
        == _record_ref(candidate.get("candidate_id"), candidate.get("revision"), candidate.get("content_sha256"))
        and relation.get("gate") == gate
        and relation.get("aggregate_ref") == expected_aggregate_ref
        and relation.get("aggregate_relation_hash")
        == aggregate.get("producer_relation_sha256", aggregate.get("plan_sha256"))
        and relation.get("evidence_ref") == expected_aggregate_ref
        and relation.get("selected_option") == recommendation
        and relation.get("next_candidate_state") == next_state
        and isinstance(relation.get("rationale"), str)
        and bool(relation["rationale"])
        and relation.get("considered_evidence_refs") == [expected_review_ref]
        and isinstance(relation.get("conditions"), list)
        and isinstance(relation.get("effective_scope"), str)
        and bool(relation["effective_scope"])
        and isinstance(relation.get("revisit_triggers"), list)
        and relation.get("actor_id") == actor_id
        and review.get("status") == "satisfied"
    )


def _revisit_relation_matches(
    relation: Any,
    *,
    decision_id: Any,
    candidate: Mapping[str, Any],
    aggregate_id: Any,
    aggregate: Mapping[str, Any],
    review: Mapping[str, Any],
    observations: Mapping[str, Any],
    recommendation: Any,
    actor_id: Any,
) -> bool:
    """Validate a discovery-revisit relation and its later objective evidence."""

    predicate_ref = relation.get("satisfied_revisit_predicate_ref") if isinstance(relation, Mapping) else None
    predicate = observations.get(predicate_ref.get("id")) if isinstance(predicate_ref, Mapping) else None
    predicate_batch = predicate.get("batch") if isinstance(predicate, Mapping) else None
    matching_facts = predicate_batch.get("matching_facts") if isinstance(predicate_batch, Mapping) else None
    revisit_requirements = aggregate.get("revisit_requirements")
    review_position = review.get("verdict_global_position")
    parked_position = candidate.get("parked_at_global_position")
    threshold = max(
        review_position if isinstance(review_position, int) else -1,
        parked_position if isinstance(parked_position, int) else -1,
    )
    return bool(
        isinstance(relation, Mapping)
        and set(relation)
        == {
            "schema_id",
            "schema_version",
            "relation_kind",
            "decision_id",
            "candidate_ref",
            "prior_aggregate_ref",
            "prior_outcome_review_ref",
            "satisfied_revisit_predicate_ref",
            "selected_option",
            "actor_id",
        }
        and relation.get("schema_id") == "ars://portfolio/relation/discovery-revisit"
        and relation.get("schema_version") == "1.0.0"
        and relation.get("relation_kind") == "discovery_revisit"
        and relation.get("decision_id") == decision_id
        and relation.get("candidate_ref")
        == _record_ref(candidate.get("candidate_id"), candidate.get("revision"), candidate.get("content_sha256"))
        and relation.get("prior_aggregate_ref")
        == _record_ref(aggregate_id, aggregate.get("version"), _aggregate_content_hash(aggregate))
        and relation.get("prior_outcome_review_ref") == _review_ref(review)
        and isinstance(predicate, Mapping)
        and predicate_ref == _record_ref(predicate_ref.get("id"), 1, predicate.get("content_sha256"))
        and predicate_ref.get("id") not in {candidate.get("candidate_id"), aggregate_id, review.get("review_id")}
        and isinstance(predicate.get("global_position"), int)
        and predicate["global_position"] > threshold
        and isinstance(revisit_requirements, list)
        and bool(revisit_requirements)
        and isinstance(matching_facts, list)
        and all(isinstance(requirement, str) and requirement in matching_facts for requirement in revisit_requirements)
        and relation.get("selected_option") == recommendation
        and relation.get("actor_id") == actor_id
    )


def _current_assay_bar_matches(subject: Mapping[str, Any], bar: Mapping[str, Any], actor_id: Any = None) -> bool:
    """Bind every Assay route to the current accepted bar and prospective producer."""

    producer_ref = bar.get("prospective_producer_ref")
    producer_id = producer_ref.get("id") if isinstance(producer_ref, Mapping) else None
    return bool(
        bar.get("status") == "accepted"
        and subject.get("assay_bar_acceptance_sha256") == bar.get("acceptance_sha256")
        and subject.get("producer_relation_sha256") == bar.get("producer_relation_sha256")
        and isinstance(producer_id, str)
        and subject.get("producer_actor_id") == producer_id
        and (actor_id is None or actor_id == producer_id)
    )


def _current_projection_record_ref(state: Mapping[str, Any], value: Any) -> dict[str, Any] | None:
    """Resolve one exact current immutable Discovery record reference."""

    if not isinstance(value, Mapping) or set(value) != {"id", "record_revision", "content_hash"}:
        return None
    record_id = value.get("id")
    record: Mapping[str, Any] | None = None
    revision: Any = None
    content_hash: Any = None
    for collection in (
        "source_observations",
        "candidates",
        "assays",
        "spikes",
        "decisions",
        "reviews",
        "portfolio_objects",
        "scopes",
    ):
        candidate = state.get(collection, {}).get(record_id)
        if isinstance(candidate, Mapping):
            record = candidate
            if collection == "source_observations":
                revision = candidate.get("version")
                content_hash = candidate.get("content_sha256")
            elif collection == "candidates":
                revision = candidate.get("revision")
                content_hash = candidate.get("content_sha256")
            elif collection == "assays":
                revision = 1
                content_hash = _aggregate_content_hash(candidate)
            elif collection == "spikes":
                revision = 1
                content_hash = candidate.get("verdict_sha256", candidate.get("plan_sha256"))
            elif collection == "decisions":
                revision = candidate.get("proposal_version")
                content_hash = candidate.get("proposal_event_hash")
            elif collection == "portfolio_objects":
                revision = candidate.get("record_revision")
                content_hash = candidate.get("content_sha256")
            elif collection == "scopes":
                revision = candidate.get("scope_revision")
                content_hash = candidate.get("content_sha256")
            else:
                revision = candidate.get("version")
                content_hash = candidate.get("verdict_event_hash", candidate.get("request_event_hash"))
            break
    resolved = _record_ref(record_id, revision, content_hash)
    return resolved if record is not None and value == resolved and isinstance(content_hash, str) else None


def _projection_record_ref_matches(state: Mapping[str, Any], value: Any) -> bool:
    """Return whether a reference resolves to an exact current Discovery record."""

    return _current_projection_record_ref(state, value) is not None


def _axis_set_hash(axis_ids: Iterable[str]) -> str:
    """Return the canonical P0 multiset hash for an observed axis closure."""

    return sha256_hex(canonical_bytes(sorted(axis_ids)))


_SPEC_GATE6_ASSAY_AXIS_IDS = (
    "topology_earns_its_keep",
    "data_feasibility",
    "novelty_publishability",
)
_SPEC_GATE6_MECHANICAL_PREDICATES = (
    "PROMOTE requires topology_earns_its_keep == true",
    "PROMOTE requires data_feasibility + novelty_publishability >= 4",
    "PROMOTE requires data_feasibility > 0 and novelty_publishability > 0",
)
_SPEC_GATE6_PARTIAL_PREDICATES = (
    "Partial requires blocked or incomplete required evidence and cannot be relabelled PROMOTE",
)
_SPEC_GATE6_PARK_PREDICATES = (
    "PARK when topology_earns_its_keep == true, data_feasibility > 0, "
    "novelty_publishability > 0, and data_feasibility + novelty_publishability < 4, "
    "with named remediable gaps and revisit requirements",
    "PARK is required when any additional human-readable promotion gate is unmet or cannot be expressed by the "
    "machine scorecard",
)
_SPEC_GATE6_KILL_PREDICATES = (
    "KILL when completed evidence has topology_earns_its_keep == false",
    "KILL when completed evidence has data_feasibility == 0",
    "KILL when completed evidence has novelty_publishability == 0",
    "KILL requires a directly verified decisive failure or redundancy",
)


def _mechanical_assay_recommendation(
    rubric: Mapping[str, Any],
    axis_definitions: list[Any],
    results_by_axis: Mapping[str, tuple[Mapping[str, Any], Mapping[str, Any]]],
) -> str | None:
    """Evaluate the accepted rubric's named mechanical recommendation algorithm."""

    algorithm_id = rubric.get("rule_evaluation_algorithm_id")
    if algorithm_id == "spec-gate6-assay-score-v1":
        required_axis_ids = rubric.get("required_axis_ids")
        evaluation_order = rubric.get("evaluation_order")
        recommendation_predicates = rubric.get("recommendation_predicates")
        partial_predicates = rubric.get("partial_predicates")
        park_predicates = rubric.get("park_predicates")
        kill_predicates = rubric.get("kill_predicates")
        rule_preimage_fields = (
            "evaluation_order",
            "recommendation_predicates",
            "hard_gate_predicates",
            "partial_predicates",
            "park_predicates",
            "kill_predicates",
            "rule_evaluation_algorithm_id",
            "rule_evaluation_algorithm_version",
        )
        try:
            expected_rule_hash = sha256_hex(canonical_bytes({field: rubric[field] for field in rule_preimage_fields}))
        except (KeyError, TypeError, ValueError):
            return None
        if (
            rubric.get("rule_evaluation_algorithm_version") != "1.0.0"
            or not isinstance(required_axis_ids, list)
            or tuple(required_axis_ids) != _SPEC_GATE6_ASSAY_AXIS_IDS
            or not isinstance(evaluation_order, list)
            or tuple(evaluation_order) != _SPEC_GATE6_ASSAY_AXIS_IDS
            or not isinstance(recommendation_predicates, list)
            or tuple(recommendation_predicates[:3]) != _SPEC_GATE6_MECHANICAL_PREDICATES
            or not isinstance(partial_predicates, list)
            or tuple(partial_predicates) != _SPEC_GATE6_PARTIAL_PREDICATES
            or not isinstance(park_predicates, list)
            or tuple(park_predicates) != _SPEC_GATE6_PARK_PREDICATES
            or not isinstance(kill_predicates, list)
            or tuple(kill_predicates) != _SPEC_GATE6_KILL_PREDICATES
            or rubric.get("rule_evaluation_algorithm_hash") != expected_rule_hash
            or tuple(definition.get("axis_id") for definition in axis_definitions) != _SPEC_GATE6_ASSAY_AXIS_IDS
        ):
            return None
        topology_definition, topology_result = results_by_axis["topology_earns_its_keep"]
        data_definition, data_result = results_by_axis["data_feasibility"]
        novelty_definition, novelty_result = results_by_axis["novelty_publishability"]
        if (
            topology_definition.get("axis_kind") != "gate"
            or topology_definition.get("value_type") != "boolean"
            or topology_definition.get("allowed_set") != [False, True]
            or data_definition.get("axis_kind") != "integer_score"
            or data_definition.get("value_type") != "integer"
            or data_definition.get("bounds") != {"minimum": 0, "maximum": 3}
            or novelty_definition.get("axis_kind") != "integer_score"
            or novelty_definition.get("value_type") != "integer"
            or novelty_definition.get("bounds") != {"minimum": 0, "maximum": 3}
            or any(definition.get("required") is not True for definition in axis_definitions)
        ):
            return None
        topology = topology_result.get("value")
        data_score = data_result.get("value")
        novelty_score = novelty_result.get("value")
        if type(data_score) is not int or type(novelty_score) is not int:
            return None
        if topology is not True or data_score == 0 or novelty_score == 0:
            return "KILL"
        return "PROMOTE" if data_score + novelty_score >= 4 else "PARK"

    required_axis_ids = rubric.get("required_axis_ids")
    if not isinstance(required_axis_ids, list):
        return None
    required_results = [results_by_axis[axis_id] for axis_id in required_axis_ids]
    return (
        "PROMOTE"
        if all(
            definition.get("axis_kind") != "gate" or result.get("value") is True
            for definition, result in required_results
        )
        else "KILL"
    )


def _assay_scorecard_matches(
    artifact: Mapping[str, Any],
    payload: Mapping[str, Any],
    candidate: Mapping[str, Any],
    assay: Mapping[str, Any],
    bar: Mapping[str, Any],
    actor_id: Any,
) -> bool:
    """Bind an Assay scorecard to its frozen accepted bar and evidence closure."""

    acceptance = bar.get("acceptance")
    contents = bar.get("contents")
    observations = bar.get("observations")
    if (
        not isinstance(acceptance, Mapping)
        or not isinstance(contents, Mapping)
        or not isinstance(observations, Mapping)
    ):
        return False
    rubric_state = contents.get("rubric")
    scope_state = contents.get("scope")
    rubric_observation = observations.get("rubric")
    scope_observation = observations.get("scope")
    if not all(
        isinstance(value, Mapping) for value in (rubric_state, scope_state, rubric_observation, scope_observation)
    ):
        return False
    rubric = rubric_state.get("content")
    scope = scope_state.get("content")
    if not isinstance(rubric, Mapping) or not isinstance(scope, Mapping):
        return False
    axis_definitions = rubric.get("axis_definitions")
    axis_results = artifact.get("axis_results")
    evidence_rows = scope.get("evidence_rows")
    if (
        not isinstance(axis_definitions, list)
        or not isinstance(axis_results, list)
        or not isinstance(evidence_rows, list)
        or len(axis_results) != len(axis_definitions)
        or len(evidence_rows) != len(axis_definitions)
    ):
        return False
    expected_file_refs = [
        _record_ref(
            rubric.get("record_id"),
            rubric.get("record_revision"),
            rubric_observation.get("file_sha256"),
        ),
        _record_ref(
            scope.get("record_id"),
            scope.get("record_revision"),
            scope_observation.get("file_sha256"),
        ),
    ]
    for definition, result, evidence_row in zip(axis_definitions, axis_results, evidence_rows, strict=True):
        if not all(isinstance(value, Mapping) for value in (definition, result, evidence_row)):
            return False
        value = result.get("value")
        allowed = definition.get("allowed_set")
        bounds = definition.get("bounds")
        minimum = bounds.get("minimum") if isinstance(bounds, Mapping) else None
        maximum = bounds.get("maximum") if isinstance(bounds, Mapping) else None
        value_type = definition.get("value_type")
        typed_value = (
            type(value) is bool
            if value_type == "boolean"
            else type(value) is int
            if value_type == "integer"
            else isinstance(value, (int, float)) and not isinstance(value, bool)
            if value_type == "number"
            else False
        )
        if (
            result.get("axis_id") != definition.get("axis_id")
            or result.get("axis_kind") != definition.get("axis_kind")
            or result.get("validator_id") != evidence_row.get("validator_id")
            or result.get("validator_hash") != evidence_row.get("validator_hash")
            or result.get("evidence_refs") != expected_file_refs
            or not typed_value
            or (isinstance(allowed, list) and value not in allowed)
            or (isinstance(minimum, (int, float)) and value < minimum)
            or (isinstance(maximum, (int, float)) and value > maximum)
        ):
            return False
    axis_ids = [definition.get("axis_id") for definition in axis_definitions]
    if not all(isinstance(axis_id, str) and axis_id for axis_id in axis_ids) or len(set(axis_ids)) != len(axis_ids):
        return False
    expected_candidate = _record_ref(
        payload.get("candidate_id"), candidate.get("revision"), candidate.get("content_sha256")
    )
    expected_acceptance = _record_ref(acceptance.get("decision_id"), 1, bar.get("acceptance_sha256"))
    expected_request = _record_ref(
        payload.get("assay_id"), assay.get("request_version"), assay.get("requested_event_hash")
    )
    expected_rule = _record_ref(
        rubric.get("rule_evaluation_algorithm_id"),
        1,
        rubric.get("rule_evaluation_algorithm_hash"),
    )
    required_axis_ids = rubric.get("required_axis_ids")
    if (
        not isinstance(required_axis_ids, list)
        or not required_axis_ids
        or not all(isinstance(axis_id, str) and axis_id for axis_id in required_axis_ids)
        or len(set(required_axis_ids)) != len(required_axis_ids)
    ):
        return False
    results_by_axis = {
        definition.get("axis_id"): (definition, result)
        for definition, result in zip(axis_definitions, axis_results, strict=True)
        if isinstance(definition.get("axis_id"), str)
    }
    if any(axis_id not in results_by_axis for axis_id in required_axis_ids):
        return False
    recommendation = _mechanical_assay_recommendation(rubric, axis_definitions, results_by_axis)
    if recommendation is None:
        return False
    try:
        artifact_sha256 = sha256_hex(canonical_bytes(artifact))
    except (TypeError, ValueError):
        return False
    producer_ref = acceptance.get("prospective_producer_ref")
    return bool(
        bar.get("status") == "accepted"
        and assay.get("assay_bar_acceptance_sha256") == bar.get("acceptance_sha256")
        and artifact.get("candidate_ref") == expected_candidate
        and artifact.get("assay_id") == payload.get("assay_id")
        and artifact.get("assay_requested_event_ref") == expected_request
        and artifact.get("assay_relation_hash") == assay.get("producer_relation_sha256")
        and artifact.get("rubric_ref") == acceptance.get("rubric_ref")
        and artifact.get("scope_ref") == acceptance.get("scope_ref")
        and artifact.get("assay_bar_acceptance_ref") == expected_acceptance
        and artifact.get("file_observation_refs") == expected_file_refs
        and artifact.get("producer_relation_ref") == producer_ref
        and artifact.get("producer_profile_ref") == producer_ref
        and artifact.get("producer_context_ref") == producer_ref
        and artifact.get("required_axis_set_hash") == acceptance.get("required_axis_set_hash")
        and artifact.get("observed_axis_set_hash") == _axis_set_hash(axis_ids)
        and artifact.get("mechanical_recommendation") == recommendation
        and artifact.get("rule_evaluation_ref") == expected_rule
        and artifact.get("producer_actor_id") == actor_id
        and artifact_sha256 == payload.get("scorecard_sha256")
    )


def _spike_execution_relation_matches(
    relation: Any,
    *,
    candidate: Mapping[str, Any],
    assay: Mapping[str, Any],
    spike: Mapping[str, Any],
    decision_id: Any,
    resource: Mapping[str, Any],
) -> bool:
    """Bind the complete Spike execution subject to its plan and assurance."""

    plan_ref = _record_ref(spike.get("spike_id"), 1, spike.get("plan_sha256"))
    return bool(
        isinstance(relation, Mapping)
        and relation.get("schema_id") == "ars://portfolio/relation/spike-execution-authority"
        and relation.get("schema_version") == "1.0.0"
        and relation.get("relation_kind") == "spike_execution_authority"
        and relation.get("decision_id") == decision_id
        and relation.get("spike_ref") == plan_ref
        and relation.get("candidate_ref")
        == _record_ref(candidate.get("candidate_id"), candidate.get("revision"), candidate.get("content_sha256"))
        and relation.get("plan_ref") == plan_ref
        and relation.get("route_ref") == plan_ref
        and relation.get("assurance_ref") == _record_ref(assay.get("assay_id"), 1, assay.get("scorecard_sha256"))
        and relation.get("resource_ref")
        == _record_ref(relation.get("resource_ref", {}).get("id"), 1, sha256_hex(canonical_bytes(resource)))
        and relation.get("selected_option") == "AUTHORIZE"
        and isinstance(relation.get("actor_id"), str)
    )


def _spike_plan_matches(
    artifact: Mapping[str, Any],
    payload: Mapping[str, Any],
    candidate: Mapping[str, Any],
    assay: Mapping[str, Any] | None,
    promotion_decision: Mapping[str, Any] | None,
) -> bool:
    """Bind one Spike plan to the exact Candidate, Assay and promotion decision."""

    return bool(
        isinstance(assay, Mapping)
        and artifact.get("spike_id") == payload.get("spike_id")
        and artifact.get("candidate_ref")
        == _record_ref(
            payload.get("candidate_id"),
            candidate.get("revision"),
            candidate.get("content_sha256"),
        )
        and artifact.get("originating_assay_ref", {}).get("id") == candidate.get("assay_id")
        and artifact.get("originating_assay_ref", {}).get("content_hash") == assay.get("scorecard_sha256")
        and artifact.get("source_scorecard_refs") == [artifact.get("originating_assay_ref")]
        and isinstance(promotion_decision, Mapping)
        and artifact.get("assay_promotion_decision_ref")
        == _record_ref(
            candidate.get("decision_id"),
            promotion_decision.get("proposal_version"),
            promotion_decision.get("proposal_event_hash"),
        )
        and payload.get("plan_sha256") == sha256_hex(canonical_bytes(artifact))
    )


def _parked_candidate_test_plan_matches(
    candidate: Mapping[str, Any] | None,
    decision: Mapping[str, Any] | None,
    payload: Mapping[str, Any],
) -> bool:
    """Require an explicit non-promotional plan for an owner-approved PARK test."""

    plan_artifact = payload.get("plan_artifact")
    return bool(
        isinstance(candidate, Mapping)
        and candidate.get("status") == "parked"
        and isinstance(decision, Mapping)
        and decision.get("status") == "resolved"
        and decision.get("selected_option") == "PARK"
        and payload.get("row_id") == "OR-014"
        and isinstance(plan_artifact, Mapping)
        and "scientific promotion" in plan_artifact.get("prohibited_work", ())
        and "automatic promotion" in plan_artifact.get("prohibited_work", ())
    )


def _spike_verdict_matches(
    artifact: Mapping[str, Any],
    payload: Mapping[str, Any],
    candidate: Mapping[str, Any],
    assay: Mapping[str, Any],
    spike: Mapping[str, Any],
    state: Mapping[str, Any],
    artefact_streams: Mapping[str, Any],
) -> bool:
    """Resolve every Spike verdict relationship, predicate and evidence ref."""

    plan = spike.get("plan_artifact")
    if not isinstance(plan, Mapping):
        return False
    expected_candidate = _record_ref(
        payload.get("candidate_id"), candidate.get("revision"), candidate.get("content_sha256")
    )
    predicate_evidence_refs = [
        *(
            ref
            for result in [
                *artifact.get("success_predicates", ()),
                *artifact.get("failure_predicates", ()),
                *artifact.get("kill_conditions", ()),
            ]
            if isinstance(result, Mapping)
            for ref in result.get("evidence_refs", ())
        ),
    ]
    relationships_match = (
        artifact.get("spike_id") == payload.get("spike_id")
        and artifact.get("candidate_ref") == expected_candidate
        and artifact.get("originating_assay_ref", {}).get("id") == candidate.get("assay_id")
        and artifact.get("originating_assay_ref", {}).get("content_hash") == assay.get("scorecard_sha256")
        and artifact.get("spike_plan_ref") == _record_ref(payload.get("spike_id"), 1, spike.get("plan_sha256"))
        and artifact.get("attempt_ref") == _record_ref(spike.get("attempt_id"), 1, spike.get("attempt_sha256"))
        and artifact.get("verdict") == payload.get("verdict")
        and sha256_hex(canonical_bytes(artifact)) == payload.get("verdict_sha256")
        and bool(artifact.get("artefact_refs"))
        and bool(artifact.get("validation_refs"))
        and bool(predicate_evidence_refs)
        and all(
            _canonical_artefact_ref_matches(artefact_streams, ref, validation=False)
            for ref in artifact.get("artefact_refs", ())
        )
        and all(
            _canonical_artefact_ref_matches(artefact_streams, ref, validation=True)
            for ref in artifact.get("validation_refs", ())
        )
        and all(
            _projection_record_ref_matches(state, ref)
            or _canonical_artefact_ref_matches(artefact_streams, ref, validation=False)
            for ref in predicate_evidence_refs
        )
        and any("dispatch" in value.casefold() for value in artifact.get("prohibited_inferences", ()))
    )
    success = artifact.get("success_predicates", [])
    failure = artifact.get("failure_predicates", [])
    kills = artifact.get("kill_conditions", [])
    if not all(isinstance(value, Mapping) for value in [*success, *failure, *kills]):
        return False
    has_unknown = any(value.get("status") == "unable_to_evaluate" for value in [*success, *failure, *kills])
    predicate_closure = (
        [value.get("predicate") for value in success] == plan.get("success_predicates")
        and [value.get("predicate") for value in failure] == plan.get("failure_predicates")
        and [value.get("condition") for value in kills] == plan.get("kill_conditions")
    )
    if artifact.get("verdict") == "PASS":
        truth_table = (
            not has_unknown
            and bool(success)
            and all(value.get("status") == "passed" for value in success)
            and all(value.get("status") != "failed" for value in failure)
            and all(value.get("status") == "not_triggered" for value in kills)
        )
    elif artifact.get("verdict") == "FAIL":
        truth_table = not has_unknown and (
            any(value.get("status") == "failed" for value in failure)
            or any(value.get("status") == "triggered" for value in kills)
        )
    else:
        truth_table = bool(
            has_unknown
            and artifact.get("completed_scope")
            and artifact.get("unmet_scope")
            and artifact.get("limitations")
            and artifact.get("mechanical_recommendation") != "PROMOTE"
        )
    return bool(relationships_match and predicate_closure and truth_table)


def _canonical_artefact_ref_matches(streams: Mapping[str, Any], value: Any, *, validation: bool) -> bool:
    """Resolve an immutable Spike evidence ref from the canonical artefact projection."""

    if not isinstance(value, Mapping) or set(value) != {"id", "record_revision", "content_hash"}:
        return False
    state = streams.get(value.get("id"))
    manifest = state.get("manifest") if isinstance(state, Mapping) else None
    artefact_type = manifest.get("artefact_type") if isinstance(manifest, Mapping) else None
    if not isinstance(artefact_type, str):
        return False
    if validation and not any(token in artefact_type.casefold() for token in ("validation", "verification", "review")):
        return False
    return bool(
        state.get("artefact_id") == value.get("id")
        and value.get("record_revision") == 1
        and state.get("content_sha256") == value.get("content_hash")
        and state.get("use_authority") not in {"rejected", "superseded"}
    )


def _assay_partial_bindings_match(
    artifact: Mapping[str, Any],
    payload: Mapping[str, Any],
    candidate: Mapping[str, Any],
    assay: Mapping[str, Any],
    bar: Mapping[str, Any],
    acceptance: Mapping[str, Any],
) -> bool:
    """Bind an Assay Partial artifact to its exact subject, bar acceptance and digest.

    Preparation and replay previously each carried their own copy of these seven
    comparisons.  They are the same rule, so there is now one definition and both
    paths reach it; each side keeps only the additional state checks its own
    context can make (a command actor before publication, the reduced Assay
    status and current-bar producer binding during replay).
    """

    return bool(
        _valid_assay_partial_shape(artifact)
        and _assay_partial_axes_match(artifact, bar)
        and artifact.get("candidate_ref")
        == {
            "id": payload.get("candidate_id"),
            "record_revision": candidate.get("revision"),
            "content_hash": candidate.get("content_sha256"),
        }
        and artifact.get("assay_id") == payload.get("assay_id")
        and artifact.get("rubric_ref") == acceptance.get("rubric_ref")
        and artifact.get("scope_ref") == acceptance.get("scope_ref")
        and artifact.get("assay_bar_acceptance_ref")
        == {
            "id": acceptance.get("decision_id"),
            "record_revision": 1,
            "content_hash": bar.get("acceptance_sha256"),
        }
        and artifact.get("assay_relation_hash") == assay.get("producer_relation_sha256")
        and sha256_hex(canonical_bytes(artifact)) == payload.get("partial_sha256")
    )


def _assay_partial_axes_match(artifact: Mapping[str, Any], bar: Mapping[str, Any]) -> bool:
    """Require an Assay Partial to partition the accepted required-axis closure exactly once."""

    contents = bar.get("contents")
    rubric_state = contents.get("rubric") if isinstance(contents, Mapping) else None
    rubric = rubric_state.get("content") if isinstance(rubric_state, Mapping) else None
    required = rubric.get("required_axis_ids") if isinstance(rubric, Mapping) else None
    completed = artifact.get("completed_axes")
    unmet = artifact.get("unmet_axes")
    return bool(
        isinstance(required, list)
        and required
        and isinstance(completed, list)
        and isinstance(unmet, list)
        and len(completed) == len(set(completed))
        and len(unmet) == len(set(unmet))
        and not (set(completed) & set(unmet))
        and set(completed) | set(unmet) == set(required)
    )


def _assay_cancellation_matches(
    artifact: Any,
    *,
    payload: Mapping[str, Any],
    candidate: Mapping[str, Any],
    assay: Mapping[str, Any],
    state: Mapping[str, Any],
) -> bool:
    """Bind one Assay cancellation to its exact aggregate, producer and evidence subject."""

    if not isinstance(artifact, Mapping) or set(artifact) != {
        "assay_id",
        "candidate_ref",
        "assay_requested_event_ref",
        "producer_relation_sha256",
        "evidence_refs",
        "reason",
    }:
        return False
    evidence_refs = artifact.get("evidence_refs")
    return bool(
        artifact.get("assay_id") == payload.get("assay_id")
        and artifact.get("candidate_ref")
        == _record_ref(candidate.get("candidate_id"), candidate.get("revision"), candidate.get("content_sha256"))
        and artifact.get("assay_requested_event_ref")
        == _record_ref(assay.get("assay_id"), assay.get("request_version"), assay.get("requested_event_hash"))
        and artifact.get("producer_relation_sha256") == assay.get("producer_relation_sha256")
        and isinstance(evidence_refs, list)
        and bool(evidence_refs)
        and all(_projection_record_ref_matches(state, ref) for ref in evidence_refs)
        and isinstance(artifact.get("reason"), str)
        and bool(artifact["reason"])
        and sha256_hex(canonical_bytes(artifact)) == payload.get("cancellation_sha256")
    )


def _is_lowercase_sha256(value: Any) -> bool:
    """Return whether ``value`` is one canonical SHA-256 digest."""

    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _assay_observation_staleness_matches(refs: Any, state: Mapping[str, Any], accepted_position: int) -> bool:
    """Resolve the historical OR-109 observation trigger without changing its contract."""

    observations = state.get("source_observations")
    if not isinstance(refs, list) or not refs or not isinstance(observations, Mapping):
        return False
    bar = state.get("assay_bar_authority")
    contents = bar.get("contents") if isinstance(bar, Mapping) else None
    accepted_hashes: set[str] = set()
    if isinstance(contents, Mapping):
        for kind in ("rubric", "scope"):
            current = contents.get(kind)
            if isinstance(current, Mapping) and isinstance(current.get("content_sha256"), str):
                accepted_hashes.add(current["content_sha256"])
    if isinstance(bar, Mapping) and isinstance(bar.get("producer_relation_sha256"), str):
        accepted_hashes.add(bar["producer_relation_sha256"])
    for ref in refs:
        if not _projection_record_ref_matches(state, ref):
            return False
        observation = observations.get(ref.get("id")) if isinstance(ref, Mapping) else None
        if not isinstance(observation, Mapping) or observation.get("global_position", -1) <= accepted_position:
            return False
        batch = observation.get("batch") if isinstance(observation, Mapping) else None
        facts = batch.get("matching_facts") if isinstance(batch, Mapping) else None
        if not isinstance(facts, list):
            return False
        demonstrated = False
        for fact in facts:
            if not isinstance(fact, str):
                continue
            parts = fact.split(":")
            if (
                len(parts) == 4
                and parts[0] == "assay-bar-change"
                and parts[1] in {"rubric", "scope", "producer"}
                and parts[2] in accepted_hashes
                and _is_lowercase_sha256(parts[3])
                and parts[3] != parts[2]
            ):
                demonstrated = True
                break
        if not demonstrated:
            return False
    return True


def _assay_source_correction_staleness_matches(
    trigger: Any,
    refs: Any,
    state: Mapping[str, Any],
    accepted_position: int,
    schemas: Any,
) -> bool:
    """Bind OR-109 to one later immutable authority-successor document."""

    if not isinstance(trigger, Mapping) or set(trigger) != {
        "artefact_ref",
        "artefact_type",
        "registered_global_position",
        "document",
    }:
        return False
    artefact_ref = trigger.get("artefact_ref")
    document = trigger.get("document")
    if (
        not isinstance(refs, list)
        or not isinstance(document, Mapping)
        or not isinstance(artefact_ref, Mapping)
        or set(artefact_ref) != {"id", "record_revision", "content_hash"}
        or not _is_lowercase_sha256(artefact_ref.get("content_hash"))
    ):
        return False
    streams = state.get("artefact_streams")
    registration_positions = state.get("artefact_registration_positions")
    artefact_id = artefact_ref.get("id")
    artefact = streams.get(artefact_id) if isinstance(streams, Mapping) and isinstance(artefact_id, str) else None
    manifest = artefact.get("manifest") if isinstance(artefact, Mapping) else None
    registered_position = trigger.get("registered_global_position")
    if not (
        isinstance(manifest, Mapping)
        and artefact.get("artefact_id") == artefact_id
        and manifest.get("artefact_id") == artefact_id
        and trigger.get("artefact_type") == ASSAY_SUCCESSOR_DOCUMENT_TYPE
        and manifest.get("artefact_type") == trigger.get("artefact_type")
        and manifest.get("artefact_schema_id") == ASSAY_SUCCESSOR_SCHEMA_ID
        and manifest.get("artefact_schema_version") == "1.0.0"
        and manifest.get("producer_actor_id") == document.get("producer_actor_id")
        and artefact_ref
        == {
            "id": artefact_id,
            "record_revision": 1,
            "content_hash": artefact.get("content_sha256"),
        }
        and isinstance(registration_positions, Mapping)
        and registered_position == registration_positions.get(artefact_id)
        and type(registered_position) is int
        and registered_position > accepted_position
        and artefact.get("use_authority") == "accepted_for_scope"
        and sha256_hex(canonical_bytes(document)) == artefact_ref.get("content_hash")
    ):
        return False

    correction_ref = document.get("source_correction_ref")
    correction_document = document.get("source_correction_document")
    if (
        refs != [correction_ref, artefact_ref]
        or not isinstance(correction_ref, Mapping)
        or not isinstance(correction_document, Mapping)
        or sha256_hex(canonical_bytes(correction_document)) != correction_ref.get("content_hash")
    ):
        return False
    try:
        schemas.validate("ars://portfolio/spec-01-source-correction", correction_document, schema_version="1.0.0")
    except (AttributeError, SchemaError):
        return False
    correction_id = correction_ref.get("id")
    correction = streams.get(correction_id) if isinstance(streams, Mapping) and isinstance(correction_id, str) else None
    correction_manifest = correction.get("manifest") if isinstance(correction, Mapping) else None
    if not (
        isinstance(correction_manifest, Mapping)
        and correction_manifest.get("artefact_type") == "spec_01_source_correction"
        and correction_ref
        == {
            "id": correction_id,
            "record_revision": 1,
            "content_hash": correction.get("content_sha256"),
        }
        and isinstance(registration_positions, Mapping)
        and type(registration_positions.get(correction_id)) is int
        and registration_positions[correction_id] > accepted_position
        and registration_positions[correction_id] < registered_position
        and correction.get("use_authority") == "accepted_for_scope"
        and correction_manifest.get("artefact_schema_id") == "ars://portfolio/spec-01-source-correction"
        and correction_manifest.get("artefact_schema_version") == "1.0.0"
        and correction_manifest.get("producer_actor_id") == correction_document.get("producer", {}).get("actor_id")
    ):
        return False

    bar = state.get("assay_bar_authority")
    contents = bar.get("contents") if isinstance(bar, Mapping) else None
    accepted_authority = document.get("accepted_authority")
    if not isinstance(contents, Mapping) or not isinstance(accepted_authority, Mapping):
        return False
    try:
        successor_hashes = successor_document_hashes(document)
        successor_authority = document["successor_authority"]
        successor_rubric = successor_authority["rubric_content"]
        successor_scope = successor_authority["scope_content"]
        schemas.validate("ars://portfolio/assay-rubric-content", successor_rubric, schema_version="1.0.0")
        schemas.validate("ars://portfolio/assay-evidence-scope-content", successor_scope, schema_version="1.0.0")
        validate_successor_authority_semantics(
            predecessor_rubric=contents["rubric"]["content"],
            predecessor_scope=contents["scope"]["content"],
            successor_rubric=successor_rubric,
            successor_scope=successor_scope,
            governed_hashes={
                "SPEC-GATE6-RUN-V1": document["governed_sources"]["route"]["content_sha256"],
                "SPEC-01": document["governed_sources"]["spec_01"]["content_sha256"],
            },
        )
    except (KeyError, TypeError, ValueError, ConfigurationError, SchemaError):
        return False
    proofs = state.get("assay_authority_successor_proofs")
    proof = proofs.get(artefact_id) if isinstance(proofs, Mapping) else None
    if proof != {
        "actor_id": proof.get("actor_id") if isinstance(proof, Mapping) else None,
        "artefact_ref": artefact_ref,
        "document_sha256": artefact_ref.get("content_hash"),
        "git_commit": document.get("git_commit"),
        "governed_sources": document.get("governed_sources"),
        "successor_content_hashes": successor_hashes,
    }:
        return False
    for kind, successor_hash in successor_hashes.items():
        content_state = contents.get(kind)
        content = content_state.get("content") if isinstance(content_state, Mapping) else None
        if (
            not isinstance(content, Mapping)
            or accepted_authority.get(f"{kind}_ref")
            != {
                "id": content.get("record_id"),
                "record_revision": content.get("record_revision"),
                "content_hash": content_state.get("content_sha256"),
            }
            or not _is_lowercase_sha256(successor_hash)
        ):
            return False
    scorecard_ref = correction_document.get("scorecard_ref")
    decision_ref = correction_document.get("decision_ref")
    assays = state.get("assays")
    decisions = state.get("decisions")
    candidates = state.get("candidates")
    assay = (
        assays.get(scorecard_ref.get("id"))
        if isinstance(assays, Mapping) and isinstance(scorecard_ref, Mapping)
        else None
    )
    decision_entry = (
        next(
            (
                (decision_id, item)
                for decision_id, item in decisions.items()
                if isinstance(item, Mapping) and item.get("terminal_event_id") == decision_ref.get("id")
            ),
            None,
        )
        if isinstance(decisions, Mapping) and isinstance(decision_ref, Mapping)
        else None
    )
    decision_id = decision_entry[0] if decision_entry is not None else None
    decision = decision_entry[1] if decision_entry is not None else None
    candidate_id = assay.get("candidate_id") if isinstance(assay, Mapping) else None
    candidate = (
        candidates.get(candidate_id) if isinstance(candidates, Mapping) and isinstance(candidate_id, str) else None
    )
    spec_candidates = (
        [item for item in candidates.values() if _is_spec_route_candidate(state, item)]
        if isinstance(candidates, Mapping)
        else []
    )
    if not (
        isinstance(assay, Mapping)
        and scorecard_ref == {"id": assay.get("assay_id"), "sha256": assay.get("scorecard_sha256")}
        and assay.get("assay_bar_acceptance_sha256") == bar.get("acceptance_sha256")
        and assay.get("producer_relation_sha256") == bar.get("producer_relation_sha256")
        and isinstance(decision, Mapping)
        and decision_ref == {"id": decision_ref.get("id"), "sha256": decision.get("terminal_event_hash")}
        and decision.get("terminal_event_id") == decision_ref.get("id")
        and decision.get("selected_option") == correction_document.get("scientific_disposition")
        and isinstance(candidate, Mapping)
        and len(spec_candidates) == 1
        and spec_candidates[0] is candidate
        and candidate.get("candidate_id") == candidate_id
        and candidate.get("assay_id") == assay.get("assay_id")
        and candidate.get("decision_id") == decision_id
        and candidate.get("revision") == assay.get("candidate_revision")
        and candidate.get("content_sha256") == assay.get("candidate_sha256")
        and candidate.get("status")
        == {"PARK": "parked", "KILL": "killed", "PROMOTE": "spike_planning_authorized"}.get(
            correction_document.get("scientific_disposition")
        )
    ):
        return False
    return True


def _assay_staleness_matches(payload: Mapping[str, Any], state: Mapping[str, Any], *, schemas: Any = None) -> bool:
    """Resolve an OR-109 trigger from either the historical observation or a governed correction."""

    refs = payload.get("trigger_evidence_refs")
    bar = state.get("assay_bar_authority")
    accepted_position = bar.get("accepted_global_position") if isinstance(bar, Mapping) else None
    if type(accepted_position) is not int:
        return False
    trigger = payload.get("source_correction_trigger")
    if trigger is not None:
        return _assay_source_correction_staleness_matches(trigger, refs, state, accepted_position, schemas)
    return _assay_observation_staleness_matches(refs, state, accepted_position)


def _spike_cancellation_matches(
    artifact: Any,
    *,
    payload: Mapping[str, Any],
    candidate: Mapping[str, Any],
    spike: Mapping[str, Any],
    decision: Mapping[str, Any] | None,
    state: Mapping[str, Any],
) -> bool:
    """Validate the closed Spike cancellation subject and its immutable evidence."""

    if not isinstance(artifact, Mapping) or set(artifact) != {
        "spike_id",
        "candidate_ref",
        "plan_ref",
        "attempt_ref",
        "lease_ref",
        "execution_proposal_ref",
        "reason",
        "evidence_refs",
        "completed_scope",
        "unmet_scope",
        "restrictions",
    }:
        return False
    running = spike.get("status") == "running"
    proposal_ref = (
        _record_ref(
            spike.get("decision_id"),
            decision.get("proposal_version"),
            decision.get("proposal_event_hash"),
        )
        if isinstance(decision, Mapping)
        and decision.get("status") in {"proposed", "cancellation_pending", "candidate_cancellation_pending"}
        else None
    )
    evidence_refs = artifact.get("evidence_refs")
    return bool(
        artifact.get("spike_id") == payload.get("spike_id")
        and artifact.get("candidate_ref")
        == _record_ref(candidate.get("candidate_id"), candidate.get("revision"), candidate.get("content_sha256"))
        and artifact.get("plan_ref") == _record_ref(spike.get("spike_id"), 1, spike.get("plan_sha256"))
        and artifact.get("attempt_ref")
        == (_record_ref(spike.get("attempt_id"), 1, spike.get("attempt_sha256")) if running else None)
        and artifact.get("lease_ref")
        == (_record_ref(spike.get("lease_id"), 1, spike.get("lease_sha256")) if running else None)
        and artifact.get("execution_proposal_ref") == proposal_ref
        and isinstance(artifact.get("reason"), str)
        and bool(artifact["reason"])
        and isinstance(evidence_refs, list)
        and bool(evidence_refs)
        and all(_projection_record_ref_matches(state, ref) for ref in evidence_refs)
        and isinstance(artifact.get("completed_scope"), list)
        and isinstance(artifact.get("unmet_scope"), list)
        and bool(artifact["unmet_scope"])
        and isinstance(artifact.get("restrictions"), list)
        and "no_promotion" in artifact["restrictions"]
        and sha256_hex(canonical_bytes(artifact)) == payload.get("cancellation_sha256")
    )


def _spike_execution_ids_available(
    spikes: Mapping[str, Mapping[str, Any]],
    spike_id: Any,
    attempt_id: Any,
    lease_id: Any,
) -> bool:
    """Return whether an Attempt and Lease are unused by every other Spike."""
    return all(
        current_id == spike_id or (spike.get("attempt_id") != attempt_id and spike.get("lease_id") != lease_id)
        for current_id, spike in spikes.items()
    )


def _review_subject_matches(
    review: Any,
    *,
    subject_kind: str,
    subject_id: Any,
    subject_sha256: Any,
) -> bool:
    """Bind a companion lifecycle event to its exact governed review subject."""

    return bool(
        isinstance(review, Mapping)
        and review.get("subject_kind") == subject_kind
        and review.get("subject_id") == subject_id
        and review.get("subject_sha256") == subject_sha256
    )


def _valid_spike_promotion_option(spike: Mapping[str, Any], option: Any) -> bool:
    """Apply the closed reviewed Spike verdict-to-disposition truth table."""

    verdict = spike.get("verdict")
    if verdict == "PASS":
        return option in {"PROMOTE", "PARK", "KILL"}
    if verdict != "FAIL":
        return False
    artifact = spike.get("verdict_artifact")
    kill_conditions = artifact.get("kill_conditions") if isinstance(artifact, Mapping) else None
    triggered_kill = isinstance(kill_conditions, list) and any(
        isinstance(condition, Mapping) and condition.get("status") == "triggered" for condition in kill_conditions
    )
    return option == "KILL" if triggered_kill else option in {"PARK", "KILL"}


def _spike_start_operational_matches(
    operational_events: Iterable[Mapping[str, Any]],
    event: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> bool:
    """Resolve the exact running Attempt, live Lease, and resource identity for a Spike start."""

    try:
        operational = replay_control_plane(operational_events)
        attempt = operational.stream_states.get(payload.get("attempt_id"))
        lease = operational.stream_states.get(payload.get("lease_id"))
        relation = payload.get("execution_authority_relation")
        resource_ref = relation.get("resource_ref") if isinstance(relation, Mapping) else None
        resource = operational.stream_states.get(resource_ref.get("id")) if isinstance(resource_ref, Mapping) else None
        occurred_at = datetime.fromisoformat(str(event.get("occurred_at")).replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(str(lease.get("expires_at")).replace("Z", "+00:00"))
    except (AttributeError, KeyError, TypeError, ValueError):
        return False
    return bool(
        event.get("stream_id") == payload.get("spike_id")
        and isinstance(attempt, Mapping)
        and attempt.get("status") == "running"
        and sha256_hex(canonical_bytes(attempt)) == payload.get("attempt_sha256")
        and attempt.get("lease_id") == payload.get("lease_id")
        and isinstance(lease, Mapping)
        and lease.get("status") == "active"
        and sha256_hex(canonical_bytes(lease)) == payload.get("lease_sha256")
        and lease.get("attempt_id") == payload.get("attempt_id")
        and lease.get("holder_actor_id") == event.get("actor_id")
        and lease.get("resource_grant_id") == payload.get("resource_grant_id")
        and isinstance(resource, Mapping)
        and resource.get("status") == "active"
        and resource_ref == _record_ref(resource_ref.get("id"), 1, sha256_hex(canonical_bytes(resource)))
        and occurred_at.tzinfo is not None
        and expires_at.tzinfo is not None
        and expires_at > occurred_at
    )


def _accepted_dossier_admission_matches(
    authority: Any,
    event: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> bool:
    """Rebind a durable admission envelope to the exact accepted expected-set authority."""

    if not isinstance(authority, Mapping) or authority.get("status") != "accepted":
        return False
    subject = authority.get("subject")
    expected_value = subject.get("expected_set") if isinstance(subject, Mapping) else None
    if not isinstance(expected_value, Mapping):
        return False
    try:
        expected = AcceptedExpectedSet(
            **{
                **expected_value,
                "members": tuple(DossierMember(**member) for member in expected_value["members"]),
            }
        )
    except (KeyError, TypeError, ValueError):
        return False
    observed_members = [
        {
            "member_key": member.member_key,
            "member_kind": member.member_kind,
            "root_id": member.root_id,
            "relative_path": member.relative_path,
            "size_bytes": member.size_bytes,
            "sha256": member.sha256,
            "provenance_id": member.provenance_id,
            "provenance_revision": member.provenance_revision,
            "provenance_hash": member.provenance_hash,
        }
        for member in expected.members
    ]
    return bool(
        accepted_expected_set_hash(expected) == expected.content_hash
        and admission_profile_hash(expected.admission_profile_id, expected.admission_profile_revision)
        == expected.admission_profile_hash
        and event.get("stream_id") == expected.dossier_id
        and payload.get("dossier_id") == expected.dossier_id
        and payload.get("project_id") == expected.project_id
        and payload.get("package_id") == expected.package_id
        and payload.get("package_version") == expected.package_version
        and payload.get("expected_set_id") == expected.expected_set_id
        and payload.get("expected_set_revision") == expected.revision
        and payload.get("expected_set_hash") == expected.content_hash
        and payload.get("admission_profile_id") == expected.admission_profile_id
        and payload.get("admission_profile_revision") == expected.admission_profile_revision
        and payload.get("admission_profile_hash") == expected.admission_profile_hash
        and payload.get("candidate_manifest_hash") == expected.manifest_sha256
        and payload.get("member_count") == len(expected.members)
        and payload.get("member_closure_hash") == canonical_dossier_hash(observed_members)
        and payload.get("provider_execution") == "forbidden"
        and payload.get("ownership_effect") == "successor_owned_new_objects_only"
    )


def _git_blob(data: bytes) -> str:
    """Return the Git blob identity for exact bytes."""
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data,
        usedforsecurity=False,
    ).hexdigest()


def _source_observation_multiset_hash(observation_ids: list[str], observations: Mapping[str, Mapping[str, Any]]) -> str:
    """Hash an exact sorted multiset of resolved source-observation identities."""

    resolved = []
    for observation_id in sorted(observation_ids):
        observation = observations.get(observation_id)
        if not isinstance(observation, Mapping) or not isinstance(observation.get("content_sha256"), str):
            raise IntegrityError("Candidate source observation is not registered")
        resolved.append({"observation_id": observation_id, "content_sha256": observation["content_sha256"]})
    return sha256_hex(canonical_bytes(resolved))


def _review_policy_status(payload: Mapping[str, Any]) -> str:
    """Return the closed W11 review-policy projection status."""

    verdict = payload.get("verdict")
    if verdict == "approve":
        return "satisfied"
    if verdict == "approve_with_conditions":
        conditions = payload.get("conditions")
        if (
            isinstance(conditions, list)
            and conditions
            and all(
                isinstance(condition, dict)
                and condition.get("gate_disposition") == "non_blocking"
                and isinstance(condition.get("owner_actor_id"), str)
                and isinstance(condition.get("policy_id"), str)
                and isinstance(condition.get("evidence_refs"), list)
                and bool(condition["evidence_refs"])
                for condition in conditions
            )
        ):
            return "satisfied"
        return "changes_requested"
    if verdict == "changes_requested":
        return "changes_requested"
    if verdict in {"reject", "unable_to_verify"}:
        return "verdict_recorded"
    if verdict == "withdrawn":
        return "withdrawn"
    raise IntegrityError("invalid Discovery review verdict policy")


def _valid_review_supersession(
    relation: object,
    prior_review: object,
    new_subject_sha256: object,
    new_required_evidence_refs: object,
) -> bool:
    """Validate the closed W11 relation for replacing a non-satisfying review."""

    if not isinstance(relation, Mapping) or not isinstance(prior_review, Mapping):
        return False
    changed_refs = relation.get("changed_evidence_refs")
    delta_scope = relation.get("accepted_delta_scope")
    mode = relation.get("mode")
    prior_status = prior_review.get("status")
    prior_subject = prior_review.get("subject_sha256")
    prior_evidence_refs = prior_review.get("required_evidence_refs")
    same_subject = new_subject_sha256 == prior_subject
    if (
        prior_status not in {"changes_requested", "verdict_recorded", "withdrawn"}
        or relation.get("prior_review_id") != prior_review.get("review_id")
        or relation.get("prior_request_event_id") != prior_review.get("request_event_id")
        or relation.get("prior_request_event_hash") != prior_review.get("request_event_hash")
        or relation.get("prior_verdict_event_id") != prior_review.get("verdict_event_id")
        or relation.get("prior_verdict_event_hash") != prior_review.get("verdict_event_hash")
        or relation.get("prior_subject_sha256") != prior_subject
        or relation.get("new_subject_sha256") != new_subject_sha256
        or not isinstance(changed_refs, list)
        or not changed_refs
        or not all(isinstance(ref, str) and ref for ref in changed_refs)
        or len(set(changed_refs)) != len(changed_refs)
        or not isinstance(prior_evidence_refs, list)
        or not isinstance(new_required_evidence_refs, list)
        or set(changed_refs) & set(prior_evidence_refs)
        or set(new_required_evidence_refs) != {*prior_evidence_refs, *changed_refs}
        or not isinstance(relation.get("reason"), str)
        or not relation["reason"]
        or not isinstance(relation.get("proposed_reviewer_relation"), str)
        or not relation["proposed_reviewer_relation"]
        or mode not in {"superseding_subject", "bounded_delta"}
        or (same_subject and prior_status != "withdrawn")
        or (prior_review.get("verdict") == "reject" and mode != "superseding_subject")
    ):
        return False
    if mode == "bounded_delta":
        return bool(
            relation.get("unchanged_base_sha256") == prior_subject
            and isinstance(delta_scope, list)
            and delta_scope
            and all(isinstance(item, str) and item for item in delta_scope)
            and len(set(delta_scope)) == len(delta_scope)
            and new_subject_sha256
            == sha256_hex(
                canonical_bytes(
                    {
                        "unchanged_base_sha256": prior_subject,
                        "accepted_delta_scope": delta_scope,
                        "changed_evidence_refs": changed_refs,
                    }
                )
            )
        )
    return relation.get("unchanged_base_sha256") is None and relation.get("accepted_delta_scope") is None
