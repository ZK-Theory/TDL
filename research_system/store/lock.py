from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import secrets
from types import TracebackType
from typing import Any, Literal, Self

from research_system.canonical import canonical_bytes
from research_system.errors import ConflictError


LockOwnerState = Literal["missing", "live", "stale", "unknown", "malformed"]


def _windows_process_instance_id(pid: int) -> str | None:
    """Return a Windows process creation-time identity, if it is queryable."""
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
    """Return a Linux process identity including the boot and start-time tuple."""
    if os.name == "nt":
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
    """Return an OS-backed process-instance identity, never PID alone."""
    if pid < 1:
        return None
    if os.name == "nt":
        return _windows_process_instance_id(pid)
    return _proc_process_instance_id(pid)


def current_process_instance_id() -> str:
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


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        return
    finally:
        os.close(descriptor)


def _restore_recovery_claim(path: Path, claim: Path) -> None:
    """Restore a non-stale claim without replacing a newer lock generation."""
    try:
        os.link(claim, path)
    except FileExistsError:
        claim.unlink(missing_ok=True)
        _fsync_directory(path.parent)
        return
    except OSError:
        return
    try:
        claim.unlink()
    except FileNotFoundError:
        pass
    _fsync_directory(path.parent)


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
        _fsync_directory(path.parent)
        return True
    except OSError:
        _restore_recovery_claim(path, claim)
        return False


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
            _fsync_directory(self.path.parent)
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
        _fsync_directory(self.path.parent)
        return False
