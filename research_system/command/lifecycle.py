from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex


EXACT_LIFECYCLE_BINDINGS = {
    "ars://core/event/ScopeDefinitionCreated": (
        "ScopeDefinitionCreated",
        "CreateScopeDefinition",
        "ars://core/command/CreateScopeDefinition",
    ),
    "ars://core/event/ScopeDefinitionAmended": (
        "ScopeDefinitionAmended",
        "AmendScopeDefinition",
        "ars://core/command/AmendScopeDefinition",
    ),
    "ars://core/event/ScopeDefinitionSuperseded": (
        "ScopeDefinitionSuperseded",
        "SupersedeScopeDefinition",
        "ars://core/command/SupersedeScopeDefinition",
    ),
    "ars://core/event/TaskCreated": (
        "TaskCreated",
        "CreateTask",
        "ars://core/command/CreateTask",
    ),
    "ars://core/event/TaskAmended": (
        "TaskAmended",
        "AmendTask",
        "ars://core/command/AmendTask",
    ),
    "ars://core/event/TaskSuperseded": (
        "TaskSuperseded",
        "SupersedeTask",
        "ars://core/command/SupersedeTask",
    ),
    "ars://core/event/MessagePublished": (
        "MessagePublished",
        "PublishMessage",
        "ars://core/command/PublishMessage",
    ),
    "ars://core/event/MessageDelivered": (
        "MessageDelivered",
        "RecordMessageDelivery",
        "ars://core/command/RecordMessageDelivery",
    ),
    "ars://core/event/MessageAcknowledged": (
        "MessageAcknowledged",
        "AcknowledgeMessage",
        "ars://core/command/AcknowledgeMessage",
    ),
    "ars://core/event/MessageDeliveryFailed": (
        "MessageDeliveryFailed",
        "RecordMessageDeliveryFailure",
        "ars://core/command/RecordMessageDeliveryFailure",
    ),
    "ars://core/event/ReadinessRequested": (
        "ReadinessRequested",
        "RequestReadiness",
        "ars://core/command/RequestReadiness",
    ),
    "ars://core/event/ReadinessApproved": (
        "ReadinessApproved",
        "ApproveReadiness",
        "ars://core/command/ApproveReadiness",
    ),
    "ars://core/event/TaskBlocked": (
        "TaskBlocked",
        "BlockTask",
        "ars://core/command/BlockTask",
    ),
    "ars://core/event/DispatchIssued": (
        "DispatchIssued",
        "IssueDispatch",
        "ars://core/command/IssueDispatch",
    ),
    "ars://core/event/DispatchDelivered": (
        "DispatchDelivered",
        "RecordDispatchDelivery",
        "ars://core/command/RecordDispatchDelivery",
    ),
    "ars://core/event/DispatchAcknowledged": (
        "DispatchAcknowledged",
        "AcknowledgeDispatch",
        "ars://core/command/AcknowledgeDispatch",
    ),
    "ars://core/event/DispatchExpired": (
        "DispatchExpired",
        "ExpireDispatch",
        "ars://core/command/ExpireDispatch",
    ),
    "ars://core/event/DispatchWithdrawn": (
        "DispatchWithdrawn",
        "WithdrawDispatch",
        "ars://core/command/WithdrawDispatch",
    ),
    "ars://core/event/DispatchClaimed": (
        "DispatchClaimed",
        "ClaimDispatch",
        "ars://core/command/ClaimDispatch",
    ),
    "ars://core/event/TaskClaimStarted": (
        "TaskClaimStarted",
        "ClaimDispatch",
        "ars://core/command/ClaimDispatch",
    ),
    "ars://core/event/LeaseGranted": (
        "LeaseGranted",
        "ClaimExecutionLease",
        "ars://core/command/ClaimExecutionLease",
    ),
    "ars://core/event/LeaseRenewed": (
        "LeaseRenewed",
        "RenewExecutionLease",
        "ars://core/command/RenewExecutionLease",
    ),
    "ars://core/event/LeaseReleased": (
        "LeaseReleased",
        "ReleaseExecutionLease",
        "ars://core/command/ReleaseExecutionLease",
    ),
    "ars://core/event/LeaseExpired": (
        "LeaseExpired",
        "ExpireLease",
        "ars://core/command/ExpireLease",
    ),
    "ars://core/event/LeaseRevoked": (
        "LeaseRevoked",
        "RevokeLease",
        "ars://core/command/RevokeLease",
    ),
    "ars://core/event/AttemptCreated": (
        "AttemptCreated",
        "CreateAttempt",
        "ars://core/command/CreateAttempt",
    ),
    "ars://core/event/AttemptClaimed": (
        "AttemptClaimed",
        "ClaimAttempt",
        "ars://core/command/ClaimAttempt",
    ),
    "ars://core/event/AttemptStarted": (
        "AttemptStarted",
        "StartAttempt",
        "ars://core/command/StartAttempt",
    ),
    "ars://core/event/ResourceGrantRequested": (
        "ResourceGrantRequested",
        "RequestResourceGrant",
        "ars://core/command/RequestResourceGrant",
    ),
    "ars://core/event/HeartbeatRecorded": (
        "HeartbeatRecorded",
        "RecordHeartbeat",
        "ars://core/command/RecordHeartbeat",
    ),
    "ars://core/event/ResourcesReleased": (
        "ResourcesReleased",
        "ReleaseResources",
        "ars://core/command/ReleaseResources",
    ),
    "ars://core/event/BackupCreated": (
        "BackupCreated",
        "CreateBackup",
        "ars://core/command/CreateBackup",
    ),
    "ars://core/event/RestoreVerified": (
        "RestoreVerified",
        "VerifyRestore",
        "ars://core/command/VerifyRestore",
    ),
}

