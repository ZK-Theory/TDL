from __future__ import annotations

import json
import os
from pathlib import Path
from types import TracebackType
from typing import Self

from research_system.errors import ConflictError


class WriterLock:
    def __init__(self, path: Path, identity: dict[str, str]):
        self.path = path
        self.identity = identity

    def __enter__(self) -> Self:
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise ConflictError(f'writer lock exists: {self.path}') from exc
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(self.identity, handle, sort_keys=True, separators=(',', ':'))
            handle.flush()
            os.fsync(handle.fileno())
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        try:
            recorded = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as read_error:
            raise ConflictError('writer lock cannot be verified while held') from read_error
        if recorded != self.identity:
            raise ConflictError('writer lock ownership changed while held')
        self.path.unlink()
        return False
