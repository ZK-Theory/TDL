"""Physical directory identity, anchored effects, and STORE transactions."""

from __future__ import annotations

import ctypes
from hashlib import sha256
import os
import stat
import time
from contextlib import contextmanager
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
import secrets
import threading
from types import TracebackType
from typing import Iterator, Literal, NoReturn, Protocol

from research_system.errors import ConflictError
from research_system.store.durability import fsync_directory


class _NativeWindowsHandle(int):
    """A HANDLE created by the native seam, distinct from a CRT descriptor."""


@dataclass(frozen=True)
class _PendingWindowsClose:
    """One closed-set native Windows close disposition.

    ``phase`` is diagnostic only. ``disposition`` selects an internal close
    implementation; callers cannot supply callbacks. A ticket can never retry
    a link, unlink, rename, descriptor close, or deletion decision.
    """

    phase: str
    disposition: Literal["native-windows-handle", "directory-anchor"]
    resource: object


_WINDOWS_CLOSE_QUARANTINE: list[_PendingWindowsClose] = []
_WINDOWS_CLOSE_QUARANTINE_LOCK = threading.Lock()


@dataclass(frozen=True)
class _FullOwnerKey:
    """One opaque key in STORE's sole retained full-owner registry."""

    kind: str
    scope: tuple[object, ...]


class _RetainedFullOwner(Protocol):
    """A full protocol owner that can synchronously drive itself terminal."""

    def _retry_full_owner_release(self) -> bool:
        """Return true only after all namespace authority is terminal."""


@dataclass
class _FullOwnerReservation:
    """Capacity reserved before an owner may make a namespace decision."""

    key: _FullOwnerKey
    transferred: bool = False
    released: bool = False


@dataclass
class _FullOwnerSlot:
    reservation: _FullOwnerReservation
    owner: _RetainedFullOwner | None = None


# This is deliberately one registry for directory transactions, writer locks,
# and composites. A reservation occupies a slot before its owner can create a
# link or apply Delete=True, so an exceptional path always has reachable
# capacity for the whole owner rather than a best-effort cleanup callback.
_FULL_OWNER_REGISTRY_CAPACITY = 64
_FULL_OWNER_REGISTRY: dict[_FullOwnerKey, _FullOwnerSlot] = {}
_FULL_OWNER_REGISTRY_LOCK = threading.RLock()
_FULL_OWNER_DRAINING: set[_FullOwnerKey] = set()


@dataclass
class _DirectoryAdmissionSlot:
    lock: threading.Lock
    users: int = 0


@dataclass
class _DirectoryAdmissionLease:
    identity: DirectoryIdentity
    slot: _DirectoryAdmissionSlot
    held: bool = True


_DIRECTORY_ADMISSION_LOCK = threading.Lock()
_DIRECTORY_ADMISSIONS: dict[DirectoryIdentity, _DirectoryAdmissionSlot] = {}
_DIRECTORY_ADMISSION_POLL_SECONDS = 0.05


def _full_owner_key(kind: str, *scope: object) -> _FullOwnerKey:
    """Create one internal, hashable full-owner key without callbacks."""

    if not isinstance(kind, str) or not kind:
        raise ValueError("full owner key kind must be a non-empty string")
    try:
        hash((kind, scope))
    except TypeError as exc:
        raise TypeError("full owner key scope must be hashable") from exc
    return _FullOwnerKey(kind, scope)


def _reserve_full_owner(key: _FullOwnerKey) -> _FullOwnerReservation:
    """Reserve the registry slot that may later retain a full owner."""

    if not isinstance(key, _FullOwnerKey):
        raise TypeError("full owner reservation requires an internal key")
    with _FULL_OWNER_REGISTRY_LOCK:
        if key in _FULL_OWNER_REGISTRY:
            raise ConflictError("a retained store owner already controls this key")
        if len(_FULL_OWNER_REGISTRY) >= _FULL_OWNER_REGISTRY_CAPACITY:
            raise ConflictError("retained store owner capacity is exhausted")
        reservation = _FullOwnerReservation(key)
        _FULL_OWNER_REGISTRY[key] = _FullOwnerSlot(reservation)
        return reservation


def _transfer_full_owner(reservation: _FullOwnerReservation, owner: _RetainedFullOwner) -> None:
    """Make a reserved slot retain its typed, namespace-capable owner."""

    if not isinstance(reservation, _FullOwnerReservation):
        raise TypeError("full owner transfer requires its reservation")
    retry = getattr(owner, "_retry_full_owner_release", None)
    if not callable(retry):
        raise TypeError("full owner must implement synchronous retry_release")
    with _FULL_OWNER_REGISTRY_LOCK:
        slot = _FULL_OWNER_REGISTRY.get(reservation.key)
        if slot is None or slot.reservation is not reservation or reservation.released:
            raise ConflictError("full owner reservation is no longer live")
        if slot.owner is not None and slot.owner is not owner:
            raise ConflictError("full owner reservation already has an owner")
        slot.owner = owner
        reservation.transferred = True


def _release_full_owner(reservation: _FullOwnerReservation | None) -> None:
    """Release one terminal reservation; idempotent after a completed retry."""

    if reservation is None:
        return
    if not isinstance(reservation, _FullOwnerReservation):
        raise TypeError("full owner release requires its reservation")
    with _FULL_OWNER_REGISTRY_LOCK:
        if reservation.released:
            return
        slot = _FULL_OWNER_REGISTRY.get(reservation.key)
        if slot is not None and slot.reservation is reservation:
            del _FULL_OWNER_REGISTRY[reservation.key]
        reservation.released = True


def _acquire_directory_admission(identity: DirectoryIdentity) -> _DirectoryAdmissionLease:
    """Acquire one in-process entry gate while continuing to drain owners.

    The gate spans the OS mutation guard lifetime. A waiter polls rather than
    sleeping indefinitely in the OS guard acquire, so a just-transferred
    unknown owner is synchronously retried before the waiter can remain stuck.
    """

    with _DIRECTORY_ADMISSION_LOCK:
        slot = _DIRECTORY_ADMISSIONS.get(identity)
        if slot is None:
            slot = _DirectoryAdmissionSlot(threading.Lock())
            _DIRECTORY_ADMISSIONS[identity] = slot
        slot.users += 1
    acquired = False
    try:
        while not acquired:
            acquired = slot.lock.acquire(timeout=_DIRECTORY_ADMISSION_POLL_SECONDS)
            if not acquired:
                drain_retained_transaction_owners()
        return _DirectoryAdmissionLease(identity, slot)
    except BaseException:
        with _DIRECTORY_ADMISSION_LOCK:
            slot.users -= 1
            if slot.users == 0 and _DIRECTORY_ADMISSIONS.get(identity) is slot:
                del _DIRECTORY_ADMISSIONS[identity]
        raise


def _release_directory_admission(lease: _DirectoryAdmissionLease | None) -> None:
    """Release one terminal in-process guard-admission lease."""

    if lease is None or not lease.held:
        return
    lease.slot.lock.release()
    lease.held = False
    with _DIRECTORY_ADMISSION_LOCK:
        lease.slot.users -= 1
        if lease.slot.users == 0 and _DIRECTORY_ADMISSIONS.get(lease.identity) is lease.slot:
            del _DIRECTORY_ADMISSIONS[lease.identity]


def drain_retained_transaction_owners() -> None:
    """Synchronously drain full retained owners before a public safe point.

    The registry invokes only the typed owner's retry method. It never accepts
    an arbitrary callback and never runs from a background thread or finalizer.
    Re-entrant entries skip an owner already being drained; its reservation
    still prevents a competing owner from acquiring the same key.
    """

    failures: BaseException | None = None
    with _FULL_OWNER_REGISTRY_LOCK:
        candidates = tuple(
            (key, slot.reservation, slot.owner)
            for key, slot in _FULL_OWNER_REGISTRY.items()
            if slot.owner is not None and key not in _FULL_OWNER_DRAINING
        )
    for key, reservation, owner in candidates:
        assert owner is not None
        with _FULL_OWNER_REGISTRY_LOCK:
            current = _FULL_OWNER_REGISTRY.get(key)
            if current is None or current.reservation is not reservation or current.owner is not owner:
                continue
            if key in _FULL_OWNER_DRAINING:
                continue
            _FULL_OWNER_DRAINING.add(key)
        try:
            terminal = owner._retry_full_owner_release()
        except BaseException as error:
            failures = _add_cleanup_error(failures, error, "retained store owner retry failed")
            if getattr(owner, "_full_owner_terminal", False):
                _release_full_owner(reservation)
        else:
            if terminal:
                _release_full_owner(reservation)
            else:
                failures = _add_cleanup_error(
                    failures,
                    ConflictError("retained store owner remains pending"),
                    "retained store owner retry deferred",
                )
        finally:
            with _FULL_OWNER_REGISTRY_LOCK:
                _FULL_OWNER_DRAINING.discard(key)
    if failures is not None:
        raise ConflictError("retained store owner drain remains pending") from failures


class _ExactGenerationBusyError(ConflictError):
    pass


class _WindowsQuarantineBusyError(ConflictError):
    pass


@dataclass
class _WindowsPendingExactRemoval:
    """One Delete=True effect that cannot be terminal until its handle closes."""

    path: Path
    identity: os.stat_result
    data: bytes
    label: str
    handle: object | None
    effect_disposition: Literal["unlinked", "stage_removed"] | None = None


class _WindowsDeleteClosePendingError(_ExactGenerationBusyError):
    """A generic exact deletion whose transaction must retain full ownership."""

    def __init__(self, pending: _WindowsPendingExactRemoval) -> None:
        super().__init__(f"{pending.label} exact generation deletion handle cannot close")
        self.pending = pending


def _add_cleanup_error(
    current: BaseException | None,
    error: BaseException,
    label: str,
) -> BaseException:
    if current is None:
        return error
    current.add_note(f"{label}: {error!r}")
    return current


@dataclass(frozen=True)
class TransactionExitStatus:
    """Whether guard ownership is active, released, retained, or terminal-uncertain."""

    guard_state: Literal["active", "released", "unknown", "terminal_uncertain"]
    close_only_transferred: bool = False


class DirectoryMutationGuard:
    __slots__ = (
        "_anchor",
        "_active",
        "_release_state",
        "_close_only_transferred",
        "_retained_release",
        "name",
    )

    def __init__(self, anchor: object, name: str) -> None:
        self._anchor = anchor
        self._active = False
        self._release_state: Literal["active", "released", "unknown", "terminal_uncertain"] = "active"
        self._close_only_transferred = False
        self._retained_release: (
            tuple[
                object,
                Callable[[object], None],
                Callable[[object], None],
            ]
            | None
        ) = None
        self.name = name

    def _release_resource(
        self,
        resource: object,
        unlocker: Callable[[object], None],
        closer: Callable[[object], None],
    ) -> BaseException | None:
        """Release a serialization resource without downgrading unknown state.

        A successful close releases a Windows byte lock and a POSIX flock even
        when the explicit unlock reported an error. A failed descriptor close
        is terminal-but-uncertain: POSIX permits the descriptor number to have
        been released, and another thread may already have reused it. Retrying
        either unlock or close through that integer could therefore act on an
        unrelated resource. Native Windows HANDLE owners use their separate,
        typed retention paths below and never pass through this descriptor API.
        """

        try:
            unlocker(resource)
        except BaseException as unlock_error:
            try:
                closer(resource)
            except BaseException as close_error:
                self._release_state = "terminal_uncertain"
                self._retained_release = None
                return _add_cleanup_error(
                    unlock_error,
                    close_error,
                    "mutation-guard descriptor close also failed; descriptor will not be retried",
                )
            self._release_state = "released"
            self._retained_release = None
            return None
        self._release_state = "released"
        try:
            closer(resource)
        except BaseException as close_error:
            # Even after a proven unlock, an integer descriptor cannot enter
            # the close-only registry: close may already have consumed it.
            self._retained_release = None
            return close_error
        self._retained_release = None
        return None

    def retry_release(self) -> None:
        """Retry only a still-unknown safe owner, never a terminal descriptor."""

        retained = self._retained_release
        if retained is None:
            return
        resource, unlocker, closer = retained
        error = self._release_resource(resource, unlocker, closer)
        if error is not None:
            raise error