_C2_EXACT_LIFECYCLE_BINDINGS = {
    "ars://core/event/InputRequested": ("InputRequested", "RequestInput", "ars://core/command/RequestInput"),
    "ars://core/event/TaskPaused": ("TaskPaused", "PauseTask", "ars://core/command/PauseTask"),
    "ars://core/event/TaskSubmittedForReview": (
        "TaskSubmittedForReview",
        "SubmitForReview",
        "ars://core/command/SubmitForReview",
    ),
    "ars://core/event/TaskResumed": ("TaskResumed", "ResumeTask", "ars://core/command/ResumeTask"),
    "ars://core/event/TaskCancelled": ("TaskCancelled", "CancelTask", "ars://core/command/CancelTask"),
    "ars://core/event/BlockerRecorded": (
        "BlockerRecorded",
        "RecordBlocker",
        "ars://core/command/RecordBlocker",
    ),
    "ars://core/event/BlockerResolved": (
        "BlockerResolved",
        "ResolveBlocker",
        "ars://core/command/ResolveBlocker",
    ),
    "ars://core/event/DispatchFulfilled": (
        "DispatchFulfilled",
        "FulfilDispatch",
        "ars://core/command/FulfilDispatch",
    ),
    "ars://core/event/AttemptCompleted": (
        "AttemptCompleted",
        "CompleteAttempt",
        "ars://core/command/CompleteAttempt",
    ),
    "ars://core/event/AttemptFailed": ("AttemptFailed", "FailAttempt", "ars://core/command/FailAttempt"),
    "ars://core/event/PartialOutcomeRecorded": (
        "PartialOutcomeRecorded",
        "RecordAttemptPartial",
        "ars://core/command/RecordAttemptPartial",
    ),
    "ars://core/event/AttemptPaused": ("AttemptPaused", "PauseAttempt", "ars://core/command/PauseAttempt"),
    "ars://core/event/AttemptResumed": (
        "AttemptResumed",
        "ResumeAttempt",
        "ars://core/command/ResumeAttempt",
    ),
    "ars://core/event/AttemptStopRequested": (
        "AttemptStopRequested",
        "RequestAttemptStop",
        "ars://core/command/RequestAttemptStop",
    ),
    "ars://core/event/AttemptAbandoned": (
        "AttemptAbandoned",
        "ConfirmAttemptStopped",
        "ars://core/command/ConfirmAttemptStopped",
    ),
    "ars://core/event/AttemptSuperseded": (
        "AttemptSuperseded",
        "SupersedeAttempt",
        "ars://core/command/SupersedeAttempt",
    ),
    "ars://core/event/CheckpointRecorded": (
        "CheckpointRecorded",
        "RecordCheckpoint",
        "ars://core/command/RecordCheckpoint",
    ),
    "ars://core/event/PauseRequested": (
        "PauseRequested",
        "RequestPause",
        "ars://core/command/RequestPause",
    ),
    "ars://core/event/PauseConfirmed": (
        "PauseConfirmed",
        "ConfirmPause",
        "ars://core/command/ConfirmPause",
    ),
    "ars://core/event/StopRequested": ("StopRequested", "RequestStop", "ars://core/command/RequestStop"),
    "ars://core/event/StopConfirmed": ("StopConfirmed", "ConfirmStop", "ars://core/command/ConfirmStop"),
    "ars://core/event/ResumeRequested": (
        "ResumeRequested",
        "RequestResume",
        "ars://core/command/RequestResume",
    ),
    "ars://core/event/OrphanQuarantined": (
        "OrphanQuarantined",
        "QuarantineOrphan",
        "ars://core/command/QuarantineOrphan",
    ),
    "ars://core/event/ReviewRequested": (
        "ReviewRequested",
        "RequestReview",
        "ars://core/command/RequestReview",
    ),
}
EXACT_LIFECYCLE_BINDINGS.update(_C2_EXACT_LIFECYCLE_BINDINGS)
EXACT_LIFECYCLE_BINDINGS.update(
    {
        "ars://core/event/ScopeCompleted": (
            "ScopeCompleted",
            "CompleteScope",
            "ars://core/command/CompleteScope",
        ),
        "ars://core/event/TaskAccepted": (
            "TaskAccepted",
            "AcceptTask",
            "ars://core/command/AcceptTask",
        ),
        "ars://core/event/TaskRejected": (
            "TaskRejected",
            "RejectTask",
            "ars://core/command/RejectTask",
        ),
        "ars://core/event/TaskReopened": (
            "TaskReopened",
            "ReopenTask",
            "ars://core/command/ReopenTask",
        ),
        "ars://core/event/ReviewAssigned": (
            "ReviewAssigned",
            "AssignReview",
            "ars://core/command/AssignReview",
        ),
        "ars://core/event/ReviewStarted": (
            "ReviewStarted",
            "StartReview",
            "ars://core/command/StartReview",
        ),
        "ars://core/event/ReviewVerdictRecorded": (
            "ReviewVerdictRecorded",
            "RecordReviewVerdict",
            "ars://core/command/RecordReviewVerdict",
        ),
        "ars://core/event/ReviewChangesRequested": (
            "ReviewChangesRequested",
            "RequestReviewChanges",
            "ars://core/command/RequestReviewChanges",
        ),
        "ars://core/event/ReviewSatisfied": (
            "ReviewSatisfied",
            "SatisfyReview",
            "ars://core/command/SatisfyReview",
        ),
        "ars://core/event/ReviewWithdrawn": (
            "ReviewWithdrawn",
            "WithdrawReview",
            "ars://core/command/WithdrawReview",
        ),
        "ars://core/event/ReviewSuperseded": (
            "ReviewSuperseded",
            "SupersedeReview",
            "ars://core/command/SupersedeReview",
        ),
        "ars://core/event/DecisionProposed": (
            "DecisionProposed",
            "ProposeDecision",
            "ars://core/command/ProposeDecision",
        ),
        "ars://core/event/DecisionReviewRequested": (
            "DecisionReviewRequested",
            "RequestDecisionReview",
            "ars://core/command/RequestDecisionReview",
        ),
        "ars://core/event/DecisionResolved": (
            "DecisionResolved",
            "ResolveDecision",
            "ars://core/command/ResolveDecision",
        ),
        "ars://core/event/ArtefactRegistered": (
            "ArtefactRegistered",
            "RegisterArtefact",
            "ars://core/command/RegisterArtefact",
        ),
        "ars://core/event/ArtefactAvailabilityRecorded": (
            "ArtefactAvailabilityRecorded",
            "RecordArtefactAvailability",
            "ars://core/command/RecordArtefactAvailability",
        ),
        "ars://core/event/ArtefactRegenerabilityRecorded": (
            "ArtefactRegenerabilityRecorded",
            "RecordArtefactRegenerability",
            "ars://core/command/RecordArtefactRegenerability",
        ),
        "ars://core/event/ArtefactIntegrityRecorded": (
            "ArtefactIntegrityRecorded",
            "RecordArtefactIntegrity",
            "ars://core/command/RecordArtefactIntegrity",
        ),
        "ars://core/event/StructuralValidationRecorded": (
            "StructuralValidationRecorded",
            "RecordStructuralValidation",
            "ars://core/command/RecordStructuralValidation",
        ),
        "ars://core/event/ScientificReviewRecorded": (
            "ScientificReviewRecorded",
            "RecordScientificReview",
            "ars://core/command/RecordScientificReview",
        ),
        "ars://core/event/ArtefactUseAuthoritySet": (
            "ArtefactUseAuthoritySet",
            "SetArtefactUseAuthority",
            "ars://core/command/SetArtefactUseAuthority",
        ),
        "ars://core/event/ArtefactSuperseded": (
            "ArtefactSuperseded",
            "SupersedeArtefact",
            "ars://core/command/SupersedeArtefact",
        ),
        "ars://core/event/LateArtefactAdopted": (
            "LateArtefactAdopted",
            "AdoptLateArtefact",
            "ars://core/command/AdoptLateArtefact",
        ),
        "ars://core/event/DecisionRejected": (
            "DecisionRejected",
            "RejectDecision",
            "ars://core/command/RejectDecision",
        ),
        "ars://core/event/DecisionExpired": (
            "DecisionExpired",
            "ExpireDecision",
            "ars://core/command/ExpireDecision",
        ),
        "ars://core/event/DecisionSuperseded": (
            "DecisionSuperseded",
            "SupersedeDecision",
            "ars://core/command/SupersedeDecision",
        ),
        "ars://core/event/RuleEvaluationRecorded": (
            "RuleEvaluationRecorded",
            "RecordRuleEvaluation",
            "ars://core/command/RecordRuleEvaluation",
        ),
        "ars://core/event/DecisionAmendmentProposed": (
            "DecisionAmendmentProposed",
            "AmendDecision",
            "ars://core/command/AmendDecision",
        ),
        "ars://core/event/RecordCorrected": (
            "RecordCorrected",
            "RecordCorrection",
            "ars://core/command/RecordCorrection",
        ),
    }
)

