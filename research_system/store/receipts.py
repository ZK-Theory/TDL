from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from research_system.canonical import canonical_bytes
from research_system.command.models import Receipt
from research_system.errors import ConflictError


def _receipt_record(receipt: Receipt) -> dict[str, Any]:
    return {
        'schema_id': 'ars://core/receipt',
        'schema_version': '1.0.0',
        'command_id': receipt.command_id,
        'status': receipt.status,
        'payload_hash': receipt.payload_hash,
        'outcome': {
            'event_batch_id': receipt.event_batch_id,
            'observed_stream_version': receipt.observed_stream_version,
            'reason_code': receipt.reason_code,
        },
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
    )


class ReceiptStore:
    def __init__(self, control_root: Path) -> None:
        self.receipts_root = control_root / 'receipts'
        self.runtime_root = control_root / 'runtime'
        self.receipts_root.mkdir(parents=True, exist_ok=True)
        self.runtime_root.mkdir(parents=True, exist_ok=True)

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

    def _after_temp_fsync(self, temporary: Path) -> None:
        pass

    def _publish(self, source: Path, target: Path) -> None:
        os.replace(source, target)

    def _after_publish(self, target: Path) -> None:
        pass
