from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Receipt
from research_system.errors import ConflictError, IdempotencyConflictError


_RECEIPT_FIELDS = {
    'schema_id',
    'schema_version',
    'command_id',
    'status',
    'payload_hash',
    'outcome',
}
_INDEX_FIELDS = {
    'schema_id',
    'schema_version',
    'scope',
    'payload_hash',
    'authority_grant_sha256',
    'expected_stream_version',
    'receipt',
}
_PUBLICATION_INDEX_FIELDS = _INDEX_FIELDS | {'project_id', 'target_stream_id'}


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in '0123456789abcdef' for character in value)
    )


def _validated_receipt(record: object) -> Receipt:
    if not isinstance(record, dict) or set(record) != _RECEIPT_FIELDS:
        raise ConflictError('invalid idempotency index receipt')
    outcome = record.get('outcome')
    status = record.get('status')
    expected_outcome = {
        'event_batch_id',
        'observed_stream_version',
        'reason_code',
    }
    if status == 'rejected':
        expected_outcome |= {'explanation', 'unmet_preconditions'}
    if (
        record.get('schema_id') != 'ars://core/receipt'
        or record.get('schema_version') != '1.0.0'
        or status not in {'accepted', 'duplicate', 'rejected', 'conflict'}
        or not isinstance(record.get('command_id'), str)
        or not _is_sha256(record.get('payload_hash'))
        or not isinstance(outcome, dict)
        or set(outcome) != expected_outcome
        or not isinstance(outcome.get('observed_stream_version'), int)
        or isinstance(outcome.get('observed_stream_version'), bool)
        or outcome['observed_stream_version'] < 0
        or not (
            outcome.get('event_batch_id') is None
            or isinstance(outcome.get('event_batch_id'), str)
        )
        or not (
            outcome.get('reason_code') is None
            or isinstance(outcome.get('reason_code'), str)
        )
    ):
        raise ConflictError('invalid idempotency index receipt')
    if status == 'rejected' and (
        outcome.get('event_batch_id') is not None
        or not isinstance(outcome.get('reason_code'), str)
        or not outcome['reason_code']
        or not isinstance(outcome.get('explanation'), str)
        or not outcome['explanation']
        or not isinstance(outcome.get('unmet_preconditions'), list)
        or not outcome['unmet_preconditions']
        or not all(
            isinstance(item, str) and item
            for item in outcome['unmet_preconditions']
        )
        or len(outcome['unmet_preconditions'])
        != len(set(outcome['unmet_preconditions']))
    ):
        raise ConflictError('invalid idempotency index receipt')
    if status == 'accepted' and (
        not isinstance(outcome.get('event_batch_id'), str)
        or not outcome['event_batch_id']
        or outcome.get('reason_code') is not None
        or outcome['observed_stream_version'] < 1
    ):
        raise ConflictError('invalid idempotency index receipt')
    if status == 'conflict' and (
        outcome.get('event_batch_id') is not None
        or outcome.get('reason_code') != 'stream_version_conflict'
    ):
        raise ConflictError('invalid idempotency index receipt')
    if status == 'duplicate':
        raise ConflictError('invalid idempotency index receipt')
    return _receipt_from_record(record)


def _receipt_record(receipt: Receipt) -> dict[str, Any]:
    outcome: dict[str, Any] = {
        'event_batch_id': receipt.event_batch_id,
        'observed_stream_version': receipt.observed_stream_version,
        'reason_code': receipt.reason_code,
    }
    if receipt.status == 'rejected':
        outcome['explanation'] = receipt.explanation
        outcome['unmet_preconditions'] = list(receipt.unmet_preconditions)
    return {
        'schema_id': 'ars://core/receipt',
        'schema_version': '1.0.0',
        'command_id': receipt.command_id,
        'status': receipt.status,
        'payload_hash': receipt.payload_hash,
        'outcome': outcome,
    }


def _receipt_from_record(record: dict[str, Any]) -> Receipt:
    outcome = record['outcome']
    return Receipt(
        status=record['status'],
        command_id=record['command_id'],
        payload_hash=record['payload_hash'],
        event_batch_id=outcome.get('event_batch_id'),
        observed_stream_version=outcome['observed_stream_version'],
        reason_code=outcome.get('reason_code'),
        explanation=outcome.get('explanation'),
        unmet_preconditions=tuple(outcome.get('unmet_preconditions', ())),
    )


