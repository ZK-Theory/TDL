from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError as JsonSchemaError
from jsonschema.validators import extend

from research_system.errors import SchemaError

_AUTHORITY_SCHEMA_IDS = frozenset(
    {
        "ars://core/store-identity/1.1",
        "ars://core/command",
        "ars://core/command/RevokeAuthorityGrant/payload",
        "ars://core/event",
        "ars://core/event/AuthorityRootInitialized/payload",
        "ars://core/event/AuthorityGrantActivated/payload",
        "ars://core/event/AuthorityGrantRevoked/payload",
        "ars://core/event/ReleaseGateDecisionPublished",
    }
)

_RFC3339_DATE_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$")


def _is_rfc3339_date_time(value: object) -> bool:
    """Provide the Draft 2020-12 date-time check when its optional dependency is absent."""
    if not isinstance(value, str):
        # ``format`` is ignored for instance types it does not apply to, so a
        # non-string (e.g. a null ``occurred_at``) conforms vacuously. This
        # mirrors jsonschema's own ``is_datetime``; returning False here made
        # this fallback stricter than the checker it stands in for.
        return True
    if _RFC3339_DATE_TIME.fullmatch(value) is None:
        return False
    normalized = value[:-1] + "+00:00" if value[-1] in "Zz" else value
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return True


if "date-time" not in Draft202012Validator.FORMAT_CHECKER.checkers:
    Draft202012Validator.FORMAT_CHECKER.checks("date-time")(_is_rfc3339_date_time)


def _freeze_json(value: Any) -> Any:
    """Return recursively immutable JSON without mutable built-in subclasses."""
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return _FrozenSequence(_freeze_json(item) for item in value)
    return value


class _FrozenSequence(tuple[Any, ...]):
    """Tuple-backed JSON array with an explicit mutation failure surface."""

    def append(self, _value: Any) -> None:
        raise TypeError("registered schema JSON is immutable")


_IMMUTABLE_SCHEMA_TYPE_CHECKER = Draft202012Validator.TYPE_CHECKER.redefine(
    "object",
    lambda _checker, instance: isinstance(instance, Mapping),
).redefine(
    "array",
    lambda _checker, instance: isinstance(instance, (list, tuple)),
)
_ImmutableSchemaValidator = extend(
    Draft202012Validator,
    type_checker=_IMMUTABLE_SCHEMA_TYPE_CHECKER,
)


@dataclass(frozen=True)
class RegisteredSchema:
    """One immutable record for the exact bytes parsed and validated."""

    schema_id: str
    schema_version: str | None
    raw_bytes_sha256: str
    raw_bytes: bytes
    source_path: Path
    parsed: Mapping[str, Any]

    @property
    def sha256(self) -> str:
        """Compatibility name for the exact raw-byte digest."""
        return self.raw_bytes_sha256


# Compatibility for existing command producers while callers migrate to the
# contract name accepted by 06h/G-RM-9.
SchemaIdentity = RegisteredSchema


@dataclass(frozen=True)
class SchemaBinding:
    """Explicit activation of one exact catalogue entry."""

    schema_id: str
    schema_version: str
    command_type: str | None = None
    event_type: str | None = None
    producer_command_type: str | None = None
    policy_action_type: str | None = None


