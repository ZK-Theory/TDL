from datetime import UTC, datetime

import pytest

from research_system.assurance.models import (
    CORE_LANES,
    AssuranceRequirement,
    LaneRequirement,
)
from research_system.assurance.requirements import (
    DeclaredActionsAuthorityPolicy,
    LedgerBackedAuthorityPolicy,
    validate_requirement,
)
from research_system.authority import GrantedPolicyActionIdentity
from research_system.errors import ArsError, IntegrityError


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


def test_r3_acceptance_authority_accepts_and_denies_under_a_declared_policy():
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


ACCEPTOR = "act-human-authority"
GRANT_ID = "agr_" + "8" * 32
NOW = datetime(2026, 7, 29, 12, tzinfo=UTC)


class _Resolver:
    """Stand-in for ``resolve_policy_action`` outcomes.

    The grant semantics themselves — expiry, revocation, scope — are already covered against a real store
    in ``integration/test_authority_grant_source.py``. What is untested is the adapter: whether
    ``LedgerBackedAuthorityPolicy`` translates each resolver outcome into the right answer. So this raises
    the outcome under test and asserts the arguments the policy is obliged to pass through.
    """

    def __init__(self, outcome: Exception | None = None) -> None:
        self.outcome = outcome
        self.calls: list[tuple] = []

    def resolve_policy_action(
        self,
        grant_id,
        actor_id,
        actor_class,
        policy_action,
        required_risk,
        project_id,
        subject_kind,
        subject_id,
        now,
    ):
        self.calls.append(
            (
                grant_id,
                actor_id,
                actor_class,
                policy_action,
                required_risk,
                project_id,
                subject_kind,
                subject_id,
                now,
            )
        )
        if self.outcome is not None:
            raise self.outcome
        return object()


POLICY_ACTION = GrantedPolicyActionIdentity(
    "accept_r3_assurance_requirement",
    "ars://core/policy-action/AcceptR3AssuranceRequirement",
    "1.0.0",
    "a" * 64,
)


def _ledger_policy(resolver: _Resolver) -> LedgerBackedAuthorityPolicy:
    return LedgerBackedAuthorityPolicy(
        resolver=resolver,
        grant_ids_by_actor={ACCEPTOR: GRANT_ID},
        policy_action=POLICY_ACTION,
        project_id="prj-under-test",
        subject_kind="assurance_requirement",
        subject_id="asr_" + "7" * 32,
        now=NOW,
    )


def test_ledger_policy_permits_only_on_a_resolved_grant():
    resolver = _Resolver()
    assert _ledger_policy(resolver).permits(ACCEPTOR, "accept_r3_assurance_requirement") is True
    assert resolver.calls == [
        (
            GRANT_ID,
            ACCEPTOR,
            "human",
            POLICY_ACTION,
            "R3",
            "prj-under-test",
            "assurance_requirement",
            "asr_" + "7" * 32,
            NOW,
        )
    ]


def test_ledger_policy_has_no_caller_asserted_actor_class_fields():
    assert "actor_classes_by_actor" not in LedgerBackedAuthorityPolicy.__dataclass_fields__
    assert "actor_class" not in LedgerBackedAuthorityPolicy.__dataclass_fields__


@pytest.mark.parametrize(
    "reason",
    [
        "authority grant expired",
        "authority grant revoked",
        "authority subject scope mismatch",
        "authority actor mismatch",
        "authority policy-action identity mismatch",
    ],
)
def test_ledger_policy_denies_when_the_grant_does_not_resolve(reason):
    """Every ordinary refusal is a denial, not an error — these are expected answers."""
    resolver = _Resolver(ArsError(reason))
    assert _ledger_policy(resolver).permits(ACCEPTOR, "accept_r3_assurance_requirement") is False


def test_ledger_policy_denies_an_actor_claiming_no_grant():
    resolver = _Resolver()
    assert _ledger_policy(resolver).permits("act-someone-else", "accept_r3_assurance_requirement") is False
    assert resolver.calls == [], "an unclaimed actor must not reach the resolver at all"


def test_ledger_policy_does_not_disguise_tampered_evidence_as_denial():
    """IntegrityError subclasses ArsError, so a bare except would report corruption as "no authority"."""
    resolver = _Resolver(IntegrityError("canonical store evidence is invalid"))
    with pytest.raises(IntegrityError):
        _ledger_policy(resolver).permits(ACCEPTOR, "accept_r3_assurance_requirement")


def test_ledger_policy_converts_malformed_input_to_the_ars_error_surface():
    """validate_requirement's callers may assume ArsError; a leaked ValueError breaks that."""
    resolver = _Resolver(ValueError("identity is malformed"))
    with pytest.raises(ArsError, match="malformed authority resolution input"):
        _ledger_policy(resolver).permits(ACCEPTOR, "accept_r3_assurance_requirement")


def test_r3_validation_denies_through_a_ledger_policy_that_cannot_resolve_a_grant():
    """The policy must compose with validate_requirement, not merely satisfy its own unit tests."""
    requirement = _requirement(
        assurance_requirement_id="asr_" + "7" * 32,
        prospective_producer_actor_id="act-producer",
        author_actor_id="act-author",
        scope_reviewer_actor_id="act-reviewer",
        accepting_actor_id=ACCEPTOR,
        requested_risk="R3",
        action_semantic_risk="R3",
        relationship_grade="I2",
    )
    validate_requirement(requirement, _ledger_policy(_Resolver()))
    with pytest.raises(ArsError, match="R3 requires attributed human authority"):
        validate_requirement(requirement, _ledger_policy(_Resolver(ArsError("authority grant expired"))))
