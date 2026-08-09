from __future__ import annotations

import json
import os
import secrets
import sys
import threading
import time

from collections.abc import Callable, Iterable, Mapping
from copy import deepcopy
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from research_system.authority import (
    AuthorityAdministrationContext,
    EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_ID,
    EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_VERSION,
    GrantedCommandIdentity,
    LedgerAuthorityGrantResolver,
    LifecycleCommandAuthorityEvidence,
    SCOPED_AUTHORITY_ADMISSION_VERSION,
    SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES,
    SCOPED_AUTHORITY_GRANT_SCHEMA_ID,
    SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION,
    ScopedAuthorityGrant,
    ScopedAuthorityGrantResolution,
    validate_scoped_grant_activation,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.lifecycle import (
    changed_task_fields,
    content_hash_matches,
    has_unique_member_ids,
    materialize_scope_member_changes,
    validate_scope_completion_members,
)
from research_system.command.models import Command, Receipt
from research_system.command.t2 import T2_COMMAND_TYPES, T2Receipt, submit_t2
from research_system.errors import (
    ArsError,
    ConflictError,
    IdempotencyConflictError,
    IntegrityError,
    SchemaError,
)
from research_system.evals.release_publication import (
    PublicationEvidenceError,
    ReleasePublicationEvidenceResolver,
    ReleasePublicationRequest,
    VerifiedReleasePublication,
    verify_release_publication,
)
from research_system.ids import new_id, validate_id
from research_system.operations.backups import (
    BackupMaterializer,
    BackupReceipt,
    RestoreAdmissionBundle,
    RestorePreflightResult,
    revalidate_restore_admission_closure,
    restore_admission_bundle_for_result,
    validate_restore_preflight_result,
)
from research_system.operations.resources import (
    RESOURCE_GRANT_V1_1_SCHEMA_ID,
    RESOURCE_GRANT_V1_1_SCHEMA_SHA256,
    RESOURCE_GRANT_V1_1_SCHEMA_VERSION,
    TrustedRuntimeAuthority,
    derive_resource_grant_authority_preimage_ref,
    derive_resource_grant_v1_1_record,
)
from research_system.projection.replay import replay
from research_system.schema_registry import SchemaIdentity, SchemaRegistry
from research_system.store.ledger import (
    EventLedger,
    LedgerSnapshot,
    _take_release_submit_guard,
)
from research_system.store.identity import (
    StoreOriginWitness,
    physical_root_identity,
    validate_approved_origin_witness_path,
    verify_restore_binding_admission,
)
from research_system.store.lock import (
    CompositeWriterLock,
    WriterLock,
    current_process_instance_id,
    inspect_lock,
    remove_stale_lock,
)
from research_system.store.durability import fsync_directory
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore


_release_submit_guard = _take_release_submit_guard()
_ARTEFACT_REVIEW_INDEPENDENCE_ORDER = {"I0": 0, "I1": 1, "I2": 2, "I3": 3}
_CALLER_PROVENANCE_FIELDS = frozenset(
    {
        "command_schema_id",
        "command_schema_version",
        "command_schema_sha256",
    }
)
_TASK_TERMINAL_STATES = frozenset({"accepted", "rejected", "partial", "cancelled", "superseded"})
_SCOPE_COMMAND_TYPES = frozenset(
    {
        "CreateScopeDefinition",
        "AmendScopeDefinition",
        "SupersedeScopeDefinition",
        "CompleteScope",
    }
)
_TASK_REVISION_COMMAND_TYPES = frozenset(
    {
        "CreateTask",
        "AmendTask",
        "SupersedeTask",
    }
)
_MESSAGE_COMMAND_TYPES = frozenset(
    {
        "PublishMessage",
        "RecordMessageDelivery",
        "AcknowledgeMessage",
        "RecordMessageDeliveryFailure",
    }
)
_MESSAGE_ADAPTER_COMMAND_TYPES = frozenset({"RecordMessageDelivery", "RecordMessageDeliveryFailure"})
_C1_TASK_COMMAND_TYPES = frozenset({"RequestReadiness", "ApproveReadiness"})
_C2_TASK_COMMAND_TYPES = frozenset(
    {"BlockTask", "RequestInput", "PauseTask", "SubmitForReview", "ResumeTask", "CancelTask"}
)
_C2_BLOCKER_COMMAND_TYPES = frozenset({"RecordBlocker", "ResolveBlocker"})
_C2_DISPATCH_COMMAND_TYPES = frozenset({"FulfilDispatch"})
_C2_ATTEMPT_COMMAND_TYPES = frozenset(
    {
        "CompleteAttempt",
        "FailAttempt",
        "RecordAttemptPartial",
        "PauseAttempt",
        "ResumeAttempt",
        "RequestAttemptStop",
        "ConfirmAttemptStopped",
        "SupersedeAttempt",
        "RetryAttempt",
    }
)
_C2_CHECKPOINT_COMMAND_TYPES = frozenset({"RecordCheckpoint"})
_C2_OPERATOR_COMMAND_TYPES = frozenset({"RequestPause", "ConfirmPause", "RequestStop", "ConfirmStop", "RequestResume"})
_C2_RECOVERY_COMMAND_TYPES = frozenset({"QuarantineOrphan"})
_C2_REVIEW_COMMAND_TYPES = frozenset({"RequestReview"})
_C2_COMMAND_TYPES = (
    _C2_TASK_COMMAND_TYPES
    | _C2_BLOCKER_COMMAND_TYPES
    | _C2_DISPATCH_COMMAND_TYPES
    | _C2_ATTEMPT_COMMAND_TYPES
    | _C2_CHECKPOINT_COMMAND_TYPES
    | _C2_OPERATOR_COMMAND_TYPES
    | _C2_RECOVERY_COMMAND_TYPES
    | _C2_REVIEW_COMMAND_TYPES
)
_C3_TASK_COMMAND_TYPES = frozenset({"AcceptTask", "RejectTask", "ClosePartial", "ReopenTask"})
_C3_REVIEW_COMMAND_TYPES = frozenset(
    {
        "AssignReview",
        "StartReview",
        "RecordReviewVerdict",
        "RequestReviewChanges",
        "SatisfyReview",
        "WithdrawReview",
        "SupersedeReview",
    }
)
_C3_DECISION_COMMAND_TYPES = frozenset(
    {
        "ProposeDecision",
        "RequestDecisionReview",
        "RejectDecision",
        "ExpireDecision",
        "SupersedeDecision",
        "RecordRuleEvaluation",
        "AmendDecision",
        "RecordCorrection",
    }
)
_C3_COMMAND_TYPES = _C3_TASK_COMMAND_TYPES | _C3_REVIEW_COMMAND_TYPES | _C3_DECISION_COMMAND_TYPES
_C1_DISPATCH_COMMAND_TYPES = frozenset(
    {
        "IssueDispatch",
        "RecordDispatchDelivery",
        "AcknowledgeDispatch",
        "ExpireDispatch",
        "WithdrawDispatch",
        "ClaimDispatch",
    }
)
_C1_LEASE_COMMAND_TYPES = frozenset(
    {
        "ClaimExecutionLease",
        "RenewExecutionLease",
        "ReleaseExecutionLease",
        "ExpireLease",
        "RevokeLease",
        "RecordHeartbeat",
    }
)
_C1_ATTEMPT_COMMAND_TYPES = frozenset({"CreateAttempt", "ClaimAttempt", "StartAttempt"})
_C1_RESOURCE_COMMAND_TYPES = frozenset({"RequestResourceGrant", "ReleaseResources"})
_C1_COMMAND_TYPES = (
    _C1_TASK_COMMAND_TYPES
    | _C1_DISPATCH_COMMAND_TYPES
    | _C1_LEASE_COMMAND_TYPES
    | _C1_ATTEMPT_COMMAND_TYPES
    | _C1_RESOURCE_COMMAND_TYPES
)
_BACKUP_COMMAND_TYPES = frozenset({"CreateBackup"})
_ARTEFACT_AUTHORITY_COMMAND_TYPES = frozenset(
    {
        "RegisterArtefact",
        "RecordScientificReview",
        "ResolveDecision",
        "SetArtefactUseAuthority",
    }
)
_CONTEXT_PACKET_COMMAND_TYPES = frozenset(
    {
        "RequestContextPacket",
        "BeginContextCompilation",
        "CompleteContextCompilation",
        "ValidateContextPacket",
        "IssueContextPacket",
        "RecordContextDelivery",
        "FailContextPacket",
        "ExpireContextPacket",
        "SupersedeContextPacket",
    }
)
_LIFECYCLE_COMMAND_TYPES = (
    _SCOPE_COMMAND_TYPES
    | _TASK_REVISION_COMMAND_TYPES
    | _MESSAGE_COMMAND_TYPES
    | _C1_COMMAND_TYPES
    | _C2_COMMAND_TYPES
    | _C3_COMMAND_TYPES
    | _BACKUP_COMMAND_TYPES
    | _ARTEFACT_AUTHORITY_COMMAND_TYPES
    | _CONTEXT_PACKET_COMMAND_TYPES
)
_COMMAND_EVENT_TYPES = {
    "PublishReleaseGateDecision": "ReleaseGateDecisionPublished",
    "ActivateAuthorityGrant": "AuthorityGrantActivated",
    "ActivateExternalAssuranceRecordGrant": "AuthorityGrantActivated",
    "RevokeAuthorityGrant": "AuthorityGrantRevoked",
    "RevokeIssuedAuthorityGrant": "AuthorityGrantRevoked",
    "RevokeExternalAssuranceRecordGrant": "AuthorityGrantRevoked",
    "CreateScopeDefinition": "ScopeDefinitionCreated",
    "AmendScopeDefinition": "ScopeDefinitionAmended",
    "SupersedeScopeDefinition": "ScopeDefinitionSuperseded",
    "CompleteScope": "ScopeCompleted",
    "CreateTask": "TaskCreated",
    "AmendTask": "TaskAmended",
    "SupersedeTask": "TaskSuperseded",
    "PublishMessage": "MessagePublished",
    "RecordMessageDelivery": "MessageDelivered",
    "AcknowledgeMessage": "MessageAcknowledged",
    "RecordMessageDeliveryFailure": "MessageDeliveryFailed",
    "RequestReadiness": "ReadinessRequested",
    "ApproveReadiness": "ReadinessApproved",
    "BlockTask": "TaskBlocked",
    "RequestInput": "InputRequested",
    "PauseTask": "TaskPaused",
    "SubmitForReview": "TaskSubmittedForReview",
    "ResumeTask": "TaskResumed",
    "CancelTask": "TaskCancelled",
    "RecordBlocker": "BlockerRecorded",
    "ResolveBlocker": "BlockerResolved",
    "FulfilDispatch": "DispatchFulfilled",
    "CompleteAttempt": "AttemptCompleted",
    "FailAttempt": "AttemptFailed",
    "RecordAttemptPartial": "PartialOutcomeRecorded",
    "PauseAttempt": "AttemptPaused",
    "ResumeAttempt": "AttemptResumed",
    "RequestAttemptStop": "AttemptStopRequested",
    "ConfirmAttemptStopped": "AttemptAbandoned",
    "SupersedeAttempt": "AttemptSuperseded",
    "RetryAttempt": "AttemptCreated",
    "RecordCheckpoint": "CheckpointRecorded",
    "RequestPause": "PauseRequested",
    "ConfirmPause": "PauseConfirmed",
    "RequestStop": "StopRequested",
    "ConfirmStop": "StopConfirmed",
    "RequestResume": "ResumeRequested",
    "QuarantineOrphan": "OrphanQuarantined",
    "RequestReview": "ReviewRequested",
    "IssueDispatch": "DispatchIssued",
    "RecordDispatchDelivery": "DispatchDelivered",
    "AcknowledgeDispatch": "DispatchAcknowledged",
    "ExpireDispatch": "DispatchExpired",
    "WithdrawDispatch": "DispatchWithdrawn",
    "ClaimDispatch": "DispatchClaimed",
    "ClaimExecutionLease": "LeaseGranted",
    "RenewExecutionLease": "LeaseRenewed",
    "ReleaseExecutionLease": "LeaseReleased",
    "ExpireLease": "LeaseExpired",
    "RevokeLease": "LeaseRevoked",
    "CreateAttempt": "AttemptCreated",
    "ClaimAttempt": "AttemptClaimed",
    "StartAttempt": "AttemptStarted",
    "RequestResourceGrant": "ResourceGrantRequested",
    "RecordHeartbeat": "HeartbeatRecorded",
    "ReleaseResources": "ResourcesReleased",
    "CreateBackup": "BackupCreated",
    "RegisterArtefact": "ArtefactRegistered",
    "RecordScientificReview": "ScientificReviewRecorded",
    "ResolveDecision": "DecisionResolved",
    "SetArtefactUseAuthority": "ArtefactUseAuthoritySet",
    "AcceptTask": "TaskAccepted",
    "RejectTask": "TaskRejected",
    "ClosePartial": "PartialOutcomeRecorded",
    "ReopenTask": "TaskReopened",
    "AssignReview": "ReviewAssigned",
    "StartReview": "ReviewStarted",
    "RecordReviewVerdict": "ReviewVerdictRecorded",
    "RequestReviewChanges": "ReviewChangesRequested",
    "SatisfyReview": "ReviewSatisfied",
    "WithdrawReview": "ReviewWithdrawn",
    "SupersedeReview": "ReviewSuperseded",
    "ProposeDecision": "DecisionProposed",
    "RequestDecisionReview": "DecisionReviewRequested",
    "RejectDecision": "DecisionRejected",
    "ExpireDecision": "DecisionExpired",
    "SupersedeDecision": "DecisionSuperseded",
    "RecordRuleEvaluation": "RuleEvaluationRecorded",
    "AmendDecision": "DecisionAmendmentProposed",
    "RecordCorrection": "RecordCorrected",
    "RequestContextPacket": "ContextPacketRequested",
    "BeginContextCompilation": "ContextCompilationStarted",
    "CompleteContextCompilation": "ContextPacketCompiled",
    "ValidateContextPacket": "ContextPacketValidated",
    "IssueContextPacket": "ContextPacketIssued",
    "RecordContextDelivery": "ContextPacketDelivered",
    "FailContextPacket": "ContextPacketFailed",
    "ExpireContextPacket": "ContextPacketExpired",
    "SupersedeContextPacket": "ContextPacketSuperseded",
}
_SCOPED_AUTHORITY_ADMIN_COMMAND_TYPES = frozenset(
    {
        "ActivateAuthorityGrant",
        "RevokeIssuedAuthorityGrant",
        "ActivateExternalAssuranceRecordGrant",
        "RevokeExternalAssuranceRecordGrant",
    }
)
_SCOPED_ACTIVATION_COMMAND_TYPES = frozenset(
    {
        "ActivateAuthorityGrant",
        "ActivateExternalAssuranceRecordGrant",
    }
)
_SCOPED_ACTIVATION_MARKER_FIELDS = frozenset(
    {
        "schema_id",
        "schema_version",
        "command_id",
        "command_sha256",
        "command_identity",
        "target_grant_id",
        "target_generation",
        "prepared_identity",
        "object_kind",
        "object_revision",
        "object_existed_before",
        "owner_pid",
        "owner_process_instance_id",
        "object_sha256",
        "object_value",
    }
)
_SCOPED_ACTIVATION_MARKER_BINDING_FIELDS = _SCOPED_ACTIVATION_MARKER_FIELDS - {
    "owner_pid",
    "owner_process_instance_id",
}


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


_T2_AUTHORITY_COORDINATED_COMMAND_TYPES = frozenset(
    {
        "IssueCostGrant",
        "AuthorizeProviderIssue",
    }
)
_AUTHORITY_COORDINATED_COMMAND_TYPES = _LIFECYCLE_COMMAND_TYPES | frozenset(
    {
        "PublishReleaseGateDecision",
        "RevokeAuthorityGrant",
        *_SCOPED_AUTHORITY_ADMIN_COMMAND_TYPES,
        *_T2_AUTHORITY_COORDINATED_COMMAND_TYPES,
    }
)


@dataclass
class _CommandView:
    fingerprint: tuple[tuple[str, int, int], ...]
    batches_by_command_id: dict[str, list[dict[str, Any]]]
    batches_by_scope: dict[
        tuple[str, str, str, str, str | None, str | None, str | None],
        list[dict[str, Any]],
    ]
    base_scopes: set[tuple[str, str, str, str]]
    stream_versions: dict[str, int]

    @classmethod
    def from_snapshot(
        cls,
        snapshot: LedgerSnapshot,
        schemas: SchemaRegistry,
        authority_state_validator: Callable[[dict[str, Any]], None] | None = None,
    ) -> _CommandView:
        replay(
            snapshot.events,
            schema_registry=schemas,
            authority_state_validator=authority_state_validator,
        )
        view = cls(
            snapshot.fingerprint,
            {},
            {},
            set(),
            dict(snapshot.stream_versions),
        )
        batches: dict[str, list[dict[str, Any]]] = {}
        for event in snapshot.events:
            batches.setdefault(event["transaction_id"], []).append(event)
        for batch in batches.values():
            view._index_batch(batch)
        return view

    def extend(
        self,
        events: tuple[dict[str, Any], ...],
        fingerprint: tuple[tuple[str, int, int], ...],
    ) -> None:
        batches: dict[str, list[dict[str, Any]]] = {}
        for event in events:
            batches.setdefault(event["transaction_id"], []).append(event)
            self.stream_versions[event["stream_id"]] = event["stream_version"]
        for batch in batches.values():
            self._index_batch(batch)
        self.fingerprint = fingerprint

    def _index_batch(self, batch: list[dict[str, Any]]) -> None:
        first = batch[0]
        self.batches_by_command_id[first["command_id"]] = batch
        base_scope = (
            first["actor_id"],
            first["authority_grant_id"],
            first["command_type"],
            first["idempotency_key"],
        )
        self.base_scopes.add(base_scope)
        self.batches_by_scope[
            (
                *base_scope,
                first.get("command_schema_id"),
                first.get("command_schema_version"),
                first.get("command_schema_sha256"),
            )
        ] = batch


@dataclass(frozen=True)
class _TaskRevisionEvidence:
    schema_id: str
    definition: dict[str, Any] | None

    @property
    def exact(self) -> bool:
        return self.schema_id in {
            "ars://core/event/TaskCreated",
            "ars://core/event/TaskAmended",
        }


@dataclass(frozen=True)
class _LifecycleAuthorityEvidence:
    binding: dict[str, Any]
    resolution: dict[str, Any] | None
    canonical_resolution: dict[str, Any] | None
    authority_key: str
    denial: str | None = None


@dataclass(frozen=True, slots=True)
class _PreparedRestoreAdmission:
    """The single authority-bound preflight prepared before writer locking."""

    bundle: RestoreAdmissionBundle
    preflight_result_hash: str


@dataclass(frozen=True, slots=True)
class _SubmissionLease:
    """Writer-lock lease plus the one verified ledger snapshot for a submit."""

    writer_lock: CompositeWriterLock
    snapshot: LedgerSnapshot

    def locked_root(self, root: Path) -> Any:
        """Return the underlying lease for one locked root."""
        return self.writer_lock.locked_root(root)


def _validate_moved_restore_source_lineage(
    source_root: Path,
    preflight_result: RestorePreflightResult,
    approved_witness: StoreOriginWitness,
) -> None:
    if not isinstance(preflight_result, RestorePreflightResult):
        raise ArsError("restore source lineage is invalid")
    if not isinstance(preflight_result.source_root, str) or not preflight_result.source_root:
        raise ArsError("restore source lineage is missing")
    try:
        configured_root = source_root.resolve(strict=True)
        preflight_root = Path(preflight_result.source_root).resolve(strict=True)
        witness_root = Path(approved_witness.initial_control_root).resolve(strict=True)
        configured_identity = physical_root_identity(configured_root)
        preflight_identity = physical_root_identity(preflight_root)
        witness_identity = physical_root_identity(witness_root)
    except (ArsError, OSError, RuntimeError, TypeError, ValueError) as exc:
        raise ArsError("restore source lineage identity is unavailable") from exc
    if (
        configured_root != witness_root
        or preflight_root != witness_root
        or configured_identity != approved_witness.initial_physical_root_identity
        or preflight_identity != approved_witness.initial_physical_root_identity
        or witness_identity != approved_witness.initial_physical_root_identity
    ):
        raise ArsError("restore source lineage differs from approved origin witness")


@dataclass(frozen=True)
class MessageAdapterRegistration:
    """An immutable, service-local snapshot entry for one Message adapter."""

    delivery_adapter_id: str
    project_id: str
    registry_revision: str
    registry_content_sha256: str
    status: str
    effective_at: datetime
    expires_at: datetime | None
    applicable_command_types: tuple[str, ...]
    allowed_actor_ids: tuple[str, ...]

    def canonical_content(self) -> dict[str, Any]:
        """Return the immutable content bound by ``registry_content_sha256``."""
        return {
            "delivery_adapter_id": self.delivery_adapter_id,
            "project_id": self.project_id,
            "registry_revision": self.registry_revision,
            "status": self.status,
            "effective_at": self.effective_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "expires_at": (
                None if self.expires_at is None else self.expires_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
            ),
            "applicable_command_types": list(self.applicable_command_types),
            "allowed_actor_ids": list(self.allowed_actor_ids),
        }

    def __post_init__(self) -> None:
        if not isinstance(self.delivery_adapter_id, str) or not self.delivery_adapter_id:
            raise ValueError("message adapter ID must be non-empty")
        validate_id(self.project_id, "project")
        if not isinstance(self.registry_revision, str) or not self.registry_revision:
            raise ValueError("message adapter registry revision must be non-empty")
        if (
            not isinstance(self.registry_content_sha256, str)
            or len(self.registry_content_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.registry_content_sha256)
        ):
            raise ValueError("message adapter registry content hash must be a lowercase SHA-256")
        if self.status not in {"eligible", "suspended", "retired"}:
            raise ValueError("message adapter status is unsupported")
        if type(self.effective_at) is not datetime or self.effective_at.tzinfo is None:
            raise ValueError("message adapter effective_at must be timezone-aware")
        if self.expires_at is not None and (
            type(self.expires_at) is not datetime
            or self.expires_at.tzinfo is None
            or self.expires_at <= self.effective_at
        ):
            raise ValueError("message adapter expiry must follow effective_at")
        if (
            not isinstance(self.applicable_command_types, tuple)
            or not self.applicable_command_types
            or not set(self.applicable_command_types).issubset(_MESSAGE_ADAPTER_COMMAND_TYPES)
            or len(set(self.applicable_command_types)) != len(self.applicable_command_types)
        ):
            raise ValueError("message adapter capabilities must be exact and non-empty")
        if (
            not isinstance(self.allowed_actor_ids, tuple)
            or not self.allowed_actor_ids
            or len(set(self.allowed_actor_ids)) != len(self.allowed_actor_ids)
        ):
            raise ValueError("message adapter allowed actors must be exact and non-empty")
        for actor_id in self.allowed_actor_ids:
            validate_id(actor_id, "actor")
        if self.registry_content_sha256 != sha256_hex(canonical_bytes(self.canonical_content())):
            raise ValueError("message adapter registry content hash does not bind its immutable entry")


class CommandService:
    def __init__(
        self,
        control_root: Path,
        ledger: EventLedger,
        objects: ObjectStore,
        receipts: ReceiptStore,
        schemas: SchemaRegistry,
        *,
        authority_resolver: LedgerAuthorityGrantResolver | None = None,
        release_publication_evidence: ReleasePublicationEvidenceResolver | None = None,
        clock: Callable[[], datetime] | None = None,
        trusted_runtime_authority_provider: Callable[[], TrustedRuntimeAuthority] | None = None,
        release_lock_timeout_seconds: float = 300.0,
        recovery_lock_timeout_seconds: float = 1.0,
        monotonic: Callable[[], float] | None = None,
        lock_wait: Callable[[float], None] | None = None,
        t2_authority_resolver: Callable[[str, str, int], Any | None] | None = None,
        message_adapter_registry: Iterable[MessageAdapterRegistration] | None = None,
        backup_materializer: BackupMaterializer | None = None,
        governing_evidence_resolver: Any | None = None,
    ) -> None:
        if authority_resolver is not None and type(authority_resolver) is not LedgerAuthorityGrantResolver:
            raise TypeError("authority_resolver must be LedgerAuthorityGrantResolver")
        self.control_root = control_root
        self.ledger = ledger
        self.objects = objects
        self.receipts = receipts
        self.schemas = schemas
        self.authority_resolver = authority_resolver
        self.release_publication_evidence = release_publication_evidence
        self.clock = clock or (lambda: datetime.now(UTC))
        if trusted_runtime_authority_provider is not None and not callable(trusted_runtime_authority_provider):
            raise TypeError("trusted_runtime_authority_provider must be callable")
        self._trusted_runtime_authority_provider = trusted_runtime_authority_provider
        if release_lock_timeout_seconds <= 0:
            raise ValueError("release lock timeout must be positive")
        if recovery_lock_timeout_seconds <= 0:
            raise ValueError("recovery lock timeout must be positive")
        self.release_lock_timeout_seconds = release_lock_timeout_seconds
        self.recovery_lock_timeout_seconds = recovery_lock_timeout_seconds
        self._monotonic = monotonic or time.monotonic
        self._lock_wait = lock_wait or time.sleep
        self.t2_authority_resolver = t2_authority_resolver
        if backup_materializer is not None and not isinstance(backup_materializer, BackupMaterializer):
            raise TypeError("backup_materializer must be BackupMaterializer")
        self.backup_materializer = backup_materializer
        self.governing_evidence_resolver = governing_evidence_resolver
        if message_adapter_registry is None:
            self._message_adapter_registry: tuple[MessageAdapterRegistration, ...] = ()
        else:
            snapshot = tuple(message_adapter_registry)
            if any(type(entry) is not MessageAdapterRegistration for entry in snapshot):
                raise TypeError("message adapter registry entries must be MessageAdapterRegistration")
            self._message_adapter_registry = snapshot
        self._t2_authority_root: Path | None = None
        self._t2_authority_identity: tuple[int, int] | None = None
        if t2_authority_resolver is not None:
            (
                self._t2_authority_root,
                self._t2_authority_identity,
            ) = self._freeze_t2_authority_root(t2_authority_resolver)
        self._view: _CommandView | None = None
        self.deletion_manifest_authorizer: (
            Callable[
                [dict[str, Any], str, str],
                dict[str, Any],
            ]
            | None
        ) = None
        self._restore_source_root: Path | None = None
        self._restore_approved_witness: StoreOriginWitness | None = None
        self._restore_approved_witness_path: Path | None = None
        self._restore_preflight_result: RestorePreflightResult | None = None
        self._restore_preflight_rechecker: Callable[[], RestorePreflightResult | RestoreAdmissionBundle] | None = None
        self._restore_admission_sequence_lock = threading.Lock()
        self._recover_scoped_activation_markers()

    def _current_trusted_runtime_authority(self) -> TrustedRuntimeAuthority:
        """Return exactly one current trusted runtime authority binding."""
        provider = self._trusted_runtime_authority_provider
        if provider is None:
            raise IntegrityError("trusted runtime authority provider is unavailable")
        try:
            authority = provider()
        except Exception as exc:
            raise IntegrityError("trusted runtime authority provider failed") from exc
        if type(authority) is not TrustedRuntimeAuthority:
            raise IntegrityError("trusted runtime authority provider returned an invalid binding")
        return authority

    def _scoped_activation_marker_path(self, command_id: str) -> Path:
        return self.control_root / "runtime" / "scoped-authority-activation-recovery" / f"{command_id}.json"

    @staticmethod
    def _scoped_activation_command_identity(
        command: Command,
        command_schema: SchemaIdentity,
    ) -> dict[str, Any]:
        return {
            "envelope": command.envelope,
            "resolved_schema": {
                "schema_id": command_schema.schema_id,
                "schema_version": str(command_schema.schema_version),
                "sha256": command_schema.sha256,
            },
        }

    @classmethod
    def _validate_scoped_activation_marker_command(
        cls,
        marker: dict[str, Any],
        command: Command,
        command_schema: SchemaIdentity,
    ) -> None:
        identity = cls._scoped_activation_command_identity(command, command_schema)
        if marker["command_identity"] != identity or marker["command_sha256"] != sha256_hex(canonical_bytes(identity)):
            raise ConflictError("scoped activation recovery marker conflicts")

    def _validate_scoped_activation_marker_event_schema(self, marker: dict[str, Any]) -> None:
        prepared = marker["prepared_identity"]
        event_binding = self.schemas.event_binding(
            prepared["event_type"],
            prepared["command_type"],
        )
        event_schema_id = event_binding.schema_id if event_binding is not None else "ars://core/event"
        event_schema_version = event_binding.schema_version if event_binding is not None else "1.0.0"
        try:
            event_schema = self.schemas.resolve_identity(event_schema_id, event_schema_version)
        except SchemaError as exc:
            raise ConflictError("scoped activation recovery marker conflicts") from exc
        if (
            prepared["event_schema_id"],
            prepared["event_schema_version"],
            prepared["event_schema_sha256"],
        ) != (
            event_schema.schema_id,
            str(event_schema.schema_version),
            event_schema.sha256,
        ):
            raise ConflictError("scoped activation recovery marker conflicts")

    def _scoped_activation_marker_temporary_paths(self, path: Path) -> tuple[Path, ...]:
        candidates = [path.with_suffix(".json.tmp"), *sorted(path.parent.glob(f".{path.name}.*.tmp"))]
        return tuple(dict.fromkeys(candidates))

    @staticmethod
    def _quarantine_scoped_activation_marker_temp(path: Path) -> None:
        target = path.with_name(f"{path.name}.quarantine")
        while target.exists():
            target = path.with_name(f"{path.name}.{secrets.token_hex(8)}.quarantine")
        try:
            os.replace(path, target)
        except FileNotFoundError:
            return
        except OSError as exc:
            raise IntegrityError("scoped activation recovery marker temporary data cannot be quarantined") from exc
        fsync_directory(target.parent)

    def _write_scoped_activation_marker(
        self,
        command: Command,
        *,
        command_schema: SchemaIdentity,
        existed_before: bool,
    ) -> None:
        payload = command.envelope.get("payload")
        grant = payload.get("new_grant") if isinstance(payload, dict) else None
        if not isinstance(grant, dict):
            raise IntegrityError("scoped activation recovery marker requires a grant object")
        command_identity = self._scoped_activation_command_identity(command, command_schema)
        event_binding = self.schemas.event_binding(
            "AuthorityGrantActivated",
            command.envelope["command_type"],
        )
        event_schema_id = event_binding.schema_id if event_binding is not None else "ars://core/event"
        event_schema_version = event_binding.schema_version if event_binding is not None else "1.0.0"
        event_schema = self.schemas.resolve_identity(event_schema_id, event_schema_version)
        object_sha256 = sha256_hex(canonical_bytes(grant))
        marker = {
            "schema_id": "ars://core/runtime/scoped-authority-activation-recovery",
            "schema_version": "2.0.0",
            "command_id": command.command_id,
            "command_sha256": sha256_hex(canonical_bytes(command_identity)),
            "command_identity": command_identity,
            "target_grant_id": command.target_stream_id,
            "target_generation": {
                "target_stream_id": command.target_stream_id,
                "expected_stream_version": command.expected_stream_version,
                "resulting_stream_version": command.expected_stream_version + 1,
                "object_revision": 1,
            },
            "prepared_identity": {
                "event_type": "AuthorityGrantActivated",
                "event_schema_id": event_schema_id,
                "event_schema_version": event_schema_version,
                "event_schema_sha256": event_schema.sha256,
                "stream_id": command.target_stream_id,
                "stream_version": command.expected_stream_version + 1,
                "command_id": command.command_id,
                "command_type": command.envelope["command_type"],
                "command_schema_id": command_schema.schema_id,
                "command_schema_version": str(command_schema.schema_version),
                "command_schema_sha256": command_schema.sha256,
                "command_payload_hash": command.payload_hash,
                "object_kind": "authority_grant",
                "object_revision": 1,
                "object_sha256": object_sha256,
            },
            "object_kind": "authority_grant",
            "object_revision": 1,
            "object_existed_before": existed_before,
            "owner_pid": os.getpid(),
            "owner_process_instance_id": current_process_instance_id(),
            "object_sha256": object_sha256,
            "object_value": grant,
        }
        data = canonical_bytes(marker)
        path = self._scoped_activation_marker_path(command.command_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        for temporary in self._scoped_activation_marker_temporary_paths(path):
            if not temporary.exists():
                continue
            try:
                existing = self._load_scoped_activation_marker(temporary)
            except IntegrityError:
                self._quarantine_scoped_activation_marker_temp(temporary)
                continue
            if any(existing[field] != marker[field] for field in _SCOPED_ACTIVATION_MARKER_BINDING_FIELDS):
                raise ConflictError("scoped activation recovery marker temporary data conflicts")
            if path.exists():
                temporary.unlink(missing_ok=True)
                fsync_directory(path.parent)
            else:
                os.replace(temporary, path)
                fsync_directory(path.parent)
                return
        if path.exists():
            existing = self._load_scoped_activation_marker(path)
            if any(existing[field] != marker[field] for field in _SCOPED_ACTIVATION_MARKER_BINDING_FIELDS):
                raise ConflictError("scoped activation recovery marker conflicts")
            return
        temporary = path.with_name(f".{path.name}.{secrets.token_hex(16)}.tmp")
        try:
            with temporary.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            fsync_directory(path.parent)
        finally:
            temporary.unlink(missing_ok=True)

    def _cleanup_scoped_activation_marker_residue(
        self,
        residue: list[tuple[Path, dict[str, Any]]],
    ) -> bool:
        changed = False
        for temporary, _existing in residue:
            temporary.unlink(missing_ok=True)
            changed = True
        return changed

    def _remove_scoped_activation_marker(self, command_id: str) -> None:
        path = self._scoped_activation_marker_path(command_id)
        final_marker = self._load_scoped_activation_marker(path) if path.exists() else None
        residue: list[tuple[Path, dict[str, Any]]] = []
        for temporary in self._scoped_activation_marker_temporary_paths(path):
            if not temporary.exists():
                continue
            try:
                existing = self._load_scoped_activation_marker(temporary)
            except IntegrityError as exc:
                raise IntegrityError("scoped activation recovery marker temporary data is invalid") from exc
            if final_marker is None or any(
                existing[field] != final_marker[field] for field in _SCOPED_ACTIVATION_MARKER_BINDING_FIELDS
            ):
                raise ConflictError("scoped activation recovery marker temporary data conflicts")
            residue.append((temporary, existing))
        changed = final_marker is not None
        path.unlink(missing_ok=True)
        if self._cleanup_scoped_activation_marker_residue(residue):
            changed = True
        if changed and path.parent.exists():
            fsync_directory(path.parent)

    @staticmethod
    def _load_scoped_activation_marker(path: Path) -> dict[str, Any]:
        try:
            data = path.read_bytes()
            marker = json.loads(data)
            canonical = canonical_bytes(marker)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise IntegrityError("scoped activation recovery marker is invalid") from exc
        if (
            not isinstance(marker, dict)
            or set(marker) != _SCOPED_ACTIVATION_MARKER_FIELDS
            or data != canonical
            or marker.get("schema_id") != "ars://core/runtime/scoped-authority-activation-recovery"
            or marker.get("schema_version") != "2.0.0"
            or not isinstance(marker.get("command_id"), str)
            or not _is_sha256(marker.get("command_sha256"))
            or not isinstance(marker.get("target_grant_id"), str)
            or marker.get("object_kind") != "authority_grant"
            or marker.get("object_revision") != 1
            or not isinstance(marker.get("object_existed_before"), bool)
            or not isinstance(marker.get("owner_pid"), int)
            or isinstance(marker.get("owner_pid"), bool)
            or marker.get("owner_pid") < 1
            or not isinstance(marker.get("owner_process_instance_id"), str)
            or not marker.get("owner_process_instance_id")
            or not isinstance(marker.get("object_value"), dict)
            or marker.get("object_sha256") != sha256_hex(canonical_bytes(marker.get("object_value")))
        ):
            raise IntegrityError("scoped activation recovery marker is invalid")
        identity = marker["command_identity"]
        resolved_schema = identity.get("resolved_schema") if isinstance(identity, dict) else None
        envelope = identity.get("envelope") if isinstance(identity, dict) else None
        if (
            not isinstance(identity, dict)
            or set(identity) != {"envelope", "resolved_schema"}
            or not isinstance(envelope, dict)
            or not isinstance(resolved_schema, dict)
            or set(resolved_schema) != {"schema_id", "schema_version", "sha256"}
            or not isinstance(resolved_schema.get("schema_id"), str)
            or not isinstance(resolved_schema.get("schema_version"), str)
            or not _is_sha256(resolved_schema.get("sha256"))
            or marker["command_sha256"] != sha256_hex(canonical_bytes(identity))
            or envelope.get("command_id") != marker["command_id"]
            or envelope.get("target_stream_id") != marker["target_grant_id"]
        ):
            raise IntegrityError("scoped activation recovery marker command identity is invalid")
        generation = marker["target_generation"]
        if (
            not isinstance(generation, dict)
            or set(generation)
            != {"target_stream_id", "expected_stream_version", "resulting_stream_version", "object_revision"}
            or generation.get("target_stream_id") != marker["target_grant_id"]
            or not isinstance(generation.get("expected_stream_version"), int)
            or isinstance(generation.get("expected_stream_version"), bool)
            or generation.get("expected_stream_version") < 0
            or generation.get("resulting_stream_version") != generation.get("expected_stream_version") + 1
            or generation.get("object_revision") != marker["object_revision"]
        ):
            raise IntegrityError("scoped activation recovery marker target generation is invalid")
        prepared = marker["prepared_identity"]
        try:
            expected_payload_hash = sha256_hex(canonical_bytes(envelope["payload"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError("scoped activation recovery marker command payload is invalid") from exc
        if (
            not isinstance(prepared, dict)
            or set(prepared)
            != {
                "event_type",
                "event_schema_id",
                "event_schema_version",
                "event_schema_sha256",
                "stream_id",
                "stream_version",
                "command_id",
                "command_type",
                "command_schema_id",
                "command_schema_version",
                "command_schema_sha256",
                "command_payload_hash",
                "object_kind",
                "object_revision",
                "object_sha256",
            }
            or prepared.get("event_type") != "AuthorityGrantActivated"
            or not isinstance(prepared.get("event_schema_id"), str)
            or not isinstance(prepared.get("event_schema_version"), str)
            or not _is_sha256(prepared.get("event_schema_sha256"))
            or prepared.get("stream_id") != marker["target_grant_id"]
            or prepared.get("stream_version") != generation["resulting_stream_version"]
            or prepared.get("command_id") != marker["command_id"]
            or prepared.get("command_type") != envelope.get("command_type")
            or prepared.get("command_schema_id") != resolved_schema["schema_id"]
            or prepared.get("command_schema_version") != resolved_schema["schema_version"]
            or prepared.get("command_schema_sha256") != resolved_schema["sha256"]
            or prepared.get("command_payload_hash") != expected_payload_hash
            or prepared.get("object_kind") != marker["object_kind"]
            or prepared.get("object_revision") != marker["object_revision"]
            or prepared.get("object_sha256") != marker["object_sha256"]
        ):
            raise IntegrityError("scoped activation recovery marker prepared identity is invalid")
        return marker

    def _take_scoped_activation_recovery_lock(
        self,
        marker: dict[str, Any],
    ) -> WriterLock | None:
        path = self.control_root / "runtime" / "writer.lock"
        deadline = self._monotonic() + self.recovery_lock_timeout_seconds
        while True:
            lock = WriterLock(
                path,
                {
                    "operation": "scoped_activation_recovery",
                    "command_id": marker["command_id"],
                },
            )
            try:
                lock.__enter__()
            except ConflictError:
                state, observed, _ = inspect_lock(path)
                if state == "stale" and observed is not None and remove_stale_lock(path, observed):
                    continue
                if self._monotonic() >= deadline:
                    return None
                self._lock_wait(min(0.01, max(0.0, deadline - self._monotonic())))
                continue
            return lock

    @staticmethod
    def _scoped_activation_event_payload(marker: dict[str, Any]) -> dict[str, Any]:
        envelope = marker["command_identity"]["envelope"]
        payload = envelope["payload"]
        grant = payload["new_grant"]
        return {
            "authority_admission_version": SCOPED_AUTHORITY_ADMISSION_VERSION,
            "project_id": envelope["project_id"],
            "bootstrap_manifest_sha256": payload["bootstrap_manifest_sha256"],
            "root_grant_id": payload["root_grant_id"],
            "root_grant_sha256": payload["root_grant_sha256"],
            "administration_decision_id": payload["administration_decision_id"],
            "administration_decision_sha256": payload["administration_decision_sha256"],
            "activated_grant_id": marker["target_grant_id"],
            "activated_grant_sha256": marker["object_sha256"],
            "activated_grant_schema_id": grant["schema_id"],
            "activated_grant_schema_version": grant["schema_version"],
            "activated_grant_schema_sha256": payload["new_grant_schema_sha256"],
            "subject_scope": grant["subject_scope"],
            "effective_at": grant["effective_at"],
            "expires_at": grant["expires_at"],
        }

    @classmethod
    def _scoped_activation_event_matches(
        cls,
        marker: dict[str, Any],
        event: dict[str, Any],
    ) -> bool:
        identity = marker["command_identity"]
        envelope = identity["envelope"]
        resolved_schema = identity["resolved_schema"]
        generation = marker["target_generation"]
        prepared = marker["prepared_identity"]
        expected = {
            "event_type": "AuthorityGrantActivated",
            "stream_id": marker["target_grant_id"],
            "stream_version": generation["resulting_stream_version"],
            "project_id": envelope["project_id"],
            "command_id": marker["command_id"],
            "command_type": envelope["command_type"],
            "command_schema_id": resolved_schema["schema_id"],
            "command_schema_version": resolved_schema["schema_version"],
            "command_schema_sha256": resolved_schema["sha256"],
            "actor_id": envelope["actor_id"],
            "authority_grant_id": envelope["authority_grant_id"],
            "idempotency_key": envelope["idempotency_key"],
            "command_payload_hash": prepared["command_payload_hash"],
            "correlation_id": envelope["correlation_id"],
            "causation_id": envelope["causation_id"],
            "schema_id": prepared["event_schema_id"],
            "schema_version": prepared["event_schema_version"],
        }
        return all(event.get(key) == value for key, value in expected.items()) and event.get(
            "payload"
        ) == cls._scoped_activation_event_payload(marker)

    def _scoped_activation_event_status(self, marker: dict[str, Any]) -> str:
        """Classify the exact prepared generation without trusting target alone."""
        self._validate_scoped_activation_marker_event_schema(marker)
        events = self.ledger.snapshot().events
        same_command = [event for event in events if event.get("command_id") == marker["command_id"]]
        if same_command:
            if len(same_command) != 1 or not self._scoped_activation_event_matches(marker, same_command[0]):
                raise IntegrityError("scoped activation recovery event identity mismatch")
            return "committed"
        generation = marker["target_generation"]
        target_events = [
            event
            for event in events
            if event.get("stream_id") == marker["target_grant_id"]
            and isinstance(event.get("stream_version"), int)
            and not isinstance(event.get("stream_version"), bool)
            and event["stream_version"] >= generation["resulting_stream_version"]
        ]
        return "competing" if target_events else "uncommitted"

    def _reconcile_scoped_activation_marker(
        self,
        marker: dict[str, Any],
        *,
        status: str | None = None,
    ) -> str:
        status = self._scoped_activation_event_status(marker) if status is None else status
        if status in {"committed", "competing"}:
            try:
                actual = self.objects.read(
                    marker["object_kind"],
                    marker["target_grant_id"],
                    marker["object_revision"],
                )
            except (IntegrityError, ValueError) as exc:
                raise IntegrityError(f"{status} scoped activation recovery object is invalid") from exc
            if actual != marker["object_value"]:
                raise IntegrityError(f"{status} scoped activation recovery object mismatch")
            self._remove_scoped_activation_marker(marker["command_id"])
        else:
            self.objects.rollback_new_revision(
                marker["object_kind"],
                marker["target_grant_id"],
                marker["object_revision"],
                marker["object_value"],
                existed_before=marker["object_existed_before"],
            )
            # Keep the canonical command identity until an exact retry
            # commits or the command ID is otherwise collision-checked.
        return status

    def _scoped_activation_marker_committed(self, marker: dict[str, Any]) -> bool:
        return self._scoped_activation_event_status(marker) == "committed"

    def _recover_scoped_activation_markers(self) -> None:
        root = self.control_root / "runtime" / "scoped-authority-activation-recovery"
        if not root.exists():
            return
        for path in sorted(root.glob("*.json")):
            marker = self._load_scoped_activation_marker(path)
            self._validate_scoped_activation_marker_event_schema(marker)
            lock = self._take_scoped_activation_recovery_lock(marker)
            if lock is None:
                continue
            try:
                status = self._scoped_activation_event_status(marker)
                self._reconcile_scoped_activation_marker(marker, status=status)
            finally:
                lock.__exit__(*sys.exc_info())

    def configure_moved_restore(
        self,
        *,
        source_root: Path,
        preflight_result: RestorePreflightResult,
        rechecker: Callable[[], RestorePreflightResult | RestoreAdmissionBundle],
        approved_witness: StoreOriginWitness,
        approved_witness_path: Path,
    ) -> None:
        """Configure two-phase moved-restore admission for future submissions.

        Args:
            source_root: Existing moved-store root pinned to the origin witness.
            preflight_result: Sealed baseline evidence validated when configuration is installed.
            rechecker: Full read-only preparation callback run exactly once before a writer lock.
            approved_witness: Immutable origin witness authorizing the moved-store source.
            approved_witness_path: Absolute owner-approved canonical locator for the witness.

        Raises:
            ValueError: If the source equals the target or the witness inputs are absent or invalid.
            IntegrityError: If the approved witness path is not canonical or its bytes changed.
            ArsError: If the supplied preflight and source do not bind to the approved origin.
        """
        if not isinstance(approved_witness, StoreOriginWitness):
            raise ValueError("moved restore requires an approved origin witness")
        with self._restore_admission_sequence_lock:
            if source_root.resolve(strict=False) == self.control_root.resolve(strict=False):
                raise ValueError("moved restore source must differ from target")
            if approved_witness_path is None:
                raise ValueError("moved restore requires an approved origin witness path")
            resolved_witness_path, _origin_root = validate_approved_origin_witness_path(
                approved_witness_path,
                approved_witness,
            )
            _validate_moved_restore_source_lineage(source_root, preflight_result, approved_witness)
            self._restore_source_root = source_root
            self._restore_approved_witness = approved_witness
            self._restore_approved_witness_path = resolved_witness_path
            self._restore_preflight_result = preflight_result
            self._restore_preflight_rechecker = rechecker

    def _prepare_moved_restore(self, command: Command) -> _PreparedRestoreAdmission | None:
        """Run and validate one current full preflight before writer locking."""
        if self._restore_preflight_result is None and self._restore_preflight_rechecker is None:
            return None
        supplied = self._restore_preflight_result
        rechecker = self._restore_preflight_rechecker
        if (
            supplied is None
            or rechecker is None
            or self._restore_approved_witness is None
            or self._restore_approved_witness_path is None
        ):
            raise ArsError("moved store requires restore preflight")
        validate_approved_origin_witness_path(
            self._restore_approved_witness_path,
            self._restore_approved_witness,
        )
        checked = rechecker()
        bundle = (
            checked if isinstance(checked, RestoreAdmissionBundle) else restore_admission_bundle_for_result(checked)
        )
        current = bundle.result
        _validate_moved_restore_source_lineage(
            self._restore_source_root,
            current,
            self._restore_approved_witness,
        )
        validate_restore_preflight_result(
            current,
            current_root=self.control_root,
            project_id=self.ledger.project_id,
            actor_id=command.actor_id,
            authority_grant_id=command.envelope["authority_grant_id"],
            approved_witness=self._restore_approved_witness,
        )
        if current.origin_witness_path != str(self._restore_approved_witness_path):
            raise ArsError("restore preflight origin witness path differs from approved locator")
        if bundle.closure is None:
            raise ArsError("verified restore preflight requires checked-input closure")
        return _PreparedRestoreAdmission(
            bundle=bundle,
            preflight_result_hash=current.result_hash,
        )

    def _revalidate_prepared_moved_restore(
        self,
        command: Command,
        prepared: _PreparedRestoreAdmission | None,
        snapshot: LedgerSnapshot,
    ) -> None:
        """Join the prepared preflight to the one locked submission snapshot."""
        if (
            self._restore_source_root is None
            or self._restore_approved_witness is None
            or self._restore_approved_witness_path is None
        ):
            if prepared is not None:
                raise ArsError("moved store requires restore preflight")
            return
        if prepared is not None:
            current = prepared.bundle.result
            if current.result_hash != prepared.preflight_result_hash:
                raise ArsError("restore preflight changed after preparation")
            _validate_moved_restore_source_lineage(
                self._restore_source_root,
                current,
                self._restore_approved_witness,
            )
            validate_restore_preflight_result(
                current,
                current_root=self.control_root,
                project_id=self.ledger.project_id,
                actor_id=command.actor_id,
                authority_grant_id=command.envelope["authority_grant_id"],
                approved_witness=self._restore_approved_witness,
            )
            if current.origin_witness_path != str(self._restore_approved_witness_path):
                raise ArsError("restore preflight origin witness path differs from approved locator")
            if (snapshot.global_position, snapshot.event_hash) != (
                current.tail_position,
                current.tail_hash,
            ):
                raise ArsError("restore preflight ledger tail changed before writer lock")
            revalidate_restore_admission_closure(prepared.bundle)
        verify_restore_binding_admission(
            self.control_root,
            approved_witness=self._restore_approved_witness,
            approved_witness_path=self._restore_approved_witness_path,
        )

    def _retire_moved_restore_preflight(self) -> None:
        """Retire historical preflight state only after an EventLedger append."""
        self._restore_preflight_result = None
        self._restore_preflight_rechecker = None

    @_release_submit_guard
    def submit(
        self,
        envelope: dict[str, Any],
        release_append: Callable[..., dict[str, Any]] | None = None,
        scoped_authority_append: Callable[..., dict[str, Any]] | None = None,
    ) -> Receipt | T2Receipt:
        """Validate WP1 integrity controls; authorization remains downstream."""
        if release_append is None or scoped_authority_append is None:
            raise ArsError("CommandService.submit requires its guarded continuations")
        if envelope.get("command_type") in T2_COMMAND_TYPES:
            return submit_t2(self, envelope)
        validated_envelope = {key: value for key, value in envelope.items() if key not in _CALLER_PROVENANCE_FIELDS}
        schema_id = str(validated_envelope.get("schema_id", ""))
        schema_version = str(validated_envelope.get("schema_version", ""))
        command_type = str(validated_envelope.get("command_type", ""))
        command_binding = self.schemas.command_binding(command_type)
        if command_binding is not None:
            if (schema_id, schema_version) != (
                command_binding.schema_id,
                command_binding.schema_version,
            ):
                raise SchemaError(
                    f"active command binding mismatch: {command_type} requires "
                    f"{command_binding.schema_id} version {command_binding.schema_version}"
                )
            command_schema = self.schemas.validate_active(
                command_binding.schema_id,
                validated_envelope,
                schema_version=command_binding.schema_version,
            )
        else:
            command_schema = self.schemas.validate(
                "ars://core/command",
                validated_envelope,
            )
        if validated_envelope.get("command_type") == "RevokeAuthorityGrant":
            self.schemas.validate(
                "ars://core/command/RevokeAuthorityGrant/payload",
                validated_envelope.get("payload"),
            )
        elif validated_envelope.get("command_type") == "PublishReleaseGateDecision":
            self.schemas.validate(
                "ars://evals/release-publication-request",
                validated_envelope.get("payload"),
            )
            ReleasePublicationRequest.from_dict(validated_envelope["payload"])
        command = Command(validated_envelope)
        self._before_submission_lock(command)
        activation_command = command.envelope["command_type"] in _SCOPED_ACTIVATION_COMMAND_TYPES
        preloaded_activation_marker: dict[str, Any] | None = None
        if activation_command:
            marker_path = self._scoped_activation_marker_path(command.command_id)
            if marker_path.exists():
                preloaded_activation_marker = self._load_scoped_activation_marker(marker_path)
                self._validate_scoped_activation_marker_command(
                    preloaded_activation_marker,
                    command,
                    command_schema,
                )
                self._validate_scoped_activation_marker_event_schema(preloaded_activation_marker)
        with self._submission_lock(command) as submission:
            lifecycle_authority: _LifecycleAuthorityEvidence | None = None

            def write_receipt(receipt: Receipt) -> Receipt:
                return self._write_receipt(
                    command,
                    receipt,
                    lifecycle_authority,
                    command_schema=command_schema,
                )

            self._before_authority_resolution(command)
            lifecycle = command.envelope["command_type"] in _LIFECYCLE_COMMAND_TYPES
            snapshot = submission.snapshot
            if lifecycle:
                lifecycle_authority, denial = self._resolve_lifecycle_authority(
                    command,
                    command_schema,
                    snapshot,
                )
                if denial is not None:
                    observed_version = snapshot.stream_versions.get(
                        command.target_stream_id,
                        0,
                    )
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "lifecycle_authority_unauthorized",
                        denial,
                    )
                    stored = self.receipts.load(command.command_id)
                    if (
                        stored is not None
                        and stored.status == "rejected"
                        and stored.payload_hash == command.payload_hash
                    ):
                        return stored
                    # A fresh denial must not return or overwrite an older
                    # accepted receipt for the same logical submission.
                    return rejected
            scoped = self._scoped_authority_receipt(
                command,
                command_schema=command_schema,
                lifecycle_authority=lifecycle_authority,
            )
            if scoped is not None:
                return scoped
            if not lifecycle:
                stored_conflict = self._stored_conflict_receipt(command)
                if stored_conflict is not None:
                    return stored_conflict
                stored_rejected = self._stored_rejected_receipt(command)
                if stored_rejected is not None:
                    return stored_rejected
            view = self._view_for(snapshot)
            activation_marker_preexisting = preloaded_activation_marker is not None
            activation_marker_status: str | None = None
            if preloaded_activation_marker is not None:
                current_marker = self._load_scoped_activation_marker(
                    self._scoped_activation_marker_path(command.command_id)
                )
                self._validate_scoped_activation_marker_command(
                    current_marker,
                    command,
                    command_schema,
                )
                activation_marker_status = self._scoped_activation_event_status(current_marker)
                if activation_marker_status == "competing":
                    self._remove_scoped_activation_marker(command.command_id)
                    preloaded_activation_marker = None
                    activation_marker_preexisting = False
            existing = self._matching_committed(
                command,
                view,
                command_schema=command_schema,
            )
            if existing is not None:
                reconstructed = self._return_or_reconstruct(existing)
                if command.envelope["command_type"] in _C1_COMMAND_TYPES:
                    self._return_scoped_receipt_or_raise(command, reconstructed)
                if command.envelope["command_type"] == "RequestResourceGrant":
                    self._ensure_resource_grant_materialized(command)
                if command.envelope["command_type"] == "CreateBackup":
                    self._ensure_backup_materialized(command)
                if command.envelope["command_type"] == "RegisterArtefact":
                    self._ensure_artefact_materialized(command)
                receipt = write_receipt(reconstructed)
                if activation_marker_status == "committed":
                    self._remove_scoped_activation_marker(command.command_id)
                return receipt
            if (
                command.envelope["command_type"] in _MESSAGE_COMMAND_TYPES
                and self.receipts.load(command.command_id) is not None
            ):
                raise ConflictError(f"receipt already exists: {command.command_id}")
            observed_version = view.stream_versions.get(command.target_stream_id, 0)
            prepared_payload: dict[str, Any] | VerifiedReleasePublication | None = None
            activation_object_existed: bool | None = None
            append_started = False
            if command.envelope["command_type"] == "PublishReleaseGateDecision":
                request = ReleasePublicationRequest.from_dict(command.envelope["payload"])
                if (
                    request.project_id != self.ledger.project_id
                    or request.release_decision_id != command.target_stream_id
                    or request.publication_authority_grant_id != command.envelope["authority_grant_id"]
                    or request.idempotency_key != command.idempotency_key
                    or set(command.envelope["evidence_refs"])
                    != {
                        request.evaluation_runs_manifest_ref,
                        request.control_binding_ref,
                    }
                ):
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "release_publication_evidence_mismatch",
                        "Release publication envelope bindings do not match.",
                    )
                    return write_receipt(rejected)
                if self.authority_resolver is None:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "release_publication_authorizer_unavailable",
                        "Release publication requires the canonical authority resolver.",
                    )
                    return write_receipt(rejected)
                try:
                    prepared_payload = self._prepare_release_publication(command)
                except IntegrityError:
                    raise
                except PublicationEvidenceError as exc:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "release_publication_evidence_mismatch",
                        str(exc),
                    )
                    return write_receipt(rejected)
                except ArsError as exc:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "release_publication_unauthorized",
                        str(exc),
                    )
                    return write_receipt(rejected)
                if observed_version > 0:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "release_decision_already_published",
                        "The canonical release decision stream is already published.",
                    )
                    return write_receipt(rejected)
            if observed_version != command.expected_stream_version:
                receipt = Receipt(
                    status="conflict",
                    command_id=command.command_id,
                    payload_hash=command.payload_hash,
                    event_batch_id=None,
                    observed_stream_version=observed_version,
                    reason_code="stream_version_conflict",
                )
                return write_receipt(receipt)
            if command.envelope["command_type"] in _SCOPE_COMMAND_TYPES:
                prepared = self._prepare_scope_command(
                    command,
                    snapshot,
                    observed_version,
                )
                if isinstance(prepared, Receipt):
                    return write_receipt(prepared)
                prepared_payload = prepared
            elif command.envelope["command_type"] in _TASK_REVISION_COMMAND_TYPES:
                prepared = self._prepare_task_command(
                    command,
                    snapshot,
                    observed_version,
                    command_schema=command_schema,
                )
                if isinstance(prepared, Receipt):
                    return write_receipt(prepared)
                prepared_payload = prepared
            elif command.envelope["command_type"] in _MESSAGE_COMMAND_TYPES:
                prepared = self._prepare_message_command(
                    command,
                    snapshot,
                    observed_version,
                )
                if isinstance(prepared, Receipt):
                    return write_receipt(prepared)
                prepared_payload = prepared
            elif command.envelope["command_type"] in _C1_COMMAND_TYPES:
                prepared = self._prepare_c1_command(
                    command,
                    snapshot,
                    observed_version,
                )
                if isinstance(prepared, Receipt):
                    return write_receipt(prepared)
                prepared_payload = prepared
                if command.envelope["command_type"] == "RequestResourceGrant":
                    self._prepare_resource_grant_materialization(command)
            elif command.envelope["command_type"] in _C2_COMMAND_TYPES:
                prepared = self._prepare_c2_command(
                    command,
                    snapshot,
                    observed_version,
                )
                if isinstance(prepared, Receipt):
                    return write_receipt(prepared)
                prepared_payload = prepared
            elif command.envelope["command_type"] in _C3_COMMAND_TYPES:
                prepared = self._prepare_c3_command(
                    command,
                    snapshot,
                    observed_version,
                )
                if isinstance(prepared, Receipt):
                    return write_receipt(prepared)
                prepared_payload = prepared
            elif command.envelope["command_type"] in _BACKUP_COMMAND_TYPES:
                prepared = self._prepare_backup_command(
                    command,
                    snapshot,
                    observed_version,
                )
                if isinstance(prepared, Receipt):
                    return write_receipt(prepared)
                prepared_payload = prepared
            elif command.envelope["command_type"] in _ARTEFACT_AUTHORITY_COMMAND_TYPES:
                prepared = self._prepare_artefact_authority_command(
                    command,
                    snapshot,
                    observed_version,
                )
                if isinstance(prepared, Receipt):
                    return write_receipt(prepared)
                prepared_payload = prepared
            elif command.envelope["command_type"] in _CONTEXT_PACKET_COMMAND_TYPES:
                prepared = self._prepare_context_packet_command(
                    command,
                    snapshot,
                    observed_version,
                )
                if isinstance(prepared, Receipt):
                    return write_receipt(prepared)
                prepared_payload = prepared
            elif command.envelope["command_type"] == "RevokeAuthorityGrant":
                try:
                    prepared_payload = self._prepare_authority_revocation(command, observed_version)
                except IntegrityError:
                    raise
                except ArsError as exc:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "authority_revocation_unauthorized",
                        str(exc),
                    )
                    return write_receipt(rejected)
            elif command.envelope["command_type"] in _SCOPED_AUTHORITY_ADMIN_COMMAND_TYPES:
                try:
                    activation = command.envelope["command_type"] in {
                        "ActivateAuthorityGrant",
                        "ActivateExternalAssuranceRecordGrant",
                    }
                    if activation:
                        marker_path = self._scoped_activation_marker_path(command.command_id)
                        if activation_marker_preexisting:
                            existing_marker = self._load_scoped_activation_marker(marker_path)
                            self._validate_scoped_activation_marker_command(
                                existing_marker,
                                command,
                                command_schema,
                            )
                            activation_object_existed = existing_marker["object_existed_before"]
                        else:
                            activation_object_existed = self.objects.revision_exists(
                                "authority_grant",
                                command.target_stream_id,
                                1,
                            )
                        self._write_scoped_activation_marker(
                            command,
                            command_schema=command_schema,
                            existed_before=activation_object_existed,
                        )
                    if activation:
                        prepared_payload = self._prepare_scoped_authority_activation(
                            command,
                            observed_version,
                        )
                    else:
                        prepared_payload = self._prepare_issued_authority_revocation(
                            command,
                            observed_version,
                        )
                except IntegrityError:
                    self._cleanup_failed_scoped_activation(
                        command,
                        existed_before=activation_object_existed,
                        marker_preexisting=activation_marker_preexisting,
                    )
                    raise
                except ConflictError:
                    self._cleanup_failed_scoped_activation(
                        command,
                        existed_before=activation_object_existed,
                        marker_preexisting=activation_marker_preexisting,
                    )
                    raise
                except ArsError as exc:
                    self._cleanup_failed_scoped_activation(
                        command,
                        existed_before=activation_object_existed,
                        marker_preexisting=activation_marker_preexisting,
                    )
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "scoped_authority_administration_unauthorized",
                        str(exc),
                    )
                    return write_receipt(rejected)
            try:
                events = self._build_events(
                    command,
                    prepared_payload,
                    command_schema=command_schema,
                )
                event = events[0]
                append_started = True
                if isinstance(prepared_payload, VerifiedReleasePublication):
                    ledger_receipt = release_append(
                        self.ledger,
                        event,
                        lambda allocated: prepared_payload.payload_for(allocated.event_id),
                        snapshot=snapshot,
                    )
                elif (
                    command.envelope["command_type"] == "RevokeAuthorityGrant"
                    or command.envelope["command_type"] in _SCOPED_AUTHORITY_ADMIN_COMMAND_TYPES
                ):
                    ledger_receipt = scoped_authority_append(
                        self.ledger,
                        event,
                        snapshot=snapshot,
                    )
                else:
                    ledger_receipt = self.ledger.append(events, snapshot=snapshot)
                self._retire_moved_restore_preflight()
                updated = self.ledger.snapshot()
                view.extend(updated.events[len(snapshot.events) :], updated.fingerprint)
                accepted = Receipt(
                    status="accepted",
                    command_id=command.command_id,
                    payload_hash=command.payload_hash,
                    event_batch_id=ledger_receipt["event_batch_id"],
                    observed_stream_version=ledger_receipt["resulting_stream_versions"][command.target_stream_id],
                )
                receipt = write_receipt(accepted)
                if activation_object_existed is not None:
                    self._remove_scoped_activation_marker(command.command_id)
                return receipt
            except Exception:
                if activation_object_existed is not None:
                    if self._scoped_activation_committed(command, command_schema=command_schema):
                        self._remove_scoped_activation_marker(command.command_id)
                    else:
                        self._rollback_scoped_authority_activation(
                            command,
                            existed_before=activation_object_existed,
                        )
                        if not append_started:
                            self._remove_scoped_activation_marker(command.command_id)
                raise

    def _scoped_activation_committed(
        self,
        command: Command,
        *,
        command_schema: SchemaIdentity,
    ) -> bool:
        path = self._scoped_activation_marker_path(command.command_id)
        if not path.exists():
            return False
        marker = self._load_scoped_activation_marker(path)
        self._validate_scoped_activation_marker_command(marker, command, command_schema)
        return self._scoped_activation_event_status(marker) == "committed"

    def _reconcile_scoped_activation_receipt(
        self,
        command: Command,
        command_schema: SchemaIdentity,
    ) -> None:
        if command.envelope["project_id"] != self.ledger.project_id:
            raise ConflictError("scoped activation recovery marker conflicts")
        marker_path = self._scoped_activation_marker_path(command.command_id)
        if not marker_path.exists():
            residue: list[tuple[Path, dict[str, Any]]] = []
            foreign_residue = False
            for temporary in self._scoped_activation_marker_temporary_paths(marker_path):
                if not temporary.exists():
                    continue
                try:
                    existing = self._load_scoped_activation_marker(temporary)
                except IntegrityError as exc:
                    raise IntegrityError("scoped activation recovery marker temporary data is invalid") from exc
                try:
                    self._validate_scoped_activation_marker_command(existing, command, command_schema)
                except ConflictError:
                    foreign_residue = True
                    continue
                status = self._scoped_activation_event_status(existing)
                if status != "committed":
                    raise IntegrityError("scoped accepted receipt does not match recovery marker")
                try:
                    actual = self.objects.read(
                        existing["object_kind"],
                        existing["target_grant_id"],
                        existing["object_revision"],
                    )
                except (IntegrityError, ValueError) as exc:
                    raise IntegrityError("committed scoped activation recovery object is invalid") from exc
                if actual != existing["object_value"]:
                    raise IntegrityError("committed scoped activation recovery object mismatch")
                residue.append((temporary, existing))
            if foreign_residue:
                raise ConflictError("scoped activation recovery marker temporary data conflicts")
            if self._cleanup_scoped_activation_marker_residue(residue) and marker_path.parent.exists():
                fsync_directory(marker_path.parent)
            return
        marker = self._load_scoped_activation_marker(marker_path)
        self._validate_scoped_activation_marker_command(marker, command, command_schema)
        status = self._scoped_activation_event_status(marker)
        if status != "committed":
            raise IntegrityError("scoped accepted receipt does not match recovery marker")
        self._reconcile_scoped_activation_marker(marker, status=status)

    def _rollback_scoped_authority_activation(
        self,
        command: Command,
        *,
        existed_before: bool,
    ) -> None:
        payload = command.envelope.get("payload")
        if not isinstance(payload, dict):
            return
        grant = payload.get("new_grant")
        if not isinstance(grant, dict):
            return
        self.objects.rollback_new_revision(
            "authority_grant",
            command.target_stream_id,
            1,
            grant,
            existed_before=existed_before,
        )

    def _cleanup_failed_scoped_activation(
        self,
        command: Command,
        *,
        existed_before: bool | None,
        marker_preexisting: bool,
    ) -> None:
        """Undo a newly prepared activation while retaining pre-existing evidence."""
        if existed_before is None:
            return
        self._rollback_scoped_authority_activation(command, existed_before=existed_before)
        if not marker_preexisting:
            self._remove_scoped_activation_marker(command.command_id)

    def _before_submission_lock(self, command: Command) -> None:
        """Provide a post-validation setup seam before writer-lock acquisition."""

    def _before_authority_resolution(self, command: Command) -> None:
        """Provide a locked setup seam immediately before authority evaluation."""

    @contextmanager
    def _submission_lock(self, command: Command):
        """Serialize authority-governed submits across all participating roots."""
        with self._restore_admission_sequence_lock:
            prepared = self._prepare_moved_restore(command)
            identity = {"command_id": command.command_id}
            command_type = command.envelope["command_type"]
            roots: tuple[Path, ...] = (self.control_root,)
            if command_type in _T2_AUTHORITY_COORDINATED_COMMAND_TYPES:
                t2_root = self._t2_authority_root_for_lock()
                if t2_root is not None:
                    roots = (self.control_root, t2_root)
            elif command_type in _AUTHORITY_COORDINATED_COMMAND_TYPES:
                resolver = self._canonical_authority_resolver()
                if resolver is not None:
                    roots = (self.control_root, resolver.control_root)
            retry_on_conflict = command_type in {
                "PublishReleaseGateDecision",
                *_LIFECYCLE_COMMAND_TYPES,
                *_T2_AUTHORITY_COORDINATED_COMMAND_TYPES,
            }
            deadline = self._monotonic() + self.release_lock_timeout_seconds
            while True:
                lock = CompositeWriterLock(
                    roots,
                    identity,
                    lock_factory=WriterLock,
                )
                try:
                    lock.__enter__()
                except ConflictError:
                    if not retry_on_conflict or self._monotonic() >= deadline:
                        raise
                    self._lock_wait(0.01)
                    continue
                break
            try:
                snapshot = self.ledger.snapshot()
                self._revalidate_prepared_moved_restore(command, prepared, snapshot)
                yield _SubmissionLease(lock, snapshot)
            finally:
                lock.__exit__(*sys.exc_info())

    def with_locked_authority(
        self,
        *,
        authority_grant_id: str,
        actor_id: str,
        command_type: str,
        project_id: str,
        subject_kind: str,
        subject_id: str,
        callback: Callable[[Any], Any],
    ) -> Any:
        """Recheck current canonical authority and run a callback under W2 lock.

        Args:
            authority_grant_id: Grant to revalidate against canonical history.
            actor_id: Attributed actor performing the governed operation.
            command_type: Exact governed command type.
            project_id: Project identity of the governed target.
            subject_kind: Registered governed subject kind.
            subject_id: Exact governed subject identity.
            callback: Operation invoked with replay-derived authority evidence.

        Returns:
            The callback result.

        Raises:
            ArsError: If no resolver exists or current authority is invalid.
            ConflictError: If the W2 writer lock cannot be acquired.
            IntegrityError: If canonical authority evidence is invalid.
        """
        resolver = self._canonical_authority_resolver()
        if resolver is None:
            raise ArsError("governed operation requires authority resolver")
        with CompositeWriterLock(
            (self.control_root, resolver.control_root),
            {"command_id": new_id("command")},
            lock_factory=WriterLock,
        ):
            snapshot = self.ledger.snapshot()
            replay(
                snapshot.events,
                schema_registry=self.schemas,
                authority_state_validator=self._authority_state_validator(),
            )
            resolved = resolver.resolve(
                authority_grant_id,
                actor_id,
                command_type,
                project_id,
                subject_kind,
                subject_id,
                self.clock(),
            )
            return callback(resolved)

    @staticmethod
    def _authority_scope(command: Command) -> tuple[str, str, str, str]:
        return (
            command.actor_id,
            command.envelope["authority_grant_id"],
            command.envelope["command_type"],
            command.idempotency_key,
        )

    def _scoped_authority_receipt(
        self,
        command: Command,
        *,
        command_schema: SchemaIdentity,
        lifecycle_authority: _LifecycleAuthorityEvidence | None = None,
    ) -> Receipt | None:
        command_type = command.envelope["command_type"]
        if command_type in _LIFECYCLE_COMMAND_TYPES:
            if lifecycle_authority is None:
                raise IntegrityError("lifecycle command missing fresh authority resolution")
            return self._load_lifecycle_authority_receipt(
                command,
                command_schema,
                lifecycle_authority,
            )
        if command_type not in {
            "RevokeAuthorityGrant",
            "PublishReleaseGateDecision",
            *_SCOPED_AUTHORITY_ADMIN_COMMAND_TYPES,
        }:
            return None
        if command_type == "PublishReleaseGateDecision":
            hash_field = "publication_authority_sha256"
        elif command_type == "RevokeAuthorityGrant":
            hash_field = "authority_grant_sha256"
        else:
            hash_field = "root_grant_sha256"
        grant_hash = command.envelope.get("payload", {}).get(hash_field)
        if not isinstance(grant_hash, str):
            return None
        publication = command_type == "PublishReleaseGateDecision"
        try:
            receipt = self.receipts.load_scoped(
                self._authority_scope(command),
                command.payload_hash,
                grant_hash,
                command.expected_stream_version,
                project_id=self.ledger.project_id if publication else None,
                target_stream_id=(command.target_stream_id if publication else None),
            )
        except IdempotencyConflictError:
            if not publication:
                raise
            conflict = Receipt(
                status="conflict",
                command_id=command.command_id,
                payload_hash=command.payload_hash,
                event_batch_id=None,
                observed_stream_version=self.ledger.snapshot().stream_versions.get(
                    command.target_stream_id,
                    0,
                ),
                reason_code="idempotency_conflict",
            )
            return self.receipts.write(conflict)
        if receipt is None:
            return receipt
        if command.envelope["command_type"] in _SCOPED_ACTIVATION_COMMAND_TYPES and receipt.status == "accepted":
            self._reconcile_scoped_activation_receipt(command, command_schema)
        self._reconcile_scoped_authority_receipt(command, receipt)
        return self._return_scoped_receipt_or_raise(command, receipt)

    def _reconcile_scoped_authority_receipt(
        self,
        command: Command,
        receipt: Receipt,
        *,
        lifecycle_resolution: dict[str, Any] | None = None,
        canonical_resolution: dict[str, Any] | None = None,
        command_schema: SchemaIdentity | None = None,
    ) -> None:
        scope = self._authority_scope(command)
        snapshot = self.ledger.snapshot()
        replay(
            snapshot.events,
            schema_registry=self.schemas,
            authority_state_validator=self._authority_state_validator(),
        )
        events = tuple(snapshot.events)
        scoped_events = tuple(
            event
            for event in events
            if (
                event.get("actor_id"),
                event.get("authority_grant_id"),
                event.get("command_type"),
                event.get("idempotency_key"),
            )
            == scope
        )
        if receipt.status == "accepted":
            matching = tuple(event for event in scoped_events if event.get("transaction_id") == receipt.event_batch_id)
            command_type = command.envelope["command_type"]
            try:
                expected_event_type = _COMMAND_EVENT_TYPES[command_type]
            except KeyError as exc:
                raise IntegrityError(f"no canonical event type for {command_type}") from exc
            event = (
                self._claim_dispatch_receipt_event(command, matching, receipt)
                if command_type == "ClaimDispatch"
                else (matching[0] if len(matching) == 1 else None)
            )
            if (
                event is None
                or event.get("event_type") != expected_event_type
                or event.get("command_id") != receipt.command_id
                or event.get("command_payload_hash") != receipt.payload_hash
                or event.get("stream_id") != command.target_stream_id
                or event.get("stream_version") != command.expected_stream_version + 1
                or receipt.observed_stream_version != event.get("stream_version")
                or event.get("project_id") != self.ledger.project_id
            ):
                raise IntegrityError("scoped accepted receipt does not match canonical ledger")
            if lifecycle_resolution is not None:
                if command_schema is None:
                    raise IntegrityError("lifecycle command schema evidence is missing")
                self._validate_lifecycle_authority_history(
                    command,
                    command_schema=command_schema,
                    receipt=receipt,
                    resolution=lifecycle_resolution,
                    event=event,
                    canonical_resolution=canonical_resolution,
                )
        elif scoped_events:
            raise IntegrityError("scoped terminal receipt conflicts with canonical ledger")
        stored = self.receipts.load(receipt.command_id)
        if stored is not None and stored != receipt:
            raise IntegrityError("receipt does not match scoped index")
        self._validate_message_scoped_retry_identity(command, receipt)
        if stored is None:
            self.receipts.write(receipt)

    @staticmethod
    def _claim_dispatch_receipt_event(
        command: Command,
        events: tuple[dict[str, Any], ...],
        receipt: Receipt,
    ) -> dict[str, Any]:
        """Return ClaimDispatch's Dispatch event after exact batch validation."""
        payload = command.envelope["payload"]
        if (
            len(events) != 2
            or [event.get("event_type") for event in events] != ["DispatchClaimed", "TaskClaimStarted"]
            or [event.get("transaction_index") for event in events] != [1, 2]
            or any(event.get("transaction_count") != 2 for event in events)
            or events[0].get("stream_id") != command.target_stream_id
            or events[1].get("stream_id") != payload.get("task_id")
            or events[0].get("command_id") != receipt.command_id
            or events[1].get("command_id") != receipt.command_id
            or events[0].get("command_payload_hash") != receipt.payload_hash
            or events[1].get("command_payload_hash") != receipt.payload_hash
            or events[0].get("payload") != payload
            or events[1].get("payload")
            != {"task_id": payload.get("task_id"), "task_revision": payload.get("task_revision")}
            or events[0].get("stream_version") != command.expected_stream_version + 1
            or events[0].get("stream_version") != payload.get("expected_dispatch_stream_version", -1) + 1
            or events[1].get("stream_version") != payload.get("expected_task_stream_version", -1) + 1
        ):
            raise IntegrityError("ClaimDispatch accepted receipt does not match exact two-event batch")
        return events[0]

    def _validate_lifecycle_authority_history(
        self,
        command: Command,
        *,
        command_schema: SchemaIdentity,
        receipt: Receipt,
        resolution: dict[str, Any],
        event: dict[str, Any],
        canonical_resolution: dict[str, Any] | None,
    ) -> None:
        if receipt.status != "accepted":
            return
        if not isinstance(resolution, dict):
            raise IntegrityError("lifecycle authority resolution evidence is invalid")
        grant_id = resolution.get("authority_grant_id")
        canonical_history = canonical_resolution
        if (
            not isinstance(grant_id, str)
            or not grant_id
            or not isinstance(canonical_history, dict)
            or canonical_history.get("authority_grant_id") != grant_id
        ):
            raise IntegrityError("lifecycle authority evidence has no canonical grant history")
        if self._authority_key(canonical_history) != resolution.get("authority_grant_sha256"):
            raise IntegrityError("lifecycle authority resolution grant hash disagrees with canonical history")
        if (
            event.get("authority_grant_id") != grant_id
            or event.get("actor_id") != resolution.get("actor_id")
            or event.get("stream_id") != command.target_stream_id
            or event.get("command_type") != command.envelope["command_type"]
            or event.get("command_schema_id") != command_schema.schema_id
            or event.get("command_schema_version") != command_schema.schema_version
            or event.get("command_schema_sha256") != command_schema.sha256
            or event.get("command_payload_hash") != command.payload_hash
        ):
            raise IntegrityError("lifecycle authority resolution is not bound to history")

    def _write_receipt(
        self,
        command: Command,
        receipt: Receipt,
        lifecycle_authority: _LifecycleAuthorityEvidence | None = None,
        *,
        command_schema: SchemaIdentity | None = None,
    ) -> Receipt:
        command_type = command.envelope["command_type"]
        if command_type in _MESSAGE_COMMAND_TYPES and receipt.status != "accepted":
            return receipt
        if command_type in _LIFECYCLE_COMMAND_TYPES:
            if lifecycle_authority is None:
                raise IntegrityError("lifecycle command missing resolved authority evidence")
            if lifecycle_authority.resolution is None:
                raise IntegrityError("lifecycle command missing resolution evidence")
            if command_schema is None:
                raise IntegrityError("lifecycle command schema evidence is missing")
            if receipt.status == "accepted":
                snapshot = self.ledger.snapshot()
                replay(
                    snapshot.events,
                    schema_registry=self.schemas,
                    authority_state_validator=self._authority_state_validator(),
                )
                batch = tuple(
                    event for event in snapshot.events if event.get("transaction_id") == receipt.event_batch_id
                )
                if command_type == "ClaimDispatch":
                    event = self._claim_dispatch_receipt_event(command, batch, receipt)
                else:
                    event = next(
                        (event for event in batch if event.get("stream_id") == command.target_stream_id),
                        None,
                    )
                if event is None:
                    raise IntegrityError("accepted lifecycle receipt has no canonical event")
                self._validate_lifecycle_authority_history(
                    command,
                    command_schema=command_schema,
                    receipt=receipt,
                    resolution=lifecycle_authority.resolution,
                    event=event,
                    canonical_resolution=lifecycle_authority.canonical_resolution,
                )
                if command_type == "RequestResourceGrant":
                    self._ensure_resource_grant_materialized(command)
                if command_type == "CreateBackup":
                    self._ensure_backup_materialized(command)
                if command_type == "RegisterArtefact":
                    self._ensure_artefact_materialized(command)
            result = self.receipts.write_scoped(
                self._authority_scope(command),
                lifecycle_authority.authority_key,
                command.expected_stream_version,
                receipt,
                project_id=command.envelope.get("project_id"),
                target_stream_id=command.target_stream_id,
            )
            return result
        if command_type not in {
            "RevokeAuthorityGrant",
            "PublishReleaseGateDecision",
            *_SCOPED_AUTHORITY_ADMIN_COMMAND_TYPES,
        }:
            return self.receipts.write(receipt)
        publication = command_type == "PublishReleaseGateDecision"
        if publication:
            hash_field = "publication_authority_sha256"
        elif command_type == "RevokeAuthorityGrant":
            hash_field = "authority_grant_sha256"
        else:
            hash_field = "root_grant_sha256"
        grant_hash = command.envelope["payload"].get(hash_field)
        if not isinstance(grant_hash, str):
            return self.receipts.write(receipt)
        return self.receipts.write_scoped(
            self._authority_scope(command),
            grant_hash,
            command.expected_stream_version,
            receipt,
            project_id=self.ledger.project_id if publication else None,
            target_stream_id=(command.target_stream_id if publication else None),
        )

    @staticmethod
    def _risk_tier(value: object) -> str:
        return value if isinstance(value, str) and value in {"R0", "R1", "R2", "R3"} else "R3"

    @classmethod
    def _max_risk(cls, *values: object) -> str:
        order = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}
        return max(
            (cls._risk_tier(value) for value in values),
            key=order.__getitem__,
        )

    def _task_current_risk(self, snapshot: LedgerSnapshot, task_id: str) -> str:
        current, _, _ = self._revision_graph(snapshot)
        revision = current.get(task_id)
        if revision is None:
            return "R3"
        definition = self._task_revision_object(task_id, revision)
        if definition is None:
            return "R3"
        return self._risk_tier(definition.get("risk_tier_request"))

    def _lifecycle_authority_inputs(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
    ) -> tuple[str, str, str, str]:
        command_type = command.envelope["command_type"]
        payload = command.envelope["payload"]
        project_id = str(command.envelope.get("project_id", ""))
        if command_type in _SCOPE_COMMAND_TYPES:
            subject_id = str(
                payload.get(
                    "new_scope_definition_id" if command_type == "CreateScopeDefinition" else "scope_definition_id",
                    "",
                )
            )
            return project_id, "scope_definition", subject_id, "R3"

        if command_type in _MESSAGE_COMMAND_TYPES:
            subject_id = str(
                payload.get(
                    "new_message_id" if command_type == "PublishMessage" else "message_id",
                    "",
                )
            )
            return project_id, "message", subject_id, "R3"

        if command_type in _C1_TASK_COMMAND_TYPES:
            return project_id, "task", str(payload.get("task_id", "")), "R3"
        if command_type in _C2_TASK_COMMAND_TYPES:
            return project_id, "task", str(payload.get("task_id", "")), "R3"
        if command_type in _C2_BLOCKER_COMMAND_TYPES:
            blocker_id = payload.get("new_blocker_id") if command_type == "RecordBlocker" else payload.get("blocker_id")
            return project_id, "blocker", str(blocker_id or ""), "R3"
        if command_type in _C2_DISPATCH_COMMAND_TYPES:
            return project_id, "dispatch", str(payload.get("dispatch_id", "")), "R3"
        if command_type in _C2_ATTEMPT_COMMAND_TYPES:
            attempt_id = payload.get("new_attempt_id") if command_type == "RetryAttempt" else payload.get("attempt_id")
            return project_id, "attempt", str(attempt_id or ""), "R3"
        if command_type in _C2_CHECKPOINT_COMMAND_TYPES | _C2_OPERATOR_COMMAND_TYPES | _C2_RECOVERY_COMMAND_TYPES:
            return project_id, "attempt", str(payload.get("attempt_id", "")), "R3"
        if command_type in _C2_REVIEW_COMMAND_TYPES:
            return project_id, "review", str(payload.get("new_review_id", "")), "R3"
        if command_type in _C3_TASK_COMMAND_TYPES:
            return project_id, "task", str(payload.get("task_id", "")), "R3"
        if command_type in _C3_REVIEW_COMMAND_TYPES:
            return project_id, "review", str(payload.get("review_id", "")), "R3"
        if command_type == "ProposeDecision":
            return project_id, "decision", str(payload.get("new_decision_id", "")), "R3"
        if command_type in {
            "RequestDecisionReview",
            "RejectDecision",
            "ExpireDecision",
            "SupersedeDecision",
            "AmendDecision",
        }:
            return project_id, "decision", str(payload.get("decision_id", "")), "R3"
        if command_type == "RecordRuleEvaluation":
            return project_id, "rule_evaluation", str(payload.get("new_rule_evaluation_id", "")), "R3"
        if command_type == "RecordCorrection":
            return project_id, "corrected_record", str(payload.get("erroneous_record_id", "")), "R3"
        if command_type in _C1_DISPATCH_COMMAND_TYPES:
            return project_id, "dispatch", str(payload.get("dispatch_id", "")), "R3"
        if command_type in _C1_LEASE_COMMAND_TYPES:
            lease_id = payload.get("new_lease_id") if command_type == "ClaimExecutionLease" else payload.get("lease_id")
            return project_id, "lease", str(lease_id or ""), "R3"
        if command_type in _C1_ATTEMPT_COMMAND_TYPES:
            attempt_id = payload.get("new_attempt_id") if command_type == "CreateAttempt" else payload.get("attempt_id")
            return project_id, "attempt", str(attempt_id or ""), "R3"
        if command_type in _C1_RESOURCE_COMMAND_TYPES:
            return project_id, "resource", str(payload.get("resource_id", "")), "R3"
        if command_type in _BACKUP_COMMAND_TYPES:
            return project_id, "project_store", str(payload.get("project_id", "")), "R3"
        if command_type == "RegisterArtefact":
            return project_id, "artefact", str(payload.get("new_artefact_id", "")), "R3"
        if command_type in {"RecordScientificReview", "SetArtefactUseAuthority"}:
            return project_id, "artefact", str(payload.get("artefact_id", "")), "R3"
        if command_type == "ResolveDecision":
            return project_id, "decision", str(payload.get("decision_id", "")), "R3"
        if command_type in _CONTEXT_PACKET_COMMAND_TYPES:
            return project_id, "context", str(payload.get("context_id", "")), "R3"

        subject_id = str(
            payload.get(
                "new_task_id" if command_type == "CreateTask" else "task_id",
                "",
            )
        )
        if command_type == "CreateTask":
            definition = payload.get("definition")
            proposed_risk = definition.get("risk_tier_request") if isinstance(definition, dict) else None
            return project_id, "task", subject_id, self._risk_tier(proposed_risk)

        current_risk = self._task_current_risk(snapshot, subject_id)
        if command_type == "AmendTask":
            replacement = payload.get("replacement_definition")
            replacement_risk = replacement.get("risk_tier_request") if isinstance(replacement, dict) else None
        else:
            replacement_id = payload.get("replacement_task_id")
            replacement_revision = payload.get("replacement_task_revision")
            replacement = None
            if (
                isinstance(replacement_id, str)
                and isinstance(replacement_revision, int)
                and not isinstance(replacement_revision, bool)
                and replacement_revision >= 1
            ):
                replacement = self._task_revision_object(replacement_id, replacement_revision)
            replacement_risk = replacement.get("risk_tier_request") if isinstance(replacement, dict) else None
        return project_id, "task", subject_id, self._max_risk(current_risk, replacement_risk)

    @staticmethod
    def _message_content_sha256(state: dict[str, Any]) -> str:
        payload = state.get("published_payload")
        if not isinstance(payload, dict):
            raise IntegrityError("Message history has no immutable publication payload")
        return sha256_hex(canonical_bytes(payload))

    def _message_state(
        self,
        snapshot: LedgerSnapshot,
        message_id: str,
    ) -> dict[str, Any] | None:
        projection = replay(
            snapshot.events,
            schema_registry=self.schemas,
            authority_state_validator=self._authority_state_validator(),
        )
        value = projection.get("streams", {}).get(message_id)
        return dict(value) if isinstance(value, dict) else None

    def _message_adapter_denial(self, command: Command) -> str | None:
        if command.envelope["command_type"] not in _MESSAGE_ADAPTER_COMMAND_TYPES:
            return None
        adapter_id = command.envelope["payload"].get("delivery_adapter_id")
        matches = [entry for entry in self._message_adapter_registry if entry.delivery_adapter_id == adapter_id]
        if len(matches) != 1:
            return "Message adapter registration is missing or ambiguous."
        entry = matches[0]
        now = self.clock()
        if entry.project_id != self.ledger.project_id:
            return "Message adapter registration project does not match the control store."
        if entry.status != "eligible":
            return "Message adapter registration is not eligible."
        if now < entry.effective_at or (entry.expires_at is not None and now >= entry.expires_at):
            return "Message adapter registration is not currently effective."
        if command.envelope["command_type"] not in entry.applicable_command_types:
            return "Message adapter registration lacks the required capability."
        if command.actor_id not in entry.allowed_actor_ids:
            return "Message adapter registration does not bind the command actor."
        return None

    def _prepare_message_command(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
    ) -> dict[str, Any] | Receipt:
        payload = command.envelope["payload"]
        command_type = command.envelope["command_type"]
        if command.envelope.get("project_id") != self.ledger.project_id:
            return self._rejected(
                command,
                observed_version,
                "invalid_command_project",
                "Message command project must match the control-store project.",
            )
        message_id = payload.get("new_message_id") if command_type == "PublishMessage" else payload.get("message_id")
        if message_id != command.target_stream_id:
            return self._rejected(
                command,
                observed_version,
                "invalid_message_subject_identity",
                "Message payload identity must equal the target stream.",
            )
        state = self._message_state(snapshot, command.target_stream_id)
        if command_type == "PublishMessage":
            if state is not None or observed_version != 0:
                return self._rejected(
                    command,
                    observed_version,
                    "message_already_published",
                    "Message publication requires an absent stream.",
                )
            if payload.get("sender_actor_id") != command.actor_id:
                return self._rejected(
                    command,
                    observed_version,
                    "message_sender_mismatch",
                    "Message sender must equal the authority-attributed actor.",
                )
            if payload.get("reply_to_message_id") == message_id:
                return self._rejected(
                    command,
                    observed_version,
                    "message_self_reference",
                    "Message reply linkage cannot reference the new Message itself.",
                )
            if payload.get("message_type") == "acknowledgement" and (
                payload.get("correlation_message_id") != payload.get("reply_to_message_id")
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "message_correlation_mismatch",
                    "Acknowledgement publication correlation must equal its reply link.",
                )
            return payload
        if state is None:
            return self._rejected(
                command,
                observed_version,
                "message_not_published",
                "Message transition requires a committed MessagePublished event.",
            )
        published_payload = state.get("published_payload")
        if not isinstance(published_payload, dict):
            raise IntegrityError("Message history has no immutable publication payload")
        recipients = published_payload.get("recipient_actor_ids")
        if not isinstance(recipients, list) or any(not isinstance(recipient, str) for recipient in recipients):
            raise IntegrityError("Message history has an invalid published recipient list")
        if command_type in _MESSAGE_ADAPTER_COMMAND_TYPES:
            denial = self._message_adapter_denial(command)
            if denial is not None:
                return self._rejected(
                    command,
                    observed_version,
                    "message_adapter_unauthorized",
                    denial,
                )
        content_sha256 = self._message_content_sha256(state)
        if command_type == "RecordMessageDelivery":
            if state.get("status") != "published":
                return self._rejected(
                    command, observed_version, "invalid_message_transition", "Message is not publishable for delivery."
                )
            if not payload.get("delivery_evidence_refs"):
                return self._rejected(
                    command,
                    observed_version,
                    "message_evidence_required",
                    "Message delivery requires immutable delivery evidence.",
                )
            if payload.get("content_sha256") != content_sha256 or payload.get("recipient_actor_ids") != recipients:
                return self._rejected(
                    command,
                    observed_version,
                    "message_content_mismatch",
                    "Delivery must bind the published Message payload and recipients.",
                )
        elif command_type == "AcknowledgeMessage":
            if state.get("status") != "delivered":
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_message_transition",
                    "Message acknowledgement requires delivery.",
                )
            if command.actor_id not in recipients:
                return self._rejected(
                    command,
                    observed_version,
                    "message_recipient_mismatch",
                    "Only a published recipient may acknowledge a Message.",
                )
            if (
                payload.get("content_sha256") != content_sha256
                or payload.get("recipient_actor_ids") != recipients
                or payload.get("source_position") != state.get("published_position")
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "message_content_mismatch",
                    "Acknowledgement must bind the publication payload, recipients, and source position.",
                )
        elif command_type == "RecordMessageDeliveryFailure":
            if state.get("status") != "published":
                return self._rejected(
                    command, observed_version, "invalid_message_transition", "Message failure requires published state."
                )
            if not payload.get("failure_evidence_refs"):
                return self._rejected(
                    command,
                    observed_version,
                    "message_evidence_required",
                    "Message delivery failure requires immutable failure evidence.",
                )
        else:
            raise IntegrityError("unknown Message command")
        return payload

    def _c1_streams(self, snapshot: LedgerSnapshot) -> dict[str, dict[str, Any]]:
        projection = replay(
            snapshot.events,
            schema_registry=self.schemas,
            authority_state_validator=self._authority_state_validator(),
        )
        streams = projection.get("streams", {})
        if not isinstance(streams, dict):
            raise IntegrityError("C1 projection streams are invalid")
        return streams

    def _prepare_c1_command(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
    ) -> dict[str, Any] | Receipt:
        """Validate C1 relationships without materializing unaccepted records."""
        payload = command.envelope["payload"]
        command_type = command.envelope["command_type"]
        if command.envelope.get("project_id") != self.ledger.project_id:
            return self._rejected(
                command,
                observed_version,
                "invalid_command_project",
                "C1 command project must match the control-store project.",
            )

        subject_id = (
            payload.get("task_id")
            if command_type in _C1_TASK_COMMAND_TYPES
            else payload.get("dispatch_id")
            if command_type in _C1_DISPATCH_COMMAND_TYPES
            else payload.get("new_lease_id")
            if command_type == "ClaimExecutionLease"
            else payload.get("lease_id")
            if command_type in _C1_LEASE_COMMAND_TYPES
            else payload.get("new_attempt_id")
            if command_type == "CreateAttempt"
            else payload.get("attempt_id")
            if command_type in _C1_ATTEMPT_COMMAND_TYPES
            else payload.get("resource_id")
        )
        if subject_id != command.target_stream_id:
            return self._rejected(
                command,
                observed_version,
                "invalid_command_subject_identity",
                "C1 payload identity must equal the authority-bound target stream.",
            )
        streams = self._c1_streams(snapshot)

        def rejected(code: str, explanation: str) -> Receipt:
            return self._rejected(command, observed_version, code, explanation)

        if command_type in _C1_TASK_COMMAND_TYPES:
            task = streams.get(command.target_stream_id)
            if not isinstance(task, dict) or int(payload["task_revision"]) != int(task.get("current_revision", 0)):
                return rejected("stale_task_revision", "Readiness must bind the current Task revision.")
            expected_status = "draft" if command_type == "RequestReadiness" else "readiness_pending"
            if task.get("status") != expected_status:
                return rejected("invalid_task_transition", "Readiness command is not valid for the current Task state.")
            evidence = payload.get("readiness_evidence_refs")
            if not isinstance(evidence, list) or not evidence:
                return rejected("readiness_evidence_required", "Readiness requires immutable evidence references.")
            if command_type == "ApproveReadiness" and not payload.get("passed_check_ids"):
                return rejected("readiness_checks_required", "Readiness approval requires passing check identities.")
            return payload

        if command_type == "IssueDispatch":
            definition = payload["definition"]
            task = streams.get(definition["task_id"])
            if (
                payload["dispatch_id"] != definition["dispatch_id"]
                or command.target_stream_id in streams
                or not isinstance(task, dict)
                or task.get("status") != "ready"
                or int(definition["task_revision"]) != int(task.get("current_revision", 0))
            ):
                return rejected("dispatch_task_not_ready", "Dispatch must bind a ready current Task revision.")
            if not definition.get("root_bindings") or not definition.get("context_packet_id"):
                return rejected(
                    "dispatch_context_or_roots_missing", "Dispatch requires exact context and root bindings."
                )
            return payload

        if command_type in {
            "RecordDispatchDelivery",
            "AcknowledgeDispatch",
            "ExpireDispatch",
            "WithdrawDispatch",
            "ClaimDispatch",
        }:
            dispatch = streams.get(command.target_stream_id)
            if not isinstance(dispatch, dict):
                return rejected("dispatch_missing", "Dispatch transition requires a committed Dispatch.")
            if command_type == "RecordDispatchDelivery":
                if dispatch.get("status") != "issued" or not payload.get("delivery_evidence_refs"):
                    return rejected(
                        "invalid_dispatch_transition", "Delivery requires issued Dispatch and delivery evidence."
                    )
                return payload
            if command_type == "AcknowledgeDispatch":
                delivery = dispatch.get("delivery", {})
                if dispatch.get("status") != "delivered" or payload["recipient_actor_id"] != delivery.get(
                    "recipient_actor_id"
                ):
                    return rejected("invalid_dispatch_transition", "Acknowledgement requires the delivered recipient.")
                return payload
            if command_type == "ExpireDispatch":
                prior_state = dispatch.get("status")
                if (
                    prior_state not in {"issued", "delivered", "acknowledged"}
                    or payload["observed_prior_state"] != prior_state
                ):
                    return rejected(
                        "invalid_dispatch_transition", "Expiry requires its exact observed pre-claim state."
                    )
                definition = dispatch.get("definition")
                deadline_field = "delivery_deadline" if prior_state == "issued" else "claim_deadline"
                expected_deadline = definition.get(deadline_field) if isinstance(definition, dict) else None
                deadline = self._resource_grant_expiry(expected_deadline)
                observed_at = self._resource_grant_expiry(payload.get("observed_at"))
                now = self._c1_trusted_now()
                if (
                    payload.get("observed_deadline") != expected_deadline
                    or deadline is None
                    or observed_at is None
                    or now is None
                    or observed_at < deadline
                    or observed_at > now
                ):
                    return rejected(
                        "dispatch_expiry_observation_invalid",
                        "Dispatch expiry requires its exact deadline observed at or after that deadline and not in the future.",
                    )
                return payload
            if command_type == "WithdrawDispatch":
                prior_state = dispatch.get("status")
                if prior_state == "issued" and payload["observed_prior_state"] == "issued":
                    return payload
                stop = payload.get("attempt_stop_disposition")
                attempts = [
                    value
                    for stream_id, value in streams.items()
                    if isinstance(value, dict)
                    and value.get("dispatch_id") == command.target_stream_id
                    and value.get("attempt_id") == stream_id
                ]
                if (
                    prior_state != "claimed"
                    or payload.get("observed_prior_state") != "claimed"
                    or len(attempts) != 1
                    or attempts[0].get("status") not in {"completed", "failed", "partial", "abandoned", "superseded"}
                    or not isinstance(stop, dict)
                    or not stop.get("children_closed")
                    or not stop.get("writers_closed")
                ):
                    return rejected(
                        "invalid_dispatch_transition",
                        "Claimed withdrawal requires its terminal Attempt and closed stop disposition.",
                    )
                return payload
            task = streams.get(payload["task_id"])
            lease = streams.get(payload["lease_id"])
            definition = dispatch.get("definition") if isinstance(dispatch, dict) else None
            claim_deadline = self._resource_grant_expiry(
                definition.get("claim_deadline") if isinstance(definition, dict) else None
            )
            trusted_now = self._c1_trusted_now()
            expected_tail_hash = snapshot.events[-1]["event_hash"] if snapshot.events else "0" * 64
            if (
                dispatch.get("status") != "acknowledged"
                or not isinstance(definition, dict)
                or claim_deadline is None
                or trusted_now is None
                or trusted_now >= claim_deadline
                or not isinstance(task, dict)
                or task.get("status") != "ready"
                or payload["task_id"] != dispatch.get("task_id")
                or int(payload["task_revision"]) != int(dispatch.get("task_revision", 0))
                or int(payload["task_revision"]) != int(task.get("current_revision", 0))
                or payload["declared_write_set"] != ["dispatch", "task"]
                or payload["expected_dispatch_stream_version"] != observed_version
                or payload["expected_task_stream_version"] != snapshot.stream_versions.get(payload["task_id"], 0)
                or payload["expected_global_position"] != snapshot.global_position
                or payload["expected_tail_hash"] != expected_tail_hash
                or not isinstance(lease, dict)
                or lease.get("status") != "active"
                or not self._c1_lease_is_current(lease)
                or lease.get("task_id") != payload["task_id"]
                or int(lease.get("task_revision", 0)) != int(payload["task_revision"])
                or lease.get("dispatch_id") != command.target_stream_id
            ):
                return rejected(
                    "claim_dispatch_precondition_failed",
                    "Claim must bind the current ready Task, Dispatch, and active Lease.",
                )
            _, grant_reason = self._current_c1_lease_resource_grant(streams=streams, lease=lease)
            if grant_reason is not None:
                return rejected(
                    grant_reason,
                    "Claim requires the current materialized Resource grant.",
                )
            return payload

        if command_type == "CreateAttempt":
            dispatch = streams.get(payload["dispatch_id"])
            task = streams.get(payload["task_id"])
            lease_id = dispatch.get("lease_id") if isinstance(dispatch, dict) else None
            lease = streams.get(lease_id) if isinstance(lease_id, str) else None
            existing = [
                value
                for stream_id, value in streams.items()
                if isinstance(value, dict)
                and value.get("attempt_id") == stream_id
                and value.get("attempt_id")
                and value.get("task_id") == payload["task_id"]
                and value.get("dispatch_id") == payload["dispatch_id"]
            ]
            if (
                command.target_stream_id in streams
                or not isinstance(dispatch, dict)
                or dispatch.get("status") != "claimed"
                or dispatch.get("task_id") != payload["task_id"]
                or int(dispatch.get("task_revision", 0)) != int(payload["task_revision"])
                or not isinstance(task, dict)
                or task.get("task_id") != payload["task_id"]
                or task.get("status") != "in_progress"
                or int(payload["task_revision"]) != int(task.get("current_revision", 0))
                or not isinstance(lease, dict)
                or lease.get("lease_id") != lease_id
                or lease.get("status") != "active"
                or not self._c1_lease_is_current(lease)
                or lease.get("task_id") != payload["task_id"]
                or int(lease.get("task_revision", 0)) != int(payload["task_revision"])
                or lease.get("dispatch_id") != payload["dispatch_id"]
                or lease.get("attempt_id") != command.target_stream_id
                or payload["attempt_ordinal"] != 1
                or payload["execution_epoch"] != 1
                or existing
            ):
                return rejected(
                    "attempt_creation_precondition_failed",
                    "Initial Attempt requires the current Task, Dispatch, and active Lease relation.",
                )
            _, grant_reason = self._current_c1_lease_resource_grant(streams=streams, lease=lease)
            if grant_reason is not None:
                return rejected(
                    grant_reason,
                    "Attempt creation requires the current materialized Resource grant.",
                )
            return payload

        if command_type == "RequestResourceGrant":
            if command.target_stream_id in streams:
                return rejected(
                    "resource_request_already_recorded", "Resource request requires an empty Resource stream."
                )
            request = payload["resource_request"]
            if (
                request["requesting_actor_id"] != command.actor_id
                or request["requesting_authority_grant_id"] != command.envelope["authority_grant_id"]
            ):
                return rejected(
                    "resource_request_authority_mismatch",
                    "Resource request actor and authority must bind its committed request command.",
                )
            if request["expected_control_store_position"] != snapshot.global_position:
                return rejected(
                    "resource_request_stale_position",
                    "Resource request must bind the current control-store position.",
                )
            return payload

        if command_type == "ClaimExecutionLease":
            if command.target_stream_id in streams:
                return rejected("lease_already_granted", "Lease claim requires an empty Lease stream.")
            resource = streams.get(payload["resource_grant_id"])
            try:
                stored_grant, grant_reason = self._current_materialized_resource_grant(
                    resource_grant_id=payload["resource_grant_id"],
                    resource=resource,
                    trusted_authority=self._current_trusted_runtime_authority(),
                )
            except IntegrityError:
                stored_grant, grant_reason = None, "resource_grant_invalid"
            if grant_reason is not None or stored_grant is None:
                return rejected(
                    grant_reason or "resource_grant_invalid",
                    "Lease claim requires the current committed Resource grant.",
                )
            request = stored_grant["granted_claims"]
            dispatch = streams.get(payload["dispatch_id"])
            definition = dispatch.get("definition") if isinstance(dispatch, dict) else None
            task = streams.get(payload["task_id"])
            dispatch_capabilities = definition.get("capabilities") if isinstance(definition, dict) else None
            dispatch_permissions = definition.get("permissions") if isinstance(definition, dict) else None
            capability_scope = payload.get("capability_scope")
            if (
                payload["task_id"] != request.get("task_id")
                or not isinstance(task, dict)
                or task.get("task_id") != payload["task_id"]
                or int(task.get("current_revision", 0)) != int(payload["task_revision"])
                or payload["dispatch_id"] != request.get("dispatch_id")
                or payload["attempt_id"] != request.get("attempt_id")
                or command.actor_id != request.get("requesting_actor_id")
                or payload["holder_actor_id"] != command.actor_id
                or payload["operational_profile"] != request.get("operational_profile")
                or not isinstance(definition, dict)
                or not isinstance(dispatch_capabilities, list)
                or not isinstance(dispatch_permissions, list)
                or not isinstance(capability_scope, list)
                or not all(
                    isinstance(item, str) for item in dispatch_capabilities + dispatch_permissions + capability_scope
                )
                or payload["holder_profile"] != request.get("requesting_profile")
                or payload["holder_profile"] != definition.get("target_profile")
                or definition.get("task_id") != payload["task_id"]
                or int(definition.get("task_revision", 0)) != int(payload["task_revision"])
                or set(capability_scope) != set(dispatch_capabilities) | set(dispatch_permissions)
            ):
                return rejected(
                    "resource_grant_binding_mismatch",
                    "Lease claim must bind the committed Resource grant request and referenced Dispatch.",
                )
            grant_expiry = self._resource_grant_expiry(stored_grant["expires_at"])
            granted_at = self._resource_grant_expiry(payload.get("granted_at"))
            lease_expiry = self._resource_grant_expiry(payload["expires_at"])
            now = self._c1_trusted_now()
            if grant_expiry is None or lease_expiry is None or now is None:
                return rejected("resource_grant_invalid", "Resource grant expiry is invalid.")
            if granted_at is None or granted_at > now or granted_at >= lease_expiry:
                return rejected(
                    "lease_granted_at_invalid",
                    "Lease grant time must be within the current Resource grant and trusted lease interval.",
                )
            if grant_expiry <= now:
                return rejected("resource_grant_expired", "Resource grant is no longer current.")
            if lease_expiry > grant_expiry:
                return rejected("resource_grant_expiry_exceeded", "Lease expiry exceeds the Resource grant expiry.")
            if lease_expiry <= now:
                return rejected("lease_expired", "Lease expiry must be later than trusted current time.")
            return payload

        if command_type in {
            "RenewExecutionLease",
            "ReleaseExecutionLease",
            "ExpireLease",
            "RevokeLease",
            "RecordHeartbeat",
        }:
            lease = streams.get(command.target_stream_id)
            if not isinstance(lease, dict) or lease.get("status") != "active":
                return rejected("lease_not_active", "Lease transition requires an active LeaseGranted record.")
            if payload.get("lease_id") != lease.get("lease_id"):
                return rejected("lease_relation_mismatch", "Lease command must bind its active Lease.")
            if command_type == "RenewExecutionLease" and (
                payload["holder_actor_id"] != lease.get("holder_actor_id")
                or command.actor_id != lease.get("holder_actor_id")
            ):
                return rejected("lease_holder_mismatch", "Lease transition requires the current holder.")
            if command_type == "ReleaseExecutionLease" and payload["holder_actor_id"] != lease.get("holder_actor_id"):
                return rejected("lease_holder_mismatch", "Lease release must preserve its immutable holder.")
            if command_type == "RenewExecutionLease":
                prior_expiry = self._resource_grant_expiry(payload["prior_expiry"])
                new_expiry = self._resource_grant_expiry(payload["new_expiry"])
                if (
                    payload["prior_expiry"] != lease.get("expires_at")
                    or payload["renewal_policy_ref"] != lease.get("renewal_policy_ref")
                    or prior_expiry is None
                    or new_expiry is None
                    or new_expiry <= prior_expiry
                ):
                    return rejected("lease_renewal_mismatch", "Lease renewal must bind its current expiry and policy.")
            if command_type == "ReleaseExecutionLease":
                observed_at = self._resource_grant_expiry(payload.get("observed_at"))
                now = self._c1_trusted_now()
                if observed_at is None or now is None or observed_at > now:
                    return rejected(
                        "lease_release_observation_invalid",
                        "Lease release observation must not be later than trusted current time.",
                    )
            if command_type == "ExpireLease":
                observed_at = self._resource_grant_expiry(payload.get("observed_at"))
                lease_expiry = self._resource_grant_expiry(lease.get("expires_at"))
                now = self._c1_trusted_now()
                if (
                    observed_at is None
                    or lease_expiry is None
                    or now is None
                    or observed_at < lease_expiry
                    or observed_at > now
                ):
                    return rejected(
                        "lease_expiry_observation_invalid",
                        "Lease expiry requires an observation at or after its deadline and not in the future.",
                    )
            if command_type == "RevokeLease":
                observed_at = self._resource_grant_expiry(payload.get("observed_at"))
                now = self._c1_trusted_now()
                if observed_at is None or now is None or observed_at > now:
                    return rejected(
                        "lease_revocation_observation_invalid",
                        "Lease revocation observation must not be later than trusted current time.",
                    )
            if command_type in {"RenewExecutionLease", "RecordHeartbeat"}:
                context, context_reason = self._current_c1_lease_context(
                    streams=streams,
                    lease=lease,
                    require_running_attempt=command_type == "RecordHeartbeat",
                )
                if context is None:
                    return rejected(
                        context_reason or "lease_relation_mismatch",
                        "Lease command requires the current Task, Dispatch, Attempt, and Lease relation.",
                    )
                _, _, attempt, now = context
                resource_grant_id = lease.get("resource_grant_id")
                resource = streams.get(resource_grant_id) if isinstance(resource_grant_id, str) else None
                try:
                    trusted_authority = self._current_trusted_runtime_authority()
                    stored_grant, grant_reason = self._current_materialized_resource_grant(
                        resource_grant_id=resource_grant_id,
                        resource=resource,
                        trusted_authority=trusted_authority,
                    )
                except IntegrityError:
                    stored_grant, grant_reason = None, "resource_grant_invalid"
                if grant_reason is not None or stored_grant is None:
                    return rejected(
                        grant_reason or "resource_grant_invalid",
                        "Lease command requires the current committed Resource grant.",
                    )
                grant_expiry = self._resource_grant_expiry(stored_grant.get("expires_at"))
                if grant_expiry is None:
                    return rejected("resource_grant_invalid", "Resource grant expiry is invalid.")
                if now >= grant_expiry:
                    return rejected("resource_grant_expired", "Resource grant is no longer current.")
                if (
                    stored_grant.get("resource_grant_id") != resource_grant_id
                    or stored_grant.get("task_id") != lease.get("task_id")
                    or stored_grant.get("dispatch_id") != lease.get("dispatch_id")
                    or stored_grant.get("attempt_id") != lease.get("attempt_id")
                ):
                    return rejected("resource_grant_mismatch", "Lease relation does not match its Resource grant.")
                if lease.get("renewal_policy_ref") != stored_grant.get("renewal_policy_ref"):
                    return rejected(
                        "lease_renewal_mismatch"
                        if command_type == "RenewExecutionLease"
                        else "resource_grant_mismatch",
                        "Lease policy does not match its Resource grant.",
                    )
                threshold = self._grant_heartbeat_stale_threshold(stored_grant)
                if threshold is None:
                    return rejected("resource_grant_invalid", "Resource grant heartbeat policy is invalid.")
                snapshot_events = tuple(self.ledger.snapshot().events)
                heartbeat_events = self._heartbeat_events_for_lease(
                    snapshot_events,
                    lease["lease_id"],
                )
                last_heartbeat = lease.get("last_heartbeat")
                if command_type == "RenewExecutionLease":
                    profile_constraints = stored_grant.get("profile_constraints")
                    if (
                        not isinstance(profile_constraints, dict)
                        or profile_constraints.get("renewal_allowed") is not True
                    ):
                        return rejected("lease_renewal_mismatch", "Resource grant does not permit lease renewal.")
                    if not isinstance(last_heartbeat, dict) or not heartbeat_events:
                        return rejected(
                            "lease_renewal_heartbeat_missing",
                            "Lease renewal requires one latest accepted heartbeat.",
                        )
                    latest_heartbeat_event = heartbeat_events[-1]
                    latest_heartbeat = latest_heartbeat_event["payload"]
                    latest_heartbeat_id = latest_heartbeat.get("heartbeat_id")
                    if latest_heartbeat != last_heartbeat or not isinstance(latest_heartbeat_id, str):
                        return rejected(
                            "lease_renewal_heartbeat_mismatch",
                            "Lease renewal heartbeat does not match canonical history.",
                        )
                    if payload.get("heartbeat_evidence_refs") != [latest_heartbeat_id]:
                        return rejected(
                            "lease_renewal_heartbeat_mismatch",
                            "Lease renewal must cite exactly its latest heartbeat.",
                        )
                    heartbeat_wall_time = self._resource_grant_expiry(latest_heartbeat.get("wall_time"))
                    heartbeat_recorded_at = self._resource_grant_expiry(latest_heartbeat_event.get("recorded_at"))
                    if heartbeat_wall_time is None or heartbeat_recorded_at is None:
                        return rejected(
                            "lease_renewal_heartbeat_mismatch",
                            "Lease renewal heartbeat timestamps are invalid.",
                        )
                    if now > heartbeat_wall_time + timedelta(
                        seconds=threshold
                    ) or now > heartbeat_recorded_at + timedelta(seconds=threshold):
                        return rejected("heartbeat_stale", "Lease renewal heartbeat is stale.")
                    if payload["renewal_policy_ref"] != stored_grant.get("renewal_policy_ref"):
                        return rejected("lease_renewal_mismatch", "Lease renewal policy is not current.")
                    renewal_expiry = self._resource_grant_expiry(payload["new_expiry"])
                    if renewal_expiry is None or renewal_expiry > grant_expiry:
                        return rejected(
                            "resource_grant_expiry_exceeded", "Lease expiry exceeds the Resource grant expiry."
                        )
                else:
                    started = attempt.get("start")
                    if not isinstance(started, dict) or payload.get("process_identity_id") != started.get(
                        "process_identity_id"
                    ):
                        return rejected(
                            "heartbeat_process_mismatch",
                            "Heartbeat requires the active Lease's running process identity.",
                        )
                    if (
                        payload.get("host_identity") != trusted_authority.host_identity
                        or payload.get("host_identity") != stored_grant.get("host_identity")
                        or payload.get("boot_identity") != trusted_authority.boot_identity
                        or payload.get("boot_identity") != stored_grant.get("boot_identity")
                    ):
                        return rejected(
                            "heartbeat_runtime_identity_mismatch",
                            "Heartbeat host and boot must match the current Resource grant authority.",
                        )
                    heartbeat_sequence = payload.get("heartbeat_sequence")
                    heartbeat_id = payload.get("heartbeat_id")
                    wall_time = self._resource_grant_expiry(payload.get("wall_time"))
                    monotonic_time = payload.get("monotonic_time")
                    work_unit_progress = payload.get("work_unit_progress")
                    issued_at = self._resource_grant_expiry(stored_grant.get("issued_at"))
                    if (
                        type(heartbeat_sequence) is not int
                        or not isinstance(heartbeat_id, str)
                        or wall_time is None
                        or type(monotonic_time) is not int
                        or type(work_unit_progress) is not int
                        or issued_at is None
                    ):
                        return rejected("heartbeat_identity_invalid", "Heartbeat identity and time values are invalid.")
                    if wall_time > now:
                        return rejected("heartbeat_time_invalid", "Heartbeat wall time cannot be in the future.")
                    if any(
                        event["payload"].get("heartbeat_id") == heartbeat_id
                        for event in snapshot_events
                        if event.get("event_type") == "HeartbeatRecorded" and isinstance(event.get("payload"), dict)
                    ):
                        return rejected("heartbeat_id_conflict", "Heartbeat ID already exists in canonical history.")
                    if last_heartbeat is None:
                        if heartbeat_events or heartbeat_sequence != 1:
                            return rejected(
                                "heartbeat_sequence_mismatch", "First heartbeat sequence must be exactly one."
                            )
                        if wall_time < issued_at:
                            return rejected("heartbeat_time_invalid", "First heartbeat precedes its Resource grant.")
                        stale_boundary = issued_at
                    else:
                        if (
                            not isinstance(last_heartbeat, dict)
                            or not heartbeat_events
                            or heartbeat_events[-1]["payload"] != last_heartbeat
                        ):
                            return rejected("heartbeat_identity_invalid", "Latest heartbeat is not canonical.")
                        prior_sequence = last_heartbeat.get("heartbeat_sequence")
                        prior_wall_time = self._resource_grant_expiry(last_heartbeat.get("wall_time"))
                        prior_monotonic_time = last_heartbeat.get("monotonic_time")
                        prior_work_unit_progress = last_heartbeat.get("work_unit_progress")
                        if (
                            type(prior_sequence) is not int
                            or prior_wall_time is None
                            or type(prior_monotonic_time) is not int
                            or type(prior_work_unit_progress) is not int
                            or heartbeat_sequence != prior_sequence + 1
                            or wall_time <= prior_wall_time
                            or monotonic_time <= prior_monotonic_time
                            or work_unit_progress <= prior_work_unit_progress
                        ):
                            return rejected(
                                "heartbeat_progression_mismatch",
                                "Heartbeat sequence, time, and progress must strictly advance.",
                            )
                        stale_boundary = prior_wall_time
                    if now > stale_boundary + timedelta(seconds=threshold) or wall_time > stale_boundary + timedelta(
                        seconds=threshold
                    ):
                        return rejected("heartbeat_stale", "Heartbeat cannot revive a stale lease.")
            return payload

        if command_type == "ClaimAttempt":
            lease = streams.get(payload["lease_id"])
            if not isinstance(lease, dict) or lease.get("status") != "active":
                return rejected(
                    "claim_attempt_precondition_failed",
                    "Attempt claim requires the current Task, Dispatch, and active Lease relation.",
                )
            context, _ = self._current_c1_lease_context(
                streams=streams,
                lease=lease,
                require_running_attempt=False,
                allowed_attempt_statuses=frozenset({"created"}),
                require_attempt_lease=False,
            )
            if context is None:
                return rejected(
                    "claim_attempt_precondition_failed",
                    "Attempt claim requires the current Task, Dispatch, and active Lease relation.",
                )
            task, dispatch, attempt, _ = context
            grant = lease.get("grant")
            if (
                payload["attempt_id"] != attempt.get("attempt_id")
                or payload["lease_id"] != lease.get("lease_id")
                or payload["task_id"] != task.get("task_id")
                or int(payload["task_revision"]) != int(task.get("current_revision", 0))
                or payload["dispatch_id"] != dispatch.get("dispatch_id")
                or command.actor_id != lease.get("holder_actor_id")
                or not isinstance(grant, dict)
                or grant.get("holder_actor_id") != lease.get("holder_actor_id")
            ):
                return rejected(
                    "claim_attempt_precondition_failed",
                    "Attempt claim requires the current Task, Dispatch, and active Lease relation.",
                )
            _, grant_reason = self._current_c1_lease_resource_grant(streams=streams, lease=lease)
            if grant_reason is not None:
                return rejected(
                    grant_reason,
                    "Attempt claim requires the current materialized Resource grant.",
                )
            return payload

        if command_type == "StartAttempt":
            attempt = streams.get(command.target_stream_id)
            lease_id = attempt.get("lease_id") if isinstance(attempt, dict) else None
            lease = streams.get(lease_id) if isinstance(lease_id, str) else None
            if not isinstance(lease, dict) or lease.get("status") != "active":
                return rejected(
                    "start_attempt_precondition_failed",
                    "Attempt start requires the current Task, Dispatch, and active Lease relation.",
                )
            context, _ = self._current_c1_lease_context(
                streams=streams,
                lease=lease,
                require_running_attempt=False,
                allowed_attempt_statuses=frozenset({"claimed"}),
            )
            if context is None:
                return rejected(
                    "start_attempt_precondition_failed",
                    "Attempt start requires the current Task, Dispatch, and active Lease relation.",
                )
            _, dispatch, attempt, _ = context
            definition = dispatch.get("definition")
            grant = lease.get("grant")
            if (
                payload["attempt_id"] != attempt.get("attempt_id")
                or not isinstance(definition, dict)
                or command.actor_id != lease.get("holder_actor_id")
                or not isinstance(grant, dict)
                or grant.get("holder_actor_id") != lease.get("holder_actor_id")
                or payload["session_identity"] != grant.get("holder_session")
                or payload["context_packet_id"] != definition.get("context_packet_id")
                or payload["root_bindings"] != definition.get("root_bindings")
            ):
                return rejected(
                    "start_attempt_precondition_failed",
                    "Attempt start requires the current Task, Dispatch, active Lease, context, and roots.",
                )
            _, grant_reason = self._current_c1_lease_resource_grant(streams=streams, lease=lease)
            if grant_reason is not None:
                return rejected(
                    grant_reason,
                    "Attempt start requires the current materialized Resource grant.",
                )
            return payload

        if command_type == "ReleaseResources":
            resource = streams.get(command.target_stream_id)
            if not isinstance(resource, dict) or resource.get("status") != "active":
                return rejected("resource_request_missing", "Resource release requires ResourceGrantRequested history.")
            stored_grant, grant_reason = self._stored_materialized_resource_grant(
                resource_grant_id=command.target_stream_id,
                resource=resource,
            )
            if stored_grant is None:
                return rejected(
                    grant_reason or "resource_grant_invalid",
                    "Resource release requires one authoritative committed Resource grant.",
                )
            lease = streams.get(payload["lease_id"])
            if (
                not isinstance(lease, dict)
                or lease.get("lease_id") != payload["lease_id"]
                or lease.get("resource_grant_id") != command.target_stream_id
                or stored_grant.get("resource_grant_id") != command.target_stream_id
                or stored_grant.get("task_id") != lease.get("task_id")
                or stored_grant.get("dispatch_id") != lease.get("dispatch_id")
                or stored_grant.get("attempt_id") != lease.get("attempt_id")
            ):
                return rejected("resource_lease_mismatch", "Resource release must bind its owning Lease.")
            if lease.get("status") not in {"released", "expired", "revoked"}:
                return rejected(
                    "resource_release_lease_not_terminal",
                    "Resource release requires the owning Lease to be terminal.",
                )
            if not self._meaningful_text_list(payload.get("consumption_reconciliation")):
                return rejected(
                    "resource_consumption_reconciliation_invalid",
                    "Resource release requires non-empty meaningful consumption reconciliation.",
                )
            granted_claims = stored_grant.get("granted_claims")
            cleanup_obligations = (
                granted_claims.get("cleanup_obligations") if isinstance(granted_claims, dict) else None
            )
            if cleanup_obligations is not None and not self._meaningful_text_list(cleanup_obligations):
                return rejected("resource_grant_invalid", "Resource grant cleanup obligations are invalid.")
            if cleanup_obligations and not self._meaningful_text_list(payload.get("cleanup_evidence_refs")):
                return rejected(
                    "resource_cleanup_evidence_missing",
                    "Resource release requires cleanup evidence for granted cleanup obligations.",
                )
            return payload
        raise IntegrityError(f"unsupported C1 command type: {command_type}")

    def _prepare_c2_command(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
    ) -> dict[str, Any] | Receipt:
        """Validate an active C2 transition against replayed state."""
        payload = command.envelope["payload"]
        command_type = command.envelope["command_type"]
        if command.envelope.get("project_id") != self.ledger.project_id:
            return self._rejected(
                command,
                observed_version,
                "invalid_command_project",
                "C2 command project must match the control-store project.",
            )
        streams = self._c1_streams(snapshot)
        if command_type in _C2_BLOCKER_COMMAND_TYPES:
            blocker_id = payload.get("new_blocker_id") if command_type == "RecordBlocker" else payload.get("blocker_id")
            if blocker_id != command.target_stream_id:
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_command_subject_identity",
                    "C2 Blocker payload identity must equal the authority-bound target stream.",
                )
            blocker = streams.get(command.target_stream_id)
            if command_type == "RecordBlocker":
                if blocker is not None or not payload.get("blocker_evidence_refs"):
                    return self._rejected(
                        command,
                        observed_version,
                        "invalid_blocker_transition",
                        "RecordBlocker requires an empty stream and evidence.",
                    )
                return payload
            if (
                not isinstance(blocker, dict)
                or blocker.get("status") != "open"
                or not payload.get("resolution_evidence_refs")
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_blocker_transition",
                    "ResolveBlocker requires an open Blocker and resolution evidence.",
                )
            return payload
        if command_type in _C2_ATTEMPT_COMMAND_TYPES:
            attempt_id = payload.get("new_attempt_id") if command_type == "RetryAttempt" else payload.get("attempt_id")
            if attempt_id != command.target_stream_id:
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_command_subject_identity",
                    "C2 Attempt payload identity must equal the authority-bound target stream.",
                )
            if command_type == "RetryAttempt":
                prior = streams.get(payload.get("prior_attempt_id"))
                successors = [
                    value
                    for stream_id, value in streams.items()
                    if isinstance(value, dict)
                    and value.get("attempt_id") == stream_id
                    and value.get("prior_attempt_id") == payload.get("prior_attempt_id")
                ]
                if successors:
                    return self._rejected(
                        command,
                        observed_version,
                        "attempt_already_retried",
                        "RetryAttempt prior outcome already has a committed successor.",
                    )
                if (
                    command.target_stream_id in streams
                    or not isinstance(prior, dict)
                    or prior.get("status") not in {"completed", "failed", "partial", "abandoned"}
                    or payload.get("prior_outcome") != prior.get("status")
                    or int(payload.get("attempt_ordinal", 0)) != int(prior.get("attempt_ordinal", 0)) + 1
                    or int(payload.get("execution_epoch", 0)) <= int(prior.get("execution_epoch", 0))
                ):
                    return self._rejected(
                        command,
                        observed_version,
                        "attempt_retry_precondition_failed",
                        "RetryAttempt requires an empty new stream and the exact retryable prior outcome and lineage.",
                    )
                return payload
            attempt = streams.get(command.target_stream_id)
            if not isinstance(attempt, dict):
                return self._rejected(
                    command,
                    observed_version,
                    "attempt_missing",
                    "C2 Attempt transition requires a committed Attempt.",
                )
            status = attempt.get("status")
            if command_type in {"CompleteAttempt", "FailAttempt", "RecordAttemptPartial"}:
                if status != "running":
                    return self._rejected(
                        command,
                        observed_version,
                        "invalid_attempt_transition",
                        "Attempt outcome requires a running Attempt.",
                    )
                if command_type == "RecordAttemptPartial":
                    return {
                        "task_id": attempt["task_id"],
                        "completed_obligations": payload["completed_obligations"],
                        "unmet_obligations": payload["unmet_obligations"],
                        "accepted_artefact_ids": payload["candidate_artefact_ids"],
                        "claim_restrictions": payload["restrictions"],
                        "resume_policy": payload["stop_cause"],
                        "subject_kind": "task",
                    }
                return payload
            if command_type == "PauseAttempt":
                if status != "running":
                    return self._rejected(
                        command,
                        observed_version,
                        "invalid_attempt_transition",
                        "PauseAttempt requires a running Attempt.",
                    )
                return payload
            if command_type == "ResumeAttempt":
                lease = streams.get(payload.get("lease_id"))
                checkpoint = payload.get("checkpoint_disposition")
                if (
                    status != "paused"
                    or payload.get("compatibility") != "compatible"
                    or not isinstance(checkpoint, dict)
                    or checkpoint.get("compatibility") != "compatible"
                    or not isinstance(lease, dict)
                    or lease.get("status") != "active"
                    or lease.get("attempt_id") != command.target_stream_id
                ):
                    return self._rejected(
                        command,
                        observed_version,
                        "attempt_resume_precondition_failed",
                        "ResumeAttempt requires confirmed compatible checkpoint state and its active Lease.",
                    )
                return payload
            if command_type == "RequestAttemptStop":
                if status != "running":
                    return self._rejected(
                        command,
                        observed_version,
                        "invalid_attempt_transition",
                        "RequestAttemptStop requires a running Attempt.",
                    )
                return payload
            if command_type == "ConfirmAttemptStopped":
                process = payload.get("process_disposition")
                if (
                    status != "stopping"
                    or not isinstance(process, dict)
                    or not process.get("children_closed")
                    or not process.get("writers_closed")
                ):
                    return self._rejected(
                        command,
                        observed_version,
                        "attempt_stop_not_confirmed",
                        "ConfirmAttemptStopped requires a requested stop and closed process writers and children.",
                    )
                return payload
            if command_type == "SupersedeAttempt":
                if (
                    status not in {"created", "claimed", "running", "paused", "stopping"}
                    or payload.get("replacement_attempt_id") == command.target_stream_id
                    or int(payload.get("execution_epoch", 0)) <= int(attempt.get("execution_epoch", 0))
                    or not payload.get("retained_evidence_refs")
                ):
                    return self._rejected(
                        command,
                        observed_version,
                        "attempt_supersession_precondition_failed",
                        "SupersedeAttempt requires nonterminal state, a distinct replacement, a later epoch, and evidence.",
                    )
                return payload
        if command_type in _C2_CHECKPOINT_COMMAND_TYPES:
            if payload.get("attempt_id") != command.target_stream_id:
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_command_subject_identity",
                    "Checkpoint authority must bind the payload Attempt and target stream.",
                )
            attempt = streams.get(command.target_stream_id)
            lease = streams.get(attempt.get("lease_id")) if isinstance(attempt, dict) else None
            task = streams.get(payload.get("task_id"))
            latest = attempt.get("latest_checkpoint") if isinstance(attempt, dict) else None
            if (
                not isinstance(attempt, dict)
                or attempt.get("status") not in {"running", "paused", "stopping"}
                or payload.get("task_id") != attempt.get("task_id")
                or int(payload.get("task_revision", 0)) != int(attempt.get("task_revision", 0))
                or not isinstance(task, dict)
                or int(task.get("current_revision", 0)) != int(payload.get("task_revision", 0))
                or not isinstance(lease, dict)
                or lease.get("status") != "active"
                or lease.get("attempt_id") != command.target_stream_id
                or payload.get("integrity_status") != "verified"
                or payload.get("validation_status") != "passed"
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "checkpoint_precondition_failed",
                    "Checkpoint requires the current Attempt, Task revision, active Lease, and verified validation.",
                )
            if isinstance(latest, dict) and (
                payload.get("checkpoint_manifest_id") == latest.get("checkpoint_manifest_id")
                or int(payload.get("completed_units", -1)) < int(latest.get("completed_units", 0))
                or int(payload.get("remaining_units", -1)) > int(latest.get("remaining_units", 0))
                or payload.get("compatibility_fingerprint") != latest.get("compatibility_fingerprint")
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "checkpoint_progression_invalid",
                    "Checkpoint must preserve its fingerprint and monotonically advance units with a new manifest.",
                )
            return payload
        if command_type in _C2_OPERATOR_COMMAND_TYPES:
            if payload.get("attempt_id") != command.target_stream_id:
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_command_subject_identity",
                    "Operator command must bind its payload Attempt and target stream.",
                )
            attempt = streams.get(command.target_stream_id)
            lease = streams.get(payload.get("lease_id"))
            if (
                not isinstance(attempt, dict)
                or not isinstance(lease, dict)
                or lease.get("status") != "active"
                or lease.get("attempt_id") != command.target_stream_id
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "operator_lease_precondition_failed",
                    "Operator command requires its Attempt's active Lease.",
                )
            status = attempt.get("status")
            operation_state = attempt.get("operation_state")
            if command_type == "RequestPause":
                if status != "running" or operation_state in {"pause_requested", "stop_requested"}:
                    return self._rejected(
                        command,
                        observed_version,
                        "operator_pause_precondition_failed",
                        "RequestPause requires a running Attempt without a pending control request.",
                    )
                return payload
            if command_type == "ConfirmPause":
                process = payload.get("process_disposition")
                if (
                    status != "running"
                    or operation_state != "pause_requested"
                    or not isinstance(process, dict)
                    or not process.get("children_closed")
                    or not process.get("writers_closed")
                ):
                    return self._rejected(
                        command,
                        observed_version,
                        "operator_pause_not_confirmed",
                        "ConfirmPause requires the pending request and quiesced process writers and children.",
                    )
                return payload
            if command_type == "RequestResume":
                pause = attempt.get("pause_confirmation")
                if (
                    status != "paused"
                    or operation_state != "pause_confirmed"
                    or payload.get("compatibility") != "compatible"
                    or int(payload.get("new_execution_epoch", 0)) <= int(attempt.get("execution_epoch", 0))
                    or not isinstance(pause, dict)
                    or payload.get("checkpoint_manifest_id")
                    != pause.get("checkpoint_disposition", {}).get("checkpoint_manifest_id")
                    or not payload.get("compatibility_evidence_refs")
                ):
                    return self._rejected(
                        command,
                        observed_version,
                        "operator_resume_precondition_failed",
                        "RequestResume requires a confirmed pause and its exact compatible checkpoint.",
                    )
                return payload
            if command_type == "RequestStop":
                if status not in {"running", "paused"} or operation_state == "stop_requested":
                    return self._rejected(
                        command,
                        observed_version,
                        "operator_stop_precondition_failed",
                        "RequestStop requires active or confirmed-paused execution without a pending stop.",
                    )
                return payload
            if command_type == "ConfirmStop":
                process = payload.get("process_disposition")
                stop_request = attempt.get("stop_request")
                if (
                    status != "stopping"
                    or operation_state != "stop_requested"
                    or not isinstance(stop_request, dict)
                    or payload.get("stop_record_id") != stop_request.get("stop_record_id")
                    or not isinstance(process, dict)
                    or not process.get("children_closed")
                    or not process.get("writers_closed")
                ):
                    return self._rejected(
                        command,
                        observed_version,
                        "operator_stop_not_confirmed",
                        "ConfirmStop requires its pending stop record and closed process writers and children.",
                    )
                return payload
        if command_type in _C2_RECOVERY_COMMAND_TYPES:
            if payload.get("attempt_id") != command.target_stream_id:
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_command_subject_identity",
                    "Recovery command must bind its payload Attempt and target stream.",
                )
            attempt = streams.get(command.target_stream_id)
            lease = streams.get(attempt.get("lease_id")) if isinstance(attempt, dict) else None
            if not isinstance(attempt, dict):
                return self._rejected(
                    command,
                    observed_version,
                    "attempt_missing",
                    "QuarantineOrphan requires a committed Attempt.",
                )
            if isinstance(lease, dict) and lease.get("status") == "active":
                return self._rejected(
                    command,
                    observed_version,
                    "live_attempt_owner",
                    "QuarantineOrphan cannot displace the Attempt's active Lease owner.",
                )
            if not payload.get("quarantine_actions") or not payload.get("consumer_restrictions"):
                return self._rejected(
                    command,
                    observed_version,
                    "quarantine_evidence_incomplete",
                    "QuarantineOrphan requires actions and consumer restrictions.",
                )
            return payload
        if command_type in _C2_DISPATCH_COMMAND_TYPES:
            if payload.get("dispatch_id") != command.target_stream_id:
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_command_subject_identity",
                    "C2 Dispatch payload identity must equal the authority-bound target stream.",
                )
            dispatch = streams.get(command.target_stream_id)
            attempt = streams.get(payload.get("attempt_id"))
            if (
                not isinstance(dispatch, dict)
                or dispatch.get("status") != "claimed"
                or not isinstance(attempt, dict)
                or attempt.get("dispatch_id") != command.target_stream_id
                or attempt.get("status") not in {"completed", "failed", "partial", "abandoned"}
                or payload.get("terminal_attempt_status") != attempt.get("status")
                or not payload.get("attempt_evidence_refs")
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "dispatch_fulfilment_precondition_failed",
                    "FulfilDispatch requires its exact claimed Dispatch and terminal producing Attempt evidence.",
                )
            return payload
        if command_type in _C2_REVIEW_COMMAND_TYPES:
            if payload.get("new_review_id") != command.target_stream_id:
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_command_subject_identity",
                    "Review payload identity must equal the authority-bound target stream.",
                )
            subject_ids = payload.get("subject_ids", [])
            subject_hashes = payload.get("subject_hashes", [])
            if command.target_stream_id in streams or not subject_ids or len(subject_ids) != len(subject_hashes):
                return self._rejected(
                    command,
                    observed_version,
                    "review_subject_binding_invalid",
                    "RequestReview requires an empty review stream and paired subject identities and hashes.",
                )
            for subject_id, subject_hash in zip(subject_ids, subject_hashes, strict=True):
                subject = streams.get(subject_id)
                if not isinstance(subject, dict) or subject_hash != sha256_hex(canonical_bytes(subject)):
                    return self._rejected(
                        command,
                        observed_version,
                        "stale_subject_hash",
                        "RequestReview must bind each exact current replayed subject hash.",
                    )
            if (
                not payload.get("review_questions")
                or not payload.get("required_evidence_refs")
                or not payload.get("required_lanes")
                or not payload.get("reviewer_capability")
                or not payload.get("allowed_verdicts")
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "review_requirements_incomplete",
                    "RequestReview requires questions, evidence, lanes, reviewer capability and verdicts.",
                )
            return payload
        if command_type not in _C2_TASK_COMMAND_TYPES:
            raise IntegrityError(f"unsupported C2 command type: {command_type}")
        if payload.get("task_id") != command.target_stream_id:
            return self._rejected(
                command,
                observed_version,
                "invalid_command_subject_identity",
                "C2 Task payload identity must equal the authority-bound target stream.",
            )
        task = streams.get(command.target_stream_id)
        if not isinstance(task, dict):
            return self._rejected(
                command,
                observed_version,
                "invalid_task_transition",
                "C2 Task transition requires a current Task.",
            )
        status = task.get("status")
        blockable = {
            "draft",
            "readiness_pending",
            "ready",
            "in_progress",
            "review_pending",
            "input_required",
            "paused",
        }
        if command_type == "BlockTask" and status not in blockable:
            return self._rejected(
                command,
                observed_version,
                "invalid_task_transition",
                "BlockTask requires a current blockable Task.",
            )
        if command_type == "RequestInput" and status not in {
            "draft",
            "readiness_pending",
            "ready",
            "in_progress",
            "review_pending",
            "blocked",
            "paused",
        }:
            return self._rejected(
                command,
                observed_version,
                "invalid_task_transition",
                "RequestInput requires an active Task.",
            )
        if command_type == "PauseTask":
            expected_prior = task.get("prior_active_status") if status in {"blocked", "input_required"} else status
            if (
                status
                not in {
                    "draft",
                    "readiness_pending",
                    "ready",
                    "in_progress",
                    "review_pending",
                    "blocked",
                    "input_required",
                }
                or payload.get("prior_active_status") != expected_prior
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_task_transition",
                    "PauseTask must bind the exact current active Task status.",
                )
        if command_type == "ResumeTask":
            if status not in {"blocked", "input_required", "paused"}:
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_task_transition",
                    "ResumeTask requires a suspended Task.",
                )
            prior = task.get("prior_active_status")
            if payload.get("suspended_status") != status or payload.get("prior_active_status") != prior:
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_task_resume_binding",
                    "ResumeTask must bind the exact suspended and prior active states.",
                )
            if not payload.get("resolution_evidence_refs") or not payload.get("authority_evidence_refs"):
                return self._rejected(
                    command,
                    observed_version,
                    "task_resume_evidence_required",
                    "ResumeTask requires resolution and authority evidence.",
                )
        if command_type in {"SubmitForReview", "CancelTask"}:
            attempts = [
                value
                for stream_id, value in streams.items()
                if isinstance(value, dict)
                and value.get("attempt_id") == stream_id
                and value.get("task_id") == command.target_stream_id
            ]
            terminal = {"completed", "failed", "partial", "abandoned", "superseded"}
            if not attempts or any(attempt.get("status") not in terminal for attempt in attempts):
                return self._rejected(
                    command,
                    observed_version,
                    "c2_dependency_not_terminal",
                    f"{command_type} requires terminal Attempt evidence.",
                )
            if command_type == "CancelTask":
                process = payload.get("process_disposition")
                attempt_ids = {str(attempt["attempt_id"]) for attempt in attempts}
                if (
                    status in {"accepted", "rejected", "partial", "cancelled", "superseded"}
                    or not isinstance(process, dict)
                    or not process.get("children_closed")
                    or not process.get("writers_closed")
                    or set(payload.get("active_attempt_dispositions", [])) != attempt_ids
                ):
                    return self._rejected(
                        command,
                        observed_version,
                        "task_cancellation_precondition_failed",
                        "CancelTask requires all exact Attempt dispositions and closed process writers and children.",
                    )
                return payload
            attempt = streams.get(payload.get("attempt_id"))
            outcome = attempt.get("outcome") if isinstance(attempt, dict) else None
            candidate_ids = outcome.get("candidate_artefact_ids") if isinstance(outcome, dict) else None
            if (
                status != "in_progress"
                or not isinstance(attempt, dict)
                or attempt.get("task_id") != command.target_stream_id
                or attempt.get("status") not in {"completed", "failed", "partial"}
                or payload.get("attempt_outcome") != attempt.get("status")
                or payload.get("candidate_artefact_ids") != (candidate_ids or [])
                or len(payload.get("candidate_artefact_hashes", [])) != len(payload.get("candidate_artefact_ids", []))
                or not payload.get("requested_review_ids")
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "task_review_precondition_failed",
                    "SubmitForReview must bind the exact terminal Attempt outcome, candidate IDs and requested reviews.",
                )
            return payload
        return payload

    def _prepare_c3_command(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
    ) -> dict[str, Any] | Receipt:
        """Validate C3 Task, Review, Decision, rule, and correction transitions."""
        payload = command.envelope["payload"]
        command_type = command.envelope["command_type"]

        def rejected(code: str, explanation: str) -> Receipt:
            return self._rejected(command, observed_version, code, explanation)

        if command.envelope.get("project_id") != self.ledger.project_id:
            return rejected(
                "invalid_command_project",
                "C3 command project must match the control-store project.",
            )
        streams = self._c1_streams(snapshot)

        if command_type in _C3_TASK_COMMAND_TYPES:
            if payload.get("task_id") != command.target_stream_id:
                return rejected(
                    "invalid_command_subject_identity",
                    "C3 Task payload identity must equal the authority-bound target stream.",
                )
            task = streams.get(command.target_stream_id)
            if not isinstance(task, dict):
                return rejected("invalid_task_transition", "C3 Task transition requires a current Task.")
            status = task.get("status")
            revision = int(task.get("current_revision", 1))
            if command_type == "AcceptTask":
                review_ids = tuple(payload.get("satisfied_review_ids", ()))
                criteria = tuple(task.get("definition", {}).get("acceptance_criteria", ()))
                selected = set(payload.get("selected_artefact_ids", ()))
                submitted = set(task.get("review_submission", {}).get("candidate_artefact_ids", ()))
                task_hash = sha256_hex(canonical_bytes(task))

                def binds_task(review_id: str) -> bool:
                    review = streams.get(review_id)
                    if not isinstance(review, dict) or review.get("status") != "satisfied":
                        return False
                    request = review.get("request", {})
                    return (command.target_stream_id, task_hash) in tuple(
                        zip(request.get("subject_ids", ()), request.get("subject_hashes", ()), strict=False)
                    )

                if (
                    status != "review_pending"
                    or payload.get("task_revision") != revision
                    or not review_ids
                    or any(not binds_task(review_id) for review_id in review_ids)
                    or set(payload.get("satisfied_acceptance_criteria", ())) != set(criteria)
                    or not selected.issubset(submitted)
                ):
                    return rejected(
                        "task_acceptance_precondition_failed",
                        "AcceptTask requires the current review-pending revision and an explicit satisfied review and criterion set.",
                    )
                return deepcopy(payload)
            if command_type == "RejectTask":
                review = streams.get(payload.get("review_verdict_id"))
                request = review.get("request", {}) if isinstance(review, dict) else {}
                reviewed_subject = (
                    command.target_stream_id,
                    payload.get("verdict_subject_sha256"),
                )
                if (
                    status != "review_pending"
                    or payload.get("task_revision") != revision
                    or not isinstance(review, dict)
                    or review.get("status") != "verdict_recorded"
                    or review.get("verdict", {}).get("verdict") not in {"reject", "changes_requested"}
                    or payload.get("verdict_subject_sha256") != review.get("subject_sha256")
                    or reviewed_subject
                    not in tuple(zip(request.get("subject_ids", ()), request.get("subject_hashes", ()), strict=False))
                ):
                    return rejected(
                        "task_rejection_precondition_failed",
                        "RejectTask requires the current review-pending revision and exact verdict evidence.",
                    )
                return deepcopy(payload)
            if command_type == "ClosePartial":
                if (
                    status in _TASK_TERMINAL_STATES
                    or not payload.get("unmet_obligations")
                    or not payload.get("claim_restrictions")
                ):
                    return rejected(
                        "task_partial_precondition_failed",
                        "ClosePartial requires a nonterminal Task, unmet obligations, and explicit claim restrictions.",
                    )
                return deepcopy(payload)

            prior_status = payload.get("prior_terminal_status")
            terminal_event_type = {
                "partial": "PartialOutcomeRecorded",
                "rejected": "TaskRejected",
                "cancelled": "TaskCancelled",
            }.get(str(prior_status))
            terminal_event = next(
                (
                    event
                    for event in reversed(snapshot.events)
                    if event.get("stream_id") == command.target_stream_id
                    and event.get("event_type") == terminal_event_type
                ),
                None,
            )
            terminal_ref = payload.get("preserved_terminal_record_ref")
            if (
                terminal_event_type is None
                or status != prior_status
                or payload.get("new_execution_epoch") != int(task.get("execution_epoch", 1)) + 1
                or not payload.get("authority_evidence_refs")
                or not isinstance(terminal_event, dict)
                or not isinstance(terminal_ref, dict)
                or terminal_ref.get("record_id") != terminal_event.get("event_id")
                or terminal_ref.get("content_sha256") != terminal_event.get("event_hash")
            ):
                return rejected(
                    "task_reopen_precondition_failed",
                    "ReopenTask requires the exact terminal event, a new execution epoch, and explicit authority evidence.",
                )
            return deepcopy(payload)

        if command_type in _C3_REVIEW_COMMAND_TYPES:
            if payload.get("review_id") != command.target_stream_id:
                return rejected(
                    "invalid_command_subject_identity",
                    "C3 Review payload identity must equal the authority-bound target stream.",
                )
            review = streams.get(command.target_stream_id)
            if not isinstance(review, dict):
                return rejected("invalid_review_transition", "C3 Review transition requires a current Review.")
            status = review.get("status")
            request = review.get("request")
            if not isinstance(request, dict):
                return rejected("invalid_review_transition", "C3 Review transition requires its immutable request.")
            subject_hashes = tuple(request.get("subject_hashes", ()))
            if command_type == "AssignReview":
                if (
                    status != "requested"
                    or command.actor_id != review.get("requester_actor_id")
                    or payload.get("reviewer_actor_id") == review.get("requester_actor_id")
                    or not payload.get("independence_evidence_refs")
                ):
                    return rejected(
                        "review_assignment_precondition_failed",
                        "AssignReview requires an eligible reviewer distinct from the requester and independence evidence.",
                    )
                return deepcopy(payload)
            if command_type == "StartReview":
                assignment = review.get("assignment")
                if (
                    status != "assigned"
                    or not isinstance(assignment, dict)
                    or command.actor_id != assignment.get("reviewer_actor_id")
                    or payload.get("unchanged_subject_sha256") not in subject_hashes
                ):
                    return rejected(
                        "review_start_subject_mismatch",
                        "StartReview requires the assigned reviewer and one exact unchanged requested subject hash.",
                    )
                return deepcopy(payload)
            if command_type == "RecordReviewVerdict":
                assignment = review.get("assignment")
                started = review.get("start")
                if (
                    status != "in_review"
                    or not isinstance(assignment, dict)
                    or not isinstance(started, dict)
                    or payload.get("reviewer_actor_id") != command.actor_id
                    or payload.get("reviewer_actor_id") != assignment.get("reviewer_actor_id")
                    or payload.get("unchanged_subject_sha256") != started.get("unchanged_subject_sha256")
                    or payload.get("computed_independence_grade") != assignment.get("computed_independence_grade")
                    or not payload.get("required_evidence_refs")
                    or not payload.get("trace_visibility_evidence_refs")
                ):
                    return rejected(
                        "review_verdict_precondition_failed",
                        "RecordReviewVerdict requires the assigned reviewer, exact started subject, independence grade, and evidence.",
                    )
                return deepcopy(payload)
            if command_type == "RequestReviewChanges":
                if (
                    status != "verdict_recorded"
                    or command.actor_id != review.get("requester_actor_id")
                    or not payload.get("policy_evaluation_refs")
                    or not payload.get("conditions")
                ):
                    return rejected(
                        "review_changes_precondition_failed",
                        "RequestReviewChanges requires a recorded verdict, policy evaluation, and conditions.",
                    )
                return deepcopy(payload)
            if command_type == "SatisfyReview":
                assignment = review.get("assignment", {})
                if (
                    status not in {"verdict_recorded", "changes_requested"}
                    or command.actor_id != review.get("requester_actor_id")
                    or command.actor_id == assignment.get("reviewer_actor_id")
                    or payload.get("prior_review_state") != status
                    or not payload.get("policy_evaluation_refs")
                    or (status == "changes_requested" and not payload.get("unchanged_subject_sha256"))
                ):
                    return rejected(
                        "review_satisfaction_precondition_failed",
                        "SatisfyReview requires the exact prior review state and policy evidence; changed subjects require a bound hash.",
                    )
                return deepcopy(payload)
            if command_type == "WithdrawReview":
                if status in {"satisfied", "withdrawn", "superseded"} or command.actor_id != review.get(
                    "requester_actor_id"
                ):
                    return rejected("review_terminal", "A terminal Review cannot be withdrawn.")
                return deepcopy(payload)
            replacement = streams.get(payload.get("replacement_review_id"))
            expected_hash = review.get("subject_sha256") or (subject_hashes[0] if len(subject_hashes) == 1 else None)
            if (
                status in {"satisfied", "withdrawn", "superseded"}
                or command.actor_id != review.get("requester_actor_id")
                or not isinstance(replacement, dict)
                or replacement.get("status") in {"satisfied", "withdrawn", "superseded"}
                or payload.get("unchanged_subject_sha256") != expected_hash
            ):
                return rejected(
                    "review_supersession_precondition_failed",
                    "SupersedeReview requires a live replacement Review bound to the same exact subject hash.",
                )
            return deepcopy(payload)

        if command_type == "ProposeDecision":
            if (
                payload.get("new_decision_id") != command.target_stream_id
                or command.target_stream_id in streams
                or payload.get("decision_revision") != 1
                or not payload.get("options")
                or payload.get("recommendation") not in payload.get("options", ())
                or not payload.get("governing_evidence_refs")
            ):
                return rejected(
                    "decision_proposal_precondition_failed",
                    "ProposeDecision requires an empty stream, revision 1, a listed recommendation, and governing evidence.",
                )
            return deepcopy(payload)
        if command_type == "RecordRuleEvaluation":
            if (
                payload.get("new_rule_evaluation_id") != command.target_stream_id
                or command.target_stream_id in streams
                or not payload.get("input_ids")
                or len(payload.get("input_ids", ())) != len(payload.get("input_hashes", ()))
            ):
                return rejected(
                    "rule_evaluation_precondition_failed",
                    "RecordRuleEvaluation requires an empty bound stream and paired exact inputs and hashes.",
                )
            return deepcopy(payload)
        if command_type == "RecordCorrection":
            correction_id = payload.get("erroneous_record_id")
            if (
                correction_id != command.target_stream_id
                or correction_id not in streams
                or not payload.get("corrected_evidence_refs")
                or not payload.get("affected_projections")
                or any(
                    event.get("event_type") == "RecordCorrected"
                    and isinstance(event.get("payload"), dict)
                    and event["payload"].get("governance_correction_index")
                    == payload.get("governance_correction_index")
                    for event in snapshot.events
                )
            ):
                return rejected(
                    "correction_precondition_failed",
                    "RecordCorrection requires an existing erroneous record, evidence, affected projections, and a unique correction index.",
                )
            return deepcopy(payload)

        decision = streams.get(command.target_stream_id)
        if not isinstance(decision, dict) or payload.get("decision_id") != command.target_stream_id:
            return rejected(
                "invalid_decision_transition", "Decision command requires its exact current Decision stream."
            )
        status = decision.get("status")
        revision = int(decision.get("decision_revision", 1))
        if command_type == "RequestDecisionReview":
            if (
                status != "proposed"
                or command.actor_id != decision.get("proposer_actor_id")
                or payload.get("decision_revision") != revision
                or not payload.get("review_requirements")
                or not payload.get("governing_evidence_refs")
            ):
                return rejected(
                    "decision_review_precondition_failed",
                    "RequestDecisionReview requires the current proposal and explicit review requirements and evidence.",
                )
            return deepcopy(payload)
        if command_type == "RejectDecision":
            if (
                status not in {"proposed", "under_review"}
                or command.actor_id == decision.get("proposer_actor_id")
                or payload.get("decision_revision") != revision
                or payload.get("deciding_actor_id") != command.actor_id
                or payload.get("decision_authority_grant_id") != command.envelope.get("authority_grant_id")
            ):
                return rejected(
                    "decision_rejection_precondition_failed",
                    "RejectDecision requires an unresolved current revision and exact deciding authority.",
                )
            return deepcopy(payload)
        if command_type == "ExpireDecision":
            observed_at = datetime.fromisoformat(str(payload.get("observed_at", "")).replace("Z", "+00:00"))
            expires_at = datetime.fromisoformat(str(decision.get("expires_at", "")).replace("Z", "+00:00"))
            if (
                status not in {"proposed", "under_review"}
                or payload.get("decision_revision") != revision
                or observed_at < expires_at
            ):
                return rejected(
                    "decision_expiry_precondition_failed",
                    "ExpireDecision requires an unresolved current revision observed at or after its expiry.",
                )
            return deepcopy(payload)
        if command_type == "SupersedeDecision":
            replacement = streams.get(payload.get("replacement_decision_id"))
            if (
                status not in {"proposed", "under_review"}
                or command.actor_id == decision.get("proposer_actor_id")
                or payload.get("decision_revision") != revision
                or not isinstance(replacement, dict)
                or replacement.get("decision_kind") != decision.get("decision_kind")
            ):
                return rejected(
                    "decision_supersession_precondition_failed",
                    "SupersedeDecision requires an unresolved source and a compatible replacement Decision.",
                )
            return deepcopy(payload)
        if command_type == "AmendDecision":
            if (
                status != "resolved"
                or command.actor_id == decision.get("proposer_actor_id")
                or payload.get("decision_revision") != revision + 1
                or not payload.get("changed_fields")
                or not payload.get("governing_evidence_refs")
            ):
                return rejected(
                    "decision_amendment_precondition_failed",
                    "AmendDecision requires a resolved Decision, the next revision, changed fields, and governing evidence.",
                )
            return deepcopy(payload)
        raise IntegrityError(f"unsupported C3 command type: {command_type}")

    def _prepare_resource_grant_materialization(self, command: Command) -> dict[str, Any]:
        """Validate the exact authority preimage without writing before append."""
        payload = command.envelope["payload"]
        try:
            resource_grant_id = payload["resource_id"]
            request = payload["resource_request"]
            expected_ref = derive_resource_grant_authority_preimage_ref(
                project_id=self.ledger.project_id,
                resource_grant_id=resource_grant_id,
                resource_request=request,
                trusted_authority=self._current_trusted_runtime_authority(),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError("resource grant authority preimage is invalid") from exc
        if request.get("projection_evidence_refs") != [expected_ref]:
            raise IntegrityError("resource grant authority preimage is invalid")
        if self.objects.revision_exists("resource_grant", resource_grant_id, 1):
            raise ConflictError("resource grant revision conflicts")
        return {"authority_preimage_ref": expected_ref}

    def _prepare_backup_command(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
    ) -> dict[str, Any] | Receipt:
        """Validate and stage one exact backup without publishing it pre-event."""
        payload = command.envelope["payload"]
        if (
            command.envelope.get("project_id") != self.ledger.project_id
            or command.target_stream_id != self.ledger.project_id
            or payload.get("project_id") != self.ledger.project_id
        ):
            return self._rejected(
                command,
                observed_version,
                "invalid_backup_project",
                "CreateBackup must target the selected control-store project.",
            )
        if (
            payload.get("canonical_tail_position") != snapshot.global_position
            or payload.get("canonical_tail_sha256") != snapshot.event_hash
            or payload.get("replay_end_position") != snapshot.global_position
        ):
            return self._rejected(
                command,
                observed_version,
                "backup_source_drift",
                "CreateBackup must bind the exact locked source tail.",
            )
        snapshot_id = payload.get("snapshot_id")
        if any(
            event.get("event_type") == "BackupCreated"
            and event.get("stream_id") == self.ledger.project_id
            and isinstance(event.get("payload"), dict)
            and event["payload"].get("snapshot_id") == snapshot_id
            for event in snapshot.events
        ):
            return self._rejected(
                command,
                observed_version,
                "backup_snapshot_identity_conflict",
                "CreateBackup snapshot identity is already committed.",
            )
        materializer = self.backup_materializer
        if materializer is None:
            raise ArsError("CreateBackup requires the governed backup materializer")
        prepared = materializer.prepare(command, snapshot)
        if prepared.event_payload != payload:
            raise IntegrityError("backup preparation payload differs from the accepted command")
        return deepcopy(prepared.event_payload)

    def _ensure_backup_materialized(self, command: Command) -> BackupReceipt:
        """Publish or repair a backup only from one exact committed event."""
        materializer = self.backup_materializer
        if materializer is None:
            raise ArsError("CreateBackup requires the governed backup materializer")
        events = [
            event
            for event in self.ledger.snapshot().events
            if event.get("command_id") == command.command_id
            and event.get("command_type") == "CreateBackup"
            and event.get("event_type") == "BackupCreated"
            and event.get("stream_id") == command.target_stream_id
            and event.get("command_payload_hash") == command.payload_hash
        ]
        if len(events) != 1 or events[0].get("payload") != command.envelope["payload"]:
            raise IntegrityError("backup materialization requires one exact committed event")
        return materializer.materialize(command, events[0])

    def _prepare_artefact_authority_command(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
    ) -> dict[str, Any] | Receipt:
        """Validate the accepted 06i transitions before any durable write."""
        payload = command.envelope["payload"]
        command_type = command.envelope["command_type"]

        def rejected(code: str, explanation: str) -> Receipt:
            return self._rejected(command, observed_version, code, explanation)

        if command.envelope.get("project_id") != self.ledger.project_id:
            return rejected(
                "invalid_artefact_project",
                "Artefact authority commands must target the selected control-store project.",
            )
        artefact_events = [
            event
            for event in snapshot.events
            if event.get("stream_id") == command.target_stream_id
            and event.get("event_type") in {"ArtefactRegistered", "ScientificReviewRecorded", "ArtefactUseAuthoritySet"}
        ]
        registered = next(
            (event for event in artefact_events if event.get("event_type") == "ArtefactRegistered"),
            None,
        )

        if command_type == "RegisterArtefact":
            manifest = payload.get("manifest")
            if (
                payload.get("new_artefact_id") != command.target_stream_id
                or not isinstance(manifest, dict)
                or manifest.get("artefact_id") != command.target_stream_id
            ):
                return rejected(
                    "invalid_artefact_identity",
                    "RegisterArtefact must bind one exact new artefact identity.",
                )
            authority = manifest.get("authority")
            if not isinstance(authority, dict) or authority.get("use_authority") != "candidate":
                return rejected(
                    "artefact_initial_authority_invalid",
                    "RegisterArtefact always starts at candidate authority.",
                )
            if authority.get("regenerability") == "regenerable_verified":
                return rejected(
                    "artefact_regenerability_evidence_unavailable",
                    "RegisterArtefact cannot claim regenerable verification before its required canary evidence is governed.",
                )
            if (
                observed_version != 0
                or registered is not None
                or self.objects.revision_exists("artefact", command.target_stream_id, 1)
            ):
                return rejected(
                    "artefact_already_registered",
                    "RegisterArtefact requires an empty artefact stream and object revision.",
                )
            return deepcopy(payload)

        if command_type in {"RecordScientificReview", "SetArtefactUseAuthority"}:
            if payload.get("artefact_id") != command.target_stream_id or registered is None:
                return rejected(
                    "artefact_not_registered",
                    "Artefact authority transitions require the registered artefact stream.",
                )
            registered_payload = registered.get("payload")
            manifest = registered_payload.get("manifest") if isinstance(registered_payload, dict) else None
            if not isinstance(manifest, dict) or payload.get("subject_sha256") != manifest.get("content_sha256"):
                return rejected(
                    "artefact_subject_hash_mismatch",
                    "Artefact authority transitions must bind the registered content hash.",
                )
            current_use_authority = "candidate"
            for event in artefact_events:
                if event.get("event_type") == "ArtefactUseAuthoritySet" and isinstance(event.get("payload"), dict):
                    current_use_authority = str(event["payload"].get("use_authority", ""))
            if current_use_authority in {"rejected", "superseded"}:
                return rejected(
                    "artefact_authority_terminal",
                    "Rejected or superseded artefacts cannot receive further authority transitions.",
                )
            if command_type == "RecordScientificReview":
                review_id = payload.get("review_id")
                if any(
                    event.get("event_type") == "ScientificReviewRecorded"
                    and isinstance(event.get("payload"), dict)
                    and event["payload"].get("review_id") == review_id
                    for event in snapshot.events
                ):
                    return rejected(
                        "scientific_review_identity_conflict",
                        "Scientific review identity is already committed.",
                    )
                return deepcopy(payload)
            if payload.get("use_authority") == "candidate":
                return rejected(
                    "invalid_artefact_authority_transition",
                    "Candidate is established only by RegisterArtefact.",
                )
            if payload.get("use_authority") == "accepted_for_scope":
                evidence_error = self._validate_governing_review_evidence(
                    command,
                    artefact_events,
                    manifest,
                )
                if evidence_error is not None:
                    return rejected(*evidence_error)
            return deepcopy(payload)

        if command_type == "ResolveDecision":
            if (
                payload.get("decision_id") != command.target_stream_id
                or payload.get("deciding_actor_id") != command.actor_id
                or payload.get("decision_authority_grant_id") != command.envelope.get("authority_grant_id")
            ):
                return rejected(
                    "decision_authority_binding_mismatch",
                    "ResolveDecision must bind its stream, deciding actor, and authority grant.",
                )
            if any(
                event.get("event_type") == "DecisionResolved"
                for event in snapshot.events
                if event.get("stream_id") == command.target_stream_id
            ):
                return rejected("decision_already_resolved", "Decision is already resolved.")
            decision = self._c1_streams(snapshot).get(command.target_stream_id)
            if isinstance(decision, dict):
                review_ids = tuple(payload.get("considered_review_ids", ()))
                decision_hash = sha256_hex(canonical_bytes(decision))
                reviewed = tuple(self._c1_streams(snapshot).get(review_id) for review_id in review_ids)
                if (
                    decision.get("status") != "under_review"
                    or command.actor_id == decision.get("proposer_actor_id")
                    or payload.get("decision_revision") != decision.get("decision_revision")
                    or payload.get("selected_option") not in decision.get("options", ())
                    or not review_ids
                    or any(
                        not isinstance(review, dict)
                        or review.get("status") != "satisfied"
                        or (
                            command.target_stream_id,
                            decision_hash,
                        )
                        not in tuple(
                            zip(
                                review.get("request", {}).get("subject_ids", ()),
                                review.get("request", {}).get("subject_hashes", ()),
                                strict=False,
                            )
                        )
                        or review.get("assignment", {}).get("reviewer_actor_id")
                        in {decision.get("proposer_actor_id"), command.actor_id}
                        for review in reviewed
                    )
                ):
                    return rejected(
                        "decision_resolution_precondition_failed",
                        "ResolveDecision requires the current reviewed revision, a listed option, and satisfied exact-subject reviews.",
                    )
            return deepcopy(payload)

        raise IntegrityError(f"unsupported artefact authority command type: {command_type}")

    def _validate_governing_review_evidence(
        self,
        command: Command,
        artefact_events: list[dict[str, Any]],
        manifest: dict[str, Any],
    ) -> tuple[str, str] | None:
        """Resolve the accepted predicate's complete independent review set."""
        resolver = self.governing_evidence_resolver
        if resolver is None or not callable(getattr(resolver, "resolve", None)):
            return (
                "governing_review_resolver_unavailable",
                "Accepted artefact use requires the production governing-review resolver.",
            )
        from research_system.artefacts.authority import ArtefactAuthorityContractLoader
        from research_system.artefacts.runtime import ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT
        from research_system.artefacts.use_resolver import predicate_reference

        contract = ArtefactAuthorityContractLoader(ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT).load()
        supplied_reference = command.envelope["payload"].get("consumer_predicate")
        consumer_kind: str | None = None
        for candidate_kind, predicate in contract.predicates_by_kind.items():
            expected = predicate_reference(
                str(predicate["predicate_id"]),
                str(predicate["predicate_version"]),
                contract.predicate_sha256_by_kind[candidate_kind],
            )
            if supplied_reference == expected:
                consumer_kind = candidate_kind
                break
        if consumer_kind is None:
            return (
                "artefact_consumer_predicate_unaccepted",
                "Accepted artefact use must bind one exact accepted consumer predicate.",
            )
        rule = contract.review_rules_by_kind[consumer_kind]
        minimum = rule.get("minimum_approved_reviews")
        minimum_grade = rule.get("minimum_independence_grade")
        if not isinstance(minimum, int) or minimum < 1 or minimum_grade not in _ARTEFACT_REVIEW_INDEPENDENCE_ORDER:
            raise IntegrityError("accepted governing-review rule is invalid")
        submitted_at = datetime.fromisoformat(str(command.envelope["submitted_at"]).replace("Z", "+00:00"))
        use_refs = command.envelope["payload"].get("evidence_refs")
        if not isinstance(use_refs, list):
            return (
                "governing_scientific_review_missing",
                "Accepted artefact use must bind its complete governing review evidence.",
            )
        approved = 0
        for event in artefact_events:
            review = event.get("payload")
            if (
                event.get("event_type") != "ScientificReviewRecorded"
                or not isinstance(review, dict)
                or review.get("scientific_review") != "approved"
                or review.get("subject_sha256") != command.envelope["payload"].get("subject_sha256")
            ):
                continue
            review_id = review.get("review_id")
            review_refs = review.get("evidence_refs")
            reviewer_actor_id = event.get("actor_id")
            if (
                not isinstance(review_id, str)
                or not isinstance(review_refs, list)
                or not review_refs
                or review_id not in use_refs
                or any(reference not in use_refs for reference in review_refs)
            ):
                continue
            matched = False
            for reference in review_refs:
                if not isinstance(reference, str):
                    continue
                try:
                    resolution = resolver.resolve(
                        reference,
                        project_id=self.ledger.project_id,
                        evaluation_time=submitted_at,
                    )
                except Exception:  # noqa: BLE001 - invalid authority is one stable rejection
                    continue
                record = resolution.record
                if (
                    resolution.reference_id != reference
                    or not isinstance(record, Mapping)
                    or record.get("schema_id") != "ars://evidence/governing-scientific-review"
                    or record.get("schema_version") != "1.0.0"
                    or record.get("project_id") != self.ledger.project_id
                    or record.get("review_id") != review_id
                    or record.get("subject_sha256") != review.get("subject_sha256")
                    or record.get("reviewer_actor_id") != reviewer_actor_id
                    or record.get("status") != "active"
                    or (rule.get("require_eligible") is True and record.get("eligible") is not True)
                    or (rule.get("prohibit_related_reviewer") is True and record.get("related") is not False)
                    or (
                        rule.get("prohibit_producer_reviewer") is True
                        and reviewer_actor_id == manifest.get("producer_actor_id")
                    )
                    or _ARTEFACT_REVIEW_INDEPENDENCE_ORDER.get(str(record.get("independence_grade")), -1)
                    < _ARTEFACT_REVIEW_INDEPENDENCE_ORDER[str(minimum_grade)]
                    or sha256_hex(canonical_bytes(record)) != resolution.canonical_sha256
                ):
                    continue
                matched = True
                break
            if matched:
                approved += 1
        if approved < minimum:
            return (
                "governing_scientific_review_missing",
                "Accepted artefact use requires the complete independently resolved governing review set.",
            )
        return None

    def _ensure_artefact_materialized(self, command: Command) -> dict[str, Any]:
        """Materialize revision 1 only from the exact committed registration."""
        events = [
            event
            for event in self.ledger.snapshot().events
            if event.get("command_id") == command.command_id
            and event.get("command_type") == "RegisterArtefact"
            and event.get("event_type") == "ArtefactRegistered"
            and event.get("stream_id") == command.target_stream_id
            and event.get("command_payload_hash") == command.payload_hash
        ]
        if len(events) != 1 or events[0].get("payload") != command.envelope["payload"]:
            raise IntegrityError("artefact materialization requires one exact committed registration")
        manifest = deepcopy(command.envelope["payload"]["manifest"])
        if self.objects.revision_exists("artefact", command.target_stream_id, 1):
            existing = self.objects.read("artefact", command.target_stream_id, 1)
            if existing != manifest:
                raise ConflictError("artefact revision conflicts")
            return existing
        self.objects.write("artefact", command.target_stream_id, 1, manifest)
        persisted = self.objects.read("artefact", command.target_stream_id, 1)
        if persisted != manifest:
            raise ConflictError("artefact revision conflicts")
        return persisted

    def _prepare_context_packet_command(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
    ) -> dict[str, Any] | Receipt:
        """Validate the W3 lifecycle and exact packet identity before append."""
        payload = command.envelope["payload"]
        command_type = command.envelope["command_type"]

        def rejected(code: str, explanation: str) -> Receipt:
            return self._rejected(command, observed_version, code, explanation)

        if (
            command.envelope.get("project_id") != self.ledger.project_id
            or payload.get("context_id") != command.target_stream_id
        ):
            return rejected(
                "invalid_context_identity",
                "Context lifecycle commands must bind the selected project and context stream.",
            )
        events = sorted(
            (
                event
                for event in snapshot.events
                if event.get("stream_id") == command.target_stream_id
                and event.get("event_type")
                in {
                    "ContextPacketRequested",
                    "ContextCompilationStarted",
                    "ContextPacketCompiled",
                    "ContextPacketValidated",
                    "ContextPacketIssued",
                    "ContextPacketDelivered",
                    "ContextPacketFailed",
                    "ContextPacketExpired",
                    "ContextPacketSuperseded",
                }
            ),
            key=lambda event: int(event.get("stream_version", 0)),
        )
        states = {
            "ContextPacketRequested": "requested",
            "ContextCompilationStarted": "compiling",
            "ContextPacketCompiled": "compiled",
            "ContextPacketValidated": "validated",
            "ContextPacketIssued": "issued",
            "ContextPacketDelivered": "delivered",
            "ContextPacketFailed": "failed",
            "ContextPacketExpired": "expired",
            "ContextPacketSuperseded": "superseded",
        }
        current = states.get(str(events[-1].get("event_type"))) if events else None
        allowed = {
            "RequestContextPacket": {None},
            "BeginContextCompilation": {"requested"},
            "CompleteContextCompilation": {"compiling"},
            "ValidateContextPacket": {"compiled"},
            "IssueContextPacket": {"validated"},
            "RecordContextDelivery": {"issued"},
            "FailContextPacket": {"requested", "compiling", "compiled"},
            "ExpireContextPacket": {"issued", "delivered"},
            "SupersedeContextPacket": {"issued", "delivered"},
        }
        if current not in allowed[command_type]:
            return rejected(
                "invalid_context_transition",
                f"{command_type} is not valid from context state {current!r}.",
            )
        if command_type == "RequestContextPacket":
            if payload.get("project_id") != self.ledger.project_id:
                return rejected("invalid_context_project", "Context request project does not match Control.")
            return deepcopy(payload)

        request_payload = events[0].get("payload") if events else None
        supplied_revision = (
            payload.get("revision") if command_type == "BeginContextCompilation" else payload.get("packet_revision")
        )
        revision_mismatch = (
            isinstance(request_payload, dict)
            and supplied_revision is not None
            and supplied_revision != request_payload.get("revision")
        )
        if not isinstance(request_payload, dict) or revision_mismatch:
            return rejected(
                "context_revision_mismatch",
                "Context lifecycle commands must retain the requested revision.",
            )
        compiled = next(
            (event.get("payload") for event in events if event.get("event_type") == "ContextPacketCompiled"),
            None,
        )
        if command_type in {"ValidateContextPacket", "IssueContextPacket", "RecordContextDelivery"}:
            if not isinstance(compiled, dict):
                return rejected("context_compilation_missing", "Context packet compilation is missing.")
            for field in ("packet_revision", "packet_sha256"):
                if payload.get(field) != compiled.get(field):
                    return rejected(
                        "context_packet_identity_mismatch",
                        "Context lifecycle command does not bind the compiled packet identity.",
                    )
        return deepcopy(payload)

    def _ensure_resource_grant_materialized(self, command: Command) -> dict[str, Any]:
        """Materialize revision 1 only from the exact committed request event."""
        events = [
            event
            for event in self.ledger.snapshot().events
            if event.get("command_id") == command.command_id
            and event.get("command_type") == "RequestResourceGrant"
            and event.get("stream_id") == command.target_stream_id
            and event.get("command_payload_hash") == command.payload_hash
        ]
        if len(events) != 1 or events[0].get("payload") != command.envelope["payload"]:
            raise IntegrityError("resource grant materialization requires one exact committed request")
        try:
            record = derive_resource_grant_v1_1_record(
                committed_event=events[0],
                project_id=self.ledger.project_id,
                trusted_authority=self._current_trusted_runtime_authority(),
            )
            self._validate_resource_grant_record(record)
        except (KeyError, TypeError, ValueError) as exc:
            raise IntegrityError("resource grant materialization is invalid") from exc
        resource_grant_id = record["resource_grant_id"]
        if self.objects.revision_exists("resource_grant", resource_grant_id, 1):
            existing = self._read_resource_grant_record(resource_grant_id)
            if existing != record:
                raise ConflictError("resource grant revision conflicts")
            return record
        self.objects.write("resource_grant", resource_grant_id, 1, record)
        persisted = self._read_resource_grant_record(resource_grant_id)
        if persisted != record:
            raise ConflictError("resource grant revision conflicts")
        return record

    def _read_resource_grant_record(self, resource_grant_id: str) -> dict[str, Any]:
        record = self.objects.read("resource_grant", resource_grant_id, 1)
        self._validate_resource_grant_record(record)
        return record

    def _validate_resource_grant_record(self, record: object) -> None:
        if not isinstance(record, dict):
            raise IntegrityError("resource grant revision must be an object")
        self.schemas.validate(
            RESOURCE_GRANT_V1_1_SCHEMA_ID,
            record,
            schema_version=RESOURCE_GRANT_V1_1_SCHEMA_VERSION,
            expected_sha256=RESOURCE_GRANT_V1_1_SCHEMA_SHA256,
        )
        content_hash = record.get("content_hash")
        immutable_content = {key: value for key, value in record.items() if key != "content_hash"}
        if content_hash != sha256_hex(canonical_bytes(immutable_content)):
            raise IntegrityError("resource grant content hash is invalid")

    def _stored_materialized_resource_grant(
        self,
        *,
        resource_grant_id: str,
        resource: object,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Return one source/projection-bound persisted grant without runtime identity.

        This validates the immutable grant record against its committed request
        event and current resource projection.  It deliberately does not read
        the live runtime-authority provider, so terminal cleanup remains
        possible after that provider has drifted.
        """
        if not isinstance(resource, dict) or resource.get("status") != "active":
            return None, "resource_request_missing"
        if not self.objects.revision_exists("resource_grant", resource_grant_id, 1):
            return None, "resource_grant_unmaterialized"
        try:
            stored_grant = self._read_resource_grant_record(resource_grant_id)
            source_events = [
                event
                for event in self.ledger.snapshot().events
                if event.get("event_id") == stored_grant["source_event_id"]
                and event.get("event_hash") == stored_grant["source_event_hash"]
                and event.get("command_id") == stored_grant["source_command_id"]
                and event.get("command_payload_hash") == stored_grant["source_command_payload_hash"]
                and event.get("stream_id") == resource_grant_id
            ]
            if len(source_events) != 1:
                raise IntegrityError("resource grant source event is not exact")
            source_event = source_events[0]
            source_payload = source_event.get("payload")
            if source_event.get("event_type") != "ResourceGrantRequested" or not isinstance(source_payload, dict):
                raise IntegrityError("resource grant source event is invalid")
            source_request = source_payload.get("resource_request")
            if not isinstance(source_request, dict):
                raise IntegrityError("resource grant source request is invalid")
            canonical_request = json.loads(canonical_bytes(source_request).decode("utf-8"))
            if not isinstance(canonical_request, dict):
                raise IntegrityError("resource grant source request is invalid")
            source_request_sha256 = sha256_hex(canonical_bytes(canonical_request))
            projected_request = resource.get("request")
            if not isinstance(projected_request, dict):
                raise IntegrityError("resource grant projection request is invalid")
            projected_request_sha256 = sha256_hex(canonical_bytes(projected_request))
            expected_grant_ref = {
                "kind": "resource_grant",
                "id": resource_grant_id,
                "revision": 1,
                "schema_version": RESOURCE_GRANT_V1_1_SCHEMA_VERSION,
            }
            source_preimage_refs = canonical_request.get("projection_evidence_refs")
            source_matches = (
                source_payload.get("resource_id") == resource_grant_id
                and stored_grant.get("resource_grant_id") == resource_grant_id
                and stored_grant.get("resource_request_id") == canonical_request.get("resource_request_id")
                and stored_grant.get("task_id") == canonical_request.get("task_id")
                and stored_grant.get("dispatch_id") == canonical_request.get("dispatch_id")
                and stored_grant.get("attempt_id") == canonical_request.get("attempt_id")
                and stored_grant.get("requesting_actor_id") == canonical_request.get("requesting_actor_id")
                and stored_grant.get("requesting_authority_grant_id")
                == canonical_request.get("requesting_authority_grant_id")
                and stored_grant.get("expected_control_store_position")
                == canonical_request.get("expected_control_store_position")
                and stored_grant.get("resource_request_sha256") == source_request_sha256
                and stored_grant.get("granted_claims") == canonical_request
                and stored_grant.get("granted_claims_sha256") == source_request_sha256
                and isinstance(source_preimage_refs, list)
                and len(source_preimage_refs) == 1
                and stored_grant.get("authority_preimage_ref") == source_preimage_refs[0]
            )
            projected_matches = (
                resource.get("resource_id") == resource_grant_id
                and resource.get("request_sha256") == projected_request_sha256
                and resource.get("request_sha256") == stored_grant.get("resource_request_sha256")
                and resource.get("authority_preimage_ref") == stored_grant.get("authority_preimage_ref")
                and resource.get("grant_ref") == expected_grant_ref
            )
        except (IntegrityError, KeyError, SchemaError, TypeError, ValueError):
            return None, "resource_grant_invalid"
        if not source_matches or not projected_matches:
            return None, "resource_grant_mismatch"
        return stored_grant, None

    def _current_materialized_resource_grant(
        self,
        *,
        resource_grant_id: str,
        resource: object,
        trusted_authority: TrustedRuntimeAuthority,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Return one current v1.1 grant or its stable admission denial code."""
        stored_grant, stored_reason = self._stored_materialized_resource_grant(
            resource_grant_id=resource_grant_id,
            resource=resource,
        )
        if stored_grant is None:
            return None, stored_reason
        try:
            source_events = [
                event
                for event in self.ledger.snapshot().events
                if event.get("event_id") == stored_grant["source_event_id"]
                and event.get("event_hash") == stored_grant["source_event_hash"]
                and event.get("command_id") == stored_grant["source_command_id"]
                and event.get("command_payload_hash") == stored_grant["source_command_payload_hash"]
                and event.get("stream_id") == resource_grant_id
            ]
            if len(source_events) != 1:
                raise IntegrityError("resource grant source event is not exact")
            expected_grant = derive_resource_grant_v1_1_record(
                committed_event=source_events[0],
                project_id=self.ledger.project_id,
                trusted_authority=trusted_authority,
            )
            self._validate_resource_grant_record(expected_grant)
        except (IntegrityError, KeyError, SchemaError, TypeError, ValueError):
            return None, "resource_grant_invalid"
        if stored_grant != expected_grant:
            return None, "resource_grant_mismatch"
        return stored_grant, None

    def _current_c1_lease_resource_grant(
        self,
        *,
        streams: dict[str, dict[str, Any]],
        lease: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Return a lease's current materialized Resource grant."""
        resource_grant_id = lease.get("resource_grant_id")
        if not isinstance(resource_grant_id, str):
            return None, "resource_grant_mismatch"
        try:
            stored_grant, grant_reason = self._current_materialized_resource_grant(
                resource_grant_id=resource_grant_id,
                resource=streams.get(resource_grant_id),
                trusted_authority=self._current_trusted_runtime_authority(),
            )
        except IntegrityError:
            return None, "resource_grant_invalid"
        if stored_grant is None:
            return None, grant_reason or "resource_grant_invalid"
        return stored_grant, grant_reason

    def _current_c1_lease_context(
        self,
        *,
        streams: dict[str, dict[str, Any]],
        lease: dict[str, Any],
        require_running_attempt: bool,
        allowed_attempt_statuses: frozenset[str] | None = None,
        require_attempt_lease: bool = True,
    ) -> tuple[tuple[dict[str, Any], dict[str, Any], dict[str, Any], datetime] | None, str | None]:
        """Return the active Task/Dispatch/Attempt/Lease relation at trusted now."""
        now = self._c1_trusted_now()
        lease_expiry = self._resource_grant_expiry(lease.get("expires_at"))
        if now is None or lease_expiry is None:
            return None, "lease_time_invalid"
        if now >= lease_expiry:
            return None, "lease_expired"
        task_id = lease.get("task_id")
        dispatch_id = lease.get("dispatch_id")
        attempt_id = lease.get("attempt_id")
        if not all(isinstance(value, str) for value in (task_id, dispatch_id, attempt_id)):
            return None, "lease_relation_mismatch"
        task = streams.get(task_id)
        dispatch = streams.get(dispatch_id)
        attempt = streams.get(attempt_id)
        task_revision = lease.get("task_revision")
        attempt_statuses = (
            allowed_attempt_statuses
            if allowed_attempt_statuses is not None
            else ({"running"} if require_running_attempt else {"claimed", "running"})
        )
        if (
            not isinstance(task, dict)
            or task.get("task_id") != task_id
            or task.get("status") != "in_progress"
            or task.get("current_revision") != task_revision
            or not isinstance(dispatch, dict)
            or dispatch.get("dispatch_id") != dispatch_id
            or dispatch.get("status") != "claimed"
            or dispatch.get("task_id") != task_id
            or dispatch.get("task_revision") != task_revision
            or dispatch.get("lease_id") != lease.get("lease_id")
            or not isinstance(attempt, dict)
            or attempt.get("attempt_id") != attempt_id
            or attempt.get("status") not in attempt_statuses
            or attempt.get("task_id") != task_id
            or attempt.get("task_revision") != task_revision
            or attempt.get("dispatch_id") != dispatch_id
            or (require_attempt_lease and attempt.get("lease_id") != lease.get("lease_id"))
            or (not require_attempt_lease and attempt.get("lease_id") is not None)
        ):
            return None, "lease_relation_mismatch"
        return (task, dispatch, attempt, now), None

    @staticmethod
    def _heartbeat_events_for_lease(events: Iterable[dict[str, Any]], lease_id: str) -> list[dict[str, Any]]:
        return [
            event
            for event in events
            if event.get("event_type") == "HeartbeatRecorded"
            and event.get("stream_id") == lease_id
            and isinstance(event.get("payload"), dict)
            and event["payload"].get("lease_id") == lease_id
        ]

    @staticmethod
    def _grant_heartbeat_stale_threshold(grant: dict[str, Any]) -> int | None:
        heartbeat_policy = grant.get("heartbeat_policy")
        threshold = heartbeat_policy.get("stale_threshold_seconds") if isinstance(heartbeat_policy, dict) else None
        if type(threshold) is not int or threshold < 0:
            return None
        return threshold

    @staticmethod
    def _meaningful_text_list(value: object) -> bool:
        return (
            isinstance(value, list)
            and bool(value)
            and all(isinstance(item, str) and bool(item.strip()) for item in value)
        )

    @staticmethod
    def _resource_grant_expiry(value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                return None
            return parsed.astimezone(UTC)
        except (OverflowError, TypeError, ValueError):
            return None

    def _c1_trusted_now(self) -> datetime | None:
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None:
            return None
        try:
            if now.utcoffset() is None:
                return None
            return now.astimezone(UTC)
        except (OverflowError, TypeError, ValueError):
            return None

    def _c1_lease_is_current(self, lease: dict[str, Any]) -> bool:
        expiry = self._resource_grant_expiry(lease.get("expires_at"))
        now = self._c1_trusted_now()
        return expiry is not None and now is not None and now < expiry

    def _canonical_authority_resolver(self) -> LedgerAuthorityGrantResolver | None:
        resolver = self.authority_resolver
        return resolver if type(resolver) is LedgerAuthorityGrantResolver else None

    @staticmethod
    def _freeze_t2_authority_root(resolver: Any) -> tuple[Path, tuple[int, int]]:
        if not callable(resolver):
            raise ArsError("T2 authority resolver must be callable")
        candidate = getattr(resolver, "control_root", None)
        if candidate is None:
            raise ArsError("T2 authority resolver requires an existing control_root")
        try:
            root = Path(candidate).resolve(strict=True)
            observed = root.stat()
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise ArsError("T2 authority resolver control_root is not verifiable") from exc
        if not root.is_dir():
            raise ArsError("T2 authority resolver control_root must be an existing directory")
        return root, (observed.st_dev, observed.st_ino)

    def _t2_authority_root_for_lock(self) -> Path | None:
        resolver = self.t2_authority_resolver
        if resolver is None:
            return None
        root, identity = self._freeze_t2_authority_root(resolver)
        if (root, identity) != (self._t2_authority_root, self._t2_authority_identity):
            raise ArsError("T2 authority resolver control_root changed after construction")
        return self._t2_authority_root

    @staticmethod
    def _authority_time(value: object) -> object:
        if isinstance(value, datetime):
            return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
        return value

    @classmethod
    def _authority_resolution_record(cls, resolution: Any | None) -> dict[str, Any] | None:
        if resolution is None:
            return None
        if type(resolution) is not ScopedAuthorityGrantResolution:
            raise IntegrityError("lifecycle authority resolver returned non-canonical evidence")
        subject_scope = getattr(resolution, "subject_scope", None)
        if hasattr(subject_scope, "to_dict"):
            subject_scope = subject_scope.to_dict()
        return {
            "authority_grant_id": getattr(resolution, "authority_grant_id", None),
            "authority_grant_sha256": getattr(resolution, "authority_grant_sha256", None),
            "schema_id": getattr(resolution, "schema_id", None),
            "schema_version": getattr(resolution, "schema_version", None),
            "schema_sha256": getattr(resolution, "schema_sha256", None),
            "actor_id": getattr(resolution, "actor_id", None),
            "subject_scope": subject_scope,
            "effective_at": cls._authority_time(getattr(resolution, "effective_at", None)),
            "expires_at": cls._authority_time(getattr(resolution, "expires_at", None)),
            "activation_event_id": getattr(resolution, "activation_event_id", None),
            "activation_position": getattr(resolution, "activation_position", None),
            "administration_decision_id": getattr(resolution, "administration_decision_id", None),
            "administration_decision_sha256": getattr(resolution, "administration_decision_sha256", None),
            "status": getattr(resolution, "status", None),
            "revocation_event_id": getattr(resolution, "revocation_event_id", None),
        }

    def _lifecycle_authority_binding(
        self,
        command: Command,
        command_schema: SchemaIdentity,
        snapshot: LedgerSnapshot,
        *,
        actor_class: str,
    ) -> tuple[dict[str, Any], str]:
        project_id, subject_kind, subject_id, required_risk = self._lifecycle_authority_inputs(
            command,
            snapshot,
        )
        binding = {
            "actor_id": command.actor_id,
            "actor_class": actor_class,
            "authority_grant_id": command.envelope["authority_grant_id"],
            "command_type": command.envelope["command_type"],
            "idempotency_key": command.idempotency_key,
            "command_schema_id": command_schema.schema_id,
            "command_schema_version": command_schema.schema_version,
            "command_schema_sha256": command_schema.sha256,
            "project_id": project_id,
            "subject_kind": subject_kind,
            "subject_id": subject_id,
            "required_risk": required_risk,
            "target_stream_id": command.target_stream_id,
            "expected_stream_version": command.expected_stream_version,
            "payload_hash": command.payload_hash,
        }
        return binding, actor_class

    @staticmethod
    def _authority_key(
        resolution: dict[str, Any] | None,
    ) -> str:
        grant_hash = resolution.get("authority_grant_sha256") if resolution is not None else None
        if (
            isinstance(grant_hash, str)
            and len(grant_hash) == 64
            and all(character in "0123456789abcdef" for character in grant_hash)
        ):
            return grant_hash
        raise IntegrityError("lifecycle authority resolution has no canonical grant hash")

    def _resolve_lifecycle_authority(
        self,
        command: Command,
        command_schema: SchemaIdentity,
        snapshot: LedgerSnapshot,
    ) -> tuple[_LifecycleAuthorityEvidence, str | None]:
        resolver = self._canonical_authority_resolver()
        binding, _ = self._lifecycle_authority_binding(
            command,
            command_schema,
            snapshot,
            actor_class="unproven",
        )
        resolution: dict[str, Any] | None = None
        canonical_resolution: dict[str, Any] | None = None
        denial: str | None = None
        resolver_now: Any = None
        if resolver is None:
            denial = "Lifecycle commands require the canonical scoped authority resolver."
        else:
            if command.envelope["command_type"] in _C1_COMMAND_TYPES:
                resolver_now = self._c1_trusted_now()
                if resolver_now is None:
                    denial = "C1 lifecycle commands require a timezone-aware trusted clock convertible to UTC."
            else:
                resolver_now = self.clock()
        if resolver is not None and denial is None:
            command_identity = GrantedCommandIdentity(
                command_type=command.envelope["command_type"],
                schema_id=command_schema.schema_id,
                schema_version=str(command_schema.schema_version),
                schema_sha256=command_schema.sha256,
            )
            project_id = binding["project_id"]
            subject_kind = binding["subject_kind"]
            subject_id = binding["subject_id"]
            required_risk = binding["required_risk"]
            try:
                evidence = resolver.resolve_lifecycle_command(
                    grant_id=command.envelope["authority_grant_id"],
                    actor_id=command.actor_id,
                    command=command_identity,
                    required_risk=required_risk,
                    project_id=project_id,
                    subject_kind=subject_kind,
                    subject_id=subject_id,
                    now=resolver_now,
                )
                if type(evidence) is not LifecycleCommandAuthorityEvidence:
                    raise ArsError("authority resolver returned non-canonical lifecycle evidence")
                context = evidence.administration_context
                if (
                    type(context) is not AuthorityAdministrationContext
                    or context.project_id != project_id
                    or type(evidence.command_resolution) is not ScopedAuthorityGrantResolution
                    or type(evidence.canonical_grant_identity) is not ScopedAuthorityGrantResolution
                ):
                    raise IntegrityError("lifecycle authority bundle evidence is invalid")
                if (
                    command.envelope["command_type"] in SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES
                    and command.actor_id != context.owner_actor_id
                ):
                    expected_actor_class = evidence.actor_class
                else:
                    expected_actor_class = "human" if command.actor_id == context.owner_actor_id else "unproven"
                if evidence.actor_class != expected_actor_class:
                    raise IntegrityError("lifecycle authority actor class disagrees with owner context")
                if evidence.actor_class == "unproven":
                    raise ArsError("authority actor class is not proven by the bootstrap owner")
                resolution = self._authority_resolution_record(evidence.command_resolution)
                canonical_resolution = self._authority_resolution_record(evidence.canonical_grant_identity)
                if canonical_resolution != resolution:
                    raise IntegrityError("lifecycle authority bundle resolutions disagree")
                binding = {**binding, "actor_class": evidence.actor_class}
            except IntegrityError:
                raise
            except ArsError as exc:
                resolution = None
                canonical_resolution = None
                denial = str(exc)
        return (
            _LifecycleAuthorityEvidence(
                binding=binding,
                resolution=resolution,
                canonical_resolution=canonical_resolution,
                authority_key=(self._authority_key(canonical_resolution) if canonical_resolution is not None else ""),
                denial=denial,
            ),
            denial,
        )

    def _load_lifecycle_authority_receipt(
        self,
        command: Command,
        command_schema: SchemaIdentity,
        lifecycle_authority: _LifecycleAuthorityEvidence,
    ) -> Receipt | None:
        if lifecycle_authority.resolution is None:
            raise IntegrityError("lifecycle command missing fresh resolution evidence")
        receipt = self.receipts.load_scoped(
            self._authority_scope(command),
            command.payload_hash,
            lifecycle_authority.authority_key,
            command.expected_stream_version,
            project_id=command.envelope.get("project_id"),
            target_stream_id=command.target_stream_id,
        )
        if receipt is None:
            return None
        if command.envelope["command_type"] in _C1_COMMAND_TYPES:
            self._return_scoped_receipt_or_raise(command, receipt)
        if command.envelope["command_type"] == "RequestResourceGrant" and receipt.status == "accepted":
            self._ensure_resource_grant_materialized(command)
        if command.envelope["command_type"] == "CreateBackup" and receipt.status == "accepted":
            self._ensure_backup_materialized(command)
        self._reconcile_scoped_authority_receipt(
            command,
            receipt,
            lifecycle_resolution=lifecycle_authority.resolution,
            canonical_resolution=lifecycle_authority.canonical_resolution,
            command_schema=command_schema,
        )
        return self._return_scoped_receipt_or_raise(command, receipt)

    def _validate_message_scoped_retry_identity(
        self,
        command: Command,
        receipt: Receipt,
    ) -> None:
        if command.envelope["command_type"] not in {*_MESSAGE_COMMAND_TYPES, "ClaimDispatch"}:
            return
        if command.command_id == receipt.command_id:
            return
        if self.receipts.load(command.command_id) is not None:
            raise ConflictError("command ID conflicts with stored receipt")
        if any(event.get("command_id") == command.command_id for event in self.ledger.snapshot().events):
            raise ConflictError("command ID conflicts with committed command")
        raise ConflictError("idempotency key conflicts with committed command")

    def _return_scoped_receipt_or_raise(
        self,
        command: Command,
        receipt: Receipt,
    ) -> Receipt:
        if command.command_id == receipt.command_id:
            return receipt
        if self.receipts.load(command.command_id) is not None:
            raise ConflictError("command ID conflicts with stored receipt")
        if any(event.get("command_id") == command.command_id for event in self.ledger.snapshot().events):
            raise ConflictError("command ID conflicts with committed command")
        raise ConflictError("idempotency key conflicts with committed command")

    def _stored_rejected_receipt(self, command: Command) -> Receipt | None:
        """Return an idempotent rejected receipt while holding WriterLock."""
        stored = self.receipts.load(command.command_id)
        if stored is None or stored.status != "rejected":
            return None
        if stored.payload_hash != command.payload_hash:
            raise ConflictError("command ID conflicts with stored receipt")
        if (
            stored.command_id != command.command_id
            or stored.event_batch_id is not None
            or not stored.reason_code
            or not stored.explanation
            or not stored.unmet_preconditions
        ):
            raise IntegrityError("stored rejected receipt is inconsistent")
        return stored

    def _rejected(
        self,
        command: Command,
        observed_version: int,
        reason_code: str,
        explanation: str,
    ) -> Receipt:
        return Receipt(
            status="rejected",
            command_id=command.command_id,
            payload_hash=command.payload_hash,
            event_batch_id=None,
            observed_stream_version=observed_version,
            reason_code=reason_code,
            explanation=explanation,
            unmet_preconditions=(reason_code,),
        )

    def _task_revision_object(
        self,
        task_id: str,
        revision: int,
    ) -> dict[str, Any] | None:
        directory = self.control_root / "objects" / "task" / task_id
        matches = sorted(directory.glob(f"{revision:08d}-*.json"))
        if not matches:
            return None
        value = self.objects.read("task", task_id, revision)
        if not isinstance(value, dict):
            raise IntegrityError("Task revision object must be a mapping")
        return value

    @staticmethod
    def _revision_graph(
        snapshot: LedgerSnapshot,
    ) -> tuple[
        dict[str, int],
        dict[tuple[str, int], tuple[str, int]],
        dict[tuple[str, int], _TaskRevisionEvidence],
    ]:
        current: dict[str, int] = {}
        edges: dict[tuple[str, int], tuple[str, int]] = {}
        evidence: dict[tuple[str, int], _TaskRevisionEvidence] = {}
        for event in snapshot.events:
            if event["event_type"] == "TaskCreated":
                payload = event.get("payload", {})
                if not isinstance(payload, dict):
                    raise IntegrityError("TaskCreated payload must be a mapping")
                if event.get("schema_id") == "ars://core/event/TaskCreated":
                    definition = payload.get("definition", {})
                    revision = int(definition["revision"])
                else:
                    definition = payload
                    revision = int(payload.get("revision", 1))
                current.setdefault(event["stream_id"], revision)
                evidence[(event["stream_id"], revision)] = _TaskRevisionEvidence(
                    str(event.get("schema_id", "")),
                    definition,
                )
            elif event["event_type"] == "TaskAmended":
                payload = event["payload"]
                task_id = str(payload["task_id"])
                prior_revision = int(payload["prior_revision"])
                new_revision = int(payload["new_revision"])
                if current.get(task_id) != prior_revision:
                    raise IntegrityError("Task amendment history is not current")
                source = (task_id, prior_revision)
                if source in edges:
                    raise IntegrityError("Task revision has multiple successor edges")
                edges[source] = (task_id, new_revision)
                current[task_id] = new_revision
                evidence[(task_id, new_revision)] = _TaskRevisionEvidence(
                    str(event.get("schema_id", "")),
                    payload.get("replacement_definition"),
                )
            elif event["event_type"] == "TaskSuperseded":
                payload = event["payload"]
                if event.get("schema_id") == "ars://core/event/TaskSuperseded":
                    source_id = str(payload["task_id"])
                    source_revision = current.get(source_id)
                    if source_revision is None:
                        raise IntegrityError("Task supersession source history is absent")
                    source = (source_id, source_revision)
                else:
                    source = (
                        str(payload["source_task_id"]),
                        int(payload["source_task_revision"]),
                    )
                replacement = (
                    str(payload["replacement_task_id"]),
                    int(payload["replacement_task_revision"]),
                )
                if source in edges:
                    raise IntegrityError("Task revision has multiple supersession edges")
                edges[source] = replacement
                if source[0] == replacement[0]:
                    current[source[0]] = replacement[1]
                    source_evidence = evidence.get(source)
                    if source_evidence is not None:
                        evidence[replacement] = _TaskRevisionEvidence(
                            source_evidence.schema_id,
                            None,
                        )
        return current, edges, evidence

    @staticmethod
    def _reaches(
        edges: dict[tuple[str, int], tuple[str, int]],
        start: tuple[str, int],
        target: tuple[str, int],
    ) -> bool:
        seen: set[tuple[str, int]] = set()
        pending = [start]
        while pending:
            node = pending.pop()
            if node == target:
                return True
            if node in seen:
                continue
            seen.add(node)
            replacement = edges.get(node)
            if replacement is not None:
                pending.append(replacement)
        return False

    @staticmethod
    def _derived_lineage(
        edges: dict[tuple[str, int], tuple[str, int]],
        source: tuple[str, int],
        replacement: tuple[str, int],
    ) -> list[dict[str, Any]]:
        reverse = {target: origin for origin, target in edges.items()}
        lineage = [source]
        seen = {source}
        while lineage[0] in reverse:
            predecessor = reverse[lineage[0]]
            if predecessor in seen:
                raise IntegrityError("supersession lineage cycle")
            seen.add(predecessor)
            lineage.insert(0, predecessor)
        lineage.append(replacement)
        return [{"task_id": task_id, "revision": revision} for task_id, revision in lineage]

    @staticmethod
    def _content_hash_matches(value: dict[str, Any]) -> bool:
        return content_hash_matches(value)

    @classmethod
    def _is_rich_task_definition(cls, value: dict[str, Any]) -> bool:
        return (
            isinstance(value.get("task_id"), str)
            and isinstance(value.get("revision"), int)
            and not isinstance(value.get("revision"), bool)
            and isinstance(value.get("project_id"), str)
            and cls._content_hash_matches(value)
        )

    def _task_revision_kind(
        self,
        value: dict[str, Any],
        evidence: _TaskRevisionEvidence | None,
        *,
        task_id: str,
        revision: int,
    ) -> str | None:
        if evidence is None:
            return None
        if evidence.definition is not None and value != evidence.definition:
            raise IntegrityError("Task revision object differs from committed event content")
        if evidence.exact:
            if (
                evidence.definition is None
                or not self._is_rich_task_definition(value)
                or value.get("task_id") != task_id
                or value.get("revision") != revision
                or value.get("project_id") != self.ledger.project_id
            ):
                return None
            return "rich"
        consumers = value.get("continuing_consumers")
        if (
            not isinstance(value.get("task_type"), str)
            or not value["task_type"]
            or not isinstance(consumers, list)
            or not consumers
            or not all(isinstance(item, str) and item for item in consumers)
        ):
            return None
        return "generic"

    def _scope_revision_object(
        self,
        scope_id: str,
        revision: int,
        committed_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        directory = self.control_root / "objects" / "scope_definition" / scope_id
        if not list(directory.glob(f"{revision:08d}-*.json")):
            return None
        value = self.objects.read("scope_definition", scope_id, revision)
        if not isinstance(value, dict):
            raise IntegrityError("ScopeDefinition revision object must be a mapping")
        if committed_payload is not None and value != committed_payload:
            raise IntegrityError("ScopeDefinition revision object differs from committed event content")
        return value

    @staticmethod
    def _scope_revision_graph(
        snapshot: LedgerSnapshot,
    ) -> tuple[
        dict[str, int],
        dict[tuple[str, int], tuple[str, int]],
        dict[tuple[str, int], dict[str, Any]],
    ]:
        current: dict[str, int] = {}
        edges: dict[tuple[str, int], tuple[str, int]] = {}
        evidence: dict[tuple[str, int], dict[str, Any]] = {}
        for event in snapshot.events:
            event_type = event["event_type"]
            if event_type == "ScopeDefinitionCreated":
                payload = event["payload"]
                scope_id = str(payload["new_scope_definition_id"])
                revision = int(payload["revision"])
                current.setdefault(scope_id, revision)
                if event.get("schema_id") == "ars://core/event/ScopeDefinitionCreated":
                    evidence[(scope_id, revision)] = payload
            elif event_type == "ScopeDefinitionAmended":
                payload = event["payload"]
                scope_id = str(payload["scope_definition_id"])
                prior = int(payload["prior_revision"])
                new = int(payload["new_revision"])
                if current.get(scope_id) != prior:
                    raise IntegrityError("ScopeDefinition amendment history is not current")
                source = (scope_id, prior)
                if source in edges:
                    raise IntegrityError("ScopeDefinition revision has multiple successor edges")
                edges[source] = (scope_id, new)
                current[scope_id] = new
                if event.get("schema_id") == "ars://core/event/ScopeDefinitionAmended":
                    evidence[(scope_id, new)] = payload
            elif event_type == "ScopeDefinitionSuperseded":
                payload = event["payload"]
                source_id = str(payload["scope_definition_id"])
                source_revision = current.get(source_id)
                if source_revision is None:
                    raise IntegrityError("ScopeDefinition supersession source history is absent")
                source = (source_id, source_revision)
                replacement = (
                    str(payload["replacement_scope_definition_id"]),
                    int(payload["replacement_revision"]),
                )
                if source in edges:
                    raise IntegrityError("ScopeDefinition revision has multiple successor edges")
                edges[source] = replacement
                if source[0] == replacement[0]:
                    current[source[0]] = replacement[1]
        return current, edges, evidence

    def _scope_definition(
        self,
        scope_id: str,
        revision: int,
        evidence: dict[tuple[str, int], dict[str, Any]],
    ) -> dict[str, Any]:
        created = self._scope_revision_object(
            scope_id,
            1,
            evidence.get((scope_id, 1)),
        )
        if created is None:
            raise IntegrityError("ScopeDefinition base revision is absent")
        definition = dict(created)
        for candidate_revision in range(2, revision + 1):
            amendment = self._scope_revision_object(
                scope_id,
                candidate_revision,
                evidence.get((scope_id, candidate_revision)),
            )
            if amendment is None:
                raise IntegrityError("ScopeDefinition amendment revision is absent")
            try:
                members = materialize_scope_member_changes(
                    definition.get("members", []),
                    amendment.get("member_changes", []),
                )
            except ValueError as exc:
                raise IntegrityError(
                    "ScopeDefinition amendment history contains an invalid typed member delta"
                ) from exc
            definition = {
                **definition,
                "revision": candidate_revision,
                "members": members,
            }
        return definition

    def _scope_members(
        self,
        scope_id: str,
        revision: int,
        evidence: dict[tuple[str, int], dict[str, Any]],
    ) -> dict[str, str]:
        definition = self._scope_definition(scope_id, revision, evidence)
        return {str(member["member_id"]): str(member["member_kind"]) for member in definition.get("members", [])}

    def _prepare_task_command(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
        *,
        command_schema: SchemaIdentity,
    ) -> dict[str, Any] | Receipt:
        payload = command.envelope["payload"]
        command_type = command.envelope["command_type"]
        if command.envelope.get("project_id") != self.ledger.project_id:
            return self._rejected(
                command,
                observed_version,
                "invalid_command_project",
                "Task command project must match the control-store project.",
            )
        task_id = payload.get("new_task_id") if command_type == "CreateTask" else payload.get("task_id")
        if task_id != command.target_stream_id:
            return self._rejected(
                command,
                observed_version,
                "invalid_command_subject_identity",
                "Task payload identity must equal the target stream.",
            )

        if command_type == "CreateTask":
            definition = payload["definition"]
            if (
                definition.get("task_id") != task_id
                or definition.get("project_id") != self.ledger.project_id
                or command.envelope.get("project_id") != self.ledger.project_id
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_command_subject_identity",
                    "Task definition identity and project must bind the command.",
                )
            if definition.get("revision") != 1:
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_task_revision",
                    "A new Task must begin at revision 1.",
                )
            if not self._content_hash_matches(definition):
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_task_definition_hash",
                    "Task definition content hash does not match canonical content.",
                )
            return payload

        if command_type == "SupersedeTask":
            return self._prepare_supersession(
                command,
                snapshot,
                observed_version,
            )

        current, edges, evidence = self._revision_graph(snapshot)
        prior_revision = int(payload["prior_revision"])
        new_revision = int(payload["new_revision"])
        replacement = payload["replacement_definition"]
        if (
            current.get(command.target_stream_id) != prior_revision
            or (command.target_stream_id, prior_revision) in edges
        ):
            return self._rejected(
                command,
                observed_version,
                "stale_task_revision",
                "Task amendment must name the current nonterminal revision.",
            )
        if new_revision != prior_revision + 1:
            return self._rejected(
                command,
                observed_version,
                "invalid_task_revision",
                "Task amendment must advance exactly one revision.",
            )
        if (
            replacement.get("task_id") != command.target_stream_id
            or replacement.get("revision") != new_revision
            or replacement.get("project_id") != self.ledger.project_id
            or command.envelope.get("project_id") != self.ledger.project_id
        ):
            return self._rejected(
                command,
                observed_version,
                "invalid_command_subject_identity",
                "Replacement Task definition must bind the command and revision.",
            )
        if not self._content_hash_matches(replacement):
            return self._rejected(
                command,
                observed_version,
                "invalid_task_definition_hash",
                "Replacement Task definition hash does not match canonical content.",
            )
        source_definition = self._task_revision_object(
            command.target_stream_id,
            prior_revision,
        )
        if source_definition is None:
            return self._rejected(
                command,
                observed_version,
                "task_revision_missing",
                "The prior immutable Task revision is absent.",
            )
        source_kind = self._task_revision_kind(
            source_definition,
            evidence.get((command.target_stream_id, prior_revision)),
            task_id=command.target_stream_id,
            revision=prior_revision,
        )
        if source_kind != "rich":
            return self._rejected(
                command,
                observed_version,
                "source_task_definition_incompatible",
                "Task amendment requires a matching rich source definition.",
            )
        actual_changes = changed_task_fields(
            source_definition,
            replacement,
        )
        if not actual_changes or set(payload["changed_fields"]) != actual_changes:
            return self._rejected(
                command,
                observed_version,
                "task_changed_fields_mismatch",
                "Task changed_fields must name the exact typed definition delta.",
            )
        if command_schema.schema_id != "ars://core/command/AmendTask":
            raise IntegrityError("Task amendment used an unexpected schema identity")
        return payload

    def _prepare_scope_command(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
    ) -> dict[str, Any] | Receipt:
        payload = command.envelope["payload"]
        command_type = command.envelope["command_type"]
        if command.envelope.get("project_id") != self.ledger.project_id:
            return self._rejected(
                command,
                observed_version,
                "invalid_command_project",
                "ScopeDefinition command project must match the control-store project.",
            )
        scope_id = (
            payload.get("new_scope_definition_id")
            if command_type == "CreateScopeDefinition"
            else payload.get("scope_definition_id")
        )
        if scope_id != command.target_stream_id:
            return self._rejected(
                command,
                observed_version,
                "invalid_command_subject_identity",
                "ScopeDefinition payload identity must equal the target stream.",
            )

        if command_type == "CreateScopeDefinition":
            members = payload["members"]
            if (
                payload["revision"] != 1
                or not has_unique_member_ids(members)
                or command.envelope.get("project_id") != self.ledger.project_id
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_scope_definition",
                    "A new ScopeDefinition requires revision 1 and unique members.",
                )
            return payload

        current, edges, evidence = self._scope_revision_graph(snapshot)
        source_revision = current.get(command.target_stream_id)
        if source_revision is None:
            return self._rejected(
                command,
                observed_version,
                "scope_revision_missing",
                "The current ScopeDefinition revision is absent.",
            )
        source = (command.target_stream_id, source_revision)
        if source in edges:
            return self._rejected(
                command,
                observed_version,
                "scope_revision_terminal",
                "The current ScopeDefinition revision is terminal.",
            )

        if command_type == "AmendScopeDefinition":
            prior_revision = int(payload["prior_revision"])
            new_revision = int(payload["new_revision"])
            if source_revision != prior_revision:
                return self._rejected(
                    command,
                    observed_version,
                    "stale_scope_revision",
                    "ScopeDefinition amendment must name the current revision.",
                )
            if new_revision != prior_revision + 1:
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_scope_revision",
                    "ScopeDefinition amendment must advance exactly one revision.",
                )
            if set(payload["changed_fields"]) != {"members"}:
                return self._rejected(
                    command,
                    observed_version,
                    "unsupported_scope_amendment_field",
                    "The accepted delta contract materializes only member changes.",
                )
            member_changes = payload["member_changes"]
            if not member_changes or not has_unique_member_ids(member_changes):
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_scope_definition",
                    "ScopeDefinition amendment member identities must be unique.",
                )
            if (
                self._scope_revision_object(
                    command.target_stream_id,
                    prior_revision,
                    evidence.get((command.target_stream_id, prior_revision)),
                )
                is None
            ):
                return self._rejected(
                    command,
                    observed_version,
                    "scope_revision_missing",
                    "The prior immutable ScopeDefinition revision is absent.",
                )
            source_definition = self._scope_definition(
                command.target_stream_id,
                prior_revision,
                evidence,
            )
            try:
                materialize_scope_member_changes(
                    source_definition.get("members", []),
                    member_changes,
                )
            except ValueError as exc:
                return self._rejected(
                    command,
                    observed_version,
                    "invalid_scope_definition",
                    str(exc),
                )
            return payload

        if command_type == "CompleteScope":
            revision = int(payload["revision"])
            if revision != source_revision:
                return self._rejected(
                    command,
                    observed_version,
                    "stale_scope_revision",
                    "Scope completion must name the current immutable revision.",
                )
            definition = self._scope_definition(
                command.target_stream_id,
                source_revision,
                evidence,
            )
            if payload["completion_predicate"] != definition.get("completion_predicate"):
                return self._rejected(
                    command,
                    observed_version,
                    "scope_completion_predicate_mismatch",
                    "Scope completion must reproduce the current revision's predicate.",
                )
            dispositions = payload["member_dispositions"]
            if not has_unique_member_ids(dispositions):
                return self._rejected(
                    command,
                    observed_version,
                    "duplicate_scope_member_disposition",
                    "Each current ScopeDefinition member requires one disposition.",
                )
            observed_members = {str(item["member_id"]): str(item["member_kind"]) for item in dispositions}
            expected_members = {
                str(item["member_id"]): str(item["member_kind"]) for item in definition.get("members", [])
            }
            if observed_members != expected_members:
                return self._rejected(
                    command,
                    observed_version,
                    "missing_scope_member_disposition",
                    "Every current ScopeDefinition member requires one exact disposition.",
                )
            if not payload["completion_evidence_refs"]:
                return self._rejected(
                    command,
                    observed_version,
                    "scope_completion_evidence_missing",
                    "Scope completion requires durable completion evidence.",
                )
            try:
                validate_scope_completion_members(
                    definition,
                    dispositions,
                    self._c1_streams(snapshot),
                )
            except ValueError as exc:
                return self._rejected(
                    command,
                    observed_version,
                    "scope_member_not_resolved",
                    str(exc),
                )
            return payload

        replacement = (
            str(payload["replacement_scope_definition_id"]),
            int(payload["replacement_revision"]),
        )
        if self._reaches(edges, replacement, source):
            return self._rejected(
                command,
                observed_version,
                "scope_supersession_cycle",
                "The replacement ScopeDefinition reaches the source revision.",
            )
        if replacement in edges:
            return self._rejected(
                command,
                observed_version,
                "replacement_scope_revision_terminal",
                "The replacement ScopeDefinition revision is terminal.",
            )
        if (
            current.get(replacement[0]) != replacement[1]
            or self._scope_revision_object(
                *replacement,
                committed_payload=evidence.get(replacement),
            )
            is None
        ):
            return self._rejected(
                command,
                observed_version,
                "replacement_scope_revision_missing",
                "The replacement must be the current immutable ScopeDefinition revision.",
            )
        expected_members = self._scope_members(*source, evidence=evidence)
        if not has_unique_member_ids(payload["member_dispositions"]):
            return self._rejected(
                command,
                observed_version,
                "duplicate_scope_member_disposition",
                "Each current ScopeDefinition member requires one disposition.",
            )
        dispositions = {str(item["member_id"]): str(item["member_kind"]) for item in payload["member_dispositions"]}
        if dispositions != expected_members:
            return self._rejected(
                command,
                observed_version,
                "missing_scope_member_disposition",
                "Every current ScopeDefinition member requires one exact disposition.",
            )
        return payload

    def _prepare_exact_supersession(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
    ) -> dict[str, Any] | Receipt:
        payload = command.envelope["payload"]
        replacement_id = str(payload["replacement_task_id"])
        replacement_revision = int(payload["replacement_task_revision"])
        dispositions = payload["continuing_consumer_dispositions"]
        if not dispositions:
            return self._rejected(
                command,
                observed_version,
                "missing_continuing_consumer_disposition",
                "Task supersession requires explicit continuing-consumer dispositions.",
            )

        current, edges, evidence = self._revision_graph(snapshot)
        source_id = command.target_stream_id
        source_revision = current.get(source_id)
        if source_revision is None:
            return self._rejected(
                command,
                observed_version,
                "source_revision_missing",
                "The source Task revision is absent from committed events.",
            )
        source = (source_id, source_revision)
        replacement = (replacement_id, replacement_revision)
        if source in edges:
            return self._rejected(
                command,
                observed_version,
                "source_revision_terminal",
                "The source Task revision is already terminal.",
            )
        if self._reaches(edges, replacement, source):
            return self._rejected(
                command,
                observed_version,
                "supersession_cycle",
                "The proposed replacement reaches the source revision.",
            )
        if replacement in edges:
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_terminal",
                "The replacement Task revision is already terminal.",
            )

        source_object = self._task_revision_object(source_id, source_revision)
        replacement_object = self._task_revision_object(*replacement)
        if source_object is None or replacement_object is None:
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_missing",
                "The replacement must be an existing immutable Task revision.",
            )
        if replacement_id == source_id:
            if replacement_revision <= source_revision:
                return self._rejected(
                    command,
                    observed_version,
                    "replacement_revision_stale",
                    "A same-Task replacement must be a higher revision.",
                )
        elif current.get(replacement_id) != replacement_revision:
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_stale",
                "The replacement is not the current Task revision.",
            )
        source_evidence = evidence.get(source)
        source_kind = self._task_revision_kind(
            source_object,
            source_evidence,
            task_id=source_id,
            revision=source_revision,
        )
        if replacement_id == source_id and source_kind == "rich":
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_uncommitted",
                "A rich same-Task replacement requires a committed revision transition.",
            )
        replacement_evidence = evidence.get(replacement)
        if (
            replacement_id == source_id
            and replacement_evidence is None
            and source_evidence is not None
            and not source_evidence.exact
        ):
            replacement_evidence = _TaskRevisionEvidence(
                source_evidence.schema_id,
                None,
            )
        replacement_kind = self._task_revision_kind(
            replacement_object,
            replacement_evidence,
            task_id=replacement_id,
            revision=replacement_revision,
        )
        if (
            source_kind is None
            or replacement_kind is None
            or source_kind != replacement_kind
            or (source_kind == "generic" and source_object.get("task_type") != replacement_object.get("task_type"))
        ):
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_incompatible",
                "The replacement Task revision is type-incompatible.",
            )
        expected_consumers = source_object.get("continuing_consumers")
        if expected_consumers is not None and set(dispositions) != set(expected_consumers):
            return self._rejected(
                command,
                observed_version,
                "continuing_consumers_mismatch",
                "Continuing-consumer dispositions must equal the legacy source contract.",
            )
        return dict(payload)

    def _prepare_supersession(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
    ) -> dict[str, Any] | Receipt:
        """Validate a revision-qualified edge from one committed snapshot."""
        if command.envelope.get("schema_id") == "ars://core/command/SupersedeTask":
            return self._prepare_exact_supersession(
                command,
                snapshot,
                observed_version,
            )
        payload = command.envelope["payload"]
        exact_fields = {
            "replacement_task_id",
            "replacement_task_revision",
            "supersession_scope",
            "continuing_consumers",
        }
        if set(payload) != exact_fields:
            return self._rejected(
                command,
                observed_version,
                "invalid_supersession_payload",
                "SupersedeTask payload fields are not exact; caller lineage is forbidden.",
            )
        replacement_id = payload["replacement_task_id"]
        replacement_revision = payload["replacement_task_revision"]
        scope = payload["supersession_scope"]
        consumers = payload["continuing_consumers"]
        if (
            not isinstance(replacement_id, str)
            or not isinstance(replacement_revision, int)
            or isinstance(replacement_revision, bool)
            or replacement_revision < 1
            or not isinstance(scope, list)
            or not scope
            or len(scope) != len(set(scope))
            or not all(isinstance(item, str) and item for item in scope)
            or not isinstance(consumers, list)
            or not consumers
            or len(consumers) != len(set(consumers))
            or not all(isinstance(item, str) and item for item in consumers)
        ):
            return self._rejected(
                command,
                observed_version,
                "invalid_supersession_payload",
                "SupersedeTask requires positive revisions and non-empty exact sets.",
            )

        current, edges, evidence = self._revision_graph(snapshot)
        source_id = command.target_stream_id
        source_revision = current.get(source_id)
        if source_revision is None:
            return self._rejected(
                command,
                observed_version,
                "source_revision_missing",
                "The source Task revision is absent from committed events.",
            )
        source = (source_id, source_revision)
        replacement = (replacement_id, replacement_revision)
        if source in edges:
            return self._rejected(
                command,
                observed_version,
                "source_revision_terminal",
                "The source Task revision is already terminal.",
            )
        if self._reaches(edges, replacement, source):
            return self._rejected(
                command,
                observed_version,
                "supersession_cycle",
                "The proposed replacement reaches the source revision.",
            )
        if replacement in edges:
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_terminal",
                "The replacement Task revision is already terminal.",
            )

        source_object = self._task_revision_object(source_id, source_revision)
        replacement_object = self._task_revision_object(
            replacement_id,
            replacement_revision,
        )
        if source_object is None or replacement_object is None:
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_missing",
                "The replacement must be an existing immutable Task revision.",
            )
        if replacement_id == source_id:
            if replacement_revision <= source_revision:
                return self._rejected(
                    command,
                    observed_version,
                    "replacement_revision_stale",
                    "A same-Task replacement must be a higher revision.",
                )
        elif current.get(replacement_id) != replacement_revision:
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_stale",
                "The replacement is not the current Task revision.",
            )
        source_kind = self._task_revision_kind(
            source_object,
            evidence.get(source),
            task_id=source_id,
            revision=source_revision,
        )
        replacement_evidence = evidence.get(replacement)
        if (
            replacement_id == source_id
            and replacement_evidence is None
            and evidence.get(source) is not None
            and not evidence[source].exact
        ):
            replacement_evidence = _TaskRevisionEvidence(
                evidence[source].schema_id,
                None,
            )
        replacement_kind = self._task_revision_kind(
            replacement_object,
            replacement_evidence,
            task_id=replacement_id,
            revision=replacement_revision,
        )
        if (
            source_kind != "generic"
            or replacement_kind != "generic"
            or source_object.get("task_type") != replacement_object.get("task_type")
        ):
            return self._rejected(
                command,
                observed_version,
                "replacement_revision_incompatible",
                "The replacement Task revision is type-incompatible.",
            )
        expected_consumers = source_object.get("continuing_consumers")
        if expected_consumers is not None and set(consumers) != set(expected_consumers):
            return self._rejected(
                command,
                observed_version,
                "continuing_consumers_mismatch",
                "Continuing consumers must equal the source revision contract.",
            )
        return {
            "source_task_id": source_id,
            "source_task_revision": source_revision,
            "replacement_task_id": replacement_id,
            "replacement_task_revision": replacement_revision,
            "supersession_scope": list(scope),
            "continuing_consumers": sorted(consumers),
            "actor_id": command.actor_id,
            "authority_grant_id": command.envelope["authority_grant_id"],
            "lineage": self._derived_lineage(edges, source, replacement),
        }

    def _stored_conflict_receipt(self, command: Command) -> Receipt | None:
        stored = self.receipts.load(command.command_id)
        if stored is None or stored.status != "conflict":
            return None
        if stored.payload_hash != command.payload_hash:
            raise ConflictError("command ID conflicts with stored receipt")
        if (
            stored.command_id != command.command_id
            or stored.event_batch_id is not None
            or stored.reason_code not in {"stream_version_conflict", "idempotency_conflict"}
        ):
            raise IntegrityError("stored conflict receipt is inconsistent")
        return stored

    def _view_for(self, snapshot: LedgerSnapshot) -> _CommandView:
        if self._view is None or self._view.fingerprint != snapshot.fingerprint:
            self._view = _CommandView.from_snapshot(
                snapshot,
                self.schemas,
                self._authority_state_validator(),
            )
        return self._view

    def _authority_state_validator(
        self,
    ) -> Callable[[dict[str, Any]], None] | None:
        resolver = self._canonical_authority_resolver()
        return resolver.validate_replayed_administration_state if resolver is not None else None

    def _matching_committed(
        self,
        command: Command,
        view: _CommandView,
        *,
        command_schema: SchemaIdentity,
    ) -> list[dict[str, Any]] | None:
        base_scope = (
            command.actor_id,
            command.envelope["authority_grant_id"],
            command.envelope["command_type"],
            command.idempotency_key,
        )
        schema_scope = (
            command_schema.schema_id,
            command_schema.schema_version,
            command_schema.sha256,
        )
        scope = (*base_scope, *schema_scope)
        scoped = view.batches_by_scope.get(scope)
        if scoped is not None:
            first = scoped[0]
            if (
                command.envelope["command_type"] in {*_MESSAGE_COMMAND_TYPES, "ClaimDispatch"}
                and first.get("command_id") != command.command_id
            ):
                raise ConflictError("idempotency key conflicts with committed command")
            same_submission = (
                first.get("command_payload_hash") == command.payload_hash
                and first.get("stream_id") == command.target_stream_id
                and first.get("stream_version") == command.expected_stream_version + 1
            )
            if same_submission:
                return list(scoped)
            raise ConflictError("idempotency key conflicts with committed command")
        if base_scope in view.base_scopes:
            raise ConflictError("idempotency key conflicts with committed command schema")
        identified = view.batches_by_command_id.get(command.command_id)
        if identified is not None:
            raise ConflictError("command ID conflicts with committed command")
        return None

    def _return_or_reconstruct(self, events: list[dict[str, Any]]) -> Receipt:
        receipt = Receipt(
            status="accepted",
            command_id=events[0]["command_id"],
            payload_hash=events[0]["command_payload_hash"],
            event_batch_id=events[0]["transaction_id"],
            observed_stream_version=max(
                event["stream_version"] for event in events if event["stream_id"] == events[0]["stream_id"]
            ),
        )
        stored = self.receipts.load(receipt.command_id)
        if stored is not None:
            if stored != receipt:
                raise IntegrityError("stored receipt does not match committed batch")
            return stored
        return receipt

    def _build_events(
        self,
        command: Command,
        prepared_payload: dict[str, Any] | VerifiedReleasePublication | None = None,
        *,
        command_schema: SchemaIdentity,
    ) -> list[dict[str, Any]]:
        primary = self._build_event(
            command,
            prepared_payload,
            command_schema=command_schema,
        )
        if command.envelope["command_type"] != "ClaimDispatch":
            return [primary]
        payload = command.envelope["payload"]
        event_binding = self.schemas.event_binding("TaskClaimStarted", "ClaimDispatch")
        if event_binding is None:
            raise IntegrityError("ClaimDispatch Task event binding is inactive")
        return [
            primary,
            {
                **primary,
                "event_type": "TaskClaimStarted",
                "stream_id": payload["task_id"],
                "schema_id": event_binding.schema_id,
                "schema_version": event_binding.schema_version,
                "payload": {
                    "task_id": payload["task_id"],
                    "task_revision": payload["task_revision"],
                },
            },
        ]

    def _build_event(
        self,
        command: Command,
        prepared_payload: dict[str, Any] | VerifiedReleasePublication | None = None,
        *,
        command_schema: SchemaIdentity,
    ) -> dict[str, Any]:
        command_type = command.envelope["command_type"]
        if command_type == "CreateScopeDefinition":
            self.objects.write(
                "scope_definition",
                command.target_stream_id,
                int(command.envelope["payload"]["revision"]),
                command.envelope["payload"],
            )
            event_type = "ScopeDefinitionCreated"
            payload = command.envelope["payload"]
        elif command_type == "AmendScopeDefinition":
            self.objects.write(
                "scope_definition",
                command.target_stream_id,
                int(command.envelope["payload"]["new_revision"]),
                command.envelope["payload"],
            )
            event_type = "ScopeDefinitionAmended"
            payload = command.envelope["payload"]
        elif command_type == "SupersedeScopeDefinition":
            event_type = "ScopeDefinitionSuperseded"
            payload = command.envelope["payload"]
        elif command_type == "CompleteScope":
            if prepared_payload is None or prepared_payload != command.envelope["payload"]:
                raise IntegrityError("CompleteScope requires its exact prepared payload")
            event_type = "ScopeCompleted"
            payload = deepcopy(prepared_payload)
        elif command_type == "CreateTask":
            create_binding = self.schemas.command_binding("CreateTask")
            activated_create = create_binding is not None and (
                command_schema.schema_id,
                command_schema.schema_version,
            ) == (
                create_binding.schema_id,
                create_binding.schema_version,
            )
            self.objects.write(
                "task",
                command.target_stream_id,
                1,
                (command.envelope["payload"]["definition"] if activated_create else command.envelope["payload"]),
            )
            event_type = "TaskCreated"
            payload = command.envelope["payload"]
        elif command_type == "AmendTask":
            self.objects.write(
                "task",
                command.target_stream_id,
                int(command.envelope["payload"]["new_revision"]),
                command.envelope["payload"]["replacement_definition"],
            )
            event_type = "TaskAmended"
            payload = command.envelope["payload"]
        elif command_type in _C1_COMMAND_TYPES:
            event_type = _COMMAND_EVENT_TYPES[command_type]
            payload = deepcopy(command.envelope["payload"])
            if command_type == "ExpireLease":
                payload.pop("scheduler_authority_ref")
            elif command_type == "CreateAttempt":
                payload["creation_kind"] = "initial"
        elif command_type in _C2_COMMAND_TYPES:
            event_type = _COMMAND_EVENT_TYPES[command_type]
            payload = deepcopy(
                prepared_payload if command_type == "RecordAttemptPartial" else command.envelope["payload"]
            )
            if command_type == "RetryAttempt":
                payload["creation_kind"] = "retry"
        elif command_type in _C3_COMMAND_TYPES:
            if prepared_payload is None or prepared_payload != command.envelope["payload"]:
                raise IntegrityError(f"{command_type} requires its exact prepared payload")
            event_type = _COMMAND_EVENT_TYPES[command_type]
            payload = deepcopy(prepared_payload)
            if command_type == "ClosePartial":
                payload["subject_kind"] = "task"
        elif command_type in _BACKUP_COMMAND_TYPES:
            if prepared_payload is None or prepared_payload != command.envelope["payload"]:
                raise IntegrityError("CreateBackup requires its exact prepared payload")
            event_type = _COMMAND_EVENT_TYPES[command_type]
            payload = deepcopy(prepared_payload)
        elif command_type in _ARTEFACT_AUTHORITY_COMMAND_TYPES:
            if prepared_payload is None or prepared_payload != command.envelope["payload"]:
                raise IntegrityError(f"{command_type} requires its exact prepared payload")
            event_type = _COMMAND_EVENT_TYPES[command_type]
            payload = deepcopy(prepared_payload)
        elif command_type in _CONTEXT_PACKET_COMMAND_TYPES:
            if prepared_payload is None or prepared_payload != command.envelope["payload"]:
                raise IntegrityError(f"{command_type} requires its exact prepared payload")
            event_type = _COMMAND_EVENT_TYPES[command_type]
            payload = deepcopy(prepared_payload)
        elif command_type == "SupersedeTask":
            if prepared_payload is None:
                raise IntegrityError("SupersedeTask requires prepared graph payload")
            event_type = "TaskSuperseded"
            payload = prepared_payload
        elif command_type in _MESSAGE_COMMAND_TYPES:
            event_type = _COMMAND_EVENT_TYPES[command_type]
            payload = deepcopy(command.envelope["payload"])
        elif command_type == "VerifyEvidenceDeletion":
            authorizer = self.deletion_manifest_authorizer
            if authorizer is None:
                raise ArsError("VerifyEvidenceDeletion requires a trusted deletion manifest authorizer")
            payload = authorizer(
                command.envelope["payload"],
                command.actor_id,
                command.envelope["authority_grant_id"],
            )
            if payload.get("status") != "verified":
                raise ArsError("deletion manifest authorizer did not verify")
            event_type = "EvidenceDeletionVerified"
        elif command_type == "RevokeAuthorityGrant":
            if prepared_payload is None:
                raise IntegrityError("RevokeAuthorityGrant requires prepared payload")
            event_type = "AuthorityGrantRevoked"
            payload = prepared_payload
        elif command_type in {
            "ActivateAuthorityGrant",
            "ActivateExternalAssuranceRecordGrant",
        }:
            if prepared_payload is None:
                raise IntegrityError(f"{command_type} requires prepared payload")
            event_type = "AuthorityGrantActivated"
            payload = prepared_payload
        elif command_type in {
            "RevokeIssuedAuthorityGrant",
            "RevokeExternalAssuranceRecordGrant",
        }:
            if prepared_payload is None:
                raise IntegrityError(f"{command_type} requires prepared payload")
            event_type = "AuthorityGrantRevoked"
            payload = prepared_payload
        elif command_type == "PublishReleaseGateDecision":
            if not isinstance(prepared_payload, VerifiedReleasePublication):
                raise IntegrityError("PublishReleaseGateDecision requires verified publication")
            event_type = "ReleaseGateDecisionPublished"
            payload = None
        else:
            raise ArsError(f"unsupported command type: {command_type}")
        event_binding = self.schemas.event_binding(event_type, command_type)
        event_schema_id = event_binding.schema_id if event_binding is not None else "ars://core/event"
        event_schema_version = event_binding.schema_version if event_binding is not None else "1.0.0"
        if event_type == "ReleaseGateDecisionPublished" and event_binding is None:
            event_schema_id = "ars://core/event/ReleaseGateDecisionPublished"
        occurred_at: str | None = None
        if command_type == "RequestResourceGrant":
            trusted_now = self._c1_trusted_now()
            if trusted_now is None:
                raise IntegrityError("resource grant requires a valid trusted service clock")
            occurred_at = trusted_now.isoformat().replace("+00:00", "Z")
        envelope = {
            "event_type": event_type,
            "stream_id": command.target_stream_id,
            "command_id": command.command_id,
            "command_type": command_type,
            "command_schema_id": command_schema.schema_id,
            "command_schema_version": command_schema.schema_version,
            "command_schema_sha256": command_schema.sha256,
            "actor_id": command.actor_id,
            "authority_grant_id": command.envelope["authority_grant_id"],
            "idempotency_key": command.idempotency_key,
            "command_payload_hash": command.payload_hash,
            "correlation_id": command.envelope["correlation_id"],
            "causation_id": command.envelope["causation_id"],
            "schema_id": event_schema_id,
            "schema_version": event_schema_version,
            "occurred_at": occurred_at,
        }
        return envelope if payload is None else {**envelope, "payload": payload}

    def _prepare_release_publication(
        self,
        command: Command,
    ) -> VerifiedReleasePublication:
        evidence = self.release_publication_evidence
        if evidence is None:
            raise PublicationEvidenceError("release publication evidence resolver is unavailable")
        resolver = self._canonical_authority_resolver()
        if resolver is None:
            raise ArsError("release publication requires the canonical authority resolver")
        request = ReleasePublicationRequest.from_dict(command.envelope["payload"])
        resolved = resolver.resolve(
            request.publication_authority_grant_id,
            command.actor_id,
            "PublishReleaseGateDecision",
            self.ledger.project_id,
            "release_gate_decision",
            command.target_stream_id,
            self.clock(),
        )
        if resolved.authority_grant_sha256 != request.publication_authority_sha256:
            raise ArsError("publication authority hash mismatch")
        verified = verify_release_publication(request, evidence, self.schemas)
        if (
            verified.publication_authority_grant_id != command.envelope["authority_grant_id"]
            or verified.publication_authority_sha256 != resolved.authority_grant_sha256
        ):
            raise ArsError("publication authority evidence mismatch")
        return verified

    def _prepare_authority_revocation(self, command: Command, observed_version: int) -> dict[str, Any]:
        resolver = self._canonical_authority_resolver()
        if resolver is None:
            raise ArsError("RevokeAuthorityGrant requires authority resolver")
        payload = command.envelope["payload"]
        fields = {
            "project_id",
            "target_grant_id",
            "target_grant_sha256",
            "authority_grant_sha256",
            "reason",
        }
        if set(payload) != fields or not isinstance(payload.get("reason"), str) or not payload["reason"]:
            raise ArsError("invalid authority revocation payload")
        if payload["project_id"] != self.ledger.project_id:
            raise ArsError("authority revocation project mismatch")
        if payload["target_grant_id"] != command.target_stream_id:
            raise ArsError("authority revocation target mismatch")
        now = self.clock()
        authorizing = resolver.resolve(
            command.envelope["authority_grant_id"],
            command.actor_id,
            "RevokeAuthorityGrant",
            self.ledger.project_id,
            "authority_grant",
            command.target_stream_id,
            now,
        )
        target = resolver.grant_at(command.target_stream_id, now)
        if authorizing.authority_grant_sha256 != payload["authority_grant_sha256"]:
            raise ArsError("authority revocation authorizing hash mismatch")
        if target.authority_grant_sha256 != payload["target_grant_sha256"]:
            raise ArsError("authority revocation target hash mismatch")
        if observed_version != 1:
            raise ArsError("authority revocation requires active version 1")
        return {
            "project_id": self.ledger.project_id,
            "target_grant_id": target.authority_grant_id,
            "target_grant_sha256": target.authority_grant_sha256,
            "authorizing_grant_id": authorizing.authority_grant_id,
            "authorizing_grant_sha256": authorizing.authority_grant_sha256,
            "reason": payload["reason"],
        }

    def _prepare_scoped_authority_activation(
        self,
        command: Command,
        observed_version: int,
    ) -> dict[str, Any]:
        resolver = self._canonical_authority_resolver()
        if resolver is None:
            raise ArsError("ActivateAuthorityGrant requires authority resolver")
        payload = command.envelope["payload"]
        context = resolver.administration_context()
        if (
            observed_version != 0
            or command.envelope.get("project_id") != self.ledger.project_id
            or payload.get("project_id") != self.ledger.project_id
            or payload.get("bootstrap_manifest_sha256") != context.bootstrap_manifest_sha256
            or command.envelope.get("authority_grant_id") != context.root_grant_id
            or payload.get("root_grant_id") != context.root_grant_id
            or payload.get("root_grant_sha256") != context.root_grant_sha256
            or command.actor_id != context.owner_actor_id
            or command.envelope.get("on_behalf_of_actor_id") is not None
        ):
            raise ArsError("scoped authority activation anchor mismatch")
        grant_schema_id, grant_schema_version = self._scoped_grant_schema_for_command(command.envelope["command_type"])
        grant_value = payload.get("new_grant")
        try:
            grant = ScopedAuthorityGrant.from_dict(
                grant_value,
                expected_schema_id=grant_schema_id,
                expected_schema_version=grant_schema_version,
            )
        except ValueError as exc:
            raise ArsError("scoped authority grant invalid") from exc
        if grant.authority_grant_id != command.target_stream_id or grant.canonical_sha256 != payload.get(
            "new_grant_sha256"
        ):
            raise ArsError("scoped authority activation target mismatch")
        schema_identity = self.schemas.resolve_identity(
            grant_schema_id,
            grant_schema_version,
            expected_sha256=str(payload.get("new_grant_schema_sha256", "")),
        )
        if not self.schemas.is_active(
            schema_identity.schema_id,
            str(schema_identity.schema_version),
        ):
            raise ArsError("scoped authority grant schema is not active")
        self.schemas.validate_active(
            schema_identity.schema_id,
            grant_value,
            schema_version=grant_schema_version,
            expected_sha256=schema_identity.sha256,
        )
        validate_scoped_grant_activation(
            grant,
            self.schemas,
            owner_actor_id=context.owner_actor_id,
        )
        decision = resolver.verify_owner_administration_decision(
            str(payload.get("administration_decision_id", "")),
            str(payload.get("administration_decision_sha256", "")),
            action="activate_authority_grant",
            target_grant_id=grant.authority_grant_id,
            target_grant_sha256=grant.canonical_sha256,
            target_grant_schema_sha256=schema_identity.sha256,
            target_grant_schema_id=schema_identity.schema_id,
            target_grant_schema_version=str(schema_identity.schema_version),
            subject_scope=grant.subject_scope,
            effective_at=grant.effective_at,
            expires_at=grant.expires_at,
            owner_actor_id=command.actor_id,
            now=self.clock(),
        )
        if decision.record_id not in command.envelope.get("evidence_refs", []):
            raise ArsError("owner authority administration decision evidence missing")
        self.objects.write(
            "authority_grant",
            grant.authority_grant_id,
            1,
            grant_value,
        )
        return {
            "authority_admission_version": SCOPED_AUTHORITY_ADMISSION_VERSION,
            "project_id": self.ledger.project_id,
            "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
            "root_grant_id": context.root_grant_id,
            "root_grant_sha256": context.root_grant_sha256,
            "administration_decision_id": decision.record_id,
            "administration_decision_sha256": decision.canonical_sha256,
            "activated_grant_id": grant.authority_grant_id,
            "activated_grant_sha256": grant.canonical_sha256,
            "activated_grant_schema_id": schema_identity.schema_id,
            "activated_grant_schema_version": schema_identity.schema_version,
            "activated_grant_schema_sha256": schema_identity.sha256,
            "subject_scope": grant.subject_scope.to_dict(),
            "effective_at": payload["new_grant"]["effective_at"],
            "expires_at": payload["new_grant"]["expires_at"],
        }

    @staticmethod
    def _scoped_grant_schema_for_command(command_type: str) -> tuple[str, str]:
        if command_type == "ActivateExternalAssuranceRecordGrant":
            return EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_ID, EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_VERSION
        return SCOPED_AUTHORITY_GRANT_SCHEMA_ID, SCOPED_AUTHORITY_GRANT_SCHEMA_VERSION

    def _prepare_issued_authority_revocation(
        self,
        command: Command,
        observed_version: int,
    ) -> dict[str, Any]:
        resolver = self._canonical_authority_resolver()
        if resolver is None:
            raise ArsError("RevokeIssuedAuthorityGrant requires authority resolver")
        payload = command.envelope["payload"]
        context = resolver.administration_context()
        if (
            observed_version != 1
            or command.envelope.get("project_id") != self.ledger.project_id
            or payload.get("project_id") != self.ledger.project_id
            or payload.get("bootstrap_manifest_sha256") != context.bootstrap_manifest_sha256
            or command.envelope.get("authority_grant_id") != context.root_grant_id
            or payload.get("root_grant_id") != context.root_grant_id
            or payload.get("root_grant_sha256") != context.root_grant_sha256
            or command.actor_id != context.owner_actor_id
            or command.envelope.get("on_behalf_of_actor_id") is not None
            or payload.get("target_grant_id") != command.target_stream_id
            or payload.get("reason") != command.envelope.get("reason")
        ):
            raise ArsError("issued authority revocation anchor mismatch")
        target = resolver.scoped_grant_identity(command.target_stream_id)
        if (
            target.status != "active"
            or target.authority_grant_sha256 != payload.get("target_grant_sha256")
            or target.schema_sha256 != payload.get("target_grant_schema_sha256")
        ):
            raise ArsError("issued authority revocation target mismatch")
        decision = resolver.verify_owner_administration_decision(
            str(payload.get("administration_decision_id", "")),
            str(payload.get("administration_decision_sha256", "")),
            action="revoke_issued_authority_grant",
            target_grant_id=target.authority_grant_id,
            target_grant_sha256=target.authority_grant_sha256,
            target_grant_schema_sha256=target.schema_sha256,
            target_grant_schema_id=target.schema_id,
            target_grant_schema_version=target.schema_version,
            subject_scope=target.subject_scope,
            effective_at=target.effective_at,
            expires_at=target.expires_at,
            owner_actor_id=command.actor_id,
            now=self.clock(),
        )
        if decision.record_id not in command.envelope.get("evidence_refs", []):
            raise ArsError("owner authority administration decision evidence missing")
        return {
            "authority_admission_version": SCOPED_AUTHORITY_ADMISSION_VERSION,
            "project_id": self.ledger.project_id,
            "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
            "root_grant_id": context.root_grant_id,
            "root_grant_sha256": context.root_grant_sha256,
            "administration_decision_id": decision.record_id,
            "administration_decision_sha256": decision.canonical_sha256,
            "target_grant_id": target.authority_grant_id,
            "target_grant_sha256": target.authority_grant_sha256,
            "target_grant_schema_id": target.schema_id,
            "target_grant_schema_version": target.schema_version,
            "target_grant_schema_sha256": target.schema_sha256,
            "reason": payload["reason"],
        }


del _release_submit_guard
