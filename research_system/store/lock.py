from __future__ import annotations

import ctypes
import json
import os
import stat
import sys
import time
from contextlib import contextmanager
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
import secrets
import threading
from types import TracebackType
from typing import Any, Iterator, Literal, NoReturn, Protocol, Self

from research_system.canonical import canonical_bytes
from research_system.errors import ConflictError
from research_system.store.durability import fsync_directory


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


_WINDOWS_CLOSE_QUARANTINE: list[_PendingWindowsClose] = []
_WINDOWS_CLOSE_QUARANTINE_LOCK = threading.Lock()


class WriterLockContentionError(ConflictError):
    pass


class _ClaimNameCollisionError(ConflictError):
    pass


class _ExactGenerationBusyError(ConflictError):
    pass


class _WindowsQuarantineBusyError(ConflictError):
    pass


class DirectoryMutationGuard:
    __slots__ = ("_anchor", "_active", "_descriptor", "name")

    def __init__(self, anchor: object, name: str) -> None:
        self._anchor = anchor
        self._active = False
        self._descriptor: int | None = None
        self.name = name

    def _verify_canonical_generation(self) -> None:
        """Prove the held POSIX flock still names the guard generation in the anchor."""

        if os.name != "posix":
            return
        descriptor = self._descriptor
        anchor = self._anchor
        if descriptor is None or not isinstance(anchor, _DirectoryAnchor):
            raise ConflictError("anchored directory mutation guard ownership is unavailable")
        try:
            opened = os.fstat(descriptor)
            current = os.stat(self.name, dir_fd=int(anchor._handle), follow_symlinks=False)
        except (OSError, ValueError) as exc:
            raise ConflictError("anchored directory mutation guard generation is unavailable") from exc
        if (
            not stat.S_ISREG(opened.st_mode)
            or not stat.S_ISREG(current.st_mode)
            or not os.path.samestat(opened, current)
        ):
            raise ConflictError("anchored directory mutation guard generation changed while held")


def _is_windows_sharing_violation(error: OSError) -> bool:
    return getattr(error, "winerror", None) == 32 or error.errno == 32


def _supports_exact_writer_lock_deletion() -> bool:
    return os.name == "nt" or (os.name == "posix" and sys.platform == "linux")


def _link_without_following(source: Path, destination: Path) -> None:
    os.link(source, destination, follow_symlinks=False)


def _before_exact_generation_unlink(_path: Path) -> None:
    pass


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

    def stage_private_file(self, name: str, data: bytes) -> tuple[str, os.stat_result]: ...

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

    def write_exact_file(self, name: str, data: bytes) -> None: ...

    def replace_exact_file(self, name: str, expected: bytes, data: bytes) -> None: ...

    def remove_exact_file(self, name: str, expected: bytes) -> None: ...

    def remove_exact_generation(
        self,
        name: str,
        expected: os.stat_result,
        expected_bytes: bytes,
        *,
        guard: DirectoryMutationGuard | None = None,
    ) -> None: ...

    def remove_exact_generation_after_parent_change(
        self,
        name: str,
        expected: os.stat_result,
        expected_bytes: bytes,
        *,
        guard: DirectoryMutationGuard,
    ) -> None: ...

    def acquire_mutation_guard(self, name: str) -> Iterator[DirectoryMutationGuard]: ...

    def close(self) -> None: ...


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

    def write_exact_file(self, relative_path: str, data: bytes) -> None:
        parent, name, opened = self._open_relative_file_parent(relative_path, create=True)
        with self._closing_relative_file_parents(opened):
            if os.name == "nt":
                parent.write_exact_file(name, data)
            else:
                with parent.acquire_mutation_guard(".locked-root-mutation.guard"):
                    parent.write_exact_file(name, data)

    def replace_exact_file(self, relative_path: str, expected: bytes, data: bytes) -> None:
        parent, name, opened = self._open_relative_file_parent(relative_path, create=False)
        with self._closing_relative_file_parents(opened):
            if os.name == "nt":
                parent.replace_exact_file(name, expected, data)
            else:
                with parent.acquire_mutation_guard(".locked-root-mutation.guard"):
                    parent.replace_exact_file(name, expected, data)

    def remove_exact_file(self, relative_path: str, expected: bytes) -> None:
        parent, name, opened = self._open_relative_file_parent(relative_path, create=False)
        with self._closing_relative_file_parents(opened):
            if os.name == "nt":
                parent.remove_exact_file(name, expected)
            else:
                with parent.acquire_mutation_guard(".locked-root-mutation.guard"):
                    parent.remove_exact_file(name, expected)