_RUNTIME_BINDINGS = (
    SchemaBinding("ars://core/command", "1.0.0", command_type="ImportAcceptedW11CatalogueGenesis"),
    SchemaBinding("ars://core/command", "1.0.0", command_type="RegisterCandidate"),
    SchemaBinding("ars://core/command", "1.0.0", command_type="RequestAssay"),
    SchemaBinding("ars://core/command", "1.0.0", command_type="RecordAssayScore"),
    SchemaBinding("ars://core/command", "1.0.0", command_type="RequestDiscoveryOutcomeReview"),
    SchemaBinding("ars://core/command", "1.0.0", command_type="ReviewDiscoveryOutcome"),
    SchemaBinding("ars://core/command", "1.0.0", command_type="ProposePromotionDecision"),
    SchemaBinding("ars://core/command", "1.0.0", command_type="RegisterSpikePlan"),
    SchemaBinding("ars://core/command", "1.0.0", command_type="ProposeSpikeExecutionDecision"),
    SchemaBinding("ars://core/command", "1.0.0", command_type="StartSpike"),
    SchemaBinding("ars://core/command", "1.0.0", command_type="RecordSpikeVerdict"),
    SchemaBinding("ars://core/command", "1.0.0", command_type="RegisterDossierExpectedSetContent"),
    SchemaBinding("ars://core/command", "1.0.0", command_type="RegisterPathRegistrationContent"),
    SchemaBinding("ars://core/command", "1.0.0", command_type="ObserveW11AuthorityFile"),
    SchemaBinding("ars://core/command", "1.0.0", command_type="RequestW11AuthorityReview"),
    SchemaBinding("ars://core/command", "1.0.0", command_type="RecordW11AuthorityReview"),
    SchemaBinding("ars://core/command", "1.0.0", command_type="ProposeW11AuthorityDecision"),
    SchemaBinding("ars://core/command", "1.0.0", command_type="AdmitResearchDossier"),
    SchemaBinding(
        "ars://core/event/ReviewRequested",
        "1.0.0",
        event_type="ReviewRequested",
        producer_command_type="RequestDiscoveryOutcomeReview",
    ),
    SchemaBinding(
        "ars://core/event/ReviewRequested",
        "1.0.0",
        event_type="ReviewRequested",
        producer_command_type="RequestW11AuthorityReview",
    ),
    SchemaBinding(
        "ars://core/event/ReviewVerdictRecorded",
        "1.0.0",
        event_type="ReviewVerdictRecorded",
        producer_command_type="ReviewDiscoveryOutcome",
    ),
    SchemaBinding(
        "ars://core/event/ReviewVerdictRecorded",
        "1.0.0",
        event_type="ReviewVerdictRecorded",
        producer_command_type="RecordW11AuthorityReview",
    ),
    SchemaBinding(
        "ars://core/command/CreateScopeDefinition",
        "1.0.0",
        command_type="CreateScopeDefinition",
    ),
    SchemaBinding(
        "ars://core/event/ScopeDefinitionCreated",
        "1.0.0",
        event_type="ScopeDefinitionCreated",
    ),
    SchemaBinding(
        "ars://core/command/AmendScopeDefinition",
        "1.0.0",
        command_type="AmendScopeDefinition",
    ),
    SchemaBinding(
        "ars://core/event/ScopeDefinitionAmended",
        "1.0.0",
        event_type="ScopeDefinitionAmended",
    ),
    SchemaBinding(
        "ars://core/command/SupersedeScopeDefinition",
        "1.0.0",
        command_type="SupersedeScopeDefinition",
    ),
    SchemaBinding(
        "ars://core/event/ScopeDefinitionSuperseded",
        "1.0.0",
        event_type="ScopeDefinitionSuperseded",
    ),
    SchemaBinding(
        "ars://core/command/CompleteScope",
        "1.0.0",
        command_type="CompleteScope",
    ),
    SchemaBinding(
        "ars://core/event/ScopeCompleted",
        "1.0.0",
        event_type="ScopeCompleted",
        producer_command_type="CompleteScope",
    ),
    SchemaBinding("ars://core/command/AcceptTask", "1.0.0", command_type="AcceptTask"),
    SchemaBinding(
        "ars://core/event/TaskAccepted",
        "1.0.0",
        event_type="TaskAccepted",
        producer_command_type="AcceptTask",
    ),
    SchemaBinding("ars://core/command/RejectTask", "1.0.0", command_type="RejectTask"),
    SchemaBinding(
        "ars://core/event/TaskRejected",
        "1.0.0",
        event_type="TaskRejected",
        producer_command_type="RejectTask",
    ),
    SchemaBinding("ars://core/command/ClosePartial", "1.0.0", command_type="ClosePartial"),
    SchemaBinding(
        "ars://core/event/PartialOutcomeRecorded",
        "1.0.0",
        event_type="PartialOutcomeRecorded",
        producer_command_type="ClosePartial",
    ),
    SchemaBinding("ars://core/command/ReopenTask", "1.0.0", command_type="ReopenTask"),
    SchemaBinding(
        "ars://core/event/TaskReopened",
        "1.0.0",
        event_type="TaskReopened",
        producer_command_type="ReopenTask",
    ),
    SchemaBinding("ars://core/command/AssignReview", "1.0.0", command_type="AssignReview"),
    SchemaBinding(
        "ars://core/event/ReviewAssigned",
        "1.0.0",
        event_type="ReviewAssigned",
        producer_command_type="AssignReview",
    ),
    SchemaBinding("ars://core/command/StartReview", "1.0.0", command_type="StartReview"),
    SchemaBinding(
        "ars://core/event/ReviewStarted",
        "1.0.0",
        event_type="ReviewStarted",
        producer_command_type="StartReview",
    ),
    SchemaBinding(
        "ars://core/command/RecordReviewVerdict",
        "1.0.0",
        command_type="RecordReviewVerdict",
    ),
    SchemaBinding(
        "ars://core/event/ReviewVerdictRecorded",
        "1.0.0",
        event_type="ReviewVerdictRecorded",
        producer_command_type="RecordReviewVerdict",
    ),
    SchemaBinding(
        "ars://core/command/RequestReviewChanges",
        "1.0.0",
        command_type="RequestReviewChanges",
    ),
    SchemaBinding(
        "ars://core/event/ReviewChangesRequested",
        "1.0.0",
        event_type="ReviewChangesRequested",
        producer_command_type="RequestReviewChanges",
    ),
    SchemaBinding("ars://core/command/SatisfyReview", "1.0.0", command_type="SatisfyReview"),
    SchemaBinding(
        "ars://core/event/ReviewSatisfied",
        "1.0.0",
        event_type="ReviewSatisfied",
        producer_command_type="SatisfyReview",
    ),
    SchemaBinding("ars://core/command/WithdrawReview", "1.0.0", command_type="WithdrawReview"),
    SchemaBinding(
        "ars://core/event/ReviewWithdrawn",
        "1.0.0",
        event_type="ReviewWithdrawn",
        producer_command_type="WithdrawReview",
    ),
    SchemaBinding("ars://core/command/SupersedeReview", "1.0.0", command_type="SupersedeReview"),
    SchemaBinding(
        "ars://core/event/ReviewSuperseded",
        "1.0.0",
        event_type="ReviewSuperseded",
        producer_command_type="SupersedeReview",
    ),
    SchemaBinding("ars://core/command/ProposeDecision", "1.0.0", command_type="ProposeDecision"),
    SchemaBinding(
        "ars://core/event/DecisionProposed",
        "1.0.0",
        event_type="DecisionProposed",
        producer_command_type="ProposeDecision",
    ),
    SchemaBinding(
        "ars://core/event/DecisionProposed",
        "1.0.0",
        event_type="DecisionProposed",
        producer_command_type="ProposePromotionDecision",
    ),
    SchemaBinding(
        "ars://core/event/DecisionProposed",
        "1.0.0",
        event_type="DecisionProposed",
        producer_command_type="ProposeSpikeExecutionDecision",
    ),
    SchemaBinding(
        "ars://core/event/DecisionProposed",
        "1.0.0",
        event_type="DecisionProposed",
        producer_command_type="ProposeW11AuthorityDecision",
    ),
    SchemaBinding(
        "ars://core/command/RequestDecisionReview",
        "1.0.0",
        command_type="RequestDecisionReview",
    ),
    SchemaBinding(
        "ars://core/event/DecisionReviewRequested",
        "1.0.0",
        event_type="DecisionReviewRequested",
        producer_command_type="RequestDecisionReview",
    ),
    SchemaBinding("ars://core/command/RejectDecision", "1.0.0", command_type="RejectDecision"),
    SchemaBinding(
        "ars://core/event/DecisionRejected",
        "1.0.0",
        event_type="DecisionRejected",
        producer_command_type="RejectDecision",
    ),
    SchemaBinding("ars://core/command/ExpireDecision", "1.0.0", command_type="ExpireDecision"),
    SchemaBinding(
        "ars://core/event/DecisionExpired",
        "1.0.0",
        event_type="DecisionExpired",
        producer_command_type="ExpireDecision",
    ),
    SchemaBinding("ars://core/command/SupersedeDecision", "1.0.0", command_type="SupersedeDecision"),
    SchemaBinding(
        "ars://core/event/DecisionSuperseded",
        "1.0.0",
        event_type="DecisionSuperseded",
        producer_command_type="SupersedeDecision",
    ),
    SchemaBinding(
        "ars://core/command/RecordRuleEvaluation",
        "1.0.0",
        command_type="RecordRuleEvaluation",
    ),
    SchemaBinding(
        "ars://core/event/RuleEvaluationRecorded",
        "1.0.0",
        event_type="RuleEvaluationRecorded",
        producer_command_type="RecordRuleEvaluation",
    ),
    SchemaBinding("ars://core/command/AmendDecision", "1.0.0", command_type="AmendDecision"),
    SchemaBinding(
        "ars://core/event/DecisionAmendmentProposed",
        "1.0.0",
        event_type="DecisionAmendmentProposed",
        producer_command_type="AmendDecision",
    ),
    SchemaBinding("ars://core/command/RecordCorrection", "1.0.0", command_type="RecordCorrection"),
    SchemaBinding(
        "ars://core/event/RecordCorrected",
        "1.0.0",
        event_type="RecordCorrected",
        producer_command_type="RecordCorrection",
    ),
    SchemaBinding(
        "ars://core/command/CreateTask",
        "1.0.0",
        command_type="CreateTask",
    ),
    SchemaBinding(
        "ars://core/event/TaskCreated",
        "1.0.0",
        event_type="TaskCreated",
    ),
    SchemaBinding(
        "ars://core/command/AmendTask",
        "1.0.0",
        command_type="AmendTask",
    ),
    SchemaBinding(
        "ars://core/event/TaskAmended",
        "1.0.0",
        event_type="TaskAmended",
    ),
    SchemaBinding(
        "ars://core/command/SupersedeTask",
        "1.0.0",
        command_type="SupersedeTask",
    ),
    SchemaBinding(
        "ars://core/event/TaskSuperseded",
        "1.0.0",
        event_type="TaskSuperseded",
    ),
    SchemaBinding(
        "ars://core/command/PublishMessage",
        "1.0.0",
        command_type="PublishMessage",
    ),
    SchemaBinding(
        "ars://core/event/MessagePublished",
        "1.0.0",
        event_type="MessagePublished",
        producer_command_type="PublishMessage",
    ),
    SchemaBinding(
        "ars://core/command/RecordMessageDelivery",
        "1.0.0",
        command_type="RecordMessageDelivery",
    ),
    SchemaBinding(
        "ars://core/event/MessageDelivered",
        "1.0.0",
        event_type="MessageDelivered",
        producer_command_type="RecordMessageDelivery",
    ),
    SchemaBinding(
        "ars://core/command/AcknowledgeMessage",
        "1.0.0",
        command_type="AcknowledgeMessage",
    ),
    SchemaBinding(
        "ars://core/event/MessageAcknowledged",
        "1.0.0",
        event_type="MessageAcknowledged",
        producer_command_type="AcknowledgeMessage",
    ),
    SchemaBinding(
        "ars://core/command/RecordMessageDeliveryFailure",
        "1.0.0",
        command_type="RecordMessageDeliveryFailure",
    ),
    SchemaBinding(
        "ars://core/event/MessageDeliveryFailed",
        "1.0.0",
        event_type="MessageDeliveryFailed",
        producer_command_type="RecordMessageDeliveryFailure",
    ),
    SchemaBinding(
        "ars://core/event/ReleaseGateDecisionPublished",
        "1.1.0",
        event_type="ReleaseGateDecisionPublished",
    ),
    SchemaBinding(
        "ars://core/scoped-authority-grant",
        "2.1.0",
    ),
    SchemaBinding(
        "ars://core/external-assurance-record-scoped-authority-grant",
        "1.0.0",
    ),
    SchemaBinding(
        "ars://core/owner-authority-administration-decision",
        "1.1.0",
    ),
    SchemaBinding(
        "ars://core/external-assurance-record-owner-authority-administration-decision",
        "1.0.0",
    ),
    SchemaBinding(
        "ars://core/policy-action/AcceptR3AssuranceRequirement",
        "1.0.0",
        policy_action_type="accept_r3_assurance_requirement",
    ),
    SchemaBinding(
        "ars://core/policy-action/AcceptOwnerOperatedSessionEvidence",
        "1.0.0",
        policy_action_type="accept_owner_operated_session_evidence",
    ),
    SchemaBinding(
        "ars://core/policy-action/PublishOwnerOperatedSessionReview",
        "1.0.0",
        policy_action_type="publish_owner_operated_session_review",
    ),
    SchemaBinding(
        "ars://core/policy-action/PublishExternalAssuranceRecord",
        "1.0.0",
        policy_action_type="publish_external_assurance_record",
    ),
    SchemaBinding(
        "ars://core/command/ActivateAuthorityGrant",
        "1.1.0",
        command_type="ActivateAuthorityGrant",
    ),
    SchemaBinding(
        "ars://core/command/ActivateExternalAssuranceRecordGrant",
        "1.0.0",
        command_type="ActivateExternalAssuranceRecordGrant",
    ),
    SchemaBinding(
        "ars://core/command/RevokeIssuedAuthorityGrant",
        "1.0.0",
        command_type="RevokeIssuedAuthorityGrant",
    ),
    SchemaBinding(
        "ars://core/command/RevokeExternalAssuranceRecordGrant",
        "1.0.0",
        command_type="RevokeExternalAssuranceRecordGrant",
    ),
    SchemaBinding(
        "ars://core/event/ScopedAuthorityGrantActivated",
        "1.1.0",
        event_type="AuthorityGrantActivated",
        producer_command_type="ActivateAuthorityGrant",
    ),
    SchemaBinding(
        "ars://core/event/ExternalAssuranceRecordGrantActivated",
        "1.0.0",
        event_type="AuthorityGrantActivated",
        producer_command_type="ActivateExternalAssuranceRecordGrant",
    ),
    SchemaBinding(
        "ars://core/event/IssuedAuthorityGrantRevoked",
        "1.1.0",
        event_type="AuthorityGrantRevoked",
        producer_command_type="RevokeIssuedAuthorityGrant",
    ),
    SchemaBinding(
        "ars://core/event/ExternalAssuranceRecordGrantRevoked",
        "1.0.0",
        event_type="AuthorityGrantRevoked",
        producer_command_type="RevokeExternalAssuranceRecordGrant",
    ),
    SchemaBinding(
        "ars://wp6-2/t2/command/IssueCostGrant",
        "1.0.0",
        command_type="IssueCostGrant",
    ),
    SchemaBinding(
        "ars://wp6-2/t2/command/AuthorizeProviderIssue",
        "1.0.0",
        command_type="AuthorizeProviderIssue",
    ),
    SchemaBinding(
        "ars://wp6-2/t2/command/RecordProviderReceipt",
        "1.0.0",
        command_type="RecordProviderReceipt",
    ),
    SchemaBinding(
        "ars://wp6-2/t2/event/CostGrantIssued",
        "1.1.0",
        event_type="CostGrantIssued",
    ),
    SchemaBinding(
        "ars://wp6-2/t2/event/CostGrantReserved",
        "1.1.0",
        event_type="CostGrantReserved",
    ),
    SchemaBinding(
        "ars://wp6-2/t2/event/ProviderCommandIssued",
        "1.1.0",
        event_type="ProviderCommandIssued",
    ),
    SchemaBinding(
        "ars://wp6-2/t2/event/ProviderReceiptRecorded",
        "1.1.0",
        event_type="ProviderReceiptRecorded",
    ),
    SchemaBinding(
        "ars://wp6-2/t2/event/CostGrantReconciled",
        "1.1.0",
        event_type="CostGrantReconciled",
    ),
    SchemaBinding(
        "ars://core/command/RequestReadiness",
        "1.0.0",
        command_type="RequestReadiness",
    ),
    SchemaBinding(
        "ars://core/event/ReadinessRequested",
        "1.0.0",
        event_type="ReadinessRequested",
        producer_command_type="RequestReadiness",
    ),
    SchemaBinding(
        "ars://core/command/ApproveReadiness",
        "1.0.0",
        command_type="ApproveReadiness",
    ),
    SchemaBinding(
        "ars://core/event/ReadinessApproved",
        "1.0.0",
        event_type="ReadinessApproved",
        producer_command_type="ApproveReadiness",
    ),
    SchemaBinding(
        "ars://core/command/BlockTask",
        "1.0.0",
        command_type="BlockTask",
    ),
    SchemaBinding(
        "ars://core/event/TaskBlocked",
        "1.0.0",
        event_type="TaskBlocked",
        producer_command_type="BlockTask",
    ),
    SchemaBinding("ars://core/command/RequestInput", "1.0.0", command_type="RequestInput"),
    SchemaBinding(
        "ars://core/event/InputRequested",
        "1.0.0",
        event_type="InputRequested",
        producer_command_type="RequestInput",
    ),
    SchemaBinding("ars://core/command/PauseTask", "1.0.0", command_type="PauseTask"),
    SchemaBinding(
        "ars://core/event/TaskPaused",
        "1.0.0",
        event_type="TaskPaused",
        producer_command_type="PauseTask",
    ),
    SchemaBinding("ars://core/command/SubmitForReview", "1.0.0", command_type="SubmitForReview"),
    SchemaBinding(
        "ars://core/event/TaskSubmittedForReview",
        "1.0.0",
        event_type="TaskSubmittedForReview",
        producer_command_type="SubmitForReview",
    ),
    SchemaBinding("ars://core/command/ResumeTask", "1.0.0", command_type="ResumeTask"),
    SchemaBinding(
        "ars://core/event/TaskResumed",
        "1.0.0",
        event_type="TaskResumed",
        producer_command_type="ResumeTask",
    ),
    SchemaBinding("ars://core/command/CancelTask", "1.0.0", command_type="CancelTask"),
    SchemaBinding(
        "ars://core/event/TaskCancelled",
        "1.0.0",
        event_type="TaskCancelled",
        producer_command_type="CancelTask",
    ),
    SchemaBinding("ars://core/command/RecordBlocker", "1.0.0", command_type="RecordBlocker"),
    SchemaBinding(
        "ars://core/event/BlockerRecorded",
        "1.0.0",
        event_type="BlockerRecorded",
        producer_command_type="RecordBlocker",
    ),
    SchemaBinding("ars://core/command/ResolveBlocker", "1.0.0", command_type="ResolveBlocker"),
    SchemaBinding(
        "ars://core/event/BlockerResolved",
        "1.0.0",
        event_type="BlockerResolved",
        producer_command_type="ResolveBlocker",
    ),
    SchemaBinding("ars://core/command/FulfilDispatch", "1.0.0", command_type="FulfilDispatch"),
    SchemaBinding(
        "ars://core/event/DispatchFulfilled",
        "1.0.0",
        event_type="DispatchFulfilled",
        producer_command_type="FulfilDispatch",
    ),
    SchemaBinding("ars://core/command/CompleteAttempt", "1.0.0", command_type="CompleteAttempt"),
    SchemaBinding(
        "ars://core/event/AttemptCompleted",
        "1.0.0",
        event_type="AttemptCompleted",
        producer_command_type="CompleteAttempt",
    ),
    SchemaBinding("ars://core/command/FailAttempt", "1.0.0", command_type="FailAttempt"),
    SchemaBinding(
        "ars://core/event/AttemptFailed",
        "1.0.0",
        event_type="AttemptFailed",
        producer_command_type="FailAttempt",
    ),
    SchemaBinding(
        "ars://core/command/RecordAttemptPartial",
        "1.0.0",
        command_type="RecordAttemptPartial",
    ),
    SchemaBinding(
        "ars://core/event/PartialOutcomeRecorded",
        "1.0.0",
        event_type="PartialOutcomeRecorded",
        producer_command_type="RecordAttemptPartial",
    ),
    SchemaBinding("ars://core/command/PauseAttempt", "1.0.0", command_type="PauseAttempt"),
    SchemaBinding(
        "ars://core/event/AttemptPaused",
        "1.0.0",
        event_type="AttemptPaused",
        producer_command_type="PauseAttempt",
    ),
    SchemaBinding("ars://core/command/ResumeAttempt", "1.0.0", command_type="ResumeAttempt"),
    SchemaBinding(
        "ars://core/event/AttemptResumed",
        "1.0.0",
        event_type="AttemptResumed",
        producer_command_type="ResumeAttempt",
    ),
    SchemaBinding(
        "ars://core/command/RequestAttemptStop",
        "1.0.0",
        command_type="RequestAttemptStop",
    ),
    SchemaBinding(
        "ars://core/event/AttemptStopRequested",
        "1.0.0",
        event_type="AttemptStopRequested",
        producer_command_type="RequestAttemptStop",
    ),
    SchemaBinding(
        "ars://core/command/ConfirmAttemptStopped",
        "1.0.0",
        command_type="ConfirmAttemptStopped",
    ),
    SchemaBinding(
        "ars://core/event/AttemptAbandoned",
        "1.0.0",
        event_type="AttemptAbandoned",
        producer_command_type="ConfirmAttemptStopped",
    ),
    SchemaBinding("ars://core/command/SupersedeAttempt", "1.0.0", command_type="SupersedeAttempt"),
    SchemaBinding(
        "ars://core/event/AttemptSuperseded",
        "1.0.0",
        event_type="AttemptSuperseded",
        producer_command_type="SupersedeAttempt",
    ),
    SchemaBinding("ars://core/command/RetryAttempt", "1.0.0", command_type="RetryAttempt"),
    SchemaBinding(
        "ars://core/event/AttemptCreated",
        "1.0.0",
        event_type="AttemptCreated",
        producer_command_type="RetryAttempt",
    ),
    SchemaBinding("ars://core/command/RecordCheckpoint", "1.0.0", command_type="RecordCheckpoint"),
    SchemaBinding(
        "ars://core/event/CheckpointRecorded",
        "1.0.0",
        event_type="CheckpointRecorded",
        producer_command_type="RecordCheckpoint",
    ),
    SchemaBinding("ars://core/command/RequestPause", "1.0.0", command_type="RequestPause"),
    SchemaBinding(
        "ars://core/event/PauseRequested",
        "1.0.0",
        event_type="PauseRequested",
        producer_command_type="RequestPause",
    ),
    SchemaBinding("ars://core/command/ConfirmPause", "1.0.0", command_type="ConfirmPause"),
    SchemaBinding(
        "ars://core/event/PauseConfirmed",
        "1.0.0",
        event_type="PauseConfirmed",
        producer_command_type="ConfirmPause",
    ),
    SchemaBinding("ars://core/command/RequestStop", "1.0.0", command_type="RequestStop"),
    SchemaBinding(
        "ars://core/event/StopRequested",
        "1.0.0",
        event_type="StopRequested",
        producer_command_type="RequestStop",
    ),
    SchemaBinding("ars://core/command/ConfirmStop", "1.0.0", command_type="ConfirmStop"),
    SchemaBinding(
        "ars://core/event/StopConfirmed",
        "1.0.0",
        event_type="StopConfirmed",
        producer_command_type="ConfirmStop",
    ),
    SchemaBinding("ars://core/command/RequestResume", "1.0.0", command_type="RequestResume"),
    SchemaBinding(
        "ars://core/event/ResumeRequested",
        "1.0.0",
        event_type="ResumeRequested",
        producer_command_type="RequestResume",
    ),
    SchemaBinding("ars://core/command/QuarantineOrphan", "1.0.0", command_type="QuarantineOrphan"),
    SchemaBinding(
        "ars://core/event/OrphanQuarantined",
        "1.0.0",
        event_type="OrphanQuarantined",
        producer_command_type="QuarantineOrphan",
    ),
    SchemaBinding("ars://core/command/RequestReview", "1.0.0", command_type="RequestReview"),
    SchemaBinding(
        "ars://core/event/ReviewRequested",
        "1.0.0",
        event_type="ReviewRequested",
        producer_command_type="RequestReview",
    ),
    SchemaBinding(
        "ars://core/command/IssueDispatch",
        "1.0.0",
        command_type="IssueDispatch",
    ),
    SchemaBinding(
        "ars://core/event/DispatchIssued",
        "1.0.0",
        event_type="DispatchIssued",
        producer_command_type="IssueDispatch",
    ),
    SchemaBinding(
        "ars://core/command/RecordDispatchDelivery",
        "1.0.0",
        command_type="RecordDispatchDelivery",
    ),
    SchemaBinding(
        "ars://core/event/DispatchDelivered",
        "1.0.0",
        event_type="DispatchDelivered",
        producer_command_type="RecordDispatchDelivery",
    ),
    SchemaBinding(
        "ars://core/command/AcknowledgeDispatch",
        "1.0.0",
        command_type="AcknowledgeDispatch",
    ),
    SchemaBinding(
        "ars://core/event/DispatchAcknowledged",
        "1.0.0",
        event_type="DispatchAcknowledged",
        producer_command_type="AcknowledgeDispatch",
    ),
    SchemaBinding(
        "ars://core/command/ExpireDispatch",
        "1.0.0",
        command_type="ExpireDispatch",
    ),
    SchemaBinding(
        "ars://core/event/DispatchExpired",
        "1.0.0",
        event_type="DispatchExpired",
        producer_command_type="ExpireDispatch",
    ),
    SchemaBinding(
        "ars://core/command/WithdrawDispatch",
        "1.0.0",
        command_type="WithdrawDispatch",
    ),
    SchemaBinding(
        "ars://core/event/DispatchWithdrawn",
        "1.0.0",
        event_type="DispatchWithdrawn",
        producer_command_type="WithdrawDispatch",
    ),
    SchemaBinding(
        "ars://core/command/ClaimDispatch",
        "1.0.0",
        command_type="ClaimDispatch",
    ),
    SchemaBinding(
        "ars://core/event/DispatchClaimed",
        "1.0.0",
        event_type="DispatchClaimed",
        producer_command_type="ClaimDispatch",
    ),
    SchemaBinding(
        "ars://core/event/TaskClaimStarted",
        "1.0.0",
        event_type="TaskClaimStarted",
        producer_command_type="ClaimDispatch",
    ),
    SchemaBinding(
        "ars://core/command/ClaimExecutionLease",
        "1.0.0",
        command_type="ClaimExecutionLease",
    ),
    SchemaBinding(
        "ars://core/event/LeaseGranted",
        "1.0.0",
        event_type="LeaseGranted",
        producer_command_type="ClaimExecutionLease",
    ),
    SchemaBinding(
        "ars://core/command/RenewExecutionLease",
        "1.0.0",
        command_type="RenewExecutionLease",
    ),
    SchemaBinding(
        "ars://core/event/LeaseRenewed",
        "1.0.0",
        event_type="LeaseRenewed",
        producer_command_type="RenewExecutionLease",
    ),
    SchemaBinding(
        "ars://core/command/ReleaseExecutionLease",
        "1.0.0",
        command_type="ReleaseExecutionLease",
    ),
    SchemaBinding(
        "ars://core/event/LeaseReleased",
        "1.0.0",
        event_type="LeaseReleased",
        producer_command_type="ReleaseExecutionLease",
    ),
    SchemaBinding(
        "ars://core/command/ExpireLease",
        "1.0.0",
        command_type="ExpireLease",
    ),
    SchemaBinding(
        "ars://core/event/LeaseExpired",
        "1.0.0",
        event_type="LeaseExpired",
        producer_command_type="ExpireLease",
    ),
    SchemaBinding(
        "ars://core/command/RevokeLease",
        "1.0.0",
        command_type="RevokeLease",
    ),
    SchemaBinding(
        "ars://core/event/LeaseRevoked",
        "1.0.0",
        event_type="LeaseRevoked",
        producer_command_type="RevokeLease",
    ),
    SchemaBinding(
        "ars://core/command/CreateAttempt",
        "1.0.0",
        command_type="CreateAttempt",
    ),
    SchemaBinding(
        "ars://core/event/AttemptCreated",
        "1.0.0",
        event_type="AttemptCreated",
        producer_command_type="CreateAttempt",
    ),
    SchemaBinding(
        "ars://core/command/ClaimAttempt",
        "1.0.0",
        command_type="ClaimAttempt",
    ),
    SchemaBinding(
        "ars://core/event/AttemptClaimed",
        "1.0.0",
        event_type="AttemptClaimed",
        producer_command_type="ClaimAttempt",
    ),
    SchemaBinding(
        "ars://core/command/StartAttempt",
        "1.0.0",
        command_type="StartAttempt",
    ),
    SchemaBinding(
        "ars://core/event/AttemptStarted",
        "1.0.0",
        event_type="AttemptStarted",
        producer_command_type="StartAttempt",
    ),
    SchemaBinding(
        "ars://core/command/RequestResourceGrant",
        "1.0.0",
        command_type="RequestResourceGrant",
    ),
    SchemaBinding(
        "ars://core/event/ResourceGrantRequested",
        "1.0.0",
        event_type="ResourceGrantRequested",
        producer_command_type="RequestResourceGrant",
    ),
    SchemaBinding(
        "ars://core/command/RecordHeartbeat",
        "1.0.0",
        command_type="RecordHeartbeat",
    ),
    SchemaBinding(
        "ars://core/event/HeartbeatRecorded",
        "1.0.0",
        event_type="HeartbeatRecorded",
        producer_command_type="RecordHeartbeat",
    ),
    SchemaBinding(
        "ars://core/command/ReleaseResources",
        "1.0.0",
        command_type="ReleaseResources",
    ),
    SchemaBinding(
        "ars://core/event/ResourcesReleased",
        "1.0.0",
        event_type="ResourcesReleased",
        producer_command_type="ReleaseResources",
    ),
    SchemaBinding(
        "ars://core/command/CreateBackup",
        "1.0.0",
        command_type="CreateBackup",
    ),
    SchemaBinding(
        "ars://core/event/BackupCreated",
        "1.0.0",
        event_type="BackupCreated",
        producer_command_type="CreateBackup",
    ),
    SchemaBinding(
        "ars://core/command/VerifyRestore",
        "1.0.0",
        command_type="VerifyRestore",
    ),
    SchemaBinding(
        "ars://core/event/RestoreVerified",
        "1.0.0",
        event_type="RestoreVerified",
        producer_command_type="VerifyRestore",
    ),
    SchemaBinding(
        "ars://core/command/RegisterArtefact",
        "1.0.0",
        command_type="RegisterArtefact",
    ),
    SchemaBinding(
        "ars://core/event/ArtefactRegistered",
        "1.0.0",
        event_type="ArtefactRegistered",
        producer_command_type="RegisterArtefact",
    ),
    SchemaBinding("ars://core/command/RecordArtefactAvailability", "1.0.0", command_type="RecordArtefactAvailability"),
    SchemaBinding(
        "ars://core/event/ArtefactAvailabilityRecorded",
        "1.0.0",
        event_type="ArtefactAvailabilityRecorded",
        producer_command_type="RecordArtefactAvailability",
    ),
    SchemaBinding(
        "ars://core/command/RecordArtefactRegenerability", "1.0.0", command_type="RecordArtefactRegenerability"
    ),
    SchemaBinding(
        "ars://core/event/ArtefactRegenerabilityRecorded",
        "1.0.0",
        event_type="ArtefactRegenerabilityRecorded",
        producer_command_type="RecordArtefactRegenerability",
    ),
    SchemaBinding("ars://core/command/RecordArtefactIntegrity", "1.0.0", command_type="RecordArtefactIntegrity"),
    SchemaBinding(
        "ars://core/event/ArtefactIntegrityRecorded",
        "1.0.0",
        event_type="ArtefactIntegrityRecorded",
        producer_command_type="RecordArtefactIntegrity",
    ),
    SchemaBinding("ars://core/command/RecordStructuralValidation", "1.0.0", command_type="RecordStructuralValidation"),
    SchemaBinding(
        "ars://core/event/StructuralValidationRecorded",
        "1.0.0",
        event_type="StructuralValidationRecorded",
        producer_command_type="RecordStructuralValidation",
    ),
    SchemaBinding(
        "ars://core/command/RecordScientificReview",
        "1.0.0",
        command_type="RecordScientificReview",
    ),
    SchemaBinding(
        "ars://core/event/ScientificReviewRecorded",
        "1.0.0",
        event_type="ScientificReviewRecorded",
        producer_command_type="RecordScientificReview",
    ),
    SchemaBinding(
        "ars://core/command/ResolveDecision",
        "1.0.0",
        command_type="ResolveDecision",
    ),
    SchemaBinding(
        "ars://core/event/DecisionResolved",
        "1.0.0",
        event_type="DecisionResolved",
        producer_command_type="ResolveDecision",
    ),
    SchemaBinding(
        "ars://core/command/SetArtefactUseAuthority",
        "1.0.0",
        command_type="SetArtefactUseAuthority",
    ),
    SchemaBinding(
        "ars://core/event/ArtefactUseAuthoritySet",
        "1.0.0",
        event_type="ArtefactUseAuthoritySet",
        producer_command_type="SetArtefactUseAuthority",
    ),
    SchemaBinding("ars://core/command/SupersedeArtefact", "1.0.0", command_type="SupersedeArtefact"),
    SchemaBinding(
        "ars://core/event/ArtefactSuperseded",
        "1.0.0",
        event_type="ArtefactSuperseded",
        producer_command_type="SupersedeArtefact",
    ),
    SchemaBinding("ars://core/command/AdoptLateArtefact", "1.0.0", command_type="AdoptLateArtefact"),
    SchemaBinding(
        "ars://core/event/LateArtefactAdopted",
        "1.0.0",
        event_type="LateArtefactAdopted",
        producer_command_type="AdoptLateArtefact",
    ),
    SchemaBinding("ars://core/command/RequestContextPacket", "1.0.0", command_type="RequestContextPacket"),
    SchemaBinding(
        "ars://core/event/ContextPacketRequested",
        "1.0.0",
        event_type="ContextPacketRequested",
        producer_command_type="RequestContextPacket",
    ),
    SchemaBinding("ars://core/command/BeginContextCompilation", "1.0.0", command_type="BeginContextCompilation"),
    SchemaBinding(
        "ars://core/event/ContextCompilationStarted",
        "1.0.0",
        event_type="ContextCompilationStarted",
        producer_command_type="BeginContextCompilation",
    ),
    SchemaBinding("ars://core/command/CompleteContextCompilation", "1.0.0", command_type="CompleteContextCompilation"),
    SchemaBinding(
        "ars://core/event/ContextPacketCompiled",
        "1.0.0",
        event_type="ContextPacketCompiled",
        producer_command_type="CompleteContextCompilation",
    ),
    SchemaBinding("ars://core/command/ValidateContextPacket", "1.0.0", command_type="ValidateContextPacket"),
    SchemaBinding(
        "ars://core/event/ContextPacketValidated",
        "1.0.0",
        event_type="ContextPacketValidated",
        producer_command_type="ValidateContextPacket",
    ),
    SchemaBinding("ars://core/command/IssueContextPacket", "1.0.0", command_type="IssueContextPacket"),
    SchemaBinding(
        "ars://core/event/ContextPacketIssued",
        "1.0.0",
        event_type="ContextPacketIssued",
        producer_command_type="IssueContextPacket",
    ),
    SchemaBinding("ars://core/command/RecordContextDelivery", "1.0.0", command_type="RecordContextDelivery"),
    SchemaBinding(
        "ars://core/event/ContextPacketDelivered",
        "1.0.0",
        event_type="ContextPacketDelivered",
        producer_command_type="RecordContextDelivery",
    ),
    SchemaBinding("ars://core/command/FailContextPacket", "1.0.0", command_type="FailContextPacket"),
    SchemaBinding(
        "ars://core/event/ContextPacketFailed",
        "1.0.0",
        event_type="ContextPacketFailed",
        producer_command_type="FailContextPacket",
    ),
    SchemaBinding("ars://core/command/ExpireContextPacket", "1.0.0", command_type="ExpireContextPacket"),
    SchemaBinding(
        "ars://core/event/ContextPacketExpired",
        "1.0.0",
        event_type="ContextPacketExpired",
        producer_command_type="ExpireContextPacket",
    ),
    SchemaBinding("ars://core/command/SupersedeContextPacket", "1.0.0", command_type="SupersedeContextPacket"),
    SchemaBinding(
        "ars://core/event/ContextPacketSuperseded",
        "1.0.0",
        event_type="ContextPacketSuperseded",
        producer_command_type="SupersedeContextPacket",
    ),
)