_EXACT_LIFECYCLE_PRODUCER_BINDINGS = {
    ("ars://core/event/AttemptCreated", "RetryAttempt"): (
        "AttemptCreated",
        "RetryAttempt",
        "ars://core/command/RetryAttempt",
    ),
    ("ars://core/event/PartialOutcomeRecorded", "ClosePartial"): (
        "PartialOutcomeRecorded",
        "ClosePartial",
        "ars://core/command/ClosePartial",
    ),
    ("ars://core/event/PartialOutcomeRecorded", "RecordSpikeVerdict"): (
        "PartialOutcomeRecorded",
        "RecordSpikeVerdict",
        "ars://core/command",
    ),
    ("ars://core/event/AttemptCompleted", "RecordSpikeVerdict"): (
        "AttemptCompleted",
        "RecordSpikeVerdict",
        "ars://core/command",
    ),
    ("ars://core/event/LeaseReleased", "RecordSpikeVerdict"): (
        "LeaseReleased",
        "RecordSpikeVerdict",
        "ars://core/command",
    ),
    ("ars://core/event/PartialOutcomeRecorded", "CancelDiscoveryEvaluation"): (
        "PartialOutcomeRecorded",
        "CancelDiscoveryEvaluation",
        "ars://core/command",
    ),
    ("ars://core/event/LeaseReleased", "CancelDiscoveryEvaluation"): (
        "LeaseReleased",
        "CancelDiscoveryEvaluation",
        "ars://core/command",
    ),
}