class _DirectoryAnchor:
    __slots__ = (
        "identity",
        "final_path",
        "_parent",
        "_active_mutation_guard",
        "_deferred_windows_closures",
        "_handle",
        "_refresh_impl",
        "_close_impl",
        "_delete_protected",
        "_quarantined",
        "_closed",
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
        self._deferred_windows_closures: list[_PendingWindowsClose] = []
        self._handle = handle
        self._refresh_impl = refresh_impl
        self._close_impl = close_impl
        self._delete_protected = delete_protected
        self._quarantined = False
        self._closed = False

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
        if not self._deferred_windows_closures:
            return
        pending = self._deferred_windows_closures
        self._deferred_windows_closures = []
        cleanup_error: BaseException | None = None
        for close in pending:
            try:
                close.closer(close.resource)
            except BaseException as exc:
                self._deferred_windows_closures.append(close)
                cleanup_error = _add_cleanup_error(
                    cleanup_error, exc, f"anchored Windows {close.phase} close retry failed"
                )
        if cleanup_error is not None:
            raise ConflictError("anchored Windows resource cleanup remains pending") from cleanup_error

    def _close_or_defer_windows_resource(self, resource: object, closer: Callable[[object], None]) -> None:
        pending = _PendingWindowsClose("anchor", resource, closer)
        try:
            closer(resource)
        except BaseException:
            self._deferred_windows_closures.append(pending)
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
        try:
            if os.name == "nt":
                child_path = parent_path / name
                if create:
                    try:
                        child_path.mkdir()
                    except FileExistsError:
                        pass
                    fsync_directory(parent_path)
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
                        self._verify_active_posix_mutation_guard()
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
        except FileNotFoundError:
            raise
        except ConflictError:
            raise
        except OSError as exc:
            raise ConflictError(f"{name} is not a physical member directory") from exc
        child._parent = self
        try:
            self.verify_unchanged()
        except BaseException:
            child.close()
            raise ConflictError("anchored parent directory changed during member traversal")
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
        try:
            if os.name == "nt":
                descriptor = os.open(final_path / name, os.O_RDONLY | getattr(os, "O_BINARY", 0))
            else:
                nofollow = getattr(os, "O_NOFOLLOW", 0)
                if not nofollow or os.open not in os.supports_dir_fd:
                    raise ConflictError("platform cannot read an anchored regular file")
                descriptor = os.open(name, os.O_RDONLY | nofollow, dir_fd=int(self._handle))
            with os.fdopen(descriptor, "rb") as handle:
                descriptor = None
                opened = os.fstat(handle.fileno())
                if not stat.S_ISREG(opened.st_mode) or not os.path.samestat(before, opened):
                    raise ConflictError("anchored directory member is not the observed regular file")
                data = handle.read()
            after = self._member_identity(name, final_path)
            if not os.path.samestat(opened, after):
                raise ConflictError("anchored directory member changed during read")
            return data, after
        except FileNotFoundError:
            raise
        except ConflictError:
            raise
        except OSError as exc:
            raise ConflictError("anchored regular file cannot be read") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)

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
                    self._close_or_defer_windows_resource(fence, _windows_close_handle)
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
        self._verify_active_posix_mutation_guard()
        os.link(
            source,
            destination,
            src_dir_fd=int(self._handle),
            dst_dir_fd=int(self._handle),
            follow_symlinks=False,
        )

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
        self._verify_active_posix_mutation_guard()
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

    def remove_exact_generation_after_parent_change(
        self,
        name: str,
        expected_identity: os.stat_result,
        expected_bytes: bytes,
        *,
        guard: DirectoryMutationGuard,
    ) -> None:
        self._require_member_name(name)
        self._validate_mutation_guard(guard)
        directory_identity, final_path = self.refresh()
        if directory_identity != self.identity:
            raise ConflictError("anchored directory identity changed during recovery deletion")
        with self._effect_final_path(final_path) as effect_path:
            self._unlink_member(name, expected_identity, expected_bytes, effect_path)
            self._fsync_directory(effect_path)
        refreshed_identity, _refreshed_path = self.refresh()
        if refreshed_identity != directory_identity:
            raise ConflictError("anchored directory identity changed during recovery deletion")

    def _validate_mutation_guard(self, guard: DirectoryMutationGuard) -> None:
        if guard._anchor is not self or not guard._active or self._active_mutation_guard is not guard:
            raise ConflictError("anchored directory mutation guard is not active")
        guard._verify_canonical_generation()

    def _verify_active_posix_mutation_guard(self) -> None:
        if os.name != "posix":
            return
        guard = self._active_mutation_guard
        if guard is not None:
            self._validate_mutation_guard(guard)

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
                    try:
                        os.lseek(descriptor, 0, 0)
                        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                    except BaseException as exc:
                        cleanup_error = _add_cleanup_error(cleanup_error, exc, "mutation-guard unlock also failed")
                if descriptor is not None:
                    try:
                        self._close_or_defer_windows_resource(descriptor, os.close)
                    except BaseException as exc:
                        cleanup_error = _add_cleanup_error(cleanup_error, exc, "mutation-guard close also failed")
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
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            locked = True
            guard._descriptor = descriptor
            guard._verify_canonical_generation()
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
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                except BaseException as error:
                    cleanup_error = error
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except BaseException as error:
                    cleanup_error = _add_cleanup_error(cleanup_error, error, "mutation-guard close also failed")
                finally:
                    guard._descriptor = None
        if primary_error is not None:
            _raise_primary_with_cleanup(primary_error, cleanup_error)
        if cleanup_error is not None:
            raise cleanup_error

    def _stage_private_file(self, name: str, data: bytes, final_path: Path) -> tuple[str, os.stat_result]:
        temporary = f".{name}.{secrets.token_hex(16)}.tmp"
        descriptor: int | None = None
        temporary_identity: os.stat_result | None = None
        try:
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
            if os.name == "nt":
                descriptor = os.open(final_path / temporary, flags, 0o600)
            else:
                nofollow = getattr(os, "O_NOFOLLOW", 0)
                if not nofollow or os.open not in os.supports_dir_fd:
                    raise ConflictError("platform cannot write an anchored regular file")
                self._verify_active_posix_mutation_guard()
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
            os.close(descriptor)
            descriptor = None
            if not os.path.samestat(temporary_identity, self._member_identity(temporary, final_path)):
                raise ConflictError("anchored private publication changed after fsync")
            return temporary, temporary_identity
        except BaseException as primary_error:
            cleanup_error: BaseException | None = None
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except BaseException as exc:
                    cleanup_error = exc
            if temporary_identity is not None:
                try:
                    self._remove_owned_generation(temporary, temporary_identity, data, final_path)
                except FileNotFoundError:
                    pass
                except BaseException as exc:
                    if cleanup_error is None:
                        cleanup_error = exc
            _raise_primary_with_cleanup(primary_error, cleanup_error)

    def stage_private_file(self, name: str, data: bytes) -> tuple[str, os.stat_result]:
        self._require_member_name(name)
        if not isinstance(data, bytes):
            raise TypeError("anchored file content must be bytes")
        self.verify_unchanged()
        _identity, final_path = self.refresh()
        with self._effect_final_path(final_path) as effect_path:
            return self._stage_private_file(name, data, effect_path)

    def _claim_generation(
        self,
        source: str,
        expected_identity: os.stat_result,
        expected_bytes: bytes,
        claim: str,
        final_path: Path,
    ) -> os.stat_result:
        self._require_member_name(source)
        self._require_member_name(claim)
        if not os.path.samestat(expected_identity, self._member_identity(source, final_path)):
            raise ConflictError("anchored file changed before claim")
        claim_identity: os.stat_result | None = None
        source_removed = False
        try:
            try:
                self._link_member(source, claim, final_path)
            except FileExistsError as exc:
                raise _ClaimNameCollisionError("anchored claim name already exists") from exc
            claim_identity = self._member_identity(claim, final_path)
            if not os.path.samestat(expected_identity, claim_identity):
                raise ConflictError("anchored claim changed while created")
            claim_data, claimed_identity = self._read_regular_file_with_identity(claim, final_path)
            if claim_data != expected_bytes or not os.path.samestat(expected_identity, claimed_identity):
                raise ConflictError("anchored claim bytes changed while created")
            if not os.path.samestat(expected_identity, self._member_identity(source, final_path)):
                raise ConflictError("anchored file changed before claim source removal")
            self._unlink_member(source, expected_identity, expected_bytes, final_path)
            source_removed = True
            if not os.path.samestat(expected_identity, self._member_identity(claim, final_path)):
                raise ConflictError("anchored claim changed after source removal")
            return claim_identity
        except BaseException as primary_error:
            cleanup_error: BaseException | None = None
            if (
                claim_identity is not None
                and os.path.samestat(expected_identity, claim_identity)
                and not source_removed
            ):
                try:
                    self._unlink_claimed_generation(claim, claim_identity, expected_bytes, final_path)
                except FileNotFoundError:
                    pass
                except BaseException as exc:
                    cleanup_error = exc
            _raise_primary_with_cleanup(primary_error, cleanup_error)

    def _unlink_claimed_generation(
        self,
        claim: str,
        expected_identity: os.stat_result,
        expected_bytes: bytes,
        final_path: Path,
    ) -> None:
        if not os.path.samestat(expected_identity, self._member_identity(claim, final_path)):
            raise ConflictError("anchored claim changed before unlink")
        self._unlink_member(claim, expected_identity, expected_bytes, final_path)

    def _remove_owned_generation(
        self,
        name: str,
        expected_identity: os.stat_result,
        expected_bytes: bytes,
        final_path: Path,
    ) -> None:
        stem = name if name.startswith(".") else f".{name}"
        for _attempt in range(8):
            claim = f"{stem}.{secrets.token_hex(16)}.remove"
            try:
                claim_identity = self._claim_generation(name, expected_identity, expected_bytes, claim, final_path)
            except _ClaimNameCollisionError:
                continue
            self._unlink_claimed_generation(claim, claim_identity, expected_bytes, final_path)
            return
        raise ConflictError("anchored removal claim name cannot be acquired")

    def _read_claim_or_none(
        self,
        claim: str,
        expected: bytes,
        final_path: Path,
    ) -> os.stat_result | None:
        try:
            data, identity = self._read_regular_file_with_identity(claim, final_path)
        except FileNotFoundError:
            return None
        if data != expected:
            raise ConflictError("anchored claim already binds different bytes")
        return identity

    def write_exact_file(self, name: str, data: bytes) -> None:
        self._require_member_name(name)
        if not isinstance(data, bytes):
            raise TypeError("anchored file content must be bytes")
        directory_identity, final_path = self.refresh()
        claim = f".{name}.publication-claim"
        claim_identity = self._read_claim_or_none(claim, data, final_path)
        claim_created = False
        if claim_identity is None:
            temporary, temporary_identity = self._stage_private_file(name, data, final_path)
            try:
                claim_identity = self._claim_generation(temporary, temporary_identity, data, claim, final_path)
                claim_created = True
                self._fsync_directory(final_path)
            except BaseException:
                try:
                    self._remove_owned_generation(temporary, temporary_identity, data, final_path)
                except FileNotFoundError:
                    pass
                except ConflictError:
                    pass
                raise

        assert claim_identity is not None
        published_identity: os.stat_result | None = None
        primary_error: BaseException | None = None
        keep_claim_for_recovery = False
        try:
            try:
                self._link_member(claim, name, final_path)
                published_identity = self._member_identity(name, final_path)
                if not os.path.samestat(claim_identity, published_identity):
                    raise ConflictError("anchored final changed during publication")
                self._fsync_directory(final_path)
            except FileExistsError:
                existing, published_identity = self._read_regular_file_with_identity(name, final_path)
                if existing != data:
                    raise ConflictError("anchored file identity already binds different bytes")
            final_data, _ = self._read_regular_file_with_identity(name, final_path)
            if final_data != data:
                raise ConflictError("anchored regular file publication did not remain exact")
            self._unlink_claimed_generation(claim, claim_identity, data, final_path)
            self._fsync_directory(final_path)
            final_data, final_identity = self._read_regular_file_with_identity(name, final_path)
            if final_data != data or (
                published_identity is not None and not os.path.samestat(final_identity, published_identity)
            ):
                raise ConflictError("anchored regular file publication did not remain exact")
        except OSError as exc:
            primary_error = ConflictError("anchored regular file cannot be published")
            primary_error.__cause__ = exc
            keep_claim_for_recovery = True
        except BaseException as exc:
            primary_error = exc

        if primary_error is not None:
            cleanup_error: BaseException | None = None
            if not keep_claim_for_recovery and claim_created:
                try:
                    self._unlink_claimed_generation(claim, claim_identity, data, final_path)
                    self._fsync_directory(final_path)
                except FileNotFoundError:
                    pass
                except BaseException as exc:
                    cleanup_error = exc
            _raise_primary_with_cleanup(primary_error, cleanup_error)

        refreshed_identity, refreshed_path = self.refresh()
        if refreshed_identity != directory_identity or refreshed_path != final_path:
            raise ConflictError("anchored directory identity changed during file publication")

    def replace_exact_file(self, name: str, expected: bytes, data: bytes) -> None:
        self._require_member_name(name)
        if not isinstance(expected, bytes) or not isinstance(data, bytes):
            raise TypeError("anchored file content must be bytes")
        if expected == data:
            _directory_identity, final_path = self.refresh()
            current, _ = self._read_regular_file_with_identity(name, final_path)
            if current != expected:
                raise ConflictError("anchored file replacement expected bytes differ")
            return

        directory_identity, final_path = self.refresh()
        predecessor_claim = f".{name}.replacement-predecessor-claim"
        publication_claim = f".{name}.replacement-publication-claim"

        old_claim_identity = self._read_claim_or_none(predecessor_claim, expected, final_path)
        try:
            source_data, source_identity = self._read_regular_file_with_identity(name, final_path)
        except FileNotFoundError:
            source_data = None
            source_identity = None
        committed_final_identity: os.stat_result | None = None
        if source_identity is not None:
            if source_data != expected:
                if old_claim_identity is not None and source_data == data:
                    committed_final_identity = source_identity
                    source_identity = None
                else:
                    raise ConflictError("anchored file replacement expected bytes differ")
            elif old_claim_identity is not None and not os.path.samestat(old_claim_identity, source_identity):
                raise ConflictError("anchored predecessor claim does not own the observed generation")
        elif old_claim_identity is None:
            raise ConflictError("anchored file replacement expected predecessor is missing")

        new_claim_identity = self._read_claim_or_none(publication_claim, data, final_path)
        committed_recovery_without_publication_claim = (
            committed_final_identity is not None and new_claim_identity is None
        )
        new_claim_created = False
        if new_claim_identity is None:
            if committed_recovery_without_publication_claim:
                new_claim_identity = committed_final_identity
            else:
                temporary, temporary_identity = self._stage_private_file(name, data, final_path)
                try:
                    new_claim_identity = self._claim_generation(
                        temporary, temporary_identity, data, publication_claim, final_path
                    )
                    new_claim_created = True
                    self._fsync_directory(final_path)
                except BaseException:
                    try:
                        self._remove_owned_generation(temporary, temporary_identity, data, final_path)
                    except (FileNotFoundError, ConflictError):
                        pass
                    raise

        assert new_claim_identity is not None
        primary_error: BaseException | None = None
        keep_claims_for_recovery = False
        try:
            if old_claim_identity is None:
                assert source_identity is not None
                old_claim_identity = self._claim_generation(
                    name,
                    source_identity,
                    expected,
                    predecessor_claim,
                    final_path,
                )
                self._fsync_directory(final_path)
            elif source_identity is not None:
                if not os.path.samestat(old_claim_identity, self._member_identity(name, final_path)):
                    raise ConflictError("anchored predecessor changed before source removal")
                self._unlink_member(name, old_claim_identity, expected, final_path)
                self._fsync_directory(final_path)
                if not os.path.samestat(old_claim_identity, self._member_identity(predecessor_claim, final_path)):
                    raise ConflictError("anchored predecessor claim changed after source removal")

            if committed_recovery_without_publication_claim:
                final_identity = committed_final_identity
            else:
                try:
                    self._link_member(publication_claim, name, final_path)
                    final_identity = self._member_identity(name, final_path)
                    if not os.path.samestat(new_claim_identity, final_identity):
                        raise ConflictError("anchored final changed during replacement publication")
                    self._fsync_directory(final_path)
                except FileExistsError:
                    final_data, final_identity = self._read_regular_file_with_identity(name, final_path)
                    if final_data != data:
                        raise ConflictError("anchored replacement final already binds different bytes")
            final_data, final_identity = self._read_regular_file_with_identity(name, final_path)
            if final_data != data or not os.path.samestat(new_claim_identity, final_identity):
                raise ConflictError("anchored replacement publication did not remain exact")
            if not committed_recovery_without_publication_claim:
                self._unlink_claimed_generation(publication_claim, new_claim_identity, data, final_path)
            self._unlink_claimed_generation(predecessor_claim, old_claim_identity, expected, final_path)
            self._fsync_directory(final_path)
            final_data, verified_final_identity = self._read_regular_file_with_identity(name, final_path)
            if final_data != data or not os.path.samestat(final_identity, verified_final_identity):
                raise ConflictError("anchored replacement publication did not remain exact")
        except OSError as exc:
            primary_error = ConflictError("anchored regular file cannot be replaced")
            primary_error.__cause__ = exc
            keep_claims_for_recovery = True
        except BaseException as exc:
            primary_error = exc

        if primary_error is not None:
            cleanup_error: BaseException | None = None
            if not keep_claims_for_recovery and new_claim_created:
                try:
                    self._unlink_claimed_generation(publication_claim, new_claim_identity, data, final_path)
                    self._fsync_directory(final_path)
                except FileNotFoundError:
                    pass
                except BaseException as exc:
                    cleanup_error = exc
            _raise_primary_with_cleanup(primary_error, cleanup_error)

        refreshed_identity, refreshed_path = self.refresh()
        if refreshed_identity != directory_identity or refreshed_path != final_path:
            raise ConflictError("anchored directory identity changed during file replacement")

    def remove_exact_file(self, name: str, expected: bytes) -> None:
        self._require_member_name(name)
        if not isinstance(expected, bytes):
            raise TypeError("anchored file content must be bytes")
        directory_identity, final_path = self.refresh()
        try:
            data, source_identity = self._read_regular_file_with_identity(name, final_path)
        except FileNotFoundError as exc:
            raise ConflictError("anchored file changed before removal") from exc
        if data != expected:
            raise ConflictError("anchored file removal expected bytes differ")
        try:
            self._remove_owned_generation(name, source_identity, expected, final_path)
            self._fsync_directory(final_path)
        except FileNotFoundError as exc:
            raise ConflictError("anchored file changed before removal") from exc
        refreshed_identity, refreshed_path = self.refresh()
        if refreshed_identity != directory_identity or refreshed_path != final_path:
            raise ConflictError("anchored directory identity changed during file removal")

    def _close_without_quarantine(self) -> None:
        if self._closed:
            return
        self._retry_deferred_windows_closures()
        self._close_impl(self._handle)
        self._closed = True
        self._quarantined = False

    def close(self) -> None:
        if self._quarantined:
            _drain_windows_close_quarantine()
            return
        try:
            self._close_without_quarantine()
        except BaseException:
            if os.name == "nt":
                self._quarantined = True
                with _WINDOWS_CLOSE_QUARANTINE_LOCK:
                    _WINDOWS_CLOSE_QUARANTINE.append(
                        _PendingWindowsClose("anchor", self, lambda value: value._close_without_quarantine())
                    )
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
        delete_access = delete_protect
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
    return handle