class SchemaRegistry:
    def __init__(
        self,
        root: Path,
        *,
        active_bindings: Iterable[SchemaBinding] = (),
    ) -> None:
        """Load and validate every JSON Schema below a registry root.

        Args:
            root: Directory containing registered ``*.schema.json`` files.
            active_bindings: Exact schema ID/version bindings selected for
                trusted runtime command and event discriminators.

        Raises:
            SchemaError: If a schema is unreadable, invalid, or duplicated; an
                active binding is unknown; or command/event discriminators are
                bound more than once.
        """
        self._schemas: dict[tuple[str, str | None], RegisteredSchema] = {}
        self._schemas_by_id: dict[str, dict[str | None, RegisteredSchema]] = {}
        for path in sorted(root.rglob("*.schema.json")):
            try:
                source_path = path.resolve(strict=True)
                raw_bytes = source_path.read_bytes()
                schema = json.loads(raw_bytes)
                Draft202012Validator.check_schema(schema)
                schema_id = schema["$id"]
                schema_version = schema.get("properties", {}).get("schema_version", {}).get("const")
                if schema_version is not None and not isinstance(schema_version, str):
                    raise TypeError("schema version const must be a string")
            except (
                OSError,
                UnicodeDecodeError,
                json.JSONDecodeError,
                JsonSchemaError,
                KeyError,
                TypeError,
            ) as exc:
                raise SchemaError(f"invalid schema: {path}") from exc
            key = (schema_id, schema_version)
            if key in self._schemas:
                raise SchemaError(f"duplicate schema: {schema_id} version {schema_version}")
            registered = RegisteredSchema(
                schema_id=schema_id,
                schema_version=schema_version,
                raw_bytes_sha256=sha256(raw_bytes).hexdigest(),
                raw_bytes=raw_bytes,
                source_path=source_path,
                parsed=_freeze_json(schema),
            )
            self._schemas[key] = registered
            self._schemas_by_id.setdefault(schema_id, {})[schema_version] = registered
        self._active_bindings = frozenset(active_bindings)
        self._command_bindings: dict[str, SchemaBinding] = {}
        self._policy_action_bindings: dict[str, SchemaBinding] = {}
        self._event_bindings: dict[tuple[str, str | None], SchemaBinding] = {}
        self._producer_bound_event_types: set[str] = set()
        for binding in self._active_bindings:
            self._resolve(binding.schema_id, binding.schema_version)
            if binding.producer_command_type is not None and binding.event_type is None:
                raise SchemaError("producer command binding requires an event discriminator")
            if binding.command_type is not None:
                if binding.command_type in self._command_bindings:
                    raise SchemaError(f"duplicate command binding: {binding.command_type}")
                self._command_bindings[binding.command_type] = binding
            if binding.policy_action_type is not None:
                if binding.policy_action_type in self._policy_action_bindings:
                    raise SchemaError(f"duplicate policy-action binding: {binding.policy_action_type}")
                self._policy_action_bindings[binding.policy_action_type] = binding
            if binding.event_type is not None:
                event_key = (binding.event_type, binding.producer_command_type)
                if event_key in self._event_bindings:
                    producer = binding.producer_command_type or "<any>"
                    raise SchemaError(f"duplicate event binding: {binding.event_type} from {producer}")
                self._event_bindings[event_key] = binding
                if binding.producer_command_type is not None:
                    self._producer_bound_event_types.add(binding.event_type)

    def _resolve(
        self,
        schema_id: str,
        schema_version: str | None = None,
    ) -> RegisteredSchema:
        if schema_version is not None:
            entry = self._schemas.get((schema_id, schema_version))
            if entry is None:
                raise SchemaError(f"unknown schema: {schema_id} version {schema_version}")
            return entry
        versions = self._schemas_by_id.get(schema_id)
        if not versions:
            raise SchemaError(f"unknown schema: {schema_id}")
        if len(versions) != 1:
            raise SchemaError(f"schema version required: {schema_id}")
        return next(iter(versions.values()))

    def validate(
        self,
        schema_id: str,
        value: Any,
        *,
        schema_version: str | None = None,
        expected_sha256: str | None = None,
    ) -> SchemaIdentity:
        """Validate a value against an exact registered schema identifier.

        Args:
            schema_id: Exact ``$id`` of the schema to apply.
            value: JSON-compatible value to validate.
            schema_version: Exact semantic version, required when more than one
                catalogue entry shares ``schema_id``.
            expected_sha256: Recorded exact-source digest that must match.

        Raises:
            SchemaError: If the schema is unknown or the value is invalid.

        Returns:
            Exact raw-source identity of the schema used for validation.
        """
        entry = self._resolve(schema_id, schema_version)
        if expected_sha256 is not None and entry.raw_bytes_sha256 != expected_sha256:
            raise SchemaError(f"schema hash mismatch: {schema_id} version {entry.schema_version}")
        errors = sorted(
            _ImmutableSchemaValidator(
                entry.parsed,
                format_checker=Draft202012Validator.FORMAT_CHECKER,
            ).iter_errors(value),
            key=lambda error: list(error.absolute_path),
        )
        if errors:
            message = "; ".join(
                f"{'.'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}" for error in errors
            )
            raise SchemaError(f"{schema_id}: {message}")
        return entry

    def resolve_identity(
        self,
        schema_id: str,
        schema_version: str,
        *,
        expected_sha256: str | None = None,
    ) -> SchemaIdentity:
        """Resolve an exact version and optionally verify its recorded digest."""
        entry = self._resolve(schema_id, schema_version)
        if expected_sha256 is not None and entry.raw_bytes_sha256 != expected_sha256:
            raise SchemaError(f"schema hash mismatch: {schema_id} version {schema_version}")
        return entry

    def is_active(self, schema_id: str, schema_version: str) -> bool:
        """Return whether the exact version has an explicit runtime binding."""
        return any(
            binding.schema_id == schema_id and binding.schema_version == schema_version
            for binding in self._active_bindings
        )

    @property
    def requires_command_provenance(self) -> bool:
        """Return whether this registry is enforcing explicit runtime bindings."""
        return bool(self._active_bindings)

    def active_bindings(self) -> tuple[SchemaBinding, ...]:
        """Return the complete active binding set in deterministic order."""
        return tuple(
            sorted(
                self._active_bindings,
                key=lambda binding: (
                    binding.schema_id,
                    binding.schema_version,
                    binding.command_type or "",
                    binding.event_type or "",
                    binding.producer_command_type or "",
                    binding.policy_action_type or "",
                ),
            )
        )

    def command_binding(self, command_type: str) -> SchemaBinding | None:
        """Return the active schema selected by a trusted command discriminator."""
        return self._command_bindings.get(command_type)

    def policy_action_binding(
        self,
        policy_action_type: str,
    ) -> SchemaBinding | None:
        """Return the active schema selected by a trusted policy-action name."""
        return self._policy_action_bindings.get(policy_action_type)

    def event_binding(
        self,
        event_type: str,
        producer_command_type: str | None = None,
    ) -> SchemaBinding | None:
        """Return the schema selected by event and optional producer identities."""
        exact = self._event_bindings.get((event_type, producer_command_type))
        if exact is not None:
            return exact
        if producer_command_type is not None and event_type in self._producer_bound_event_types:
            return None
        return self._event_bindings.get((event_type, None))

    def has_producer_bindings(self, event_type: str) -> bool:
        """Return whether an event family requires an exact producer selection."""
        return event_type in self._producer_bound_event_types

    def validate_active(
        self,
        schema_id: str,
        value: Any,
        *,
        schema_version: str,
        expected_sha256: str | None = None,
    ) -> SchemaIdentity:
        """Validate through one explicitly activated schema binding."""
        if not self.is_active(schema_id, schema_version):
            raise SchemaError(f"inactive schema: {schema_id} version {schema_version}")
        return self.validate(
            schema_id,
            value,
            schema_version=schema_version,
            expected_sha256=expected_sha256,
        )

    def contains(self, schema_id: str) -> bool:
        """Return whether an exact schema identifier is registered.

        Args:
            schema_id: Exact ``$id`` to look up.

        Returns:
            Whether the registry contains the identifier.
        """
        return schema_id in self._schemas_by_id


