"""Immutable W8 identity-bearing records."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionLease:
    execution_lease_id: str
    attempt_id: str
    execution_epoch: int
    profile_id: str
    expires_at: str
    state: str


@dataclass(frozen=True)
class RecoveryEvidence:
    recovery_evidence_id: str
    attempt_id: str
    detected_condition: str
    consumer_restrictions: tuple[str, ...]
    unresolved_uncertainty: tuple[str, ...]