def _windows_read_handle(handle: object) -> bytes:
    chunks: list[bytes] = []
    while True:
        buffer = ctypes.create_string_buffer(1024 * 1024)
        count = wintypes.DWORD()
        if not _KERNEL32.ReadFile(handle, buffer, len(buffer), ctypes.byref(count), None):
            raise _windows_api_error("ReadFile")
        if count.value == 0:
            return b"".join(chunks)
        chunks.append(buffer.raw[: count.value])


def _windows_close_handle(handle: object) -> None:
    if not _KERNEL32.CloseHandle(handle):
        raise _windows_api_error("CloseHandle")


def _drain_windows_close_quarantine() -> None:
    if os.name != "nt":
        return
    with _WINDOWS_CLOSE_QUARANTINE_LOCK:
        retained: list[_PendingWindowsClose] = []
        error: BaseException | None = None
        for pending in _WINDOWS_CLOSE_QUARANTINE:
            try:
                pending.closer(pending.resource)
            except BaseException as exc:
                retained.append(pending)
                error = _add_cleanup_error(error, exc, f"Windows {pending.phase} close retry failed")
        _WINDOWS_CLOSE_QUARANTINE[:] = retained
        if error is not None:
            raise _WindowsQuarantineBusyError("Windows handle cleanup remains pending") from error


