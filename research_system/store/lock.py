from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable
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
            raise ConflictError(f"writer lock exists: {self.path}") from exc
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(self.identity, handle, sort_keys=True, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            self.path.unlink(missing_ok=True)
            raise
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        try:
            recorded = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as read_error:
            raise ConflictError("writer lock cannot be verified while held") from read_error
        if recorded != self.identity:
            raise ConflictError("writer lock ownership changed while held")
        self.path.unlink()
        return False


class CompositeWriterLock:
    """Acquire one writer lock per distinct root in canonical path order."""

    def __init__(
        self,
        roots: Iterable[Path],
        identity: dict[str, str],
        *,
        lock_factory: Callable[[Path, dict[str, str]], WriterLock] | None = None,
    ):
        canonical_roots: dict[str, Path] = {}
        for root in roots:
            resolved = Path(root).resolve(strict=False)
            canonical_roots.setdefault(os.path.normcase(str(resolved)), resolved)
        if not canonical_roots:
            raise ValueError("composite writer lock requires at least one root")
        self.paths = tuple(canonical_roots[key] / "runtime" / "writer.lock" for key in sorted(canonical_roots))
        factory = WriterLock if lock_factory is None else lock_factory
        self._locks = tuple(factory(path, identity) for path in self.paths)
        self._acquired: list[WriterLock] = []

    def __enter__(self) -> Self:
        acquired: list[WriterLock] = []
        try:
            for lock in self._locks:
                lock.__enter__()
                acquired.append(lock)
        except BaseException:
            for lock in reversed(acquired):
                lock.__exit__(None, None, None)
            raise
        self._acquired = acquired
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        first_error: BaseException | None = None
        for lock in reversed(self._acquired):
            try:
                lock.__exit__(exc_type, exc, traceback)
            except BaseException as release_error:
                if first_error is None:
                    first_error = release_error
        self._acquired = []
        if first_error is not None:
            raise first_error
        return False
