from __future__ import annotations

import ctypes
import json
import os
import stat
import sys
import time
from contextlib import contextmanager
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
import secrets
from types import TracebackType
from typing import Any, Iterator, Literal, Self

from research_system.canonical import canonical_bytes
from research_system.errors import ConflictError
from research_system.store import anchor as anchor_module
from research_system.store.anchor import (
    DirectoryAnchor,
    DirectoryIdentity,
    DirectoryTransaction,
    _DirectoryAnchor,
    _ExactGenerationBusyError,
    _WindowsDeleteClosePendingError,
    _WindowsQuarantineBusyError,
    _close_only_ticket,
    _delete_exact_regular_file as _anchor_delete_exact_regular_file,
    _full_owner_key,
    _is_windows_sharing_violation,
    _link_without_following,
    _open_directory_anchor,
    _regular_file_identity,
    _release_full_owner,
    _retain_close_ticket,
    _raise_primary_with_cleanup,
    _reserve_full_owner,
    _transfer_full_owner,
    _windows_close_handle,
    _windows_file_attribute_tag,
    _windows_open_handle,
    _windows_read_handle,
    drain_retained_transaction_owners,
)
from research_system.store.durability import fsync_directory

if os.name == "nt":
    from research_system.store.anchor import (
        _FILE_ATTRIBUTE_DIRECTORY,
        _FILE_ATTRIBUTE_REPARSE_POINT,
        _FILE_SHARE_READ,
    )


LockOwnerState = Literal["missing", "live", "stale", "unknown", "malformed"]


@dataclass(frozen=True)
class LockObservation:
    data: bytes
    identity: os.stat_result


@dataclass(frozen=True)
class _PendingWindowsClose:
    phase: Literal["observation", "canonical", "temporary", "anchor"]
    resource: object
    closer: Callable[[object], None]
    disposition_applied: bool = False


@dataclass
class _WindowsReleaseState:
    identity: os.stat_result
    temporary: tuple[Path, os.stat_result, BaseException | None] | None
    closes: tuple[_PendingWindowsClose, ...] = ()
    metadata_pending: bool = True
    primary: BaseException | None = None
    close_primary: BaseException | None = None

    @property
    def pending(self) -> bool:
        return self.metadata_pending or self.temporary is not None or bool(self.closes)


def _terminal_before_disposition(
    error: BaseException | None,
    closes: tuple[_PendingWindowsClose, ...],
    phase: Literal["canonical", "temporary"],
) -> bool:
    retryable = (_ExactGenerationBusyError, _WindowsQuarantineBusyError)
    return bool(
        error
        and not isinstance(error, retryable)
        and any(close.phase == phase and not close.disposition_applied for close in closes)
    )


class WriterLockContentionError(ConflictError):
    pass


def _supports_exact_writer_lock_deletion() -> bool:
    return os.name == "nt" or (os.name == "posix" and sys.platform == "linux")


def _windows_process_instance_id(pid: int) -> str | None:
    """Return a Windows process creation-time identity, if it is queryable.

    ``process_instance_id`` supports Windows and Linux only; it never falls
    back to a PID-only identity.
    """
    if os.name != "nt":
        return None

    class _FileTime(ctypes.Structure):
        _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.GetProcessTimes.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(_FileTime),
        ctypes.POINTER(_FileTime),
        ctypes.POINTER(_FileTime),
        ctypes.POINTER(_FileTime),
    ]
    kernel32.GetProcessTimes.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        created = _FileTime()
        exited = _FileTime()
        kernel32_time = _FileTime()
        user = _FileTime()
        if not kernel32.GetProcessTimes(
            handle,
            ctypes.byref(created),
            ctypes.byref(exited),
            ctypes.byref(kernel32_time),
            ctypes.byref(user),
        ):
            return None
        value = (int(created.high) << 32) | int(created.low)
        return f"windows:{value:016x}"
    finally:
        kernel32.CloseHandle(handle)


def _proc_process_instance_id(pid: int) -> str | None:
    """Return a Linux process identity including the boot and start-time tuple.

    Unsupported non-Linux POSIX platforms fail closed with ``None`` rather
    than inventing a PID-reuse-unsafe identity.
    """
    if os.name != "posix" or sys.platform != "linux":
        return None
    stat_path = Path("/proc") / str(pid) / "stat"
    try:
        raw = stat_path.read_text(encoding="ascii")
    except (FileNotFoundError, OSError, UnicodeError):
        return None
    closing_paren = raw.rfind(")")
    if closing_paren < 0:
        return None
    fields = raw[closing_paren + 2 :].split()
    # The suffix starts with field 3 (state); field 22 (starttime) is index 19.
    if len(fields) <= 19:
        return None
    try:
        start_time = int(fields[19])
    except ValueError:
        return None
    try:
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
    except (FileNotFoundError, OSError, UnicodeError):
        boot_id = "unknown-boot"
    return f"linux:{boot_id}:{start_time}"


def process_instance_id(pid: int) -> str | None:
    """Return a Windows or Linux process-instance identity, never PID alone.

    Unsupported platforms return ``None`` so callers can fail closed.
    """
    if pid < 1:
        return None
    if os.name == "nt":
        return _windows_process_instance_id(pid)
    if os.name == "posix" and sys.platform == "linux":
        return _proc_process_instance_id(pid)
    return None


def current_process_instance_id() -> str:
    """Return this Windows/Linux process identity or fail closed."""
    value = process_instance_id(os.getpid())
    if value is None:
        raise ConflictError("writer lock process instance cannot be established")
    return value


def open_registered_member_directory_anchor(path: Path) -> DirectoryAnchor:
    """Open one non-reparse member directory with replacement protection."""

    return _open_directory_anchor(path, reject_reparse=True, delete_protect=True)


def _close_or_retain_windows_resource(
    pending: _PendingWindowsClose,
    release: _WindowsReleaseState | None = None,
) -> None:
    """Keep writer-local release ownership or transfer a close-only resource.

    The physical close operation and its typed close-only registry remain in
    ``store.anchor``.  A writer retains only resources that are still part of
    its own release transaction.
    """

    try:
        pending.closer(pending.resource)
    except BaseException:
        if release is not None:
            release.closes += (pending,)
        else:
            disposition = (
                "directory-anchor" if isinstance(pending.resource, _DirectoryAnchor) else "native-windows-handle"
            )
            _retain_close_ticket(_close_only_ticket(pending.phase, disposition, pending.resource))
        raise


def _delete_exact_regular_file(
    path: Path,
    expected_identity: os.stat_result,
    *,
    expected_bytes: bytes,
    label: str,
    close_phase: Literal["canonical", "temporary"],
    release: _WindowsReleaseState | None = None,
) -> None:
    """Delegate physical deletion to the anchor and retain only its close.

    A ``Delete=True`` handle that could not close remains writer-owned until
    the existing release loop proves it terminal; no filesystem operation is
    reimplemented here.
    """

    if release is None and os.name == "nt":
        parent = _open_directory_anchor(path.parent, reject_reparse=True)
        try:
            with DirectoryTransaction(parent) as transaction:
                transaction.remove_exact_final(path.name, expected_identity, expected_bytes)
        except BaseException as primary_error:
            try:
                parent.close()
            except BaseException as close_error:
                _raise_primary_with_cleanup(primary_error, close_error)
            raise
        parent.close()
        return

    try:
        _anchor_delete_exact_regular_file(
            path,
            expected_identity,
            expected_bytes=expected_bytes,
            label=label,
            close_phase=close_phase,
        )
    except _WindowsDeleteClosePendingError as error:
        if release is None:
            raise
        pending = error.pending
        if pending.handle is None:
            raise ConflictError("writer lock pending deletion has no native handle") from error

        def close_pending(value: object) -> None:
            handle = getattr(value, "handle", None)
            if handle is None:
                return
            _windows_close_handle(handle)
            value.handle = None

        release.closes += (_PendingWindowsClose(close_phase, pending, close_pending, disposition_applied=True),)
        raise _WindowsQuarantineBusyError("writer lock deletion handle remains pending") from error


