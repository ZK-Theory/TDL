from research_system.assurance.requirements import effective_risk, two_key_decision
from research_system.routing.independence import (
    RelationshipEvidence,
    independence_grade,
)


def test_correlated_actor_session_context_family_is_not_independent():
    evidence = RelationshipEvidence(True, True, True, True, True)
    assert independence_grade(evidence) == "I0"


def test_role_label_change_does_not_change_relationship_grade():
    evidence = RelationshipEvidence(False, False, True, False, False)
    assert independence_grade(evidence) == "I0"


def test_r3_action_raises_floor_even_when_request_says_r2():
    assert effective_risk("R2", "R2", "R1", "R3", "R0") == "R3"


def test_key_a_cannot_compensate_for_missing_key_b():
    assert two_key_decision(key_a=True, key_b=False) == "blocked"


def test_producer_pass_flag_cannot_satisfy_property_grader():
    evidence = {
        "producer_pass_flag": True,
        "independent_property_evidence": None,
    }
    assert (
        two_key_decision(
            key_a=True,
            key_b=bool(evidence["independent_property_evidence"]),
        )
        == "blocked"
    )