def _is_windows_sharing_violation(error: OSError) -> bool:
    return getattr(error, "winerror", None) == 32 or error.errno == 32


def _link_without_following(source: str | Path, destination: str | Path, **kwargs: object) -> None:
    """Call the one no-follow hard-link seam on every supported platform."""

    os.link(source, destination, follow_symlinks=False, **kwargs)


def _windows_ordinary_path(path: Path) -> Path:
    """Return the ordinary spelling of a held Windows final path."""

    value = str(path)
    if value.startswith("\\\\?\\UNC\\"):
        return Path("\\\\" + value[8:])
    if value.startswith("\\\\?\\"):
        return Path(value[4:])
    return path


def _before_exact_generation_unlink(_path: Path) -> None:
    pass


@dataclass(frozen=True, order=True)
class DirectoryIdentity:
    scheme: Literal["windows-file-id-v1", "posix-dev-inode-v1"]
    volume_or_device: int
    file_id: bytes


class DirectoryAnchor(Protocol):
    """Public structural contract for a held physical directory anchor."""

    identity: DirectoryIdentity
    final_path: Path

    def refresh(self) -> tuple[DirectoryIdentity, Path]: ...

    def open_member_directory(
        self,
        name: str,
        *,
        create: bool = False,
        delete_protect: bool = True,
    ) -> DirectoryAnchor: ...

    def list_names(self) -> tuple[str, ...]: ...

    def read_regular_file(self, name: str) -> bytes: ...

    def read_regular_file_with_identity(self, name: str) -> tuple[bytes, os.stat_result]: ...

    def stage_private_file(self, name: str, data: bytes) -> tuple[str, os.stat_result]:
        """Stage exact private bytes for a separately guarded writer.

        Args:
            name: Canonical final member name used to derive the private name.
            data: Exact bytes to stage.

        Returns:
            The private member name and its exact physical identity.

        Raises:
            ConflictError: If the anchored directory or staged generation cannot
                be proved physical and unchanged.
            OSError: If staging or required durability cannot complete.
        """
        ...

    def link_exact_regular_file(
        self,
        source: str,
        expected_identity: os.stat_result,
        destination: str,
        *,
        guard: DirectoryMutationGuard | None = None,
    ) -> os.stat_result: ...

    def fsync(self) -> None: ...

    def verify_unchanged(self) -> None: ...

    def remove_exact_generation(
        self,
        name: str,
        expected: os.stat_result,
        expected_bytes: bytes,
        *,
        guard: DirectoryMutationGuard | None = None,
    ) -> None: ...

    def acquire_mutation_guard(self, name: str) -> Iterator[DirectoryMutationGuard]: ...

    def close(self) -> None: ...


