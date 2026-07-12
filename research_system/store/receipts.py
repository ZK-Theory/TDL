from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Receipt
from research_system.errors import ConflictError


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
    ) -> Receipt | None:
        key = sha256_hex(canonical_bytes(list(scope)))
        path = self.index_root / f'{key}.json'
        if not path.exists():
            return None
        try:
            record = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConflictError('invalid idempotency index') from exc
        if record.get('scope') != list(scope):
            raise ConflictError('idempotency index scope mismatch')
        if (
            record.get('payload_hash') != payload_hash
            or record.get('authority_grant_sha256') != authority_grant_sha256
        ):
            raise ConflictError('idempotency key conflicts with stored outcome')
        return _receipt_from_record(record['receipt'])

    def write_scoped(
        self,
        scope: tuple[str, str, str, str],
        authority_grant_sha256: str,
        receipt: Receipt,
    ) -> Receipt:
        key = sha256_hex(canonical_bytes(list(scope)))
        target = self.index_root / f'{key}.json'
        record = {
            'schema_id': 'ars://core/authority-receipt-index',
            'schema_version': '1.0.0',
            'scope': list(scope),
            'payload_hash': receipt.payload_hash,
            'authority_grant_sha256': authority_grant_sha256,
            'receipt': _receipt_record(receipt),
        }
        data = canonical_bytes(record)
        if target.exists():
            if target.read_bytes() != data:
                existing = self.load_scoped(
                    scope, receipt.payload_hash, authority_grant_sha256
                )
                if existing != receipt:
                    raise ConflictError('idempotency index outcome mismatch')
            return receipt
        temporary = self.runtime_root / f'{key}.idempotency.tmp'
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
