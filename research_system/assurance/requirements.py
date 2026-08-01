"""Fail-closed validation for W5 assurance requirements."""

from collections.abc import Mapping, Set
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from research_system.assurance.models import CORE_LANES, AssuranceRequirement
from research_system.authority import (
    GrantedPolicyActionIdentity,
    LedgerAuthorityGrantResolver,
)
from research_system.errors import ArsError, IntegrityError


RISK_ORDER = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}
_INDEPENDENCE_ORDER = {"I0": 0, "I1": 1, "I2": 2}
_R3_ACCEPTANCE_ACTION = "accept_r3_assurance_requirement"


class AssuranceAuthorityPolicy(Protocol):
    """Decides whether an actor holds authority to take an assurance action."""

    def permits(self, actor_id: str, action: str) -> bool:
        """Return whether the actor is authorised to take the action."""


@dataclass(frozen=True)
class DeclaredActionsAuthorityPolicy:
    """Authority policy over a caller-declared actor-to-actions mapping.

    This asserts nothing about whether the actions were ever granted: the mapping is whatever the caller
    passes. It exists as a test seam and for callers that have already resolved authority by some other
    means. Production acceptance paths must use :class:`LedgerBackedAuthorityPolicy`, which derives the
    answer from replayed authority grants instead of taking it on trust.
    """

    granted_actions_by_actor: Mapping[str, Set[str]]

    def permits(self, actor_id: str, action: str) -> bool:
        """Return whether the caller-declared mapping includes an action for an actor."""
        return action in self.granted_actions_by_actor.get(actor_id, frozenset())


@dataclass(frozen=True)
class LedgerBackedAuthorityPolicy:
    """Authority policy backed by replay-resolved authority grants.

    Every answer comes from
    :meth:`~research_system.authority.LedgerAuthorityGrantResolver.resolve_policy_action`,
    so an expired, revoked, wrongly-scoped, or wrongly-attributed grant denies
    the action rather than being absorbed by a mapping the caller assembled.

    Attributes:
        resolver: Replay-backed authority grant resolver.
        grant_ids_by_actor: Grant identity each actor claims authority under.
        policy_action: Exact active policy-action schema identity.
        project_id: Project identity of the governed subject.
        subject_kind: Registered governed subject kind.
        subject_id: Exact governed subject identity.
        now: Trusted local operator time in UTC, used for validity-window checks.
    """

    resolver: LedgerAuthorityGrantResolver
    grant_ids_by_actor: Mapping[str, str]
    policy_action: GrantedPolicyActionIdentity
    project_id: str
    subject_kind: str
    subject_id: str
    now: datetime

    def permits(self, actor_id: str, action: str) -> bool:
        """Return whether a replayed grant authorises an actor to take an action.

        Three resolver outcomes are deliberately kept distinct, because collapsing them loses information
        the caller needs:

        * **Denial** — expired, revoked, wrongly-attributed, or wrongly-scoped grant, or no grant claimed
          for the actor. Returns ``False``: an ordinary, expected answer.
        * **Tampered store evidence** — :class:`~research_system.errors.IntegrityError` propagates. It is an
          ``ArsError`` subclass, so a bare ``except ArsError`` would silently report a corrupted canonical
          history as a routine denial. "The store cannot be trusted" is not "this actor lacks authority",
          and the two must not be reported the same way.
        * **Malformed input** — the resolver raises ``ValueError`` for a bad identity or trusted time. That
          is converted to :class:`~research_system.errors.ArsError` so this policy keeps
          :func:`validate_requirement`'s ArsError-only failure surface rather than leaking a different
          exception type through it.

        Args:
            actor_id: Actor whose authority is in question.
            action: Assurance action, resolved as the grant's allowed policy-action type.

        Returns:
            ``True`` only when a grant resolves for that exact actor, action, and subject scope.

        Raises:
            ArsError: If an identity or the trusted time is malformed.
            IntegrityError: If canonical store evidence fails verification.
        """
        grant_id = self.grant_ids_by_actor.get(actor_id)
        if grant_id is None or action != _R3_ACCEPTANCE_ACTION or action != self.policy_action.policy_action_type:
            return False
        try:
            self.resolver.resolve_policy_action(
                grant_id,
                actor_id,
                "human",
                self.policy_action,
                "R3",
                self.project_id,
                self.subject_kind,
                self.subject_id,
                self.now,
            )
        except IntegrityError:
            raise
        except ArsError:
            return False
        except ValueError as exc:
            raise ArsError(f"malformed authority resolution input: {exc}") from exc
        return True


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
    authority_policy: AssuranceAuthorityPolicy,
) -> None:
    """Validate completeness, risk, independence, and acceptance authority."""
    lanes = {item.lane for item in requirement.lanes}
    if lanes != CORE_LANES or len(requirement.lanes) != len(CORE_LANES):
        raise ArsError("assurance_requirement_incomplete: exact core lanes required")

    for lane in requirement.lanes:
        if lane.disposition == "not_applicable" and (
            not lane.rationale.strip() or not lane.governing_ref_hashes or not lane.reviewer_capabilities
        ):
            raise ArsError("assurance_requirement_incomplete: not_applicable needs rationale and authority")

    try:
        requested = RISK_ORDER[requirement.requested_risk]
        floor = RISK_ORDER[requirement.w5_epistemic_risk_floor]
        semantic = RISK_ORDER[requirement.action_semantic_risk]
        relationship = _INDEPENDENCE_ORDER[requirement.requirement_relationship_grade]
    except KeyError as exc:
        raise ArsError(f"unknown assurance classification: {exc.args[0]}") from exc

    effective = max(requested, semantic)
    if effective >= RISK_ORDER["R2"] and (
        requirement.scope_reviewer_actor_id == requirement.prospective_producer_actor_id
        or relationship < _INDEPENDENCE_ORDER["I1"]
    ):
        raise ArsError("assurance_requirement_scope_unconfirmed")

    if effective >= RISK_ORDER["R3"] and (
        relationship < _INDEPENDENCE_ORDER["I2"]
        or not authority_policy.permits(requirement.accepting_actor_id, _R3_ACCEPTANCE_ACTION)
    ):
        raise ArsError("assurance_requirement_scope_unconfirmed: R3 requires attributed human authority")

    if floor < effective:
        raise ArsError("assurance_requirement_risk_underclassified")