class _DirectoryAnchor:
    __slots__ = (
        "identity",
        "final_path",
        "_parent",
        "_active_mutation_guard",
        "_handle",
        "_refresh_impl",
        "_close_impl",
        "_delete_protected",
        "_quarantined",
        "_closed",
        "_transaction_holds",
        "_close_requested",
    )

    def __init__(
        self,
        identity: DirectoryIdentity,
        final_path: Path,
        handle: object,
        refresh_impl: Callable[[object], tuple[DirectoryIdentity, Path]],
        close_impl: Callable[[object], None],
        parent: _DirectoryAnchor | None = None,
        *,
        delete_protected: bool = False,
    ) -> None:
        self.identity = identity
        self.final_path = final_path
        self._parent = parent
        self._active_mutation_guard: DirectoryMutationGuard | None = None
        self._handle = handle
        self._refresh_impl = refresh_impl
        self._close_impl = close_impl
        self._delete_protected = delete_protected
        self._quarantined = False
        self._closed = False
        self._transaction_holds = 0
        self._close_requested = False

    def refresh(self) -> tuple[DirectoryIdentity, Path]:
        if self._closed:
            raise ConflictError("directory anchor is no longer live")
        self._retry_deferred_windows_closures()
        try:
            return self._refresh_impl(self._handle)
        except FileNotFoundError:
            raise
        except ConflictError:
            raise
        except (OSError, ValueError) as exc:
            raise ConflictError("directory anchor identity is unavailable") from exc

    def _retry_deferred_windows_closures(self) -> None:
        # Historical call seam only.  The sole registry drains at public safe
        # points (transaction and writer entry), never opportunistically while
        # an anchor might itself be one of the retained resources.
        return

    def _close_or_defer_windows_handle(self, handle: object) -> None:
        pending = _close_only_ticket(
            "anchor-fence",
            "native-windows-handle",
            handle,
        )
        try:
            _close_close_only_ticket(pending)
        except BaseException:
            _retain_close_ticket(pending)
            raise

    @staticmethod
    def _require_member_name(name: str) -> None:
        if not isinstance(name, str) or not name or "\x00" in name or Path(name).name != name or name in {".", ".."}:
            raise ConflictError("directory member name is invalid")

    def open_member_directory(
        self,
        name: str,
        *,
        create: bool = False,
        delete_protect: bool = True,
    ) -> DirectoryAnchor:
        self._require_member_name(name)
        self.verify_unchanged()
        _parent_identity, parent_path = self.refresh()
        child: _DirectoryAnchor | None = None
        try:
            if os.name == "nt":
                # The same held parent-generation fence covers both the
                # namespace effect and acquisition of the child anchor.  A
                # post-effect identity check would detect a root replacement
                # only after mkdir had already mutated the replacement root.
                with self._effect_final_path(parent_path) as protected_parent:
                    child_path = _windows_ordinary_path(protected_parent) / name
                    if create:
                        try:
                            child_path.mkdir()
                        except FileExistsError:
                            pass
                        fsync_directory(protected_parent)
                    child = _open_windows_anchor(
                        child_path,
                        reject_reparse=True,
                        delete_protect=delete_protect,
                    )
            else:
                nofollow = getattr(os, "O_NOFOLLOW", 0)
                directory_flag = getattr(os, "O_DIRECTORY", 0)
                if not nofollow or not directory_flag or os.open not in os.supports_dir_fd:
                    raise ConflictError("platform cannot open an anchored member directory")
                descriptor = int(self._handle)
                if create:
                    try:
                        os.mkdir(name, 0o700, dir_fd=descriptor)
                    except FileExistsError:
                        pass
                    os.fsync(descriptor)
                child_descriptor = os.open(
                    name,
                    os.O_RDONLY | directory_flag | nofollow,
                    dir_fd=descriptor,
                )
                try:
                    refresh = _posix_anchor_refresh_factory(parent_path / name, delete_protect=delete_protect)
                    child_identity, child_path = refresh(child_descriptor)
                    child = _DirectoryAnchor(
                        child_identity,
                        child_path,
                        child_descriptor,
                        refresh,
                        lambda value: os.close(int(value)),
                        self,
                        delete_protected=delete_protect,
                    )
                except BaseException as primary_error:
                    try:
                        os.close(child_descriptor)
                    except BaseException as cleanup_error:
                        raise primary_error from cleanup_error
                    raise
        except (FileNotFoundError, ConflictError) as primary_error:
            cleanup_error: BaseException | None = None
            if child is not None:
                try:
                    child.close()
                except BaseException as error:
                    cleanup_error = error
            _raise_primary_with_cleanup(primary_error, cleanup_error)
        except OSError as exc:
            if os.name == "nt" and _is_windows_sharing_violation(exc):
                primary_error = ConflictError("anchored parent directory changed during member traversal")
            else:
                primary_error = ConflictError(f"{name} is not a physical member directory")
            primary_error.__cause__ = exc
            cleanup_error = None
            if child is not None:
                try:
                    child.close()
                except BaseException as error:
                    cleanup_error = error
            _raise_primary_with_cleanup(primary_error, cleanup_error)
        except BaseException as primary_error:
            cleanup_error = None
            if child is not None:
                try:
                    child.close()
                except BaseException as error:
                    cleanup_error = error
            _raise_primary_with_cleanup(primary_error, cleanup_error)
        assert child is not None
        child._parent = self
        try:
            self.verify_unchanged()
        except BaseException as primary_error:
            cleanup_error = None
            try:
                child.close()
            except BaseException as error:
                cleanup_error = error
            _raise_primary_with_cleanup(primary_error, cleanup_error)
        return child

    def list_names(self) -> tuple[str, ...]:
        self.verify_unchanged()
        identity, final_path = self.refresh()
        try:
            with self._effect_final_path(final_path) as effect_path:
                if os.name == "nt":
                    names = tuple(entry.name for entry in effect_path.iterdir())
                else:
                    names = tuple(os.listdir(int(self._handle)))
        except OSError as exc:
            raise ConflictError("anchored directory cannot be listed") from exc
        self.verify_unchanged()
        refreshed_identity, refreshed_path = self.refresh()
        if refreshed_identity != identity or refreshed_path != final_path:
            raise ConflictError("anchored directory identity changed during listing")
        return tuple(sorted(names))

    def _member_identity(self, name: str, final_path: Path) -> os.stat_result:
        self._require_member_name(name)
        try:
            if os.name == "nt":
                observed = (final_path / name).lstat()
                attributes = getattr(observed, "st_file_attributes", 0)
                if stat.S_ISLNK(observed.st_mode) or attributes & getattr(
                    stat,
                    "FILE_ATTRIBUTE_REPARSE_POINT",
                    0,
                ):
                    raise ConflictError("anchored directory member must not be a reparse file")
            else:
                observed = os.stat(name, dir_fd=int(self._handle), follow_symlinks=False)
        except FileNotFoundError:
            raise
        except ConflictError:
            raise
        except OSError as exc:
            raise ConflictError("anchored regular file identity is unavailable") from exc
        if not stat.S_ISREG(observed.st_mode):
            raise ConflictError("anchored directory member is not a regular file")
        return observed

    def _read_regular_file_with_identity(self, name: str, final_path: Path) -> tuple[bytes, os.stat_result]:
        before = self._member_identity(name, final_path)
        descriptor: int | None = None
        primary_error: BaseException | None = None
        cleanup_error: BaseException | None = None
        result: tuple[bytes, os.stat_result] | None = None
        try:
            if os.name == "nt":
                descriptor = os.open(final_path / name, os.O_RDONLY | getattr(os, "O_BINARY", 0))
            else:
                nofollow = getattr(os, "O_NOFOLLOW", 0)
                if not nofollow or os.open not in os.supports_dir_fd:
                    raise ConflictError("platform cannot read an anchored regular file")
                descriptor = os.open(name, os.O_RDONLY | nofollow, dir_fd=int(self._handle))
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or not os.path.samestat(before, opened):
                raise ConflictError("anchored directory member is not the observed regular file")
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            data = b"".join(chunks)
            after = self._member_identity(name, final_path)
            if not os.path.samestat(opened, after):
                raise ConflictError("anchored directory member changed during read")
            result = data, after
        except FileNotFoundError as exc:
            primary_error = exc
        except ConflictError as exc:
            primary_error = exc
        except OSError as exc:
            wrapped = ConflictError("anchored regular file cannot be read")
            wrapped.__cause__ = exc
            primary_error = wrapped
        finally:
            if descriptor is not None:
                try:
                    # A CRT/POSIX descriptor close is one-shot.  An exception
                    # may mean the integer was already consumed and reused, so
                    # it is never retained or retried by number.
                    os.close(descriptor)
                except BaseException as error:
                    cleanup_error = error
        if primary_error is not None:
            _raise_primary_with_cleanup(primary_error, cleanup_error)
        if cleanup_error is not None:
            raise ConflictError("anchored regular file descriptor cannot be closed") from cleanup_error
        assert result is not None
        return result

    def read_regular_file(self, name: str) -> bytes:
        try:
            data, _ = self.read_regular_file_with_identity(name)
            return data
        except FileNotFoundError as exc:
            raise ConflictError("anchored regular file cannot be read") from exc

    def read_regular_file_with_identity(self, name: str) -> tuple[bytes, os.stat_result]:
        self.verify_unchanged()
        _identity, final_path = self.refresh()
        with self._effect_final_path(final_path) as effect_path:
            result = self._read_regular_file_with_identity(name, effect_path)
        self.verify_unchanged()
        return result

    def _fsync_directory(self, final_path: Path) -> None:
        if os.name == "nt":
            fsync_directory(final_path)
        else:
            os.fsync(int(self._handle))

    def fsync(self) -> None:
        self.verify_unchanged()
        _identity, final_path = self.refresh()
        with self._effect_final_path(final_path) as effect_path:
            self._fsync_directory(effect_path)
        self.verify_unchanged()

    def verify_unchanged(self) -> None:
        if self._parent is not None:
            self._parent.verify_unchanged()
        identity, final_path = self.refresh()
        if identity != self.identity or final_path != self.final_path:
            raise ConflictError("anchored directory identity changed during object operation")

    @contextmanager
    def _effect_final_path(self, final_path: Path) -> Iterable[Path]:
        if os.name != "nt":
            yield final_path
            return
        if self._delete_protected:
            self.verify_unchanged()
            _identity, guarded_path = self.refresh()
            yield guarded_path
            self.verify_unchanged()
            return
        fence: object | None = None
        primary_error: BaseException | None = None
        cleanup_error: BaseException | None = None
        try:
            for attempt in range(64):
                try:
                    fence = _windows_open_handle(
                        final_path,
                        open_reparse_point=False,
                        delete_protect=True,
                        # Windows enforces this replacement fence only when
                        # the held handle both requests DELETE and withholds
                        # FILE_SHARE_DELETE. Anchors reaching this branch were
                        # opened share-delete, so the transient handle can
                        # request DELETE without conflicting with its owner.
                        delete_access=True,
                    )
                except OSError as exc:
                    if not _is_windows_sharing_violation(exc) or attempt == 63:
                        raise
                    self.verify_unchanged()
                    time.sleep(0.005)
                    continue
                break
            if fence is None:  # pragma: no cover - the final retry raises
                raise ConflictError("anchored directory filesystem fence is unavailable")
            identity, guarded_path = _windows_anchor_refresh(fence)
            if identity != self.identity:
                raise ConflictError("anchored directory identity changed before filesystem effect")
            yield guarded_path
        except BaseException as exc:
            primary_error = exc
        finally:
            if fence is not None:
                try:
                    self._close_or_defer_windows_handle(fence)
                except BaseException as exc:
                    cleanup_error = exc
        if primary_error is not None:
            _raise_primary_with_cleanup(primary_error, cleanup_error)
        if cleanup_error is not None:
            raise cleanup_error

    def _link_member(self, source: str, destination: str, final_path: Path) -> None:
        if os.name == "nt":
            _link_without_following(final_path / source, final_path / destination)
            return
        _link_without_following(
            source,
            destination,
            src_dir_fd=int(self._handle),
            dst_dir_fd=int(self._handle),
        )

    def stage_private_file(self, name: str, data: bytes) -> tuple[str, os.stat_result]:
        """Create one exact private generation for a separately guarded writer.

        Writer-lock publication holds its own POSIX flock for the lifetime of
        the lock, so it cannot use ``DirectoryTransaction``'s short-lived
        transaction guard.  The physical directory owner therefore provides
        this one stage operation; all public publication and deletion remain
        anchored operations.

        Args:
            name: Canonical final member name used to derive the stage name.
            data: Exact bytes to write and durability-prove.

        Returns:
            The private stage member name and its exact physical identity.

        Raises:
            ConflictError: If the anchor or staged generation cannot remain
                exact.
            OSError: If the filesystem cannot stage or durably flush the bytes.
        """

        self._require_member_name(name)
        if not isinstance(data, bytes):
            raise TypeError("anchored file content must be bytes")
        self.verify_unchanged()
        _identity, final_path = self.refresh()
        temporary = f".{name}.{secrets.token_hex(16)}.tmp"
        descriptor: int | None = None
        temporary_identity: os.stat_result | None = None
        try:
            with self._effect_final_path(final_path) as effect_path:
                flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
                if os.name == "nt":
                    descriptor = os.open(effect_path / temporary, flags, 0o600)
                else:
                    nofollow = getattr(os, "O_NOFOLLOW", 0)
                    if not nofollow or os.open not in os.supports_dir_fd:
                        raise ConflictError("platform cannot write an anchored regular file")
                    descriptor = os.open(temporary, flags | nofollow, 0o600, dir_fd=int(self._handle))
                temporary_identity = os.fstat(descriptor)
                if not stat.S_ISREG(temporary_identity.st_mode):
                    raise ConflictError("anchored private file is not regular")
                remaining = memoryview(data)
                while remaining:
                    written = os.write(descriptor, remaining)
                    if written < 1:
                        raise OSError("anchored private file write made no progress")
                    remaining = remaining[written:]
                os.fsync(descriptor)
                closing_descriptor = descriptor
                descriptor = None
                os.close(closing_descriptor)
                observed_data, observed_identity = self._read_regular_file_with_identity(temporary, effect_path)
                if observed_data != data or not os.path.samestat(temporary_identity, observed_identity):
                    raise ConflictError("anchored private publication changed after fsync")
            return temporary, temporary_identity
        except BaseException as primary_error:
            cleanup_error: BaseException | None = None
            if descriptor is not None:
                closing_descriptor = descriptor
                descriptor = None
                try:
                    os.close(closing_descriptor)
                except BaseException as error:
                    cleanup_error = error
            if temporary_identity is not None:
                try:
                    with self.acquire_mutation_guard(TRANSACTION_GUARD_NAME) as guard:
                        self.remove_exact_generation(
                            temporary,
                            temporary_identity,
                            data,
                            guard=guard,
                        )
                except FileNotFoundError:
                    pass
                except BaseException as error:
                    cleanup_error = _add_cleanup_error(
                        cleanup_error,
                        error,
                        "anchored private-stage cleanup also failed",
                    )
            _raise_primary_with_cleanup(primary_error, cleanup_error)

    def link_exact_regular_file(
        self,
        source: str,
        expected_identity: os.stat_result,
        destination: str,
        *,
        guard: DirectoryMutationGuard | None = None,
    ) -> os.stat_result:
        self._require_member_name(source)
        self._require_member_name(destination)
        if guard is not None:
            self._validate_mutation_guard(guard)
        self.verify_unchanged()
        _directory_identity, final_path = self.refresh()
        with self._effect_final_path(final_path) as effect_path:
            if not os.path.samestat(expected_identity, self._member_identity(source, effect_path)):
                raise ConflictError("anchored file changed before link publication")
            self._link_member(source, destination, effect_path)
            destination_identity = self._member_identity(destination, effect_path)
            if not os.path.samestat(expected_identity, destination_identity):
                raise ConflictError("anchored linked generation changed during publication")
        return destination_identity

    def _unlink_member(
        self,
        name: str,
        expected_identity: os.stat_result,
        expected_bytes: bytes,
        final_path: Path,
    ) -> None:
        data, observed_identity = self._read_regular_file_with_identity(name, final_path)
        if not os.path.samestat(expected_identity, observed_identity):
            raise ConflictError("anchored file changed before exact generation deletion")
        if data != expected_bytes:
            raise ConflictError("anchored file bytes changed before exact generation deletion")
        if os.name == "nt":
            _delete_exact_regular_file(
                final_path / name,
                expected_identity,
                expected_bytes=expected_bytes,
                label="anchored file",
                close_phase="canonical",
            )
            return
        if self._active_mutation_guard is None:
            raise ConflictError("POSIX exact generation deletion requires an anchored exclusive guard")
        _before_exact_generation_unlink(final_path / name)
        data, observed_identity = self._read_regular_file_with_identity(name, final_path)
        if not os.path.samestat(expected_identity, observed_identity):
            raise ConflictError("anchored file changed before exact generation deletion")
        if data != expected_bytes:
            raise ConflictError("anchored file bytes changed before exact generation deletion")
        try:
            os.unlink(name, dir_fd=int(self._handle))
        except FileNotFoundError:
            raise
        except OSError as exc:
            raise ConflictError("anchored exact generation cannot be deleted") from exc

    def remove_exact_generation(
        self,
        name: str,
        expected_identity: os.stat_result,
        expected_bytes: bytes,
        *,
        guard: DirectoryMutationGuard | None = None,
    ) -> None:
        self.verify_unchanged()
        if os.name != "nt" and guard is None:
            raise ConflictError("POSIX exact generation deletion requires an anchored exclusive guard")
        if guard is not None:
            self._validate_mutation_guard(guard)
        directory_identity, final_path = self.refresh()
        with self._effect_final_path(final_path) as effect_path:
            self._unlink_member(name, expected_identity, expected_bytes, effect_path)
            self._fsync_directory(effect_path)
        refreshed_identity, refreshed_path = self.refresh()
        if refreshed_identity != directory_identity or refreshed_path != final_path:
            raise ConflictError("anchored directory identity changed during exact generation deletion")

    def _validate_mutation_guard(self, guard: DirectoryMutationGuard) -> None:
        if guard._anchor is not self or not guard._active or self._active_mutation_guard is not guard:
            raise ConflictError("anchored directory mutation guard is not active")

    @contextmanager
    def acquire_mutation_guard(self, name: str) -> Iterator[DirectoryMutationGuard]:
        self._require_member_name(name)
        self.verify_unchanged()
        if self._active_mutation_guard is not None:
            raise ConflictError("anchored directory mutation guard is already active")
        guard = DirectoryMutationGuard(self, name)
        if os.name == "nt":
            descriptor: int | None = None
            locked = False
            primary_error: BaseException | None = None
            cleanup_error: BaseException | None = None
            try:
                _identity, final_path = self.refresh()
                with self._effect_final_path(final_path) as effect_path:
                    descriptor = os.open(
                        effect_path / name,
                        os.O_CREAT | os.O_RDWR | getattr(os, "O_BINARY", 0),
                        0o600,
                    )
                    observed = self._member_identity(name, effect_path)
                    if not os.path.samestat(observed, os.fstat(descriptor)):
                        raise ConflictError("anchored exclusive guard changed during open")
                    self._fsync_directory(effect_path)
                import msvcrt

                for attempt in range(64):
                    try:
                        os.lseek(descriptor, 0, 0)
                        msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                    except OSError:
                        if attempt == 63:
                            raise
                        time.sleep(0.005)
                        continue
                    locked = True
                    break
                if not locked:  # pragma: no cover - the final retry raises
                    raise ConflictError("anchored exclusive guard is unavailable")
                guard._active = True
                self._active_mutation_guard = guard
                yield guard
            except BaseException as exc:
                primary_error = exc
            finally:
                guard._active = False
                self._active_mutation_guard = None
                if locked:
                    assert descriptor is not None

                    def unlocker(resource: object) -> None:
                        os.lseek(int(resource), 0, 0)
                        msvcrt.locking(int(resource), msvcrt.LK_UNLCK, 1)

                    cleanup_error = guard._release_resource(descriptor, unlocker, os.close)
                elif descriptor is not None:
                    closing_descriptor = descriptor
                    descriptor = None
                    try:
                        os.close(closing_descriptor)
                    except BaseException as exc:
                        cleanup_error = _add_cleanup_error(
                            cleanup_error,
                            exc,
                            "mutation-guard descriptor close also failed; descriptor will not be retried",
                        )
            if primary_error is not None:
                _raise_primary_with_cleanup(primary_error, cleanup_error)
            if cleanup_error is not None:
                raise cleanup_error
            return
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        if not nofollow or os.open not in os.supports_dir_fd:
            raise ConflictError("platform cannot create an anchored exclusive guard")
        descriptor: int | None = None
        locked = False
        primary_error: BaseException | None = None
        try:
            descriptor = os.open(
                name,
                os.O_CREAT | os.O_RDWR | nofollow,
                0o600,
                dir_fd=int(self._handle),
            )
            observed = os.fstat(descriptor)
            if not stat.S_ISREG(observed.st_mode):
                raise ConflictError("anchored exclusive guard is not a regular file")
            os.fsync(int(self._handle))
            try:
                import fcntl
            except ImportError as exc:  # pragma: no cover - non-POSIX fallback
                raise ConflictError("platform cannot lock an anchored exclusive guard") from exc
            for attempt in range(64):
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    if attempt == 63:
                        raise ConflictError("anchored exclusive guard is unavailable") from exc
                    time.sleep(0.005)
                    continue
                locked = True
                break
            if not locked:  # pragma: no cover - the final retry raises
                raise ConflictError("anchored exclusive guard is unavailable")
            guard._active = True
            self._active_mutation_guard = guard
            self.verify_unchanged()
            yield guard
        except BaseException as error:
            primary_error = error
        finally:
            cleanup_error: BaseException | None = None
            if locked:
                guard._active = False
                self._active_mutation_guard = None
                assert descriptor is not None

                def unlocker(resource: object) -> None:
                    fcntl.flock(int(resource), fcntl.LOCK_UN)

                cleanup_error = guard._release_resource(descriptor, unlocker, os.close)
            elif descriptor is not None:
                closing_descriptor = descriptor
                descriptor = None
                try:
                    os.close(closing_descriptor)
                except BaseException as error:
                    cleanup_error = _add_cleanup_error(
                        cleanup_error,
                        error,
                        "mutation-guard descriptor close also failed; descriptor will not be retried",
                    )
        if primary_error is not None:
            _raise_primary_with_cleanup(primary_error, cleanup_error)
        if cleanup_error is not None:
            raise cleanup_error

    def _close_without_quarantine(self) -> None:
        if self._closed:
            return
        if os.name != "nt":
            # A POSIX close error does not grant retry authority over the same
            # descriptor number; it may already name an unrelated resource.
            self._closed = True
            self._close_impl(self._handle)
        else:
            self._close_impl(self._handle)
            self._closed = True
        self._quarantined = False

    def _retain_transaction_hold(self) -> None:
        """Retain this anchor and every ancestor needed to verify its identity."""

        chain = self._transaction_anchor_chain()
        # Validate the complete chain before incrementing any member. A failed
        # retain therefore cannot leave a partial hold which no transaction
        # owns or knows how to release.
        for anchor in reversed(chain):
            if anchor._closed:
                raise ConflictError("anchored directory is already closed")
        for anchor in reversed(chain):
            anchor._transaction_holds += 1

    def _release_transaction_hold(self) -> None:
        """Release one complete leaf-to-root hold, attempting every deferred close."""

        chain = self._transaction_anchor_chain()
        # As on retain, validate before changing any count. The transaction
        # owns the chain as one unit; a partial release would make a later retry
        # either double-release an ancestor or strand another one.
        for anchor in chain:
            if anchor._transaction_holds < 1:
                raise RuntimeError("anchored transaction hold is not live")

        first_error: BaseException | None = None
        for anchor in chain:
            anchor._transaction_holds -= 1
            if anchor._transaction_holds or not anchor._close_requested:
                continue
            anchor._close_requested = False
            try:
                anchor.close()
            except BaseException as error:
                first_error = _add_cleanup_error(first_error, error, "ancestor anchor close also failed")
        if first_error is not None:
            raise first_error

    def _transaction_anchor_chain(self) -> tuple[_DirectoryAnchor, ...]:
        """Return the physical leaf-to-root identity chain without callbacks."""

        chain: list[_DirectoryAnchor] = []
        seen: set[int] = set()
        current: _DirectoryAnchor | None = self
        while current is not None:
            marker = id(current)
            if marker in seen:
                raise ConflictError("anchored directory ancestry is cyclic")
            seen.add(marker)
            chain.append(current)
            current = current._parent
        return tuple(chain)

    def close(self) -> None:
        if self._transaction_holds:
            # A retained DirectoryTransaction owns a guard or Delete=True
            # state tied to this physical directory. Let its synchronous
            # registry retry finish first; no outer ``with`` may strand it.
            self._close_requested = True
            return
        if self._quarantined:
            drain_close_quarantine()
            return
        try:
            self._close_without_quarantine()
        except BaseException:
            if os.name == "nt":
                self._quarantined = True
                _retain_close_ticket(_close_only_ticket("anchor", "directory-anchor", self))
            raise


