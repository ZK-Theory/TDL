from __future__ import annotations

import ctypes
import json
import os
import stat
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
import secrets
import threading
from types import TracebackType
from typing import Any, Literal, NoReturn, Protocol, Self

from research_system.canonical import canonical_bytes
from research_system.errors import ConflictError
from research_system.store.durability import fsync_directory


LockOwnerState = Literal["missing", "live", "stale", "unknown", "malformed"]


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
    kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
    kernel32.GetExitCodeProcess.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        exit_code = ctypes.c_uint32()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)) or exit_code.value != 259:
            return None
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


def _windows_process_has_exited(pid: int) -> bool | None:
    """Return an observed Windows exit, or ``None`` when it cannot be proved."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
    kernel32.GetExitCodeProcess.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return True if ctypes.get_last_error() == 87 else None  # ERROR_INVALID_PARAMETER: PID no longer exists
    try:
        exit_code = ctypes.c_uint32()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return None
        return exit_code.value != 259  # STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


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
    if os.name == "nt":
        exited = _windows_process_has_exited(pid)
        if exited is True:
            return "stale"
        return "unknown"
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return "stale"
    except PermissionError:
        return "unknown"
    except OSError:
        return "unknown"
    return "unknown"


def inspect_lock(path: Path) -> tuple[LockOwnerState, bytes | None, dict[str, Any] | None]:
    """Read a lock without making an ownership decision from PID alone."""
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return "missing", None, None
    except OSError:
        return "unknown", None, None
    try:
        record = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "malformed", data, None
    if not isinstance(record, dict):
        return "malformed", data, record if isinstance(record, dict) else None
    try:
        canonical = canonical_bytes(record)
    except (TypeError, ValueError):
        return "malformed", data, record
    if canonical != data:
        return "malformed", data, record
    return _owner_state(record), data, record


def _restore_recovery_claim(path: Path, claim: Path) -> None:
    """Restore a non-stale claim without replacing a newer lock generation."""
    try:
        os.link(claim, path)
    except FileExistsError:
        claim.unlink(missing_ok=True)
        fsync_directory(path.parent)
        return
    except OSError:
        return
    try:
        claim.unlink()
    except FileNotFoundError:
        pass
    fsync_directory(path.parent)


def remove_stale_lock(path: Path, observed: bytes) -> bool:
    """Atomically claim and remove one observed stale lock generation."""
    claim = path.with_name(f".{path.name}.{secrets.token_hex(16)}.reclaim")
    try:
        os.replace(path, claim)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    try:
        if claim.read_bytes() != observed:
            _restore_recovery_claim(path, claim)
            return False
        state, current, _ = inspect_lock(claim)
        if state != "stale" or current != observed:
            _restore_recovery_claim(path, claim)
            return False
        try:
            claim.unlink()
        except FileNotFoundError:
            return True
        fsync_directory(path.parent)
        return True
    except OSError:
        _restore_recovery_claim(path, claim)
        return False


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
    ) -> Self:
        instance = object.__new__(cls)
        object.__setattr__(instance, "identity", identity)
        object.__setattr__(instance, "final_path", final_path)
        object.__setattr__(instance, "runtime_identity", runtime_identity)
        object.__setattr__(instance, "runtime_final_path", runtime_final_path)
        object.__setattr__(instance, "aliases", aliases)
        object.__setattr__(instance, "_lease_token", lease_token)
        return instance


class _DirectoryAnchor:
    __slots__ = (
        "identity",
        "final_path",
        "_handle",
        "_refresh_impl",
        "_close_impl",
        "_closed",
    )

    def __init__(
        self,
        identity: DirectoryIdentity,
        final_path: Path,
        handle: object,
        refresh_impl: Callable[[object], tuple[DirectoryIdentity, Path]],
        close_impl: Callable[[object], None],
    ) -> None:
        self.identity = identity
        self.final_path = final_path
        self._handle = handle
        self._refresh_impl = refresh_impl
        self._close_impl = close_impl
        self._closed = False

    def refresh(self) -> tuple[DirectoryIdentity, Path]:
        if self._closed:
            raise ConflictError("directory anchor is no longer live")
        try:
            return self._refresh_impl(self._handle)
        except ConflictError:
            raise
        except (OSError, ValueError) as exc:
            raise ConflictError("directory anchor identity is unavailable") from exc

    def close(self) -> None:
        if self._closed:
            return
        self._close_impl(self._handle)
        self._closed = True


_delete_protected_anchor_state = threading.local()


def _active_delete_protected_anchors() -> list[_DirectoryAnchor]:
    anchors = getattr(_delete_protected_anchor_state, "anchors", None)
    if anchors is None:
        anchors = []
        _delete_protected_anchor_state.anchors = anchors
    return anchors


def register_delete_protected_directory_anchors(
    anchors: Iterable[DirectoryAnchor],
) -> tuple[_DirectoryAnchor, ...]:
    """Publish exact live anchors as a same-thread trust capability."""

    registered: list[_DirectoryAnchor] = []
    for anchor in anchors:
        if type(anchor) is not _DirectoryAnchor:
            raise ConflictError("delete-protected directory anchor is invalid")
        identity, final_path = anchor.refresh()
        if identity != anchor.identity or final_path != anchor.final_path:
            raise ConflictError("delete-protected directory anchor changed before registration")
        registered.append(anchor)
    _active_delete_protected_anchors().extend(registered)
    return tuple(registered)


def unregister_delete_protected_directory_anchors(anchors: Iterable[DirectoryAnchor]) -> None:
    """Remove only the exact same-thread anchors registered by the caller."""

    active = _active_delete_protected_anchors()
    for anchor in reversed(tuple(anchors)):
        for index in range(len(active) - 1, -1, -1):
            if active[index] is anchor:
                del active[index]
                break


def has_live_delete_protected_directory_anchor(path: Path) -> bool:
    """Return whether this thread holds the exact physical directory anchor."""

    try:
        requested = _root_sort_key(Path(path))[0]
        for anchor in reversed(_active_delete_protected_anchors()):
            identity, final_path = anchor.refresh()
            if (
                identity == anchor.identity
                and final_path == anchor.final_path
                and _root_sort_key(final_path)[0] == requested
            ):
                return True
        return False
    except ConflictError:
        return False


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

    _FILE_ATTRIBUTE_TAG_INFO_CLASS = 9
    _FILE_ID_INFO_CLASS = 18
    _FILE_ATTRIBUTE_DIRECTORY = 0x00000010
    _FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
    _FILE_READ_ATTRIBUTES = 0x00000080
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
    return OSError(error_code, f"{operation} failed: {ctypes.FormatError(error_code)}")


def _windows_open_handle(
    path: Path,
    *,
    open_reparse_point: bool,
    delete_protect: bool = False,
    share_delete: bool = False,
) -> object:
    flags = _FILE_FLAG_BACKUP_SEMANTICS
    if open_reparse_point:
        flags |= _FILE_FLAG_OPEN_REPARSE_POINT
    access = _FILE_READ_ATTRIBUTES | _SYNCHRONIZE
    if delete_protect:
        access |= _DELETE
    share_mode = _FILE_SHARE_READ | _FILE_SHARE_WRITE
    if share_delete:
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


def _windows_close_handle(handle: object) -> None:
    if not _KERNEL32.CloseHandle(handle):
        raise _windows_api_error("CloseHandle")


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
        inherited_delete_protection = delete_protect and has_live_delete_protected_directory_anchor(path)
        if reject_reparse:
            if inherited_delete_protection:
                probe = _windows_open_handle(path, open_reparse_point=True, share_delete=True)
            else:
                probe = _windows_open_handle(path, open_reparse_point=True)
            attributes, _ = _windows_file_attribute_tag(probe)
            if not attributes & _FILE_ATTRIBUTE_DIRECTORY:
                raise ConflictError(f"{path} is not an existing directory")
            if attributes & _FILE_ATTRIBUTE_REPARSE_POINT:
                raise ConflictError(f"{path} must not be a reparse directory")

        if inherited_delete_protection:
            handle = _windows_open_handle(path, open_reparse_point=False, share_delete=True)
        else:
            handle = _windows_open_handle(
                path,
                open_reparse_point=False,
                delete_protect=delete_protect and not reject_reparse,
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
                _windows_close_handle(probe)
            except BaseException as close_error:
                first_close_error = close_error
            else:
                probe = None
            if first_close_error is None and delete_protect and not inherited_delete_protection:
                # The live no-follow probe deliberately does not share delete,
                # so the followed comparison handle cannot request DELETE
                # until the probe has closed. Reopen the same final path with
                # DELETE access and compare its FileIdInfo before publishing.
                try:
                    _windows_close_handle(handle)
                except BaseException as close_error:
                    first_close_error = close_error
                else:
                    handle = None
                if first_close_error is None:
                    handle = _windows_open_handle(
                        final_path,
                        open_reparse_point=False,
                        delete_protect=True,
                    )
                    guarded_identity, guarded_final_path = _windows_anchor_refresh(handle)
                    if guarded_identity != identity:
                        raise ConflictError(f"{path} physical identity changed before delete-protected anchor")
                    identity, final_path = guarded_identity, guarded_final_path

        if first_close_error is None:
            anchor = _DirectoryAnchor(
                identity,
                final_path,
                handle,
                _windows_anchor_refresh,
                _windows_close_handle,
            )
            handle = None
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
                _windows_close_handle(candidate)
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
        anchor.close()


def _capture_claim(alias: Path) -> _RootClaim:
    root_anchor: _DirectoryAnchor | None = None
    runtime_anchor: _DirectoryAnchor | None = None
    try:
        root_anchor = _open_directory_anchor(alias)
        runtime_anchor = _open_directory_anchor(
            root_anchor.final_path / "runtime",
            reject_reparse=True,
        )
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
            try:
                _close_anchor(anchor)
            except BaseException as cleanup_error:
                if first_cleanup_error is None:
                    first_cleanup_error = cleanup_error
        if first_cleanup_error is not None:
            _raise_primary_with_cleanup(capture_error, first_cleanup_error)
        raise
    first_cleanup_error: BaseException | None = None
    for anchor in (runtime_anchor, root_anchor):
        try:
            _close_anchor(anchor)
        except BaseException as cleanup_error:
            if first_cleanup_error is None:
                first_cleanup_error = cleanup_error
    if first_cleanup_error is not None:
        raise first_cleanup_error
    return claim


def _verify_writer_lock(lock: Any, expected_runtime_path: Path) -> None:
    try:
        path = Path(lock.path)
        identity = lock.identity
    except AttributeError as exc:
        raise ConflictError("writer lock ownership record is unavailable") from exc
    expected_path = expected_runtime_path / "writer.lock"
    if path != expected_path:
        raise ConflictError("writer lock path is not under its runtime anchor")
    try:
        recorded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConflictError("writer lock ownership record cannot be verified") from exc
    if recorded != identity:
        raise ConflictError("writer lock ownership changed before protected work")


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

    def __enter__(self) -> Self:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{secrets.token_hex(16)}.tmp")
        try:
            with temporary.open("xb") as handle:
                handle.write(self._data)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                # A hard-link publication gives us a complete metadata file and
                # an O_EXCL-equivalent claim on the final path in one operation.
                os.link(temporary, self.path)
            except FileExistsError as exc:
                raise ConflictError(f"writer lock exists: {self.path}") from exc
            fsync_directory(self.path.parent)
        finally:
            temporary.unlink(missing_ok=True)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        try:
            recorded = json.loads(self.path.read_bytes())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as read_error:
            raise ConflictError("writer lock cannot be verified while held") from read_error
        if recorded != self.identity or canonical_bytes(recorded) != self._data:
            raise ConflictError("writer lock ownership changed while held")
        try:
            self.path.unlink()
        except FileNotFoundError as exc:
            raise ConflictError("writer lock disappeared while held") from exc
        fsync_directory(self.path.parent)
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
        self._registered_delete_protected_anchors: tuple[_DirectoryAnchor, ...] = ()
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
                and (getattr(cause, "winerror", None) == 32 or cause.errno == 32)
                and lock_state == "live"
            ):
                raise ConflictError(f"writer lock exists: {lock_path}") from exc
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
        for acquired in reversed(members):
            if not acquired.lock_entered or acquired.lock is None:
                continue
            try:
                acquired.lock.__exit__(exc_type, exc, traceback)
            except BaseException as release_error:
                if first_error is None:
                    first_error = release_error
            finally:
                acquired.lock_entered = False

        for acquired in reversed(members):
            for anchor in (acquired.runtime_anchor, acquired.root_anchor):
                try:
                    _close_anchor(anchor)
                except BaseException as close_error:
                    if first_error is None:
                        first_error = close_error
        return first_error

    def __enter__(self) -> Self:
        if self._lease_token is not None or self._active_members:
            raise RuntimeError("composite writer lock cannot be entered twice")

        lease_token = _LeaseState()
        self._lease_token = lease_token
        acquired_members: list[_AcquiredMember] = []
        try:
            for member in self._members:
                acquired = _AcquiredMember(member)
                acquired_members.append(acquired)
                self._prepare_member(acquired)
            self._final_fence(acquired_members)
            self._registered_delete_protected_anchors = register_delete_protected_directory_anchors(
                anchor
                for acquired in acquired_members
                for anchor in (acquired.root_anchor, acquired.runtime_anchor)
                if anchor is not None
            )

            locked_roots = tuple(
                LockedRoot._create(
                    identity=acquired.member.identity,
                    final_path=acquired.root_anchor.final_path,  # type: ignore[union-attr]
                    runtime_identity=acquired.member.runtime_identity,
                    runtime_final_path=acquired.runtime_anchor.final_path,  # type: ignore[union-attr]
                    aliases=acquired.member.aliases,
                    lease_token=lease_token,
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
            unregister_delete_protected_directory_anchors(self._registered_delete_protected_anchors)
            self._registered_delete_protected_anchors = ()
            lease_token.invalidate()
            cleanup_error = self._cleanup_members(
                acquired_members,
                exc_type=None,
                exc=None,
                traceback=None,
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
        finally:
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
        active_members, self._active_members = self._active_members, []
        unregister_delete_protected_directory_anchors(self._registered_delete_protected_anchors)
        self._registered_delete_protected_anchors = ()
        lease_token, self._lease_token = self._lease_token, None
        if lease_token is not None:
            lease_token.invalidate()
        self._locked_roots = ()
        self.paths = ()
        self._locks = ()
        self._acquired = []
        first_error = self._cleanup_members(
            active_members,
            exc_type=exc_type,
            exc=exc,
            traceback=traceback,
        )
        if first_error is not None:
            if exc is not None:
                raise exc.with_traceback(traceback) from first_error
            raise first_error
        return False
