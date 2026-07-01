from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

from research_system.canonical import canonical_bytes
from research_system.command.models import Receipt
from research_system.errors import ConflictError


class ReceiptStore:
    def __init__(self, control_root: Path):
        self.receipts_root = control_root / 'receipts'
        self.runtime_root = control_root / 'runtime'
        self.receipts_root.mkdir(parents=True, exist_ok=True)
        self.runtime_root.mkdir(parents=True, exist_ok=True)

    def load(self, command_id: str) -> Receipt | None:
        path = self.receipts_root / f'{command_id}.json'
        if not path.exists():
            return None
        return Receipt(**json.loads(path.read_text(encoding='utf-8')))

    def write(self, receipt: Receipt) -> Receipt:
        target = self.receipts_root / f'{receipt.command_id}.json'
        data = canonical_bytes(asdict(receipt))
        if target.exists():
            if target.read_bytes() == data:
                return receipt
            raise ConflictError(f'receipt already exists: {receipt.command_id}')
        temporary = self.runtime_root / f'{receipt.command_id}.receipt.tmp'
        with temporary.open('xb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        return receipt