def _close_or_retain_windows_resource(
    pending: _PendingWindowsClose,
    release: _WindowsReleaseState | None = None,
) -> None:
    try:
        pending.closer(pending.resource)
    except BaseException:
        if release is not None:
            release.closes += (pending,)
        else:
            with _WINDOWS_CLOSE_QUARANTINE_LOCK:
                _WINDOWS_CLOSE_QUARANTINE.append(pending)
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
        raise ConflictError("Windows directory returned an unusable file identity")
    return DirectoryIdentity(
        "windows-file-id-v1",
        int(info.VolumeSerialNumber),
        file_id,
    )


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
    parent_descriptor: int | None = None,
    release: _WindowsReleaseState | None = None,
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
            share_mode=_FILE_SHARE_READ,
        )
        attributes, _ = _windows_file_attribute_tag(handle)
        if attributes & _FILE_ATTRIBUTE_REPARSE_POINT:
            raise ConflictError(f"{label} must be a physical regular file")
        if attributes & _FILE_ATTRIBUTE_DIRECTORY:
            raise ConflictError(f"{label} must be a regular file")
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
                _close_or_retain_windows_resource(
                    _PendingWindowsClose(close_phase, handle, _windows_close_handle, disposition_applied),
                    release,
                )
            except OSError as close_error:
                if primary_error is None:
                    wrapped = ConflictError(f"{label} exact generation deletion handle cannot close")
                    wrapped.__cause__ = close_error
                    primary_error = wrapped
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
                _close_or_retain_windows_resource(_PendingWindowsClose("anchor", probe, _windows_close_handle))
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
                _close_or_retain_windows_resource(_PendingWindowsClose("anchor", candidate, _windows_close_handle))
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