_MESSAGE_EVENT_SCHEMA_IDS = {
    "MessagePublished": "ars://core/event/MessagePublished",
    "MessageDelivered": "ars://core/event/MessageDelivered",
    "MessageAcknowledged": "ars://core/event/MessageAcknowledged",
    "MessageDeliveryFailed": "ars://core/event/MessageDeliveryFailed",
}

# These payloads are derived from their command payloads rather than copied verbatim.
_DERIVED_COMMAND_PAYLOAD_EVENT_TYPES = frozenset(
    {"TaskClaimStarted", "LeaseExpired", "AttemptCreated", "PartialOutcomeRecorded", "ArtefactUseAuthoritySet"}
)
_DERIVED_PRODUCER_PAYLOAD_EVENTS = frozenset(
    {
        ("AttemptCompleted", "RecordSpikeVerdict"),
        ("LeaseReleased", "RecordSpikeVerdict"),
        ("LeaseReleased", "CancelDiscoveryEvaluation"),
    }
)


def validate_exact_lifecycle_envelope(
    event: Mapping[str, Any],
) -> str | None:
    """Validate provenance carried by an exact lifecycle event.

    Args:
        event: Recorded event envelope to inspect.

    Returns:
        The originating command type for an exact lifecycle event, or ``None``
        for an event outside the exact lifecycle bindings.

    Raises:
        TypeError: If the payload contains a value unsupported by P0 canonical
            JSON.
        ValueError: If an exact event's type, schema identity, command
            provenance, or canonical payload hash is inconsistent.
    """
    event_type = str(event.get("event_type", ""))
    schema_id = str(event.get("schema_id", ""))
    expected_message_schema_id = _MESSAGE_EVENT_SCHEMA_IDS.get(event_type)
    if expected_message_schema_id is not None and schema_id != expected_message_schema_id:
        raise ValueError("Message event requires its exact active schema identity")
    binding = _EXACT_LIFECYCLE_PRODUCER_BINDINGS.get((schema_id, str(event.get("command_type", ""))))
    if binding is None:
        binding = EXACT_LIFECYCLE_BINDINGS.get(schema_id)
    if binding is None:
        return None
    event_type, command_type, command_schema_id = binding
    payload = event.get("payload")
    if (
        event.get("event_type") != event_type
        or event.get("schema_version") != "1.0.0"
        or event.get("command_type") != command_type
        or event.get("command_schema_id") != command_schema_id
        or event.get("command_schema_version") != "1.0.0"
        or (
            event_type not in _DERIVED_COMMAND_PAYLOAD_EVENT_TYPES
            and (event_type, command_type) not in _DERIVED_PRODUCER_PAYLOAD_EVENTS
            and event.get("command_payload_hash") != sha256_hex(canonical_bytes(payload))
        )
    ):
        raise ValueError("exact lifecycle event provenance mismatch")
    return command_type


