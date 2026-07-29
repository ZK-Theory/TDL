import pytest

from research_system.assurance.models import (
    CORE_LANES,
    AssuranceRequirement,
    LaneRequirement,
)
from research_system.assurance.requirements import (
    DeclaredActionsAuthorityPolicy,
    validate_requirement,
)
from research_system.errors import ArsError


def _requirement(
    assurance_requirement_id,
    prospective_producer_actor_id,
    author_actor_id,
    scope_reviewer_actor_id,
    accepting_actor_id,
    requested_risk="R2",
    action_semantic_risk="R2",
    relationship_grade="I1",
):
    lanes = tuple(
        LaneRequirement(
            lane,
            "required",
            "P0 test",
            ("governing-hash",),
            ("proof-1",),
            ("scientific_review",),
            "blocked",
        )
        for lane in sorted(CORE_LANES)
    )
    return AssuranceRequirement(
        assurance_requirement_id,
        1,
        "a" * 64,
        "tsk_" + "1" * 32,
        1,
        "implementation",
        0,
        "act-owner",
        author_actor_id,
        scope_reviewer_actor_id,
        accepting_actor_id,
        prospective_producer_actor_id,
        "arp-producer",
        requested_risk,
        requested_risk,
        action_semantic_risk,
        relationship_grade,
        lanes,
        (),
        "b" * 64,
    )


def test_assurance_requirement_uses_exact_six_w5_lanes_and_identity():
    assert CORE_LANES == frozenset(
        {
            "topology",
            "stochastic_null",
            "statistical_panel",
            "representation",
            "output_provenance",
            "paper_claim",
        }
    )
    requirement = _requirement(
        assurance_requirement_id="asr_" + "5" * 32,
        prospective_producer_actor_id="act-producer",
        author_actor_id="act-author",
        scope_reviewer_actor_id="act-reviewer",
        accepting_actor_id="act-manager",
    )
    assert {item.lane for item in requirement.lanes} == CORE_LANES


def test_producer_cannot_self_confirm_r2_scope_or_r3_action():
    requirement = _requirement(
        assurance_requirement_id="asr_" + "6" * 32,
        prospective_producer_actor_id="act-producer",
        author_actor_id="act-producer",
        scope_reviewer_actor_id="act-producer",
        accepting_actor_id="act-producer",
        requested_risk="R2",
        action_semantic_risk="R3",
    )
    with pytest.raises(ArsError, match="assurance_requirement_scope_unconfirmed"):
        validate_requirement(
            requirement,
            DeclaredActionsAuthorityPolicy({"act-producer": frozenset({"accept_r3_assurance_requirement"})}),
        )


def test_r3_acceptance_authority_is_resolved_from_grant_policy():
    requirement = _requirement(
        assurance_requirement_id="asr_" + "7" * 32,
        prospective_producer_actor_id="act-producer",
        author_actor_id="act-author",
        scope_reviewer_actor_id="act-reviewer",
        accepting_actor_id="act-human-authority",
        requested_risk="R3",
        action_semantic_risk="R3",
        relationship_grade="I2",
    )
    allowed = DeclaredActionsAuthorityPolicy({"act-human-authority": frozenset({"accept_r3_assurance_requirement"})})
    validate_requirement(requirement, allowed)
    denied = DeclaredActionsAuthorityPolicy({"act-other": frozenset({"accept_r3_assurance_requirement"})})
    with pytest.raises(ArsError, match="R3 requires attributed human authority"):
        validate_requirement(requirement, denied)