class ReceiptStore:
    def __init__(self, control_root: Path) -> None:
        self.receipts_root = control_root / 'receipts'
        self.runtime_root = control_root / 'runtime'
        self.receipts_root.mkdir(parents=True, exist_ok=True)
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.index_root = self.receipts_root / 'idempotency'
        self.index_root.mkdir(parents=True, exist_ok=True)

    def load(self, command_id: str) -> Receipt | None:
        path = self.receipts_root / f'{command_id}.json'
        if not path.exists():
            return None
        return _receipt_from_record(json.loads(path.read_text(encoding='utf-8')))

    def write(self, receipt: Receipt) -> Receipt:
        target = self.receipts_root / f'{receipt.command_id}.json'
        data = canonical_bytes(_receipt_record(receipt))
        if target.exists():
            if target.read_bytes() == data:
                return receipt
            raise ConflictError(f'receipt already exists: {receipt.command_id}')
        temporary = self.runtime_root / f'{receipt.command_id}.receipt.tmp'
        if not temporary.exists() or temporary.read_bytes() != data:
            with temporary.open('wb') as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        self._after_temp_fsync(temporary)
        self._publish(temporary, target)
        self._after_publish(target)
        return receipt

    def load_scoped(
        self,
        scope: tuple[str, str, str, str],
        payload_hash: str,
        authority_grant_sha256: str,
        expected_stream_version: int,
        *,
        project_id: str | None = None,
        target_stream_id: str | None = None,
    ) -> Receipt | None:
        """Load an exact authority-scoped idempotency outcome.

        Args:
            scope: Actor, grant, command, and idempotency-key tuple.
            payload_hash: Canonical command payload digest required for retry.
            authority_grant_sha256: Exact authorizing grant digest.
            expected_stream_version: Stream version bound into the submission.
            project_id: Optional project binding paired with target stream.
            target_stream_id: Optional target binding paired with project.

        Returns:
            The validated stored receipt, or ``None`` when no index exists.

        Raises:
            ConflictError: If stored index data is malformed or conflicts.
            ValueError: If only one target binding is supplied.
        """
        if (project_id is None) != (target_stream_id is None):
            raise ValueError('project and target idempotency bindings are paired')
        key = sha256_hex(canonical_bytes(list(scope)))
        path = self.index_root / f'{key}.json'
        if not path.exists():
            return None
        try:
            record = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConflictError('invalid idempotency index') from exc
        publication_index = (
            isinstance(record, dict)
            and set(record) == _PUBLICATION_INDEX_FIELDS
        )
        legacy_index = isinstance(record, dict) and set(record) == _INDEX_FIELDS
        if (
            not isinstance(record, dict)
            or not (publication_index or legacy_index)
            or record.get('schema_id') != 'ars://core/authority-receipt-index'
            or record.get('schema_version')
            != ('1.2.0' if publication_index else '1.1.0')
            or not isinstance(record.get('scope'), list)
            or len(record['scope']) != 4
            or not all(isinstance(item, str) and item for item in record['scope'])
            or not _is_sha256(record.get('payload_hash'))
            or not _is_sha256(record.get('authority_grant_sha256'))
            or not isinstance(record.get('expected_stream_version'), int)
            or isinstance(record.get('expected_stream_version'), bool)
            or record['expected_stream_version'] < 0
        ):
            raise ConflictError('invalid idempotency index')
        if project_id is not None or target_stream_id is not None:
            if (
                not publication_index
                or record.get('project_id') != project_id
                or record.get('target_stream_id') != target_stream_id
            ):
                raise IdempotencyConflictError(
                    'idempotency index target mismatch'
                )
        if record.get('scope') != list(scope):
            raise ConflictError('idempotency index scope mismatch')
        if (
            record.get('payload_hash') != payload_hash
            or record.get('authority_grant_sha256') != authority_grant_sha256
        ):
            raise IdempotencyConflictError(
                'idempotency key conflicts with stored outcome'
            )
        if record['expected_stream_version'] != expected_stream_version:
            raise IdempotencyConflictError(
                'idempotency key conflicts with expected stream version'
            )
        receipt = _validated_receipt(record['receipt'])
        if receipt.payload_hash != payload_hash:
            raise ConflictError('idempotency index receipt payload mismatch')
        return receipt

    def write_scoped(
        self,
        scope: tuple[str, str, str, str],
        authority_grant_sha256: str,
        expected_stream_version: int,
        receipt: Receipt,
        *,
        project_id: str | None = None,
        target_stream_id: str | None = None,
    ) -> Receipt:
        """Atomically publish one authority-scoped idempotency outcome.

        Args:
            scope: Actor, grant, command, and idempotency-key tuple.
            authority_grant_sha256: Exact authorizing grant digest.
            expected_stream_version: Stream version bound into the submission.
            receipt: Terminal command receipt to index and persist.
            project_id: Optional project binding paired with target stream.
            target_stream_id: Optional target binding paired with project.

        Returns:
            The newly written or exact existing receipt.

        Raises:
            ConflictError: If existing or recoverable data conflicts.
            OSError: If durable publication fails.
            ValueError: If only one target binding is supplied.
        """
        key = sha256_hex(canonical_bytes(list(scope)))
        target = self.index_root / f'{key}.json'
        if (project_id is None) != (target_stream_id is None):
            raise ValueError('project and target idempotency bindings are paired')
        record = {
            'schema_id': 'ars://core/authority-receipt-index',
            'schema_version': (
                '1.2.0' if project_id is not None else '1.1.0'
            ),
            'scope': list(scope),
            'payload_hash': receipt.payload_hash,
            'authority_grant_sha256': authority_grant_sha256,
            'expected_stream_version': expected_stream_version,
            'receipt': _receipt_record(receipt),
        }
        if project_id is not None:
            record['project_id'] = project_id
            record['target_stream_id'] = target_stream_id
        data = canonical_bytes(record)
        if target.exists():
            if target.read_bytes() != data:
                existing = self.load_scoped(
                    scope,
                    receipt.payload_hash,
                    authority_grant_sha256,
                    expected_stream_version,
                    project_id=project_id,
                    target_stream_id=target_stream_id,
                )
                if existing != receipt:
                    raise ConflictError('idempotency index outcome mismatch')
            return receipt
        temporary = self.runtime_root / f'{key}.idempotency.tmp'
        if temporary.exists():
            if temporary.read_bytes() != data:
                raise ConflictError('idempotency index temporary outcome mismatch')
        else:
            with temporary.open('xb') as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        self._publish(temporary, target)
        self.write(receipt)
        return receipt

    def _after_temp_fsync(self, temporary: Path) -> None:
        pass

    def _publish(self, source: Path, target: Path) -> None:
        os.replace(source, target)

    def _after_publish(self, target: Path) -> None:
        pass