def content_hash_matches(value: Mapping[str, Any]) -> bool:
    """Check a mapping's recorded hash against its canonical unsigned content.

    Args:
        value: Mapping whose ``content_sha256`` field records the expected hash.

    Returns:
        Whether the recorded hash equals the canonical hash after removing the
        hash field, or ``False`` when the value cannot be hashed canonically.
    """
    recorded = value.get("content_sha256")
    if not isinstance(recorded, str):
        return False
    unsigned = dict(value)
    unsigned.pop("content_sha256", None)
    try:
        return recorded == sha256_hex(canonical_bytes(unsigned))
    except (TypeError, ValueError):
        return False


def changed_task_fields(
    source: Mapping[str, Any],
    replacement: Mapping[str, Any],
) -> set[str]:
    """Return changed Task definition fields excluding revision metadata.

    Args:
        source: Current immutable Task definition.
        replacement: Proposed replacement Task definition.

    Returns:
        Names of fields whose values differ, excluding ``revision`` and
        ``content_sha256``.
    """
    metadata = {"revision", "content_sha256"}
    return {
        field
        for field in source.keys() | replacement.keys()
        if field not in metadata and source.get(field) != replacement.get(field)
    }


def materialize_scope_member_changes(
    current_members: Iterable[Mapping[str, Any]],
    member_changes: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Apply a typed ScopeDefinition member delta to committed membership.

    Args:
        current_members: Materialized members of the current immutable
            ScopeDefinition revision.
        member_changes: Typed additions, disposition changes, or removals.

    Returns:
        The materialized member list with existing order preserved and new
        members appended.

    Raises:
        ValueError: If a removal names an absent member, an existing member is
            named under the wrong kind, or the resulting membership is
            semantically unchanged.
    """
    members = [dict(member) for member in current_members]
    original_members = [dict(member) for member in members]
    member_indexes = {str(member["member_id"]): index for index, member in enumerate(members)}
    removed: set[str] = set()
    additions: list[dict[str, Any]] = []

    for change in member_changes:
        member_id = str(change["member_id"])
        member_kind = str(change["member_kind"])
        disposition = str(change["disposition"])
        index = member_indexes.get(member_id)
        if index is None:
            if disposition == "removed_by_amendment":
                raise ValueError("ScopeDefinitionAmended member change refers to absent member")
            additions.append(
                {
                    "member_id": member_id,
                    "member_kind": member_kind,
                    "required_disposition": disposition,
                }
            )
            continue

        if str(members[index]["member_kind"]) != member_kind:
            raise ValueError("ScopeDefinitionAmended member kind mismatch")
        if disposition == "removed_by_amendment":
            removed.add(member_id)
        else:
            members[index] = {
                "member_id": member_id,
                "member_kind": member_kind,
                "required_disposition": disposition,
            }

    materialized = [member for member in members if str(member["member_id"]) not in removed]
    materialized.extend(additions)
    if materialized == original_members:
        raise ValueError("ScopeDefinitionAmended has no semantic member delta")
    return materialized


def has_unique_member_ids(records: Iterable[Mapping[str, Any]]) -> bool:
    """Return whether every member record has a unique member identity.

    Args:
        records: Member or member-change records to inspect.

    Returns:
        Whether no two records carry the same ``member_id`` value.
    """
    member_ids = [record.get("member_id") for record in records]
    return len(member_ids) == len(set(member_ids))


def validate_scope_completion_members(
    definition: Mapping[str, Any],
    dispositions: Iterable[Mapping[str, Any]],
    streams: Mapping[str, Mapping[str, Any]],
) -> None:
    """Fail closed unless every required member has its declared terminal state."""
    expected = {str(member["member_id"]): member for member in definition.get("members", ())}
    terminal_status = {
        "accepted": "accepted",
        "superseded": "superseded",
        "cancelled": "cancelled",
        "rejected": "rejected",
    }
    for disposition in dispositions:
        member_id = str(disposition["member_id"])
        member = expected.get(member_id)
        if member is None:
            raise ValueError("scope completion contains an undeclared member")
        declared = str(member.get("required_disposition"))
        observed = str(disposition.get("disposition"))
        if observed != declared:
            raise ValueError("scope member disposition differs from its required disposition")
        if observed in {"partial_accepted", "deferred"}:
            raise ValueError("scope member remains unresolved")
        if not disposition.get("completion_evidence_ref"):
            raise ValueError("scope member completion evidence is missing")
        if observed == "removed_by_amendment":
            continue
        expected_status = terminal_status.get(observed)
        current = streams.get(member_id)
        if expected_status is None or not isinstance(current, Mapping) or current.get("status") != expected_status:
            raise ValueError("scope member is not in its declared terminal state")