def open_registered_member_directory_anchor(path: Path) -> DirectoryAnchor:
    """Open one non-reparse member directory with replacement protection."""

    return _open_directory_anchor(path, reject_reparse=True, delete_protect=True)


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
    try:
        current = os.stat(
            _posix_lock_guard_path(path).name,
            dir_fd=int(parent_anchor._handle),
            follow_symlinks=False,
        )
    except FileNotFoundError as exc:
        raise ConflictError("writer-lock guard generation changed while held") from exc
    except OSError as exc:
        raise ConflictError("writer-lock guard generation is unavailable") from exc
    if not os.path.samestat(opened, current):
        raise ConflictError("writer-lock guard generation changed while held")


def _posix_guarded_delete_lock(
    path: Path,
    expected: LockObservation,
    parent_anchor: _DirectoryAnchor,
    guard_descriptor: int,
) -> None:
    _verify_posix_lock_guard(path, guard_descriptor, parent_anchor)
    _before_exact_generation_unlink(path)
    data, identity = parent_anchor.read_regular_file_with_identity(path.name)
    if data != expected.data or not os.path.samestat(identity, expected.identity):
        raise ConflictError("writer lock generation changed before guarded deletion")
    _verify_posix_lock_guard(path, guard_descriptor, parent_anchor)
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
            _verify_posix_lock_guard(self.path, guard, parent_anchor)
            temporary, temporary_identity = parent_anchor.stage_private_file(self.path.name, self._data)
            try:
                canonical_identity = temporary_identity
                _verify_posix_lock_guard(self.path, guard, parent_anchor)
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
                )
                temporary = None
                raise WriterLockContentionError(f"writer lock exists: {self.path}") from exc
            try:
                _posix_guarded_delete_lock(
                    parent_anchor.final_path / temporary,
                    LockObservation(self._data, temporary_identity),
                    parent_anchor,
                    guard,
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

    def __enter__(self) -> Self:
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
                        with _WINDOWS_CLOSE_QUARANTINE_LOCK:
                            _WINDOWS_CLOSE_QUARANTINE.append(
                                _PendingWindowsClose(
                                    "anchor", retained_anchor, lambda value: value._close_without_quarantine()
                                )
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

    def __exit__(
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
            except FileNotFoundError as missing_error:
                release_error = ConflictError("writer lock disappeared while held")
                release_error.__cause__ = missing_error
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
                try:
                    _close_anchor(observer)
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

    @staticmethod
    def _cleanup_members(
        acquired_members: Iterable[_AcquiredMember],
        *,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> BaseException | None:
        members = tuple(acquired_members)
        first_error: BaseException | None = None
        for acquired in reversed(members):
            if not acquired.lock_entered or acquired.lock is None:
                continue
            release_error: BaseException | None = None
            for _attempt in range(3):
                try:
                    acquired.lock.__exit__(exc_type, exc, traceback)
                except BaseException as error:
                    release_error = error
                    retryable = bool(
                        getattr(acquired.lock, "_posix_backend_entered", False)
                        and not getattr(acquired.lock, "_posix_release_complete", False)
                        or getattr(acquired.lock, "release_pending", False)
                    )
                    if retryable:
                        if _attempt < 2:
                            time.sleep(0.01 * (_attempt + 1))
                        continue
                    acquired.lock_entered = False
                    break
                else:
                    acquired.lock_entered = False
                    release_error = None
                    break
            if release_error is not None and first_error is None:
                first_error = release_error

        for acquired in reversed(members):
            if acquired.lock_entered:
                continue
            for attribute in ("runtime_anchor", "root_anchor"):
                anchor = getattr(acquired, attribute)
                try:
                    _close_anchor(anchor)
                except BaseException as close_error:
                    if first_error is None:
                        first_error = close_error
                else:
                    setattr(acquired, attribute, None)
            if acquired.runtime_anchor is None and acquired.root_anchor is None:
                acquired.lock = None
        return first_error

    def __enter__(self) -> Self:
        if self._lease_token is not None or self._active_members:
            raise RuntimeError("composite writer lock cannot be entered twice")

        _drain_pending_composite_releases(self._members)
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
            owner = _retain_pending_composite_release(acquired_members)
            cleanup_error: BaseException | None = None
            if owner is not None:
                drain = _drain_pending_composite_release(owner, blocking=True)
                cleanup_error = drain.cleanup_error
                if drain.pending:
                    retry_start_error = _start_pending_composite_release_retry(owner)
                    if retry_start_error is not None:
                        cleanup_error = _add_cleanup_error(
                            cleanup_error,
                            retry_start_error,
                            "pending composite cleanup retry could not start",
                        )
            self._active_members = []
            self._locks = ()
            self._acquired = []
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
        except BaseException as primary_error:
            cleanup_error: BaseException | None = None
            try:
                _close_anchor(observer)
            except BaseException as error:
                cleanup_error = error
            _raise_primary_with_cleanup(primary_error, cleanup_error)
        _close_anchor(observer)
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
        if first_error is not None:
            if exc is not None:
                raise exc.with_traceback(traceback) from first_error
            raise first_error
        return False


@dataclass
class _PendingCompositeRelease:
    """Process-local ownership of cleanup stranded by a failed acquisition."""

    members: list[_AcquiredMember]
    drain_lock: threading.Lock = field(default_factory=threading.Lock)
    retry_deadline: float | None = None
    retry_thread: threading.Thread | None = None


@dataclass(frozen=True)
class _PendingCompositeReleaseDrain:
    cleanup_error: BaseException | None
    pending: bool
    in_progress: bool = False


_PENDING_COMPOSITE_RELEASES: dict[DirectoryIdentity, list[_PendingCompositeRelease]] = {}
_PENDING_COMPOSITE_RELEASES_LOCK = threading.RLock()
_PENDING_COMPOSITE_RETRY_DELAY_SECONDS = 0.01
_PENDING_COMPOSITE_RETRY_DEADLINE_SECONDS = 0.5


def _pending_composite_members(members: Iterable[_AcquiredMember]) -> list[_AcquiredMember]:
    return [
        member
        for member in members
        if member.lock_entered or member.runtime_anchor is not None or member.root_anchor is not None
    ]


def _remove_pending_composite_release(owner: _PendingCompositeRelease) -> None:
    with _PENDING_COMPOSITE_RELEASES_LOCK:
        for identity, owners in tuple(_PENDING_COMPOSITE_RELEASES.items()):
            remaining = [candidate for candidate in owners if candidate is not owner]
            if remaining:
                _PENDING_COMPOSITE_RELEASES[identity] = remaining
            else:
                del _PENDING_COMPOSITE_RELEASES[identity]


def _retain_pending_composite_release(members: Iterable[_AcquiredMember]) -> _PendingCompositeRelease | None:
    pending = _pending_composite_members(members)
    if not pending:
        return None
    owner = _PendingCompositeRelease(pending)
    with _PENDING_COMPOSITE_RELEASES_LOCK:
        for member in pending:
            _PENDING_COMPOSITE_RELEASES.setdefault(member.member.identity, []).append(owner)
    return owner


def _drain_pending_composite_release(
    owner: _PendingCompositeRelease,
    *,
    blocking: bool,
) -> _PendingCompositeReleaseDrain:
    """Attempt the cleanup a module-owned failed acquisition still requires.

    Registry membership is independent from the owner drain lock: unrelated
    roots can proceed while one owner's arbitrary release or close is pending.
    """

    if not owner.drain_lock.acquire(blocking=blocking):
        return _PendingCompositeReleaseDrain(cleanup_error=None, pending=True, in_progress=True)
    try:
        cleanup_error = CompositeWriterLock._cleanup_members(
            owner.members,
            exc_type=None,
            exc=None,
            traceback=None,
        )
        owner.members[:] = _pending_composite_members(owner.members)
        pending = bool(owner.members)
    finally:
        owner.drain_lock.release()
    if not pending:
        _remove_pending_composite_release(owner)
    return _PendingCompositeReleaseDrain(cleanup_error=cleanup_error, pending=pending)


def _start_pending_composite_release_retry(owner: _PendingCompositeRelease) -> BaseException | None:
    """Give a retained owner one bounded autonomous cleanup lifecycle.

    The owner is already present in the identity registry when this is called.
    Its retry thread only attempts release; overlapping acquisitions still take
    the registry lock and synchronously drain or reject before they can enter.
    """

    with owner.drain_lock:
        if not owner.members or owner.retry_thread is not None:
            return None
        owner.retry_deadline = time.monotonic() + _PENDING_COMPOSITE_RETRY_DEADLINE_SECONDS
        retry_thread = threading.Thread(
            target=_retry_pending_composite_release,
            args=(owner,),
            daemon=True,
            name="ars-pending-composite-lock-release",
        )
        owner.retry_thread = retry_thread
    try:
        retry_thread.start()
    except BaseException as error:
        with owner.drain_lock:
            if owner.retry_thread is retry_thread:
                owner.retry_thread = None
        return error
    return None


def _retry_pending_composite_release(owner: _PendingCompositeRelease) -> None:
    deadline = owner.retry_deadline
    try:
        while deadline is not None and time.monotonic() < deadline:
            time.sleep(_PENDING_COMPOSITE_RETRY_DELAY_SECONDS)
            drain = _drain_pending_composite_release(owner, blocking=False)
            if not drain.pending:
                return
    finally:
        with owner.drain_lock:
            if owner.retry_thread is threading.current_thread():
                owner.retry_thread = None


def _drain_pending_composite_releases(members: Iterable[_RootMember]) -> None:
    """Finish failed-acquisition cleanup before a later overlapping lease can enter."""

    with _PENDING_COMPOSITE_RELEASES_LOCK:
        owners: list[_PendingCompositeRelease] = []
        seen: set[int] = set()
        for member in members:
            for owner in _PENDING_COMPOSITE_RELEASES.get(member.identity, ()):
                if id(owner) not in seen:
                    seen.add(id(owner))
                    owners.append(owner)
    for owner in owners:
        drain = _drain_pending_composite_release(owner, blocking=False)
        if drain.in_progress:
            raise ConflictError("pending composite writer-lock cleanup is in progress")
        if drain.pending:
            error = ConflictError("pending composite writer-lock cleanup remains")
            if drain.cleanup_error is not None:
                raise error from drain.cleanup_error
            raise error
