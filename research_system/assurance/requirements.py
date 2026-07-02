"""Fail-closed validation for W5 assurance requirements."""

from research_system.assurance.models import CORE_LANES, AssuranceRequirement
from research_system.errors import ArsError


_RISK_ORDER = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}
_INDEPENDENCE_ORDER = {"I0": 0, "I1": 1, "I2": 2}
_STEPHEN_ACTOR_IDS = frozenset({"act-stephen", "act_stephen"})


def validate_requirement(requirement: AssuranceRequirement) -> None:
    """Validate scope completeness, risk floor, and acceptance independence."""
    lanes = {item.lane for item in requirement.lanes}
    if lanes != CORE_LANES or len(requirement.lanes) != len(CORE_LANES):
        raise ArsError("assurance_requirement_incomplete: exact core lanes required")

    for lane in requirement.lanes:
        if lane.disposition == "not_applicable" and (
            not lane.rationale.strip()
            or not lane.governing_ref_hashes
            or not lane.reviewer_capabilities
        ):
            raise ArsError(
                "assurance_requirement_incomplete: not_applicable needs rationale and authority"
            )

    try:
        requested = _RISK_ORDER[requirement.requested_risk]
        floor = _RISK_ORDER[requirement.w5_epistemic_risk_floor]
        semantic = _RISK_ORDER[requirement.action_semantic_risk]
        relationship = _INDEPENDENCE_ORDER[
            requirement.requirement_relationship_grade
        ]
    except KeyError as exc:
        raise ArsError(f"unknown assurance classification: {exc.args[0]}") from exc

    effective_risk = max(requested, semantic)
    if effective_risk >= _RISK_ORDER["R2"] and (
        requirement.scope_reviewer_actor_id
        == requirement.prospective_producer_actor_id
        or relationship < _INDEPENDENCE_ORDER["I1"]
    ):
        raise ArsError("assurance_requirement_scope_unconfirmed")

    if effective_risk >= _RISK_ORDER["R3"] and (
        relationship < _INDEPENDENCE_ORDER["I2"]
        or requirement.accepting_actor_id not in _STEPHEN_ACTOR_IDS
    ):
        raise ArsError("assurance_requirement_scope_unconfirmed: R3 requires Stephen")

    if floor < effective_risk:
        raise ArsError("assurance_requirement_risk_underclassified")
