"""Fail-closed validation for W5 assurance requirements."""

from collections.abc import Mapping, Set
from dataclasses import dataclass

from research_system.assurance.models import CORE_LANES, AssuranceRequirement
from research_system.errors import ArsError


RISK_ORDER = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}
_INDEPENDENCE_ORDER = {"I0": 0, "I1": 1, "I2": 2}
_R3_ACCEPTANCE_ACTION = 'accept_r3_assurance_requirement'


@dataclass(frozen=True)
class GrantBackedAuthorityPolicy:
    """Resolve assurance actions from canonical actor grant mappings."""

    granted_actions_by_actor: Mapping[str, Set[str]]

    def permits(self, actor_id: str, action: str) -> bool:
        """Return whether the actor's resolved grants include an action."""
        return action in self.granted_actions_by_actor.get(actor_id, frozenset())


def effective_risk(*risks: str) -> str:
    """Return the strongest declared risk using the frozen W5 ordering."""
    try:
        return max(risks, key=RISK_ORDER.__getitem__)
    except (KeyError, ValueError) as exc:
        raise ArsError("unknown or missing assurance risk") from exc


def two_key_decision(*, key_a: bool, key_b: bool) -> str:
    """Require both structural and scientific validity keys."""
    return "accepted" if key_a and key_b else "blocked"


def validate_requirement(
    requirement: AssuranceRequirement,
    authority_policy: GrantBackedAuthorityPolicy,
) -> None:
    """Validate completeness, risk, independence, and acceptance authority."""
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
        requested = RISK_ORDER[requirement.requested_risk]
        floor = RISK_ORDER[requirement.w5_epistemic_risk_floor]
        semantic = RISK_ORDER[requirement.action_semantic_risk]
        relationship = _INDEPENDENCE_ORDER[
            requirement.requirement_relationship_grade
        ]
    except KeyError as exc:
        raise ArsError(f"unknown assurance classification: {exc.args[0]}") from exc

    effective = max(requested, semantic)
    if effective >= RISK_ORDER["R2"] and (
        requirement.scope_reviewer_actor_id
        == requirement.prospective_producer_actor_id
        or relationship < _INDEPENDENCE_ORDER["I1"]
    ):
        raise ArsError("assurance_requirement_scope_unconfirmed")

    if effective >= RISK_ORDER["R3"] and (
        relationship < _INDEPENDENCE_ORDER["I2"]
        or not authority_policy.permits(
            requirement.accepting_actor_id, _R3_ACCEPTANCE_ACTION
        )
    ):
        raise ArsError(
            "assurance_requirement_scope_unconfirmed: "
            "R3 requires attributed human authority"
        )

    if floor < effective:
        raise ArsError("assurance_requirement_risk_underclassified")
