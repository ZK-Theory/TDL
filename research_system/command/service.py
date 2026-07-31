from __future__ import annotations

import sys
import time

from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_system.authority import ScopedAuthorityGrant
from research_system.command.lifecycle import (
    changed_task_fields,
    content_hash_matches,
    has_unique_member_ids,
    materialize_scope_member_changes,
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
from research_system.ids import new_id
from research_system.operations.backups import (
    RestorePreflightResult,
    validate_restore_preflight_result,
)
from research_system.projection.replay import replay
from research_system.schema_registry import SchemaIdentity, SchemaRegistry
from research_system.store.ledger import (
    EventLedger,
    LedgerSnapshot,
    _take_release_submit_guard,
)
from research_system.store.lock import WriterLock
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore


_release_submit_guard = _take_release_submit_guard()
_CALLER_PROVENANCE_FIELDS = frozenset(
    {
        "command_schema_id",
        "command_schema_version",
        "command_schema_sha256",
    }
)
_SCOPE_COMMAND_TYPES = frozenset(
    {
        "CreateScopeDefinition",
        "AmendScopeDefinition",
        "SupersedeScopeDefinition",
    }
)
_TASK_REVISION_COMMAND_TYPES = frozenset(
    {
        "CreateTask",
        "AmendTask",
        "SupersedeTask",
    }
)
_SCOPED_AUTHORITY_ADMIN_COMMAND_TYPES = frozenset(
    {
        "ActivateAuthorityGrant",
        "RevokeIssuedAuthorityGrant",
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
    ) -> _CommandView:
        replay(snapshot.events, schema_registry=schemas)
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


class CommandService:
    def __init__(
        self,
        control_root: Path,
        ledger: EventLedger,
        objects: ObjectStore,
        receipts: ReceiptStore,
        schemas: SchemaRegistry,
        *,
        authority_resolver: Any | None = None,
        release_publication_evidence: ReleasePublicationEvidenceResolver | None = None,
        clock: Callable[[], datetime] | None = None,
        release_lock_timeout_seconds: float = 300.0,
        monotonic: Callable[[], float] | None = None,
        lock_wait: Callable[[float], None] | None = None,
        t2_authority_resolver: Callable[[str, str, int], Any | None] | None = None,
    ) -> None:
        self.control_root = control_root
        self.ledger = ledger
        self.objects = objects
        self.receipts = receipts
        self.schemas = schemas
        self.authority_resolver = authority_resolver
        self.release_publication_evidence = release_publication_evidence
        self.clock = clock or (lambda: datetime.now(UTC))
        if release_lock_timeout_seconds <= 0:
            raise ValueError("release lock timeout must be positive")
        self.release_lock_timeout_seconds = release_lock_timeout_seconds
        self._monotonic = monotonic or time.monotonic
        self._lock_wait = lock_wait or time.sleep
        self.t2_authority_resolver = t2_authority_resolver
        self._view: _CommandView | None = None
        self.deletion_manifest_authorizer: (
            Callable[
                [dict[str, Any], str, str],
                dict[str, Any],
            ]
            | None
        ) = None
        self._restore_source_root: Path | None = None
        self._restore_preflight_result: RestorePreflightResult | None = None
        self._restore_preflight_rechecker: Callable[[], RestorePreflightResult] | None = None

    def configure_moved_restore(
        self,
        *,
        source_root: Path,
        preflight_result: RestorePreflightResult,
        rechecker: Callable[[], RestorePreflightResult],
    ) -> None:
        """Bind a moved store to evidence that is rerun before each writer lock."""
        if source_root.resolve(strict=False) == self.control_root.resolve(strict=False):
            raise ValueError("moved restore source must differ from target")
        self._restore_source_root = source_root
        self._restore_preflight_result = preflight_result
        self._restore_preflight_rechecker = rechecker

    def _recheck_moved_restore(self, command: Command) -> None:
        if self._restore_source_root is None:
            return
        supplied = self._restore_preflight_result
        rechecker = self._restore_preflight_rechecker
        if supplied is None or rechecker is None:
            raise ArsError("moved store requires restore preflight")
        current = rechecker()
        validate_restore_preflight_result(
            current,
            current_root=self.control_root,
            project_id=self.ledger.project_id,
            actor_id=command.actor_id,
            authority_grant_id=command.envelope["authority_grant_id"],
        )
        if current != supplied:
            raise ArsError("restore preflight changed before writer lock")

    @_release_submit_guard
    def submit(
        self,
        envelope: dict[str, Any],
        release_append: Callable[..., dict[str, Any]] | None = None,
    ) -> Receipt | T2Receipt:
        """Validate WP1 integrity controls; authorization remains downstream."""
        if release_append is None:
            raise ArsError("CommandService.submit requires its guarded release continuation")
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
        with self._submission_lock(command):
            if (
                command.envelope["command_type"] in _SCOPE_COMMAND_TYPES | _TASK_REVISION_COMMAND_TYPES
                and command.envelope.get("project_id") != self.ledger.project_id
            ):
                snapshot = self.ledger.snapshot()
                observed_version = snapshot.stream_versions.get(
                    command.target_stream_id,
                    0,
                )
                return self._write_receipt(
                    command,
                    self._rejected(
                        command,
                        observed_version,
                        "invalid_command_project",
                        "Lifecycle command project must match the control-store project.",
                    ),
                )
            self._recheck_moved_restore(command)
            scoped = self._scoped_authority_receipt(command)
            if scoped is not None:
                return scoped
            stored_conflict = self._stored_conflict_receipt(command)
            if stored_conflict is not None:
                return stored_conflict
            stored_rejected = self._stored_rejected_receipt(command)
            if stored_rejected is not None:
                return stored_rejected
            snapshot = self.ledger.snapshot()
            view = self._view_for(snapshot)
            existing = self._matching_committed(
                command,
                view,
                command_schema=command_schema,
            )
            if existing is not None:
                return self._write_receipt(
                    command,
                    self._return_or_reconstruct(existing),
                )
            observed_version = view.stream_versions.get(command.target_stream_id, 0)
            prepared_payload: dict[str, Any] | VerifiedReleasePublication | None = None
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
                    return self._write_receipt(command, rejected)
                if self.authority_resolver is None:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "release_publication_authorizer_unavailable",
                        "Release publication requires the canonical authority resolver.",
                    )
                    return self._write_receipt(command, rejected)
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
                    return self._write_receipt(command, rejected)
                except ArsError as exc:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "release_publication_unauthorized",
                        str(exc),
                    )
                    return self._write_receipt(command, rejected)
                if observed_version > 0:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "release_decision_already_published",
                        "The canonical release decision stream is already published.",
                    )
                    return self._write_receipt(command, rejected)
            if observed_version != command.expected_stream_version:
                receipt = Receipt(
                    status="conflict",
                    command_id=command.command_id,
                    payload_hash=command.payload_hash,
                    event_batch_id=None,
                    observed_stream_version=observed_version,
                    reason_code="stream_version_conflict",
                )
                return self._write_receipt(command, receipt)
            if command.envelope["command_type"] in _SCOPE_COMMAND_TYPES:
                prepared = self._prepare_scope_command(
                    command,
                    snapshot,
                    observed_version,
                )
                if isinstance(prepared, Receipt):
                    return self._write_receipt(command, prepared)
                prepared_payload = prepared
            elif command.envelope["command_type"] in _TASK_REVISION_COMMAND_TYPES:
                prepared = self._prepare_task_command(
                    command,
                    snapshot,
                    observed_version,
                    command_schema=command_schema,
                )
                if isinstance(prepared, Receipt):
                    return self._write_receipt(command, prepared)
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
                    return self._write_receipt(command, rejected)
            elif command.envelope["command_type"] in _SCOPED_AUTHORITY_ADMIN_COMMAND_TYPES:
                try:
                    if command.envelope["command_type"] == "ActivateAuthorityGrant":
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
                    raise
                except ConflictError:
                    raise
                except ArsError as exc:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        "scoped_authority_administration_unauthorized",
                        str(exc),
                    )
                    return self._write_receipt(command, rejected)
            event = self._build_event(
                command,
                prepared_payload,
                command_schema=command_schema,
            )
            if isinstance(prepared_payload, VerifiedReleasePublication):
                ledger_receipt = release_append(
                    self.ledger,
                    event,
                    lambda allocated: prepared_payload.payload_for(allocated.event_id),
                    snapshot=snapshot,
                )
            else:
                ledger_receipt = self.ledger.append([event], snapshot=snapshot)
            updated = self.ledger.snapshot()
            view.extend(updated.events[len(snapshot.events) :], updated.fingerprint)
            accepted = Receipt(
                status="accepted",
                command_id=command.command_id,
                payload_hash=command.payload_hash,
                event_batch_id=ledger_receipt["event_batch_id"],
                observed_stream_version=ledger_receipt["resulting_stream_versions"][command.target_stream_id],
            )
            return self._write_receipt(command, accepted)

    @contextmanager
    def _submission_lock(self, command: Command):
        """Serialize release retries while preserving fail-fast legacy locks."""
        identity = {"command_id": command.command_id}
        path = self.control_root / "runtime" / "writer.lock"
        deadline = self._monotonic() + self.release_lock_timeout_seconds
        while True:
            lock = WriterLock(path, identity)
            try:
                lock.__enter__()
            except ConflictError:
                if command.envelope["command_type"] != "PublishReleaseGateDecision" or self._monotonic() >= deadline:
                    raise
                self._lock_wait(0.01)
                continue
            break
        try:
            yield
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
        resolver = self.authority_resolver
        if resolver is None:
            raise ArsError("governed operation requires authority resolver")
        with WriterLock(
            self.control_root / "runtime" / "writer.lock",
            {"command_id": new_id("command")},
        ):
            snapshot = self.ledger.snapshot()
            replay(snapshot.events, schema_registry=self.schemas)
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

    def _scoped_authority_receipt(self, command: Command) -> Receipt | None:
        command_type = command.envelope["command_type"]
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
        self._reconcile_scoped_authority_receipt(command, receipt)
        if command.command_id == receipt.command_id:
            return receipt
        if self.receipts.load(command.command_id) is not None:
            raise ConflictError("command ID conflicts with stored receipt")
        if any(event.get("command_id") == command.command_id for event in self.ledger.snapshot().events):
            raise ConflictError("command ID conflicts with committed command")
        return receipt

    def _reconcile_scoped_authority_receipt(self, command: Command, receipt: Receipt) -> None:
        scope = self._authority_scope(command)
        snapshot = self.ledger.snapshot()
        replay(snapshot.events, schema_registry=self.schemas)
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
            expected_event_type = (
                "ReleaseGateDecisionPublished"
                if command.envelope["command_type"] == "PublishReleaseGateDecision"
                else (
                    "AuthorityGrantActivated"
                    if command.envelope["command_type"] == "ActivateAuthorityGrant"
                    else "AuthorityGrantRevoked"
                )
            )
            if (
                len(matching) != 1
                or matching[0].get("event_type") != expected_event_type
                or matching[0].get("command_id") != receipt.command_id
                or matching[0].get("command_payload_hash") != receipt.payload_hash
                or matching[0].get("stream_id") != command.target_stream_id
                or matching[0].get("stream_version") != command.expected_stream_version + 1
                or receipt.observed_stream_version != matching[0].get("stream_version")
                or matching[0].get("project_id") != self.ledger.project_id
            ):
                raise IntegrityError("scoped accepted receipt does not match canonical ledger")
        elif scoped_events:
            raise IntegrityError("scoped terminal receipt conflicts with canonical ledger")
        stored = self.receipts.load(receipt.command_id)
        if stored is None:
            self.receipts.write(receipt)
        elif stored != receipt:
            raise IntegrityError("scoped index does not match stored receipt")

    def _write_receipt(self, command: Command, receipt: Receipt) -> Receipt:
        command_type = command.envelope["command_type"]
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
            self._view = _CommandView.from_snapshot(snapshot, self.schemas)
        return self._view

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
        return self.receipts.write(receipt)

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
        elif command_type == "ClaimDispatch":
            event_type = "DispatchClaimed"
            payload = {"attempt_id": new_id("attempt")}
        elif command_type == "SupersedeTask":
            if prepared_payload is None:
                raise IntegrityError("SupersedeTask requires prepared graph payload")
            event_type = "TaskSuperseded"
            payload = prepared_payload
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
        elif command_type == "ActivateAuthorityGrant":
            if prepared_payload is None:
                raise IntegrityError("ActivateAuthorityGrant requires prepared payload")
            event_type = "AuthorityGrantActivated"
            payload = prepared_payload
        elif command_type == "RevokeIssuedAuthorityGrant":
            if prepared_payload is None:
                raise IntegrityError("RevokeIssuedAuthorityGrant requires prepared payload")
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
            "occurred_at": None,
        }
        return envelope if payload is None else {**envelope, "payload": payload}

    def _prepare_release_publication(
        self,
        command: Command,
    ) -> VerifiedReleasePublication:
        evidence = self.release_publication_evidence
        if evidence is None:
            raise PublicationEvidenceError("release publication evidence resolver is unavailable")
        request = ReleasePublicationRequest.from_dict(command.envelope["payload"])
        resolved = self.authority_resolver.resolve(
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
        resolver = self.authority_resolver
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
        resolver = self.authority_resolver
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
        grant_value = payload.get("new_grant")
        try:
            grant = ScopedAuthorityGrant.from_dict(grant_value)
        except ValueError as exc:
            raise ArsError("scoped authority grant invalid") from exc
        if grant.authority_grant_id != command.target_stream_id or grant.canonical_sha256 != payload.get(
            "new_grant_sha256"
        ):
            raise ArsError("scoped authority activation target mismatch")
        schema_identity = self.schemas.resolve_identity(
            "ars://core/scoped-authority-grant",
            "2.0.0",
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
            schema_version="2.0.0",
            expected_sha256=schema_identity.sha256,
        )
        decision = resolver.verify_owner_administration_decision(
            str(payload.get("administration_decision_id", "")),
            str(payload.get("administration_decision_sha256", "")),
            action="activate_authority_grant",
            target_grant_id=grant.authority_grant_id,
            target_grant_sha256=grant.canonical_sha256,
            target_grant_schema_sha256=schema_identity.sha256,
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

    def _prepare_issued_authority_revocation(
        self,
        command: Command,
        observed_version: int,
    ) -> dict[str, Any]:
        resolver = self.authority_resolver
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
            subject_scope=target.subject_scope,
            effective_at=target.effective_at,
            expires_at=target.expires_at,
            owner_actor_id=command.actor_id,
            now=self.clock(),
        )
        if decision.record_id not in command.envelope.get("evidence_refs", []):
            raise ArsError("owner authority administration decision evidence missing")
        return {
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