def _raise_primary_with_cleanup(
    primary_error: BaseException,
    cleanup_error: BaseException | None,
) -> NoReturn:
    if cleanup_error is None:
        raise primary_error
    raise primary_error from cleanup_error


if os.name == "nt":
    from ctypes import wintypes

    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _KERNEL32.CreateFileW.argtypes = [
        ctypes.c_wchar_p,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    _KERNEL32.CreateFileW.restype = wintypes.HANDLE
    _KERNEL32.ReadFile.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    _KERNEL32.ReadFile.restype = wintypes.BOOL
    _KERNEL32.GetFileInformationByHandleEx.argtypes = [
        wintypes.HANDLE,
        wintypes.INT,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    _KERNEL32.GetFileInformationByHandleEx.restype = wintypes.BOOL
    _KERNEL32.GetFinalPathNameByHandleW.argtypes = [
        wintypes.HANDLE,
        ctypes.c_wchar_p,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    _KERNEL32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    _KERNEL32.SetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        wintypes.INT,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    _KERNEL32.SetFileInformationByHandle.restype = wintypes.BOOL
    _KERNEL32.CloseHandle.argtypes = [wintypes.HANDLE]
    _KERNEL32.CloseHandle.restype = wintypes.BOOL

    class _FILE_ID_128(ctypes.Structure):
        _fields_ = [("Identifier", ctypes.c_ubyte * 16)]

    class _FILE_ID_INFO(ctypes.Structure):
        _fields_ = [
            ("VolumeSerialNumber", ctypes.c_ulonglong),
            ("FileId", _FILE_ID_128),
        ]

    class _FILE_ATTRIBUTE_TAG_INFO(ctypes.Structure):
        _fields_ = [
            ("FileAttributes", wintypes.DWORD),
            ("ReparseTag", wintypes.DWORD),
        ]

    class _FILE_DISPOSITION_INFO(ctypes.Structure):
        _fields_ = [("DeleteFile", ctypes.c_ubyte)]

    _FILE_ATTRIBUTE_TAG_INFO_CLASS = 9
    _FILE_ID_INFO_CLASS = 18
    _FILE_ATTRIBUTE_DIRECTORY = 0x00000010
    _FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
    _FILE_DISPOSITION_INFO_CLASS = 4
    _FILE_READ_ATTRIBUTES = 0x00000080
    _GENERIC_READ = 0x80000000
    _DELETE = 0x00010000
    _SYNCHRONIZE = 0x00100000
    _FILE_SHARE_READ = 0x00000001
    _FILE_SHARE_WRITE = 0x00000002
    _FILE_SHARE_DELETE = 0x00000004
    _OPEN_EXISTING = 3
    _FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    _VOLUME_NAME_DOS = 0x0
    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


def _windows_api_error(operation: str) -> OSError:
    error_code = ctypes.get_last_error()
    if error_code in {2, 3}:  # ERROR_FILE_NOT_FOUND, ERROR_PATH_NOT_FOUND
        return FileNotFoundError(error_code, f"{operation} failed: {ctypes.FormatError(error_code)}")
    return OSError(error_code, f"{operation} failed: {ctypes.FormatError(error_code)}")


def _windows_open_handle(
    path: Path,
    *,
    open_reparse_point: bool,
    delete_protect: bool = False,
    delete_access: bool | None = None,
    read_contents: bool = False,
    share_mode: int | None = None,
) -> object:
    _drain_windows_close_quarantine()
    flags = _FILE_FLAG_BACKUP_SEMANTICS
    if open_reparse_point:
        flags |= _FILE_FLAG_OPEN_REPARSE_POINT
    access = _FILE_READ_ATTRIBUTES | _SYNCHRONIZE
    if delete_access is None:
        # Delete protection is a share-mode property: omitting
        # FILE_SHARE_DELETE blocks a later delete/rename opener. Request
        # DELETE only at the exact deletion seam, whose callers pass True.
        delete_access = False
    if delete_access:
        access |= _DELETE
    if read_contents:
        access |= _GENERIC_READ
    if share_mode is None:
        share_mode = _FILE_SHARE_READ | _FILE_SHARE_WRITE
        if not delete_protect:
            share_mode |= _FILE_SHARE_DELETE
    handle = _KERNEL32.CreateFileW(
        str(path),
        access,
        share_mode,
        None,
        _OPEN_EXISTING,
        flags,
        None,
    )
    value = getattr(handle, "value", handle)
    if value in (None, _INVALID_HANDLE_VALUE):
        raise _windows_api_error(f"CreateFileW({path})")
    return _NativeWindowsHandle(int(value))


def _windows_read_handle(handle: object) -> bytes:
    _windows_rewind_handle(handle)
    chunks: list[bytes] = []
    while True:
        buffer = ctypes.create_string_buffer(1024 * 1024)
        count = wintypes.DWORD()
        if not _KERNEL32.ReadFile(handle, buffer, len(buffer), ctypes.byref(count), None):
            raise _windows_api_error("ReadFile")
        if count.value == 0:
            return b"".join(chunks)
        chunks.append(buffer.raw[: count.value])


def _windows_rewind_handle(handle: object) -> None:
    set_pointer = _KERNEL32.SetFilePointerEx
    set_pointer.argtypes = [
        wintypes.HANDLE,
        ctypes.c_longlong,
        ctypes.POINTER(ctypes.c_longlong),
        wintypes.DWORD,
    ]
    set_pointer.restype = wintypes.BOOL
    if not set_pointer(handle, 0, None, 0):  # FILE_BEGIN
        raise _windows_api_error("SetFilePointerEx")


def _windows_close_handle(handle: object) -> None:
    if not _KERNEL32.CloseHandle(handle):
        raise _windows_api_error("CloseHandle")


def _drain_windows_close_quarantine() -> None:
    """Synchronously drain native Windows close-only resources."""

    with _WINDOWS_CLOSE_QUARANTINE_LOCK:
        retained: list[_PendingWindowsClose] = []
        error: BaseException | None = None
        for pending in _WINDOWS_CLOSE_QUARANTINE:
            try:
                _close_close_only_ticket(pending)
            except BaseException as exc:
                retained.append(pending)
                error = _add_cleanup_error(error, exc, f"Windows {pending.phase} close retry failed")
        _WINDOWS_CLOSE_QUARANTINE[:] = retained
        if error is not None:
            raise _WindowsQuarantineBusyError("resource close remains pending") from error


def drain_close_quarantine() -> None:
    """Synchronously retry the closed-set native Windows close registry."""

    _drain_windows_close_quarantine()


def _close_only_ticket(
    label: str,
    disposition: Literal["native-windows-handle", "directory-anchor"],
    resource: object,
) -> _PendingWindowsClose:
    """Construct one closed-set resource-only close ticket.

    The disposition, not a caller callback, selects the only permitted close.
    Integer descriptors and namespace-capable Delete=True owners cannot be
    represented here.
    """

    if not isinstance(label, str) or not label:
        raise ValueError("close quarantine label must be a non-empty string")
    if os.name != "nt":
        raise TypeError("close quarantine accepts only native Windows resources")
    if disposition == "native-windows-handle":
        if not isinstance(resource, _NativeWindowsHandle):
            raise TypeError("close quarantine rejects untyped integer descriptor ownership")
        if int(resource) in (0, _INVALID_HANDLE_VALUE):
            raise TypeError("close quarantine requires a live native Windows HANDLE")
    elif disposition == "directory-anchor":
        if not isinstance(resource, _DirectoryAnchor):
            raise TypeError("close quarantine requires a concrete directory anchor")
    else:
        raise TypeError("close quarantine disposition is invalid")
    return _PendingWindowsClose(label, disposition, resource)


def _close_close_only_ticket(ticket: _PendingWindowsClose) -> None:
    """Dispatch one validated ticket without accepting caller code."""

    if ticket.disposition == "native-windows-handle":
        if not isinstance(ticket.resource, _NativeWindowsHandle):
            raise TypeError("close quarantine native HANDLE wrapper is invalid")
        _windows_close_handle(ticket.resource)
        return
    if ticket.disposition == "directory-anchor" and isinstance(ticket.resource, _DirectoryAnchor):
        ticket.resource._close_without_quarantine()
        return
    raise TypeError("close quarantine ticket is not a permitted typed resource")


def _retain_close_ticket(ticket: _PendingWindowsClose) -> None:
    """Transfer one typed resource-only ticket to the close registry."""

    if not isinstance(ticket, _PendingWindowsClose):
        raise TypeError("close quarantine accepts only a resource-only ticket")
    # Re-run closed-set validation so direct construction cannot bypass the
    # private constructor's resource/disposition checks.
    _close_only_ticket(ticket.phase, ticket.disposition, ticket.resource)
    with _WINDOWS_CLOSE_QUARANTINE_LOCK:
        _WINDOWS_CLOSE_QUARANTINE.append(ticket)


def retain_close_failure(ticket: _PendingWindowsClose) -> None:
    """Compatibility import for the typed internal close-ticket contract.

    This intentionally no longer accepts ``(resource, closer, label)``. The
    public ``store.lock`` facade does not export it, so production callers
    cannot register an arbitrary namespace callback in the close-only queue.
    """

    _retain_close_ticket(ticket)


def _close_or_retain_windows_handle(label: str, handle: object) -> None:
    pending = _close_only_ticket(
        label,
        "native-windows-handle",
        handle,
    )
    try:
        _close_close_only_ticket(pending)
    except BaseException:
        _retain_close_ticket(pending)
        raise


def _windows_file_attribute_tag(handle: object) -> tuple[int, int]:
    info = _FILE_ATTRIBUTE_TAG_INFO()
    if not _KERNEL32.GetFileInformationByHandleEx(
        handle,
        _FILE_ATTRIBUTE_TAG_INFO_CLASS,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        raise _windows_api_error("GetFileInformationByHandleEx(FileAttributeTagInfo)")
    return int(info.FileAttributes), int(info.ReparseTag)


def _windows_file_id(handle: object) -> DirectoryIdentity:
    info = _FILE_ID_INFO()
    if not _KERNEL32.GetFileInformationByHandleEx(
        handle,
        _FILE_ID_INFO_CLASS,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        raise _windows_api_error("GetFileInformationByHandleEx(FileIdInfo)")
    file_id = bytes(info.FileId.Identifier)
    if not file_id or file_id == b"\0" * 16:
        raise ConflictError("Windows filesystem object returned an unusable file identity")
    return DirectoryIdentity(
        "windows-file-id-v1",
        int(info.VolumeSerialNumber),
        file_id,
    )


def _windows_handle_matches_stat(handle: object, expected: os.stat_result) -> bool:
    """Compare one live native HANDLE with the generation captured by stat.

    CPython's Windows ``st_dev`` and ``st_ino`` are the volume serial and the
    little-endian 128-bit file identifier returned by ``FileIdInfo``. Reading
    both values from the already-open delete HANDLE closes the path/open race:
    no later pathname observation can substitute for this comparison.
    """

    identity = _windows_file_id(handle)
    return identity.volume_or_device == int(expected.st_dev) and int.from_bytes(
        identity.file_id,
        "little",
        signed=False,
    ) == int(expected.st_ino)


def _windows_final_path(handle: object) -> Path:
    size = 512
    while size <= 1_048_576:
        buffer = ctypes.create_unicode_buffer(size)
        length = _KERNEL32.GetFinalPathNameByHandleW(
            handle,
            buffer,
            size,
            _VOLUME_NAME_DOS,
        )
        if length == 0:
            raise _windows_api_error("GetFinalPathNameByHandleW")
        if length < size - 1:
            value = buffer.value
            if not value:
                raise ConflictError("Windows directory returned an empty final path")
            return Path(value)
        size *= 2
    raise ConflictError("Windows directory final path is unavailable or unstable")


def _regular_file_identity(path: Path, *, label: str) -> os.stat_result:
    try:
        observed = path.lstat()
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise ConflictError(f"{label} physical identity is unavailable") from exc
    attributes = getattr(observed, "st_file_attributes", 0)
    if stat.S_ISLNK(observed.st_mode) or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
        raise ConflictError(f"{label} must be a physical regular file")
    if not stat.S_ISREG(observed.st_mode):
        raise ConflictError(f"{label} must be a regular file")
    return observed


def _delete_exact_regular_file(
    path: Path,
    expected_identity: os.stat_result,
    *,
    expected_bytes: bytes,
    label: str,
    close_phase: Literal["canonical", "temporary"],
) -> None:
    _before_exact_generation_unlink(path)
    if os.name != "nt":
        raise ConflictError(f"{label} deletion requires an explicit held POSIX guard")

    handle: object | None = None
    primary_error: BaseException | None = None
    disposition_applied = False
    try:
        handle = _windows_open_handle(
            path,
            open_reparse_point=True,
            delete_protect=True,
            delete_access=True,
            read_contents=True,
            # A staged file can already have a second hard link that a live
            # writer leases read/write/delete.  This exact handle validates
            # and applies Delete=True to *its* inode, so it must coexist with
            # that lease; a narrow share mode would make reserved-stage
            # recovery spuriously busy after publication.
            share_mode=_FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE,
        )
        attributes, _ = _windows_file_attribute_tag(handle)
        if attributes & _FILE_ATTRIBUTE_REPARSE_POINT:
            raise ConflictError(f"{label} must be a physical regular file")
        if attributes & _FILE_ATTRIBUTE_DIRECTORY:
            raise ConflictError(f"{label} must be a regular file")
        if not _windows_handle_matches_stat(handle, expected_identity):
            raise ConflictError(f"{label} opened generation changed before exact deletion")
        observed = _regular_file_identity(path, label=label)
        if not os.path.samestat(observed, expected_identity):
            raise ConflictError(f"{label} generation changed before exact deletion")
        if _windows_read_handle(handle) != expected_bytes:
            raise ConflictError(f"{label} bytes changed before exact deletion")
        disposition = _FILE_DISPOSITION_INFO(True)
        if not _KERNEL32.SetFileInformationByHandle(
            handle,
            _FILE_DISPOSITION_INFO_CLASS,
            ctypes.byref(disposition),
            ctypes.sizeof(disposition),
        ):
            raise _windows_api_error("SetFileInformationByHandle(FileDispositionInfo)")
        disposition_applied = True
    except FileNotFoundError as exc:
        primary_error = exc
    except ConflictError as exc:
        primary_error = exc
    except OSError as exc:
        if _is_windows_sharing_violation(exc):
            wrapped = _ExactGenerationBusyError(f"{label} exact generation deletion is temporarily busy")
        else:
            wrapped = ConflictError(f"{label} exact generation deletion cannot be sealed")
        wrapped.__cause__ = exc
        primary_error = wrapped
    finally:
        if handle is not None:
            try:
                _windows_close_handle(handle)
            except OSError as close_error:
                if disposition_applied:
                    # This handle still determines whether Delete=True becomes
                    # terminal. It leaves this helper as typed transaction
                    # state, never as a close-only ticket or an exception-only
                    # resource that a caller can accidentally discard.
                    pending = _WindowsPendingExactRemoval(
                        path,
                        expected_identity,
                        expected_bytes,
                        label,
                        handle,
                    )
                    pending_error = _WindowsDeleteClosePendingError(pending)
                    pending_error.__cause__ = close_error
                    primary_error = pending_error
                else:
                    # No Delete=True disposition was applied, so this native
                    # HANDLE is resource-only cleanup authority. Transfer it
                    # even when validation already supplied the primary error;
                    # otherwise preserving that primary silently leaks its
                    # live HANDLE and loses the only retryable owner.
                    try:
                        _retain_close_ticket(
                            _close_only_ticket(
                                close_phase,
                                "native-windows-handle",
                                handle,
                            )
                        )
                    except BaseException as retention_error:
                        close_error = _add_cleanup_error(
                            close_error,
                            retention_error,
                            "native HANDLE close-ticket retention also failed",
                        )
                    if primary_error is None:
                        wrapped = ConflictError(f"{label} exact generation deletion handle cannot close")
                        wrapped.__cause__ = close_error
                        primary_error = wrapped
                    else:
                        primary_error = _add_cleanup_error(
                            primary_error,
                            close_error,
                            "exact-generation validation HANDLE close also failed and was retained",
                        )
        if primary_error is not None:
            raise primary_error
    try:
        _regular_file_identity(path, label=label)
    except FileNotFoundError:
        return
    raise ConflictError(f"{label} name was replaced during exact generation deletion")


def _windows_anchor_refresh(handle: object) -> tuple[DirectoryIdentity, Path]:
    attributes, _ = _windows_file_attribute_tag(handle)
    if not attributes & _FILE_ATTRIBUTE_DIRECTORY:
        raise ConflictError("Windows directory anchor is no longer a directory")
    return _windows_file_id(handle), _windows_final_path(handle)


def _open_windows_anchor(
    path: Path,
    *,
    reject_reparse: bool,
    delete_protect: bool = False,
) -> _DirectoryAnchor:
    probe: object | None = None
    handle: object | None = None
    first_close_error: BaseException | None = None
    primary_error: BaseException | None = None
    anchor: _DirectoryAnchor | None = None
    try:
        if reject_reparse:
            probe = _windows_open_handle(path, open_reparse_point=True)
            attributes, _ = _windows_file_attribute_tag(probe)
            if not attributes & _FILE_ATTRIBUTE_DIRECTORY:
                raise ConflictError(f"{path} is not an existing directory")
            if attributes & _FILE_ATTRIBUTE_REPARSE_POINT:
                raise ConflictError(f"{path} must not be a reparse directory")

        handle = _windows_open_handle(
            path,
            open_reparse_point=False,
            delete_protect=delete_protect,
        )
        attributes, _ = _windows_file_attribute_tag(handle)
        if not attributes & _FILE_ATTRIBUTE_DIRECTORY:
            raise ConflictError(f"{path} is not an existing directory")
        identity, final_path = _windows_anchor_refresh(handle)

        if reject_reparse:
            probe_identity = _windows_file_id(probe)
            if probe_identity != identity:
                raise ConflictError(f"{path} physical identity changed between no-follow probe and followed open")
            try:
                _close_or_retain_windows_handle("anchor-probe", probe)
            except BaseException as close_error:
                first_close_error = close_error
                probe = None
            else:
                probe = None

        if first_close_error is None:
            anchor = _DirectoryAnchor(
                identity,
                final_path,
                handle,
                _windows_anchor_refresh,
                _windows_close_handle,
                delete_protected=delete_protect,
            )
            handle = None
    except FileNotFoundError as exc:
        primary_error = exc
    except ConflictError as exc:
        primary_error = exc
    except OSError as exc:
        primary_error = ConflictError(f"{path} is not an existing directory")
        primary_error.__cause__ = exc
        primary_error.__suppress_context__ = True
    except BaseException as exc:
        primary_error = exc
    finally:
        for candidate in (probe, handle):
            if candidate is None:
                continue
            try:
                _close_or_retain_windows_handle("anchor-candidate", candidate)
            except BaseException as close_error:
                if first_close_error is None:
                    first_close_error = close_error
    if primary_error is not None:
        _raise_primary_with_cleanup(primary_error, first_close_error)
    if first_close_error is not None:
        raise first_close_error
    assert anchor is not None
    return anchor


def _posix_identity(observed: os.stat_result) -> DirectoryIdentity:
    if observed.st_dev < 0 or observed.st_ino <= 0:
        raise ConflictError("POSIX directory returned an unusable file identity")
    try:
        file_id = int(observed.st_ino).to_bytes(16, "big", signed=False)
    except OverflowError as exc:
        raise ConflictError("POSIX directory file identity is too large") from exc
    return DirectoryIdentity("posix-dev-inode-v1", int(observed.st_dev), file_id)


def _posix_final_path(
    file_descriptor: int,
    fallback: Path,
    *,
    delete_protect: bool = False,
) -> Path:
    proc_path = Path(f"/proc/self/fd/{file_descriptor}")
    try:
        value = os.readlink(proc_path)
    except OSError:
        return fallback
    deleted = value.endswith(" (deleted)")
    if deleted and delete_protect:
        raise ConflictError("POSIX directory anchor was deleted")
    if deleted:
        value = value[: -len(" (deleted)")]
    return Path(value)


def _posix_anchor_refresh_factory(
    fallback: Path,
    *,
    delete_protect: bool = False,
) -> Callable[[object], tuple[DirectoryIdentity, Path]]:
    def refresh(file_descriptor: object) -> tuple[DirectoryIdentity, Path]:
        observed = os.fstat(int(file_descriptor))
        if not stat.S_ISDIR(observed.st_mode):
            raise ConflictError("POSIX directory anchor is no longer a directory")
        if delete_protect and observed.st_nlink <= 0:
            raise ConflictError("POSIX directory anchor is unlinked")
        return _posix_identity(observed), _posix_final_path(
            int(file_descriptor),
            fallback,
            delete_protect=delete_protect,
        )

    return refresh


def _open_posix_anchor(
    path: Path,
    *,
    reject_reparse: bool,
    delete_protect: bool = False,
) -> _DirectoryAnchor:
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    if not directory_flag:
        raise ConflictError("platform cannot provide a directory anchor")
    flags = os.O_RDONLY | directory_flag
    if reject_reparse:
        nofollow_flag = getattr(os, "O_NOFOLLOW", 0)
        if not nofollow_flag:
            raise ConflictError("platform cannot reject reparse directories")
        flags |= nofollow_flag
    try:
        file_descriptor = os.open(path, flags)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise ConflictError(f"{path} is not an existing directory") from exc
    try:
        refresh = _posix_anchor_refresh_factory(
            Path(os.path.realpath(path)),
            delete_protect=delete_protect,
        )
        identity, final_path = refresh(file_descriptor)
        return _DirectoryAnchor(
            identity,
            final_path,
            file_descriptor,
            refresh,
            lambda descriptor: os.close(int(descriptor)),
            delete_protected=delete_protect,
        )
    except BaseException as primary_error:
        try:
            os.close(file_descriptor)
        except BaseException as cleanup_error:
            raise primary_error from cleanup_error
        raise


def _open_directory_anchor(
    path: Path,
    *,
    reject_reparse: bool = False,
    delete_protect: bool = False,
) -> _DirectoryAnchor:
    if os.name == "nt":
        # Windows deliberately has no lexical/stat-only fallback. The held
        # CreateFileW handle is the physical identity and replacement fence.
        return _open_windows_anchor(
            path,
            reject_reparse=reject_reparse,
            delete_protect=delete_protect,
        )
    return _open_posix_anchor(
        path,
        reject_reparse=reject_reparse,
        delete_protect=delete_protect,
    )


def open_registered_root_anchor(path: Path, *, delete_protect: bool) -> DirectoryAnchor:
    """Open the physical anchor for an explicitly registered root.

    Registered roots may themselves be junctions, so this purpose-named seam
    follows the root alias while retaining the physical identity handle.
    Nested member aliases remain the caller's responsibility to reject.

    Args:
        path: Registered root path whose physical directory is opened.
        delete_protect: Whether the held anchor prevents replacement while open.

    Returns:
        A physical directory anchor for the registered root.
    """

    return _open_directory_anchor(path, reject_reparse=False, delete_protect=delete_protect)


TRANSACTION_GUARD_NAME = ".store-transaction-v2.guard"


@dataclass(frozen=True)
class StagePin:
    """The exact private generation owned by one transaction."""

    name: str
    identity: os.stat_result
    data: bytes


@dataclass(frozen=True)
class TransactionEffect:
    """An in-memory receipt recorded immediately after its namespace effect."""

    disposition: str
    name: str
    identity: os.stat_result | None


def _after_stage_opened(_name: str, _descriptor: int) -> None:
    """Test seam after O_EXCL receipt and before fstat/write."""


class DirectoryTransaction:
    """One linear transaction over one already-opened physical directory.

    ``publish`` is commit-on-link: after its hard link succeeds, abort and
    close paths never delete that final name.  A retry adopts an equal final,
    fsyncs it, and only then clears a same-byte private stage.
    """

    guard_name = TRANSACTION_GUARD_NAME

    def __init__(self, anchor: DirectoryAnchor) -> None:
        self._anchor = anchor
        self._guard_context = None
        self._guard: DirectoryMutationGuard | None = None
        self._retained_guard: DirectoryMutationGuard | None = None
        self._reservation: _FullOwnerReservation | None = None
        self._admission: _DirectoryAdmissionLease | None = None
        self._anchor_hold = False
        self._pending_windows_removals: list[_WindowsPendingExactRemoval] = []
        self._full_owner_terminal = False
        self._stages: dict[str, StagePin] = {}
        self.effects: list[TransactionEffect] = []
        self._entered = False
        self._exit_status = TransactionExitStatus("released")

    @property
    def exit_status(self) -> TransactionExitStatus:
        """The most recent guard-release outcome.

        A caller must not treat an exception from ``__exit__`` as merely a
        close failure: ``unknown`` retains a safe full protocol owner, while
        ``terminal_uncertain`` means a descriptor close could not be proven but
        its integer is no longer retry authority.
        """

        return self._exit_status

    def __enter__(self) -> DirectoryTransaction:
        if self._entered:
            raise ConflictError("directory transaction is already active")
        if self._retained_guard is not None or self._pending_windows_removals:
            raise ConflictError("directory transaction has a retained full owner")
        if self._reservation is not None and not self._reservation.released:
            raise ConflictError("directory transaction full-owner reservation remains live")
        # Public transaction entry is the anchor-level safe point for every
        # retained owner. It runs before a new slot is reserved or any
        # namespace effect becomes possible.
        drain_retained_transaction_owners()
        _drain_windows_close_quarantine()
        identity = getattr(self._anchor, "identity", None)
        if not isinstance(identity, DirectoryIdentity):
            raise ConflictError("directory transaction anchor has no physical identity")
        # Identity is retained as metadata, while the nonce makes this one
        # operation's capacity reservation unique. A concurrent cooperative
        # transaction may reserve and then serialize at the admission/OS guard;
        # it must not be rejected merely because it targets this directory.
        reservation = _reserve_full_owner(_full_owner_key("directory-transaction", identity, secrets.token_hex(16)))
        self._reservation = reservation
        try:
            self._admission = _acquire_directory_admission(identity)
            self._retain_anchor_hold()
            context = self._anchor.acquire_mutation_guard(self.guard_name)
            guard = context.__enter__()
            self._guard_context = context
            self._guard = guard
            self._entered = True
            self._exit_status = TransactionExitStatus("active")
            return self
        except BaseException as primary_error:
            cleanup_error: BaseException | None = None
            try:
                self._release_anchor_hold()
            except BaseException as error:
                cleanup_error = _add_cleanup_error(
                    cleanup_error,
                    error,
                    "transaction-entry anchor-chain release failed",
                )

            admission = self._admission
            try:
                _release_directory_admission(admission)
            except BaseException as error:
                cleanup_error = _add_cleanup_error(
                    cleanup_error,
                    error,
                    "transaction-entry admission release failed",
                )
            if admission is None or not admission.held:
                self._admission = None

            # A failed entry never transferred this reservation to a retained
            # full owner. Free its capacity once every acquired resource has
            # reached terminal state. If cleanup itself remains non-terminal,
            # transfer this transaction so the next registry drain can finish
            # the exact admission/anchor release rather than stranding an
            # ownerless capacity slot.
            if not self._anchor_hold and self._admission is None:
                try:
                    _release_full_owner(reservation)
                except BaseException as error:
                    cleanup_error = _add_cleanup_error(
                        cleanup_error,
                        error,
                        "transaction-entry reservation release failed",
                    )
                    if not reservation.released:
                        try:
                            _transfer_full_owner(reservation, self)
                        except BaseException as transfer_error:
                            cleanup_error = _add_cleanup_error(
                                cleanup_error,
                                transfer_error,
                                "transaction-entry owner transfer also failed",
                            )
                else:
                    self._reservation = None
            else:
                try:
                    _transfer_full_owner(reservation, self)
                except BaseException as error:
                    cleanup_error = _add_cleanup_error(
                        cleanup_error,
                        error,
                        "transaction-entry owner transfer also failed",
                    )
            _raise_primary_with_cleanup(primary_error, cleanup_error)

    def _retain_anchor_hold(self) -> None:
        retain = getattr(self._anchor, "_retain_transaction_hold", None)
        if callable(retain):
            retain()
            self._anchor_hold = True

    def _release_anchor_hold(self) -> None:
        if not self._anchor_hold:
            return
        self._anchor_hold = False
        release = getattr(self._anchor, "_release_transaction_hold", None)
        if callable(release):
            release()

    def _transfer_retained_full_owner(self) -> None:
        reservation = self._reservation
        if reservation is None:
            raise RuntimeError("retained directory transaction has no reservation")
        _transfer_full_owner(reservation, self)

    def _release_terminal_full_owner(self) -> None:
        if self._entered or self._retained_guard is not None or self._pending_windows_removals:
            return

        # Namespace authority is terminal before resource release begins.
        # Attempt both the complete anchor-chain release and admission release
        # even when one close fails. Anchor close failures are retained by the
        # close-only registry; an admission failure remains a full-owner state.
        first_error: BaseException | None = None
        try:
            self._release_anchor_hold()
        except BaseException as error:
            first_error = _add_cleanup_error(first_error, error, "transaction anchor-chain release failed")

        admission = self._admission
        try:
            _release_directory_admission(admission)
        except BaseException as error:
            first_error = _add_cleanup_error(first_error, error, "transaction admission release failed")
        if admission is None or not admission.held:
            self._admission = None

        if not self._anchor_hold and self._admission is None:
            self._full_owner_terminal = True
            _release_full_owner(self._reservation)
            self._reservation = None
        if first_error is not None:
            raise first_error

    def _require_active(self, *, allow_pending: bool = False) -> DirectoryMutationGuard:
        if not self._entered or self._guard is None:
            raise ConflictError("directory transaction is not active")
        if self._pending_windows_removals and not allow_pending:
            raise ConflictError("directory transaction exact deletion remains pending")
        return self._guard

    def retry_guard_release(self) -> None:
        """Retry only a safely retained guard, never a terminal-uncertain descriptor."""

        guard = self._retained_guard
        if guard is None:
            return
        try:
            guard.retry_release()
        except BaseException:
            self._exit_status = TransactionExitStatus("unknown")
            raise
        self._retained_guard = None
        self._exit_status = TransactionExitStatus(
            guard._release_state,
            guard._close_only_transferred,
        )
        if not self._pending_windows_removals:
            self._release_terminal_full_owner()

    def _retain_windows_exact_removal(
        self,
        pending: _WindowsPendingExactRemoval,
        *,
        name: str,
        effect_disposition: Literal["unlinked", "stage_removed"],
    ) -> None:
        """Attach a disposed Windows handle to this transaction before raising.

        The exception carrying ``pending`` is only the handoff mechanism from
        the low-level helper. From here onward this transaction and its reserved
        registry slot are the reachable full owner.
        """

        if pending.handle is None:
            raise ConflictError("directory transaction pending deletion has no handle")
        if pending.path.name != name:
            raise ConflictError("directory transaction pending deletion name changed")
        if self._pending_windows_removals:
            raise ConflictError("directory transaction already has a pending exact deletion")
        pending.effect_disposition = effect_disposition
        self._pending_windows_removals.append(pending)

    def _retry_pending_windows_removals(self) -> bool:
        """Close and prove every retained Delete=True effect under this guard."""

        self._require_active(allow_pending=True)
        while self._pending_windows_removals:
            pending = self._pending_windows_removals[0]
            if pending.handle is not None:
                try:
                    _windows_close_handle(pending.handle)
                except BaseException:
                    return False
                pending.handle = None
            try:
                self._anchor.verify_unchanged()
                _identity, final_path = self._anchor.refresh()
            except BaseException:
                # Closing the Delete=True handle consumed this transaction's
                # last physical authority over the exact generation.  If the
                # anchored path can no longer be proved, retaining a handleless
                # pending entry can never make progress and would block every
                # later STORE operation.  Preserve the conflict, but make the
                # owner terminal before releasing it.
                self._pending_windows_removals.pop(0)
                self._full_owner_terminal = True
                raise
            current_path = final_path / pending.path.name
            try:
                observed = _regular_file_identity(current_path, label=pending.label)
            except FileNotFoundError:
                # Close plus observed absence is the terminal namespace effect.
                # Receipt it before the directory durability step, exactly as
                # ordinary unlink receipts do.
                disposition = pending.effect_disposition
                if disposition is None:  # pragma: no cover - retained handoff validates it
                    raise RuntimeError("pending Windows deletion has no effect disposition")
                self.effects.append(TransactionEffect(disposition, pending.path.name, pending.identity))
                self._pending_windows_removals.pop(0)
                self._anchor.fsync()
                try:
                    _regular_file_identity(current_path, label=pending.label)
                except FileNotFoundError:
                    continue
                raise ConflictError("directory transaction final name reappeared during deletion")
            if self._same_generation(pending.identity, observed):
                # Another compatible handle still keeps the delete-pending
                # generation live. The full owner remains registered; this is
                # not a close-only resource and cannot be quarantined.
                return False
            self._pending_windows_removals.pop(0)
            self._full_owner_terminal = True
            raise ConflictError("directory transaction final name was substituted during deletion")
        return True

    def _retry_full_owner_release(self) -> bool:
        """Registry protocol: synchronously drive one retained transaction terminal."""

        if self._entered:
            return False
        if self._retained_guard is not None:
            self.retry_guard_release()
        if not self._pending_windows_removals:
            self._release_terminal_full_owner()
            return True
        context = self._anchor.acquire_mutation_guard(self.guard_name)
        guard = context.__enter__()
        self._guard_context = context
        self._guard = guard
        self._entered = True
        self._exit_status = TransactionExitStatus("active")
        primary_error: BaseException | None = None
        try:
            self._retry_pending_windows_removals()
        except BaseException as error:
            primary_error = error
        try:
            self.__exit__(
                type(primary_error) if primary_error is not None else None,
                primary_error,
                primary_error.__traceback__ if primary_error is not None else None,
            )
        except BaseException as cleanup_error:
            if primary_error is None:
                primary_error = cleanup_error
            elif cleanup_error is not primary_error:
                primary_error = _add_cleanup_error(
                    primary_error, cleanup_error, "retained transaction close also failed"
                )
        if primary_error is not None:
            raise primary_error
        return not self._pending_windows_removals and self._retained_guard is None

    @staticmethod
    def _same_generation(left: os.stat_result, right: os.stat_result) -> bool:
        return os.path.samestat(left, right)

    def _read_exact(self, name: str, expected: StagePin, *, label: str) -> os.stat_result:
        data, identity = self._anchor.read_regular_file_with_identity(name)
        if data != expected.data or not self._same_generation(expected.identity, identity):
            raise ConflictError(f"directory transaction {label} generation changed")
        return identity

    def _stage_owned_private(
        self,
        target_name: str,
        data: bytes,
        *,
        temporary_name: str | None = None,
    ) -> StagePin:
        """Create one private generation with ownership from ``O_EXCL``.

        The successful exclusive open is recorded immediately in this owner,
        before fstat, writes, or descriptor fsync.  A pre-pin failure leaves
        deterministic reserved recovery state rather than invoking a second
        publication or cleanup protocol.
        """

        anchor = self._anchor
        require_name = getattr(anchor, "_require_member_name", None)
        effect_path = getattr(anchor, "_effect_final_path", None)
        member_identity = getattr(anchor, "_member_identity", None)
        unlink_member = getattr(anchor, "_unlink_member", None)
        flush = getattr(anchor, "_fsync_directory", None)
        refresh = getattr(anchor, "refresh", None)
        handle = getattr(anchor, "_handle", None)
        if not all(
            callable(item) for item in (require_name, effect_path, member_identity, unlink_member, flush, refresh)
        ):
            raise ConflictError("directory transaction anchor lacks owned staging support")
        require_name(target_name)
        _identity, final_path = refresh()
        temporary = temporary_name or f".{target_name}.{secrets.token_hex(16)}.tmp"
        descriptor: int | None = None
        opened_identity: os.stat_result | None = None
        primary_error: BaseException | None = None
        try:
            with effect_path(final_path) as protected_path:
                flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
                if os.name == "nt":
                    descriptor = os.open(protected_path / temporary, flags, 0o600)
                else:
                    nofollow = getattr(os, "O_NOFOLLOW", 0)
                    if not nofollow or os.open not in os.supports_dir_fd or handle is None:
                        raise ConflictError("platform cannot write an anchored regular file")
                    descriptor = os.open(temporary, flags | nofollow, 0o600, dir_fd=int(handle))
                # Ownership starts at the exclusive create, not after the
                # later fstat/write/fsync sequence.  ``None`` is intentional:
                # a fstat failure still has a recorded, deterministic cleanup
                # disposition for this exact temporary name.
                self.effects.append(TransactionEffect("stage_opened", temporary, None))
                _after_stage_opened(temporary, descriptor)
                opened_identity = os.fstat(descriptor)
                if not stat.S_ISREG(opened_identity.st_mode):
                    raise ConflictError("directory transaction private stage is not regular")
                remaining = memoryview(data)
                while remaining:
                    written = os.write(descriptor, remaining)
                    if written < 1:
                        raise OSError("directory transaction private stage write made no progress")
                    remaining = remaining[written:]
                os.fsync(descriptor)
                closing_descriptor = descriptor
                descriptor = None
                os.close(closing_descriptor)
                observed_data, observed_identity = anchor._read_regular_file_with_identity(temporary, protected_path)
                if observed_data != data or not self._same_generation(opened_identity, observed_identity):
                    raise ConflictError("directory transaction private stage changed before pin")
            pin = StagePin(name=temporary, identity=opened_identity, data=data)
        except BaseException as error:
            primary_error = error
            cleanup_error: BaseException | None = None
            if descriptor is not None:
                closing_descriptor = descriptor
                descriptor = None
                try:
                    os.close(closing_descriptor)
                except BaseException as close_error:
                    # An integer descriptor is never safe retry state after a
                    # failed close: it may already have been recycled. The
                    # reserved stage name is the durable recovery owner.
                    cleanup_error = close_error
            # A failed pre-metadata stage is deliberate recovery state. The
            # random 32-hex token reserves this exact name for a later guarded
            # transaction; it must not be guessed from payload bytes or
            # asynchronously cleaned up.  A nonconforming private-looking
            # name is foreign residue and is ignored by recovery below.
            if opened_identity is not None:
                self.effects.append(TransactionEffect("stage_abandoned", temporary, opened_identity))
            if cleanup_error is not None:
                _raise_primary_with_cleanup(primary_error, cleanup_error)
            raise
        self._stages[pin.name] = pin
        self.effects.append(TransactionEffect("staged", pin.name, pin.identity))
        # This directory flush is deliberately outside the pre-pin abort path:
        # ambiguity after a complete stage leaves its retained inode pin for an
        # exact retry rather than deleting it speculatively.
        anchor.fsync()
        self._read_exact(pin.name, pin, label="stage")
        return pin

    @staticmethod
    def _is_reserved_stage_name(name: str, target_name: str) -> bool:
        prefix = f".{target_name}."
        suffix = ".tmp"
        if not name.startswith(prefix) or not name.endswith(suffix):
            return False
        token = name[len(prefix) : -len(suffix)]
        return len(token) == 32 and all(character in "0123456789abcdef" for character in token)

    @staticmethod
    def _replacement_stage_name(target_name: str, expected: bytes) -> str:
        """Return one durable desired-stage name bound to its predecessor."""

        expected_digest = sha256(expected).hexdigest()
        return f".{target_name}.replace-{expected_digest}-{secrets.token_hex(16)}.tmp"

    @staticmethod
    def _is_reserved_replacement_stage_name(name: str, target_name: str, expected: bytes) -> bool:
        """Whether ``name`` is this exact predecessor's recovery stage."""

        return (
            DirectoryTransaction._replacement_stage_predecessor_digest(name, target_name)
            == sha256(expected).hexdigest()
        )

    @staticmethod
    def _replacement_stage_predecessor_digest(name: str, target_name: str) -> str | None:
        """Return the predecessor digest bound into a replacement stage name."""

        prefix = f".{target_name}.replace-"
        suffix = ".tmp"
        if not name.startswith(prefix) or not name.endswith(suffix):
            return None
        digest, separator, token = name[len(prefix) : -len(suffix)].partition("-")
        if separator != "-" or len(digest) != 64 or len(token) != 32:
            return None
        if not all(character in "0123456789abcdef" for character in digest + token):
            return None
        return digest

    def _stage_replacement(self, target_name: str, expected: bytes, desired: bytes) -> StagePin:
        """Stage desired bytes under the immutable predecessor they replace."""

        return self._stage_owned_private(
            target_name,
            desired,
            temporary_name=self._replacement_stage_name(target_name, expected),
        )

    def _link_with_immediate_receipt(
        self, stage: StagePin, final_name: str, guard: DirectoryMutationGuard
    ) -> os.stat_result:
        """Perform the hard link with a receipt before any later fallible work."""

        anchor = self._anchor
        require_name = getattr(anchor, "_require_member_name", None)
        validate_guard = getattr(anchor, "_validate_mutation_guard", None)
        effect_path = getattr(anchor, "_effect_final_path", None)
        member_identity = getattr(anchor, "_member_identity", None)
        link_member = getattr(anchor, "_link_member", None)
        refresh = getattr(anchor, "refresh", None)
        if not all(
            callable(item)
            for item in (require_name, validate_guard, effect_path, member_identity, link_member, refresh)
        ):
            raise ConflictError("directory transaction anchor lacks immediate link support")
        require_name(stage.name)
        require_name(final_name)
        validate_guard(guard)
        anchor.verify_unchanged()
        _identity, final_path = refresh()
        with effect_path(final_path) as protected_path:
            if not self._same_generation(stage.identity, member_identity(stage.name, protected_path)):
                raise ConflictError("directory transaction stage changed before link publication")
            link_member(stage.name, final_name, protected_path)
            # Link is now public.  Do not defer this record behind an identity
            # probe, handle close, or flush that can fail after the effect.
            self.effects.append(TransactionEffect("linked", final_name, stage.identity))
            final_identity = member_identity(final_name, protected_path)
            if not self._same_generation(stage.identity, final_identity):
                raise ConflictError("directory transaction final changed during publication")
        return final_identity

    def stage(self, target_name: str, data: bytes) -> StagePin:
        """Create and pin a private generation before any public effect."""

        self._require_active()
        if not isinstance(data, bytes):
            raise TypeError("directory transaction stage data must be bytes")
        return self._stage_owned_private(target_name, data)

    def verify_stage(self, stage: StagePin) -> None:
        """Re-prove a retained private inode after an externally visible seam."""

        self._require_active()
        if self._stages.get(stage.name) != stage:
            raise ConflictError("directory transaction stage pin is not owned")
        self._read_exact(stage.name, stage, label="stage")

    def _publish(self, stage: StagePin, final_name: str, *, adopt_existing: bool) -> os.stat_result:
        """Publish or adopt an equal immutable final and establish durability.

        The in-memory ``linked`` receipt is appended in the same straight-line
        path immediately after a successful link, before any verification or
        directory fsync that may fail.  Any such failure leaves the final in
        place for an identical retry to adopt.
        """

        guard = self._require_active()
        known = self._stages.get(stage.name)
        if known != stage:
            raise ConflictError("directory transaction stage pin is not owned")
        self._read_exact(stage.name, stage, label="stage")
        try:
            final_identity = self._link_with_immediate_receipt(stage, final_name, guard)
        except FileExistsError:
            if not adopt_existing:
                raise
            final_data, final_identity = self._anchor.read_regular_file_with_identity(final_name)
            if final_data != stage.data:
                raise ConflictError("directory transaction final already binds different bytes")
            self.effects.append(TransactionEffect("adopted", final_name, final_identity))
        final_pin = StagePin(final_name, final_identity, stage.data)
        self._read_exact(final_name, final_pin, label="final")
        # A failed flush makes visibility ambiguous, not reversible.  The
        # exact retry above will re-read and fsync this final.
        self._anchor.fsync()
        self._read_exact(final_name, final_pin, label="final")
        self.effects.append(TransactionEffect("durable", final_name, final_identity))
        return final_identity

    def adopt_or_publish(self, stage: StagePin, final_name: str) -> os.stat_result:
        """Publish or adopt an equal immutable final and establish durability."""

        return self._publish(stage, final_name, adopt_existing=True)

    def publish_exact(self, target_name: str, data: bytes) -> None:
        """Publish immutable bytes without retaining a stage after a collision.

        A stage is retained only after this transaction recorded its own public
        link.  Before that point a conflicting final proves this transaction
        made no public effect, so the exact private generation is removed
        rather than becoming residue for an unrelated replacement operation.
        """

        stage = self.stage(target_name, data)
        try:
            self.adopt_or_publish(stage, target_name)
        except BaseException as primary_error:
            linked = any(effect.disposition == "linked" and effect.name == target_name for effect in self.effects)
            if linked:
                raise
            try:
                self.discard_stage(stage, missing_ok=True)
            except BaseException as cleanup_error:
                _raise_primary_with_cleanup(primary_error, cleanup_error)
            raise
        self.recover_private_stages(target_name, data)

    def remove_exact_final(self, name: str, expected_identity: os.stat_result, data: bytes) -> None:
        """Unlink one exact final under this guard, then establish durability.

        The in-memory unlink receipt is recorded directly after the namespace
        effect and before the directory flush.  It does not arrange a deferred
        retry callback: a later caller observes the resulting namespace.
        """

        self._require_active()
        observed_data, identity = self._anchor.read_regular_file_with_identity(name)
        if observed_data != data or not self._same_generation(expected_identity, identity):
            raise ConflictError("directory transaction final generation changed")
        # ``DirectoryAnchor`` intentionally keeps its no-follow effect path
        # private.  The concrete anchor is the only implementation used by
        # STORE; retain the protocol check so a test double cannot silently
        # downgrade this exact-generation operation.
        effect_path = getattr(self._anchor, "_effect_final_path", None)
        unlink_member = getattr(self._anchor, "_unlink_member", None)
        flush = getattr(self._anchor, "_fsync_directory", None)
        refresh = getattr(self._anchor, "refresh", None)
        if not all(callable(item) for item in (effect_path, unlink_member, flush, refresh)):
            raise ConflictError("directory transaction anchor lacks exact unlink support")
        _directory_identity, final_path = refresh()
        with effect_path(final_path) as protected_path:
            try:
                unlink_member(name, expected_identity, data, protected_path)
            except _WindowsDeleteClosePendingError as pending_error:
                self._retain_windows_exact_removal(
                    pending_error.pending,
                    name=name,
                    effect_disposition="unlinked",
                )
                raise ConflictError("directory transaction final deletion handle remains pending") from pending_error
            self.effects.append(TransactionEffect("unlinked", name, expected_identity))
            flush(protected_path)
        self._anchor.verify_unchanged()

    def discard_stage(self, stage: StagePin, *, missing_ok: bool = False) -> None:
        """Remove only the exact private generation after final durability."""

        guard = self._require_active()
        if self._stages.get(stage.name) != stage:
            raise ConflictError("directory transaction stage pin is not owned")
        try:
            self._anchor.remove_exact_generation(
                stage.name,
                stage.identity,
                stage.data,
                guard=guard,
            )
        except _WindowsDeleteClosePendingError as pending_error:
            self._retain_windows_exact_removal(
                pending_error.pending,
                name=stage.name,
                effect_disposition="stage_removed",
            )
            raise ConflictError("directory transaction stage deletion handle remains pending") from pending_error
        except FileNotFoundError:
            if not missing_ok:
                raise
        except _ExactGenerationBusyError:
            raise ConflictError("directory transaction stage cleanup is temporarily busy") from None
        else:
            self.effects.append(TransactionEffect("stage_removed", stage.name, stage.identity))
        if stage.name not in self._stages:
            return
        # ``FileNotFoundError`` with ``missing_ok`` is a terminal observed
        # absence. Every other failure retains ownership for a later explicit
        # transaction/recovery handoff.
        self._stages.pop(stage.name, None)

    def recover_private_stages(self, target_name: str, data: bytes) -> None:
        """Synchronously reconcile owned pre-metadata stage residues.

        The final must bind ``data`` and be durably re-proven before any
        cleanup.  A conforming reserved stage name was created by this
        transaction protocol but never published, so its bytes need not match
        a later retry's payload: it is safe to remove its exact generation.
        Names outside the unguessable reserved pattern remain foreign and are
        ignored.
        """

        self._require_active()
        final_data, final_identity = self._anchor.read_regular_file_with_identity(target_name)
        if final_data != data:
            raise ConflictError("directory transaction final recovery bytes differ")
        # An existing content-addressed final may be this process's ambiguous
        # post-link generation. Re-establish directory durability before
        # interpreting it as an idempotent success or clearing any stage pin.
        self._anchor.fsync()
        verified_data, verified_identity = self._anchor.read_regular_file_with_identity(target_name)
        if verified_data != data or not self._same_generation(final_identity, verified_identity):
            raise ConflictError("directory transaction final changed during recovery")
        for name in self._anchor.list_names():
            if not self._is_reserved_stage_name(name, target_name):
                continue
            staged_data, staged_identity = self._anchor.read_regular_file_with_identity(name)
            self._stages[name] = StagePin(name, staged_identity, staged_data)
            self.discard_stage(self._stages[name])

    def _reserved_stages_for_replacement(self, target_name: str, expected: bytes) -> tuple[StagePin, ...]:
        """Inventory all target replacement stages, rejecting other predecessors."""

        stages: list[StagePin] = []
        predecessor_digests: set[str] = set()
        for name in sorted(self._anchor.list_names()):
            predecessor_digest = self._replacement_stage_predecessor_digest(name, target_name)
            if predecessor_digest is None:
                continue
            data, identity = self._anchor.read_regular_file_with_identity(name)
            predecessor_digests.add(predecessor_digest)
            stages.append(StagePin(name, identity, data))
        if predecessor_digests and predecessor_digests != {sha256(expected).hexdigest()}:
            raise ConflictError("directory transaction replacement stages bind different predecessors")
        for stage in stages:
            self._stages[stage.name] = stage
        return tuple(stages)

    def _revalidate_durable_final(self, target_name: str, data: bytes) -> None:
        """Re-establish the exact durable final before private-stage cleanup."""

        observed_data, identity = self._anchor.read_regular_file_with_identity(target_name)
        if observed_data != data:
            raise ConflictError("directory transaction final recovery bytes differ")
        self._anchor.fsync()
        verified_data, verified_identity = self._anchor.read_regular_file_with_identity(target_name)
        if verified_data != data or not self._same_generation(identity, verified_identity):
            raise ConflictError("directory transaction final changed during recovery")

    def replace_or_recover(self, target_name: str, expected: bytes, desired: bytes) -> None:
        """Replace one mutable final, or finish an exact desired-stage retry.

        Replacement stages are the sole durable recovery state for this
        mutable operation. They carry the SHA-256 of ``expected`` in their
        private, physically anchored name, so a desired stage cannot authorize
        a different predecessor after an absent-final crash.
        """

        self._require_active()
        stages = self._reserved_stages_for_replacement(target_name, expected)
        if any(stage.data != desired for stage in stages):
            raise ConflictError("directory transaction replacement stages bind different bytes")

        try:
            final_data, final_identity = self._anchor.read_regular_file_with_identity(target_name)
        except FileNotFoundError:
            final_data = None
            final_identity = None
        else:
            if final_data != expected and final_data != desired:
                raise ConflictError("anchored file replacement expected bytes differ")

        if final_data is None:
            if not stages:
                raise ConflictError("anchored file replacement expected predecessor is missing")
            selected = stages[0]
            self.adopt_or_publish(selected, target_name)
            for stage in stages:
                self.discard_stage(stage)
            return

        if final_data == desired:
            self._revalidate_durable_final(target_name, desired)
            for stage in stages:
                self.discard_stage(stage)
            return

        assert final_identity is not None
        selected = stages[0] if stages else self._stage_replacement(target_name, expected, desired)
        # The desired stage is durable before this irreversible predecessor
        # unlink.  A failure after either effect is therefore an exact retry.
        self.remove_exact_final(target_name, final_identity, expected)
        self.adopt_or_publish(selected, target_name)
        cleanup_stages = stages if stages else (selected,)
        for stage in cleanup_stages:
            self.discard_stage(stage)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        context, guard = self._guard_context, self._guard
        pending_error: BaseException | None = None
        if context is not None and self._pending_windows_removals:
            # The original guard still serializes this deletion; use the
            # immediate safe point before surrendering it. A remaining failure
            # is transferred as this whole transaction, never to close-only.
            try:
                self._retry_pending_windows_removals()
            except BaseException as error:
                pending_error = error
        self._guard_context = None
        self._guard = None
        self._entered = False
        if context is None:
            self._exit_status = TransactionExitStatus("released")
            terminal_error: BaseException | None = None
            try:
                self._release_terminal_full_owner()
            except BaseException as error:
                terminal_error = error
            if exc is not None and terminal_error is not None:
                _raise_primary_with_cleanup(exc, terminal_error)
            if terminal_error is not None:
                raise terminal_error
            return False
        context_error: BaseException | None = None
        try:
            context.__exit__(exc_type, exc, traceback)
        except BaseException as cleanup_error:
            context_error = cleanup_error
        guard_state = "released" if guard is None else getattr(guard, "_release_state", "unknown")
        close_only = False if guard is None else bool(getattr(guard, "_close_only_transferred", False))
        if guard_state == "unknown" and isinstance(guard, DirectoryMutationGuard):
            self._retained_guard = guard
        self._exit_status = TransactionExitStatus(guard_state, close_only)
        owner_error: BaseException | None = None
        try:
            if self._retained_guard is not None or self._pending_windows_removals:
                self._transfer_retained_full_owner()
            else:
                self._release_terminal_full_owner()
        except BaseException as error:
            owner_error = error

        cleanup_error = context_error
        if pending_error is not None:
            cleanup_error = _add_cleanup_error(
                cleanup_error,
                pending_error,
                "pending exact deletion retry also failed",
            )
        if owner_error is not None:
            cleanup_error = _add_cleanup_error(
                cleanup_error,
                owner_error,
                "transaction owner handoff or terminal release also failed",
            )
        if exc is not None and cleanup_error is not None:
            _raise_primary_with_cleanup(exc, cleanup_error)
        if cleanup_error is not None:
            raise cleanup_error
        if self._pending_windows_removals and exc is None:
            raise ConflictError("directory transaction exact deletion remains pending")
        # Do not delete staged names on an error. They are the sole persistent
        # pre-metadata recovery state and are reconciled by an exact retry.
        return False
