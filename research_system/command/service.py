from __future__ import annotations

import json
import sys
import time

from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_system.command.models import Command, Receipt
from research_system.errors import (
    ArsError,
    ConflictError,
    IdempotencyConflictError,
    IntegrityError,
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
from research_system.schema_registry import SchemaRegistry
from research_system.store.ledger import EventDraft, EventLedger, LedgerSnapshot
from research_system.store.lock import WriterLock
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore


_RELEASE_DRAFT_CAPABILITY = object()


@dataclass
class _CommandView:
    fingerprint: tuple[tuple[str, int, int], ...]
    batches_by_command_id: dict[str, list[dict[str, Any]]]
    batches_by_scope: dict[tuple[str, str, str, str], list[dict[str, Any]]]
    stream_versions: dict[str, int]

    @classmethod
    def from_snapshot(
        cls,
        snapshot: LedgerSnapshot,
        schemas: SchemaRegistry,
    ) -> _CommandView:
        replay(snapshot.events, schema_registry=schemas)
        view = cls(snapshot.fingerprint, {}, {}, dict(snapshot.stream_versions))
        batches: dict[str, list[dict[str, Any]]] = {}
        for event in snapshot.events:
            batches.setdefault(event['transaction_id'], []).append(event)
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
            batches.setdefault(event['transaction_id'], []).append(event)
            self.stream_versions[event['stream_id']] = event['stream_version']
        for batch in batches.values():
            self._index_batch(batch)
        self.fingerprint = fingerprint

    def _index_batch(self, batch: list[dict[str, Any]]) -> None:
        first = batch[0]
        self.batches_by_command_id[first['command_id']] = batch
        self.batches_by_scope[
            (
                first['actor_id'],
                first['authority_grant_id'],
                first['command_type'],
                first['idempotency_key'],
            )
        ] = batch


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
            raise ValueError('release lock timeout must be positive')
        self.release_lock_timeout_seconds = release_lock_timeout_seconds
        self._monotonic = monotonic or time.monotonic
        self._lock_wait = lock_wait or time.sleep
        self._release_draft_factory = ledger._bind_command_service_release_factory(
            _RELEASE_DRAFT_CAPABILITY
        )
        self._view: _CommandView | None = None
        self.deletion_manifest_authorizer: Callable[
            [dict[str, Any], str, str],
            dict[str, Any],
        ] | None = None
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

    def submit(self, envelope: dict[str, Any]) -> Receipt:
        """Validate WP1 integrity controls; authorization remains downstream."""
        self.schemas.validate('ars://core/command', envelope)
        if envelope.get('command_type') == 'RevokeAuthorityGrant':
            self.schemas.validate(
                'ars://core/command/RevokeAuthorityGrant/payload',
                envelope.get('payload'),
            )
        elif envelope.get('command_type') == 'PublishReleaseGateDecision':
            self.schemas.validate(
                'ars://evals/release-publication-request',
                envelope.get('payload'),
            )
            ReleasePublicationRequest.from_dict(envelope['payload'])
        command = Command(dict(envelope))
        with self._submission_lock(command):
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
            existing = self._matching_committed(command, view)
            if existing is not None:
                return self._write_receipt(
                    command,
                    self._return_or_reconstruct(existing),
                )
            observed_version = view.stream_versions.get(command.target_stream_id, 0)
            prepared_payload: dict[str, Any] | VerifiedReleasePublication | None = None
            if (
                command.envelope['command_type']
                == 'PublishReleaseGateDecision'
            ):
                request = ReleasePublicationRequest.from_dict(
                    command.envelope['payload']
                )
                if (
                    request.project_id != self.ledger.project_id
                    or request.release_decision_id != command.target_stream_id
                    or request.publication_authority_grant_id
                    != command.envelope['authority_grant_id']
                    or request.idempotency_key != command.idempotency_key
                    or set(command.envelope['evidence_refs'])
                    != {
                        request.evaluation_runs_manifest_ref,
                        request.control_binding_ref,
                    }
                ):
                    rejected = self._rejected(
                        command,
                        observed_version,
                        'release_publication_evidence_mismatch',
                        'Release publication envelope bindings do not match.',
                    )
                    return self._write_receipt(command, rejected)
                if self.authority_resolver is None:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        'release_publication_authorizer_unavailable',
                        'Release publication requires the canonical authority resolver.',
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
                        'release_publication_evidence_mismatch',
                        str(exc),
                    )
                    return self._write_receipt(command, rejected)
                except ArsError as exc:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        'release_publication_unauthorized',
                        str(exc),
                    )
                    return self._write_receipt(command, rejected)
                if observed_version > 0:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        'release_decision_already_published',
                        'The canonical release decision stream is already published.',
                    )
                    return self._write_receipt(command, rejected)
            if observed_version != command.expected_stream_version:
                receipt = Receipt(
                        status='conflict',
                        command_id=command.command_id,
                        payload_hash=command.payload_hash,
                        event_batch_id=None,
                        observed_stream_version=observed_version,
                        reason_code='stream_version_conflict',
                    )
                return self._write_receipt(command, receipt)
            if command.envelope['command_type'] == 'SupersedeTask':
                prepared = self._prepare_supersession(
                    command, snapshot, observed_version
                )
                if isinstance(prepared, Receipt):
                    return self.receipts.write(prepared)
                prepared_payload = prepared
            elif command.envelope['command_type'] == 'RevokeAuthorityGrant':
                try:
                    prepared_payload = self._prepare_authority_revocation(
                        command, observed_version
                    )
                except IntegrityError:
                    raise
                except ArsError as exc:
                    rejected = self._rejected(
                        command,
                        observed_version,
                        'authority_revocation_unauthorized',
                        str(exc),
                    )
                    return self._write_receipt(command, rejected)
            event = self._build_event(command, prepared_payload)
            ledger_receipt = self.ledger.append([event], snapshot=snapshot)
            updated = self.ledger.snapshot()
            view.extend(updated.events[len(snapshot.events) :], updated.fingerprint)
            accepted = Receipt(
                status='accepted',
                command_id=command.command_id,
                payload_hash=command.payload_hash,
                event_batch_id=ledger_receipt['event_batch_id'],
                observed_stream_version=ledger_receipt[
                    'resulting_stream_versions'
                ][command.target_stream_id],
            )
            return self._write_receipt(command, accepted)

    @contextmanager
    def _submission_lock(self, command: Command):
        """Serialize release retries while preserving fail-fast legacy locks."""
        identity = {'command_id': command.command_id}
        path = self.control_root / 'runtime' / 'writer.lock'
        deadline = self._monotonic() + self.release_lock_timeout_seconds
        while True:
            lock = WriterLock(path, identity)
            try:
                lock.__enter__()
            except ConflictError:
                if (
                    command.envelope['command_type']
                    != 'PublishReleaseGateDecision'
                    or self._monotonic() >= deadline
                ):
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
            raise ArsError('governed operation requires authority resolver')
        with WriterLock(
            self.control_root / 'runtime' / 'writer.lock',
            {'command_id': new_id('command')},
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
            command.envelope['authority_grant_id'],
            command.envelope['command_type'],
            command.idempotency_key,
        )

    def _scoped_authority_receipt(self, command: Command) -> Receipt | None:
        command_type = command.envelope['command_type']
        if command_type not in {
            'RevokeAuthorityGrant',
            'PublishReleaseGateDecision',
        }:
            return None
        hash_field = (
            'publication_authority_sha256'
            if command_type == 'PublishReleaseGateDecision'
            else 'authority_grant_sha256'
        )
        grant_hash = command.envelope.get('payload', {}).get(hash_field)
        if not isinstance(grant_hash, str):
            return None
        publication = command_type == 'PublishReleaseGateDecision'
        try:
            receipt = self.receipts.load_scoped(
                self._authority_scope(command),
                command.payload_hash,
                grant_hash,
                command.expected_stream_version,
                project_id=self.ledger.project_id if publication else None,
                target_stream_id=(
                    command.target_stream_id if publication else None
                ),
            )
        except IdempotencyConflictError:
            if not publication:
                raise
            conflict = Receipt(
                status='conflict',
                command_id=command.command_id,
                payload_hash=command.payload_hash,
                event_batch_id=None,
                observed_stream_version=self.ledger.snapshot().stream_versions.get(
                    command.target_stream_id,
                    0,
                ),
                reason_code='idempotency_conflict',
            )
            return self.receipts.write(conflict)
        if receipt is None:
            return receipt
        self._reconcile_scoped_authority_receipt(command, receipt)
        if command.command_id == receipt.command_id:
            return receipt
        if self.receipts.load(command.command_id) is not None:
            raise ConflictError('command ID conflicts with stored receipt')
        if any(
            event.get('command_id') == command.command_id
            for event in self.ledger.snapshot().events
        ):
            raise ConflictError('command ID conflicts with committed command')
        return receipt

    def _reconcile_scoped_authority_receipt(
        self, command: Command, receipt: Receipt
    ) -> None:
        scope = self._authority_scope(command)
        snapshot = self.ledger.snapshot()
        replay(snapshot.events, schema_registry=self.schemas)
        events = tuple(snapshot.events)
        scoped_events = tuple(
            event
            for event in events
            if (
                event.get('actor_id'),
                event.get('authority_grant_id'),
                event.get('command_type'),
                event.get('idempotency_key'),
            )
            == scope
        )
        if receipt.status == 'accepted':
            matching = tuple(
                event
                for event in scoped_events
                if event.get('transaction_id') == receipt.event_batch_id
            )
            expected_event_type = (
                'ReleaseGateDecisionPublished'
                if command.envelope['command_type']
                == 'PublishReleaseGateDecision'
                else 'AuthorityGrantRevoked'
            )
            if (
                len(matching) != 1
                or matching[0].get('event_type') != expected_event_type
                or matching[0].get('command_id') != receipt.command_id
                or matching[0].get('command_payload_hash') != receipt.payload_hash
                or matching[0].get('stream_id') != command.target_stream_id
                or matching[0].get('stream_version')
                != command.expected_stream_version + 1
                or receipt.observed_stream_version
                != matching[0].get('stream_version')
                or matching[0].get('project_id') != self.ledger.project_id
            ):
                raise IntegrityError(
                    'scoped accepted receipt does not match canonical ledger'
                )
        elif scoped_events:
            raise IntegrityError(
                'scoped terminal receipt conflicts with canonical ledger'
            )
        stored = self.receipts.load(receipt.command_id)
        if stored is None:
            self.receipts.write(receipt)
        elif stored != receipt:
            raise IntegrityError('scoped index does not match stored receipt')

    def _write_receipt(self, command: Command, receipt: Receipt) -> Receipt:
        command_type = command.envelope['command_type']
        if command_type not in {
            'RevokeAuthorityGrant',
            'PublishReleaseGateDecision',
        }:
            return self.receipts.write(receipt)
        publication = command_type == 'PublishReleaseGateDecision'
        hash_field = (
            'publication_authority_sha256'
            if publication
            else 'authority_grant_sha256'
        )
        grant_hash = command.envelope['payload'].get(hash_field)
        if not isinstance(grant_hash, str):
            return self.receipts.write(receipt)
        return self.receipts.write_scoped(
            self._authority_scope(command),
            grant_hash,
            command.expected_stream_version,
            receipt,
            project_id=self.ledger.project_id if publication else None,
            target_stream_id=(
                command.target_stream_id if publication else None
            ),
        )

    def _stored_rejected_receipt(self, command: Command) -> Receipt | None:
        """Return an idempotent rejected receipt while holding WriterLock."""
        stored = self.receipts.load(command.command_id)
        if stored is None or stored.status != 'rejected':
            return None
        if stored.payload_hash != command.payload_hash:
            raise ConflictError('command ID conflicts with stored receipt')
        if (
            stored.command_id != command.command_id
            or stored.event_batch_id is not None
            or not stored.reason_code
            or not stored.explanation
            or not stored.unmet_preconditions
        ):
            raise IntegrityError('stored rejected receipt is inconsistent')
        return stored

    def _rejected(
        self,
        command: Command,
        observed_version: int,
        reason_code: str,
        explanation: str,
    ) -> Receipt:
        return Receipt(
            status='rejected',
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
        directory = self.control_root / 'objects' / 'task' / task_id
        matches = sorted(directory.glob(f'{revision:08d}-*.json'))
        if not matches:
            return None
        if len(matches) != 1:
            raise IntegrityError('duplicate immutable Task revision')
        try:
            value = json.loads(matches[0].read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise IntegrityError('invalid immutable Task revision') from exc
        if not isinstance(value, dict):
            raise IntegrityError('Task revision object must be a mapping')
        return value

    @staticmethod
    def _revision_graph(
        snapshot: LedgerSnapshot,
    ) -> tuple[
        dict[str, int],
        dict[tuple[str, int], tuple[str, int]],
    ]:
        current: dict[str, int] = {}
        edges: dict[tuple[str, int], tuple[str, int]] = {}
        for event in snapshot.events:
            if event['event_type'] == 'TaskCreated':
                revision = int(event.get('payload', {}).get('revision', 1))
                current.setdefault(event['stream_id'], revision)
            elif event['event_type'] == 'TaskSuperseded':
                payload = event['payload']
                source = (
                    str(payload['source_task_id']),
                    int(payload['source_task_revision']),
                )
                replacement = (
                    str(payload['replacement_task_id']),
                    int(payload['replacement_task_revision']),
                )
                if source in edges:
                    raise IntegrityError('Task revision has multiple supersession edges')
                edges[source] = replacement
                if source[0] == replacement[0]:
                    current[source[0]] = replacement[1]
        return current, edges

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
                raise IntegrityError('supersession lineage cycle')
            seen.add(predecessor)
            lineage.insert(0, predecessor)
        lineage.append(replacement)
        return [
            {'task_id': task_id, 'revision': revision}
            for task_id, revision in lineage
        ]

    def _prepare_supersession(
        self,
        command: Command,
        snapshot: LedgerSnapshot,
        observed_version: int,
    ) -> dict[str, Any] | Receipt:
        """Validate a revision-qualified edge from one committed snapshot."""
        payload = command.envelope['payload']
        exact_fields = {
            'replacement_task_id',
            'replacement_task_revision',
            'supersession_scope',
            'continuing_consumers',
        }
        if set(payload) != exact_fields:
            return self._rejected(
                command,
                observed_version,
                'invalid_supersession_payload',
                'SupersedeTask payload fields are not exact; caller lineage is forbidden.',
            )
        replacement_id = payload['replacement_task_id']
        replacement_revision = payload['replacement_task_revision']
        scope = payload['supersession_scope']
        consumers = payload['continuing_consumers']
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
                'invalid_supersession_payload',
                'SupersedeTask requires positive revisions and non-empty exact sets.',
            )

        current, edges = self._revision_graph(snapshot)
        source_id = command.target_stream_id
        source_revision = current.get(source_id)
        if source_revision is None:
            return self._rejected(
                command,
                observed_version,
                'source_revision_missing',
                'The source Task revision is absent from committed events.',
            )
        source = (source_id, source_revision)
        replacement = (replacement_id, replacement_revision)
        if source in edges:
            return self._rejected(
                command,
                observed_version,
                'source_revision_terminal',
                'The source Task revision is already terminal.',
            )
        if self._reaches(edges, replacement, source):
            return self._rejected(
                command,
                observed_version,
                'supersession_cycle',
                'The proposed replacement reaches the source revision.',
            )
        if replacement in edges:
            return self._rejected(
                command,
                observed_version,
                'replacement_revision_terminal',
                'The replacement Task revision is already terminal.',
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
                'replacement_revision_missing',
                'The replacement must be an existing immutable Task revision.',
            )
        if source_object.get('task_type', 'task') != replacement_object.get(
            'task_type', 'task'
        ):
            return self._rejected(
                command,
                observed_version,
                'replacement_revision_incompatible',
                'The replacement Task revision is type-incompatible.',
            )
        if replacement_id == source_id:
            if replacement_revision <= source_revision:
                return self._rejected(
                    command,
                    observed_version,
                    'replacement_revision_stale',
                    'A same-Task replacement must be a higher revision.',
                )
        elif current.get(replacement_id) != replacement_revision:
            return self._rejected(
                command,
                observed_version,
                'replacement_revision_stale',
                'The replacement is not the current Task revision.',
            )
        expected_consumers = source_object.get('continuing_consumers')
        if expected_consumers is not None and set(consumers) != set(expected_consumers):
            return self._rejected(
                command,
                observed_version,
                'continuing_consumers_mismatch',
                'Continuing consumers must equal the source revision contract.',
            )
        return {
            'source_task_id': source_id,
            'source_task_revision': source_revision,
            'replacement_task_id': replacement_id,
            'replacement_task_revision': replacement_revision,
            'supersession_scope': list(scope),
            'continuing_consumers': sorted(consumers),
            'actor_id': command.actor_id,
            'authority_grant_id': command.envelope['authority_grant_id'],
            'lineage': self._derived_lineage(edges, source, replacement),
        }
    def _stored_conflict_receipt(self, command: Command) -> Receipt | None:
        stored = self.receipts.load(command.command_id)
        if stored is None or stored.status != 'conflict':
            return None
        if stored.payload_hash != command.payload_hash:
            raise ConflictError('command ID conflicts with stored receipt')
        if (
            stored.command_id != command.command_id
            or stored.event_batch_id is not None
            or stored.reason_code
            not in {'stream_version_conflict', 'idempotency_conflict'}
        ):
            raise IntegrityError('stored conflict receipt is inconsistent')
        return stored

    def _view_for(self, snapshot: LedgerSnapshot) -> _CommandView:
        if self._view is None or self._view.fingerprint != snapshot.fingerprint:
            self._view = _CommandView.from_snapshot(snapshot, self.schemas)
        return self._view

    def _matching_committed(
        self, command: Command, view: _CommandView
    ) -> list[dict[str, Any]] | None:
        scope = (
            command.actor_id,
            command.envelope['authority_grant_id'],
            command.envelope['command_type'],
            command.idempotency_key,
        )
        scoped = view.batches_by_scope.get(scope)
        if scoped is not None:
            first = scoped[0]
            same_submission = (
                first.get('command_payload_hash') == command.payload_hash
                and first.get('stream_id') == command.target_stream_id
                and first.get('stream_version')
                == command.expected_stream_version + 1
            )
            if same_submission:
                return list(scoped)
            raise ConflictError('idempotency key conflicts with committed command')
        identified = view.batches_by_command_id.get(command.command_id)
        if identified is not None:
            raise ConflictError('command ID conflicts with committed command')
        return None

    def _return_or_reconstruct(self, events: list[dict[str, Any]]) -> Receipt:
        receipt = Receipt(
            status='accepted',
            command_id=events[0]['command_id'],
            payload_hash=events[0]['command_payload_hash'],
            event_batch_id=events[0]['transaction_id'],
            observed_stream_version=max(
                event['stream_version']
                for event in events
                if event['stream_id'] == events[0]['stream_id']
            ),
        )
        stored = self.receipts.load(receipt.command_id)
        if stored is not None:
            if stored != receipt:
                raise IntegrityError('stored receipt does not match committed batch')
            return stored
        return self.receipts.write(receipt)

    def _build_event(
        self,
        command: Command,
        prepared_payload: dict[str, Any] | VerifiedReleasePublication | None = None,
    ) -> dict[str, Any] | EventDraft:
        command_type = command.envelope['command_type']
        if command_type == 'CreateTask':
            self.objects.write(
                'task',
                command.target_stream_id,
                1,
                command.envelope['payload'],
            )
            event_type = 'TaskCreated'
            payload = command.envelope['payload']
        elif command_type == 'ClaimDispatch':
            event_type = 'DispatchClaimed'
            payload = {'attempt_id': new_id('attempt')}
        elif command_type == 'SupersedeTask':
            if prepared_payload is None:
                raise IntegrityError('SupersedeTask requires prepared graph payload')
            event_type = 'TaskSuperseded'
            payload = prepared_payload
        elif command_type == 'VerifyEvidenceDeletion':
            authorizer = self.deletion_manifest_authorizer
            if authorizer is None:
                raise ArsError(
                    'VerifyEvidenceDeletion requires a trusted deletion '
                    'manifest authorizer'
                )
            payload = authorizer(
                command.envelope['payload'],
                command.actor_id,
                command.envelope['authority_grant_id'],
            )
            if payload.get('status') != 'verified':
                raise ArsError('deletion manifest authorizer did not verify')
            event_type = 'EvidenceDeletionVerified'
        elif command_type == 'RevokeAuthorityGrant':
            if prepared_payload is None:
                raise IntegrityError('RevokeAuthorityGrant requires prepared payload')
            event_type = 'AuthorityGrantRevoked'
            payload = prepared_payload
        elif command_type == 'PublishReleaseGateDecision':
            if not isinstance(prepared_payload, VerifiedReleasePublication):
                raise IntegrityError(
                    'PublishReleaseGateDecision requires verified publication'
                )
            event_type = 'ReleaseGateDecisionPublished'
            payload = None
        else:
            raise ArsError(f'unsupported command type: {command_type}')
        envelope = {
            'event_type': event_type,
            'stream_id': command.target_stream_id,
            'command_id': command.command_id,
            'command_type': command_type,
            'actor_id': command.actor_id,
            'authority_grant_id': command.envelope['authority_grant_id'],
            'idempotency_key': command.idempotency_key,
            'command_payload_hash': command.payload_hash,
            'correlation_id': command.envelope['correlation_id'],
            'causation_id': command.envelope['causation_id'],
            'schema_id': f'ars://core/event/{event_type}',
            'schema_version': '1.0.0',
            'occurred_at': None,
        }
        if command_type == 'PublishReleaseGateDecision':
            return self._release_draft_factory(
                envelope,
                lambda allocated: prepared_payload.payload_for(
                    allocated.event_id
                ),
            )
        return {**envelope, 'payload': payload}

    def _prepare_release_publication(
        self,
        command: Command,
    ) -> VerifiedReleasePublication:
        evidence = self.release_publication_evidence
        if evidence is None:
            raise PublicationEvidenceError(
                'release publication evidence resolver is unavailable'
            )
        request = ReleasePublicationRequest.from_dict(command.envelope['payload'])
        resolved = self.authority_resolver.resolve(
            request.publication_authority_grant_id,
            command.actor_id,
            'PublishReleaseGateDecision',
            self.ledger.project_id,
            'release_gate_decision',
            command.target_stream_id,
            self.clock(),
        )
        if (
            resolved.authority_grant_sha256
            != request.publication_authority_sha256
        ):
            raise ArsError('publication authority hash mismatch')
        verified = verify_release_publication(request, evidence, self.schemas)
        if (
            verified.publication_authority_grant_id
            != command.envelope['authority_grant_id']
            or verified.publication_authority_sha256
            != resolved.authority_grant_sha256
        ):
            raise ArsError('publication authority evidence mismatch')
        return verified

    def _prepare_authority_revocation(
        self, command: Command, observed_version: int
    ) -> dict[str, Any]:
        resolver = self.authority_resolver
        if resolver is None:
            raise ArsError('RevokeAuthorityGrant requires authority resolver')
        payload = command.envelope['payload']
        fields = {
            'project_id',
            'target_grant_id',
            'target_grant_sha256',
            'authority_grant_sha256',
            'reason',
        }
        if set(payload) != fields or not isinstance(payload.get('reason'), str) or not payload['reason']:
            raise ArsError('invalid authority revocation payload')
        if payload['project_id'] != self.ledger.project_id:
            raise ArsError('authority revocation project mismatch')
        if payload['target_grant_id'] != command.target_stream_id:
            raise ArsError('authority revocation target mismatch')
        now = self.clock()
        authorizing = resolver.resolve(
            command.envelope['authority_grant_id'],
            command.actor_id,
            'RevokeAuthorityGrant',
            self.ledger.project_id,
            'authority_grant',
            command.target_stream_id,
            now,
        )
        target = resolver.grant_at(command.target_stream_id, now)
        if authorizing.authority_grant_sha256 != payload['authority_grant_sha256']:
            raise ArsError('authority revocation authorizing hash mismatch')
        if target.authority_grant_sha256 != payload['target_grant_sha256']:
            raise ArsError('authority revocation target hash mismatch')
        if observed_version != 1:
            raise ArsError('authority revocation requires active version 1')
        return {
            'project_id': self.ledger.project_id,
            'target_grant_id': target.authority_grant_id,
            'target_grant_sha256': target.authority_grant_sha256,
            'authorizing_grant_id': authorizing.authority_grant_id,
            'authorizing_grant_sha256': authorizing.authority_grant_sha256,
            'reason': payload['reason'],
        }
