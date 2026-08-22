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
import secrets
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from research_system.canonical import canonical_bytes
from research_system.errors import ConflictError
from research_system.store.lock import (
    DirectoryAnchor,
    WriterLock,
    inspect_lock,
    open_registered_member_directory_anchor,
    open_registered_root_anchor,
    register_delete_protected_directory_anchors,
    remove_stale_lock,
    unregister_delete_protected_directory_anchors,
)


@dataclass
class _HeldFence:
    lock: WriterLock
    anchors: tuple[DirectoryAnchor, DirectoryAnchor]
    registered_anchors: tuple[DirectoryAnchor, ...]
    instances: list["SpecPreparationFence"]


class SpecPreparationFence:
    """Serialize public SPEC action sagas with every normal public append.

    Distinct instances on one thread may nest while ``CommandService`` and
    ``DiscoveryRuntime`` invoke the fence again.  One instance is single-use
    while entered, and nested instances exit in reverse entry order.  A
    competing thread or process encounters the durable exclusive lock and
    fails before it can append.
    """

    _state = threading.local()

    def __init__(self, control_root: Path) -> None:
        self.control_root = Path(control_root)
        self._key: str | None = None
        self._entered = False
        self._owner_thread_id: int | None = None

    @classmethod
    def _held(cls) -> dict[str, _HeldFence]:
        held = getattr(cls._state, "held", None)
        if held is None:
            held = {}
            cls._state.held = held
        return held

    @staticmethod
    def _rollback_failed_acquire(lock: WriterLock) -> None:
        """Release only this failed acquire's uniquely identified publication."""

        try:
            if lock.path.read_bytes() != canonical_bytes(lock.identity):
                return
        except FileNotFoundError:
            return
        lock.__exit__(None, None, None)

    @staticmethod
    def _reclaim_stale_lock(lock_path: Path) -> bool:
        """Remove only an atomically revalidated dead-owner fence generation."""

        state, observed, _ = inspect_lock(lock_path)
        return state == "stale" and observed is not None and remove_stale_lock(lock_path, observed)

    def __enter__(self) -> Self:
        if self._entered:
            raise RuntimeError("SPEC preparation fence instance is already entered")
        root = self.control_root.resolve(strict=True)
        lock_path = root / "runtime" / "spec-preparation.lock"
        key = os.path.normcase(str(lock_path))
        held = self._held()
        entry = held.get(key)
        if entry is None:
            root_anchor: DirectoryAnchor | None = None
            runtime_anchor: DirectoryAnchor | None = None
            registered_anchors: tuple[DirectoryAnchor, ...] = ()
            lock: WriterLock | None = None
            try:
                root_anchor = open_registered_root_anchor(root, delete_protect=True)
                runtime_anchor = open_registered_member_directory_anchor(root_anchor.final_path / "runtime")
                root_identity, root_final_path = root_anchor.refresh()
                if root_identity != root_anchor.identity or root_final_path != root_anchor.final_path:
                    raise ConflictError("SPEC preparation root changed during fence acquisition")
                registered_anchors = register_delete_protected_directory_anchors((root_anchor, runtime_anchor))
                lock_path = runtime_anchor.final_path / "spec-preparation.lock"
                lock = WriterLock(
                    lock_path,
                    {
                        "operation": "spec-preparation",
                        "fence_acquisition_id": secrets.token_hex(16),
                    },
                )
                while True:
                    try:
                        lock.__enter__()
                    except ConflictError:
                        if self._reclaim_stale_lock(lock_path):
                            continue
                        raise
                    break
            except BaseException as acquire_error:
                reported_error = acquire_error
                if isinstance(acquire_error, ConflictError) and inspect_lock(lock_path)[0] == "live":
                    reported_error = ConflictError(f"writer lock exists: {lock_path}")
                    reported_error.__cause__ = acquire_error
                try:
                    if lock is not None:
                        self._rollback_failed_acquire(lock)
                except BaseException as rollback_error:
                    raise reported_error from rollback_error
                finally:
                    unregister_delete_protected_directory_anchors(registered_anchors)
                    for anchor in (runtime_anchor, root_anchor):
                        if anchor is not None:
                            anchor.close()
                raise reported_error
            assert root_anchor is not None and runtime_anchor is not None and lock is not None
            held[key] = _HeldFence(
                lock=lock,
                anchors=(root_anchor, runtime_anchor),
                registered_anchors=registered_anchors,
                instances=[self],
            )
        else:
            entry.instances.append(self)
        self._key = key
        self._entered = True
        self._owner_thread_id = threading.get_ident()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        if not self._entered or self._key is None:
            raise RuntimeError("SPEC preparation fence exit without matching entry")
        if self._owner_thread_id != threading.get_ident():
            raise RuntimeError("SPEC preparation fence exit from a non-owning thread")
        held = self._held()
        try:
            entry = held[self._key]
        except KeyError as error:
            raise RuntimeError("SPEC preparation fence ownership is unavailable") from error
        if not entry.instances or entry.instances[-1] is not self:
            raise RuntimeError("SPEC preparation fence instances must exit in reverse entry order")
        if len(entry.instances) > 1:
            entry.instances.pop()
            self._entered = False
            self._owner_thread_id = None
            return False
        entry.lock.__exit__(exc_type, exc, traceback)
        unregister_delete_protected_directory_anchors(entry.registered_anchors)
        for anchor in reversed(entry.anchors):
            anchor.close()
        del held[self._key]
        self._entered = False
        self._owner_thread_id = None
        return False


__all__ = ["SpecPreparationFence"]