def _owner_state(record: object) -> LockOwnerState:
    if not isinstance(record, dict):
        return "malformed"
    process_id = record.get("process_id")
    recorded_instance = record.get("process_instance_id")
    if (
        not isinstance(process_id, str)
        or not process_id.isdigit()
        or int(process_id) < 1
        or not isinstance(recorded_instance, str)
        or not recorded_instance
    ):
        return "malformed"
    pid = int(process_id)
    actual_instance = process_instance_id(pid)
    if actual_instance is not None:
        return "live" if actual_instance == recorded_instance else "stale"
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return "stale"
    except PermissionError:
        return "unknown"
    except OSError:
        return "unknown"
    return "unknown"


def _read_lock_observation(path: Path, release: _WindowsReleaseState | None = None) -> LockObservation:
    if os.name == "nt":
        handle: object | None = None
        try:
            handle = _windows_open_handle(
                path,
                open_reparse_point=True,
                delete_protect=True,
                delete_access=False,
                read_contents=True,
                share_mode=_FILE_SHARE_READ,
            )
            attributes, _ = _windows_file_attribute_tag(handle)
            if attributes & _FILE_ATTRIBUTE_REPARSE_POINT or attributes & _FILE_ATTRIBUTE_DIRECTORY:
                raise ConflictError("writer lock must be a physical regular file")
            identity = _regular_file_identity(path, label="writer lock")
            data = _windows_read_handle(handle)
            if not os.path.samestat(identity, _regular_file_identity(path, label="writer lock")):
                raise ConflictError("writer lock generation changed during inspection")
            return LockObservation(data=data, identity=identity)
        finally:
            if handle is not None:
                _close_or_retain_windows_resource(
                    _PendingWindowsClose("observation", handle, _windows_close_handle),
                    release,
                )

    nofollow_flag = getattr(os, "O_NOFOLLOW", 0)
    if not nofollow_flag:
        raise ConflictError("platform cannot inspect a physical writer-lock generation")
    descriptor = os.open(path, os.O_RDONLY | nofollow_flag)
    try:
        identity = os.fstat(descriptor)
        if not stat.S_ISREG(identity.st_mode):
            raise ConflictError("writer lock must be a physical regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        if not os.path.samestat(identity, _regular_file_identity(path, label="writer lock")):
            raise ConflictError("writer lock generation changed during inspection")
        return LockObservation(data=b"".join(chunks), identity=identity)
    finally:
        os.close(descriptor)


def _classify_lock_data(data: bytes) -> tuple[LockOwnerState, dict[str, Any] | None]:
    try:
        record = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "malformed", None
    if not isinstance(record, dict):
        return "malformed", None
    try:
        canonical = canonical_bytes(record)
    except (TypeError, ValueError):
        return "malformed", record
    if canonical != data:
        return "malformed", record
    return _owner_state(record), record


def inspect_lock(path: Path) -> tuple[LockOwnerState, LockObservation | None, dict[str, Any] | None]:
    try:
        observation = _read_lock_observation(path)
    except FileNotFoundError:
        return "missing", None, None
    except (OSError, ConflictError):
        return "unknown", None, None
    state, record = _classify_lock_data(observation.data)
    return state, observation, record


def remove_stale_lock(path: Path, observed: LockObservation) -> bool:
    if not isinstance(observed, LockObservation):
        return False
    state, _ = _classify_lock_data(observed.data)
    if state != "stale":
        return False
    if os.name == "posix" and sys.platform == "linux":
        guard: int | None = None
        parent_anchor: _DirectoryAnchor | None = None
        outcome = False
        primary_error: BaseException | None = None
        try:
            parent_anchor = _open_directory_anchor(path.parent, reject_reparse=True)
            guard = _acquire_posix_lock_guard(path, parent_anchor)
            data, identity = parent_anchor.read_regular_file_with_identity(path.name)
            current = LockObservation(data=data, identity=identity)
            if current.data == observed.data and os.path.samestat(current.identity, observed.identity):
                current_state, _ = _classify_lock_data(current.data)
                if current_state == "stale":
                    _verify_posix_lock_guard(path, guard, parent_anchor)
                    _posix_guarded_delete_lock(path, observed, parent_anchor, guard)
                    outcome = True
        except FileNotFoundError:
            outcome = True
        except (BlockingIOError, OSError, ConflictError):
            outcome = False
        except BaseException as error:
            primary_error = error
        cleanup_error = _close_posix_lock_resources(guard, parent_anchor)
        if primary_error is not None:
            _raise_primary_with_cleanup(primary_error, cleanup_error)
        if cleanup_error is not None:
            raise cleanup_error
        return outcome
    try:
        _delete_exact_regular_file(
            path,
            observed.identity,
            expected_bytes=observed.data,
            label="stale writer lock",
            close_phase="canonical",
        )
    except FileNotFoundError:
        return True
    except (OSError, ConflictError):
        return False
    fsync_directory(path.parent)
    return True


class _LeaseState:
    __slots__ = ("_live",)

    def __init__(self) -> None:
        self._live = True

    @property
    def live(self) -> bool:
        return self._live

    def invalidate(self) -> None:
        self._live = False


@dataclass(frozen=True, init=False)
class LockedRoot:
    identity: DirectoryIdentity
    final_path: Path
    runtime_identity: DirectoryIdentity
    runtime_final_path: Path
    aliases: tuple[Path, ...]
    _lease_token: _LeaseState
    _anchor: DirectoryAnchor
    _runtime_anchor: DirectoryAnchor

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("LockedRoot is a lock-created capability")

    @classmethod
    def _create(
        cls,
        *,
        identity: DirectoryIdentity,
        final_path: Path,
        runtime_identity: DirectoryIdentity,
        runtime_final_path: Path,
        aliases: tuple[Path, ...],
        lease_token: _LeaseState,
        anchor: DirectoryAnchor,
        runtime_anchor: DirectoryAnchor,
    ) -> Self:
        instance = object.__new__(cls)
        object.__setattr__(instance, "identity", identity)
        object.__setattr__(instance, "final_path", final_path)
        object.__setattr__(instance, "runtime_identity", runtime_identity)
        object.__setattr__(instance, "runtime_final_path", runtime_final_path)
        object.__setattr__(instance, "aliases", aliases)
        object.__setattr__(instance, "_lease_token", lease_token)
        object.__setattr__(instance, "_anchor", anchor)
        object.__setattr__(instance, "_runtime_anchor", runtime_anchor)
        return instance

    def _require_live_anchor(self, *, runtime: bool) -> DirectoryAnchor:
        if not self._lease_token.live:
            raise ConflictError("locked root lease is no longer live")
        anchor = self._runtime_anchor if runtime else self._anchor
        expected_identity = self.runtime_identity if runtime else self.identity
        expected_path = self.runtime_final_path if runtime else self.final_path
        identity, final_path = anchor.refresh()
        if identity != expected_identity or final_path != expected_path:
            raise ConflictError(
                "locked runtime physical identity changed" if runtime else "locked root physical identity changed"
            )
        return anchor

    def open_member_directory(
        self,
        name: str,
        *,
        create: bool = False,
        delete_protect: bool = True,
    ) -> DirectoryAnchor:
        return self._require_live_anchor(runtime=False).open_member_directory(
            name,
            create=create,
            delete_protect=delete_protect,
        )

    def open_runtime_member_directory(self, name: str, *, create: bool = False) -> DirectoryAnchor:
        return self._require_live_anchor(runtime=True).open_member_directory(name, create=create)

    @staticmethod
    def _relative_file_parts(relative_path: str) -> tuple[str, ...]:
        if (
            not isinstance(relative_path, str)
            or not relative_path
            or "\x00" in relative_path
            or "\\" in relative_path
            or relative_path.startswith("/")
        ):
            raise ConflictError("anchored relative file path is invalid")
        parts = tuple(relative_path.split("/"))
        if any(part in {"", ".", ".."} for part in parts):
            raise ConflictError("anchored relative file path is invalid")
        if len(parts) == 1 and parts[0] == "runtime":
            raise ConflictError("anchored relative file path requires a file name")
        return parts

    def _open_relative_file_parent(
        self,
        relative_path: str,
        *,
        create: bool,
    ) -> tuple[DirectoryAnchor, str, tuple[DirectoryAnchor, ...]]:
        parts = self._relative_file_parts(relative_path)
        if parts[0] == "runtime":
            anchor = self._require_live_anchor(runtime=True)
            parts = parts[1:]
        else:
            anchor = self._require_live_anchor(runtime=False)
        opened: list[DirectoryAnchor] = []
        try:
            for part in parts[:-1]:
                child = anchor.open_member_directory(part, create=create)
                opened.append(child)
                anchor = child
            return anchor, parts[-1], tuple(opened)
        except BaseException as primary_error:
            try:
                self._close_all_relative_file_parents(tuple(opened))
            except BaseException as cleanup_error:
                raise primary_error from cleanup_error
            raise

    @staticmethod
    def _close_all_relative_file_parents(opened: tuple[DirectoryAnchor, ...]) -> None:
        first_error: BaseException | None = None
        for child in reversed(opened):
            try:
                child.close()
            except BaseException as error:
                first_error = _add_cleanup_error(first_error, error, "nested directory close also failed")
        if first_error is not None:
            raise first_error

    @classmethod
    @contextmanager
    def _closing_relative_file_parents(cls, opened: tuple[DirectoryAnchor, ...]) -> Iterator[None]:
        try:
            yield
        except BaseException as primary_error:
            try:
                cls._close_all_relative_file_parents(opened)
            except BaseException as cleanup_error:
                raise primary_error from cleanup_error
            raise
        cls._close_all_relative_file_parents(opened)

    def read_exact_file(self, relative_path: str) -> bytes:
        parent, name, opened = self._open_relative_file_parent(relative_path, create=False)
        with self._closing_relative_file_parents(opened):
            return parent.read_regular_file(name)

    @staticmethod
    def _publish_exact(parent: DirectoryAnchor, name: str, data: bytes) -> None:
        """Publish one file through anchor's sole physical transaction seam."""

        with DirectoryTransaction(parent) as transaction:
            transaction.publish_exact(name, data)

    def write_exact_file(self, relative_path: str, data: bytes) -> None:
        parent, name, opened = self._open_relative_file_parent(relative_path, create=True)
        with self._closing_relative_file_parents(opened):
            self._publish_exact(parent, name, data)

    def replace_exact_file(self, relative_path: str, expected: bytes, data: bytes) -> None:
        parent, name, opened = self._open_relative_file_parent(relative_path, create=False)
        with self._closing_relative_file_parents(opened):
            with DirectoryTransaction(parent) as transaction:
                transaction.replace_or_recover(name, expected, data)

    def remove_exact_file(self, relative_path: str, expected: bytes) -> None:
        parent, name, opened = self._open_relative_file_parent(relative_path, create=False)
        with self._closing_relative_file_parents(opened):
            with DirectoryTransaction(parent) as transaction:
                try:
                    current, identity = parent.read_regular_file_with_identity(name)
                except FileNotFoundError as error:
                    raise ConflictError("anchored file changed before removal") from error
                if current != expected:
                    raise ConflictError("anchored file removal expected bytes differ")
                transaction.remove_exact_final(name, identity, expected)


def _root_sort_key(path: Path) -> tuple[str, str]:
    normalized = os.path.normcase(str(path))
    display = normalized
    for prefix in ("\\\\?\\", "//?/"):
        if display.startswith(prefix):
            display = display[len(prefix) :]
            break
    return display, normalized


@dataclass(frozen=True)
class _RootClaim:
    alias: Path
    identity: DirectoryIdentity
    final_path: Path
    runtime_identity: DirectoryIdentity
    runtime_final_path: Path


@dataclass(frozen=True)
class _RootMember:
    identity: DirectoryIdentity
    representative: _RootClaim
    aliases: tuple[Path, ...]
    runtime_identity: DirectoryIdentity


@dataclass
class _AcquiredMember:
    member: _RootMember
    root_anchor: _DirectoryAnchor | None = None
    runtime_anchor: _DirectoryAnchor | None = None
    lock: Any | None = None
    lock_entered: bool = False
    release_owned_by_composite: bool = False


def _close_anchor(anchor: _DirectoryAnchor | None) -> None:
    if anchor is not None:
        anchor._close_without_quarantine()


def _capture_claim(alias: Path) -> _RootClaim:
    root_anchor: _DirectoryAnchor | None = None
    runtime_anchor: _DirectoryAnchor | None = None
    try:
        try:
            root_anchor = _open_directory_anchor(alias)
            runtime_anchor = _open_directory_anchor(root_anchor.final_path / "runtime", reject_reparse=True)
        except FileNotFoundError as exc:
            raise ConflictError(f"{alias} is not an existing directory") from exc
        current_identity, current_final_path = root_anchor.refresh()
        if current_identity != root_anchor.identity or current_final_path != root_anchor.final_path:
            raise ConflictError(f"{alias} changed while its identity was captured")
        runtime_identity, runtime_final_path = runtime_anchor.refresh()
        if runtime_identity != runtime_anchor.identity or runtime_final_path != runtime_anchor.final_path:
            raise ConflictError(f"{alias}/runtime changed while its identity was captured")
        claim = _RootClaim(
            alias=alias,
            identity=root_anchor.identity,
            final_path=root_anchor.final_path,
            runtime_identity=runtime_anchor.identity,
            runtime_final_path=runtime_anchor.final_path,
        )
    except BaseException as capture_error:
        first_cleanup_error: BaseException | None = None
        for anchor in (runtime_anchor, root_anchor):
            if anchor is None:
                continue
            try:
                anchor.close()
            except BaseException as cleanup_error:
                if first_cleanup_error is None:
                    first_cleanup_error = cleanup_error
        if first_cleanup_error is not None:
            _raise_primary_with_cleanup(capture_error, first_cleanup_error)
        raise
    first_cleanup_error: BaseException | None = None
    for anchor in (runtime_anchor, root_anchor):
        if anchor is None:
            continue
        try:
            anchor.close()
        except BaseException as cleanup_error:
            if first_cleanup_error is None:
                first_cleanup_error = cleanup_error
    if first_cleanup_error is not None:
        raise first_cleanup_error
    return claim


def _posix_lock_guard_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.guard")


def _posix_flock(descriptor: int, *, unlock: bool = False) -> None:
    if os.name != "posix" or sys.platform != "linux":
        raise ConflictError("POSIX writer-lock guards require Linux flock")
    import fcntl

    operation = fcntl.LOCK_UN if unlock else fcntl.LOCK_EX | fcntl.LOCK_NB
    fcntl.flock(descriptor, operation)


def _acquire_posix_lock_guard(path: Path, parent_anchor: _DirectoryAnchor) -> int:
    nofollow_flag = getattr(os, "O_NOFOLLOW", 0)
    if not nofollow_flag:
        raise ConflictError("platform cannot open a no-follow writer-lock guard")
    guard = _posix_lock_guard_path(path)
    descriptor = os.open(
        guard.name,
        os.O_RDWR | os.O_CREAT | nofollow_flag,
        0o600,
        dir_fd=int(parent_anchor._handle),
    )
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ConflictError("writer-lock guard must be a physical regular file")
        os.fchmod(descriptor, 0o600)
        opened = os.fstat(descriptor)
        if stat.S_IMODE(opened.st_mode) != 0o600:
            raise ConflictError("writer-lock guard must remain private")
        _posix_flock(descriptor)
        current = os.stat(guard.name, dir_fd=int(parent_anchor._handle), follow_symlinks=False)
        if not os.path.samestat(opened, current):
            raise ConflictError("writer-lock guard generation changed during acquisition")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _close_posix_lock_guard(descriptor: int) -> None:
    try:
        _posix_flock(descriptor, unlock=True)
    finally:
        os.close(descriptor)


def _add_cleanup_error(
    current: BaseException | None,
    error: BaseException,
    label: str,
) -> BaseException:
    if current is None:
        return error
    current.add_note(f"{label}: {error!r}")
    return current


def _append_cleanup_cause(primary: BaseException, error: BaseException) -> None:
    """Retain every member-release failure behind one primary exception."""

    cursor = primary
    seen: set[int] = set()
    while cursor.__cause__ is not None and id(cursor) not in seen:
        seen.add(id(cursor))
        cursor = cursor.__cause__
    cursor.__cause__ = error


def _close_posix_lock_resources(
    guard: int | None,
    parent_anchor: _DirectoryAnchor | None,
) -> BaseException | None:
    cleanup_error: BaseException | None = None
    if guard is not None:
        try:
            _close_posix_lock_guard(guard)
        except BaseException as error:
            cleanup_error = _add_cleanup_error(cleanup_error, error, "writer-lock guard close also failed")
    if parent_anchor is not None:
        try:
            parent_anchor.close()
        except BaseException as error:
            cleanup_error = _add_cleanup_error(cleanup_error, error, "writer-lock parent close also failed")
    return cleanup_error


def _after_posix_lock_unlink(_path: Path) -> None:
    pass


def _verify_posix_lock_guard(path: Path, descriptor: int, parent_anchor: _DirectoryAnchor) -> None:
    opened = os.fstat(descriptor)
    current = os.stat(
        _posix_lock_guard_path(path).name,
        dir_fd=int(parent_anchor._handle),
        follow_symlinks=False,
    )
    if not os.path.samestat(opened, current):
        raise ConflictError("writer-lock guard generation changed while held")


def _posix_guarded_delete_lock(
    path: Path,
    expected: LockObservation,
    parent_anchor: _DirectoryAnchor,
    guard_descriptor: int,
    *,
    guard_path: Path | None = None,
) -> None:
    _verify_posix_lock_guard(guard_path or path, guard_descriptor, parent_anchor)
    anchor_module._before_exact_generation_unlink(path)
    data, identity = parent_anchor.read_regular_file_with_identity(path.name)
    if data != expected.data or not os.path.samestat(identity, expected.identity):
        raise ConflictError("writer lock generation changed before guarded deletion")
    os.unlink(path.name, dir_fd=int(parent_anchor._handle))
    _after_posix_lock_unlink(path)
    parent_anchor.fsync()
    parent_anchor.verify_unchanged()


def _verify_writer_lock(lock: Any, expected_runtime_path: Path) -> None:
    try:
        path = Path(lock.path)
        identity = lock.identity
    except AttributeError as exc:
        raise ConflictError("writer lock ownership record is unavailable") from exc
    expected_path = expected_runtime_path / "writer.lock"
    if path != expected_path:
        raise ConflictError("writer lock path is not under its runtime anchor")
    generation = getattr(lock, "_posix_lock_identity", None)
    parent_anchor = getattr(lock, "_posix_parent_anchor", None)
    try:
        if parent_anchor is None:
            raw = path.read_bytes()
        else:
            raw, _ = parent_anchor.read_regular_file_with_identity(path.name)
        recorded = json.loads(raw)
    except (OSError, ConflictError, json.JSONDecodeError) as exc:
        raise ConflictError("writer lock ownership record cannot be verified") from exc
    if recorded != identity:
        raise ConflictError("writer lock ownership changed before protected work")
    if generation is not None:
        guard = getattr(lock, "_posix_guard_descriptor", None)
        if guard is None or parent_anchor is None:
            raise ConflictError("writer-lock guard ownership is unavailable")
        _verify_posix_lock_guard(path, guard, parent_anchor)
        _, observed = parent_anchor.read_regular_file_with_identity(path.name)
        if not os.path.samestat(generation, observed):
            raise ConflictError("writer lock generation changed before protected work")


class WriterLock:
    def __init__(self, path: Path, identity: dict[str, str]):
        self.path = path
        self.identity = dict(identity)
        process_id = self.identity.setdefault("process_id", str(os.getpid()))
        if "process_instance_id" not in self.identity:
            if process_id != str(os.getpid()):
                raise ConflictError("writer lock foreign process requires process instance identity")
            self.identity["process_instance_id"] = current_process_instance_id()
        self._data = canonical_bytes(self.identity)
        self._deferred_temporary: tuple[Path, os.stat_result, BaseException | None] | None = None
        self._windows_release: _WindowsReleaseState | None = None
        self._posix_guard_descriptor: int | None = None
        self._posix_lock_identity: os.stat_result | None = None
        self._posix_parent_anchor: _DirectoryAnchor | None = None
        self._posix_deferred_temporary: tuple[str, os.stat_result] | None = None
        self._posix_backend_entered = False
        self._posix_release_complete = False
        self._owner_reservation: Any | None = None
        self._owner_nonce = secrets.token_hex(16)
        self._composite_owner: object | None = None
        self._full_owner_terminal = False

    def _enter_posix(self) -> Self:
        if self._posix_backend_entered and not self._posix_release_complete:
            raise ConflictError("POSIX writer lock is already active")
        if self._posix_release_complete:
            self._posix_backend_entered = False
            self._posix_release_complete = False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        parent_anchor: _DirectoryAnchor | None = None
        guard: int | None = None
        temporary: str | None = None
        temporary_identity: os.stat_result | None = None
        canonical_identity: os.stat_result | None = None
        try:
            parent_anchor = _open_directory_anchor(self.path.parent, reject_reparse=True)
            try:
                guard = _acquire_posix_lock_guard(self.path, parent_anchor)
            except BlockingIOError as exc:
                raise WriterLockContentionError(f"writer lock exists: {self.path}") from exc
            temporary, temporary_identity = parent_anchor.stage_private_file(self.path.name, self._data)
            try:
                canonical_identity = temporary_identity
                published_identity = parent_anchor.link_exact_regular_file(
                    temporary,
                    temporary_identity,
                    self.path.name,
                )
                parent_anchor.fsync()
            except FileExistsError as exc:
                canonical_identity = None
                _posix_guarded_delete_lock(
                    parent_anchor.final_path / temporary,
                    LockObservation(self._data, temporary_identity),
                    parent_anchor,
                    guard,
                    guard_path=self.path,
                )
                temporary = None
                raise WriterLockContentionError(f"writer lock exists: {self.path}") from exc
            try:
                _posix_guarded_delete_lock(
                    parent_anchor.final_path / temporary,
                    LockObservation(self._data, temporary_identity),
                    parent_anchor,
                    guard,
                    guard_path=self.path,
                )
                temporary = None
            except (ConflictError, OSError):
                pass
            data, verified_identity = parent_anchor.read_regular_file_with_identity(self.path.name)
            if data != self._data or not os.path.samestat(published_identity, verified_identity):
                raise ConflictError("writer lock publication did not remain exact")
            _verify_posix_lock_guard(self.path, guard, parent_anchor)
            parent_anchor.verify_unchanged()
            self._posix_guard_descriptor = guard
            self._posix_lock_identity = verified_identity
            self._posix_parent_anchor = parent_anchor
            self._posix_backend_entered = True
            if temporary is not None:
                self._posix_deferred_temporary = (temporary, temporary_identity)
                temporary = None
            return self
        except BaseException as primary_error:
            cleanup_error: BaseException | None = None
            if canonical_identity is not None and parent_anchor is not None and guard is not None:
                try:
                    _posix_guarded_delete_lock(
                        self.path,
                        LockObservation(self._data, canonical_identity),
                        parent_anchor,
                        guard,
                    )
                except FileNotFoundError:
                    pass
                except BaseException as error:
                    cleanup_error = error
            if temporary is not None and temporary_identity is not None and parent_anchor is not None:
                try:
                    _posix_guarded_delete_lock(
                        parent_anchor.final_path / temporary,
                        LockObservation(self._data, temporary_identity),
                        parent_anchor,
                        guard,
                        guard_path=self.path,
                    )
                except FileNotFoundError:
                    pass
                except BaseException as error:
                    cleanup_error = _add_cleanup_error(
                        cleanup_error, error, "writer lock temporary cleanup also failed"
                    )
            resource_error = _close_posix_lock_resources(guard, parent_anchor)
            if resource_error is not None:
                cleanup_error = _add_cleanup_error(
                    cleanup_error, resource_error, "writer-lock resource cleanup also failed"
                )
            _raise_primary_with_cleanup(primary_error, cleanup_error)

    def _reserve_release_owner(self) -> None:
        if self._owner_reservation is not None:
            raise ConflictError("writer lock release owner is already reserved")
        self._full_owner_terminal = False
        self._owner_reservation = _reserve_full_owner(
            _full_owner_key("writer-release", str(self.path.absolute()), self._owner_nonce)
        )

    def _clear_release_owner(self) -> None:
        reservation, self._owner_reservation = self._owner_reservation, None
        _release_full_owner(reservation)

    def _has_retained_release(self) -> bool:
        """Whether this lock still has safe release authority to retry.

        A POSIX lock remains retryable until its guarded namespace effect and
        owned resources have completed. Descriptor numbers are never retried
        after resource cleanup has consumed them.
        """

        return self.release_pending or (self._posix_backend_entered and not self._posix_release_complete)

    def __enter__(self) -> Self:
        drain_retained_transaction_owners()
        self._reserve_release_owner()
        try:
            return self._enter_once()
        except BaseException:
            self._clear_release_owner()
            raise

    def _enter_once(self) -> Self:
        if not _supports_exact_writer_lock_deletion():
            raise ConflictError("writer lock leases require Windows or Linux inode-safe locking")
        if os.name == "posix":
            return self._enter_posix()
        return self._enter_path_published()

    def _enter_path_published(self) -> Self:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{secrets.token_hex(16)}.tmp")
        temporary_identity: os.stat_result | None = None
        canonical_published = False
        try:
            with temporary.open("xb") as handle:
                handle.write(self._data)
                handle.flush()
                os.fsync(handle.fileno())
                temporary_identity = os.fstat(handle.fileno())
            if not stat.S_ISREG(temporary_identity.st_mode):
                raise ConflictError("writer lock temporary is not a regular file")
            try:
                # A hard-link publication gives us a complete metadata file and
                # an O_EXCL-equivalent claim on the final path in one operation.
                _link_without_following(temporary, self.path)
                canonical_published = True
            except FileExistsError as exc:
                raise WriterLockContentionError(f"writer lock exists: {self.path}") from exc
            fsync_directory(self.path.parent)
        except BaseException as primary_error:
            canonical_cleanup_error: BaseException | None = None
            temporary_cleanup_error: BaseException | None = None
            if canonical_published:
                assert temporary_identity is not None
                try:
                    _delete_exact_regular_file(
                        self.path,
                        temporary_identity,
                        expected_bytes=self._data,
                        label="writer lock rollback canonical",
                        close_phase="canonical",
                    )
                except FileNotFoundError:
                    pass
                except BaseException as cleanup_error:
                    canonical_cleanup_error = cleanup_error
            if temporary_identity is not None:
                try:
                    _delete_exact_regular_file(
                        temporary,
                        temporary_identity,
                        expected_bytes=self._data,
                        label="writer lock temporary",
                        close_phase="temporary",
                    )
                except FileNotFoundError:
                    pass
                except BaseException as cleanup_error:
                    temporary_cleanup_error = cleanup_error
            if canonical_cleanup_error is not None and temporary_cleanup_error is not None:
                canonical_cleanup_error.add_note(
                    f"writer lock temporary cleanup also failed: {temporary_cleanup_error!r}"
                )
            _raise_primary_with_cleanup(primary_error, canonical_cleanup_error or temporary_cleanup_error)

        anchor_close_error: BaseException | None = None
        retained_anchor: _DirectoryAnchor | None = None
        if temporary_identity is not None:
            try:
                _delete_exact_regular_file(
                    temporary,
                    temporary_identity,
                    expected_bytes=self._data,
                    label="writer lock temporary",
                    close_phase="temporary",
                )
            except FileNotFoundError:
                pass
            except BaseException as cleanup_error:
                parent_anchor: _DirectoryAnchor | None = None
                ownership_error: BaseException | None = None
                canonical_proven_exact = False
                canonical_rollback_unsafe = False
                try:
                    parent_anchor = _open_directory_anchor(self.path.parent, reject_reparse=True)
                    observed_bytes, observed_identity = parent_anchor._read_regular_file_with_identity(
                        self.path.name,
                        parent_anchor.final_path,
                    )
                    if not os.path.samestat(temporary_identity, observed_identity) or observed_bytes != self._data:
                        canonical_rollback_unsafe = True
                        raise ConflictError("writer lock ownership changed after durable publication")
                    canonical_proven_exact = True
                except ConflictError as exc:
                    canonical_rollback_unsafe = True
                    ownership_error = exc
                except BaseException as exc:
                    ownership_error = exc
                finally:
                    if parent_anchor is not None:
                        try:
                            parent_anchor._close_without_quarantine()
                        except BaseException as close_error:
                            anchor_close_error = close_error
                            retained_anchor = parent_anchor
                if not canonical_proven_exact:
                    canonical_rollback_error: BaseException | None = None
                    retry_error: BaseException | None = None
                    if not canonical_rollback_unsafe:
                        try:
                            _delete_exact_regular_file(
                                self.path,
                                temporary_identity,
                                expected_bytes=self._data,
                                label="writer lock rejected canonical",
                                close_phase="canonical",
                            )
                        except FileNotFoundError:
                            pass
                        except BaseException as exc:
                            canonical_rollback_error = exc
                    try:
                        _delete_exact_regular_file(
                            temporary,
                            temporary_identity,
                            expected_bytes=self._data,
                            label="writer lock rejected temporary",
                            close_phase="temporary",
                        )
                    except FileNotFoundError:
                        pass
                    except BaseException as exc:
                        retry_error = exc
                    error = ConflictError("writer lock canonical ownership cannot be verified after temporary cleanup")
                    error.add_note(f"writer lock temporary cleanup failed: {cleanup_error!r}")
                    if canonical_rollback_error is not None:
                        error.add_note(
                            f"writer lock rejected canonical rollback also failed: {canonical_rollback_error!r}"
                        )
                    if retry_error is not None:
                        error.add_note(f"writer lock rejected temporary retry also failed: {retry_error!r}")
                    if retained_anchor is not None:
                        _retain_close_ticket(
                            _close_only_ticket("writer lock rejected anchor", "directory-anchor", retained_anchor)
                        )
                    raise error from ownership_error
                self._deferred_temporary = (temporary, temporary_identity, None)
        closes = ()
        if retained_anchor is not None:
            closes = (_PendingWindowsClose("anchor", retained_anchor, lambda value: value._close_without_quarantine()),)
        self._windows_release = _WindowsReleaseState(
            temporary_identity,
            self._deferred_temporary,
            closes=closes,
            close_primary=anchor_close_error,
        )
        return self

    @property
    def release_pending(self) -> bool:
        return self._windows_release is not None and self._windows_release.pending

    def _release_once(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if self._posix_backend_entered:
            if self._posix_release_complete:
                return False
            guard = self._posix_guard_descriptor
            identity = self._posix_lock_identity
            parent_anchor = self._posix_parent_anchor
            deferred_temporary = self._posix_deferred_temporary
            if guard is None or identity is None or parent_anchor is None:
                raise ConflictError("POSIX writer lock ownership state is incomplete")
            release_error: BaseException | None = None
            release_finished = False
            try:
                _verify_posix_lock_guard(self.path, guard, parent_anchor)
                _posix_guarded_delete_lock(
                    self.path,
                    LockObservation(self._data, identity),
                    parent_anchor,
                    guard,
                )
                release_finished = True
            except FileNotFoundError:
                release_finished = True
            except BaseException as error:
                release_error = error
                try:
                    current_data, current_identity = parent_anchor.read_regular_file_with_identity(self.path.name)
                except FileNotFoundError:
                    release_finished = True
                except BaseException as classification_error:
                    error.add_note(f"writer lock release state cannot be classified: {classification_error!r}")
                    raise error from classification_error
                else:
                    if current_data == self._data and os.path.samestat(current_identity, identity):
                        raise
                    release_finished = True
            if not release_finished:  # pragma: no cover - every branch above classifies or raises
                raise ConflictError("POSIX writer lock release state is unresolved")

            cleanup_error: BaseException | None = None
            if deferred_temporary is not None:
                temporary, temporary_identity = deferred_temporary
                try:
                    _posix_guarded_delete_lock(
                        parent_anchor.final_path / temporary,
                        LockObservation(self._data, temporary_identity),
                        parent_anchor,
                        guard,
                        guard_path=self.path,
                    )
                except FileNotFoundError:
                    pass
                except BaseException as error:
                    cleanup_error = error
            resource_error = _close_posix_lock_resources(guard, parent_anchor)
            if resource_error is not None:
                cleanup_error = _add_cleanup_error(
                    cleanup_error, resource_error, "writer-lock resource cleanup also failed"
                )
            self._posix_guard_descriptor = None
            self._posix_lock_identity = None
            self._posix_parent_anchor = None
            self._posix_deferred_temporary = None
            self._posix_release_complete = True
            if release_error is not None:
                _raise_primary_with_cleanup(release_error, cleanup_error)
            if cleanup_error is not None:
                raise cleanup_error
            return False

        release = self._windows_release
        if release is None:
            raise ConflictError("writer lock release transaction is unavailable")
        prior_primary = release.primary
        close_primary = release.close_primary
        while release.closes:
            pending, *remaining = release.closes
            try:
                pending.closer(pending.resource)
            except BaseException as close_error:
                primary = prior_primary or close_primary or close_error
                _raise_primary_with_cleanup(primary, close_error if primary is not close_error else None)
            release.closes = tuple(remaining)
            if pending.disposition_applied:
                if pending.phase == "canonical":
                    release.metadata_pending = False
                elif pending.phase == "temporary":
                    release.temporary = None
        release.close_primary = None

        canonical_error = prior_primary if not release.metadata_pending else None
        if release.metadata_pending:
            attempt_error: BaseException | None = None
            close_count = len(release.closes)
            try:
                observation = _read_lock_observation(self.path, release)
                recorded = json.loads(observation.data)
            except _WindowsQuarantineBusyError as busy_error:
                attempt_error = busy_error
            except (OSError, ConflictError, UnicodeDecodeError, json.JSONDecodeError) as read_error:
                error = ConflictError("writer lock cannot be verified while held")
                error.__cause__ = read_error
                attempt_error = error
            else:
                if (
                    not os.path.samestat(release.identity, observation.identity)
                    or recorded != self.identity
                    or canonical_bytes(recorded) != self._data
                ):
                    attempt_error = ConflictError("writer lock ownership changed while held")
                else:
                    try:
                        _delete_exact_regular_file(
                            self.path,
                            release.identity,
                            expected_bytes=self._data,
                            label="writer lock",
                            close_phase="canonical",
                            release=release,
                        )
                    except FileNotFoundError as delete_error:
                        error = ConflictError("writer lock disappeared while held")
                        error.__cause__ = delete_error
                        attempt_error = error
                    except BaseException as delete_error:
                        attempt_error = delete_error
            new_closes = release.closes[close_count:]
            terminal_with_cleanup = _terminal_before_disposition(attempt_error, new_closes, "canonical")
            if terminal_with_cleanup:
                release.metadata_pending = False
                release.primary = prior_primary or attempt_error
                _raise_primary_with_cleanup(release.primary, attempt_error if prior_primary else None)
            if release.closes or isinstance(attempt_error, (_ExactGenerationBusyError, _WindowsQuarantineBusyError)):
                if release.closes:
                    release.close_primary = close_primary or attempt_error
                primary = prior_primary or release.close_primary or attempt_error
                _raise_primary_with_cleanup(primary, attempt_error if primary is not attempt_error else None)
            release.metadata_pending = False
            canonical_error = prior_primary or attempt_error
            release.primary = canonical_error

        temporary_error: BaseException | None = None
        deferred_close_error: BaseException | None = None
        terminal_with_cleanup = False
        if release.temporary is not None:
            temporary, temporary_identity, deferred_close_error = release.temporary
            close_count = len(release.closes)
            try:
                _delete_exact_regular_file(
                    temporary,
                    temporary_identity,
                    expected_bytes=self._data,
                    label="writer lock deferred temporary",
                    close_phase="temporary",
                    release=release,
                )
            except FileNotFoundError:
                release.temporary = None
            except BaseException as cleanup_error:
                temporary_error = cleanup_error
                terminal_with_cleanup = _terminal_before_disposition(
                    cleanup_error, release.closes[close_count:], "temporary"
                )
                if terminal_with_cleanup or (
                    not isinstance(cleanup_error, (_ExactGenerationBusyError, _WindowsQuarantineBusyError))
                    and len(release.closes) == close_count
                ):
                    release.temporary = None
            else:
                release.temporary = None
        if release.closes or isinstance(temporary_error, (_ExactGenerationBusyError, _WindowsQuarantineBusyError)):
            if terminal_with_cleanup:
                release.primary = canonical_error or release.primary or temporary_error
                _raise_primary_with_cleanup(release.primary, temporary_error if canonical_error else None)
            if release.closes:
                release.close_primary = release.close_primary or temporary_error
            _raise_primary_with_cleanup(
                canonical_error or release.close_primary or temporary_error,
                temporary_error if canonical_error or release.close_primary is not temporary_error else None,
            )
        self._deferred_temporary = release.temporary
        if not release.pending:
            self._windows_release = None
        if canonical_error is not None:
            if temporary_error is not None and deferred_close_error is not None:
                temporary_error.add_note(f"writer lock deferred anchor close also failed: {deferred_close_error!r}")
            _raise_primary_with_cleanup(canonical_error, temporary_error or deferred_close_error)
        if temporary_error is not None:
            _raise_primary_with_cleanup(temporary_error, deferred_close_error)
        try:
            fsync_directory(self.path.parent)
        except BaseException as fsync_error:
            _raise_primary_with_cleanup(fsync_error, deferred_close_error)
        if deferred_close_error is not None:
            raise deferred_close_error
        return False

    def _transfer_to_composite(self, owner: object) -> None:
        """Let one CompositeWriterLock retain the only release authority."""

        if self._composite_owner is not None or self._owner_reservation is None:
            raise ConflictError("writer lock cannot transfer incomplete ownership")
        self._composite_owner = owner
        self._clear_release_owner()

    def _release_from_composite(
        self,
        owner: object,
        exc_type: type[BaseException] | None = None,
        exc: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> bool:
        if self._composite_owner is not owner:
            raise ConflictError("writer lock composite owner is not live")
        try:
            result = self._release_once(exc_type, exc, traceback)
        except BaseException:
            if not self._has_retained_release():
                self._composite_owner = None
            raise
        if not self._has_retained_release():
            self._composite_owner = None
        return result

    def _retry_full_owner_release(self) -> bool:
        """Drive one retained Windows writer release at an explicit safe point."""

        try:
            self._release_once(None, None, None)
        except BaseException:
            if not self._has_retained_release():
                self._full_owner_terminal = True
                self._clear_release_owner()
            raise
        self._full_owner_terminal = not self._has_retained_release()
        if self._full_owner_terminal:
            self._clear_release_owner()
        return self._full_owner_terminal

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if self._composite_owner is not None:
            raise ConflictError("writer lock release is owned by its composite")
        reservation = self._owner_reservation
        if reservation is not None and getattr(reservation, "transferred", False):
            try:
                terminal = self._retry_full_owner_release()
            except BaseException as retry_error:
                if exc is not None:
                    raise exc.with_traceback(traceback) from retry_error
                raise
            if terminal:
                return False
            raise ConflictError("writer lock retained release remains pending")
        try:
            result = self._release_once(exc_type, exc, traceback)
        except BaseException as release_error:
            if self._has_retained_release():
                if reservation is None:
                    raise ConflictError("writer lock release owner is unavailable") from release_error
                _transfer_full_owner(reservation, self)
            else:
                self._full_owner_terminal = True
                self._clear_release_owner()
            if exc is not None:
                raise exc.with_traceback(traceback) from release_error
            raise
        self._full_owner_terminal = True
        self._clear_release_owner()
        return result


class CompositeWriterLock:
    """Acquire physical-root writer locks and publish a live lease."""

    def __init__(
        self,
        roots: Iterable[Path],
        identity: dict[str, str],
        *,
        lock_factory: Callable[[Path, dict[str, str]], WriterLock] | None = None,
    ):
        supplied_roots = tuple(Path(root) for root in roots)
        if not supplied_roots:
            raise ValueError("composite writer lock requires at least one root")

        claims = tuple(_capture_claim(root) for root in supplied_roots)
        grouped: dict[DirectoryIdentity, list[_RootClaim]] = {}
        for claim in claims:
            grouped.setdefault(claim.identity, []).append(claim)

        members: list[_RootMember] = []
        for identity_key, candidates in grouped.items():
            representative = min(
                candidates,
                key=lambda candidate: _root_sort_key(candidate.final_path),
            )
            runtime_identities = {candidate.runtime_identity for candidate in candidates}
            if len(runtime_identities) != 1:
                raise ConflictError("aliases of one physical root have different runtime directories")
            aliases = tuple(sorted((candidate.alias for candidate in candidates), key=_root_sort_key))
            members.append(
                _RootMember(
                    identity=identity_key,
                    representative=representative,
                    aliases=aliases,
                    runtime_identity=representative.runtime_identity,
                )
            )

        self._members = tuple(sorted(members, key=lambda member: member.identity))
        self._identity = dict(identity)
        self._lock_factory = WriterLock if lock_factory is None else lock_factory
        self._active_members: list[_AcquiredMember] = []
        self._locks: tuple[Any, ...] = ()
        self._acquired: list[Any] = []
        self._lease_token: _LeaseState | None = None
        self._locked_roots: tuple[LockedRoot, ...] = ()
        self.paths: tuple[Path, ...] = ()
        self._owner_token = object()
        self._owner_nonce = secrets.token_hex(16)
        self._owner_reservation: Any | None = None
        self._full_owner_terminal = False

    def _reserve_release_owner(self) -> None:
        if self._owner_reservation is not None:
            raise ConflictError("composite release owner is already reserved")
        self._full_owner_terminal = False
        self._owner_reservation = _reserve_full_owner(
            _full_owner_key(
                "composite-release",
                tuple(str(member.identity) for member in self._members),
                self._owner_nonce,
            )
        )

    def _clear_release_owner(self) -> None:
        reservation, self._owner_reservation = self._owner_reservation, None
        _release_full_owner(reservation)

    @staticmethod
    def _member_release_pending(acquired: _AcquiredMember) -> bool:
        lock = acquired.lock
        if lock is None:
            return False
        retained = getattr(lock, "_has_retained_release", None)
        if callable(retained):
            return bool(retained())
        return bool(
            getattr(lock, "release_pending", False)
            or (getattr(lock, "_posix_backend_entered", False) and not getattr(lock, "_posix_release_complete", False))
        )

    def _prepare_member(self, acquired: _AcquiredMember) -> None:
        member = acquired.member
        try:
            root_anchor = _open_directory_anchor(member.representative.alias, delete_protect=True)
        except ConflictError as exc:
            cause = exc.__cause__
            lock_path = member.representative.runtime_final_path / "writer.lock"
            lock_state, _, _ = inspect_lock(lock_path)
            if (
                os.name == "nt"
                and isinstance(cause, OSError)
                and _is_windows_sharing_violation(cause)
                and lock_state == "live"
            ):
                raise WriterLockContentionError(f"writer lock exists: {lock_path}") from exc
            raise
        acquired.root_anchor = root_anchor
        if root_anchor.identity != member.identity:
            raise ConflictError("composite root identity changed before acquisition")

        runtime_anchor = _open_directory_anchor(
            root_anchor.final_path / "runtime",
            reject_reparse=True,
            delete_protect=True,
        )
        acquired.runtime_anchor = runtime_anchor
        if runtime_anchor.identity != member.runtime_identity:
            raise ConflictError("composite runtime identity changed before acquisition")
        current_root_identity, current_root_final_path = root_anchor.refresh()
        if current_root_identity != member.identity or current_root_final_path != root_anchor.final_path:
            raise ConflictError("composite root anchor changed during acquisition")

        lock_path = runtime_anchor.final_path / "writer.lock"
        lock = self._lock_factory(lock_path, self._identity)
        acquired.lock = lock
        lock.__enter__()
        acquired.lock_entered = True
        transfer = getattr(lock, "_transfer_to_composite", None)
        if callable(transfer):
            transfer(self._owner_token)
            acquired.release_owned_by_composite = True

    def _final_fence(self, acquired_members: list[_AcquiredMember]) -> None:
        for member in self._members:
            for alias in member.aliases:
                observer: _DirectoryAnchor | None = None
                fence_error: BaseException | None = None
                try:
                    observer = _open_directory_anchor(alias)
                    if observer.identity != member.identity:
                        raise ConflictError("composite root alias changed before protected work")
                except BaseException as exc:
                    fence_error = exc
                close_error: BaseException | None = None
                if observer is not None:
                    try:
                        observer.close()
                    except BaseException as exc:
                        close_error = exc
                if fence_error is not None:
                    _raise_primary_with_cleanup(fence_error, close_error)
                if close_error is not None:
                    raise close_error

        for acquired in acquired_members:
            member = acquired.member
            root_anchor = acquired.root_anchor
            runtime_anchor = acquired.runtime_anchor
            lock = acquired.lock
            if root_anchor is None or runtime_anchor is None or lock is None or not acquired.lock_entered:
                raise ConflictError("composite lock member is incomplete")

            root_identity, root_final_path = root_anchor.refresh()
            if root_identity != member.identity or root_final_path != root_anchor.final_path:
                raise ConflictError("composite root anchor changed before protected work")
            runtime_identity, runtime_final_path = runtime_anchor.refresh()
            if runtime_identity != member.runtime_identity or runtime_final_path != runtime_anchor.final_path:
                raise ConflictError("composite runtime anchor changed before protected work")
            _verify_writer_lock(lock, runtime_anchor.final_path)

    def _cleanup_members(
        self,
        acquired_members: Iterable[_AcquiredMember],
        *,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> BaseException | None:
        members = tuple(acquired_members)
        first_error: BaseException | None = None

        def retain_terminal_error(error: BaseException) -> None:
            nonlocal first_error
            if first_error is None:
                first_error = error
            else:
                _append_cleanup_cause(first_error, error)

        for acquired in reversed(members):
            if not acquired.lock_entered or acquired.lock is None:
                continue
            member_error: BaseException | None = None
            for attempt in range(3):
                try:
                    release = getattr(acquired.lock, "_release_from_composite", None)
                    if acquired.release_owned_by_composite and callable(release):
                        release(self._owner_token, exc_type, exc, traceback)
                    else:
                        acquired.lock.__exit__(exc_type, exc, traceback)
                except BaseException as error:
                    if member_error is None:
                        member_error = error
                    else:
                        _append_cleanup_cause(member_error, error)
                    if not self._member_release_pending(acquired):
                        acquired.lock_entered = False
                        retain_terminal_error(member_error)
                        break
                    if attempt < 2:
                        time.sleep(0.01 * (attempt + 1))
                else:
                    acquired.lock_entered = False
                    # A bounded retry completed the release. Its earlier
                    # transient errors are diagnostics, not terminal cleanup
                    # failures for this composite operation.
                    member_error = None
                    break
            if acquired.lock_entered and member_error is not None:
                retain_terminal_error(member_error)

        for acquired in reversed(members):
            if acquired.lock_entered:
                continue
            for attribute in ("runtime_anchor", "root_anchor"):
                anchor = getattr(acquired, attribute)
                try:
                    _close_anchor(anchor)
                except BaseException as close_error:
                    retain_terminal_error(close_error)
                else:
                    setattr(acquired, attribute, None)
            if acquired.runtime_anchor is None and acquired.root_anchor is None:
                acquired.lock = None
        return first_error

    def __enter__(self) -> Self:
        if self._lease_token is not None or self._active_members:
            raise RuntimeError("composite writer lock cannot be entered twice")

        drain_retained_transaction_owners()
        self._reserve_release_owner()
        lease_token = _LeaseState()
        self._lease_token = lease_token
        acquired_members: list[_AcquiredMember] = []
        try:
            for member in self._members:
                acquired = _AcquiredMember(member)
                acquired_members.append(acquired)
                self._prepare_member(acquired)
            self._final_fence(acquired_members)

            locked_roots = tuple(
                LockedRoot._create(
                    identity=acquired.member.identity,
                    final_path=acquired.root_anchor.final_path,  # type: ignore[union-attr]
                    runtime_identity=acquired.member.runtime_identity,
                    runtime_final_path=acquired.runtime_anchor.final_path,  # type: ignore[union-attr]
                    aliases=acquired.member.aliases,
                    lease_token=lease_token,
                    anchor=acquired.root_anchor,  # type: ignore[arg-type]
                    runtime_anchor=acquired.runtime_anchor,  # type: ignore[arg-type]
                )
                for acquired in acquired_members
            )
            self._active_members = acquired_members
            self._locks = tuple(acquired.lock for acquired in acquired_members)
            self._acquired = [acquired.lock for acquired in acquired_members]
            self._locked_roots = locked_roots
            self.paths = tuple(Path(acquired.lock.path) for acquired in acquired_members)
            return self
        except BaseException as acquisition_error:
            lease_token.invalidate()
            cleanup_error = self._cleanup_members(
                acquired_members,
                exc_type=None,
                exc=None,
                traceback=None,
            )
            pending = [
                member
                for member in acquired_members
                if member.lock_entered or member.runtime_anchor is not None or member.root_anchor is not None
            ]
            self._active_members = pending
            self._locks = tuple(member.lock for member in pending)
            self._acquired = list(self._locks)
            if pending:
                reservation = self._owner_reservation
                if reservation is None:
                    raise ConflictError("composite release owner is unavailable")
                _transfer_full_owner(reservation, self)
            else:
                self._full_owner_terminal = True
                self._clear_release_owner()
            self._lease_token = None
            self._locked_roots = ()
            self.paths = ()
            if cleanup_error is not None:
                _raise_primary_with_cleanup(acquisition_error, cleanup_error)
            raise

    def locked_root(self, path: Path) -> LockedRoot:
        if self._lease_token is None or not self._active_members:
            raise ConflictError("composite lock lease is not live")
        observer: _DirectoryAnchor | None = None
        try:
            observer = _open_directory_anchor(Path(path))
            matches = tuple(
                locked_root for locked_root in self._locked_roots if locked_root.identity == observer.identity
            )
        finally:
            if observer is not None:
                observer.close()
        if len(matches) != 1:
            raise ConflictError("path does not resolve to exactly one locked root")
        return self._validate_locked_root(matches[0])

    def _validate_locked_root(self, locked_root: LockedRoot) -> LockedRoot:
        lease_token = self._lease_token
        if lease_token is None or not lease_token.live or not self._active_members:
            raise ConflictError("composite lock lease is not live")
        if type(locked_root) is not LockedRoot or locked_root._lease_token is not lease_token:
            raise ConflictError("composite lock lease token is not live")
        if sum(candidate == locked_root for candidate in self._locked_roots) != 1:
            raise ConflictError("locked root is not a member of this composite lease")
        return locked_root

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        reservation = self._owner_reservation
        if reservation is not None and getattr(reservation, "transferred", False):
            try:
                terminal = self._retry_full_owner_release()
            except BaseException as retry_error:
                if exc is not None:
                    raise exc.with_traceback(traceback) from retry_error
                raise
            if terminal:
                return False
            raise ConflictError("composite retained release remains pending")
        active_members = self._active_members
        lease_token, self._lease_token = self._lease_token, None
        if lease_token is not None:
            lease_token.invalidate()
        self._locked_roots = ()
        self.paths = ()
        first_error = self._cleanup_members(
            active_members,
            exc_type=exc_type,
            exc=exc,
            traceback=traceback,
        )
        pending = [
            member
            for member in active_members
            if member.lock_entered or member.runtime_anchor is not None or member.root_anchor is not None
        ]
        self._active_members = pending
        self._locks = tuple(member.lock for member in pending)
        self._acquired = list(self._locks)
        if pending:
            if reservation is None:
                raise ConflictError("composite release owner is unavailable")
            _transfer_full_owner(reservation, self)
        else:
            self._full_owner_terminal = True
            self._clear_release_owner()
        if first_error is not None:
            if exc is not None:
                raise exc.with_traceback(traceback) from first_error
            raise first_error
        return False

    def _retry_full_owner_release(self) -> bool:
        """Retry the whole retained Composite only from the registry safe point."""

        first_error = self._cleanup_members(
            self._active_members,
            exc_type=None,
            exc=None,
            traceback=None,
        )
        pending = [
            member
            for member in self._active_members
            if member.lock_entered or member.runtime_anchor is not None or member.root_anchor is not None
        ]
        self._active_members = pending
        self._locks = tuple(member.lock for member in pending)
        self._acquired = list(self._locks)
        self._full_owner_terminal = not pending
        if self._full_owner_terminal:
            self._clear_release_owner()
        if first_error is not None:
            raise first_error
        return self._full_owner_terminal
