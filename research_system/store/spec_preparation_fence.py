"""Exclusive, recoverable fence for a complete public SPEC action saga.

The SPEC coordinator publishes contexts, briefs, packages, raw artefacts, and
reviews through several independently governed services.  Those writes must
observe one unchanged Discovery tail: a later phase cannot safely repair an
earlier durable phase that was bound before an intervening public append.  This
fence is deliberately separate from ``runtime/writer.lock`` so the coordinator
can hold it while the individual services acquire their ordinary writer locks.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Self

from research_system.store.lock import WriterLock


class SpecPreparationFence:
    """Serialize public SPEC action sagas with every normal public append.

    A single thread may re-enter the fence while it invokes ``CommandService``
    and ``DiscoveryRuntime``.  A competing thread or process encounters the
    durable exclusive lock and fails before it can append.  The final exit is
    responsible for releasing the lock, so an exception leaves no in-process
    reentrancy state behind.
    """

    _state = threading.local()

    def __init__(self, control_root: Path) -> None:
        self.control_root = Path(control_root)
        self._key: str | None = None
        self._entered = False

    @classmethod
    def _held(cls) -> dict[str, tuple[WriterLock, int]]:
        held = getattr(cls._state, "held", None)
        if held is None:
            held = {}
            cls._state.held = held
        return held

    def __enter__(self) -> Self:
        root = self.control_root.resolve(strict=True)
        lock_path = root / "runtime" / "spec-preparation.lock"
        key = os.path.normcase(str(lock_path))
        held = self._held()
        entry = held.get(key)
        if entry is None:
            lock = WriterLock(lock_path, {"operation": "spec-preparation"})
            lock.__enter__()
            held[key] = (lock, 1)
        else:
            lock, depth = entry
            held[key] = (lock, depth + 1)
        self._key = key
        self._entered = True
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        if not self._entered or self._key is None:
            raise RuntimeError("SPEC preparation fence exit without matching entry")
        held = self._held()
        try:
            lock, depth = held[self._key]
        except KeyError as error:
            raise RuntimeError("SPEC preparation fence ownership is unavailable") from error
        if depth < 1:
            raise RuntimeError("SPEC preparation fence depth is invalid")
        self._entered = False
        if depth > 1:
            held[self._key] = (lock, depth - 1)
            return False
        del held[self._key]
        return lock.__exit__(exc_type, exc, traceback)


__all__ = ["SpecPreparationFence"]