def authority_schema_registry(root: Path) -> SchemaRegistry:
    """Load a registry that supports authority genesis and governed operations.

    Args:
        root: Directory containing the candidate authority schemas.

    Returns:
        A complete authority-capable schema registry.

    Raises:
        SchemaError: If any schema is invalid or a required schema is absent.
    """
    return require_authority_schemas(SchemaRegistry(root))


def require_authority_schemas(registry: SchemaRegistry) -> SchemaRegistry:
    """Require authority genesis and governed-operation schemas on one registry."""
    missing = sorted(schema_id for schema_id in _AUTHORITY_SCHEMA_IDS if not registry.contains(schema_id))
    if missing:
        raise SchemaError(f"authority schema registry is incomplete: {', '.join(missing)}")
    return registry


@lru_cache(maxsize=8)
def _registry_for_resolved_root(root: Path) -> SchemaRegistry:
    return SchemaRegistry(root)


def cached_schema_registry(root: Path | str) -> SchemaRegistry:
    """Return a shared registry for an immutable schema directory.

    Constructing a registry meta-validates every ``*.schema.json`` below the
    root, so callers that validate many documents against one checked-in schema
    tree must not rebuild it per document. Registries are read-only after
    construction, and the schema tree is immutable for the life of a checkout,
    so one instance per resolved root is safe to share.

    Args:
        root: Directory containing registered ``*.schema.json`` files.

    Returns:
        The shared registry for ``root``.

    Raises:
        SchemaError: If a schema is unreadable, invalid, or duplicated.
    """
    return _registry_for_resolved_root(Path(root).resolve())


@lru_cache(maxsize=8)
def _runtime_registry_for_resolved_root(root: Path) -> SchemaRegistry:
    return SchemaRegistry(
        root,
        active_bindings=_RUNTIME_BINDINGS,
    )


def runtime_schema_registry(root: Path | str) -> SchemaRegistry:
    """Load the catalogue with the explicitly accepted runtime bindings."""
    return _runtime_registry_for_resolved_root(Path(root).resolve())


@lru_cache(maxsize=1)
def bundled_schema_registry() -> SchemaRegistry:
    """Return the inert schema catalogue shipped with this code checkout."""
    return SchemaRegistry(Path(__file__).resolve().parent.parent / ".research-system" / "schemas")


@lru_cache(maxsize=1)
def bundled_runtime_schema_registry() -> SchemaRegistry:
    """Return the bundled catalogue with accepted runtime bindings active."""
    return runtime_schema_registry(Path(__file__).resolve().parent.parent / ".research-system" / "schemas")
