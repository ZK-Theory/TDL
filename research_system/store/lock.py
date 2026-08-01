from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable
from pathlib import Path
from types import TracebackType
from typing import Self

from research_system.errors import ConflictError


def _physical_identity(path: Path) -> tuple[int, int] | None:
    try:
        observed = os.stat(path)
    except (FileNotFoundError, NotADirectoryError, OSError):
        return None
    return observed.st_dev, observed.st_ino


def _root_sort_key(path: Path) -> tuple[str, str]:
    normalized = os.path.normcase(str(path))
    display = normalized
    for prefix in ("\\\\?\\", "//?/"):
        if display.startswith(prefix):
            display = display[len(prefix) :]
            break
    return display, normalized


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
        grouped_roots: dict[tuple[object, ...], list[Path]] = {}
        for root in roots:
            resolved = Path(root).resolve(strict=False)
            physical = _physical_identity(resolved)
            if physical is None:
                key: tuple[object, ...] = ("lexical", os.path.normcase(str(resolved)))
            else:
                key = ("physical", *physical)
            grouped_roots.setdefault(key, []).append(resolved)
        if not grouped_roots:
            raise ValueError("composite writer lock requires at least one root")
        representatives = sorted(
            (min(candidates, key=_root_sort_key) for candidates in grouped_roots.values()),
            key=_root_sort_key,
        )
        self.paths = tuple(root / "runtime" / "writer.lock" for root in representatives)
        factory = WriterLock if lock_factory is None else lock_factory
        self._locks = tuple(factory(path, identity) for path in self.paths)
        self._acquired: list[WriterLock] = []

    def __enter__(self) -> Self:
        acquired: list[WriterLock] = []
        try:
            for lock in self._locks:
                lock.__enter__()
                acquired.append(lock)
        except BaseException as acquisition_error:
            self._acquired = []
            first_error: BaseException | None = None
            for lock in reversed(acquired):
                try:
                    lock.__exit__(None, None, None)
                except BaseException as release_error:
                    if first_error is None:
                        first_error = release_error
            if first_error is not None:
                raise first_error from acquisition_error
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
        acquired, self._acquired = self._acquired, []
        for lock in reversed(acquired):
            try:
                lock.__exit__(exc_type, exc, traceback)
            except BaseException as release_error:
                if first_error is None:
                    first_error = release_error
        if first_error is not None:
            raise first_error
        return False
