from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ConflictError
from research_system.ids import validate_id


def write_object(
    control_root: Path,
    kind: str,
    object_id: str,
    revision: int,
    value: Any,
) -> Path:
    validate_id(object_id, kind)
    if revision < 1:
        raise ValueError('object revision must be positive')
    data = canonical_bytes(value)
    digest = sha256_hex(data)
    directory = control_root / 'objects' / kind / object_id
    directory.mkdir(parents=True, exist_ok=True)
    prefix = f'{revision:08d}-'
    existing = sorted(directory.glob(f'{prefix}*.json'))
    if existing:
        if len(existing) == 1 and existing[0].read_bytes() == data:
            return existing[0]
        raise ConflictError(f'object revision already exists: {kind}/{object_id}/{revision}')
    target = directory / f'{prefix}{digest}.json'
    try:
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if target.read_bytes() == data:
            return target
        raise ConflictError(
            f'object revision already exists: {kind}/{object_id}/{revision}'
        ) from None
    with os.fdopen(fd, 'wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return target

class ObjectStore:
    def __init__(self, control_root: Path):
        self.control_root = control_root

    def write(
        self,
        kind: str,
        object_id: str,
        revision: int,
        value: Any,
    ) -> Path:
        return write_object(self.control_root, kind, object_id, revision, value)
